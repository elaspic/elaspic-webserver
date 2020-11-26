import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.getenv("ENV_FILE"))

import django
import pytest

django.setup()

assert django.conf.settings.DATABASES["default"]["USER"].endswith("-readonly")


@pytest.fixture(scope="session")
def django_db_setup():
    pass
