import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.getenv("ENV_FILE", ".env.test"))

import django
import pytest

django.setup()

if not django.conf.settings.DATABASES["default"]["USER"].endswith("-readonly"):
    django.conf.settings.DATABASES["default"]["USER"] += "-readonly"
assert django.conf.settings.DATABASES["default"]["USER"].endswith("-readonly")


@pytest.fixture(scope="session")
def django_db_setup():
    pass
