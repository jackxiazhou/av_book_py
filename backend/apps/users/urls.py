from django.urls import path
from django.http import JsonResponse

def user_profile(request):
    return JsonResponse({'message': 'User API endpoint'})

urlpatterns = [
    path('', user_profile, name='user-profile'),
]
