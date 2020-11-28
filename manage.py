#!/usr/bin/env python
import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.getenv("ENV_FILE", ".env.prod"))

import sys

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
