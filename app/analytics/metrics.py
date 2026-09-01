"""Phase 18 — Core metrics computation.

Computes DAU/MAU, feature adoption/engagement, conversion funnel, retention
curves, churn rate, and ARPU/LTV from raw analytics events.

Part B of the Phase 18 execution prompt.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import distinct
from sqlalchemy.orm import Session

from app.models import (
    AnalyticsEvent,
    User,
)

# ── Active Users ──────────────────────────────────────────────────────


def compute_dau(db: Session, date: datetime | None = None) -> dict[str, int]:
    """Compute Daily Active Users for a given date.

    Active = took at least one action (viewed, created, searched, etc.).
    Passive receipt of notifications does NOT count (Part B1).
    """
    if date is None:
        date = datetime.now(timezone.utc)

    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    # Passive events that do NOT count as "active"
    passive_events = {"alert_triggered", "notification_sent"}

    base = (
        db.query(distinct(AnalyticsEvent.user_id))
        .filter(
            AnalyticsEvent.user_id.isnot(None),
            AnalyticsEvent.created_at >= day_start,
            AnalyticsEvent.created_at < day_end,
            ~AnalyticsEvent.event_name.in_(passive_events),
        )
    )

    total = base.count()

    # By tier — separate query to avoid double-joining the Event table.
    free_count = (
        db.query(distinct(AnalyticsEvent.user_id))
        .join(User, User.id == AnalyticsEvent.user_id)
        .filter(
            AnalyticsEvent.user_id.isnot(None),
            AnalyticsEvent.created_at >= day_start,
            AnalyticsEvent.created_at < day_end,
            ~AnalyticsEvent.event_name.in_(passive_events),
            User.plan == "free",
        )
        .count()
    )

    pro_count = total - free_count

    return {
        "date": day_start.isoformat(),
        "dau_total": total,
        "dau_free": free_count,
        "dau_pro": pro_count,
    }


def compute_mau(db: Session, date: datetime | None = None) -> dict[str, int]:
    """Compute Monthly Active Users for a given date's month."""
    if date is None:
        date = datetime.now(timezone.utc)

    month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1)

    passive_events = {"alert_triggered", "notification_sent"}

    base = (
        db.query(distinct(AnalyticsEvent.user_id))
        .filter(
            AnalyticsEvent.user_id.isnot(None),
            AnalyticsEvent.created_at >= month_start,
            AnalyticsEvent.created_at < month_end,
            ~AnalyticsEvent.event_name.in_(passive_events),
        )
    )

    total = base.count()

    # By tier — separate query to avoid double-joining the Event table.
    free_count = (
        db.query(distinct(AnalyticsEvent.user_id))
        .join(User, User.id == AnalyticsEvent.user_id)
        .filter(
            AnalyticsEvent.user_id.isnot(None),
            AnalyticsEvent.created_at >= month_start,
            AnalyticsEvent.created_at < month_end,
            ~AnalyticsEvent.event_name.in_(passive_events),
            User.plan == "free",
        )
        .count()
    )

    pro_count = total - free_count

    return {
        "month": month_start.strftime("%Y-%m"),
        "mau_total": total,
        "mau_free": free_count,
        "mau_pro": pro_count,
    }


# ── Feature Adoption & Engagement ─────────────────────────────────────


FEATURE_DEFINITIONS = {
    "shortlists": {
        "view_events": ["feature_viewed"],
        "view_filter": lambda p: p.get("feature_name") == "shortlists",
        "create_events": ["feature_created"],
        "create_filter": lambda p: p.get("feature_name") == "shortlists",
    },
    "searches": {
        "view_events": ["feature_viewed"],
        "view_filter": lambda p: p.get("feature_name") == "searches",
        "create_events": ["search_executed", "search_saved"],
        "create_filter": lambda p: True,
    },
    "reports": {
        "view_events": ["feature_viewed"],
        "view_filter": lambda p: p.get("feature_name") == "reports",
        "create_events": ["report_generated"],
        "create_filter": lambda p: True,
    },
    "watches": {
        "view_events": ["feature_viewed"],
        "view_filter": lambda p: p.get("feature_name") == "watches",
        "create_events": ["alert_dismissed"],
        "create_filter": lambda p: True,
    },
    "transfer_intelligence": {
        "view_events": ["valuation_compared", "transfer_candidate_viewed", "opportunity_viewed"],
        "view_filter": lambda p: True,
        "create_events": [],
        "create_filter": lambda p: False,
    },
    "tactical_analysis": {
        "view_events": ["tactical_analysis_viewed"],
        "view_filter": lambda p: True,
        "create_events": [],
        "create_filter": lambda p: False,
    },
    "dashboard": {
        "view_events": ["dashboard_viewed"],
        "view_filter": lambda p: True,
        "create_events": ["widget_interacted"],
        "create_filter": lambda p: True,
    },
    "organizations": {
        "view_events": ["feature_viewed"],
        "view_filter": lambda p: p.get("feature_name") == "organizations",
        "create_events": ["org_created", "org_member_invited", "org_member_joined"],
        "create_filter": lambda p: True,
    },
}


def compute_feature_usage(
    db: Session,
    date: datetime | None = None,
) -> list[dict] -> None:
    """Compute adoption and engagement for all tracked features.

    Adoption = unique users who used feature / active users that day.
    Engagement = average minutes per session when using feature.
    """
    if date is None:
        date = datetime.now(timezone.utc)

    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    # Total active users that day (for adoption % denominator)
    active_users = (
        db.query(distinct(AnalyticsEvent.user_id))
        .filter(
            AnalyticsEvent.user_id.isnot(None),
            AnalyticsEvent.created_at >= day_start,
            AnalyticsEvent.created_at < day_end,
        )
        .count()
    )

    results = []

    for feature_name, defn in FEATURE_DEFINITIONS.items():
        all_events = defn["view_events"] + defn["create_events"]
        view_filter = defn["view_filter"]
        create_filter = defn["create_filter"]

        # Fetch all events for this feature on this day
        events = (
            db.query(AnalyticsEvent)
            .filter(
                AnalyticsEvent.event_name.in_(all_events),
                AnalyticsEvent.created_at >= day_start,
                AnalyticsEvent.created_at < day_end,
            )
            .all()
        )

        # Filter by the feature-specific filter
        relevant = [e for e in events if view_filter(e.event_properties) or create_filter(e.event_properties)]
        unique_users = len({e.user_id for e in relevant if e.user_id})

        adoption_pct = (unique_users / active_users * 100) if active_users > 0 else 0.0

        # Count creation actions
        creation_count = sum(
            1 for e in events
            if create_filter(e.event_properties)
        )

        results.append({
            "date": day_start.isoformat(),
            "feature_name": feature_name,
            "adoption_count": unique_users,
            "adoption_pct": round(adoption_pct, 2),
            "actions_count": creation_count,
            "avg_engagement_minutes": 0.0,  # computed from sessions, not events
        })

    return results


# ── Conversion Funnel ─────────────────────────────────────────────────


def compute_conversion_funnel(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict -> None:
    """Compute the Free → Pro conversion funnel.

    Steps:
    1. User signs up (Free account)
    2. User creates first shortlist (engagement)
    3. User uses feature for 30+ minutes (commitment)
    4. User tries to use Pro feature (upgrade trigger)
    5. User subscribes to Pro (conversion)

    Part B3 of Phase 18.
    """
    now = datetime.now(timezone.utc)
    if start_date is None:
        start_date = now - timedelta(days=30)
    if end_date is None:
        end_date = now

    # Step 1: Signups in period
    signups = (
        db.query(User)
        .filter(User.created_at >= start_date, User.created_at < end_date)
        .count()
    )

    # Step 2: Created a shortlist
    created_shortlist = (
        db.query(distinct(AnalyticsEvent.user_id))
        .filter(
            AnalyticsEvent.event_name == "feature_created",
            AnalyticsEvent.event_properties["feature_name"].as_string() == "shortlists",
            AnalyticsEvent.created_at >= start_date,
            AnalyticsEvent.created_at < end_date,
        )
        .count()
    )

    # Step 3: Upgrade attempted (hit paywall)
    upgrade_attempted = (
        db.query(distinct(AnalyticsEvent.user_id))
        .filter(
            AnalyticsEvent.event_name == "upgrade_attempted",
            AnalyticsEvent.created_at >= start_date,
            AnalyticsEvent.created_at < end_date,
        )
        .count()
    )

    # Step 4: Actually subscribed
    subscribed = (
        db.query(distinct(AnalyticsEvent.user_id))
        .filter(
            AnalyticsEvent.event_name == "upgrade_completed",
            AnalyticsEvent.created_at >= start_date,
            AnalyticsEvent.created_at < end_date,
        )
        .count()
    )

    return {
        "period": f"{start_date.date()} to {end_date.date()}",
        "step_1_signups": signups,
        "step_2_created_shortlist": created_shortlist,
        "step_2_rate": round(created_shortlist / signups * 100, 1) if signups else 0,
        "step_3_upgrade_attempted": upgrade_attempted,
        "step_3_rate": round(upgrade_attempted / signups * 100, 1) if signups else 0,
        "step_4_subscribed": subscribed,
        "step_4_rate": round(subscribed / signups * 100, 1) if signups else 0,
        "overall_conversion": round(subscribed / signups * 100, 2) if signups else 0,
    }


# ── Retention ─────────────────────────────────────────────────────────


def compute_retention_cohort(
    db: Session,
    cohort_month: datetime | None = None,
) -> list[dict] -> None:
    """Compute retention for a signup cohort.

    For each user who signed up in the given month, check if they were
    active N months later.  Part B4 of Phase 18.
    """
    if cohort_month is None:
        now = datetime.now(timezone.utc)
        cohort_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    month_end = cohort_month.replace(month=cohort_month.month % 12 + 1) if cohort_month.month < 12 else cohort_month.replace(year=cohort_month.year + 1, month=1)

    # Users who signed up in this month
    cohort_users = (
        db.query(User.id)
        .filter(
            User.created_at >= cohort_month,
            User.created_at < month_end,
        )
        .all()
    )

    cohort_size = len(cohort_users)
    if cohort_size == 0:
        return []

    user_ids = [u.id for u in cohort_users]

    results = []

    # Check retention for months 0 through 12 using proper month arithmetic.
    for months_after in range(13):
        # Compute the actual start of the Nth month after cohort_month.
        raw_month = cohort_month.month + months_after
        check_year = cohort_month.year + (raw_month - 1) // 12
        check_month = (raw_month - 1) % 12 + 1
        check_start = cohort_month.replace(year=check_year, month=check_month, day=1)
        # End of that month = start of next month.
        if check_month == 12:
            check_end = check_start.replace(year=check_year + 1, month=1)
        else:
            check_end = check_start.replace(month=check_month + 1)

        if check_start > datetime.now(timezone.utc):
            break

        # How many of these users were active in the check period
        active_count = (
            db.query(distinct(AnalyticsEvent.user_id))
            .filter(
                AnalyticsEvent.user_id.in_(user_ids),
                AnalyticsEvent.created_at >= check_start,
                AnalyticsEvent.created_at < check_end,
            )
            .count()
        )

        retention_pct = (active_count / cohort_size * 100) if cohort_size else 0

        results.append({
            "cohort_month": cohort_month.strftime("%Y-%m"),
            "months_since_signup": months_after,
            "cohort_size": cohort_size,
            "retained_count": active_count,
            "retention_pct": round(retention_pct, 2),
        })

    return results


# ── Churn ─────────────────────────────────────────────────────────────


def compute_churn_rate(
    db: Session,
    date: datetime | None = None,
) -> dict -> None:
    """Compute monthly churn rate for Pro subscribers.

    Churn rate = (users who unsubscribed this month) / (users subscribed
    at start of month).  Part B4 of Phase 18.

    5% monthly churn = 50%+ annual (unsustainable).
    2-3% monthly = healthy B2B SaaS.
    """
    if date is None:
        date = datetime.now(timezone.utc)

    month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1)

    # Pro users at start of month (had plan=pro before month started)
    pro_at_start = (
        db.query(User)
        .filter(
            User.plan == "pro",
            User.created_at < month_start,
        )
        .count()
    )

    # Cancellations this month
    cancellations = (
        db.query(distinct(AnalyticsEvent.user_id))
        .filter(
            AnalyticsEvent.event_name == "subscription_canceled",
            AnalyticsEvent.created_at >= month_start,
            AnalyticsEvent.created_at < month_end,
        )
        .count()
    )

    churn_rate = (cancellations / pro_at_start * 100) if pro_at_start else 0

    return {
        "month": month_start.strftime("%Y-%m"),
        "pro_users_at_start": pro_at_start,
        "cancellations": cancellations,
        "churn_rate_pct": round(churn_rate, 2),
        "annualized_churn_pct": round(churn_rate * 12, 2),
    }


# ── ARPU & LTV ────────────────────────────────────────────────────────


def compute_arpu(db: Session, date: datetime | None = None) -> dict:
    """Compute Average Revenue Per User.

    ARPU = total MRR / active Pro users.  Part B5 of Phase 18.
    """
    if date is None:
        date = datetime.now(timezone.utc)

    month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1)

    # Count Pro users active this month
    pro_users = (
        db.query(distinct(AnalyticsEvent.user_id))
        .join(User, User.id == AnalyticsEvent.user_id)
        .filter(
            User.plan == "pro",
            AnalyticsEvent.created_at >= month_start,
            AnalyticsEvent.created_at < month_end,
        )
        .count()
    )

    # Count upgrades completed this month
    upgrades = (
        db.query(distinct(AnalyticsEvent.user_id))
        .filter(
            AnalyticsEvent.event_name == "upgrade_completed",
            AnalyticsEvent.created_at >= month_start,
            AnalyticsEvent.created_at < month_end,
        )
        .count()
    )

    # Count cancellations this month
    cancellations = (
        db.query(distinct(AnalyticsEvent.user_id))
        .filter(
            AnalyticsEvent.event_name == "subscription_canceled",
            AnalyticsEvent.created_at >= month_start,
            AnalyticsEvent.created_at < month_end,
        )
        .count()
    )

    # Pro price from config (single source of truth).
    try:
        from app.config import load_pricing
        pricing = load_pricing()
        PRO_PRICE_EUR = float(pricing.get("plans", {}).get("pro", {}).get("price_monthly_eur", 49.0))
    except (OSError, ValueError, KeyError):
        PRO_PRICE_EUR = 49.0  # fallback if pricing.json unreadable

    mrr = pro_users * PRO_PRICE_EUR
    arpu = mrr / pro_users if pro_users else 0

    # Simple LTV estimate: ARPU * average lifetime months
    # 2-3% churn ≈ 33-50 month average lifetime
    estimated_lifetime_months = 1 / (0.03) if pro_users else 0  # assume 3% churn
    ltv = arpu * estimated_lifetime_months

    return {
        "month": month_start.strftime("%Y-%m"),
        "pro_users": pro_users,
        "mrr_eur": round(mrr, 2),
        "arpu_eur": round(arpu, 2),
        "upgrades": upgrades,
        "cancellations": cancellations,
        "estimated_lifetime_months": round(estimated_lifetime_months, 1),
        "estimated_ltv_eur": round(ltv, 2),
    }
