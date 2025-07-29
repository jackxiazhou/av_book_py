"""
Django管理命令 - 递归爬取女友完整信息
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import random
from urllib.parse import urljoin
from django.core.management.base import BaseCommand
from apps.actresses.models import Actress
from apps.movies.models import Movie
from django.db import transaction
import json


class Command(BaseCommand):
    help = '递归爬取女友完整信息和相关作品'

    def add_arguments(self, parser):
        parser.add_argument(
            '--actress-url',
            type=str,
            help='女友详情页URL'
        )
        parser.add_argument(
            '--actress-id',
            type=str,
            help='女友ID'
        )
        parser.add_argument(
            '--max-movies',
            type=int,
            default=20,
            help='最大爬取作品数量'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=3,
            help='请求延迟（秒）'
        )

    def handle(self, *args, **options):
        actress_url = options.get('actress_url')
        actress_id = options.get('actress_id')
        max_movies = options['max_movies']
        delay = options['delay']

        if not actress_url and not actress_id:
            self.stdout.write(
                self.style.ERROR('请提供 --actress-url 或 --actress-id 参数')
            )
            return

        if actress_id and not actress_url:
            actress_url = f'https://avmoo.website/cn/star/{actress_id}'

        self.stdout.write(
            self.style.SUCCESS(f'🕷️ 开始递归爬取女友信息: {actress_url}')
        )

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
        })

        try:
            # 爬取女友信息
            actress_data = self.crawl_actress(actress_url)
            if not actress_data:
                self.stdout.write(self.style.ERROR('❌ 女友信息爬取失败'))
                return

            # 保存女友信息
            actress = self.save_actress(actress_data)
            if not actress:
                self.stdout.write(self.style.ERROR('❌ 女友信息保存失败'))
                return

            self.stdout.write(f'✅ 女友信息保存成功: {actress.name}')

            # 爬取作品信息
            movie_urls = actress_data.get('movie_urls', [])[:max_movies]
            self.stdout.write(f'🎬 开始爬取 {len(movie_urls)} 个作品')

            movies_saved = 0
            for i, movie_url in enumerate(movie_urls, 1):
                self.stdout.write(f'  爬取作品 {i}/{len(movie_urls)}: {movie_url}')
                
                movie_data = self.crawl_movie(movie_url)
                if movie_data:
                    movie = self.save_movie(movie_data, actress)
                    if movie:
                        movies_saved += 1
                        self.stdout.write(f'    ✅ 保存成功: {movie.censored_id}')
                    else:
                        self.stdout.write(f'    ❌ 保存失败')
                else:
                    self.stdout.write(f'    ❌ 爬取失败')

                # 延迟
                if i < len(movie_urls):
                    time.sleep(delay + random.uniform(0, 2))

            self.stdout.write(
                self.style.SUCCESS(f'🎉 爬取完成！保存了 {movies_saved} 个作品')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 爬取过程出错: {e}')
            )

    def crawl_actress(self, url):
        """爬取女友信息"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            actress_data = {
                'source_url': url,
                'movie_urls': []
            }
            
            # 提取女友ID
            actress_id_match = re.search(r'/star/([a-f0-9]+)', url)
            if actress_id_match:
                actress_data['actress_id'] = actress_id_match.group(1)
            
            # 提取姓名
            title_text = soup.title.text if soup.title else ''
            if title_text and ' - ' in title_text:
                actress_data['name'] = title_text.split(' - ')[0].strip()
            
            # 提取头像
            img_elements = soup.select('img')
            for img in img_elements:
                src = img.get('src')
                if src and any(keyword in src.lower() for keyword in ['avatar', 'photo', 'image']) and src.endswith(('.jpg', '.png', '.jpeg')):
                    actress_data['profile_image'] = urljoin(url, src)
                    break
            
            # 提取详细信息
            page_text = soup.get_text()
            
            # 生日
            birthday_patterns = [
                r'生日[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
                r'Birthday[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
                r'出生[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})'
            ]
            for pattern in birthday_patterns:
                match = re.search(pattern, page_text)
                if match:
                    actress_data['birth_date'] = match.group(1).replace('/', '-')
                    break
            
            # 身高
            height_patterns = [
                r'身高[：:]\s*(\d+)\s*cm',
                r'Height[：:]\s*(\d+)\s*cm'
            ]
            for pattern in height_patterns:
                match = re.search(pattern, page_text)
                if match:
                    height = int(match.group(1))
                    if 140 <= height <= 200:
                        actress_data['height'] = height
                        break
            
            # 罩杯
            cup_patterns = [
                r'罩杯[：:]\s*([A-Z]+)',
                r'Cup[：:]\s*([A-Z]+)'
            ]
            for pattern in cup_patterns:
                match = re.search(pattern, page_text)
                if match:
                    actress_data['cup_size'] = match.group(1)
                    break
            
            # 三围
            measurements_patterns = [
                r'三围[：:]\s*(\d+[-/]\d+[-/]\d+)',
                r'BWH[：:]\s*(\d+[-/]\d+[-/]\d+)'
            ]
            for pattern in measurements_patterns:
                match = re.search(pattern, page_text)
                if match:
                    actress_data['measurements'] = match.group(1).replace('/', '-')
                    break
            
            # 获取作品链接
            movie_links = soup.select('a[href*="/movie/"]')
            for link in movie_links:
                href = link.get('href')
                if href:
                    movie_url = urljoin(url, href)
                    actress_data['movie_urls'].append(movie_url)
            
            # 去重
            actress_data['movie_urls'] = list(set(actress_data['movie_urls']))
            
            return actress_data
            
        except Exception as e:
            self.stdout.write(f'爬取女友信息失败: {e}')
            return None

    def crawl_movie(self, url):
        """爬取作品信息"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            movie_data = {
                'source_url': url
            }
            
            # 提取番号和标题
            title_text = soup.title.text if soup.title else ''
            if title_text:
                # 从标题中提取番号
                code_match = re.search(r'([A-Z]+-\d+|[A-Z]+\d+)', title_text)
                if code_match:
                    movie_data['censored_id'] = code_match.group(1)
                
                # 提取标题（去掉番号和网站名）
                clean_title = re.sub(r'([A-Z]+-\d+|[A-Z]+\d+)', '', title_text)
                clean_title = re.sub(r' - AVMOO.*$', '', clean_title).strip()
                if clean_title:
                    movie_data['movie_title'] = clean_title
            
            # 提取封面图片
            img_elements = soup.select('img')
            for img in img_elements:
                src = img.get('src')
                if src and src.endswith(('.jpg', '.png', '.jpeg')):
                    movie_data['cover_image'] = urljoin(url, src)
                    break
            
            # 提取页面文本信息
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
                    if len(studio) < 50:  # 避免过长的文本
                        movie_data['studio'] = studio
                        break
            
            return movie_data
            
        except Exception as e:
            self.stdout.write(f'爬取作品信息失败: {e}')
            return None

    def save_actress(self, data):
        """保存女友信息"""
        try:
            with transaction.atomic():
                actress, created = Actress.objects.get_or_create(
                    name=data.get('name', ''),
                    defaults={
                        'birth_date': data.get('birth_date'),
                        'height': data.get('height'),
                        'cup_size': data.get('cup_size'),
                        'measurements': data.get('measurements'),
                        'profile_image': data.get('profile_image'),
                        'source': 'avmoo_recursive',
                    }
                )
                
                if not created:
                    # 更新现有记录
                    for field, value in data.items():
                        if value and hasattr(actress, field):
                            setattr(actress, field, value)
                    actress.save()
                
                return actress
                
        except Exception as e:
            self.stdout.write(f'保存女友信息失败: {e}')
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
                        'source': 'avmoo_recursive',
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
            self.stdout.write(f'保存作品信息失败: {e}')
            return None
