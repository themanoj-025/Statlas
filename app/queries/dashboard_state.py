"""Dashboard — state management, save/unsave, saved players."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    DashboardState,
    Player,
    SavedPlayer,
    StatSnapshot,
)

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
) -> list[str] -> None:
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
) -> SavedPlayer -> None:
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
    from app.models import Team

    entries = (
        db.query(SavedPlayer)
        .filter(SavedPlayer.user_id == user_id)
        .order_by(SavedPlayer.saved_at.desc())
        .all()
    )
    if not entries:
        return []

    # Batch-load all players and teams (eliminates N+1)
    player_ids = [e.player_id for e in entries]
    players_map = {p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()}
    team_ids = {p.current_team_id for p in players_map.values() if p.current_team_id}
    teams_map = {t.id: t for t in db.query(Team).filter(Team.id.in_(team_ids)).all()} if team_ids else {}

    results: list[dict] = []
    for entry in entries:
        player = players_map.get(entry.player_id)
        if player is None:
            continue
        team = teams_map.get(player.current_team_id) if player.current_team_id else None
        results.append(
            {
                "player_id": player.id,
                "player_name": player.canonical_name,
                "team_name": team.name if team else None,
                "position_group": player.position_group,
                "saved_at": entry.saved_at.isoformat(),
                "category": entry.category,
            }
        )
    return results
