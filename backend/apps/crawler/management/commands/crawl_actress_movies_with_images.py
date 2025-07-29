"""
Django管理命令 - 爬取现有女友的作品并保存图片
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import random
import os
from urllib.parse import urljoin, urlparse
from django.core.management.base import BaseCommand
from apps.actresses.models import Actress
from apps.movies.models import Movie
from django.db import transaction
from django.conf import settings
from django.utils import timezone
import hashlib


class Command(BaseCommand):
    help = '爬取现有女友的作品并保存图片'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-actresses',
            type=int,
            default=10,
            help='最大处理女友数量 (默认: 10)'
        )
        parser.add_argument(
            '--max-movies-per-actress',
            type=int,
            default=20,
            help='每个女友最大作品数 (默认: 20)'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=3,
            help='请求延迟（秒）'
        )
        parser.add_argument(
            '--download-images',
            action='store_true',
            help='下载并保存图片到本地'
        )
        parser.add_argument(
            '--actress-name',
            type=str,
            help='指定女友姓名'
        )
        parser.add_argument(
            '--continue-on-error',
            action='store_true',
            help='遇到错误时继续处理'
        )

    def handle(self, *args, **options):
        max_actresses = options['max_actresses']
        max_movies = options['max_movies_per_actress']
        delay = options['delay']
        download_images = options['download_images']
        actress_name = options.get('actress_name')
        continue_on_error = options['continue_on_error']

        self.stdout.write(
            self.style.SUCCESS('🎬 开始爬取女友作品和图片')
        )

        # 初始化
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
        })

        # 创建媒体目录
        if download_images:
            self.ensure_media_directories()

        # 获取要处理的女友
        actresses = self.get_actresses_to_process(actress_name, max_actresses)
        
        if not actresses:
            self.stdout.write(
                self.style.WARNING('❌ 没有找到符合条件的女友')
            )
            return

        self.stdout.write(f'📋 找到 {len(actresses)} 个女友需要处理')

        # 开始处理
        success_count = 0
        error_count = 0
        total_movies = 0
        total_images = 0

        for i, actress in enumerate(actresses, 1):
            self.stdout.write(f'\n👩 [{i}/{len(actresses)}] 处理女友: {actress.name}')
            
            try:
                movies_count, images_count = self.process_actress(
                    actress, max_movies, delay, download_images
                )
                
                success_count += 1
                total_movies += movies_count
                total_images += images_count
                
                self.stdout.write(f'  ✅ 成功: {movies_count} 个作品, {images_count} 张图片')
                
                # 更新女友爬取时间
                actress.last_crawled_at = timezone.now()
                actress.crawl_count += 1
                actress.save()

            except Exception as e:
                error_count += 1
                self.stdout.write(f'  ❌ 失败: {e}')
                
                if not continue_on_error:
                    break

            # 女友间延迟
            if i < len(actresses):
                delay_time = delay + random.uniform(0, 2)
                self.stdout.write(f'  ⏱️ 等待 {delay_time:.1f} 秒...')
                time.sleep(delay_time)

        # 统计结果
        self.stdout.write(f'\n🎉 处理完成!')
        self.stdout.write(f'📊 统计结果:')
        self.stdout.write(f'  成功女友: {success_count}')
        self.stdout.write(f'  失败女友: {error_count}')
        self.stdout.write(f'  总作品数: {total_movies}')
        self.stdout.write(f'  总图片数: {total_images}')

    def get_actresses_to_process(self, actress_name, max_count):
        """获取要处理的女友列表"""
        if actress_name:
            # 指定女友
            actresses = Actress.objects.filter(name__icontains=actress_name)
        else:
            # 优先处理有头像但缺少作品的女友
            actresses = Actress.objects.exclude(
                profile_image__isnull=True
            ).exclude(
                profile_image=''
            ).filter(
                movies__isnull=True
            ).distinct()
            
            # 如果没有，则处理所有有头像的女友
            if not actresses.exists():
                actresses = Actress.objects.exclude(
                    profile_image__isnull=True
                ).exclude(
                    profile_image=''
                )

        return list(actresses[:max_count])

    def process_actress(self, actress, max_movies, delay, download_images):
        """处理单个女友"""
        movies_count = 0
        images_count = 0
        
        # 构造女友URL
        actress_url = self.get_actress_url(actress)
        if not actress_url:
            self.stdout.write(f'    ❌ 无法构造女友URL')
            return movies_count, images_count

        # 爬取女友页面
        try:
            response = self.session.get(actress_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 获取作品链接
            movie_links = soup.select('a[href*="/movie/"]')
            movie_urls = []
            for link in movie_links:
                href = link.get('href')
                if href:
                    movie_url = urljoin(actress_url, href)
                    movie_urls.append(movie_url)
            
            # 去重并限制数量
            unique_movie_urls = list(set(movie_urls))[:max_movies]
            self.stdout.write(f'    🎬 找到 {len(unique_movie_urls)} 个作品')
            
            # 处理每个作品
            for j, movie_url in enumerate(unique_movie_urls, 1):
                self.stdout.write(f'      [{j}/{len(unique_movie_urls)}] 处理作品')
                
                movie_data = self.crawl_movie_with_images(movie_url, download_images)
                if movie_data:
                    movie = self.save_movie(movie_data, actress)
                    if movie:
                        movies_count += 1
                        images_count += movie_data.get('images_downloaded', 0)
                
                # 作品间延迟
                if j < len(unique_movie_urls):
                    time.sleep(1 + random.uniform(0, 1))
            
        except Exception as e:
            self.stdout.write(f'    ❌ 爬取女友页面失败: {e}')
        
        return movies_count, images_count

    def crawl_movie_with_images(self, movie_url, download_images):
        """爬取作品信息和图片"""
        try:
            response = self.session.get(movie_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            movie_data = {
                'source_url': movie_url,
                'images_downloaded': 0
            }
            
            # 提取番号
            title_text = soup.title.text if soup.title else ''
            if title_text:
                code_match = re.search(r'([A-Z]+-\d+|[A-Z]+\d+)', title_text)
                if code_match:
                    movie_data['censored_id'] = code_match.group(1)
            
            # 提取标题
            clean_title = re.sub(r'([A-Z]+-\d+|[A-Z]+\d+)', '', title_text)
            clean_title = re.sub(r' - AVMOO.*$', '', clean_title).strip()
            if clean_title:
                movie_data['movie_title'] = clean_title
            
            # 提取封面图片
            cover_img = soup.select_one('.screencap img, .bigImage img, .cover img')
            if cover_img:
                cover_src = cover_img.get('src')
                if cover_src:
                    cover_url = urljoin(movie_url, cover_src)
                    movie_data['cover_image'] = cover_url
                    
                    if download_images:
                        local_path = self.download_image(
                            cover_url, 
                            'cover', 
                            movie_data.get('censored_id', 'unknown')
                        )
                        if local_path:
                            movie_data['cover_image_local'] = local_path
                            movie_data['images_downloaded'] += 1
            
            # 提取样品图片
            sample_imgs = soup.select('.sample-box img, .samples img, .preview img')
            sample_urls = []
            sample_local_paths = []
            
            for i, img in enumerate(sample_imgs[:6]):  # 最多6张样品图
                src = img.get('src')
                if src:
                    sample_url = urljoin(movie_url, src)
                    sample_urls.append(sample_url)
                    
                    if download_images:
                        local_path = self.download_image(
                            sample_url, 
                            'sample', 
                            movie_data.get('censored_id', 'unknown'),
                            f'sample_{i+1:02d}'
                        )
                        if local_path:
                            sample_local_paths.append(local_path)
                            movie_data['images_downloaded'] += 1
            
            if sample_urls:
                movie_data['sample_images'] = '\n'.join(sample_urls)
            
            if sample_local_paths:
                movie_data['sample_images_local'] = '\n'.join(sample_local_paths)
            
            # 提取其他信息
            page_text = soup.get_text()
            
            # 发行日期
            date_patterns = [
                r'发行日期[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
                r'Release Date[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
                r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})'
            ]
            for pattern in date_patterns:
                match = re.search(pattern, page_text)
                if match:
                    movie_data['release_date'] = match.group(1).replace('/', '-')
                    break
            
            # 时长
            duration_patterns = [
                r'时长[：:]\s*(\d+)\s*分',
                r'Duration[：:]\s*(\d+)\s*min',
                r'(\d+)\s*分钟'
            ]
            for pattern in duration_patterns:
                match = re.search(pattern, page_text)
                if match:
                    movie_data['duration_minutes'] = int(match.group(1))
                    break
            
            # 制作商
            studio_patterns = [
                r'制作商[：:]\s*([^\n\r]+)',
                r'Studio[：:]\s*([^\n\r]+)'
            ]
            for pattern in studio_patterns:
                match = re.search(pattern, page_text)
                if match:
                    studio = match.group(1).strip()
                    if len(studio) < 50:
                        movie_data['studio'] = studio
                        break
            
            # 标签
            tags = soup.select('.genre a, .tags a')
            if tags:
                tag_list = [tag.get_text().strip() for tag in tags]
                movie_data['movie_tags'] = ', '.join(tag_list)
            
            return movie_data
            
        except Exception as e:
            self.stdout.write(f'        ❌ 爬取作品失败: {e}')
            return None

    def download_image(self, image_url, image_type, movie_id, filename=None):
        """下载图片到本地"""
        try:
            response = self.session.get(image_url, timeout=30)
            response.raise_for_status()
            
            # 获取文件扩展名
            parsed_url = urlparse(image_url)
            ext = os.path.splitext(parsed_url.path)[1]
            if not ext:
                ext = '.jpg'
            
            # 生成文件名
            if not filename:
                filename = f'{image_type}{ext}'
            else:
                filename = f'{filename}{ext}'
            
            # 创建目录路径
            movie_dir = os.path.join(
                settings.MEDIA_ROOT, 
                'images', 
                'movies', 
                movie_id
            )
            os.makedirs(movie_dir, exist_ok=True)
            
            # 保存文件
            file_path = os.path.join(movie_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # 返回相对路径
            relative_path = os.path.join('images', 'movies', movie_id, filename)
            return relative_path
            
        except Exception as e:
            self.stdout.write(f'          ❌ 下载图片失败 {image_url}: {e}')
            return None

    def save_movie(self, data, actress):
        """保存作品信息"""
        try:
            with transaction.atomic():
                movie, created = Movie.objects.get_or_create(
                    censored_id=data.get('censored_id', ''),
                    defaults={
                        'movie_title': data.get('movie_title'),
                        'release_date': data.get('release_date'),
                        'duration_minutes': data.get('duration_minutes'),
                        'studio': data.get('studio'),
                        'cover_image': data.get('cover_image'),
                        'cover_image_local': data.get('cover_image_local'),
                        'sample_images': data.get('sample_images'),
                        'sample_images_local': data.get('sample_images_local'),
                        'movie_tags': data.get('movie_tags'),
                        'source': 'actress_movies_crawl',
                    }
                )
                
                if not created:
                    # 更新现有记录
                    for field, value in data.items():
                        if value and hasattr(movie, field):
                            setattr(movie, field, value)
                    movie.save()
                
                # 建立女友和作品的关联
                movie.actresses.add(actress)
                
                return movie
                
        except Exception as e:
            self.stdout.write(f'        ❌ 保存作品失败: {e}')
            return None

    def get_actress_url(self, actress):
        """获取女友URL"""
        if actress.source_url:
            return actress.source_url
        
        # 尝试从姓名搜索构造URL（这里需要实际的搜索逻辑）
        return None

    def ensure_media_directories(self):
        """确保媒体目录存在"""
        media_dirs = [
            os.path.join(settings.MEDIA_ROOT, 'images'),
            os.path.join(settings.MEDIA_ROOT, 'images', 'movies'),
        ]
        
        for dir_path in media_dirs:
            os.makedirs(dir_path, exist_ok=True)
        
        self.stdout.write('📁 媒体目录已准备就绪')
