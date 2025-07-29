"""
Demo spider for testing real data crawling.
"""

import scrapy
import re
from datetime import date, timedelta
import random
from ..items import MovieItem, MagnetItem


class DemoSpider(scrapy.Spider):
    name = 'demo'
    
    # 使用一个简单的测试网站
    start_urls = ['http://httpbin.org/get']
    
    def parse(self, response):
        """生成真实格式的测试数据"""
        self.logger.info("Creating realistic demo data...")
        
        # 创建一些真实格式的测试影片
        for i in range(5):
            movie = self.create_realistic_movie(i)
            yield movie
            
            # 为每个影片创建磁力链接
            for j in range(random.randint(1, 3)):
                magnet = self.create_realistic_magnet(movie['censored_id'], j)
                yield magnet
    
    def create_realistic_movie(self, index):
        """创建真实格式的测试影片"""
        # 真实的影片编号格式
        studios = ['SSIS', 'PRED', 'IPX', 'YMLW', 'START']
        studio = random.choice(studios)
        number = str(random.randint(100, 999))
        censored_id = f"{studio}-{number}"
        
        # 真实的演员名字
        idols = [
            '橋本ありな', '深田えいみ', '三上悠亜', '明日花キララ', '美咲かんな',
            '桃乃木かな', '夢乃あいか', '葵つかさ', '天使もえ', '吉高寧々'
        ]
        
        # 真实的制作商
        real_studios = ['S1 NO.1 STYLE', 'PREMIUM', 'IDEA POCKET', 'MOODYZ', 'SOD Create']
        
        # 真实的类型
        genres = ['美少女', 'OL', '人妻', '学生', '巨乳', '美脚', 'フェラ', '中出し', '単体作品', '高画質']
        
        movie = MovieItem()
        movie['censored_id'] = censored_id
        movie['movie_title'] = f"{censored_id} {random.choice(idols)}の新作"
        movie['movie_pic_cover'] = f"https://pics.dmm.co.jp/digital/video/{censored_id.lower()}/{censored_id.lower()}pl.jpg"
        movie['release_date'] = date.today() - timedelta(days=random.randint(1, 365))
        movie['movie_length'] = f"{random.randint(90, 180)}分"
        movie['director'] = random.choice(['田中太郎', '佐藤次郎', '鈴木三郎'])
        movie['studio'] = random.choice(real_studios)
        movie['label'] = movie['studio']
        movie['series'] = f"シリーズ{random.randint(1, 10)}"
        movie['genre'] = ', '.join(random.sample(genres, random.randint(3, 6)))
        movie['jav_idols'] = ', '.join(random.sample(idols, random.randint(1, 2)))
        movie['source'] = 'demo_crawler'
        movie['source_url'] = f"https://www.javbus.com/{censored_id}"
        
        return movie
    
    def create_realistic_magnet(self, movie_id, index):
        """创建真实格式的磁力链接"""
        qualities = ['HD', 'FHD', 'UHD']
        quality = random.choice(qualities)
        
        # 生成真实格式的磁力链接
        hash_value = ''.join(random.choices('0123456789ABCDEF', k=40))
        magnet_link = f"magnet:?xt=urn:btih:{hash_value}&dn={movie_id}_{quality}&tr=udp://tracker.example.com:80"
        
        # 真实的文件大小
        if quality == 'UHD':
            size_gb = random.uniform(4.0, 8.0)
        elif quality == 'FHD':
            size_gb = random.uniform(2.0, 4.0)
        else:
            size_gb = random.uniform(1.0, 2.5)
        
        magnet = MagnetItem()
        magnet['movie_censored_id'] = movie_id
        magnet['magnet_name'] = f"[{quality}] {movie_id} - 高画質版"
        magnet['magnet_link'] = magnet_link
        magnet['file_size'] = f"{size_gb:.1f}GB"
        magnet['file_size_bytes'] = int(size_gb * 1024 * 1024 * 1024)
        magnet['quality'] = quality.lower()
        magnet['has_subtitle'] = random.choice([True, False])
        magnet['subtitle_language'] = '中文' if magnet['has_subtitle'] else ''
        magnet['seeders'] = random.randint(5, 100)
        magnet['leechers'] = random.randint(0, 30)
        magnet['completed'] = random.randint(50, 500)
        magnet['publish_date'] = date.today() - timedelta(days=random.randint(1, 30))
        magnet['uploader'] = random.choice(['User123', 'Uploader456', 'Anonymous'])
        magnet['source'] = 'demo_crawler'
        magnet['source_url'] = f"https://www.javbus.com/{movie_id}"
        
        return magnet
