"""
Magnet views for AVBook API.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta

from .models import MagnetLink, MagnetCategory, DownloadHistory
from .serializers import (
    MagnetLinkSerializer, MagnetLinkDetailSerializer, 
    MagnetCategorySerializer, DownloadHistorySerializer
)


class MagnetLinkViewSet(viewsets.ReadOnlyModelViewSet):
    """磁力链接视图集"""
    
    queryset = MagnetLink.objects.select_related('movie').prefetch_related('categories')
    serializer_class = MagnetLinkSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['quality', 'has_subtitle', 'is_active', 'is_verified', 'movie__source']
    search_fields = ['magnet_name', 'movie__censored_id', 'movie__movie_title', 'uploader']
    ordering_fields = ['created_at', 'seeders', 'leechers', 'health_score', 'download_count']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'retrieve':
            return MagnetLinkDetailSerializer
        return MagnetLinkSerializer
    
    def get_queryset(self):
        """获取查询集"""
        queryset = super().get_queryset()
        
        # 默认只显示活跃的磁力链接
        if not self.request.query_params.get('include_inactive'):
            queryset = queryset.filter(is_active=True)
        
        # 按健康度过滤
        min_health = self.request.query_params.get('min_health')
        if min_health:
            try:
                min_health = int(min_health)
                # 这里需要在数据库层面计算健康度，暂时用简单的过滤
                queryset = queryset.filter(seeders__gte=1)
            except ValueError:
                pass
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """记录下载"""
        magnet = self.get_object()
        
        # 记录下载历史
        DownloadHistory.objects.create(
            magnet=magnet,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # 增加下载次数
        magnet.increment_download_count()
        
        return Response({
            'message': '下载记录已保存',
            'magnet_link': magnet.magnet_link,
            'download_count': magnet.download_count
        })
    
    @action(detail=True, methods=['post'])
    def click(self, request, pk=None):
        """记录点击"""
        magnet = self.get_object()
        magnet.increment_click_count()
        
        return Response({
            'message': '点击记录已保存',
            'click_count': magnet.click_count
        })
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """获取热门磁力链接"""
        queryset = self.get_queryset().filter(
            is_active=True
        ).order_by('-download_count', '-seeders')[:20]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def high_quality(self, request):
        """获取高质量磁力链接"""
        queryset = self.get_queryset().filter(
            is_active=True,
            quality__in=['fhd', 'uhd'],
            seeders__gte=5
        ).order_by('-seeders', '-created_at')[:20]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取磁力链接统计信息"""
        queryset = self.get_queryset()
        
        stats = {
            'total_magnets': queryset.count(),
            'active_magnets': queryset.filter(is_active=True).count(),
            'verified_magnets': queryset.filter(is_verified=True).count(),
            'total_downloads': sum(magnet.download_count for magnet in queryset),
            'quality_distribution': dict(
                queryset.values_list('quality').annotate(count=Count('id'))
            ),
            'top_uploaders': list(
                queryset.exclude(uploader='').values('uploader')
                .annotate(count=Count('id')).order_by('-count')[:10]
            ),
            'recent_magnets': queryset.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
        }
        
        return Response(stats)
    
    def get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class MagnetCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """磁力分类视图集"""
    
    queryset = MagnetCategory.objects.all()
    serializer_class = MagnetCategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['get'])
    def magnets(self, request, pk=None):
        """获取分类下的磁力链接"""
        category = self.get_object()
        magnets = category.magnets.filter(is_active=True).order_by('-created_at')
        
        # 分页
        page = self.paginate_queryset(magnets)
        if page is not None:
            serializer = MagnetLinkSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = MagnetLinkSerializer(magnets, many=True)
        return Response(serializer.data)


class DownloadHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """下载历史视图集"""
    
    queryset = DownloadHistory.objects.select_related('magnet__movie')
    serializer_class = DownloadHistorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['magnet__movie__source', 'magnet__quality']
    ordering_fields = ['download_time']
    ordering = ['-download_time']
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """获取最近下载"""
        queryset = self.get_queryset().order_by('-download_time')[:50]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取下载统计"""
        queryset = self.get_queryset()
        
        stats = {
            'total_downloads': queryset.count(),
            'today_downloads': queryset.filter(
                download_time__date=timezone.now().date()
            ).count(),
            'week_downloads': queryset.filter(
                download_time__gte=timezone.now() - timedelta(days=7)
            ).count(),
            'popular_movies': list(
                queryset.values('magnet__movie__censored_id', 'magnet__movie__movie_title')
                .annotate(count=Count('id')).order_by('-count')[:10]
            ),
        }
        
        return Response(stats)
