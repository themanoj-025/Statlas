"""Phase 18 — Alerting and anomaly detection.

Part D of the Phase 18 execution prompt.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AnalyticsAlert, DailyMetric

# ── Threshold Alerts (Part D1) ────────────────────────────────────────

ALERT_THRESHOLDS: list[dict] = [
    {
        "name": "dau_drop",
        "metric_name": "dau_total",
        "threshold_type": "week_over_week_drop_pct",
        "threshold_value": 20.0,
        "message": "DAU dropped >20% week-over-week. Check for deployed bugs or service issues.",
    },
    {
        "name": "conversion_drop",
        "metric_name": "free_to_pro_conversion",
        "threshold_type": "month_over_month_drop_pct",
        "threshold_value": 30.0,
        "message": "Free-to-Pro conversion dropped >30%. Review upgrade flow and Pro value proposition.",
    },
    {
        "name": "error_rate_spike",
        "metric_name": "error_rate",
        "threshold_type": "above",
        "threshold_value": 2.0,
        "message": "Error rate exceeded 2% of events. Investigate feature-level errors.",
    },
    {
        "name": "latency_spike",
        "metric_name": "p95_latency_ms",
        "threshold_type": "above",
        "threshold_value": 5000.0,
        "message": "API p95 latency exceeded 5 seconds. Check database queries and slow endpoints.",
    },
]


def check_threshold_alerts(db: Session) -> list[AnalyticsAlert]:
    """Check all threshold-based alerts and fire if breached.

    Returns list of alerts that fired.
    """
    now = datetime.now(timezone.utc)
    alerts_fired = []

    for alert_def in ALERT_THRESHOLDS:
        alert = _evaluate_threshold(db, alert_def, now)
        if alert:
            db.add(alert)
            alerts_fired.append(alert)

    if alerts_fired:
        db.commit()

    return alerts_fired


def _evaluate_threshold(
    db: Session,
    alert_def: dict,
    now: datetime,
) -> AnalyticsAlert | None:
    """Evaluate a single threshold alert.  Returns alert if fired, None otherwise."""
    if alert_def["threshold_type"] == "week_over_week_drop_pct":
        return _check_week_over_week(db, alert_def, now)
    elif alert_def["threshold_type"] == "month_over_month_drop_pct":
        return _check_month_over_month(db, alert_def, now)
    elif alert_def["threshold_type"] == "above":
        return _check_above_threshold(db, alert_def, now)

    return None


def _check_week_over_week(
    db: Session,
    alert_def: dict,
    now: datetime,
) -> AnalyticsAlert | None:
    """Check if metric dropped more than threshold week-over-week."""
    this_week = now - timedelta(days=7)
    last_week = now - timedelta(days=14)

    this_week_val = _get_metric_avg(db, alert_def["metric_name"], this_week, now)
    last_week_val = _get_metric_avg(db, alert_def["metric_name"], last_week, this_week)

    if last_week_val is None or this_week_val is None or last_week_val == 0:
        return None

    drop_pct = ((last_week_val - this_week_val) / last_week_val) * 100

    if drop_pct > alert_def["threshold_value"]:
        return AnalyticsAlert(
            alert_name=alert_def["name"],
            metric_name=alert_def["metric_name"],
            threshold_type=alert_def["threshold_type"],
            threshold_value=alert_def["threshold_value"],
            actual_value=round(drop_pct, 2),
            message=f"{alert_def['message']} ({alert_def['metric_name']}: {this_week_val:.0f} this week vs {last_week_val:.0f} last week, ↓{drop_pct:.1f}%)",
        )

    return None


def _check_month_over_month(
    db: Session,
    alert_def: dict,
    now: datetime,
) -> AnalyticsAlert | None:
    """Check if metric dropped more than threshold month-over-month."""
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

    this_month_val = _get_metric_avg(db, alert_def["metric_name"], this_month_start, now)
    last_month_val = _get_metric_avg(db, alert_def["metric_name"], last_month_start, this_month_start)

    if last_month_val is None or this_month_val is None or last_month_val == 0:
        return None

    drop_pct = ((last_month_val - this_month_val) / last_month_val) * 100

    if drop_pct > alert_def["threshold_value"]:
        return AnalyticsAlert(
            alert_name=alert_def["name"],
            metric_name=alert_def["metric_name"],
            threshold_type=alert_def["threshold_type"],
            threshold_value=alert_def["threshold_value"],
            actual_value=round(drop_pct, 2),
            message=f"{alert_def['message']} ({alert_def['metric_name']}: {this_month_val:.0f} this month vs {last_month_val:.0f} last month, ↓{drop_pct:.1f}%)",
        )

    return None


def _check_above_threshold(
    db: Session,
    alert_def: dict,
    now: datetime,
) -> AnalyticsAlert | None:
    """Check if metric exceeds a maximum threshold."""
    yesterday = now - timedelta(days=1)
    current_val = _get_metric_avg(db, alert_def["metric_name"], yesterday, now)

    if current_val is None:
        return None

    if current_val > alert_def["threshold_value"]:
        return AnalyticsAlert(
            alert_name=alert_def["name"],
            metric_name=alert_def["metric_name"],
            threshold_type=alert_def["threshold_type"],
            threshold_value=alert_def["threshold_value"],
            actual_value=round(current_val, 2),
            message=f"{alert_def['message']} ({alert_def['metric_name']}: {current_val:.2f}, threshold: {alert_def['threshold_value']})",
        )

    return None


def _get_metric_avg(
    db: Session,
    metric_name: str,
    start: datetime,
    end: datetime,
) -> float | None:
    """Get the average value of a daily metric over a period."""
    result = (
        db.query(func.avg(DailyMetric.value))
        .filter(
            DailyMetric.metric_name == metric_name,
            DailyMetric.metric_date >= start,
            DailyMetric.metric_date < end,
        )
        .scalar()
    )
    return float(result) if result is not None else None


# ── Anomaly Detection (Part D2) ───────────────────────────────────────


def detect_anomalies(
    db: Session,
    metric_name: str,
    window_weeks: int = 8,
    sigma_threshold: float = 2.0,
    now: datetime | None = None,
) -> dict | None -> None:
    """Detect anomalies using simple statistical method (2σ from mean).

    Compares the current week's average to the average of the past
    window_weeks weeks.  If current is > sigma_threshold standard
    deviations below the mean, flag it as an anomaly.

    Part D2 of Phase 18: "simple statistical methods, not ML."
    """
    if now is None:
        now = datetime.now(timezone.utc)

    current_week_start = now - timedelta(days=7)

    # Current week average
    current_avg = _get_metric_avg(
        db, metric_name, current_week_start, now
    )
    if current_avg is None:
        return None

    # Historical average (past 8 weeks, excluding current)
    historical_start = now - timedelta(weeks=window_weeks + 1)
    historical_end = current_week_start

    historical_values = (
        db.query(DailyMetric.value)
        .filter(
            DailyMetric.metric_name == metric_name,
            DailyMetric.metric_date >= historical_start,
            DailyMetric.metric_date < historical_end,
        )
        .all()
    )

    if len(historical_values) < 7:  # need at least a week of data
        return None

    values = [float(v[0]) for v in historical_values]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std_dev = variance ** 0.5

    if std_dev == 0:
        return None

    z_score = (current_avg - mean) / std_dev

    if z_score < -sigma_threshold:
        return {
            "metric_name": metric_name,
            "current_avg": round(current_avg, 2),
            "historical_mean": round(mean, 2),
            "std_dev": round(std_dev, 2),
            "z_score": round(z_score, 2),
            "sigma_threshold": sigma_threshold,
            "window_weeks": window_weeks,
            "message": (
                f"Anomaly detected: {metric_name} this week ({current_avg:.0f}) is "
                f"{abs(z_score):.1f}σ below {window_weeks}-week mean ({mean:.0f})"
            ),
        }

    return None
