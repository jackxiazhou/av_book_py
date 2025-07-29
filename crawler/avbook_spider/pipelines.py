"""
Scrapy pipelines for AVBook spider.
"""

import os
import sys
import django
import requests
import hashlib
import time
from urllib.parse import urlparse, urljoin
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

# 设置Django环境
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avbook.settings')
django.setup()

from apps.movies.models import Movie, MovieRating
from apps.magnets.models import MagnetLink
from apps.actresses.models import Actress, ActressTag
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


class ValidationPipeline:
    """数据验证管道"""
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # 验证必需字段
        if not adapter.get('censored_id'):
            raise DropItem(f"Missing censored_id in {item}")
        
        # 清理数据
        for field_name in adapter.field_names():
            value = adapter.get(field_name)
            if isinstance(value, str):
                adapter[field_name] = value.strip()
        
        return item


class DuplicatesPipeline:
    """去重管道"""
    
    def __init__(self):
        self.ids_seen = set()
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        censored_id = adapter['censored_id']
        
        if censored_id in self.ids_seen:
            raise DropItem(f"Duplicate item found: {censored_id}")
        else:
            self.ids_seen.add(censored_id)
            return item


class DatabasePipeline:
    """数据库写入管道"""
    
    def __init__(self):
        self.movies_created = 0
        self.magnets_created = 0
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        if 'movie_censored_id' in adapter:
            # 这是磁力链接项
            return self.process_magnet_item(adapter, spider)
        else:
            # 这是影片项
            return self.process_movie_item(adapter, spider)
    
    def process_movie_item(self, adapter, spider):
        """处理影片项"""
        try:
            # 检查是否已存在
            movie, created = Movie.objects.get_or_create(
                censored_id=adapter['censored_id'],
                defaults={
                    'movie_title': adapter.get('movie_title', ''),
                    'movie_pic_cover': adapter.get('movie_pic_cover', ''),
                    'release_date': adapter.get('release_date'),
                    'movie_length': adapter.get('movie_length', ''),
                    'director': adapter.get('director', ''),
                    'studio': adapter.get('studio', ''),
                    'label': adapter.get('label', ''),
                    'series': adapter.get('series', ''),
                    'genre': adapter.get('genre', ''),
                    'jav_idols': adapter.get('jav_idols', ''),
                    'source': adapter.get('source', 'unknown'),
                }
            )
            
            if created:
                self.movies_created += 1
                spider.logger.info(f"Created movie: {movie.censored_id}")
                
                # 创建评分记录
                MovieRating.objects.get_or_create(movie=movie)
            else:
                spider.logger.info(f"Movie already exists: {movie.censored_id}")
            
            return adapter.item
            
        except Exception as e:
            spider.logger.error(f"Error saving movie {adapter['censored_id']}: {e}")
            raise DropItem(f"Error saving movie: {e}")
    
    def process_magnet_item(self, adapter, spider):
        """处理磁力链接项"""
        try:
            # 查找关联的影片
            try:
                movie = Movie.objects.get(censored_id=adapter['movie_censored_id'])
            except Movie.DoesNotExist:
                spider.logger.warning(f"Movie not found for magnet: {adapter['movie_censored_id']}")
                raise DropItem(f"Movie not found: {adapter['movie_censored_id']}")
            
            # 检查是否已存在相同的磁力链接
            magnet_link = adapter.get('magnet_link', '')
            if MagnetLink.objects.filter(movie=movie, magnet_link=magnet_link).exists():
                spider.logger.info(f"Magnet already exists for {movie.censored_id}")
                return adapter.item
            
            # 创建磁力链接
            magnet = MagnetLink.objects.create(
                movie=movie,
                magnet_name=adapter.get('magnet_name', ''),
                magnet_link=magnet_link,
                file_size=adapter.get('file_size', ''),
                file_size_bytes=adapter.get('file_size_bytes'),
                seeders=adapter.get('seeders', 0),
                leechers=adapter.get('leechers', 0),
                completed=adapter.get('completed', 0),
                publish_date=adapter.get('publish_date'),
                uploader=adapter.get('uploader', ''),
                source=adapter.get('source', 'unknown'),
            )
            
            self.magnets_created += 1
            spider.logger.info(f"Created magnet for {movie.censored_id}: {magnet.magnet_name}")
            
            return adapter.item
            
        except Exception as e:
            spider.logger.error(f"Error saving magnet: {e}")
            raise DropItem(f"Error saving magnet: {e}")
    
    def close_spider(self, spider):
        """爬虫结束时的统计"""
        spider.logger.info(f"Pipeline stats:")
        spider.logger.info(f"  Movies created: {self.movies_created}")
        spider.logger.info(f"  Magnets created: {self.magnets_created}")


class ActressImageDownloadPipeline:
    """女友图片下载管道"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

        # 确保目录存在
        self.ensure_directories()

    def ensure_directories(self):
        """确保存储目录存在"""
        directories = [
            'images/actresses/profiles',
            'images/actresses/covers',
            'images/actresses/galleries',
        ]

        for directory in directories:
            os.makedirs(os.path.join(settings.MEDIA_ROOT, directory), exist_ok=True)

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # 只处理女友数据
        if not adapter.get('name') or adapter.get('censored_id'):
            return item

        try:
            # 下载头像
            if adapter.get('profile_image'):
                local_path = self.download_image(
                    adapter['profile_image'],
                    'actress_profile',
                    f"{adapter['name']}_profile",
                    spider
                )
                if local_path:
                    adapter['profile_image'] = f"/media/{local_path}"

            # 下载封面
            if adapter.get('cover_image'):
                local_path = self.download_image(
                    adapter['cover_image'],
                    'actress_cover',
                    f"{adapter['name']}_cover",
                    spider
                )
                if local_path:
                    adapter['cover_image'] = f"/media/{local_path}"

            return item

        except Exception as e:
            spider.logger.error(f"Error downloading images for {adapter.get('name', 'unknown')}: {e}")
            return item

    def download_image(self, url, category, filename_prefix, spider):
        """下载单个图片"""
        if not url or url.startswith('/media/'):
            return None

        try:
            spider.logger.info(f"Downloading image: {url}")

            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # 检查内容类型
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                spider.logger.warning(f"Invalid content type: {content_type}")
                return None

            # 生成文件名
            filename = self.generate_filename(url, filename_prefix)

            # 确定存储路径
            storage_path = self.get_storage_path(category, filename)

            # 检查文件是否已存在
            if default_storage.exists(storage_path):
                spider.logger.info(f"Image already exists: {storage_path}")
                return storage_path

            # 读取图片内容
            image_content = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    image_content += chunk
                    if len(image_content) > 10 * 1024 * 1024:  # 10MB限制
                        spider.logger.warning("Image too large")
                        return None

            if len(image_content) < 1024:  # 至少1KB
                spider.logger.warning("Image too small")
                return None

            # 保存文件
            saved_path = default_storage.save(storage_path, ContentFile(image_content))
            spider.logger.info(f"Image saved: {saved_path}")

            # 添加延迟避免过于频繁的请求
            time.sleep(1)

            return saved_path

        except Exception as e:
            spider.logger.error(f"Error downloading image {url}: {e}")
            return None

    def generate_filename(self, url, prefix):
        """生成文件名"""
        parsed_url = urlparse(url)
        original_filename = os.path.basename(parsed_url.path)

        if '.' in original_filename:
            name, ext = os.path.splitext(original_filename)
        else:
            ext = '.jpg'  # 默认扩展名

        # 生成唯一标识
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        filename = f"{prefix}_{url_hash}{ext}"

        # 清理文件名中的特殊字符
        filename = "".join(c for c in filename if c.isalnum() or c in '._-')
        return filename

    def get_storage_path(self, category, filename):
        """获取存储路径"""
        category_paths = {
            'actress_profile': 'images/actresses/profiles',
            'actress_cover': 'images/actresses/covers',
            'actress_gallery': 'images/actresses/galleries',
        }

        base_path = category_paths.get(category, 'images/general')
        return os.path.join(base_path, filename)


class ActressDatabasePipeline:
    """女友数据库存储管道"""

    def __init__(self):
        self.actresses_created = 0
        self.actresses_updated = 0

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # 只处理女友数据
        if not adapter.get('name') or adapter.get('censored_id'):
            return item

        try:
            # 保存女友数据
            actress_data = {
                'name': adapter['name'],
                'name_en': adapter.get('name_en', ''),
                'birth_date': adapter.get('birth_date'),
                'height': adapter.get('height'),
                'weight': adapter.get('weight'),
                'measurements': adapter.get('measurements', ''),
                'cup_size': adapter.get('cup_size', ''),
                'blood_type': adapter.get('blood_type', ''),
                'nationality': adapter.get('nationality', '日本'),
                'debut_date': adapter.get('debut_date'),
                'is_active': adapter.get('is_active', True),
                'profile_image': adapter.get('profile_image', ''),
                'cover_image': adapter.get('cover_image', ''),
                'gallery_images': adapter.get('gallery_images', ''),
                'movie_count': adapter.get('movie_count', 0),
                'popularity_score': adapter.get('popularity_score', 0),
                'description': f"从AVMoo爬取的女友数据，共有 {adapter.get('movie_count', 0)} 部作品",
            }

            # 创建或更新女友
            actress, created = Actress.objects.get_or_create(
                name=actress_data['name'],
                defaults=actress_data
            )

            if created:
                self.actresses_created += 1
                spider.logger.info(f"Created new actress: {actress.name}")

                # 添加标签
                self.add_actress_tags(actress, spider)
            else:
                # 更新现有女友信息
                updated = False
                for field, value in actress_data.items():
                    if field != 'name' and value and not getattr(actress, field):
                        setattr(actress, field, value)
                        updated = True

                if updated:
                    actress.save()
                    self.actresses_updated += 1
                    spider.logger.info(f"Updated actress: {actress.name}")

            return item

        except Exception as e:
            spider.logger.error(f"Error saving actress {adapter.get('name', 'unknown')}: {e}")
            return item

    def add_actress_tags(self, actress, spider):
        """为女友添加标签"""
        try:
            # 根据作品数添加标签
            if actress.movie_count > 20:
                popular_tag, _ = ActressTag.objects.get_or_create(
                    name='人气',
                    defaults={'slug': 'popular', 'color': '#ffd700', 'description': '人气女友'}
                )
                popular_tag.actresses.add(actress)

            if actress.movie_count > 10:
                active_tag, _ = ActressTag.objects.get_or_create(
                    name='活跃',
                    defaults={'slug': 'active', 'color': '#28a745', 'description': '活跃女友'}
                )
                active_tag.actresses.add(actress)

            # 添加爬取来源标签
            avmoo_tag, _ = ActressTag.objects.get_or_create(
                name='AVMoo',
                defaults={'slug': 'avmoo', 'color': '#17a2b8', 'description': '从AVMoo爬取的女友'}
            )
            avmoo_tag.actresses.add(actress)

        except Exception as e:
            spider.logger.error(f"Error adding tags for actress {actress.name}: {e}")

    def close_spider(self, spider):
        """爬虫结束时的统计"""
        spider.logger.info(f"Actress Pipeline stats:")
        spider.logger.info(f"  Actresses created: {self.actresses_created}")
        spider.logger.info(f"  Actresses updated: {self.actresses_updated}")


class ActressCompleteValidationPipeline:
    """完整女友数据验证管道"""

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        data_type = adapter.get('data_type')

        if data_type == 'actress':
            # 验证女友数据
            if not adapter.get('name'):
                raise DropItem(f"Missing actress name in {item}")

        elif data_type == 'movie':
            # 验证作品数据
            if not adapter.get('censored_id') and not adapter.get('movie_title'):
                raise DropItem(f"Missing movie identifier in {item}")

        # 清理数据
        for field_name in adapter.field_names():
            value = adapter.get(field_name)
            if isinstance(value, str):
                adapter[field_name] = value.strip()

        return item


class ActressCompleteDjangoPipeline:
    """完整女友Django数据库管道"""

    def __init__(self):
        self.actresses_created = 0
        self.movies_created = 0
        self.actresses_updated = 0
        self.movies_updated = 0

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        data_type = adapter.get('data_type')

        try:
            if data_type == 'actress':
                return self.save_actress(adapter, spider)
            elif data_type == 'movie':
                return self.save_movie(adapter, spider)
            else:
                spider.logger.warning(f"Unknown data type: {data_type}")
                return item

        except Exception as e:
            spider.logger.error(f"Error processing item: {e}")
            raise DropItem(f"Error processing item: {e}")

    def save_actress(self, adapter, spider):
        """保存女友数据"""
        name = adapter.get('name')

        try:
            # 查找或创建女友
            actress, created = Actress.objects.get_or_create(
                name=name,
                defaults={
                    'name_en': adapter.get('name_en', ''),
                    'alias': adapter.get('alias', ''),
                    'birth_date': self.parse_date(adapter.get('birth_date')),
                    'debut_date': self.parse_date(adapter.get('debut_date')),
                    'height': adapter.get('height'),
                    'weight': adapter.get('weight'),
                    'measurements': adapter.get('measurements', ''),
                    'cup_size': adapter.get('cup_size', ''),
                    'nationality': adapter.get('nationality', ''),
                    'profile_image': adapter.get('profile_image', ''),
                    'gallery_images': adapter.get('gallery_images', ''),
                    'popularity_score': adapter.get('popularity_score', 0),
                    'source': 'avmoo_complete'
                }
            )

            if created:
                self.actresses_created += 1
                spider.logger.info(f"Created new actress: {name}")
            else:
                # 更新现有数据
                updated = False

                # 更新基本信息
                if adapter.get('name_en') and not actress.name_en:
                    actress.name_en = adapter.get('name_en')
                    updated = True

                if adapter.get('birth_date') and not actress.birth_date:
                    actress.birth_date = self.parse_date(adapter.get('birth_date'))
                    updated = True

                if adapter.get('height') and not actress.height:
                    actress.height = adapter.get('height')
                    updated = True

                if adapter.get('profile_image') and not actress.profile_image:
                    actress.profile_image = adapter.get('profile_image')
                    updated = True

                if updated:
                    actress.save()
                    self.actresses_updated += 1
                    spider.logger.info(f"Updated actress: {name}")

            return adapter._values

        except Exception as e:
            spider.logger.error(f"Error saving actress {name}: {e}")
            raise

    def save_movie(self, adapter, spider):
        """保存作品数据"""
        censored_id = adapter.get('censored_id')
        movie_title = adapter.get('movie_title')
        movie_hash = adapter.get('movie_hash')

        try:
            # 查找或创建作品
            movie = None
            created = False

            if censored_id:
                movie, created = Movie.objects.get_or_create(
                    censored_id=censored_id,
                    defaults=self.get_movie_defaults(adapter)
                )
            elif movie_hash:
                # 使用hash作为临时ID
                temp_id = f"HASH-{movie_hash[:8].upper()}"
                movie, created = Movie.objects.get_or_create(
                    censored_id=temp_id,
                    defaults=self.get_movie_defaults(adapter)
                )

            if movie:
                if created:
                    self.movies_created += 1
                    spider.logger.info(f"Created new movie: {censored_id or temp_id}")
                else:
                    # 更新现有数据
                    updated = self.update_movie(movie, adapter)
                    if updated:
                        self.movies_updated += 1
                        spider.logger.info(f"Updated movie: {censored_id or temp_id}")

                # 关联女友
                self.link_actress_to_movie(movie, adapter, spider)

            return adapter._values

        except Exception as e:
            spider.logger.error(f"Error saving movie {censored_id}: {e}")
            raise

    def get_movie_defaults(self, adapter):
        """获取作品默认数据"""
        return {
            'movie_title': adapter.get('movie_title', ''),
            'release_date': self.parse_date(adapter.get('release_date')),
            'movie_length': adapter.get('movie_length', ''),
            'director': adapter.get('director', ''),
            'studio': adapter.get('studio', ''),
            'label': adapter.get('label', ''),
            'series': adapter.get('series', ''),
            'jav_idols': adapter.get('jav_idols', ''),
            'genre': adapter.get('genre', ''),
            'movie_tags': adapter.get('movie_tags', ''),
            'movie_pic_cover': adapter.get('movie_pic_cover', ''),
            'sample_images': adapter.get('sample_images', ''),
            'source': 'avmoo_complete'
        }

    def update_movie(self, movie, adapter):
        """更新作品数据"""
        updated = False

        # 更新空字段
        fields_to_update = [
            'movie_title', 'release_date', 'director', 'studio',
            'label', 'series', 'genre', 'movie_pic_cover', 'sample_images'
        ]

        for field in fields_to_update:
            new_value = adapter.get(field)
            if new_value and not getattr(movie, field):
                setattr(movie, field, new_value)
                updated = True

        if updated:
            movie.save()

        return updated

    def link_actress_to_movie(self, movie, adapter, spider):
        """关联女友到作品"""
        actress_name = adapter.get('related_actress')

        if actress_name:
            try:
                actress = Actress.objects.get(name=actress_name)

                # 检查是否已经关联
                if not movie.actresses.filter(id=actress.id).exists():
                    movie.actresses.add(actress)
                    spider.logger.info(f"Linked actress {actress_name} to movie {movie.censored_id}")

            except Actress.DoesNotExist:
                spider.logger.warning(f"Actress {actress_name} not found for movie {movie.censored_id}")

    def parse_date(self, date_str):
        """解析日期字符串"""
        if not date_str:
            return None

        try:
            from datetime import datetime

            # 尝试多种日期格式
            formats = ['%Y-%m-%d', '%Y/%m/%d', '%Y年%m月%d日']

            for fmt in formats:
                try:
                    return datetime.strptime(str(date_str), fmt).date()
                except ValueError:
                    continue

            return None

        except Exception:
            return None

    def close_spider(self, spider):
        """爬虫结束时的统计"""
        spider.logger.info(f"Complete Actress Pipeline stats:")
        spider.logger.info(f"  Actresses created: {self.actresses_created}")
        spider.logger.info(f"  Actresses updated: {self.actresses_updated}")
        spider.logger.info(f"  Movies created: {self.movies_created}")
        spider.logger.info(f"  Movies updated: {self.movies_updated}")
