"""
Django management command to crawl all actresses from AVMoo with images.
"""

import os
import sys
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from apps.movies.models import Movie
from apps.actresses.models import Actress, ActressTag
from apps.crawler.models import CrawlerSession, CrawlerLog
from apps.crawler.utils.image_downloader import ImageDownloader
import uuid
from datetime import datetime


class AVMooActressCrawler:
    def __init__(self, proxy_url='http://127.0.0.1:5890', download_images=True):
        self.session = requests.Session()
        self.proxy_url = proxy_url
        self.download_images = download_images
        
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
        
        # 初始化图片下载器
        if self.download_images:
            self.image_downloader = ImageDownloader(proxy_url=proxy_url)
        
        self.scraped_actresses = set()
        self.actresses_created = 0
        self.actresses_updated = 0
        self.request_count = 0
        
        self.base_url = 'https://avmoo.cyou'
    
    def update_headers(self):
        """更新请求头"""
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
    
    def get_page(self, url, timeout=30, max_retries=3):
        """获取页面内容"""
        import random
        
        for attempt in range(max_retries):
            try:
                # 每5个请求轮换一次User-Agent
                if self.request_count > 0 and self.request_count % 5 == 0:
                    self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
                    self.update_headers()
                
                if attempt > 0:
                    delay = random.uniform(5, 10)
                    print(f"Retry {attempt}, waiting {delay:.1f}s...")
                    time.sleep(delay)
                
                print(f"Requesting: {url}")
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                response.encoding = 'utf-8'
                
                self.request_count += 1
                return response
                
            except Exception as e:
                print(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(random.uniform(3, 7))
        
        return None
    
    def get_actress_list_urls(self, max_pages=50):
        """获取女友列表页面URL"""
        list_urls = []
        
        # AVMoo的女友列表页面
        base_patterns = [
            f'{self.base_url}/cn/star',
            f'{self.base_url}/cn/actresses',
            f'{self.base_url}/star',
        ]
        
        for base_pattern in base_patterns:
            # 测试基础URL
            response = self.get_page(base_pattern)
            if response and response.status_code == 200:
                print(f"Found working actress list URL: {base_pattern}")
                
                # 添加分页URL
                list_urls.append(base_pattern)
                for page in range(2, max_pages + 1):
                    list_urls.append(f"{base_pattern}?page={page}")
                
                break
        
        return list_urls
    
    def parse_actress_list(self, list_url):
        """解析女友列表页面"""
        response = self.get_page(list_url)
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        actress_urls = []
        
        # 查找女友链接的多种选择器
        actress_selectors = [
            '.star-box a',
            '.actress-box a',
            '.avatar a',
            'a[href*="/star/"]',
            'a[href*="/actress/"]',
            '.star-name a',
            '.photo-frame a'
        ]
        
        for selector in actress_selectors:
            links = soup.select(selector)
            if links:
                print(f"Found {len(links)} actress links with selector: {selector}")
                for link in links:
                    href = link.get('href')
                    if href and ('/star/' in href or '/actress/' in href):
                        full_url = urljoin(list_url, href)
                        actress_urls.append(full_url)
                break
        
        # 去重
        unique_urls = list(set(actress_urls))
        print(f"Found {len(unique_urls)} unique actress URLs")
        return unique_urls
    
    def parse_actress_detail(self, actress_url):
        """解析女友详情页面"""
        response = self.get_page(actress_url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        try:
            actress_data = {}
            
            # 基本信息提取
            actress_data.update(self.extract_basic_info(soup, actress_url))
            
            # 个人资料提取
            actress_data.update(self.extract_personal_info(soup))
            
            # 图片信息提取
            if self.download_images:
                actress_data.update(self.extract_and_download_images(soup, actress_url, actress_data.get('name', 'unknown')))
            
            # 作品信息提取
            actress_data.update(self.extract_movie_info(soup))
            
            return actress_data
            
        except Exception as e:
            print(f"Error parsing actress detail {actress_url}: {e}")
            return None
    
    def extract_basic_info(self, soup, url):
        """提取基本信息"""
        data = {}
        
        # 姓名
        name_selectors = [
            '.avatar-box .photo-info span',
            '.star-name',
            '.actress-name',
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
        
        if not data.get('name'):
            # 从URL中提取
            url_match = re.search(r'/star/([^/]+)', url)
            if url_match:
                data['name'] = url_match.group(1).replace('-', ' ')
        
        # 英文名
        name_en_selectors = [
            '.photo-info .en-name',
            '.english-name',
            '.name-en'
        ]
        
        for selector in name_en_selectors:
            elem = soup.select_one(selector)
            if elem:
                data['name_en'] = elem.get_text().strip()
                break
        
        return data
    
    def extract_personal_info(self, soup):
        """提取个人资料"""
        data = {}
        
        # 获取所有文本内容进行模式匹配
        text_content = soup.get_text()
        
        # 生日
        birthday_patterns = [
            r'生日[：:]\s*(\d{4}-\d{2}-\d{2})',
            r'出生[：:]\s*(\d{4}-\d{2}-\d{2})',
            r'Birthday[：:]\s*(\d{4}-\d{2}-\d{2})'
        ]
        
        for pattern in birthday_patterns:
            match = re.search(pattern, text_content)
            if match:
                try:
                    data['birth_date'] = datetime.strptime(match.group(1), '%Y-%m-%d').date()
                    break
                except ValueError:
                    continue
        
        # 身高
        height_patterns = [
            r'身高[：:]\s*(\d+)',
            r'Height[：:]\s*(\d+)'
        ]
        
        for pattern in height_patterns:
            match = re.search(pattern, text_content)
            if match:
                data['height'] = int(match.group(1))
                break
        
        # 体重
        weight_patterns = [
            r'体重[：:]\s*(\d+)',
            r'Weight[：:]\s*(\d+)'
        ]
        
        for pattern in weight_patterns:
            match = re.search(pattern, text_content)
            if match:
                data['weight'] = int(match.group(1))
                break
        
        # 三围
        measurements_patterns = [
            r'三围[：:]\s*([^\\n]+)',
            r'Measurements[：:]\s*([^\\n]+)'
        ]
        
        for pattern in measurements_patterns:
            match = re.search(pattern, text_content)
            if match:
                data['measurements'] = match.group(1).strip()
                break
        
        # 罩杯
        cup_patterns = [
            r'罩杯[：:]\s*([A-Z]+)',
            r'Cup[：:]\s*([A-Z]+)'
        ]
        
        for pattern in cup_patterns:
            match = re.search(pattern, text_content)
            if match:
                data['cup_size'] = match.group(1)
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
                    data['debut_date'] = datetime.strptime(match.group(1), '%Y-%m-%d').date()
                    break
                except ValueError:
                    continue
        
        # 默认值
        data.setdefault('nationality', '日本')
        data.setdefault('is_active', True)
        
        return data
    
    def extract_and_download_images(self, soup, url, actress_name):
        """提取并下载图片"""
        data = {}
        
        # 头像
        profile_selectors = [
            '.avatar-box .photo-frame img',
            '.profile-image img',
            '.actress-photo img',
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
                    break
        
        # 封面图片
        cover_selectors = [
            '.cover-image img',
            '.actress-cover img',
            '.banner img'
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
                    break
        
        # 图片集
        gallery_selectors = [
            '.gallery img',
            '.photo-gallery img',
            '.actress-gallery img'
        ]
        
        gallery_urls = []
        for selector in gallery_selectors:
            imgs = soup.select(selector)
            for img in imgs:
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    gallery_urls.append(urljoin(url, img_url))
        
        if gallery_urls:
            # 下载图片集（最多10张）
            downloaded_paths = self.image_downloader.download_multiple_images(
                gallery_urls[:10],
                'actress_gallery'
            )
            
            if downloaded_paths:
                gallery_urls_local = [self.image_downloader.get_image_url(path) for path in downloaded_paths]
                data['gallery_images'] = '\n'.join(gallery_urls_local)
        
        return data
    
    def extract_movie_info(self, soup):
        """提取作品信息"""
        data = {}
        
        # 统计作品数量
        movie_selectors = [
            '.movie-box',
            '.video-box', 
            '.work-box',
            '.item'
        ]
        
        movie_count = 0
        for selector in movie_selectors:
            movies = soup.select(selector)
            if movies:
                movie_count = len(movies)
                break
        
        data['movie_count'] = movie_count
        data['popularity_score'] = min(movie_count * 3, 100)  # 基于作品数计算人气值
        
        return data


class Command(BaseCommand):
    help = 'Crawl all actresses from AVMoo with images'
    
    def add_arguments(self, parser):
        parser.add_argument('--max-pages', type=int, default=20, help='Maximum pages to crawl')
        parser.add_argument('--max-actresses', type=int, default=500, help='Maximum actresses to crawl')
        parser.add_argument('--proxy', type=str, default='http://127.0.0.1:5890', help='Proxy server URL')
        parser.add_argument('--delay', type=int, default=8, help='Download delay in seconds')
        parser.add_argument('--no-images', action='store_true', help='Skip image downloading')
        parser.add_argument('--session-id', type=str, help='Custom session ID')
        parser.add_argument('--resume', type=str, help='Resume from session ID')
    
    def handle(self, *args, **options):
        max_pages = options['max_pages']
        max_actresses = options['max_actresses']
        proxy = options['proxy']
        delay = options['delay']
        download_images = not options['no_images']
        custom_session_id = options.get('session_id')
        resume_session_id = options.get('resume')
        
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
            session_id = custom_session_id or f"avmoo_actresses_{int(time.time())}"
            session = CrawlerSession.objects.create(
                session_id=session_id,
                crawler_type='avmoo_actresses',
                total_pages=max_pages,
                max_movies=max_actresses,
                delay_seconds=delay,
                proxy_url=proxy
            )
            self.stdout.write(f'Created new session: {session_id}')
        
        self.stdout.write(f'Starting AVMoo actress crawler...')
        self.stdout.write(f'Max pages: {max_pages}')
        self.stdout.write(f'Max actresses: {max_actresses}')
        self.stdout.write(f'Download images: {download_images}')
        
        # 创建爬虫实例
        crawler = AVMooActressCrawler(proxy_url=proxy, download_images=download_images)
        
        try:
            # 获取女友列表页面
            list_urls = crawler.get_actress_list_urls(max_pages)
            if not list_urls:
                self.stdout.write(self.style.ERROR('No actress list URLs found'))
                session.mark_failed('No actress list URLs found')
                return
            
            self.stdout.write(f'Found {len(list_urls)} list pages to crawl')
            
            actresses_processed = 0
            
            for page_num, list_url in enumerate(list_urls, 1):
                if actresses_processed >= max_actresses:
                    break
                
                if session.is_url_processed(list_url):
                    continue
                
                self.stdout.write(f'Processing list page {page_num}: {list_url}')
                actress_urls = crawler.parse_actress_list(list_url)
                self.stdout.write(f'Found {len(actress_urls)} actress URLs')
                
                session.add_processed_url(list_url)
                session.update_progress(page=page_num)
                
                for actress_url in actress_urls:
                    if actresses_processed >= max_actresses:
                        break
                    
                    if session.is_url_processed(actress_url):
                        continue
                    
                    self.stdout.write(f'Processing actress: {actress_url}')
                    actress_data = crawler.parse_actress_detail(actress_url)
                    
                    if actress_data:
                        actress = self.save_actress(actress_data)
                        if actress:
                            actresses_processed += 1
                            session.update_progress(processed=actresses_processed, created=crawler.actresses_created)
                            self.stdout.write(f"Processed actress: {actress.name}")
                    
                    session.add_processed_url(actress_url)
                    time.sleep(delay)
                
                # 页面间延迟
                time.sleep(delay * 2)
            
            session.mark_completed()
            self.stdout.write(self.style.SUCCESS(f'AVMoo actress crawler completed!'))
            self.stdout.write(f'Actresses processed: {actresses_processed}')
            self.stdout.write(f'Actresses created: {crawler.actresses_created}')
            self.stdout.write(f'Actresses updated: {crawler.actresses_updated}')
            
        except KeyboardInterrupt:
            session.pause()
            self.stdout.write(self.style.WARNING(f'Crawler paused. Resume with: --resume {session.session_id}'))
        except Exception as e:
            session.mark_failed(str(e))
            self.stdout.write(self.style.ERROR(f'Error running crawler: {e}'))
            import traceback
            traceback.print_exc()
    
    def save_actress(self, actress_data):
        """保存女友到数据库"""
        try:
            actress, created = Actress.objects.get_or_create(
                name=actress_data['name'],
                defaults=actress_data
            )
            
            if created:
                self.stdout.write(f"Created actress: {actress.name}")
                
                # 添加默认标签
                if actress.movie_count > 20:
                    popular_tag, _ = ActressTag.objects.get_or_create(
                        name='人气',
                        defaults={'slug': 'popular', 'color': '#ffd700'}
                    )
                    popular_tag.actresses.add(actress)
                
                if actress.movie_count > 0:
                    active_tag, _ = ActressTag.objects.get_or_create(
                        name='活跃',
                        defaults={'slug': 'active', 'color': '#28a745'}
                    )
                    active_tag.actresses.add(actress)
            else:
                # 更新现有女友信息
                updated = False
                for field, value in actress_data.items():
                    if field != 'name' and value and not getattr(actress, field):
                        setattr(actress, field, value)
                        updated = True
                
                if updated:
                    actress.save()
                    self.stdout.write(f"Updated actress: {actress.name}")
            
            return actress
            
        except Exception as e:
            self.stdout.write(f"Error saving actress {actress_data.get('name', 'unknown')}: {e}")
            return None
