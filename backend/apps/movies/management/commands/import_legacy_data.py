"""
Django management command to import data from legacy PHP system.
"""

import json
import csv
import os
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from django.db import transaction
from datetime import datetime

from apps.movies.models import Movie, MovieTag, MovieRating
from apps.magnets.models import MagnetLink, MagnetCategory


class Command(BaseCommand):
    help = 'Import data from legacy PHP system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['json', 'csv', 'sql'],
            default='json',
            help='Source data format'
        )
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to source data file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without saving data'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for bulk operations'
        )
    
    def handle(self, *args, **options):
        source_format = options['source']
        file_path = options['file']
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'File not found: {file_path}')
            )
            return
        
        self.stdout.write(f'Starting data import from {file_path}')
        self.stdout.write(f'Format: {source_format}')
        self.stdout.write(f'Dry run: {dry_run}')
        
        try:
            if source_format == 'json':
                self.import_from_json(file_path, dry_run, batch_size)
            elif source_format == 'csv':
                self.import_from_csv(file_path, dry_run, batch_size)
            elif source_format == 'sql':
                self.import_from_sql(file_path, dry_run, batch_size)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Import failed: {e}')
            )
            raise
    
    def import_from_json(self, file_path, dry_run, batch_size):
        """从JSON文件导入数据"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        movies_data = data.get('movies', [])
        magnets_data = data.get('magnets', [])
        
        self.stdout.write(f'Found {len(movies_data)} movies and {len(magnets_data)} magnets')
        
        if not dry_run:
            with transaction.atomic():
                # 导入影片
                movies_created = self.import_movies(movies_data, batch_size)
                self.stdout.write(f'Imported {movies_created} movies')
                
                # 导入磁力链接
                magnets_created = self.import_magnets(magnets_data, batch_size)
                self.stdout.write(f'Imported {magnets_created} magnets')
        else:
            self.stdout.write('Dry run completed - no data was saved')
    
    def import_from_csv(self, file_path, dry_run, batch_size):
        """从CSV文件导入数据"""
        movies_created = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            movies_batch = []
            
            for row in reader:
                movie_data = self.parse_csv_row(row)
                if movie_data:
                    movies_batch.append(movie_data)
                    
                    if len(movies_batch) >= batch_size:
                        if not dry_run:
                            created = self.create_movies_batch(movies_batch)
                            movies_created += created
                        movies_batch = []
            
            # 处理剩余的数据
            if movies_batch and not dry_run:
                created = self.create_movies_batch(movies_batch)
                movies_created += created
        
        self.stdout.write(f'Processed {movies_created} movies from CSV')
    
    def import_movies(self, movies_data, batch_size):
        """批量导入影片"""
        created_count = 0
        movies_batch = []
        
        for movie_data in movies_data:
            try:
                # 检查是否已存在
                censored_id = movie_data.get('censored_id')
                if not censored_id:
                    continue
                
                if Movie.objects.filter(censored_id=censored_id).exists():
                    self.stdout.write(f'Movie {censored_id} already exists, skipping...')
                    continue
                
                # 准备数据
                movie_obj = Movie(
                    censored_id=censored_id,
                    movie_title=movie_data.get('movie_title', ''),
                    movie_pic_cover=movie_data.get('movie_pic_cover', ''),
                    release_date=self.parse_date(movie_data.get('release_date')),
                    movie_length=movie_data.get('movie_length', ''),
                    director=movie_data.get('director', ''),
                    studio=movie_data.get('studio', ''),
                    label=movie_data.get('label', ''),
                    series=movie_data.get('series', ''),
                    genre=movie_data.get('genre', ''),
                    jav_idols=movie_data.get('jav_idols', ''),
                    source=movie_data.get('source', 'legacy'),
                    view_count=movie_data.get('view_count', 0),
                    download_count=movie_data.get('download_count', 0),
                )
                
                movies_batch.append(movie_obj)
                
                if len(movies_batch) >= batch_size:
                    Movie.objects.bulk_create(movies_batch, ignore_conflicts=True)
                    created_count += len(movies_batch)
                    self.stdout.write(f'Created batch of {len(movies_batch)} movies')
                    movies_batch = []
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Error processing movie {movie_data}: {e}')
                )
        
        # 处理剩余的批次
        if movies_batch:
            Movie.objects.bulk_create(movies_batch, ignore_conflicts=True)
            created_count += len(movies_batch)
        
        return created_count
    
    def import_magnets(self, magnets_data, batch_size):
        """批量导入磁力链接"""
        created_count = 0
        magnets_batch = []
        
        for magnet_data in magnets_data:
            try:
                # 查找关联的影片
                movie_id = magnet_data.get('movie_censored_id')
                if not movie_id:
                    continue
                
                try:
                    movie = Movie.objects.get(censored_id=movie_id)
                except Movie.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Movie {movie_id} not found for magnet')
                    )
                    continue
                
                # 检查是否已存在
                magnet_link = magnet_data.get('magnet_link', '')
                if MagnetLink.objects.filter(movie=movie, magnet_link=magnet_link).exists():
                    continue
                
                # 准备数据
                magnet_obj = MagnetLink(
                    movie=movie,
                    magnet_name=magnet_data.get('magnet_name', ''),
                    magnet_link=magnet_link,
                    file_size=magnet_data.get('file_size', ''),
                    file_size_bytes=magnet_data.get('file_size_bytes'),
                    quality=magnet_data.get('quality', 'sd'),
                    has_subtitle=magnet_data.get('has_subtitle', False),
                    subtitle_language=magnet_data.get('subtitle_language', ''),
                    seeders=magnet_data.get('seeders', 0),
                    leechers=magnet_data.get('leechers', 0),
                    completed=magnet_data.get('completed', 0),
                    publish_date=self.parse_date(magnet_data.get('publish_date')),
                    uploader=magnet_data.get('uploader', ''),
                    is_active=magnet_data.get('is_active', True),
                    is_verified=magnet_data.get('is_verified', False),
                    download_count=magnet_data.get('download_count', 0),
                    click_count=magnet_data.get('click_count', 0),
                )
                
                magnets_batch.append(magnet_obj)
                
                if len(magnets_batch) >= batch_size:
                    MagnetLink.objects.bulk_create(magnets_batch, ignore_conflicts=True)
                    created_count += len(magnets_batch)
                    self.stdout.write(f'Created batch of {len(magnets_batch)} magnets')
                    magnets_batch = []
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Error processing magnet {magnet_data}: {e}')
                )
        
        # 处理剩余的批次
        if magnets_batch:
            MagnetLink.objects.bulk_create(magnets_batch, ignore_conflicts=True)
            created_count += len(magnets_batch)
        
        return created_count
    
    def parse_date(self, date_str):
        """解析日期字符串"""
        if not date_str:
            return None
        
        try:
            # 尝试多种日期格式
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y']:
                try:
                    return datetime.strptime(str(date_str), fmt).date()
                except ValueError:
                    continue
            
            # 使用Django的解析器
            return parse_date(str(date_str))
        except:
            return None
    
    def parse_csv_row(self, row):
        """解析CSV行数据"""
        return {
            'censored_id': row.get('censored_id', ''),
            'movie_title': row.get('movie_title', ''),
            'movie_pic_cover': row.get('movie_pic_cover', ''),
            'release_date': row.get('release_date', ''),
            'movie_length': row.get('movie_length', ''),
            'director': row.get('director', ''),
            'studio': row.get('studio', ''),
            'label': row.get('label', ''),
            'series': row.get('series', ''),
            'genre': row.get('genre', ''),
            'jav_idols': row.get('jav_idols', ''),
            'source': row.get('source', 'csv_import'),
            'view_count': int(row.get('view_count', 0) or 0),
            'download_count': int(row.get('download_count', 0) or 0),
        }
