"""
Django admin configuration for magnets app.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import MagnetLink, MagnetCategory, DownloadHistory


@admin.register(MagnetLink)
class MagnetLinkAdmin(admin.ModelAdmin):
    """Magnet link admin configuration"""
    
    list_display = [
        'magnet_name', 'movie', 'quality', 'file_size_display', 
        'seeders', 'leechers', 'health_indicator', 'is_active', 'created_at'
    ]
    list_filter = [
        'quality', 'has_subtitle', 'is_active', 'is_verified', 
        'created_at', 'movie__source'
    ]
    search_fields = [
        'magnet_name', 'movie__censored_id', 'movie__movie_title', 'uploader'
    ]
    readonly_fields = [
        'health_score', 'download_count', 'click_count', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('movie', 'magnet_name', 'magnet_link')
        }),
        ('文件信息', {
            'fields': ('file_size', 'file_size_bytes', 'quality', 'has_subtitle', 'subtitle_language')
        }),
        ('种子信息', {
            'fields': ('seeders', 'leechers', 'completed', 'publish_date', 'uploader')
        }),
        ('状态信息', {
            'fields': ('is_active', 'is_verified', 'last_checked')
        }),
        ('统计信息', {
            'fields': ('health_score', 'download_count', 'click_count'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    filter_horizontal = ['categories']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def health_indicator(self, obj):
        """健康度指示器"""
        score = obj.health_score
        if score >= 80:
            color = 'green'
            icon = '🟢'
        elif score >= 60:
            color = 'orange'
            icon = '🟡'
        else:
            color = 'red'
            icon = '🔴'
        
        return format_html(
            '<span style="color: {};">{} {}%</span>',
            color, icon, score
        )
    health_indicator.short_description = '健康度'
    
    def file_size_display(self, obj):
        """文件大小显示"""
        return obj.get_file_size_display()
    file_size_display.short_description = '文件大小'


@admin.register(MagnetCategory)
class MagnetCategoryAdmin(admin.ModelAdmin):
    """Magnet category admin configuration"""
    
    list_display = ['name', 'color_display', 'get_magnet_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    
    def color_display(self, obj):
        """颜色显示"""
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = '颜色'
    
    def get_magnet_count(self, obj):
        return obj.magnets.filter(is_active=True).count()
    get_magnet_count.short_description = '磁力数量'


@admin.register(DownloadHistory)
class DownloadHistoryAdmin(admin.ModelAdmin):
    """Download history admin configuration"""
    
    list_display = [
        'magnet', 'get_movie_title', 'ip_address', 'download_time'
    ]
    list_filter = ['download_time', 'magnet__movie__source']
    search_fields = [
        'magnet__magnet_name', 'magnet__movie__censored_id', 
        'magnet__movie__movie_title', 'ip_address'
    ]
    readonly_fields = ['download_time']
    date_hierarchy = 'download_time'
    ordering = ['-download_time']
    
    def get_movie_title(self, obj):
        return obj.magnet.movie.censored_id
    get_movie_title.short_description = '影片编号'
    
    def has_add_permission(self, request):
        # 禁止手动添加下载历史
        return False
