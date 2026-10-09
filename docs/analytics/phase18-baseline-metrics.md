# Phase 18 — Baseline Metrics

**Date:** 2026-08-20
**Status:** Infrastructure ready, awaiting soft-launch data

---

## Purpose

This document establishes baseline metrics for Statlas product health
measurement.  Baselines are measured during soft-launch (Phase 5/7.5)
and become the reference point for measuring product improvements.

---

## Key Performance Indicators (KPIs)

### 1. Daily Active Users (DAU)

**Definition:** Unique users who took at least one action in a 24-hour period.
Passive receipt of notifications does NOT count.

**Breakdown:** DAU Free, DAU Pro (never aggregate — Constitution principle:
brutal honesty about metrics).

**Measurement:** From `analytics_events` table, count distinct user_ids
where event_name NOT IN ('alert_triggered', 'notification_sent').

**Baseline target:** Establish reliable measurement during soft-launch.
No target number until we have real user data.

---

### 2. Monthly Active Users (MAU)

**Definition:** Unique users who took at least one action in a calendar month.

**Rolling metric:** Computed on the 1st of each month for the prior month.

---

### 3. DAU/MAU Ratio (Stickiness)

**Definition:** DAU / MAU — measures how often active users return.

**Benchmarks:**
- 20%+ = good stickiness (users return frequently)
- 50%+ = excellent (daily habit)
- <10% = users visit rarely

---

### 4. Feature Adoption

**Definition:** % of active users who used a specific feature in the month.

**Formula:** (unique users who used feature this month) / (MAU) × 100

**Features tracked:** shortlists, searches, reports, watches,
transfer_intelligence, tactical_analysis, dashboard, organizations

---

### 5. Conversion Funnel (Free → Pro)

**Steps:**
1. User signs up (Free account)
2. User creates first shortlist (engagement)
3. User tries to use Pro feature (upgrade trigger)
4. User subscribes to Pro (conversion)

**Measurement:** From `analytics_events` with event names
'subscription_created', 'feature_created', 'upgrade_attempted',
'upgrade_completed'.

---

### 6. Retention Curves

**Definition:** % of users from a signup cohort still active N months later.

**Measurement:** For each cohort (users who signed up in month M),
check if they had any activity in month M+N.

**Cohorts tracked:** Monthly, last 12 months.

---

### 7. Monthly Churn Rate

**Definition:** (Pro users who unsubscribed this month) / (Pro users at
start of month) × 100

**Benchmarks:**
- 2-3% monthly = healthy B2B SaaS
- 5% monthly = 50%+ annual (unsustainable)
- 1% monthly = excellent

---

### 8. ARPU (Average Revenue Per User)

**Definition:** Total MRR / active Pro users

**Formula:** (pro_users × €49) / pro_users

**Tracked monthly** with month-over-month change.

---

### 9. LTV (Lifetime Value)

**Definition:** Estimated total revenue per user over lifetime.

**Formula:** ARPU × (1 / monthly churn rate)

**Example:** €49 ARPU × 33 months (3% churn) = €1,617 LTV

---

## Event Schema Reference

All tracked events are documented in `docs/analytics/event-schema.md`.
Every event has: name, trigger, required properties, and rationale.

---

## Data Retention Policy (Part E3)

- **Raw events:** 90 days
- **Aggregated metrics (daily/weekly/monthly):** 3 years
- **Alerts:** 1 year
- **Access logs:** 6 months

Automated deletion jobs enforce these policies.

---

## Analytics Governance

Every dashboard must include:
- Last-updated timestamp
- Data confidence note (sampling, completeness)
- Caveat on correlation vs causation
- Links to methodology

**Example footer:**
> Last updated 2026-01-15 at 22:30 UTC. All metrics based on 100% of
> events (no sampling). Note: feature adoption growth may correlate with
> retention, but causation requires further analysis.

---

## 3-Month Review Process

After 3 months of analytics data:
1. Review retention curves — are early cohorts staying engaged?
2. Review feature adoption — which features are actually used?
3. Review conversion — are users upgrading?
4. Identify one product improvement based on data
5. Document findings in `docs/analytics/phase18-review.md`

---

## Alert Thresholds

| Alert | Condition | Action |
|-------|-----------|--------|
| DAU Drop | >20% week-over-week | Check deployment logs, error rate |
| Conversion Drop | >30% month-over-month | Review upgrade flow |
| Error Rate Spike | >2% of events | Identify broken feature |
| Latency Spike | p95 > 5s | Check database queries |

**Response procedures:** See `docs/analytics/alert-response-procedures.md`
