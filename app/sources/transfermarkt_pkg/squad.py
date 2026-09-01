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
    """Squad player fetching and parsing."""

    def fetch_squad_players(
        self, league_slug: str, season: str | None = None
    ) -> list[dict[str, Any]] -> None:
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
            except (requests.RequestException, ValueError, KeyError, OSError) as exc:
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
                with contextlib.suppress(ValueError):
                    squad_size = int(size_text)

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
                with contextlib.suppress(ValueError, TypeError):
                    age = int(cells[5].get_text(strip=True))

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

