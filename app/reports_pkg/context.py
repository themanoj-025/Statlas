"""B1 — deterministic context gathering (step 1 of the pipeline)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import load_registry
from app.models import MatchEvent, StatSnapshot
from app.queries import player_queries, similar_players, trend_queries
from app.reports_pkg.confidence import compute_report_confidence
from app.reports_pkg.constants import MIN_RECENT_NOTES, PlayerHasNoData, ReportNotFound
from app.reports_pkg.risk import derive_risk_factors

logger = logging.getLogger(__name__)


def _age_from_dob(
    date_of_birth: datetime | None, now: datetime | None = None
) -> int | None:
    if date_of_birth is None:
        return None
    now = now or datetime.now(timezone.utc)
    dob = date_of_birth
    # The Player.date_of_birth column is a DATE — SQLite returns it as a
    # datetime.date. Normalise to a naive datetime for the arithmetic.
    if hasattr(dob, "hour"):
        dob = dob.replace(tzinfo=None)
    else:
        dob = datetime(  # noqa: DTZ001 — a DATE has no tz; naive is correct here
            dob.year, dob.month, dob.day
        )
    years = now.year - dob.year - ((now.month, now.day) < (dob.month, dob.day))
    return years


def _owned_entry_for_report(db: Session, entry_id: int, user_id: int | None) -> Any:
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


def gather_report_context(
    db: Session,
    player_id: int,
    shortlist_entry_id: int | None = None,
    user_id: int | None = None,
) -> dict[str, Any] -> None:
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
        registry["gk_metrics"]
        if position_group == "GK"
        else registry["outfield_metrics"]
    )
    metrics = registry["metrics"]

    # Data completeness: how many of the position's metrics are in the vector.
    present = [m for m in metric_ids if m in percentiles["percentiles"]]
    metrics_expected = len(metric_ids)

    qualifying_minutes = registry["qualifying_minutes"]
    minutes = raw["minutes_played"] if raw else 0.0
    snapshot_date = percentiles["snapshot_date"] or (
        raw["snapshot_date"] if raw else None
    )
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
