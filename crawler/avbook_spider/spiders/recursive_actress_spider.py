"""
递归女友爬虫 - 完整爬取单个女友的所有信息和相关作品
支持从女友详情页开始，递归获取所有相关数据
"""

import scrapy
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime
import json
from ..items import ActressItem, MovieItem


class RecursiveActressSpider(scrapy.Spider):
    name = 'recursive_actress'
    allowed_domains = ['avmoo.website', 'avmoo.cyou', 'avmoo.com', 'avmoo.net']
    
    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 2,
        'AUTOTHROTTLE_MAX_DELAY': 8,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'COOKIES_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429, 403, 404],
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    def __init__(self, actress_url=None, actress_id=None, max_movies=50, *args, **kwargs):
        super(RecursiveActressSpider, self).__init__(*args, **kwargs)
        self.actress_url = actress_url
        self.actress_id = actress_id
        self.max_movies = int(max_movies) if max_movies else 50
        self.processed_movies = set()
        self.processed_actresses = set()
        
        # 如果提供了女友ID，构造URL
        if actress_id and not actress_url:
            self.actress_url = f'https://avmoo.website/cn/star/{actress_id}'
        
        self.logger.info(f'Starting recursive actress spider for: {self.actress_url}')
    
    def start_requests(self):
        """生成起始请求"""
        if not self.actress_url:
            self.logger.error('No actress URL provided')
            return
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        yield scrapy.Request(
            url=self.actress_url,
            headers=headers,
            callback=self.parse_actress_detail,
            meta={'actress_url': self.actress_url}
        )
    
    def parse_actress_detail(self, response):
        """解析女友详情页面"""
        self.logger.info(f'Parsing actress detail: {response.url}')

        # 提取女友基本信息
        actress_item = ActressItem()

        try:
            # 女友姓名 - 尝试多种选择器
            name_selectors = ['h3', '.actress-name', '.star-name', 'title']
            name = None
            for selector in name_selectors:
                name_element = response.css(f'{selector}::text').get()
                if name_element:
                    name = name_element.strip()
                    # 从标题中提取姓名（如 "JULIA - 演员 - 影片 - AVMOO"）
                    if ' - ' in name:
                        name = name.split(' - ')[0].strip()
                    break

            if name:
                actress_item['name'] = name
                self.logger.info(f'Found actress name: {name}')

            # 女友ID（从URL提取）
            actress_id_match = re.search(r'/star/([a-f0-9]+)', response.url)
            if actress_id_match:
                actress_item['actress_id'] = actress_id_match.group(1)

            # 头像图片 - 尝试多种选择器
            avatar_selectors = ['.avatar img', '.actress-photo img', '.star-photo img', 'img[alt*="头像"]', 'img[alt*="photo"]']
            for selector in avatar_selectors:
                avatar_img = response.css(f'{selector}::attr(src)').get()
                if avatar_img:
                    actress_item['profile_image'] = urljoin(response.url, avatar_img)
                    self.logger.info(f'Found avatar: {avatar_img}')
                    break
            
            # 解析女友详细信息 - 尝试多种选择器
            info_selectors = ['.info p', '.actress-info p', '.star-info p', '.profile p', 'p']
            all_text = []

            for selector in info_selectors:
                info_items = response.css(selector)
                if info_items:
                    for item in info_items:
                        text = item.css('::text').getall()
                        if text:
                            full_text = ' '.join(text).strip()
                            if full_text:
                                all_text.append(full_text)

            # 也尝试从整个页面文本中提取信息
            page_text = response.css('body::text').getall()
            all_text.extend([text.strip() for text in page_text if text.strip()])

            # 解析所有文本中的信息
            for full_text in all_text:
                # 生日
                if any(keyword in full_text for keyword in ['生日:', 'Birthday:', '出生:', 'Born:']):
                    birthday_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', full_text)
                    if birthday_match:
                        actress_item['birth_date'] = birthday_match.group(1).replace('/', '-')

                # 年龄
                elif any(keyword in full_text for keyword in ['年龄:', 'Age:', '岁']):
                    age_match = re.search(r'(\d+)', full_text)
                    if age_match:
                        actress_item['age'] = int(age_match.group(1))

                # 身高
                elif any(keyword in full_text for keyword in ['身高:', 'Height:', 'cm']):
                    height_match = re.search(r'(\d+)', full_text)
                    if height_match:
                        height = int(height_match.group(1))
                        if 140 <= height <= 200:  # 合理的身高范围
                            actress_item['height'] = height

                # 罩杯
                elif any(keyword in full_text for keyword in ['罩杯:', 'Cup:', 'Bust:']):
                    cup_match = re.search(r'([A-Z]+)', full_text)
                    if cup_match:
                        actress_item['cup_size'] = cup_match.group(1)

                # 三围
                elif any(keyword in full_text for keyword in ['三围:', 'BWH:', 'Measurements:']):
                    measurements_match = re.search(r'(\d+[-/]\d+[-/]\d+)', full_text)
                    if measurements_match:
                        actress_item['measurements'] = measurements_match.group(1).replace('/', '-')

                # 爱好
                elif any(keyword in full_text for keyword in ['爱好:', 'Hobby:', 'Hobbies:']):
                    hobby_text = re.sub(r'爱好:|Hobby:|Hobbies:', '', full_text).strip()
                    if hobby_text and len(hobby_text) < 100:  # 避免过长的文本
                        actress_item['hobby'] = hobby_text
            
            # 出道日期
            debut_info = response.css('.info').re(r'出道日期?:?\s*(\d{4}-\d{2}-\d{2})')
            if debut_info:
                actress_item['debut_date'] = debut_info[0]
            
            # 所属事务所
            agency_info = response.css('.info').re(r'事务所:?\s*([^<\n]+)')
            if agency_info:
                actress_item['agency'] = agency_info[0].strip()
            
            self.logger.info(f'Extracted actress info: {actress_item.get("name", "Unknown")}')
            
            # 发送女友数据
            yield actress_item
            
            # 获取女友的作品列表 - 尝试多种选择器
            movie_selectors = [
                '.movie-box a', '.movie-list a', '.filmography a',
                'a[href*="/movie/"]', 'a[href*="/video/"]', 'a[href*="/av/"]'
            ]

            movie_links = []
            for selector in movie_selectors:
                links = response.css(f'{selector}::attr(href)').getall()
                if links:
                    movie_links.extend(links)
                    self.logger.info(f'Found {len(links)} movie links with selector: {selector}')

            # 去重
            movie_links = list(set(movie_links))
            self.logger.info(f'Total unique movie links found: {len(movie_links)}')

            # 如果没找到作品链接，尝试从页面中查找所有可能的作品链接
            if not movie_links:
                all_links = response.css('a::attr(href)').getall()
                for link in all_links:
                    if any(pattern in link for pattern in ['/movie/', '/video/', '/av/', '/film/']):
                        movie_links.append(link)

                self.logger.info(f'Found {len(movie_links)} potential movie links from all links')

            # 递归爬取每个作品的详情
            for i, movie_link in enumerate(movie_links[:self.max_movies]):
                if movie_link not in self.processed_movies:
                    self.processed_movies.add(movie_link)
                    movie_url = urljoin(response.url, movie_link)

                    yield scrapy.Request(
                        url=movie_url,
                        callback=self.parse_movie_detail,
                        meta={
                            'actress_id': actress_item.get('actress_id'),
                            'actress_name': actress_item.get('name'),
                            'movie_index': i + 1
                        },
                        headers=self.get_headers()
                    )
        
        except Exception as e:
            self.logger.error(f'Error parsing actress detail: {e}')
    
    def parse_movie_detail(self, response):
        """解析作品详情页面"""
        self.logger.info(f'Parsing movie detail: {response.url}')
        
        try:
            movie_item = MovieItem()
            
            # 作品基本信息
            movie_item['source_url'] = response.url
            
            # 番号
            movie_id = response.css('.container h3::text').get()
            if movie_id:
                movie_item['censored_id'] = movie_id.strip()
            
            # 作品标题
            title = response.css('.container .info h3::text').get()
            if title:
                movie_item['movie_title'] = title.strip()
            
            # 作品封面
            cover_img = response.css('.screencap img::attr(src)').get()
            if cover_img:
                movie_item['cover_image'] = urljoin(response.url, cover_img)
            
            # 解析作品详细信息
            info_items = response.css('.info p')
            for item in info_items:
                text = item.css('::text').getall()
                if not text:
                    continue
                
                full_text = ' '.join(text).strip()
                
                # 发行日期
                if '发行日期:' in full_text or 'Release Date:' in full_text:
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', full_text)
                    if date_match:
                        movie_item['release_date'] = date_match.group(1)
                
                # 时长
                elif '时长:' in full_text or 'Duration:' in full_text:
                    duration_match = re.search(r'(\d+)', full_text)
                    if duration_match:
                        movie_item['duration_minutes'] = int(duration_match.group(1))
                
                # 制作商
                elif '制作商:' in full_text or 'Studio:' in full_text:
                    studio_text = re.sub(r'制作商:|Studio:', '', full_text).strip()
                    if studio_text:
                        movie_item['studio'] = studio_text
                
                # 发行商
                elif '发行商:' in full_text or 'Publisher:' in full_text:
                    publisher_text = re.sub(r'发行商:|Publisher:', '', full_text).strip()
                    if publisher_text:
                        movie_item['publisher'] = publisher_text
                
                # 系列
                elif '系列:' in full_text or 'Series:' in full_text:
                    series_text = re.sub(r'系列:|Series:', '', full_text).strip()
                    if series_text:
                        movie_item['series'] = series_text
            
            # 作品标签
            tags = response.css('.genre a::text').getall()
            if tags:
                movie_item['movie_tags'] = ', '.join([tag.strip() for tag in tags])
            
            # 参演女友
            actresses = response.css('.star a')
            actress_list = []
            for actress in actresses:
                actress_name = actress.css('::text').get()
                actress_link = actress.css('::attr(href)').get()
                if actress_name and actress_link:
                    actress_list.append({
                        'name': actress_name.strip(),
                        'url': urljoin(response.url, actress_link)
                    })
            
            if actress_list:
                movie_item['actresses'] = json.dumps(actress_list, ensure_ascii=False)
            
            # 样品图片
            sample_images = response.css('.sample-box img::attr(src)').getall()
            if sample_images:
                sample_urls = [urljoin(response.url, img) for img in sample_images]
                movie_item['sample_images'] = '\n'.join(sample_urls)
            
            self.logger.info(f'Extracted movie info: {movie_item.get("censored_id", "Unknown")}')
            
            # 发送作品数据
            yield movie_item
            
            # 递归爬取参演的其他女友（可选，避免无限递归）
            # 这里可以根据需要决定是否继续递归
            
        except Exception as e:
            self.logger.error(f'Error parsing movie detail: {e}')
    
    def get_headers(self):
        """获取请求头"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
