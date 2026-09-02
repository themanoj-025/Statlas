"""Tests for Phase 15 — Transfer Intelligence modules.

Covers:
- Market queries (valuation comparison, undervaluation/overvaluation detection)
- Transfer queries (candidate search, contract scoring)
- Opportunity finder (hidden gems, age opportunities, position scarcity)
- Risk module (valuation confidence, transfer risk)
- Market validation (plausibility checks)
- Market data source (fixture implementation)
- Weekly refresh market data ingestion

Constitution §4: Every data-parsing function has a unit test.
Constitution §7: Testing minimum bar — critical UI paths tested.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import (

    ContractStatus,
    League,
    MarketValuation,
    PercentileSnapshot,
    Player,
    StatSnapshot,
    Team,
)

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_player(
    db: Session,
    *,
    name: str = "Test Player",
    position_group: str = "ST",
    team: Team | None = None,
    dob: datetime | None = None,
) -> Player:
    player = Player(
        canonical_name=name,
        position_group=position_group,
        current_team_id=team.id if team else None,
        date_of_birth=dob,
    )
    db.add(player)
    db.flush()
    return player


def _make_league(
    db: Session, *, slug: str = "premier-league", tier: str = "tier_1"
) -> League:
    league = League(
        slug=slug, name="Premier League", country="England", tier=tier, external_ids={}
    )
    db.add(league)
    db.flush()
    return league


def _make_snapshot(
    db: Session,
    player: Player,
    *,
    minutes: float = 2000,
    scrape_date: datetime | None = None,
    league: League | None = None,
) -> StatSnapshot:
    scrape_date = scrape_date or datetime.now(timezone.utc)
    if league is None:
        league = _make_league(db)
    if player.current_team_id is None:
        team_name = f"Team {player.canonical_name}"
        team = Team(name=team_name, league_id=league.id, external_ids={})
        db.add(team)
        db.flush()
        player.current_team_id = team.id
    snap = StatSnapshot(
        player_id=player.id,
        team_id=player.current_team_id,
        league_id=league.id,
        season="2025-26",
        source="fbref",
        scrape_date=scrape_date,
        raw_stats={},
        minutes_played=minutes,
        matches_played=30,
        status="ingested",
    )
    db.add(snap)
    db.flush()
    return snap


def _make_percentile(
    db: Session,
    snap: StatSnapshot,
    *,
    metric: str = "si_prgp_p90",
    percentile: float = 75.0,
    index_score: float | None = None,
    position_group: str = "ST",
    league_tier: str = "tier_1",
) -> PercentileSnapshot:
    pct = PercentileSnapshot(
        stat_snapshot_id=snap.id,
        metric_name=metric,
        percentile_value=percentile,
        index_score=index_score,
        computed_date=datetime.now(timezone.utc),
        position_group=position_group,
        league_tier=league_tier,
        is_published=True,
    )
    db.add(pct)
    db.flush()
    return pct


def _make_valuation(
    db: Session,
    player: Player,
    *,
    amount: float = 20_000_000,
    source: str = "transfermarkt",
    confidence: str = "medium",
) -> MarketValuation:
    val = MarketValuation(
        player_id=player.id,
        source=source,
        valuation_amount_eur=amount,
        valuation_date=datetime.now(timezone.utc),
        low_range=amount * 0.8,
        high_range=amount * 1.2,
        confidence_level=confidence,
        raw={},
    )
    db.add(val)
    db.flush()
    return val


# ---------------------------------------------------------------------------
# Market queries tests
# ---------------------------------------------------------------------------


class TestAgeAdjustment:
    """Age-adjustment factor computation."""

    def test_peak_age_returns_1_0(self) -> None:
        from app.queries.market_queries import compute_age_adjustment

        # CM peak is 27
        result = compute_age_adjustment(27, "CM")
        assert result == 1.0

    def test_younger_than_peak_returns_less_than_1(self) -> None:
        from app.queries.market_queries import compute_age_adjustment

        result = compute_age_adjustment(21, "CM")
        assert 0.5 <= result < 1.0

    def test_older_than_peak_returns_less_than_1(self) -> None:
        from app.queries.market_queries import compute_age_adjustment

        result = compute_age_adjustment(33, "CM")
        assert 0.4 <= result < 1.0

    def test_different_positions_different_peaks(self) -> None:
        from app.queries.market_queries import compute_age_adjustment

        # GK peaks later (29) than ST (27)
        gk_at_28 = compute_age_adjustment(28, "GK")
        st_at_28 = compute_age_adjustment(28, "ST")
        assert gk_at_28 > st_at_28  # GK still rising, ST past peak

    def test_very_old_player_has_floor(self) -> None:
        from app.queries.market_queries import compute_age_adjustment

        result = compute_age_adjustment(40, "CM")
        assert result >= 0.4  # Floor

    def test_very_young_player_has_floor(self) -> None:
        from app.queries.market_queries import compute_age_adjustment

        result = compute_age_adjustment(16, "CM")
        assert result >= 0.5  # Floor


class TestComputeAgeAtDate:
    """Age computation at a specific date."""

    def test_basic_age(self) -> None:
        from app.queries.market_queries import compute_age_at_date

        dob = datetime(2000, 6, 15, tzinfo=timezone.utc)
        ref = datetime(2026, 8, 19, tzinfo=timezone.utc)
        assert compute_age_at_date(dob, ref) == 26

    def test_birthday_not_yet_passed(self) -> None:
        from app.queries.market_queries import compute_age_at_date

        dob = datetime(2000, 12, 25, tzinfo=timezone.utc)
        ref = datetime(2026, 8, 19, tzinfo=timezone.utc)
        assert compute_age_at_date(dob, ref) == 25

    def test_none_dob(self) -> None:
        from app.queries.market_queries import compute_age_at_date

        assert compute_age_at_date(None, datetime.now(timezone.utc)) is None


class TestStatValueProxy:
    """Stat-based value proxy computation."""

    def test_returns_none_for_missing_player(self, db: Session) -> None:
        from app.queries.market_queries import compute_stat_value_proxy

        assert compute_stat_value_proxy(db, 99999) is None

    def test_returns_none_for_no_snapshots(self, db: Session) -> None:
        from app.queries.market_queries import compute_stat_value_proxy

        player = _make_player(db)
        assert compute_stat_value_proxy(db, player.id) is None

    def test_computes_score_with_data(self, db: Session) -> None:
        from app.queries.market_queries import compute_stat_value_proxy

        player = _make_player(db, dob=datetime(2000, 1, 1, tzinfo=timezone.utc))
        snap = _make_snapshot(db, player, minutes=2000)

        # Create several percentile metrics
        for i, metric in enumerate(["si_prgp_p90", "si_prgc_p90", "si_tkl_p90"]):
            _make_percentile(db, snap, metric=metric, percentile=60 + i * 10)

        # Also create an index score
        _make_percentile(db, snap, metric="si_index", index_score=70.0)

        result = compute_stat_value_proxy(db, player.id)
        assert result is not None
        assert "stat_value_score" in result
        assert "age_adjustment" in result
        assert 0 <= result["stat_value_score"] <= 100


class TestValuationComparison:
    """Valuation comparison framework."""

    def test_returns_none_for_no_market_data(self, db: Session) -> None:
        from app.queries.market_queries import get_valuation_comparison

        player = _make_player(db)
        assert get_valuation_comparison(db, player.id) is None

    def test_returns_none_for_no_stat_data(self, db: Session) -> None:
        from app.queries.market_queries import get_valuation_comparison

        player = _make_player(db)
        _make_valuation(db, player)
        assert get_valuation_comparison(db, player.id) is None

    def test_undervalued_player(self, db: Session) -> None:
        from app.queries.market_queries import get_valuation_comparison

        player = _make_player(db, dob=datetime(2000, 1, 1, tzinfo=timezone.utc))
        snap = _make_snapshot(db, player, minutes=2000)

        # High percentiles
        for metric in ["si_prgp_p90", "si_prgc_p90", "si_tkl_p90", "si_shots_p90"]:
            _make_percentile(db, snap, metric=metric, percentile=80.0)
        _make_percentile(db, snap, metric="si_index", index_score=80.0)

        # Low market value
        _make_valuation(db, player, amount=5_000_000, confidence="high")

        result = get_valuation_comparison(db, player.id)
        assert result is not None
        assert result["label"] == "potentially undervalued"
        assert result["valuation_gap_eur"] > 0
        assert result["explanation"]  # Has an explanation

    def test_overvalued_player(self, db: Session) -> None:
        from app.queries.market_queries import get_valuation_comparison

        player = _make_player(db, dob=datetime(1990, 1, 1, tzinfo=timezone.utc))
        snap = _make_snapshot(db, player, minutes=2000)

        # Low percentiles
        for metric in ["si_prgp_p90", "si_prgc_p90", "si_tkl_p90"]:
            _make_percentile(db, snap, metric=metric, percentile=30.0)
        _make_percentile(db, snap, metric="si_index", index_score=30.0)

        # High market value
        _make_valuation(db, player, amount=80_000_000, confidence="high")

        result = get_valuation_comparison(db, player.id)
        assert result is not None
        assert result["label"] == "potentially overvalued"
        assert result["valuation_gap_eur"] < 0


class TestUndervaluedPlayers:
    """Undervaluation detection across all players."""

    def test_returns_empty_for_no_data(self, db: Session) -> None:
        from app.queries.market_queries import get_undervalued_players

        result = get_undervalued_players(db)
        assert result == []

    def test_finds_undervalued_players(self, db: Session) -> None:
        from app.queries.market_queries import get_undervalued_players

        league = _make_league(db)
        team = Team(name="Test FC", league_id=league.id, external_ids={})
        db.add(team)
        db.flush()

        player = _make_player(
            db, team=team, dob=datetime(2000, 1, 1, tzinfo=timezone.utc)
        )
        snap = _make_snapshot(db, player, minutes=2000, league=league)

        for metric in ["si_prgp_p90", "si_prgc_p90", "si_tkl_p90", "si_shots_p90"]:
            _make_percentile(db, snap, metric=metric, percentile=80.0)
        _make_percentile(db, snap, metric="si_index", index_score=80.0)

        _make_valuation(db, player, amount=5_000_000)

        result = get_undervalued_players(db, threshold=0.2)
        assert len(result) >= 1
        assert result[0]["player_id"] == player.id
        assert result[0]["valuation_gap_pct"] > 0


# ---------------------------------------------------------------------------
# Transfer queries tests
# ---------------------------------------------------------------------------


class TestContractScoring:
    """Contract situation scoring."""

    def test_no_contract_returns_unknown(self, db: Session) -> None:
        from app.queries.transfer_queries import get_contract_situation_score

        player = _make_player(db)
        result = get_contract_situation_score(db, player.id)
        assert result["contract_status"] == "unknown"
        assert result["availability_score"] == 50

    def test_expiring_contract_high_availability(self, db: Session) -> None:
        from app.queries.transfer_queries import get_contract_situation_score

        player = _make_player(db)
        contract = ContractStatus(
            player_id=player.id,
            contract_end_date=datetime.now(timezone.utc) + timedelta(days=200),
            contract_status="expiring_next_season",
            source="transfermarkt",
            snapshot_date=datetime.now(timezone.utc),
            raw={},
        )
        db.add(contract)
        db.flush()

        result = get_contract_situation_score(db, player.id)
        assert result["availability_score"] >= 80
        assert result["contract_status"] == "expiring_next_season"

    def test_long_contract_low_availability(self, db: Session) -> None:
        from app.queries.transfer_queries import get_contract_situation_score

        player = _make_player(db)
        contract = ContractStatus(
            player_id=player.id,
            contract_end_date=datetime.now(timezone.utc) + timedelta(days=1500),
            contract_status="active",
            source="transfermarkt",
            snapshot_date=datetime.now(timezone.utc),
            raw={},
        )
        db.add(contract)
        db.flush()

        result = get_contract_situation_score(db, player.id)
        assert result["availability_score"] <= 40


class TestTransferCandidateSearch:
    """Multi-condition transfer candidate search."""

    def test_returns_empty_for_no_data(self, db: Session) -> None:
        from app.queries.transfer_queries import get_transfer_candidate_search

        result = get_transfer_candidate_search(db)
        assert result["candidates"] == []
        assert result["total"] == 0

    def test_finds_candidates_with_data(self, db: Session) -> None:
        from app.queries.transfer_queries import get_transfer_candidate_search

        player = _make_player(db, dob=datetime(2000, 1, 1, tzinfo=timezone.utc))
        snap = _make_snapshot(db, player, minutes=2000)

        for metric in ["si_prgp_p90", "si_prgc_p90", "si_tkl_p90"]:
            _make_percentile(db, snap, metric=metric, percentile=70.0)
        _make_percentile(db, snap, metric="si_index", index_score=70.0)

        _make_valuation(db, player, amount=15_000_000)

        result = get_transfer_candidate_search(db)
        assert len(result["candidates"]) >= 1
        assert result["candidates"][0]["player_id"] == player.id

    def test_position_filter(self, db: Session) -> None:
        from app.queries.transfer_queries import get_transfer_candidate_search

        league = _make_league(db)
        player_st = _make_player(db, name="Striker", position_group="ST")
        player_gk = _make_player(db, name="Goalkeeper", position_group="GK")

        for p in [player_st, player_gk]:
            snap = _make_snapshot(db, p, minutes=2000, league=league)
            _make_percentile(db, snap, metric="si_index", index_score=70.0)

        result = get_transfer_candidate_search(db, position_group="ST")
        assert len(result["candidates"]) == 1
        assert result["candidates"][0]["name"] == "Striker"


# ---------------------------------------------------------------------------
# Opportunity finder tests
# ---------------------------------------------------------------------------


class TestHiddenGems:
    """Hidden gem detection."""

    def test_returns_empty_for_no_data(self, db: Session) -> None:
        from app.compute.opportunity import detect_hidden_gems

        result = detect_hidden_gems(db)
        assert result == []

    def test_detects_hidden_gem(self, db: Session) -> None:
        from app.compute.opportunity import detect_hidden_gems

        player = _make_player(db, dob=datetime(2000, 1, 1, tzinfo=timezone.utc))
        snap = _make_snapshot(db, player, minutes=2000)

        for metric in ["si_prgp_p90", "si_prgc_p90", "si_tkl_p90", "si_shots_p90"]:
            _make_percentile(db, snap, metric=metric, percentile=80.0)
        _make_percentile(db, snap, metric="si_index", index_score=80.0)

        # Low market value → hidden gem
        _make_valuation(db, player, amount=5_000_000)

        result = detect_hidden_gems(
            db, min_stat_percentile=75, max_market_value=30_000_000
        )
        assert len(result) >= 1
        assert result[0]["player_id"] == player.id
        assert result[0]["opportunity_type"] == "hidden_gem"
        assert result[0]["upside_eur"] > 0

    def test_excludes_high_value_players(self, db: Session) -> None:
        from app.compute.opportunity import detect_hidden_gems

        player = _make_player(db, dob=datetime(2000, 1, 1, tzinfo=timezone.utc))
        snap = _make_snapshot(db, player, minutes=2000)

        for metric in ["si_prgp_p90", "si_prgc_p90", "si_tkl_p90"]:
            _make_percentile(db, snap, metric=metric, percentile=80.0)
        _make_percentile(db, snap, metric="si_index", index_score=80.0)

        # High market value → not a hidden gem
        _make_valuation(db, player, amount=50_000_000)

        result = detect_hidden_gems(
            db, min_stat_percentile=75, max_market_value=30_000_000
        )
        assert len(result) == 0


class TestAgeOpportunities:
    """Age opportunity detection."""

    def test_returns_empty_for_no_data(self, db: Session) -> None:
        from app.compute.opportunity import detect_age_opportunities

        result = detect_age_opportunities(db)
        assert result == []

    def test_detects_young_high_performer(self, db: Session) -> None:
        from app.compute.opportunity import detect_age_opportunities

        player = _make_player(db, dob=datetime(2003, 6, 1, tzinfo=timezone.utc))
        snap = _make_snapshot(db, player, minutes=2000)

        for metric in ["si_prgp_p90", "si_prgc_p90", "si_tkl_p90", "si_shots_p90"]:
            _make_percentile(db, snap, metric=metric, percentile=80.0)
        _make_percentile(db, snap, metric="si_index", index_score=80.0)

        result = detect_age_opportunities(db, max_age=24, min_stat_percentile=75)
        assert len(result) >= 1
        assert result[0]["opportunity_type"] == "age_opportunity"
        assert result[0]["age"] is not None
        assert result[0]["age"] <= 24


class TestPositionScarcity:
    """Position scarcity opportunity detection."""

    def test_returns_empty_for_no_data(self, db: Session) -> None:
        from app.compute.opportunity import detect_position_scarcity_opportunities

        result = detect_position_scarcity_opportunities(db)
        assert result == []

    def test_detects_scarce_position(self, db: Session) -> None:
        from app.compute.opportunity import detect_position_scarcity_opportunities

        # Wingers have a premium factor > 1.0
        player = _make_player(db, position_group="W")
        snap = _make_snapshot(db, player, minutes=2000)

        for metric in ["si_prgp_p90", "si_prgc_p90", "si_tkl_p90"]:
            _make_percentile(db, snap, metric=metric, percentile=75.0)
        _make_percentile(db, snap, metric="si_index", index_score=75.0)

        result = detect_position_scarcity_opportunities(db, min_stat_percentile=70)
        assert len(result) >= 1
        assert result[0]["opportunity_type"] == "position_scarcity"
        assert result[0]["premium_factor"] > 1.0

    def test_excludes_non_scarce_positions(self, db: Session) -> None:
        from app.compute.opportunity import detect_position_scarcity_opportunities

        # Defensive midfielders have premium factor <= 1.0
        player = _make_player(db, position_group="DM")
        snap = _make_snapshot(db, player, minutes=2000)

        for metric in ["si_prgp_p90", "si_prgc_p90", "si_tkl_p90"]:
            _make_percentile(db, snap, metric=metric, percentile=75.0)
        _make_percentile(db, snap, metric="si_index", index_score=75.0)

        result = detect_position_scarcity_opportunities(db, min_stat_percentile=70)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Risk module tests
# ---------------------------------------------------------------------------


class TestValuationConfidence:
    """Valuation confidence scoring."""

    def test_no_data_returns_low(self, db: Session) -> None:
        from app.compute.risk import compute_valuation_confidence

        player = _make_player(db)
        result = compute_valuation_confidence(db, player.id)
        assert result["confidence_level"] == "low"
        assert result["confidence_score"] < 45

    def test_full_data_returns_higher(self, db: Session) -> None:
        from app.compute.risk import compute_valuation_confidence

        league = _make_league(db)
        player = _make_player(db, dob=datetime(2000, 1, 1, tzinfo=timezone.utc))
        _make_snapshot(db, player, minutes=2500, league=league)

        # Multiple valuations
        for i in range(5):
            val = MarketValuation(
                player_id=player.id,
                source="transfermarkt",
                valuation_amount_eur=20_000_000 + i * 1_000_000,
                valuation_date=datetime.now(timezone.utc) - timedelta(days=30 * i),
                confidence_level="high",
                raw={},
            )
            db.add(val)
        db.flush()

        # Contract data
        contract = ContractStatus(
            player_id=player.id,
            contract_end_date=datetime.now(timezone.utc) + timedelta(days=730),
            contract_status="active",
            source="transfermarkt",
            snapshot_date=datetime.now(timezone.utc),
            raw={},
        )
        db.add(contract)
        db.flush()

        result = compute_valuation_confidence(db, player.id)
        assert result["confidence_level"] in ("medium", "high")
        assert result["confidence_score"] >= 45


class TestTransferRisk:
    """Transfer risk assessment."""

    def test_basic_risk_assessment(self, db: Session) -> None:
        from app.compute.risk import compute_transfer_risk

        player = _make_player(db, dob=datetime(2000, 1, 1, tzinfo=timezone.utc))
        result = compute_transfer_risk(db, player.id)

        assert "risk_tier" in result
        assert result["risk_tier"] in ("low", "medium", "high")
        assert "risk_score" in result
        assert 0 <= result["risk_score"] <= 100
        assert isinstance(result["risk_factors"], list)
        assert isinstance(result["mitigation_factors"], list)

    def test_league_upgrade_increases_risk(self, db: Session) -> None:
        from app.compute.risk import compute_transfer_risk

        league = League(
            slug="league-2",
            name="League 2",
            country="England",
            tier="tier_3",
            external_ids={},
        )
        db.add(league)
        db.flush()

        team = Team(name="Small FC", league_id=league.id, external_ids={})
        db.add(team)
        db.flush()

        player = _make_player(
            db, team=team, dob=datetime(2000, 1, 1, tzinfo=timezone.utc)
        )
        result = compute_transfer_risk(db, player.id, target_league_tier="tier_1")

        assert result["risk_score"] > 0
        assert any("tier" in f.lower() for f in result["risk_factors"])


# ---------------------------------------------------------------------------
# Market validation tests
# ---------------------------------------------------------------------------


class TestMarketValidation:
    """Market data validation rules."""

    def test_valid_valuation_passes(self, db: Session) -> None:
        from app.compute.market_validation import validate_valuation

        player = _make_player(db)
        val = MarketValuation(
            player_id=player.id,
            source="transfermarkt",
            valuation_amount_eur=20_000_000,
            valuation_date=datetime.now(timezone.utc),
            low_range=16_000_000,
            high_range=24_000_000,
            confidence_level="medium",
            raw={},
        )
        result = validate_valuation(val, db)
        assert result.is_valid

    def test_negative_valuation_fails(self, db: Session) -> None:
        from app.compute.market_validation import validate_valuation

        player = _make_player(db)
        val = MarketValuation(
            player_id=player.id,
            source="transfermarkt",
            valuation_amount_eur=-1000,
            valuation_date=datetime.now(timezone.utc),
            confidence_level="medium",
            raw={},
        )
        result = validate_valuation(val, db)
        assert not result.is_valid
        assert any("below minimum" in i for i in result.issues)

    def test_implausibly_high_valuation_fails(self, db: Session) -> None:
        from app.compute.market_validation import validate_valuation

        player = _make_player(db)
        val = MarketValuation(
            player_id=player.id,
            source="transfermarkt",
            valuation_amount_eur=1_000_000_000,  # €1B — implausible
            valuation_date=datetime.now(timezone.utc),
            confidence_level="medium",
            raw={},
        )
        result = validate_valuation(val, db)
        assert not result.is_valid
        assert any("exceeds maximum" in i for i in result.issues)

    def test_wide_range_spread_warns(self, db: Session) -> None:
        from app.compute.market_validation import validate_valuation

        player = _make_player(db)
        val = MarketValuation(
            player_id=player.id,
            source="transfermarkt",
            valuation_amount_eur=20_000_000,
            valuation_date=datetime.now(timezone.utc),
            low_range=5_000_000,
            high_range=50_000_000,  # Very wide spread
            confidence_level="low",
            raw={},
        )
        result = validate_valuation(val, db)
        assert any("spread" in i.lower() for i in result.issues)

    def test_future_date_fails(self, db: Session) -> None:
        from app.compute.market_validation import validate_valuation

        player = _make_player(db)
        val = MarketValuation(
            player_id=player.id,
            source="transfermarkt",
            valuation_amount_eur=20_000_000,
            valuation_date=datetime.now(timezone.utc) + timedelta(days=30),
            confidence_level="medium",
            raw={},
        )
        result = validate_valuation(val, db)
        assert not result.is_valid
        assert any("future" in i for i in result.issues)


# ---------------------------------------------------------------------------
# Market data source tests
# ---------------------------------------------------------------------------


class TestFixtureMarketDataSource:
    """Fixture market data source implementation."""

    def test_fetch_valuations_returns_records(self) -> None:
        from app.sources.market_data import FixtureMarketDataSource

        source = FixtureMarketDataSource(seed=42)
        records = source.fetch_valuations([1, 2, 3], as_of=datetime.now(timezone.utc))
        assert len(records) == 3
        assert all(r.player_id in [1, 2, 3] for r in records)
        assert all(r.valuation_amount_eur > 0 for r in records)
        assert all(r.confidence_level in ("high", "medium", "low") for r in records)

    def test_fetch_contracts_returns_records(self) -> None:
        from app.sources.market_data import FixtureMarketDataSource

        source = FixtureMarketDataSource(seed=42)
        records = source.fetch_contracts([1, 2], as_of=datetime.now(timezone.utc))
        assert len(records) == 2
        assert all(
            r.contract_status in ("active", "expiring_next_season") for r in records
        )

    def test_fetch_transfers_returns_empty(self) -> None:
        from app.sources.market_data import FixtureMarketDataSource

        source = FixtureMarketDataSource(seed=42)
        records = source.fetch_transfers(
            since=datetime.now(timezone.utc) - timedelta(days=365)
        )
        assert records == []

    def test_deterministic_with_same_seed(self) -> None:
        from app.sources.market_data import FixtureMarketDataSource

        source1 = FixtureMarketDataSource(seed=42)
        source2 = FixtureMarketDataSource(seed=42)

        records1 = source1.fetch_valuations([1], as_of=datetime.now(timezone.utc))
        records2 = source2.fetch_valuations([1], as_of=datetime.now(timezone.utc))

        assert records1[0].valuation_amount_eur == records2[0].valuation_amount_eur


# ---------------------------------------------------------------------------
# Transfer search presets tests
# ---------------------------------------------------------------------------


class TestTransferPresets:
    """Transfer search presets."""

    def test_presets_have_required_fields(self) -> None:
        from app.queries.transfer_queries import TRANSFER_PRESETS

        assert len(TRANSFER_PRESETS) >= 4  # At least 4 presets
        for preset in TRANSFER_PRESETS:
            assert "id" in preset
            assert "name" in preset
            assert "rationale" in preset
            assert "filters" in preset

    def test_preset_ids_are_unique(self) -> None:
        from app.queries.transfer_queries import TRANSFER_PRESETS

pytestmark = pytest.mark.slow


        ids = [p["id"] for p in TRANSFER_PRESETS]
        assert len(ids) == len(set(ids))
