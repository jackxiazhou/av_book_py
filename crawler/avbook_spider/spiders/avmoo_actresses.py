"""
AVMoo女友爬虫 - 爬取真实的女友图片和信息
"""

import scrapy
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime
import json


class AvmooActressesSpider(scrapy.Spider):
    name = 'avmoo_actresses'
    allowed_domains = ['avmoo.cyou', 'avmoo.com', 'avmoo.net']
    
    # AVMoo女友列表页面
    start_urls = [
        'https://avmoo.cyou/cn/star',
        'https://avmoo.cyou/star',
    ]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 3,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'COOKIES_ENABLED': True,
        'RETRY_TIMES': 5,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429, 403, 404],
    }
    
    def __init__(self, max_pages=10, max_actresses=50, *args, **kwargs):
        super(AvmooActressesSpider, self).__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        self.max_actresses = int(max_actresses)
        self.actresses_count = 0
        self.processed_urls = set()
        
        self.logger.info(f'Starting AVMoo actresses spider with max_pages={self.max_pages}, max_actresses={self.max_actresses}')
    
    def start_requests(self):
        """生成起始请求"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                headers=headers,
                callback=self.parse_actress_list,
                meta={'page': 1}
            )
    
    def parse_actress_list(self, response):
        """解析女友列表页面"""
        page = response.meta.get('page', 1)
        self.logger.info(f'Parsing actress list page {page}: {response.url}')
        
        # 查找女友链接的多种选择器
        actress_selectors = [
            '.star-box a::attr(href)',
            '.actress-box a::attr(href)',
            '.avatar a::attr(href)',
            'a[href*="/star/"]::attr(href)',
            'a[href*="/actress/"]::attr(href)',
            '.star-name a::attr(href)',
            '.photo-frame a::attr(href)'
        ]
        
        actress_urls = []
        for selector in actress_selectors:
            urls = response.css(selector).getall()
            if urls:
                self.logger.info(f'Found {len(urls)} actress URLs with selector: {selector}')
                actress_urls.extend(urls)
                break
        
        # 去重并转换为绝对URL
        unique_urls = []
        for url in actress_urls:
            if url and url not in self.processed_urls:
                full_url = urljoin(response.url, url)
                if '/star/' in full_url or '/actress/' in full_url:
                    unique_urls.append(full_url)
                    self.processed_urls.add(url)
        
        self.logger.info(f'Found {len(unique_urls)} unique actress URLs on page {page}')
        
        # 爬取女友详情页面
        for actress_url in unique_urls:
            if self.actresses_count >= self.max_actresses:
                self.logger.info(f'Reached max actresses limit: {self.max_actresses}')
                return
            
            yield scrapy.Request(
                url=actress_url,
                callback=self.parse_actress_detail,
                meta={'page': page},
                headers=response.request.headers
            )
        
        # 爬取下一页
        if page < self.max_pages and unique_urls:
            next_page_urls = [
                f"{response.url}?page={page + 1}",
                f"{response.url}/page/{page + 1}",
                urljoin(response.url, f"?p={page + 1}"),
            ]
            
            # 也尝试查找下一页链接
            next_links = response.css('a[href*="page"]:contains("下一页")::attr(href), a[href*="next"]::attr(href), .pagination a:last-child::attr(href)').getall()
            if next_links:
                next_page_urls.extend([urljoin(response.url, link) for link in next_links])
            
            for next_url in next_page_urls:
                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse_actress_list,
                    meta={'page': page + 1},
                    headers=response.request.headers
                )
                break  # 只尝试第一个有效的下一页URL
    
    def parse_actress_detail(self, response):
        """解析女友详情页面"""
        self.actresses_count += 1
        self.logger.info(f'Parsing actress detail ({self.actresses_count}/{self.max_actresses}): {response.url}')
        
        try:
            actress_data = {}
            
            # 基本信息提取
            actress_data.update(self.extract_basic_info(response))
            
            # 个人资料提取
            actress_data.update(self.extract_personal_info(response))
            
            # 图片信息提取
            actress_data.update(self.extract_image_info(response))
            
            # 作品信息提取
            actress_data.update(self.extract_movie_info(response))
            
            # 添加爬取信息
            actress_data['source_url'] = response.url
            actress_data['crawled_at'] = datetime.now().isoformat()
            
            if actress_data.get('name'):
                yield actress_data
            else:
                self.logger.warning(f'No name found for actress at {response.url}')
                
        except Exception as e:
            self.logger.error(f'Error parsing actress detail {response.url}: {e}')
    
    def extract_basic_info(self, response):
        """提取基本信息"""
        data = {}
        
        # 姓名提取 - 多种选择器
        name_selectors = [
            '.avatar-box .photo-info span::text',
            '.star-name::text',
            '.actress-name::text',
            'h1::text',
            '.title::text',
            '.name::text'
        ]
        
        for selector in name_selectors:
            name = response.css(selector).get()
            if name:
                name = name.strip()
                if name and len(name) > 1:
                    data['name'] = name
                    break
        
        # 如果没有找到姓名，从URL中提取
        if not data.get('name'):
            url_match = re.search(r'/star/([^/]+)', response.url)
            if url_match:
                data['name'] = url_match.group(1).replace('-', ' ').replace('_', ' ')
        
        # 英文名
        name_en_selectors = [
            '.photo-info .en-name::text',
            '.english-name::text',
            '.name-en::text'
        ]
        
        for selector in name_en_selectors:
            name_en = response.css(selector).get()
            if name_en:
                data['name_en'] = name_en.strip()
                break
        
        return data
    
    def extract_personal_info(self, response):
        """提取个人资料"""
        data = {}
        
        # 获取页面文本内容进行模式匹配
        text_content = ' '.join(response.css('*::text').getall())
        
        # 生日
        birthday_patterns = [
            r'生日[：:]\s*(\d{4}-\d{2}-\d{2})',
            r'出生[：:]\s*(\d{4}-\d{2}-\d{2})',
            r'Birthday[：:]\s*(\d{4}-\d{2}-\d{2})',
            r'(\d{4}-\d{2}-\d{2})'
        ]
        
        for pattern in birthday_patterns:
            match = re.search(pattern, text_content)
            if match:
                try:
                    birth_date = datetime.strptime(match.group(1), '%Y-%m-%d').date()
                    data['birth_date'] = birth_date.isoformat()
                    break
                except ValueError:
                    continue
        
        # 身高
        height_patterns = [
            r'身高[：:]\s*(\d+)',
            r'Height[：:]\s*(\d+)',
            r'(\d{3})cm'
        ]
        
        for pattern in height_patterns:
            match = re.search(pattern, text_content)
            if match:
                height = int(match.group(1))
                if 140 <= height <= 200:  # 合理的身高范围
                    data['height'] = height
                    break
        
        # 体重
        weight_patterns = [
            r'体重[：:]\s*(\d+)',
            r'Weight[：:]\s*(\d+)',
            r'(\d{2})kg'
        ]
        
        for pattern in weight_patterns:
            match = re.search(pattern, text_content)
            if match:
                weight = int(match.group(1))
                if 35 <= weight <= 80:  # 合理的体重范围
                    data['weight'] = weight
                    break
        
        # 三围
        measurements_patterns = [
            r'三围[：:]\s*([^\\n\\r]+)',
            r'Measurements[：:]\s*([^\\n\\r]+)',
            r'B(\d+)-W(\d+)-H(\d+)'
        ]
        
        for pattern in measurements_patterns:
            match = re.search(pattern, text_content)
            if match:
                measurements = match.group(1).strip()
                if 'B' in measurements or '-' in measurements:
                    data['measurements'] = measurements
                    break
        
        # 罩杯
        cup_patterns = [
            r'罩杯[：:]\s*([A-Z]+)',
            r'Cup[：:]\s*([A-Z]+)',
            r'([A-Z])杯'
        ]
        
        for pattern in cup_patterns:
            match = re.search(pattern, text_content)
            if match:
                cup = match.group(1)
                if len(cup) <= 3:  # 合理的罩杯
                    data['cup_size'] = cup
                    break
        
        # 血型
        blood_patterns = [
            r'血型[：:]\s*([ABO]+)',
            r'Blood[：:]\s*([ABO]+)'
        ]
        
        for pattern in blood_patterns:
            match = re.search(pattern, text_content)
            if match:
                data['blood_type'] = match.group(1)
                break
        
        # 出道日期
        debut_patterns = [
            r'出道[：:]\s*(\d{4}-\d{2}-\d{2})',
            r'Debut[：:]\s*(\d{4}-\d{2}-\d{2})'
        ]
        
        for pattern in debut_patterns:
            match = re.search(pattern, text_content)
            if match:
                try:
                    debut_date = datetime.strptime(match.group(1), '%Y-%m-%d').date()
                    data['debut_date'] = debut_date.isoformat()
                    break
                except ValueError:
                    continue
        
        # 默认值
        data['nationality'] = '日本'
        data['is_active'] = True
        
        return data
    
    def extract_image_info(self, response):
        """提取图片信息"""
        data = {}
        
        # 头像图片
        profile_selectors = [
            '.avatar-box .photo-frame img::attr(src)',
            '.profile-image img::attr(src)',
            '.actress-photo img::attr(src)',
            '.star-photo img::attr(src)',
            '.avatar img::attr(src)'
        ]
        
        for selector in profile_selectors:
            img_url = response.css(selector).get()
            if img_url:
                data['profile_image'] = urljoin(response.url, img_url)
                break
        
        # 封面图片
        cover_selectors = [
            '.cover-image img::attr(src)',
            '.actress-cover img::attr(src)',
            '.banner img::attr(src)',
            '.header-image img::attr(src)'
        ]
        
        for selector in cover_selectors:
            img_url = response.css(selector).get()
            if img_url:
                data['cover_image'] = urljoin(response.url, img_url)
                break
        
        # 图片集
        gallery_selectors = [
            '.gallery img::attr(src)',
            '.photo-gallery img::attr(src)',
            '.actress-gallery img::attr(src)',
            '.sample-box img::attr(src)'
        ]
        
        gallery_urls = []
        for selector in gallery_selectors:
            imgs = response.css(selector).getall()
            for img_url in imgs:
                if img_url:
                    full_url = urljoin(response.url, img_url)
                    gallery_urls.append(full_url)
        
        if gallery_urls:
            # 去重并限制数量
            unique_gallery = list(dict.fromkeys(gallery_urls))[:10]
            data['gallery_images'] = '\\n'.join(unique_gallery)
        
        return data
    
    def extract_movie_info(self, response):
        """提取作品信息"""
        data = {}
        
        # 统计作品数量
        movie_selectors = [
            '.movie-box',
            '.video-box',
            '.work-box',
            '.item',
            '.film-item'
        ]
        
        movie_count = 0
        for selector in movie_selectors:
            movies = response.css(selector)
            if movies:
                movie_count = len(movies)
                break
        
        data['movie_count'] = movie_count
        data['popularity_score'] = min(movie_count * 3, 100)  # 基于作品数计算人气值
        
        return data
