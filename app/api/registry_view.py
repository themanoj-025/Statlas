"""Public registry view — the API's single source of metric metadata.

The Metric Registry (config/metric_registry.json, generated from
methodology.md) is the source of truth for metric names, units, definitions,
directions, null-vs-zero policies, and floors. The frontend never hardcodes any
of this: it renders whatever this view returns (methodology-as-code, §5).

Unit strings mirror methodology.md §2 (e.g. goals/90, percentage).
"""

from __future__ import annotations

from typing import Any

from app.config import load_registry, load_tiers

UNITS: dict[str, str] = {
    "si_gls_p90": "goals / 90",
    "si_xg_p90": "xG / 90",
    "si_sh_p90": "shots / 90",
    "si_prgp_p90": "passes / 90",
    "si_prgc_p90": "carries / 90",
    "si_xag_p90": "xAG / 90",
    "si_kp_p90": "key passes / 90",
    "si_tkl_p90": "tackles / 90",
    "si_int_p90": "interceptions / 90",
    "si_press_p90": "pressures / 90",
    "si_cmp_pct": "percentage",
    "si_dis_p90": "events / 90",
    "si_save_pct": "percentage",
    "si_psxg_ga_p90": "goals / 90",
    "si_ga_p90": "goals / 90",
    "si_cross_pct": "percentage",
}

DEFINITIONS: dict[str, str] = {
    "si_gls_p90": "Goals scored per 90 minutes.",
    "si_xg_p90": "Expected goals per 90 minutes. Tier 1 uses the Understat model; Tiers 2–3 use FBref's Opta model — one model per comparison group.",
    "si_sh_p90": "Total shots taken per 90 minutes.",
    "si_prgp_p90": "Completed passes that move the ball at least 10 yards toward the opponent's goal, or into the penalty area, per 90.",
    "si_prgc_p90": "Carries that move the ball at least 10 yards toward the opponent's goal, or into the penalty area, per 90.",
    "si_xag_p90": "Expected assisted goals per 90 minutes.",
    "si_kp_p90": "Passes that lead directly to a shot, per 90.",
    "si_tkl_p90": "Number of players tackled (successful tackles) per 90.",
    "si_int_p90": "Interceptions per 90 minutes.",
    "si_press_p90": "Total pressing actions (applying pressure to a player controlling the ball) per 90.",
    "si_cmp_pct": "Completed passes as a share of attempted passes. Shown only for players with at least 50 attempts.",
    "si_dis_p90": "Times the player is dispossessed while attempting to control the ball, per 90. Lower is better.",
    "si_save_pct": "Saves as a share of shots on target faced. Shown only for players with at least 20 shots on target faced.",
    "si_psxg_ga_p90": "Post-shot expected goals faced minus goals conceded, per 90 — goals prevented above or below expectation.",
    "si_ga_p90": "Goals conceded per 90 minutes. Lower is better.",
    "si_cross_pct": "Share of crosses faced that the goalkeeper successfully stopped or claimed. Shown only for players with at least 10 crosses faced.",
}

POSITION_LABELS: dict[str, str] = {
    "GK": "Goalkeeper",
    "CB": "Centre-back",
    "FB": "Full-back",
    "DM": "Defensive midfield",
    "CM": "Central midfield",
    "AM": "Attacking midfield",
    "W": "Wide attacker",
    "ST": "Striker",
}

POSITION_PLURALS: dict[str, str] = {
    "GK": "Goalkeepers",
    "CB": "Centre-backs",
    "FB": "Full-backs",
    "DM": "Defensive midfielders",
    "CM": "Central midfielders",
    "AM": "Attacking midfielders",
    "W": "Wide attackers",
    "ST": "Strikers",
}

TIER_LABELS: dict[str, str] = {
    "tier_1": "Tier 1",
    "tier_2": "Tier 2",
    "tier_3": "Tier 3",
}


def metric_meta(registry: dict[str, Any], mid: str) -> dict[str, Any] | None:
    spec = registry["metrics"].get(mid)
    if spec is None:
        return None
    return {
        "id": mid,
        "name": spec["name"],
        "unit": UNITS.get(mid, ""),
        "definition": DEFINITIONS.get(mid, ""),
        "direction": spec["direction"],
        "lower_is_better": spec["direction"] == "lower_is_better",
        "null_vs_zero": spec.get("null_vs_zero", "zero_when_genuine"),
        "display_floor": spec.get("display_floor"),
        "kind": spec.get("kind", "per90"),
    }


def public_meta() -> dict[str, Any]:
    """Everything the frontend needs to render metric-aware UI + methodology."""
    registry = load_registry()
    tiers_cfg = load_tiers()
    metrics = {mid: metric_meta(registry, mid) for mid in registry["metrics"]}

    position_groups = []
    for code in registry["position_groups"]:
        metric_ids = (
            registry["gk_metrics"] if code == "GK" else registry["outfield_metrics"]
        )
        position_groups.append(
            {
                "code": code,
                "label": POSITION_LABELS[code],
                "plural": POSITION_PLURALS[code],
                "metric_ids": metric_ids,
                "weights": registry["position_weights"].get(code, {}),
            }
        )

    tiers = [
        {
            "code": tier,
            "label": TIER_LABELS[tier],
            "league_slugs": leagues,
        }
        for tier, leagues in tiers_cfg["tiers"].items()
    ]

    return {
        "qualifying_minutes": registry["qualifying_minutes"],
        "display_floor_minutes": registry["display_floor_minutes"],
        "min_pool_size": registry["min_pool_size"],
        "index_metric_id": registry["index_metric_id"],
        "metrics": metrics,
        "position_groups": position_groups,
        "tiers": tiers,
        "weekly_refresh": "Every Wednesday 03:00 UTC the pipeline ingests the previous match week and recomputes percentiles immediately after (percentile-rules.md §3).",
    }
