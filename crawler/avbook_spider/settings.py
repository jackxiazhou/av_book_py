# Scrapy settings for avbook_spider project

BOT_NAME = 'avbook_spider'

SPIDER_MODULES = ['avbook_spider.spiders']
NEWSPIDER_MODULE = 'avbook_spider.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 8

# Configure a delay for requests for the same website (default: 0)
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True

# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 2
CONCURRENT_REQUESTS_PER_IP = 1

# Disable cookies (enabled by default)
COOKIES_ENABLED = True

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
}

# Enable or disable spider middlewares
SPIDER_MIDDLEWARES = {
    'avbook_spider.middlewares.AvbookSpiderMiddleware': 543,
}

# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
    # 'avbook_spider.middlewares.ProxyMiddleware': 350,  # 暂时禁用
    # 'avbook_spider.middlewares.RetryMiddleware': 550,  # 暂时禁用
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
}

# Enable or disable extensions
EXTENSIONS = {
    'scrapy.extensions.telnet.TelnetConsole': None,
    # 'avbook_spider.extensions.StatsExtension': 500,  # 暂时禁用
}

# Configure item pipelines
ITEM_PIPELINES = {
    # 'avbook_spider.pipelines.ValidationPipeline': 300,  # 暂时禁用
    # 'avbook_spider.pipelines.DuplicatesPipeline': 400,  # 暂时禁用
    # 'avbook_spider.pipelines.ActressImageDownloadPipeline': 600,  # 暂时禁用
    # 'avbook_spider.pipelines.ActressDatabasePipeline': 700,  # 暂时禁用
    # 'avbook_spider.pipelines.DatabasePipeline': 800,  # 暂时禁用
}

# Enable and configure the AutoThrottle extension (disabled by default)
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = [503, 504, 505, 500, 403, 404, 408, 429]

# Database settings
DATABASE_SETTINGS = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root-1234',
    'database': 'avbook_py',
    'charset': 'utf8mb4',
}

# Redis settings
REDIS_URL = 'redis://localhost:6379/1'

# Proxy settings
PROXY_ENABLED = True
PROXY_LIST = [
    'http://127.0.0.1:5890',  # Clash proxy
    'socks5://127.0.0.1:5891',
]

# User agent settings
RANDOM_UA_PER_PROXY = True
RANDOM_UA_TYPE = 'random'

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]

# Log settings
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/scrapy.log'

# Custom settings for different spiders
SPIDER_SETTINGS = {
    'javbus': {
        'DOWNLOAD_DELAY': 5,
        'CONCURRENT_REQUESTS': 4,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
    },
    'avmoo': {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS': 6,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.5,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    },
    'javlibrary': {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 8,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 2.0,
    },
    'avmoo_actresses_complete': {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS': 2,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'ITEM_PIPELINES': {
            'avbook_spider.pipelines.ActressCompleteValidationPipeline': 300,
            'avbook_spider.pipelines.DuplicatesPipeline': 400,
            'avbook_spider.pipelines.ActressCompleteDjangoPipeline': 800,
        },
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    },
}

# Feed exports
FEEDS = {
    'output/movies_%(name)s_%(time)s.json': {
        'format': 'json',
        'encoding': 'utf8',
        'store_empty': False,
        'fields': None,
        'indent': 2,
    },
}

# Stats collection
STATS_CLASS = 'scrapy.statscollectors.MemoryStatsCollector'

# DNS settings
DNSCACHE_ENABLED = True
DNSCACHE_SIZE = 10000
DNS_TIMEOUT = 60

# Request fingerprinting
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'

# Twisted reactor
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'

