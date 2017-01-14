import os
import os.path as op
import sys


BASE_DIR = op.dirname(op.abspath(__file__))
print(BASE_DIR)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mum.settings.test')

import django
django.setup()


# import pytest
#
# @pytest.fixture(scope='session')
# def django_db_setup():
#     """Avoid creating/setting up the test database.
#
#     Source: http://pytest-django.readthedocs.io/en/latest/database.html#use-a-read-only-database
#     """
#     pass
#
#
# @pytest.fixture
# def db_access_without_rollback_and_truncate(request, django_db_setup, django_db_blocker):
#     """
#     Source: http://pytest-django.readthedocs.io/en/latest/database.html#use-a-read-only-database
#     """
#     django_db_blocker.unblock()
#     request.addfinalizer(django_db_blocker.restore)
