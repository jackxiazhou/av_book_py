"""
Django管理命令 - 批量下载作品图片
"""

import requests
import os
import time
import random
from urllib.parse import urlparse
from django.core.management.base import BaseCommand
from apps.movies.models import Movie
from django.conf import settings
from django.db import transaction
import hashlib


class Command(BaseCommand):
    help = '批量下载作品图片'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-movies',
            type=int,
            default=50,
            help='最大处理作品数量 (默认: 50)'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=2,
            help='下载延迟（秒）'
        )
        parser.add_argument(
            '--movie-id',
            type=str,
            help='指定作品番号'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='覆盖已存在的文件'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='试运行，不实际下载'
        )

    def handle(self, *args, **options):
        max_movies = options['max_movies']
        delay = options['delay']
        movie_id = options.get('movie_id')
        overwrite = options['overwrite']
        dry_run = options['dry_run']

        self.stdout.write(
            self.style.SUCCESS('📥 开始批量下载作品图片')
        )

        # 初始化
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

        # 创建媒体目录
        self.ensure_media_directories()

        # 获取要处理的作品
        movies = self.get_movies_to_process(movie_id, max_movies)
        
        if not movies:
            self.stdout.write(
                self.style.WARNING('❌ 没有找到符合条件的作品')
            )
            return

        self.stdout.write(f'📋 找到 {len(movies)} 个作品需要下载图片')

        if dry_run:
            self.stdout.write(
                self.style.WARNING('🧪 试运行模式，显示待下载作品:')
            )
            for i, movie in enumerate(movies, 1):
                self.stdout.write(f'  {i}. {movie.censored_id} - {movie.movie_title}')
            return

        # 开始下载
        success_count = 0
        error_count = 0
        total_images = 0

        for i, movie in enumerate(movies, 1):
            self.stdout.write(f'\n🎬 [{i}/{len(movies)}] 处理作品: {movie.censored_id}')
            
            try:
                images_count = self.download_movie_images(movie, overwrite, delay)
                
                if images_count > 0:
                    success_count += 1
                    total_images += images_count
                    self.stdout.write(f'  ✅ 下载成功: {images_count} 张图片')
                else:
                    self.stdout.write(f'  ℹ️ 没有新图片需要下载')

            except Exception as e:
                error_count += 1
                self.stdout.write(f'  ❌ 下载失败: {e}')

            # 作品间延迟
            if i < len(movies):
                delay_time = delay + random.uniform(0, 1)
                time.sleep(delay_time)

        # 统计结果
        self.stdout.write(f'\n🎉 下载完成!')
        self.stdout.write(f'📊 统计结果:')
        self.stdout.write(f'  成功作品: {success_count}')
        self.stdout.write(f'  失败作品: {error_count}')
        self.stdout.write(f'  总图片数: {total_images}')

    def get_movies_to_process(self, movie_id, max_count):
        """获取要处理的作品列表"""
        if movie_id:
            # 指定作品
            movies = Movie.objects.filter(censored_id__icontains=movie_id)
        else:
            # 优先处理有在线图片但没有本地图片的作品
            movies = Movie.objects.exclude(
                cover_image__isnull=True
            ).exclude(
                cover_image=''
            ).filter(
                cover_image_local__isnull=True
            )
            
            # 如果没有，则处理所有有在线图片的作品
            if not movies.exists():
                movies = Movie.objects.exclude(
                    cover_image__isnull=True
                ).exclude(
                    cover_image=''
                )

        return list(movies[:max_count])

    def download_movie_images(self, movie, overwrite, delay):
        """下载单个作品的图片"""
        images_downloaded = 0
        
        # 下载封面图片
        if movie.cover_image:
            if not movie.cover_image_local or overwrite:
                self.stdout.write(f'    📸 下载封面图片')
                local_path = self.download_image(
                    movie.cover_image, 
                    'cover', 
                    movie.censored_id
                )
                if local_path:
                    movie.cover_image_local = local_path
                    images_downloaded += 1
                    time.sleep(delay)
        
        # 下载样品图片
        if movie.sample_images:
            sample_urls = [url.strip() for url in movie.sample_images.split('\n') if url.strip()]
            sample_local_paths = []
            
            if movie.sample_images_local:
                existing_paths = [path.strip() for path in movie.sample_images_local.split('\n') if path.strip()]
            else:
                existing_paths = []
            
            for i, sample_url in enumerate(sample_urls):
                if i < len(existing_paths) and not overwrite:
                    sample_local_paths.append(existing_paths[i])
                    continue
                
                self.stdout.write(f'    📸 下载样品图 {i+1}/{len(sample_urls)}')
                local_path = self.download_image(
                    sample_url, 
                    'sample', 
                    movie.censored_id,
                    f'sample_{i+1:02d}'
                )
                if local_path:
                    sample_local_paths.append(local_path)
                    images_downloaded += 1
                    time.sleep(delay)
                else:
                    # 如果下载失败，保留原有路径（如果存在）
                    if i < len(existing_paths):
                        sample_local_paths.append(existing_paths[i])
            
            if sample_local_paths:
                movie.sample_images_local = '\n'.join(sample_local_paths)
        
        # 保存更新
        if images_downloaded > 0:
            movie.save()
        
        return images_downloaded

    def download_image(self, image_url, image_type, movie_id, filename=None):
        """下载单张图片"""
        try:
            response = self.session.get(image_url, timeout=30)
            response.raise_for_status()
            
            # 获取文件扩展名
            parsed_url = urlparse(image_url)
            ext = os.path.splitext(parsed_url.path)[1]
            if not ext:
                # 根据Content-Type判断扩展名
                content_type = response.headers.get('content-type', '')
                if 'jpeg' in content_type or 'jpg' in content_type:
                    ext = '.jpg'
                elif 'png' in content_type:
                    ext = '.png'
                elif 'webp' in content_type:
                    ext = '.webp'
                else:
                    ext = '.jpg'  # 默认
            
            # 生成文件名
            if not filename:
                filename = f'{image_type}{ext}'
            else:
                filename = f'{filename}{ext}'
            
            # 创建目录路径
            movie_dir = os.path.join(
                settings.MEDIA_ROOT, 
                'images', 
                'movies', 
                movie_id
            )
            os.makedirs(movie_dir, exist_ok=True)
            
            # 保存文件
            file_path = os.path.join(movie_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # 验证文件大小
            file_size = os.path.getsize(file_path)
            if file_size < 1024:  # 小于1KB可能是错误页面
                os.remove(file_path)
                self.stdout.write(f'      ❌ 文件太小，可能下载失败: {file_size} bytes')
                return None
            
            # 返回相对路径
            relative_path = os.path.join('images', 'movies', movie_id, filename)
            self.stdout.write(f'      ✅ 下载成功: {filename} ({file_size} bytes)')
            return relative_path
            
        except Exception as e:
            self.stdout.write(f'      ❌ 下载失败 {image_url}: {e}')
            return None

    def ensure_media_directories(self):
        """确保媒体目录存在"""
        media_dirs = [
            os.path.join(settings.MEDIA_ROOT, 'images'),
            os.path.join(settings.MEDIA_ROOT, 'images', 'movies'),
        ]
        
        for dir_path in media_dirs:
            os.makedirs(dir_path, exist_ok=True)
        
        self.stdout.write('📁 媒体目录已准备就绪')

    def get_download_statistics(self):
        """获取下载统计"""
        total_movies = Movie.objects.count()
        movies_with_cover = Movie.objects.exclude(
            cover_image_local__isnull=True
        ).exclude(
            cover_image_local=''
        ).count()
        
        movies_with_samples = Movie.objects.exclude(
            sample_images_local__isnull=True
        ).exclude(
            sample_images_local=''
        ).count()
        
        stats = {
            'total_movies': total_movies,
            'movies_with_cover': movies_with_cover,
            'movies_with_samples': movies_with_samples,
            'cover_rate': movies_with_cover / max(total_movies, 1) * 100,
            'sample_rate': movies_with_samples / max(total_movies, 1) * 100,
        }
        
        self.stdout.write(f'\n📊 下载统计:')
        self.stdout.write(f'  总作品数: {stats["total_movies"]}')
        self.stdout.write(f'  有封面: {stats["movies_with_cover"]} ({stats["cover_rate"]:.1f}%)')
        self.stdout.write(f'  有样品图: {stats["movies_with_samples"]} ({stats["sample_rate"]:.1f}%)')
        
        return stats
