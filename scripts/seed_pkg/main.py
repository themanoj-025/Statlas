"""Seed entrypoint — thin shim restoring the pre-split public surface.

Restores `seed_pkg.main` (lost in the seed_dev_db.py split). The entrypoint
`scripts/seed_dev_db.py` and `seed_pkg/__init__.py` both import from here.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap: make `app.*` importable when run as `python scripts/seed_dev_db.py`
# (sys.path[0] is scripts/ in that case; app lives at the repo root).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from seed_pkg.seeding import main

__all__ = ["main"]
