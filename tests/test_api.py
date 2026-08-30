"""API layer tests — the FastAPI /api/v1 endpoints (Phase 2).

The app reads the db.py engine (same module the pipeline uses), so these tests
seed through the REAL pipeline (run_weekly_refresh with fixture-backed fakes)
and then exercise the HTTP surface: search, slug resolution, leaderboards,
teams, coverage, meta. Input validation errors are explicit (400), unknowns
are 404s, and the dataset mode is reported honestly.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.config import load_registry
from app.db import create_schema, session_scope
from app.orchestration.weekly_refresh import run_weekly_refresh
from tests.conftest import SNAPSHOT_DATE
from tests.test_integration import FakeFBrefSource, FakeUnderstatSource, _fixtures


pytestmark = pytest.mark.slow
SEASON = "2025-26"


@pytest.fixture()
def api_client():
    """A TestClient over a fresh in-memory DB seeded via the real pipeline."""
    db_module._engine = None
    db_module._session_factory = None
    create_schema()

    registry = load_registry()
    original = (registry["min_pool_size"], registry["qualifying_minutes"])
    registry["min_pool_size"] = 5
    registry["qualifying_minutes"] = 900

    fbref, understat = _fixtures()
    try:
        with session_scope() as db:
            report = run_weekly_refresh(
                db,
                SEASON,
                snapshot_date=SNAPSHOT_DATE,
                league_slugs=["premier-league"],
                fbref_source=FakeFBrefSource(fbref),
                understat_source=FakeUnderstatSource(understat),
            )
            assert report.errors == []
    finally:
        registry["min_pool_size"], registry["qualifying_minutes"] = original

    from app.api.main import app


    with TestClient(app) as client:
        yield client


def test_health_and_meta(api_client):
    health = api_client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["api_version"] == "1.0.0"

    meta = api_client.get("/api/v1/meta")
    assert meta.status_code == 200
    body = meta.json()
    assert body["qualifying_minutes"] == 900
    assert body["index_metric_id"] == "si_index"
    assert len(body["metrics"]) >= 16
    assert body["dataset"]["mode"] == "fixture-demo"
    assert body["position_groups"][0]["code"] == "GK"


def test_search_and_slug_resolution(api_client):
    hits = api_client.get("/api/v1/players/search", params={"q": "Player A"})
    assert hits.status_code == 200
    assert hits.json()[0]["name"] == "Player A"

    player = api_client.get("/api/v1/players/by-slug/player-a")
    assert player.status_code == 200
    body = player.json()
    assert body["player"]["name"] == "Player A"
    assert body["player"]["is_canonical"] is True
    assert len(body["axes"]) == 12
    assert "among Tier 1 strikers this season" in body["sentence"]
    assert body["percentiles"]["index"] is not None
    assert len(body["similar"]) >= 1

    # non-canonical slug (club suffix) still resolves, flagged for a 301
    suffixed = api_client.get("/api/v1/players/by-slug/player-a-manchester-city")
    assert suffixed.status_code == 200
    assert suffixed.json()["player"]["is_canonical"] is False
    assert suffixed.json()["player"]["canonical_slug"] == "player-a"

    assert api_client.get("/api/v1/players/by-slug/does-not-exist").status_code == 404
    assert api_client.get("/api/v1/players/search", params={"q": "zzz"}).json() == []


def test_leaderboard_endpoints(api_client):
    board = api_client.get(
        "/api/v1/leaderboard",
        params={
            "position": "ST",
            "league": "premier-league",
            "metric": "si_index",
            "season": SEASON,
            "limit": 5,
        },
    )
    assert board.status_code == 200
    body = board.json()
    assert body["total"] == 5
    assert len(body["entries"]) == 5
    assert body["entries"][0]["slug"]  # linkable
    values = [e["value"] for e in body["entries"]]
    assert values == sorted(values, reverse=True)

    # validation: unknown position/tier/sort -> explicit 400, not a 500
    assert (
        api_client.get("/api/v1/leaderboard", params={"position": "XX"}).status_code
        == 400
    )
    assert (
        api_client.get("/api/v1/leaderboard", params={"tier": "tier_9"}).status_code
        == 400
    )
    assert (
        api_client.get("/api/v1/leaderboard", params={"sort_by": "nope"}).status_code
        == 400
    )

    tier = api_client.get(
        "/api/v1/leaderboard",
        params={"tier": "tier_1", "metric": "si_index", "limit": 2},
    )
    assert tier.status_code == 200
    assert tier.json()["total"] == 5


def test_team_endpoints(api_client):
    team = api_client.get("/api/v1/clubs/premier-league/manchester-city")
    assert team.status_code == 200
    body = team.json()
    assert body["roster_count"] == 2
    assert body["squad_radar"] is None  # only 2 qualified -> honest empty state
    assert all(r["slug"] for r in body["roster"])

    assert api_client.get("/api/v1/clubs/premier-league/nope").status_code == 404
    assert (
        api_client.get("/api/v1/clubs/not-a-league/manchester-city").status_code == 404
    )


def test_coverage_and_positions(api_client):
    coverage = api_client.get("/api/v1/coverage")
    assert coverage.status_code == 200
    body = coverage.json()
    sources = {row["source"] for row in body["rows"]}
    assert sources == {"fbref", "understat"}
    assert "StatsBomb" in body["attribution"]["statsbomb"]

    positions = api_client.get("/api/v1/positions")
    assert positions.status_code == 200
    st = next(p for p in positions.json() if p["code"] == "ST")
    assert st["qualifying_counts"]["tier_1"] == 5


def test_similar_endpoint(api_client):
    similar = api_client.get("/api/v1/players/1/similar", params={"limit": 3})
    assert similar.status_code == 200
    assert len(similar.json()) >= 1
    assert api_client.get("/api/v1/players/9999/similar").status_code == 404
