"""Transfermarkt source -- market valuations, transfer history, and contract data.

Scrapes Transfermarkt.com for player market values, transfer fees, and contract
information. Implements the MarketDataSource interface so it plugs directly into
the weekly_refresh market data ingestion (Phase 15).

Compliance posture:
- Self-imposed rate limit: 1 request per 5 seconds (+/- 1s jitter).
  Transfermarkt aggressively blocks scrapers; we are conservative.
- User-Agent: StatlasAnalytics/0.1 (descriptive, never browser-spoofing).
- Aggressive local caching (7-day TTL) to minimize repeat requests.
- Exponential backoff on 429/403/503; hard abort after 6 retries.
- Data is used for non-commercial analytics only (personal project).

Transfermarkt URL structure:
- League squad: /premier-league/startseite/wettbewerb/GB1
- Player profile: /erling-haaland/profil/spieler/418560
- Transfer history: /erling-haaland/transfers/spieler/418560
- Market value history: /erling-haaland/marktwertverlauf/spieler/418560

NOTE: Transfermarkt's HTML structure changes periodically. The parser uses
multiple fallback selectors and raises SchemaChangedError loudly when the
structure changes beyond recovery (Constitution: fail loudly, never guess).
"""

from __future__ import annotations

import contextlib
import logging
import re
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

from app.config import get_settings, load_tiers
from app.sources.base import (
    HttpCache,
    RateLimiter,
    SourceError,
    fetch_with_retry,
)
from app.sources.market_data import (
    ContractRecord,
    MarketDataSource,
    MarketValuationRecord,
    TransferRecord,
)

logger = logging.getLogger(__name__)

from app.sources.transfermarkt_pkg.constants import LEAGUE_URL_SLUGS, TRANSFERMARKT_BASE


from app.sources.transfermarkt_pkg.parsers import (
    TransfermarktSchemaChangedError,
    _parse_date,
    _parse_market_value,
    _parse_transfer_fee,
)


class TransfermarktSource(MarketDataSource):


"""
fetching.py — HTTP fetching and URL construction helpers.
"""

    def _fetch(self, url: str) -> str:
        """Fetch a Transfermarkt page with rate limiting and caching."""
        return fetch_with_retry(
            url,
            limiter=self.limiter,
            cache=self.cache,
            headers={
                "User-Agent": get_settings().user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            session=self.session,
        )

    def _soup(self, url: str) -> BeautifulSoup:
        """Fetch and parse a Transfermarkt page."""
        html = self._fetch(url)
        return BeautifulSoup(html, "html.parser")

    # -- League squad URLs ---------------------------------------------------

    def _league_squad_url(self, league_slug: str) -> str:
        tm_slug = LEAGUE_URL_SLUGS.get(league_slug)
        if tm_slug is None:
            raise SourceError(
                f"No Transfermarkt URL mapping for league '{league_slug}'"
            )
        tm_code = self.tiers["leagues"][league_slug]["external_ids"].get(
            "transfermarkt"
        )
        if tm_code is None:
            raise SourceError(
                f"No Transfermarkt code in tiers.json for '{league_slug}'"
            )
        return f"{TRANSFERMARKT_BASE}/{tm_slug}/startseite/wettbewerb/{tm_code}"

    def _league_transfers_url(self, league_slug: str, season: str) -> str:
        tm_slug = LEAGUE_URL_SLUGS.get(league_slug)
        tm_code = self.tiers["leagues"][league_slug]["external_ids"].get(
            "transfermarkt"
        )
        if tm_slug is None or tm_code is None:
            raise SourceError(f"Missing Transfermarkt config for '{league_slug}'")
        # Season format: "2025-26" -> "2025" for Transfermarkt
        year = season.split("-")[0]
        return (
            f"{TRANSFERMARKT_BASE}/{tm_slug}/alletransfers/wettbewerb/{tm_code}"
            f"?saison_id={year}"
        )

    # -- Bulk squad ingestion ------------------------------------------------

    def fetch_squad_players(
