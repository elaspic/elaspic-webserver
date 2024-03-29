import os
import os.path as op

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# Site settings
SITE_NAME = "ELASPIC"
DEBUG = os.getenv("DEBUG", "").lower() == "true"

SEND_CRASH_LOGS_TO_ADMINS = True
SEND_BROKEN_LINK_EMAILS = True
ADMINS = (("KimLab CCBR", os.getenv("ADMIN_EMAIL")),)
MANAGERS = ADMINS

# Databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        "HOST": os.getenv("DB_HOST"),
        # Set to empty string for default.
        "PORT": os.getenv("DB_PORT", ""),
    },
}

CACHES = {
    "default": {
        "BACKEND": os.getenv("CACHE_BACKEND", "django.core.cache.backends.locmem.LocMemCache"),
        "LOCATION": os.getenv("CACHE_LOCATION", "unique-snowflake"),
    }
}
if CACHES["default"]["BACKEND"] == "django.core.cache.backends.memcached.PyLibMCCache":
    CACHES["default"]["OPTIONS"] = {  # type: ignore
        "binary": True,
        "behaviors": {
            "ketama": True,
        },
    }

BASE_DIR = op.dirname(op.dirname(op.abspath(__file__)))
PROJECT_ROOT = op.dirname(BASE_DIR)

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN is not None:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
        release="elaspic-webserver@0.2.10",
    )

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
# ALLOWED_HOSTS = [SITE_URL, '142.150.84.65', 'elaspic.kimlab.org', 'elaspic.witvliet.ca']
SITE_URL = os.getenv("SITE_URL", "http://elaspic.kimlab.org")  # required only for 'sendEmail'
ALLOWED_HOSTS = "*"

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = "America/Toronto"

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = "en-us"

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: '/var/www/example.com/media/'
MEDIA_ROOT = os.getenv("MEDIA_ROOT", op.join(PROJECT_ROOT, "media"))

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: 'http://example.com/media/', 'http://media.example.com/'
MEDIA_URL = "/media/"

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' 'static/' subdirectories and in STATICFILES_DIRS.
# Example: '/var/www/example.com/static/'
STATIC_ROOT = os.getenv("STATIC_ROOT", op.join(PROJECT_ROOT, "static"))

# URL prefix for static files.
# Example: 'http://example.com/static/', 'http://static.example.com/'
STATIC_URL = "/static/"

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like '/home/html/static' or 'C:/www/django/static'.
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    # op.join(PROJECT_ROOT, 'static'),
    # op.join(PROJECT_ROOT, 'web_pipeline'),
    # op.join(PROJECT_ROOT, 'web_pipeline', 'static'),
    # '/home/kimlab1/database_data/elaspic.kimlab.org',
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

FILE_UPLOAD_PERMISSIONS = 0o664
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o775
FILE_UPLOAD_MAX_MEMORY_SIZE = 0

# Make this unique, and don't share it with anybody.
SECRET_KEY = os.environ["SECRET_KEY"]

INTERNAL_IPS = ("127.0.0.1",)

MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # 'django.middleware.csrf.CsrfViewMiddleware',
    # 'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = "mum.urls"

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = "mum.wsgi.app"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": DEBUG,
            # Generally, string_if_invalid should only be enabled in order to debug
            # a specific template problem, then cleared once debugging is complete.
            "string_if_invalid": "[MISSING VARIABLE %s]",
            # 'loaders': [
            #     'django.template.loaders.filesystem.Loader',
            #     'django.template.loaders.app_directories.Loader',
            # ],
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "mum.processors.sitevars",
            ],
        },
    },
]

INSTALLED_APPS = (
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    # 'django.contrib.messages',
    "django.contrib.staticfiles",
    "web_pipeline",
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

SESSION_SERIALIZER = "django.contrib.sessions.serializers.JSONSerializer"

# Email configuration
EMAIL_USE_TLS = bool(os.getenv("EMAIL_USE_TLS"))
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "0"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

# Custom logging
LOGGING_CONFIG = None

# REST API
REST_API_URL = os.environ["REST_API_URL"]
REST_API_TOKEN = os.environ["REST_API_TOKEN"]
