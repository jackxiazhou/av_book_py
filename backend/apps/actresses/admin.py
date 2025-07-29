"""
女友/演员管理的Django Admin配置
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Actress, ActressTag


@admin.register(Actress)
class ActressAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'name_en', 'get_profile_image', 'age', 'status', 
        'movie_count', 'popularity_score', 'view_count', 'created_at'
    ]
    
    list_filter = [
        'is_active', 'nationality', 'blood_type', 'created_at',
        'debut_date', 'retirement_date'
    ]
    
    search_fields = ['name', 'name_en', 'alias', 'agency']
    
    readonly_fields = [
        'view_count', 'favorite_count', 'movie_count', 'created_at', 
        'updated_at', 'get_profile_image_large', 'get_cover_image_large',
        'get_gallery_preview', 'get_tags_display'
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'name_en', 'alias', 'nationality')
        }),
        ('个人资料', {
            'fields': (
                'birth_date', 'height', 'weight', 'measurements', 
                'cup_size', 'blood_type'
            )
        }),
        ('职业信息', {
            'fields': (
                'debut_date', 'retirement_date', 'is_active', 'agency'
            )
        }),
        ('图片信息', {
            'fields': (
                'profile_image', 'get_profile_image_large',
                'cover_image', 'get_cover_image_large',
                'gallery_images', 'get_gallery_preview'
            )
        }),
        ('描述信息', {
            'fields': ('description', 'specialties')
        }),
        ('社交媒体', {
            'fields': ('twitter', 'instagram', 'blog')
        }),
        ('标签管理', {
            'fields': ('get_tags_display',)
        }),
        ('统计信息', {
            'fields': (
                'popularity_score', 'view_count', 'favorite_count', 'movie_count'
            )
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-popularity_score', '-created_at']
    
    def get_profile_image(self, obj):
        """显示小头像"""
        if obj.profile_image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 50%;" />',
                obj.profile_image
            )
        return '无头像'
    get_profile_image.short_description = '头像'
    
    def get_profile_image_large(self, obj):
        """显示大头像"""
        if obj.profile_image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px; object-fit: cover;" />',
                obj.profile_image
            )
        return '无头像'
    get_profile_image_large.short_description = '头像预览'
    
    def get_cover_image_large(self, obj):
        """显示封面图片"""
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 200px; object-fit: cover;" />',
                obj.cover_image
            )
        return '无封面'
    get_cover_image_large.short_description = '封面预览'
    
    def get_gallery_preview(self, obj):
        """显示图片集预览"""
        images = obj.get_gallery_images_list()
        if images:
            html = '<div style="display: flex; flex-wrap: wrap; gap: 5px;">'
            for i, img in enumerate(images[:6]):  # 最多显示6张
                html += f'<img src="{img}" style="width: 80px; height: 80px; object-fit: cover;" />'
            if len(images) > 6:
                html += f'<div style="width: 80px; height: 80px; background: #f0f0f0; display: flex; align-items: center; justify-content: center;">+{len(images)-6}</div>'
            html += '</div>'
            return format_html(html)
        return '无图片'
    get_gallery_preview.short_description = '图片集预览'
    
    def get_tags_display(self, obj):
        """显示标签"""
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
    
    def age(self, obj):
        """显示年龄"""
        return f'{obj.age}岁' if obj.age else '未知'
    age.short_description = '年龄'
    
    def status(self, obj):
        """显示状态"""
        return obj.status
    status.short_description = '状态'
    
    actions = ['update_movie_counts']
    
    def update_movie_counts(self, request, queryset):
        """批量更新作品数量"""
        for actress in queryset:
            actress.update_movie_count()
        self.message_user(request, f'已更新 {queryset.count()} 位女友的作品数量')
    update_movie_counts.short_description = '更新作品数量'


@admin.register(ActressTag)
class ActressTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'get_color_display', 'get_actress_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['actresses']
    
    def get_color_display(self, obj):
        """显示颜色"""
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            obj.color, obj.color
        )
    get_color_display.short_description = '颜色'
    
    def get_actress_count(self, obj):
        """显示关联女友数量"""
        return obj.actresses.count()
    get_actress_count.short_description = '关联女友数'
