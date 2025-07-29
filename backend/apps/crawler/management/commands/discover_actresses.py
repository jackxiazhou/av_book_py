"""
Django管理命令 - 自动发现女友列表
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import random
from urllib.parse import urljoin, urlparse
from django.core.management.base import BaseCommand
from apps.actresses.models import Actress
from django.db import transaction
import json


class Command(BaseCommand):
    help = '自动发现女友列表页的所有女友'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-page',
            type=int,
            default=1,
            help='起始页码 (默认: 1)'
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            default=10,
            help='最大页数 (默认: 10)'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=3,
            help='页面间延迟（秒）'
        )
        parser.add_argument(
            '--save-urls',
            action='store_true',
            help='保存女友URL到文件'
        )
        parser.add_argument(
            '--output-file',
            type=str,
            default='discovered_actresses.json',
            help='输出文件名'
        )

    def handle(self, *args, **options):
        start_page = options['start_page']
        max_pages = options['max_pages']
        delay = options['delay']
        save_urls = options['save_urls']
        output_file = options['output_file']

        self.stdout.write(
            self.style.SUCCESS(f'🔍 开始发现女友列表 (页码 {start_page}-{start_page + max_pages - 1})')
        )

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
        })

        discovered_actresses = []
        total_found = 0

        try:
            for page in range(start_page, start_page + max_pages):
                self.stdout.write(f'📄 正在处理第 {page} 页...')
                
                actresses = self.discover_page(page)
                if actresses:
                    discovered_actresses.extend(actresses)
                    total_found += len(actresses)
                    self.stdout.write(f'  ✅ 发现 {len(actresses)} 个女友')
                else:
                    self.stdout.write(f'  ❌ 第 {page} 页没有发现女友')
                
                # 延迟
                if page < start_page + max_pages - 1:
                    delay_time = delay + random.uniform(0, 2)
                    self.stdout.write(f'  ⏱️ 等待 {delay_time:.1f} 秒...')
                    time.sleep(delay_time)

            self.stdout.write(
                self.style.SUCCESS(f'🎉 发现完成！总共找到 {total_found} 个女友')
            )

            # 去重
            unique_actresses = self.deduplicate_actresses(discovered_actresses)
            self.stdout.write(f'📊 去重后: {len(unique_actresses)} 个唯一女友')

            # 保存到文件
            if save_urls:
                self.save_to_file(unique_actresses, output_file)

            # 保存到数据库
            saved_count = self.save_to_database(unique_actresses)
            self.stdout.write(f'💾 保存到数据库: {saved_count} 个女友')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 发现过程出错: {e}')
            )

    def discover_page(self, page):
        """发现单页女友"""
        # 尝试多个可能的女友列表URL
        base_urls = [
            f'https://avmoo.website/cn/star?page={page}',
            f'https://avmoo.website/star?page={page}',
            f'https://avmoo.cyou/cn/star?page={page}',
            f'https://avmoo.cyou/star?page={page}',
        ]

        for base_url in base_urls:
            try:
                response = self.session.get(base_url, timeout=30)
                if response.status_code == 200:
                    return self.parse_actress_list(response, base_url)
            except Exception as e:
                self.stdout.write(f'    尝试 {base_url} 失败: {e}')
                continue

        return []

    def parse_actress_list(self, response, base_url):
        """解析女友列表页面"""
        soup = BeautifulSoup(response.content, 'html.parser')
        actresses = []

        # 尝试多种选择器
        selectors = [
            'a[href*="/star/"]',
            '.actress-item a',
            '.star-item a',
            '.grid-item a',
            '.thumbnail a'
        ]

        for selector in selectors:
            links = soup.select(selector)
            if links:
                self.stdout.write(f'    使用选择器: {selector} (找到 {len(links)} 个链接)')
                
                for link in links:
                    href = link.get('href')
                    if href and '/star/' in href:
                        # 提取女友ID
                        actress_id_match = re.search(r'/star/([a-f0-9]+)', href)
                        if actress_id_match:
                            actress_id = actress_id_match.group(1)
                            actress_url = urljoin(base_url, href)
                            
                            # 尝试获取女友姓名
                            name = self.extract_actress_name(link)
                            
                            actress_info = {
                                'actress_id': actress_id,
                                'name': name,
                                'url': actress_url,
                                'discovered_from': base_url
                            }
                            actresses.append(actress_info)
                
                if actresses:
                    break  # 找到女友就停止尝试其他选择器

        return actresses

    def extract_actress_name(self, link_element):
        """从链接元素中提取女友姓名"""
        # 尝试多种方式获取姓名
        name_sources = [
            link_element.get('title'),
            link_element.get_text().strip(),
        ]
        
        # 查找图片的alt属性
        img = link_element.find('img')
        if img:
            name_sources.extend([
                img.get('alt'),
                img.get('title')
            ])

        for name in name_sources:
            if name and name.strip():
                # 清理姓名
                clean_name = re.sub(r'\s+', ' ', name.strip())
                if len(clean_name) > 0 and len(clean_name) < 50:
                    return clean_name

        return None

    def deduplicate_actresses(self, actresses):
        """去重女友列表"""
        seen_ids = set()
        unique_actresses = []
        
        for actress in actresses:
            actress_id = actress['actress_id']
            if actress_id not in seen_ids:
                seen_ids.add(actress_id)
                unique_actresses.append(actress)
        
        return unique_actresses

    def save_to_file(self, actresses, filename):
        """保存女友列表到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(actresses, f, ensure_ascii=False, indent=2)
            
            self.stdout.write(f'📁 女友列表已保存到: {filename}')
        except Exception as e:
            self.stdout.write(f'❌ 保存文件失败: {e}')

    def save_to_database(self, actresses):
        """保存女友基本信息到数据库"""
        saved_count = 0
        
        for actress_info in actresses:
            try:
                with transaction.atomic():
                    actress, created = Actress.objects.get_or_create(
                        name=actress_info.get('name', ''),
                        defaults={
                            'source': 'discovered',
                            'source_url': actress_info.get('url'),
                        }
                    )
                    
                    if created:
                        saved_count += 1
                        self.stdout.write(f'  ✅ 新增女友: {actress.name}')
                    else:
                        # 更新URL如果为空
                        if not actress.source_url and actress_info.get('url'):
                            actress.source_url = actress_info.get('url')
                            actress.save()
                        self.stdout.write(f'  ℹ️ 已存在: {actress.name}')
                        
            except Exception as e:
                self.stdout.write(f'  ❌ 保存失败 {actress_info.get("name", "Unknown")}: {e}')
        
        return saved_count

    def get_discovered_actresses_stats(self):
        """获取发现的女友统计"""
        total_actresses = Actress.objects.count()
        discovered_actresses = Actress.objects.filter(source='discovered').count()
        
        self.stdout.write(f'\n📊 女友统计:')
        self.stdout.write(f'  总女友数: {total_actresses}')
        self.stdout.write(f'  已发现女友: {discovered_actresses}')
        self.stdout.write(f'  待爬取女友: {discovered_actresses}')

        return {
            'total': total_actresses,
            'discovered': discovered_actresses,
        }
