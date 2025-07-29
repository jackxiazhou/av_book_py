"""
Magnet serializers for AVBook API.
"""

from rest_framework import serializers
from .models import MagnetLink, MagnetCategory, DownloadHistory


class MagnetCategorySerializer(serializers.ModelSerializer):
    """磁力分类序列化器"""
    
    magnet_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MagnetCategory
        fields = ['id', 'name', 'description', 'color', 'magnet_count', 'created_at']
    
    def get_magnet_count(self, obj):
        """获取分类下的磁力链接数量"""
        return obj.magnets.filter(is_active=True).count()


class MagnetLinkSerializer(serializers.ModelSerializer):
    """磁力链接序列化器"""
    
    movie_title = serializers.CharField(source='movie.movie_title', read_only=True)
    movie_censored_id = serializers.CharField(source='movie.censored_id', read_only=True)
    categories = MagnetCategorySerializer(many=True, read_only=True)
    file_size_display = serializers.ReadOnlyField(source='get_file_size_display')
    health_score = serializers.ReadOnlyField()
    
    class Meta:
        model = MagnetLink
        fields = [
            'id', 'movie_title', 'movie_censored_id', 'magnet_name', 'magnet_link',
            'file_size', 'file_size_display', 'file_size_bytes', 'quality',
            'has_subtitle', 'subtitle_language', 'seeders', 'leechers', 'completed',
            'publish_date', 'uploader', 'is_active', 'is_verified', 'last_checked',
            'download_count', 'click_count', 'categories', 'health_score',
            'created_at', 'updated_at'
        ]


class MagnetLinkDetailSerializer(MagnetLinkSerializer):
    """磁力链接详情序列化器"""
    
    movie = serializers.SerializerMethodField()
    download_history = serializers.SerializerMethodField()
    
    class Meta(MagnetLinkSerializer.Meta):
        fields = MagnetLinkSerializer.Meta.fields + ['movie', 'download_history']
    
    def get_movie(self, obj):
        """获取关联影片信息"""
        from apps.movies.serializers import MovieSerializer
        return MovieSerializer(obj.movie).data
    
    def get_download_history(self, obj):
        """获取最近下载历史"""
        recent_downloads = obj.download_history.order_by('-download_time')[:5]
        return DownloadHistorySerializer(recent_downloads, many=True).data


class DownloadHistorySerializer(serializers.ModelSerializer):
    """下载历史序列化器"""
    
    magnet_name = serializers.CharField(source='magnet.magnet_name', read_only=True)
    movie_title = serializers.CharField(source='magnet.movie.movie_title', read_only=True)
    
    class Meta:
        model = DownloadHistory
        fields = [
            'id', 'magnet_name', 'movie_title', 'ip_address',
            'user_agent', 'download_time'
        ]


class MagnetCreateSerializer(serializers.ModelSerializer):
    """磁力链接创建序列化器"""
    
    class Meta:
        model = MagnetLink
        fields = [
            'movie', 'magnet_name', 'magnet_link', 'file_size', 'file_size_bytes',
            'seeders', 'leechers', 'completed', 'publish_date', 'uploader'
        ]
    
    def validate_magnet_link(self, value):
        """验证磁力链接格式"""
        if not value.startswith('magnet:?xt=urn:btih:'):
            raise serializers.ValidationError('磁力链接格式不正确')
        return value
    
    def validate(self, data):
        """验证数据"""
        # 检查是否已存在相同的磁力链接
        movie = data.get('movie')
        magnet_link = data.get('magnet_link')
        
        if MagnetLink.objects.filter(movie=movie, magnet_link=magnet_link).exists():
            raise serializers.ValidationError('该影片的磁力链接已存在')
        
        return data


class MagnetStatsSerializer(serializers.Serializer):
    """磁力链接统计序列化器"""
    
    total_magnets = serializers.IntegerField()
    active_magnets = serializers.IntegerField()
    verified_magnets = serializers.IntegerField()
    total_downloads = serializers.IntegerField()
    quality_distribution = serializers.DictField()
    top_uploaders = serializers.ListField()
    recent_magnets = serializers.IntegerField()
