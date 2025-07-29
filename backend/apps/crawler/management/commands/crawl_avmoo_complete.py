"""
完整的AVMoo爬虫系统
1. 爬取女友列表页 https://avmoo.website/cn/actresses
2. 爬取女友详情页 https://avmoo.website/cn/star/xxx
3. 爬取女友的所有作品并建立关联
4. 爬取作品详情页和样例图片
"""

import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.movies.models import Movie, MovieRating
from apps.actresses.models import Actress, ActressTag
from apps.crawler.models import CrawlerSession, CrawlerLog
from apps.crawler.utils.image_downloader import ImageDownloader
import random
from datetime import datetime


class AVMooCompleteCrawler:
    def __init__(self, proxy_url=None, download_images=True):
        self.session = requests.Session()
        self.proxy_url = proxy_url
        self.download_images = download_images
        
        if proxy_url:
            self.session.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://avmoo.website/',
        })
        
        # 初始化图片下载器
        if self.download_images:
            self.image_downloader = ImageDownloader(proxy_url=proxy_url)
        
        self.base_url = 'https://avmoo.website'
        self.actresses_processed = 0
        self.movies_processed = 0
        self.request_count = 0

        # 待爬取女友队列
        self.pending_actresses = set()
        self.processed_actress_urls = set()
        
        # 统计信息
        self.stats = {
            'actresses_created': 0,
            'actresses_updated': 0,
            'movies_created': 0,
            'movies_updated': 0,
            'relationships_created': 0,
            'images_downloaded': 0
        }
    
    def get_page(self, url, timeout=30, max_retries=3):
        """获取页面内容"""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = random.uniform(3, 8)
                    print(f"Retry {attempt}, waiting {delay:.1f}s...")
                    time.sleep(delay)
                
                print(f"Requesting: {url}")
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                response.encoding = 'utf-8'
                
                self.request_count += 1
                
                # 添加请求间隔
                time.sleep(random.uniform(2, 5))
                
                return response
                
            except Exception as e:
                print(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return None
        
        return None
    
    def crawl_actresses_list(self, max_pages=10):
        """爬取女友列表页面"""
        print("=== 开始爬取女友列表 ===")
        
        actress_urls = []
        
        for page in range(1, max_pages + 1):
            if page == 1:
                list_url = f"{self.base_url}/cn/actresses"
            else:
                list_url = f"{self.base_url}/cn/actresses?page={page}"
            
            print(f"爬取女友列表页面 {page}: {list_url}")
            response = self.get_page(list_url)
            
            if not response:
                print(f"无法获取页面 {page}")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找女友链接
            page_actress_urls = self.extract_actress_urls(soup, list_url)
            
            if not page_actress_urls:
                print(f"页面 {page} 没有找到女友链接，可能已到最后一页")
                break
            
            actress_urls.extend(page_actress_urls)
            print(f"页面 {page} 找到 {len(page_actress_urls)} 个女友链接")
        
        print(f"总共找到 {len(actress_urls)} 个女友链接")
        return actress_urls
    
    def extract_actress_urls(self, soup, base_url):
        """从页面中提取女友链接"""
        actress_urls = []
        
        # 多种选择器尝试
        selectors = [
            'a[href*="/star/"]',
            '.actress-box a',
            '.star-box a',
            '.avatar a',
            '.photo-frame a'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            if links:
                for link in links:
                    href = link.get('href')
                    if href and '/star/' in href:
                        full_url = urljoin(base_url, href)
                        actress_urls.append(full_url)
                break
        
        return list(set(actress_urls))  # 去重
    
    def crawl_actress_detail(self, actress_url):
        """爬取女友详情页面"""
        print(f"爬取女友详情: {actress_url}")

        response = self.get_page(actress_url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # 提取女友基本信息
        actress_data = self.extract_actress_info(soup, actress_url)

        if not actress_data.get('name'):
            print(f"无法提取女友姓名: {actress_url}")
            return None

        # 保存女友信息
        actress = self.save_actress(actress_data)

        if actress:
            # 检查是否已经爬取过作品
            if actress.movies_crawled:
                print(f"女友 {actress.name} 已爬取过作品，跳过")
                return actress

            # 爬取女友的所有作品
            movie_urls = self.crawl_actress_movies(actress_url, actress)
            print(f"女友 {actress.name} 找到 {len(movie_urls)} 部作品")

            # 标记为已爬取
            actress.movies_crawled = True
            actress.crawl_date = timezone.now()
            actress.save()
            print(f"女友 {actress.name} 作品爬取完成")

        return actress
    
    def extract_actress_info(self, soup, url):
        """提取女友信息"""
        data = {}
        
        # 姓名提取
        name_selectors = [
            '.avatar-box .photo-info span',
            '.star-name',
            'h1',
            '.title'
        ]
        
        for selector in name_selectors:
            elem = soup.select_one(selector)
            if elem:
                name = elem.get_text().strip()
                if name and len(name) > 1:
                    data['name'] = name
                    break
        
        # 从URL提取姓名作为备选
        if not data.get('name'):
            url_match = re.search(r'/star/([^/]+)', url)
            if url_match:
                data['name'] = url_match.group(1).replace('-', ' ')
        
        # 提取个人信息
        text_content = soup.get_text()
        
        # 生日
        birthday_match = re.search(r'生日[：:]\s*(\d{4}-\d{2}-\d{2})', text_content)
        if birthday_match:
            try:
                data['birth_date'] = datetime.strptime(birthday_match.group(1), '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # 身高
        height_match = re.search(r'身高[：:]\s*(\d+)', text_content)
        if height_match:
            data['height'] = int(height_match.group(1))
        
        # 体重
        weight_match = re.search(r'体重[：:]\s*(\d+)', text_content)
        if weight_match:
            data['weight'] = int(weight_match.group(1))
        
        # 三围
        measurements_match = re.search(r'三围[：:]\s*([^\\n]+)', text_content)
        if measurements_match:
            data['measurements'] = measurements_match.group(1).strip()
        
        # 罩杯
        cup_match = re.search(r'罩杯[：:]\s*([A-Z]+)', text_content)
        if cup_match:
            data['cup_size'] = cup_match.group(1)
        
        # 血型
        blood_match = re.search(r'血型[：:]\s*([ABO]+)', text_content)
        if blood_match:
            data['blood_type'] = blood_match.group(1)
        
        # 出道日期
        debut_match = re.search(r'出道[：:]\s*(\d{4}-\d{2}-\d{2})', text_content)
        if debut_match:
            try:
                data['debut_date'] = datetime.strptime(debut_match.group(1), '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # 提取图片
        if self.download_images:
            data.update(self.extract_actress_images(soup, url, data.get('name', 'unknown')))
        
        # 默认值
        data['nationality'] = '日本'
        data['is_active'] = True
        data['source_url'] = url
        data['movies_crawled'] = False  # 标记是否已爬取过作品

        return data
    
    def extract_actress_images(self, soup, url, actress_name):
        """提取女友图片"""
        data = {}
        
        # 头像
        profile_selectors = [
            '.avatar-box .photo-frame img',
            '.profile-image img',
            '.star-photo img'
        ]
        
        for selector in profile_selectors:
            img = soup.select_one(selector)
            if img:
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    img_url = urljoin(url, img_url)
                    local_path = self.image_downloader.download_image(
                        img_url, 
                        'actress_profile',
                        f"{actress_name}_profile"
                    )
                    if local_path:
                        data['profile_image'] = self.image_downloader.get_image_url(local_path)
                        self.stats['images_downloaded'] += 1
                    break
        
        # 封面图片
        cover_selectors = [
            '.cover-image img',
            '.banner img',
            '.header-image img'
        ]
        
        for selector in cover_selectors:
            img = soup.select_one(selector)
            if img:
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    img_url = urljoin(url, img_url)
                    local_path = self.image_downloader.download_image(
                        img_url,
                        'actress_cover', 
                        f"{actress_name}_cover"
                    )
                    if local_path:
                        data['cover_image'] = self.image_downloader.get_image_url(local_path)
                        self.stats['images_downloaded'] += 1
                    break
        
        return data
    
    def crawl_actress_movies(self, actress_url, actress):
        """爬取女友的所有作品"""
        movie_urls = []
        page = 1
        
        while True:
            if page == 1:
                page_url = actress_url
            else:
                page_url = f"{actress_url}?page={page}"
            
            print(f"爬取女友作品页面 {page}: {page_url}")
            response = self.get_page(page_url)
            
            if not response:
                break
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取作品链接
            page_movie_urls = self.extract_movie_urls(soup, page_url)
            
            if not page_movie_urls:
                print(f"女友作品页面 {page} 没有找到作品，结束爬取")
                break
            
            movie_urls.extend(page_movie_urls)
            print(f"女友作品页面 {page} 找到 {len(page_movie_urls)} 部作品")
            
            # 处理每部作品
            for movie_url in page_movie_urls:
                self.crawl_movie_detail(movie_url, actress)
            
            page += 1
            
            # 限制最大页数
            if page > 20:
                break
        
        return movie_urls
    
    def extract_movie_urls(self, soup, base_url):
        """从页面中提取作品链接"""
        movie_urls = []
        
        selectors = [
            'a[href*="/movie/"]',
            '.movie-box a',
            '.item a',
            '.video-box a'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            if links:
                for link in links:
                    href = link.get('href')
                    if href and '/movie/' in href:
                        full_url = urljoin(base_url, href)
                        movie_urls.append(full_url)
                break
        
        return list(set(movie_urls))  # 去重

    def crawl_movie_detail(self, movie_url, primary_actress=None):
        """爬取作品详情页面"""
        print(f"爬取作品详情: {movie_url}")

        response = self.get_page(movie_url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # 提取作品信息
        movie_data = self.extract_movie_info(soup, movie_url)

        if not movie_data.get('censored_id'):
            print(f"无法提取作品编号: {movie_url}")
            return None

        # 保存作品信息
        movie = self.save_movie(movie_data)

        if movie:
            # 处理作品中的所有女友
            actresses_in_movie = self.process_movie_actresses(soup, movie_url, movie)

            # 如果有主要女友，确保建立关联
            if primary_actress:
                if not movie.actresses.filter(id=primary_actress.id).exists():
                    movie.actresses.add(primary_actress)
                    self.stats['relationships_created'] += 1
                    print(f"建立主要关联: {primary_actress.name} <-> {movie.censored_id}")

            print(f"作品 {movie.censored_id} 关联了 {len(actresses_in_movie)} 位女友")

        return movie

    def process_movie_actresses(self, soup, movie_url, movie):
        """处理作品中的所有女友"""
        actresses_processed = []

        # 提取作品中的所有演员
        idol_elems = soup.select('p:contains("演員") a, .star a, a[href*="/star/"]')

        for idol_elem in idol_elems:
            actress_name = idol_elem.get_text().strip()
            actress_url = idol_elem.get('href')

            if not actress_name or not actress_url:
                continue

            # 转换为绝对URL
            actress_url = urljoin(movie_url, actress_url)

            print(f"  处理作品中的女友: {actress_name}")

            # 检查女友是否已存在
            actress = Actress.objects.filter(name=actress_name).first()

            if not actress:
                # 创建新女友（基本信息）
                actress_data = {
                    'name': actress_name,
                    'nationality': '日本',
                    'is_active': True,
                    'source_url': actress_url,
                    'movies_crawled': False,
                    'description': f'从作品 {movie.censored_id} 中发现的女友'
                }
                actress = self.save_actress(actress_data)
                print(f"    创建新女友: {actress_name}")

            if actress:
                # 建立关联
                if not movie.actresses.filter(id=actress.id).exists():
                    movie.actresses.add(actress)
                    self.stats['relationships_created'] += 1
                    print(f"    建立关联: {actress_name} <-> {movie.censored_id}")

                actresses_processed.append(actress)

                # 检查是否需要爬取女友详情
                if not actress.movies_crawled and actress.source_url:
                    print(f"    女友 {actress_name} 未爬取过，加入待爬取队列")
                    # 这里可以添加到队列中，稍后处理
                    self.pending_actresses.add(actress_url)

        return actresses_processed

    def extract_movie_info(self, soup, url):
        """提取作品信息"""
        data = {}

        # 提取作品编号
        censored_id = self.extract_censored_id(soup, url)
        if not censored_id:
            return data

        data['censored_id'] = censored_id
        data['source'] = 'avmoo_complete'
        data['source_url'] = url

        # 标题
        title_selectors = ['h3', '.title', 'title']
        for selector in title_selectors:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text().strip()
                if title and censored_id not in title:
                    data['movie_title'] = title
                    break

        # 封面图片
        cover_selectors = ['.bigImage img', '.cover img', '.poster img']
        for selector in cover_selectors:
            img = soup.select_one(selector)
            if img:
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    data['movie_pic_cover'] = urljoin(url, img_url)
                    break

        # 发行日期
        text_content = soup.get_text()
        date_match = re.search(r'發行日期[：:]\s*(\d{4}-\d{2}-\d{2})', text_content)
        if date_match:
            try:
                data['release_date'] = datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
            except ValueError:
                pass

        # 时长
        length_match = re.search(r'長度[：:]\s*([^<\\n]+)', text_content)
        if length_match:
            data['movie_length'] = length_match.group(1).strip()

        # 导演
        director_elem = soup.select_one('p:contains("導演") a, .director a')
        if director_elem:
            data['director'] = director_elem.get_text().strip()

        # 制作商
        studio_elem = soup.select_one('p:contains("製作商") a, .studio a')
        if studio_elem:
            data['studio'] = studio_elem.get_text().strip()

        # 发行商
        label_elem = soup.select_one('p:contains("發行商") a, .label a')
        if label_elem:
            data['label'] = label_elem.get_text().strip()

        # 系列
        series_elem = soup.select_one('p:contains("系列") a, .series a')
        if series_elem:
            data['series'] = series_elem.get_text().strip()

        # 类别
        genre_elems = soup.select('p:contains("類別") a, .genre a')
        if genre_elems:
            genres = [elem.get_text().strip() for elem in genre_elems]
            data['genre'] = ', '.join(genres)

        # 演员
        idol_elems = soup.select('p:contains("演員") a, .star a, a[href*="/star/"]')
        if idol_elems:
            idols = [elem.get_text().strip() for elem in idol_elems if elem.get_text().strip()]
            data['jav_idols'] = ', '.join(idols)

        # 样例图片
        if self.download_images:
            data['sample_images'] = self.extract_sample_images(soup, url, censored_id)

        # 影片标记
        tag_elems = soup.select('.genre a, .tag a, .label a')
        if tag_elems:
            tags = [elem.get_text().strip() for elem in tag_elems]
            data['movie_tags'] = ', '.join(list(set(tags)))

        return data

    def extract_censored_id(self, soup, url):
        """提取作品编号"""
        # 从URL中提取
        url_match = re.search(r'/movie/([^/]+)', url)
        if url_match:
            return url_match.group(1).upper()

        # 从页面内容中提取
        patterns = [
            r'識別碼[：:]\s*([A-Z0-9-]+)',
            r'品番[：:]\s*([A-Z0-9-]+)',
            r'番號[：:]\s*([A-Z0-9-]+)',
        ]

        text = soup.get_text()
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip().upper()

        return None

    def extract_sample_images(self, soup, url, movie_id):
        """提取样例图片"""
        sample_urls = []

        # 查找样例图片
        sample_selectors = [
            '.sample-box img',
            '.preview-images img',
            '.sample-waterfall img',
            'a[href*="sample"] img'
        ]

        for selector in sample_selectors:
            imgs = soup.select(selector)
            for img in imgs:
                src = img.get('src') or img.get('data-src')
                if src:
                    full_url = urljoin(url, src)

                    # 下载样例图片
                    local_path = self.image_downloader.download_image(
                        full_url,
                        'movie_sample',
                        f"{movie_id}_sample_{len(sample_urls)+1}"
                    )
                    if local_path:
                        sample_urls.append(self.image_downloader.get_image_url(local_path))
                        self.stats['images_downloaded'] += 1
                    else:
                        sample_urls.append(full_url)  # 保留原URL作为备选

        return '\\n'.join(sample_urls[:10])  # 最多10张样例图片

    def save_actress(self, actress_data):
        """保存女友到数据库"""
        try:
            actress, created = Actress.objects.get_or_create(
                name=actress_data['name'],
                defaults=actress_data
            )

            if created:
                self.stats['actresses_created'] += 1
                print(f"创建女友: {actress.name}")

                # 添加标签
                self.add_actress_tags(actress)
            else:
                # 更新现有女友信息
                updated = False
                for field, value in actress_data.items():
                    if field != 'name' and value and not getattr(actress, field):
                        setattr(actress, field, value)
                        updated = True

                if updated:
                    actress.save()
                    self.stats['actresses_updated'] += 1
                    print(f"更新女友: {actress.name}")

            return actress

        except Exception as e:
            print(f"保存女友失败 {actress_data.get('name', 'unknown')}: {e}")
            return None

    def save_movie(self, movie_data):
        """保存作品到数据库"""
        try:
            movie, created = Movie.objects.get_or_create(
                censored_id=movie_data['censored_id'],
                defaults=movie_data
            )

            if created:
                self.stats['movies_created'] += 1
                print(f"创建作品: {movie.censored_id}")
                # 创建对应的评分记录
                MovieRating.objects.get_or_create(movie=movie)
            else:
                # 更新现有作品信息
                updated = False
                for field, value in movie_data.items():
                    if field != 'censored_id' and value:
                        current_value = getattr(movie, field)
                        if not current_value or (field == 'sample_images' and len(value) > len(str(current_value))):
                            setattr(movie, field, value)
                            updated = True

                if updated:
                    movie.save()
                    self.stats['movies_updated'] += 1
                    print(f"更新作品: {movie.censored_id}")

            return movie

        except Exception as e:
            print(f"保存作品失败 {movie_data.get('censored_id', 'unknown')}: {e}")
            return None

    def add_actress_tags(self, actress):
        """为女友添加标签"""
        try:
            # AVMoo来源标签
            avmoo_tag, _ = ActressTag.objects.get_or_create(
                name='AVMoo',
                defaults={'slug': 'avmoo', 'color': '#17a2b8', 'description': '从AVMoo爬取的女友'}
            )
            avmoo_tag.actresses.add(actress)

            # 根据作品数添加其他标签（稍后更新）

        except Exception as e:
            print(f"添加标签失败 {actress.name}: {e}")

    def update_actress_stats(self):
        """更新女友统计信息"""
        print("=== 更新女友统计信息 ===")

        for actress in Actress.objects.all():
            # 更新作品数
            movie_count = actress.movies.count()
            if actress.movie_count != movie_count:
                actress.movie_count = movie_count
                actress.popularity_score = min(movie_count * 3, 100)
                actress.save()

                # 根据作品数添加标签
                if movie_count > 20:
                    popular_tag, _ = ActressTag.objects.get_or_create(
                        name='人气',
                        defaults={'slug': 'popular', 'color': '#ffd700', 'description': '人气女友'}
                    )
                    popular_tag.actresses.add(actress)

                if movie_count > 10:
                    active_tag, _ = ActressTag.objects.get_or_create(
                        name='活跃',
                        defaults={'slug': 'active', 'color': '#28a745', 'description': '活跃女友'}
                    )
                    active_tag.actresses.add(actress)

        print("女友统计信息更新完成")

    def process_pending_actresses(self, max_pending=50):
        """处理待爬取的女友队列"""
        print(f"=== 处理待爬取女友队列 ({len(self.pending_actresses)} 个) ===")

        processed_count = 0
        for actress_url in list(self.pending_actresses):
            if processed_count >= max_pending:
                break

            if actress_url in self.processed_actress_urls:
                continue

            print(f"处理待爬取女友: {actress_url}")

            # 爬取女友详情
            actress = self.crawl_actress_detail(actress_url)

            if actress:
                processed_count += 1
                self.processed_actress_urls.add(actress_url)
                print(f"完成待爬取女友: {actress.name}")

            # 从队列中移除
            self.pending_actresses.discard(actress_url)

        print(f"处理了 {processed_count} 位待爬取女友")


class Command(BaseCommand):
    help = 'Complete AVMoo crawler: actresses list -> actress details -> movies -> movie details'

    def add_arguments(self, parser):
        parser.add_argument('--max-actresses', type=int, default=20, help='Maximum actresses to crawl')
        parser.add_argument('--max-pages', type=int, default=5, help='Maximum actress list pages to crawl')
        parser.add_argument('--proxy', type=str, help='Proxy server URL')
        parser.add_argument('--delay', type=int, default=5, help='Download delay in seconds')
        parser.add_argument('--no-images', action='store_true', help='Skip image downloading')
        parser.add_argument('--session-id', type=str, help='Custom session ID')
        parser.add_argument('--actresses-only', action='store_true', help='Only crawl actresses, skip movies')

    def handle(self, *args, **options):
        max_actresses = options['max_actresses']
        max_pages = options['max_pages']
        proxy = options.get('proxy')
        delay = options['delay']
        download_images = not options['no_images']
        custom_session_id = options.get('session_id')
        actresses_only = options['actresses_only']

        session_id = custom_session_id or f"avmoo_complete_{int(time.time())}"
        session = CrawlerSession.objects.create(
            session_id=session_id,
            crawler_type='avmoo_complete',
            total_pages=max_pages,
            max_movies=max_actresses,
            delay_seconds=delay,
            proxy_url=proxy or ''
        )

        self.stdout.write(self.style.SUCCESS('=== AVMoo完整爬虫开始 ==='))
        self.stdout.write(f'会话ID: {session_id}')
        self.stdout.write(f'最大女友数: {max_actresses}')
        self.stdout.write(f'最大页数: {max_pages}')
        self.stdout.write(f'下载图片: {download_images}')
        self.stdout.write(f'仅爬女友: {actresses_only}')

        # 显示初始统计
        self.show_initial_stats()

        # 创建爬虫实例
        crawler = AVMooCompleteCrawler(proxy_url=proxy, download_images=download_images)

        try:
            # 第一步：爬取女友列表
            self.stdout.write(self.style.WARNING('\\n=== 第一步：爬取女友列表 ==='))
            actress_urls = crawler.crawl_actresses_list(max_pages)

            if not actress_urls:
                self.stdout.write(self.style.ERROR('未找到女友链接'))
                session.mark_failed('No actress URLs found')
                return

            # 限制女友数量
            actress_urls = actress_urls[:max_actresses]
            self.stdout.write(f'将爬取 {len(actress_urls)} 位女友')

            # 第二步：爬取女友详情和作品
            self.stdout.write(self.style.WARNING('\\n=== 第二步：爬取女友详情和作品 ==='))

            for i, actress_url in enumerate(actress_urls, 1):
                self.stdout.write(f'\\n处理女友 {i}/{len(actress_urls)}: {actress_url}')

                try:
                    actress = crawler.crawl_actress_detail(actress_url)
                    if actress:
                        session.update_progress(processed=i, created=crawler.stats['actresses_created'])

                        if not actresses_only:
                            self.stdout.write(f'女友 {actress.name} 处理完成')
                        else:
                            self.stdout.write(f'女友 {actress.name} 基本信息爬取完成（跳过作品）')

                    # 添加延迟
                    time.sleep(delay)

                except Exception as e:
                    self.stdout.write(f'处理女友失败: {e}')
                    continue

            # 第三步：处理待爬取女友队列
            if crawler.pending_actresses:
                self.stdout.write(self.style.WARNING('\\n=== 第三步：处理待爬取女友队列 ==='))
                crawler.process_pending_actresses(max_pending=20)

            # 第四步：更新统计信息
            self.stdout.write(self.style.WARNING('\\n=== 第四步：更新统计信息 ==='))
            crawler.update_actress_stats()

            session.mark_completed()

            # 显示最终统计
            self.show_final_stats(crawler.stats)

            self.stdout.write(self.style.SUCCESS('\\n=== AVMoo完整爬虫完成 ==='))

        except KeyboardInterrupt:
            session.pause()
            self.stdout.write(self.style.WARNING(f'爬虫被中断，会话ID: {session_id}'))
        except Exception as e:
            session.mark_failed(str(e))
            self.stdout.write(self.style.ERROR(f'爬虫执行失败: {e}'))
            import traceback
            traceback.print_exc()

    def show_initial_stats(self):
        """显示初始统计"""
        from apps.movies.models import Movie
        from apps.actresses.models import Actress

        movie_count = Movie.objects.count()
        actress_count = Actress.objects.count()
        relationships = sum(movie.actresses.count() for movie in Movie.objects.all())

        self.stdout.write('\\n=== 初始数据统计 ===')
        self.stdout.write(f'现有影片数: {movie_count}')
        self.stdout.write(f'现有女友数: {actress_count}')
        self.stdout.write(f'现有关联数: {relationships}')

    def show_final_stats(self, stats):
        """显示最终统计"""
        from apps.movies.models import Movie
        from apps.actresses.models import Actress

        total_movies = Movie.objects.count()
        total_actresses = Actress.objects.count()
        total_relationships = sum(movie.actresses.count() for movie in Movie.objects.all())

        # 图片统计
        actresses_with_profile = Actress.objects.exclude(profile_image='').count()
        actresses_with_cover = Actress.objects.exclude(cover_image='').count()
        movies_with_samples = Movie.objects.exclude(sample_images='').count()

        self.stdout.write('\\n' + '='*60)
        self.stdout.write('=== 爬取结果统计 ===')
        self.stdout.write('='*60)

        self.stdout.write(f'📊 新增女友: {stats["actresses_created"]}')
        self.stdout.write(f'📊 更新女友: {stats["actresses_updated"]}')
        self.stdout.write(f'📊 新增作品: {stats["movies_created"]}')
        self.stdout.write(f'📊 更新作品: {stats["movies_updated"]}')
        self.stdout.write(f'📊 新增关联: {stats["relationships_created"]}')
        self.stdout.write(f'📊 下载图片: {stats["images_downloaded"]}')

        self.stdout.write(f'\\n📈 总女友数: {total_actresses}')
        self.stdout.write(f'📈 总作品数: {total_movies}')
        self.stdout.write(f'📈 总关联数: {total_relationships}')

        self.stdout.write(f'\\n🖼️ 有头像女友: {actresses_with_profile} ({actresses_with_profile/total_actresses*100:.1f}%)')
        self.stdout.write(f'🖼️ 有封面女友: {actresses_with_cover} ({actresses_with_cover/total_actresses*100:.1f}%)')
        self.stdout.write(f'🖼️ 有样例图片作品: {movies_with_samples} ({movies_with_samples/total_movies*100:.1f}%)')

        self.stdout.write('\\n=== 访问链接 ===')
        self.stdout.write('🌐 女友列表: http://localhost:8000/actresses/')
        self.stdout.write('🌐 影片列表: http://localhost:8000/movies/')
        self.stdout.write('🌐 管理后台: http://localhost:8000/admin/')

        self.stdout.write('='*60)
