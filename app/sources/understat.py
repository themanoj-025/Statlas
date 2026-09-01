"""Understat source — xG/xA supplement for the Big-5 (Tier 1) leagues only.

Compliance posture (data-compliance-notes.md):
- robots.txt is `Disallow: /` and no express license exists — this source is
  used minimally (one request per league-season per week) and treated as revocable.
- Self-imposed rate limit: 1 request per 5 seconds (UNDERSTAT_DELAY_SECONDS),
  enforced by RateLimiter.
- Data is extracted from the embedded JSON payload in the page's <script>
  tags (not fragile HTML table scraping): `var playersDataObject = JSON.parse('...')`.
- PRODUCTION DRIFT (2026-08-14, live validation): Understat stopped embedding
  playersDataObject in the league page HTML; player rows now come from the
  POST endpoint `main/getPlayersStats/`. fetch_league_stats therefore tries the
  embedded payload first (fixture/older pages), then falls back to the POST
  endpoint, then fails loudly — never returns partial data.
- Only derived per-90 values are produced; raw payloads are never republished.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from app.config import get_settings, load_registry, load_tiers
from app.sources.base import (
    HttpCache,
    RateLimiter,
    RawPlayerStatRecord,
    SchemaChangedError,
    StatsSource,
    fetch_with_retry,
)

logger = logging.getLogger(__name__)

UNDERSTAT_BASE = "https://understat.com"

_PLAYERS_DATA_RE = re.compile(
    r"var\s+playersDataObject\s*=\s*JSON\.parse\('(.+?)'\)\s*;", re.DOTALL
)

# Understat's current player-table endpoint (live page calls this with
# league + season form data after dropping the embedded playersDataObject).
_PLAYERS_API_PATH = "main/getPlayersStats/"

# Understat JSON key -> registry metric id (all per-90 derived from totals).
METRIC_KEY_MAP = {
    "xG": "si_xg_p90",
    "xA": "si_xag_p90",
    "shots": "si_sh_p90",
    "key_passes": "si_kp_p90",
    "goals": "si_gls_p90",
}


class UnderstatSchemaChangedError(SchemaChangedError):
    """The embedded JSON payload structure changed unexpectedly."""


def canonical_season_to_understat(season: str) -> str:
    """'2025-26' -> '2025' (Understat URL year format)."""
    return season.split("-", maxsplit=1)[0]


def extract_players_json(html: str) -> list[dict[str, Any]]:
    """Extract and decode the `playersDataObject` embedded JSON from page HTML.

    The payload is JS single-quote escaped inside JSON.parse('...'); it must be
    unescaped before json.loads. Raises UnderstatSchemaChangedError loudly if the
    payload is absent — never returns a partial guess.
    """
    match = _PLAYERS_DATA_RE.search(html)
    if not match:
        raise UnderstatSchemaChangedError(
            "understat page did not contain playersDataObject JSON.parse payload"
        )
    raw = match.group(1)
    try:
        unescaped = raw.encode("utf-8").decode("unicode_escape")
        data = json.loads(unescaped)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UnderstatSchemaChangedError(
            f"could not decode playersDataObject payload: {exc}"
        ) from exc
    if not isinstance(data, list):
        raise UnderstatSchemaChangedError(
            "playersDataObject decoded to a non-list payload"
        )
    return data


class UnderstatSource(StatsSource):
    source_name = "understat"

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        cache: HttpCache | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        settings = get_settings()
        self.session = session or requests.Session()
        self.cache = cache or HttpCache()
        self.limiter = limiter or RateLimiter(settings.understat_delay_seconds)
        self.registry = load_registry()
        self.tiers = load_tiers()

    def get_rate_limit_seconds(self) -> float:
        return self.limiter.interval

    def build_url(self, league_slug: str, season: str) -> str:
        understat_id = self.tiers["leagues"][league_slug]["external_ids"].get(
            "understat"
        )
        if understat_id is None:
            raise SchemaChangedError(
                f"league '{league_slug}' has no understat id — Understat covers Big-5 only"
            )
        return f"{UNDERSTAT_BASE}/league/{understat_id}/{canonical_season_to_understat(season)}"

    def fetch_league_stats(
        self, league_slug: str, season: str
    ) -> list[RawPlayerStatRecord] -> None:
        url = self.build_url(league_slug, season)
        logger.info("fetching Understat %s %s", league_slug, season)
        html = fetch_with_retry(
            url,
            limiter=self.limiter,
            cache=self.cache,
            headers={"User-Agent": get_settings().user_agent},
        )
        try:
            payload = extract_players_json(html)
        except UnderstatSchemaChangedError:
            # Live drift (2026): no embedded payload — fetch the same players
            # from the current POST endpoint before failing loudly.
            logger.info(
                "no embedded playersDataObject; falling back to %s", _PLAYERS_API_PATH
            )
            payload = self._fetch_players_api(league_slug, season)

        records: list[RawPlayerStatRecord] = []
        for entry in payload:
            try:
                minutes = int(float(entry.get("time", 0)))
            except (TypeError, ValueError):
                minutes = 0
            raw_stats: dict[str, float] = {}
            for key, mid in METRIC_KEY_MAP.items():
                raw = entry.get(key)
                if raw is None or raw == "":
                    continue
                try:
                    total = float(raw)
                except (TypeError, ValueError):
                    continue
                if minutes > 0:
                    raw_stats[mid] = round(total / minutes * 90, 4)
            if not raw_stats:
                logger.debug(
                    "understat entry with no usable stats: %s", entry.get("player_name")
                )
            records.append(
                RawPlayerStatRecord(
                    source="understat",
                    season=season,
                    league_slug=league_slug,
                    player_name=str(entry.get("player_name", "")),
                    team_name=str(entry.get("team_title", "")),
                    minutes_played=minutes,
                    matches_played=int(entry.get("games", 0) or 0),
                    raw_stats=raw_stats,
                    position_code=str(entry.get("position", ""))
                    or None,  # GK/D/M/F — reconciliation hint only
                    dob_year=None,  # Understat does not expose DOB
                    external_ids={"understat": int(entry.get("id", 0))},
                )
            )
        return records

    def _fetch_players_api(self, league_slug: str, season: str) -> list[dict[str, Any]]:
        """Fetch the player list from Understat's current POST endpoint.

        Returns the same list-of-dicts shape as the embedded payload. Raises
        UnderstatSchemaChangedError loudly on a non-JSON / error response —
        never a partial guess.
        """
        understat_id = self.tiers["leagues"][league_slug]["external_ids"].get(
            "understat"
        )
        if understat_id is None:
            raise UnderstatSchemaChangedError(
                f"league '{league_slug}' has no understat id — Understat covers Big-5 only"
            )
        api_url = f"{UNDERSTAT_BASE}/{_PLAYERS_API_PATH}"
        logger.info("POST %s league=%s season=%s", api_url, understat_id, season)
        body = fetch_with_retry(
            api_url,
            limiter=self.limiter,
            cache=self.cache,
            method="POST",
            data={
                "league": understat_id,
                "season": canonical_season_to_understat(season),
            },
            headers={
                "User-Agent": get_settings().user_agent,
                "Referer": f"{UNDERSTAT_BASE}/league/{understat_id}/{canonical_season_to_understat(season)}",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise UnderstatSchemaChangedError(
                f"{_PLAYERS_API_PATH} returned non-JSON (structure changed): {exc}"
            ) from exc
        if not isinstance(data, dict) or not data.get("success"):
            raise UnderstatSchemaChangedError(
                f"{_PLAYERS_API_PATH} returned an error payload"
            )
        players = data.get("players")
        if not isinstance(players, list):
            raise UnderstatSchemaChangedError(
                f"{_PLAYERS_API_PATH} payload has no players list"
            )
        return players
