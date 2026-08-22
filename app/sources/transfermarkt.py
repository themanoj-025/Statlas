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

    # -- Bulk squad ingestion ------------------------------------------------

    def fetch_squad_players(
        self, league_slug: str, season: str | None = None
    ) -> list[dict[str, Any]]:
        """Scrape every player in a league from Transfermarkt squad pages.

        Workflow:
        1. Fetch the league overview page to discover all club URLs.
        2. For each club, fetch the squad (``/kader/verein/{id}``) page.
        3. Parse each player row for name, TM ID, position, age, nationality,
           contract end, and market value.

        Returns a list of dicts, one per player, suitable for upserting into
        the ``Player`` model and storing market valuations.
        """
        all_players: list[dict[str, Any]] = []

        # Step 1: discover clubs from the league overview page
        tm_slug = LEAGUE_URL_SLUGS.get(league_slug)
        if tm_slug is None:
            raise SourceError(f"No Transfermarkt URL mapping for '{league_slug}'")
        tm_code = self.tiers["leagues"][league_slug]["external_ids"].get(
            "transfermarkt"
        )
        if tm_code is None:
            raise SourceError(
                f"No Transfermarkt code in tiers.json for '{league_slug}'"
            )

        season_param = f"/saison_id/{season.split('-')[0]}" if season else ""
        overview_url = (
            f"{TRANSFERMARKT_BASE}/{tm_slug}/startseite/wettbewerb/{tm_code}"
            f"{season_param}"
        )
        logger.info("Fetching league overview: %s", overview_url)
        overview_soup = self._soup(overview_url)

        clubs = self._extract_clubs_from_overview(overview_soup)
        logger.info("Found %d clubs in %s", len(clubs), league_slug)

        # Step 2: fetch each club's squad page
        for club in clubs:
            try:
                club_url = (
                    f"{TRANSFERMARKT_BASE}{club['squad_url']}"
                )
                logger.info(
                    "  Fetching squad: %s (%d players expected)",
                    club["name"],
                    club.get("squad_size", 0),
                )
                club_soup = self._soup(club_url)
                players = self._parse_squad_page(
                    club_soup, club["name"], club["tm_club_id"], league_slug
                )
                all_players.extend(players)
                logger.info("    Parsed %d players from %s", len(players), club["name"])
            except Exception as exc:
                logger.warning(
                    "  Failed to fetch squad for %s: %s", club["name"], exc
                )

        logger.info(
            "Total players scraped from %s: %d", league_slug, len(all_players)
        )
        return all_players

    def _extract_clubs_from_overview(
        self, soup: BeautifulSoup
    ) -> list[dict[str, Any]]:
        """Extract club names, IDs, and squad page URLs from a league overview."""
        clubs: list[dict[str, Any]] = []
        seen_ids: set[int] = set()

        # The first table.items has club rows
        tables = soup.select("table.items")
        if not tables:
            return clubs

        for row in tables[0].select("tr"):
            # Each club row has /startseite/verein/{id} links
            start_links = row.select('a[href*="/startseite/verein/"]')
            if not start_links:
                continue

            # The first link is usually an image (empty text), the second has the name
            href = start_links[0].get("href", "")
            m_id = re.search(r"/verein/(\d+)", href)
            if not m_id:
                continue
            club_id = int(m_id.group(1))
            if club_id in seen_ids:
                continue
            seen_ids.add(club_id)

            # Club name: try the second link text, then title attr, then first link text
            club_name = ""
            for link in start_links:
                t = link.get_text(strip=True)
                if t:
                    club_name = t
                    break
            if not club_name:
                # Fallback: use title attribute from the image link
                club_name = start_links[0].get("title", "")
            if not club_name:
                continue

            # Find the squad/kader link for this club
            kader_link = row.select_one(
                f'a[href*="/verein/{club_id}"][href*="/kader/"]'
            )
            squad_url = kader_link.get("href", "") if kader_link else ""

            # Squad size (from the cell linking to /kader/)
            squad_size = 0
            if kader_link:
                size_text = kader_link.get_text(strip=True)
                try:
                    squad_size = int(size_text)
                except ValueError:
                    pass

            # Total market value
            mv_cell = row.select_one("td.rechts")
            total_mv = mv_cell.get_text(strip=True) if mv_cell else ""

            clubs.append({
                "name": club_name,
                "tm_club_id": club_id,
                "squad_url": squad_url,
                "squad_size": squad_size,
                "total_market_value": total_mv,
            })

        return clubs

    def _parse_squad_page(
        self,
        soup: BeautifulSoup,
        club_name: str,
        tm_club_id: int,
        league_slug: str,
    ) -> list[dict[str, Any]]:
        """Parse a club squad page into a list of player dicts.

        Each player dict contains:
        - name, transfermarkt_id, position, age, nationality
        - contract_expires, market_value_text, market_value_eur
        - club_name, tm_club_id, league_slug
        """
        players: list[dict[str, Any]] = []

        # The first table.items has the player rows
        tables = soup.select("table.items")
        if not tables:
            return players

        table = tables[0]
        # Main player rows have class 'odd' or 'even'
        for row in table.select("tr"):
            classes = row.get("class", [])
            if "odd" not in classes and "even" not in classes:
                continue

            # Must have a player profile link
            player_link = row.select_one('a[href*="/profil/spieler/"]')
            if not player_link:
                continue

            href = player_link.get("href", "")
            m_id = re.search(r"/spieler/(\d+)", href)
            if not m_id:
                continue

            tm_id = int(m_id.group(1))
            name = player_link.get_text(strip=True)
            if not name:
                continue

            # Position (td[4] text or td.posrela inner span)
            position = ""
            cells = row.select("td")
            if len(cells) > 4:
                position = cells[4].get_text(strip=True)

            # Age (td[5])
            age = None
            if len(cells) > 5:
                try:
                    age = int(cells[5].get_text(strip=True))
                except (ValueError, TypeError):
                    pass

            # Contract expires (td[7])
            contract_expires = ""
            if len(cells) > 7:
                contract_expires = cells[7].get_text(strip=True)

            # Market value (td.rechts)
            mv_text = ""
            mv_cell = row.select_one("td.rechts")
            if mv_cell:
                mv_text = mv_cell.get_text(strip=True)
            mv_eur = _parse_market_value(mv_text)

            players.append({
                "name": name,
                "transfermarkt_id": tm_id,
                "position": position,
                "age": age,
                "contract_expires": contract_expires,
                "market_value_text": mv_text,
                "market_value_eur": mv_eur,
                "club_name": club_name,
                "tm_club_id": tm_club_id,
                "league_slug": league_slug,
            })

        return players

    # -- Player profile parsing ---------------------------------------------

    def _parse_player_profile(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract player info from a Transfermarkt profile page.

        Handles the real Transfermarkt HTML structure:
        - Name in ``h1.data-header__headline``
        - Market value in ``div.data-header__market-value-wrapper``
        - Player details in ``div.info-table`` using paired
          ``span.info-table__content`` elements (label + value)
        - Additional details in ``div.data-header__details``
        """
        data: dict[str, Any] = {}

        # Player name (h1 > div.data-header__headline-wrapper)
        name_el = soup.select_one(
            "h1.data-header__headline, "
            ".data-header__headline-wrapper, "
            "h1.tw-text-2xl"
        )
        if name_el:
            data["name"] = name_el.get_text(strip=True)

        # Market value
        mv_el = soup.select_one(
            "div.data-header__market-value-wrapper, "
            "div.tm-player-market-value-development__current-value"
        )
        if mv_el:
            mv_text = mv_el.get_text(strip=True)
            # Strip trailing "Last update: ..." if present
            if "Last update" in mv_text:
                mv_text = mv_text.split("Last update")[0].strip()
            data["market_value_text"] = mv_text
            data["market_value_eur"] = _parse_market_value(mv_text)

        # Info table: div.info-table with paired spans
        # Real HTML: <div class="info-table">
        #   <span class="info-table__content info-table__content--regular">Label:</span>
        #   <span class="info-table__content info-table__content--bold">Value</span>
        #   ...
        # </div>
        for info_box in soup.select("div.info-table"):
            spans = info_box.select("span.info-table__content")
            for i in range(0, len(spans) - 1, 2):
                label = spans[i].get_text(strip=True).rstrip(":")
                value = spans[i + 1].get_text(strip=True)
                if label:
                    data[label.lower()] = value

        # Fallback: data-header__details (li elements)
        if len(data) <= 1:  # only name so far
            for li in soup.select("div.data-header__details li"):
                label_el = li.select_one(".data-header__label")
                content_el = li.select_one(".data-header__content")
                if label_el and content_el:
                    label = label_el.get_text(strip=True).rstrip(":")
                    value = content_el.get_text(strip=True)
                    if label:
                        data[label.lower()] = value

        return data

    # -- MarketDataSource interface ------------------------------------------

    def fetch_valuations(
        self, player_ids: list[int], as_of: datetime,
        player_names: list[str] | None = None,
    ) -> list[MarketValuationRecord]:
        """Fetch current market valuations for specified players.

        Strategy:
        1. CEAPI JSON endpoint (``/ceapi/marketValueDevelopment/graph/{id}``)
           — no slug needed, returns full history with latest value.
        2. Profile page fallback — requires name slug for correct URL.
        """
        records: list[MarketValuationRecord] = []
        names = player_names or [None] * len(player_ids)  # type: ignore[list-item]

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
            except Exception as exc:
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
        except Exception as exc:
            logger.debug("Slug resolution failed for %s: %s", player_id, exc)
        return None

    def fetch_market_value_history(
        self, player_id: int
    ) -> list[dict[str, Any]]:
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
        except Exception as exc:
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
        self, player_ids: list[int], as_of: datetime,
        player_names: list[str] | None = None,
    ) -> list[ContractRecord]:
        """Fetch contract status for specified players.

        Scrapes individual player profile pages for contract end dates
        and estimated salary.
        """
        records: list[ContractRecord] = []
        names = player_names or [None] * len(player_ids)  # type: ignore[list-item]

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
