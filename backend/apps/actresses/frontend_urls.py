"""
女友/演员前端URL配置
"""

from django.urls import path
from . import frontend_views

urlpatterns = [
    path('', frontend_views.actress_list, name='actress-list'),
    path('<int:pk>/', frontend_views.actress_detail, name='actress-detail'),
]
