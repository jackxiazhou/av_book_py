"""
Django management command to create sample data.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
import random

from apps.movies.models import Movie, MovieTag, MovieRating
from apps.magnets.models import MagnetLink, MagnetCategory


class Command(BaseCommand):
    help = 'Create sample data for testing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--movies',
            type=int,
            default=20,
            help='Number of movies to create'
        )
        parser.add_argument(
            '--magnets',
            type=int,
            default=50,
            help='Number of magnet links to create'
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # 创建标签
        tags = self.create_tags()
        self.stdout.write(f'Created {len(tags)} tags')
        
        # 创建磁力分类
        categories = self.create_magnet_categories()
        self.stdout.write(f'Created {len(categories)} magnet categories')
        
        # 创建影片
        movies = self.create_movies(options['movies'], tags)
        self.stdout.write(f'Created {len(movies)} movies')
        
        # 创建磁力链接
        magnets = self.create_magnets(options['magnets'], movies, categories)
        self.stdout.write(f'Created {len(magnets)} magnet links')
        
        # 创建评分
        ratings = self.create_ratings(movies)
        self.stdout.write(f'Created {len(ratings)} ratings')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample data!')
        )
    
    def create_tags(self):
        """创建标签"""
        tag_data = [
            ('高清', 'hd', '高清视频', '#007bff'),
            ('字幕', 'subtitle', '有字幕', '#28a745'),
            ('热门', 'popular', '热门影片', '#dc3545'),
            ('新作', 'new', '新发布', '#ffc107'),
            ('经典', 'classic', '经典作品', '#6f42c1'),
        ]
        
        tags = []
        for name, slug, desc, color in tag_data:
            tag, created = MovieTag.objects.get_or_create(
                name=name,
                defaults={
                    'slug': slug,
                    'description': desc,
                    'color': color
                }
            )
            tags.append(tag)
        
        return tags
    
    def create_magnet_categories(self):
        """创建磁力分类"""
        category_data = [
            ('高清', '高清视频资源', '#007bff'),
            ('字幕版', '带字幕的资源', '#28a745'),
            ('无码', '无码资源', '#dc3545'),
            ('有码', '有码资源', '#ffc107'),
        ]
        
        categories = []
        for name, desc, color in category_data:
            category, created = MagnetCategory.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'color': color
                }
            )
            categories.append(category)
        
        return categories
    
    def create_movies(self, count, tags):
        """创建影片"""
        sources = ['javbus', 'avmoo', 'javlibrary']
        studios = ['SOD', 'MOODYZ', 'S1', 'IDEA POCKET', 'PREMIUM']
        directors = ['田中太郎', '佐藤次郎', '鈴木三郎', '高橋四郎']
        idols = ['美咲かんな', '橋本ありな', '深田えいみ', '三上悠亜', '明日花キララ']
        genres = ['美少女', 'OL', '人妻', '学生', '巨乳', '美脚', 'フェラ', '中出し']
        
        movies = []
        for i in range(count):
            # 生成影片编号
            prefix = random.choice(['YMLW', 'START', 'SSIS', 'IPX', 'PRED'])
            number = str(random.randint(1, 999)).zfill(3)
            censored_id = f"{prefix}-{number}"
            
            # 检查是否已存在
            if Movie.objects.filter(censored_id=censored_id).exists():
                continue
            
            movie = Movie.objects.create(
                censored_id=censored_id,
                movie_title=f"Sample Movie {censored_id}",
                movie_pic_cover=f"https://example.com/covers/{censored_id}.jpg",
                release_date=date.today() - timedelta(days=random.randint(1, 365)),
                movie_length=f"{random.randint(90, 180)}分钟",
                director=random.choice(directors),
                studio=random.choice(studios),
                label=random.choice(studios),
                series=f"Series {random.randint(1, 10)}",
                genre=', '.join(random.sample(genres, random.randint(2, 4))),
                jav_idols=', '.join(random.sample(idols, random.randint(1, 2))),
                source=random.choice(sources),
                view_count=random.randint(0, 1000),
                download_count=random.randint(0, 500)
            )
            
            # 添加随机标签
            movie.tags.set(random.sample(tags, random.randint(1, 3)))
            movies.append(movie)
        
        return movies
    
    def create_magnets(self, count, movies, categories):
        """创建磁力链接"""
        qualities = ['sd', 'hd', 'fhd', 'uhd']
        uploaders = ['User1', 'User2', 'User3', 'Anonymous']
        
        magnets = []
        for i in range(count):
            movie = random.choice(movies)
            quality = random.choice(qualities)
            
            # 生成假的磁力链接
            hash_value = ''.join(random.choices('0123456789ABCDEF', k=40))
            magnet_link = f"magnet:?xt=urn:btih:{hash_value}"
            
            magnet = MagnetLink.objects.create(
                movie=movie,
                magnet_name=f"{movie.censored_id} [{quality.upper()}]",
                magnet_link=magnet_link,
                file_size=f"{random.uniform(1.0, 5.0):.1f}GB",
                file_size_bytes=random.randint(1000000000, 5000000000),
                quality=quality,
                has_subtitle=random.choice([True, False]),
                subtitle_language=random.choice(['中文', '英文', '日文', '']),
                seeders=random.randint(0, 100),
                leechers=random.randint(0, 50),
                completed=random.randint(0, 1000),
                publish_date=date.today() - timedelta(days=random.randint(1, 30)),
                uploader=random.choice(uploaders),
                is_active=random.choice([True, True, True, False]),  # 75%概率为活跃
                is_verified=random.choice([True, False]),
                download_count=random.randint(0, 200),
                click_count=random.randint(0, 500)
            )
            
            # 添加随机分类
            magnet.categories.set(random.sample(categories, random.randint(1, 2)))
            magnets.append(magnet)
        
        return magnets
    
    def create_ratings(self, movies):
        """创建评分"""
        ratings = []
        for movie in random.sample(movies, min(len(movies), 15)):
            rating = MovieRating.objects.create(movie=movie)
            
            # 生成随机评分分布
            total_votes = random.randint(5, 100)
            votes = [0, 0, 0, 0, 0]
            
            for _ in range(total_votes):
                star = random.choices(range(5), weights=[5, 10, 20, 35, 30])[0]
                votes[star] += 1
            
            rating.one_star = votes[0]
            rating.two_star = votes[1]
            rating.three_star = votes[2]
            rating.four_star = votes[3]
            rating.five_star = votes[4]
            rating.calculate_average()
            
            ratings.append(rating)
        
        return ratings
