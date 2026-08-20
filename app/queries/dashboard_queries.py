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
    results: list[dict] = []
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
            player = db.get(Player, row.entity_id)
            if player is not None:
                entry["player_name"] = player.canonical_name
                entry["position_group"] = player.position_group
                if player.current_team_id:
                    from app.models import Team

                    team = db.get(Team, player.current_team_id)
                    entry["team_name"] = team.name if team else None
                else:
                    entry["team_name"] = None
        results.append(entry)
        if len(results) >= limit:
            break

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
        )
        if len(results) >= limit:
            break

    return results


# ---------------------------------------------------------------------------
# C4 — Recommended players (grounded heuristics, not ML)
# ---------------------------------------------------------------------------


def get_recommended_players(
    db: Session,
    user_id: int,
    *,
    limit: int = RECOMMENDATION_LIMIT,
) -> list[dict]:
    """Personalized recommendations based on the user's viewing patterns.

    Logic (documented in docs/product/dashboard-recommendations-logic.md):
    1. Find the user's recently viewed/saved players (last 30 days).
    2. Extract their position groups.
    3. Find similar-position players the user hasn't seen, ranked by average
       percentile.
    4. Exclude dismissed recommendations.
    """
    # Step 1: Get user's recently viewed/saved players
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    viewed_player_ids = [
        r[0]
        for r in (
            db.query(ActivityLog.entity_id)
            .filter(
                ActivityLog.user_id == user_id,
                ActivityLog.entity_type == "player",
                ActivityLog.performed_at > cutoff,
            )
            .distinct()
            .all()
        )
    ]
    saved_player_ids = [
        r[0]
        for r in (
            db.query(SavedPlayer.player_id).filter(SavedPlayer.user_id == user_id).all()
        )
    ]

    all_seen = set(viewed_player_ids + saved_player_ids)
    if not all_seen:
        return []

    # Step 2: Get dismissed recommendations
    dashboard = (
        db.query(DashboardState).filter(DashboardState.user_id == user_id).first()
    )
    dismissed: set[int] = set()
    if dashboard and dashboard.dismissed_recommendations:
        dismissed = set(dashboard.dismissed_recommendations)

    # Step 3: Extract position groups from seen players
    seen_players = db.query(Player).filter(Player.id.in_(all_seen)).all()

    position_counts: dict[str, int] = {}
    for p in seen_players:
        if p.position_group:
            position_counts[p.position_group] = (
                position_counts.get(p.position_group, 0) + 1
            )

    if not position_counts:
        return []

    # Top 2 position groups the user is interested in
    top_positions = sorted(
        position_counts, key=position_counts.get, reverse=True  # type: ignore[arg-type]
    )[:2]

    # Step 4: Find similar unseen players ranked by average percentile
    latest_date_row = (
        db.query(PercentileSnapshot.computed_date)
        .filter(PercentileSnapshot.is_published.is_(True))
        .order_by(PercentileSnapshot.computed_date.desc())
        .first()
    )
    if not latest_date_row:
        return []

    latest_date = latest_date_row[0]

    candidates = (
        db.query(
            StatSnapshot.player_id,
            func.avg(PercentileSnapshot.percentile_value).label("avg_pct"),
        )
        .join(
            PercentileSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id
        )
        .filter(
            PercentileSnapshot.computed_date == latest_date,
            PercentileSnapshot.is_published.is_(True),
            StatSnapshot.player_id.notin_(all_seen),
            StatSnapshot.player_id.notin_(dismissed),
        )
        .join(Player, StatSnapshot.player_id == Player.id)
        .filter(Player.position_group.in_(top_positions))
        .group_by(StatSnapshot.player_id)
        .order_by(func.avg(PercentileSnapshot.percentile_value).desc())
        .limit(limit * 3)
        .all()
    )

    results: list[dict] = []
    for row in candidates:
        pid = row.player_id
        if pid in all_seen or pid in dismissed:
            continue
        player = db.get(Player, pid)
        if player is None:
            continue
        team_name = None
        if player.current_team_id:
            from app.models import Team

            team = db.get(Team, player.current_team_id)
            team_name = team.name if team else None

        avg_pct = round(float(row.avg_pct), 1)

        pos_label = player.position_group or "unknown"
        matching_count = position_counts.get(pos_label, 0)
        explanation = (
            f"Similar to the {pos_label} players you've recently viewed "
            f"({matching_count} viewed), with an average {avg_pct}th percentile rating"
        )

        results.append(
            {
                "player_id": pid,
                "player_name": player.canonical_name,
                "team_name": team_name,
                "position_group": player.position_group,
                "avg_percentile": avg_pct,
                "explanation": explanation,
            }
        )
        if len(results) >= limit:
            break

    return results


# ---------------------------------------------------------------------------
# B1 — Dashboard state management
# ---------------------------------------------------------------------------


def get_or_create_dashboard_state(db: Session, user_id: int) -> DashboardState:
    """Get or create the user's dashboard state row."""
    state = db.query(DashboardState).filter(DashboardState.user_id == user_id).first()
    if state is None:
        state = DashboardState(user_id=user_id)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def dismiss_recommendation(db: Session, user_id: int, player_id: int) -> None:
    """Add a player to the user's dismissed-recommendations list."""
    state = get_or_create_dashboard_state(db, user_id)
    dismissed = list(state.dismissed_recommendations or [])
    if player_id not in dismissed:
        dismissed.append(player_id)
    state.dismissed_recommendations = dismissed
    state.updated_at = datetime.now(timezone.utc)
    db.commit()


# ---------------------------------------------------------------------------
# B1.5 — Top viewed positions (for transfer opportunities widget)
# ---------------------------------------------------------------------------


def get_top_viewed_positions(
    db: Session,
    user_id: int,
    *,
    lookback_days: int = 30,
    limit: int = 5,
) -> list[str]:
    """Return the position groups the user has viewed most frequently.

    Used by the dashboard's transfer opportunities widget to surface
    relevant hidden gems for the user's areas of interest.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    # Get recently viewed player IDs
    viewed_player_ids = [
        r[0]
        for r in (
            db.query(ActivityLog.entity_id)
            .filter(
                ActivityLog.user_id == user_id,
                ActivityLog.entity_type == "player",
                ActivityLog.action_type == "viewed",
                ActivityLog.performed_at > cutoff,
            )
            .distinct()
            .all()
        )
    ]
    if not viewed_player_ids:
        return []

    # Count position groups from viewed players
    from sqlalchemy import func

    position_counts = (
        db.query(
            Player.position_group,
            func.count().label("view_count"),
        )
        .filter(
            Player.id.in_(viewed_player_ids),
            Player.position_group.isnot(None),
        )
        .group_by(Player.position_group)
        .order_by(func.count().desc())
        .limit(limit)
        .all()
    )

    return [row.position_group for row in position_counts if row.position_group]


# ---------------------------------------------------------------------------
# B2 — Saved players CRUD
# ---------------------------------------------------------------------------


def save_player(
    db: Session,
    user_id: int,
    player_id: int,
    category: str | None = None,
) -> SavedPlayer:
    """Bookmark a player.  Unique constraint prevents duplicates."""
    existing = (
        db.query(SavedPlayer)
        .filter(
            SavedPlayer.user_id == user_id,
            SavedPlayer.player_id == player_id,
        )
        .first()
    )
    if existing is not None:
        if category is not None:
            existing.category = category
            db.commit()
            db.refresh(existing)
        return existing

    player = db.get(Player, player_id)
    if player is None:
        raise ValueError(f"Player {player_id} not found")

    entry = SavedPlayer(user_id=user_id, player_id=player_id, category=category)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def unsave_player(db: Session, user_id: int, player_id: int) -> bool:
    """Remove a player from the user's saved list.  Returns True if removed."""
    entry = (
        db.query(SavedPlayer)
        .filter(
            SavedPlayer.user_id == user_id,
            SavedPlayer.player_id == player_id,
        )
        .first()
    )
    if entry is None:
        return False
    db.delete(entry)
    db.commit()
    return True


def get_saved_players(db: Session, user_id: int) -> list[dict]:
    """Return the user's saved players with summary data."""
    entries = (
        db.query(SavedPlayer)
        .filter(SavedPlayer.user_id == user_id)
        .order_by(SavedPlayer.saved_at.desc())
        .all()
    )
    results: list[dict] = []
    for entry in entries:
        player = db.get(Player, entry.player_id)
        if player is None:
            continue
        team_name = None
        if player.current_team_id:
            from app.models import Team

            team = db.get(Team, player.current_team_id)
            team_name = team.name if team else None
        results.append(
            {
                "player_id": player.id,
                "player_name": player.canonical_name,
                "team_name": team_name,
                "position_group": player.position_group,
                "saved_at": entry.saved_at.isoformat(),
                "category": entry.category,
            }
        )
    return results
