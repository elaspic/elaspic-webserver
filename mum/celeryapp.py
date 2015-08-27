from __future__ import absolute_import 

import os 

from celery import Celery 
from celery.signals import worker_process_init

from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mum.settings')

app = Celery('mum') 
app.config_from_object('django.conf:settings') 
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS) 


@worker_process_init.connect
def fix_multiprocessing(**kwargs):
    from multiprocessing import current_process
    try:
        current_process()._config
    except AttributeError:
        current_process()._config = {'semprefix': '/mp'}


@app.task(bind=True)
def debug_task(self): 
    print('Request: {0!r}'.format(self.request))
    
