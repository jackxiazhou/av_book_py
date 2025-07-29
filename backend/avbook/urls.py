"""
AVBook URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls.static import static
# from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API Documentation (暂时注释掉)
    # path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Movies frontend URLs
    path('movies/', include('apps.movies.frontend_urls')),

    # Actresses frontend URLs
    path('actresses/', include('apps.actresses.frontend_urls')),

    # API Routes
    path('api/', include('apps.movies.urls')),
    path('api/', include('apps.actresses.urls')),
    path('api/', include('apps.magnets.urls')),

    # Health Check (暂时注释掉)
    # path('health/', include('apps.core.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
