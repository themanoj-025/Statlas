"""Understat scraper unit tests — extraction from the embedded playersDataObject
JSON fixture (no network).

LIVE-DRIFT REGRESSION (2026-08-14): Understat stopped embedding the payload in
league-page HTML; the current player table comes from a POST endpoint. The
parser tries the embedded payload first, then falls back to the API response
fixture (understat_api_players.json, a labeled sample of the real live
response), then fails loudly.
"""
from __future__ import annotations

import json

import pytest

import app.sources.understat as understat_module
from app.sources.base import SchemaChangedError
from app.sources.understat import (
    UnderstatSchemaChangedError,
    UnderstatSource,
    extract_players_json,
)
from tests.conftest import fixtures_dir

FIXTURE = fixtures_dir() / "understat_page.html"
API_FIXTURE = fixtures_dir() / "understat_api_players.json"


def _source_with_html(html: str) -> UnderstatSource:
    source = UnderstatSource(cache=None)
    understat_module.fetch_with_retry = lambda *a, **k: html
    return source


def test_extract_players_json():
    data = extract_players_json(FIXTURE.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["player_name"] == "Erling Haaland"
    assert data[0]["xG"] == "20.25"
    assert data[0]["time"] == "2700"


def test_missing_payload_raises():
    with pytest.raises(UnderstatSchemaChangedError):
        extract_players_json("<html><body>nothing here</body></html>")


def test_fetch_league_stats_per90_values():
    source = _source_with_html(FIXTURE.read_text(encoding="utf-8"))
    records = source.fetch_league_stats("premier-league", "2025-26")
    assert len(records) == 2

    haaland = next(r for r in records if r.player_name == "Erling Haaland")
    assert haaland.minutes_played == 2700
    assert haaland.external_ids == {"understat": 123}
    assert haaland.position_code == "F"
    # Hand-computed per-90 values from season totals.
    assert haaland.raw_stats["si_xg_p90"] == pytest.approx(0.675, abs=1e-4)
    assert haaland.raw_stats["si_xag_p90"] == pytest.approx(0.225, abs=1e-4)
    assert haaland.raw_stats["si_sh_p90"] == pytest.approx(2.0, abs=1e-4)
    assert haaland.raw_stats["si_kp_p90"] == pytest.approx(1.0, abs=1e-4)
    assert haaland.raw_stats["si_gls_p90"] == pytest.approx(0.8, abs=1e-4)


def test_big5_only_guard():
    """C4 closeout: specific exception type, not a blind `pytest.raises(Exception)`."""
    source = UnderstatSource(cache=None)
    with pytest.raises(SchemaChangedError):
        source.build_url("championship", "2025-26")  # no understat id configured


def test_falls_back_to_players_api_when_payload_dropped():
    """Live drift regression: a league page WITHOUT the embedded payload must
    fall back to the POST endpoint (labeled real-response fixture) instead of
    failing — and must raise loudly only when BOTH paths fail."""
    calls: list[tuple[str, dict]] = []

    def fake_fetch(url, *, method="GET", data=None, **kw):
        calls.append((method, dict(data or {})))
        if method == "POST":
            return json.dumps(json.loads(API_FIXTURE.read_text(encoding="utf-8")))
        return "<html><body>no embedded payload here</body></html>"

    source = UnderstatSource(cache=None)
    original = understat_module.fetch_with_retry
    understat_module.fetch_with_retry = fake_fetch
    try:
        records = source.fetch_league_stats("premier-league", "2025-26")
    finally:
        understat_module.fetch_with_retry = original

    # POST fallback hit with the canonical league id + year.
    assert len(calls) == 2
    assert calls[1][0] == "POST"
    assert calls[1][1] == {"league": "EPL", "season": "2025"}

    assert len(records) == 2
    haaland = next(r for r in records if r.player_name == "Erling Haaland")
    assert haaland.raw_stats["si_gls_p90"] > 0
    assert haaland.external_ids == {"understat": 8260}  # real id from the live response fixture
    salah = next(r for r in records if r.player_name == "Mohamed Salah")
    assert salah.raw_stats["si_gls_p90"] == pytest.approx(29 / 3392 * 90, abs=1e-3)


def test_api_fallback_raises_loudly_on_bad_payload():
    """A POST response that is not a success payload must raise loudly — never
    a partial/empty guess."""

    def fake_fetch(url, *, method="GET", data=None, **kw):
        if method == "POST":
            return "{\"success\": false}"
        return "<html><body>no payload</body></html>"

    source = UnderstatSource(cache=None)
    original = understat_module.fetch_with_retry
    understat_module.fetch_with_retry = fake_fetch
    try:
        with pytest.raises(UnderstatSchemaChangedError):
            source.fetch_league_stats("premier-league", "2025-26")
    finally:
        understat_module.fetch_with_retry = original
