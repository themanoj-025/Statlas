"""League queries — Phase 2 league index pages.

- get_league_catalog: the league list (from config/tiers.json via the DB
  catalog) enriched with what data actually exists for each league.
- get_league_stats_table: per-90 raw-stats table for a league (latest snapshot
  per player), excluding players with unresolved anomalies (the anomaly gate —
  flagged values are never silently published, Constitution §3).
- get_league_teams: team list for a league (roster links).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.compute.anomaly_check import blocked_player_ids
from app.compute.percentiles import REGISTRY_FLOOR_KEYS
from app.config import CURRENT_SEASON, load_registry, load_tiers
from app.models import DataCoverage, League, Player, StatSnapshot, Team
from app.queries.player_queries import get_player_slug, slugify_name


def _current_season() -> str:
    return CURRENT_SEASON


def get_league_catalog(db: Session) -> list[dict[str, Any]]:
    """All leagues (config tiers) with coverage + team counts per league."""
    tiers_cfg = load_tiers()
    leagues = {league.slug: league for league in db.query(League).all()}
    coverage = db.query(DataCoverage).all()
    by_league: dict[int, list[DataCoverage]] = {}
    for row in coverage:
        if row.league_id is not None:
            by_league.setdefault(row.league_id, []).append(row)

    # Team counts per league for the index page.
    team_counts: dict[int, int] = {}
    for league_id, cnt in (
        db.query(Team.league_id, func.count(Team.id)).group_by(Team.league_id).all()
    ):
        team_counts[league_id] = cnt

    catalog: list[dict[str, Any]] = []
    for slug, cfg in tiers_cfg["leagues"].items():
        league = leagues.get(slug)
        rows = by_league.get(league.id, []) if league else []
        catalog.append(
            {
                "slug": slug,
                "name": cfg["name"],
                "country": cfg["country"],
                "tier": cfg["tier"],
                "tier_label": _tier_label(cfg["tier"]),
                "has_fbref_coverage": any(
                    r.source == "fbref" and r.status == "active" for r in rows
                ),
                "team_count": team_counts.get(league.id, 0) if league else 0,
                "seasons_available": sorted(
                    {s for r in rows for s in (r.seasons_available or [])}
                ),
                "sources": sorted({r.source for r in rows if r.status == "active"}),
            }
        )
    return catalog


def get_league_detail(db: Session, league_slug: str) -> dict[str, Any] | None:
    """League hub payload: identity, teams, coverage rows, qualifying counts."""
    league = db.query(League).filter_by(slug=league_slug).first()
    if league is None:
        return None
    season = _current_season()
    teams = db.query(Team).filter(Team.league_id == league.id).order_by(Team.name).all()
    from app.queries.coverage_queries import get_data_coverage

    return {
        "slug": league.slug,
        "name": league.name,
        "country": league.country,
        "tier": league.tier,
        "tier_label": _tier_label(league.tier),
        "season": season,
        "teams": [
            {
                "team_id": t.id,
                "name": t.name,
                "slug": slugify_name(t.name),
                "logo_url": t.logo_url,
            }
            for t in teams
        ],
        "coverage": get_data_coverage(db, league_id=league.id),
        "has_fbref_coverage": any(
            r["source"] == "fbref" and r["status"] == "active"
            for r in get_data_coverage(db, league_id=league.id)
        ),
    }


def get_league_stats_table(
    db: Session,
    league_slug: str,
    *,
    metric: str,
    season: str | None = None,
    limit: int = 300,
) -> list[dict[str, Any]] -> None:
    """Per-90 raw stats table for a league, sorted by a registry metric.

    Latest snapshot per player; players with unresolved anomalies are excluded
    (never silently published). Values are raw per-90 from the snapshot —
    sample floors (minutes < 180 etc.) are resolved here, not by the UI.
    """
    season = season or _current_season()
    league = db.query(League).filter_by(slug=league_slug).first()
    if league is None:
        return []

    registry = load_registry()
    spec = registry["metrics"].get(metric)
    if spec is None:
        raise ValueError(f"unknown metric '{metric}'")
    invert = spec["direction"] == "lower_is_better"

    blocked = blocked_player_ids(db)
    snaps = (
        db.query(StatSnapshot)
        .filter(
            StatSnapshot.league_id == league.id,
            StatSnapshot.season == season,
        )
        .order_by(StatSnapshot.scrape_date.desc(), StatSnapshot.player_id)
        .all()
    )
    latest: dict[int, StatSnapshot] = {}
    for snap in snaps:
        latest.setdefault(snap.player_id, snap)
    if not latest:
        return []

    player_ids = list(latest.keys())
    players = {
        p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
    }
    teams = {
        t.id: t
        for t in db.query(Team)
        .filter(Team.id.in_([s.team_id for s in latest.values() if s.team_id]))
        .all()
    }

    entries: list[dict[str, Any]] = []
    for pid, snap in latest.items():
        if pid in blocked:
            continue
        raw = snap.raw_stats or {}
        value = raw.get(metric)
        display_value = None
        status = "no_data"
        if value is not None:
            if _floor_met(raw, snap.minutes_played, metric):
                display_value = value
                status = "qualified"
            else:
                status = "below_floor"
        entries.append(
            {
                "player_id": pid,
                "name": players[pid].canonical_name,
                "slug": get_player_slug(db, pid),
                "position_group": players[pid].position_group,
                "club": teams[snap.team_id].name if snap.team_id in teams else None,
                "minutes": snap.minutes_played,
                "matches": snap.matches_played,
                "value": display_value,
                "status": status,
                "snapshot_date": snap.scrape_date,
                "season": snap.season,
            }
        )

    def _sort_key(e: dict[str, Any]) -> tuple[int, float]:
        # qualified values rank first; below-floor and no-data last (both show N/A).
        if e["value"] is None:
            return (1, 0.0)
        return (0, e["value"])

    entries.sort(key=_sort_key, reverse=not invert)
    return entries[:limit]


def _floor_met(raw_stats: dict[str, float], minutes: float, metric: str) -> bool:
    """Resolve the registry's per-metric sample floor (methodology.md §2.4).

    Minutes-kind floors compare the snapshot's minutes; counter-kind floors
    (pass attempts / shots on target / crosses faced) compare the '_'-prefixed
    counter keys the FBref scraper writes (REGISTRY_FLOOR_KEYS is the single
    source of truth — same keys compute.percentiles uses).
    """
    from app.config import load_registry as _lr

    floor = _lr()["metrics"][metric].get("display_floor")
    minutes_fail = (
        floor is not None and floor["type"] == "minutes" and minutes < floor["value"]
    )
    counter = REGISTRY_FLOOR_KEYS.get(metric)
    counter_fail = counter is not None and raw_stats.get(counter[0], 0) < counter[1]
    return not (minutes_fail or counter_fail)


def get_league_teams(db: Session, league_slug: str) -> list[dict[str, Any]]:
    detail = get_league_detail(db, league_slug)
    return detail["teams"] if detail else []


def _tier_label(tier: str) -> str:
    return {"tier_1": "Tier 1", "tier_2": "Tier 2", "tier_3": "Tier 3"}.get(tier, tier)
