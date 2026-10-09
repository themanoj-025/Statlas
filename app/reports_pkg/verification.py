"""B2 — the hard verification gate (code, not prompt)."""

from __future__ import annotations

import re
from typing import Any

from app.reports_pkg.constants import _NARRATIVE_FIELDS

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_ORDINAL_RE = re.compile(r"\b\d+(?:st|nd|rd|th)\b", re.IGNORECASE)


_MASK_LABELS = (
    "statlas index",  # the product term — never a metric claim
    "per 90",  # the per-90 unit label
    "per90",
)


def _mask_labels(text: str, corpus: dict[str, Any]) -> str:
    """Blank out every label that legitimately appears in prose but is not a
    claim: metric display names ("Goals per 90"), the player/club/league names,
    the season string ("2025-26"), and product/unit labels ("Statlas Index",
    "per 90"). The gate then only checks the numbers and metric-shaped phrases
    that genuinely remain."""
    for name in corpus.get("metric_names", ()):
        text = re.sub(re.escape(name), " ", text, flags=re.IGNORECASE)
    for label in (
        corpus.get("player_name"),
        corpus.get("club"),
        corpus.get("league"),
        corpus.get("season"),
    ):
        if label:
            text = re.sub(re.escape(label), " ", text, flags=re.IGNORECASE)
    for label in _MASK_LABELS:
        text = re.sub(re.escape(label), " ", text, flags=re.IGNORECASE)
    return text


def _extract_numbers(text: str, corpus: dict[str, Any] | None = None) -> list[float]:
    """Every number in a text field, ordinals normalised to their integer.

    Labels (metric display names, player/club/league/season, product terms)
    are masked first — they are labels, not claims — and thousand separators
    are stripped so "2,700" reads as 2700.
    """
    if corpus is not None:
        text = _mask_labels(text, corpus)
    text = re.sub(r"(?<=\d),(?=\d)", "", text)  # strip thousand separators
    out: list[float] = []
    cleaned = _ORDINAL_RE.sub(lambda m: m.group(0)[:-2], text)
    for match in _NUMBER_RE.finditer(cleaned):
        try:
            out.append(float(match.group(0)))
        except ValueError:
            continue
    return out


def verify_report(report: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Check every numeric + metric-name claim against the verified corpus.

    Returns {"passed", "unverified": [...], "checked"}. A single unmatched
    number or metric name fails the report — this is the mechanism that makes
    the generator architecturally incapable of shipping an ungrounded claim.
    """
    corpus = context["verification"]
    unverified: list[dict[str, Any]] = []

    def tolerance_ok(value: float) -> bool:
        return any(abs(value - allowed) <= 0.55 for allowed in corpus["numbers"])

    # 1. Narrative text fields.
    for section_key, field in _NARRATIVE_FIELDS:
        section = report.get("sections", {}).get(section_key)
        if not section:
            continue
        text = section.get(field, "")
        for number in _extract_numbers(text, corpus):
            if not tolerance_ok(number):
                unverified.append(
                    {
                        "claim": f"number {number:g} in '{section_key}.{field}'",
                        "source": section_key,
                        "kind": "number",
                    }
                )
        # Metric-shaped phrases must be real corpus metric names. Labels are
        # masked first, so anything still containing a metric-vocabulary word
        # is a genuine invented-metric reference (e.g. "Progressive Passes Per
        # 85" — the number is caught above AND the label here).
        vocab = {
            w
            for name in corpus["metric_names"]
            for w in name.split()
            if len(w) > 3 and w.isalpha()
        }
        vocab |= {"percentile", "percentiles", "index"}
        masked = _mask_labels(text, corpus)
        for token in re.findall(r"[A-Z][a-zA-Z]+(?: [A-Za-z]+){0,3}", masked):
            lowered = token.strip().lower()
            words = set(lowered.split())
            if lowered in corpus["metric_names"]:
                continue  # a real metric name (should not survive masking)
            if words & vocab:
                unverified.append(
                    {
                        "claim": f"unrecognised metric-like term '{token.strip()}' in '{section_key}'",
                        "source": section_key,
                        "kind": "term",
                    }
                )

    # 2. Strengths / weaknesses: supporting_metric must exist in the corpus,
    #    and their values/percentiles must match.
    for item_key in ("strengths", "weaknesses"):
        for item in report.get("sections", {}).get(item_key, []):
            metric = item.get("supporting_metric")
            if metric and metric not in corpus["metric_ids"]:
                unverified.append(
                    {
                        "claim": f"unknown metric '{metric}' in {item_key}",
                        "source": item_key,
                        "kind": "metric",
                    }
                )
            for field in ("value", "percentile"):
                value = item.get(field)
                if value is not None and not tolerance_ok(float(value)):
                    unverified.append(
                        {
                            "claim": f"{item_key} {field} {value!r} not in corpus",
                            "source": item_key,
                            "kind": "number",
                        }
                    )

    # 3. Comparables must be a subset of the real Phase 6 results (B3).
    context_ids = {c["player_id"] for c in context["comparables"]}
    context_sims = {
        (c["player_id"], round(float(c["similarity"]), 4))
        for c in context["comparables"]
    }
    for comparable in report.get("sections", {}).get("comparable_players", []):
        pid = comparable.get("player_id")
        sim = comparable.get("similarity")
        if pid not in context_ids:
            unverified.append(
                {
                    "claim": f"comparable player {pid} not in real Phase 6 results",
                    "source": "comparable_players",
                    "kind": "comparable",
                }
            )
        if sim is not None and (pid, round(float(sim), 4)) not in context_sims:
            unverified.append(
                {
                    "claim": f"similarity {sim} for player {pid} not in real results",
                    "source": "comparable_players",
                    "kind": "number",
                }
            )

    # 4. Confidence level must equal the deterministic computation.
    expected_level = context["confidence"]["level"]
    actual_level = (
        report.get("sections", {}).get("recommendation", {}).get("confidence_level")
    )
    if actual_level != expected_level:
        unverified.append(
            {
                "claim": f"confidence_level '{actual_level}' != computed '{expected_level}'",
                "source": "recommendation",
                "kind": "confidence",
            }
        )

    return {
        "passed": not unverified,
        "unverified": unverified,
        "checked": True,
    }
