import os
import os.path as op
import sys

import django
import pytest

TESTS_DIR = op.dirname(op.abspath(__file__))
BASE_DIR = op.dirname(TESTS_DIR)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mum.settings.local')

django.setup()

# @pytest.fixture(scope='session')
# def django_db_setup():
#     settings.DATABASES['default']['NAME'] = (
#         'test_' + settings.DATABASES['default']['NAME']
#     )
#     # settings.DATABASES['default'] = {
#     #     'ENGINE': 'django.db.backends.mysql',
#     #     'NAME': 'test_elaspic_webserver',
#     #     'USER': 'elaspic-web',
#     #     'PASSWORD': 'elaspic',
#     #     'HOST': '192.168.6.19',
#     #     'PORT': ''
#     # }
#

# @pytest.fixture(scope='session')
# def django_db_keepdb():
#     return True
#
#
# @pytest.fixture(autouse=True)
# def enable_db_access(db):
#     pass
