from django.urls import path
from django.http import JsonResponse
from django.utils import timezone

def health_check(request):
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'AVBook API'
    })

urlpatterns = [
    path('', health_check, name='health-check'),
]
