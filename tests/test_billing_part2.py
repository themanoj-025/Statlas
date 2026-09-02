"""Phase 4 — Part A6: billing + auth test suite.

Runs entirely against a fake Stripe client (no live keys — the real client is
lazy-imported and key-gated), but the WEBHOOK SIGNATURE path uses the real
stripe library's Webhook.construct_event with a generated test secret, so the
D3 "unsigned/tampered payload is rejected" guarantee is tested genuinely.

Covers the mandatory Part A6 scenarios:
- successful checkout grants access (optimistic path + webhook confirmation)
- payment failed -> grace period (access retained) -> recovery
- payment failed -> grace period -> cancellation (access revoked)
- plan changes via customer.subscription.updated
- webhook idempotency (same event twice -> no duplicate effects) — Part 2."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.api.main import app
from app.db import create_schema, session_scope
from app.models import Subscription, User, WebhookEvent


def test_payment_failed_then_cancellation_revokes(client) -> None:
    register_user(client)
    with session_scope() as db:
        user_id = db.query(User).filter(User.email == "scout@example.com").first().id
    _grant_pro(client, user_id)

    raw, sig = signed_event(payment_failed_event("sub_test_grace"))
    client.post(
        "/api/v1/billing/webhook", content=raw, headers={"stripe-signature": sig}
    )

    # Cancellation -> end-of-period retention: access persists until period
    # end, then is revoked. Simulate with a current_period_end already past.
    past = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
    raw, sig = signed_event(
        subscription_updated_event("sub_test_grace", "canceled", past)
    )
    resp = client.post(
        "/api/v1/billing/webhook", content=raw, headers={"stripe-signature": sig}
    )
    assert resp.status_code == 200
    assert client.get("/api/v1/auth/me").json()["has_pro"] is False  # revoked


def test_canceled_keeps_access_to_period_end(client) -> None:
    """End-of-period retention: canceled with a future period_end still grants."""
    register_user(client)
    with session_scope() as db:
        user_id = db.query(User).filter(User.email == "scout@example.com").first().id
    _grant_pro(client, user_id)

    future = int((datetime.now(timezone.utc) + timedelta(days=10)).timestamp())
    raw, sig = signed_event(
        subscription_updated_event("sub_test_grace", "canceled", future)
    )
    client.post(
        "/api/v1/billing/webhook", content=raw, headers={"stripe-signature": sig}
    )
    assert client.get("/api/v1/auth/me").json()["has_pro"] is True  # until period end


# ---------------------------------------------------------------------------
# Access gating (A4): the single has_pro_access function
# ---------------------------------------------------------------------------


def test_limits_report_plan_boundaries(client) -> None:
    register_user(client)
    resp = client.get("/api/v1/billing/limits")
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "free"
    assert body["limits"]["leaderboard_rows"] == 50
    assert body["limits"]["comparisons_per_day"] == 3

    # Upgrade -> limits flip to Pro values.
    with session_scope() as db:
        user = db.query(User).filter(User.email == "scout@example.com").first()
        user.plan = "pro"
        db.add(
            Subscription(
                user_id=user.id,
                plan="pro",
                stripe_subscription_id="sub_x",
                status="active",
            )
        )
        db.commit()
    resp = client.get("/api/v1/billing/limits")
    assert resp.json()["plan"] == "pro"
    assert resp.json()["limits"]["leaderboard_rows"] is None  # unlimited
    assert resp.json()["limits"]["assistant_queries_per_period"] == 200


def test_billing_configured_flag(client) -> None:
    register_user(client)
    body = client.get("/api/v1/billing/subscription").json()
    assert body["billing_configured"] is True  # env keys present in this suite


# ---------------------------------------------------------------------------
# Registration rate limiting (5 per IP per 10 minutes)
# ---------------------------------------------------------------------------


def test_register_rate_limit_allows_under_threshold(client) -> None:
    """First 5 registrations from the same IP should all succeed."""
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": f"user{i}@example.com", "password": "Hunter2hunter!"},
        )
        assert resp.status_code == 201, f"Registration {i + 1} should succeed"


def test_register_rate_limit_blocks_over_threshold(client) -> None:
    """6th registration from the same IP should be rate-limited (429)."""
    # Exhaust the limit
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": f"rate{i}@example.com", "password": "Hunter2hunter!"},
        )
        assert resp.status_code == 201

    # 6th attempt should be blocked
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "rate5@example.com", "password": "Hunter2hunter!"},
    )
    assert resp.status_code == 429
    assert "Too many" in resp.json()["error"]["message"]


def test_register_rate_limit_resets_after_clear(client) -> None:
    """After clearing rate limit state, registrations should succeed again."""
    # Exhaust the limit
    for i in range(5):
        client.post(
            "/api/v1/auth/register",
            json={"email": f"clear{i}@example.com", "password": "Hunter2hunter!"},
        )

    # Should be blocked
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "clear5@example.com", "password": "Hunter2hunter!"},
    )
    assert resp.status_code == 429

    # Clear the rate limiter (simulates time passing)
    from app.rate_limiting import get_rate_limiter

    limiter = get_rate_limiter()
    limiter.reset_all()

    # Should succeed again
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "clear6@example.com", "password": "Hunter2hunter!"},
    )
    assert resp.status_code == 201


def test_register_rate_limit_independent_of_email(client) -> None:
    """Rate limit is per IP, not per email — different emails from same IP count."""
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"unique{i}@example.com",
                "password": "Hunter2hunter!",
            },
        )
        assert resp.status_code == 201

    # Even a different email is blocked (same IP)
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "another@example.com", "password": "Hunter2hunter!"},
    )
    assert resp.status_code == 429


def test_register_rate_limit_error_message(client) -> None:
    """Rate limit response includes a clear error message."""
    for i in range(5):
        client.post(
            "/api/v1/auth/register",
            json={"email": f"msg{i}@example.com", "password": "Hunter2hunter!"},
        )

    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "msg5@example.com", "password": "Hunter2hunter!"},
    )
    assert resp.status_code == 429
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "http_429"
    assert isinstance(body["error"]["message"], str)
    assert len(body["error"]["message"]) > 0


# ---------------------------------------------------------------------------
# Change-password rate limiting (5 per user per 10 min)
# ---------------------------------------------------------------------------


def test_change_password_rate_limit(client) -> None:
    """Change password endpoint should be rate-limited after 5 attempts."""
    register_user(client)

    # 5 failed attempts (wrong current password) should all return 400
    for _i in range(5):
        resp = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "wrongpass", "new_password": "NewPass123!"},
        )
        assert resp.status_code == 400

    # 6th attempt should be rate-limited (429)
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrongpass", "new_password": "NewPass123!"},
    )
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "http_429"


def test_change_password_succeeds_under_limit(client) -> None:
    """Successful password change within rate limit should work."""
    register_user(client)
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Hunter2hunter!", "new_password": "NewPass123!"},
    )
    assert resp.status_code == 200
    assert "Password changed" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Verify-email rate limiting (5 per user per hour)
# ---------------------------------------------------------------------------


def test_verify_email_rate_limit(client) -> None:
    """Verify email endpoint should be rate-limited after 5 requests."""
    register_user(client)
    body = {"email": "scout@example.com"}

    for _i in range(5):
        resp = client.post("/api/v1/auth/verify-email/request", json=body)
        assert resp.status_code == 200

    # 6th request should be rate-limited
    resp = client.post("/api/v1/auth/verify-email/request", json=body)
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "http_429"


# ---------------------------------------------------------------------------
# Stripe redirect URL validation (open redirect prevention)
# ---------------------------------------------------------------------------


def test_checkout_rejects_external_redirect(client) -> None:
    """success_url pointing to a different domain must be rejected."""
    register_user(client)
    resp = client.post(
        "/api/v1/billing/checkout",
        json={"success_url": "https://evil.com/steal", "cancel_url": "/cancel"},
    )
    assert resp.status_code == 400
    assert "domain" in resp.json()["error"]["message"].lower()


def test_checkout_rejects_double_slash_redirect(client) -> None:
    """URLs like //evil.com are protocol-relative and must be rejected."""
    register_user(client)
    resp = client.post(
        "/api/v1/billing/checkout",
        json={"success_url": "//evil.com/steal", "cancel_url": "/ok"},
    )
    assert resp.status_code == 400


def test_checkout_allows_relative_redirect(client, monkeypatch) -> dict[str, object]:
    """Relative paths like /success are always safe."""
    register_user(client)
    # Mock Stripe to avoid real API calls
    import app.billing as _billing


    created = {}

    class FakeSession:
        @staticmethod
        def create(**kwargs) -> dict[str, object]:
            created.update(kwargs)
            return {"url": "https://checkout.stripe.com/test", "id": "cs_test"}

    class FakeCheckout:
        Session = FakeSession

    class FakeCustomer:
        @staticmethod
        def create(**kwargs) -> dict[str, object]:
            return {"id": "cus_test"}

    class FakeStripe:
        checkout = FakeCheckout()
        Customer = FakeCustomer

    fake_stripe = FakeStripe()
    monkeypatch.setattr(_billing, "_stripe_client", lambda: fake_stripe)
    monkeypatch.setattr(_billing, "_current_sub", lambda db, uid: None)

    resp = client.post(
        "/api/v1/billing/checkout",
        json={"success_url": "/success", "cancel_url": "/cancel"},
    )
    # URL passed validation (200 = checkout session created)
    assert resp.status_code == 200
    assert created["success_url"] == "/success"
    assert created["cancel_url"] == "/cancel"
