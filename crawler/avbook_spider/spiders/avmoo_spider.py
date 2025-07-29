"""
Avmoo spider for scraping movie data from avmoo.website.
"""

import scrapy
from scrapy import Request
from urllib.parse import urljoin, urlparse
import re
from datetime import datetime
from ..items import MovieItem, MagnetItem


class AvmooSpider(scrapy.Spider):
    name = 'avmoo'
    allowed_domains = ['avmoo.website', 'www.avmoo.website']
    start_urls = [
        'https://avmoo.website/cn',
        'https://avmoo.website/cn/page/2',
        'https://avmoo.website/cn/page/3',
    ]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 4,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.5,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scraped_movies = set()
        self.scraped_urls = set()
        self.max_pages = int(kwargs.get('max_pages', 5))
        self.current_page = 1

    def start_requests(self):
        """生成初始请求"""
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse,
                meta={
                    'proxy': 'http://127.0.0.1:5890',
                    'dont_cache': True,
                },
                headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
    
    def parse(self, response):
        """解析列表页面"""
        self.logger.info(f'Parsing list page: {response.url}')
        
        # 提取影片链接 - Avmoo使用不同的CSS选择器
        movie_links = response.css('a.movie-box::attr(href)').getall()
        if not movie_links:
            # 尝试其他可能的选择器
            movie_links = response.css('.item a::attr(href)').getall()
        if not movie_links:
            movie_links = response.css('.movie a::attr(href)').getall()
        
        self.logger.info(f'Found {len(movie_links)} movie links on page')
        
        for link in movie_links:
            if link and link not in self.scraped_urls:
                self.scraped_urls.add(link)
                full_url = urljoin(response.url, link)
                
                yield Request(
                    url=full_url,
                    callback=self.parse_movie,
                    meta={
                        'proxy': 'http://127.0.0.1:5890',
                        'dont_cache': True,
                    },
                    headers={
                        'Referer': response.url,
                    }
                )
        
        # 处理分页
        if self.current_page < self.max_pages:
            next_page = response.css('a.next::attr(href)').get()
            if not next_page:
                # 尝试其他分页选择器
                next_page = response.css('.pagination .next::attr(href)').get()
            if not next_page:
                next_page = response.css('a[rel="next"]::attr(href)').get()
            
            if next_page:
                next_url = urljoin(response.url, next_page)
                if next_url not in self.scraped_urls:
                    self.scraped_urls.add(next_url)
                    self.current_page += 1
                    yield Request(
                        url=next_url,
                        callback=self.parse,
                        meta={
                            'proxy': 'http://127.0.0.1:5890',
                            'dont_cache': True,
                        },
                        headers={
                            'Referer': response.url,
                        }
                    )
    
    def parse_movie(self, response):
        """解析影片详情页面"""
        self.logger.info(f'Parsing movie page: {response.url}')
        
        # 提取影片编号
        censored_id = self.extract_censored_id(response)
        if not censored_id or censored_id in self.scraped_movies:
            self.logger.warning(f'Skipping duplicate or invalid movie: {censored_id}')
            return
        
        self.scraped_movies.add(censored_id)
        
        # 创建影片数据项
        movie = MovieItem()
        movie['censored_id'] = censored_id
        movie['movie_title'] = self.extract_title(response)
        movie['movie_pic_cover'] = self.extract_cover_image(response)
        movie['release_date'] = self.extract_release_date(response)
        movie['movie_length'] = self.extract_movie_length(response)
        movie['director'] = self.extract_director(response)
        movie['studio'] = self.extract_studio(response)
        movie['label'] = self.extract_label(response)
        movie['series'] = self.extract_series(response)
        movie['genre'] = self.extract_genres(response)
        movie['jav_idols'] = self.extract_idols(response)
        movie['source'] = 'avmoo'
        movie['source_url'] = response.url
        
        yield movie
        
        # 查找磁力链接页面
        magnet_url = self.extract_magnet_url(response)
        if magnet_url:
            yield Request(
                url=magnet_url,
                callback=self.parse_magnets,
                meta={
                    'movie_id': censored_id,
                    'proxy': 'http://127.0.0.1:5890',
                },
                headers={
                    'Referer': response.url,
                }
            )
    
    def extract_censored_id(self, response):
        """提取影片编号"""
        # 尝试多种方式提取编号
        patterns = [
            r'品番:\s*([A-Z0-9-]+)',
            r'識別碼:\s*([A-Z0-9-]+)',
            r'番號:\s*([A-Z0-9-]+)',
            r'品番：\s*([A-Z0-9-]+)',
        ]
        
        text = response.text
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # 从URL中提取
        url_match = re.search(r'/movie/([A-Z0-9-]+)', response.url, re.IGNORECASE)
        if url_match:
            return url_match.group(1)
        
        # 从标题中提取
        title = response.css('h3::text').get() or response.css('title::text').get() or ''
        title_match = re.search(r'([A-Z]{2,}-\d+)', title, re.IGNORECASE)
        if title_match:
            return title_match.group(1).upper()
        
        return None
    
    def extract_title(self, response):
        """提取影片标题"""
        title = response.css('h3::text').get()
        if not title:
            title = response.css('.title::text').get()
        if not title:
            title = response.css('title::text').get()
        
        return title.strip() if title else ''
    
    def extract_cover_image(self, response):
        """提取封面图片"""
        cover = response.css('.bigImage img::attr(src)').get()
        if not cover:
            cover = response.css('.cover img::attr(src)').get()
        if not cover:
            cover = response.css('img.poster::attr(src)').get()
        
        if cover:
            return urljoin(response.url, cover)
        return ''
    
    def extract_release_date(self, response):
        """提取发行日期"""
        date_text = response.css('p:contains("發行日期") span::text').get()
        if not date_text:
            date_text = response.css('p:contains("发行日期") span::text').get()
        if not date_text:
            date_text = response.css('.release-date::text').get()
        
        if date_text:
            try:
                return datetime.strptime(date_text.strip(), '%Y-%m-%d').date()
            except ValueError:
                pass
        
        return None
    
    def extract_movie_length(self, response):
        """提取影片时长"""
        length = response.css('p:contains("長度") span::text').get()
        if not length:
            length = response.css('p:contains("时长") span::text').get()
        if not length:
            length = response.css('.duration::text').get()
        
        return length.strip() if length else ''
    
    def extract_director(self, response):
        """提取导演"""
        director = response.css('p:contains("導演") a::text').get()
        if not director:
            director = response.css('p:contains("导演") a::text').get()
        if not director:
            director = response.css('.director a::text').get()
        
        return director.strip() if director else ''
    
    def extract_studio(self, response):
        """提取制作商"""
        studio = response.css('p:contains("製作商") a::text').get()
        if not studio:
            studio = response.css('p:contains("制作商") a::text').get()
        if not studio:
            studio = response.css('.studio a::text').get()
        
        return studio.strip() if studio else ''
    
    def extract_label(self, response):
        """提取发行商"""
        label = response.css('p:contains("發行商") a::text').get()
        if not label:
            label = response.css('p:contains("发行商") a::text').get()
        if not label:
            label = response.css('.label a::text').get()
        
        return label.strip() if label else ''
    
    def extract_series(self, response):
        """提取系列"""
        series = response.css('p:contains("系列") a::text').get()
        if not series:
            series = response.css('.series a::text').get()
        
        return series.strip() if series else ''
    
    def extract_genres(self, response):
        """提取类别"""
        genres = response.css('p:contains("類別") a::text').getall()
        if not genres:
            genres = response.css('p:contains("类别") a::text').getall()
        if not genres:
            genres = response.css('.genre a::text').getall()
        
        return ', '.join([g.strip() for g in genres if g.strip()])
    
    def extract_idols(self, response):
        """提取演员"""
        idols = response.css('p:contains("演員") a::text').getall()
        if not idols:
            idols = response.css('p:contains("演员") a::text').getall()
        if not idols:
            idols = response.css('.star a::text').getall()
        
        return ', '.join([i.strip() for i in idols if i.strip()])
    
    def extract_magnet_url(self, response):
        """提取磁力链接页面URL"""
        magnet_link = response.css('a:contains("磁力連結")::attr(href)').get()
        if not magnet_link:
            magnet_link = response.css('a:contains("磁力链接")::attr(href)').get()
        if not magnet_link:
            magnet_link = response.css('a[href*="magnet"]::attr(href)').get()
        
        if magnet_link:
            return urljoin(response.url, magnet_link)
        return None
    
    def parse_magnets(self, response):
        """解析磁力链接页面"""
        movie_id = response.meta['movie_id']
        self.logger.info(f'Parsing magnets for movie: {movie_id}')
        
        # 提取磁力链接
        magnet_rows = response.css('table tr')
        
        for row in magnet_rows[1:]:  # 跳过表头
            magnet_link = row.css('a[href^="magnet:"]::attr(href)').get()
            if not magnet_link:
                continue
            
            magnet = MagnetItem()
            magnet['movie_censored_id'] = movie_id
            magnet['magnet_name'] = self.extract_magnet_name(row)
            magnet['magnet_link'] = magnet_link
            magnet['file_size'] = self.extract_file_size(row)
            magnet['file_size_bytes'] = self.parse_file_size_bytes(magnet['file_size'])
            magnet['quality'] = self.extract_quality(magnet['magnet_name'])
            magnet['has_subtitle'] = self.check_subtitle(magnet['magnet_name'])
            magnet['subtitle_language'] = '中文' if magnet['has_subtitle'] else ''
            magnet['seeders'] = self.extract_seeders(row)
            magnet['leechers'] = self.extract_leechers(row)
            magnet['completed'] = self.extract_completed(row)
            magnet['publish_date'] = self.extract_publish_date(row)
            magnet['uploader'] = self.extract_uploader(row)
            magnet['source'] = 'avmoo'
            
            yield magnet
    
    def extract_magnet_name(self, row):
        """提取磁力链接名称"""
        name = row.css('a[href^="magnet:"]::text').get()
        if not name:
            name = row.css('td:first-child::text').get()
        return name.strip() if name else ''
    
    def extract_file_size(self, row):
        """提取文件大小"""
        size_cell = row.css('td:nth-child(2)::text').get()
        if not size_cell:
            size_cell = row.css('.size::text').get()
        return size_cell.strip() if size_cell else ''
    
    def parse_file_size_bytes(self, size_str):
        """解析文件大小为字节"""
        if not size_str:
            return 0
        
        size_str = size_str.upper()
        multipliers = {'GB': 1024**3, 'MB': 1024**2, 'KB': 1024, 'TB': 1024**4}
        
        for unit, multiplier in multipliers.items():
            if unit in size_str:
                try:
                    number = float(re.search(r'([\d.]+)', size_str).group(1))
                    return int(number * multiplier)
                except (AttributeError, ValueError):
                    pass
        
        return 0
    
    def extract_quality(self, name):
        """从名称中提取质量"""
        name_upper = name.upper()
        if any(q in name_upper for q in ['4K', 'UHD', '2160P']):
            return 'uhd'
        elif any(q in name_upper for q in ['1080P', 'FHD']):
            return 'fhd'
        elif any(q in name_upper for q in ['720P', 'HD']):
            return 'hd'
        else:
            return 'sd'
    
    def check_subtitle(self, name):
        """检查是否有字幕"""
        subtitle_keywords = ['字幕', '中字', 'SUB', 'SUBTITLE', '中文']
        return any(keyword in name.upper() for keyword in subtitle_keywords)
    
    def extract_seeders(self, row):
        """提取做种数"""
        seeders = row.css('td:nth-child(3)::text').get()
        if seeders and seeders.isdigit():
            return int(seeders)
        return 0
    
    def extract_leechers(self, row):
        """提取下载数"""
        leechers = row.css('td:nth-child(4)::text').get()
        if leechers and leechers.isdigit():
            return int(leechers)
        return 0
    
    def extract_completed(self, row):
        """提取完成数"""
        completed = row.css('td:nth-child(5)::text').get()
        if completed and completed.isdigit():
            return int(completed)
        return 0
    
    def extract_publish_date(self, row):
        """提取发布日期"""
        date_text = row.css('td:nth-child(6)::text').get()
        if date_text:
            try:
                return datetime.strptime(date_text.strip(), '%Y-%m-%d').date()
            except ValueError:
                pass
        return None
    
    def extract_uploader(self, row):
        """提取上传者"""
        uploader = row.css('td:nth-child(7)::text').get()
        return uploader.strip() if uploader else 'Anonymous'