"""Phase 4 — auth + billing API routes (Parts A2–A5).

Cookie-based sessions (HttpOnly, SameSite=Lax) set by the API; the web app
forwards the cookie to server components. Webhook endpoint is deliberately
unauthenticated (Stripe signature IS the auth) but signature-verified.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from app import auth, billing
from app.config import get_settings
from app.config import plan_limits as pricing_limits
from app.db import session_scope
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["accounts", "billing"])

SESSION_COOKIE = "statlas_session"


class RegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginBody(BaseModel):
    email: EmailStr
    password: str


def _set_session_cookie(
    response: Response, raw_token: str, expires_at: datetime
) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,  # set True on https deployments
        max_age=int((expires_at - datetime.now(timezone.utc)).total_seconds()),
        path="/",
    )


def _session_token(request: Request) -> str | None:
    return request.cookies.get(get_settings().session_cookie_name)


def _require_user(request: Request) -> User:
    with session_scope() as db:
        user = auth.user_from_session(db, _session_token(request))
        if user is None:
            raise HTTPException(status_code=401, detail="Not signed in.")
        return user


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@router.post("/auth/register", status_code=201)
def register(body: RegisterBody, response: Response):
    with session_scope() as db:
        existing = db.query(User).filter(User.email == body.email.lower()).first()
        if existing is not None:
            raise HTTPException(
                status_code=409, detail="An account with that email already exists."
            )
        user = User(
            email=body.email.lower(),
            password_hash=auth.hash_password(body.password),
            plan="free",
        )
        db.add(user)
        db.commit()
        raw, expires_at = auth.create_session(db, user.id)
        _set_session_cookie(response, raw, expires_at)
        return auth.user_payload(user)


@router.post("/auth/login")
def login(body: LoginBody, response: Response):
    with session_scope() as db:
        user = db.query(User).filter(User.email == body.email.lower()).first()
        if user is None or not auth.verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Incorrect email or password.")
        raw, expires_at = auth.create_session(db, user.id)
        _set_session_cookie(response, raw, expires_at)
        return auth.user_payload(user)


@router.post("/auth/logout")
def logout(request: Request, response: Response):
    with session_scope() as db:
        auth.revoke_session(db, _session_token(request))
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    return {"ok": True}


@router.get("/auth/me")
def me(request: Request):
    with session_scope() as db:
        user = auth.user_from_session(db, _session_token(request))
        if user is None:
            raise HTTPException(status_code=401, detail="Not signed in.")
        return {**auth.user_payload(user), "has_pro": auth.has_pro_access(db, user.id)}


# ---------------------------------------------------------------------------
# Billing — checkout / portal / webhook / status
# ---------------------------------------------------------------------------


class CheckoutBody(BaseModel):
    success_url: str
    cancel_url: str


@router.post("/billing/checkout")
def checkout(body: CheckoutBody, request: Request):
    user = _require_user(request)
    try:
        with session_scope() as db:
            return billing.create_checkout_session(
                db, user, success_url=body.success_url, cancel_url=body.cancel_url
            )
    except billing.BillingNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/billing/portal")
def billing_portal(request: Request, body: dict[str, str] | None = None):
    user = _require_user(request)
    return_url = (body or {}).get("return_url") or "/account"
    try:
        with session_scope() as db:
            return billing.create_billing_portal_session(
                db, user, return_url=return_url
            )
    except billing.BillingNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    """Stripe webhook endpoint. Auth = the verified signature, never a cookie.
    Returns 200 for every VALID event (including duplicates) and 400/503 for
    anything that must not be silently dropped."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        event = billing.verify_webhook_signature(payload, sig)
    except billing.WebhookVerificationError as exc:
        logger.warning("rejected webhook: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid signature.") from exc
    except billing.BillingNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    with session_scope() as db:
        return billing.process_webhook(db, event)


@router.get("/billing/subscription")
def subscription_status(request: Request):
    user = _require_user(request)
    with session_scope() as db:
        sub = auth.current_subscription(db, user.id)
        return {
            "has_pro": auth.has_pro_access(db, user.id),
            "plan": auth.effective_plan(db, user.id),
            "status": sub.status if sub else None,
            "current_period_end": (
                sub.current_period_end.isoformat()
                if sub and sub.current_period_end
                else None
            ),
            "grace_period_end": (
                sub.grace_period_end.isoformat()
                if sub and sub.grace_period_end
                else None
            ),
            "billing_configured": billing.billing_configured(),
            "portal_enabled": get_settings().billing_portal_enabled,
        }


@router.get("/billing/limits")
def plan_limits(request: Request):
    """What the CURRENT plan can do — the honest upsell data source (A4)."""
    with session_scope() as db:
        user = auth.user_from_session(db, _session_token(request))
        if user is None:
            plan = "free"
        else:
            plan = auth.effective_plan(db, user.id)
    return {"plan": plan, "limits": pricing_limits(plan)}
