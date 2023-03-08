import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'youtube_spotify.settings')

app = Celery('youtube_spotify')

app.conf.broker_url = 'redis://localhost:6379/0'
app.conf.broker_transport_options = {'visibility_timeout': 3600}
app.conf.result_backend = 'redis://localhost:6379/0'
app.conf.result_backend_transport_options = {
    'retry_policy': {
       'timeout': 5.0
    }
}
app.conf.result_backend_transport_options = {
    'result_chord_ordered': False  
}
# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')