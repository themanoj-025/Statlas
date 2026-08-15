"""API-Football unit tests: fixture parsing and the persistent daily request
budget (the hard stop that prevents quota exhaustion mid-run)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from app.sources.api_football import APIFootballSource, FileBackedBudget
from app.sources.base import BudgetExhaustedError
from tests.conftest import fixtures_dir

FIXTURES = fixtures_dir()


def test_parse_fixtures():
    payload = json.loads(FIXTURES.joinpath("api_football_fixtures.json").read_text(encoding="utf-8"))
    records = APIFootballSource.parse_fixtures(payload, "premier-league", "2025-26")
    assert len(records) == 2
    first = records[0]
    assert first.api_fixture_id == 101010
    assert first.home_team_name == "Arsenal"
    assert first.away_team_name == "Chelsea"
    assert first.status == "NS"
    assert first.kickoff_utc == "2026-08-15T19:30:00+01:00"


def test_build_url():
    assert APIFootballSource.build_url(39, 2025) == (
        "https://v3.football.api-sports.io/fixtures?league=39&season=2025"
    )


def test_budget_hard_stop(tmp_path):
    budget = FileBackedBudget(daily_limit=3, path=tmp_path / "budget.json")
    for _ in range(3):
        budget.acquire()
    assert budget.remaining() == 0
    with pytest.raises(BudgetExhaustedError):
        budget.acquire()


def test_budget_persists_across_instances(tmp_path):
    path = tmp_path / "budget.json"
    first = FileBackedBudget(daily_limit=10, path=path)
    first.acquire()
    first.acquire()
    second = FileBackedBudget(daily_limit=10, path=path)
    assert second.used == 2


def test_budget_rolls_over_next_day(tmp_path):
    path = tmp_path / "budget.json"
    budget = FileBackedBudget(daily_limit=10, path=path)
    budget.acquire()
    # Simulate a stale file from yesterday (UTC day boundary — timezone-policy.md).
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    path.write_text(json.dumps({"day": yesterday, "used": 9}))
    fresh = FileBackedBudget(daily_limit=10, path=path)
    assert fresh.used == 0
    assert fresh.remaining() == 10
