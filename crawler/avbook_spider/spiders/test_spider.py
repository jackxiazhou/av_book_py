"""
Test spider for creating sample data.
"""

import scrapy
from datetime import date, timedelta
import random
from ..items import MovieItem, MagnetItem


class TestSpider(scrapy.Spider):
    name = 'test'
    
    def start_requests(self):
        """生成测试数据"""
        # 只生成一个虚拟请求来触发数据创建
        yield scrapy.Request(
            url='http://httpbin.org/get',
            callback=self.create_test_data
        )
    
    def create_test_data(self, response):
        """创建测试数据"""
        self.logger.info("Creating test data...")
        
        # 创建测试影片
        for i in range(10):
            movie = self.create_test_movie(i)
            yield movie
            
            # 为每个影片创建1-3个磁力链接
            for j in range(random.randint(1, 3)):
                magnet = self.create_test_magnet(movie['censored_id'], j)
                yield magnet
    
    def create_test_movie(self, index):
        """创建测试影片"""
        prefixes = ['TEST', 'DEMO', 'SAMPLE']
        studios = ['Test Studio', 'Demo Productions', 'Sample Films']
        directors = ['Test Director', 'Demo Director']
        idols = ['Test Idol 1', 'Test Idol 2', 'Demo Actress']
        genres = ['测试', '演示', '样例', '高清', '字幕']
        
        prefix = random.choice(prefixes)
        number = str(index + 1).zfill(3)
        censored_id = f"{prefix}-{number}"
        
        movie = MovieItem()
        movie['censored_id'] = censored_id
        movie['movie_title'] = f"Test Movie {censored_id}"
        movie['movie_pic_cover'] = f"https://via.placeholder.com/300x400?text={censored_id}"
        movie['release_date'] = date.today() - timedelta(days=random.randint(1, 365))
        movie['movie_length'] = f"{random.randint(90, 180)}分钟"
        movie['director'] = random.choice(directors)
        movie['studio'] = random.choice(studios)
        movie['label'] = random.choice(studios)
        movie['series'] = f"Test Series {random.randint(1, 5)}"
        movie['genre'] = ', '.join(random.sample(genres, random.randint(2, 4)))
        movie['jav_idols'] = ', '.join(random.sample(idols, random.randint(1, 2)))
        movie['source'] = 'test'
        movie['source_url'] = f"http://test.com/{censored_id}"
        
        return movie
    
    def create_test_magnet(self, movie_id, index):
        """创建测试磁力链接"""
        qualities = ['sd', 'hd', 'fhd']
        uploaders = ['TestUser1', 'TestUser2', 'DemoUploader']
        
        # 生成假的磁力链接
        hash_value = ''.join(random.choices('0123456789ABCDEF', k=40))
        magnet_link = f"magnet:?xt=urn:btih:{hash_value}"
        
        quality = random.choice(qualities)
        
        magnet = MagnetItem()
        magnet['movie_censored_id'] = movie_id
        magnet['magnet_name'] = f"{movie_id} [{quality.upper()}] Test Magnet {index + 1}"
        magnet['magnet_link'] = magnet_link
        magnet['file_size'] = f"{random.uniform(1.0, 4.0):.1f}GB"
        magnet['file_size_bytes'] = random.randint(1000000000, 4000000000)
        magnet['seeders'] = random.randint(0, 50)
        magnet['leechers'] = random.randint(0, 20)
        magnet['completed'] = random.randint(0, 500)
        magnet['publish_date'] = date.today() - timedelta(days=random.randint(1, 30))
        magnet['uploader'] = random.choice(uploaders)
        magnet['source'] = 'test'
        magnet['source_url'] = f"http://test.com/magnet/{hash_value}"
        
        return magnet
