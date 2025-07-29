"""
女友/演员前端视图
"""

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Actress, ActressTag


def actress_list(request):
    """女友列表页面"""
    actresses = Actress.objects.all().order_by('-popularity_score', '-created_at')[:20]
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AVBook - 女友列表</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; }
            .actress { 
                border: 1px solid #ddd; margin: 15px 0; padding: 20px; 
                border-radius: 10px; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .actress h3 { margin: 0 0 10px 0; color: #333; }
            .actress p { margin: 5px 0; color: #666; }
            .actress a { color: #007bff; text-decoration: none; }
            .actress a:hover { text-decoration: underline; }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 30px; margin: -20px -20px 30px -20px; 
                border-radius: 0 0 15px 15px;
            }
            .admin-link { 
                background: #007bff; color: white; padding: 10px 15px; 
                text-decoration: none; border-radius: 5px; margin-right: 10px;
            }
            .status-active { color: #28a745; font-weight: bold; }
            .status-retired { color: #dc3545; }
            .tag { 
                background: #007bff; color: white; padding: 2px 8px; 
                border-radius: 15px; margin-right: 5px; font-size: 12px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>💕 AVBook 女友数据库</h1>
            <p>发现你的专属女友，探索无限可能</p>
            <a href="/admin/actresses/actress/" class="admin-link">管理后台</a>
            <a href="/movies/" class="admin-link">影片列表</a>
        </div>
        
        <h2>热门女友 (共 """ + str(Actress.objects.count()) + """ 位)</h2>
    """
    
    for actress in actresses:
        # 获取标签
        tags_html = ""
        for tag in actress.tags.all()[:3]:  # 最多显示3个标签
            tags_html += f'<span class="tag" style="background-color: {tag.color};">{tag.name}</span>'
        
        status_class = "status-active" if actress.is_active else "status-retired"
        
        html += f"""
        <div class="actress">
            <div style="display: flex; gap: 20px;">
                <div style="flex-shrink: 0;">
                    {f'<img src="{actress.profile_image}" style="width: 100px; height: 120px; object-fit: cover; border-radius: 10px;" />' if actress.profile_image else '<div style="width: 100px; height: 120px; background: linear-gradient(45deg, #ff9a9e, #fecfef); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-size: 24px;">👩</div>'}
                </div>
                <div style="flex: 1;">
                    <h3><a href="/actresses/{actress.pk}/">{actress.name}</a></h3>
                    {f'<p><strong>英文名:</strong> {actress.name_en}</p>' if actress.name_en else ''}
                    <p><strong>年龄:</strong> {actress.age}岁 | <strong>身高:</strong> {actress.height}cm | <strong>三围:</strong> {actress.measurements}</p>
                    <p><strong>状态:</strong> <span class="{status_class}">{actress.status}</span></p>
                    <p><strong>人气值:</strong> {actress.popularity_score} | <strong>作品数:</strong> {actress.movie_count} | <strong>浏览:</strong> {actress.view_count}</p>
                    {f'<p><strong>所属:</strong> {actress.agency}</p>' if actress.agency else ''}
                    <p><strong>标签:</strong> {tags_html if tags_html else '暂无标签'}</p>
                    <p><strong>加入时间:</strong> {actress.created_at.strftime('%Y-%m-%d')}</p>
                </div>
            </div>
        </div>
        """
    
    html += """
        <div style="margin-top: 30px; text-align: center;">
            <a href="/admin/actresses/actress/" class="admin-link">在管理后台查看所有女友</a>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)


def actress_detail(request, pk):
    """女友详情页面"""
    actress = get_object_or_404(Actress, pk=pk)
    
    # 获取标签
    tags = actress.tags.all()
    
    # 获取图片集
    gallery_images = actress.get_gallery_images_list()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{actress.name} - AVBook 女友详情</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; }}
            .header {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 30px; margin: -20px -20px 30px -20px; 
                border-radius: 0 0 15px 15px;
            }}
            .actress-detail {{ max-width: 1000px; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .field {{ margin: 15px 0; }}
            .field strong {{ display: inline-block; width: 120px; color: #333; }}
            .tag {{ 
                background: #007bff; color: white; padding: 4px 12px; 
                border-radius: 15px; margin-right: 8px; font-size: 14px;
            }}
            .admin-link {{ 
                background: #007bff; color: white; padding: 12px 20px; 
                text-decoration: none; border-radius: 5px; margin-right: 10px;
            }}
            .back-link {{ 
                background: #6c757d; color: white; padding: 12px 20px; 
                text-decoration: none; border-radius: 5px;
            }}
            .profile-section {{ display: flex; gap: 30px; margin-bottom: 30px; }}
            .profile-images {{ flex-shrink: 0; }}
            .profile-info {{ flex: 1; }}
            .gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; margin-top: 20px; }}
            .gallery img {{ width: 100%; height: 150px; object-fit: cover; border-radius: 8px; }}
            .social-links a {{ 
                display: inline-block; background: #007bff; color: white; 
                padding: 8px 15px; text-decoration: none; border-radius: 5px; margin-right: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>💕 女友详情</h1>
            <a href="/admin/actresses/actress/{actress.pk}/change/" class="admin-link">编辑资料</a>
            <a href="/actresses/" class="back-link">返回列表</a>
        </div>
        
        <div class="actress-detail">
            <div class="profile-section">
                <div class="profile-images">
                    {f'<img src="{actress.profile_image}" style="width: 200px; height: 250px; object-fit: cover; border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);" />' if actress.profile_image else '<div style="width: 200px; height: 250px; background: linear-gradient(45deg, #ff9a9e, #fecfef); border-radius: 15px; display: flex; align-items: center; justify-content: center; color: white; font-size: 48px;">👩</div>'}
                    {f'<br><br><img src="{actress.cover_image}" style="width: 200px; height: 120px; object-fit: cover; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);" />' if actress.cover_image else ''}
                </div>
                
                <div class="profile-info">
                    <h2>{actress.name}</h2>
                    {f'<h3 style="color: #666; margin-top: 0;">{actress.name_en}</h3>' if actress.name_en else ''}
                    
                    <div class="field">
                        <strong>年龄:</strong> {actress.age}岁 ({actress.birth_date or '生日未知'})
                    </div>
                    
                    <div class="field">
                        <strong>身材:</strong> {actress.height}cm / {actress.weight}kg / {actress.measurements}
                    </div>
                    
                    <div class="field">
                        <strong>罩杯:</strong> {actress.cup_size or '未知'}
                    </div>
                    
                    <div class="field">
                        <strong>血型:</strong> {actress.blood_type or '未知'}
                    </div>
                    
                    <div class="field">
                        <strong>国籍:</strong> {actress.nationality}
                    </div>
                    
                    <div class="field">
                        <strong>出道:</strong> {actress.debut_date or '未知'} ({actress.career_years}年经验 if actress.career_years else '')
                    </div>
                    
                    <div class="field">
                        <strong>状态:</strong> <span style="color: {'#28a745' if actress.is_active else '#dc3545'}; font-weight: bold;">{actress.status}</span>
                    </div>
                    
                    <div class="field">
                        <strong>所属:</strong> {actress.agency or '自由身'}
                    </div>
                </div>
            </div>
            
            <div class="field">
                <strong>标签:</strong> 
    """
    
    if tags:
        for tag in tags:
            html += f'<span class="tag" style="background-color: {tag.color};">{tag.name}</span>'
    else:
        html += '暂无标签'
    
    html += f"""
            </div>
            
            {f'<div class="field"><strong>个人简介:</strong><br>{actress.description}</div>' if actress.description else ''}
            
            {f'<div class="field"><strong>特长特色:</strong><br>{actress.specialties}</div>' if actress.specialties else ''}
            
            {f'<div class="field"><strong>别名:</strong> {actress.alias}</div>' if actress.alias else ''}
            
            <div class="field">
                <strong>统计数据:</strong> 
                人气值 {actress.popularity_score} | 作品数 {actress.movie_count} | 浏览 {actress.view_count} | 收藏 {actress.favorite_count}
            </div>
            
            <div class="field">
                <strong>时间信息:</strong> 
                加入时间 {actress.created_at.strftime('%Y-%m-%d')} | 最后更新 {actress.updated_at.strftime('%Y-%m-%d')}
            </div>
    """
    
    # 社交媒体链接
    social_links = []
    if actress.twitter:
        social_links.append(f'<a href="{actress.twitter}" target="_blank">Twitter</a>')
    if actress.instagram:
        social_links.append(f'<a href="{actress.instagram}" target="_blank">Instagram</a>')
    if actress.blog:
        social_links.append(f'<a href="{actress.blog}" target="_blank">官网/博客</a>')
    
    if social_links:
        html += f"""
            <div class="field">
                <strong>社交媒体:</strong><br>
                <div class="social-links">
                    {''.join(social_links)}
                </div>
            </div>
        """
    
    # 图片集
    if gallery_images:
        html += f"""
            <div class="field">
                <strong>图片集:</strong>
                <div class="gallery">
        """
        for img in gallery_images:
            html += f'<img src="{img}" />'
        html += """
                </div>
            </div>
        """
    
    html += f"""
        </div>
        
        <div style="margin-top: 30px; text-align: center;">
            <a href="/admin/actresses/actress/{actress.pk}/change/" class="admin-link">编辑女友资料</a>
            <a href="/actresses/" class="back-link">返回女友列表</a>
        </div>
    </body>
    </html>
    """
    
    # 增加浏览次数
    actress.increment_view_count()
    
    return HttpResponse(html)
