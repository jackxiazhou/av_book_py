"""
Celery configuration for AVBook project.
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avbook.settings')

app = Celery('avbook')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    'crawl-javbus-daily': {
        'task': 'apps.crawler.tasks.crawl_javbus',
        'schedule': 60.0 * 60.0 * 24,  # 24 hours
        'options': {'queue': 'crawler'}
    },
    'crawl-avmoo-daily': {
        'task': 'apps.crawler.tasks.crawl_avmoo',
        'schedule': 60.0 * 60.0 * 24,  # 24 hours
        'options': {'queue': 'crawler'}
    },
    'crawl-all-sites-weekly': {
        'task': 'apps.crawler.tasks.crawl_all_sites',
        'schedule': 60.0 * 60.0 * 24 * 7,  # Weekly
        'options': {'queue': 'crawler'}
    },
    'cleanup-old-logs': {
        'task': 'apps.core.tasks.cleanup_old_logs',
        'schedule': 60.0 * 60.0 * 24 * 7,  # Weekly
        'options': {'queue': 'maintenance'}
    },
}

app.conf.task_routes = {
    'apps.crawler.tasks.*': {'queue': 'crawler'},
    'apps.core.tasks.*': {'queue': 'maintenance'},
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

