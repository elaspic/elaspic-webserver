#!/usr/bin/env python
import sys

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
