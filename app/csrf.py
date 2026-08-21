"""CSRF protection for state-changing requests.

Uses HMAC-signed tokens tied to a session ID, with a 1-hour expiry.
Safe methods (GET, HEAD, OPTIONS) are exempt.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from fastapi import HTTPException, Request

from app.config import get_settings

CSRF_TOKEN_HEADER = "X-CSRF-Token"
CSRF_TOKEN_TTL = 3600  # 1 hour

__all__ = [
    "CSRF_TOKEN_HEADER",
    "CSRF_TOKEN_TTL",
    "generate_csrf_token",
    "verify_csrf_token",
]


def _secret_key() -> str:
    """CSRF secret — from CSRF_SECRET_KEY env var if set, else derived from
    the session cookie name (backward-compatible default).
    """
    settings = get_settings()
    if settings.csrf_secret_key:
        return settings.csrf_secret_key
    # Fallback: domain-separated derivation (not ideal, but functional)
    return hmac.new(
        b"csrf-protection",
        settings.session_cookie_name.encode(),
        hashlib.sha256,
    ).hexdigest()


def generate_csrf_token(session_id: str) -> str:
    """Generate a CSRF token tied to a session ID."""
    secret = _secret_key()
    timestamp = str(int(time.time()))
    message = f"{session_id}:{timestamp}".encode()
    signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()[:32]
    return f"{timestamp}:{signature}"


def verify_csrf_token(token: str, session_id: str) -> bool:
    """Verify a CSRF token is valid and not expired."""
    try:
        timestamp_str, signature = token.split(":")
        secret = _secret_key()
        expected = hmac.new(
            secret.encode(),
            f"{session_id}:{timestamp_str}".encode(),
            hashlib.sha256,
        ).hexdigest()[:32]

        # Check expiry
        if time.time() - int(timestamp_str) > CSRF_TOKEN_TTL:
            return False

        return hmac.compare_digest(signature, expected)
    except (ValueError, TypeError):
        return False



