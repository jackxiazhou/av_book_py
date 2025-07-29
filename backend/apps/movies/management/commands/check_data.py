"""
Django management command to check crawled data.
"""

from django.core.management.base import BaseCommand
from apps.movies.models import Movie
from apps.magnets.models import MagnetLink


class Command(BaseCommand):
    help = 'Check crawled data statistics'
    
    def handle(self, *args, **options):
        total_movies = Movie.objects.count()
        total_magnets = MagnetLink.objects.count()
        
        self.stdout.write(f'=== 数据库统计 ===')
        self.stdout.write(f'总影片数: {total_movies}')
        self.stdout.write(f'总磁力链接: {total_magnets}')
        
        # 按来源统计
        sources = Movie.objects.values_list('source', flat=True).distinct()
        self.stdout.write(f'\n=== 按来源统计 ===')
        for source in sources:
            count = Movie.objects.filter(source=source).count()
            self.stdout.write(f'{source}: {count} 部影片')
        
        # 最新的5部影片
        self.stdout.write(f'\n=== 最新影片 ===')
        recent_movies = Movie.objects.order_by('-created_at')[:5]
        for movie in recent_movies:
            magnet_count = movie.magnets.count()
            self.stdout.write(f'{movie.censored_id}: {movie.movie_title} ({magnet_count} 个磁力)')
        
        # 磁力链接统计
        self.stdout.write(f'\n=== 磁力链接统计 ===')
        qualities = MagnetLink.objects.values_list('quality', flat=True).distinct()
        for quality in qualities:
            count = MagnetLink.objects.filter(quality=quality).count()
            self.stdout.write(f'{quality.upper()}: {count} 个')
        
        # 有字幕的磁力链接
        subtitle_count = MagnetLink.objects.filter(has_subtitle=True).count()
        self.stdout.write(f'有字幕: {subtitle_count} 个')
        
        self.stdout.write(f'\n=== 检查完成 ===')
        self.stdout.write(
            self.style.SUCCESS(f'数据库中共有 {total_movies} 部影片和 {total_magnets} 个磁力链接')
        )
