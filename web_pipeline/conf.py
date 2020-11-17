import os.path as op

# Duplicate from proj.settings
BASE_DIR = op.dirname(op.abspath(__file__))
PROJECT_ROOT = op.dirname(BASE_DIR)

# Redis
REDIS_SOCKET_FILE = "/tmp/redis.sock"

# ELASPIC
ELASPIC_NAME = "ELASPIC"
ELASPIC_HOME = "https://gitlab.com/kimlab/elaspic"
ELASPIC_VERSION = "v0.1.14"
ELASPIC_RELEASE_URL = "https://gitlab.com/kimlab/elaspic/tags/{}".format(
    ELASPIC_VERSION
)
ELASPIC_DOCS = "https://kimlab.gitlab.io/elaspic/{}/".format(ELASPIC_VERSION)

# Jobsubmitter
JOBSUBMITTER_SECRET_KEY = "J6;u.950z5750Q#344vy7*idT1FBs0"
JOB_EXPIRY_DAY = 90
TASK_SOFT_TIME_LIMIT = 24 * 60 * 60

# Other configurations.
DATABASE_PATH = op.join("/home/kimlab1/database_data/")
DB_PATH = op.join(DATABASE_PATH, "elaspic/")
SAVE_PATH = op.join(DB_PATH, "webserver", "jobs")
