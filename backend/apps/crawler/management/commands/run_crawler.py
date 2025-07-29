"""
Django management command to run Scrapy crawlers.
"""

import os
import sys
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Run Scrapy crawler'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'spider',
            type=str,
            help='Spider name to run (javbus, avmoo, etc.)'
        )
        parser.add_argument(
            '--pages',
            type=int,
            default=3,
            help='Number of pages to crawl'
        )
        parser.add_argument(
            '--proxy',
            type=str,
            default='http://127.0.0.1:5890',
            help='Proxy server URL'
        )
    
    def handle(self, *args, **options):
        spider_name = options['spider']
        pages = options['pages']
        proxy = options['proxy']
        
        self.stdout.write(f'Starting crawler: {spider_name}')
        self.stdout.write(f'Pages to crawl: {pages}')
        self.stdout.write(f'Using proxy: {proxy}')
        
        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        crawler_dir = os.path.join(project_root, 'crawler')
        
        # 构建命令
        venv_python = os.path.join(crawler_dir, 'venv', 'Scripts', 'python.exe')
        scrapy_cmd = [
            venv_python, '-m', 'scrapy', 'crawl', spider_name,
            '-s', f'PAGES_TO_CRAWL={pages}',
            '-s', f'PROXY_URL={proxy}',
            '-s', 'LOG_LEVEL=INFO'
        ]
        
        try:
            # 运行爬虫
            result = subprocess.run(
                scrapy_cmd,
                cwd=crawler_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                self.stdout.write(
                    self.style.SUCCESS(f'Crawler {spider_name} completed successfully!')
                )
                if result.stdout:
                    self.stdout.write('Output:')
                    self.stdout.write(result.stdout)
            else:
                self.stdout.write(
                    self.style.ERROR(f'Crawler {spider_name} failed!')
                )
                if result.stderr:
                    self.stdout.write('Error:')
                    self.stdout.write(result.stderr)
                    
        except subprocess.TimeoutExpired:
            self.stdout.write(
                self.style.ERROR(f'Crawler {spider_name} timed out!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error running crawler: {e}')
            )
