"""Shared source infrastructure.

- `StatsSource` — the interface every source implements (Constitution §4:
  swappable data-source layer).
- `RawPlayerStatRecord` — the normalized record each source returns; the
  orchestration layer only ever sees this shape.
- `RateLimiter` — enforced delay BETWEEN requests (the compliance notes'
  self-imposed limits are the declared values, not comments).
- `HttpCache` — local raw-response cache to minimise repeat requests.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from app.config import get_settings

logger = logging.getLogger(__name__)


class SourceError(RuntimeError):
    """Base error for all source failures. Raised loudly, never swallowed."""


class SchemaChangedError(SourceError):
    """A source's structure changed and we refuse to guess (Constitution: fail loudly)."""


class BudgetExhaustedError(SourceError):
    """The daily request budget is exhausted; the job must stop, not limp on."""


@dataclass
class RawPlayerStatRecord:
    """The normalized unit of player statistics flowing through the pipeline.

    raw_stats is keyed by *registry metric id* (e.g. "si_gls_p90") holding the
    value as the index consumes it: per-90 values for per90-kind metrics and
    percentages/rates as-is. This is what makes sources swappable — FBref and a
    licensed feed both produce this same shape.
    """

    source: str  # "fbref" | "understat" | ...
    season: str  # canonical "2025-26"
    league_slug: str  # canonical league slug (config/tiers.json)
    player_name: str
    team_name: str
    minutes_played: float
    matches_played: int
    raw_stats: dict[str, float] = field(default_factory=dict)
    position_code: str | None = None  # FBref-style Pos code (GK/DF/MF/FW...)
    position_group: str | None = (
        None  # GK/CB/FB/DM/CM/AM/W/ST (methodology.md §3 mapping)
    )
    position_label: str | None = None  # natural-language position (player pages)
    dob_year: int | None = None
    external_ids: dict[str, Any] = field(
        default_factory=dict
    )  # {"fbref": "abc123", "understat": 42}
    nation: str | None = None


@dataclass
class FixtureRecord:
    """Normalized fixture/live-score record (API-Football layer only)."""

    league_slug: str
    season: str
    api_fixture_id: int
    home_team_name: str
    away_team_name: str
    kickoff_utc: str | None
    status: str | None
    raw: dict[str, Any] = field(default_factory=dict)


class StatsSource(ABC):
    """The contract every data source implements."""

    source_name: str = "base"

    @abstractmethod
    def fetch_league_stats(
        self, league_slug: str, season: str
    ) -> list[RawPlayerStatRecord]:
        """Fetch per-player stats for a league season.

        Raises SourceError subclasses loudly on any structural problem — partial
        or guessed data is never returned silently.
        """

    def get_source_name(self) -> str:
        return self.source_name

    @abstractmethod
    def get_rate_limit_seconds(self) -> float:
        """Declared delay between requests (the compliance limit, in code)."""


class RateLimiter:
    """Sleeps so consecutive requests are spaced by at least `interval` seconds.

    `interval` is the SELF-IMPOSED value declared in data-compliance-notes.md and
    enforced in config; it is not a suggestion.
    """

    def __init__(self, interval: float, jitter: float = 0.0) -> None:
        self.interval = interval
        self.jitter = jitter
        self._last_request = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last_request
            delay = self.interval - elapsed + random.uniform(0, self.jitter)
            if delay > 0:
                time.sleep(delay)
            self._last_request = time.monotonic()

    def reset(self) -> None:
        with self._lock:
            self._last_request = 0.0


def backoff_delays(
    initial: float = 1.0, factor: float = 2.0, cap: float = 60.0
) -> list[float]:
    """Exponential backoff schedule declared in data-compliance-notes.md:
    1s -> 2s -> 4s -> 8s -> 16s -> 30s -> 60s cap, then the caller aborts.

    Returns a FINITE list ending exactly at `cap`. The doubling generator snaps
    the 32s step to the documented 30s and must terminate once d reaches cap
    (the pre-fix implementation looped forever at cap — `d = min(d * factor,
    cap)` keeps d == cap, so `while d <= cap` never exits; MemoryError in prod).
    """
    delays: list[float] = []
    d = initial
    while d < cap:
        delays.append(round(d, 2))
        next_d = min(d * factor, cap)
        # Snap to the documented 30s step (factor-2 doubling yields 32).
        if 20 < next_d < 40:
            next_d = 30.0
        d = next_d
    if not delays or delays[-1] != cap:
        delays.append(cap)
    return delays


class HttpCache:
    """Local cache for raw HTTP responses, keyed by URL + method.

    Caching aggressively is part of the compliance posture (minimise repeat
    requests). Cached entries are plain files under the configured cache dir.
    """

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        self.cache_dir = Path(cache_dir or get_settings().cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        return self.cache_dir / f"{digest}.json"

    def get(self, url: str) -> str | None:
        path = self._key_path(url)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - data.get("ts", 0) > data.get("ttl", 86400 * 7):
                return None
            return data["body"]
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def put(self, url: str, body: str, ttl: int = 86400 * 7) -> None:
        try:
            self._key_path(url).write_text(
                json.dumps({"ts": time.time(), "ttl": ttl, "body": body}),
                encoding="utf-8",
            )
        except OSError:  # cache must never take the pipeline down
            logger.warning("cache write failed for %s", url)


_ALLOWED_FETCH_HOSTS: set[str] | None = None


def set_allowed_fetch_hosts(*, allow_all: bool = False, extra: set[str] | None = None) -> None:
    """Configure the host allowlist checked by ``fetch_with_retry``.

    Called once at source initialization (never in request paths). In dev/CI the
    scraper fixtures override ``fetch_with_retry`` entirely, so this is relevant
    only for live-scrape runs.

    By default only the hosts the built-in sources actually use are permitted.
    Pass ``extra`` to add hosts for new sources (the allowlist is the same
    enum-gated discipline the structured-search surface already enforces).
    """
    global _ALLOWED_FETCH_HOSTS
    if allow_all:
        _ALLOWED_FETCH_HOSTS = None
        return
    base: set[str] = {
        "fbref.com",
        "understat.com",
        "v3.football.api-sports.io",
        "raw.githubusercontent.com",
    }
    if extra:
        base |= extra
    _ALLOWED_FETCH_HOSTS = base


def _check_fetch_url(url: str) -> None:
    """Fail fast when ``url`` targets a host not covered by the allowlist.

    This is the SSRF defense-in-depth boundary: before any network request is
    made, the target host must be on the allowlist configured via
    ``set_allowed_fetch_hosts``. A non-whitelisted host raises immediately so a
    future change that passes a user-derived URL cannot silently open SSRF.
    """
    if _ALLOWED_FETCH_HOSTS is None:
        return
    parsed = _parse_url_host(url)
    if parsed is None or parsed not in _ALLOWED_FETCH_HOSTS:
        raise SourceError(
            f"fetch to host {parsed or url!r} is not permitted by the fetch allowlist"
        )


def _parse_url_host(url: str) -> str | None:
    """Best-effort host extraction without pulling in ``urllib.parse``.

    Good enough for the hardcoded URLs the sources build today; not a full
    RFC parser. Scheme and host are matched case-insensitively (RFC 3986),
    so a user-derived URL cannot dodge the allowlist via ``HTTPS://``.
    """
    s = url.strip().lower()
    for prefix in ("https://", "http://"):
        if s.startswith(prefix):
            rest = s[len(prefix):]
            host = rest.split("/", 1)[0].split("&", 1)[0].split("?", 1)[0]
            host = host.split("#")[0].strip()
            return host.lower() if host else None
    return None


def fetch_with_retry(
    url: str,
    *,
    limiter: RateLimiter,
    cache: HttpCache | None,
    use_cache: bool = True,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    params: dict[str, Any] | None = None,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    session: Any | None = None,
) -> str:
    """HTTP GET (default) or POST with rate limiting, caching, and backoff.

    Backoff schedule per data-compliance-notes.md: 1s->2s->4s->8s->16s->30s->60s
    cap. After the schedule is exhausted the error is raised loudly — we never
    hammer through a block and never return partial data.

    POST requests bypass the cache (a form payload is stateful; serving a
    cached response for a POST could silently serve stale data).

    Before any request is made, the target host is checked against the allowlist
    configured by ``set_allowed_fetch_hosts``. A non-whitelisted host raises
    ``SourceError`` immediately — this is the SSRF defense-in-depth boundary so
    that a future change passing a user-derived URL cannot silently open SSRF.
    """
    _check_fetch_url(url)

    if cache is not None and use_cache and method == "GET":
        cached = cache.get(url)
        if cached is not None:
            return cached

    headers = dict(headers or {})
    headers.setdefault("User-Agent", get_settings().user_agent)

    last_error: Exception | None = None
    for delay in backoff_delays():
        limiter.wait()
        try:
            _session = session or requests
            resp = _session.request(
                method, url, headers=headers, params=params, data=data, timeout=timeout
            )
            if resp.status_code in (429, 503):
                last_error = SourceError(
                    f"HTTP {resp.status_code} for {url} (rate limited/blocked)"
                )
                time.sleep(delay)  # backoff, then retry
                continue
            if resp.status_code == 403:
                raise SourceError(f"HTTP 403 for {url} — source blocked this scraper")
            resp.raise_for_status()
            body = resp.text
            if cache is not None and method == "GET":
                cache.put(url, body)
            return body
        except (requests.RequestException, SourceError) as exc:
            last_error = exc
            time.sleep(delay)
    raise SourceError(f"fetch failed after backoff for {url}: {last_error}")
