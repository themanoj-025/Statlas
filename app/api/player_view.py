"""Player payload builders — the server-rendered profile page consumes ONE
aggregate endpoint so SSR does one round trip (site-map.md §3.1).

Radar axes resolve the per-metric display semantics HERE (never left to the
rendering layer, Constitution §3 null-vs-zero policy):

    qualified     — published percentile + raw value present (floor met)
    below_floor   — raw value present but the metric's sample floor not met
    unranked_pool — value qualified but the position-group cohort was below
                    the minimum pool size for that metric (no percentile)
    no_data       — no value for this metric in the latest snapshot
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.api.registry_view import metric_meta
from app.compute.percentiles import REGISTRY_FLOOR_KEYS
from app.config import load_registry
from app.models import MatchEvent
from app.queries.event_queries import get_player_event_coverage
from app.queries.player_queries import (
    get_player_percentiles,
    get_player_profile,
    get_player_raw_stats,
    get_player_slug,
)
from app.queries.sentences import build_profile_sentence
from app.queries.similar_players import get_similar_players


def _age_on(birth: date | None, as_of: date | None) -> int | None:
    if birth is None or as_of is None:
        return None
    return as_of.year - birth.year - ((as_of.month, as_of.day) < (birth.month, birth.day))


def _axis_status(
    pct: float | None, raw: float | None, minutes: float, raw_stats: dict[str, float], mid: str
) -> str:
    if pct is not None:
        return "qualified"
    if raw is None:
        return "no_data"
    floor = REGISTRY_FLOOR_KEYS.get(mid)
    if floor is not None and raw_stats.get(floor[0], 0) < floor[1]:
        return "below_floor"
    if minutes < load_registry()["display_floor_minutes"]:
        return "below_floor"
    return "unranked_pool"


def build_radar_axes(
    db: Session, player_id: int, percentiles: dict[str, float], raw_stats: dict[str, float], minutes: float
) -> list[dict[str, Any]]:
    registry = load_registry()
    profile = get_player_profile(db, player_id)
    group = profile["position_group"] if profile else None
    metric_ids = registry["gk_metrics"] if group == "GK" else registry["outfield_metrics"]

    axes: list[dict[str, Any]] = []
    for mid in metric_ids:
        meta = metric_meta(registry, mid)
        if meta is None:
            continue
        raw = raw_stats.get(mid)
        pct = percentiles.get(mid)
        axes.append(
            {
                **meta,
                "raw": raw,
                "pct": pct,
                "status": _axis_status(pct, raw, minutes, raw_stats, mid),
            }
        )
    return axes


def has_player_event_data(db: Session, player_id: int) -> bool:
    """StatsBomb event-data availability (Phase 2 C1 coverage indicator).

    Mechanically honest: only when match_events rows are actually linked to
    this player (coverage matrix arbiter — Never-List #8). No coverage, no
    teaser, no implied shot maps.
    """
    return (
        db.query(MatchEvent.id)
        .filter(MatchEvent.player_id == player_id)
        .first()
        is not None
    )


def build_player_payload(
    db: Session,
    player_id: int,
    *,
    similar_limit: int = 5,
) -> dict[str, Any] | None:
    profile = get_player_profile(db, player_id)
    if profile is None:
        return None

    percentiles = get_player_percentiles(db, player_id)
    raw = get_player_raw_stats(db, player_id)

    snapshot_date = None
    if percentiles and percentiles.get("snapshot_date"):
        snapshot_date = percentiles["snapshot_date"]
    if raw and raw.get("snapshot_date"):
        snapshot_date = raw["snapshot_date"]

    axes = build_radar_axes(
        db,
        player_id,
        percentiles["percentiles"] if percentiles else {},
        raw["raw_stats"] if raw else {},
        raw["minutes_played"] if raw else 0,
    )

    return {
        "player": {
            "player_id": player_id,
            "name": profile["name"],
            "slug": get_player_slug(db, player_id),
            "club": profile["current_team"],
            "position_group": profile["position_group"],
            "position_label": profile["primary_position"],
            "nationality": profile["nationality"],
            "date_of_birth": profile["date_of_birth"],
            "age": _age_on(
                profile["date_of_birth"],
                snapshot_date.date() if snapshot_date else datetime.now(timezone.utc).date(),
            ),  # UTC policy: "today" for age is the UTC date (timezone-policy.md)
            "photo": None,  # honest placeholder — no licensed imagery yet (Constitution imagery rule)
        },
        "percentiles": {
            "snapshot_date": percentiles["snapshot_date"] if percentiles else None,
            "computed_date": percentiles["computed_date"] if percentiles else None,
            "index": percentiles["index"] if percentiles else None,
        },
        "raw": {
            "snapshot_date": raw["snapshot_date"] if raw else None,
            "season": raw["season"] if raw else None,
            "source": raw["source"] if raw else None,
            "minutes_played": raw["minutes_played"] if raw else 0,
            "matches_played": raw["matches_played"] if raw else 0,
            "league": raw["league"] if raw else None,
            "league_slug": raw["league_slug"] if raw else None,
            "league_tier": raw["league_tier"] if raw else None,
            "team": raw["team"] if raw else None,
        },
        "axes": axes,
        "sentence": build_profile_sentence(db, player_id),
        "similar": get_similar_players(db, player_id, limit=similar_limit),
        "has_event_data": has_player_event_data(db, player_id),
        "event_coverage": get_player_event_coverage(db, player_id),
        "qualifying_minutes": load_registry()["qualifying_minutes"],
        "min_pool_size": load_registry()["min_pool_size"],
    }
