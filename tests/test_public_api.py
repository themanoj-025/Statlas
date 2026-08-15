"""Phase 4 — Part C: public API tests.

- Key storage is hashed (SHA-256), never plaintext — the raw key exists once.
- Key auth resolves bearer tokens; revoked keys fail.
- Rotation mints a new key and revokes the old.
- Rate limits come from pricing.json per plan, with X-RateLimit-* headers.
- Free/pro plans without API access get an explicit 403 (honest gating).
"""

from __future__ import annotations

import os

os.environ["STRIPE_SECRET_KEY"] = "sk_test_dummy_for_signature_tests"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_dummy_webhook_secret"

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.auth import hash_token
from app.config import load_registry
from app.db import create_schema, session_scope
from app.models import ApiKey, User
from app.orchestration.weekly_refresh import run_weekly_refresh
from tests.conftest import SNAPSHOT_DATE
from tests.test_integration import FakeFBrefSource, FakeUnderstatSource, _fixtures

SEASON = "2025-26"


@pytest.fixture()
def seeded_client():
    """Seeded DB (players with published percentiles) + signed-in user."""
    db_module._engine = None
    db_module._session_factory = None
    create_schema()

    registry = load_registry()
    original = (registry["min_pool_size"], registry["qualifying_minutes"])
    registry["min_pool_size"] = 5
    registry["qualifying_minutes"] = 900

    fbref, understat = _fixtures()
    with session_scope() as db:
        run_weekly_refresh(
            db,
            SEASON,
            snapshot_date=SNAPSHOT_DATE,
            fbref_source=FakeFBrefSource(fbref),
            understat_source=FakeUnderstatSource(understat),
        )
    registry["min_pool_size"], registry["qualifying_minutes"] = original

    from app.api.main import app

    with TestClient(app) as c:
        c.post("/api/v1/auth/register", json={"email": "dev@example.com", "password": "hunter2hunter"})
        yield c


def create_key(client) -> str:
    resp = client.post("/api/v1/keys", json={"name": "ci-pipeline"})
    assert resp.status_code == 201, resp.text
    return resp.json()["key"]


def make_api_business(client):
    """Upgrade the signed-in user to api_business (key rate limits apply)."""
    with session_scope() as db:
        user = db.query(User).filter(User.email == "dev@example.com").first()
        user.plan = "api_business"
        db.commit()


def test_key_created_with_one_time_reveal_and_hashed_storage(seeded_client):
    raw = create_key(seeded_client)
    assert raw.startswith("sl_")
    with session_scope() as db:
        row = db.query(ApiKey).first()
        assert row is not None
        # Stored value is the hash — the raw key is NOT in the DB (D3).
        assert row.key_hash == hash_token(raw)
        assert row.key_hash != raw  # the plaintext never touches the DB
    # List endpoint shows prefixes only, never the raw key.
    listed = seeded_client.get("/api/v1/keys").json()["keys"]
    assert listed[0]["prefix"].startswith("sl_")
    assert "key" not in listed[0]


def test_key_auth_resolves_and_serves_real_data(seeded_client):
    make_api_business(seeded_client)
    raw = create_key(seeded_client)
    resp = seeded_client.get(
        "/api/v1/public/players/1/percentiles",
        headers={"Authorization": f"Bearer {raw}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["player"] is not None
    assert body["player"]["player_id"] == 1
    assert "percentiles" in body
    # Rate-limit headers present per Part C1.
    assert resp.headers["x-ratelimit-remaining"] is not None
    assert resp.headers["x-ratelimit-limit"] is not None


def test_public_endpoints_require_key(seeded_client):
    resp = seeded_client.get("/api/v1/public/players/1/percentiles")
    assert resp.status_code == 401


def test_revoked_key_fails(seeded_client):
    raw = create_key(seeded_client)
    key_id = seeded_client.get("/api/v1/keys").json()["keys"][0]["id"]
    resp = seeded_client.delete(f"/api/v1/keys/{key_id}")
    assert resp.status_code == 200
    resp = seeded_client.get(
        "/api/v1/public/players/1/percentiles",
        headers={"Authorization": f"Bearer {raw}"},
    )
    assert resp.status_code == 401
    assert "revoked" in resp.json()["detail"].lower()


def test_rotate_mints_new_key_and_revokes_old(seeded_client):
    make_api_business(seeded_client)
    old_raw = create_key(seeded_client)
    key_id = seeded_client.get("/api/v1/keys").json()["keys"][0]["id"]
    resp = seeded_client.post(f"/api/v1/keys/{key_id}/rotate", json={})
    assert resp.status_code == 200
    new_raw = resp.json()["key"]
    assert new_raw != old_raw

    # Old key dead, new key live.
    assert (
        seeded_client.get(
            "/api/v1/public/players/1/percentiles",
            headers={"Authorization": f"Bearer {old_raw}"},
        ).status_code
        == 401
    )
    assert (
        seeded_client.get(
            "/api/v1/public/players/1/percentiles",
            headers={"Authorization": f"Bearer {new_raw}"},
        ).status_code
        == 200
    )


def test_rate_limit_headers_and_403_for_non_api_plan(seeded_client):
    # Free plan: public API not included -> explicit 403, not silence.
    raw = create_key(seeded_client)
    resp = seeded_client.get(
        "/api/v1/public/players/1/percentiles",
        headers={"Authorization": f"Bearer {raw}"},
    )
    assert resp.status_code == 403
    assert "api business" in resp.json()["detail"].lower()


def test_rate_limit_429_after_cap(seeded_client):
    make_api_business(seeded_client)
    raw = create_key(seeded_client)
    from app.api import public_views

    original = public_views._WINDOW
    public_views._WINDOW = 60
    try:
        # api_business allows 120/min — exceed via a temporarily clamped cap.
        import app.config as config_mod

        pricing = config_mod.load_pricing()
        api_plan = pricing["plans"]["api_business"]["limits"]
        orig_rpm = api_plan["api_rate_limit_per_minute"]
        # The loaded pricing dict is a shared cached object — mutation is
        # visible to plan_limits without clearing the lru cache (clearing would
        # re-read the file from disk and lose the override).
        api_plan["api_rate_limit_per_minute"] = 3
        # Fresh key so prior hits cannot leak into this window.
        from app.api import public_views

        public_views._hits.clear()
        try:
            for _ in range(3):
                resp = seeded_client.get(
                    "/api/v1/public/players/1/percentiles",
                    headers={"Authorization": f"Bearer {raw}"},
                )
                assert resp.status_code == 200, resp.text
            resp = seeded_client.get(
                "/api/v1/public/players/1/percentiles",
                headers={"Authorization": f"Bearer {raw}"},
            )
            assert resp.status_code == 429
        finally:
            api_plan["api_rate_limit_per_minute"] = orig_rpm
    finally:
        public_views._WINDOW = original


def test_leaderboard_public_endpoint(seeded_client):
    make_api_business(seeded_client)
    raw = create_key(seeded_client)
    resp = seeded_client.get(
        "/api/v1/public/leaderboard",
        params={"metric": "si_gls_p90", "league": "premier-league"},
        headers={"Authorization": f"Bearer {raw}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["metric"] == "si_gls_p90"
    assert body["league"] == "premier-league"
    assert isinstance(body["rows"], list)
