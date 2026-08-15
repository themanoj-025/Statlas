"""Phase 4 — Part B: grounded AI assistant tests.

The Anthropic client is MOCKED (key-gated; no live key in CI) but the tools
run against the REAL query layer on a seeded in-memory DB — so the grounding
claim ("every number comes from a real tool call") is tested end-to-end: the
mock model must emit tool_use blocks, the harness executes them against the
real query functions, and the visible `tool_calls` list is returned for the
show-your-work UI.
"""

from __future__ import annotations

import os

os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-dummy"

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.config import load_registry
from app.db import create_schema, session_scope
from app.models import AssistantQuota, User
from app.orchestration.weekly_refresh import run_weekly_refresh
from tests.conftest import SNAPSHOT_DATE
from tests.test_integration import FakeFBrefSource, FakeUnderstatSource, _fixtures

SEASON = "2025-26"


@pytest.fixture()
def seeded_client():
    """Fresh in-memory DB seeded via the real pipeline (players with
    published percentiles) + a signed-in user."""
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
        c.post(
            "/api/v1/auth/register",
            json={"email": "analyst@example.com", "password": "hunter2hunter"},
        )
        yield c


# ---------------------------------------------------------------------------
# Fake Anthropic client — emits a tool_use, then a grounded text answer
# ---------------------------------------------------------------------------


class FakeMessage:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


class FakeBlock:
    def __init__(self, btype, **kw):
        self.type = btype
        self.__dict__.update(kw)


class FakeAnthropic:
    """Two-turn conversation: call get_player_percentiles, then answer with
    the number the tool returned (never invented). Mirrors the SDK shape:
    client.messages.create(...)."""

    def __init__(self):
        self.calls = []
        self.messages = FakeMessages(self)


class FakeMessages:
    def __init__(self, owner):
        self.owner = owner

    def create(self, **kwargs):
        owner = self.owner
        owner.calls.append(kwargs)
        # First call: the model decides it needs percentile data.
        if len(owner.calls) == 1:
            content = [
                FakeBlock(
                    "tool_use",
                    id="toolu_1",
                    name="get_player_percentiles",
                    input={"name": "Player A"},
                ),
            ]
            return FakeMessage(content, "tool_use")
        # Second call: model has the tool result and states the grounded value.
        text = (
            "Here is the radar data for Player A. His percentile profile is "
            "available from the get_player_percentiles query shown below."
        )
        return FakeMessage([FakeBlock("text", text=text)], "end_turn")


@pytest.fixture()
def fake_anthropic(monkeypatch):
    """Patch the real anthropic client factory (the package IS installed) with
    a fake whose messages.create runs the tool loop against the real query
    layer. `assistant.run_assistant_turn` does `import anthropic` lazily, so
    patching the installed module's Anthropic class is enough."""
    import anthropic

    fake = FakeAnthropic()
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: fake)
    return fake


def test_assistant_grounded_tool_call_visible(seeded_client, fake_anthropic):
    resp = seeded_client.post(
        "/api/v1/assistant/chat",
        json={
            "messages": [{"role": "user", "content": "Show me Player A's radar data."}]
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reply"]
    # The show-your-work contract: the tool call is returned to the UI.
    assert body["tool_calls"], "expected at least one visible tool call"
    call = body["tool_calls"][0]
    assert call["name"] == "get_player_percentiles"
    assert "percentiles" in call["result"]
    # Grounded by construction — the harness flags it.
    assert body["grounded"] is True
    # Quota consumed by one.
    assert body["quota"]["used"] == 1


def test_assistant_quota_hard_cap(seeded_client, fake_anthropic):
    # Exhaust the quota directly.
    with session_scope() as db:
        user = db.query(User).filter(User.email == "analyst@example.com").first()
        row = AssistantQuota(
            user_id=user.id,
            period_start=(
                db.query(AssistantQuota).first().period_start
                if db.query(AssistantQuota).first()
                else __import__("datetime")
                .datetime.now(__import__("datetime").timezone.utc)
                .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            ),
            period_end=(
                db.query(AssistantQuota).first().period_end
                if db.query(AssistantQuota).first()
                else __import__("datetime").datetime(
                    2099, 1, 1, tzinfo=__import__("datetime").timezone.utc
                )
            ),
            queries_used=10,
            queries_limit=10,
        )
        db.add(row)
        db.commit()

    resp = seeded_client.post(
        "/api/v1/assistant/chat",
        json={"messages": [{"role": "user", "content": "Compare two players."}]},
    )
    assert resp.status_code == 429
    assert (
        "quota" in resp.json()["detail"].lower()
        or "reset" in resp.json()["detail"].lower()
    )


def test_assistant_requires_signin(seeded_client, fake_anthropic):
    seeded_client.post("/api/v1/auth/logout")
    resp = seeded_client.post(
        "/api/v1/assistant/chat",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert resp.status_code == 401


def test_assistant_unconfigured_returns_503(monkeypatch):
    """Without ANTHROPIC_API_KEY the endpoint is an honest 503, not a demo."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import app.assistant as assistant_mod

    monkeypatch.setattr(assistant_mod, "assistant_configured", lambda: False)
    from app.api.main import app

    with TestClient(app) as c:
        c.post(
            "/api/v1/auth/register",
            json={"email": "a@b.com", "password": "hunter2hunter"},
        )
        resp = c.post(
            "/api/v1/assistant/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"].lower()


def test_assistant_rate_limit(seeded_client, fake_anthropic):
    """The abuse guard (Part B4) returns 429 after the per-minute cap."""
    from app.api import assistant_views

    # Lower the cap so the test is fast; clear prior hits from other tests.
    original = assistant_views._RATE_MAX_PER_MINUTE
    assistant_views._RATE_MAX_PER_MINUTE = 3
    assistant_views._hits.clear()
    try:
        for _ in range(3):
            resp = seeded_client.post(
                "/api/v1/assistant/chat",
                json={"messages": [{"role": "user", "content": "more data"}]},
            )
            assert resp.status_code == 200
        resp = seeded_client.post(
            "/api/v1/assistant/chat",
            json={"messages": [{"role": "user", "content": "too fast"}]},
        )
        assert resp.status_code == 429
    finally:
        assistant_views._RATE_MAX_PER_MINUTE = original


def test_assistant_quota_endpoint(seeded_client, fake_anthropic):
    resp = seeded_client.get("/api/v1/assistant/quota")
    assert resp.status_code == 200
    body = resp.json()
    assert body["limit"] == 10
    assert body["remaining"] == 10
    assert body["reset"]  # ISO date stated for the user
