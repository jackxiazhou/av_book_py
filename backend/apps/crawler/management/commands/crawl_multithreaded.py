"""
Django管理命令 - 多线程爬取女友作品和图片
"""

import threading
import queue
import time
import random
import requests
from bs4 import BeautifulSoup
import re
import os
from urllib.parse import urljoin, urlparse
from django.core.management.base import BaseCommand
from apps.actresses.models import Actress
from apps.movies.models import Movie
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging


class Command(BaseCommand):
    help = '多线程爬取女友作品和图片'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-actresses',
            type=int,
            default=100,
            help='最大爬取女友数量'
        )
        parser.add_argument(
            '--max-workers',
            type=int,
            default=5,
            help='最大线程数'
        )
        parser.add_argument(
            '--max-movies-per-actress',
            type=int,
            default=15,
            help='每个女友最大作品数'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='请求延迟（秒）'
        )

    def handle(self, *args, **options):
        max_actresses = options['max_actresses']
        max_workers = options['max_workers']
        max_movies = options['max_movies_per_actress']
        delay = options['delay']

        self.stdout.write(
            self.style.SUCCESS(f'🚀 启动多线程爬取 ({max_workers} 线程)')
        )

        # 初始化
        self.delay = delay
        self.max_movies = max_movies
        self.session_pool = self.create_session_pool(max_workers)
        self.ensure_media_directories()

        # 获取女友列表
        actresses = self.get_actresses_to_crawl(max_actresses)
        self.stdout.write(f'📋 找到 {len(actresses)} 个女友需要爬取')

        # 多线程爬取
        start_time = timezone.now()
        results = self.crawl_actresses_multithreaded(actresses, max_workers)
        end_time = timezone.now()

        # 统计结果
        success_count = sum(1 for r in results if r['success'])
        total_movies = sum(r['movies'] for r in results)
        total_images = sum(r['images'] for r in results)
        
        self.stdout.write(f'\n🎉 多线程爬取完成!')
        self.stdout.write(f'📊 统计结果:')
        self.stdout.write(f'  成功女友: {success_count}/{len(actresses)}')
        self.stdout.write(f'  总作品数: {total_movies}')
        self.stdout.write(f'  总图片数: {total_images}')
        self.stdout.write(f'  总耗时: {end_time - start_time}')
        self.stdout.write(f'  平均速度: {len(actresses) / (end_time - start_time).total_seconds():.2f} 女友/秒')

    def create_session_pool(self, pool_size):
        """创建会话池"""
        sessions = []
        for _ in range(pool_size):
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
            })
            sessions.append(session)
        return sessions

    def get_actresses_to_crawl(self, max_count):
        """获取要爬取的女友列表"""
        # 优先选择有头像但作品较少的女友
        actresses = Actress.objects.exclude(
            profile_image__isnull=True
        ).exclude(
            profile_image=''
        ).order_by('?')[:max_count]  # 随机排序避免重复爬取同一批
        
        return list(actresses)

    def crawl_actresses_multithreaded(self, actresses, max_workers):
        """多线程爬取女友"""
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_actress = {
                executor.submit(self.crawl_single_actress, actress, i % len(self.session_pool)): actress 
                for i, actress in enumerate(actresses)
            }
            
            # 处理结果
            for future in as_completed(future_to_actress):
                actress = future_to_actress[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['success']:
                        self.stdout.write(f'✅ {actress.name}: {result["movies"]} 作品, {result["images"]} 图片')
                    else:
                        self.stdout.write(f'❌ {actress.name}: {result["error"]}')
                        
                except Exception as e:
                    self.stdout.write(f'❌ {actress.name}: 线程异常 {e}')
                    results.append({
                        'actress': actress.name,
                        'success': False,
                        'movies': 0,
                        'images': 0,
                        'error': str(e)
                    })
        
        return results

    def crawl_single_actress(self, actress, session_index):
        """爬取单个女友"""
        session = self.session_pool[session_index]
        result = {
            'actress': actress.name,
            'success': False,
            'movies': 0,
            'images': 0,
            'error': None
        }
        
        try:
            # 构造女友URL
            actress_url = self.get_actress_url(actress)
            if not actress_url:
                result['error'] = '无法构造女友URL'
                return result
            
            # 爬取女友页面
            response = session.get(actress_url, timeout=30)
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
            unique_movie_urls = list(set(movie_urls))[:self.max_movies]
            
            # 爬取作品
            movies_count = 0
            images_count = 0
            
            for movie_url in unique_movie_urls:
                try:
                    movie_data = self.crawl_movie_with_images(movie_url, session)
                    if movie_data:
                        movie = self.save_movie(movie_data, actress)
                        if movie:
                            movies_count += 1
                            images_count += movie_data.get('images_downloaded', 0)
                    
                    # 延迟
                    time.sleep(self.delay + random.uniform(0, 0.5))
                    
                except Exception as e:
                    continue  # 跳过失败的作品
            
            result['success'] = True
            result['movies'] = movies_count
            result['images'] = images_count
            
            # 更新女友信息
            with transaction.atomic():
                actress.last_crawled_at = timezone.now()
                actress.crawl_count += 1
                actress.save()
            
        except Exception as e:
            result['error'] = str(e)
        
        return result

    def crawl_movie_with_images(self, movie_url, session):
        """爬取作品信息和图片"""
        try:
            response = session.get(movie_url, timeout=30)
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
                    
                    # 下载封面
                    local_path = self.download_image(
                        cover_url, 
                        'cover', 
                        movie_data.get('censored_id', 'unknown'),
                        session
                    )
                    if local_path:
                        movie_data['cover_image_local'] = local_path
                        movie_data['images_downloaded'] += 1
            
            # 提取样品图片
            sample_imgs = soup.select('.sample-box img, .samples img, .preview img')
            sample_urls = []
            sample_local_paths = []
            
            for i, img in enumerate(sample_imgs[:6]):
                src = img.get('src')
                if src:
                    sample_url = urljoin(movie_url, src)
                    sample_urls.append(sample_url)
                    
                    # 下载样品图
                    local_path = self.download_image(
                        sample_url, 
                        'sample', 
                        movie_data.get('censored_id', 'unknown'),
                        session,
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
            date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', page_text)
            if date_match:
                movie_data['release_date'] = date_match.group(1).replace('/', '-')
            
            # 时长
            duration_match = re.search(r'(\d+)\s*分', page_text)
            if duration_match:
                movie_data['duration_minutes'] = int(duration_match.group(1))
            
            # 制作商
            studio_match = re.search(r'制作商[：:]\s*([^\n\r]+)', page_text)
            if studio_match:
                studio = studio_match.group(1).strip()
                if len(studio) < 50:
                    movie_data['studio'] = studio
            
            return movie_data
            
        except Exception as e:
            return None

    def download_image(self, image_url, image_type, movie_id, session, filename=None):
        """下载图片"""
        try:
            response = session.get(image_url, timeout=30)
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
            
            # 验证文件大小
            file_size = os.path.getsize(file_path)
            if file_size < 1024:
                os.remove(file_path)
                return None
            
            # 返回相对路径
            relative_path = os.path.join('images', 'movies', movie_id, filename)
            return relative_path
            
        except Exception as e:
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
                        'source': 'multithreaded_crawl',
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
            return None

    def get_actress_url(self, actress):
        """获取女友URL"""
        if actress.source_url:
            return actress.source_url
        return None

    def ensure_media_directories(self):
        """确保媒体目录存在"""
        media_dirs = [
            os.path.join(settings.MEDIA_ROOT, 'images'),
            os.path.join(settings.MEDIA_ROOT, 'images', 'movies'),
        ]
        
        for dir_path in media_dirs:
            os.makedirs(dir_path, exist_ok=True)
