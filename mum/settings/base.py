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
    )

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
# ALLOWED_HOSTS = [SITE_URL, '142.150.84.65', 'elaspic.kimlab.org', 'elaspic.witvliet.ca']
SITE_URL = "http://elaspic.kimlab.org"  # required only for 'sendEmail'
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
if DEBUG:
    MEDIA_ROOT = op.join(PROJECT_ROOT, "media")
else:
    MEDIA_ROOT = "/var/www/elaspic.kimlab.org/media/"

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: 'http://example.com/media/', 'http://media.example.com/'
MEDIA_URL = "/media/"

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' 'static/' subdirectories and in STATICFILES_DIRS.
# Example: '/var/www/example.com/static/'
if DEBUG:
    STATIC_ROOT = op.join(PROJECT_ROOT, "static")
else:
    STATIC_ROOT = "/var/www/elaspic.kimlab.org/static/"

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
WSGI_APPLICATION = "mum.wsgi.application"

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

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
        "timely": {
            "format": "%(asctime)s %(message)s",
        },
        "clean": {
            "format": "[%(levelname)s] %(module)s: %(message)s",
        },
    },
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "info_log": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": op.join(PROJECT_ROOT, "log", "django.log"),
            "maxBytes": 32 * 1024 * 1024,  # 32 MB
            "backupCount": 3,
        },
        "debug_log": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": op.join(PROJECT_ROOT, "log", "django.err"),
            "maxBytes": 32 * 1024 * 1024,  # 32 MB
            "backupCount": 3,
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "clean",
        },
    },
    "loggers": {
        "": {
            "handlers": ["info_log", "debug_log"] + (["console"] if DEBUG else []),
            "level": "DEBUG",
            "propagate": False,
        },
        "web_pipeline": {
            "level": "DEBUG",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}

FILE_UPLOAD_MAX_MEMORY_SIZE = 0

# Email configuration
EMAIL_USE_TLS = bool(os.getenv("EMAIL_USE_TLS"))
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "0"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
