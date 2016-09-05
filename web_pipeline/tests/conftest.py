import sys
import os.path as op

PACKAGE_DIR = op.dirname(op.dirname(op.abspath(__file__)))

if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)
