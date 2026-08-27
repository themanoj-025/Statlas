"""Phase 9 — AI scouting report API routes.

Session-authenticated (401 otherwise). Generation runs the full grounded
pipeline from app/reports.py (gather -> narrate -> verify -> store); this
module only maps domain errors to HTTP statuses:

- ReportNotFound            -> 404 (existence never leaks, per Phase 7/8)
- ReportLimitExceeded       -> 403 (honest tier/quota upsell copy)
- ReportNotConfigured       -> 503 (honest "not configured" state, per Phase 4)
- PlayerHasNoData           -> 422 (a report cannot be grounded on no data)
- ValueError                -> 400 (validation)

The dev narrator is used only when REPORTS_DEV_NARRATOR=1 (tests/e2e); the
verification gate runs identically on every generation regardless of narrator.
"""

from __future__ import annotations

from typing import Any

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from app import report_export, reports
from app.api.deps import require_user
from app.config import get_settings
from app.db import session_scope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


# _require_user consolidated into app/api/deps.py
_require_user = require_user


def _narrator() -> Any:
    if get_settings().reports_dev_narrator:
        return reports.deterministic_narrator
    return None


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, reports.ReportNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, reports.ReportLimitExceeded):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, reports.ReportNotConfigured):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, reports.PlayerHasNoData):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    logger.exception("Unmapped exception in report_views")
    return HTTPException(status_code=500, detail="Something went wrong.")


class GenerateBody(BaseModel):
    player_id: int
    shortlist_entry_id: int | None = Field(default=None)


# ---------------------------------------------------------------------------
# Routes — static paths BEFORE /{report_id} so they are not captured.
# ---------------------------------------------------------------------------


@router.get("/quota")
def report_quota(request: Request) -> dict[str, Any]:
    user = _require_user(request)
    with session_scope() as db:
        return reports.get_report_quota(db, user.id)


@router.get("")
def list_reports(request: Request) -> list[dict[str, Any]]:
    user = _require_user(request)
    with session_scope() as db:
        return {"reports": reports.list_reports(db, user.id)}


@router.post("", status_code=201)
def generate(body: GenerateBody, request: Request) -> dict[str, Any]:
    """Generate a scouting report. Rate-limited to 10 per user per hour."""
    from app.rate_limiting import get_rate_limiter

    user = _require_user(request)
    limiter = get_rate_limiter()
    if limiter.is_limited(
        f"report:{user.id}", max_attempts=10, window_seconds=3600
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many report requests. Please try again later.",
            headers={"Retry-After": "3600"},
        )
    with session_scope() as db:
        try:
            return reports.generate_report(
                db,
                user.id,
                body.player_id,
                shortlist_entry_id=body.shortlist_entry_id,
                narrator=_narrator(),
            )
        except (reports.ReportNotFound, reports.ReportLimitExceeded, reports.ReportNotConfigured, reports.PlayerHasNoData, ValueError) as exc:
            raise _map_error(exc)


@router.get("/{report_id}")
def get_report(report_id: int, request: Request) -> dict[str, Any]:
    user = _require_user(request)
    with session_scope() as db:
        try:
            return reports.get_report(db, user.id, report_id)
        except (reports.ReportNotFound, reports.ReportLimitExceeded, reports.ReportNotConfigured, reports.PlayerHasNoData, ValueError) as exc:
            raise _map_error(exc)


@router.post("/{report_id}/regenerate", status_code=201)
def regenerate(report_id: int, request: Request) -> dict[str, Any]:
    """Re-run the stored report's definition against CURRENT data (the stored
    report itself is never mutated — a fresh report row is created, matching
    the Phase 8 'results may have changed since last run' discipline).
    Shares rate limit with generate (10 per user per hour)."""
    from app.rate_limiting import get_rate_limiter

    user = _require_user(request)
    limiter = get_rate_limiter()
    if limiter.is_limited(
        f"report:{user.id}", max_attempts=10, window_seconds=3600
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many report requests. Please try again later.",
            headers={"Retry-After": "3600"},
        )
    with session_scope() as db:
        try:
            stored = reports.get_report(db, user.id, report_id)
            player_id = stored["report"]["player_id"]
            entry_id = stored["report"].get("shortlist_entry_id")
        except (reports.ReportNotFound, reports.ReportLimitExceeded, reports.ReportNotConfigured, reports.PlayerHasNoData, ValueError) as exc:
            raise _map_error(exc)
        try:
            return reports.generate_report(
                db,
                user.id,
                player_id,
                shortlist_entry_id=entry_id,
                narrator=_narrator(),
            )
        except (reports.ReportNotFound, reports.ReportLimitExceeded, reports.ReportNotConfigured, reports.PlayerHasNoData, ValueError) as exc:
            raise _map_error(exc)


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: int, request: Request) -> dict[str, str]:
    user = _require_user(request)
    with session_scope() as db:
        try:
            reports.delete_report(db, user.id, report_id)
        except (reports.ReportNotFound, reports.ReportLimitExceeded, reports.ReportNotConfigured, reports.PlayerHasNoData, ValueError) as exc:
            raise _map_error(exc)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Exports — all derived from the single stored, verified report object
# ---------------------------------------------------------------------------


def _load_verified(db, user_id: int, report_id: int) -> Any:
    payload = reports.get_report(db, user_id, report_id)
    if payload["status"] == "needs_review":
        raise HTTPException(
            status_code=409,
            detail="This report contains a claim that failed automated verification and is held for review — export is disabled until it is regenerated.",
        )
    return payload


@router.get("/{report_id}/export.json")
def export_json(report_id: int, request: Request) -> dict[str, Any]:
    user = _require_user(request)
    with session_scope() as db:
        try:
            payload = _load_verified(db, user.id, report_id)
        except (reports.ReportNotFound, reports.ReportLimitExceeded, reports.ReportNotConfigured, reports.PlayerHasNoData, ValueError) as exc:
            raise _map_error(exc)
        content = report_export.export_json(payload["report"])
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="report-{report_id}.json"'
            },
        )


@router.get("/{report_id}/export.pdf")
def export_pdf(report_id: int, request: Request) -> Any:
    user = _require_user(request)
    with session_scope() as db:
        try:
            payload = _load_verified(db, user.id, report_id)
        except (reports.ReportNotFound, reports.ReportLimitExceeded, reports.ReportNotConfigured, reports.PlayerHasNoData, ValueError) as exc:
            raise _map_error(exc)
        pdf = report_export.export_pdf(
            payload["report"], player_name=payload.get("player_name")
        )
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="statlas-report-{report_id}.pdf"'
            },
        )


@router.get("/{report_id}/export.csv")
def export_csv(report_id: int, request: Request) -> Any:
    user = _require_user(request)
    with session_scope() as db:
        try:
            payload = _load_verified(db, user.id, report_id)
        except (reports.ReportNotFound, reports.ReportLimitExceeded, reports.ReportNotConfigured, reports.PlayerHasNoData, ValueError) as exc:
            raise _map_error(exc)
        csv_text = report_export.export_csv(
            payload["report"], player_name=payload.get("player_name")
        )
        return StreamingResponse(
            iter([csv_text]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="statlas-report-{report_id}.csv"'
            },
        )
