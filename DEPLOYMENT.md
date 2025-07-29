# 🚀 部署指南

## 📋 部署概述

本文档详细说明如何部署AV Book系统的三个核心组件：前端、后端和爬虫守护线程。

## 🔧 系统要求

### 硬件要求
- **CPU**: 2核心以上
- **内存**: 4GB以上
- **存储**: 20GB以上可用空间
- **网络**: 稳定的互联网连接

### 软件要求
- **操作系统**: Windows 10+ / Ubuntu 18+ / macOS 10.15+
- **Python**: 3.8+
- **Node.js**: 16+
- **Git**: 最新版本

## 🚀 快速部署

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd av_book_vsproject_0727

# 检查Python版本
python --version

# 检查Node.js版本
node --version
```

### 2. 后端部署

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 启动后端服务
python manage.py runserver 0.0.0.0:8000
```

### 3. 前端部署

```bash
# 新开终端，进入前端目录
cd frontend

# 安装依赖
npm install

# 启动前端服务
npm start
```

### 4. 爬虫守护线程部署

```bash
# 新开终端，进入项目根目录
cd av_book_vsproject_0727

# 激活后端虚拟环境
cd backend
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 启动多线程爬虫 (后台运行)
nohup python manage.py crawl_multithreaded --max-actresses=100 --max-workers=8 > crawl.log 2>&1 &

# 启动图片下载器 (后台运行)
nohup python manage.py download_movie_images --max-movies=500 --delay=1 > download.log 2>&1 &

# 启动深度递归爬取 (后台运行)
nohup python manage.py deep_recursive_crawl --start-actress-id="b75aa78f5dd72299" --max-depth=3 > recursive.log 2>&1 &
```

## 🔄 生产环境部署

### 1. 使用Gunicorn部署后端

```bash
# 安装Gunicorn
pip install gunicorn

# 启动Gunicorn服务
gunicorn --bind 0.0.0.0:8000 --workers 4 avbook.wsgi:application
```

### 2. 使用Nginx反向代理

```nginx
# /etc/nginx/sites-available/avbook
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/frontend/build;
        try_files $uri $uri/ /index.html;
    }

    # 后端API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 媒体文件
    location /media/ {
        alias /path/to/backend/media/;
    }
}
```

### 3. 使用PM2管理Node.js进程

```bash
# 安装PM2
npm install -g pm2

# 构建前端
npm run build

# 使用serve提供静态文件服务
npm install -g serve
pm2 start "serve -s build -l 3000" --name "avbook-frontend"

# 管理PM2进程
pm2 list
pm2 restart avbook-frontend
pm2 logs avbook-frontend
```

### 4. 使用Supervisor管理爬虫进程

```ini
# /etc/supervisor/conf.d/avbook-crawler.conf
[program:avbook-multithreaded]
command=/path/to/venv/bin/python manage.py crawl_multithreaded --max-actresses=100 --max-workers=8
directory=/path/to/backend
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/avbook/crawler.log
stderr_logfile=/var/log/avbook/crawler_error.log

[program:avbook-downloader]
command=/path/to/venv/bin/python manage.py download_movie_images --max-movies=500 --delay=1
directory=/path/to/backend
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/avbook/downloader.log
stderr_logfile=/var/log/avbook/downloader_error.log
```

## 🔧 配置说明

### 后端配置

#### Django设置 (`backend/avbook/settings.py`)
```python
# 生产环境设置
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com', 'localhost']

# 数据库配置 (可选择PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'avbook',
        'USER': 'avbook_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 静态文件配置
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
```

### 前端配置

#### API地址配置 (`frontend/src/services/api.ts`)
```typescript
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://your-domain.com/api'
  : 'http://localhost:8000/api';
```

### 爬虫配置

#### 爬虫参数调优
```bash
# 高性能配置 (服务器环境)
python manage.py crawl_multithreaded \
  --max-actresses=200 \
  --max-workers=16 \
  --max-movies-per-actress=30 \
  --delay=0.5

# 保守配置 (避免被封)
python manage.py crawl_multithreaded \
  --max-actresses=50 \
  --max-workers=4 \
  --max-movies-per-actress=10 \
  --delay=2.0
```

## 📊 监控和维护

### 1. 日志监控

```bash
# 查看爬虫日志
tail -f crawl.log

# 查看下载日志
tail -f download.log

# 查看Django日志
tail -f /var/log/django/avbook.log
```

### 2. 性能监控

```bash
# 检查系统资源
htop

# 检查磁盘使用
df -h

# 检查网络连接
netstat -an | grep :8000
```

### 3. 数据库维护

```bash
# 数据库备份
python manage.py dumpdata > backup.json

# 数据库恢复
python manage.py loaddata backup.json

# 清理过期数据
python manage.py cleanup_old_data
```

## 🔒 安全配置

### 1. Django安全设置

```python
# settings.py
SECRET_KEY = 'your-secret-key'
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### 2. 防火墙配置

```bash
# 开放必要端口
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw enable
```

### 3. 定期更新

```bash
# 更新系统包
sudo apt update && sudo apt upgrade

# 更新Python依赖
pip install --upgrade -r requirements.txt

# 更新Node.js依赖
npm update
```

## 🎯 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 查找占用端口的进程
   netstat -ano | findstr :8000
   # 杀死进程
   taskkill /PID <PID> /F
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库服务
   python manage.py dbshell
   ```

3. **爬虫被封IP**
   ```bash
   # 增加延迟时间
   python manage.py crawl_multithreaded --delay=5.0
   ```

4. **内存不足**
   ```bash
   # 减少并发数
   python manage.py crawl_multithreaded --max-workers=2
   ```

## ✅ 部署检查清单

- [ ] Python和Node.js环境已安装
- [ ] 后端依赖已安装
- [ ] 数据库迁移已完成
- [ ] 前端依赖已安装
- [ ] 前端已构建
- [ ] 后端服务正常启动
- [ ] 前端服务正常启动
- [ ] API接口可正常访问
- [ ] 爬虫守护线程已启动
- [ ] 日志文件正常生成
- [ ] 图片存储目录已创建
- [ ] 防火墙配置正确
- [ ] 域名解析正确 (生产环境)

## 🎉 部署完成

部署完成后，您可以通过以下地址访问系统：

- **前端界面**: http://localhost:3000 (开发) / http://your-domain.com (生产)
- **后端API**: http://localhost:8000/api/ (开发) / http://your-domain.com/api/ (生产)
- **管理后台**: http://localhost:8000/admin/ (开发) / http://your-domain.com/admin/ (生产)

系统将自动开始爬取数据并下载图片，您可以通过日志文件监控爬取进度。
