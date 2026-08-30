"""Constitution §3 CI validation — coverage matrix and Metric Registry.

The Constitution requires "The coverage matrix and Metric Registry are
validated by a CI check (schema validity, uniqueness of metric IDs, no UI
claims beyond the matrix)." This test file is that check: it runs in the normal
pytest suite (and therefore CI), so a registry that drifts from the locked
methodology, or a coverage claim beyond the matrix, fails the build.

These tests read config files directly (no DB) so they run fast and are
independent of the fixture dataset.
"""

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "app" / "config" / "metric_registry.json"
TIERS_PATH = PROJECT_ROOT / "app" / "config" / "tiers.json"
COVERAGE_MATRIX_PATH = PROJECT_ROOT / "data" / "coverage_matrix.json"

# Position groups locked in methodology.md / percentile-rules.md.
EXPECTED_POSITION_GROUPS = {"GK", "CB", "FB", "DM", "CM", "AM", "W", "ST"}


@pytest.fixture(scope="module")
def registry():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tiers():
    return json.loads(TIERS_PATH.read_text(encoding="utf-8"))


# --- Metric Registry: schema validity + uniqueness (Constitution §3) ---------


def test_registry_has_schema_version_and_required_keys(registry) -> None:
    assert isinstance(registry["schema_version"], int)
    for key in (
        "qualifying_minutes",
        "min_pool_size",
        "index_metric_id",
        "position_groups",
        "metrics",
        "position_weights",
    ):
        assert key in registry, f"registry missing required key {key!r}"


def test_metric_ids_are_unique_and_well_formed(registry) -> None:
    ids = list(registry["metrics"].keys())
    assert len(ids) == len(set(ids)), "duplicate metric IDs in registry"
    for mid in ids:
        # Locked naming convention: si_<abbrev>_<unit> (e.g. si_gls_p90).
        assert mid.startswith("si_"), f"metric id {mid!r} violates si_ prefix rule"


def test_every_metric_defines_direction_unit_and_bounds(registry) -> None:
    for mid, m in registry["metrics"].items():
        assert m["direction"] in {"higher_is_better", "lower_is_better"}, mid
        assert m["kind"] in {
            "per90",
            "percent",
            "count",
            "rate",
            "derived",
        }, f"{mid} bad kind {m['kind']!r}"
        lo, hi = m["bounds"]
        assert lo < hi, f"{mid} bounds must be ordered (lo < hi)"
        if m["kind"] == "derived":
            # Derived metrics (e.g. PSxG minus GA) must declare their formula
            # and inputs rather than a direct source column.
            assert m.get("formula"), f"{mid} derived but has no formula"
            assert m.get("inputs"), f"{mid} derived but has no inputs"
        else:
            assert "fbref" in m or "understat" in m, f"{mid} has no source mapping"


def test_position_groups_match_methodology(registry) -> None:
    assert set(registry["position_groups"]) == EXPECTED_POSITION_GROUPS


def test_every_position_weights_row_sums_to_1(registry) -> None:
    weights = registry["position_weights"]
    assert set(weights.keys()) == EXPECTED_POSITION_GROUPS
    for group, row in weights.items():
        total = sum(row.values())
        assert total == pytest.approx(
            1.0, abs=1e-6
        ), f"{group} weights sum to {total}, must be 1.0"
        # Every weight cell must reference a real metric id.
        for mid in row:
            assert (
                mid in registry["metrics"]
            ), f"{group} references unknown metric {mid!r}"


def test_gk_and_outfield_metric_lists_are_consistent(registry) -> None:
    outfield = set(registry["outfield_metrics"])
    gk = set(registry["gk_metrics"])
    assert outfield.isdisjoint(gk), "outfield and GK metric lists overlap"
    assert outfield | gk == set(
        registry["metrics"].keys()
    ), "metric lists do not cover the registry exactly"


def test_anomaly_bounds_match_metric_bounds(registry) -> None:
    for mid, m in registry["metrics"].items():
        bounds = m["bounds"]
        # Only `derived` differential metrics (e.g. PSxG minus GA) may span
        # negative values; raw per-90 metrics never should.
        if m["kind"] != "derived":
            assert bounds[0] >= 0, f"{mid} allows negative values"
        assert m["display_floor"]["type"] in {
            "minutes",
            "count",
            "percent",
            "attempts",
        }, mid
        # Bounds must be sane: no statistically impossible ranges (Constitution
        # anomaly gate — e.g. 50 goals in 5 matches must be outside the bounds).
        lo, hi = bounds
        assert lo < hi, f"{mid} bounds must be ordered"
        assert abs(hi) <= 100 and abs(lo) <= 100, f"{mid} bounds implausible: {bounds}"


# --- League tiers: schema validity (percentile-rules.md) ---------------------


def test_tiers_schema(registry, tiers) -> None:
    assert tiers["schema_version"] >= 1
    leagues = tiers["leagues"]
    assert isinstance(leagues, dict) and len(leagues) > 0
    tier_1 = tiers["tiers"]["tier_1"]
    assert len(tier_1) >= 5, "tier_1 must contain the top-5 leagues"
    for slug, league in leagues.items():
        assert league["tier"] in {"tier_1", "tier_2", "tier_3"}
        for key in ("name", "country", "external_ids"):
            assert key in league, f"league {slug} missing {key!r}"
        # Every tier-list slug must resolve to a league entry, and vice versa.
        assert slug in tiers["tiers"][league["tier"]], f"{slug} not in its tier list"
    listed = {s for group in tiers["tiers"].values() for s in group}
    assert listed == set(leagues.keys()), "tier lists and leagues dict disagree"


# --- Coverage matrix: no UI claim beyond the matrix (Constitution §3) --------


def test_coverage_matrix_exists_and_is_valid_schema() -> None:
    assert (
        COVERAGE_MATRIX_PATH.exists()
    ), "data/coverage_matrix.json missing — run scripts/seed_dev_db.py"
    matrix = json.loads(COVERAGE_MATRIX_PATH.read_text(encoding="utf-8"))
    assert matrix["schema_version"] >= 1
    assert matrix["dataset_mode"] in {"fixture-demo", "production"}
    assert len(matrix["rows"]) > 0


def test_coverage_matrix_rows_are_well_formed() -> None:
    matrix = json.loads(COVERAGE_MATRIX_PATH.read_text(encoding="utf-8"))
    seen = set()
    for row in matrix["rows"]:
        key = (row["source"], row["source_identifier"])
        assert key not in seen, f"duplicate coverage row {key}"
        seen.add(key)
        assert row["status"] in {"active", "stale", "failed"}
        assert isinstance(row["seasons_available"], list) and row["seasons_available"]
        assert row["last_successful_scrape"], "missing last_successful_scrape"


def test_ui_coverage_page_claims_match_matrix() -> None:
    """The /data-coverage page copy must not claim more than the matrix holds."""
    matrix = json.loads(COVERAGE_MATRIX_PATH.read_text(encoding="utf-8"))
    sources = {row["source"] for row in matrix["rows"]}
    active = {row["source"] for row in matrix["rows"] if row["status"] == "active"}
    page = (PROJECT_ROOT / "web" / "app" / "data-coverage" / "page.tsx").read_text(
        encoding="utf-8"
    )
    # Page may only name sources that exist in the matrix.
    for source in ("fbref", "understat", "statsbomb", "api_football"):
        if source in page.lower():
            assert (
                source in sources
            ), f"UI claims source {source!r} not in coverage matrix"
    # An 'active' claim in the UI requires an active row in the matrix.
    if "active" in page.lower():
        assert len(active) > 0, "UI claims active coverage but matrix has none"


def test_dataset_banner_reflects_matrix_mode() -> None:
    """The site-wide dataset banner must mirror the matrix's mode.

    The banner is client-rendered from GET /api/v1/meta, which serves
    Settings.dataset_mode; the matrix file is generated from the same setting
    during seed. A mismatch means the honesty label drifted from what the
    coverage matrix claims.
    """
    matrix = json.loads(COVERAGE_MATRIX_PATH.read_text(encoding="utf-8"))
    banner = (PROJECT_ROOT / "web" / "components" / "DatasetBanner.tsx").read_text(
        encoding="utf-8"
    )
    mode = matrix["dataset_mode"]  # fixture-demo | production
    assert mode in ("fixture-demo", "production")
    # Production mode hides the banner entirely; fixture mode must render it.
    if mode == "production":
        assert 'mode === "production"' in banner and "return null" in banner
    else:
        assert "Development dataset" in banner
