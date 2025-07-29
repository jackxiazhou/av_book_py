"""
Magnet models for AVBook application.
"""
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from apps.movies.models import Movie


class MagnetQuality(models.TextChoices):
    """磁力链接质量选择"""
    SD = 'sd', '标清'
    HD = 'hd', '高清'
    FHD = 'fhd', '全高清'
    UHD = 'uhd', '超高清'
    UNKNOWN = 'unknown', '未知'


class MagnetLink(models.Model):
    """磁力链接模型"""
    
    # 关联影片
    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name='magnets',
        verbose_name='关联影片'
    )
    
    # 基础信息
    magnet_name = models.TextField(
        verbose_name='磁力名称',
        help_text='磁力链接的文件名或描述'
    )
    
    magnet_link = models.TextField(
        validators=[
            RegexValidator(
                regex=r'^magnet:\?xt=urn:btih:[a-fA-F0-9]{40}',
                message='磁力链接格式不正确'
            )
        ],
        verbose_name='磁力链接',
        help_text='完整的磁力链接'
    )
    
    # 文件信息
    file_size = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='文件大小',
        help_text='如: 1.5GB'
    )
    
    file_size_bytes = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='文件大小(字节)',
        help_text='文件大小的字节数'
    )
    
    # 质量标识
    quality = models.CharField(
        max_length=10,
        choices=MagnetQuality.choices,
        default=MagnetQuality.UNKNOWN,
        verbose_name='视频质量'
    )
    
    has_subtitle = models.BooleanField(
        default=False,
        verbose_name='是否有字幕'
    )
    
    subtitle_language = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='字幕语言',
        help_text='如: 中文, 英文, 日文'
    )
    
    # 种子信息
    seeders = models.PositiveIntegerField(
        default=0,
        verbose_name='做种数'
    )
    
    leechers = models.PositiveIntegerField(
        default=0,
        verbose_name='下载数'
    )
    
    completed = models.PositiveIntegerField(
        default=0,
        verbose_name='完成数'
    )
    
    # 发布信息
    publish_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='发布日期'
    )
    
    uploader = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='上传者'
    )
    
    # 状态信息
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否有效'
    )
    
    is_verified = models.BooleanField(
        default=False,
        verbose_name='是否已验证'
    )
    
    last_checked = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='最后检查时间'
    )
    
    # 统计信息
    download_count = models.PositiveIntegerField(
        default=0,
        verbose_name='下载次数'
    )
    
    click_count = models.PositiveIntegerField(
        default=0,
        verbose_name='点击次数'
    )
    
    # 来源信息
    source = models.CharField(
        max_length=50,
        default='unknown',
        verbose_name='数据来源',
        help_text='如: avmoo, javbus, javlibrary'
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
        db_table = 'magnet_links'
        verbose_name = '磁力链接'
        verbose_name_plural = '磁力链接'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['movie']),
            models.Index(fields=['quality']),
            models.Index(fields=['has_subtitle']),
            models.Index(fields=['is_active']),
            models.Index(fields=['seeders']),
            models.Index(fields=['created_at']),
        ]
        # unique_together = ['movie', 'magnet_link']  # 暂时注释掉，因为MySQL不支持TEXT字段的唯一约束
    
    def __str__(self):
        return f"{self.movie.censored_id} - {self.magnet_name[:50]}"
    
    def save(self, *args, **kwargs):
        # 自动检测质量
        if not self.quality or self.quality == MagnetQuality.UNKNOWN:
            self.quality = self.detect_quality()
        
        # 自动检测字幕
        if not self.has_subtitle:
            self.has_subtitle = self.detect_subtitle()
        
        super().save(*args, **kwargs)
    
    def detect_quality(self):
        """根据文件名检测视频质量"""
        name_lower = self.magnet_name.lower()
        
        if any(keyword in name_lower for keyword in ['4k', '2160p', 'uhd']):
            return MagnetQuality.UHD
        elif any(keyword in name_lower for keyword in ['1080p', 'fhd', 'fullhd']):
            return MagnetQuality.FHD
        elif any(keyword in name_lower for keyword in ['720p', 'hd']):
            return MagnetQuality.HD
        elif any(keyword in name_lower for keyword in ['480p', '360p', 'sd']):
            return MagnetQuality.SD
        else:
            return MagnetQuality.UNKNOWN
    
    def detect_subtitle(self):
        """根据文件名检测是否有字幕"""
        name_lower = self.magnet_name.lower()
        subtitle_keywords = [
            'sub', 'subtitle', '字幕', 'chinese', 'chs', 'cht',
            'eng', 'english', 'jp', 'japanese'
        ]
        return any(keyword in name_lower for keyword in subtitle_keywords)
    
    def get_file_size_display(self):
        """获取友好的文件大小显示"""
        if self.file_size:
            return self.file_size
        
        if self.file_size_bytes:
            return self.format_file_size(self.file_size_bytes)
        
        return '未知'
    
    @staticmethod
    def format_file_size(size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    def increment_download_count(self):
        """增加下载次数"""
        self.download_count += 1
        self.movie.increment_download_count()
        self.save(update_fields=['download_count'])
    
    def increment_click_count(self):
        """增加点击次数"""
        self.click_count += 1
        self.save(update_fields=['click_count'])
    
    @property
    def health_score(self):
        """计算健康度评分 (0-100)"""
        if not self.is_active:
            return 0
        
        # 基础分数
        score = 50
        
        # 做种数加分
        if self.seeders > 0:
            score += min(self.seeders * 2, 30)
        
        # 完成数加分
        if self.completed > 0:
            score += min(self.completed, 20)
        
        # 验证状态加分
        if self.is_verified:
            score += 10
        
        # 最近检查加分
        if self.last_checked:
            from django.utils import timezone
            days_since_check = (timezone.now() - self.last_checked).days
            if days_since_check <= 7:
                score += 10
            elif days_since_check <= 30:
                score += 5
        
        return min(score, 100)


class MagnetCategory(models.Model):
    """磁力链接分类"""
    
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='分类名称'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='分类描述'
    )
    
    color = models.CharField(
        max_length=7,
        default='#28a745',
        verbose_name='分类颜色'
    )
    
    magnets = models.ManyToManyField(
        MagnetLink,
        related_name='categories',
        blank=True,
        verbose_name='关联磁力链接'
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='创建时间'
    )
    
    class Meta:
        db_table = 'magnet_categories'
        verbose_name = '磁力分类'
        verbose_name_plural = '磁力分类'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class DownloadHistory(models.Model):
    """下载历史记录"""
    
    magnet = models.ForeignKey(
        MagnetLink,
        on_delete=models.CASCADE,
        related_name='download_history',
        verbose_name='磁力链接'
    )
    
    ip_address = models.GenericIPAddressField(
        verbose_name='IP地址'
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name='用户代理'
    )
    
    download_time = models.DateTimeField(
        default=timezone.now,
        verbose_name='下载时间'
    )
    
    class Meta:
        db_table = 'download_history'
        verbose_name = '下载历史'
        verbose_name_plural = '下载历史'
        ordering = ['-download_time']
        indexes = [
            models.Index(fields=['magnet']),
            models.Index(fields=['download_time']),
            models.Index(fields=['ip_address']),
        ]
    
    def __str__(self):
        return f"{self.magnet.movie.censored_id} - {self.download_time}"
