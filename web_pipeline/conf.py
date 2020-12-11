import os
import os.path as op

# ELASPIC
ELASPIC_VERSION = "v0.1.14"

# ELASPIC REST API
JOB_EXPIRY_DAY = 90
DB_PATH = os.getenv("DATA_DIR", "/home/kimlab1/database_data/elaspic/")
SAVE_PATH = op.join(DB_PATH, "webserver", "jobs")
