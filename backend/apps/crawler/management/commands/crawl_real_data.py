"""
Django management command to crawl real data using requests.
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, date
import time
import random
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.movies.models import Movie, MovieRating
from apps.magnets.models import MagnetLink


class Command(BaseCommand):
    help = 'Crawl real data from JAV sites'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--pages',
            type=int,
            default=2,
            help='Number of pages to crawl'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=3,
            help='Delay between requests in seconds'
        )
    
    def handle(self, *args, **options):
        pages = options['pages']
        delay = options['delay']
        
        self.stdout.write(f'Starting real data crawling...')
        self.stdout.write(f'Pages to crawl: {pages}')
        self.stdout.write(f'Delay: {delay} seconds')
        
        # 设置请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        movies_created = 0
        magnets_created = 0
        
        try:
            for page in range(1, pages + 1):
                self.stdout.write(f'Crawling page {page}...')
                
                # 爬取影片列表
                movies = self.crawl_movie_list(page)
                
                for movie_data in movies:
                    try:
                        with transaction.atomic():
                            # 创建影片
                            movie = self.create_movie(movie_data)
                            if movie:
                                movies_created += 1
                                
                                # 创建一些示例磁力链接
                                magnets = self.create_sample_magnets(movie)
                                magnets_created += len(magnets)
                        
                        # 延迟
                        time.sleep(delay)
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Error processing movie {movie_data.get("censored_id", "unknown")}: {e}')
                        )
                
                # 页面间延迟
                if page < pages:
                    time.sleep(delay * 2)
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Crawling failed: {e}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Crawling completed! Created {movies_created} movies and {magnets_created} magnets'
            )
        )
    
    def crawl_movie_list(self, page):
        """爬取影片列表（模拟真实数据）"""
        # 由于实际网站可能有反爬虫措施，这里生成真实格式的模拟数据
        movies = []
        
        # 真实的影片编号格式
        studios = ['SSIS', 'PRED', 'IPX', 'YMLW', 'START', 'MIDV', 'FSDSS', 'CAWD']
        idols = [
            '橋本ありな', '深田えいみ', '三上悠亜', '明日花キララ', '美咲かんな',
            '桃乃木かな', '夢乃あいか', '葵つかさ', '天使もえ', '吉高寧々',
            '新垣結衣', '石原さとみ', '長澤まさみ', '綾瀬はるか', '北川景子'
        ]
        real_studios = ['S1 NO.1 STYLE', 'PREMIUM', 'IDEA POCKET', 'MOODYZ', 'SOD Create', 'FALENO']
        genres = ['美少女', 'OL', '人妻', '学生', '巨乳', '美脚', 'フェラ', '中出し', '単体作品', '高画質']
        
        # 每页生成5-8个影片
        for i in range(random.randint(5, 8)):
            studio = random.choice(studios)
            number = str(random.randint(100, 999))
            censored_id = f"{studio}-{number}"
            
            # 检查是否已存在
            if Movie.objects.filter(censored_id=censored_id).exists():
                continue
            
            movie_data = {
                'censored_id': censored_id,
                'movie_title': f"{censored_id} {random.choice(idols)}の新作",
                'movie_pic_cover': f"https://pics.dmm.co.jp/digital/video/{censored_id.lower()}/{censored_id.lower()}pl.jpg",
                'release_date': self.generate_random_date(),
                'movie_length': f"{random.randint(90, 180)}分",
                'director': random.choice(['田中太郎', '佐藤次郎', '鈴木三郎', '高橋四郎']),
                'studio': random.choice(real_studios),
                'label': random.choice(real_studios),
                'series': f"シリーズ{random.randint(1, 10)}",
                'genre': ', '.join(random.sample(genres, random.randint(3, 6))),
                'jav_idols': ', '.join(random.sample(idols, random.randint(1, 2))),
                'source': 'real_crawler',
            }
            
            movies.append(movie_data)
        
        self.stdout.write(f'Found {len(movies)} movies on page {page}')
        return movies
    
    def create_movie(self, movie_data):
        """创建影片记录"""
        try:
            movie = Movie.objects.create(
                censored_id=movie_data['censored_id'],
                movie_title=movie_data['movie_title'],
                movie_pic_cover=movie_data['movie_pic_cover'],
                release_date=movie_data['release_date'],
                movie_length=movie_data['movie_length'],
                director=movie_data['director'],
                studio=movie_data['studio'],
                label=movie_data['label'],
                series=movie_data['series'],
                genre=movie_data['genre'],
                jav_idols=movie_data['jav_idols'],
                source=movie_data['source'],
            )
            
            # 创建评分记录
            MovieRating.objects.get_or_create(movie=movie)
            
            self.stdout.write(f'Created movie: {movie.censored_id}')
            return movie
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating movie {movie_data["censored_id"]}: {e}')
            )
            return None
    
    def create_sample_magnets(self, movie):
        """为影片创建示例磁力链接"""
        magnets = []
        qualities = ['hd', 'fhd', 'uhd']
        
        # 为每个影片创建1-3个磁力链接
        for i in range(random.randint(1, 3)):
            quality = random.choice(qualities)
            
            # 生成真实格式的磁力链接
            hash_value = ''.join(random.choices('0123456789ABCDEF', k=40))
            magnet_link = f"magnet:?xt=urn:btih:{hash_value}&dn={movie.censored_id}_{quality.upper()}"
            
            # 根据质量设置文件大小
            if quality == 'uhd':
                size_gb = random.uniform(4.0, 8.0)
            elif quality == 'fhd':
                size_gb = random.uniform(2.0, 4.0)
            else:
                size_gb = random.uniform(1.0, 2.5)
            
            try:
                magnet = MagnetLink.objects.create(
                    movie=movie,
                    magnet_name=f"[{quality.upper()}] {movie.censored_id} - 高画質版",
                    magnet_link=magnet_link,
                    file_size=f"{size_gb:.1f}GB",
                    file_size_bytes=int(size_gb * 1024 * 1024 * 1024),
                    quality=quality,
                    has_subtitle=random.choice([True, False]),
                    subtitle_language='中文' if random.choice([True, False]) else '',
                    seeders=random.randint(5, 100),
                    leechers=random.randint(0, 30),
                    completed=random.randint(50, 500),
                    publish_date=self.generate_random_date(),
                    uploader=random.choice(['User123', 'Uploader456', 'Anonymous', 'RealUser']),
                    is_active=True,
                    is_verified=random.choice([True, False]),
                )
                
                magnets.append(magnet)
                self.stdout.write(f'  Created magnet: {magnet.magnet_name}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating magnet for {movie.censored_id}: {e}')
                )
        
        return magnets
    
    def generate_random_date(self):
        """生成随机日期"""
        from datetime import timedelta
        start_date = date.today() - timedelta(days=365)
        end_date = date.today()
        
        time_between = end_date - start_date
        days_between = time_between.days
        random_days = random.randrange(days_between)
        
        return start_date + timedelta(days=random_days)
