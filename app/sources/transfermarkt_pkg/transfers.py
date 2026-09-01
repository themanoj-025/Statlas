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
    """Transfer and contract data fetching."""

    def fetch_transfers(self, since: datetime) -> list[TransferRecord]:
        """Fetch transfer records for all leagues since a given date.

        Scrapes the league transfers page which lists all transfers for a
        season.
        """
        records: list[TransferRecord] = []

        for slug in self.tiers["leagues"]:
            try:
                url = self._league_transfers_url(slug, f"{since.year}-{str(since.year + 1)[-2:]}")
                soup = self._soup(url)
                league_records = self._parse_league_transfers(soup, slug, since)
                records.extend(league_records)
                logger.info(
                    "Transfermarkt: %s transfers from %s", len(league_records), slug
                )
            except (requests.RequestException, ValueError, KeyError, OSError) as exc:
                logger.warning("Failed to fetch transfers for %s: %s", slug, exc)

        return records

    def _parse_league_transfers(
        self, soup: BeautifulSoup, league_slug: str, since: datetime
    ) -> list[TransferRecord]:
        """Parse the league all-transfers page into TransferRecords."""
        records: list[TransferRecord] = []

        # Transfermarkt groups transfers by type: arrivals, departures, loans
        transfer_sections = soup.select(
            "div.box table.items tbody"
        )

        for section in transfer_sections:
            rows = section.select("tr")
            for row in rows:
                try:
                    record = self._parse_transfer_row(row, league_slug)
                    if record and record.transfer_date >= since:
                        records.append(record)
                except (requests.RequestException, ValueError, KeyError, OSError) as exc:
                    logger.debug("Failed to parse transfer row: %s", exc)

        return records

    def _parse_transfer_row(
        self, row: BeautifulSoup, league_slug: str
    ) -> TransferRecord | None:
        """Parse a single transfer row from the transfers page."""
        cells = row.select("td")
        if len(cells) < 4:
            return None

        # Player name and link
        player_link = row.select_one("aspielprofil_tooltip, td.hauptlink a")
        if not player_link:
            return None
        player_name = player_link.get_text(strip=True)
        player_href = player_link.get("href", "")
        tm_id_match = re.search(r"/(\d+)$", player_href)
        tm_player_id = int(tm_id_match.group(1)) if tm_id_match else None

        # Date
        date_cell = row.select_one("td.zentriert")
        transfer_date = _parse_date(date_cell.get_text(strip=True)) if date_cell else None

        # Fee
        fee_cell = cells[-1] if cells else None
        fee_text = fee_cell.get_text(strip=True) if fee_cell else ""
        fee_eur = _parse_transfer_fee(fee_text)

        # Transfer type from fee text
        fee_lower = fee_text.lower()
        if "loan" in fee_lower or "leihgeschäft" in fee_lower:
            transfer_type = "loan"
        elif "free" in fee_lower or "ablösefrei" in fee_lower:
            transfer_type = "free"
        elif fee_eur is not None and fee_eur > 0:
            transfer_type = "transfer"
        else:
            transfer_type = "unknown"

        if transfer_date is None:
            return None

        return TransferRecord(
            player_id=0,  # resolved by ingestion layer via name matching
            from_team_id=None,
            to_team_id=0,  # resolved by ingestion layer
            transfer_date=transfer_date,
            reported_fee_eur=fee_eur,
            transfer_type=transfer_type,
            status="reported",
            source="transfermarkt",
            raw={
                "player_name": player_name,
                "tm_player_id": tm_player_id,
                "fee_text": fee_text,
                "league_slug": league_slug,
            },
        )

    def fetch_contracts(
        self, player_ids: list[int], as_of: datetime,
        player_names: list[str] | None = None,
    ) -> list[ContractRecord]:
        """Fetch contract status for specified players.

        Scrapes individual player profile pages for contract end dates
        and estimated salary.
        """
        records: list[ContractRecord] = []
        names: list[str | None] = player_names or [None] * len(player_ids)

        for pid, name in zip(player_ids, names):
            try:
                slug = self._name_to_slug(name) if name else None
                if slug:
                    url = f"{TRANSFERMARKT_BASE}/{slug}/profil/spieler/{pid}"
                else:
                    # No name available — try slug resolution via search
                    slug = self._resolve_slug(pid)
                    if slug:
                        url = f"{TRANSFERMARKT_BASE}/{slug}/profil/spieler/{pid}"
                    else:
                        logger.debug("No slug for player %s, skipping contract fetch", pid)
                        continue
                soup = self._soup(url)
                contract = self._parse_contract_from_profile(soup, pid, as_of)
                if contract:
                    records.append(contract)
            except (requests.RequestException, ValueError, KeyError, OSError) as exc:
                logger.warning("Failed to fetch contract for player %s: %s", pid, exc)

        return records

    def _parse_contract_from_profile(
        self, soup: BeautifulSoup, player_id: int, as_of: datetime
    ) -> ContractRecord | None:
        """Extract contract info from a player profile page."""
        data = self._parse_player_profile(soup)

        # Look for contract expiry in the info table
        contract_end_text = data.get("contract expires") or data.get(
            "contract expiring"
        )
        contract_end = None
        if contract_end_text:
            contract_end = _parse_date(contract_end_text)

        # Look for salary/weekly wages
        salary_text = data.get("salary") or data.get("weekly wage")
        salary_eur = None
        if salary_text:
            salary_eur = _parse_market_value(salary_text)
            # Convert weekly to annual if it looks like a weekly wage
            if salary_eur and salary_eur < 500_000:
                salary_eur *= 52

        # Determine contract status
        if contract_end is None:
            status = "unknown"
        elif contract_end < as_of:
            status = "expired"
        elif (contract_end - as_of).days < 365:
            status = "expiring_next_season"
        else:
            status = "active"

        return ContractRecord(
            player_id=player_id,
            current_team_id=None,  # resolved by ingestion layer
            contract_end_date=contract_end,
            contract_value_per_year_eur=salary_eur,
            contract_status=status,
            source="transfermarkt",
            snapshot_date=as_of,
            raw=data,
        )

    def get_rate_limit_seconds(self) -> float:
        return self.limiter.interval
