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
    """Player valuation and market value history."""

    def fetch_valuations(
        self, player_ids: list[int], as_of: datetime,
        player_names: list[str] | None = None,
    ) -> list[MarketValuationRecord] -> None:
        """Fetch current market valuations for specified players.

        Strategy:
        1. CEAPI JSON endpoint (``/ceapi/marketValueDevelopment/graph/{id}``)
           — no slug needed, returns full history with latest value.
        2. Profile page fallback — requires name slug for correct URL.
        """
        records: list[MarketValuationRecord] = []
        names: list[str | None] = player_names or [None] * len(player_ids)

        for pid, name in zip(player_ids, names):
            try:
                # Strategy 1: CEAPI JSON endpoint (no slug needed)
                mv_data = self.fetch_market_value_history(pid)
                if mv_data:
                    latest = mv_data[-1]
                    records.append(
                        MarketValuationRecord(
                            player_id=pid,
                            source="transfermarkt",
                            valuation_amount_eur=latest["value"],
                            valuation_date=latest.get("date", as_of),
                            low_range=latest["value"] * 0.85,
                            high_range=latest["value"] * 1.15,
                            confidence_level="medium",
                            raw={
                                "tm_player_id": pid,
                                "history_count": len(mv_data),
                                "club": latest.get("club", ""),
                            },
                        )
                    )
                    continue

                # Strategy 2: Profile page fallback (needs name slug)
                slug = self._name_to_slug(name) if name else None
                if slug:
                    profile_url = (
                        f"{TRANSFERMARKT_BASE}/{slug}/profil/spieler/{pid}"
                    )
                    profile_soup = self._soup(profile_url)
                    profile = self._parse_player_profile(profile_soup)
                    mv = profile.get("market_value_eur")
                    if mv is not None:
                        records.append(
                            MarketValuationRecord(
                                player_id=pid,
                                source="transfermarkt",
                                valuation_amount_eur=mv,
                                valuation_date=as_of,
                                low_range=mv * 0.85,
                                high_range=mv * 1.15,
                                confidence_level="low",
                                raw={"tm_player_id": pid, "source": "profile_fallback"},
                            )
                        )
                else:
                    logger.debug(
                        "No name for player %s, cannot build profile URL", pid
                    )
            except (requests.RequestException, ValueError, KeyError, OSError) as exc:
                logger.warning("Failed to fetch valuation for player %s: %s", pid, exc)

        return records

    # -- Slug helpers ---------------------------------------------------------

    @staticmethod
    def _name_to_slug(name: str) -> str:
        """Convert a player full name to a Transfermarkt URL slug.

        Examples:
            'Kylian Mbappe'   -> 'kylian-mbappe'
            'Erling Haaland'  -> 'erling-haaland'
            'Lionel Messi'    -> 'lionel-messi'
        """
        import unicodedata

        # Normalize unicode (e.g. accents)
        nfkd = unicodedata.normalize("NFKD", name)
        ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
        slug = ascii_name.lower().strip()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)  # keep only safe chars
        slug = re.sub(r"\s+", "-", slug)  # spaces -> hyphens
        slug = re.sub(r"-+", "-", slug)  # collapse multiple hyphens
        return slug.strip("-")

    def _resolve_slug(self, player_id: int) -> str | None:
        """Resolve a Transfermarkt player slug by searching for the ID.

        Uses the quick-search page to find the profile URL for a given
        Transfermarkt player ID.  Returns None if the player cannot be found.
        """
        try:
            search_url = (
                f"{TRANSFERMARKT_BASE}/schnellsuche/ergebnis/schnellsuche"
                f"?query={player_id}"
            )
            html = self._fetch(search_url)
            soup = BeautifulSoup(html, "html.parser")
            # Find the link containing /profil/spieler/{id}
            target = f"/profil/spieler/{player_id}"
            for a in soup.select("a[href*='/profil/spieler/']"):
                href = a.get("href", "")
                if target in href:
                    # href like /kylian-mbappe/profil/spieler/342229
                    parts = href.strip("/").split("/")
                    if len(parts) >= 2:
                        return parts[0]  # the slug
        except (requests.RequestException, ValueError, KeyError, OSError) as exc:
            logger.debug("Slug resolution failed for %s: %s", player_id, exc)
        return None

    def fetch_market_value_history(
        self, player_id: int
    ) -> list[dict[str, Any]] -> None:
        """Fetch market value history via Transfermarkt's CEAPI JSON endpoint.

        The ``/ceapi/marketValueDevelopment/graph/{id}`` endpoint returns
        structured JSON without requiring any HTML scraping or browser JS.

        Response format::
            {
              "list": [
                {"x": 1449010800000, "y": 50000, "mw": "\u20ac50k",
                 "datum_mw": "02/12/2015", "verein": "AS Monaco U19", ...},
                ...
              ],
              "current": {"y": 200000000},
              "highest": {"y": 200000000},
              "highest_date": "17/12/2018",
              "last_change": {...}
            }
        """
        ceapi_url = (
            f"{TRANSFERMARKT_BASE}/ceapi/marketValueDevelopment/graph/{player_id}"
        )
        try:
            html = self._fetch(ceapi_url)
            # _fetch returns a string; parse it as JSON
            import json as _json
            data = _json.loads(html)
        except (requests.RequestException, ValueError, KeyError, OSError) as exc:
            logger.debug("CEAPI fetch failed for player %s: %s", player_id, exc)
            return []

        result: list[dict[str, Any]] = []
        for entry in data.get("list", []):
            try:
                ts_ms = entry["x"]
                value = float(entry["y"])
                dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                if value > 0:
                    result.append({
                        "date": dt,
                        "value": value,
                        "club": entry.get("verein", ""),
                        "age": entry.get("age", ""),
                        "display_value": entry.get("mw", ""),
                    })
            except (KeyError, ValueError, OSError):
                continue

        result.sort(key=lambda x: x["date"])
        return result

    # Keep the old HTML-based extractor as a fallback for testing with fixtures
    def _extract_market_value_history(
        self, soup: BeautifulSoup, player_id: int
    ) -> list[dict[str, Any]]:
        """Fallback: extract market value history from embedded Highcharts data.

        Used when the CEAPI endpoint is unavailable or for test fixtures.
        """
        result: list[dict[str, Any]] = []
        for script in soup.find_all("script"):
            text = script.string or ""
            if not text.strip():
                continue
            if "Highcharts" in text or "series" in text or "data" in text:
                pairs = re.findall(r"\[(\d+),\s*(\d+)\]", text)
                for ts, val in pairs:
                    try:
                        dt = datetime.fromtimestamp(
                            int(ts) / 1000, tz=timezone.utc
                        )
                        value = float(val)
                        if value > 0:
                            result.append({"date": dt, "value": value})
                    except (ValueError, OSError):
                        continue
        result.sort(key=lambda x: x["date"])
        return result
