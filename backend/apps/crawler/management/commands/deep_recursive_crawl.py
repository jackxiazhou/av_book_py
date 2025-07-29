"""
Django管理命令 - 深度递归爬取
从作品页面继续递归其他参演女友，实现多层递归爬取网络
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import random
from urllib.parse import urljoin
from django.core.management.base import BaseCommand
from apps.actresses.models import Actress
from apps.movies.models import Movie
from django.db import transaction
from django.utils import timezone
import json
from collections import deque


class Command(BaseCommand):
    help = '深度递归爬取女友网络'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-actress-url',
            type=str,
            help='起始女友URL'
        )
        parser.add_argument(
            '--start-actress-id',
            type=str,
            help='起始女友ID'
        )
        parser.add_argument(
            '--max-depth',
            type=int,
            default=3,
            help='最大递归深度 (默认: 3)'
        )
        parser.add_argument(
            '--max-actresses-per-level',
            type=int,
            default=5,
            help='每层最大女友数 (默认: 5)'
        )
        parser.add_argument(
            '--max-movies-per-actress',
            type=int,
            default=10,
            help='每个女友最大作品数 (默认: 10)'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=5,
            help='请求延迟（秒）'
        )
        parser.add_argument(
            '--save-network',
            action='store_true',
            help='保存网络关系到文件'
        )

    def handle(self, *args, **options):
        start_url = options.get('start_actress_url')
        start_id = options.get('start_actress_id')
        max_depth = options['max_depth']
        max_actresses_per_level = options['max_actresses_per_level']
        max_movies = options['max_movies_per_actress']
        delay = options['delay']
        save_network = options['save_network']

        if not start_url and not start_id:
            self.stdout.write(
                self.style.ERROR('请提供 --start-actress-url 或 --start-actress-id 参数')
            )
            return

        if start_id and not start_url:
            start_url = f'https://avmoo.website/cn/star/{start_id}'

        self.stdout.write(
            self.style.SUCCESS(f'🕸️ 开始深度递归爬取 (最大深度: {max_depth})')
        )
        self.stdout.write(f'起始女友: {start_url}')

        # 初始化
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
        })

        # 递归爬取状态
        self.crawled_actresses = set()  # 已爬取的女友URL
        self.crawled_movies = set()     # 已爬取的作品URL
        self.actress_network = {}       # 女友网络关系
        self.delay = delay

        try:
            # 开始深度递归
            network = self.deep_crawl(
                start_url, 
                max_depth, 
                max_actresses_per_level, 
                max_movies
            )

            self.stdout.write(
                self.style.SUCCESS(f'🎉 深度递归完成!')
            )
            
            # 显示统计
            self.show_network_stats(network)

            # 保存网络关系
            if save_network:
                self.save_network_to_file(network)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 深度递归出错: {e}')
            )

    def deep_crawl(self, start_url, max_depth, max_actresses_per_level, max_movies):
        """深度递归爬取"""
        # 使用广度优先搜索
        queue = deque([(start_url, 0)])  # (url, depth)
        network = {
            'actresses': {},
            'movies': {},
            'relationships': []
        }

        while queue:
            current_url, depth = queue.popleft()
            
            if depth >= max_depth:
                continue
                
            if current_url in self.crawled_actresses:
                continue

            self.stdout.write(f'\n🎭 [深度 {depth}] 爬取女友: {current_url}')
            
            # 爬取当前女友
            actress_data = self.crawl_actress_with_movies(current_url, max_movies)
            if not actress_data:
                continue

            self.crawled_actresses.add(current_url)
            
            # 保存女友信息
            actress_id = actress_data['actress_id']
            network['actresses'][actress_id] = actress_data
            
            self.stdout.write(f'  ✅ 女友: {actress_data.get("name", "Unknown")}')
            self.stdout.write(f'  🎬 作品: {len(actress_data.get("movies", []))} 个')

            # 从作品中发现新女友
            new_actresses = []
            for movie_data in actress_data.get('movies', []):
                movie_id = movie_data.get('censored_id')
                if movie_id:
                    network['movies'][movie_id] = movie_data
                    
                    # 记录关系
                    network['relationships'].append({
                        'actress_id': actress_id,
                        'movie_id': movie_id,
                        'type': 'stars_in'
                    })

                # 获取作品中的其他女友
                co_actresses = movie_data.get('co_actresses', [])
                for co_actress in co_actresses:
                    if co_actress['url'] not in self.crawled_actresses:
                        new_actresses.append(co_actress['url'])

            # 限制每层的女友数量
            if new_actresses:
                selected_actresses = random.sample(
                    new_actresses, 
                    min(len(new_actresses), max_actresses_per_level)
                )
                
                self.stdout.write(f'  🔗 发现 {len(new_actresses)} 个关联女友，选择 {len(selected_actresses)} 个')
                
                # 添加到队列
                for actress_url in selected_actresses:
                    queue.append((actress_url, depth + 1))

            # 延迟
            time.sleep(self.delay + random.uniform(0, 2))

        return network

    def crawl_actress_with_movies(self, actress_url, max_movies):
        """爬取女友及其作品信息"""
        try:
            # 爬取女友基本信息
            response = self.session.get(actress_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            actress_data = {
                'url': actress_url,
                'movies': []
            }
            
            # 提取女友基本信息
            actress_id_match = re.search(r'/star/([a-f0-9]+)', actress_url)
            if actress_id_match:
                actress_data['actress_id'] = actress_id_match.group(1)
            
            # 提取姓名
            title_text = soup.title.text if soup.title else ''
            if title_text and ' - ' in title_text:
                actress_data['name'] = title_text.split(' - ')[0].strip()
            
            # 获取作品链接
            movie_links = soup.select('a[href*="/movie/"]')
            movie_urls = []
            for link in movie_links:
                href = link.get('href')
                if href:
                    movie_url = urljoin(actress_url, href)
                    movie_urls.append(movie_url)
            
            # 去重并限制数量
            unique_movie_urls = list(set(movie_urls))[:max_movies]
            
            # 爬取每个作品的详情
            for i, movie_url in enumerate(unique_movie_urls):
                if movie_url in self.crawled_movies:
                    continue
                    
                self.stdout.write(f'    🎬 [{i+1}/{len(unique_movie_urls)}] 爬取作品')
                
                movie_data = self.crawl_movie_with_actresses(movie_url)
                if movie_data:
                    actress_data['movies'].append(movie_data)
                    self.crawled_movies.add(movie_url)
                
                # 作品间延迟
                if i < len(unique_movie_urls) - 1:
                    time.sleep(1 + random.uniform(0, 1))
            
            return actress_data
            
        except Exception as e:
            self.stdout.write(f'    ❌ 爬取女友失败: {e}')
            return None

    def crawl_movie_with_actresses(self, movie_url):
        """爬取作品及参演女友信息"""
        try:
            response = self.session.get(movie_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            movie_data = {
                'url': movie_url,
                'co_actresses': []
            }
            
            # 提取番号
            title_text = soup.title.text if soup.title else ''
            if title_text:
                code_match = re.search(r'([A-Z]+-\d+|[A-Z]+\d+)', title_text)
                if code_match:
                    movie_data['censored_id'] = code_match.group(1)
            
            # 提取标题
            clean_title = re.sub(r'([A-Z]+-\d+|[A-Z]+\d+)', '', title_text)
            clean_title = re.sub(r' - AVMOO.*$', '', clean_title).strip()
            if clean_title:
                movie_data['title'] = clean_title
            
            # 获取参演女友
            actress_links = soup.select('a[href*="/star/"]')
            for link in actress_links:
                href = link.get('href')
                name = link.get_text().strip()
                if href and name:
                    actress_url = urljoin(movie_url, href)
                    movie_data['co_actresses'].append({
                        'name': name,
                        'url': actress_url
                    })
            
            return movie_data
            
        except Exception as e:
            self.stdout.write(f'      ❌ 爬取作品失败: {e}')
            return None

    def show_network_stats(self, network):
        """显示网络统计"""
        actresses_count = len(network['actresses'])
        movies_count = len(network['movies'])
        relationships_count = len(network['relationships'])
        
        self.stdout.write(f'\n📊 网络统计:')
        self.stdout.write(f'  女友数量: {actresses_count}')
        self.stdout.write(f'  作品数量: {movies_count}')
        self.stdout.write(f'  关系数量: {relationships_count}')
        
        # 计算网络密度
        if actresses_count > 1:
            max_relationships = actresses_count * movies_count
            density = relationships_count / max_relationships * 100
            self.stdout.write(f'  网络密度: {density:.2f}%')
        
        # 显示热门女友（参演作品最多）
        actress_movie_counts = {}
        for rel in network['relationships']:
            actress_id = rel['actress_id']
            actress_movie_counts[actress_id] = actress_movie_counts.get(actress_id, 0) + 1
        
        if actress_movie_counts:
            top_actresses = sorted(
                actress_movie_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
            
            self.stdout.write(f'\n🌟 热门女友 (作品数):')
            for actress_id, movie_count in top_actresses:
                actress_name = network['actresses'].get(actress_id, {}).get('name', 'Unknown')
                self.stdout.write(f'  {actress_name}: {movie_count} 部作品')

    def save_network_to_file(self, network):
        """保存网络关系到文件"""
        try:
            filename = f'actress_network_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(network, f, ensure_ascii=False, indent=2)
            
            self.stdout.write(f'📁 网络关系已保存到: {filename}')
        except Exception as e:
            self.stdout.write(f'❌ 保存网络文件失败: {e}')
