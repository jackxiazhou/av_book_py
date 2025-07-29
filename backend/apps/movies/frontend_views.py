"""
Frontend views for movies app.
"""

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Movie


def movie_list(request):
    """影片列表页面"""
    movies = Movie.objects.all().order_by('-created_at')[:20]
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AVBook - 影片列表</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .movie { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
            .movie h3 { margin: 0 0 10px 0; color: #333; }
            .movie p { margin: 5px 0; color: #666; }
            .movie a { color: #007bff; text-decoration: none; }
            .movie a:hover { text-decoration: underline; }
            .header { background: #f8f9fa; padding: 20px; margin: -20px -20px 20px -20px; }
            .admin-link { background: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎬 AVBook 影片数据库</h1>
            <a href="/admin/" class="admin-link">管理后台</a>
            <a href="/actresses/" class="admin-link">女友列表</a>
        </div>
        
        <h2>最新影片 (共 """ + str(Movie.objects.count()) + """ 部)</h2>
    """
    
    for movie in movies:
        html += f"""
        <div class="movie">
            <div style="display: flex; gap: 15px;">
                <div style="flex-shrink: 0;">
                    {f'<img src="{movie.movie_pic_cover}" style="width: 120px; height: 160px; object-fit: cover; border-radius: 5px;" />' if movie.movie_pic_cover else '<div style="width: 120px; height: 160px; background: #f0f0f0; border-radius: 5px; display: flex; align-items: center; justify-content: center; color: #999;">无封面</div>'}
                </div>
                <div style="flex: 1;">
                    <h3><a href="/movies/{movie.pk}/">{movie.censored_id}</a></h3>
                    <p><strong>标题:</strong> {movie.movie_title}</p>
                    <p><strong>导演:</strong> {movie.director or '未知'}</p>
                    <p><strong>制作商:</strong> {movie.studio or '未知'}</p>
                    <p><strong>类型:</strong> {movie.genre or '未分类'}</p>
                    <p><strong>来源:</strong> {movie.source}</p>
                    <p><strong>创建时间:</strong> {movie.created_at.strftime('%Y-%m-%d %H:%M')}</p>
                </div>
            </div>
        </div>
        """
    
    html += """
        <div style="margin-top: 30px; text-align: center;">
            <a href="/admin/movies/movie/" class="admin-link">在管理后台查看所有影片</a>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)


def movie_detail(request, pk):
    """影片详情页面"""
    movie = get_object_or_404(Movie, pk=pk)
    
    # 获取标签
    tags = movie.tags.all()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{movie.censored_id} - AVBook</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background: #f8f9fa; padding: 20px; margin: -20px -20px 20px -20px; }}
            .movie-detail {{ max-width: 800px; }}
            .field {{ margin: 10px 0; }}
            .field strong {{ display: inline-block; width: 100px; color: #333; }}
            .tag {{ background: #007bff; color: white; padding: 2px 8px; border-radius: 3px; margin-right: 5px; }}
            .admin-link {{ background: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 3px; margin-right: 10px; }}
            .back-link {{ background: #6c757d; color: white; padding: 10px 15px; text-decoration: none; border-radius: 3px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>影片详情</h1>
            <a href="/admin/movies/movie/{movie.pk}/change/" class="admin-link">编辑</a>
            <a href="/movies/" class="back-link">返回列表</a>
        </div>
        
        <div class="movie-detail">
            <div style="display: flex; gap: 30px; margin-bottom: 30px;">
                <div style="flex-shrink: 0;">
                    {f'<img src="{movie.movie_pic_cover}" style="width: 300px; height: 400px; object-fit: cover; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);" />' if movie.movie_pic_cover else '<div style="width: 300px; height: 400px; background: #f0f0f0; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #999; font-size: 24px;">无封面</div>'}
                </div>
                <div style="flex: 1;">
                    <h2>{movie.censored_id}</h2>
            
            <div class="field">
                <strong>标题:</strong> {movie.movie_title}
            </div>
            
            <div class="field">
                <strong>发行日期:</strong> {movie.release_date or '未知'}
            </div>
            
            <div class="field">
                <strong>时长:</strong> {movie.movie_length or '未知'}
            </div>
            
            <div class="field">
                <strong>导演:</strong> {movie.director or '未知'}
            </div>
            
            <div class="field">
                <strong>制作商:</strong> {movie.studio or '未知'}
            </div>
            
            <div class="field">
                <strong>发行商:</strong> {movie.label or '未知'}
            </div>
            
            <div class="field">
                <strong>系列:</strong> {movie.series or '未知'}
            </div>
            
            <div class="field">
                <strong>类型:</strong> {movie.genre or '未分类'}
            </div>
            
            <div class="field">
                <strong>演员:</strong> {movie.jav_idols or '未知'}
            </div>

            <div class="field">
                <strong>关联女友:</strong>
    """

    # 显示关联女友
    actresses = movie.actresses.all()
    if actresses:
        for actress in actresses:
            html += f'<a href="/actresses/{actress.pk}/" style="background: #28a745; color: white; padding: 4px 8px; border-radius: 3px; margin-right: 5px; text-decoration: none;">{actress.name}</a>'
    else:
        html += '暂无关联女友'

    html += f"""
            </div>

            <div class="field">
                <strong>影片标记:</strong> {movie.movie_tags or '无标记'}
            </div>
            
            <div class="field">
                <strong>标签:</strong> 
    """
    
    if tags:
        for tag in tags:
            html += f'<span class="tag" style="background-color: {tag.color};">{tag.name}</span>'
    else:
        html += '无标签'
    
    html += f"""
            </div>
                </div>
            </div>

            <div class="field">
                <strong>数据来源:</strong> {movie.source}
            </div>
            
            <div class="field">
                <strong>浏览次数:</strong> {movie.view_count}
            </div>
            
            <div class="field">
                <strong>下载次数:</strong> {movie.download_count}
            </div>
            
            <div class="field">
                <strong>创建时间:</strong> {movie.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            </div>
            
            <div class="field">
                <strong>更新时间:</strong> {movie.updated_at.strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>

        <!-- 样例图片展示 -->
    """

    sample_images = movie.sample_images_list
    if sample_images:
        html += f"""
        <div style="margin-top: 30px;">
            <h3>样例图片</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
        """
        for img in sample_images:
            html += f'<img src="{img}" style="width: 100%; height: 150px; object-fit: cover; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />'
        html += """
            </div>
        </div>
        """

    html += """
        
        <div style="margin-top: 30px;">
            <a href="/admin/movies/movie/{movie.pk}/change/" class="admin-link">在管理后台编辑</a>
            <a href="/movies/" class="back-link">返回影片列表</a>
        </div>
    </body>
    </html>
    """
    
    # 增加浏览次数
    movie.increment_view_count()
    
    return HttpResponse(html)
