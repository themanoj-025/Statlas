"""Leaderboard queries — internal functions for the Phase 2 leaderboard pages.

Serves PUBLISHED percentile/index rows for a league × position group × season.
The `metric` parameter accepts a registry metric id or the index id
("si_index"); rows are ordered by the metric's direction so 'lower is better'
metrics sort ascending (a lower value ranks higher).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import load_registry
from app.models import League, PercentileSnapshot, Player, StatSnapshot


def get_leaderboard(
    db: Session,
    *,
    league_slug: str,
    position_group: str,
    metric: str,
    season: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    registry = load_registry()
    metric_spec = registry["metrics"].get(metric)
    invert = bool(metric_spec and metric_spec["direction"] == "lower_is_better")

    league = db.query(League).filter_by(slug=league_slug).first()
    if league is None:
        return []

    rows = (
        db.query(PercentileSnapshot, StatSnapshot, Player)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .join(Player, StatSnapshot.player_id == Player.id)
        .filter(
            PercentileSnapshot.is_published.is_(True),
            PercentileSnapshot.metric_name == metric,
            PercentileSnapshot.position_group == position_group,
            StatSnapshot.league_id == league.id,
            StatSnapshot.season == season,
        )
        .all()
    )

    # Keep the latest snapshot per player (a player may have multiple snapshots
    # across scrape dates; published rows exist per snapshot).
    best: dict[int, tuple[PercentileSnapshot, StatSnapshot, Player]] = {}
    for percentile, snap, player in rows:
        existing = best.get(player.id)
        if existing is None or snap.scrape_date > existing[1].scrape_date:
            best[player.id] = (percentile, snap, player)

    entries = []
    for percentile, snap, player in best.values():
        value = percentile.index_score if metric == registry["index_metric_id"] else percentile.percentile_value
        if value is None:
            continue
        entries.append(
            {
                "player_id": player.id,
                "name": player.canonical_name,
                "position_group": percentile.position_group,
                "club": _team_name(db, snap.team_id),
                "minutes": snap.minutes_played,
                "value": value,
                "snapshot_date": snap.scrape_date,
            }
        )

    entries.sort(key=lambda e: e["value"], reverse=not invert)
    return entries[:limit]


def _team_name(db: Session, team_id: int | None) -> str | None:
    if team_id is None:
        return None
    from app.models import Team

    team = db.get(Team, team_id)
    return team.name if team else None


# ---------------------------------------------------------------------------
# Phase 2: filtered + paginated leaderboard (leaderboard page consumption)
# ---------------------------------------------------------------------------

def get_leaderboard_filtered(
    db: Session,
    *,
    metric: str,
    season: str,
    league_slugs: list[str] | None = None,
    tier: str | None = None,
    position_group: str | None = None,
    min_minutes: float | None = None,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "value",
    sort_dir: str | None = None,
) -> dict[str, Any]:
    """Paginated leaderboard across one or more leagues / a tier.

    Same published-only, latest-snapshot-per-player, direction-aware rules as
    get_leaderboard (its per-league behaviour is the limit case of this),
    plus filters, pagination, and server-side column sorting so the table can
    be sortable without shipping thousands of rows to the client.
    """
    registry = load_registry()
    metric_spec = registry["metrics"].get(metric)
    if metric_spec is None and metric != registry["index_metric_id"]:
        raise ValueError(f"unknown metric '{metric}'")
    invert = bool(metric_spec and metric_spec["direction"] == "lower_is_better")

    from app.models import League
    from app.queries.player_queries import player_slug_map

    league_filter = None
    if league_slugs:
        league_ids = [row[0] for row in db.query(League.id).filter(League.slug.in_(league_slugs)).all()]
        league_filter = StatSnapshot.league_id.in_(league_ids)
    elif tier:
        league_ids = [row[0] for row in db.query(League.id).filter(League.tier == tier).all()]
        league_filter = StatSnapshot.league_id.in_(league_ids)

    query = (
        db.query(PercentileSnapshot, StatSnapshot, Player, League)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .join(Player, StatSnapshot.player_id == Player.id)
        .join(League, StatSnapshot.league_id == League.id)
        .filter(
            PercentileSnapshot.is_published.is_(True),
            PercentileSnapshot.metric_name == metric,
            StatSnapshot.season == season,
        )
    )
    if league_filter is not None:
        query = query.filter(league_filter)
    if position_group is not None:
        query = query.filter(PercentileSnapshot.position_group == position_group)
    if min_minutes is not None:
        query = query.filter(StatSnapshot.minutes_played >= min_minutes)

    rows = query.all()

    best: dict[int, tuple[PercentileSnapshot, StatSnapshot, Player, League]] = {}
    for percentile, snap, player, league in rows:
        existing = best.get(player.id)
        if existing is None or snap.scrape_date > existing[1].scrape_date:
            best[player.id] = (percentile, snap, player, league)

    entries: list[dict[str, Any]] = []
    slugs = {p["player_id"]: p["slug"] for p in player_slug_map(db)}
    for percentile, snap, player, league in best.values():
        value = percentile.index_score if metric == registry["index_metric_id"] else percentile.percentile_value
        if value is None:
            continue
        entries.append(
            {
                "player_id": player.id,
                "name": player.canonical_name,
                "slug": slugs.get(player.id),
                "position_group": percentile.position_group,
                "club": _team_name(db, snap.team_id),
                "league": league.name,
                "league_slug": league.slug,
                "tier": league.tier,
                "minutes": snap.minutes_played,
                "matches": snap.matches_played,
                "value": value,
                "snapshot_date": snap.scrape_date,
            }
        )

    if sort_by == "minutes":
        entries.sort(key=lambda e: e["minutes"], reverse=(sort_dir or "desc") == "desc")
    elif sort_by == "name":
        entries.sort(key=lambda e: e["name"].lower(), reverse=(sort_dir or "asc") == "desc")
    elif sort_by == "club":
        entries.sort(key=lambda e: (e["club"] or "").lower(), reverse=(sort_dir or "asc") == "desc")
    else:  # value — direction-aware default
        if sort_dir is not None:
            entries.sort(key=lambda e: e["value"], reverse=sort_dir == "desc")
        else:
            entries.sort(key=lambda e: e["value"], reverse=not invert)

    total = len(entries)
    page = entries[offset : offset + limit]
    return {
        "entries": page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }
