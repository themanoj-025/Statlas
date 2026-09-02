"""Phase 2 query-layer tests (queries/*):

- Slug generation + collision resolution (name / name-club / name-id).
- Search over canonical names AND reconciliation aliases.
- Similar players (cosine similarity, same cohort, real computation).
- Team queries (roster + squad radar) with the not-enough-players empty case.
"""

from __future__ import annotations

from app.config import load_registry
from app.models import Player, PlayerNameAlias, Team
from app.queries.leaderboard_queries import get_leaderboard_filtered
from app.queries.player_queries import (
    get_player_slug,
    resolve_player_slug,
    search_players,
    slugify_name,
)
from app.queries.similar_players import get_similar_players
from app.queries.team_queries import get_team_profile
from tests.conftest import SNAPSHOT_DATE, compute_and_publish
from tests.test_percentiles import _seed_player  # reuse the proven seeder

SEASON = "2025-26"


def _seed_team(db, league, name: str) -> Team:
    team = Team(name=name, league_id=league.id)
    db.add(team)
    db.commit()
    return team


def test_slugify() -> None:
    assert slugify_name("Erling Haaland") == "erling-haaland"
    assert slugify_name("Kevin De Bruyne") == "kevin-de-bruyne"
    assert slugify_name("  José   Mourinho ") == "jose-mourinho"
    assert slugify_name("Player A") == "player-a"


def test_slug_collision_resolution(db, premier_league) -> None:
    """Two 'Alex Smith's on different clubs: BOTH get club-suffixed slugs
    (site-map §1.1 rule 2 — deterministic, never order-dependent)."""
    city = _seed_team(db, premier_league, "Manchester City")
    united = _seed_team(db, premier_league, "Manchester United")
    a = Player(
        canonical_name="Alex Smith", position_group="ST", current_team_id=city.id
    )
    b = Player(
        canonical_name="Alex Smith", position_group="ST", current_team_id=united.id
    )
    db.add_all([a, b])
    db.commit()

    assert get_player_slug(db, a.id) == "alex-smith-manchester-city"
    assert get_player_slug(db, b.id) == "alex-smith-manchester-united"

    resolved_a = resolve_player_slug(db, "alex-smith-manchester-city")
    assert resolved_a["player_id"] == a.id
    assert resolved_a["canonical"] is True

    resolved_b = resolve_player_slug(db, "alex-smith-manchester-united")
    assert resolved_b["player_id"] == b.id
    assert resolved_b["canonical"] is True

    # the bare name is now ambiguous -> None (never a silent guess)
    assert resolve_player_slug(db, "alex-smith") is None

    # a same-club collision falls back to the numeric id suffix
    c = Player(
        canonical_name="Alex Smith", position_group="ST", current_team_id=city.id
    )
    db.add(c)
    db.commit()
    assert get_player_slug(db, c.id) == f"alex-smith-{c.id}"
    assert resolve_player_slug(db, f"alex-smith-{c.id}")["player_id"] == c.id
    assert resolve_player_slug(db, "nobody-here") is None


def test_search_matches_aliases(db, premier_league) -> None:
    """Alternate spellings resolve through the alias table (B3)."""
    _seed_team(db, premier_league, "City")
    player = Player(
        canonical_name="Kevin De Bruyne",
        position_group="CM",
        current_team_id=db.query(Team).first().id,
    )
    db.add(player)
    db.commit()
    db.add(
        PlayerNameAlias(
            player_id=player.id, source="understat", source_name_string="KDB"
        )
    )
    db.commit()

    hits = search_players(db, "kdb", limit=5)
    assert hits and hits[0]["player_id"] == player.id
    assert hits[0]["club"] == "City"
    assert hits[0]["league"] == "Premier League"

    # no match -> empty
    assert search_players(db, "zzzznope") == []


def test_search_escapes_ilike_wildcards(db, premier_league) -> None:
    """ILIKE wildcards (% and _) in user input are escaped so they are
    treated as literal characters, not pattern metacharacters.

    Without escaping:
    - '%' would match everything (empty LIKE pattern)
    - '_' would match any single character
    """
    _seed_team(db, premier_league, "Test Club")
    # Player with literal % in name (unlikely but possible via aliases)
    player_pct = Player(
        canonical_name="100% Striker",
        position_group="ST",
    )
    player_normal = Player(
        canonical_name="Normal Striker",
        position_group="ST",
    )
    db.add_all([player_pct, player_normal])
    db.commit()

    # Searching for '100%' should match the literal-name player,
    # not return all players (which '%' alone would do unescaped)
    hits = search_players(db, "100%", limit=10)
    player_ids = [h["player_id"] for h in hits]
    assert player_pct.id in player_ids, "Literal % should match, not be a wildcard"
    # 'Normal Striker' should NOT appear — '%' is not a wildcard
    assert player_normal.id not in player_ids

    # Searching for '_' should match literal underscore, not any char
    # Create a player with literal underscore
    player_uscore = Player(
        canonical_name="Player_ASpecial",
        position_group="CM",
    )
    player_uother = Player(
        canonical_name="PlayerBSpecial",
        position_group="CM",
    )
    db.add_all([player_uscore, player_uother])
    db.commit()

    hits = search_players(db, "Player_A", limit=10)
    player_ids = [h["player_id"] for h in hits]
    assert player_uscore.id in player_ids, "Literal _ should match"
    # 'PlayerBSpecial' should NOT appear — '_' is not a single-char wildcard
    assert player_uother.id not in player_ids


def test_similar_players_real_nearest_neighbour(db, premier_league, small_pool) -> None:
    """Cosine similarity is computed from real percentile vectors in-cohort."""
    for name, gls in [("A", 0.2), ("B", 0.4), ("C", 0.6), ("D", 0.8), ("E", 0.9)]:
        _seed_player(db, premier_league, name, "ST", gls)
    compute_and_publish(db, snapshot_date=SNAPSHOT_DATE, season=SEASON)

    a = db.query(Player).filter_by(canonical_name="A").one()

    # A's nearest neighbour is B (closest vector), not E
    similar = get_similar_players(db, a.id, limit=5)
    assert similar, "anchor player has a percentile vector"
    assert all(s["position_group"] == "ST" for s in similar)
    assert all(0 < s["similarity"] <= 1.0 for s in similar)
    assert all(s["shared_metrics"] >= 5 for s in similar)
    assert similar[0]["name"] == "B"

    # a GK in the same test league has no outfield percentile vector:
    # get_similar_players([] result path) — covered by the cohort guard.
    gk = Player(canonical_name="Goalkeeper X", position_group="GK")
    db.add(gk)
    db.commit()
    assert get_similar_players(db, gk.id) == []


def test_leaderboard_filtered_pagination_and_sort(db, premier_league, small_pool) -> None:
    for name, gls in [("A", 0.2), ("B", 0.4), ("C", 0.6), ("D", 0.8), ("E", 0.9)]:
        _seed_player(db, premier_league, name, "ST", gls)
    compute_and_publish(db, snapshot_date=SNAPSHOT_DATE, season=SEASON)

    page1 = get_leaderboard_filtered(
        db,
        metric="si_index",
        season=SEASON,
        league_slugs=["premier-league"],
        position_group="ST",
        limit=3,
        offset=0,
    )
    page2 = get_leaderboard_filtered(
        db,
        metric="si_index",
        season=SEASON,
        league_slugs=["premier-league"],
        position_group="ST",
        limit=3,
        offset=3,
    )
    assert page1["total"] == 5
    assert len(page1["entries"]) == 3
    assert len(page2["entries"]) == 2
    assert page1["has_more"] is True
    assert page2["has_more"] is False
    ids = {e["player_id"] for e in page1["entries"] + page2["entries"]}
    assert len(ids) == 5
    # value sort is descending by default (higher is better)
    values = [e["value"] for e in page1["entries"]]
    assert values == sorted(values, reverse=True)
    # every entry carries a slug for linking
    assert all(e["slug"] for e in page1["entries"])


def test_team_roster_and_squad_radar(db, premier_league, small_pool) -> None:
    for name, gls in [("A", 0.2), ("B", 0.4), ("C", 0.6), ("D", 0.8), ("E", 0.9)]:
        _seed_player(db, premier_league, name, "ST", gls, team_name="City")
    compute_and_publish(db, snapshot_date=SNAPSHOT_DATE, season=SEASON)

    profile = get_team_profile(db, league_slug="premier-league", team_slug="city")
    assert profile is not None
    assert profile["roster_count"] == 5
    assert profile["qualified_count"] == 5
    assert profile["squad_radar"] is not None
    assert profile["squad_radar"]["n_players"] == 5
    assert len(profile["squad_radar"]["metrics"]) == 12  # all outfield metrics
    assert all(0 <= m["avg_pct"] <= 100 for m in profile["squad_radar"]["metrics"])

    # unknown team -> None
    assert get_team_profile(db, league_slug="premier-league", team_slug="nope") is None


def test_team_radar_empty_below_five(db, premier_league, small_pool) -> None:
    for name, gls in [("A", 0.2), ("B", 0.4), ("C", 0.6)]:  # only 3 qualified
        _seed_player(db, premier_league, name, "ST", gls, team_name="City")
    compute_and_publish(db, snapshot_date=SNAPSHOT_DATE, season=SEASON)

    profile = get_team_profile(db, league_slug="premier-league", team_slug="city")
    assert profile["squad_radar"] is None  # the UI renders the explicit empty state


def test_radar_axis_status_partial_data(db, premier_league, small_pool) -> None:
    """Radar axes must carry an honest status per metric — below_floor / no_data
    / unranked_pool are explicit states, never a silently plotted zero (B2)."""
    from app.api.player_view import _axis_status

    registry = load_registry()
    raw_full = {"si_gls_p90": 0.5, "si_cmp_pct": 80.0, "_cmp_attempts": 300}
    raw_below_floor = {"si_cmp_pct": 80.0, "_cmp_attempts": 10}  # < 50 attempts
    raw_missing = {"si_gls_p90": 0.5}  # cmp_pct absent entirely

    # qualified
    assert _axis_status(70.0, 0.5, 1000, raw_full, "si_gls_p90") == "qualified"
    # present but below the sample floor -> below_floor, never a zero
    assert (
        _axis_status(None, 80.0, 1000, raw_below_floor, "si_cmp_pct") == "below_floor"
    )
    # present but under display-floor minutes -> below_floor
    assert _axis_status(None, 0.5, 100, raw_full, "si_gls_p90") == "below_floor"
    # value qualifies but the metric's pool was under the min size -> unranked_pool
    assert _axis_status(None, 0.5, 1000, raw_full, "si_gls_p90") == "unranked_pool"
    # no value at all -> no_data
    assert _axis_status(None, None, 1000, raw_missing, "si_cmp_pct") == "no_data"
    # no published percentiles AND registry threshold sanity
    assert registry["qualifying_minutes"] == 900
