# Django settings for mum project.
# python D:\Dropbox\django\mum\manage.py shell

import os
import socket
#from multiprocessing import cpu_count

from celery.schedules import crontab

import djcelery
djcelery.setup_loader()

# Site settings.
SITE_NAME = 'ELASPIC'

# Time limits.
JOB_EXPIRY_DAY = 90
CELERYD_TASK_SOFT_TIME_LIMIT = 7200    # 7200 = 2 hours

# Crash logs are emailed to admins and deleted every day. Check spam folder.
# If disabled, logs will be saved for 90 days.
SEND_CRASH_LOGS_TO_ADMINS = True
SEND_BROKEN_LINK_EMAILS = True
ADMINS = (
    ('Daniel Witvliet', 'daniel.witvliet@kimlab.org'),
    ('Alexey Strokach', 'alex.strokach@utoronto.ca'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',   # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'elaspic_webserver',            # Or path to database file if using sqlite3.
        'USER': 'elaspic-web',
        'PASSWORD': 'elaspic',
        'HOST': '192.168.6.19', 	               # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                             # Set to empty string for default.
    },
    'data': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'elaspic', 
        'USER': 'elaspic-web',
        'PASSWORD': 'elaspic',
        'HOST': '192.168.6.19', 
        'PORT': '',
    },
    'uniprot': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'uniprot_kb', 
        'USER': 'elaspic-web',
        'PASSWORD': 'elaspic',
        'HOST': '192.168.6.19', 
        'PORT': '',
    },

}

COMPUTERNAME = socket.gethostname()
if COMPUTERNAME == 'desk02':
    DEBUG = TEMPLATE_DEBUG = True
    MOUNT_PATH = '/home/'
    HOME_PATH = '/home/witvliet'
    SITE_URL = '127.0.0.1:8000'
else:
    DEBUG = TEMPLATE_DEBUG = False
    MOUNT_PATH = '/mnt/'
    HOME_PATH = '/home/kimadmin'
    SITE_URL = '192.168.6.53'

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [SITE_URL, '142.150.84.65', 'elaspic.kimlab.org', 'elaspic.com']
#ALLOWED_HOSTS = '*'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Toronto'
CELERY_TIMEZONE = 'US/Eastern'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

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
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: 'http://example.com/media/', 'http://media.example.com/'
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' 'static/' subdirectories and in STATICFILES_DIRS.
# Example: '/var/www/example.com/static/'
STATIC_ROOT = ''

# URL prefix for static files.
# Example: 'http://example.com/static/', 'http://static.example.com/'
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like '/home/html/static' or 'C:/www/django/static'.
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(os.path.dirname(__file__), 'static').replace('\\','/'), 
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '@klblcjv9(4$ktuoey14_mz^%))u9hw&j*tv_pavj0ye8xxy*e'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

INTERNAL_IPS = (
    '127.0.0.1',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)


ROOT_URLCONF = 'mum.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'mum.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like '/home/html/django_templates' or 'C:/www/django/templates'.
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(os.path.dirname(__file__), 'templates').replace('\\','/'), 
)

INSTALLED_APPS = (
    #'django.contrib.auth',
    #'django.contrib.contenttypes',
    'django.contrib.sessions',
    #'django.contrib.sites',
    #'django.contrib.messages',
    'django.contrib.staticfiles',
    'web_pipeline',
    'djcelery',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
    },
    
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}


# Context processors.
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'mum.processors.sitevars'
)



# Other configurations.
FILE_UPLOAD_MAX_MEMORY_SIZE = 0
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SAVE_PATH = os.path.join(PROJECT_ROOT, 'mum/static/jobs/')
CRASH_LOG_PATH = os.path.join(PROJECT_ROOT, 'crashlogs/')

# Celery configuration.
CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend'
BROKER_URL = 'amqp://guest:guest@localhost:5672//'
CELERYD_CONCURRENCY = 20 # Set to twice the real amount because of subprocesses.
CELERY_ACCEPT_CONTENT = ['pickle', 'json']
CELERY_HIJACK_ROOT_LOGGER = False
CELERY_ACKS_LATE = True
CELERY_ROUTES = {
    'web_pipeline.tasks.cleanupServer': {'queue': 'scheduled'},
    'web_pipeline.tasks.runPipelineWrapper': {'queue': 'celery'}
}

# Celery cleanup schedule
CELERYBEAT_SCHEDULE = {
    'pipeline_cleanup': {
        'task': 'web_pipeline.tasks.cleanupServer',
        'schedule': crontab(minute=0, hour=2)
    },
}

# Celery time limits
CELERYD_TASK_TIME_LIMIT = CELERYD_TASK_SOFT_TIME_LIMIT + 600

# Email configuration.
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'no-reply@kimlab.org'
EMAIL_HOST_PASSWORD = '630kim630'

# Pipeline configuration.
DATABASE_PATH = os.path.join(MOUNT_PATH, 'kimlab1/database_data/')
DB_PATH = os.path.join(DATABASE_PATH, 'elaspic_v2/')
PDB_PATH = os.path.join(DATABASE_PATH, 'pdb/data/data/structures/divided/pdb/')
BLAST_DB_PATH = os.path.join(DATABASE_PATH, 'blast/')
BIN_PATH = os.path.join(PROJECT_ROOT, 'pipeline/bin/')
DB_FILE = os.path.join(DATABASE_PATH, 'db/elaspic.sqlite')
PIPELINE_DEBUG = True