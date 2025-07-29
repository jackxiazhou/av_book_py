"""
Define here the models for your scraped items.
"""

import scrapy
from itemloaders.processors import TakeFirst, MapCompose, Join
from w3lib.html import remove_tags
import re
from datetime import datetime


def clean_text(value):
    """清理文本内容"""
    if not value:
        return value
    # 移除HTML标签
    value = remove_tags(value)
    # 移除多余空白
    value = re.sub(r'\s+', ' ', value).strip()
    return value


def parse_date(value):
    """解析日期"""
    if not value:
        return None
    
    # 清理日期字符串
    value = clean_text(value)
    
    # 尝试多种日期格式
    date_formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y年%m月%d日',
        '%m/%d/%Y',
        '%d/%m/%Y',
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    
    return None


def parse_file_size(value):
    """解析文件大小"""
    if not value:
        return None
    
    value = clean_text(value).upper()
    
    # 提取数字和单位
    match = re.search(r'([\d.]+)\s*(B|KB|MB|GB|TB)', value)
    if not match:
        return None
    
    size, unit = match.groups()
    size = float(size)
    
    # 转换为字节
    units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
    return int(size * units.get(unit, 1))


def extract_censored_id(value):
    """提取影片编号"""
    if not value:
        return value
    
    # 使用正则表达式提取标准格式的编号
    match = re.search(r'([A-Z]+[-_]?\d+)', value.upper())
    if match:
        return match.group(1).replace('_', '-')
    
    return value


class MovieItem(scrapy.Item):
    """影片数据项"""
    
    # 基础信息
    censored_id = scrapy.Field(
        input_processor=MapCompose(extract_censored_id, clean_text),
        output_processor=TakeFirst()
    )
    
    movie_title = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    movie_pic_cover = scrapy.Field(
        output_processor=TakeFirst()
    )

    cover_image = scrapy.Field(
        output_processor=TakeFirst()
    )

    # 新增字段
    duration_minutes = scrapy.Field(
        input_processor=MapCompose(int),
        output_processor=TakeFirst()
    )

    publisher = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )

    movie_tags = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )

    actresses = scrapy.Field(
        output_processor=TakeFirst()
    )

    sample_images = scrapy.Field(
        output_processor=TakeFirst()
    )
    
    # 详细信息
    release_date = scrapy.Field(
        input_processor=MapCompose(parse_date),
        output_processor=TakeFirst()
    )
    
    movie_length = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    director = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    studio = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    label = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    series = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    # 分类和标签
    genre = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=Join(', ')
    )
    
    jav_idols = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=Join(', ')
    )
    
    # 元数据
    source = scrapy.Field(
        output_processor=TakeFirst()
    )
    
    source_url = scrapy.Field(
        output_processor=TakeFirst()
    )
    
    # 磁力链接
    magnets = scrapy.Field()


class MagnetItem(scrapy.Item):
    """磁力链接数据项"""
    
    # 关联影片
    movie_censored_id = scrapy.Field(
        input_processor=MapCompose(extract_censored_id, clean_text),
        output_processor=TakeFirst()
    )
    
    # 基础信息
    magnet_name = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    magnet_link = scrapy.Field(
        output_processor=TakeFirst()
    )
    
    # 文件信息
    file_size = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    file_size_bytes = scrapy.Field(
        input_processor=MapCompose(parse_file_size),
        output_processor=TakeFirst()
    )
    
    # 种子信息
    seeders = scrapy.Field(
        input_processor=MapCompose(lambda x: int(x) if x.isdigit() else 0),
        output_processor=TakeFirst()
    )
    
    leechers = scrapy.Field(
        input_processor=MapCompose(lambda x: int(x) if x.isdigit() else 0),
        output_processor=TakeFirst()
    )
    
    completed = scrapy.Field(
        input_processor=MapCompose(lambda x: int(x) if x.isdigit() else 0),
        output_processor=TakeFirst()
    )
    
    # 发布信息
    publish_date = scrapy.Field(
        input_processor=MapCompose(parse_date),
        output_processor=TakeFirst()
    )
    
    uploader = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    # 来源信息
    source = scrapy.Field(
        output_processor=TakeFirst()
    )
    
    source_url = scrapy.Field(
        output_processor=TakeFirst()
    )


class CrawlStatsItem(scrapy.Item):
    """爬虫统计数据项"""

    spider_name = scrapy.Field()
    start_time = scrapy.Field()
    end_time = scrapy.Field()
    duration = scrapy.Field()

    # 请求统计
    total_requests = scrapy.Field()
    successful_requests = scrapy.Field()
    failed_requests = scrapy.Field()

    # 数据统计
    total_items = scrapy.Field()
    movies_scraped = scrapy.Field()
    magnets_scraped = scrapy.Field()

    # 错误统计
    error_count = scrapy.Field()
    retry_count = scrapy.Field()

    # 性能统计
    avg_response_time = scrapy.Field()
    items_per_second = scrapy.Field()

    # 状态
    status = scrapy.Field()
    error_message = scrapy.Field()


class ActressItem(scrapy.Item):
    """女友数据项 - 用于递归爬虫"""

    # 基本信息
    actress_id = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    name = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    name_en = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )

    # 个人资料
    birth_date = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    age = scrapy.Field(
        input_processor=MapCompose(int),
        output_processor=TakeFirst()
    )
    height = scrapy.Field(
        input_processor=MapCompose(int),
        output_processor=TakeFirst()
    )
    weight = scrapy.Field(
        input_processor=MapCompose(int),
        output_processor=TakeFirst()
    )
    cup_size = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    measurements = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    hobby = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    debut_date = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    agency = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )

    # 图片信息
    profile_image = scrapy.Field(
        output_processor=TakeFirst()
    )
    cover_image = scrapy.Field(
        output_processor=TakeFirst()
    )
    lifestyle_photos = scrapy.Field(
        output_processor=TakeFirst()
    )
    portrait_photos = scrapy.Field(
        output_processor=TakeFirst()
    )

    # 元数据
    source = scrapy.Field(
        output_processor=TakeFirst()
    )
    source_url = scrapy.Field(
        output_processor=TakeFirst()
    )
    crawled_at = scrapy.Field(
        output_processor=TakeFirst()
    )


class ActressCompleteItem(scrapy.Item):
    """完整女友数据项"""

    # 基本信息
    name = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    name_en = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    alias = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )

    # 个人资料
    birth_date = scrapy.Field(
        input_processor=MapCompose(parse_date),
        output_processor=TakeFirst()
    )
    debut_date = scrapy.Field(
        input_processor=MapCompose(parse_date),
        output_processor=TakeFirst()
    )
    height = scrapy.Field(
        input_processor=MapCompose(int),
        output_processor=TakeFirst()
    )
    weight = scrapy.Field(
        input_processor=MapCompose(int),
        output_processor=TakeFirst()
    )
    measurements = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    cup_size = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    nationality = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )

    # 图片信息
    profile_image = scrapy.Field(
        output_processor=TakeFirst()
    )
    cover_image = scrapy.Field(
        output_processor=TakeFirst()
    )
    gallery_images = scrapy.Field(
        output_processor=TakeFirst()
    )

    # 统计信息
    popularity_score = scrapy.Field(
        input_processor=MapCompose(int),
        output_processor=TakeFirst()
    )
    movie_count = scrapy.Field(
        input_processor=MapCompose(int),
        output_processor=TakeFirst()
    )

    # 元数据
    data_type = scrapy.Field(
        output_processor=TakeFirst()
    )
    source = scrapy.Field(
        output_processor=TakeFirst()
    )
    source_url = scrapy.Field(
        output_processor=TakeFirst()
    )
    crawled_at = scrapy.Field(
        output_processor=TakeFirst()
    )


class MovieCompleteItem(scrapy.Item):
    """完整作品数据项"""

    # 基本信息
    censored_id = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    movie_title = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    movie_hash = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )

    # 发行信息
    release_date = scrapy.Field(
        input_processor=MapCompose(parse_date),
        output_processor=TakeFirst()
    )
    movie_length = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    director = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    studio = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    label = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    series = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )

    # 演员信息
    jav_idols = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    related_actress = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    actress_url = scrapy.Field(
        output_processor=TakeFirst()
    )

    # 分类信息
    genre = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    movie_tags = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )

    # 图片信息
    movie_pic_cover = scrapy.Field(
        output_processor=TakeFirst()
    )
    sample_images = scrapy.Field(
        output_processor=TakeFirst()
    )

    # 磁力链接
    magnet_links = scrapy.Field()

    # 元数据
    data_type = scrapy.Field(
        output_processor=TakeFirst()
    )
    source = scrapy.Field(
        output_processor=TakeFirst()
    )
    source_url = scrapy.Field(
        output_processor=TakeFirst()
    )
    crawled_at = scrapy.Field(
        output_processor=TakeFirst()
    )
