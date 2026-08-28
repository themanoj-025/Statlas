"""
transfermarkt_pkg — Backward-compatible re-exporter.

All implementation lives in focused sub-modules.
This file re-exports ``TransfermarktSource`` so existing
``from app.sources.transfermarkt_pkg import TransfermarktSource``
continues to work unchanged.
"""

from app.sources.transfermarkt_pkg.source import TransfermarktSource

__all__ = ["TransfermarktSource"]
