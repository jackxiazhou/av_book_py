"""
Crawler models for tracking crawling progress and state.
"""

from django.db import models
from django.utils import timezone
import json


class CrawlerSession(models.Model):
    """爬虫会话模型 - 用于断点续跑"""
    
    SESSION_STATUS = [
        ('running', '运行中'),
        ('paused', '暂停'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]
    
    CRAWLER_TYPES = [
        ('avmoo', 'AVMoo'),
        ('javlibrary', 'JAVLibrary'),
        ('javbus', 'JAVBus'),
    ]
    
    # 基础信息
    session_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='会话ID'
    )
    
    crawler_type = models.CharField(
        max_length=20,
        choices=CRAWLER_TYPES,
        verbose_name='爬虫类型'
    )
    
    status = models.CharField(
        max_length=20,
        choices=SESSION_STATUS,
        default='running',
        verbose_name='状态'
    )
    
    # 爬取配置
    total_pages = models.IntegerField(
        default=1,
        verbose_name='总页数'
    )
    
    max_movies = models.IntegerField(
        default=10,
        verbose_name='最大影片数'
    )
    
    delay_seconds = models.IntegerField(
        default=3,
        verbose_name='延迟秒数'
    )
    
    proxy_url = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='代理URL'
    )
    
    # 进度信息
    current_page = models.IntegerField(
        default=1,
        verbose_name='当前页数'
    )
    
    processed_movies = models.IntegerField(
        default=0,
        verbose_name='已处理影片数'
    )
    
    created_movies = models.IntegerField(
        default=0,
        verbose_name='已创建影片数'
    )
    
    processed_urls = models.TextField(
        blank=True,
        verbose_name='已处理URL列表',
        help_text='JSON格式存储已处理的URL'
    )
    
    # 时间信息
    started_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='开始时间'
    )
    
    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name='最后活动时间'
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='完成时间'
    )
    
    # 错误信息
    error_message = models.TextField(
        blank=True,
        verbose_name='错误信息'
    )
    
    error_count = models.IntegerField(
        default=0,
        verbose_name='错误次数'
    )
    
    class Meta:
        db_table = 'crawler_sessions'
        verbose_name = '爬虫会话'
        verbose_name_plural = '爬虫会话'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.crawler_type} - {self.session_id}"
    
    def get_processed_urls(self):
        """获取已处理的URL列表"""
        if self.processed_urls:
            try:
                return json.loads(self.processed_urls)
            except json.JSONDecodeError:
                return []
        return []
    
    def add_processed_url(self, url):
        """添加已处理的URL"""
        urls = self.get_processed_urls()
        if url not in urls:
            urls.append(url)
            self.processed_urls = json.dumps(urls)
            self.save(update_fields=['processed_urls'])
    
    def is_url_processed(self, url):
        """检查URL是否已处理"""
        return url in self.get_processed_urls()
    
    def update_progress(self, page=None, processed=None, created=None):
        """更新进度"""
        if page is not None:
            self.current_page = page
        if processed is not None:
            self.processed_movies = processed
        if created is not None:
            self.created_movies = created
        
        self.last_activity = timezone.now()
        self.save(update_fields=['current_page', 'processed_movies', 'created_movies', 'last_activity'])
    
    def mark_completed(self):
        """标记为完成"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    def mark_failed(self, error_message):
        """标记为失败"""
        self.status = 'failed'
        self.error_message = error_message
        self.error_count += 1
        self.save(update_fields=['status', 'error_message', 'error_count'])

    def add_processed_url(self, url):
        """添加已处理的URL"""
        if not hasattr(self, '_processed_urls'):
            self._processed_urls = set()
        self._processed_urls.add(url)

    def is_url_processed(self, url):
        """检查URL是否已处理"""
        if not hasattr(self, '_processed_urls'):
            self._processed_urls = set()
        return url in self._processed_urls

    def resume(self):
        """恢复会话"""
        self.status = 'running'
        self.save()
    
    def pause(self):
        """暂停会话"""
        self.status = 'paused'
        self.save(update_fields=['status'])
    
    def resume(self):
        """恢复会话"""
        self.status = 'running'
        self.save(update_fields=['status'])
    
    @property
    def progress_percentage(self):
        """计算进度百分比"""
        if self.max_movies > 0:
            return min(100, (self.processed_movies / self.max_movies) * 100)
        return 0
    
    @property
    def duration(self):
        """计算持续时间"""
        end_time = self.completed_at or timezone.now()
        return end_time - self.started_at


class CrawlerLog(models.Model):
    """爬虫日志模型"""
    
    LOG_LEVELS = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    session = models.ForeignKey(
        CrawlerSession,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='爬虫会话'
    )
    
    level = models.CharField(
        max_length=10,
        choices=LOG_LEVELS,
        default='info',
        verbose_name='日志级别'
    )
    
    message = models.TextField(
        verbose_name='日志消息'
    )
    
    url = models.URLField(
        blank=True,
        verbose_name='相关URL'
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='创建时间'
    )
    
    class Meta:
        db_table = 'crawler_logs'
        verbose_name = '爬虫日志'
        verbose_name_plural = '爬虫日志'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.level.upper()}: {self.message[:50]}"


class CrawlerSchedule(models.Model):
    """爬虫定时任务模型"""
    
    SCHEDULE_TYPES = [
        ('once', '单次'),
        ('daily', '每日'),
        ('weekly', '每周'),
        ('monthly', '每月'),
    ]
    
    name = models.CharField(
        max_length=100,
        verbose_name='任务名称'
    )
    
    crawler_type = models.CharField(
        max_length=20,
        choices=CrawlerSession.CRAWLER_TYPES,
        verbose_name='爬虫类型'
    )
    
    schedule_type = models.CharField(
        max_length=10,
        choices=SCHEDULE_TYPES,
        verbose_name='调度类型'
    )
    
    # 调度配置
    pages = models.IntegerField(
        default=5,
        verbose_name='页数'
    )
    
    max_movies = models.IntegerField(
        default=50,
        verbose_name='最大影片数'
    )
    
    delay_seconds = models.IntegerField(
        default=3,
        verbose_name='延迟秒数'
    )
    
    proxy_url = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='代理URL'
    )
    
    # 时间配置
    scheduled_time = models.TimeField(
        verbose_name='调度时间'
    )
    
    next_run = models.DateTimeField(
        verbose_name='下次运行时间'
    )
    
    last_run = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='上次运行时间'
    )
    
    # 状态
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否激活'
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='创建时间'
    )
    
    class Meta:
        db_table = 'crawler_schedules'
        verbose_name = '爬虫定时任务'
        verbose_name_plural = '爬虫定时任务'
        ordering = ['next_run']
    
    def __str__(self):
        return f"{self.name} ({self.crawler_type})"


class CrawlTask(models.Model):
    """爬虫任务模型"""

    TASK_STATUS = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]

    # 基本信息
    spider_name = models.CharField(
        max_length=50,
        verbose_name='爬虫名称'
    )

    status = models.CharField(
        max_length=20,
        choices=TASK_STATUS,
        default='pending',
        verbose_name='任务状态'
    )

    # 配置信息
    config = models.JSONField(
        default=dict,
        verbose_name='任务配置'
    )

    # 结果信息
    result = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='任务结果'
    )

    # 时间信息
    start_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='开始时间'
    )

    end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='结束时间'
    )

    duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='持续时间(秒)'
    )

    # 错误信息
    error_message = models.TextField(
        blank=True,
        verbose_name='错误信息'
    )

    # 元数据
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='创建时间'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )

    class Meta:
        db_table = 'crawl_tasks'
        verbose_name = '爬虫任务'
        verbose_name_plural = '爬虫任务'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.spider_name} - {self.status}"

    def mark_running(self):
        """标记为运行中"""
        self.status = 'running'
        self.start_time = timezone.now()
        self.save(update_fields=['status', 'start_time'])

    def mark_completed(self, result=None):
        """标记为完成"""
        self.status = 'completed'
        self.end_time = timezone.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
        if result:
            self.result = result
        self.save(update_fields=['status', 'end_time', 'duration', 'result'])

    def mark_failed(self, error_message):
        """标记为失败"""
        self.status = 'failed'
        self.end_time = timezone.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
        self.error_message = error_message
        self.save(update_fields=['status', 'end_time', 'duration', 'error_message'])

    def mark_cancelled(self):
        """标记为取消"""
        self.status = 'cancelled'
        self.end_time = timezone.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
        self.save(update_fields=['status', 'end_time', 'duration'])
