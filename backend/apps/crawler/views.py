from rest_framework.decorators import api_view
from rest_framework.response import Response
from .tasks import crawl_avmoo, crawl_all_sites


@api_view(['POST'])
def start_avmoo_crawler(request):
    """启动Avmoo爬虫"""
    pages = request.data.get('pages', 5)
    
    task = crawl_avmoo.delay(pages=pages)
    
    return Response({
        'message': 'Avmoo crawler started',
        'task_id': task.id,
        'pages': pages
    })


@api_view(['POST'])
def start_all_crawlers(request):
    """启动所有爬虫"""
    task = crawl_all_sites.delay()
    
    return Response({
        'message': 'All crawlers started',
        'task_id': task.id
    })