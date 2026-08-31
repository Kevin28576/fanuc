"""Lets the package run as ``python -m fanuc``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
