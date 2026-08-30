"""Shared source-infrastructure tests (app/sources/base.py).

Regression coverage for the compliance-declared backoff schedule — the
pre-fix implementation infinite-looped once the delay reached the cap
(d = min(d * factor, cap) keeps d == cap, so `while d <= cap` never exits),
which surfaced as a MemoryError only on a live fetch. Fixture-only tests
never exercised the fetch path, which is exactly why this unit test exists.
"""

from __future__ import annotations

from app.sources.base import backoff_delays


def test_backoff_delays_matches_documented_schedule() -> None:
    """data-compliance-notes.md declares: 1s -> 2s -> 4s -> 8s -> 16s -> 30s -> 60s cap."""
    assert backoff_delays() == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 60.0]


def test_backoff_delays_terminates_and_ends_at_cap() -> None:
    """The list must be FINITE and end exactly at the cap (regression: the
    original looped forever once d reached cap -> MemoryError)."""
    delays = backoff_delays()
    assert delays[-1] == 60.0
    assert len(delays) < 100  # finiteness proof


def test_backoff_delays_custom_cap() -> None:
    assert backoff_delays(initial=1.0, factor=2.0, cap=8.0) == [1.0, 2.0, 4.0, 8.0]
