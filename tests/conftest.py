import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.getenv("ENV_FILE", ".env.test"), override=True)

from pathlib import Path

import django
import pytest

import web_pipeline.conf

django.setup()

# Database settings
if not django.conf.settings.DATABASES["default"]["USER"].endswith("-readonly"):
    django.conf.settings.DATABASES["default"]["USER"] += "-readonly"
    django.conf.settings.DATABASES["default"]["PASSWORD"] += "-readonly"
assert django.conf.settings.DATABASES["default"]["USER"].endswith("-readonly")
assert django.conf.settings.DATABASES["default"]["PASSWORD"].endswith("-readonly")

# Data dir
web_pipeline.conf.DB_PATH = (
    Path(__file__).resolve(strict=True).parent.joinpath("data_dir", "elaspic").as_posix()
)


@pytest.fixture(scope="session")
def django_db_setup():
    pass
