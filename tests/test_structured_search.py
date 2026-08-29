"""Phase 8 — structured search test suite.

The most important category is query-translation correctness: multi-condition
AND queries against a hand-calculated synthetic dataset must return exactly the
players that genuinely satisfy every condition (an incorrect AND translation
silently returning wrong players would be a data-integrity bug).

Covered (Part B5 + quality gates):
- hand-verified translation: percentile-only, raw-only, and mixed AND queries
- the always-applied minutes qualification floor (no minutes condition needed)
- missing-metric exclusion (a player without data for a condition metric is
  excluded, never guessed)
- age conditions incl. missing date-of-birth exclusion
- empty-result diagnostics (most-restrictive condition guidance)
- grammar validation: unknown metric/operator/position/tier, OR logic rejected,
  >8 conditions, malformed between, bad percentile ranges
- saved searches: CRUD, free-tier cap with honest upsell, re-run reflects
  CURRENT data (staleness is explicit, never silently cached)
- history: auto-log on execute, retention cap of 50, rerun, cross-user 404
- presets: every curated preset validates against the grammar
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.db import create_schema
from app.models import (
    League,
    PercentileSnapshot,
    Player,
    SearchHistory,
    StatSnapshot,
    Subscription,
    Team,
    User,
)
from app.queries import structured_search as ss

SNAPSHOT_DATE = datetime(2026, 8, 12, 3, 0, 0, tzinfo=timezone.utc)
SEASON = "2025-26"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def make_user(db, email: str = "scout@example.com", plan: str = "free") -> User:
    user = User(email=email, password_hash="x" * 64, plan=plan)
    db.add(user)
    db.commit()
    return user


def make_pro_user(db, email: str = "pro@example.com") -> User:
    user = make_user(db, email, plan="pro")
    db.add(
        Subscription(
            user_id=user.id, plan="pro", stripe_subscription_id="sub_x", status="active"
        )
    )
    db.commit()
    return user


def seed_player(
    db,
    name: str,
    *,
    position: str = "CM",
    minutes: float = 1800.0,
    percentiles: dict[str, float] | None = None,
    index_score: float | None = None,
    dob: str | None = None,
    league: League | None = None,
    team: Team | None = None,
) -> Player:
    """Seed one player with a published snapshot and hand-set percentiles.

    Values are set directly (not via the compute pipeline) so tests can assert
    against hand-calculated expectations — the pipeline's own math is covered
    by tests/test_percentiles.py.
    """
    league = league or db.query(League).first()
    team = team or db.query(Team).first()
    player = Player(
        canonical_name=name,
        position_group=position,
        primary_position=position,
        date_of_birth=datetime.fromisoformat(dob).date() if dob else None,
        external_ids={},
        current_team_id=team.id,
    )
    db.add(player)
    db.flush()
    snap = StatSnapshot(
        player_id=player.id,
        team_id=team.id,
        league_id=league.id,
        season=SEASON,
        scrape_date=SNAPSHOT_DATE,
        source="fbref",
        raw_stats={"si_prgp_p90": 1.0},
        minutes_played=minutes,
        matches_played=int(minutes / 90),
        status="published",
    )
    db.add(snap)
    db.flush()
    # The index row defines the published population (execute_structured_query
    # always includes it in the needed-metric set).
    db.add(
        PercentileSnapshot(
            stat_snapshot_id=snap.id,
            computed_date=SNAPSHOT_DATE,
            position_group=position,
            league_tier=league.tier,
            metric_name="si_index",
            percentile_value=None,
            index_score=index_score,
            is_published=True,
        )
    )
    for metric, value in (percentiles or {}).items():
        db.add(
            PercentileSnapshot(
                stat_snapshot_id=snap.id,
                computed_date=SNAPSHOT_DATE,
                position_group=position,
                league_tier=league.tier,
                metric_name=metric,
                percentile_value=value,
                index_score=None,
                is_published=True,
            )
        )
    db.commit()
    return player


@pytest.fixture()
def search_data(db):
    """One free + one pro user, one tier-1 league/team, and a hand-designed
    population of 6 players:

    name   pos  min    prgp%  tkl%   index  dob
    A      CM   2000   80     70     85     2005-06-01  (age 21)
    B      CM   1500   75     65     78     2002-01-01  (age 24)
    C      CM    800   95     90     92     2006-03-15  (age 20, BELOW floor)
    D      DM   1800   40     95     88     2001-09-09  (age 24)
    E      CM   1200   MISS   60     70     None        (missing prgp row)
    F      CM   1000   20     30     55     2008-11-30  (age 17)

    Hand-checked expectations used throughout:
    - prgp >= 70 AND tkl >= 60 (CM only): A, B  -> exactly 2
    - minutes >= 1500 (no position filter): A, B, D -> 3
    - prgp >= 50 AND minutes >= 1500: A, B -> 2
    - tkl >= 50 (no minutes condition): A, B, D, E -> 4 (C is below the floor)
    - prgp >= 90: 0 (C qualifies but is below the floor) -> diagnostics
    """
    free = make_user(db, "free@example.com")
    pro = make_pro_user(db, "pro@example.com")
    league = League(
        slug="test-league",
        name="Test League",
        country="England",
        tier="tier_1",
        external_ids={},
    )
    db.add(league)
    db.commit()
    team = Team(name="Test FC", league_id=league.id, external_ids={})
    db.add(team)
    db.commit()

    seed_player(
        db,
        "Player A",
        position="CM",
        minutes=2000,
        percentiles={"si_prgp_p90": 80, "si_tkl_p90": 70},
        index_score=85,
        dob="2005-06-01",
        league=league,
        team=team,
    )
    seed_player(
        db,
        "Player B",
        position="CM",
        minutes=1500,
        percentiles={"si_prgp_p90": 75, "si_tkl_p90": 65},
        index_score=78,
        dob="2002-01-01",
        league=league,
        team=team,
    )
    seed_player(
        db,
        "Player C",
        position="CM",
        minutes=800,
        percentiles={"si_prgp_p90": 95, "si_tkl_p90": 90},
        index_score=92,
        dob="2006-03-15",
        league=league,
        team=team,
    )
    seed_player(
        db,
        "Player D",
        position="DM",
        minutes=1800,
        percentiles={"si_prgp_p90": 40, "si_tkl_p90": 95},
        index_score=88,
        dob="2001-09-09",
        league=league,
        team=team,
    )
    # Player E deliberately has NO si_prgp_p90 percentile row.
    seed_player(
        db,
        "Player E",
        position="CM",
        minutes=1200,
        percentiles={"si_tkl_p90": 60},
        index_score=70,
        dob=None,
        league=league,
        team=team,
    )
    seed_player(
        db,
        "Player F",
        position="CM",
        minutes=1000,
        percentiles={"si_prgp_p90": 20, "si_tkl_p90": 30},
        index_score=55,
        dob="2008-11-30",
        league=league,
        team=team,
    )
    return {"free": free, "pro": pro}


def qd(conditions, **extra):
    base = {"conditions": conditions, "condition_logic": "AND"}
    base.update(extra)
    return base


def names(result) -> list[str]:
    return [e["name"] for e in result["entries"]]


# ---------------------------------------------------------------------------
# Query translation correctness (the critical category)
# ---------------------------------------------------------------------------


def test_multi_condition_and_translation(db, search_data):
    """prgp >= 70 AND tkl >= 60, CM only — hand-verified: A, B exactly."""
    result = ss.execute_structured_query(
        db,
        qd(
            [
                {"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70},
                {"metric": "si_tkl_p90", "operator": "percentile_gte", "value": 60},
            ],
            position_group="CM",
        ),
        user_id=None,
        log_history=False,
    )
    assert result["total"] == 2
    assert names(result) == ["Player A", "Player B"]
    # Every result carries the actual values behind each condition — the
    # transparency requirement (why each result matched).
    for entry in result["entries"]:
        by_metric = {cv["metric"]: cv for cv in entry["condition_values"]}
        assert by_metric["si_prgp_p90"]["actual"] >= 70
        assert by_metric["si_tkl_p90"]["actual"] >= 60
        assert by_metric["si_prgp_p90"]["condition_type"] == "percentile"


def test_raw_value_condition_minutes(db, search_data):
    """minutes >= 1500 with no position filter — A, B, D."""
    result = ss.execute_structured_query(
        db,
        qd([{"metric": "minutes_played", "operator": "gte", "value": 1500}]),
        user_id=None,
        log_history=False,
    )
    assert result["total"] == 3
    assert set(names(result)) == {"Player A", "Player B", "Player D"}
    entry = result["entries"][0]
    cv = entry["condition_values"][0]
    assert cv["condition_type"] == "raw"
    assert cv["actual"] >= 1500


def test_mixed_percentile_and_raw_query(db, search_data):
    """prgp >= 70 (percentile) AND minutes >= 1500 (raw) — A, B."""
    result = ss.execute_structured_query(
        db,
        qd(
            [
                {"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70},
                {"metric": "minutes_played", "operator": "gte", "value": 1500},
            ]
        ),
        user_id=None,
        log_history=False,
    )
    assert result["total"] == 2
    assert set(names(result)) == {"Player A", "Player B"}


def test_percentile_lte_and_between(db, search_data):
    result = ss.execute_structured_query(
        db,
        qd(
            [
                {"metric": "si_prgp_p90", "operator": "percentile_lte", "value": 50},
                {
                    "metric": "si_tkl_p90",
                    "operator": "percentile_between",
                    "value": 60,
                    "value_max": 100,
                },
            ]
        ),
        user_id=None,
        log_history=False,
    )
    # prgp <= 50: D (40) only — F has prgp 20 but tkl 30 fails between.
    assert result["total"] == 1
    assert names(result) == ["Player D"]


def test_minutes_floor_always_applied(db, search_data):
    """tkl >= 50 with NO minutes condition — C (800 min, tkl 90) must still be
    excluded by the always-applied 900-minute qualification floor."""
    result = ss.execute_structured_query(
        db,
        qd([{"metric": "si_tkl_p90", "operator": "percentile_gte", "value": 50}]),
        user_id=None,
        log_history=False,
    )
    assert result["total"] == 4  # A, B, D, E — never C
    assert "Player C" not in names(result)
    assert result["qualifying_minutes"] == 900
    assert "qualification floor" in result["note"]


def test_missing_metric_excludes_player(db, search_data):
    """Player E has no prgp percentile row — cannot satisfy a prgp condition."""
    result = ss.execute_structured_query(
        db,
        qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 50}]),
        user_id=None,
        log_history=False,
    )
    assert "Player E" not in names(result)
    assert result["total"] == 2  # A, B — C below floor, D prgp 40, F prgp 20


def test_age_max_with_missing_dob_excluded(db, search_data):
    """age_max 23 + tkl >= 60 — only A (21). E has no DOB and is excluded,
    D/B are 24, C is below the floor, F fails tkl."""
    result = ss.execute_structured_query(
        db,
        qd(
            [{"metric": "si_tkl_p90", "operator": "percentile_gte", "value": 60}],
            age_max=23,
        ),
        user_id=None,
        log_history=False,
    )
    assert names(result) == ["Player A"]


def test_empty_result_diagnostics_identify_restrictive_condition(db, search_data):
    """prgp >= 90 returns 0 (C qualifies but is below the floor) — the response
    must include per-condition pass counts and the most-restrictive condition
    so the UI can give actionable guidance instead of a bare 'no results'."""
    result = ss.execute_structured_query(
        db,
        qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 90}]),
        user_id=None,
        log_history=False,
    )
    assert result["total"] == 0
    assert result["entries"] == []
    diag = result["diagnostics"]
    assert diag is not None
    assert diag["most_restrictive"]["metric"] == "si_prgp_p90"
    assert diag["most_restrictive"]["passing_count"] == 0
    # metric display name comes from the registry (D1 consistency).
    assert diag["most_restrictive"]["metric_name"] == "Progressive passes per 90"


def test_position_group_list_and_tier_filter(db, search_data):
    result = ss.execute_structured_query(
        db,
        qd(
            [{"metric": "si_tkl_p90", "operator": "percentile_gte", "value": 60}],
            position_group=["CM", "DM"],
            league_tier="tier_1",
        ),
        user_id=None,
        log_history=False,
    )
    assert result["total"] == 4  # A, B, D, E
    result = ss.execute_structured_query(
        db,
        qd(
            [{"metric": "si_tkl_p90", "operator": "percentile_gte", "value": 60}],
            position_group=["CM", "DM"],
            league_tier="tier_2",
        ),
        user_id=None,
        log_history=False,
    )
    assert result["total"] == 0


def test_sort_by_index_default_and_metric(db, search_data):
    r1 = ss.execute_structured_query(
        db,
        qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 50}]),
        user_id=None,
        log_history=False,
        sort_by="index",
    )
    # A (85) before B (78) — default index sort, descending.
    assert names(r1) == ["Player A", "Player B"]
    r2 = ss.execute_structured_query(
        db,
        qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 50}]),
        user_id=None,
        log_history=False,
        sort_by="minutes",
        sort_dir="asc",
    )
    assert names(r2) == ["Player B", "Player A"]  # 1500 then 2000


def test_pagination(db, search_data):
    result = ss.execute_structured_query(
        db,
        qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 50}]),
        user_id=None,
        log_history=False,
        limit=1,
        offset=1,
    )
    assert result["total"] == 2
    assert result["has_more"] is False
    assert len(result["entries"]) == 1
    assert result["entries"][0]["name"] == "Player B"


# ---------------------------------------------------------------------------
# Grammar validation (Part A1 — reject, never silently reinterpret)
# ---------------------------------------------------------------------------


def test_or_logic_rejected_with_documented_message(db, search_data):
    with pytest.raises(ss.InvalidQuery) as excinfo:
        ss.execute_structured_query(
            db,
            qd(
                [{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70}],
                condition_logic="OR",
            ),
            user_id=None,
            log_history=False,
        )
    assert "AND-only" in str(excinfo.value)


def test_unknown_metric_rejected(db, search_data):
    with pytest.raises(ss.InvalidQuery) as excinfo:
        ss.execute_structured_query(
            db,
            qd([{"metric": "goals_above_expected_xyz", "operator": "gte", "value": 1}]),
            user_id=None,
            log_history=False,
        )
    assert "Metric Registry" in str(excinfo.value)


def test_bad_operator_for_minutes_rejected(db, search_data):
    with pytest.raises(ss.InvalidQuery):
        ss.execute_structured_query(
            db,
            qd(
                [
                    {
                        "metric": "minutes_played",
                        "operator": "percentile_gte",
                        "value": 70,
                    }
                ]
            ),
            user_id=None,
            log_history=False,
        )


def test_percentile_out_of_range_rejected(db, search_data):
    with pytest.raises(ss.InvalidQuery):
        ss.execute_structured_query(
            db,
            qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 120}]),
            user_id=None,
            log_history=False,
        )


def test_between_requires_value_max(db, search_data):
    with pytest.raises(ss.InvalidQuery) as excinfo:
        ss.execute_structured_query(
            db,
            qd([{"metric": "si_prgp_p90", "operator": "between", "value": 50}]),
            user_id=None,
            log_history=False,
        )
    assert "value_max" in str(excinfo.value)


def test_max_conditions_enforced(db, search_data):
    many = [{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 50}] * (
        ss.MAX_CONDITIONS + 1
    )
    with pytest.raises(ss.InvalidQuery) as excinfo:
        ss.execute_structured_query(db, qd(many), user_id=None, log_history=False)
    assert "at most 8" in str(excinfo.value)


def test_unknown_position_and_tier_rejected(db, search_data):
    with pytest.raises(ss.InvalidQuery):
        ss.execute_structured_query(
            db, qd([], position_group="XYZ"), user_id=None, log_history=False
        )
    with pytest.raises(ss.InvalidQuery):
        ss.execute_structured_query(
            db,
            qd(
                [{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 50}],
                league_tier="tier_9",
            ),
            user_id=None,
            log_history=False,
        )


def test_empty_conditions_rejected(db, search_data):
    with pytest.raises(ss.InvalidQuery):
        ss.execute_structured_query(db, qd([]), user_id=None, log_history=False)


# ---------------------------------------------------------------------------
# Saved searches — CRUD, staleness, cap, authorization
# ---------------------------------------------------------------------------


def test_save_list_run_delete(db, search_data):
    user = search_data["free"]
    saved = ss.save_search(
        db,
        user.id,
        "U23 progressive midfielders",
        qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70}]),
        description="Looking for the next press-resistant 8",
    )
    assert saved["condition_count"] == 1
    assert saved["last_run_at"] is None

    listed = ss.list_saved_searches(db, user.id)
    assert [s["name"] for s in listed] == ["U23 progressive midfielders"]

    ran = ss.run_saved_search(db, user.id, saved["search_id"])
    assert ran["saved"]["last_run_at"] is not None
    assert ran["results"]["total"] == 2

    ss.delete_saved_search(db, user.id, saved["search_id"])
    assert ss.list_saved_searches(db, user.id) == []


def test_saved_search_rerun_reflects_current_data(db, search_data):
    """A saved search re-run against changed data must return the NEW results
    (the weekly refresh is explicit — never silently cached/stale)."""
    user = search_data["free"]
    saved = ss.save_search(
        db,
        user.id,
        "Progressors",
        qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70}]),
    )
    first = ss.run_saved_search(db, user.id, saved["search_id"])
    assert first["results"]["total"] == 2

    # The dataset changes (a new player qualifies).
    seed_player(
        db,
        "Player G",
        position="CM",
        minutes=1900,
        percentiles={"si_prgp_p90": 85, "si_tkl_p90": 55},
        index_score=81,
        dob="2003-04-04",
    )
    second = ss.run_saved_search(db, user.id, saved["search_id"])
    assert second["results"]["total"] == 3
    assert "Player G" in names(second["results"])
    # The saved payload reports the fresh run timestamp.
    assert second["saved"]["last_run_at"] is not None


def test_saved_search_requires_name(db, search_data):
    with pytest.raises(ss.InvalidQuery):
        ss.save_search(
            db,
            search_data["free"].id,
            "   ",
            qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70}]),
        )


def test_free_tier_saved_search_cap(db, search_data):
    user = search_data["free"]
    max_saved = 5
    for i in range(max_saved):
        ss.save_search(
            db,
            user.id,
            f"Search {i}",
            qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70}]),
        )
    with pytest.raises(ss.SearchLimitExceeded) as excinfo:
        ss.save_search(
            db,
            user.id,
            "One too many",
            qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70}]),
        )
    assert "Upgrade to Pro" in str(excinfo.value)


def test_cross_user_saved_search_404(db, search_data):
    free, pro = search_data["free"], search_data["pro"]
    saved = ss.save_search(
        db,
        free.id,
        "Private search",
        qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70}]),
    )
    with pytest.raises(ss.SearchNotFound):
        ss.run_saved_search(db, pro.id, saved["search_id"])
    with pytest.raises(ss.SearchNotFound):
        ss.delete_saved_search(db, pro.id, saved["search_id"])
    # Pro's own list is empty — nothing leaked.
    assert ss.list_saved_searches(db, pro.id) == []


# ---------------------------------------------------------------------------
# History — auto-log, retention cap, rerun, authorization
# ---------------------------------------------------------------------------


def test_execute_logs_history_automatically(db, search_data):
    user = search_data["free"]
    ss.execute_structured_query(
        db,
        qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70}]),
        user_id=user.id,
        log_history=True,
    )
    history = ss.get_search_history(db, user.id)
    assert len(history) == 1
    assert history[0]["result_count"] == 2
    assert "Progressive passes per 90" in history[0]["summary"]
    assert "≥ 70th pct" in history[0]["summary"]


def test_history_not_logged_without_user_or_log_flag(db, search_data):
    user = search_data["free"]
    # Anonymous execution (no user_id) must not log to anyone's history.
    ss.execute_structured_query(
        db,
        qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70}]),
        user_id=None,
        log_history=True,
    )
    # Explicit opt-out must not log either.
    ss.execute_structured_query(
        db,
        qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70}]),
        user_id=user.id,
        log_history=False,
    )
    assert ss.get_search_history(db, user.id) == []


def test_history_retention_cap(db, search_data):
    user = search_data["free"]
    for _ in range(ss.HISTORY_CAP + 5):
        ss.execute_structured_query(
            db,
            qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70}]),
            user_id=user.id,
            log_history=True,
        )
    history = ss.get_search_history(db, user.id, limit=100)
    assert len(history) == ss.HISTORY_CAP
    assert db.query(SearchHistory).count() == ss.HISTORY_CAP


def test_rerun_history_entry_logs_new_row(db, search_data):
    user = search_data["free"]
    ss.execute_structured_query(
        db,
        qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70}]),
        user_id=user.id,
    )
    history = ss.get_search_history(db, user.id)
    reran = ss.rerun_history_entry(db, user.id, history[0]["history_id"])
    assert reran["results"]["total"] == 2
    assert reran["reran"]["history_id"] == history[0]["history_id"]
    assert len(ss.get_search_history(db, user.id)) == 2  # new entry logged


def test_cross_user_history_404(db, search_data):
    free, pro = search_data["free"], search_data["pro"]
    ss.execute_structured_query(
        db,
        qd([{"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70}]),
        user_id=free.id,
    )
    history = ss.get_search_history(db, free.id)
    with pytest.raises(ss.SearchNotFound):
        ss.rerun_history_entry(db, pro.id, history[0]["history_id"])
    assert ss.get_search_history(db, pro.id) == []


# ---------------------------------------------------------------------------
# Presets (Part D — every curated preset must validate and run)
# ---------------------------------------------------------------------------


def test_all_presets_validate_and_execute(db, search_data):
    presets = ss.list_presets()
    assert len(presets) >= 6
    for preset in presets:
        assert preset["id"] and preset["name"] and preset["rationale"]
        # Each preset must execute without error against the synthetic set
        # (real-result validation happens in scripts/validate_search_presets.py).
        result = ss.execute_structured_query(
            db, preset["query_definition"], user_id=None, log_history=False
        )
        assert "total" in result


def test_preset_summarize_query(db):
    assert (
        ss.summarize_query(
            {
                "position_group": ["CM"],
                "league_tier": "tier_1",
                "age_max": 23,
                "conditions": [
                    {"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 70}
                ],
            }
        )
        == "CM · Tier 1 · U23 · Progressive passes per 90 ≥ 70th pct"
    )


# ---------------------------------------------------------------------------
# API level — auth, error mapping, honest upsell
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    db_module._engine = None
    db_module._session_factory = None
    create_schema()
    with TestClient(app) as c:
        yield c


from app.api.main import app


def _register(client, email: str = "api-scout@example.com"):
    resp = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "Hunter2hunter!"}
    )
    assert resp.status_code == 201, resp.text


def _seed_api_player(db):
    league = League(
        slug="test-league",
        name="Test League",
        country="England",
        tier="tier_1",
        external_ids={},
    )
    db.add(league)
    db.commit()
    team = Team(name="Test FC", league_id=league.id, external_ids={})
    db.add(team)
    db.commit()
    seed_player(
        db,
        "API Player",
        position="CM",
        minutes=2000,
        percentiles={"si_prgp_p90": 80},
        index_score=85,
        league=league,
        team=team,
    )


def test_api_execute_public_and_history_requires_signin(client):
    # Execution is public (signed-out users can build queries)...
    resp = client.post(
        "/api/v1/search/execute",
        json={
            "query_definition": {
                "conditions": [
                    {"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 50}
                ],
                "condition_logic": "AND",
            },
            "log_history": False,
        },
    )
    assert resp.status_code == 400  # no data seeded yet -> season error
    # ...but saved searches and history are authenticated.
    assert client.get("/api/v1/search/saved").status_code == 401
    assert client.get("/api/v1/search/history").status_code == 401


def test_api_save_run_delete_and_free_gate(client, db):
    with db_module.session_scope() as session:
        _seed_api_player(session)
    _register(client)

    resp = client.post(
        "/api/v1/search/saved",
        json={
            "name": "API saved search",
            "description": "via the API",
            "query_definition": {
                "conditions": [
                    {"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 50}
                ],
                "condition_logic": "AND",
            },
        },
    )
    assert resp.status_code == 201, resp.text
    search_id = resp.json()["search_id"]

    resp = client.post(f"/api/v1/search/saved/{search_id}/run", json={})
    assert resp.status_code == 200, resp.text
    assert resp.json()["results"]["total"] == 1

    # Free-tier upsell: create the 5 cap, then attempt a 6th -> honest 403.
    for i in range(4):
        client.post(
            "/api/v1/search/saved",
            json={
                "name": f"Extra {i}",
                "query_definition": {
                    "conditions": [
                        {
                            "metric": "si_prgp_p90",
                            "operator": "percentile_gte",
                            "value": 50,
                        }
                    ],
                    "condition_logic": "AND",
                },
            },
        )
    resp = client.post(
        "/api/v1/search/saved",
        json={
            "name": "Sixth",
            "query_definition": {
                "conditions": [
                    {"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 50}
                ],
                "condition_logic": "AND",
            },
        },
    )
    assert resp.status_code == 403
    body = resp.json()
    msg = body.get("detail") or body.get("error", {}).get("message", "")
    assert "Upgrade to Pro" in msg

    assert client.delete(f"/api/v1/search/saved/{search_id}").status_code == 200


def test_api_invalid_query_400_and_cross_user_404(client, db):
    with db_module.session_scope() as session:
        _seed_api_player(session)
    _register(client, "first@example.com")

    # Grammar violation -> specific 400 message.
    resp = client.post(
        "/api/v1/search/execute",
        json={
            "query_definition": {
                "conditions": [
                    {"metric": "not_a_metric", "operator": "gte", "value": 1}
                ],
                "condition_logic": "AND",
            },
            "log_history": False,
        },
    )
    assert resp.status_code == 400
    body = resp.json()
    msg = body.get("detail") or body.get("error", {}).get("message", "")
    assert "Metric Registry" in msg

    # Save under user one, then attempt access as user two -> 404 not 403.
    saved = client.post(
        "/api/v1/search/saved",
        json={
            "name": "First user's search",
            "query_definition": {
                "conditions": [
                    {"metric": "si_prgp_p90", "operator": "percentile_gte", "value": 50}
                ],
                "condition_logic": "AND",
            },
        },
    ).json()["search_id"]

    client.post("/api/v1/auth/logout")
    _register(client, "second@example.com")
    resp = client.post(f"/api/v1/search/saved/{saved}/run", json={})
    assert resp.status_code == 404
    assert client.delete(f"/api/v1/search/saved/{saved}").status_code == 404


def test_api_presets_public(client):
    resp = client.get("/api/v1/search/presets")
    assert resp.status_code == 200
    assert len(resp.json()["presets"]) >= 6
