"""Permite `python -m dane_data app` (equivale al comando `dane-data`)."""

import sys

from .cli import main

sys.exit(main())
