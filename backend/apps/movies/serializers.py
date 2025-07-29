"""
Movie serializers for AVBook API.
"""

from rest_framework import serializers
from .models import Movie, MovieTag, MovieRating


class MovieTagSerializer(serializers.ModelSerializer):
    """影片标签序列化器"""
    
    movie_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MovieTag
        fields = ['id', 'name', 'slug', 'description', 'color', 'movie_count', 'created_at']
    
    def get_movie_count(self, obj):
        """获取标签下的影片数量"""
        return obj.movies.count()


class MovieRatingSerializer(serializers.ModelSerializer):
    """影片评分序列化器"""
    
    movie_title = serializers.CharField(source='movie.movie_title', read_only=True)
    movie_censored_id = serializers.CharField(source='movie.censored_id', read_only=True)
    
    class Meta:
        model = MovieRating
        fields = [
            'id', 'movie_title', 'movie_censored_id', 'average_rating', 'total_votes',
            'five_star', 'four_star', 'three_star', 'two_star', 'one_star', 'updated_at'
        ]


class MovieSerializer(serializers.ModelSerializer):
    """影片序列化器（列表视图）"""

    tags = MovieTagSerializer(many=True, read_only=True)
    rating = MovieRatingSerializer(read_only=True)
    magnet_count = serializers.SerializerMethodField()
    genre_list = serializers.ReadOnlyField()
    idol_list = serializers.ReadOnlyField()
    actresses = serializers.SerializerMethodField()
    sample_images_list = serializers.SerializerMethodField()
    sample_images_local_list = serializers.SerializerMethodField()
    movie_tags_list = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        fields = [
            'id', 'censored_id', 'movie_title', 'movie_pic_cover', 'cover_image',
            'cover_image_local', 'release_date', 'studio', 'duration_minutes',
            'movie_tags', 'sample_images', 'sample_images_local',
            'source', 'view_count', 'download_count', 'actresses', 'sample_images_list',
            'sample_images_local_list', 'movie_tags_list', 'tags', 'rating',
            'magnet_count', 'genre_list', 'idol_list', 'created_at', 'updated_at'
        ]
    
    def get_magnet_count(self, obj):
        """获取磁力链接数量"""
        return obj.magnets.filter(is_active=True).count()

    def get_actresses(self, obj):
        """获取演员信息"""
        return [{
            'id': actress.id,
            'name': actress.name,
            'profile_image': actress.profile_image,
            'profile_image_local': actress.profile_image_local,
            'cup_size': actress.cup_size,
            'height': actress.height,
            'birth_date': actress.birth_date,
        } for actress in obj.actresses.all()]

    def get_sample_images_list(self, obj):
        """获取样品图片列表"""
        if obj.sample_images:
            return [url.strip() for url in obj.sample_images.split('\n') if url.strip()]
        return []

    def get_sample_images_local_list(self, obj):
        """获取本地样品图片列表"""
        if obj.sample_images_local:
            return [url.strip() for url in obj.sample_images_local.split('\n') if url.strip()]
        return []

    def get_movie_tags_list(self, obj):
        """获取作品标签列表"""
        if obj.movie_tags:
            return [tag.strip() for tag in obj.movie_tags.split(',') if tag.strip()]
        return []


class MovieDetailSerializer(serializers.ModelSerializer):
    """影片详情序列化器"""

    tags = MovieTagSerializer(many=True, read_only=True)
    rating = MovieRatingSerializer(read_only=True)
    magnets = serializers.SerializerMethodField()
    genre_list = serializers.ReadOnlyField()
    idol_list = serializers.ReadOnlyField()
    actresses = serializers.SerializerMethodField()
    sample_images_list = serializers.SerializerMethodField()
    sample_images_local_list = serializers.SerializerMethodField()
    movie_tags_list = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        fields = [
            'id', 'censored_id', 'movie_title', 'movie_pic_cover', 'cover_image',
            'cover_image_local', 'release_date', 'movie_length', 'director', 'studio',
            'label', 'series', 'genre', 'jav_idols', 'source', 'code_36', 'view_count',
            'download_count', 'sample_images', 'sample_images_local', 'movie_tags',
            'duration_minutes', 'tags', 'rating', 'magnets', 'genre_list', 'idol_list',
            'actresses', 'sample_images_list', 'sample_images_local_list', 'movie_tags_list',
            'created_at', 'updated_at'
        ]
    
    def get_magnets(self, obj):
        """获取磁力链接信息"""
        from apps.magnets.serializers import MagnetLinkSerializer
        magnets = obj.magnets.filter(is_active=True).order_by('-seeders', '-created_at')[:10]
        return MagnetLinkSerializer(magnets, many=True).data

    def get_actresses(self, obj):
        """获取演员信息"""
        return [{
            'id': actress.id,
            'name': actress.name,
            'profile_image': actress.profile_image,
            'profile_image_local': actress.profile_image_local,
            'cup_size': actress.cup_size,
            'height': actress.height,
            'birth_date': actress.birth_date,
        } for actress in obj.actresses.all()]

    def get_sample_images_list(self, obj):
        """获取样品图片列表"""
        if obj.sample_images:
            return [url.strip() for url in obj.sample_images.split('\n') if url.strip()]
        return []

    def get_sample_images_local_list(self, obj):
        """获取本地样品图片列表"""
        if obj.sample_images_local:
            return [url.strip() for url in obj.sample_images_local.split('\n') if url.strip()]
        return []

    def get_movie_tags_list(self, obj):
        """获取作品标签列表"""
        if obj.movie_tags:
            return [tag.strip() for tag in obj.movie_tags.split(',') if tag.strip()]
        return []


class MovieStatsSerializer(serializers.Serializer):
    """影片统计序列化器"""
    
    total_movies = serializers.IntegerField()
    total_magnets = serializers.IntegerField()
    sources = serializers.ListField()
    recent_movies = serializers.IntegerField()
    top_genres = serializers.ListField()
    top_idols = serializers.ListField()


class MovieCreateSerializer(serializers.ModelSerializer):
    """影片创建序列化器"""
    
    class Meta:
        model = Movie
        fields = [
            'censored_id', 'movie_title', 'movie_pic_cover',
            'release_date', 'movie_length', 'director', 'studio', 'label', 'series',
            'genre', 'jav_idols', 'source'
        ]
    
    def validate_censored_id(self, value):
        """验证影片编号"""
        if Movie.objects.filter(censored_id=value).exists():
            raise serializers.ValidationError('该影片编号已存在')
        return value
    
    def create(self, validated_data):
        """创建影片"""
        movie = Movie.objects.create(**validated_data)
        
        # 创建评分记录
        MovieRating.objects.create(movie=movie)
        
        return movie


class MovieUpdateSerializer(serializers.ModelSerializer):
    """影片更新序列化器"""
    
    class Meta:
        model = Movie
        fields = [
            'movie_title', 'movie_pic_cover', 'release_date', 'movie_length',
            'director', 'studio', 'label', 'series', 'genre', 'jav_idols'
        ]
    
    def update(self, instance, validated_data):
        """更新影片"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
