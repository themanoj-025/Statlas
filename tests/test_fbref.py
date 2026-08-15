"""FBref scraper unit tests — parsing against the representative fixture HTML
(no network). Validates combined-header parsing, metric extraction against the
registry, position mapping, and loud schema-change failures."""
from __future__ import annotations

import pytest

import app.sources.fbref as fbref_module
from app.sources.base import RawPlayerStatRecord
from app.sources.fbref import FBrefSchemaChangedError, FBrefSource, parse_fbref_table
from tests.conftest import fixtures_dir

FIXTURE = fixtures_dir() / "fbref_league.html"


def _source_with_html(html: str) -> FBrefSource:
    source = FBrefSource(cache=None)
    fbref_module.fetch_with_retry = lambda *a, **k: html  # no network
    return source


@pytest.fixture(autouse=True)
def _restore(monkeypatch):
    yield
    monkeypatch.undo()


def test_combined_headers_are_disambiguated():
    """FBref duplicates column names across sections; combined headers must
    keep them apart (e.g. 'Expected xG' vs 'Per 90 Minutes xG')."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(FIXTURE.read_text(encoding="utf-8"), "html.parser")
    rows = parse_fbref_table(soup, "stats_standard")
    assert rows is not None
    assert len(rows) == 4
    first = rows[0]
    assert first["Standard Gls"] == "24"
    assert first["Expected xG"] == "20.25"
    assert first["Progression PrgC"] == "30"
    assert first["__fbref_id__"] == "aaaaaaaa"


def test_fetch_league_stats_extracts_registry_metrics():
    source = _source_with_html(FIXTURE.read_text(encoding="utf-8"))
    records = source.fetch_league_stats("premier-league", "2025-26")
    assert len(records) == 4

    by_name = {r.player_name: r for r in records}
    haaland: RawPlayerStatRecord = by_name["Erling Haaland"]
    assert haaland.position_group == "ST"
    assert haaland.minutes_played == 2700
    assert haaland.matches_played == 30
    assert haaland.external_ids == {"fbref": "aaaaaaaa"}

    # Hand-computed per-90 values (totals / minutes * 90).
    assert haaland.raw_stats["si_gls_p90"] == pytest.approx(0.8, abs=1e-4)
    assert haaland.raw_stats["si_xg_p90"] == pytest.approx(0.675, abs=1e-4)
    assert haaland.raw_stats["si_sh_p90"] == pytest.approx(2.0, abs=1e-4)
    assert haaland.raw_stats["si_prgp_p90"] == pytest.approx(1.5, abs=1e-4)
    assert haaland.raw_stats["si_prgc_p90"] == pytest.approx(1.0, abs=1e-4)
    assert haaland.raw_stats["si_xag_p90"] == pytest.approx(0.225, abs=1e-4)
    assert haaland.raw_stats["si_kp_p90"] == pytest.approx(1.0, abs=1e-4)
    assert haaland.raw_stats["si_tkl_p90"] == pytest.approx(0.3333, abs=1e-3)
    assert haaland.raw_stats["si_int_p90"] == pytest.approx(0.4, abs=1e-4)
    assert haaland.raw_stats["si_press_p90"] == pytest.approx(5.0, abs=1e-4)
    assert haaland.raw_stats["si_cmp_pct"] == pytest.approx(66.7, abs=1e-4)
    assert haaland.raw_stats["si_dis_p90"] == pytest.approx(0.6667, abs=1e-3)
    # sample-floor counters (percentile eligibility + display rules)
    assert haaland.raw_stats["_cmp_attempts"] == 300

    kdb = by_name["Kevin De Bruyne"]
    assert kdb.position_group == "CM"
    assert kdb.raw_stats["si_cmp_pct"] == pytest.approx(88.9, abs=1e-4)

    salah = by_name["Mohamed Salah"]
    assert salah.position_group == "W"  # FW,MF -> W
    assert salah.raw_stats["si_sh_p90"] == pytest.approx(3.75, abs=1e-4)


def test_goalkeeper_extracts_gk_metrics_only():
    source = _source_with_html(FIXTURE.read_text(encoding="utf-8"))
    records = source.fetch_league_stats("premier-league", "2025-26")
    alisson = next(r for r in records if r.player_name == "Alisson Becker")
    assert alisson.position_group == "GK"
    assert alisson.raw_stats["si_save_pct"] == pytest.approx(78.0, abs=1e-4)
    assert alisson.raw_stats["si_psxg_ga_p90"] == pytest.approx(0.2, abs=1e-4)  # (36-30)/2700*90
    assert alisson.raw_stats["si_ga_p90"] == pytest.approx(1.0, abs=1e-4)
    assert alisson.raw_stats["si_cross_pct"] == pytest.approx(50.0, abs=1e-4)
    assert alisson.raw_stats["_sota_faced"] == 100
    assert alisson.raw_stats["_crosses_faced"] == 50
    # no outfield metrics for a GK
    assert "si_gls_p90" not in alisson.raw_stats


def test_schema_change_raises_loudly():
    source = _source_with_html("<html><body><p>blocked or changed page</p></body></html>")
    with pytest.raises(FBrefSchemaChangedError):
        source.fetch_league_stats("premier-league", "2025-26")


def test_rate_limit_value_is_declared():
    assert FBrefSource().get_rate_limit_seconds() >= 10.0


def test_build_url():
    source = FBrefSource()
    url = source.build_url("premier-league", "2025-26")
    assert url == (
        "https://fbref.com/en/comps/9/2025-2026/Premier-League-Stats"
    )
