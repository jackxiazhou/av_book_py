"""
Movie URLs for AVBook API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MovieViewSet, MovieTagViewSet, MovieRatingViewSet

router = DefaultRouter()
router.register(r'movies', MovieViewSet, basename='movie')
router.register(r'movie-tags', MovieTagViewSet, basename='movie-tag')
router.register(r'movie-ratings', MovieRatingViewSet, basename='movie-rating')

urlpatterns = [
    path('', include(router.urls)),
]
