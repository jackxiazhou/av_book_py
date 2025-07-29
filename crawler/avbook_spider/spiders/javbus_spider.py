"""
Javbus spider for scraping movie data.
"""

import scrapy
from scrapy import Request
from urllib.parse import urljoin, urlparse
import re
from datetime import datetime
from ..items import MovieItem, MagnetItem


class JavbusSpider(scrapy.Spider):
    name = 'javbus'
    allowed_domains = ['javbus.com', 'www.javbus.com']
    start_urls = [
        'https://www.javbus.com/',
        'https://www.javbus.com/page/2',
        'https://www.javbus.com/page/3',
    ]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scraped_movies = set()
        self.scraped_urls = set()
    
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
                    'Referer': 'https://www.javbus.com/',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                }
            )
    
    def parse(self, response):
        """解析列表页面"""
        self.logger.info(f'Parsing list page: {response.url}')
        
        # 提取影片链接
        movie_links = response.css('a.movie-box::attr(href)').getall()
        
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
        next_page = response.css('a#next::attr(href)').get()
        if next_page and len(self.scraped_movies) < 100:  # 限制爬取数量
            next_url = urljoin(response.url, next_page)
            if next_url not in self.scraped_urls:
                self.scraped_urls.add(next_url)
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
        movie['source'] = 'javbus'
        movie['source_url'] = response.url
        movie['magnets'] = []
        
        yield movie
        
        # 获取磁力链接
        magnet_url = self.get_magnet_url(response.url)
        if magnet_url:
            yield Request(
                url=magnet_url,
                callback=self.parse_magnets,
                meta={
                    'movie_censored_id': censored_id,
                    'movie_url': response.url,
                    'proxy': 'http://127.0.0.1:5890',
                    'dont_cache': True,
                },
                headers={
                    'Referer': response.url,
                }
            )
    
    def extract_censored_id(self, response):
        """提取影片编号"""
        # 方法1: 从标题中提取
        title = response.css('h3::text').get()
        if title:
            match = re.search(r'([A-Z]+[-_]?\d+)', title.upper())
            if match:
                return match.group(1).replace('_', '-')
        
        # 方法2: 从URL中提取
        url_path = urlparse(response.url).path
        match = re.search(r'/([A-Z]+[-_]?\d+)', url_path.upper())
        if match:
            return match.group(1).replace('_', '-')
        
        # 方法3: 从页面其他位置提取
        code_elements = response.css('span.header::text, .info p::text').getall()
        for text in code_elements:
            if text:
                match = re.search(r'([A-Z]+[-_]?\d+)', text.upper())
                if match:
                    return match.group(1).replace('_', '-')
        
        return None
    
    def extract_title(self, response):
        """提取影片标题"""
        title = response.css('h3::text').get()
        if title:
            return title.strip()
        return ''
    
    def extract_cover_image(self, response):
        """提取封面图片"""
        img_url = response.css('a.bigImage img::attr(src)').get()
        if img_url:
            return urljoin(response.url, img_url)
        return ''
    
    def extract_release_date(self, response):
        """提取发行日期"""
        # 查找包含日期的元素
        date_text = response.css('.info p:contains("發行日期") span.header::text').get()
        if not date_text:
            # 尝试其他选择器
            date_elements = response.css('.info p span.header::text').getall()
            for text in date_elements:
                if re.match(r'\d{4}-\d{2}-\d{2}', text):
                    date_text = text
                    break
        
        if date_text:
            try:
                return datetime.strptime(date_text.strip(), '%Y-%m-%d').date()
            except ValueError:
                pass
        
        return None
    
    def extract_movie_length(self, response):
        """提取影片时长"""
        length_text = response.css('.info p:contains("長度") span.header::text').get()
        if length_text:
            return length_text.strip()
        return ''
    
    def extract_director(self, response):
        """提取导演"""
        director = response.css('.info p:contains("導演") span.header a::text').get()
        if director:
            return director.strip()
        return ''
    
    def extract_studio(self, response):
        """提取制作商"""
        studio = response.css('.info p:contains("製作商") span.header a::text').get()
        if studio:
            return studio.strip()
        return ''
    
    def extract_label(self, response):
        """提取发行商"""
        label = response.css('.info p:contains("發行商") span.header a::text').get()
        if label:
            return label.strip()
        return ''
    
    def extract_series(self, response):
        """提取系列"""
        series = response.css('.info p:contains("系列") span.header a::text').get()
        if series:
            return series.strip()
        return ''
    
    def extract_genres(self, response):
        """提取类型"""
        genres = response.css('.info p:contains("類別") span.genre a::text').getall()
        if not genres:
            # 尝试其他选择器
            genres = response.css('span.genre a::text').getall()
        if genres:
            return ', '.join([genre.strip() for genre in genres if genre.strip()])
        return ''

    def extract_idols(self, response):
        """提取演员"""
        idols = response.css('.info p:contains("演員") span.star a::text').getall()
        if not idols:
            # 尝试其他选择器
            idols = response.css('.star-name a::text').getall()
        if idols:
            return ', '.join([idol.strip() for idol in idols if idol.strip()])
        return ''
    
    def get_magnet_url(self, movie_url):
        """构造磁力链接页面URL"""
        # Javbus的磁力链接页面通常是在影片URL后加上特定路径
        if '/ajax/uncledatoolsbyajax.php' in movie_url:
            return None
        
        # 提取影片ID
        match = re.search(r'/([A-Z]+[-_]?\d+)', movie_url.upper())
        if match:
            movie_id = match.group(1)
            return f"https://www.javbus.com/ajax/uncledatoolsbyajax.php?gid={movie_id}&lang=zh"
        
        return None
    
    def parse_magnets(self, response):
        """解析磁力链接页面"""
        movie_censored_id = response.meta['movie_censored_id']
        self.logger.info(f'Parsing magnets for movie: {movie_censored_id}')
        
        # 解析磁力链接表格
        magnet_rows = response.css('tr')
        
        for row in magnet_rows:
            magnet_link = row.css('td a::attr(href)').get()
            if magnet_link and magnet_link.startswith('magnet:'):
                magnet = MagnetItem()
                magnet['movie_censored_id'] = movie_censored_id
                magnet['magnet_link'] = magnet_link
                magnet['magnet_name'] = row.css('td a::text').get() or ''
                magnet['file_size'] = row.css('td:nth-child(2)::text').get() or ''
                magnet['seeders'] = row.css('td:nth-child(3)::text').get() or '0'
                magnet['leechers'] = row.css('td:nth-child(4)::text').get() or '0'
                magnet['completed'] = row.css('td:nth-child(5)::text').get() or '0'
                magnet['publish_date'] = row.css('td:nth-child(6)::text').get()
                magnet['source'] = 'javbus'
                magnet['source_url'] = response.url

                # 解析文件大小为字节
                magnet['file_size_bytes'] = self.parse_file_size_bytes(magnet['file_size'])

                # 确定质量
                magnet['quality'] = self.determine_quality(magnet['magnet_name'])

                # 检查是否有字幕
                magnet['has_subtitle'] = self.has_subtitle(magnet['magnet_name'])

                # 提取上传者
                magnet['uploader'] = row.css('td:nth-child(7)::text').get() or ''

                # 解析发布日期
                if magnet['publish_date']:
                    magnet['publish_date'] = self.parse_publish_date(magnet['publish_date'])

                # 转换数字字段
                try:
                    magnet['seeders'] = int(magnet['seeders']) if magnet['seeders'].isdigit() else 0
                    magnet['leechers'] = int(magnet['leechers']) if magnet['leechers'].isdigit() else 0
                    magnet['completed'] = int(magnet['completed']) if magnet['completed'].isdigit() else 0
                except:
                    magnet['seeders'] = 0
                    magnet['leechers'] = 0
                    magnet['completed'] = 0

                yield magnet

    def parse_file_size_bytes(self, file_size_str):
        """将文件大小字符串转换为字节数"""
        if not file_size_str:
            return 0

        try:
            # 移除空格并转换为大写
            size_str = file_size_str.strip().upper()

            # 提取数字部分
            import re
            match = re.search(r'([\d.]+)', size_str)
            if not match:
                return 0

            size_num = float(match.group(1))

            # 确定单位
            if 'GB' in size_str:
                return int(size_num * 1024 * 1024 * 1024)
            elif 'MB' in size_str:
                return int(size_num * 1024 * 1024)
            elif 'KB' in size_str:
                return int(size_num * 1024)
            else:
                return int(size_num)
        except:
            return 0

    def determine_quality(self, magnet_name):
        """根据磁力链接名称确定视频质量"""
        if not magnet_name:
            return 'sd'

        name_upper = magnet_name.upper()

        if any(keyword in name_upper for keyword in ['4K', 'UHD', '2160P']):
            return 'uhd'
        elif any(keyword in name_upper for keyword in ['1080P', 'FHD', 'FULLHD']):
            return 'fhd'
        elif any(keyword in name_upper for keyword in ['720P', 'HD']):
            return 'hd'
        else:
            return 'sd'

    def has_subtitle(self, magnet_name):
        """检查是否有字幕"""
        if not magnet_name:
            return False

        name_upper = magnet_name.upper()
        subtitle_keywords = ['字幕', 'SUB', 'SUBTITLE', '中文', '中字', 'CHN']

        return any(keyword in name_upper for keyword in subtitle_keywords)

    def parse_publish_date(self, date_str):
        """解析发布日期"""
        if not date_str:
            return None

        try:
            # 尝试多种日期格式
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d/%m/%Y']:
                try:
                    return datetime.strptime(date_str.strip(), fmt).date()
                except ValueError:
                    continue
            return None
        except:
            return None
