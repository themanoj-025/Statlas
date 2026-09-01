"""B1/B2 — narrators (step 2 of the pipeline)."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import get_settings
from app.reports_pkg.constants import ReportNotConfigured

logger = logging.getLogger(__name__)


def deterministic_narrator(
    context: dict[str, Any], correction: str | None = None
) -> dict[str, Any] -> None:
    """A narrator that can ONLY emit context values — used by tests and dev
    seeding. It writes real, grounded prose from the context object; every
    number is pulled from the corpus by construction, so the verification gate
    always passes on its output (and any bug in it is caught by the gate).
    """
    player = context["player"]
    pct = context["percentiles"]["values"]
    raw = context["raw"]["values"]
    metrics = context["metrics"]
    index = context["percentiles"].get("index")
    minutes = context["raw"]["minutes_played"]
    matches = context["raw"]["matches_played"]

    def _top(n: int = 3) -> list[tuple[str, float, float | None]]:
        """Highest-percentile metrics (metric id, percentile, raw)."""
        rows = sorted(
            ((m, pct.get(m), raw.get(m)) for m in pct if pct.get(m) is not None),
            key=lambda r: -r[1],
        )
        return rows[:n]

    def _bottom(n: int = 3) -> list[tuple[str, float, float | None]]:
        rows = sorted(
            ((m, pct.get(m), raw.get(m)) for m in pct if pct.get(m) is not None),
            key=lambda r: r[1],
        )
        return rows[:n]

    def _fmt(value: float | None, digits: int = 1) -> str:
        if value is None:
            return "N/A"
        return f"{value:.{digits}f}"

    top = _top()
    bottom = _bottom()

    strengths = [
        {
            "point": (
                f"Ranks in the {_fmt(t[1], 0)}th percentile for "
                f"{metrics[t[0]]['name'].lower()} ({_fmt(t[2])} per 90) — "
                f"a genuine standout versus the {player['position_group']} "
                "cohort in this league tier."
            ),
            "supporting_metric": t[0],
            "value": t[2],
            "percentile": t[1],
            "source_calls": ["percentiles", "raw_stats"],
        }
        for t in top
    ]
    weaknesses = [
        {
            "point": (
                f"Sits at the {_fmt(b[1], 0)}th percentile for "
                f"{metrics[b[0]]['name'].lower()} ({_fmt(b[2])} per 90) — "
                "the clearest gap in the profile versus the cohort."
            ),
            "supporting_metric": b[0],
            "value": b[2],
            "percentile": b[1],
            "source_calls": ["percentiles", "raw_stats"],
        }
        for b in bottom
    ]

    comparables = []
    for c in context["comparables"]:
        comparables.append(
            {
                "player_id": c["player_id"],
                "name": c["name"],
                "club": c.get("club"),
                "similarity": c["similarity"],
                "explanation": c.get("explanation", {}),
            }
        )

    trend_points = context["trend"].get("points", [])
    if len(trend_points) >= 2:
        first_raw, last_raw = trend_points[0]["raw"], trend_points[-1]["raw"]
        direction = (
            "risen"
            if (last_raw or 0) > (first_raw or 0)
            else ("fallen" if (last_raw or 0) < (first_raw or 0) else "held steady")
        )
        trend_summary = (
            f"Over the {len(trend_points)} most recent weekly snapshots, the "
            f"{context['index_metric_name'].lower()} has {direction} from "
            f"{_fmt(first_raw)} to {_fmt(last_raw)} (snapshot granularity, "
            "not per-match data)."
        )
    else:
        trend_summary = (
            f"Fewer than two usable snapshots are available for the "
            f"{context['index_metric_name'].lower()} trend — insufficient to "
            "describe a trajectory."
        )

    risk_factors = [
        {"point": r["point"], "basis": r["basis"]} for r in context["risk_factors"]
    ]

    workspace_context = None
    if context.get("workspace_context"):
        wc = context["workspace_context"]
        workspace_context = {
            "shortlist_status": wc["shortlist_status"],
            "priority": wc["priority"],
            "tags": wc["tags"],
            "recent_notes": wc["recent_notes"],
            "label": wc["label"],
        }

    return {
        "sections": {
            "overview": {
                "text": (
                    f"{player['name']} is a {player['position_label'] or player['position_group']} "
                    f"for {player['club']}, assessed against the "
                    f"{player['position_group']} cohort in {context['raw']['league'] or 'their league'}. "
                    f"Across {matches} matches and {_fmt(minutes, 0)} minutes this season "
                    f"({context['raw']['season'] or 'current season'}), the profile is defined by "
                    f"{metrics[top[0][0]]['name'].lower()} (top strength) with a "
                    f"{'Statlas Index of ' + _fmt(index, 1) if index is not None else 'Statlas Index pending'}."
                ),
                "source_calls": ["profile", "percentiles", "raw_stats"],
            },
            "statistical_profile": {
                "metrics": [
                    {
                        "metric": m,
                        "metric_name": metrics[m]["name"],
                        "value": raw.get(m),
                        "percentile": pct.get(m),
                    }
                    for m in pct
                    if pct.get(m) is not None or raw.get(m) is not None
                ],
                "source_calls": ["percentiles", "raw_stats"],
            },
            "role_and_position": {
                "text": (
                    f"{player['name']} is listed as {player['position_label'] or 'unknown'} "
                    f"({player['position_group']} group). In {context['raw']['league'] or 'their league'}, "
                    f"the role profile is {metrics[top[0][0]]['name'].lower()}-led; the weakest "
                    f"dimension is {metrics[bottom[0][0]]['name'].lower()}."
                ),
                "source_calls": ["profile", "percentiles"],
            },
            "strengths": strengths,
            "weaknesses": weaknesses,
            "comparable_players": comparables,
            "development_trajectory": {
                "trend_summary": trend_summary,
                "metric": context["index_metric_id"],
                "source_calls": ["trend"],
            },
            "risk_factors": risk_factors,
            "recommendation": {
                "text": (
                    f"Profile is {context['confidence']['level']} confidence based on the factors "
                    f"stated below. Monitor {metrics[top[0][0]]['name'].lower()} and the "
                    f"{context['index_metric_name'].lower()} trend over the next snapshots "
                    "before a final call."
                ),
                "confidence_level": context["confidence"]["level"],
                "confidence_rationale": context["confidence"]["rationale"],
            },
            "workspace_context": workspace_context,
        },
        "confidence": context["confidence"],
    }


def _narrate_via_anthropic(
    context: dict[str, Any], correction: str | None = None
) -> dict[str, Any]:
    """The real LLM narrator (key-gated). Receives ONLY the verified context
    and must produce the report JSON; the verification gate still runs on its
    output regardless of how careful the prompt is.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ReportNotConfigured(
            "Report generation is not configured on this deployment "
            "(ANTHROPIC_API_KEY unset)."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    corpus_preview = {
        "numbers": sorted(context["verification"]["numbers"]),
        "metric_names": sorted(context["verification"]["metric_names"]),
    }
    # The model sees the context WITHOUT the internal corpus; the corpus is
    # used only by the gate. We give it the real data object (minus helpers).
    model_context = {k: v for k, v in context.items() if k != "verification"}
    model_context["verification"] = corpus_preview

    system = (
        "You generate Statlas scouting reports. NON-NEGOTIABLE: you may ONLY "
        "use numbers and metric names present in the provided context. You "
        "NEVER invent a statistic, percentile, similarity score, or fact. "
        "Every number you write must appear in the context's data. "
        "You return ONLY a JSON object matching the report structure: "
        "{'sections': {overview: {text, source_calls}, statistical_profile: "
        "{metrics: [{metric, metric_name, value, percentile}], source_calls}, "
        "role_and_position: {text, source_calls}, strengths: [{point, "
        "supporting_metric, value, percentile, source_calls}], weaknesses: [...], "
        "comparable_players: [{player_id, name, similarity, explanation}], "
        "development_trajectory: {trend_summary, metric, source_calls}, "
        "risk_factors: [{point, basis}], recommendation: {text, "
        "confidence_level, confidence_rationale}, workspace_context: {...} }, "
        "confidence: {level, rationale, factors}}. "
        "confidence_level MUST equal the context's confidence.level. "
        "comparable_players MUST be drawn exactly from the context's comparables. "
        "risk_factors MUST be drawn exactly from the context's risk_factors. "
        "Use source_calls keys from the context (profile, percentiles, "
        "raw_stats, trend, workspace)."
    )
    if correction:
        system += (
            "\n\nYour previous attempt FAILED verification for these reasons: "
            f"{correction}. Correct every listed claim to match the context "
            "exactly and resubmit."
        )

    response = client.messages.create(
        model=settings.assistant_model,
        max_tokens=4096,
        system=system,
        messages=[
            {
                "role": "user",
                "content": "Generate the report JSON from this verified context: "
                + json.dumps(model_context, default=str),
            }
        ],
    )
    text = "".join(
        getattr(b, "text", "")
        for b in response.content
        if getattr(b, "type", "") == "text"
    )
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("narrator returned no JSON object")
    parsed = json.loads(text[start : end + 1])
    if "sections" not in parsed:
        raise ValueError("narrator JSON missing 'sections'")
    return parsed
