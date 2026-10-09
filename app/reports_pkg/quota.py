"""Quota (D5) — separate report allowance, same hard-cap model as Phase 4."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.auth import effective_plan, has_pro_access
from app.config import plan_limits
from app.models import ReportQuota
from app.reports_pkg.constants import ReportLimitExceeded


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
