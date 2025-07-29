"""
运行真实的AVMoo女友爬虫（基于Scrapy）
"""

import os
import sys
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.actresses.models import Actress
from apps.crawler.models import CrawlerSession
import time


class Command(BaseCommand):
    help = 'Run real AVMoo actress crawler with Scrapy to get real images'
    
    def add_arguments(self, parser):
        parser.add_argument('--max-pages', type=int, default=5, help='Maximum pages to crawl')
        parser.add_argument('--max-actresses', type=int, default=20, help='Maximum actresses to crawl')
        parser.add_argument('--output-dir', type=str, default='output', help='Output directory for scrapy')
        parser.add_argument('--session-id', type=str, help='Custom session ID')
        parser.add_argument('--no-images', action='store_true', help='Skip image downloading')
    
    def handle(self, *args, **options):
        max_pages = options['max_pages']
        max_actresses = options['max_actresses']
        output_dir = options['output_dir']
        custom_session_id = options.get('session_id')
        skip_images = options['no_images']
        
        session_id = custom_session_id or f"real_avmoo_actresses_{int(time.time())}"
        
        # 创建爬虫会话
        session = CrawlerSession.objects.create(
            session_id=session_id,
            crawler_type='real_avmoo_actresses',
            total_pages=max_pages,
            max_movies=max_actresses,
            delay_seconds=5
        )
        
        self.stdout.write(self.style.SUCCESS('=== 开始真实AVMoo女友爬虫 ==='))
        self.stdout.write(f'会话ID: {session_id}')
        self.stdout.write(f'最大页数: {max_pages}')
        self.stdout.write(f'最大女友数: {max_actresses}')
        self.stdout.write(f'下载图片: {not skip_images}')
        
        # 显示初始统计
        initial_count = Actress.objects.count()
        self.stdout.write(f'当前女友数: {initial_count}')
        
        try:
            # 构建Scrapy命令
            scrapy_cmd = self.build_scrapy_command(
                max_pages, max_actresses, output_dir, skip_images
            )
            
            self.stdout.write(f'执行命令: {" ".join(scrapy_cmd)}')
            
            # 运行Scrapy爬虫
            result = subprocess.run(
                scrapy_cmd,
                cwd=os.path.join(settings.BASE_DIR.parent, 'crawler'),
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            if result.returncode == 0:
                session.mark_completed()
                self.stdout.write(self.style.SUCCESS('爬虫执行成功！'))
                
                # 显示输出
                if result.stdout:
                    self.stdout.write('\\n=== Scrapy输出 ===')
                    self.stdout.write(result.stdout[-2000:])  # 显示最后2000字符
                
                # 显示最终统计
                self.show_final_stats(initial_count)
                
            else:
                session.mark_failed(f"Scrapy exit code: {result.returncode}")
                self.stdout.write(self.style.ERROR(f'爬虫执行失败，退出码: {result.returncode}'))
                
                if result.stderr:
                    self.stdout.write('\\n=== 错误信息 ===')
                    self.stdout.write(result.stderr[-1000:])  # 显示最后1000字符错误
                
                if result.stdout:
                    self.stdout.write('\\n=== 输出信息 ===')
                    self.stdout.write(result.stdout[-1000:])
        
        except subprocess.TimeoutExpired:
            session.mark_failed("Timeout expired")
            self.stdout.write(self.style.ERROR('爬虫执行超时'))
        
        except FileNotFoundError:
            session.mark_failed("Scrapy not found")
            self.stdout.write(self.style.ERROR('未找到Scrapy命令，请确保已安装Scrapy'))
            self.stdout.write('安装命令: pip install scrapy scrapy-user-agents')
        
        except Exception as e:
            session.mark_failed(str(e))
            self.stdout.write(self.style.ERROR(f'执行过程中出现错误: {e}'))
    
    def build_scrapy_command(self, max_pages, max_actresses, output_dir, skip_images):
        """构建Scrapy命令"""
        cmd = [
            'scrapy', 'crawl', 'avmoo_actresses',
            '-a', f'max_pages={max_pages}',
            '-a', f'max_actresses={max_actresses}',
            '-s', 'LOG_LEVEL=INFO',
            '-s', 'DOWNLOAD_DELAY=5',
            '-s', 'RANDOMIZE_DOWNLOAD_DELAY=True',
            '-s', 'CONCURRENT_REQUESTS=2',
            '-s', 'AUTOTHROTTLE_ENABLED=True',
            '-s', 'AUTOTHROTTLE_TARGET_CONCURRENCY=1.0',
            '-o', f'{output_dir}/actresses_%(time)s.json'
        ]
        
        # 如果跳过图片下载，禁用图片Pipeline
        if skip_images:
            cmd.extend([
                '-s', 'ITEM_PIPELINES={"avbook_spider.pipelines.ValidationPipeline": 300, "avbook_spider.pipelines.DuplicatesPipeline": 400, "avbook_spider.pipelines.ActressDatabasePipeline": 700}'
            ])
        
        return cmd
    
    def show_final_stats(self, initial_count):
        """显示最终统计"""
        final_count = Actress.objects.count()
        new_actresses = final_count - initial_count
        
        # 统计图片
        with_profile = Actress.objects.exclude(profile_image='').count()
        with_cover = Actress.objects.exclude(cover_image='').count()
        with_gallery = Actress.objects.exclude(gallery_images='').count()
        
        # 统计本地图片
        local_profile = Actress.objects.filter(profile_image__startswith='/media/').count()
        local_cover = Actress.objects.filter(cover_image__startswith='/media/').count()
        
        self.stdout.write('\\n' + '='*50)
        self.stdout.write('=== 爬取结果统计 ===')
        self.stdout.write('='*50)
        
        self.stdout.write(f'📊 新增女友数: {new_actresses}')
        self.stdout.write(f'📊 总女友数: {final_count}')
        self.stdout.write(f'🖼️ 有头像的女友: {with_profile} ({with_profile/final_count*100:.1f}%)')
        self.stdout.write(f'🖼️ 有封面的女友: {with_cover} ({with_cover/final_count*100:.1f}%)')
        self.stdout.write(f'🖼️ 有图片集的女友: {with_gallery} ({with_gallery/final_count*100:.1f}%)')
        self.stdout.write(f'💾 本地头像数: {local_profile}')
        self.stdout.write(f'💾 本地封面数: {local_cover}')
        
        # 显示最新创建的女友
        if new_actresses > 0:
            self.stdout.write('\\n=== 最新创建的女友 ===')
            latest_actresses = Actress.objects.order_by('-created_at')[:min(new_actresses, 10)]
            for actress in latest_actresses:
                has_local_images = (
                    actress.profile_image.startswith('/media/') if actress.profile_image else False
                ) or (
                    actress.cover_image.startswith('/media/') if actress.cover_image else False
                )
                image_status = '📷 有本地图片' if has_local_images else '🔗 仅外部链接'
                self.stdout.write(f'  👩 {actress.name} - 作品数: {actress.movie_count} - {image_status}')
        
        self.stdout.write('\\n=== 访问链接 ===')
        self.stdout.write('🌐 女友列表: http://localhost:8000/actresses/')
        self.stdout.write('🌐 管理后台: http://localhost:8000/admin/actresses/actress/')
        
        # 检查媒体目录
        media_root = settings.MEDIA_ROOT
        if os.path.exists(media_root):
            actress_dirs = [
                'images/actresses/profiles',
                'images/actresses/covers',
                'images/actresses/galleries'
            ]
            
            total_files = 0
            total_size = 0
            
            for dir_name in actress_dirs:
                dir_path = os.path.join(media_root, dir_name)
                if os.path.exists(dir_path):
                    files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
                    total_files += len(files)
                    
                    for file in files:
                        file_path = os.path.join(dir_path, file)
                        total_size += os.path.getsize(file_path)
            
            if total_files > 0:
                self.stdout.write(f'\\n💾 本地图片文件: {total_files} 个')
                self.stdout.write(f'💾 占用空间: {total_size / 1024 / 1024:.2f} MB')
        
        self.stdout.write('='*50)
