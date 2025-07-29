"""
Movie models for AVBook application.
"""
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.urls import reverse


class MovieSource(models.TextChoices):
    """影片来源选择"""
    AVMOO = 'avmoo', 'Avmoo'
    JAVBUS = 'javbus', 'Javbus'
    JAVLIBRARY = 'javlibrary', 'Javlibrary'


class Movie(models.Model):
    """影片模型"""
    
    # 基础信息
    censored_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z0-9]+-\d+$',
                message='影片编号格式不正确，应为类似 YMLW-047 的格式'
            )
        ],
        verbose_name='影片编号',
        help_text='影片的唯一编号，如 YMLW-047'
    )
    
    movie_title = models.TextField(
        blank=True,
        verbose_name='影片标题',
        help_text='影片的完整标题'
    )
    
    movie_pic_cover = models.URLField(
        blank=True,
        max_length=500,
        verbose_name='封面图片',
        help_text='影片封面图片URL'
    )
    
    # 详细信息
    release_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='发行日期'
    )
    
    movie_length = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='影片时长',
        help_text='如: 120分钟'
    )

    # 新增字段：时长（分钟数）
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='时长(分钟)',
        help_text='影片时长，以分钟为单位'
    )

    # 新增字段：作品封面
    cover_image = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='作品封面',
        help_text='作品封面图片URL'
    )

    # 本地图片路径字段
    cover_image_local = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='本地封面路径',
        help_text='本地封面图片路径'
    )

    sample_images_local = models.TextField(
        blank=True,
        verbose_name='本地样品图路径',
        help_text='本地样品图片路径，用换行分隔'
    )
    
    director = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='导演'
    )
    
    studio = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='制作商'
    )
    
    label = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='发行商'
    )
    
    series = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='系列'
    )
    
    # 分类和标签
    genre = models.TextField(
        blank=True,
        verbose_name='类型',
        help_text='多个类型用逗号分隔'
    )
    
    jav_idols = models.TextField(
        blank=True,
        verbose_name='演员',
        help_text='多个演员用逗号分隔'
    )

    # 女友关联 (多对多关系)
    actresses = models.ManyToManyField(
        'actresses.Actress',
        related_name='movies',
        blank=True,
        verbose_name='关联女友',
        help_text='参演此影片的女友'
    )

    # 新增字段：影片样例图片
    sample_images = models.TextField(
        blank=True,
        verbose_name='样例图片',
        help_text='影片样例图片URL，多个URL用换行分隔'
    )

    # 新增字段：影片标记/标签
    movie_tags = models.TextField(
        blank=True,
        verbose_name='影片标记',
        help_text='影片的特殊标记或标签，用逗号分隔'
    )
    
    # 元数据
    source = models.CharField(
        max_length=20,
        choices=MovieSource.choices,
        default=MovieSource.JAVBUS,
        verbose_name='数据来源'
    )
    
    code_36 = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='36进制编码',
        help_text='用于内部标识的36进制编码'
    )
    
    # 统计信息
    view_count = models.PositiveIntegerField(
        default=0,
        verbose_name='浏览次数'
    )
    
    download_count = models.PositiveIntegerField(
        default=0,
        verbose_name='下载次数'
    )
    
    # 时间戳
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    class Meta:
        db_table = 'movies'
        verbose_name = '影片'
        verbose_name_plural = '影片'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['censored_id']),
            models.Index(fields=['source']),
            models.Index(fields=['release_date']),
            models.Index(fields=['created_at']),
            models.Index(fields=['view_count']),
        ]
    
    def __str__(self):
        return f"{self.censored_id} - {self.movie_title[:50]}"
    
    def get_absolute_url(self):
        return reverse('movie-detail', kwargs={'pk': self.pk})
    
    def save(self, *args, **kwargs):
        # 自动生成code_36
        if not self.code_36 and self.censored_id:
            import hashlib
            self.code_36 = hashlib.md5(self.censored_id.encode()).hexdigest()[:6]
        super().save(*args, **kwargs)
    
    @property
    def genre_list(self):
        """返回类型列表"""
        if self.genre:
            return [g.strip() for g in self.genre.split(',') if g.strip()]
        return []
    
    @property
    def idol_list(self):
        """返回演员列表"""
        if self.jav_idols:
            return [idol.strip() for idol in self.jav_idols.split(',') if idol.strip()]
        return []

    @property
    def sample_images_list(self):
        """返回样例图片列表"""
        if self.sample_images:
            return [img.strip() for img in self.sample_images.split('\n') if img.strip()]
        return []

    @property
    def movie_tags_list(self):
        """返回影片标记列表"""
        if self.movie_tags:
            return [tag.strip() for tag in self.movie_tags.split(',') if tag.strip()]
        return []

    def get_actresses_names(self):
        """获取关联女友姓名列表"""
        return [actress.name for actress in self.actresses.all()]

    def add_actress_by_name(self, actress_name):
        """根据姓名添加女友关联"""
        from apps.actresses.models import Actress
        try:
            actress = Actress.objects.get(name=actress_name)
            self.actresses.add(actress)
            return True
        except Actress.DoesNotExist:
            return False
    
    def increment_view_count(self):
        """增加浏览次数"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_download_count(self):
        """增加下载次数"""
        self.download_count += 1
        self.save(update_fields=['download_count'])


class MovieTag(models.Model):
    """影片标签"""
    
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
        help_text='十六进制颜色代码'
    )
    
    movies = models.ManyToManyField(
        'Movie',  # 使用字符串引用避免循环导入
        related_name='tags',
        blank=True,
        verbose_name='关联影片'
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='创建时间'
    )
    
    class Meta:
        db_table = 'movie_tags'
        verbose_name = '影片标签'
        verbose_name_plural = '影片标签'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class MovieRating(models.Model):
    """影片评分"""
    
    movie = models.OneToOneField(
        Movie,
        on_delete=models.CASCADE,
        related_name='rating',
        verbose_name='影片'
    )
    
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        verbose_name='平均评分'
    )
    
    total_votes = models.PositiveIntegerField(
        default=0,
        verbose_name='总投票数'
    )
    
    five_star = models.PositiveIntegerField(default=0, verbose_name='5星')
    four_star = models.PositiveIntegerField(default=0, verbose_name='4星')
    three_star = models.PositiveIntegerField(default=0, verbose_name='3星')
    two_star = models.PositiveIntegerField(default=0, verbose_name='2星')
    one_star = models.PositiveIntegerField(default=0, verbose_name='1星')
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    class Meta:
        db_table = 'movie_ratings'
        verbose_name = '影片评分'
        verbose_name_plural = '影片评分'
    
    def __str__(self):
        return f"{self.movie.censored_id} - {self.average_rating}★"
    
    def calculate_average(self):
        """计算平均评分"""
        total_points = (
            self.five_star * 5 +
            self.four_star * 4 +
            self.three_star * 3 +
            self.two_star * 2 +
            self.one_star * 1
        )
        
        self.total_votes = (
            self.five_star + self.four_star + self.three_star +
            self.two_star + self.one_star
        )
        
        if self.total_votes > 0:
            self.average_rating = round(total_points / self.total_votes, 2)
        else:
            self.average_rating = 0.00
        
        self.save()
