import os
import os.path as op
import sys
import django


DATA_DIR = '/home/kimlab1/database_data/elaspic_v2'
DB_SCHEMA = 'elaspic_webserver'
SCRIPTS_DIR = op.join(DATA_DIR, 'scripts')

BASE_DIR = op.abspath(op.dirname(__file__))
PROJECT_DIR = op.abspath(op.join(BASE_DIR, '..'))
sys.path.insert(0, PROJECT_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mum.settings.production")
django.setup()


# %% Logger
LOGGING_CONFIGS = {
    'version': 1,
    'disable_existing_loggers': False,  # this fixes the problem

    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        },
        'timely': {
            'format': '%(asctime)s %(message)s',
        },
        'clean': {
            'format': '[%(levelname)s] %(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'clean',
        },
        'info_log': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'timely',
            'filename': op.abspath(op.join(BASE_DIR, '..', 'log', 'jobsubmitter.log')),
            'maxBytes': 32 * 1024 * 1024,  # 32 MB
            'backupCount': 3,
        },
        'debug_log': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'timely',
            'filename': op.abspath(op.join(BASE_DIR, '..', 'log', 'jobsubmitter.err')),
            'maxBytes': 32 * 1024 * 1024,  # 32 MB
            'backupCount': 3,
        },
    },
    'loggers': {
        '': {
            'handlers': ['info_log', 'debug_log'],
            'level': 'DEBUG',
            'propagate': True
        }
    }
}
