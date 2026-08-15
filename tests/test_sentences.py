"""Data-driven sentence generator tests (Constitution §5).

Grammar, pluralization, ranges, and boundary cases: percentile 0, tiny
samples, league with zero qualifying players, pending qualification, and the
ordinal helper (1st/2nd/3rd/11th/21st...).
"""
from __future__ import annotations

from app.models import Player, StatSnapshot, Team
from app.queries.sentences import build_profile_sentence, ordinal
from tests.conftest import SNAPSHOT_DATE, compute_and_publish

SEASON = "2025-26"


def _seed(db, league, name, group, gls, minutes=1000, **extra):
    team = db.query(Team).filter_by(name="City", league_id=league.id).first()
    if team is None:
        team = Team(name="City", league_id=league.id)
        db.add(team)
        db.flush()
    player = Player(canonical_name=name, position_group=group)
    db.add(player)
    db.flush()
    raw = {
        "si_gls_p90": gls,
        "si_dis_p90": 0.5,
        "si_cmp_pct": 80.0,
        "si_prgp_p90": 1.0,
        "si_prgc_p90": 1.0,
        "si_xag_p90": 0.1,
        "si_kp_p90": 0.5,
        "si_tkl_p90": 0.5,
        "si_int_p90": 0.5,
        "si_press_p90": 5.0,
        "si_sh_p90": 1.0,
        "si_xg_p90": gls * 0.9,
        "_cmp_attempts": 300,
        **extra,
    }
    db.add(
        StatSnapshot(
            player_id=player.id,
            team_id=team.id,
            league_id=league.id,
            season=SEASON,
            scrape_date=SNAPSHOT_DATE,
            source="fbref",
            raw_stats=raw,
            minutes_played=minutes,
            matches_played=12,
            status="ingested",
        )
    )
    db.commit()
    return player


def test_ordinal():
    assert ordinal(1) == "1st"
    assert ordinal(2) == "2nd"
    assert ordinal(3) == "3rd"
    assert ordinal(4) == "4th"
    assert ordinal(11) == "11th"
    assert ordinal(12) == "12th"
    assert ordinal(13) == "13th"
    assert ordinal(21) == "21st"
    assert ordinal(22) == "22nd"
    assert ordinal(87) == "87th"


def test_qualified_player_sentence_grammar(db, premier_league, small_pool):
    """A fully-qualified ST: sentence names the top metric, tier and plural."""
    for name, gls in [("A", 0.2), ("B", 0.4), ("C", 0.6), ("D", 0.8), ("E", 0.9)]:
        _seed(db, premier_league, name, "ST", gls)
    compute_and_publish(db, snapshot_date=SNAPSHOT_DATE, season=SEASON)

    player = db.query(Player).filter_by(canonical_name="E").one()
    sentence = build_profile_sentence(db, player.id)
    assert "ranks in the" in sentence
    assert "among Tier 1 strikers this season" in sentence
    assert "Statlas Index" in sentence
    # grammar: 'strikers' plural, ordinal present
    assert "0.2" not in sentence  # never a fabricated number


def test_pluralization_per_position(db, premier_league, small_pool):
    """GK -> 'goalkeepers', W -> 'wide attackers', CB -> 'centre-backs'."""
    # five per group so each pool clears the min-pool size (5)
    for i in range(5):
        _seed(db, premier_league, f"G{i}", "GK", 0.5,
              si_save_pct=70 + i, si_psxg_ga_p90=0.1 + 0.05 * i,
              si_ga_p90=1.2 - 0.1 * i, si_cross_pct=4 + i,
              _sota_faced=60, _crosses_faced=40)
        _seed(db, premier_league, f"W{i}", "W", 0.5 + 0.1 * i)
        _seed(db, premier_league, f"C{i}", "CB", 0.5 + 0.1 * i)
    compute_and_publish(db, snapshot_date=SNAPSHOT_DATE, season=SEASON)

    expected = {"G0": "goalkeepers", "W0": "wide attackers", "C0": "centre-backs"}
    for name, plural in expected.items():
        player = db.query(Player).filter_by(canonical_name=name).one()
        assert plural in build_profile_sentence(db, player.id)


def test_percentile_zero_boundary(db, premier_league, small_pool):
    """The pool minimum gets the honest 'bottom of the group' phrasing."""
    # A is the bottom of EVERY metric pool (all values scale with gls), so its
    # top percentile is genuinely 0 — the copy must say so honestly.
    for name, gls in [("A", 0.2), ("B", 0.4), ("C", 0.6), ("D", 0.8), ("E", 0.9)]:
        _seed(db, premier_league, name, "ST", gls,
              si_prgp_p90=gls * 3, si_prgc_p90=gls * 3, si_xag_p90=gls * 0.2,
              si_kp_p90=gls * 1.5, si_tkl_p90=gls * 1.5, si_int_p90=gls * 1.5,
              si_press_p90=gls * 10, si_sh_p90=gls * 2, si_cmp_pct=70 + gls * 10,
              si_dis_p90=1.5 - gls * 0.8, si_xg_p90=gls * 0.9)
    compute_and_publish(db, snapshot_date=SNAPSHOT_DATE, season=SEASON)

    player = db.query(Player).filter_by(canonical_name="A").one()  # lowest everywhere
    sentence = build_profile_sentence(db, player.id)
    assert "at the bottom of the group" in sentence
    assert "0th percentile" not in sentence  # no false precision


def test_pending_qualification_sentence(db, premier_league, small_pool):
    """Below-threshold player: pending copy with the real minutes, never a score."""
    player = _seed(db, premier_league, "Sub", "ST", 9.0, minutes=480)
    sentence = build_profile_sentence(db, player.id)
    assert "pending qualification" in sentence
    assert "480 league minutes" in sentence
    assert "Statlas Index" not in sentence


def test_zero_qualifying_players(db, premier_league):
    """League with zero qualifying players -> coverage-honest sentence."""
    player = _seed(db, premier_league, "Only", "ST", 0.5, minutes=100)  # below threshold
    sentence = build_profile_sentence(db, player.id)
    assert "pending qualification" in sentence


def test_no_snapshot_at_all(db, premier_league):
    """A player row with no snapshot -> no fabricated claim."""
    player = Player(canonical_name="Ghost", position_group="ST")
    db.add(player)
    db.commit()
    sentence = build_profile_sentence(db, player.id)
    assert "not in the current data coverage" in sentence


def test_tiny_sample_pool(db, premier_league, small_pool):
    """Pool below minimum size: no percentiles exist -> pending path, honest."""
    for name, gls in [("A", 0.2), ("B", 0.4)]:  # N=2 < min pool (5)
        _seed(db, premier_league, name, "ST", gls)
    compute_and_publish(db, snapshot_date=SNAPSHOT_DATE, season=SEASON)
    player = db.query(Player).filter_by(canonical_name="A").one()
    sentence = build_profile_sentence(db, player.id)
    # no percentile rows were published; must not fabricate a rank
    assert "no published percentile ranks" in sentence
    assert "ranks in the" not in sentence
