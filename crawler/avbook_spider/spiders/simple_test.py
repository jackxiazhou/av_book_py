"""
简单测试爬虫 - 用于测试基本功能
"""

import scrapy
import json
from datetime import datetime


class SimpleTestSpider(scrapy.Spider):
    name = 'simple_test'
    allowed_domains = ['avmoo.website']
    start_urls = ['https://avmoo.website/cn/actresses']
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1,
        'ITEM_PIPELINES': {},  # 不使用管道
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    def __init__(self, max_actresses=3, *args, **kwargs):
        super(SimpleTestSpider, self).__init__(*args, **kwargs)
        self.max_actresses = int(max_actresses)
        self.actresses_count = 0
        
        self.logger.info(f'Starting simple test spider with max_actresses={self.max_actresses}')
    
    def parse(self, response):
        """解析女友列表页面"""
        self.logger.info(f'Parsing actresses list page: {response.url}')
        
        # 尝试多种选择器找到女友链接
        actress_selectors = [
            '.star-box a::attr(href)',
            '.actress-box a::attr(href)', 
            '.avatar a::attr(href)',
            'a[href*="/star/"]::attr(href)',
            '.star-name a::attr(href)',
            '.photo-frame a::attr(href)',
            '.item a::attr(href)',
        ]
        
        actress_urls = []
        for selector in actress_selectors:
            urls = response.css(selector).getall()
            if urls:
                self.logger.info(f'Found {len(urls)} actress URLs with selector: {selector}')
                actress_urls.extend(urls[:self.max_actresses])  # 限制数量
                break
        
        if not actress_urls:
            self.logger.warning('No actress URLs found, trying xpath selectors')
            xpath_selectors = [
                '//a[contains(@href, "/star/")]/@href',
                '//div[@class="star-box"]//a/@href',
                '//div[@class="actress-box"]//a/@href'
            ]
            for xpath in xpath_selectors:
                urls = response.xpath(xpath).getall()
                if urls:
                    self.logger.info(f'Found {len(urls)} actress URLs with xpath: {xpath}')
                    actress_urls.extend(urls[:self.max_actresses])
                    break
        
        # 处理找到的女友链接
        for url in actress_urls[:self.max_actresses]:
            if self.actresses_count >= self.max_actresses:
                break
                
            full_url = response.urljoin(url)
            self.logger.info(f'Following actress URL: {full_url}')
            
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_actress,
                meta={'actress_url': full_url}
            )
    
    def parse_actress(self, response):
        """解析女友详情页面"""
        self.actresses_count += 1
        actress_url = response.meta.get('actress_url', response.url)
        
        self.logger.info(f'Parsing actress detail ({self.actresses_count}/{self.max_actresses}): {response.url}')
        
        # 提取女友基本信息
        actress_data = {
            'data_type': 'actress',
            'source_url': response.url,
            'crawled_at': datetime.now().isoformat(),
        }
        
        # 尝试提取姓名
        name_selectors = [
            '.star-name::text',
            '.actress-name::text',
            'h1::text',
            '.title::text',
            '.name::text'
        ]
        
        for selector in name_selectors:
            name = response.css(selector).get()
            if name:
                actress_data['name'] = name.strip()
                self.logger.info(f'Found actress name: {name.strip()}')
                break
        
        # 尝试提取个人信息
        info_text = response.text
        
        # 身高
        import re
        height_match = re.search(r'身高[：:]\s*(\d+)\s*cm', info_text, re.IGNORECASE)
        if height_match:
            actress_data['height'] = int(height_match.group(1))
        
        # 三围
        measurements_match = re.search(r'三围[：:]\s*([B-Z]\d+[-–]\w\d+[-–]\w\d+)', info_text, re.IGNORECASE)
        if measurements_match:
            actress_data['measurements'] = measurements_match.group(1)
        
        # 罩杯
        cup_match = re.search(r'罩杯[：:]\s*([A-Z]+)', info_text, re.IGNORECASE)
        if cup_match:
            actress_data['cup_size'] = cup_match.group(1)
        
        # 提取头像图片
        profile_selectors = [
            '.star-photo img::attr(src)',
            '.actress-photo img::attr(src)',
            '.profile-image img::attr(src)',
            '.avatar img::attr(src)',
            '.photo img::attr(src)'
        ]
        
        for selector in profile_selectors:
            profile_img = response.css(selector).get()
            if profile_img:
                actress_data['profile_image'] = response.urljoin(profile_img)
                break
        
        # 输出女友数据
        if actress_data.get('name'):
            yield actress_data
            self.logger.info(f'Successfully extracted actress data: {actress_data.get("name")}')
        else:
            self.logger.warning(f'No name found for actress at {response.url}')
        
        # 查找作品链接（简化版本，只取前几个）
        movie_selectors = [
            '.movie-box a::attr(href)',
            '.item a::attr(href)',
            'a[href*="/movie/"]::attr(href)',
        ]
        
        movie_urls = []
        for selector in movie_selectors:
            urls = response.css(selector).getall()
            if urls:
                movie_urls.extend(urls[:2])  # 只取前2个作品
                break
        
        # 爬取作品详情
        for movie_url in movie_urls:
            full_movie_url = response.urljoin(movie_url)
            yield scrapy.Request(
                url=full_movie_url,
                callback=self.parse_movie,
                meta={
                    'actress_name': actress_data.get('name'),
                    'actress_url': actress_url
                }
            )
    
    def parse_movie(self, response):
        """解析作品详情页面"""
        actress_name = response.meta.get('actress_name')
        self.logger.info(f'Parsing movie for actress {actress_name}: {response.url}')
        
        movie_data = {
            'data_type': 'movie',
            'source_url': response.url,
            'crawled_at': datetime.now().isoformat(),
            'related_actress': actress_name,
            'actress_url': response.meta.get('actress_url')
        }
        
        # 提取作品编号
        id_selectors = [
            '.movie-id::text',
            '.code::text',
            '.number::text',
            '.title::text'
        ]
        
        for selector in id_selectors:
            movie_id = response.css(selector).get()
            if movie_id and re.match(r'^[A-Z0-9]+-\d+', movie_id.strip()):
                movie_data['censored_id'] = movie_id.strip()
                break
        
        # 提取作品标题
        title_selectors = [
            '.movie-title::text',
            '.title::text',
            'h1::text',
        ]
        
        for selector in title_selectors:
            title = response.css(selector).get()
            if title:
                movie_data['movie_title'] = title.strip()
                break
        
        # 提取封面图片
        cover_selectors = [
            '.movie-cover img::attr(src)',
            '.cover img::attr(src)',
            '.poster img::attr(src)',
        ]
        
        for selector in cover_selectors:
            cover = response.css(selector).get()
            if cover:
                movie_data['movie_pic_cover'] = response.urljoin(cover)
                break
        
        # 输出作品数据
        if movie_data.get('censored_id') or movie_data.get('movie_title'):
            yield movie_data
            self.logger.info(f'Successfully extracted movie data: {movie_data.get("censored_id", "Unknown")}')
        else:
            self.logger.warning(f'No valid movie data found at {response.url}')
    
    def closed(self, reason):
        """爬虫结束时的统计"""
        self.logger.info(f'Spider closed: {reason}')
        self.logger.info(f'Total actresses processed: {self.actresses_count}')
