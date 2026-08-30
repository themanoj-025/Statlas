"""Dashboard queries — Phase 13 Parts B–C.

Composes existing per-user data (shortlists, saved searches, reports, watches)
with activity tracking and grounded recommendation heuristics into dashboard
widgets.  No ML — every recommendation is explainable via documented heuristics
(docs/product/dashboard-recommendations-logic.md).

PercentileSnapshot joins through StatSnapshot to reach player_id — the
percentile table has no direct player FK (C1 closeout tier-dimension design).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    ActivityLog,
    DashboardState,
    PercentileSnapshot,
    Player,
    SavedPlayer,
    SavedSearch,
    Shortlist,
    ShortlistEntry,
    StatSnapshot,
    Team,
    Watch,
    WatchAlert,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RECENT_ACTIVITY_LOOKBACK_DAYS = 14
RECENT_ACTIVITY_LIMIT = 20
TRENDING_LIMIT = 10
RECOMMENDATION_LIMIT = 10
DISMISS_DECAY_DAYS = 30


# ---------------------------------------------------------------------------
# C1 — Recent activity aggregation
# ---------------------------------------------------------------------------


def get_recent_activity(
    db: Session,
    user_id: int,
    *,
    limit: int = RECENT_ACTIVITY_LIMIT,
    lookback_days: int = RECENT_ACTIVITY_LOOKBACK_DAYS,
) -> list[dict]:
    """Return recently-viewed players/teams for the dashboard's "Recently
    Viewed" widget.  Deduplication is handled at write time (activity.py);
    this query just orders and limits.
    """
    from app.models import Team

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    rows = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.user_id == user_id,
            ActivityLog.action_type == "viewed",
            ActivityLog.performed_at > cutoff,
        )
        .order_by(ActivityLog.performed_at.desc())
        .limit(limit * 2)
        .all()
    )

    seen: set[tuple[str, int]] = set()
    player_ids: list[int] = []
    team_ids: set[int] = set()
    raw_entries: list[dict] = []
    for row in rows:
        key = (row.entity_type, row.entity_id)
        if key in seen:
            continue
        seen.add(key)
        entry: dict = {
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "action_type": row.action_type,
            "performed_at": row.performed_at.isoformat(),
        }
        if row.entity_type == "player":
            player_ids.append(row.entity_id)
        raw_entries.append(entry)
        if len(raw_entries) >= limit:
            break

    # Batch-load all players and teams (eliminates N+1)
    players_map: dict[int, Player] = {}
    if player_ids:
        players_map = {p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()}
        team_ids = {p.current_team_id for p in players_map.values() if p.current_team_id}
    teams_map: dict[int, Team] = {}
    if team_ids:
        teams_map = {t.id: t for t in db.query(Team).filter(Team.id.in_(team_ids)).all()}

    results: list[dict] = []
    for entry in raw_entries:
        if entry["entity_type"] == "player":
            player = players_map.get(entry["entity_id"])
            if player is not None:
                entry["player_name"] = player.canonical_name
                entry["position_group"] = player.position_group
                team = teams_map.get(player.current_team_id) if player.current_team_id else None
                entry["team_name"] = team.name if team else None
        results.append(entry)

    return results


# ---------------------------------------------------------------------------
# C2 — Workspace shortcuts aggregation
# ---------------------------------------------------------------------------


def get_workspace_summary(db: Session, user_id: int) -> dict:
    """Quick counts for the dashboard's "Workspace Shortcuts" widget."""
    shortlist_count = (
        db.query(func.count(Shortlist.id))
        .filter(
            Shortlist.user_id == user_id,
            Shortlist.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )

    search_count = (
        db.query(func.count(SavedSearch.id))
        .filter(SavedSearch.user_id == user_id)
        .scalar()
        or 0
    )

    # Count shortlist entries (proxy for report count — reports are linked
    # to shortlist entries in this product)
    report_count = (
        db.query(func.count())
        .select_from(ShortlistEntry)
        .join(Shortlist, ShortlistEntry.shortlist_id == Shortlist.id)
        .filter(Shortlist.user_id == user_id)
        .scalar()
        or 0
    )

    watch_count = (
        db.query(func.count(Watch.id)).filter(Watch.user_id == user_id).scalar() or 0
    )

    unread_alerts = (
        db.query(func.count(WatchAlert.id))
        .join(Watch, WatchAlert.watch_id == Watch.id)
        .filter(Watch.user_id == user_id, WatchAlert.read_at.is_(None))
        .scalar()
        or 0
    )

    return {
        "shortlist_count": shortlist_count,
        "saved_search_count": search_count,
        "report_count": report_count,
        "watch_count": watch_count,
        "unread_alert_count": unread_alerts,
    }


# ---------------------------------------------------------------------------
# C3 — Trending players (grounded in real data, not vibes)
# ---------------------------------------------------------------------------


def get_trending_players(
    db: Session,
    user_id: int,
    *,
    limit: int = TRENDING_LIMIT,
) -> list[dict]:
    """Players with sustained upward percentile movement in the past week.

    Trending = players whose average percentile gain across metrics that moved
    up exceeds 5.0 points between the two most recent published snapshots,
    AND the user hasn't already viewed/saved them.
    """
    # Get user's recently viewed/saved player IDs (to exclude)
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    viewed_ids = {
        r[0]
        for r in (
            db.query(ActivityLog.entity_id)
            .filter(
                ActivityLog.user_id == user_id,
                ActivityLog.entity_type == "player",
                ActivityLog.performed_at > cutoff,
            )
            .all()
        )
    }
    saved_ids = {
        r[0]
        for r in (
            db.query(SavedPlayer.player_id).filter(SavedPlayer.user_id == user_id).all()
        )
    }
    exclude_ids = viewed_ids | saved_ids

    # Get the two most recent published snapshot computed_dates
    dates = (
        db.query(PercentileSnapshot.computed_date)
        .filter(PercentileSnapshot.is_published.is_(True))
        .order_by(PercentileSnapshot.computed_date.desc())
        .distinct()
        .limit(2)
        .all()
    )
    if len(dates) < 2:
        return []

    latest_date = dates[0][0]
    prev_date = dates[1][0]

    # Find players with percentile gains by joining through StatSnapshot
    from sqlalchemy import and_

    curr_subq = (
        db.query(
            StatSnapshot.player_id,
            PercentileSnapshot.metric_name,
            PercentileSnapshot.percentile_value,
        )
        .join(
            PercentileSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id
        )
        .filter(
            PercentileSnapshot.computed_date == latest_date,
            PercentileSnapshot.is_published.is_(True),
        )
        .subquery()
    )

    prev_subq = (
        db.query(
            StatSnapshot.player_id,
            PercentileSnapshot.metric_name,
            PercentileSnapshot.percentile_value,
        )
        .join(
            PercentileSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id
        )
        .filter(
            PercentileSnapshot.computed_date == prev_date,
            PercentileSnapshot.is_published.is_(True),
        )
        .subquery()
    )

    gains = (
        db.query(
            curr_subq.c.player_id,
            func.avg(curr_subq.c.percentile_value - prev_subq.c.percentile_value).label(
                "avg_gain"
            ),
            func.count().label("metrics_with_data"),
        )
        .join(
            prev_subq,
            and_(
                curr_subq.c.player_id == prev_subq.c.player_id,
                curr_subq.c.metric_name == prev_subq.c.metric_name,
            ),
        )
        .filter(curr_subq.c.percentile_value > prev_subq.c.percentile_value)
        .group_by(curr_subq.c.player_id)
        .having(
            func.avg(curr_subq.c.percentile_value - prev_subq.c.percentile_value) > 5.0
        )
        .order_by(
            func.avg(curr_subq.c.percentile_value - prev_subq.c.percentile_value).desc()
        )
        .limit(limit * 3)
        .all()
    )

    results: list[dict] = []
    for row in gains:
        pid = row.player_id
        if pid in exclude_ids:
            continue
        player = db.get(Player, pid)
        if player is None:
            continue
        team_name = None
        if player.current_team_id:
            from app.models import Team

            team = db.get(Team, player.current_team_id)
            team_name = team.name if team else None
        results.append(
            {
                "player_id": pid,
                "player_name": player.canonical_name,
                "team_name": team_name,
                "position_group": player.position_group,
                "avg_gain": round(float(row.avg_gain), 1),
                "explanation": (
                    f"Average percentile gain of "
                    f"{abs(round(float(row.avg_gain), 1))} points across "
                    f"{row.metrics_with_data} metrics"
                ),
            }
