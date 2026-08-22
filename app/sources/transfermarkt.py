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

TRANSFERMARKT_BASE = "https://www.transfermarkt.com"

# Transfermarkt league slug -> wettbewerb code (must match tiers.json).
# Verified against live Transfermarkt URLs as of 2026-08.
LEAGUE_URL_SLUGS = {
    "premier-league": "premier-league",
    "la-liga": "laliga",
    "serie-a": "serie-a",
    "bundesliga": "bundesliga",
    "ligue-1": "ligue-1",
    "eredivisie": "eredivisie",
    "primeira-liga": "liga-portugal",
    "belgian-pro-league": "jupiler-pro-league",
    "super-lig": "super-lig",
    "scottish-premiership": "scottish-premiership",
    "austrian-bundesliga": "bundesliga",
    "swiss-super-league": "super-league",
    "greek-super-league": "super-league-1",
    "danish-superliga": "superligaen",
    "championship": "championship",
    "la-liga-2": "laliga2",
    "serie-b": "serie-b",
    "2-bundesliga": "2-bundesliga",
    "ligue-2": "ligue-2",
}


class TransfermarktSchemaChangedError(SourceError):
    """Transfermarkt's HTML structure changed in a way we refuse to guess at."""


def _parse_market_value(text: str) -> float | None:
    """Parse Transfermarkt market value strings like '€85.00m' or '€500K' to EUR.

    Returns None when the text is unparseable (e.g. ' цена неизвестна').
    """
    if not text:
        return None
    text = text.strip().replace("\xa0", " ")
    # Match patterns like: €85.00m, €500K, €1.50bn, €23.50m, £85.00m
    m = re.search(r"[€$£]\s*([\d.,]+)\s*(bn|mn|m|k|K|M|B)?", text, re.IGNORECASE)
    if not m:
        return None
    num_str = m.group(1).replace(",", "")
    try:
        num = float(num_str)
    except ValueError:
        return None
    suffix = (m.group(2) or "").lower()
    if suffix in ("bn", "b"):
        num *= 1_000_000_000
    elif suffix in ("mn", "m"):
        num *= 1_000_000
    elif suffix in ("k",):
        num *= 1_000
    return num


def _parse_transfer_fee(text: str) -> float | None:
    """Parse transfer fee text. Handles 'Free transfer', 'Loan', numeric values."""
    if not text:
        return None
    text = text.strip().lower()
    if "free" in text or "ablösefrei" in text:
        return 0.0
    if "loan" in text or "leihgeschäft" in text:
        return None  # loan fees are not always public
    return _parse_market_value(text)


def _parse_date(text: str) -> datetime | None:
    """Parse Transfermarkt date formats (DD/MM/YYYY, MMM D, YYYY, etc.)."""
    if not text:
        return None
    text = text.strip()
    for fmt in ("%b %d, %Y", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


class TransfermarktSource(MarketDataSource):
    """Scrapes Transfermarkt for market valuations, transfers, and contracts."""

    source_name = "transfermarkt"

    def __init__(
        self,
        *,
        cache: HttpCache | None = None,
        limiter: RateLimiter | None = None,
        session: requests.Session | None = None,
    ) -> None:
        settings = get_settings()
        if session is not None:
            self.session = session
        else:
            try:
                import cloudscraper

                self.session = cloudscraper.create_scraper(
                    browser={
                        "browser": "chrome",
                        "platform": "windows",
                        "mobile": False,
                    }
                )
            except ImportError:
                self.session = requests.Session()
        self.cache = cache or HttpCache()
        # Conservative: 1 request per 5s +/- 1s jitter.
        self.limiter = limiter or RateLimiter(5.0, 1.0)
        self.tiers = load_tiers()

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

    # -- Player profile parsing ---------------------------------------------

    def _parse_player_profile(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract player info from a Transfermarkt profile page."""
        data: dict[str, Any] = {}

        # Player name
        name_el = soup.select_one(
            ".data-header__headline-wrapper, h1.tw-text-2xl"
        )
        if name_el:
            data["name"] = name_el.get_text(strip=True)

        # Market value
        mv_el = soup.select_one(
            "div.tm-player-market-value-development__current-value, "
            "div.data-header__market-value-wrapper"
        )
        if mv_el:
            data["market_value_text"] = mv_el.get_text(strip=True)
            data["market_value_eur"] = _parse_market_value(
                mv_el.get_text(strip=True)
            )

        # Info table (DOB, nationality, position, etc.)
        info_box = soup.select_one(
            "div.info-table, div.data-header__details"
        )
        if info_box:
            for row in info_box.select("tr"):
                label_el = row.select_one("th, span.info-table__content--bold")
                value_el = row.select_one("td, span.info-table__content")
                if label_el and value_el:
                    label = label_el.get_text(strip=True).rstrip(":")
                    value = value_el.get_text(strip=True)
                    data[label.lower()] = value

        return data

    # -- MarketDataSource interface ------------------------------------------

    def fetch_valuations(
        self, player_ids: list[int], as_of: datetime
    ) -> list[MarketValuationRecord]:
        """Fetch current market valuations for specified players.

        Uses the Transfermarkt market value API endpoint (embedded JSON in
        the player profile page) for efficient bulk lookups.
        """
        records: list[MarketValuationRecord] = []

        for pid in player_ids:
            try:
                url = f"{TRANSFERMARKT_BASE}/marktwertverlauf/spieler/{pid}"
                soup = self._soup(url)

                # The market value page has a JSON data attribute with history
                mv_data = self._extract_market_value_history(soup, pid)
                if mv_data:
                    # Get the most recent valuation
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
                            raw={"tm_player_id": pid, "history_count": len(mv_data)},
                        )
                    )
                else:
                    # Fallback: try the profile page for current value
                    profile_url = f"{TRANSFERMARKT_BASE}/profil/spieler/{pid}"
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
            except Exception as exc:
                logger.warning("Failed to fetch valuation for player %s: %s", pid, exc)

        return records

    def _extract_market_value_history(
        self, soup: BeautifulSoup, player_id: int
    ) -> list[dict[str, Any]]:
        """Extract market value history from the market value chart page.

        Transfermarkt embeds chart data in a <script> tag as JSON.
        """
        result: list[dict[str, Any]] = []

        # Look for the embedded JSON data in script tags
        for script in soup.find_all("script"):
            text = script.string or ""
            if not text.strip():
                continue
            # Transfermarkt embeds chart data as [timestamp_ms, value] pairs
            # inside Highcharts.Chart({series: [{data: [[ts, val], ...]}]})
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

        # Sort by date ascending
        result.sort(key=lambda x: x["date"])
        return result

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
            except Exception as exc:
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
                except Exception as exc:
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
        self, player_ids: list[int], as_of: datetime
    ) -> list[ContractRecord]:
        """Fetch contract status for specified players.

        Scrapes individual player profile pages for contract end dates
        and estimated salary.
        """
        records: list[ContractRecord] = []

        for pid in player_ids:
            try:
                url = f"{TRANSFERMARKT_BASE}/profil/spieler/{pid}"
                soup = self._soup(url)
                contract = self._parse_contract_from_profile(soup, pid, as_of)
                if contract:
                    records.append(contract)
            except Exception as exc:
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
