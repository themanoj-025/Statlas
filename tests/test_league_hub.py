"""Phase 11 — league hub & emerging-player detection tests.

Tests cover:
- Emerging-player score computation against hand-calculated synthetic data
- Boundary conditions (below/above threshold, min snapshots, qualification)
- League hub aggregation (partial-data honesty)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import load_registry
from app.models import (

pytestmark = pytest.mark.slow
    Base,
    EmergingPlayerScore,
    League,
    PercentileSnapshot,
    Player,
    StatSnapshot,
    Team,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SNAP_DATE = datetime(2026, 8, 1, tzinfo=timezone.utc)
SEASON = "2025-26"


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _seed_league(db: Session, name: str = "Premier League") -> League:
    league = League(slug="premier-league", name=name, country="England", tier="tier_1")
    db.add(league)
    db.flush()
    return league


def _seed_team(db: Session, league: League, name: str = "Arsenal") -> Team:
    team = Team(name=name, league_id=league.id)
    db.add(team)
    db.flush()
    return team


def _seed_player(
    db: Session,
    name: str,
    team: Team,
    league: League,
    *,
    dob: date | str | None = "2002-06-15",
) -> Player:
    player = Player(canonical_name=name, current_team_id=team.id)
    if dob:
        if isinstance(dob, str):
            parts = dob.split("-")
            dob = date(int(parts[0]), int(parts[1]), int(parts[2]))
        player.date_of_birth = dob
    db.add(player)
    db.flush()
    return player


def _seed_snapshots(
    db: Session,
    player: Player,
    league: League,
    *,
    dates: list[datetime],
    minutes: float = 2000,
    raw_stats: dict | None = None,
) -> list[StatSnapshot]:
    """Create stat_snapshots at given dates for a player."""
    snaps = []
    for d in dates:
        snap = StatSnapshot(
            player_id=player.id,
            league_id=league.id,
            team_id=player.current_team_id,
            season=SEASON,
            scrape_date=d,
            minutes_played=minutes,
            matches_played=10,
            source="fbref",
            raw_stats=raw_stats or {},
        )
        db.add(snap)
        db.flush()
        snaps.append(snap)
    return snaps


def _seed_percentiles(
    db: Session,
    snaps: list[StatSnapshot],
    *,
    metric_name: str,
    values: list[float],
    position_group: str = "CM",
    league_tier: str = "tier_1",
) -> None:
    """Create percentile snapshots with given values at each snapshot date."""
    for snap, val in zip(snaps, values, strict=True):
        pct = PercentileSnapshot(
            stat_snapshot_id=snap.id,
            computed_date=snap.scrape_date,
            position_group=position_group,
            league_tier=league_tier,
            metric_name=metric_name,
            percentile_value=val,
            is_published=True,
        )
        db.add(pct)
    db.flush()


# ---------------------------------------------------------------------------
# Tests — Emerging score computation
# ---------------------------------------------------------------------------


class TestEmergingScoreComputation:
    """Unit tests for compute_emerging_scores against hand-calculated data."""

    def test_player_with_strong_upward_trend_scores_above_threshold(self, db):
        """A player whose percentiles rise steadily across 5 snapshots should
        score above SCORE_THRESHOLD (0.50).

        Hand-calculation:
          - 5 snapshots → window_dates = all 5
          - Progressive passes: 50 → 55 → 60 → 65 → 70
            improvement = (70-50) = 20, normalized = 20/100 = 0.20
          - Defensive actions:   40 → 45 → 50 → 55 → 60
            improvement = (60-40) = 20, normalized = 20/100 = 0.20
          - trend_magnitude = (0.20 + 0.20) / 2 = 0.20
          - trend_consistency: both metrics have 4 positive steps (>= ceil(5*0.6)=3) → 1.0
          - age_weight: age 22 → sigmoid(22-24, scale=3) ≈ 0.5498
          - sample_weight: min(2000/900, 1) = 1.0
          - score = 0.45*0.20 + 0.30*1.0 + 0.15*0.55 + 0.10*1.0
                  = 0.09 + 0.30 + 0.0825 + 0.10 = 0.5725  (above 0.50)
        """
        league = _seed_league(db)
        team = _seed_team(db, league)
        player = _seed_player(db, "Emerging Star", team, league, dob="2004-06-15")

        dates = [SNAP_DATE - timedelta(weeks=w) for w in range(4, -1, -1)]
        snaps = _seed_snapshots(db, player, league, dates=dates, minutes=2000)
        _seed_percentiles(
            db, snaps, metric_name="progressive_passes_p90", values=[50, 55, 60, 65, 70]
        )
        _seed_percentiles(
            db, snaps, metric_name="defensive_actions_p90", values=[40, 45, 50, 55, 60]
        )
        _seed_percentiles(
            db, snaps, metric_name="duels_won_pct", values=[30, 35, 40, 45, 50]
        )
        db.commit()

        from app.compute.emerging import compute_emerging_scores

        written = compute_emerging_scores(db, snapshot_date=SNAP_DATE, season=SEASON)
        assert written >= 1

        score_row = (
            db.query(EmergingPlayerScore)
            .filter(EmergingPlayerScore.player_id == player.id)
            .first()
        )
        assert score_row is not None
        assert score_row.score >= 0.50
        assert score_row.contributing_factors["trend_magnitude"] > 0
        assert score_row.contributing_factors["trend_consistency"] > 0

    def test_player_with_flat_trend_scores_below_threshold(self, db):
        """A player with no improvement should stay below the threshold."""
        league = _seed_league(db)
        team = _seed_team(db, league)
        player = _seed_player(db, "Flat Player", team, league, dob="2000-01-01")

        dates = [SNAP_DATE - timedelta(weeks=w) for w in range(4, -1, -1)]
        snaps = _seed_snapshots(db, player, league, dates=dates, minutes=2000)
        # Constant percentiles — no improvement.
        _seed_percentiles(
            db, snaps, metric_name="progressive_passes_p90", values=[50, 50, 50, 50, 50]
        )
        _seed_percentiles(
            db, snaps, metric_name="defensive_actions_p90", values=[40, 40, 40, 40, 40]
        )
        _seed_percentiles(
            db, snaps, metric_name="duels_won_pct", values=[60, 60, 60, 60, 60]
        )
        db.commit()

        from app.compute.emerging import compute_emerging_scores

        written = compute_emerging_scores(db, snapshot_date=SNAP_DATE, season=SEASON)
        assert written == 0

    def test_unqualified_player_excluded(self, db):
        """A player below qualifying minutes should never appear in results."""
        registry = load_registry()
        qm = registry.get("qualifying_minutes", 900)

        league = _seed_league(db)
        team = _seed_team(db, league)
        player = _seed_player(db, "Low Minutes", team, league, dob="2002-01-01")

        dates = [SNAP_DATE - timedelta(weeks=w) for w in range(4, -1, -1)]
        snaps = _seed_snapshots(db, player, league, dates=dates, minutes=qm - 100)
        _seed_percentiles(
            db, snaps, metric_name="progressive_passes_p90", values=[50, 60, 70, 80, 90]
        )
        _seed_percentiles(
            db, snaps, metric_name="defensive_actions_p90", values=[40, 50, 60, 70, 80]
        )
        _seed_percentiles(
            db, snaps, metric_name="duels_won_pct", values=[30, 40, 50, 60, 70]
        )
        db.commit()

        from app.compute.emerging import compute_emerging_scores

        written = compute_emerging_scores(db, snapshot_date=SNAP_DATE, season=SEASON)
        assert written == 0

    def test_idempotent_rerun_replaces_rows(self, db):
        """Running compute twice for the same snapshot_date should replace, not duplicate."""
        league = _seed_league(db)
        team = _seed_team(db, league)
        player = _seed_player(db, "Star", team, league, dob="2003-01-01")

        dates = [SNAP_DATE - timedelta(weeks=w) for w in range(4, -1, -1)]
        snaps = _seed_snapshots(db, player, league, dates=dates, minutes=2000)
        _seed_percentiles(
            db, snaps, metric_name="progressive_passes_p90", values=[50, 60, 70, 80, 90]
        )
        _seed_percentiles(
            db, snaps, metric_name="defensive_actions_p90", values=[40, 50, 60, 70, 80]
        )
        _seed_percentiles(
            db, snaps, metric_name="duels_won_pct", values=[30, 40, 50, 60, 70]
        )
        db.commit()

        from app.compute.emerging import compute_emerging_scores

        compute_emerging_scores(db, snapshot_date=SNAP_DATE, season=SEASON)
        compute_emerging_scores(db, snapshot_date=SNAP_DATE, season=SEASON)

        count = (
            db.query(EmergingPlayerScore)
            .filter(EmergingPlayerScore.player_id == player.id)
            .count()
        )
        assert count == 1

    def test_younger_player_scores_higher_than_older_with_same_trend(self, db):
        """A 21-year-old should score higher than a 28-year-old with identical trend data."""
        league = _seed_league(db)
        team = _seed_team(db, league)

        young = _seed_player(db, "Young Star", team, league, dob="2005-06-15")
        old = _seed_player(db, "Old Pro", team, league, dob="1998-06-15")

        dates = [SNAP_DATE - timedelta(weeks=w) for w in range(4, -1, -1)]
        for p in [young, old]:
            snaps = _seed_snapshots(db, p, league, dates=dates, minutes=2000)
            _seed_percentiles(
                db,
                snaps,
                metric_name="progressive_passes_p90",
                values=[50, 60, 70, 80, 90],
            )
            _seed_percentiles(
                db,
                snaps,
                metric_name="defensive_actions_p90",
                values=[40, 50, 60, 70, 80],
            )
            _seed_percentiles(
                db, snaps, metric_name="duels_won_pct", values=[30, 40, 50, 60, 70]
            )
        db.commit()

        from app.compute.emerging import compute_emerging_scores

        compute_emerging_scores(db, snapshot_date=SNAP_DATE, season=SEASON)

        young_score = (
            db.query(EmergingPlayerScore)
            .filter(EmergingPlayerScore.player_id == young.id)
            .first()
        )
        old_score = (
            db.query(EmergingPlayerScore)
            .filter(EmergingPlayerScore.player_id == old.id)
            .first()
        )
        assert young_score is not None
        assert old_score is not None
        assert young_score.score > old_score.score


class TestLeagueHubAggregation:
    """Tests for get_league_hub_data aggregation."""

    def test_hub_returns_standalone_available_false(self, db):
        """The hub must return standings_available: False (no match data)."""
        league = _seed_league(db)
        _seed_team(db, league, "Team A")
        db.commit()

        from app.queries.league_page_queries import get_league_hub_data

        hub = get_league_hub_data(db, "premier-league")
        assert hub is not None
        assert hub["standings_available"] is False

    def test_hub_returns_empty_when_league_not_found(self, db):
        from app.queries.league_page_queries import get_league_hub_data


        hub = get_league_hub_data(db, "nonexistent-league")
        assert hub is None
