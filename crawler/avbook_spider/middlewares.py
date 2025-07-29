"""
Define here the models for your spider middleware.
"""

from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message
from scrapy.core.downloader.handlers.http11 import TunnelError
import random
import time
import logging


class AvbookSpiderMiddleware:
    """Spider middleware for AVBook spider."""
    
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        pass

    def process_start_requests(self, start_requests, spider):
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class ProxyMiddleware:
    """代理中间件"""
    
    def __init__(self):
        self.proxies = [
            'http://127.0.0.1:5890',
            'socks5://127.0.0.1:5891',
        ]
        self.proxy_index = 0
        self.logger = logging.getLogger(__name__)
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls()
    
    def process_request(self, request, spider):
        """为请求设置代理"""
        if hasattr(spider, 'use_proxy') and not spider.use_proxy:
            return None
        
        # 从meta中获取指定的代理，或使用轮询代理
        proxy = request.meta.get('proxy')
        if not proxy and self.proxies:
            proxy = self.get_next_proxy()
            request.meta['proxy'] = proxy
        
        if proxy:
            self.logger.debug(f'Using proxy {proxy} for {request.url}')
        
        return None
    
    def get_next_proxy(self):
        """获取下一个代理"""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy
    
    def process_response(self, request, response, spider):
        """处理响应"""
        # 检查响应状态
        if response.status in [403, 429, 503]:
            self.logger.warning(f'Proxy blocked or rate limited: {response.status}')
            # 可以在这里切换代理或添加延迟
        
        return response
    
    def process_exception(self, request, exception, spider):
        """处理异常"""
        if isinstance(exception, (ConnectionError, TunnelError)):
            self.logger.error(f'Proxy connection error: {exception}')
            # 切换到下一个代理
            if self.proxies:
                new_proxy = self.get_next_proxy()
                request.meta['proxy'] = new_proxy
                self.logger.info(f'Switching to proxy: {new_proxy}')
        
        return None


class CustomRetryMiddleware(RetryMiddleware):
    """自定义重试中间件"""
    
    def __init__(self, settings):
        super().__init__(settings)
        self.max_retry_times = settings.getint('RETRY_TIMES', 3)
        self.retry_http_codes = set(int(x) for x in settings.getlist('RETRY_HTTP_CODES'))
        self.priority_adjust = settings.getint('RETRY_PRIORITY_ADJUST', -1)
        self.logger = logging.getLogger(__name__)
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)
    
    def process_response(self, request, response, spider):
        """处理响应重试"""
        if request.meta.get('dont_retry', False):
            return response
        
        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response
        
        # 检查响应内容是否有效
        if self.is_invalid_response(response):
            reason = 'Invalid response content'
            return self._retry(request, reason, spider) or response
        
        return response
    
    def process_exception(self, request, exception, spider):
        """处理异常重试"""
        if isinstance(exception, self.EXCEPTIONS_TO_RETRY) and not request.meta.get('dont_retry', False):
            return self._retry(request, str(exception), spider)
        
        return None
    
    def _retry(self, request, reason, spider):
        """执行重试"""
        retries = request.meta.get('retry_times', 0) + 1
        
        if retries <= self.max_retry_times:
            self.logger.debug(f"Retrying {request.url} (failed {retries} times): {reason}")
            
            retryreq = request.copy()
            retryreq.meta['retry_times'] = retries
            retryreq.dont_filter = True
            retryreq.priority = request.priority + self.priority_adjust
            
            # 添加重试延迟
            delay = self.get_retry_delay(retries)
            if delay > 0:
                time.sleep(delay)
            
            return retryreq
        else:
            self.logger.error(f"Gave up retrying {request.url} (failed {retries} times): {reason}")
            return None
    
    def get_retry_delay(self, retry_times):
        """计算重试延迟"""
        # 指数退避策略
        return min(2 ** retry_times, 60)
    
    def is_invalid_response(self, response):
        """检查响应是否无效"""
        # 检查响应长度
        if len(response.body) < 100:
            return True
        
        # 检查是否包含错误页面标识
        error_indicators = [
            b'404 Not Found',
            b'403 Forbidden',
            b'500 Internal Server Error',
            b'Service Unavailable',
            b'Access Denied',
            b'Blocked',
        ]
        
        body_lower = response.body.lower()
        for indicator in error_indicators:
            if indicator.lower() in body_lower:
                return True
        
        return False


class UserAgentMiddleware:
    """用户代理中间件"""
    
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        ]
    
    def process_request(self, request, spider):
        """为请求设置随机用户代理"""
        ua = random.choice(self.user_agents)
        request.headers['User-Agent'] = ua
        return None


class DelayMiddleware:
    """延迟中间件"""
    
    def __init__(self, delay=1, randomize_delay=0.5):
        self.delay = delay
        self.randomize_delay = randomize_delay
        self.logger = logging.getLogger(__name__)
    
    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        delay = settings.getfloat('DOWNLOAD_DELAY', 1)
        randomize_delay = settings.getfloat('RANDOMIZE_DOWNLOAD_DELAY', 0.5)
        return cls(delay, randomize_delay)
    
    def process_request(self, request, spider):
        """添加请求延迟"""
        if self.delay > 0:
            delay = self.delay
            if self.randomize_delay:
                delay *= (0.5 + random.random() * self.randomize_delay)
            
            self.logger.debug(f'Delaying request for {delay:.2f}s: {request.url}')
            time.sleep(delay)
        
        return None


class StatisticsMiddleware:
    """统计中间件"""
    
    def __init__(self):
        self.stats = {
            'requests_total': 0,
            'requests_success': 0,
            'requests_failed': 0,
            'response_times': [],
        }
        self.logger = logging.getLogger(__name__)
    
    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
    
    def process_request(self, request, spider):
        """记录请求开始时间"""
        request.meta['start_time'] = time.time()
        self.stats['requests_total'] += 1
        return None
    
    def process_response(self, request, response, spider):
        """记录响应统计"""
        start_time = request.meta.get('start_time')
        if start_time:
            response_time = time.time() - start_time
            self.stats['response_times'].append(response_time)
        
        if response.status < 400:
            self.stats['requests_success'] += 1
        else:
            self.stats['requests_failed'] += 1
        
        return response
    
    def process_exception(self, request, exception, spider):
        """记录异常统计"""
        self.stats['requests_failed'] += 1
        return None
    
    def spider_opened(self, spider):
        """爬虫开始时初始化统计"""
        self.logger.info(f'Statistics middleware initialized for spider: {spider.name}')
    
    def spider_closed(self, spider):
        """爬虫结束时输出统计"""
        total_requests = self.stats['requests_total']
        success_requests = self.stats['requests_success']
        failed_requests = self.stats['requests_failed']
        response_times = self.stats['response_times']
        
        success_rate = (success_requests / total_requests * 100) if total_requests > 0 else 0
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        self.logger.info(f'Spider {spider.name} statistics:')
        self.logger.info(f'  Total requests: {total_requests}')
        self.logger.info(f'  Successful requests: {success_requests}')
        self.logger.info(f'  Failed requests: {failed_requests}')
        self.logger.info(f'  Success rate: {success_rate:.2f}%')
        self.logger.info(f'  Average response time: {avg_response_time:.2f}s')
