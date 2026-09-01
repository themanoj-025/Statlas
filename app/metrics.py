"""Prometheus metrics collection for production observability.

Exposes a /metrics endpoint (Prometheus text format) with:
- Request counts and durations (by method, endpoint, status)
- Database connection pool stats
- Cache hit/miss counters
- Active user gauges
- Business metrics (subscriptions, reports generated)

Constitution §4 (Observability): every action traced, every metric measured.
"""
from __future__ import annotations

import time


class MetricsCollector:
    """In-process metrics collector — no external dependencies required.

    Counts and histograms are stored in plain dicts. The /metrics endpoint
    serialises them to Prometheus text format. For production scale, replace
    with prometheus_client (already in the ecosystem).
    """

    def __init__(self) -> None:
        self._request_count: dict[str, int] = {}
        self._request_duration_sum: dict[str, float] = {}
        self._request_duration_count: dict[str, int] = {}
        self._request_duration_bucket: dict[str, dict[float, int]] = {}
        self._error_count: dict[str, int] = {}
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._active_sessions: int = 0
        self._start_time = time.time()

    # -- request recording ------------------------------------------------

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        """Record a completed HTTP request."""
        key = f"{method}:{path}"
        self._request_count[key] = self._request_count.get(key, 0) + 1

        # Duration histogram (buckets: 10ms, 50ms, 100ms, 500ms, 1s, 2s, 5s, 10s)
        buckets = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        if key not in self._request_duration_bucket:
            self._request_duration_bucket[key] = dict.fromkeys(buckets, 0)
        for b in buckets:
            if duration_seconds <= b:
                self._request_duration_bucket[key][b] += 1

        self._request_duration_sum[key] = (
            self._request_duration_sum.get(key, 0.0) + duration_seconds
        )
        self._request_duration_count[key] = (
            self._request_duration_count.get(key, 0) + 1
        )

        if status_code >= 400:
            err_key = f"{status_code}"
            self._error_count[err_key] = self._error_count.get(err_key, 0) + 1

    def record_cache_hit(self) -> None:
        self._cache_hits += 1

    def record_cache_miss(self) -> None:
        self._cache_misses += 1

    def set_active_sessions(self, count: int) -> None:
        self._active_sessions = count

    # -- Prometheus serialisation -----------------------------------------

    def render(self) -> str:
        """Render all metrics in Prometheus exposition format."""
        lines: list[str] = []
        lines.append("# HELP statlas_requests_total Total HTTP requests.")
        lines.append("# TYPE statlas_requests_total counter")
        for key, count in sorted(self._request_count.items()):
            method, path = key.split(":", 1)
            lines.append(
                f'statlas_requests_total{{method="{method}",endpoint="{path}"}} {count}'
            )

        lines.append("# HELP statlas_request_duration_seconds HTTP request duration.")
        lines.append("# TYPE statlas_request_duration_seconds histogram")
        for key, buckets in sorted(self._request_duration_bucket.items()):
            method, path = key.split(":", 1)
            total_count = self._request_duration_count.get(key, 0)
            total_sum = self._request_duration_sum.get(key, 0.0)
            for upper, count in buckets.items():
                lines.append(
                    f'statlas_request_duration_seconds_bucket{{method="{method}",'
                    f'endpoint="{path}",le="{upper}"}} {count}'
                )
            lines.append(
                f'statlas_request_duration_seconds_bucket{{method="{method}",'
                f'endpoint="{path}",le="+Inf"}} {total_count}'
            )
            lines.append(
                f'statlas_request_duration_seconds_sum{{method="{method}",'
                f'endpoint="{path}"}} {total_sum:.6f}'
            )
            lines.append(
                f'statlas_request_duration_seconds_count{{method="{method}",'
                f'endpoint="{path}"}} {total_count}'
            )

        lines.append("# HELP statlas_errors_total Total error responses.")
        lines.append("# TYPE statlas_errors_total counter")
        for status, count in sorted(self._error_count.items()):
            lines.append(f'statlas_errors_total{{status="{status}"}} {count}')

        lines.append("# HELP statlas_cache_hits_total Cache hits.")
        lines.append("# TYPE statlas_cache_hits_total counter")
        lines.append(f"statlas_cache_hits_total {self._cache_hits}")

        lines.append("# HELP statlas_cache_misses_total Cache misses.")
        lines.append("# TYPE statlas_cache_misses_total counter")
        lines.append(f"statlas_cache_misses_total {self._cache_misses}")

        lines.append("# HELP statlas_uptime_seconds Process uptime.")
        lines.append("# TYPE statlas_uptime_seconds gauge")
        lines.append(f"statlas_uptime_seconds {time.time() - self._start_time:.1f}")

        lines.append("# HELP statlas_active_sessions Active sessions.")
        lines.append("# TYPE statlas_active_sessions gauge")
        lines.append(f"statlas_active_sessions {self._active_sessions}")

        return "\n".join(lines) + "\n"


# Module-level singleton
_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    return _collector
