"""
女友/演员模型
"""

from django.db import models
from django.urls import reverse
from django.utils import timezone


class Actress(models.Model):
    """女友/演员模型"""
    
    # 基本信息
    name = models.CharField(
        max_length=100,
        verbose_name='姓名',
        help_text='女友/演员的姓名'
    )
    
    name_en = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='英文名',
        help_text='英文或罗马音姓名'
    )
    
    alias = models.TextField(
        blank=True,
        verbose_name='别名',
        help_text='其他别名，用逗号分隔'
    )
    
    # 个人信息
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='出生日期'
    )
    
    height = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='身高(cm)'
    )
    
    weight = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='体重(kg)'
    )
    
    measurements = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='三围',
        help_text='例如：B88-W58-H85'
    )
    
    cup_size = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='罩杯'
    )
    
    blood_type = models.CharField(
        max_length=5,
        blank=True,
        verbose_name='血型'
    )
    
    nationality = models.CharField(
        max_length=50,
        default='日本',
        verbose_name='国籍'
    )
    
    # 职业信息
    debut_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='出道日期'
    )
    
    retirement_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='引退日期'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否活跃'
    )
    
    agency = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='所属事务所'
    )
    
    # 图片
    profile_image = models.URLField(
        blank=True,
        max_length=500,
        verbose_name='头像',
        help_text='个人头像图片URL'
    )
    
    cover_image = models.URLField(
        blank=True,
        max_length=500,
        verbose_name='封面图片',
        help_text='个人封面图片URL'
    )
    
    gallery_images = models.TextField(
        blank=True,
        verbose_name='图片集',
        help_text='多张图片URL，用换行分隔'
    )

    # 新增字段：生活照/写真照
    lifestyle_photos = models.TextField(
        blank=True,
        verbose_name='生活照',
        help_text='生活照片URL，用换行分隔'
    )

    portrait_photos = models.TextField(
        blank=True,
        verbose_name='写真照',
        help_text='写真照片URL，用换行分隔'
    )

    # 本地图片路径字段
    profile_image_local = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='本地头像路径',
        help_text='本地头像图片路径'
    )

    cover_image_local = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='本地封面路径',
        help_text='本地封面图片路径'
    )

    lifestyle_photos_local = models.TextField(
        blank=True,
        verbose_name='本地生活照路径',
        help_text='本地生活照片路径，用换行分隔'
    )

    portrait_photos_local = models.TextField(
        blank=True,
        verbose_name='本地写真照路径',
        help_text='本地写真照片路径，用换行分隔'
    )
    
    # 描述信息
    description = models.TextField(
        blank=True,
        verbose_name='个人简介'
    )
    
    specialties = models.TextField(
        blank=True,
        verbose_name='特长/特色',
        help_text='个人特色、擅长类型等'
    )
    
    # 社交媒体
    twitter = models.URLField(
        blank=True,
        verbose_name='Twitter'
    )
    
    instagram = models.URLField(
        blank=True,
        verbose_name='Instagram'
    )
    
    blog = models.URLField(
        blank=True,
        verbose_name='博客/官网'
    )
    
    # 统计信息
    popularity_score = models.PositiveIntegerField(
        default=0,
        verbose_name='人气值'
    )
    
    view_count = models.PositiveIntegerField(
        default=0,
        verbose_name='浏览次数'
    )
    
    favorite_count = models.PositiveIntegerField(
        default=0,
        verbose_name='收藏次数'
    )
    
    movie_count = models.PositiveIntegerField(
        default=0,
        verbose_name='作品数量'
    )

    # 爬取状态
    movies_crawled = models.BooleanField(
        default=False,
        verbose_name='是否已爬取作品'
    )

    crawl_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='爬取日期'
    )

    # 新增爬取相关字段
    source_url = models.URLField(
        blank=True,
        max_length=500,
        verbose_name='来源URL',
        help_text='女友详情页URL'
    )

    last_crawled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='最后爬取时间'
    )

    crawl_count = models.PositiveIntegerField(
        default=0,
        verbose_name='爬取次数'
    )

    crawl_depth = models.PositiveIntegerField(
        default=0,
        verbose_name='爬取深度',
        help_text='在递归爬取中的深度层级'
    )

    # 元数据
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    class Meta:
        verbose_name = '女友/演员'
        verbose_name_plural = '女友/演员管理'
        ordering = ['-popularity_score', '-created_at']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('actress-detail', kwargs={'pk': self.pk})
    
    @property
    def age(self):
        """计算年龄"""
        if self.birth_date:
            today = timezone.now().date()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None
    
    @property
    def career_years(self):
        """计算从业年数"""
        if self.debut_date:
            end_date = self.retirement_date or timezone.now().date()
            return end_date.year - self.debut_date.year
        return None
    
    @property
    def status(self):
        """获取状态"""
        if self.retirement_date:
            return '已引退'
        elif self.is_active:
            return '活跃'
        else:
            return '暂停活动'
    
    def get_gallery_images_list(self):
        """获取图片集列表"""
        if self.gallery_images:
            return [img.strip() for img in self.gallery_images.split('\n') if img.strip()]
        return []
    
    def increment_view_count(self):
        """增加浏览次数"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_favorite_count(self):
        """增加收藏次数"""
        self.favorite_count += 1
        self.save(update_fields=['favorite_count'])
    
    def update_movie_count(self):
        """更新作品数量"""
        from apps.movies.models import Movie
        self.movie_count = Movie.objects.filter(jav_idols__icontains=self.name).count()
        self.save(update_fields=['movie_count'])


class ActressTag(models.Model):
    """女友/演员标签"""
    
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='标签名称'
    )
    
    slug = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name='标签别名'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='标签描述'
    )
    
    color = models.CharField(
        max_length=7,
        default='#007bff',
        verbose_name='标签颜色',
        help_text='十六进制颜色代码，如 #007bff'
    )
    
    actresses = models.ManyToManyField(
        'Actress',
        related_name='tags',
        blank=True,
        verbose_name='关联女友'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    class Meta:
        verbose_name = '女友标签'
        verbose_name_plural = '女友标签管理'
        ordering = ['name']
    
    def __str__(self):
        return self.name
