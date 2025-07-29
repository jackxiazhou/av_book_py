from django.urls import path
from . import views

urlpatterns = [
    path('', views.crawler_status, name='crawler-status'),
    path('start/avmoo/', views.start_avmoo_crawler, name='start-avmoo'),
    path('start/all/', views.start_all_crawlers, name='start-all'),
]

