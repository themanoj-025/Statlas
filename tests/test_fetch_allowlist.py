"""Tests for the ``fetch_with_retry`` host allowlist guard.

The guard is the SSRF defense-in-depth boundary: before any network request,
the target host must be on the allowlist configured by
``set_allowed_fetch_hosts``. A non-whitelisted host raises immediately.

These tests never touch Redis or the network — they only exercise the
host-parsing + allowlist logic and the guard's early-exit behavior.
"""

from __future__ import annotations

import logging
import os

import pytest

# Make imports deterministic and redis-free: point REDIS_URL at a
# definitely-unreachable server so get_rate_limiter()'s fallback kicks in
# without ever reaching a real Redis. (The app config reads REDIS_URL.)
os.environ.setdefault("STATLAS_ENV", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:9999/0")

# Silence any logger churn during import and execution.
_root = logging.root
_old_level = _root.level
_root.handlers.clear()
_root.setLevel(logging.CRITICAL)

try:
    from app.sources.base import (
        SourceError,
        _check_fetch_url,
        _parse_url_host,
        fetch_with_retry,
        set_allowed_fetch_hosts,
    )
finally:
    _root.handlers[:] = []
    _root.setLevel(_old_level)


# ── _parse_url_host ────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://fbref.com/en/comps/9/schedule/", "fbref.com"),
        ("http://understat.com/main/getPlayersStats/", "understat.com"),
        ("https://raw.githubusercontent.com/hudl/open-data/master/data/", "raw.githubusercontent.com"),
        ("https://transfermarkt.com/england/premier-league/startseite/verein/21/", "transfermarkt.com"),
        ("https://example.com/foo", "example.com"),
        ("HTTPS://FBREF.COM/comps/9", "fbref.com"),
    ],
)
def test_parse_url_host(url: str, expected: str) -> None:
    assert _parse_url_host(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "not-a-url",
        "ftp://host/file",
        "",
        "   ",
        "mailto:test@example.com",
        "file:///etc/passwd",
    ],
)
def test_parse_url_host_returns_none_for_non_http(url: str) -> None:
    assert _parse_url_host(url) is None


# ── allowlist behavior ─────────────────────────────────────────────────────────

def test_allowed_host_succeeds() -> None:
    set_allowed_fetch_hosts(allow_all=False)
    _check_fetch_url("https://fbref.com/en/comps/9/schedule/")


def test_disallowed_host_raises() -> None:
    set_allowed_fetch_hosts(allow_all=False)
    with pytest.raises(SourceError, match="not permitted by the fetch allowlist"):
        _check_fetch_url("https://evil.internal.local/foo")


def test_allow_all_disables_guard() -> None:
    set_allowed_fetch_hosts(allow_all=True)
    _check_fetch_url("https://evil.internal.local/foo")  # no-op


def test_extra_hosts_are_whitelisted() -> None:
    set_allowed_fetch_hosts(allow_all=False, extra={"custom-datasource.example.com"})
    _check_fetch_url("https://custom-datasource.example.com/v1/data")


def test_host_matching_is_case_insensitive() -> None:
    set_allowed_fetch_hosts(allow_all=False)
    _check_fetch_url("https://FBREF.COM/en/comps/9/schedule/")


def test_query_fragment_and_params_are_stripped_from_host() -> None:
    set_allowed_fetch_hosts(allow_all=False)
    _check_fetch_url(
        "https://fbref.com/en/comps/9/schedule/?league=9#section"
    )


def test_fetch_with_retry_raises_on_disallowed_host_no_request() -> None:
    """The guard must raise before any Redis/network setup happens."""
    set_allowed_fetch_hosts(allow_all=False)
    with pytest.raises(SourceError, match="not permitted by the fetch allowlist"):
        # limiter here is irrelevant — the guard raises before it is used.
        fetch_with_retry(
            "https://evil.internal.local/foo",
            limiter=None,  # type: ignore[arg-type]
            cache=None,
        )
