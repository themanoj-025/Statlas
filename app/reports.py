"""AI scouting reports — the grounded report pipeline (Phase 9).

The Constitution's Never-List #4 applied to a PERSISTED, shareable artifact:
a report outlives the session that generated it, so a system prompt is not
enough. This module enforces grounding architecturally:

    1. gather_report_context()  — deterministic: every number the report may
       contain comes from the real query layer (the same functions the REST
       API and pages use). The context carries a verification corpus: every
       value + metric name that may legally appear.
    2. narrate()                — an injectable narrator (LLM via Anthropic, or
       the deterministic narrator used by tests/dev seeding) receives ONLY the
       context and must produce the report JSON without introducing new data.
    3. verify_report()          — the HARD gate (code, not prompt): every
       number and metric name in the narrative is checked against the corpus;
       comparables must be a subset of real Phase 6 results; the confidence
       level must equal the deterministic computation. A failure retries once
       with the mismatches fed back; a second failure stores the report as
       status="needs_review" — never silently shipped.

Confidence (A2) and risk factors (A3) are deterministic functions of real
signals — documented in docs/product/scouting-reports.md §§3-4.

Quota (D5): reports consume a SEPARATE report_quotas allowance, never the
Phase 4 chat quota (a shared pool would cause confusing "why did my chat quota
drop" experiences). Ownership (D4): every read/write verifies user_id;
foreign/missing ids raise ReportNotFound -> HTTP 404 (never a 403 that leaks
existence), exactly like Phase 7/8.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.auth import effective_plan, has_pro_access
from app.config import get_settings, load_registry, plan_limits
from app.models import (
    MatchEvent,
    Player,
    Report,
    ReportQuota,
    StatSnapshot,
)
from app.queries import player_queries, similar_players, trend_queries

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (documented in docs/product/scouting-reports.md)
# ---------------------------------------------------------------------------

CONFIDENCE_WEIGHTS = {"sample_size": 0.5, "data_completeness": 0.3, "recency": 0.2}
CONFIDENCE_HIGH = 0.85
CONFIDENCE_MEDIUM = 0.60

# Age vs. position development curve (scouting-reports.md §4). Typical peak
# ranges by position group — the ONLY age-based risk signal the generator uses.
POSITION_PEAK_AGES: dict[str, tuple[int, int]] = {
    "GK": (26, 33),
    "CB": (26, 33),
    "FB": (24, 30),
    "DM": (24, 30),
    "CM": (24, 30),
    "AM": (22, 28),
    "W": (22, 28),
    "ST": (23, 29),
}

REPORT_SOURCE_LABEL = "player_profile"
WORKSPACE_SOURCE_LABEL = "shortlist_entry"

OUT_OF_SCOPE_RISK = (
    "Not assessed: injury history, attitude and off-field factors are outside "
    "what Statlas data can support — this report does not cover them."
)

MIN_RECENT_NOTES = 3  # most recent workspace notes included in the report

# Narrative text fields verified by verify_report (walked for numbers/metrics).
_NARRATIVE_FIELDS = (
    ("overview", "text"),
    ("role_and_position", "text"),
    ("development_trajectory", "trend_summary"),
    ("recommendation", "text"),
)


# ---------------------------------------------------------------------------
# Domain errors
# ---------------------------------------------------------------------------


class ReportNotFound(ValueError):
    """Missing OR not owned — mapped to HTTP 404 (existence must not leak)."""


class ReportLimitExceeded(ValueError):
    """Free tier or quota cap reached — honest, specific upsell message."""


class ReportNotConfigured(ValueError):
    """ANTHROPIC_API_KEY unset — honest \"not configured\" state, never a scripted demo."""


class PlayerHasNoData(ValueError):
    """The player has no published percentile data — a report cannot be grounded."""


# ---------------------------------------------------------------------------
# A2 — deterministic confidence scoring (never LLM self-assessment)
# ---------------------------------------------------------------------------


def compute_report_confidence(
    *,
    minutes_played: float,
    qualifying_minutes: float,
    metrics_present: int,
    metrics_expected: int,
    snapshot_date: datetime,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Confidence level from real, checkable factors only.

    Factors (scouting-reports.md §3): sample size (minutes ÷ qualification
    threshold), data completeness (fraction of the position's metric set
    present), and recency (days since the snapshot). Composite = weighted
    mean; high >= 0.85, medium >= 0.60, else low. The rationale names the
    actual factor values so the claim is checkable.
    """
    now = now or datetime.now(timezone.utc)

    ratio = minutes_played / qualifying_minutes if qualifying_minutes else 0.0
    if ratio >= 3.0:
        sample_level, sample_score = "full-season", 1.0
    elif ratio >= 1.5:
        sample_level, sample_score = "solid", 0.8
    elif ratio >= 1.0:
        sample_level, sample_score = "qualifying", 0.6
    else:
        sample_level, sample_score = "below-threshold", 0.3

    fraction = metrics_present / metrics_expected if metrics_expected else 0.0
    if fraction >= 0.9:
        completeness_level, completeness_score = "complete", 1.0
    elif fraction >= 0.6:
        completeness_level, completeness_score = "partial", 0.7
    else:
        completeness_level, completeness_score = "sparse", 0.4

    snap = snapshot_date
    if snap.tzinfo is None:
        snap = snap.replace(tzinfo=timezone.utc)
    recency_days = max(0, int((now - snap).total_seconds() // 86400))
    if recency_days <= 7:
        recency_level, recency_score = "current", 1.0
    elif recency_days <= 30:
        recency_level, recency_score = "recent", 0.8
    elif recency_days <= 60:
        recency_level, recency_score = "moderately-recent", 0.6
    else:
        recency_level, recency_score = "stale", 0.4

    composite = (
        CONFIDENCE_WEIGHTS["sample_size"] * sample_score
        + CONFIDENCE_WEIGHTS["data_completeness"] * completeness_score
        + CONFIDENCE_WEIGHTS["recency"] * recency_score
    )
    if composite >= CONFIDENCE_HIGH:
        level = "high"
    elif composite >= CONFIDENCE_MEDIUM:
        level = "medium"
    else:
        level = "low"

    rationale = (
        f"Based on {minutes_played:,.0f} minutes played — {sample_level} "
        f"relative to the {qualifying_minutes:,.0f}-minute qualification "
        f"threshold — {completeness_level} data across the player's position "
        f"metric set ({metrics_present}/{metrics_expected} metrics), and data "
        f"{recency_days} day{'s' if recency_days != 1 else ''} old."
    )
    return {
        "level": level,
        "rationale": rationale,
        "composite": round(composite, 3),
        "factors": {
            "sample_size": {"level": sample_level, "score": sample_score, "minutes_played": minutes_played, "qualifying_minutes": qualifying_minutes},
            "data_completeness": {"level": completeness_level, "score": completeness_score, "metrics_present": metrics_present, "metrics_expected": metrics_expected},
            "recency": {"level": recency_level, "score": recency_score, "days": recency_days},
        },
    }


# ---------------------------------------------------------------------------
# A3 — risk factors derived from real signals (never invented)
# ---------------------------------------------------------------------------


def derive_risk_factors(
    *,
    minutes_played: float,
    qualifying_minutes: float,
    seasons: int,
    has_event_data: bool,
    age: int | None,
    position_group: str | None,
) -> list[dict[str, str]]:
    """Real-signal risk factors + the explicit out-of-scope statement.

    Only signals Statlas actually has data for are allowed (scouting-reports.md
    §4): sample size, single-season coverage, event-data availability, and age
    vs. the documented position peak range. The out-of-scope statement is
    always appended so silence never implies completeness.
    """
    risks: list[dict[str, str]] = []
    if minutes_played < 2 * qualifying_minutes:
        risks.append(
            {
                "point": (
                    f"Limited sample size: {minutes_played:,.0f} minutes played, "
                    f"below twice the {qualifying_minutes:,.0f}-minute "
                    "qualification threshold. Percentile ranks are less stable "
                    "with a small sample."
                ),
                "basis": "sample_size",
            }
        )
    if seasons <= 1:
        risks.append(
            {
                "point": (
                    "Single-season assessment: Statlas only has snapshot "
                    "history for one season for this player, so no "
                    "multi-season development trend can be established."
                ),
                "basis": "single_season",
            }
        )
    if not has_event_data:
        risks.append(
            {
                "point": (
                    "No event-level data available: shot/pass maps for this "
                    "player are not in coverage, so tactical assessment from "
                    "event data is not possible in this report."
                ),
                "basis": "no_event_data",
            }
        )
    if age is not None and position_group in POSITION_PEAK_AGES:
        peak_min, peak_max = POSITION_PEAK_AGES[position_group]
        if age < peak_min:
            risks.append(
                {
                    "point": (
                        f"Age {age} is below the typical peak range "
                        f"({peak_min}-{peak_max}) for {position_group}s — "
                        "development trajectory should be weighted when "
                        "interpreting current output."
                    ),
                    "basis": "age_vs_position",
                }
            )
        elif age > peak_max:
            risks.append(
                {
                    "point": (
                        f"Age {age} is above the typical peak range "
                        f"({peak_min}-{peak_max}) for {position_group}s — "
                        "recent output may already be past peak."
                    ),
                    "basis": "age_vs_position",
                }
            )
    risks.append({"point": OUT_OF_SCOPE_RISK, "basis": "out_of_scope"})
    return risks


# ---------------------------------------------------------------------------
# B1 — deterministic context gathering (step 1 of the pipeline)
# ---------------------------------------------------------------------------


def _age_from_dob(date_of_birth: datetime | None, now: datetime | None = None) -> int | None:
    if date_of_birth is None:
        return None
    now = now or datetime.now(timezone.utc)
    dob = date_of_birth
    # The Player.date_of_birth column is a DATE — SQLite returns it as a
    # datetime.date. Normalise to a naive datetime for the arithmetic.
    if hasattr(dob, "hour"):
        dob = dob.replace(tzinfo=None)
    else:
        dob = datetime(dob.year, dob.month, dob.day)  # noqa: DTZ001 — a DATE has no tz; naive is correct here
    years = now.year - dob.year - ((now.month, now.day) < (dob.month, dob.day))
    return years


def gather_report_context(
    db: Session,
    player_id: int,
    shortlist_entry_id: int | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    """Assemble ALL real data the report may reference (never fabricated).

    Every value here comes from the existing query layer — the same functions
    the REST API and pages use. The `verification` sub-object is the corpus the
    hard gate checks against: every number (raw + rounded forms) and every
    metric display name that may legally appear in the report.
    """
    registry = load_registry()
    profile = player_queries.get_player_profile(db, player_id)
    if profile is None:
        raise PlayerHasNoData(f"No player with id {player_id} exists.")
    percentiles = player_queries.get_player_percentiles(db, player_id)
    if percentiles is None:
        raise PlayerHasNoData(
            f"No published percentile data for {profile['name']} — a report "
            "cannot be grounded on unpublished or unqualified data."
        )
    raw = player_queries.get_player_raw_stats(db, player_id)

    position_group = profile.get("position_group")
    metric_ids = (
        registry["gk_metrics"] if position_group == "GK" else registry["outfield_metrics"]
    )
    metrics = registry["metrics"]

    # Data completeness: how many of the position's metrics are in the vector.
    present = [m for m in metric_ids if m in percentiles["percentiles"]]
    metrics_expected = len(metric_ids)

    qualifying_minutes = registry["qualifying_minutes"]
    minutes = raw["minutes_played"] if raw else 0.0
    snapshot_date = percentiles["snapshot_date"] or (raw["snapshot_date"] if raw else None)
    if snapshot_date is None:
        raise PlayerHasNoData(
            f"No snapshot date for {profile['name']} — the report needs a "
            "dated, published snapshot to anchor its recency claim."
        )

    # Comparable players: VERBATIM from Phase 6 (B3) — never LLM-computed.
    comparables = similar_players.get_similar_players(db, player_id, limit=3)

    # Development trajectory: trend of the player's STRONGEST real metric
    # (Phase 3). si_index is not a registry metric (it has no per-90 value), so
    # it cannot be trended; the strongest position metric is a real, deterministic
    # choice.
    if not present:
        raise PlayerHasNoData(
            f"No published percentile values for {profile['name']} — a report "
            "cannot be grounded on a player with no metric data."
        )
    trend_metric = max(present, key=lambda m: percentiles["percentiles"][m] or 0)
    trend = trend_queries.get_player_trend(db, player_id, trend_metric, window=5)

    # Event-data availability for the risk factor.
    has_event_data = (
        db.query(MatchEvent.id).filter(MatchEvent.player_id == player_id).first()
        is not None
    )
    seasons = (
        db.query(StatSnapshot.season)
        .filter(StatSnapshot.player_id == player_id)
        .distinct()
        .count()
    )

    # Workspace context (B4) — only when generated from a shortlist entry, and
    # ONLY when that entry belongs to the requesting user (D4: another user's
    # private scouting notes must never leak into a report).
    workspace_context = None
    if shortlist_entry_id is not None:
        entry = _owned_entry_for_report(db, shortlist_entry_id, user_id)
        workspace_context = {
            "shortlist_entry_id": entry.id,
            "shortlist_status": entry.status,
            "priority": entry.priority,
            "tags": [t.tag_text for t in entry.tags],
            "recent_notes": [
                {"note_text": n.note_text, "created_at": n.created_at.isoformat()}
                for n in entry.notes[:MIN_RECENT_NOTES]
            ],
            "label": "user's own scouting notes (Phase 7 workspace), not an independent data finding",
        }

    age = _age_from_dob(profile.get("date_of_birth"))

    context = {
        "player": {
            "player_id": player_id,
            "name": profile["name"],
            "position_group": position_group,
            "position_label": profile.get("primary_position"),
            "club": profile.get("current_team"),
            "nationality": profile.get("nationality"),
            "age": age,
        },
        "percentiles": {
            "snapshot_date": snapshot_date.isoformat() if snapshot_date else None,
            "computed_date": (
                percentiles["computed_date"].isoformat()
                if percentiles.get("computed_date")
                else None
            ),
            "index": percentiles.get("index"),
            "values": {m: percentiles["percentiles"].get(m) for m in metric_ids},
        },
        "raw": {
            "snapshot_date": raw["snapshot_date"].isoformat() if raw else None,
            "season": raw["season"] if raw else None,
            "source": raw["source"] if raw else None,
            "minutes_played": minutes,
            "matches_played": raw["matches_played"] if raw else 0,
            "league": raw["league"] if raw else None,
            "league_tier": raw["league_tier"] if raw else None,
            "values": {m: (raw["raw_stats"] or {}).get(m) for m in metric_ids},
        },
        "metrics": {
            m: {"name": metrics[m]["name"], "unit": metrics[m].get("unit", "")}
            for m in metric_ids
        },
        "qualifying_minutes": qualifying_minutes,
        "index_metric_id": trend_metric,
        "index_metric_name": metrics[trend_metric]["name"],
        "comparables": comparables,
        "trend": {
            "available": trend["available"] if trend else 0,
            "insufficient": trend["insufficient"] if trend else True,
            "metric": trend_metric,
            "points": trend["points"] if trend else [],
            "note": trend["granularity_note"] if trend else None,
        },
        "has_event_data": has_event_data,
        "seasons_available": seasons,
        "data_snapshot_date": snapshot_date,
        "workspace_context": workspace_context,
        "confidence": compute_report_confidence(
            minutes_played=minutes,
            qualifying_minutes=qualifying_minutes,
            metrics_present=len(present),
            metrics_expected=metrics_expected,
            snapshot_date=snapshot_date,
        ),
        "risk_factors": derive_risk_factors(
            minutes_played=minutes,
            qualifying_minutes=qualifying_minutes,
            seasons=seasons,
            has_event_data=has_event_data,
            age=age,
            position_group=position_group,
        ),
    }
    context["verification"] = _build_corpus(context)
    return context


def _owned_entry_for_report(db: Session, entry_id: int, user_id: int | None):
    """The shortlist entry for a report — must belong to the requesting user
    (D4). Foreign/missing entries raise ReportNotFound -> 404, the Phase 7/8
    never-leak-existence rule."""
    from app.models import EntryNote, EntryTag, Shortlist, ShortlistEntry

    entry = (
        db.query(ShortlistEntry)
        .join(Shortlist, ShortlistEntry.shortlist_id == Shortlist.id)
        .filter(
            ShortlistEntry.id == entry_id,
            Shortlist.user_id == user_id,
            Shortlist.deleted_at.is_(None),
            ShortlistEntry.removed_at.is_(None),
        )
        .first()
    )
    if entry is None:
        raise ReportNotFound(f"shortlist entry {entry_id} not found")
    entry.notes = (
        db.query(EntryNote)
        .filter(EntryNote.shortlist_entry_id == entry.id)
        .order_by(EntryNote.created_at.desc(), EntryNote.id.desc())
        .limit(MIN_RECENT_NOTES)
        .all()
    )
    entry.tags = (
        db.query(EntryTag)
        .filter(EntryTag.shortlist_entry_id == entry.id)
        .order_by(EntryTag.tag_text.asc())
        .all()
    )
    return entry


def _build_corpus(context: dict[str, Any]) -> dict[str, Any]:
    """Every number + metric name that may legally appear in a report.

    Numbers are stored raw, rounded to 1 dp, and rounded to an integer so the
    gate tolerates legitimate narration forms ("88th" matches 87.6-88.4) while
    a fabricated value fails.
    """
    numbers: set[float] = set()

    def add(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            numbers.add(float(value))
            numbers.add(round(float(value), 1))
            numbers.add(float(round(float(value))))
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                add(item)
            return
        if isinstance(value, dict):
            for item in value.values():
                add(item)

    # Percentiles + raw values + index + matches/minutes + similarity.
    add(context["percentiles"]["values"])
    add(context["raw"]["values"])
    add(context["percentiles"].get("index"))
    add(context["raw"].get("minutes_played"))
    add(context["raw"].get("matches_played"))
    add(context["qualifying_minutes"])
    add(context["player"].get("age"))
    for comparable in context["comparables"]:
        add(comparable.get("similarity"))
        add(comparable.get("index"))
        add(comparable.get("anchor_index"))
        add(comparable.get("shared_metrics"))
        add(comparable.get("explanation", {}).get("shared_metrics"))
        for item in comparable.get("explanation", {}).get("matched_strengths", []):
            add(item.get("player_a_percentile"))
            add(item.get("player_b_percentile"))
            add(item.get("difference"))
            add(item.get("contribution"))
        for item in comparable.get("explanation", {}).get("key_differences", []):
            add(item.get("player_a_percentile"))
            add(item.get("player_b_percentile"))
            add(item.get("difference"))
    for point in context["trend"].get("points", []):
        add(point.get("raw"))
        add(point.get("pct"))
        add(point.get("minutes"))
        add(point.get("matches"))
    add(len(context["trend"].get("points", [])))  # "over the N most recent snapshots"
    # Snapshot date components (so prose can say "data as of August 2026").
    snap = context["data_snapshot_date"]
    if snap is not None:
        if snap.tzinfo is None:
            snap = snap.replace(tzinfo=timezone.utc)
        add(snap.year)
        add(snap.month)
        add(snap.day)

    metric_names: set[str] = set()
    for meta in context["metrics"].values():
        metric_names.add(meta["name"].lower())
    metric_ids = set(context["metrics"].keys())

    return {
        "numbers": numbers,
        "metric_names": metric_names,
        "metric_ids": metric_ids,
        "player_name": context["player"]["name"].lower(),
        "club": (context["player"].get("club") or "").lower(),
        "league": (context["raw"].get("league") or "").lower(),
        "season": (context["raw"].get("season") or "").lower(),
    }


# ---------------------------------------------------------------------------
# B2 — the hard verification gate (code, not prompt)
# ---------------------------------------------------------------------------


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
    for label in (corpus.get("player_name"), corpus.get("club"), corpus.get("league"), corpus.get("season")):
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

    Returns {\"passed\", \"unverified\": [...], \"checked\"}. A single unmatched
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
                    {"claim": f"unknown metric '{metric}' in {item_key}", "source": item_key, "kind": "metric"}
                )
            for field in ("value", "percentile"):
                value = item.get(field)
                if value is not None and not tolerance_ok(float(value)):
                    unverified.append(
                        {"claim": f"{item_key} {field} {value!r} not in corpus", "source": item_key, "kind": "number"}
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
                {"claim": f"comparable player {pid} not in real Phase 6 results", "source": "comparable_players", "kind": "comparable"}
            )
        if sim is not None and (pid, round(float(sim), 4)) not in context_sims:
            unverified.append(
                {"claim": f"similarity {sim} for player {pid} not in real results", "source": "comparable_players", "kind": "number"}
            )

    # 4. Confidence level must equal the deterministic computation.
    expected_level = context["confidence"]["level"]
    actual_level = report.get("sections", {}).get("recommendation", {}).get("confidence_level")
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


# ---------------------------------------------------------------------------
# B1/B2 — narrators (step 2 of the pipeline)
# ---------------------------------------------------------------------------


def deterministic_narrator(context: dict[str, Any], correction: str | None = None) -> dict[str, Any]:
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
        direction = "risen" if (last_raw or 0) > (first_raw or 0) else ("fallen" if (last_raw or 0) < (first_raw or 0) else "held steady")
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


def _narrate_via_anthropic(context: dict[str, Any], correction: str | None = None) -> dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Quota (D5) — separate report allowance, same hard-cap model as Phase 4
# ---------------------------------------------------------------------------


def _quota_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def get_report_quota(db: Session, user_id: int) -> dict[str, Any]:
    plan = effective_plan(db, user_id)
    limit = int(plan_limits(plan).get("report_quotas_per_period", 0) or 0)
    start, end = _quota_window()
    row = (
        db.query(ReportQuota)
        .filter(ReportQuota.user_id == user_id, ReportQuota.period_start == start)
        .first()
    )
    if row is None:
        row = ReportQuota(
            user_id=user_id,
            period_start=start,
            period_end=end,
            reports_used=0,
            reports_limit=limit,
        )
        db.add(row)
        db.commit()
    return {
        "used": row.reports_used,
        "limit": row.reports_limit,
        "reset": end.date().isoformat(),
        "remaining": max(0, row.reports_limit - row.reports_used),
        "plan": plan,
        "has_pro": has_pro_access(db, user_id),
    }


def _consume_report_quota(db: Session, user_id: int) -> dict[str, Any]:
    quota = get_report_quota(db, user_id)
    if quota["remaining"] <= 0:
        raise ReportLimitExceeded(
            f"Reports are a Pro feature and your Pro plan's allowance of "
            f"{quota['limit']} reports this period is used up — resets "
            f"{quota['reset']}. Upgrade your plan for a higher monthly "
            "allowance."
        )
    start = _quota_window()[0]
    row = (
        db.query(ReportQuota)
        .filter(ReportQuota.user_id == user_id, ReportQuota.period_start == start)
        .first()
    )
    row.reports_used += 1
    db.commit()
    quota["used"] = row.reports_used
    quota["remaining"] = max(0, row.reports_limit - row.reports_used)
    return quota


# ---------------------------------------------------------------------------
# The pipeline (B1/B2) + CRUD with ownership (D4)
# ---------------------------------------------------------------------------


def generate_report(
    db: Session,
    user_id: int,
    player_id: int,
    *,
    shortlist_entry_id: int | None = None,
    narrator: Callable[[dict[str, Any], str | None], dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Full pipeline: gather -> narrate -> verify -> (retry once) -> store.

    `narrator` defaults to the Anthropic LLM; tests and dev seeding inject the
    deterministic narrator. The verification gate runs on EVERY generation
    regardless of narrator. Free-tier users are blocked with an honest upsell
    BEFORE any LLM call (and before quota consumption).
    """
    now = now or datetime.now(timezone.utc)

    # Tier gate first (D5): honest upsell, never a generic error.
    if not has_pro_access(db, user_id):
        raise ReportLimitExceeded(
            "Reports are a Pro feature — generate shareable, fully grounded "
            "scouting reports with every claim traced to real Statlas data. "
            "Upgrade to Pro to get started."
        )

    # Then the key gate: an unconfigured deployment is an honest state, not a
    # scripted demo (the Phase 4 assistant's rule, applied to reports).
    if narrator is None and not get_settings().anthropic_api_key:
        raise ReportNotConfigured(
            "Report generation is not configured on this deployment "
            "(ANTHROPIC_API_KEY unset)."
        )

    narrate = narrator or _narrate_via_anthropic

    context = gather_report_context(db, player_id, shortlist_entry_id, user_id)

    # One auto-correction retry, then an honest hold (never silent shipping).
    correction: str | None = None
    for attempt in (1, 2):
        draft = narrate(context, correction)
        verification = verify_report(draft, context)
        if verification["passed"]:
            break
        correction = "; ".join(
            f"{c['claim']} ({c['kind']})" for c in verification["unverified"]
        )
        if attempt == 2:
            # Second failure: store as needs_review — never silently shipped.
            verification["retried"] = True
            break

    snapshot_date = context["data_snapshot_date"]
    if snapshot_date.tzinfo is None:
        snapshot_date = snapshot_date.replace(tzinfo=timezone.utc)

    report_doc = {
        "player_id": player_id,
        "generated_at": now.isoformat(),
        "generated_by_user_id": user_id,
        "data_snapshot_date": snapshot_date.date().isoformat(),
        "source": (
            WORKSPACE_SOURCE_LABEL if shortlist_entry_id else REPORT_SOURCE_LABEL
        ),
        "shortlist_entry_id": shortlist_entry_id,
        "sections": draft.get("sections", {}),
        "confidence": draft.get("confidence", context["confidence"]),
        "evidence_appendix": _build_evidence_appendix(context),
        "verification": {
            "status": "passed" if verification["passed"] else "needs_review",
            "log": {
                "attempts": 2 if verification.get("retried") else (1 if verification["passed"] else 2),
                "unverified": verification["unverified"],
                "passed": verification["passed"],
            },
        },
    }

    _consume_report_quota(db, user_id)

    row = Report(
        user_id=user_id,
        player_id=player_id,
        shortlist_entry_id=shortlist_entry_id,
        status="generated" if verification["passed"] else "needs_review",
        data_snapshot_date=snapshot_date,
        report_json=report_doc,
        verification_log=report_doc["verification"]["log"],
    )
    db.add(row)
    db.commit()

    if not verification["passed"]:
        logger.warning(
            "report %s failed verification (needs_review): %s",
            row.id,
            correction,
        )
    return _report_payload(row)


def _build_evidence_appendix(context: dict[str, Any]) -> list[dict[str, Any]]:
    """The claim-by-claim appendix: every number in the report traces to a
    real context value, shown with its source call (A1/B2 traceability)."""
    appendix: list[dict[str, Any]] = []
    pct = context["percentiles"]["values"]
    raw = context["raw"]["values"]
    for metric_id, meta in context["metrics"].items():
        appendix.append(
            {
                "claim": f"{meta['name']} percentile and raw value",
                "source_call": "percentiles",
                "raw_result": {"metric": metric_id, "percentile": pct.get(metric_id), "value": raw.get(metric_id)},
            }
        )
    appendix.append(
        {
            "claim": "Statlas Index",
            "source_call": "percentiles",
            "raw_result": {"index": context["percentiles"].get("index")},
        }
    )
    appendix.append(
        {
            "claim": "minutes and matches played",
            "source_call": "raw_stats",
            "raw_result": {"minutes": context["raw"]["minutes_played"], "matches": context["raw"]["matches_played"], "season": context["raw"]["season"]},
        }
    )
    appendix.append(
        {
            "claim": "data snapshot date",
            "source_call": "percentiles",
            "raw_result": {"snapshot_date": context["percentiles"]["snapshot_date"]},
        }
    )
    for comparable in context["comparables"]:
        appendix.append(
            {
                "claim": f"similarity to {comparable['name']}",
                "source_call": "similar_players",
                "raw_result": {"player_id": comparable["player_id"], "similarity": comparable["similarity"], "shared_metrics": comparable.get("shared_metrics")},
            }
        )
    return appendix


def _snapshot_label(value: Any) -> str:
    """'YYYY-MM-DD' from a date or (possibly naive) datetime — SQLite returns
    date objects for DateTime columns, so both must be handled."""
    if hasattr(value, "tzinfo") and value.tzinfo is not None:
        return value.date().isoformat()
    text = value.isoformat() if hasattr(value, "isoformat") else str(value)
    return text[:10]


def _report_payload(row: Report) -> dict[str, Any]:
    return {
        "report_id": row.id,
        "player_id": row.player_id,
        "shortlist_entry_id": row.shortlist_entry_id,
        "status": row.status,
        "data_snapshot_date": _snapshot_label(row.data_snapshot_date),
        "created_at": row.created_at.isoformat(),
        "report": row.report_json,
    }


def list_reports(db: Session, user_id: int) -> list[dict[str, Any]]:
    """The user's report history, newest first (D3 persistence)."""
    rows = (
        db.query(Report)
        .filter(Report.user_id == user_id)
        .order_by(Report.created_at.desc(), Report.id.desc())
        .all()
    )
    out = []
    for row in rows:
        payload = _report_payload(row)
        payload["player_name"] = _player_name(db, row.player_id)
        payload["verification_status"] = row.report_json.get("verification", {}).get("status")
        out.append(payload)
    return out


def get_report(db: Session, user_id: int, report_id: int) -> dict[str, Any]:
    """One report — ownership verified (404 for foreign/missing ids)."""
    row = (
        db.query(Report)
        .filter(Report.id == report_id, Report.user_id == user_id)
        .first()
    )
    if row is None:
        raise ReportNotFound(f"report {report_id} not found")
    payload = _report_payload(row)
    payload["player_name"] = _player_name(db, row.player_id)
    payload["verification_status"] = row.report_json.get("verification", {}).get("status")
    return payload


def delete_report(db: Session, user_id: int, report_id: int) -> None:
    """Delete a report (the user's own generated document)."""
    row = (
        db.query(Report)
        .filter(Report.id == report_id, Report.user_id == user_id)
        .first()
    )
    if row is None:
        raise ReportNotFound(f"report {report_id} not found")
    db.delete(row)
    db.commit()


def _player_name(db: Session, player_id: int) -> str | None:
    player = db.get(Player, player_id)
    return player.canonical_name if player else None
