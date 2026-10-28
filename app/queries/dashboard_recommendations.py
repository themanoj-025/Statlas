"""Dashboard — trending players and recommendations."""

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
    StatSnapshot,
    Team,
)
from app.queries.dashboard_activity import RECOMMENDATION_LIMIT, TRENDING_LIMIT

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

    # Find players with percentile gains by comparing published snapshots
    curr_rows = (
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
        .all()
    )

    prev_rows = (
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
        .all()
    )

    prev_map = {(pid, m): val for pid, m, val in prev_rows if val is not None}

    from collections import defaultdict

    player_gains: dict[int, list[float]] = defaultdict(list)
    for pid, m, c_val in curr_rows:
        if c_val is None or pid in exclude_ids:
            continue
        p_val = prev_map.get((pid, m))
        if p_val is not None and c_val > p_val:
            player_gains[pid].append(c_val - p_val)

    qualifying: list[tuple[int, float, int]] = []
    for pid, gains in player_gains.items():
        avg_gain = sum(gains) / len(gains)
        if avg_gain > 5.0:
            qualifying.append((pid, avg_gain, len(gains)))

    qualifying.sort(key=lambda x: x[1], reverse=True)
    top_candidates = qualifying[: limit * 3]

    candidate_pids = [pid for pid, _, _ in top_candidates]
    players_map = (
        {p.id: p for p in db.query(Player).filter(Player.id.in_(candidate_pids)).all()}
        if candidate_pids
        else {}
    )
    team_ids = {p.current_team_id for p in players_map.values() if p.current_team_id}
    teams_map = (
        {t.id: t for t in db.query(Team).filter(Team.id.in_(team_ids)).all()}
        if team_ids
        else {}
    )

    results: list[dict] = []
    for pid, avg_gain, metrics_with_data in top_candidates:
        player = players_map.get(pid)
        if player is None:
            continue
        team = teams_map.get(player.current_team_id) if player.current_team_id else None
        results.append(
            {
                "player_id": pid,
                "player_name": player.canonical_name,
                "team_name": team.name if team else None,
                "position_group": player.position_group,
                "avg_gain": round(float(avg_gain), 1),
                "explanation": (
                    f"Average percentile gain of "
                    f"{abs(round(float(avg_gain), 1))} points across "
                    f"{metrics_with_data} metrics"
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
        position_counts, key=lambda k: position_counts[k], reverse=True
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

    # Batch-load all candidates' players and teams (eliminates N+1)
    candidate_pids = [
        row.player_id
        for row in candidates
        if row.player_id not in all_seen and row.player_id not in dismissed
    ]
    players_map = (
        {p.id: p for p in db.query(Player).filter(Player.id.in_(candidate_pids)).all()}
        if candidate_pids
        else {}
    )
    team_ids = {p.current_team_id for p in players_map.values() if p.current_team_id}
    teams_map = (
        {t.id: t for t in db.query(Team).filter(Team.id.in_(team_ids)).all()}
        if team_ids
        else {}
    )

    results: list[dict] = []
    for row in candidates:
        pid = row.player_id
        if pid in all_seen or pid in dismissed:
            continue
        player = players_map.get(pid)
        if player is None:
            continue
        team = teams_map.get(player.current_team_id) if player.current_team_id else None

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
                "team_name": team.name if team else None,
                "position_group": player.position_group,
                "avg_percentile": avg_pct,
                "explanation": explanation,
            }
        )
        if len(results) >= limit:
            break

    return results
