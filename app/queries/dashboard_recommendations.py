"""Dashboard recommendation queries."""

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
    candidate_pids = [row.player_id for row in candidates if row.player_id not in all_seen and row.player_id not in dismissed]
    players_map = {p.id: p for p in db.query(Player).filter(Player.id.in_(candidate_pids)).all()} if candidate_pids else {}
    team_ids = {p.current_team_id for p in players_map.values() if p.current_team_id}
    teams_map = {t.id: t for t in db.query(Team).filter(Team.id.in_(team_ids)).all()} if team_ids else {}

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
