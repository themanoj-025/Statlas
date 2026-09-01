"""Team queries — Phase 2 Part D (team profile pages).

- get_team_profile: identity + roster + squad-average radar in one payload
  (server-rendered page consumes this once, not N round trips).
- Roster entries carry each player's latest published index + minutes so the
  table is sortable by real data.
- Squad radar is the average published percentile per metric across the team's
  qualifying players (same values the leaderboards show); N is returned so the
  UI can render the "not enough qualifying players" empty state honestly.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.config import load_registry
from app.models import League, PercentileSnapshot, Player, StatSnapshot, Team
from app.queries.player_queries import get_player_slug, slugify_name


def _team_by_slug(db: Session, league: League, team_slug: str) -> Team | None:
    for team in db.query(Team).filter(Team.league_id == league.id).all():
        if slugify_name(team.name) == team_slug:
            return team
    return None


def get_team_profile(
    db: Session,
    *,
    league_slug: str,
    team_slug: str,
    season: str | None = None,
) -> dict[str, Any] | None:
    """Full team-profile payload, or None when league/team is unknown."""
    league = db.query(League).filter_by(slug=league_slug).first()
    if league is None:
        return None
    team = _team_by_slug(db, league, team_slug)
    if team is None:
        return None

    roster = _roster(db, team, season=season)
    return {
        "team_id": team.id,
        "name": team.name,
        "slug": slugify_name(team.name),
        "league_id": league.id,
        "league": league.name,
        "league_slug": league.slug,
        "tier": league.tier,
        "logo_url": team.logo_url,  # NULL until real assets exist — UI shows honest placeholder
        "founded_year": team.founded_year,
        "roster": roster,
        "squad_radar": _squad_radar(db, roster),
        "roster_count": len(roster),
        "qualified_count": sum(1 for r in roster if r["index"] is not None),
    }


def _roster(
    db: Session, team: Team, *, season: str | None = None
) -> list[dict[str, Any]]:
    """Players whose latest snapshot is with this team, with published stats.

    Uses the snapshot's team (a player's latest team of record), falling back
    to current_team_id — a mid-season move shows the player under the team they
    last played for in the data, which is the honest snapshot-based answer.
    """
    snaps = (
        db.query(StatSnapshot)
        .filter(StatSnapshot.team_id == team.id)
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

    # Latest published index per player.
    index_id = load_registry()["index_metric_id"]
    pct_rows = (
        db.query(PercentileSnapshot, StatSnapshot)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(
            PercentileSnapshot.is_published.is_(True),
            PercentileSnapshot.metric_name == index_id,
            StatSnapshot.player_id.in_(player_ids),
        )
        .all()
    )
    best_index: dict[int, float] = {}
    for pct, snap in pct_rows:
        existing = best_index.get(snap.player_id)
        # SIM102: newest-snapshot + present-index is one condition.
        if (
            existing is None or snap.scrape_date >= latest[snap.player_id].scrape_date
        ) and pct.index_score is not None:
            best_index[snap.player_id] = pct.index_score

    roster: list[dict[str, Any]] = []
    for pid, snap in latest.items():
        player = players.get(pid)
        if player is None:
            continue
        roster.append(
            {
                "player_id": pid,
                "name": player.canonical_name,
                "slug": get_player_slug(db, pid),
                "position_group": player.position_group,
                "position_label": player.primary_position,
                "nationality": player.nationality,
                "minutes": snap.minutes_played,
                "matches": snap.matches_played,
                "index": best_index.get(pid),
                "snapshot_date": snap.scrape_date,
                "season": snap.season,
            }
        )
    roster.sort(
        key=lambda r: (r["index"] is None, -(r["index"] or 0), r["name"].lower())
    )
    return roster


def _squad_radar(db: Session, roster: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Average published percentile per metric across qualifying squad members.

    Returns {snapshot_date, n_players, metrics: [{id, avg_pct}]} or None when
    fewer than 5 qualifying players (the UI renders the explicit empty state).
    """
    qualified = [r for r in roster if r["index"] is not None]
    if len(qualified) < 5:
        return None
    player_ids = [r["player_id"] for r in qualified]

    rows = (
        db.query(PercentileSnapshot, StatSnapshot)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(
            PercentileSnapshot.is_published.is_(True),
            PercentileSnapshot.percentile_value.isnot(None),
            StatSnapshot.player_id.in_(player_ids),
        )
        .all()
    )
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    latest_date = None
    for pct, snap in rows:
        sums[pct.metric_name] += pct.percentile_value
        counts[pct.metric_name] += 1
        if latest_date is None or snap.scrape_date > latest_date:
            latest_date = snap.scrape_date

    metrics = [
        {"id": mid, "avg_pct": round(sums[mid] / counts[mid], 2), "n": counts[mid]}
        for mid in sums
    ]
    metrics.sort(key=lambda m: m["avg_pct"], reverse=True)
    return {
        "snapshot_date": latest_date,
        "n_players": len(qualified),
        "metrics": metrics,
    }
