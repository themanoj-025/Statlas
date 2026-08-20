"""Phase 13 — personal dashboard tests.

Tests cover:
- Activity logging with 60s deduplication
- Workspace summary aggregation
- Trending player detection against hand-calculated synthetic data
- Recommendation logic (matching user interest, excluding viewed)
- Saved players CRUD
- Dismiss recommendation persistence
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.activity import DEDUP_WINDOW_SECONDS, log_activity
from app.models import (
    ActivityLog,
    Base,
    League,
    PercentileSnapshot,
    Player,
    Shortlist,
    StatSnapshot,
    User,
)
from app.queries.dashboard_queries import (
    dismiss_recommendation,
    get_or_create_dashboard_state,
    get_recommended_players,
    get_saved_players,
    get_trending_players,
    get_workspace_summary,
    save_player,
    unsave_player,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_engine = create_engine("sqlite:///:memory:", echo=False)
_Session = sessionmaker(bind=_engine)


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(_engine)
    with _Session() as db:
        yield db
    Base.metadata.drop_all(_engine)


def _create_user(db: Session, email: str = "test@example.com") -> User:
    user = User(email=email, password_hash="x", plan="pro")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_player(
    db: Session, name: str, pos: str = "CM", team_id: int | None = None
) -> Player:
    player = Player(canonical_name=name, position_group=pos, current_team_id=team_id)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def _create_stat_snapshot(
    db: Session, player_id: int, league_id: int, season: str, scrape_date: datetime
) -> StatSnapshot:
    snap = StatSnapshot(
        player_id=player_id,
        league_id=league_id,
        season=season,
        scrape_date=scrape_date,
        source="fbref",
        raw_stats={},
        minutes_played=2000,
        matches_played=30,
        status="published",
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def _seed_percentiles(
    db: Session,
    stat_snapshot_id: int,
    computed_date: datetime,
    position_group: str,
    league_tier: str,
    metrics: dict[str, float],
    is_published: bool = True,
) -> None:
    for metric_name, percentile in metrics.items():
        db.add(
            PercentileSnapshot(
                stat_snapshot_id=stat_snapshot_id,
                computed_date=computed_date,
                position_group=position_group,
                league_tier=league_tier,
                metric_name=metric_name,
                percentile_value=percentile,
                is_published=is_published,
            )
        )
    db.commit()


# ---------------------------------------------------------------------------
# Activity logging tests
# ---------------------------------------------------------------------------


class TestActivityLogging:
    def test_log_creates_row(self, db: Session):
        user = _create_user(db)
        player = _create_player(db, "Player A")

        logged = log_activity(
            db,
            user_id=user.id,
            entity_type="player",
            entity_id=player.id,
            action_type="viewed",
        )
        assert logged is True

        rows = db.query(ActivityLog).all()
        assert len(rows) == 1
        assert rows[0].user_id == user.id

    def test_dedup_within_window(self, db: Session):
        """Same user + same entity within 60s = no duplicate."""
        user = _create_user(db)
        player = _create_player(db, "Player B")

        first = log_activity(
            db,
            user_id=user.id,
            entity_type="player",
            entity_id=player.id,
            action_type="viewed",
        )
        second = log_activity(
            db,
            user_id=user.id,
            entity_type="player",
            entity_id=player.id,
            action_type="viewed",
        )

        assert first is True
        assert second is False
        assert db.query(ActivityLog).count() == 1

    def test_no_dedup_after_window(self, db: Session):
        """After the dedup window, the same action is logged again."""
        user = _create_user(db)
        player = _create_player(db, "Player C")

        log_activity(
            db,
            user_id=user.id,
            entity_type="player",
            entity_id=player.id,
            action_type="viewed",
        )

        # Backdate the existing row beyond the dedup window
        row = db.query(ActivityLog).first()
        row.performed_at = datetime.now(timezone.utc) - timedelta(
            seconds=DEDUP_WINDOW_SECONDS + 10
        )
        db.commit()

        second = log_activity(
            db,
            user_id=user.id,
            entity_type="player",
            entity_id=player.id,
            action_type="viewed",
        )
        assert second is True
        assert db.query(ActivityLog).count() == 2

    def test_different_entities_not_deduped(self, db: Session):
        user = _create_user(db)
        p1 = _create_player(db, "Player D")
        p2 = _create_player(db, "Player E")

        log_activity(
            db,
            user_id=user.id,
            entity_type="player",
            entity_id=p1.id,
            action_type="viewed",
        )
        log_activity(
            db,
            user_id=user.id,
            entity_type="player",
            entity_id=p2.id,
            action_type="viewed",
        )

        assert db.query(ActivityLog).count() == 2


# ---------------------------------------------------------------------------
# Workspace summary tests
# ---------------------------------------------------------------------------


class TestWorkspaceSummary:
    def test_empty_workspace(self, db: Session):
        user = _create_user(db)
        summary = get_workspace_summary(db, user.id)
        assert summary["shortlist_count"] == 0
        assert summary["saved_search_count"] == 0
        assert summary["report_count"] == 0
        assert summary["watch_count"] == 0
        assert summary["unread_alert_count"] == 0

    def test_counts_shortlists(self, db: Session):
        user = _create_user(db)
        db.add(Shortlist(user_id=user.id, name="List 1"))
        db.add(Shortlist(user_id=user.id, name="List 2"))
        db.commit()

        summary = get_workspace_summary(db, user.id)
        assert summary["shortlist_count"] == 2

    def test_excludes_deleted_shortlists(self, db: Session):
        user = _create_user(db)
        db.add(Shortlist(user_id=user.id, name="Active"))
        db.add(
            Shortlist(
                user_id=user.id,
                name="Deleted",
                deleted_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

        summary = get_workspace_summary(db, user.id)
        assert summary["shortlist_count"] == 1


# ---------------------------------------------------------------------------
# Trending player tests
# ---------------------------------------------------------------------------


class TestTrendingPlayers:
    def _setup_trending(self, db: Session) -> tuple[User, Player, Player]:
        """Create a trending player and a static player with synthetic data."""
        user = _create_user(db)
        league = League(
            name="Test League",
            country="Testland",
            tier="tier_1",
            slug="test-league",
        )
        db.add(league)
        db.commit()
        db.refresh(league)

        trending_player = _create_player(db, "Trending Star", "CM")
        static_player = _create_player(db, "Static Player", "CM")

        prev_date = datetime(2026, 8, 1, tzinfo=timezone.utc)
        curr_date = datetime(2026, 8, 8, tzinfo=timezone.utc)

        # Trending Star: big gains
        snap_prev = _create_stat_snapshot(
            db, trending_player.id, league.id, "2025-26", prev_date
        )
        snap_curr = _create_stat_snapshot(
            db, trending_player.id, league.id, "2025-26", curr_date
        )
        _seed_percentiles(
            db,
            snap_prev.id,
            prev_date,
            "CM",
            "tier_1",
            {
                "progressive_passes_p90": 50,
                "defensive_actions_p90": 40,
                "duels_won_pct": 45,
            },
        )
        _seed_percentiles(
            db,
            snap_curr.id,
            curr_date,
            "CM",
            "tier_1",
            {
                "progressive_passes_p90": 70,  # +20
                "defensive_actions_p90": 60,  # +20
                "duels_won_pct": 55,  # +10
            },
        )

        # Static Player: no change
        snap_prev_s = _create_stat_snapshot(
            db, static_player.id, league.id, "2025-26", prev_date
        )
        snap_curr_s = _create_stat_snapshot(
            db, static_player.id, league.id, "2025-26", curr_date
        )
        _seed_percentiles(
            db,
            snap_prev_s.id,
            prev_date,
            "CM",
            "tier_1",
            {
                "progressive_passes_p90": 50,
                "defensive_actions_p90": 50,
                "duels_won_pct": 50,
            },
        )
        _seed_percentiles(
            db,
            snap_curr_s.id,
            curr_date,
            "CM",
            "tier_1",
            {
                "progressive_passes_p90": 50,
                "defensive_actions_p90": 50,
                "duels_won_pct": 50,
            },
        )

        return user, trending_player, static_player

    def test_returns_players_with_upward_movement(self, db: Session):
        user, trending_player, _ = self._setup_trending(db)

        trending = get_trending_players(db, user.id)
        assert len(trending) >= 1
        assert trending[0]["player_id"] == trending_player.id
        assert trending[0]["avg_gain"] > 5.0

    def test_excludes_viewed_players(self, db: Session):
        user, trending_player, _ = self._setup_trending(db)

        # Log the user as having viewed this player
        log_activity(
            db,
            user_id=user.id,
            entity_type="player",
            entity_id=trending_player.id,
            action_type="viewed",
        )

        trending = get_trending_players(db, user.id)
        assert all(t["player_id"] != trending_player.id for t in trending)


# ---------------------------------------------------------------------------
# Recommendation tests
# ---------------------------------------------------------------------------


class TestRecommendations:
    def test_recommends_similar_position_unseen(self, db: Session):
        """User who viewed CM players gets recommended other CMs."""
        user = _create_user(db)
        league = League(
            name="Test League",
            country="Testland",
            tier="tier_1",
            slug="test-league-rec",
        )
        db.add(league)
        db.commit()
        db.refresh(league)

        cm1 = _create_player(db, "CM Viewed 1", "CM")
        cm2 = _create_player(db, "CM Viewed 2", "CM")
        cm_rec = _create_player(db, "CM Recommendation", "CM")
        st_other = _create_player(db, "ST Other", "ST")

        now = datetime.now(timezone.utc)

        for p in [cm1, cm2, cm_rec, st_other]:
            snap = _create_stat_snapshot(db, p.id, league.id, "2025-26", now)
            _seed_percentiles(
                db,
                snap.id,
                now,
                p.position_group or "CM",
                "tier_1",
                {
                    "progressive_passes_p90": 60,
                    "defensive_actions_p90": 50,
                    "duels_won_pct": 55,
                },
            )

        # Override CM Recommendation to have higher percentiles
        snap_rec = (
            db.query(StatSnapshot).filter(StatSnapshot.player_id == cm_rec.id).first()
        )
        # Delete and re-create with higher values
        db.query(PercentileSnapshot).filter(
            PercentileSnapshot.stat_snapshot_id == snap_rec.id
        ).delete()
        _seed_percentiles(
            db,
            snap_rec.id,
            now,
            "CM",
            "tier_1",
            {
                "progressive_passes_p90": 80,
                "defensive_actions_p90": 70,
                "duels_won_pct": 75,
            },
        )

        # Log user viewing the two CMs
        log_activity(
            db,
            user_id=user.id,
            entity_type="player",
            entity_id=cm1.id,
            action_type="viewed",
        )
        log_activity(
            db,
            user_id=user.id,
            entity_type="player",
            entity_id=cm2.id,
            action_type="viewed",
        )

        recs = get_recommended_players(db, user.id)
        rec_ids = [r["player_id"] for r in recs]

        # CM Recommendation should be recommended
        assert cm_rec.id in rec_ids
        # Already-viewed players should not appear
        assert cm1.id not in rec_ids
        assert cm2.id not in rec_ids

    def test_excludes_dismissed(self, db: Session):
        user = _create_user(db)
        league = League(
            name="Test League",
            country="Testland",
            tier="tier_1",
            slug="test-league-dismiss",
        )
        db.add(league)
        db.commit()
        db.refresh(league)

        cm1 = _create_player(db, "CM Seed 1", "CM")
        cm_dismissed = _create_player(db, "CM Dismissed", "CM")

        now = datetime.now(timezone.utc)
        for p in [cm1, cm_dismissed]:
            snap = _create_stat_snapshot(db, p.id, league.id, "2025-26", now)
            _seed_percentiles(
                db,
                snap.id,
                now,
                "CM",
                "tier_1",
                {
                    "progressive_passes_p90": 60,
                    "defensive_actions_p90": 50,
                    "duels_won_pct": 55,
                },
            )

        log_activity(
            db,
            user_id=user.id,
            entity_type="player",
            entity_id=cm1.id,
            action_type="viewed",
        )

        # Dismiss the other player
        dismiss_recommendation(db, user.id, cm_dismissed.id)

        recs = get_recommended_players(db, user.id)
        assert all(r["player_id"] != cm_dismissed.id for r in recs)


# ---------------------------------------------------------------------------
# Saved players tests
# ---------------------------------------------------------------------------


class TestSavedPlayers:
    def test_save_and_list(self, db: Session):
        user = _create_user(db)
        player = _create_player(db, "Saved One")

        entry = save_player(db, user.id, player.id, category="favorite")
        assert entry.player_id == player.id
        assert entry.category == "favorite"

        saved = get_saved_players(db, user.id)
        assert len(saved) == 1
        assert saved[0]["player_id"] == player.id

    def test_duplicate_save_is_idempotent(self, db: Session):
        user = _create_user(db)
        player = _create_player(db, "Saved Twice")

        save_player(db, user.id, player.id)
        save_player(db, user.id, player.id)

        saved = get_saved_players(db, user.id)
        assert len(saved) == 1

    def test_unsave(self, db: Session):
        user = _create_user(db)
        player = _create_player(db, "To Remove")

        save_player(db, user.id, player.id)
        removed = unsave_player(db, user.id, player.id)
        assert removed is True

        saved = get_saved_players(db, user.id)
        assert len(saved) == 0

    def test_unsave_nonexistent_returns_false(self, db: Session):
        user = _create_user(db)
        removed = unsave_player(db, user.id, 99999)
        assert removed is False


# ---------------------------------------------------------------------------
# Dashboard state tests
# ---------------------------------------------------------------------------


class TestDashboardState:
    def test_get_or_create_creates(self, db: Session):
        user = _create_user(db)
        state = get_or_create_dashboard_state(db, user.id)
        assert state.user_id == user.id
        assert state.dismissed_recommendations == []

    def test_get_or_create_reuses(self, db: Session):
        user = _create_user(db)
        s1 = get_or_create_dashboard_state(db, user.id)
        s2 = get_or_create_dashboard_state(db, user.id)
        assert s1.id == s2.id

    def test_dismiss_persists(self, db: Session):
        user = _create_user(db)
        dismiss_recommendation(db, user.id, 42)
        state = get_or_create_dashboard_state(db, user.id)
        assert 42 in state.dismissed_recommendations
