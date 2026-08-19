# Hidden Gem Detection Methodology

**Statlas Transfer Intelligence — Identifying Undervalued Performers**

## Overview

A "hidden gem" is a player performing at high statistical levels but not yet captured by major market valuations. This methodology defines how Statlas identifies these players using transparent, deterministic criteria.

## Definition

A player qualifies as a hidden gem when **all** of the following hold:

1. **Statistical performance threshold**: Statlas Index score ≥ 75th percentile
2. **Market value cap**: Latest market valuation < €30M (configurable)
3. **Data sufficiency**: At least 900 minutes played (Constitution §3: minimum qualification threshold)
4. **Positive upside**: Stat-based value estimate exceeds market value

## Upside Calculation

```
upside_eur = stat_value_eur - market_value_eur
upside_pct = (upside_eur / market_value_eur) × 100
```

Where `stat_value_eur` is computed using the valuation comparison framework's quadratic mapping:

```
stat_value_eur = (stat_value_score / 100)² × €100M
```

## Signal Strength

| Level | Criteria |
|-------|----------|
| **Strong** | 10+ percentile metrics published AND market data confidence is "high" |
| **Moderate** | 6+ percentile metrics AND market data confidence is not "low" |
| **Weak** | Fewer metrics or lower market data confidence |

## Why Players Become Hidden Gems

Common patterns:
- **Recent breakout**: Player's performance has improved sharply in the last 1-2 seasons; market valuations lag behind the improvement
- **Lower-profile league**: Playing in a league with less market attention; scouts and media haven't fully recognized the performance level
- **Late developer**: Player developed later than typical, so market valuations haven't caught up
- **Position underappreciation**: Certain position roles (defensive midfielders, ball-playing CBs) are undervalued relative to their statistical contribution

## Risk Factors

Every hidden gem opportunity explicitly surfaces risk factors:

1. **Market data confidence**: Valuations based on low-confidence data are less reliable
2. **Market recognition lag**: The player's performance level may not be recognized by the broader market yet — this is the opportunity, but also means the valuation may not increase
3. **Sample size**: If based on a single strong season, regression to mean is possible
4. **League context**: Performance may not translate across leagues (quality of opposition changes)

## Limitations

1. **No ML scoring**: This is deterministic threshold-based detection, not an ML model. ML models could be more nuanced but less explainable.
2. **Market data lag**: Valuations reflect the latest available data point, which may be weeks or months old.
3. **Binary threshold**: The 75th percentile cutoff is configurable but creates a cliff effect — a player at 74.9th percentile is excluded while 75.1th is included.
4. **No demand-side analysis**: This framework identifies supply (players worth more than they cost) but does not model demand (which clubs are looking for this profile).

## Changelog

- **2026-08-19:** Initial methodology defined for Phase 15
