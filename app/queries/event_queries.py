"""Event-level queries (Phase 3 — Part B): shot maps and pass maps.

Coverage-gating is the FIRST step (Constitution Never-List #8): the UI may
only render a shot/pass map entry point for a player when `data_coverage`
confirms the competition/season combination was actually synced AND at least
one match event for that player exists. `get_player_event_coverage` is the
single check every map component must pass before rendering — there is no
"coming soon" path for competitions outside the matrix.

Attribution: every consumer of this module's data must render the StatsBomb
source statement + logo (data-compliance-notes.md §3 — a UI requirement, not a
legal footnote). The API contract documents this; the web components enforce it.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.models import DataCoverage, MatchEvent

# Display names for well-known StatsBomb Open Data competition ids. This is a
# small, documented map for UI labels only — the coverage matrix (data_coverage
# rows) is the arbiter of what EXISTS; unknown ids fall back to the raw id,
# never a guessed name. Competitions beyond this map render as their id until
# the map is extended (same commit as any data that requires it).
STATSBOMB_COMPETITION_NAMES: dict[str, str] = {
    "2": "UEFA Champions League",
    "11": "La Liga",
    "12": "Premier League",
    "37": "FA Cup",
    "43": "FA Women's Super League",
    "49": "UEFA Women's Champions League",
    "123": "La Liga",
}

_IDENTIFIER_RE = re.compile(r"^statsbomb:(\d+):(\d+)$")


def competition_label(competition_id: str | int) -> str:
    cid = str(competition_id)
    return STATSBOMB_COMPETITION_NAMES.get(cid, f"Competition {cid}")


def parse_statsbomb_identifier(source_identifier: str) -> tuple[str, str] | None:
    match = _IDENTIFIER_RE.match(source_identifier)
    if match is None:
        return None
    return match.group(1), match.group(2)


def get_statsbomb_competitions(db: Session) -> list[dict[str, Any]]:
    """Covered StatsBomb competitions from data_coverage (the matrix arbiter).

    Returns one entry per active `statsbomb:<comp_id>:<season_id>` row with the
    readable competition name and the seasons that were actually synced.
    """
    rows = (
        db.query(DataCoverage)
        .filter(DataCoverage.source == "statsbomb")
        .order_by(DataCoverage.source_identifier)
        .all()
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        parsed = parse_statsbomb_identifier(row.source_identifier)
        if parsed is None:
            continue
        competition_id, season_id = parsed
        out.append(
            {
                "competition_id": competition_id,
                "season_id": season_id,
                "competition_name": competition_label(competition_id),
                "seasons_available": row.seasons_available or [],
                "last_successful_scrape": row.last_successful_scrape,
                "status": row.status,
            }
        )
    return out


def _coverage_confirms(
    db: Session,
    competition_id: str,
    season: str,
    *,
    require_active: bool = True,
) -> bool:
    """True only when the coverage matrix contains the exact claim.

    Matches the `statsbomb:<cid>:<sid>` rows whose seasons_available includes
    the string season carried by the events — the single check map components
    must pass (B1). Reuses the matrix arbiter semantics from coverage_queries.
    """
    rows = (
        db.query(DataCoverage)
        .filter(
            DataCoverage.source == "statsbomb",
            DataCoverage.source_identifier.like(f"statsbomb:{competition_id}:%"),
        )
        .all()
    )
    for row in rows:
        if require_active and row.status != "active":
            continue
        if season in (row.seasons_available or []):
            return True
    return False


def get_player_event_coverage(db: Session, player_id: int) -> dict[str, Any]:
    """The coverage check every map UI must pass before rendering (Part B1).

    Coverage exists only when BOTH hold: the data_coverage matrix confirms the
    competition/season combination, AND at least one match event involving this
    player is present for it. No coverage row -> no entry point, period.
    """
    events = (
        db.query(MatchEvent.source_competition_id, MatchEvent.season)
        .filter(MatchEvent.player_id == player_id)
        .distinct()
        .all()
    )
    competitions: list[dict[str, Any]] = []
    for competition_id, season in events:
        if season is None:
            continue
        if not _coverage_confirms(db, competition_id, season):
            continue
        matches = (
            db.query(MatchEvent.match_id)
            .filter(
                MatchEvent.player_id == player_id,
                MatchEvent.source_competition_id == competition_id,
                MatchEvent.season == season,
            )
            .distinct()
            .count()
        )
        competitions.append(
            {
                "competition_id": competition_id,
                "competition_name": competition_label(competition_id),
                "season": season,
                "matches": matches,
            }
        )
    competitions.sort(key=lambda c: (c["competition_name"], c["season"]))
    return {
        "has_coverage": bool(competitions),
        "competitions": competitions,
    }


def get_player_event_matches(
    db: Session,
    player_id: int,
    *,
    competition_id: str | None = None,
    season: str | None = None,
) -> list[dict[str, Any]] -> None:
    """Distinct matches with events for this player (the match filter options)."""
    query = db.query(
        MatchEvent.match_id, MatchEvent.source_competition_id, MatchEvent.season
    )
    query = query.filter(MatchEvent.player_id == player_id)
    if competition_id is not None:
        query = query.filter(MatchEvent.source_competition_id == competition_id)
    if season is not None:
        query = query.filter(MatchEvent.season == season)
    rows = query.distinct().order_by(MatchEvent.match_id).all()
    return [
        {
            "match_id": match_id,
            "competition_id": competition_id_,
            "competition_name": competition_label(competition_id_),
            "season": season_,
        }
        for match_id, competition_id_, season_ in rows
    ]


def get_player_events(
    db: Session,
    player_id: int,
    *,
    event_type: str,
    match_id: str | None = None,
    competition_id: str | None = None,
    season: str | None = None,
) -> list[dict[str, Any]] -> None:
    """Shot or pass events for a player, bounded to confirmed coverage.

    Filters are bounded strictly to what data_coverage confirms: if the
    competition/season combination has no coverage row, an empty list is
    returned — the map never renders unconfirmed data.
    """
    # SIM102: the coverage bound is one condition, not a nested if.
    if (
        competition_id is not None
        and season is not None
        and not _coverage_confirms(db, competition_id, season)
    ):
        return []

    query = db.query(MatchEvent).filter(
        MatchEvent.player_id == player_id,
        MatchEvent.event_type == event_type,
    )
    if match_id is not None:
        query = query.filter(MatchEvent.match_id == match_id)
    if competition_id is not None:
        query = query.filter(MatchEvent.source_competition_id == competition_id)
    if season is not None:
        query = query.filter(MatchEvent.season == season)

    rows = query.order_by(MatchEvent.minute.asc().nullsfirst(), MatchEvent.id).all()
    out: list[dict[str, Any]] = []
    for row in rows:
        extra = row.extra or {}
        if event_type == "Shot":
            payload = {
                "xg": extra.get("xg"),
                "body_part": extra.get("body_part"),
                "technique": extra.get("technique"),
            }
        elif event_type == "Pass":
            payload = {
                "end_x": extra.get("end_x"),
                "end_y": extra.get("end_y"),
                "pass_type": extra.get("pass_type"),
                "recipient": extra.get("recipient"),
                "length": extra.get("length"),
                "angle": extra.get("angle"),
                # Derived, documented (methodology §2 progressive-pass rule):
                # a pass is progressive when it moves the ball >= 10 yards
                # toward the opponent's goal in x, or into the penalty area.
                "progressive": is_progressive_pass(
                    row.x_coordinate, extra.get("end_x")
                ),
            }
        else:  # pragma: no cover — event_type is validated by the API
            payload = {}
        out.append(
            {
                "event_id": row.event_id,
                "match_id": row.match_id,
                "minute": row.minute,
                "x": row.x_coordinate,
                "y": row.y_coordinate,
                "outcome": row.outcome,
                "competition_id": row.source_competition_id,
                "competition_name": competition_label(row.source_competition_id),
                "season": row.season,
                **payload,
            }
        )
    return out


def is_progressive_pass(start_x: float | None, end_x: float | None) -> bool:
    """Derived progressive-pass flag on the StatsBomb 120x80 pitch.

    FBref definition adapted to StatsBomb coordinates: a pass is progressive
    when it advances the ball at least 10 yards toward the opponent's goal
    (x increasing) or ends inside the penalty area (x >= 102). Missing
    end coordinates -> False (never assumed).
    """
    if start_x is None or end_x is None:
        return False
    return (end_x - start_x) >= 10.0 or (start_x < 102.0 and end_x >= 102.0)
