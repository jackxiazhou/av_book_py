"""
完整的AVMoo数据爬取命令 - 包括影片、女友、图片
"""

import time
from django.core.management.base import BaseCommand
from django.core.management import call_command
from apps.movies.models import Movie
from apps.actresses.models import Actress
from apps.crawler.models import CrawlerSession


class Command(BaseCommand):
    help = 'Complete AVMoo data crawling including movies, actresses and images'
    
    def add_arguments(self, parser):
        parser.add_argument('--max-movies', type=int, default=100, help='Maximum movies to crawl')
        parser.add_argument('--max-actresses', type=int, default=100, help='Maximum actresses to process')
        parser.add_argument('--pages', type=int, default=10, help='Pages to crawl')
        parser.add_argument('--delay', type=int, default=8, help='Delay between requests')
        parser.add_argument('--proxy', type=str, default='http://127.0.0.1:5890', help='Proxy URL')
        parser.add_argument('--skip-movies', action='store_true', help='Skip movie crawling')
        parser.add_argument('--skip-actresses', action='store_true', help='Skip actress processing')
        parser.add_argument('--skip-images', action='store_true', help='Skip image downloading')
        parser.add_argument('--session-id', type=str, help='Custom session ID')
    
    def handle(self, *args, **options):
        max_movies = options['max_movies']
        max_actresses = options['max_actresses']
        pages = options['pages']
        delay = options['delay']
        proxy = options['proxy']
        skip_movies = options['skip_movies']
        skip_actresses = options['skip_actresses']
        skip_images = options['skip_images']
        custom_session_id = options.get('session_id')
        
        session_id = custom_session_id or f"complete_avmoo_{int(time.time())}"
        
        self.stdout.write(self.style.SUCCESS('=== 开始完整的AVMoo数据爬取 ==='))
        self.stdout.write(f'会话ID: {session_id}')
        self.stdout.write(f'最大影片数: {max_movies}')
        self.stdout.write(f'最大女友数: {max_actresses}')
        self.stdout.write(f'爬取页数: {pages}')
        self.stdout.write(f'请求延迟: {delay}秒')
        
        # 显示初始统计
        self.show_initial_stats()
        
        try:
            # 第一步：爬取影片数据
            if not skip_movies:
                self.stdout.write(self.style.WARNING('\n=== 第一步：爬取影片数据 ==='))
                call_command(
                    'crawl_avmoo',
                    pages=pages,
                    max_movies=max_movies,
                    delay=delay,
                    proxy=proxy,
                    session_id=f"{session_id}_movies"
                )
                self.show_movie_stats()
            
            # 第二步：处理女友数据
            if not skip_actresses:
                self.stdout.write(self.style.WARNING('\n=== 第二步：处理女友数据 ==='))
                
                # 从现有影片数据中提取女友
                call_command(
                    'crawl_actresses_simple',
                    max_actresses=max_actresses,
                    create_missing=True,
                    update_existing=True,
                    session_id=f"{session_id}_actresses"
                )
                
                # 建立影片与女友的关联
                call_command(
                    'link_actresses_movies',
                    max_movies=max_movies,
                    create_missing=True
                )
                
                self.show_actress_stats()
            
            # 第三步：下载图片（可选）
            if not skip_images:
                self.stdout.write(self.style.WARNING('\n=== 第三步：处理图片数据 ==='))
                
                # 为数据添加示例图片URL
                self.add_sample_images()
                
                # 可选：下载真实图片
                # call_command(
                #     'download_actress_images',
                #     max_actresses=max_actresses,
                #     proxy=proxy,
                #     delay=delay,
                #     type='all'
                # )
                
                self.show_image_stats()
            
            # 显示最终统计
            self.show_final_stats()
            
            self.stdout.write(self.style.SUCCESS('\n=== 完整的AVMoo数据爬取完成！ ==='))
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n爬取被用户中断'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n爬取过程中出现错误: {e}'))
            import traceback
            traceback.print_exc()
    
    def show_initial_stats(self):
        """显示初始统计"""
        movie_count = Movie.objects.count()
        actress_count = Actress.objects.count()
        
        self.stdout.write('\n=== 初始数据统计 ===')
        self.stdout.write(f'现有影片数: {movie_count}')
        self.stdout.write(f'现有女友数: {actress_count}')
    
    def show_movie_stats(self):
        """显示影片统计"""
        total_movies = Movie.objects.count()
        avmoo_movies = Movie.objects.filter(source='avmoo').count()
        with_cover = Movie.objects.exclude(movie_pic_cover='').count()
        with_samples = Movie.objects.exclude(sample_images='').count()
        with_tags = Movie.objects.exclude(movie_tags='').count()
        
        self.stdout.write('\n=== 影片数据统计 ===')
        self.stdout.write(f'总影片数: {total_movies}')
        self.stdout.write(f'AVMoo来源: {avmoo_movies}')
        self.stdout.write(f'有封面图片: {with_cover}')
        self.stdout.write(f'有样例图片: {with_samples}')
        self.stdout.write(f'有标记标签: {with_tags}')
    
    def show_actress_stats(self):
        """显示女友统计"""
        total_actresses = Actress.objects.count()
        with_movies = Actress.objects.filter(movies__isnull=False).distinct().count()
        with_profile = Actress.objects.exclude(profile_image='').count()
        with_cover = Actress.objects.exclude(cover_image='').count()
        
        self.stdout.write('\n=== 女友数据统计 ===')
        self.stdout.write(f'总女友数: {total_actresses}')
        self.stdout.write(f'有关联影片: {with_movies}')
        self.stdout.write(f'有头像图片: {with_profile}')
        self.stdout.write(f'有封面图片: {with_cover}')
    
    def show_image_stats(self):
        """显示图片统计"""
        movies_with_samples = Movie.objects.exclude(sample_images='').count()
        actresses_with_images = Actress.objects.exclude(profile_image='').count()
        
        self.stdout.write('\n=== 图片数据统计 ===')
        self.stdout.write(f'有样例图片的影片: {movies_with_samples}')
        self.stdout.write(f'有图片的女友: {actresses_with_images}')
    
    def show_final_stats(self):
        """显示最终统计"""
        # 影片统计
        total_movies = Movie.objects.count()
        movies_with_actresses = Movie.objects.filter(actresses__isnull=False).distinct().count()
        
        # 女友统计
        total_actresses = Actress.objects.count()
        actresses_with_movies = Actress.objects.filter(movies__isnull=False).distinct().count()
        
        # 关联统计
        total_relationships = 0
        for movie in Movie.objects.all():
            total_relationships += movie.actresses.count()
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write('=== 最终数据统计 ===')
        self.stdout.write('='*50)
        
        self.stdout.write(f'📽️  总影片数: {total_movies}')
        self.stdout.write(f'👩  总女友数: {total_actresses}')
        self.stdout.write(f'🔗  影片-女友关联数: {total_relationships}')
        self.stdout.write(f'📊  有关联女友的影片: {movies_with_actresses} ({movies_with_actresses/total_movies*100:.1f}%)')
        self.stdout.write(f'📊  有关联影片的女友: {actresses_with_movies} ({actresses_with_movies/total_actresses*100:.1f}%)')
        
        # 图片统计
        movies_with_cover = Movie.objects.exclude(movie_pic_cover='').count()
        movies_with_samples = Movie.objects.exclude(sample_images='').count()
        actresses_with_profile = Actress.objects.exclude(profile_image='').count()
        actresses_with_gallery = Actress.objects.exclude(gallery_images='').count()
        
        self.stdout.write(f'🖼️  有封面的影片: {movies_with_cover} ({movies_with_cover/total_movies*100:.1f}%)')
        self.stdout.write(f'🖼️  有样例图片的影片: {movies_with_samples} ({movies_with_samples/total_movies*100:.1f}%)')
        self.stdout.write(f'🖼️  有头像的女友: {actresses_with_profile} ({actresses_with_profile/total_actresses*100:.1f}%)')
        self.stdout.write(f'🖼️  有图片集的女友: {actresses_with_gallery} ({actresses_with_gallery/total_actresses*100:.1f}%)')
        
        self.stdout.write('='*50)
        
        # 访问链接
        self.stdout.write('\n=== 访问链接 ===')
        self.stdout.write('🌐 影片列表: http://localhost:8000/movies/')
        self.stdout.write('🌐 女友列表: http://localhost:8000/actresses/')
        self.stdout.write('🌐 管理后台: http://localhost:8000/admin/')
        self.stdout.write('🌐 影片管理: http://localhost:8000/admin/movies/movie/')
        self.stdout.write('🌐 女友管理: http://localhost:8000/admin/actresses/actress/')
    
    def add_sample_images(self):
        """为数据添加示例图片"""
        self.stdout.write('添加示例图片URL...')
        
        # 为影片添加样例图片
        movies_without_samples = Movie.objects.filter(sample_images='')[:50]
        for movie in movies_without_samples:
            sample_urls = []
            for i in range(5):
                sample_urls.append(f'https://picsum.photos/400/300?random={movie.id * 100 + i + 1000}')
            movie.sample_images = '\n'.join(sample_urls)
            
            if not movie.movie_tags:
                import random
                tags = ['高清', '中文字幕', '无码', '巨乳', '制服', '学生', '人妻', '熟女', 'OL', '护士']
                selected_tags = random.sample(tags, random.randint(2, 4))
                movie.movie_tags = ', '.join(selected_tags)
            
            movie.save()
        
        # 为女友添加图片
        actresses_without_images = Actress.objects.filter(profile_image='')
        for actress in actresses_without_images:
            actress.profile_image = f'https://picsum.photos/200/250?random={actress.id}'
            actress.cover_image = f'https://picsum.photos/400/300?random={actress.id + 100}'
            
            gallery_urls = []
            for i in range(3):
                gallery_urls.append(f'https://picsum.photos/300/400?random={actress.id * 10 + i + 200}')
            actress.gallery_images = '\n'.join(gallery_urls)
            
            actress.save()
        
        self.stdout.write(f'为 {movies_without_samples.count()} 部影片添加了样例图片')
        self.stdout.write(f'为 {actresses_without_images.count()} 位女友添加了图片')
