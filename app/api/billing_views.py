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
from app.api.deps import require_user, session_token
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

    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        """Validate password has minimum complexity."""
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in password):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one digit.")
        return password

    def model_post_init(self, __context: object) -> None:
        self.validate_password_strength(self.password)


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


def _set_csrf_cookie(response: Response, session_id: str) -> None:
    """Set a readable CSRF cookie so the frontend can read it via JS
    and send it back as the X-CSRF-Token header.
    """
    from app.csrf import CSRF_TOKEN_TTL, generate_csrf_token

    token = generate_csrf_token(session_id)
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,  # JS must be able to read this
        samesite="lax",
        secure=get_settings().session_cookie_secure,
        max_age=CSRF_TOKEN_TTL,
        path="/",
    )


# _session_token and _require_user consolidated into app/api/deps.py
_session_token = session_token
_require_user = require_user


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@router.post("/auth/register", status_code=201)
def register(body: RegisterBody, response: Response, request: Request):
    # Rate limit: 5 registrations per IP per 10 minutes
    from app.rate_limiting import get_rate_limiter

    limiter = get_rate_limiter()
    client_ip = request.client.host if request.client else "unknown"
    if limiter.is_limited(
        f"register:{client_ip}", max_attempts=5, window_seconds=600
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many registration attempts. Please try again later.",
        )
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
        _set_csrf_cookie(response, raw)
        return auth.user_payload(user)


@router.post("/auth/login")
def login(body: LoginBody, response: Response):
    email_lower = body.email.lower()
    # Rate limiting: check lockout first (Phase 12 — Part C2)
    locked, retry_after = auth.is_login_locked(email_lower)
    if locked:
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
    with session_scope() as db:
        user = db.query(User).filter(User.email == email_lower).first()
        if user is None or not auth.verify_password(body.password, user.password_hash):
            auth.record_login_failure(email_lower)
            raise HTTPException(status_code=401, detail="Incorrect email or password.")
        auth.clear_login_failures(email_lower)
        raw, expires_at = auth.create_session(db, user.id)
        _set_session_cookie(response, raw, expires_at)
        _set_csrf_cookie(response, raw)
        return auth.user_payload(user)


@router.post("/auth/logout")
def logout(request: Request, response: Response):
    with session_scope() as db:
        auth.revoke_session(db, _session_token(request))
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    response.delete_cookie("csrf_token", path="/")
    return {"ok": True}


@router.get("/auth/me")
def me(request: Request):
    with session_scope() as db:
        user = auth.user_from_session(db, _session_token(request))
        if user is None:
            raise HTTPException(status_code=401, detail="Not signed in.")
        return {**auth.user_payload(user), "has_pro": auth.has_pro_access(db, user.id)}


# ---------------------------------------------------------------------------
# Password reset (Phase 12 — Part C3)
# ---------------------------------------------------------------------------


class PasswordResetRequestBody(BaseModel):
    email: EmailStr


class PasswordResetConfirmBody(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=200)

    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in password):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one digit.")
        return password

    def model_post_init(self, __context: object) -> None:
        self.validate_password_strength(self.new_password)


@router.post("/auth/password-reset/request")
def password_reset_request(body: PasswordResetRequestBody):
    """Request a password reset. Always returns the same response to prevent
    account enumeration. Rate-limited to 3 attempts per hour per email."""
    from app.rate_limiting import get_rate_limiter

    email_lower = body.email.lower()
    limiter = get_rate_limiter()
    if limiter.is_limited(
        f"password_reset:{email_lower}",
        max_attempts=3,
        window_seconds=3600,
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many password reset requests. Try again in 1 hour.",
            headers={"Retry-After": "3600"},
        )
    with session_scope() as db:
        user = db.query(User).filter(User.email == email_lower).first()
        if user is not None:
            token = auth.create_password_reset_token(db, user.id)
            # In production, send email here. For dev/testing, log only a truncated reference.
            logger.info(
                "Password reset token generated for %s (token prefix: %s...)",
                user.email,
                token[:8],
            )
    return {
        "detail": "If an account with that email exists, a reset link has been sent."
    }


@router.post("/auth/password-reset/confirm")
def password_reset_confirm(body: PasswordResetConfirmBody):
    """Confirm a password reset with the token. Revokes all existing sessions."""
    with session_scope() as db:
        user_id = auth.consume_password_reset_token(db, body.token)
        if user_id is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired reset token.",
            )
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=400, detail="Invalid reset token.")
        user.password_hash = auth.hash_password(body.new_password)
        # Security: invalidate ALL sessions so any compromised token is dead
        auth.revoke_all_user_sessions(db, user_id)
        db.commit()
    return {"detail": "Password has been reset. All sessions invalidated. You can now log in."}


# ---------------------------------------------------------------------------
# Email verification (Phase 12 — Part C1)
# ---------------------------------------------------------------------------


class VerifyEmailRequestBody(BaseModel):
    email: EmailStr


class VerifyEmailConfirmBody(BaseModel):
    token: str


@router.post("/auth/verify-email/request")
def verify_email_request(request: Request, body: VerifyEmailRequestBody | None = None):
    """Request email verification for the signed-in user.
    Rate-limited to 5 per user per hour to prevent email spam."""
    from app.rate_limiting import get_rate_limiter

    user = _require_user(request)
    limiter = get_rate_limiter()
    if limiter.is_limited(
        f"verify_email:{user.id}", max_attempts=5, window_seconds=3600
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many verification requests. Please try again in 1 hour.",
            headers={"Retry-After": "3600"},
        )
    with session_scope() as db:
        token = auth.create_email_verification_token(db, user.id)
        logger.info("Email verification token for %s: %s", user.email, token)
    return {"detail": "Verification link sent."}


@router.post("/auth/verify-email/confirm")
def verify_email_confirm(body: VerifyEmailConfirmBody):
    """Confirm email verification."""
    with session_scope() as db:
        user_id = auth.consume_email_verification_token(db, body.token)
        if user_id is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired verification token.",
            )
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=400, detail="Invalid token.")
        user.email_verified_at = datetime.now(timezone.utc)
        db.commit()
    return {"detail": "Email verified."}


# ---------------------------------------------------------------------------
# Profile & preferences (Phase 12 — Part D)
# ---------------------------------------------------------------------------


class ProfileUpdateBody(BaseModel):
    display_name: str | None = Field(None, max_length=128)
    timezone: str | None = Field(None, max_length=64)
    locale: str | None = Field(None, max_length=10)


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)

    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in password):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one digit.")
        return password

    def model_post_init(self, __context: object) -> None:
        self.validate_password_strength(self.new_password)


class AccountDeleteBody(BaseModel):
    confirm_delete: bool


@router.put("/auth/profile")
def update_profile(request: Request, body: ProfileUpdateBody):
    """Update the signed-in user's profile."""
    user = _require_user(request)
    with session_scope() as db:
        db_user = db.get(User, user.id)
        if body.display_name is not None:
            db_user.display_name = body.display_name.strip() or None
        if body.timezone is not None:
            db_user.timezone = body.timezone.strip() or None
        if body.locale is not None:
            db_user.locale = body.locale.strip() or None
        db.commit()
        return auth.user_payload(db_user)


@router.post("/auth/change-password")
def change_password(request: Request, body: ChangePasswordBody, response: Response):
    """Change password for the signed-in user. Revokes all other sessions.
    Rate-limited to 5 attempts per 10 minutes to prevent brute force."""
    from app.rate_limiting import get_rate_limiter

    user = _require_user(request)
    limiter = get_rate_limiter()
    if limiter.is_limited(
        f"change_password:{user.id}", max_attempts=5, window_seconds=600
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many password change attempts. Please try again later.",
            headers={"Retry-After": "600"},
        )
    with session_scope() as db:
        db_user = db.get(User, user.id)
        if not auth.verify_password(body.current_password, db_user.password_hash):
            raise HTTPException(
                status_code=400, detail="Current password is incorrect."
            )
        db_user.password_hash = auth.hash_password(body.new_password)
        # Revoke all other sessions — the current session stays valid
        auth.revoke_all_user_sessions(db, user.id)
        db.commit()
    # Issue a fresh session token (the old one was revoked)
    with session_scope() as db:
        raw, expires_at = auth.create_session(db, user.id)
        _set_session_cookie(response, raw, expires_at)
    return {"detail": "Password changed. All other sessions have been invalidated."}


@router.post("/auth/delete-account")
def delete_account(request: Request, body: AccountDeleteBody):
    """Request account deletion. Sets pending_deletion with a 30-day grace period."""
    user = _require_user(request)
    if not body.confirm_delete:
        raise HTTPException(status_code=400, detail="Must confirm deletion.")
    with session_scope() as db:
        db_user = db.get(User, user.id)
        db_user.account_status = "pending_deletion"
        db.commit()
    return {"detail": "Account scheduled for deletion in 30 days. Log in to cancel."}


@router.post("/auth/cancel-deletion")
def cancel_deletion(request: Request):
    """Cancel a pending account deletion."""
    user = _require_user(request)
    with session_scope() as db:
        db_user = db.get(User, user.id)
        if db_user.account_status != "pending_deletion":
            raise HTTPException(status_code=400, detail="No pending deletion.")
        db_user.account_status = "active"
        db.commit()
    return {"detail": "Account deletion cancelled."}


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
