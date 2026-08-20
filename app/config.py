"""Statlas pipeline configuration loader.

Loads the Phase 0 artifacts (config/metric_registry.json, config/tiers.json) and
environment overrides. This module is the single place where the locked numbers
from `methodology.md` / `percentile-rules.md` / `data-compliance-notes.md` enter
the code — nothing in the pipeline hardcodes a weight, threshold, or rate limit
elsewhere.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "config"

# The current season string — single source of truth. Every endpoint, query,
# and test references this instead of hardcoding "2025-26".
CURRENT_SEASON = "2025-26"

DEFAULT_USER_AGENT = (
    "StatlasAnalytics/0.1 (public football analytics; contact: data@statlas.com)"
)


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    """The Metric Registry (methodology-as-code). Generated from methodology.md."""
    with open(CONFIG_DIR / "metric_registry.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_tiers() -> dict[str, Any]:
    """League tiers + external ids. Generated from percentile-rules.md."""
    with open(CONFIG_DIR / "tiers.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_pricing() -> dict[str, Any]:
    """Subscription tier boundaries — THE single source of truth for what each
    plan can do (Phase 4 — Part A1). Feature gating reads this, never scattered
    magic strings. The Stripe price ids are filled at setup and mirrored in
    docs/billing/pricing-config.md."""
    with open(CONFIG_DIR / "pricing.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_search_presets() -> dict[str, Any]:
    """Curated search presets (Phase 8) — Statlas-authored starting points for
    the structured query builder. Public by design (not user-owned data); the
    methodology-as-code precedent (metric_registry.json) applies. Validated by
    scripts/validate_search_presets.py against the published population."""
    with open(CONFIG_DIR / "search_presets.json", encoding="utf-8") as f:
        return json.load(f)


def plan_limits(plan: str) -> dict[str, Any]:
    """Limits dict for a plan id ("free"/"pro"/"api_business"). Unknown plans
    fall back to free — access is granted by data, never by label."""
    pricing = load_pricing()
    plans = pricing.get("plans", {})
    if plan not in plans:
        return plans.get("free", {}).get("limits", {})
    return plans[plan].get("limits", {})


def env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


def env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except (TypeError, ValueError):
        return default


def env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (TypeError, ValueError):
        return default


def env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Runtime settings with the compliance-declared defaults baked in."""

    def __init__(self) -> None:
        self.database_url = env("DATABASE_URL")  # None -> SQLite (tests/dev)
        self.user_agent = env("STATLAS_USER_AGENT", DEFAULT_USER_AGENT)
        self.fbref_delay_seconds = env_float("FBREF_DELAY_SECONDS", 10.0)
        self.fbref_jitter_seconds = env_float("FBREF_JITTER_SECONDS", 2.0)
        self.understat_delay_seconds = env_float("UNDERSTAT_DELAY_SECONDS", 5.0)
        self.api_football_delay_seconds = env_float("API_FOOTBALL_DELAY_SECONDS", 2.0)
        self.api_football_daily_budget = env_int("API_FOOTBALL_DAILY_BUDGET", 80)
        self.api_football_key = env("API_FOOTBALL_KEY", "") or None
        self.cache_dir = Path(env("STATLAS_CACHE_DIR", ".cache"))
        self.enrich_positions = env_bool("FBREF_ENRICH_POSITIONS", False)
        self.log_level = env("STATLAS_LOG_LEVEL", "INFO")
        # Honest dataset labeling: the API serves fixture/demo data until a real
        # scrape pipeline run + DATASET_MODE=production (Phase 2 F / site-map.md).
        self.dataset_mode = env("STATLAS_DATASET_MODE", "fixture-demo")
        self.dataset_note = env(
            "STATLAS_DATASET_NOTE",
            "Serving labeled fixture data from the Phase 1 test fixtures. A full data refresh must run before production launch.",
        )
        # --- Phase 4: Stripe billing (Part A) ---------------------------------
        # Optional: when unset, billing endpoints return an explicit
        # "billing not configured" state instead of failing mid-checkout.
        self.stripe_secret_key = env("STRIPE_SECRET_KEY", "") or None
        self.stripe_webhook_secret = env("STRIPE_WEBHOOK_SECRET", "") or None
        self.stripe_price_pro_monthly = env("STRIPE_PRICE_PRO_MONTHLY", "") or None
        self.billing_portal_enabled = env_bool("STRIPE_BILLING_PORTAL_ENABLED", False)
        # --- Phase 4: AI assistant (Part B) ------------------------------------
        self.anthropic_api_key = env("ANTHROPIC_API_KEY", "") or None
        self.assistant_model = env("ASSISTANT_MODEL", "claude-3-5-haiku-latest")
        # --- Phase 9: reports ---------------------------------------------------
        # Dev/e2e affordance: when set, the report API uses the deterministic
        # narrator (which can only emit context values) instead of the LLM. The
        # verification gate still runs on every generation. Never set in
        # production; the LLM narrator remains the default.
        self.reports_dev_narrator = env_bool("REPORTS_DEV_NARRATOR", False)
        # --- Phase 10: watchlist & alerts --------------------------------------
        # The percentile-movement threshold (alert-trigger-definitions.md §2.1):
        # inclusive, deployment-tunable without a code change.
        self.alert_percentile_move_threshold = env_float(
            "ALERT_PERCENTILE_MOVE_THRESHOLD", 15.0
        )
        # Outbound email (Resend — docs/product/notification-delivery.md).
        # Unset = honest "email not configured" state; delivery never fails
        # silently. The sender is injectable for tests.
        self.resend_api_key = env("RESEND_API_KEY", "") or None
        self.resend_from_email = env("RESEND_EMAIL_FROM", "notifications@statlas.app")
        # Signs one-click unsubscribe links in alert emails. Production must set
        # it; a per-process random default keeps dev links safe but invalidates
        # them on restart (documented).
        self.alert_signing_secret = env("ALERT_SIGNING_SECRET", "") or None
        # Public base URL for links inside alert emails (web app).
        self.public_base_url = env("STATLAS_PUBLIC_BASE_URL", "http://localhost:3000")
        # --- Phase 4: sessions / API keys --------------------------------------
        self.session_cookie_name = env("STATLAS_SESSION_COOKIE", "statlas_session")
        self.session_ttl_hours = env_int("STATLAS_SESSION_TTL_HOURS", 30 * 24)
        # Secure flag only on https deployments (statlas production); plain
        # http dev/test must keep the cookie usable.
        self.session_cookie_secure = env_bool("STATLAS_COOKIE_SECURE", False)
        # --- CORS Configuration -------------------------------------------------
        raw_origins = env("ALLOWED_ORIGINS", "")
        if raw_origins:
            self.allowed_origins = [
                o.strip() for o in raw_origins.split(",") if o.strip()
            ]
        else:
            self.allowed_origins = [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
        # --- Redis (production rate limiting / caching) --------------------------
        self.redis_url = env("REDIS_URL", "redis://localhost:6379/0")
        # --- Staff access (analytics dashboards) --------------------------------
        self.staff_emails = env("STAFF_EMAILS", "")
        # --- Security headers ---------------------------------------------------
        self.csp_report_uri = env("CSP_REPORT_URI", "")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
