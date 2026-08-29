"""Public API keys (Phase 4 — Part C).

Security model (Part C1 + D3):
- Keys are 32 random bytes, URL-safe, prefixed `sl_` + 6-char human id.
- Only the SHA-256 hash is stored (never plaintext); the raw key is returned
  EXACTLY once at creation, then unrecoverable — the dashboard lists prefixes.
- `authenticate_api_key` resolves a bearer token to (user, plan) and bumps
  last_used_at; revoked keys fail auth.
- Rotation = create a new key + revoke the old one (documented in the UI).
- Rate limits come from pricing.json per plan, enforced at the API layer with
  X-RateLimit-* headers (see api/public_views.py).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth import hash_token
from app.config import plan_limits
from app.models import ApiKey, User

__all__ = [
    "api_rate_limit_for_plan",
    "authenticate_api_key",
    "generate_api_key",
    "list_api_keys",
    "revoke_api_key",
    "rotate_api_key",
]

KEY_PREFIX = "sl_"


def generate_api_key(db: Session, user: User, name: str) -> dict:
    """Create a key row; returns the raw key ONCE (the only time it exists)."""
    raw = secrets.token_urlsafe(32)
    prefix = KEY_PREFIX + secrets.token_hex(3)
    full_key = f"{prefix}.{raw}"
    db.add(
        ApiKey(
            user_id=user.id,
            name=name,
            key_hash=hash_token(full_key),  # hash the FULL bearer value
            prefix=prefix,
        )
    )
    db.commit()
    return {"key": full_key, "prefix": prefix, "name": name}


def list_api_keys(db: Session, user_id: int) -> list[dict]:
    rows = (
        db.query(ApiKey)
        .filter(ApiKey.user_id == user_id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "prefix": r.prefix,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "last_used_at": r.last_used_at.isoformat() if r.last_used_at else None,
            "revoked": r.revoked_at is not None,
        }
        for r in rows
    ]


def revoke_api_key(db: Session, user_id: int, key_id: int) -> bool:
    row = (
        db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user_id).first()
    )
    if row is None:
        return False
    row.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return True


def rotate_api_key(
    db: Session, user: User, key_id: int, new_name: str | None = None
) -> dict | None:
    """Rotate: revoke the old key, mint a new one. Returns None if the old key
    was not owned by the user. The new raw key is returned exactly once."""
    old = (
        db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user.id).first()
    )
    if old is None:
        return None
    name = new_name or old.name
    old.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return generate_api_key(db, user, name)


def authenticate_api_key(db: Session, token: str | None) -> tuple[User, str] | None:
    """Resolve a bearer token to (user, plan) or None if invalid/revoked."""
    if not token:
        return None
    row = db.query(ApiKey).filter(ApiKey.key_hash == hash_token(token)).first()
    if row is None or row.revoked_at is not None:
        return None
    user = db.get(User, row.user_id)
    if user is None:
        return None
    row.last_used_at = datetime.now(timezone.utc)
    db.commit()
    plan = user.plan if user.plan in ("free", "pro", "api_business") else "free"
    # Only api_business keys are rate-limited generously; pro/free keys get the
    # free-tier API limits (0 = API not included). Auth itself always resolves.
    return user, plan


def api_rate_limit_for_plan(plan: str) -> dict:
    """(requests_per_minute, requests_per_day) for a plan, from pricing.json."""
    pricing_limits = plan_limits(plan)
    rpm = int(pricing_limits.get("api_rate_limit_per_minute", 0) or 0)
    return {"per_minute": rpm, "per_day": 0 if rpm == 0 else 50_000}
