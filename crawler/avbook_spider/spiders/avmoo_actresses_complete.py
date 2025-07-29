"""
AVMoo完整女友爬虫 - 重新梳理的女友功能
爬取女友列表、详情、作品关联和作品详情
"""

import scrapy
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime
import json
import time


class AvmooActressesCompleteSpider(scrapy.Spider):
    name = 'avmoo_actresses_complete'
    allowed_domains = ['avmoo.website', 'avmoo.cyou', 'avmoo.com']
    
    # 女友列表页面
    start_urls = [
        'https://avmoo.website/cn/actresses',
    ]
    
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
    
    def __init__(self, max_pages=5, max_actresses=50, *args, **kwargs):
        super(AvmooActressesCompleteSpider, self).__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        self.max_actresses = int(max_actresses)
        self.actresses_count = 0
        self.movies_count = 0
        self.processed_actress_urls = set()
        self.processed_movie_urls = set()
        
        self.logger.info(f'Starting AVMoo complete actresses spider')
        self.logger.info(f'Max pages: {self.max_pages}, Max actresses: {self.max_actresses}')
    
    def start_requests(self):
        """生成起始请求"""
        headers = {
            'User-Agent': self.custom_settings['USER_AGENT'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_actresses_list,
                headers=headers,
                meta={'page': 1}
            )
    
    def parse_actresses_list(self, response):
        """解析女友列表页面"""
        page = response.meta.get('page', 1)
        self.logger.info(f'Parsing actresses list page {page}: {response.url}')
        
        # 多种选择器尝试找到女友链接
        actress_selectors = [
            '.star-box a::attr(href)',
            '.actress-box a::attr(href)', 
            '.avatar a::attr(href)',
            'a[href*="/star/"]::attr(href)',
            'a[href*="/actress/"]::attr(href)',
            '.star-name a::attr(href)',
            '.photo-frame a::attr(href)',
            '.item a::attr(href)',
            '.grid-item a::attr(href)'
        ]
        
        actress_urls = []
        for selector in actress_selectors:
            urls = response.css(selector).getall()
            if urls:
                self.logger.info(f'Found {len(urls)} actress URLs with selector: {selector}')
                actress_urls.extend(urls)
                break
        
        # 如果没有找到，尝试xpath
        if not actress_urls:
            xpath_selectors = [
                '//a[contains(@href, "/star/")]/@href',
                '//a[contains(@href, "/actress/")]/@href',
                '//div[@class="star-box"]//a/@href',
                '//div[@class="actress-box"]//a/@href'
            ]
            for xpath in xpath_selectors:
                urls = response.xpath(xpath).getall()
                if urls:
                    self.logger.info(f'Found {len(urls)} actress URLs with xpath: {xpath}')
                    actress_urls.extend(urls)
                    break
        
        # 去重并转换为绝对URL
        unique_urls = []
        for url in actress_urls:
            if url and url not in self.processed_actress_urls:
                full_url = urljoin(response.url, url)
                if '/star/' in full_url or '/actress/' in full_url:
                    unique_urls.append(full_url)
                    self.processed_actress_urls.add(url)
        
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
        
        # 处理下一页
        if page < self.max_pages:
            next_page_selectors = [
                '.pagination .next::attr(href)',
                '.page-next::attr(href)',
                'a[rel="next"]::attr(href)',
                '.pagination a:contains("下一页")::attr(href)',
                '.pagination a:contains("Next")::attr(href)'
            ]
            
            next_page_url = None
            for selector in next_page_selectors:
                next_url = response.css(selector).get()
                if next_url:
                    next_page_url = urljoin(response.url, next_url)
                    break
            
            # 如果没有找到下一页链接，尝试构造
            if not next_page_url:
                base_url = response.url.split('?')[0]
                next_page_url = f"{base_url}?page={page + 1}"
            
            if next_page_url:
                self.logger.info(f'Following next page: {next_page_url}')
                yield scrapy.Request(
                    url=next_page_url,
                    callback=self.parse_actresses_list,
                    meta={'page': page + 1},
                    headers=response.request.headers
                )
    
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
            
            # 添加爬取信息
            actress_data['source_url'] = response.url
            actress_data['crawled_at'] = datetime.now().isoformat()
            actress_data['data_type'] = 'actress'
            
            if actress_data.get('name'):
                yield actress_data
                
                # 爬取女友的作品列表
                yield from self.crawl_actress_movies(response, actress_data)
            else:
                self.logger.warning(f'No name found for actress at {response.url}')
                
        except Exception as e:
            self.logger.error(f'Error parsing actress detail {response.url}: {e}')
    
    def crawl_actress_movies(self, response, actress_data):
        """爬取女友的作品列表"""
        self.logger.info(f'Crawling movies for actress: {actress_data.get("name")}')
        
        # 在详情页查找作品链接
        movie_selectors = [
            '.movie-box a::attr(href)',
            '.item a::attr(href)',
            'a[href*="/movie/"]::attr(href)',
            '.video-item a::attr(href)',
            '.grid-item a::attr(href)'
        ]
        
        movie_urls = []
        for selector in movie_selectors:
            urls = response.css(selector).getall()
            if urls:
                self.logger.info(f'Found {len(urls)} movie URLs with selector: {selector}')
                movie_urls.extend(urls)
                break
        
        # 如果没有找到，尝试xpath
        if not movie_urls:
            xpath_selectors = [
                '//a[contains(@href, "/movie/")]/@href',
                '//div[@class="movie-box"]//a/@href',
                '//div[@class="item"]//a/@href'
            ]
            for xpath in xpath_selectors:
                urls = response.xpath(xpath).getall()
                if urls:
                    self.logger.info(f'Found {len(urls)} movie URLs with xpath: {xpath}')
                    movie_urls.extend(urls)
                    break
        
        # 处理找到的作品链接
        for movie_url in movie_urls:
            if movie_url and movie_url not in self.processed_movie_urls:
                full_movie_url = urljoin(response.url, movie_url)
                if '/movie/' in full_movie_url:
                    self.processed_movie_urls.add(movie_url)
                    
                    yield scrapy.Request(
                        url=full_movie_url,
                        callback=self.parse_movie_detail,
                        meta={
                            'actress_name': actress_data.get('name'),
                            'actress_url': response.url
                        },
                        headers=response.request.headers
                    )
        
        # 处理分页 - 女友详情页的作品分页
        pagination_selectors = [
            '.pagination .next::attr(href)',
            '.page-next::attr(href)',
            'a[rel="next"]::attr(href)'
        ]
        
        for selector in pagination_selectors:
            next_url = response.css(selector).get()
            if next_url:
                next_page_url = urljoin(response.url, next_url)
                self.logger.info(f'Following actress movies next page: {next_page_url}')
                
                yield scrapy.Request(
                    url=next_page_url,
                    callback=self.parse_actress_movies_page,
                    meta={
                        'actress_name': actress_data.get('name'),
                        'actress_url': actress_data.get('source_url')
                    },
                    headers=response.request.headers
                )
                break
    
    def parse_actress_movies_page(self, response):
        """解析女友作品的分页"""
        actress_name = response.meta.get('actress_name')
        self.logger.info(f'Parsing movies page for actress {actress_name}: {response.url}')
        
        # 提取作品链接
        movie_selectors = [
            '.movie-box a::attr(href)',
            '.item a::attr(href)',
            'a[href*="/movie/"]::attr(href)'
        ]
        
        movie_urls = []
        for selector in movie_selectors:
            urls = response.css(selector).getall()
            if urls:
                movie_urls.extend(urls)
                break
        
        # 处理作品链接
        for movie_url in movie_urls:
            if movie_url and movie_url not in self.processed_movie_urls:
                full_movie_url = urljoin(response.url, movie_url)
                if '/movie/' in full_movie_url:
                    self.processed_movie_urls.add(movie_url)
                    
                    yield scrapy.Request(
                        url=full_movie_url,
                        callback=self.parse_movie_detail,
                        meta={
                            'actress_name': actress_name,
                            'actress_url': response.meta.get('actress_url')
                        },
                        headers=response.request.headers
                    )
        
        # 继续下一页
        next_url = response.css('.pagination .next::attr(href)').get()
        if next_url:
            next_page_url = urljoin(response.url, next_url)
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse_actress_movies_page,
                meta=response.meta,
                headers=response.request.headers
            )
    
    def parse_movie_detail(self, response):
        """解析作品详情页面"""
        self.movies_count += 1
        actress_name = response.meta.get('actress_name')
        self.logger.info(f'Parsing movie detail for actress {actress_name} ({self.movies_count}): {response.url}')
        
        try:
            movie_data = {}
            
            # 基本信息提取
            movie_data.update(self.extract_movie_basic_info(response))
            
            # 演员信息提取
            movie_data.update(self.extract_movie_actresses_info(response))
            
            # 样例图片提取
            movie_data.update(self.extract_movie_images(response))
            
            # 磁力链接提取
            movie_data.update(self.extract_movie_magnets(response))
            
            # 添加关联信息
            movie_data['related_actress'] = actress_name
            movie_data['actress_url'] = response.meta.get('actress_url')
            movie_data['source_url'] = response.url
            movie_data['crawled_at'] = datetime.now().isoformat()
            movie_data['data_type'] = 'movie'
            
            if movie_data.get('censored_id') or movie_data.get('movie_title'):
                yield movie_data
            else:
                self.logger.warning(f'No valid movie data found at {response.url}')
                
        except Exception as e:
            self.logger.error(f'Error parsing movie detail {response.url}: {e}')

    def extract_basic_info(self, response):
        """提取女友基本信息"""
        data = {}

        # 姓名提取
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
                data['name'] = name.strip()
                break

        # 英文名提取
        name_en_selectors = [
            '.star-name-en::text',
            '.actress-name-en::text',
            '.name-en::text'
        ]

        for selector in name_en_selectors:
            name_en = response.css(selector).get()
            if name_en:
                data['name_en'] = name_en.strip()
                break

        return data

    def extract_personal_info(self, response):
        """提取女友个人资料"""
        data = {}

        # 查找个人资料区域
        info_selectors = [
            '.star-info',
            '.actress-info',
            '.personal-info',
            '.profile-info',
            '.info'
        ]

        info_section = None
        for selector in info_selectors:
            section = response.css(selector)
            if section:
                info_section = section
                break

        if info_section:
            # 提取各种个人信息
            info_text = info_section.get()

            # 身高
            height_match = re.search(r'身高[：:]\s*(\d+)\s*cm', info_text, re.IGNORECASE)
            if height_match:
                data['height'] = int(height_match.group(1))

            # 三围
            measurements_match = re.search(r'三围[：:]\s*([B-Z]\d+[-–]\w\d+[-–]\w\d+)', info_text, re.IGNORECASE)
            if measurements_match:
                data['measurements'] = measurements_match.group(1)

            # 罩杯
            cup_match = re.search(r'罩杯[：:]\s*([A-Z]+)', info_text, re.IGNORECASE)
            if cup_match:
                data['cup_size'] = cup_match.group(1)

            # 出生日期
            birth_match = re.search(r'出生[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})', info_text)
            if birth_match:
                data['birth_date'] = birth_match.group(1)

            # 出道日期
            debut_match = re.search(r'出道[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})', info_text)
            if debut_match:
                data['debut_date'] = debut_match.group(1)

        return data

    def extract_image_info(self, response):
        """提取女友图片信息"""
        data = {}

        # 头像/个人照片
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
                data['profile_image'] = urljoin(response.url, profile_img)
                break

        # 封面图片
        cover_selectors = [
            '.star-cover img::attr(src)',
            '.actress-cover img::attr(src)',
            '.cover-image img::attr(src)',
            '.banner img::attr(src)'
        ]

        for selector in cover_selectors:
            cover_img = response.css(selector).get()
            if cover_img:
                data['cover_image'] = urljoin(response.url, cover_img)
                break

        # 图片集
        gallery_selectors = [
            '.gallery img::attr(src)',
            '.photos img::attr(src)',
            '.image-gallery img::attr(src)'
        ]

        gallery_images = []
        for selector in gallery_selectors:
            images = response.css(selector).getall()
            if images:
                gallery_images.extend([urljoin(response.url, img) for img in images])

        if gallery_images:
            data['gallery_images'] = '\n'.join(gallery_images)

        return data

    def extract_movie_basic_info(self, response):
        """提取作品基本信息"""
        data = {}

        # 作品编号
        id_selectors = [
            '.movie-id::text',
            '.code::text',
            '.number::text',
            'span:contains("番号")::text',
            '.title::text'
        ]

        for selector in id_selectors:
            movie_id = response.css(selector).get()
            if movie_id and re.match(r'^[A-Z0-9]+-\d+', movie_id.strip()):
                data['censored_id'] = movie_id.strip()
                break

        # 如果没有找到，尝试从URL提取
        if not data.get('censored_id'):
            url_match = re.search(r'/movie/([a-f0-9]+)', response.url)
            if url_match:
                data['movie_hash'] = url_match.group(1)

        # 作品标题
        title_selectors = [
            '.movie-title::text',
            '.title::text',
            'h1::text',
            '.name::text'
        ]

        for selector in title_selectors:
            title = response.css(selector).get()
            if title:
                data['movie_title'] = title.strip()
                break

        # 发行日期
        date_selectors = [
            '.release-date::text',
            '.date::text',
            'span:contains("发行")::text'
        ]

        for selector in date_selectors:
            date_text = response.css(selector).get()
            if date_text:
                date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', date_text)
                if date_match:
                    data['release_date'] = date_match.group(1)
                    break

        # 制作商
        studio_selectors = [
            '.studio::text',
            '.maker::text',
            'span:contains("制作")::text'
        ]

        for selector in studio_selectors:
            studio = response.css(selector).get()
            if studio:
                data['studio'] = studio.strip()
                break

        return data

    def extract_movie_actresses_info(self, response):
        """提取作品演员信息"""
        data = {}

        # 演员列表
        actress_selectors = [
            '.star-name::text',
            '.actress-name::text',
            '.performers .name::text',
            '.cast .name::text'
        ]

        actresses = []
        for selector in actress_selectors:
            names = response.css(selector).getall()
            if names:
                actresses.extend([name.strip() for name in names if name.strip()])

        if actresses:
            data['jav_idols'] = ', '.join(actresses)

        return data

    def extract_movie_images(self, response):
        """提取作品样例图片"""
        data = {}

        # 封面图片
        cover_selectors = [
            '.movie-cover img::attr(src)',
            '.cover img::attr(src)',
            '.poster img::attr(src)',
            '.thumbnail img::attr(src)'
        ]

        for selector in cover_selectors:
            cover = response.css(selector).get()
            if cover:
                data['movie_pic_cover'] = urljoin(response.url, cover)
                break

        # 样例图片
        sample_selectors = [
            '.sample-images img::attr(src)',
            '.screenshots img::attr(src)',
            '.preview img::attr(src)',
            '.samples img::attr(src)'
        ]

        sample_images = []
        for selector in sample_selectors:
            images = response.css(selector).getall()
            if images:
                sample_images.extend([urljoin(response.url, img) for img in images])

        if sample_images:
            data['sample_images'] = '\n'.join(sample_images)

        return data

    def extract_movie_magnets(self, response):
        """提取作品磁力链接"""
        data = {}

        # 磁力链接
        magnet_selectors = [
            'a[href^="magnet:"]::attr(href)',
            '.magnet-link::attr(href)',
            '.download-link::attr(href)'
        ]

        magnets = []
        for selector in magnet_selectors:
            links = response.css(selector).getall()
            if links:
                magnets.extend(links)

        if magnets:
            data['magnet_links'] = magnets

        return data
