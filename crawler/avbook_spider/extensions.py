"""
Scrapy extensions for AVBook spider.
"""

from scrapy import signals
from scrapy.exceptions import NotConfigured
import time
import logging


class StatsExtension:
    """统计扩展"""
    
    def __init__(self, stats):
        self.stats = stats
        self.start_time = None
        
    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool('STATS_ENABLED', True):
            raise NotConfigured('Stats extension disabled')
        
        ext = cls(crawler.stats)
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(ext.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(ext.response_received, signal=signals.response_received)
        
        return ext
    
    def spider_opened(self, spider):
        """爬虫开始时"""
        self.start_time = time.time()
        spider.logger.info(f'Spider {spider.name} opened')
    
    def spider_closed(self, spider, reason):
        """爬虫结束时"""
        if self.start_time:
            duration = time.time() - self.start_time
            spider.logger.info(f'Spider {spider.name} closed: {reason}')
            spider.logger.info(f'Duration: {duration:.2f} seconds')
            
            # 记录统计信息
            stats = self.stats.get_stats()
            spider.logger.info(f'Stats: {stats}')
    
    def item_scraped(self, item, response, spider):
        """数据项被爬取时"""
        pass
    
    def response_received(self, response, request, spider):
        """收到响应时"""
        pass


class LoggingExtension:
    """日志扩展"""
    
    def __init__(self, log_level):
        self.log_level = log_level
        
    @classmethod
    def from_crawler(cls, crawler):
        log_level = crawler.settings.get('LOG_LEVEL', 'INFO')
        ext = cls(log_level)
        
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        
        return ext
    
    def spider_opened(self, spider):
        """爬虫开始时的日志"""
        spider.logger.info(f'Starting spider: {spider.name}')
        spider.logger.info(f'Log level: {self.log_level}')
    
    def spider_closed(self, spider, reason):
        """爬虫结束时的日志"""
        spider.logger.info(f'Spider {spider.name} finished with reason: {reason}')


class MemoryUsageExtension:
    """内存使用监控扩展"""
    
    def __init__(self, enabled=True):
        self.enabled = enabled
        
    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool('MEMORY_USAGE_ENABLED', False)
        if not enabled:
            raise NotConfigured('Memory usage extension disabled')
            
        ext = cls(enabled)
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        
        return ext
    
    def spider_opened(self, spider):
        """爬虫开始时"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            spider.logger.info(f'Initial memory usage: {memory_info.rss / 1024 / 1024:.2f} MB')
        except ImportError:
            spider.logger.warning('psutil not installed, memory monitoring disabled')
    
    def spider_closed(self, spider, reason):
        """爬虫结束时"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            spider.logger.info(f'Final memory usage: {memory_info.rss / 1024 / 1024:.2f} MB')
        except ImportError:
            pass


class ProgressExtension:
    """进度监控扩展"""
    
    def __init__(self, log_interval=100):
        self.log_interval = log_interval
        self.item_count = 0
        self.request_count = 0
        
    @classmethod
    def from_crawler(cls, crawler):
        log_interval = crawler.settings.getint('PROGRESS_LOG_INTERVAL', 100)
        ext = cls(log_interval)
        
        crawler.signals.connect(ext.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(ext.request_scheduled, signal=signals.request_scheduled)
        
        return ext
    
    def item_scraped(self, item, response, spider):
        """数据项被爬取时"""
        self.item_count += 1
        if self.item_count % self.log_interval == 0:
            spider.logger.info(f'Scraped {self.item_count} items')
    
    def request_scheduled(self, request, spider):
        """请求被调度时"""
        self.request_count += 1
        if self.request_count % self.log_interval == 0:
            spider.logger.info(f'Scheduled {self.request_count} requests')
