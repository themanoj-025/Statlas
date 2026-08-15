"""Statlas Index unit tests — verifies the weighted-average formula against
hand calculations and against the worked example in methodology.md §7
(expected index 72.8 for the documented percentile profile)."""
from __future__ import annotations

from app.compute.index import compute_index, verify_index_consistency
from app.config import load_registry
from app.models import PercentileSnapshot, StatSnapshot
from tests.conftest import SNAPSHOT_DATE

# The methodology.md §7 worked example profile (ST weights).
WORKED_EXAMPLE = {
    "si_gls_p90": 88, "si_xg_p90": 82, "si_sh_p90": 71,
    "si_prgp_p90": 55, "si_prgc_p90": 62, "si_xag_p90": 74,
    "si_kp_p90": 68, "si_tkl_p90": 34, "si_int_p90": 41,
    "si_press_p90": 47, "si_cmp_pct": 39, "si_dis_p90": 45,
}


def test_methodology_worked_example_index_is_72_8():
    registry = load_registry()
    score = compute_index(WORKED_EXAMPLE, "ST", registry)
    assert score == 72.8


def test_missing_metric_renormalises_weights():
    """With >= 8 of 12 metrics present, weights renormalise over the present set.
    Present: gls .30, xg .20, sh .10, prgp .05, prgc .05, xag .10, kp .05, tkl .02
    (weight sum .87). Score = sum(w/present_sum * p) = 67.23 / 0.87 = 77.28."""
    registry = load_registry()
    partial = {
        "si_gls_p90": 88, "si_xg_p90": 82, "si_sh_p90": 71, "si_prgp_p90": 55,
        "si_prgc_p90": 62, "si_xag_p90": 74, "si_kp_p90": 68, "si_tkl_p90": 34,
    }
    score = compute_index(partial, "ST", registry)
    assert score == 77.28


def test_too_few_metrics_yields_none():
    """Fewer than 8 of 12 metrics present -> no index (displayed as pending,
    never as a low score)."""
    registry = load_registry()
    assert compute_index({"si_gls_p90": 90, "si_xg_p90": 80}, "ST", registry) is None
    assert compute_index({"si_gls_p90": 90}, "ST", registry) is None


def test_gk_uses_gk_weights():
    registry = load_registry()
    gk = {"si_save_pct": 90, "si_psxg_ga_p90": 80, "si_ga_p90": 70, "si_cross_pct": 60}
    score = compute_index(gk, "GK", registry)
    assert score == round(0.35 * 90 + 0.30 * 80 + 0.20 * 70 + 0.15 * 60, 2) == 78.5


def test_every_position_weight_row_sums_to_one():
    registry = load_registry()
    for group, weights in registry["position_weights"].items():
        assert abs(sum(weights.values()) - 1.0) < 1e-9, f"{group} weights do not sum to 1.0"


def test_verify_index_consistency_flags_discrepancies(db):
    """Stored index rows must equal the recomputation (methodology-as-code
    cannot drift). A corrupted row is reported, not silently accepted."""
    from app.models import Player, Team

    team = Team(name="City", league_id=1)
    db.add(team)
    player = Player(canonical_name="A", position_group="ST")
    db.add(player)
    db.flush()
    snap = StatSnapshot(
        player_id=player.id, team_id=team.id, league_id=1, season="2025-26",
        scrape_date=SNAPSHOT_DATE, source="fbref", raw_stats={}, minutes_played=1000,
        matches_played=10,
    )
    db.add(snap)
    db.flush()

    registry = load_registry()
    for mid, value in WORKED_EXAMPLE.items():
        db.add(
            PercentileSnapshot(
                stat_snapshot_id=snap.id, computed_date=SNAPSHOT_DATE,
                position_group="ST", league_tier="tier_1", metric_name=mid,
                percentile_value=value, index_score=None, is_published=False,
            )
        )
    db.add(
        PercentileSnapshot(
            stat_snapshot_id=snap.id, computed_date=SNAPSHOT_DATE,
            position_group="ST", league_tier="tier_1",
            metric_name=registry["index_metric_id"],
            percentile_value=None, index_score=72.8, is_published=False,
        )
    )
    db.commit()
    assert verify_index_consistency(db, computed_date=SNAPSHOT_DATE) == []

    # corrupt the stored index -> verifier must report it
    index_row = (
        db.query(PercentileSnapshot)
        .filter_by(metric_name=registry["index_metric_id"])
        .one()
    )
    index_row.index_score = 5.0
    db.commit()
    discrepancies = verify_index_consistency(db, computed_date=SNAPSHOT_DATE)
    assert len(discrepancies) == 1
    assert discrepancies[0]["stored"] == 5.0
    assert discrepancies[0]["derived"] == 72.8
