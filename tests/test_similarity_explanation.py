"""Phase 6 similarity-explanation tests (Part B3).

The explanation logic is verified against hand-calculated fixtures — the same
discipline Phase 1 used for the percentile formula. The anchor/candidate
vectors below were designed so threshold membership is unambiguous, and the
expected matched strengths / key differences were computed by hand:

    A = {gls 82, xg 78, sh 74, prgp 71, prgc 73, xag 22, kp 41, tkl 32,
         int 56, press 61, cmp 66, dis 48}
    B = {gls 84, xg 79, sh 76, prgp 30, prgc 75, xag 18, kp 43, tkl 33,
         int 58, press 63, cmp 68, dis 12}

Matched-strength candidates (both >= 70, gap <= 20): gls, xg, sh, prgc.
Ranked by contribution (products: 6888 > 6162 > 5624 > 5475) -> top 3:
gls, xg, sh. prgp is excluded (B = 30 < 70).

Key differences (gap >= 25): prgp (71 - 30 = 41, A stronger),
dis (48 - 12 = 36, A stronger) -> ordered [prgp, dis].

Hand-computed similarity: dot = 41649, ||A|| = sqrt(45360),
||B|| = sqrt(40961)  =>  sim = 41649 / (sqrt(45360) * sqrt(40961)) ~ 0.9662
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from app.config import load_registry
from app.models import PercentileSnapshot, Player, StatSnapshot, Team
from app.queries.similar_players import (
    KEY_DIFFERENCE_MIN_GAP,
    MATCHED_STRENGTH_MAX_DIFF,
    MATCHED_STRENGTH_MIN_PERCENTILE,
    _cosine_with_components,
    build_similarity_explanation,
    get_similar_players,
)
from tests.conftest import SNAPSHOT_DATE

OUTFIELD = load_registry()["outfield_metrics"]

ANCHOR = {
    "si_gls_p90": 82,
    "si_xg_p90": 78,
    "si_sh_p90": 74,
    "si_prgp_p90": 71,
    "si_prgc_p90": 73,
    "si_xag_p90": 22,
    "si_kp_p90": 41,
    "si_tkl_p90": 32,
    "si_int_p90": 56,
    "si_press_p90": 61,
    "si_cmp_pct": 66,
    "si_dis_p90": 48,
}
CANDIDATE = {
    "si_gls_p90": 84,
    "si_xg_p90": 79,
    "si_sh_p90": 76,
    "si_prgp_p90": 30,
    "si_prgc_p90": 75,
    "si_xag_p90": 18,
    "si_kp_p90": 43,
    "si_tkl_p90": 33,
    "si_int_p90": 58,
    "si_press_p90": 63,
    "si_cmp_pct": 68,
    "si_dis_p90": 12,
}


def _seed_vector(db, league, name, values, *, team_name="City"):
    """Seed a player with a hand-set published percentile vector."""
    team = db.query(Team).filter_by(
        name=team_name, league_id=league.id
    ).first() or Team(name=team_name, league_id=league.id)
    db.add(team)
    db.flush()
    player = Player(canonical_name=name, position_group="ST", current_team_id=team.id)
    db.add(player)
    db.flush()
    snap = StatSnapshot(
        player_id=player.id,
        team_id=team.id,
        league_id=league.id,
        season="2025-26",
        scrape_date=SNAPSHOT_DATE,
        source="fbref",
        raw_stats={},
        minutes_played=1000,
        matches_played=12,
        status="ingested",
    )
    db.add(snap)
    db.flush()
    now = datetime.now(timezone.utc)
    for mid, pct in values.items():
        db.add(
            PercentileSnapshot(
                stat_snapshot_id=snap.id,
                computed_date=now,
                position_group="ST",
                league_tier="tier_1",
                metric_name=mid,
                percentile_value=pct,
                index_score=None,
                is_published=True,
            )
        )
    db.commit()
    return player


def _explain(anchor, candidate, group="ST"):
    return build_similarity_explanation(
        anchor, candidate, group=group, registry=load_registry()
    )


# ---------------------------------------------------------------------------
# Hand-calculated fixture — the core contract
# ---------------------------------------------------------------------------


def test_explanation_matches_hand_calculated_fixture():
    exp = _explain(ANCHOR, CANDIDATE)

    # matched strengths: the three largest-contribution metrics where both
    # players rank highly and sit close (hand-verified order gls > xg > sh)
    assert [m["metric"] for m in exp["matched_strengths"]] == [
        "si_gls_p90",
        "si_xg_p90",
        "si_sh_p90",
    ]
    gls = exp["matched_strengths"][0]
    assert gls["player_a_percentile"] == 82
    assert gls["player_b_percentile"] == 84
    assert gls["difference"] == 2
    assert gls["metric_name"] == "Goals per 90"

    # key differences: the two largest gaps, with the stronger player stated
    assert [(m["metric"], m["stronger_player"]) for m in exp["key_differences"]] == [
        ("si_prgp_p90", "player_a"),
        ("si_dis_p90", "player_a"),
    ]
    assert exp["key_differences"][0]["difference"] == 41
    assert exp["key_differences"][1]["difference"] == 36

    # every metric compared; nothing excluded
    assert exp["shared_metrics"] == len(OUTFIELD) == 12
    assert exp["excluded_metrics"] == []
    assert exp["excluded_reason"]


def test_explanation_matches_hand_calculated_similarity():
    _explain(ANCHOR, CANDIDATE)  # smoke: builder runs on the fixture
    expected = 41649 / (math.sqrt(45360) * math.sqrt(40961))
    sim, shared, contributions = _cosine_with_components(
        ANCHOR, CANDIDATE, min_shared_metrics=5
    )
    assert shared == 12
    # hand-computed: dot = 41649, norms sqrt(45360)/sqrt(40961) -> ~0.9662
    assert abs(sim - 0.9662) < 0.001
    # the decomposition is consistent: contributions sum to the score
    assert abs(sum(contributions.values()) - sim) < 0.001
    assert abs(sim - expected) < 0.001


def test_matched_strength_rules_hold_on_fixture():
    exp = _explain(ANCHOR, CANDIDATE)
    for m in exp["matched_strengths"]:
        assert m["player_a_percentile"] >= MATCHED_STRENGTH_MIN_PERCENTILE
        assert m["player_b_percentile"] >= MATCHED_STRENGTH_MIN_PERCENTILE
        assert m["difference"] <= MATCHED_STRENGTH_MAX_DIFF
    # sorted by contribution, descending
    contribs = [m["contribution"] for m in exp["matched_strengths"]]
    assert contribs == sorted(contribs, reverse=True)
    # key differences: every gap >= threshold, ordered largest first
    for m in exp["key_differences"]:
        assert m["difference"] >= KEY_DIFFERENCE_MIN_GAP
    gaps = [m["difference"] for m in exp["key_differences"]]
    assert gaps == sorted(gaps, reverse=True)
    # the top key difference genuinely has the largest gap in the vector
    all_gaps = {mid: abs(ANCHOR[mid] - CANDIDATE[mid]) for mid in OUTFIELD}
    assert exp["key_differences"][0]["difference"] == max(all_gaps.values())


def test_boundary_gap_of_25_is_a_key_difference():
    """Gap exactly at the threshold is a key difference (inclusive boundary)."""
    a = dict(ANCHOR)
    b = dict(CANDIDATE)
    a["si_tkl_p90"] = 60.0
    b["si_tkl_p90"] = 35.0  # gap exactly 25
    exp = _explain(a, b)
    tkl = [m for m in exp["key_differences"] if m["metric"] == "si_tkl_p90"]
    assert tkl and tkl[0]["difference"] == 25
    assert tkl[0]["stronger_player"] == "player_a"


# ---------------------------------------------------------------------------
# Edge cases (A2 / A3)
# ---------------------------------------------------------------------------


def test_no_meaningful_differences_edge_case():
    """All gaps small -> key differences must be empty, not force-ranked."""
    a = {
        "si_gls_p90": 72,
        "si_xg_p90": 70,
        "si_sh_p90": 74,
        "si_prgp_p90": 71,
        "si_prgc_p90": 73,
        "si_xag_p90": 60,
        "si_kp_p90": 58,
        "si_tkl_p90": 55,
        "si_int_p90": 62,
        "si_press_p90": 64,
        "si_cmp_pct": 68,
        "si_dis_p90": 52,
    }
    b = {mid: v + 3 for mid, v in a.items()}
    exp = _explain(a, b)
    assert exp["key_differences"] == []
    assert exp["matched_strengths"]  # matched strengths still reported
    assert exp["excluded_metrics"] == []


def test_no_shared_standout_strengths_edge_case():
    """Mid-range alignment -> matched strengths empty (honest, not padded)."""
    a = {mid: 45.0 for mid in OUTFIELD}
    b = {mid: 48.0 for mid in OUTFIELD}
    exp = _explain(a, b)
    assert exp["matched_strengths"] == []
    assert exp["key_differences"] == []
    assert exp["shared_metrics"] == 12


def test_missing_metric_excluded_from_score_and_explanation():
    """A metric absent for the candidate is excluded everywhere (never a zero)."""
    candidate = {mid: v for mid, v in CANDIDATE.items() if mid != "si_xag_p90"}
    exp = _explain(ANCHOR, candidate)
    assert [e["metric"] for e in exp["excluded_metrics"]] == ["si_xag_p90"]
    assert exp["excluded_metrics"][0]["metric_name"] == "xAG per 90"
    assert exp["shared_metrics"] == 11
    # the excluded metric appears in NEITHER list — not silently treated as a
    # match or a difference
    for item in exp["matched_strengths"] + exp["key_differences"]:
        assert item["metric"] != "si_xag_p90"


def test_similarity_score_matches_explanation_shared_set():
    """The score the UI shows is computed over exactly the shared set."""
    candidate = {mid: v for mid, v in CANDIDATE.items() if mid != "si_xag_p90"}
    sim, shared, _ = _cosine_with_components(ANCHOR, candidate, min_shared_metrics=5)
    exp = _explain(ANCHOR, candidate)
    assert shared == exp["shared_metrics"] == 11
    assert 0 < sim <= 1.0


# ---------------------------------------------------------------------------
# Integration through get_similar_players (the query layer)
# ---------------------------------------------------------------------------


def test_get_similar_players_returns_explanation(db, premier_league):
    anchor = _seed_vector(db, premier_league, "Anchor", ANCHOR)
    _seed_vector(db, premier_league, "Peer", CANDIDATE)

    results = get_similar_players(db, anchor.id, limit=5)
    assert results and results[0]["name"] == "Peer"

    exp = results[0]["explanation"]
    assert exp["shared_metrics"] == 12
    assert [m["metric"] for m in exp["matched_strengths"]] == [
        "si_gls_p90",
        "si_xg_p90",
        "si_sh_p90",
    ]
    assert [(m["metric"], m["stronger_player"]) for m in exp["key_differences"]] == [
        ("si_prgp_p90", "player_a"),
        ("si_dis_p90", "player_a"),
    ]
    # explanation numbers are exactly the seeded percentile values
    gls = exp["matched_strengths"][0]
    assert gls["player_a_percentile"] == ANCHOR["si_gls_p90"]
    assert gls["player_b_percentile"] == CANDIDATE["si_gls_p90"]


def test_get_similar_players_excludes_missing_metric(db, premier_league):
    anchor = _seed_vector(db, premier_league, "Anchor", ANCHOR)
    partial = {mid: v for mid, v in CANDIDATE.items() if mid != "si_xag_p90"}
    _seed_vector(db, premier_league, "Partial", partial)

    results = get_similar_players(db, anchor.id, limit=5)
    exp = results[0]["explanation"]
    assert [e["metric"] for e in exp["excluded_metrics"]] == ["si_xag_p90"]
    assert exp["shared_metrics"] == 11
    assert results[0]["shared_metrics"] == 11


def test_get_similar_players_no_meaningful_differences(db, premier_league):
    a = {mid: 70.0 + i for i, mid in enumerate(OUTFIELD)}
    b = {mid: v + 2 for mid, v in a.items()}
    anchor = _seed_vector(db, premier_league, "Anchor", a)
    _seed_vector(db, premier_league, "Twin", b)

    results = get_similar_players(db, anchor.id, limit=5)
    exp = results[0]["explanation"]
    assert exp["key_differences"] == []
    assert exp["matched_strengths"]  # twin profiles share real strengths
    assert 0 < results[0]["similarity"] <= 1.0
