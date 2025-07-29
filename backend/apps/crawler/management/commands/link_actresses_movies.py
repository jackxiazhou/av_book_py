"""
Django management command to link actresses with movies based on jav_idols field.
"""

import re
from django.core.management.base import BaseCommand
from apps.movies.models import Movie
from apps.actresses.models import Actress, ActressTag


class Command(BaseCommand):
    help = 'Link actresses with movies based on jav_idols field'
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
        parser.add_argument('--create-missing', action='store_true', help='Create missing actresses')
        parser.add_argument('--max-movies', type=int, default=100, help='Maximum movies to process')
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        create_missing = options['create_missing']
        max_movies = options['max_movies']
        
        self.stdout.write(f'Starting actress-movie linking process...')
        self.stdout.write(f'Dry run: {dry_run}')
        self.stdout.write(f'Create missing actresses: {create_missing}')
        self.stdout.write(f'Max movies to process: {max_movies}')
        
        # 获取有演员信息的影片
        movies = Movie.objects.filter(jav_idols__isnull=False).exclude(jav_idols='')[:max_movies]
        self.stdout.write(f'Found {movies.count()} movies with actress information')
        
        linked_count = 0
        created_actresses = 0
        
        for movie in movies:
            self.stdout.write(f'Processing movie: {movie.censored_id}')
            
            # 解析演员姓名
            actress_names = self.parse_actress_names(movie.jav_idols)
            self.stdout.write(f'  Found actresses: {actress_names}')
            
            for actress_name in actress_names:
                # 查找现有女友
                actress = Actress.objects.filter(name=actress_name).first()
                
                if not actress and create_missing:
                    if not dry_run:
                        # 创建新女友
                        actress = self.create_actress(actress_name, movie)
                        created_actresses += 1
                    self.stdout.write(f'  Would create actress: {actress_name}')
                
                if actress:
                    # 检查是否已经关联
                    if not movie.actresses.filter(id=actress.id).exists():
                        if not dry_run:
                            movie.actresses.add(actress)
                            # 更新女友作品数
                            actress.update_movie_count()
                        linked_count += 1
                        self.stdout.write(f'  Linked: {actress_name}')
                    else:
                        self.stdout.write(f'  Already linked: {actress_name}')
                else:
                    self.stdout.write(f'  Actress not found: {actress_name}')
        
        self.stdout.write(self.style.SUCCESS(f'Linking process completed!'))
        self.stdout.write(f'Movies processed: {movies.count()}')
        self.stdout.write(f'Actresses linked: {linked_count}')
        self.stdout.write(f'Actresses created: {created_actresses}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('This was a dry run - no changes were made'))
    
    def parse_actress_names(self, jav_idols_text):
        """解析演员姓名"""
        if not jav_idols_text:
            return []
        
        # 分割演员姓名
        names = []
        
        # 常见的分隔符
        separators = [',', '、', '，', ';', '；', '|']
        
        # 使用正则表达式分割
        pattern = '|'.join(map(re.escape, separators))
        raw_names = re.split(pattern, jav_idols_text)
        
        for name in raw_names:
            name = name.strip()
            if name and len(name) > 1:  # 过滤掉太短的名字
                names.append(name)
        
        return names
    
    def create_actress(self, name, movie):
        """创建新女友"""
        actress = Actress.objects.create(
            name=name,
            nationality='日本',
            is_active=True,
            popularity_score=30,  # 默认人气值
            description=f'通过影片 {movie.censored_id} 发现的女友'
        )
        
        # 添加默认标签
        new_tag, _ = ActressTag.objects.get_or_create(
            name='新发现',
            defaults={
                'slug': 'new-discovery',
                'color': '#17a2b8',
                'description': '通过影片数据发现的新女友'
            }
        )
        new_tag.actresses.add(actress)
        
        self.stdout.write(f'Created new actress: {name}')
        return actress
