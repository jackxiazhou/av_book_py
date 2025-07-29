"""
Django管理命令 - 运行完整女友爬虫
"""

import os
import sys
import subprocess
import time
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from apps.crawler.models import CrawlTask
from datetime import datetime


class Command(BaseCommand):
    help = '运行AVMoo完整女友爬虫 - 爬取女友列表、详情、作品关联'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-pages',
            type=int,
            default=5,
            help='最大爬取页数 (默认: 5)'
        )
        parser.add_argument(
            '--max-actresses',
            type=int,
            default=50,
            help='最大女友数量 (默认: 50)'
        )
        parser.add_argument(
            '--output',
            type=str,
            default='actresses_complete.json',
            help='输出文件名 (默认: actresses_complete.json)'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=3,
            help='请求延时秒数 (默认: 3)'
        )
        parser.add_argument(
            '--concurrent',
            type=int,
            default=2,
            help='并发请求数 (默认: 2)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='试运行模式，不实际执行爬虫'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='详细输出模式'
        )

    def handle(self, *args, **options):
        max_pages = options['max_pages']
        max_actresses = options['max_actresses']
        output_file = options['output']
        delay = options['delay']
        concurrent = options['concurrent']
        dry_run = options['dry_run']
        verbose = options['verbose']

        self.stdout.write(
            self.style.SUCCESS('🕷️ 启动AVMoo完整女友爬虫')
        )
        
        # 显示配置信息
        self.stdout.write(f"📋 爬虫配置:")
        self.stdout.write(f"   • 最大页数: {max_pages}")
        self.stdout.write(f"   • 最大女友数: {max_actresses}")
        self.stdout.write(f"   • 输出文件: {output_file}")
        self.stdout.write(f"   • 请求延时: {delay}秒")
        self.stdout.write(f"   • 并发数: {concurrent}")
        self.stdout.write(f"   • 试运行: {'是' if dry_run else '否'}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 试运行模式 - 不会实际执行爬虫')
            )
            return

        # 创建爬虫任务记录
        task = CrawlTask.objects.create(
            spider_name='avmoo_actresses_complete',
            status='running',
            start_time=datetime.now(),
            config={
                'max_pages': max_pages,
                'max_actresses': max_actresses,
                'delay': delay,
                'concurrent': concurrent,
                'output_file': output_file
            }
        )

        try:
            # 构建爬虫命令
            crawler_dir = os.path.join(settings.BASE_DIR, '..', 'crawler')
            output_path = os.path.join(crawler_dir, 'output', output_file)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            cmd = [
                'scrapy', 'crawl', 'avmoo_actresses_complete',
                '-a', f'max_pages={max_pages}',
                '-a', f'max_actresses={max_actresses}',
                '-s', f'DOWNLOAD_DELAY={delay}',
                '-s', f'CONCURRENT_REQUESTS={concurrent}',
                '-o', output_path,
                '-L', 'INFO' if verbose else 'WARNING'
            ]

            self.stdout.write(f"🚀 执行命令: {' '.join(cmd)}")
            self.stdout.write(f"📁 工作目录: {crawler_dir}")
            self.stdout.write(f"📄 输出文件: {output_path}")

            # 执行爬虫
            start_time = time.time()
            
            process = subprocess.Popen(
                cmd,
                cwd=crawler_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )

            # 实时输出日志
            for line in iter(process.stdout.readline, ''):
                if verbose:
                    self.stdout.write(line.rstrip())
                elif any(keyword in line for keyword in ['ERROR', 'WARNING', 'INFO']):
                    self.stdout.write(line.rstrip())

            process.wait()
            end_time = time.time()
            duration = end_time - start_time

            # 更新任务状态
            if process.returncode == 0:
                task.status = 'completed'
                task.end_time = datetime.now()
                task.duration = duration
                task.save()

                self.stdout.write(
                    self.style.SUCCESS(f'✅ 爬虫执行完成! 耗时: {duration:.2f}秒')
                )
                
                # 检查输出文件
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    self.stdout.write(f"📄 输出文件大小: {file_size} 字节")
                    
                    # 简单统计
                    try:
                        import json
                        with open(output_path, 'r', encoding='utf-8') as f:
                            data = [json.loads(line) for line in f if line.strip()]
                        
                        actresses = [item for item in data if item.get('data_type') == 'actress']
                        movies = [item for item in data if item.get('data_type') == 'movie']
                        
                        self.stdout.write(f"👩 爬取女友数量: {len(actresses)}")
                        self.stdout.write(f"🎬 爬取作品数量: {len(movies)}")
                        
                        task.result = {
                            'actresses_count': len(actresses),
                            'movies_count': len(movies),
                            'total_items': len(data)
                        }
                        task.save()
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️ 统计数据时出错: {e}')
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING('⚠️ 输出文件不存在')
                    )

            else:
                task.status = 'failed'
                task.end_time = datetime.now()
                task.duration = duration
                task.error_message = f'爬虫进程退出码: {process.returncode}'
                task.save()

                raise CommandError(f'❌ 爬虫执行失败! 退出码: {process.returncode}')

        except KeyboardInterrupt:
            task.status = 'cancelled'
            task.end_time = datetime.now()
            task.save()
            
            self.stdout.write(
                self.style.WARNING('⏹️ 爬虫被用户中断')
            )
            
        except Exception as e:
            task.status = 'failed'
            task.end_time = datetime.now()
            task.error_message = str(e)
            task.save()
            
            raise CommandError(f'❌ 爬虫执行出错: {e}')

        finally:
            self.stdout.write(f"📊 任务ID: {task.id}")
            self.stdout.write(f"📈 任务状态: {task.status}")


class ActressesCompleteSpiderRunner:
    """女友爬虫运行器"""
    
    def __init__(self, max_pages=5, max_actresses=50, delay=3, concurrent=2):
        self.max_pages = max_pages
        self.max_actresses = max_actresses
        self.delay = delay
        self.concurrent = concurrent
    
    def run(self, output_file='actresses_complete.json'):
        """运行爬虫"""
        from django.core.management import call_command
        
        call_command(
            'crawl_actresses_complete',
            max_pages=self.max_pages,
            max_actresses=self.max_actresses,
            output=output_file,
            delay=self.delay,
            concurrent=self.concurrent,
            verbose=True
        )
    
    def run_async(self, output_file='actresses_complete.json'):
        """异步运行爬虫"""
        from celery import current_app
        
        # 如果有Celery，使用异步任务
        if hasattr(current_app, 'send_task'):
            return current_app.send_task(
                'apps.crawler.tasks.run_actresses_complete_spider',
                args=[self.max_pages, self.max_actresses, output_file, self.delay, self.concurrent]
            )
        else:
            # 否则同步运行
            return self.run(output_file)


def run_actresses_complete_spider(max_pages=5, max_actresses=50, output_file='actresses_complete.json'):
    """便捷函数 - 运行完整女友爬虫"""
    runner = ActressesCompleteSpiderRunner(max_pages, max_actresses)
    return runner.run(output_file)
