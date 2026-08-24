"""Stripe billing integration (Phase 4 — Part A).

Design per the Phase 4 prompt's "extreme care" list:
- Hosted Checkout only (no custom card form — minimal PCI scope).
- Every webhook verifies the Stripe signature via the official SDK; an
  unsigned/tampered payload is rejected outright (Part D3 test asserts this).
- Idempotency: webhook_events.event_id is UNIQUE. Replays are recorded as
  duplicates and never re-processed (A3 + A6 idempotency test).
- checkout.session.completed grants access immediately; the webhook confirms
  shortly after (the optimistic success path, A2).
- invoice.payment_failed sets past_due + grace_period_end (Stripe's dunning
  retry window) instead of revoking; customer.subscription.deleted revokes
  with end-of-period retention; .updated handles plan changes.
- Every processed event is logged to webhook_events with enough payload detail
  to reconstruct a billing dispute; processing failures raise loudly.
- Key-gated: with STRIPE_SECRET_KEY unset, checkout/portal return an explicit
  "billing not configured" state — never a mid-flight failure.

The Stripe client is imported lazily so tests (which use a fake client) and
the fixture-demo environment do not require live credentials.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Subscription, User, WebhookEvent

logger = logging.getLogger(__name__)


class BillingNotConfiguredError(RuntimeError):
    """Raised when Stripe env keys are absent — maps to an honest 503."""


class WebhookVerificationError(RuntimeError):
    """Signature verification failed — the payload was not sent by Stripe."""


# ---------------------------------------------------------------------------
# Stripe client (lazy, key-gated)
# ---------------------------------------------------------------------------


def _stripe_client():
    """Import + configure the Stripe SDK. Raises BillingNotConfiguredError
    when no secret key is present (never a silent no-op)."""
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise BillingNotConfiguredError(
            "Stripe is not configured on this deployment (STRIPE_SECRET_KEY unset)."
        )
    import stripe  # lazy: tests + fixture-demo run without the live SDK wired

    stripe.api_key = settings.stripe_secret_key
    return stripe


def billing_configured() -> bool:
    return bool(get_settings().stripe_secret_key)


# ---------------------------------------------------------------------------
# Checkout (A2)
# ---------------------------------------------------------------------------


def create_checkout_session(
    db: Session, user: User, *, success_url: str, cancel_url: str
) -> dict[str, Any]:
    """Create a hosted Checkout session for the Pro plan. Requires the Stripe
    price id from pricing.json/setup (docs/billing/pricing-config.md)."""
    settings = get_settings()
    stripe = _stripe_client()
    price_id = settings.stripe_price_pro_monthly
    if not price_id:
        raise BillingNotConfiguredError(
            "STRIPE_PRICE_PRO_MONTHLY is unset — create the Pro price in the Stripe "
            "dashboard and record it per docs/billing/pricing-config.md."
        )

    # Ensure the customer row exists so webhook->subscription lookup is stable.
    sub = _current_sub(db, user.id)
    customer_id = sub.stripe_customer_id if sub else None
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email, metadata={"statlas_user_id": str(user.id)}
        )
        customer_id = customer["id"]
        if sub is None:
            sub = Subscription(
                user_id=user.id,
                plan="pro",
                stripe_customer_id=customer_id,
                status="incomplete",
            )
            db.add(sub)
        else:
            sub.stripe_customer_id = customer_id
        db.commit()

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"statlas_user_id": str(user.id), "plan": "pro"},
        allow_promotion_codes=True,
    )
    return {"url": session["url"], "session_id": session["id"]}


def create_billing_portal_session(
    db: Session, user: User, *, return_url: str
) -> dict[str, Any]:
    """Stripe hosted Billing Portal (A5) — manage card, invoices, cancellation."""
    if not get_settings().billing_portal_enabled:
        raise BillingNotConfiguredError(
            "STRIPE_BILLING_PORTAL_ENABLED is false — the portal is not configured for this deployment."
        )
    stripe = _stripe_client()
    sub = _current_sub(db, user.id)
    customer_id = sub.stripe_customer_id if sub else None
    if not customer_id:
        raise BillingNotConfiguredError(
            "No Stripe customer exists for this account yet."
        )
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return {"url": session["url"]}


def _current_sub(db: Session, user_id: int) -> Subscription | None:
    return (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .order_by(Subscription.id.desc())
        .first()
    )


# ---------------------------------------------------------------------------
# Webhooks (A3) — verify, idempotent, logged, loud on failure
# ---------------------------------------------------------------------------


def verify_webhook_signature(payload: bytes, sig_header: str | None) -> dict[str, Any]:
    """Verify the Stripe signature; returns the event dict. Rejects anything
    unsigned or tampered (Part D3 test asserts this)."""
    settings = get_settings()
    secret = settings.stripe_webhook_secret
    if not secret:
        raise WebhookVerificationError("Stripe webhook secret is not configured.")
    if not sig_header:
        raise WebhookVerificationError("Missing Stripe-Signature header.")
    import stripe  # lazy

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except (ValueError, TypeError, OSError) as exc:  # stripe.SignatureVerificationError and friends
        raise WebhookVerificationError(f"Signature verification failed: {exc}") from exc
    # stripe SDK returns an Event object; the handlers expect a plain dict.
    if hasattr(event, "to_dict"):
        return event.to_dict()
    return dict(event)


def process_webhook(db: Session, event: dict[str, Any]) -> dict[str, Any]:
    """Idempotent webhook dispatch. Returns a status dict for the HTTP layer.

    Idempotency: webhook_events.event_id is UNIQUE — a replayed event either
    hits the unique key (recorded duplicate, no side effects) or is detected
    by a pre-check and short-circuited. Never double-grants.
    """
    event_id = str(event.get("id", ""))
    event_type = str(event.get("type", ""))

    existing = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
    if existing is not None:
        logger.warning(
            "webhook replay: event %s (%s) already processed", event_id, event_type
        )
        return {"processed": False, "duplicate": True, "event_id": event_id}

    sub_id = event.get("data", {}).get("object", {}).get("subscription") or event.get(
        "data", {}
    ).get("object", {}).get("id")
    row = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        stripe_subscription_id=sub_id,
        payload=event,
    )
    db.add(row)
    try:
        db.flush()  # fires the unique constraint -> protects against races
        _dispatch(db, event, row)
    except Exception:
        db.rollback()
        logger.exception(
            "webhook processing failed for event %s (%s)", event_id, event_type
        )
        raise
    db.commit()
    logger.info("webhook processed: %s (%s) for sub %s", event_id, event_type, sub_id)
    return {"processed": True, "duplicate": False, "event_id": event_id}


def _dispatch(db: Session, event: dict[str, Any], row: WebhookEvent) -> None:
    data = event.get("data", {}).get("object", {})
    handler = {
        "checkout.session.completed": _on_checkout_completed,
        "invoice.payment_failed": _on_payment_failed,
        "customer.subscription.deleted": _on_subscription_deleted,
        "customer.subscription.updated": _on_subscription_updated,
    }.get(str(event.get("type", "")))
    if handler is None:
        logger.info(
            "webhook type %s has no handler — recorded, not processed",
            event.get("type"),
        )
        return
    handler(db, data, row)


def _resolve_user(db: Session, data: dict[str, Any], row: WebhookEvent) -> User | None:
    """Find the Statlas user from metadata (set at checkout) or an existing
    subscription row's user_id."""
    meta = data.get("metadata") or {}
    user_id = meta.get("statlas_user_id")
    if user_id:
        return db.get(User, int(user_id))
    sub_id = data.get("subscription") or data.get("id")
    if sub_id:
        sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == sub_id)
            .first()
        )
        if sub is not None:
            row.user_id = sub.user_id
            return db.get(User, sub.user_id)
    return None


def _on_checkout_completed(
    db: Session, data: dict[str, Any], row: WebhookEvent
) -> None:
    """checkout.session.completed — grant access immediately (A2 optimistic
    path is confirmed here seconds later; idempotency prevents double-grant)."""
    user = _resolve_user(db, data, row)
    if user is None:
        logger.error("checkout.session.completed for unknown user: %s", data.get("id"))
        raise ValueError(
            "checkout.session.completed references an unknown Statlas user"
        )
    sub_id = data.get("subscription")
    if not sub_id:
        logger.error(
            "checkout.session.completed without subscription id: %s", data.get("id")
        )
        raise ValueError("checkout.session.completed missing subscription id")
    sub = _current_sub(db, user.id)
    if sub is None:
        sub = Subscription(user_id=user.id, plan="pro", status="incomplete")
        db.add(sub)
    sub.plan = "pro"
    sub.stripe_subscription_id = sub_id
    sub.status = "active"
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
    sub.updated_at = datetime.now(timezone.utc)
    row.user_id = user.id
    user.plan = "pro"


def _on_payment_failed(db: Session, data: dict[str, Any], row: WebhookEvent) -> None:
    """invoice.payment_failed — enter grace period (dunning retries), do NOT
    revoke. has_pro_access keeps granting until grace_period_end (default 7d)."""
    sub_id = data.get("subscription")
    if not sub_id:
        return
    sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == sub_id)
        .first()
    )
    if sub is None:
        return
    sub.status = "past_due"
    # Stripe default dunning window is 7 days; mirror it here so access and the
    # UI copy ("update your card by [date]") agree.
    sub.grace_period_end = datetime.now(timezone.utc) + timedelta(days=7)
    sub.updated_at = datetime.now(timezone.utc)
    row.user_id = sub.user_id


def _on_subscription_deleted(
    db: Session, data: dict[str, Any], row: WebhookEvent
) -> None:
    """customer.subscription.deleted — revoke with end-of-period retention:
    has_pro_access keeps granting until current_period_end, then revoked.
    (A5 documents this exact behaviour to users.)"""
    sub_id = data.get("id")
    if not sub_id:
        return
    sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == sub_id)
        .first()
    )
    if sub is None:
        return
    sub.status = "canceled"
    sub.grace_period_end = None
    sub.updated_at = datetime.now(timezone.utc)
    row.user_id = sub.user_id
    user = db.get(User, sub.user_id)
    if user is not None:
        user.plan = "free"


def _on_subscription_updated(
    db: Session, data: dict[str, Any], row: WebhookEvent
) -> None:
    """customer.subscription.updated — plan/status changes (e.g., a failed
    renewal that Stripe marks past_due at the period boundary, or an upgrade)."""
    sub_id = data.get("id")
    if not sub_id:
        return
    sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == sub_id)
        .first()
    )
    if sub is None:
        return
    status = data.get("status")
    period_end = data.get("current_period_end")
    if status:
        sub.status = (
            status
            if status in ("active", "trialing", "past_due", "canceled", "incomplete")
            else "incomplete"
        )
    if period_end:
        sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)
    sub.updated_at = datetime.now(timezone.utc)
    row.user_id = sub.user_id
