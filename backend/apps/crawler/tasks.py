from celery import shared_task
import subprocess
import os
from django.conf import settings


@shared_task(bind=True)
def crawl_avmoo(self, pages=5):
    """
    Celery task to run Avmoo crawler
    """
    try:
        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        crawler_dir = os.path.join(project_root, 'crawler')
        
        # 构建命令
        scrapy_cmd = [
            'python', '-m', 'scrapy', 'crawl', 'avmoo',
            '-s', 'DOWNLOAD_DELAY=3',
            '-s', 'LOG_LEVEL=INFO',
            '-a', f'max_pages={pages}',
        ]
        
        # 运行爬虫
        result = subprocess.run(
            scrapy_cmd,
            cwd=crawler_dir,
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode == 0:
            return {
                'status': 'success',
                'message': 'Avmoo crawler completed successfully',
                'output': result.stdout[-500:] if result.stdout else ''
            }
        else:
            return {
                'status': 'error',
                'message': 'Avmoo crawler failed',
                'error': result.stderr[-500:] if result.stderr else ''
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Crawler task failed: {str(e)}'
        }


@shared_task
def crawl_all_sites():
    """
    Run all crawlers in sequence
    """
    results = {}
    
    # 运行JAVBus爬虫
    javbus_result = crawl_javbus.delay(pages=3)
    results['javbus'] = javbus_result.get(timeout=600)
    
    # 运行Avmoo爬虫
    avmoo_result = crawl_avmoo.delay(pages=3)
    results['avmoo'] = avmoo_result.get(timeout=600)
    
    return results