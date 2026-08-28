"""The pipeline (B1/B2) + CRUD with ownership (D4)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.auth import has_pro_access
from app.config import get_settings
from app.models import Player, Report
from app.reports_pkg.confidence import compute_report_confidence
from app.reports_pkg.constants import (
    REPORT_SOURCE_LABEL,
    WORKSPACE_SOURCE_LABEL,
    PlayerHasNoData,
    ReportLimitExceeded,
    ReportNotFound,
    ReportNotConfigured,
)
from app.reports_pkg.context import gather_report_context
from app.reports_pkg.narrators import deterministic_narrator, _narrate_via_anthropic
from app.reports_pkg.quota import _consume_report_quota
from app.reports_pkg.verification import verify_report

logger = logging.getLogger(__name__)


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
                "raw_result": {
                    "metric": metric_id,
                    "percentile": pct.get(metric_id),
                    "value": raw.get(metric_id),
                },
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
            "raw_result": {
                "minutes": context["raw"]["minutes_played"],
                "matches": context["raw"]["matches_played"],
                "season": context["raw"]["season"],
            },
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
                "raw_result": {
                    "player_id": comparable["player_id"],
                    "similarity": comparable["similarity"],
                    "shared_metrics": comparable.get("shared_metrics"),
                },
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


def _player_name(db: Session, player_id: int) -> str | None:
    player = db.get(Player, player_id)
    return player.canonical_name if player else None


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
                "attempts": (
                    2
                    if verification.get("retried")
                    else (1 if verification["passed"] else 2)
                ),
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
        payload["verification_status"] = row.report_json.get("verification", {}).get(
            "status"
        )
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
    payload["verification_status"] = row.report_json.get("verification", {}).get(
        "status"
    )
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
