"""
TransfermarktSource — market data provider implementation.

.. note::

   The implementation has been refactored into ``fetching.py``,
   ``squad.py``, ``market_data.py``, and ``transfers.py``
   for maintainability.  This module re-exports
   ``TransfermarktSource`` so existing imports continue to
   work unchanged.
"""

from app.sources.transfermarkt_pkg.fetching import (
    _fetch,
    _league_squad_url,
    _league_transfers_url,
    _soup,
)
from app.sources.transfermarkt_pkg.market_data import (
    _extract_market_value_history,
    _name_to_slug,
    _resolve_slug,
    fetch_market_value_history,
    fetch_valuations,
)
from app.sources.transfermarkt_pkg.squad import (
    _extract_clubs_from_overview,
    _parse_player_profile,
    _parse_squad_page,
    fetch_squad_players,
)
from app.sources.transfermarkt_pkg.transfers import (
    _parse_contract_from_profile,
    _parse_league_transfers,
    _parse_transfer_row,
    fetch_contracts,
    fetch_transfers,
    get_rate_limit_seconds,
)

__all__ = [
    "TransfermarktSource",
]
