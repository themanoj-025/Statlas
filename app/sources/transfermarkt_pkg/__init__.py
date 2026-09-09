"""
transfermarkt_pkg — Backward-compatible re-exporter.

All implementation lives in focused sub-modules.  This file re-exports the
public surface (source class, constants, parser helpers, schema error) so
existing ``from app.sources.transfermarkt_pkg import X`` and the legacy
``app.sources.transfermarkt`` shim continue to work unchanged.
"""

from app.sources.transfermarkt_pkg.constants import LEAGUE_URL_SLUGS, TRANSFERMARKT_BASE
from app.sources.transfermarkt_pkg.parsers import (
    TransfermarktSchemaChangedError,
    _parse_date,
    _parse_market_value,
    _parse_transfer_fee,
)
from app.sources.transfermarkt_pkg.source import TransfermarktSource

__all__ = [
    "LEAGUE_URL_SLUGS",
    "TRANSFERMARKT_BASE",
    "TransfermarktSchemaChangedError",
    "TransfermarktSource",
    "_parse_date",
    "_parse_market_value",
    "_parse_transfer_fee",
]
