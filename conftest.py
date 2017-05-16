import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'mum.settings.pytest'

import django
django.setup()

assert django.conf.settings.DATABASES['default']['NAME'].startswith('pytest')
