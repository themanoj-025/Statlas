"""API-Football source — fixtures / live-score layer ONLY (Constitution §3:
the word "live" is used exclusively for this layer).

Compliance posture (data-compliance-notes.md):
- Free tier ceiling: 80 requests/day (20% headroom under the published 100/day
  figure). A FileBackedBudget hard-stops the layer before the quota runs out —
  a run never silently fails mid-way through the quota.
- Max 1 request per 2 seconds (API_FOOTBALL_DELAY_SECONDS).
- Raw fixture payloads are not republished; fixtures render as schedule/live
  state UI only. Attribution line is a UI requirement (Phase 2+).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from app.config import get_settings, load_tiers
from app.sources.base import (
    BudgetExhaustedError,
    FixtureRecord,
    HttpCache,
    RateLimiter,
    SourceError,
)

logger = logging.getLogger(__name__)

API_FOOTBALL_BASE = "https://v3.football.api-sports.io"


def _utc_today() -> str:
    """Today's date in UTC (timezone policy: the budget day boundary is the
    UTC one — two servers in different zones must agree on when a day resets)."""
    return datetime.now(timezone.utc).date().isoformat()


class FileBackedBudget:
    """Daily request budget persisted to disk; resets when the UTC date changes.

    This is what stops the weekly run at 80 requests even if the process is
    restarted mid-week.
    """

    def __init__(self, daily_limit: int, path: str | Path | None = None) -> None:
        self.daily_limit = daily_limit
        self.path = Path(path or Path(get_settings().cache_dir) / "api_football_budget.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._day: str | None = None
        self._used = 0
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("day") == _utc_today():
                self._day = data["day"]
                self._used = int(data.get("used", 0))
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            pass

    def _persist(self) -> None:
        try:
            self.path.write_text(
                json.dumps({"day": self._day or _utc_today(), "used": self._used}),
                encoding="utf-8",
            )
        except OSError:
            logger.warning("could not persist API-Football budget file")

    @property
    def used(self) -> int:
        today = _utc_today()
        if self._day != today:
            self._day = today
            self._used = 0
            self._persist()
        return self._used

    def remaining(self) -> int:
        return max(0, self.daily_limit - self.used)

    def acquire(self) -> None:
        if self.remaining() <= 0:
            raise BudgetExhaustedError(
                f"API-Football daily budget exhausted ({self.daily_limit}/day) — stopping, not limping on"
            )
        self._used += 1
        self._persist()


class APIFootballSource:
    source_name = "api_football"

    def __init__(
        self,
        *,
        key: str | None = None,
        budget: FileBackedBudget | None = None,
        limiter: RateLimiter | None = None,
        cache: HttpCache | None = None,
        session: requests.Session | None = None,
    ) -> None:
        settings = get_settings()
        self.key = key or settings.api_football_key
        if not self.key:
            logger.warning("API_FOOTBALL_KEY is not set; fixtures sync will fail loudly at first request")
        self.budget = budget or FileBackedBudget(settings.api_football_daily_budget)
        self.limiter = limiter or RateLimiter(settings.api_football_delay_seconds)
        self.cache = cache or HttpCache()
        self.session = session or requests.Session()
        self.tiers = load_tiers()

    def get_rate_limit_seconds(self) -> float:
        return self.limiter.interval

    # -- pure helpers (unit-tested without network) -------------------------
    @staticmethod
    def build_url(league_api_id: int, season: int) -> str:
        return f"{API_FOOTBALL_BASE}/fixtures?league={league_api_id}&season={season}"

    @staticmethod
    def canonical_season_to_year(season: str) -> int:
        return int(season.split("-")[0])

    @staticmethod
    def parse_fixtures(payload: dict[str, Any], league_slug: str, season: str) -> list[FixtureRecord]:
        records: list[FixtureRecord] = []
        for item in payload.get("response", []):
            teams = item.get("teams", {})
            home = teams.get("home", {}).get("name", "")
            away = teams.get("away", {}).get("name", "")
            if not home or not away:
                continue
            records.append(
                FixtureRecord(
                    league_slug=league_slug,
                    season=season,
                    api_fixture_id=int(item.get("fixture", {}).get("id", 0)),
                    home_team_name=home,
                    away_team_name=away,
                    kickoff_utc=item.get("fixture", {}).get("date"),
                    status=item.get("fixture", {}).get("status", {}).get("short"),
                    raw=item,
                )
            )
        return records

    # -- live fetch ---------------------------------------------------------
    def fetch_fixtures(self, league_slug: str, season: str) -> list[FixtureRecord]:
        league = self.tiers["leagues"][league_slug]
        api_id = league["external_ids"].get("api_football")
        if api_id is None:
            raise SourceError(f"no api_football id configured for '{league_slug}'")
        url = self.build_url(int(api_id), self.canonical_season_to_year(season))
        headers = {"x-apisports-key": self.key} if self.key else {}

        # Budget is checked here, at the moment of the request — the hard stop.
        self.budget.acquire()
        self.limiter.wait()
        try:
            resp = self.session.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise SourceError(f"API-Football request failed for {url}: {exc}") from exc

        try:
            payload = resp.json()
        except ValueError as exc:
            raise SourceError(f"API-Football returned non-JSON for {url}: {exc}") from exc
        if payload.get("errors"):
            raise SourceError(f"API-Football errors: {payload['errors']}")
        return self.parse_fixtures(payload, league_slug, season)
