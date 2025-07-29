# 🛠️ 开发指南

## 📋 开发环境设置

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd av_book_vsproject_0727

# 安装Python依赖
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 安装Node.js依赖
cd ../frontend
npm install
```

### 2. 开发服务器启动

```bash
# 启动后端开发服务器
cd backend
python manage.py runserver

# 启动前端开发服务器
cd frontend
npm start
```

## 🔧 后端开发

### 数据模型开发

#### 女友模型 (`backend/apps/actresses/models.py`)
```python
from django.db import models

class Actress(models.Model):
    name = models.CharField(max_length=100, verbose_name='姓名')
    birth_date = models.DateField(null=True, blank=True, verbose_name='生日')
    height = models.IntegerField(null=True, blank=True, verbose_name='身高')
    cup_size = models.CharField(max_length=10, blank=True, verbose_name='罩杯')
    profile_image = models.URLField(blank=True, verbose_name='头像')
    
    class Meta:
        verbose_name = '女友'
        verbose_name_plural = '女友'
```

#### 作品模型 (`backend/apps/movies/models.py`)
```python
class Movie(models.Model):
    censored_id = models.CharField(max_length=50, unique=True, verbose_name='番号')
    movie_title = models.CharField(max_length=200, verbose_name='标题')
    release_date = models.DateField(null=True, blank=True, verbose_name='发行日期')
    cover_image = models.URLField(blank=True, verbose_name='封面')
    actresses = models.ManyToManyField(Actress, related_name='movies', verbose_name='参演女友')
```

### API开发

#### 视图开发 (`backend/apps/actresses/views.py`)
```python
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Actress
from .serializers import ActressSerializer

class ActressViewSet(viewsets.ModelViewSet):
    queryset = Actress.objects.all()
    serializer_class = ActressSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['cup_size', 'height']
    search_fields = ['name']
```

#### 序列化器开发 (`backend/apps/actresses/serializers.py`)
```python
from rest_framework import serializers
from .models import Actress

class ActressSerializer(serializers.ModelSerializer):
    movies_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Actress
        fields = '__all__'
    
    def get_movies_count(self, obj):
        return obj.movies.count()
```

### 管理命令开发

#### 创建新的管理命令
```python
# backend/apps/crawler/management/commands/my_crawler.py
from django.core.management.base import BaseCommand
from apps.actresses.models import Actress

class Command(BaseCommand):
    help = '我的爬虫命令'
    
    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=10, help='处理数量')
    
    def handle(self, *args, **options):
        count = options['count']
        self.stdout.write(f'开始处理 {count} 个项目')
        
        # 爬虫逻辑
        for i in range(count):
            self.stdout.write(f'处理第 {i+1} 个项目')
        
        self.stdout.write(self.style.SUCCESS('处理完成'))
```

### 数据库操作

```bash
# 创建迁移文件
python manage.py makemigrations

# 应用迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 进入Django Shell
python manage.py shell
```

## 🎨 前端开发

### 组件开发

#### 女友列表组件 (`frontend/src/components/ActressList.tsx`)
```tsx
import React, { useState, useEffect } from 'react';
import { fetchActresses } from '../services/api';

interface Actress {
  id: number;
  name: string;
  profile_image: string;
  movies_count: number;
}

const ActressList: React.FC = () => {
  const [actresses, setActresses] = useState<Actress[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadActresses = async () => {
      try {
        const data = await fetchActresses();
        setActresses(data.results);
      } catch (error) {
        console.error('加载女友列表失败:', error);
      } finally {
        setLoading(false);
      }
    };

    loadActresses();
  }, []);

  if (loading) return <div>加载中...</div>;

  return (
    <div className="actresses-grid">
      {actresses.map(actress => (
        <div key={actress.id} className="actress-card">
          <img src={actress.profile_image} alt={actress.name} />
          <h3>{actress.name}</h3>
          <p>{actress.movies_count} 部作品</p>
        </div>
      ))}
    </div>
  );
};

export default ActressList;
```

### API服务开发

#### API服务封装 (`frontend/src/services/api.ts`)
```typescript
const API_BASE_URL = 'http://localhost:8000/api';

export interface ApiResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const fetchActresses = async (params?: {
  search?: string;
  cup_size?: string;
  page?: number;
}): Promise<ApiResponse<Actress>> => {
  const url = new URL(`${API_BASE_URL}/actresses/`);
  
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value) url.searchParams.append(key, value.toString());
    });
  }
  
  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error('获取女友列表失败');
  }
  
  return response.json();
};

export const fetchActressDetail = async (id: number): Promise<Actress> => {
  const response = await fetch(`${API_BASE_URL}/actresses/${id}/`);
  if (!response.ok) {
    throw new Error('获取女友详情失败');
  }
  
  return response.json();
};
```

### 路由配置

#### 路由设置 (`frontend/src/App.tsx`)
```tsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ActressesPage from './pages/ActressesPage';
import MoviesPage from './pages/MoviesPage';
import ActressDetailPage from './pages/ActressDetailPage';

const App: React.FC = () => {
  return (
    <Router>
      <div className="app">
        <Routes>
          <Route path="/" element={<ActressesPage />} />
          <Route path="/actresses" element={<ActressesPage />} />
          <Route path="/actresses/:id" element={<ActressDetailPage />} />
          <Route path="/movies" element={<MoviesPage />} />
        </Routes>
      </div>
    </Router>
  );
};

export default App;
```

## 🕷️ 爬虫开发

### Scrapy爬虫开发

#### 创建新爬虫 (`crawler/avbook_spider/spiders/new_spider.py`)
```python
import scrapy
from ..items import ActressItem

class NewSpider(scrapy.Spider):
    name = 'new_spider'
    allowed_domains = ['example.com']
    start_urls = ['https://example.com/actresses']
    
    def parse(self, response):
        # 解析女友列表页
        actress_links = response.css('.actress-link::attr(href)').getall()
        
        for link in actress_links:
            yield response.follow(link, self.parse_actress)
    
    def parse_actress(self, response):
        # 解析女友详情页
        item = ActressItem()
        item['name'] = response.css('.actress-name::text').get()
        item['birth_date'] = response.css('.birth-date::text').get()
        item['height'] = response.css('.height::text').re_first(r'(\d+)')
        
        yield item
```

### Django管理命令爬虫

#### 多线程爬虫开发
```python
# backend/apps/crawler/management/commands/custom_crawler.py
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        # 创建线程池
        with ThreadPoolExecutor(max_workers=4) as executor:
            # 提交任务
            futures = []
            for i in range(10):
                future = executor.submit(self.crawl_item, i)
                futures.append(future)
            
            # 等待完成
            for future in futures:
                result = future.result()
                self.stdout.write(f'完成: {result}')
    
    def crawl_item(self, item_id):
        # 爬虫逻辑
        import time
        time.sleep(1)  # 模拟网络请求
        return f'Item {item_id} processed'
```

## 🧪 测试开发

### 后端测试

#### 模型测试 (`backend/apps/actresses/tests.py`)
```python
from django.test import TestCase
from .models import Actress

class ActressModelTest(TestCase):
    def setUp(self):
        self.actress = Actress.objects.create(
            name='测试女友',
            height=160,
            cup_size='C'
        )
    
    def test_actress_creation(self):
        self.assertEqual(self.actress.name, '测试女友')
        self.assertEqual(self.actress.height, 160)
    
    def test_actress_str(self):
        self.assertEqual(str(self.actress), '测试女友')
```

#### API测试
```python
from rest_framework.test import APITestCase
from rest_framework import status

class ActressAPITest(APITestCase):
    def test_get_actresses(self):
        response = self.client.get('/api/actresses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

### 前端测试

#### 组件测试 (`frontend/src/components/__tests__/ActressList.test.tsx`)
```tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import ActressList from '../ActressList';

// Mock API
jest.mock('../../services/api', () => ({
  fetchActresses: jest.fn(() => Promise.resolve({
    results: [
      { id: 1, name: '测试女友', profile_image: '', movies_count: 5 }
    ]
  }))
}));

test('渲染女友列表', async () => {
  render(<ActressList />);
  
  // 等待数据加载
  const actressName = await screen.findByText('测试女友');
  expect(actressName).toBeInTheDocument();
});
```

## 🔧 调试技巧

### 后端调试

```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 使用Django调试工具栏
pip install django-debug-toolbar

# 查看SQL查询
from django.db import connection
print(connection.queries)
```

### 前端调试

```typescript
// 使用console.log调试
console.log('数据:', data);

// 使用React DevTools
// 安装浏览器扩展

// 使用断点调试
debugger;
```

### 爬虫调试

```python
# Scrapy调试
scrapy shell "https://example.com"

# 查看请求和响应
def parse(self, response):
    self.logger.info(f'Processing {response.url}')
    print(response.text)
```

## 📝 代码规范

### Python代码规范

```python
# 使用PEP 8规范
# 安装代码格式化工具
pip install black flake8

# 格式化代码
black .

# 检查代码质量
flake8 .
```

### TypeScript代码规范

```bash
# 安装ESLint和Prettier
npm install --save-dev eslint prettier

# 格式化代码
npm run format

# 检查代码质量
npm run lint
```

## 🚀 性能优化

### 后端优化

```python
# 数据库查询优化
actresses = Actress.objects.select_related('movies').prefetch_related('photos')

# 缓存优化
from django.core.cache import cache
result = cache.get('actresses_list')
if not result:
    result = expensive_operation()
    cache.set('actresses_list', result, 300)
```

### 前端优化

```tsx
// 使用React.memo优化组件
const ActressCard = React.memo(({ actress }) => {
  return <div>{actress.name}</div>;
});

// 使用useMemo优化计算
const filteredActresses = useMemo(() => {
  return actresses.filter(a => a.name.includes(searchTerm));
}, [actresses, searchTerm]);
```

## ✅ 开发检查清单

- [ ] 代码符合规范
- [ ] 添加了必要的注释
- [ ] 编写了单元测试
- [ ] API文档已更新
- [ ] 数据库迁移已创建
- [ ] 前端组件可复用
- [ ] 错误处理完善
- [ ] 性能已优化
- [ ] 安全性已考虑
- [ ] 日志记录完整

## 🎯 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/new-feature`)
3. 提交更改 (`git commit -am 'Add new feature'`)
4. 推送到分支 (`git push origin feature/new-feature`)
5. 创建Pull Request

欢迎贡献代码和提出改进建议！
