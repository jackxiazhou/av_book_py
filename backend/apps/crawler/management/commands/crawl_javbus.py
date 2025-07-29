"""
Django management command to run JAVBus crawler as alternative to JAVLibrary.
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


class JAVBusCrawler:
    def __init__(self, proxy_url='http://127.0.0.1:5890'):
        # 尝试使用cloudscraper
        try:
            import cloudscraper
            self.session = cloudscraper.create_scraper()
            self.using_cloudscraper = True
            print("Using cloudscraper for JAVBus")
        except ImportError:
            self.session = requests.Session()
            self.using_cloudscraper = False
        
        self.proxy_url = proxy_url
        if proxy_url:
            self.session.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
        
        # 轮换的User-Agent列表
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        self.current_ua_index = 0
        self.update_headers()
        
        self.scraped_movies = set()
        self.movies_created = 0
        self.request_count = 0
        
        # JAVBus可能的域名
        self.base_urls = [
            'https://www.javbus.com',
            'https://javbus.com',
            'https://www.buscdn.work',
            'https://www.busdmm.work',
        ]
        self.working_base_url = None
    
    def update_headers(self):
        """更新请求头"""
        if not self.using_cloudscraper:
            self.session.headers.update({
                'User-Agent': self.user_agents[self.current_ua_index],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
            })
    
    def find_working_domain(self):
        """查找可用的域名"""
        if self.working_base_url:
            return self.working_base_url
        
        for base_url in self.base_urls:
            try:
                print(f"Testing domain: {base_url}")
                response = self.session.get(base_url, timeout=15)
                if response.status_code == 200 and 'javbus' in response.text.lower():
                    print(f"✅ Working domain found: {base_url}")
                    self.working_base_url = base_url
                    return base_url
                else:
                    print(f"❌ Domain failed: {base_url} (status: {response.status_code})")
            except Exception as e:
                print(f"❌ Domain error: {base_url} - {e}")
            
            time.sleep(2)
        
        return None
    
    def get_page(self, url, timeout=30, max_retries=3):
        """获取页面内容"""
        import random
        
        for attempt in range(max_retries):
            try:
                # 轮换User-Agent
                if self.request_count > 0 and self.request_count % 5 == 0 and not self.using_cloudscraper:
                    self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
                    self.update_headers()
                
                if attempt > 0:
                    delay = random.uniform(3, 8)
                    print(f"Retry {attempt}, waiting {delay:.1f}s...")
                    time.sleep(delay)
                
                print(f"Requesting: {url}")
                response = self.session.get(url, timeout=timeout)
                
                if response.status_code == 403:
                    print(f"403 Forbidden - trying different approach...")
                    if attempt < max_retries - 1:
                        time.sleep(random.uniform(5, 10))
                        continue
                
                response.raise_for_status()
                response.encoding = 'utf-8'
                self.request_count += 1
                
                return response
                
            except Exception as e:
                print(f"Request failed (attempt {attempt + 1}): {e}")
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
        
        # JAVBus的影片链接选择器
        selectors = [
            '.movie-box',
            '.item',
            'a[href*="/"]',
        ]
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                print(f"Selector '{selector}' found {len(elements)} elements")
                
                for element in elements:
                    # 查找链接
                    link = element if element.name == 'a' else element.find('a')
                    if link and link.get('href'):
                        href = link.get('href')
                        # JAVBus的影片链接通常包含影片编号
                        if re.search(r'[A-Z]{2,}-\d+', href, re.IGNORECASE):
                            full_url = urljoin(url, href)
                            movie_links.append(full_url)
                            print(f"Found movie link: {full_url}")
                
                if movie_links:
                    break
                    
            except Exception as e:
                print(f"Error with selector '{selector}': {e}")
                continue
        
        return list(set(movie_links))  # 去重
    
    def extract_censored_id(self, soup, url):
        """提取影片编号"""
        # 从URL中提取
        url_match = re.search(r'/([A-Z]{2,}-\d+)', url, re.IGNORECASE)
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
        
        # 从标题中提取
        title_tag = soup.find('h3') or soup.find('title')
        if title_tag:
            title = title_tag.get_text()
            title_match = re.search(r'([A-Z]{2,}-\d+)', title, re.IGNORECASE)
            if title_match:
                return title_match.group(1).upper()
        
        return None


class Command(BaseCommand):
    help = 'Run JAVBus crawler as alternative to JAVLibrary'
    
    def add_arguments(self, parser):
        parser.add_argument('--pages', type=int, default=2, help='Number of pages to crawl')
        parser.add_argument('--proxy', type=str, default='http://127.0.0.1:5890', help='Proxy server URL')
        parser.add_argument('--delay', type=int, default=5, help='Download delay in seconds')
        parser.add_argument('--max-movies', type=int, default=10, help='Maximum number of movies to crawl')
        parser.add_argument('--resume', type=str, help='Resume from session ID')
        parser.add_argument('--session-id', type=str, help='Custom session ID')
    
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
                session.resume()
            except CrawlerSession.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Session {resume_session_id} not found'))
                return
        else:
            session_id = custom_session_id or str(uuid.uuid4())[:8]
            session = CrawlerSession.objects.create(
                session_id=session_id,
                crawler_type='javbus',
                total_pages=pages,
                max_movies=max_movies,
                delay_seconds=delay,
                proxy_url=proxy
            )
            self.stdout.write(f'Created new session: {session_id}')
        
        self.stdout.write(f'Starting JAVBus crawler...')
        self.stdout.write(f'Session ID: {session.session_id}')
        
        # 创建爬虫实例
        crawler = JAVBusCrawler(proxy_url=proxy)
        self.session = session
        
        # 查找可用域名
        working_domain = crawler.find_working_domain()
        if not working_domain:
            self.stdout.write(self.style.ERROR('No working JAVBus domain found'))
            session.mark_failed('No working domain found')
            return
        
        # 构建起始URL列表
        start_urls = []
        for page in range(session.current_page, pages + 1):
            if page == 1:
                start_urls.append(f'{working_domain}/page/{page}')
            else:
                start_urls.append(f'{working_domain}/page/{page}')
        
        try:
            movies_processed = session.processed_movies
            
            for page_num, start_url in enumerate(start_urls, session.current_page):
                if movies_processed >= max_movies:
                    break
                
                if session.is_url_processed(start_url):
                    continue
                    
                self.stdout.write(f'Processing page {page_num}: {start_url}')
                movie_links = crawler.parse_movie_list(start_url)
                self.stdout.write(f'Found {len(movie_links)} movie links')
                
                session.add_processed_url(start_url)
                session.update_progress(page=page_num)
                
                for movie_url in movie_links:
                    if movies_processed >= max_movies:
                        break
                    
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
                    
                    session.add_processed_url(movie_url)
                    time.sleep(delay)
            
            session.mark_completed()
            self.stdout.write(self.style.SUCCESS(f'JAVBus crawler completed successfully!'))
            self.stdout.write(f'Movies processed: {movies_processed}')
            self.stdout.write(f'Movies created: {crawler.movies_created}')
                    
        except KeyboardInterrupt:
            session.pause()
            self.stdout.write(self.style.WARNING(f'Crawler paused. Resume with: --resume {session.session_id}'))
        except Exception as e:
            session.mark_failed(str(e))
            self.stdout.write(self.style.ERROR(f'Error running crawler: {e}'))
        
        self.show_stats()
    
    def parse_movie_detail(self, crawler, url):
        """解析影片详情页面"""
        response = crawler.get_page(url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        censored_id = crawler.extract_censored_id(soup, url)
        if not censored_id or censored_id in crawler.scraped_movies:
            return None
        
        crawler.scraped_movies.add(censored_id)
        
        return {
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
            'source': 'javbus',
        }
    
    def extract_title(self, soup):
        """提取影片标题"""
        selectors = ['h3', '.title', 'title']
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text().strip()
        return ''
    
    def extract_cover_image(self, soup, base_url):
        """提取封面图片"""
        selectors = ['.bigImage img', '.cover img', 'img.poster']
        for selector in selectors:
            img = soup.select_one(selector)
            if img and img.get('src'):
                return urljoin(base_url, img['src'])
        return ''
    
    def extract_release_date(self, soup):
        """提取发行日期"""
        patterns = [r'發行日期[：:]\s*(\d{4}-\d{2}-\d{2})', r'(\d{4}-\d{2}-\d{2})']
        text = soup.get_text()
        for pattern in patterns:
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
        patterns = [r'長度[：:]\s*([^<\n]+)', r'时长[：:]\s*([^<\n]+)']
        text = soup.get_text()
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return ''
    
    def extract_director(self, soup):
        """提取导演"""
        selectors = ['p:contains("導演") a', '.director a']
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text().strip()
        return ''
    
    def extract_studio(self, soup):
        """提取制作商"""
        selectors = ['p:contains("製作商") a', '.studio a']
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text().strip()
        return ''
    
    def extract_label(self, soup):
        """提取发行商"""
        selectors = ['p:contains("發行商") a', '.label a']
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text().strip()
        return ''
    
    def extract_series(self, soup):
        """提取系列"""
        selectors = ['p:contains("系列") a', '.series a']
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text().strip()
        return ''
    
    def extract_genres(self, soup):
        """提取类别"""
        selectors = ['p:contains("類別") a', '.genre a']
        genres = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                genres = [elem.get_text().strip() for elem in elements]
                break
        return ', '.join(genres)
    
    def extract_idols(self, soup):
        """提取演员"""
        selectors = ['p:contains("演員") a', '.star a', 'a[href*="/star/"]']
        idols = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                idols = [elem.get_text().strip() for elem in elements if elem.get_text().strip()]
                if idols:
                    break
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
                MovieRating.objects.get_or_create(movie=movie)
            else:
                self.stdout.write(f"Movie already exists: {movie.censored_id}")
            
            return movie
            
        except Exception as e:
            self.stdout.write(f"Error saving movie {movie_data['censored_id']}: {e}")
            return None
    
    def show_stats(self):
        """显示爬取统计"""
        javbus_movies = Movie.objects.filter(source='javbus').count()
        self.stdout.write('\n=== Crawling Statistics ===')
        self.stdout.write(f'JAVBus Movies: {javbus_movies}')
        self.stdout.write('===========================')
