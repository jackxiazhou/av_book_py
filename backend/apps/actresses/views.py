"""
Actress views for AVBook API.
"""

from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from .models import Actress
from .serializers import ActressSerializer, ActressDetailSerializer


class ActressPagination(PageNumberPagination):
    """自定义分页类"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class ActressViewSet(viewsets.ModelViewSet):
    """
    演员视图集
    """
    queryset = Actress.objects.all().order_by('id')
    serializer_class = ActressSerializer
    pagination_class = ActressPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['cup_size', 'height']
    search_fields = ['name', 'name_en']
    ordering_fields = ['id', 'name', 'height', 'debut_date']
    ordering = ['id']

    def get_serializer_class(self):
        """根据action选择序列化器"""
        if self.action == 'retrieve':
            return ActressDetailSerializer
        return ActressSerializer

    def get_queryset(self):
        """获取查询集，支持自定义筛选，优先显示有照片的女友"""
        queryset = Actress.objects.all()

        # 按照片类型筛选
        has_photos = self.request.query_params.get('hasPhotos', None)
        if has_photos == 'lifestyle':
            queryset = queryset.exclude(
                Q(lifestyle_photos__isnull=True) | Q(lifestyle_photos='')
            )
        elif has_photos == 'portrait':
            queryset = queryset.exclude(
                Q(portrait_photos__isnull=True) | Q(portrait_photos='')
            )
        elif has_photos == 'both':
            queryset = queryset.exclude(
                Q(lifestyle_photos__isnull=True) | Q(lifestyle_photos='')
            ).exclude(
                Q(portrait_photos__isnull=True) | Q(portrait_photos='')
            )
        # 不再按照片排序，因为大部分女友没有真实照片

        # 按身高范围筛选
        height_range = self.request.query_params.get('heightRange', None)
        if height_range == 'short':  # 150-160cm
            queryset = queryset.filter(height__gte=150, height__lte=160)
        elif height_range == 'medium':  # 160-170cm
            queryset = queryset.filter(height__gte=160, height__lte=170)
        elif height_range == 'tall':  # 170cm+
            queryset = queryset.filter(height__gte=170)

        # 按罩杯筛选
        cup_size = self.request.query_params.get('cup_size', None)
        if cup_size:
            queryset = queryset.filter(cup_size__icontains=cup_size)

        # 默认按ID排序
        return queryset.order_by('id')

    @action(detail=True, methods=['get'])
    def movies(self, request, pk=None):
        """获取演员的作品列表"""
        actress = self.get_object()
        movies = actress.movies.all().order_by('-release_date')
        
        # 简单的分页
        page_size = int(request.query_params.get('page_size', 10))
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        movies_data = []
        for movie in movies[start:end]:
            movies_data.append({
                'id': movie.id,
                'censored_id': movie.censored_id,
                'movie_title': movie.movie_title,
                'release_date': movie.release_date,
                'studio': movie.studio,
                'cover_image': movie.cover_image,
                'duration_minutes': movie.duration_minutes,
                'movie_tags': movie.movie_tags,
                'sample_images': movie.sample_images.split('\n') if movie.sample_images else [],
            })
        
        return Response({
            'count': movies.count(),
            'results': movies_data,
            'page': page,
            'page_size': page_size,
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取演员统计信息"""
        total_count = Actress.objects.count()
        with_photos = Actress.objects.exclude(
            Q(profile_image__isnull=True) | Q(profile_image='')
        ).count()
        with_lifestyle_photos = Actress.objects.exclude(
            Q(lifestyle_photos__isnull=True) | Q(lifestyle_photos='')
        ).count()
        with_portrait_photos = Actress.objects.exclude(
            Q(portrait_photos__isnull=True) | Q(portrait_photos='')
        ).count()
        
        return Response({
            'total_count': total_count,
            'with_photos': with_photos,
            'with_lifestyle_photos': with_lifestyle_photos,
            'with_portrait_photos': with_portrait_photos,
            'photo_coverage': (with_photos / total_count * 100) if total_count > 0 else 0,
        })
