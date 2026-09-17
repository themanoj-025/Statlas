"""Ingest entrypoint — thin shim restoring the pre-split public surface.

Restores `ingest_pkg.main` (lost in the ingest_real_data.py split). The
entrypoint `scripts/ingest_real_data.py` and `ingest_pkg/__init__.py` both
import from here.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap: make `app.*` importable when run as `python scripts/ingest_real_data.py`
# (sys.path[0] is scripts/ in that case; app lives at the repo root).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingest_pkg.ingestors import main

__all__ = ["main"]
