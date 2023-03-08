from celery import Celery

app = Celery('tasks', backend='redis://localhost', broker='redis://localhost:6379/0')

@app.task
def smh():
    pass