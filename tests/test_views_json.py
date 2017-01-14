# flake8: noqa
import io
import logging
import os.path as op
import tempfile

import pandas as pd
import pytest
# from hypothesis import given
# from hypothesis.strategies import text
from faker import Faker

from web_pipeline import functions

logger = logging.getLogger()
fake = Faker()

print('xx')
