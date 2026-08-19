# Phase 14 — Clustering Production Monitoring

## Overview

This document defines the monitoring infrastructure for the player clustering model,
following the ML Constitution Addendum §4. The goal is to detect data drift, model
degradation, and assignment instability before they affect user-facing outputs.

## Monitoring Dimensions

### 1. Input Drift Detection

**What:** Are incoming player feature distributions shifting away from training data?

**Method:** Weekly Kolmogorov-Smirnov (KS) test comparing current season's feature
distributions against training data distributions. Per-feature KS test with
Bonferroni correction for multiple comparisons.

**Threshold:** If any feature's KS test p-value < 0.05 (after Bonferroni correction),
flag as potential drift.

**Response:** If drift detected:
1. Log the alert in `clustering_monitoring_log`
2. Check if the drift is from a data quality issue (investigate) or genuine
   distribution shift (may need retraining)
3. If data quality issue, do NOT retrain — fix the data first

### 2. Output Drift Detection

**What:** Are archetype assignment distributions changing unexpectedly?

**Method:** Track the proportion of players in each archetype week-over-week.
Compute chi-squared test of independence between current and previous week's
assignment distributions.

**Threshold:** If chi-squared test p-value < 0.01, flag as assignment drift.

**Response:** If assignment drift detected:
1. Check if input drift was also detected (correlated drift = expected)
2. If assignment drift without input drift, investigate model stability
3. Log the alert for manual review

### 3. Assignment Churn Rate

**What:** What percentage of players change archetype between weekly runs?

**Method:** For each player with a previous assignment, compare current assignment.
Churn rate = (players who changed) / (players with previous assignment).

**Threshold:** > 15% churn rate is a drift signal. > 20% is a strong signal.

**Response:** If churn > 15%:
1. Log the alert
2. Check if this correlates with a data refresh (expected after new data)
3. If churn is high without a data refresh, investigate model stability

### 4. Model Staleness Check

**What:** Is the model's training data too old?

**Method:** Compare current date against model's training_date. If difference >
staleness_months (default 6), the model must NOT serve predictions.

**Response:** If stale:
1. Error loudly — do not serve predictions
2. Log the alert
3. Trigger retraining or escalate to model owner

## Monitoring Log Schema

All monitoring events are logged to `clustering_monitoring_log`:

| Field | Type | Description |
|-------|------|-------------|
| model_id | FK | Which model this log entry relates to |
| logged_at | timestamp | When the log entry was created |
| log_type | string | One of: drift, churn, retrain, alert, info |
| details | JSON | Free-form details about the event |
| metric_name | string | Which metric was measured (if applicable) |
| metric_value | float | The measured value |
| threshold | float | The threshold that was crossed (if applicable) |
| alert_triggered | bool | Whether this event triggered an alert |

## Weekly Monitoring Job

The monitoring job runs as part of the weekly refresh (after archetype reassignment):

1. Run KS tests on current feature distributions
2. Compute assignment churn rate
3. Check model staleness
4. Log all results to monitoring log
5. If any alert threshold is crossed, log an alert entry

## Response Procedures

### If silhouette score drops below 0.40
- Do NOT automatically retrain
- Investigate data quality first
- Check for data pipeline issues (missing leagues, corrupted stats)
- Only retrain after confirming data quality is good

### If churn > 20%
- Check for anomalies in the data (new leagues, bulk transfers)
- Verify the training data is still representative
- If training data is stale, schedule retraining
- If training data is current, investigate cluster stability

### If input drift detected
- Compare affected feature distributions visually
- Determine if drift is from data quality or genuine change
- If genuine, consider retraining with updated data
- If data quality, fix the pipeline first

### If model is stale (>6 months)
- Trigger retraining with latest data
- Compare new model's silhouette score against decision threshold
- If new model meets threshold, deploy (replace old version)
- If new model fails threshold, keep old model and investigate
