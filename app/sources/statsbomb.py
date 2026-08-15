"""StatsBomb Open Data ingestion (github.com/hudl/open-data).

This is a periodic SYNC of public JSON files — not a live scrape. It feeds the
`match_events` table (shot/pass event coordinates for specific competitions).

Coverage honesty (Constitution §3, Never-List #8): every competition/season
successfully ingested updates `data_coverage` rows for source='statsbomb'.
The UI's shot-map availability badge is driven by those rows — coverage is
never implied beyond what this sync actually loaded.

Attribution: any published analysis derived from this data must state the data
source as StatsBomb and use their logo (README Terms & Conditions; treated as a
UI requirement, enforced by review).

License (re-verified 2026-08-15): the governing instrument is the bespoke
"StatsBomb Public Data User Agreement" (LICENSE.pdf, updated 8 Sep 2023) — NOT
Creative Commons. Key obligations: clause 1.4 attribution (above); clause 2.2
asks users to register (name + email) once at statsbomb.com/resource-centre
(an ask, not a hard gate — track in the refresh runbook); clauses 1.2.1/1.2.2
bar providing the data to third parties and commercially exploiting the data
or any analysis derived from it (resolution tracked in
pre-launch-human-actions.md item 3.1). Full analysis: data-compliance-notes.md
section 3.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import requests
from sqlalchemy.orm import Session

from app.config import get_settings
from app.sources.base import HttpCache, SourceError, fetch_with_retry

logger = logging.getLogger(__name__)

STATSBOMB_RAW_BASE = "https://raw.githubusercontent.com/hudl/open-data/master/data"
COMPETITIONS_URL = f"{STATSBOMB_RAW_BASE}/competitions.json"


def matches_url(competition_id: int, season_id: int) -> str:
    return f"{STATSBOMB_RAW_BASE}/matches/{competition_id}/{season_id}.json"


def events_url(match_id: int) -> str:
    return f"{STATSBOMB_RAW_BASE}/events/{match_id}.json"


def _competition_seasons(competition: dict[str, Any]) -> list[tuple[int, str]]:
    """Normalize a competition entry to [(season_id, season_name), ...].

    LIVE-DRIFT (2026-08-14, real sync): hudl/open-data's competitions.json is
    now a FLAT list of competition-season pairs (each entry carries season_id /
    season_name directly, no nested 'seasons' array). The older nested shape
    (`seasons: [{season_id, season_name}]`) is still supported so fixture tests
    and any pinned copies keep working.
    """
    nested = competition.get("seasons")
    if isinstance(nested, list) and nested:
        return [
            (int(s["season_id"]), str(s.get("season_name", s["season_id"])))
            for s in nested
        ]
    season_id = competition.get("season_id")
    if season_id is not None:
        return [(int(season_id), str(competition.get("season_name", season_id)))]
    return []


class StatsBombOpenDataSource:
    """Syncs StatsBomb event data into match_events + data_coverage."""

    source_name = "statsbomb"

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        cache: HttpCache | None = None,
        fetcher: Callable[..., str] | None = None,
    ) -> None:
        self.session = session or requests.Session()
        self.cache = cache or HttpCache()
        # Injecting a fetcher makes the sync testable without network; the
        # default is the shared retry/cache fetch (statsbomb is a public GitHub
        # repo, no rate-limit declaration required beyond basic politeness).
        self._fetch = fetcher or (
            lambda url, **kw: fetch_with_retry(
                url,
                limiter=_NOOP_LIMITER,
                cache=self.cache,
                headers={"User-Agent": get_settings().user_agent},
            )
        )

    def fetch_competitions(self) -> list[dict[str, Any]]:
        """Raw competitions.json. Note the LIVE shape is a flat list of
        competition-season pairs (see _competition_seasons) — callers should
        group by competition_id if they need per-competition aggregation."""
        return json.loads(self._fetch(COMPETITIONS_URL))

    def sync_competition(
        self,
        db: Session,
        competition: dict[str, Any],
        *,
        season_filter: list[int] | None = None,
        max_matches: int | None = None,
        now: datetime | None = None,
    ) -> dict[str, int]:
        """Sync one competition (optionally only specific seasons)."""
        competition_id = int(competition["competition_id"])
        competition_name = competition["competition_name"]
        country = competition.get("country_name", "")
        seasons = _competition_seasons(competition)
        now = now or datetime.now(timezone.utc)
        loaded_matches = 0
        loaded_events = 0

        for season_id, season in seasons:
            if season_filter and season_id not in season_filter:
                continue
            season = str(season)  # StatsBomb names seasons "2024/2025" -> keep as-is
            try:
                matches = json.loads(
                    self._fetch(matches_url(competition_id, season_id))
                )
            except SourceError as exc:
                logger.error(
                    "statsbomb matches fetch failed for %s/%s: %s",
                    competition_id,
                    season_id,
                    exc,
                )
                continue

            for match in matches:
                if max_matches and loaded_matches >= max_matches:
                    break
                match_id = int(match["match_id"])
                try:
                    events = json.loads(self._fetch(events_url(match_id)))
                except SourceError as exc:
                    logger.error(
                        "statsbomb events fetch failed for match %s: %s", match_id, exc
                    )
                    continue
                inserted = self._insert_events(
                    db, match_id, events, competition_id, season, now
                )
                loaded_events += inserted
                loaded_matches += 1

            self._upsert_coverage(
                db,
                source_identifier=f"statsbomb:{competition_id}:{season_id}",
                competition_name=competition_name,
                country=country,
                season=season,
                now=now,
            )

        db.commit()
        return {"matches": loaded_matches, "events": loaded_events}

    # -- row builders (testable without a DB) -------------------------------
    @staticmethod
    def build_event_rows(
        events: list[dict[str, Any]],
        match_id: int,
        competition_id: int,
        season: str | None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for ev in events:
            loc = ev.get("location") or []
            event_type = ev.get("type", {}).get("name", "")
            player_name = (ev.get("player") or {}).get("name")

            # Source-specific payload (Phase 3): the shot-map / pass-map chain
            # reads these from `extra`. Missing fields stay None — never an
            # invented precision (the fixture's pass has no end_location).
            extra: dict[str, Any] = {}
            if player_name:
                extra["player_name"] = player_name
            if event_type == "Shot":
                shot = ev.get("shot") or {}
                extra.update(
                    {
                        "xg": shot.get("statsbomb_xg"),
                        "body_part": (shot.get("body_part") or {}).get("name"),
                        "technique": (shot.get("technique") or {}).get("name"),
                    }
                )
            elif event_type == "Pass":
                pass_info = ev.get("pass") or {}
                end = pass_info.get("end_location") or []
                extra.update(
                    {
                        "end_x": float(end[0]) if len(end) > 0 else None,
                        "end_y": float(end[1]) if len(end) > 1 else None,
                        "pass_type": (pass_info.get("type") or {}).get("name"),
                        "recipient": (pass_info.get("recipient") or {}).get("name"),
                        "length": pass_info.get("length"),
                        "angle": pass_info.get("angle"),
                    }
                )

            rows.append(
                {
                    "match_id": str(match_id),
                    "event_id": str(ev.get("id", "")),
                    "event_type": event_type,
                    "x_coordinate": float(loc[0]) if len(loc) > 0 else None,
                    "y_coordinate": float(loc[1]) if len(loc) > 1 else None,
                    "minute": (
                        float(ev.get("minute"))
                        if ev.get("minute") is not None
                        else None
                    ),
                    "outcome": (ev.get("shot") or {}).get("outcome", {}).get("name"),
                    "source_competition_id": str(competition_id),
                    "season": season,
                    # player_id is resolved during ingestion by reconciling
                    # player name/ids — until then the event is unmatched (NULL).
                    "player_id": None,
                    "extra": extra,
                }
            )
        return rows

    def _insert_events(
        self,
        db: Session,
        match_id: int,
        events: list[dict[str, Any]],
        competition_id: int,
        season: str,
        now: datetime,
    ) -> int:
        from app.models import MatchEvent

        rows = self.build_event_rows(events, match_id, competition_id, season)
        inserted = 0
        for r in rows:
            existing = (
                db.query(MatchEvent)
                .filter_by(match_id=r["match_id"], event_id=r["event_id"])
                .first()
            )
            if existing:
                continue
            db.add(
                MatchEvent(
                    match_id=r["match_id"],
                    event_id=r["event_id"],
                    player_id=r["player_id"],
                    event_type=r["event_type"],
                    x_coordinate=r["x_coordinate"],
                    y_coordinate=r["y_coordinate"],
                    minute=r["minute"],
                    outcome=r["outcome"],
                    source_competition_id=r["source_competition_id"],
                    season=r["season"],
                    extra=r["extra"],
                )
            )
            inserted += 1
        return inserted

    def _upsert_coverage(
        self,
        db: Session,
        *,
        source_identifier: str,
        competition_name: str,
        country: str,
        season: str,
        now: datetime,
    ) -> None:
        from app.models import DataCoverage

        row = (
            db.query(DataCoverage)
            .filter_by(source="statsbomb", source_identifier=source_identifier)
            .first()
        )
        if row is None:
            row = DataCoverage(
                source="statsbomb",
                source_identifier=source_identifier,
                seasons_available=[season],
                last_successful_scrape=now,
                status="active",
            )
            db.add(row)
        else:
            seasons = list(row.seasons_available or [])
            if season not in seasons:
                seasons.append(season)
            row.seasons_available = seasons
            row.last_successful_scrape = now
            row.status = "active"
        logger.info(
            "coverage upserted for statsbomb %s (season %s)", source_identifier, season
        )


class _NoopLimiter:
    """statsbomb fetches hit a public static GitHub CDN; politeness only."""

    def wait(self) -> None:
        return None


_NOOP_LIMITER = _NoopLimiter()
