"""
Magnet URLs for AVBook API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MagnetLinkViewSet, MagnetCategoryViewSet, DownloadHistoryViewSet

router = DefaultRouter()
router.register(r'', MagnetLinkViewSet, basename='magnet')
router.register(r'categories', MagnetCategoryViewSet, basename='magnet-category')
router.register(r'downloads', DownloadHistoryViewSet, basename='download-history')

urlpatterns = [
    path('', include(router.urls)),
]
