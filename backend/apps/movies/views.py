"""
Movie views for AVBook API.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta

from .models import Movie, MovieTag, MovieRating
from .serializers import (
    MovieSerializer, MovieDetailSerializer, MovieTagSerializer,
    MovieRatingSerializer
)
from .filters import MovieFilter
from .pagination import MoviePagination


class MovieViewSet(viewsets.ReadOnlyModelViewSet):
    """影片视图集"""

    queryset = Movie.objects.select_related('rating').prefetch_related('tags', 'magnets')
    serializer_class = MovieSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = MoviePagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = MovieFilter
    search_fields = ['censored_id', 'movie_title', 'jav_idols', 'director', 'studio']
    ordering_fields = ['created_at', 'release_date', 'view_count', 'download_count']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'retrieve':
            return MovieDetailSerializer
        return MovieSerializer

    def retrieve(self, request, *args, **kwargs):
        """获取单个影片详情"""
        instance = self.get_object()

        # 增加浏览次数
        instance.increment_view_count()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def magnets(self, request, pk=None):
        """获取影片的磁力链接"""
        movie = self.get_object()
        magnets = movie.magnets.filter(is_active=True).order_by('-seeders', '-created_at')

        from apps.magnets.serializers import MagnetLinkSerializer
        serializer = MagnetLinkSerializer(magnets, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """为影片评分"""
        movie = self.get_object()
        rating_value = request.data.get('rating')

        if not rating_value or not (1 <= int(rating_value) <= 5):
            return Response(
                {'error': '评分必须在1-5之间'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 获取或创建评分记录
        rating, created = MovieRating.objects.get_or_create(movie=movie)

        # 更新评分
        rating_field = f"{['one', 'two', 'three', 'four', 'five'][int(rating_value) - 1]}_star"
        setattr(rating, rating_field, getattr(rating, rating_field) + 1)
        rating.calculate_average()

        serializer = MovieRatingSerializer(rating)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """获取热门影片"""
        # 最近30天浏览量最高的影片
        thirty_days_ago = timezone.now() - timedelta(days=30)
        queryset = self.get_queryset().filter(
            created_at__gte=thirty_days_ago
        ).order_by('-view_count')[:20]

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """获取最新影片"""
        queryset = self.get_queryset().order_by('-created_at')[:20]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def random(self, request):
        """获取随机影片"""
        count = int(request.query_params.get('count', 10))
        count = min(count, 50)  # 限制最大数量

        queryset = self.get_queryset().order_by('?')[:count]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取影片统计信息"""
        queryset = self.get_queryset()

        stats = {
            'total_movies': queryset.count(),
            'total_magnets': sum(movie.magnets.count() for movie in queryset),
            'sources': list(queryset.values('source').annotate(count=Count('id'))),
            'recent_movies': queryset.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
            'top_genres': self._get_top_genres(queryset),
            'top_idols': self._get_top_idols(queryset),
        }

        return Response(stats)

    def _get_top_genres(self, queryset, limit=10):
        """获取热门类型"""
        genre_counts = {}
        for movie in queryset:
            for genre in movie.genre_list:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1

        return sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    def _get_top_idols(self, queryset, limit=10):
        """获取热门演员"""
        idol_counts = {}
        for movie in queryset:
            for idol in movie.idol_list:
                idol_counts[idol] = idol_counts.get(idol, 0) + 1

        return sorted(idol_counts.items(), key=lambda x: x[1], reverse=True)[:limit]


class MovieTagViewSet(viewsets.ReadOnlyModelViewSet):
    """影片标签视图集"""

    queryset = MovieTag.objects.all()
    serializer_class = MovieTagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @action(detail=True, methods=['get'])
    def movies(self, request, pk=None):
        """获取标签下的影片"""
        tag = self.get_object()
        movies = tag.movies.all().order_by('-created_at')

        # 分页
        page = self.paginate_queryset(movies)
        if page is not None:
            serializer = MovieSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MovieSerializer(movies, many=True)
        return Response(serializer.data)


class MovieRatingViewSet(viewsets.ReadOnlyModelViewSet):
    """影片评分视图集"""

    queryset = MovieRating.objects.select_related('movie')
    serializer_class = MovieRatingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['average_rating', 'total_votes']
    ordering = ['-average_rating']

    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        """获取评分最高的影片"""
        queryset = self.get_queryset().filter(
            total_votes__gte=5  # 至少5个评分
        ).order_by('-average_rating')[:20]

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

