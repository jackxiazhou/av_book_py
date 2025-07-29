"""
Django management command to crawl magnet links for existing movies.
"""

import os
import sys
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, quote
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from apps.movies.models import Movie
from apps.magnets.models import MagnetLink
from apps.crawler.models import CrawlerSession, CrawlerLog
import uuid


class MagnetCrawler:
    def __init__(self, proxy_url='http://127.0.0.1:5890'):
        self.session = requests.Session()
        self.proxy_url = proxy_url
        if proxy_url:
            self.session.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.magnets_created = 0
        
        # 磁力链接搜索网站列表
        self.search_sites = [
            {
                'name': 'btdig',
                'url': 'https://btdig.com/search',
                'search_param': 'q',
                'magnet_selector': 'a[href^="magnet:"]'
            },
            {
                'name': 'torrentz2',
                'url': 'https://torrentz2.eu/search',
                'search_param': 'f',
                'magnet_selector': 'a[href^="magnet:"]'
            }
        ]
    
    def get_page(self, url, timeout=30):
        """获取页面内容"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response
        except Exception as e:
            print(f"访问页面失败 {url}: {e}")
            return None
    
    def search_magnets_for_movie(self, movie):
        """为指定影片搜索磁力链接"""
        search_terms = [
            movie.censored_id,
            f"{movie.censored_id} {movie.movie_title[:20]}",
            movie.movie_title[:30] if movie.movie_title else movie.censored_id
        ]
        
        all_magnets = []
        
        for term in search_terms:
            if len(all_magnets) >= 10:  # 限制每部影片最多10个磁力链接
                break
                
            magnets = self.search_magnets(term)
            all_magnets.extend(magnets)
            
            # 去重
            seen_links = set()
            unique_magnets = []
            for magnet in all_magnets:
                if magnet['magnet_link'] not in seen_links:
                    seen_links.add(magnet['magnet_link'])
                    unique_magnets.append(magnet)
            
            all_magnets = unique_magnets
            time.sleep(2)  # 搜索间隔
        
        return all_magnets[:10]  # 最多返回10个
    
    def search_magnets(self, search_term):
        """搜索磁力链接"""
        magnets = []
        
        for site in self.search_sites:
            try:
                # 构建搜索URL
                search_url = f"{site['url']}?{site['search_param']}={quote(search_term)}"
                
                response = self.get_page(search_url)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找磁力链接
                magnet_links = soup.select(site['magnet_selector'])
                
                for link in magnet_links[:5]:  # 每个网站最多取5个
                    magnet_url = link.get('href')
                    if magnet_url and magnet_url.startswith('magnet:'):
                        magnet_info = self.parse_magnet_info(link, soup)
                        magnet_info['magnet_link'] = magnet_url
                        magnet_info['source'] = site['name']
                        magnets.append(magnet_info)
                
                time.sleep(3)  # 网站间隔
                
            except Exception as e:
                print(f"搜索 {site['name']} 失败: {e}")
                continue
        
        return magnets
    
    def parse_magnet_info(self, link_element, soup):
        """解析磁力链接信息"""
        info = {
            'magnet_name': '',
            'file_size': '',
            'file_size_bytes': 0,
            'quality': '',
            'has_subtitle': False,
            'subtitle_language': '',
            'seeders': 0,
            'leechers': 0,
            'completed': 0,
            'publish_date': None,
            'uploader': ''
        }
        
        # 提取名称
        name = link_element.get_text().strip()
        if name:
            info['magnet_name'] = name
            
            # 从名称中提取质量信息
            if re.search(r'1080p|FHD', name, re.IGNORECASE):
                info['quality'] = '1080p'
            elif re.search(r'720p|HD', name, re.IGNORECASE):
                info['quality'] = '720p'
            elif re.search(r'4K|2160p', name, re.IGNORECASE):
                info['quality'] = '4K'
            
            # 检查字幕
            if re.search(r'中文|中字|字幕|sub', name, re.IGNORECASE):
                info['has_subtitle'] = True
                info['subtitle_language'] = '中文'
        
        # 尝试从父元素或兄弟元素中提取其他信息
        parent = link_element.parent
        if parent:
            parent_text = parent.get_text()
            
            # 提取文件大小
            size_match = re.search(r'(\d+(?:\.\d+)?)\s*(GB|MB|KB)', parent_text, re.IGNORECASE)
            if size_match:
                size_value = float(size_match.group(1))
                size_unit = size_match.group(2).upper()
                info['file_size'] = f"{size_value} {size_unit}"
                
                # 转换为字节
                if size_unit == 'GB':
                    info['file_size_bytes'] = int(size_value * 1024 * 1024 * 1024)
                elif size_unit == 'MB':
                    info['file_size_bytes'] = int(size_value * 1024 * 1024)
                elif size_unit == 'KB':
                    info['file_size_bytes'] = int(size_value * 1024)
            
            # 提取种子数和下载数
            seeders_match = re.search(r'(\d+)\s*(?:seed|种子)', parent_text, re.IGNORECASE)
            if seeders_match:
                info['seeders'] = int(seeders_match.group(1))
            
            leechers_match = re.search(r'(\d+)\s*(?:leech|下载)', parent_text, re.IGNORECASE)
            if leechers_match:
                info['leechers'] = int(leechers_match.group(1))
        
        return info


class Command(BaseCommand):
    help = 'Crawl magnet links for existing movies'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--movie-id',
            type=str,
            help='Specific movie censored_id to crawl magnets for'
        )
        parser.add_argument(
            '--source',
            type=str,
            choices=['avmoo', 'javlibrary', 'all'],
            default='all',
            help='Movie source to crawl magnets for'
        )
        parser.add_argument(
            '--max-movies',
            type=int,
            default=20,
            help='Maximum number of movies to process'
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
            help='Download delay in seconds'
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
        movie_id = options.get('movie_id')
        source = options['source']
        max_movies = options['max_movies']
        proxy = options['proxy']
        delay = options['delay']
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
            # 创建新会话
            session_id = custom_session_id or str(uuid.uuid4())[:8]
            session = CrawlerSession.objects.create(
                session_id=session_id,
                crawler_type='magnets',
                max_movies=max_movies,
                delay_seconds=delay,
                proxy_url=proxy
            )
            self.stdout.write(f'Created new session: {session_id}')
        
        self.stdout.write(f'Starting magnet crawler...')
        self.stdout.write(f'Session ID: {session.session_id}')
        self.stdout.write(f'Max movies: {max_movies}')
        self.stdout.write(f'Source filter: {source}')
        self.stdout.write(f'Using proxy: {proxy}')
        self.stdout.write(f'Download delay: {delay}s')
        
        # 创建爬虫实例
        crawler = MagnetCrawler(proxy_url=proxy)
        self.session = session
        
        # 获取要处理的影片
        if movie_id:
            movies = Movie.objects.filter(censored_id=movie_id)
        else:
            query = Movie.objects.all()
            if source != 'all':
                query = query.filter(source=source)
            
            # 优先处理没有磁力链接的影片
            movies = query.filter(magnets__isnull=True).distinct()[:max_movies]

            if len(movies) < max_movies:
                # 如果没有磁力链接的影片不够，再处理有磁力链接但数量较少的
                from django.db import models
                remaining = max_movies - len(movies)
                additional_movies = query.annotate(
                    magnet_count=models.Count('magnets')
                ).filter(magnet_count__lt=3).exclude(
                    id__in=[m.id for m in movies]
                )[:remaining]
                movies = list(movies) + list(additional_movies)
        
        if not movies:
            self.stdout.write('No movies found to process')
            return
        
        self.stdout.write(f'Found {len(movies)} movies to process')
        
        try:
            processed_count = session.processed_movies
            
            for movie in movies[processed_count:]:
                if processed_count >= max_movies:
                    break
                
                self.stdout.write(f'Processing movie: {movie.censored_id} - {movie.movie_title[:30]}')
                
                # 搜索磁力链接
                magnets = crawler.search_magnets_for_movie(movie)
                
                # 保存磁力链接
                saved_count = 0
                for magnet_info in magnets:
                    if self.save_magnet(movie, magnet_info):
                        saved_count += 1
                        crawler.magnets_created += 1
                
                processed_count += 1
                session.update_progress(processed=processed_count, created=crawler.magnets_created)
                
                self.stdout.write(f'Saved {saved_count} magnet links for {movie.censored_id}')
                
                # 延迟
                time.sleep(delay)
            
            # 标记会话完成
            session.mark_completed()
            
            self.stdout.write(
                self.style.SUCCESS(f'Magnet crawler completed successfully!')
            )
            self.stdout.write(f'Movies processed: {processed_count}')
            self.stdout.write(f'Magnets created: {crawler.magnets_created}')
                    
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
        
        # 显示统计
        self.show_stats()
    
    def save_magnet(self, movie, magnet_info):
        """保存磁力链接"""
        try:
            magnet, created = MagnetLink.objects.get_or_create(
                movie=movie,
                magnet_link=magnet_info['magnet_link'],
                defaults=magnet_info
            )
            
            if created:
                self.stdout.write(f"  Created magnet: {magnet_info['magnet_name'][:50]}")
                return True
            else:
                self.stdout.write(f"  Magnet already exists")
                return False
            
        except Exception as e:
            self.stdout.write(f"  Error saving magnet: {e}")
            return False
    
    def show_stats(self):
        """显示统计"""
        from django.db import models
        
        total_magnets = MagnetLink.objects.count()
        movies_with_magnets = Movie.objects.filter(magnets__isnull=False).distinct().count()
        
        self.stdout.write('\n=== Magnet Crawling Statistics ===')
        self.stdout.write(f'Total Magnets: {total_magnets}')
        self.stdout.write(f'Movies with Magnets: {movies_with_magnets}')
        self.stdout.write('==================================')
