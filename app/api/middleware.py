"""Statlas API middleware -- body size limits, CSRF, security headers."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.logging_setup import new_request_id

logger = logging.getLogger(__name__)

_settings = get_settings()

# CSRF-protected routes (state-changing requests from browser)
CSRF_EXEMPT_PATHS = frozenset({
    "/api/v1/health",
    "/api/v1/readiness",
    "/api/v1/meta",
    "/api/v1/leagues",
    "/api/v1/coverage",
    "/api/v1/positions",
    "/api/v1/methodology",
    "/api/v1/billing/webhook",  # Stripe signature verification
    "/api/v1/billing/checkout",  # Redirects to Stripe
    "/api/v1/billing/portal",   # Redirects to Stripe
    "/api/v1/e2e",             # Test-only endpoints
    "/metrics",                # Prometheus scrape endpoint (read-only GET)
})


MAX_REQUEST_BODY_BYTES = 1 * 1024 * 1024  # 1 MB


async def body_size_limit_middleware(request: Request, call_next: Any) -> Any:
    """Reject requests with oversized bodies (DoS protection).

    Constitution \u00a74 (Security): SSRF guard + request validation.
    Checks both Content-Length header and actual body size for chunked
    transfers where Content-Length may be absent.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return await call_next(request)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": {"code": "payload_too_large", "message": "Request body exceeds 1MB limit."}},
        )
    # For chunked transfers (no Content-Length), read body and check size.
    if not content_length:
        body = await request.body()
        if len(body) > MAX_REQUEST_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"error": {"code": "payload_too_large", "message": "Request body exceeds 1MB limit."}},
            )
    return await call_next(request)


async def csrf_middleware(request: Request, call_next: Any) -> Any:
    """Verify CSRF tokens on state-changing requests.

    Safe methods (GET, HEAD, OPTIONS) are always allowed.
    Exempt paths (webhook, health, etc.) are skipped.
    For other POST/PUT/DELETE/PATCH requests, a valid X-CSRF-Token
    header is required when a session cookie is present.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return await call_next(request)

    # Check exemption list
    path = request.url.path
    if path in CSRF_EXEMPT_PATHS or path.startswith("/api/v1/e2e"):
        return await call_next(request)

    # Skip CSRF in test/CI environments (no browser involved)
    if _settings.environment == "test":
        return await call_next(request)

    # Only enforce CSRF when a session cookie is present
    session_cookie = request.cookies.get(_settings.session_cookie_name)
    if not session_cookie:
        return await call_next(request)

    from app.csrf import CSRF_TOKEN_HEADER, verify_csrf_token

    token = request.headers.get(CSRF_TOKEN_HEADER)
    if not token or not verify_csrf_token(token, session_cookie):
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "csrf_error",
                    "message": "Invalid or missing CSRF token."
                    if token
                    else "CSRF token missing. Include the X-CSRF-Token header.",
                }
            },
        )

    return await call_next(request)


async def security_and_rate_limit_middleware(request: Request, call_next: Any) -> Any:
    """1. Attach X-RateLimit-* headers to public-API responses (Part C1).
    2. Add security headers to every response.
    The public views set request.state.rate_limit during auth; this applies
    the headers on the way out."""

    # Generate request ID for tracing + structured logging
    req_id = new_request_id()
    request.state.request_id = req_id

    start_time = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start_time) * 1000

    # --- Rate limit headers ---
    try:
        from app.api.public_views import apply_rate_limit_headers

        apply_rate_limit_headers(response, request)
    except (AttributeError, KeyError, TypeError):  # header decoration must never break a response
        pass

    # --- Security headers ---
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=()"
    )
    # HSTS: tell browsers to only use HTTPS (1 year, include subdomains)
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    # Content-Security-Policy
    csp_parts = [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "font-src 'self'",
        "connect-src 'self' https://api.resend.com",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
    if _settings.csp_report_uri:
        csp_parts.append(f"report-uri {_settings.csp_report_uri}")
    response.headers["Content-Security-Policy"] = "; ".join(csp_parts)

    # --- Performance tracking ---
    response.headers["X-Response-Time"] = f"{duration_ms:.0f}ms"
    if duration_ms > 1000:  # Log slow requests (>1s)
        logger.warning(
            "Slow request: %s %s took %.0fms",
            request.method,
            request.url.path,
            duration_ms,
        )

    # --- Metrics collection ---
    try:
        from app.metrics import get_metrics_collector

        # Normalise path for metrics (strip query params, collapse IDs)
        metrics_path = re.sub(r"/\d+", "/{id}", request.url.path)
        metrics_path = re.sub(r"/by-slug/[^/]+", "/by-slug/{slug}", metrics_path)
        get_metrics_collector().record_request(
            method=request.method,
            path=metrics_path,
            status_code=response.status_code,
            duration_seconds=duration_ms / 1000,
        )
    except (OSError, ConnectionError, ValueError):  # metrics must never break a response
        pass

    return response
