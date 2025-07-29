"""
Frontend URLs for movies app.
"""

from django.urls import path
from . import frontend_views

urlpatterns = [
    path('', frontend_views.movie_list, name='movie-list'),
    path('<int:pk>/', frontend_views.movie_detail, name='movie-detail'),
]
