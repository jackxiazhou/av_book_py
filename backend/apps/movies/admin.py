"""
Django admin configuration for movies app.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Movie, MovieTag, MovieRating


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    """Movie admin configuration"""
    
    list_display = [
        'censored_id', 'movie_title', 'source', 'release_date', 
        'view_count', 'download_count', 'created_at'
    ]
    list_filter = ['source', 'release_date', 'created_at']
    search_fields = ['censored_id', 'movie_title', 'jav_idols', 'director', 'studio']
    readonly_fields = ['code_36', 'view_count', 'download_count', 'created_at', 'updated_at', 'get_tags_display', 'get_tag_management_link', 'get_actresses_display', 'get_sample_images_preview']

    filter_horizontal = ['actresses']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('censored_id', 'movie_title', 'movie_pic_cover', 'source')
        }),
        ('详细信息', {
            'fields': ('release_date', 'movie_length', 'director', 'studio', 'label', 'series')
        }),
        ('分类标签', {
            'fields': ('genre', 'jav_idols', 'movie_tags', 'get_tags_display', 'get_tag_management_link')
        }),
        ('女友关联', {
            'fields': ('actresses', 'get_actresses_display')
        }),
        ('样例图片', {
            'fields': ('sample_images', 'get_sample_images_preview'),
            'classes': ('collapse',)
        }),
        ('统计信息', {
            'fields': ('code_36', 'view_count', 'download_count'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # filter_horizontal = ['tags']  # 暂时禁用，因为Django admin无法识别反向关系
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def get_tags_display(self, obj):
        """显示影片的标签"""
        try:
            tags = obj.tags.all()
            if tags:
                tag_html = []
                for tag in tags:
                    tag_html.append(
                        f'<span style="background-color: {tag.color}; color: white; '
                        f'padding: 2px 6px; border-radius: 3px; margin-right: 3px;">'
                        f'{tag.name}</span>'
                    )
                return format_html(''.join(tag_html))
            return '无标签'
        except Exception as e:
            return f'错误: {e}'
    get_tags_display.short_description = '标签'
    get_tags_display.allow_tags = True

    def get_tag_management_link(self, obj):
        """提供标签管理链接"""
        if obj.pk:
            return format_html(
                '<a href="/admin/movies/movietag/" target="_blank" '
                'style="background: #007cba; color: white; padding: 5px 10px; '
                'text-decoration: none; border-radius: 3px;">管理标签</a>'
            )
        return '保存后可管理标签'
    get_tag_management_link.short_description = '标签管理'

    def get_actresses_display(self, obj):
        """显示关联女友"""
        try:
            actresses = obj.actresses.all()
            if actresses:
                actress_html = []
                for actress in actresses:
                    actress_html.append(
                        f'<a href="/admin/actresses/actress/{actress.pk}/change/" '
                        f'style="background: #28a745; color: white; padding: 2px 6px; '
                        f'border-radius: 3px; margin-right: 3px; text-decoration: none;">'
                        f'{actress.name}</a>'
                    )
                return format_html(''.join(actress_html))
            return '无关联女友'
        except Exception as e:
            return f'错误: {e}'
    get_actresses_display.short_description = '关联女友'

    def get_sample_images_preview(self, obj):
        """显示样例图片预览"""
        try:
            images = obj.sample_images_list
            if images:
                html = '<div style="display: flex; flex-wrap: wrap; gap: 5px;">'
                for i, img in enumerate(images[:6]):  # 最多显示6张
                    html += f'<img src="{img}" style="width: 80px; height: 60px; object-fit: cover; border-radius: 3px;" />'
                if len(images) > 6:
                    html += f'<div style="width: 80px; height: 60px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; border-radius: 3px;">+{len(images)-6}</div>'
                html += '</div>'
                return format_html(html)
            return '无样例图片'
        except Exception as e:
            return f'错误: {e}'
    get_sample_images_preview.short_description = '样例图片预览'


@admin.register(MovieTag)
class MovieTagAdmin(admin.ModelAdmin):
    """Movie tag admin configuration"""
    
    list_display = ['name', 'slug', 'color', 'get_movie_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at']
    
    def get_movie_count(self, obj):
        return obj.movies.count()
    get_movie_count.short_description = '影片数量'


@admin.register(MovieRating)
class MovieRatingAdmin(admin.ModelAdmin):
    """Movie rating admin configuration"""
    
    list_display = [
        'movie', 'average_rating', 'total_votes', 
        'five_star', 'four_star', 'three_star', 'two_star', 'one_star',
        'updated_at'
    ]
    list_filter = ['average_rating', 'total_votes', 'updated_at']
    search_fields = ['movie__censored_id', 'movie__movie_title']
    readonly_fields = ['updated_at']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # 编辑现有对象时
            return self.readonly_fields + ['movie']
        return self.readonly_fields
