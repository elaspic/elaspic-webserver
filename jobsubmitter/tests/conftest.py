import os
import os.path as op
import sys

import django
import pytest

TESTS_DIR = op.dirname(op.abspath(__file__))
BASE_DIR = op.dirname(TESTS_DIR)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
