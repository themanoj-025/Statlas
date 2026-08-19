# Phase 14 — Clustering Feature Engineering

## Overview

This document defines the feature matrix used for unsupervised player clustering in
Statlas. The goal is to discover player archetypes — groups of players with similar
statistical profiles — using k-means clustering on real per-90 statistics.

**Constitution Addendum §1.2:** Clustering is explicitly labeled as patterns, not
predictions. Archetypes are descriptions of statistical similarity, not claims about
player ability.

## Training Data Population

- **Source:** FBref per-90 statistics (the primary data source for outfield players)
- **Season:** 2025-26 (or latest available with >= 900 minutes)
- **Leagues:** Top-5 European leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1)
- **Minimum minutes:** 900 minutes played (same as the percentile qualification threshold)
- **Position groups:** Clustered separately — midfielders, strikers, defenders. NOT across
  positions (a defender's stat profile is fundamentally different from a striker's).
- **Goalkeepers:** Excluded from outfield clustering (their stat profile is entirely different)

## Feature Set

### Included Features (Per-90 Statistics)

| Feature | Registry ID | Category | Justification |
|---------|------------|----------|---------------|
| Pass completion % | `si_cmp_pct` | Passing | Core passing quality indicator |
| Progressive passes p90 | `si_prgr_passes_p90` | Passing | Ball progression ability |
| Pass into final third p90 | `si_final_third_p90` | Passing | Attacking contribution via passing |
| Progressive carries p90 | `si_prgr_carries_p90` | Carrying | Ball progression via dribbling |
| Carries into final third p90 | `si_carry_final_third_p90` | Carrying | Attacking contribution via carrying |
| Pressures p90 | `si_pressures_p90` | Pressing | Defensive engagement intensity |
| Pressure success rate | `si_press_success_pct` | Pressing | Defensive effectiveness |
| Tackles p90 | `si_tkl_p90` | Defensive | Ball-winning activity |
| Interceptions p90 | `si_int_p90` | Defensive | Reading the game |
| Blocks p90 | `si_blocks_p90` | Defensive | Shot/pass blocking |
| Aerial duel success rate | `si_aerial_pct` | Defensive | Aerial dominance |
| Shots p90 | `si_shots_p90` | Attacking | Goal threat volume |
| xG p90 | `si_xg_p90` | Attacking | Expected goal quality |
| Goals p90 | `si_gls_p90` | Attacking | Actual finishing output |
| Key passes p90 | `si_key_passes_p90` | Creation | Chance creation volume |
| xA p90 | `si_xa_p90` | Creation | Expected assist quality |
| Assists p90 | `si_ast_p90` | Creation | Actual assist output |

### Excluded Features (with rationale)

| Feature | Reason for exclusion |
|---------|---------------------|
| Age | Confounded with position group; would cluster by career stage rather than playing style |
| Height | Physical attribute, not playing style; available on FBref but confounds positional analysis |
| Weight | Same as height |
| Possession % | Team-level stat, not player-level; would cluster by team quality rather than individual style |
| Dispossessed p90 | Highly correlated with carries; adds noise without new information |
| Statlas Index | Derived composite metric; using it in clustering would create circular reasoning |

## Preprocessing

1. **StandardScaler:** All features standardized to zero mean, unit variance per position group.
   This ensures features with naturally larger ranges (e.g., pressures p90 ≈ 30-60) don't
   dominate features with smaller ranges (e.g., xG p90 ≈ 0.0-0.8).

2. **Missing values:** Players with any missing value in the feature set are excluded from
   clustering. The minimum-minutes filter (900+) already ensures most features are populated,
   but any remaining NaN values (e.g., no xG data from FBref for some leagues) result in
   exclusion. This is documented as a limitation.

3. **Pipeline:** A sklearn `Pipeline` with preprocessing steps ensures the exact same
   preprocessing applies at inference time for new players.

## Feature Engineering Pipeline

```
stat_snapshots (per-90 raw stats)
  → filter by: season, league (top-5), minutes >= 900, position_group != GK
  → extract: feature columns from raw_stats
  → impute/exclude: drop players with any NaN in features
  → StandardScaler: zero mean, unit variance per position group
  → output: feature matrix X (n_players × n_features)
```

## Rationale for Feature Selection

The selected features cover six dimensions of playing style:

1. **Passing quality** — How well does the player distribute the ball?
2. **Ball progression** — Does the player carry or pass the ball forward?
3. **Defensive engagement** — How actively does the player press and tackle?
4. **Aerial ability** — Can the player win headers?
5. **Goal threat** — Does the player shoot and score?
6. **Creative output** — Does the player create chances for others?

These six dimensions capture the fundamental axes of variation in outfield player
profiles, without redundancy or circular reasoning (no derived metrics included).
