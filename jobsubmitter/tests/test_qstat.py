import os
import os.path as op
import sys
import asyncio
import logging
import logging.config

try:
    BASE_DIR = op.abspath(op.dirname(__file__))
except NameError:
    BASE_DIR = os.getcwd()

PROJECT_DIR = op.abspath(op.join(BASE_DIR, '..'))

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)


# %% Logger
LOGGING_CONFIGS = {
    'version': 1,
    'disable_existing_loggers': False,  # this fixes the problem

    'formatters': {
        'clean': {
            'format': '%(message)s',
        },
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'clean',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': True
        }
    }
}
logging.config.dictConfig(LOGGING_CONFIGS)
logger = logging.getLogger(__name__)


# %%
from elaspic_rest_api import jobsubmitter

jobsubmitter.running_jobs |= {1, 2, 3, 4, 5}

loop = asyncio.get_event_loop()
loop.run_until_complete(jobsubmitter.qstat())
loop.close()

# Make sure that the old values got overwritten
assert not (jobsubmitter.running_jobs & {1, 2, 3, 4, 5})
