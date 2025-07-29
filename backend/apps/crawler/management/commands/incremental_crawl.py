"""
Django管理命令 - 增量更新和定时爬取
"""

import time
from django.core.management.base import BaseCommand
from django.core.management import call_command
from apps.actresses.models import Actress
from apps.movies.models import Movie
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta, datetime
import json
import os


class Command(BaseCommand):
    help = '增量更新和定时爬取'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            choices=['discover', 'update', 'new', 'maintenance', 'full'],
            default='update',
            help='运行模式'
        )
        parser.add_argument(
            '--max-actresses',
            type=int,
            default=20,
            help='最大处理女友数'
        )
        parser.add_argument(
            '--schedule',
            action='store_true',
            help='启用定时调度模式'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=3600,
            help='定时间隔（秒），默认1小时'
        )

    def handle(self, *args, **options):
        mode = options['mode']
        max_actresses = options['max_actresses']
        schedule = options['schedule']
        interval = options['interval']

        self.stdout.write(
            self.style.SUCCESS(f'🔄 启动增量爬取 (模式: {mode})')
        )

        if schedule:
            self.run_scheduled(mode, max_actresses, interval)
        else:
            self.run_once(mode, max_actresses)

    def run_scheduled(self, mode, max_actresses, interval):
        """定时调度运行"""
        self.stdout.write(f'⏰ 启动定时调度，间隔: {interval} 秒')
        
        while True:
            try:
                self.stdout.write(f'\n🕐 {timezone.now()} - 开始定时任务')
                self.run_once(mode, max_actresses)
                
                self.stdout.write(f'⏱️ 等待 {interval} 秒...')
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.stdout.write('\n⏹️ 用户中断，停止定时调度')
                break
            except Exception as e:
                self.stdout.write(f'❌ 定时任务出错: {e}')
                time.sleep(60)  # 出错后等待1分钟

    def run_once(self, mode, max_actresses):
        """运行一次增量更新"""
        start_time = timezone.now()
        
        if mode == 'discover':
            self.run_discover_mode()
        elif mode == 'update':
            self.run_update_mode(max_actresses)
        elif mode == 'new':
            self.run_new_mode(max_actresses)
        elif mode == 'maintenance':
            self.run_maintenance_mode()
        elif mode == 'full':
            self.run_full_mode(max_actresses)
        
        duration = timezone.now() - start_time
        self.stdout.write(f'✅ 增量更新完成，耗时: {duration}')

    def run_discover_mode(self):
        """发现模式：发现新女友"""
        self.stdout.write('🔍 运行发现模式')
        
        try:
            call_command(
                'discover_actresses',
                max_pages=5,
                delay=3,
                save_urls=True,
                verbosity=1
            )
        except Exception as e:
            self.stdout.write(f'❌ 发现模式失败: {e}')

    def run_update_mode(self, max_actresses):
        """更新模式：更新现有女友信息"""
        self.stdout.write('🔄 运行更新模式')
        
        # 找到需要更新的女友
        week_ago = timezone.now() - timedelta(days=7)
        actresses_to_update = Actress.objects.filter(
            Q(last_crawled_at__lt=week_ago) |
            Q(last_crawled_at__isnull=True)
        ).order_by('last_crawled_at')[:max_actresses]
        
        if not actresses_to_update:
            self.stdout.write('ℹ️ 没有需要更新的女友')
            return
        
        self.stdout.write(f'📋 找到 {len(actresses_to_update)} 个需要更新的女友')
        
        try:
            call_command(
                'batch_crawl_actresses',
                max_actresses=len(actresses_to_update),
                mode='update',
                priority='random',
                continue_on_error=True,
                verbosity=1
            )
        except Exception as e:
            self.stdout.write(f'❌ 更新模式失败: {e}')

    def run_new_mode(self, max_actresses):
        """新增模式：爬取新女友"""
        self.stdout.write('🆕 运行新增模式')
        
        # 找到未爬取的女友
        new_actresses = Actress.objects.filter(
            Q(birth_date__isnull=True) &
            Q(height__isnull=True) &
            Q(cup_size__isnull=True)
        )[:max_actresses]
        
        if not new_actresses:
            self.stdout.write('ℹ️ 没有新女友需要爬取')
            return
        
        self.stdout.write(f'📋 找到 {len(new_actresses)} 个新女友')
        
        try:
            call_command(
                'batch_crawl_actresses',
                max_actresses=len(new_actresses),
                mode='new',
                priority='random',
                continue_on_error=True,
                verbosity=1
            )
        except Exception as e:
            self.stdout.write(f'❌ 新增模式失败: {e}')

    def run_maintenance_mode(self):
        """维护模式：数据清理和统计"""
        self.stdout.write('🔧 运行维护模式')
        
        # 清理重复数据
        self.clean_duplicate_data()
        
        # 更新统计信息
        self.update_statistics()
        
        # 生成报告
        self.generate_report()

    def run_full_mode(self, max_actresses):
        """完整模式：发现 + 新增 + 更新"""
        self.stdout.write('🚀 运行完整模式')
        
        # 1. 发现新女友
        self.run_discover_mode()
        time.sleep(30)
        
        # 2. 爬取新女友
        self.run_new_mode(max_actresses // 2)
        time.sleep(30)
        
        # 3. 更新现有女友
        self.run_update_mode(max_actresses // 2)
        time.sleep(30)
        
        # 4. 维护
        self.run_maintenance_mode()

    def clean_duplicate_data(self):
        """清理重复数据"""
        self.stdout.write('🧹 清理重复数据')
        
        # 清理重复女友
        duplicate_actresses = Actress.objects.values('name').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        for dup in duplicate_actresses:
            actresses = Actress.objects.filter(name=dup['name']).order_by('id')
            # 保留第一个，删除其他
            for actress in actresses[1:]:
                self.stdout.write(f'  删除重复女友: {actress.name} (ID: {actress.id})')
                actress.delete()
        
        # 清理重复作品
        duplicate_movies = Movie.objects.values('censored_id').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        for dup in duplicate_movies:
            movies = Movie.objects.filter(censored_id=dup['censored_id']).order_by('id')
            # 保留第一个，删除其他
            for movie in movies[1:]:
                self.stdout.write(f'  删除重复作品: {movie.censored_id} (ID: {movie.id})')
                movie.delete()

    def update_statistics(self):
        """更新统计信息"""
        self.stdout.write('📊 更新统计信息')
        
        stats = {
            'total_actresses': Actress.objects.count(),
            'complete_actresses': Actress.objects.filter(
                birth_date__isnull=False,
                height__isnull=False,
                cup_size__isnull=False
            ).count(),
            'actresses_with_images': Actress.objects.exclude(
                Q(profile_image__isnull=True) | Q(profile_image='')
            ).count(),
            'total_movies': Movie.objects.count(),
            'movies_with_covers': Movie.objects.exclude(
                Q(cover_image__isnull=True) | Q(cover_image='')
            ).count(),
            'last_updated': timezone.now().isoformat()
        }
        
        # 保存统计信息
        stats_file = 'crawl_statistics.json'
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        self.stdout.write(f'  统计信息已保存到: {stats_file}')

    def generate_report(self):
        """生成爬取报告"""
        self.stdout.write('📋 生成爬取报告')
        
        # 最近爬取的女友
        recent_actresses = Actress.objects.filter(
            last_crawled_at__gte=timezone.now() - timedelta(days=1)
        ).order_by('-last_crawled_at')[:10]
        
        # 最近添加的作品
        recent_movies = Movie.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=1)
        ).order_by('-created_at')[:10]
        
        report = {
            'generated_at': timezone.now().isoformat(),
            'recent_actresses': [
                {
                    'name': a.name,
                    'crawled_at': a.last_crawled_at.isoformat() if a.last_crawled_at else None
                }
                for a in recent_actresses
            ],
            'recent_movies': [
                {
                    'censored_id': m.censored_id,
                    'title': m.movie_title,
                    'created_at': m.created_at.isoformat() if hasattr(m, 'created_at') else None
                }
                for m in recent_movies
            ]
        }
        
        report_file = f'crawl_report_{timezone.now().strftime("%Y%m%d")}.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        self.stdout.write(f'  报告已保存到: {report_file}')

    def get_crawl_priority(self):
        """获取爬取优先级建议"""
        # 分析当前数据状态，给出爬取建议
        total_actresses = Actress.objects.count()
        complete_actresses = Actress.objects.filter(
            birth_date__isnull=False,
            height__isnull=False,
            cup_size__isnull=False
        ).count()
        
        completion_rate = complete_actresses / max(total_actresses, 1) * 100
        
        if completion_rate < 30:
            return 'new'  # 优先爬取新女友
        elif completion_rate < 70:
            return 'update'  # 平衡新增和更新
        else:
            return 'maintenance'  # 主要进行维护

    def should_run_deep_crawl(self):
        """判断是否应该运行深度爬取"""
        # 如果女友网络连接度较低，建议运行深度爬取
        actresses_with_movies = Actress.objects.filter(
            movies__isnull=False
        ).distinct().count()
        
        total_actresses = Actress.objects.count()
        connection_rate = actresses_with_movies / max(total_actresses, 1) * 100
        
        return connection_rate < 50  # 连接度低于50%时建议深度爬取
