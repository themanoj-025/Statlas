"""Reconciliation unit tests — normalization edge cases (accents, suffixes,
initials), the three match steps, the queue for unmatched records, and manual
resolution writing a permanent alias."""

from __future__ import annotations

from datetime import date

from app.models import Player, PlayerNameAlias, ReconciliationQueue, Team
from app.reconciliation import (
    Reconciler,
    normalize_name,
    resolve_queue_item,
    strip_suffixes,
)
from app.sources.base import RawPlayerStatRecord


def test_normalize_name():
    assert normalize_name("José Mourinho") == "jose mourinho"
    assert normalize_name("K. De Bruyne") == "k de bruyne"
    assert normalize_name("  Míkel  Arteta  ") == "mikel arteta"


def test_strip_suffixes():
    assert strip_suffixes("Erling Haaland Jr.") == "erling haaland"
    assert strip_suffixes("Kylian Mbappé") == "kylian mbappe"
    assert strip_suffixes("Frenkie de Jong") == "frenkie de jong"


def _record(name, team, source="fbref", ext=None, dob=None, **kw):
    return RawPlayerStatRecord(
        source=source,
        season="2025-26",
        league_slug="premier-league",
        player_name=name,
        team_name=team,
        minutes_played=900,
        matches_played=10,
        raw_stats={},
        dob_year=dob,
        external_ids=ext or {},
        **kw,
    )


def test_match_by_external_id(db):
    player = Player(canonical_name="Erling Haaland", external_ids={"fbref": "aaaaaaaa"})
    db.add(player)
    db.commit()
    reconciler = Reconciler(db)
    assert (
        reconciler.match_existing(
            _record("Erling Haaland", "Manchester City", ext={"fbref": "aaaaaaaa"})
        )
        is player
    )


def test_match_by_existing_alias(db):
    player = Player(canonical_name="Erling Haaland")
    db.add(player)
    db.flush()  # player_id must exist before the alias row references it
    db.add(
        PlayerNameAlias(
            player_id=player.id, source="understat", source_name_string="Erling Haaland"
        )
    )
    db.commit()
    reconciler = Reconciler(db)
    # different team spelling, no external id — resolved via the alias row
    assert (
        reconciler.match_existing(
            _record(
                "Erling Haaland", "Man City", source="understat", ext={"understat": 123}
            )
        )
        is player
    )


def test_match_by_exact_name_team_dob(db):
    team = Team(name="Manchester City", league_id=1)
    db.add(team)
    player = Player(
        canonical_name="Erling Haaland",
        date_of_birth=date(2000, 7, 21),
        current_team_id=team.id,
    )
    db.add(player)
    db.commit()
    reconciler = Reconciler(db)
    matched = reconciler.match_existing(
        _record("Erling Haaland", "Manchester City", dob=2000)
    )
    assert matched is player


def test_unmatched_goes_to_queue_and_resolves_permanently(db):
    reconciler = Reconciler(db)
    record = _record("El Bicho", "Al-Nassr", source="understat", ext={"understat": 999})
    assert reconciler.match_existing(record) is None
    reconciler.enqueue(record)
    db.commit()

    item = db.query(ReconciliationQueue).one()
    assert item.status == "pending"

    player = Player(canonical_name="Cristiano Ronaldo")
    db.add(player)
    db.commit()

    resolved = resolve_queue_item(db, item.id, player.id, note="confirmed by agent")
    assert resolved.status == "resolved"

    # permanent alias prevents the same mismatch from recurring
    alias = (
        db.query(PlayerNameAlias)
        .filter_by(player_id=player.id, source="understat")
        .one()
    )
    assert alias.source_name_string == "El Bicho"
    fresh = Reconciler(db)
    assert fresh.match_existing(record) is player


def test_suffix_variation_matches(db):
    team = Team(name="Borussia Dortmund", league_id=1)
    db.add(team)
    player = Player(canonical_name="Erling Haaland", current_team_id=team.id)
    db.add(player)
    db.commit()
    reconciler = Reconciler(db)
    # 'Haaland Jr.' normalizes to the same identity
    assert (
        reconciler.match_existing(_record("Erling Haaland Jr.", "Borussia Dortmund"))
        is player
    )
