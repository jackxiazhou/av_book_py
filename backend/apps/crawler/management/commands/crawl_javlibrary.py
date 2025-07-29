"""
Django management command to run JAVLibrary crawler.
"""

import os
import sys
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from apps.movies.models import Movie, MovieRating
from apps.magnets.models import MagnetLink
from apps.crawler.models import CrawlerSession, CrawlerLog
import uuid


class JAVLibraryCrawler:
    def __init__(self, proxy_url='http://127.0.0.1:5890'):
        # 尝试使用cloudscraper绕过Cloudflare
        try:
            import cloudscraper
            self.session = cloudscraper.create_scraper()
            self.using_cloudscraper = True
            print("Using cloudscraper for Cloudflare bypass")
        except ImportError:
            self.session = requests.Session()
            self.using_cloudscraper = False
            print("Cloudscraper not available, using regular requests")

        self.proxy_url = proxy_url
        if proxy_url:
            self.session.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }

        # 轮换的User-Agent列表
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

        self.current_ua_index = 0

        # 设置基础请求头
        self.update_headers()

        self.scraped_movies = set()
        self.movies_created = 0
        self.base_url = 'https://www.javlibrary.com'
        self.request_count = 0

        # 设置会话配置
        self.session.max_redirects = 5

        # 添加重试适配器
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[403, 429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def update_headers(self):
        """更新请求头"""
        self.session.headers.update({
            'User-Agent': self.user_agents[self.current_ua_index],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8,zh-CN;q=0.7,zh;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })

    def rotate_user_agent(self):
        """轮换User-Agent"""
        self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
        self.update_headers()
        print(f"Rotated to User-Agent: {self.user_agents[self.current_ua_index][:50]}...")
    
    def get_page(self, url, timeout=30, max_retries=3):
        """获取页面内容"""
        import random

        for attempt in range(max_retries):
            try:
                # 每5个请求轮换一次User-Agent
                if self.request_count > 0 and self.request_count % 5 == 0:
                    self.rotate_user_agent()

                # 添加随机延迟
                if attempt > 0:
                    delay = random.uniform(3, 8)
                    print(f"Retry {attempt}, waiting {delay:.1f}s...")
                    time.sleep(delay)

                # 更新Referer头
                if self.request_count > 0:
                    self.session.headers.update({
                        'Referer': self.base_url
                    })

                print(f"Requesting: {url} (attempt {attempt + 1})")
                response = self.session.get(url, timeout=timeout)

                # 检查响应状态
                if response.status_code == 403:
                    print(f"403 Forbidden - rotating User-Agent and retrying...")
                    self.rotate_user_agent()
                    if attempt < max_retries - 1:
                        time.sleep(random.uniform(5, 10))
                        continue

                if response.status_code == 429:
                    print(f"429 Too Many Requests - waiting longer...")
                    if attempt < max_retries - 1:
                        time.sleep(random.uniform(10, 20))
                        continue

                response.raise_for_status()
                response.encoding = 'utf-8'

                self.request_count += 1

                # 检查是否被重定向到验证页面
                if 'cloudflare' in response.text.lower() or 'checking your browser' in response.text.lower():
                    print("Detected Cloudflare protection, waiting...")
                    time.sleep(random.uniform(10, 15))
                    if attempt < max_retries - 1:
                        continue

                return response

            except requests.exceptions.RequestException as e:
                print(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    print(f"All attempts failed for {url}")
                    return None

                # 指数退避
                wait_time = (2 ** attempt) + random.uniform(1, 3)
                print(f"Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)

            except Exception as e:
                print(f"Unexpected error: {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(random.uniform(2, 5))

        return None
    
    def parse_movie_list(self, url):
        """解析影片列表页面"""
        response = self.get_page(url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        movie_links = []

        print(f"Page title: {soup.title.string if soup.title else 'No title'}")

        # 检查是否被重定向或阻止
        if soup.title and ('403' in soup.title.string or 'forbidden' in soup.title.string.lower()):
            print("Page shows 403 Forbidden")
            return []

        # JAVLibrary的影片链接选择器 - 更精确的选择器
        selectors = [
            '.video a[href*="?v=jav"]',  # 最精确的选择器
            '.videothumblist .video a',
            'a[href*="?v=jav"]',
            '.videos .video a',
            'div.video a',
            'td.video a'
        ]

        print(f"Parsing page content, length: {len(response.text)}")

        for selector in selectors:
            try:
                links = soup.select(selector)
                print(f"Selector '{selector}' found {len(links)} links")

                if links:
                    for link in links:
                        href = link.get('href')
                        if href:
                            # 确保链接包含影片ID
                            if 'v=jav' in href or '?v=' in href:
                                full_url = urljoin(url, href)
                                movie_links.append(full_url)
                                print(f"Found movie link: {full_url}")

                    if movie_links:  # 如果找到了链接就停止尝试其他选择器
                        break

            except Exception as e:
                print(f"Error with selector '{selector}': {e}")
                continue

        # 如果没有找到链接，尝试查找所有链接并过滤
        if not movie_links:
            print("No links found with specific selectors, trying all links...")
            all_links = soup.find_all('a', href=True)
            print(f"Found {len(all_links)} total links")

            for link in all_links:
                href = link.get('href')
                if href and ('v=jav' in href or '?v=' in href):
                    full_url = urljoin(url, href)
                    movie_links.append(full_url)
                    print(f"Found movie link: {full_url}")

        unique_links = list(set(movie_links))  # 去重
        print(f"Total unique movie links found: {len(unique_links)}")
        return unique_links
    
    def extract_censored_id(self, soup, url):
        """提取影片编号"""
        # 从URL中提取
        url_match = re.search(r'v=jav(\w+)', url)
        if url_match:
            return url_match.group(1).upper()
        
        # 从页面内容中提取
        patterns = [
            r'識別碼:\s*([A-Z0-9-]+)',
            r'品番:\s*([A-Z0-9-]+)',
            r'番號:\s*([A-Z0-9-]+)',
            r'ID:\s*([A-Z0-9-]+)',
        ]
        
        text = soup.get_text()
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip().upper()
        
        # 从标题中提取
        title_tag = soup.find('h3') or soup.find('title')
        if title_tag:
            title = title_tag.get_text()
            title_match = re.search(r'([A-Z]{2,}-\d+)', title, re.IGNORECASE)
            if title_match:
                return title_match.group(1).upper()
        
        return None


class Command(BaseCommand):
    help = 'Run JAVLibrary crawler to collect movie data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--pages',
            type=int,
            default=2,
            help='Number of pages to crawl (default: 2)'
        )
        parser.add_argument(
            '--proxy',
            type=str,
            default='http://127.0.0.1:5890',
            help='Proxy server URL'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=5,
            help='Download delay in seconds (default: 5)'
        )
        parser.add_argument(
            '--max-movies',
            type=int,
            default=10,
            help='Maximum number of movies to crawl'
        )
        parser.add_argument(
            '--resume',
            type=str,
            help='Resume from session ID'
        )
        parser.add_argument(
            '--session-id',
            type=str,
            help='Custom session ID'
        )
    
    def handle(self, *args, **options):
        pages = options['pages']
        proxy = options['proxy']
        delay = options['delay']
        max_movies = options['max_movies']
        resume_session_id = options.get('resume')
        custom_session_id = options.get('session_id')
        
        # 处理断点续跑
        session = None
        if resume_session_id:
            try:
                session = CrawlerSession.objects.get(session_id=resume_session_id)
                self.stdout.write(f'Resuming session: {resume_session_id}')
                self.stdout.write(f'Previous progress: {session.processed_movies}/{session.max_movies} movies')
                
                # 使用会话中的配置
                pages = session.total_pages
                max_movies = session.max_movies
                delay = session.delay_seconds
                proxy = session.proxy_url
                
                session.resume()
            except CrawlerSession.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Session {resume_session_id} not found'))
                return
        else:
            # 创建新会话
            session_id = custom_session_id or str(uuid.uuid4())[:8]
            session = CrawlerSession.objects.create(
                session_id=session_id,
                crawler_type='javlibrary',
                total_pages=pages,
                max_movies=max_movies,
                delay_seconds=delay,
                proxy_url=proxy
            )
            self.stdout.write(f'Created new session: {session_id}')
        
        self.stdout.write(f'Starting JAVLibrary crawler...')
        self.stdout.write(f'Session ID: {session.session_id}')
        self.stdout.write(f'Pages to crawl: {pages}')
        self.stdout.write(f'Max movies: {max_movies}')
        self.stdout.write(f'Using proxy: {proxy}')
        self.stdout.write(f'Download delay: {delay}s')
        
        # 创建爬虫实例
        crawler = JAVLibraryCrawler(proxy_url=proxy)
        self.session = session
        
        # 构建起始URL列表 - 尝试多个入口点
        start_urls = []
        base_urls = [
            'https://www.javlibrary.com/en/vl_newrelease.php',
            'https://www.javlibrary.com/cn/vl_newrelease.php',  # 中文版
            'https://www.javlibrary.com/ja/vl_newrelease.php',  # 日文版
        ]

        # 首先测试哪个基础URL可以访问
        working_base_url = None
        for base_url in base_urls:
            self.stdout.write(f'Testing base URL: {base_url}')
            test_response = crawler.get_page(base_url, timeout=15, max_retries=1)
            if test_response and test_response.status_code == 200:
                working_base_url = base_url
                self.stdout.write(f'Working base URL found: {base_url}')
                break
            else:
                self.stdout.write(f'Base URL failed: {base_url}')
                time.sleep(3)

        if not working_base_url:
            self.stdout.write(self.style.ERROR('No working base URL found. All JAVLibrary URLs are blocked.'))
            session.mark_failed('All base URLs are blocked')
            return

        # 构建页面URL列表
        for page in range(session.current_page, pages + 1):
            if page == 1:
                start_urls.append(working_base_url)
            else:
                start_urls.append(f'{working_base_url}?page={page}')
        
        try:
            # 开始爬取
            self.stdout.write('Starting crawl...')
            movies_processed = session.processed_movies
            
            for page_num, start_url in enumerate(start_urls, session.current_page):
                if movies_processed >= max_movies:
                    break
                
                # 检查URL是否已处理
                if session.is_url_processed(start_url):
                    self.stdout.write(f'Skipping already processed page: {start_url}')
                    continue
                    
                self.stdout.write(f'Processing page {page_num}: {start_url}')
                movie_links = crawler.parse_movie_list(start_url)
                self.stdout.write(f'Found {len(movie_links)} movie links')
                
                # 标记页面为已处理
                session.add_processed_url(start_url)
                session.update_progress(page=page_num)
                
                for movie_url in movie_links:
                    if movies_processed >= max_movies:
                        break
                    
                    # 检查影片URL是否已处理
                    if session.is_url_processed(movie_url):
                        continue
                    
                    self.stdout.write(f'Processing movie: {movie_url}')
                    movie_data = self.parse_movie_detail(crawler, movie_url)
                    
                    if movie_data:
                        movie = self.save_movie(movie_data)
                        if movie:
                            movies_processed += 1
                            crawler.movies_created += 1
                            session.update_progress(processed=movies_processed, created=crawler.movies_created)
                    
                    # 标记影片URL为已处理
                    session.add_processed_url(movie_url)
                    
                    # 延迟避免被封
                    time.sleep(delay)
            
            # 标记会话完成
            session.mark_completed()
            
            self.stdout.write(
                self.style.SUCCESS(f'JAVLibrary crawler completed successfully!')
            )
            self.stdout.write(f'Movies processed: {movies_processed}')
            self.stdout.write(f'Movies created: {crawler.movies_created}')
                    
        except KeyboardInterrupt:
            session.pause()
            self.stdout.write(
                self.style.WARNING(f'Crawler paused. Resume with: --resume {session.session_id}')
            )
        except Exception as e:
            session.mark_failed(str(e))
            self.stdout.write(
                self.style.ERROR(f'Error running crawler: {e}')
            )
            import traceback
            traceback.print_exc()
        
        # 显示数据统计
        self.show_stats()
    
    def parse_movie_detail(self, crawler, url):
        """解析影片详情页面"""
        response = crawler.get_page(url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取影片编号
        censored_id = crawler.extract_censored_id(soup, url)
        if not censored_id or censored_id in crawler.scraped_movies:
            return None
        
        crawler.scraped_movies.add(censored_id)
        
        # 提取影片信息
        movie_data = {
            'censored_id': censored_id,
            'movie_title': self.extract_title(soup),
            'movie_pic_cover': self.extract_cover_image(soup, url),
            'release_date': self.extract_release_date(soup),
            'movie_length': self.extract_movie_length(soup),
            'director': self.extract_director(soup),
            'studio': self.extract_studio(soup),
            'label': self.extract_label(soup),
            'series': self.extract_series(soup),
            'genre': self.extract_genres(soup),
            'jav_idols': self.extract_idols(soup),
            'source': 'javlibrary',
        }
        
        return movie_data
    
    def extract_title(self, soup):
        """提取影片标题"""
        # JAVLibrary特定的标题选择器
        title_selectors = [
            'h3 a',
            '.post-title',
            '#video_title',
            'title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                return title_elem.get_text().strip()
        
        return ''
    
    def extract_cover_image(self, soup, base_url):
        """提取封面图片"""
        selectors = [
            '#video_jacket_img',
            '.videojacket img',
            '.cover img',
            'img[src*="jacket"]'
        ]
        
        for selector in selectors:
            img = soup.select_one(selector)
            if img and img.get('src'):
                return urljoin(base_url, img['src'])
        return ''
    
    def extract_release_date(self, soup):
        """提取发行日期"""
        date_patterns = [
            r'發行日期[：:]\s*(\d{4}-\d{2}-\d{2})',
            r'Release Date[：:]\s*(\d{4}-\d{2}-\d{2})',
            r'(\d{4}-\d{2}-\d{2})'
        ]
        
        text = soup.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    from datetime import datetime
                    return datetime.strptime(match.group(1), '%Y-%m-%d').date()
                except ValueError:
                    continue
        return None
    
    def extract_movie_length(self, soup):
        """提取影片时长"""
        length_patterns = [
            r'Length[：:]\s*([^<\n]+)',
            r'時間[：:]\s*([^<\n]+)',
        ]
        
        text = soup.get_text()
        for pattern in length_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return ''
    
    def extract_director(self, soup):
        """提取导演"""
        director_selectors = [
            'td:contains("Director") + td a',
            'td:contains("導演") + td a',
            '.director a'
        ]
        
        for selector in director_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        return ''
    
    def extract_studio(self, soup):
        """提取制作商"""
        studio_selectors = [
            'td:contains("Studio") + td a',
            'td:contains("製作商") + td a',
            '.studio a'
        ]
        
        for selector in studio_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        return ''
    
    def extract_label(self, soup):
        """提取发行商"""
        label_selectors = [
            'td:contains("Label") + td a',
            'td:contains("發行商") + td a',
            '.label a'
        ]
        
        for selector in label_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        return ''
    
    def extract_series(self, soup):
        """提取系列"""
        series_selectors = [
            'td:contains("Series") + td a',
            'td:contains("系列") + td a',
            '.series a'
        ]
        
        for selector in series_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        return ''
    
    def extract_genres(self, soup):
        """提取类别"""
        genre_selectors = [
            'td:contains("Genre") + td a',
            'td:contains("類別") + td a',
            '.genre a'
        ]
        
        genres = []
        for selector in genre_selectors:
            elements = soup.select(selector)
            if elements:
                genres = [elem.get_text().strip() for elem in elements]
                break
        
        return ', '.join(genres)
    
    def extract_idols(self, soup):
        """提取演员"""
        idols = []
        
        # JAVLibrary特定的演员选择器
        idol_selectors = [
            'td:contains("Cast") + td a',
            'td:contains("演員") + td a',
            '.cast a',
            'a[href*="/star/"]'
        ]
        
        for selector in idol_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    idols = [elem.get_text().strip() for elem in elements if elem.get_text().strip()]
                    if idols:
                        break
            except Exception:
                continue
        
        return ', '.join(idols)
    
    def save_movie(self, movie_data):
        """保存影片到数据库"""
        try:
            movie, created = Movie.objects.get_or_create(
                censored_id=movie_data['censored_id'],
                defaults=movie_data
            )
            
            if created:
                self.stdout.write(f"Created movie: {movie.censored_id}")
                
                # 创建评分记录
                MovieRating.objects.get_or_create(movie=movie)
            else:
                self.stdout.write(f"Movie already exists: {movie.censored_id}")
            
            return movie
            
        except Exception as e:
            self.stdout.write(f"Error saving movie {movie_data['censored_id']}: {e}")
            return None
    
    def show_stats(self):
        """显示爬取统计"""
        javlibrary_movies = Movie.objects.filter(source='javlibrary').count()
        javlibrary_magnets = MagnetLink.objects.filter(source='javlibrary').count()
        
        self.stdout.write('\n=== Crawling Statistics ===')
        self.stdout.write(f'JAVLibrary Movies: {javlibrary_movies}')
        self.stdout.write(f'JAVLibrary Magnets: {javlibrary_magnets}')
        self.stdout.write('===========================')
