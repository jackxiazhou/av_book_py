"""
Actress URLs for AVBook API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ActressViewSet

router = DefaultRouter()
router.register(r'actresses', ActressViewSet, basename='actress')

urlpatterns = [
    path('', include(router.urls)),
]
