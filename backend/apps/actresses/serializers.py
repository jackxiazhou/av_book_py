"""
Actress serializers for AVBook API.
"""

from rest_framework import serializers
from .models import Actress


class ActressSerializer(serializers.ModelSerializer):
    """演员基本序列化器"""
    lifestyle_photos_list = serializers.SerializerMethodField()
    portrait_photos_list = serializers.SerializerMethodField()
    lifestyle_photos_local_list = serializers.SerializerMethodField()
    portrait_photos_local_list = serializers.SerializerMethodField()

    class Meta:
        model = Actress
        fields = [
            'id', 'name', 'name_en', 'birth_date', 'height',
            'measurements', 'cup_size', 'debut_date', 'agency',
            'profile_image', 'cover_image', 'movie_count',
            'profile_image_local', 'cover_image_local',
            'lifestyle_photos_list', 'portrait_photos_list',
            'lifestyle_photos_local_list', 'portrait_photos_local_list'
        ]
    
    def get_lifestyle_photos_list(self, obj):
        """获取生活照列表"""
        if obj.lifestyle_photos:
            return [url.strip() for url in obj.lifestyle_photos.split('\n') if url.strip()]
        return []
    
    def get_portrait_photos_list(self, obj):
        """获取写真照列表"""
        if obj.portrait_photos:
            return [url.strip() for url in obj.portrait_photos.split('\n') if url.strip()]
        return []

    def get_lifestyle_photos_local_list(self, obj):
        """获取本地生活照列表"""
        if obj.lifestyle_photos_local:
            return [url.strip() for url in obj.lifestyle_photos_local.split('\n') if url.strip()]
        return []

    def get_portrait_photos_local_list(self, obj):
        """获取本地写真照列表"""
        if obj.portrait_photos_local:
            return [url.strip() for url in obj.portrait_photos_local.split('\n') if url.strip()]
        return []


class ActressDetailSerializer(ActressSerializer):
    """演员详细序列化器"""
    gallery_images_list = serializers.SerializerMethodField()
    recent_movies = serializers.SerializerMethodField()
    
    class Meta(ActressSerializer.Meta):
        fields = ActressSerializer.Meta.fields + [
            'gallery_images_list', 'recent_movies'
        ]
    
    def get_gallery_images_list(self, obj):
        """获取图片集列表"""
        if obj.gallery_images:
            return [url.strip() for url in obj.gallery_images.split('\n') if url.strip()]
        return []
    
    def get_recent_movies(self, obj):
        """获取最近的作品"""
        recent_movies = obj.movies.all().order_by('-release_date')[:5]
        return [{
            'id': movie.id,
            'censored_id': movie.censored_id,
            'movie_title': movie.movie_title,
            'release_date': movie.release_date,
            'studio': movie.studio,
            'cover_image': movie.cover_image,
            'cover_image_local': movie.cover_image_local,
            'sample_images_list': [url.strip() for url in movie.sample_images.split('\n') if movie.sample_images and url.strip()],
            'sample_images_local_list': [url.strip() for url in movie.sample_images_local.split('\n') if movie.sample_images_local and url.strip()],
            'movie_tags': movie.movie_tags,
            'duration_minutes': movie.duration_minutes,
        } for movie in recent_movies]
