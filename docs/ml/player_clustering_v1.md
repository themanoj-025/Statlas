# Model: Player Clustering v1

## Overview

Unsupervised k-means clustering model that discovers player archetypes — groups of
outfield players with similar statistical profiles based on per-90 statistics. The model
clusters players separately by position group (midfielders, strikers, defenders) to
produce position-appropriate archetypes.

**Constitution Addendum §1.2:** This is clustering and pattern discovery, explicitly
labeled as patterns, not predictions. Archetypes describe statistical similarity, not
player ability or potential.

## Training Data

- **Source:** FBref per-90 statistics, 2025-26 season (or latest available)
- **Provenance:** Reproducible from `app/compute/clustering.py` — query against
  `stat_snapshots` table filtered by season, league (top-5), and minutes >= 900
- **Size:** ~2000 players × 17 features (varies by position group and data availability)
- **Preprocessing:** StandardScaler (zero mean, unit variance) per position group;
  players with any missing feature values are excluded

## Architecture

- **Algorithm:** K-means clustering (sklearn)
- **Hyperparameters:**
  - n_clusters: determined by silhouette analysis (typically 6-8 per position group)
  - init: k-means++ (default)
  - n_init: 10 (default)
  - max_iter: 300 (default)
  - random_state: 42 (fixed for reproducibility)
- **Training procedure:** Fit on standardized feature matrix; convergence typically
  reached in <50 iterations

## Evaluation (Test Set)

- **Test set provenance:** 20% random holdout from training population; same season,
  same leagues, same minutes threshold
- **Primary metric:** Silhouette score (target: >= 0.30)
- **Secondary metrics:** Davies-Bouldin index (lower is better)
- **Per-subgroup metrics:** Silhouette score computed separately for each position
  group (CB, FB, DM, CM, AM, W, ST) and each league

## Limitations & Bias Audit

- **Known limitations:**
  - Only includes top-5 European leagues — archetypes may not apply to other leagues
  - Requires 900+ minutes — young players with limited game time are excluded
  - Clustering is per-position-group — cross-position archetypes are not discovered
  - Feature set is based on FBref stats — may miss tactical/positional nuances not
    captured in per-90 statistics
- **Bias audit results:**
  - Check if any position group shows significantly lower silhouette score
  - Check if any league is over/under-represented in specific archetypes
  - Check if archetype assignment varies suspiciously by league (documented in
    `docs/ml/archetype-interpretations.md`)
- **Recommended use:**
  - Top-5 European leagues, current season
  - Outfield players (midfielders, strikers, defenders) with 900+ minutes
  - Use for pattern discovery and player comparison, not for recruitment decisions

## Inference

- **Inference code:** `app/compute/clustering.py` → `assign_player_to_archetype()`
- **Input features:** Same 17 per-90 statistics as training, standardized with the
  same scaler fitted during training
- **Output format:** Archetype assignment (cluster_id), distance to center (confidence),
  top 3 distinguishing features
- **Staleness check:** If model training data is > 6 months old, error instead of
  serving (Constitution Addendum §3.2)

## Deployment

- **Version:** v1.0
- **Deployed at:** (set on first production deployment)
- **Owner:** Statlas team
- **Monitoring:** Weekly drift detection (KS tests on input distributions), assignment
  churn tracking, model staleness checks (see `docs/ml/clustering-monitoring.md`)
- **Rollback:** If model produces unexpected results, fall back to deterministic
  position-based categorization (no archetype assignment) until model is retrained
  or investigated

## Model Card Updates

This document is updated every time the model is modified or redeployed. Changes include:
- Updated training data provenance (new season data)
- Updated evaluation metrics (new silhouette score)
- Updated bias audit results (new subgroup analysis)
- Updated deployment metadata (new version, new timestamp)
