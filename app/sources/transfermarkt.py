"""Transfermarkt source -- re-exports for backward compatibility.

All logic has been moved to app.sources.transfermarkt_pkg.
"""

from __future__ import annotations

from app.sources.transfermarkt_pkg import (
    LEAGUE_URL_SLUGS,
    TRANSFERMARKT_BASE,
    TransfermarktSchemaChangedError,
    TransfermarktSource,
    _parse_date,
    _parse_market_value,
    _parse_transfer_fee,
)

__all__ = [
    "LEAGUE_URL_SLUGS",
    "TRANSFERMARKT_BASE",
    "TransfermarktSchemaChangedError",
    "TransfermarktSource",
    "_parse_date",
    "_parse_market_value",
    "_parse_transfer_fee",
]
