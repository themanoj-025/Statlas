"""StatsBomb Open Data sync unit tests — fixture JSON via an injected fetcher
(no network). Asserts event rows are stored and data_coverage is updated so the
UI can never imply coverage that was not actually loaded."""

from __future__ import annotations

import json

from app.sources.statsbomb import StatsBombOpenDataSource
from tests.conftest import fixtures_dir

FIXTURES = fixtures_dir()


def _fixture_fetcher() -> dict[str, str]:
    """A URL->body map exercising the real URL patterns."""
    return {
        "competitions.json": FIXTURES.joinpath("statsbomb_competitions.json").read_text(
            encoding="utf-8"
        ),
        "matches/123/2024.json": FIXTURES.joinpath("statsbomb_matches.json").read_text(
            encoding="utf-8"
        ),
        "events/10001.json": FIXTURES.joinpath("statsbomb_events.json").read_text(
            encoding="utf-8"
        ),
    }


def test_build_event_rows_pure():
    events = json.loads(
        FIXTURES.joinpath("statsbomb_events.json").read_text(encoding="utf-8")
    )
    rows = StatsBombOpenDataSource.build_event_rows(
        events, match_id=10001, competition_id=123, season="2024/2025"
    )
    assert len(rows) == 2
    assert rows[0]["event_type"] == "Shot"
    assert rows[0]["outcome"] == "Goal"
    assert rows[0]["x_coordinate"] == 42.5
    assert rows[0]["y_coordinate"] == 33.2
    assert rows[0]["player_id"] is None  # unmatched until a player-link step runs
    assert rows[1]["event_type"] == "Pass"


def test_sync_competition_stores_events_and_coverage(db):
    urls = _fixture_fetcher()
    source = StatsBombOpenDataSource(fetcher=lambda url: urls[url.split("/data/")[1]])
    competition = json.loads(urls["competitions.json"])[0]

    result = source.sync_competition(db, competition)
    assert result == {"matches": 1, "events": 2}

    from app.models import DataCoverage, MatchEvent

    events = db.query(MatchEvent).all()
    assert len(events) == 2
    assert {e.event_type for e in events} == {"Shot", "Pass"}

    coverage = db.query(DataCoverage).filter_by(source="statsbomb").all()
    assert len(coverage) == 1
    row = coverage[0]
    assert row.source_identifier == "statsbomb:123:2024"
    assert row.seasons_available == ["2024/2025"]
    assert row.status == "active"
    assert row.last_successful_scrape is not None


def test_resync_is_idempotent(db):
    urls = _fixture_fetcher()
    source = StatsBombOpenDataSource(fetcher=lambda url: urls[url.split("/data/")[1]])
    competition = json.loads(urls["competitions.json"])[0]

    source.sync_competition(db, competition)
    source.sync_competition(db, competition)

    from app.models import MatchEvent

    assert db.query(MatchEvent).count() == 2  # no duplicates
