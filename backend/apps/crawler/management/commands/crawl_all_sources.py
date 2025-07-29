"""
Django management command to crawl all three sources systematically.
"""

import os
import sys
import time
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone
from apps.movies.models import Movie
from apps.magnets.models import MagnetLink
from apps.crawler.models import CrawlerSession
import uuid


class Command(BaseCommand):
    help = 'Crawl all three sources (AVMoo, JAVLibrary, JAVBus) systematically'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--pages-per-source',
            type=int,
            default=5,
            help='Number of pages to crawl per source (default: 5)'
        )
        parser.add_argument(
            '--movies-per-source',
            type=int,
            default=50,
            help='Maximum movies per source (default: 50)'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=5,
            help='Delay between requests (default: 5)'
        )
        parser.add_argument(
            '--proxy',
            type=str,
            default='http://127.0.0.1:5890',
            help='Proxy server URL'
        )
        parser.add_argument(
            '--session-prefix',
            type=str,
            default='multi_source',
            help='Session ID prefix'
        )
        parser.add_argument(
            '--skip-avmoo',
            action='store_true',
            help='Skip AVMoo crawling'
        )
        parser.add_argument(
            '--skip-javlibrary',
            action='store_true',
            help='Skip JAVLibrary crawling'
        )
        parser.add_argument(
            '--skip-javbus',
            action='store_true',
            help='Skip JAVBus crawling'
        )
        parser.add_argument(
            '--use-selenium',
            action='store_true',
            help='Use Selenium for JAVLibrary'
        )
        parser.add_argument(
            '--crawl-magnets',
            action='store_true',
            help='Also crawl magnet links after movies'
        )
    
    def handle(self, *args, **options):
        pages_per_source = options['pages_per_source']
        movies_per_source = options['movies_per_source']
        delay = options['delay']
        proxy = options['proxy']
        session_prefix = options['session_prefix']
        skip_avmoo = options['skip_avmoo']
        skip_javlibrary = options['skip_javlibrary']
        skip_javbus = options['skip_javbus']
        use_selenium = options['use_selenium']
        crawl_magnets = options['crawl_magnets']
        
        # 生成主会话ID
        main_session_id = f"{session_prefix}_{int(time.time())}"
        
        self.stdout.write(self.style.SUCCESS('🚀 Starting comprehensive crawling from all sources'))
        self.stdout.write(f'Main Session ID: {main_session_id}')
        self.stdout.write(f'Pages per source: {pages_per_source}')
        self.stdout.write(f'Movies per source: {movies_per_source}')
        self.stdout.write(f'Delay: {delay}s')
        self.stdout.write(f'Proxy: {proxy}')
        
        # 显示初始统计
        self.show_initial_stats()
        
        crawl_results = {}
        
        # 1. 爬取 AVMoo
        if not skip_avmoo:
            self.stdout.write('\n' + '='*60)
            self.stdout.write('📡 Phase 1: Crawling AVMoo')
            self.stdout.write('='*60)
            
            avmoo_session_id = f"{main_session_id}_avmoo"
            try:
                call_command(
                    'crawl_avmoo',
                    pages=pages_per_source,
                    max_movies=movies_per_source,
                    delay=delay,
                    proxy=proxy,
                    session_id=avmoo_session_id
                )
                crawl_results['avmoo'] = 'success'
                self.stdout.write(self.style.SUCCESS('✅ AVMoo crawling completed'))
            except Exception as e:
                crawl_results['avmoo'] = f'failed: {e}'
                self.stdout.write(self.style.ERROR(f'❌ AVMoo crawling failed: {e}'))
            
            # 等待间隔
            self.stdout.write('⏳ Waiting 30 seconds before next source...')
            time.sleep(30)
        
        # 2. 爬取 JAVLibrary
        if not skip_javlibrary:
            self.stdout.write('\n' + '='*60)
            self.stdout.write('📡 Phase 2: Crawling JAVLibrary')
            self.stdout.write('='*60)
            
            javlib_session_id = f"{main_session_id}_javlibrary"
            try:
                if use_selenium:
                    self.stdout.write('🤖 Using Selenium for JAVLibrary')
                    call_command(
                        'crawl_javlibrary_selenium',
                        pages=pages_per_source,
                        max_movies=movies_per_source,
                        delay=delay,
                        proxy=proxy,
                        session_id=javlib_session_id,
                        headless=True
                    )
                else:
                    self.stdout.write('🌐 Using Requests for JAVLibrary')
                    call_command(
                        'crawl_javlibrary',
                        pages=pages_per_source,
                        max_movies=movies_per_source,
                        delay=delay,
                        proxy=proxy,
                        session_id=javlib_session_id
                    )
                crawl_results['javlibrary'] = 'success'
                self.stdout.write(self.style.SUCCESS('✅ JAVLibrary crawling completed'))
            except Exception as e:
                crawl_results['javlibrary'] = f'failed: {e}'
                self.stdout.write(self.style.ERROR(f'❌ JAVLibrary crawling failed: {e}'))
            
            # 等待间隔
            self.stdout.write('⏳ Waiting 30 seconds before next source...')
            time.sleep(30)
        
        # 3. 爬取 JAVBus
        if not skip_javbus:
            self.stdout.write('\n' + '='*60)
            self.stdout.write('📡 Phase 3: Crawling JAVBus')
            self.stdout.write('='*60)
            
            javbus_session_id = f"{main_session_id}_javbus"
            try:
                call_command(
                    'crawl_javbus',
                    pages=pages_per_source,
                    max_movies=movies_per_source,
                    delay=delay,
                    proxy=proxy,
                    session_id=javbus_session_id
                )
                crawl_results['javbus'] = 'success'
                self.stdout.write(self.style.SUCCESS('✅ JAVBus crawling completed'))
            except Exception as e:
                crawl_results['javbus'] = f'failed: {e}'
                self.stdout.write(self.style.ERROR(f'❌ JAVBus crawling failed: {e}'))
            
            # 等待间隔
            self.stdout.write('⏳ Waiting 30 seconds before magnet crawling...')
            time.sleep(30)
        
        # 4. 爬取磁力链接 (可选)
        if crawl_magnets:
            self.stdout.write('\n' + '='*60)
            self.stdout.write('🧲 Phase 4: Crawling Magnet Links')
            self.stdout.write('='*60)
            
            magnet_session_id = f"{main_session_id}_magnets"
            try:
                call_command(
                    'crawl_magnets',
                    max_movies=movies_per_source * 2,  # 为更多影片爬取磁力链接
                    source='all',
                    delay=delay,
                    proxy=proxy,
                    session_id=magnet_session_id
                )
                crawl_results['magnets'] = 'success'
                self.stdout.write(self.style.SUCCESS('✅ Magnet links crawling completed'))
            except Exception as e:
                crawl_results['magnets'] = f'failed: {e}'
                self.stdout.write(self.style.ERROR(f'❌ Magnet links crawling failed: {e}'))
        
        # 显示最终结果
        self.show_final_results(crawl_results, main_session_id)
    
    def show_initial_stats(self):
        """显示初始统计"""
        self.stdout.write('\n📊 Initial Database Statistics:')
        self.stdout.write('-' * 40)
        
        # 按来源统计影片
        sources = ['avmoo', 'javlibrary', 'javbus']
        for source in sources:
            count = Movie.objects.filter(source=source).count()
            self.stdout.write(f'{source.upper():<12}: {count:>6} movies')
        
        total_movies = Movie.objects.count()
        total_magnets = MagnetLink.objects.count()
        movies_with_magnets = Movie.objects.filter(magnets__isnull=False).distinct().count()
        
        self.stdout.write('-' * 40)
        self.stdout.write(f'{"TOTAL":<12}: {total_movies:>6} movies')
        self.stdout.write(f'{"MAGNETS":<12}: {total_magnets:>6} links')
        self.stdout.write(f'{"WITH MAGNETS":<12}: {movies_with_magnets:>6} movies')
    
    def show_final_results(self, crawl_results, main_session_id):
        """显示最终结果"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('🎉 COMPREHENSIVE CRAWLING COMPLETED')
        self.stdout.write('='*60)
        
        # 显示爬取结果
        self.stdout.write('\n📋 Crawling Results:')
        self.stdout.write('-' * 40)
        for source, result in crawl_results.items():
            status = '✅' if result == 'success' else '❌'
            self.stdout.write(f'{status} {source.upper():<12}: {result}')
        
        # 显示最终统计
        self.stdout.write('\n📊 Final Database Statistics:')
        self.stdout.write('-' * 40)
        
        sources = ['avmoo', 'javlibrary', 'javbus']
        total_new = 0
        
        for source in sources:
            count = Movie.objects.filter(source=source).count()
            self.stdout.write(f'{source.upper():<12}: {count:>6} movies')
        
        total_movies = Movie.objects.count()
        total_magnets = MagnetLink.objects.count()
        movies_with_magnets = Movie.objects.filter(magnets__isnull=False).distinct().count()
        
        self.stdout.write('-' * 40)
        self.stdout.write(f'{"TOTAL":<12}: {total_movies:>6} movies')
        self.stdout.write(f'{"MAGNETS":<12}: {total_magnets:>6} links')
        self.stdout.write(f'{"WITH MAGNETS":<12}: {movies_with_magnets:>6} movies')
        
        # 显示会话信息
        self.stdout.write('\n🔍 Session Information:')
        self.stdout.write('-' * 40)
        sessions = CrawlerSession.objects.filter(session_id__startswith=main_session_id.split('_')[0])
        for session in sessions:
            status_icon = {
                'completed': '✅',
                'failed': '❌',
                'paused': '⏸️',
                'running': '🔄'
            }.get(session.status, '❓')
            
            self.stdout.write(f'{status_icon} {session.session_id}: {session.processed_movies} movies processed')
        
        # 推荐下一步操作
        self.stdout.write('\n💡 Recommended Next Steps:')
        self.stdout.write('-' * 40)
        self.stdout.write('1. Review crawled data quality')
        self.stdout.write('2. Set up scheduled crawling:')
        self.stdout.write('   python manage.py schedule_crawler create --name="Daily Multi-Source" --crawler=avmoo --schedule=daily --time=02:00')
        self.stdout.write('3. Crawl magnet links for existing movies:')
        self.stdout.write('   python manage.py crawl_magnets --max-movies=100')
        self.stdout.write('4. Check for duplicate movies and clean data')
        
        self.stdout.write(f'\n🎯 Main Session ID: {main_session_id}')
        self.stdout.write('Use this ID to track related crawling sessions.')
        
        self.stdout.write('\n🚀 Multi-source crawling completed successfully!')
