"""
Movie filters for API.
"""

import django_filters
from django.db.models import Q
from .models import Movie, MovieSource


class MovieFilter(django_filters.FilterSet):
    """Movie filter set"""
    
    # 基础过滤
    source = django_filters.ChoiceFilter(choices=MovieSource.choices)
    
    # 日期范围过滤
    release_date_from = django_filters.DateFilter(field_name='release_date', lookup_expr='gte')
    release_date_to = django_filters.DateFilter(field_name='release_date', lookup_expr='lte')
    
    # 创建时间过滤
    created_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # 数值范围过滤
    view_count_min = django_filters.NumberFilter(field_name='view_count', lookup_expr='gte')
    view_count_max = django_filters.NumberFilter(field_name='view_count', lookup_expr='lte')
    
    # 文本搜索
    search = django_filters.CharFilter(method='filter_search')
    
    # 标签过滤
    has_tags = django_filters.BooleanFilter(method='filter_has_tags')
    tag = django_filters.CharFilter(field_name='tags__name', lookup_expr='icontains')
    
    # 演员过滤
    idol = django_filters.CharFilter(method='filter_idol')
    
    # 类型过滤
    genre = django_filters.CharFilter(method='filter_genre')
    
    # 磁力链接相关过滤
    has_magnets = django_filters.BooleanFilter(method='filter_has_magnets')
    quality = django_filters.CharFilter(method='filter_quality')
    has_subtitle = django_filters.BooleanFilter(method='filter_has_subtitle')
    
    class Meta:
        model = Movie
        fields = [
            'source', 'release_date_from', 'release_date_to',
            'created_from', 'created_to', 'view_count_min', 'view_count_max',
            'search', 'has_tags', 'tag', 'idol', 'genre',
            'has_magnets', 'quality', 'has_subtitle'
        ]
    
    def filter_search(self, queryset, name, value):
        """全文搜索"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(censored_id__icontains=value) |
            Q(movie_title__icontains=value) |
            Q(jav_idols__icontains=value) |
            Q(director__icontains=value) |
            Q(studio__icontains=value) |
            Q(genre__icontains=value)
        )
    
    def filter_has_tags(self, queryset, name, value):
        """是否有标签"""
        if value is True:
            return queryset.filter(tags__isnull=False).distinct()
        elif value is False:
            return queryset.filter(tags__isnull=True)
        return queryset
    
    def filter_idol(self, queryset, name, value):
        """演员过滤"""
        if not value:
            return queryset
        return queryset.filter(jav_idols__icontains=value)
    
    def filter_genre(self, queryset, name, value):
        """类型过滤"""
        if not value:
            return queryset
        return queryset.filter(genre__icontains=value)
    
    def filter_has_magnets(self, queryset, name, value):
        """是否有磁力链接"""
        if value is True:
            return queryset.filter(magnets__isnull=False, magnets__is_active=True).distinct()
        elif value is False:
            return queryset.filter(
                Q(magnets__isnull=True) | 
                Q(magnets__is_active=False)
            ).distinct()
        return queryset
    
    def filter_quality(self, queryset, name, value):
        """视频质量过滤"""
        if not value:
            return queryset
        return queryset.filter(magnets__quality=value, magnets__is_active=True).distinct()
    
    def filter_has_subtitle(self, queryset, name, value):
        """是否有字幕"""
        if value is not None:
            return queryset.filter(
                magnets__has_subtitle=value, 
                magnets__is_active=True
            ).distinct()
        return queryset
