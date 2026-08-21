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
- webhook idempotency (same event twice -> no duplicate effects)
"""

from __future__ import annotations

import hashlib
import hmac
import json

# --- configure Stripe test keys BEFORE importing the app ----------------------
import os
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.db import create_schema, session_scope
from app.models import Subscription, User, WebhookEvent

os.environ["STRIPE_SECRET_KEY"] = "sk_test_dummy_for_signature_tests"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_dummy_webhook_secret"
os.environ["STRIPE_PRICE_PRO_MONTHLY"] = "price_test_pro_monthly"
os.environ["STRIPE_BILLING_PORTAL_ENABLED"] = "true"

from app.api.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# Test-mode webhook signature helper (real construct_event path)
# ---------------------------------------------------------------------------


def signed_event(payload: dict) -> tuple[bytes, str]:
    """Produce (raw_body, Stripe-Signature header) for a test-mode event using
    the real stripe.webhook signing algorithm against the test secret."""

    secret = os.environ["STRIPE_WEBHOOK_SECRET"]
    raw = json.dumps(payload).encode("utf-8")
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{raw.decode('utf-8')}"
    signature = hmac.new(
        secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    header = f"t={timestamp},v1={signature}"
    return raw, header


def make_event(event_id: str, event_type: str, obj: dict) -> dict:
    return {"id": event_id, "type": event_type, "data": {"object": obj}}


@pytest.fixture()
def client():
    """A TestClient over a fresh in-memory DB (billing tables included)."""
    db_module._engine = None
    db_module._session_factory = None
    create_schema()
    with TestClient(app) as c:
        yield c


def register_user(client, email: str = "scout@example.com") -> None:
    resp = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "Hunter2hunter"}
    )
    assert resp.status_code == 201, resp.text


def checkout_completed_event(user_id: int, sub_id: str = "sub_test_123") -> dict:
    return make_event(
        "evt_checkout_completed",
        "checkout.session.completed",
        {
            "id": "cs_test_abc",
            "subscription": sub_id,
            "metadata": {"statlas_user_id": str(user_id), "plan": "pro"},
        },
    )


def payment_failed_event(sub_id: str) -> dict:
    return make_event(
        "evt_payment_failed",
        "invoice.payment_failed",
        {"id": "in_test_1", "subscription": sub_id},
    )


def subscription_deleted_event(sub_id: str) -> dict:
    return make_event(
        "evt_sub_deleted",
        "customer.subscription.deleted",
        {"id": sub_id},
    )


def subscription_updated_event(sub_id: str, status: str, period_end: int) -> dict:
    return make_event(
        "evt_sub_updated",
        "customer.subscription.updated",
        {"id": sub_id, "status": status, "current_period_end": period_end},
    )


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_register_login_logout_roundtrip(client):
    register_user(client)
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "scout@example.com"
    assert resp.json()["has_pro"] is False

    client.post("/api/v1/auth/logout")
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401  # session revoked

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "scout@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401  # bad password rejected

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "scout@example.com", "password": "Hunter2hunter"},
    )
    assert resp.status_code == 200
    assert client.get("/api/v1/auth/me").json()["email"] == "scout@example.com"


def test_duplicate_email_rejected(client):
    register_user(client)
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "scout@example.com", "password": "Anotherpass1"},
    )
    assert resp.status_code == 409


def test_password_stored_hashed_not_plaintext(client):
    register_user(client)
    with session_scope() as db:
        user = db.query(User).filter(User.email == "scout@example.com").first()
        assert user is not None
        assert "Hunter2hunter" not in user.password_hash
        assert user.password_hash.count("$") == 2  # iterations$salt$hash
    resp = client.get("/api/v1/billing/subscription")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Checkout (A2)
# ---------------------------------------------------------------------------


def test_checkout_requires_signin(client):
    resp = client.post(
        "/api/v1/billing/checkout",
        json={"success_url": "http://x/ok", "cancel_url": "http://x/c"},
    )
    assert resp.status_code == 401


def test_checkout_creates_session_and_grants_on_webhook(client, monkeypatch):
    register_user(client)
    created = {}

    class FakeCheckoutSession:
        @staticmethod
        def create(**kwargs):
            created.update(kwargs)
            return {"url": "https://checkout.stripe.com/test", "id": "cs_test_fake"}

    class FakeCustomer:
        @staticmethod
        def create(**kwargs):
            return {"id": "cus_test_1"}

    import stripe

    monkeypatch.setattr(stripe, "Customer", FakeCustomer)
    monkeypatch.setattr(
        stripe, "checkout", type("CO", (), {"Session": FakeCheckoutSession})
    )

    resp = client.post(
        "/api/v1/billing/checkout",
        json={
            "success_url": "http://localhost:3000/account?checkout=success",
            "cancel_url": "http://localhost:3000/pricing?checkout=cancelled",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["url"] == "https://checkout.stripe.com/test"
    assert created["mode"] == "subscription"
    assert created["metadata"]["plan"] == "pro"

    # Webhook confirms -> immediate access grant.
    with session_scope() as db:
        user = db.query(User).filter(User.email == "scout@example.com").first()
        user_id = user.id
    raw, sig = signed_event(checkout_completed_event(user_id))
    resp = client.post(
        "/api/v1/billing/webhook", content=raw, headers={"stripe-signature": sig}
    )
    assert resp.status_code == 200, resp.text
    assert client.get("/api/v1/auth/me").json()["has_pro"] is True


# ---------------------------------------------------------------------------
# Webhook security (D3): signature verification is genuinely enforced
# ---------------------------------------------------------------------------


def test_unsigned_webhook_rejected(client):
    register_user(client)
    raw = json.dumps(checkout_completed_event(1)).encode("utf-8")
    resp = client.post("/api/v1/billing/webhook", content=raw)
    assert resp.status_code == 400  # missing signature header


def test_tampered_webhook_rejected(client):
    register_user(client)
    event = checkout_completed_event(1)
    raw, sig = signed_event(event)
    # Tamper the payload AFTER signing.
    tampered = raw.replace(b"cs_test_abc", b"cs_test_TAMPERED")
    resp = client.post(
        "/api/v1/billing/webhook", content=tampered, headers={"stripe-signature": sig}
    )
    assert resp.status_code == 400
    # And no side effect happened.
    with session_scope() as db:
        assert db.query(WebhookEvent).count() == 0


# ---------------------------------------------------------------------------
# Idempotency (A3/A6): replaying an event must not double-grant
# ---------------------------------------------------------------------------


def test_webhook_idempotent_replay(client):
    register_user(client)
    with session_scope() as db:
        user = db.query(User).filter(User.email == "scout@example.com").first()
        user_id = user.id

    raw, sig = signed_event(checkout_completed_event(user_id))
    first = client.post(
        "/api/v1/billing/webhook", content=raw, headers={"stripe-signature": sig}
    )
    assert first.status_code == 200
    second = client.post(
        "/api/v1/billing/webhook", content=raw, headers={"stripe-signature": sig}
    )
    assert second.status_code == 200
    assert second.json()["duplicate"] is True

    with session_scope() as db:
        # Exactly one subscription row, one webhook row, one active grant.
        subs = db.query(Subscription).all()
        assert len(subs) == 1
        events = db.query(WebhookEvent).all()
        assert len(events) == 1
        assert events[0].duplicate is False
        assert client.get("/api/v1/auth/me").json()["has_pro"] is True


# ---------------------------------------------------------------------------
# Grace period (A3): payment failure does not cut access; recovery + cancel
# ---------------------------------------------------------------------------


def _grant_pro(client, user_id: int, sub_id: str = "sub_test_grace") -> None:
    raw, sig = signed_event(checkout_completed_event(user_id, sub_id))
    resp = client.post(
        "/api/v1/billing/webhook", content=raw, headers={"stripe-signature": sig}
    )
    assert resp.status_code == 200


def test_payment_failed_enters_grace_period_and_recovery(client):
    register_user(client)
    with session_scope() as db:
        user_id = db.query(User).filter(User.email == "scout@example.com").first().id
    _grant_pro(client, user_id)

    # First payment failure -> past_due + grace period, access RETAINED.
    raw, sig = signed_event(payment_failed_event("sub_test_grace"))
    resp = client.post(
        "/api/v1/billing/webhook", content=raw, headers={"stripe-signature": sig}
    )
    assert resp.status_code == 200
    assert client.get("/api/v1/auth/me").json()["has_pro"] is True  # not cut off
    with session_scope() as db:
        sub = db.query(Subscription).first()
        assert sub.status == "past_due"
        assert sub.grace_period_end is not None
        # SQLite round-trips naive; normalize before comparing (same helper the
        # access gate uses).
        grace = sub.grace_period_end
        if grace.tzinfo is None:
            grace = grace.replace(tzinfo=timezone.utc)
        assert grace > datetime.now(timezone.utc)

    # Recovery: renewal succeeds -> active again, grace cleared by updated event.
    future = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    raw, sig = signed_event(
        subscription_updated_event("sub_test_grace", "active", future)
    )
    resp = client.post(
        "/api/v1/billing/webhook", content=raw, headers={"stripe-signature": sig}
    )
    assert resp.status_code == 200
    assert client.get("/api/v1/auth/me").json()["has_pro"] is True
    with session_scope() as db:
        sub = db.query(Subscription).first()
        assert sub.status == "active"
        assert sub.current_period_end is not None


def test_payment_failed_then_cancellation_revokes(client):
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


def test_canceled_keeps_access_to_period_end(client):
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


def test_limits_report_plan_boundaries(client):
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


def test_billing_configured_flag(client):
    register_user(client)
    body = client.get("/api/v1/billing/subscription").json()
    assert body["billing_configured"] is True  # env keys present in this suite


# ---------------------------------------------------------------------------
# Registration rate limiting (5 per IP per 10 minutes)
# ---------------------------------------------------------------------------


def test_register_rate_limit_allows_under_threshold(client):
    """First 5 registrations from the same IP should all succeed."""
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": f"user{i}@example.com", "password": "Hunter2hunter"},
        )
        assert resp.status_code == 201, f"Registration {i + 1} should succeed"


def test_register_rate_limit_blocks_over_threshold(client):
    """6th registration from the same IP should be rate-limited (429)."""
    # Exhaust the limit
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": f"rate{i}@example.com", "password": "Hunter2hunter"},
        )
        assert resp.status_code == 201

    # 6th attempt should be blocked
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "rate5@example.com", "password": "Hunter2hunter"},
    )
    assert resp.status_code == 429
    assert "Too many" in resp.json()["error"]["message"]


def test_register_rate_limit_resets_after_clear(client):
    """After clearing rate limit state, registrations should succeed again."""
    # Exhaust the limit
    for i in range(5):
        client.post(
            "/api/v1/auth/register",
            json={"email": f"clear{i}@example.com", "password": "Hunter2hunter"},
        )

    # Should be blocked
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "clear5@example.com", "password": "Hunter2hunter"},
    )
    assert resp.status_code == 429

    # Clear the rate limiter (simulates time passing)
    from app.rate_limiting import get_rate_limiter

    limiter = get_rate_limiter()
    limiter.reset_all()

    # Should succeed again
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "clear6@example.com", "password": "Hunter2hunter"},
    )
    assert resp.status_code == 201


def test_register_rate_limit_independent_of_email(client):
    """Rate limit is per IP, not per email — different emails from same IP count."""
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"unique{i}@example.com",
                "password": "Hunter2hunter",
            },
        )
        assert resp.status_code == 201

    # Even a different email is blocked (same IP)
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "another@example.com", "password": "Hunter2hunter"},
    )
    assert resp.status_code == 429


def test_register_rate_limit_error_message(client):
    """Rate limit response includes a clear error message."""
    for i in range(5):
        client.post(
            "/api/v1/auth/register",
            json={"email": f"msg{i}@example.com", "password": "Hunter2hunter"},
        )

    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "msg5@example.com", "password": "Hunter2hunter"},
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


def test_change_password_rate_limit(client):
    """Change password endpoint should be rate-limited after 5 attempts."""
    register_user(client)

    # 5 failed attempts (wrong current password) should all return 400
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "wrongpass", "new_password": "NewPass123"},
        )
        assert resp.status_code == 400

    # 6th attempt should be rate-limited (429)
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrongpass", "new_password": "NewPass123"},
    )
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "http_429"


def test_change_password_succeeds_under_limit(client):
    """Successful password change within rate limit should work."""
    register_user(client)
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Hunter2hunter", "new_password": "NewPass123"},
    )
    assert resp.status_code == 200
    assert "Password changed" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Verify-email rate limiting (5 per user per hour)
# ---------------------------------------------------------------------------


def test_verify_email_rate_limit(client):
    """Verify email endpoint should be rate-limited after 5 requests."""
    register_user(client)
    body = {"email": "scout@example.com"}

    for i in range(5):
        resp = client.post("/api/v1/auth/verify-email/request", json=body)
        assert resp.status_code == 200

    # 6th request should be rate-limited
    resp = client.post("/api/v1/auth/verify-email/request", json=body)
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "http_429"


# ---------------------------------------------------------------------------
# Stripe redirect URL validation (open redirect prevention)
# ---------------------------------------------------------------------------


def test_checkout_rejects_external_redirect(client):
    """success_url pointing to a different domain must be rejected."""
    register_user(client)
    resp = client.post(
        "/api/v1/billing/checkout",
        json={"success_url": "https://evil.com/steal", "cancel_url": "/cancel"},
    )
    assert resp.status_code == 400
    assert "domain" in resp.json()["error"]["message"].lower()


def test_checkout_rejects_double_slash_redirect(client):
    """URLs like //evil.com are protocol-relative and must be rejected."""
    register_user(client)
    resp = client.post(
        "/api/v1/billing/checkout",
        json={"success_url": "//evil.com/steal", "cancel_url": "/ok"},
    )
    assert resp.status_code == 400


def test_checkout_allows_relative_redirect(client, monkeypatch):
    """Relative paths like /success are always safe."""
    register_user(client)
    # Mock Stripe to avoid real API calls
    import app.billing as _billing

    created = {}

    class FakeSession:
        @staticmethod
        def create(**kwargs):
            created.update(kwargs)
            return {"url": "https://checkout.stripe.com/test", "id": "cs_test"}

    class FakeCheckout:
        Session = FakeSession

    class FakeCustomer:
        @staticmethod
        def create(**kwargs):
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
