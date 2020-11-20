import django
import pytest

django.setup()

assert django.conf.settings.DATABASES["default"]["USER"].endswith("-readonly")


@pytest.fixture(scope="session")
def django_db_setup():
    pass
