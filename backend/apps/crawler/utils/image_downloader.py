"""
图片下载和存储工具
"""

import os
import requests
import hashlib
from urllib.parse import urlparse, urljoin
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import time
import random


class ImageDownloader:
    def __init__(self, proxy_url=None, base_dir='images'):
        self.session = requests.Session()
        self.base_dir = base_dir
        
        if proxy_url:
            self.session.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://avmoo.cyou/',
        })
        
        # 创建存储目录
        self.ensure_directories()
    
    def ensure_directories(self):
        """确保存储目录存在"""
        directories = [
            f'{self.base_dir}/actresses/profiles',
            f'{self.base_dir}/actresses/covers', 
            f'{self.base_dir}/actresses/galleries',
            f'{self.base_dir}/movies/covers',
            f'{self.base_dir}/movies/samples',
        ]
        
        for directory in directories:
            os.makedirs(os.path.join(settings.MEDIA_ROOT, directory), exist_ok=True)
    
    def download_image(self, url, category='general', filename=None, max_retries=3):
        """
        下载图片并保存到本地
        
        Args:
            url: 图片URL
            category: 图片分类 (actress_profile, actress_cover, actress_gallery, movie_cover, movie_sample)
            filename: 自定义文件名
            max_retries: 最大重试次数
            
        Returns:
            本地文件路径或None
        """
        if not url:
            return None
        
        try:
            # 生成文件名
            if not filename:
                filename = self.generate_filename(url)
            
            # 确定存储路径
            storage_path = self.get_storage_path(category, filename)
            
            # 检查文件是否已存在
            if default_storage.exists(storage_path):
                print(f"Image already exists: {storage_path}")
                return storage_path
            
            # 下载图片
            for attempt in range(max_retries):
                try:
                    print(f"Downloading image: {url} (attempt {attempt + 1})")
                    
                    response = self.session.get(url, timeout=30, stream=True)
                    response.raise_for_status()
                    
                    # 检查内容类型
                    content_type = response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        print(f"Invalid content type: {content_type}")
                        return None
                    
                    # 检查文件大小
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB限制
                        print(f"File too large: {content_length} bytes")
                        return None
                    
                    # 读取图片内容
                    image_content = b''
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            image_content += chunk
                            if len(image_content) > 10 * 1024 * 1024:  # 10MB限制
                                print("File too large during download")
                                return None
                    
                    if len(image_content) < 1024:  # 至少1KB
                        print("File too small, probably not a valid image")
                        return None
                    
                    # 保存文件
                    saved_path = default_storage.save(storage_path, ContentFile(image_content))
                    print(f"Image saved: {saved_path}")
                    
                    # 添加延迟避免过于频繁的请求
                    time.sleep(random.uniform(1, 3))
                    
                    return saved_path
                    
                except requests.exceptions.RequestException as e:
                    print(f"Download attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(random.uniform(2, 5))
                    continue
            
            print(f"Failed to download after {max_retries} attempts: {url}")
            return None
            
        except Exception as e:
            print(f"Error downloading image {url}: {e}")
            return None
    
    def generate_filename(self, url):
        """根据URL生成文件名"""
        parsed_url = urlparse(url)
        
        # 获取原始文件名和扩展名
        original_filename = os.path.basename(parsed_url.path)
        if '.' in original_filename:
            name, ext = os.path.splitext(original_filename)
        else:
            name = original_filename
            ext = '.jpg'  # 默认扩展名
        
        # 生成唯一文件名
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        timestamp = str(int(time.time()))
        
        filename = f"{name}_{url_hash}_{timestamp}{ext}"
        
        # 清理文件名中的特殊字符
        filename = "".join(c for c in filename if c.isalnum() or c in '._-')
        
        return filename
    
    def get_storage_path(self, category, filename):
        """获取存储路径"""
        category_paths = {
            'actress_profile': f'{self.base_dir}/actresses/profiles',
            'actress_cover': f'{self.base_dir}/actresses/covers',
            'actress_gallery': f'{self.base_dir}/actresses/galleries',
            'movie_cover': f'{self.base_dir}/movies/covers',
            'movie_sample': f'{self.base_dir}/movies/samples',
            'general': f'{self.base_dir}/general',
        }
        
        base_path = category_paths.get(category, category_paths['general'])
        return os.path.join(base_path, filename)
    
    def download_multiple_images(self, urls, category='general', max_images=None):
        """
        批量下载图片
        
        Args:
            urls: 图片URL列表
            category: 图片分类
            max_images: 最大下载数量
            
        Returns:
            成功下载的文件路径列表
        """
        if not urls:
            return []
        
        if max_images:
            urls = urls[:max_images]
        
        downloaded_paths = []
        
        for i, url in enumerate(urls):
            print(f"Downloading image {i+1}/{len(urls)}: {url}")
            
            path = self.download_image(url, category)
            if path:
                downloaded_paths.append(path)
            
            # 批量下载时增加延迟
            if i < len(urls) - 1:
                time.sleep(random.uniform(2, 4))
        
        print(f"Downloaded {len(downloaded_paths)}/{len(urls)} images")
        return downloaded_paths
    
    def get_image_url(self, relative_path):
        """获取图片的访问URL"""
        if not relative_path:
            return None
        
        if relative_path.startswith('http'):
            return relative_path
        
        return urljoin(settings.MEDIA_URL, relative_path)
    
    def cleanup_old_images(self, days=30):
        """清理旧图片文件"""
        # 这里可以实现清理逻辑
        pass
