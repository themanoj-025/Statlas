# Transfer Valuation Methodology

**Statlas Transfer Intelligence — How Valuation Comparison Works**

## Overview

The valuation comparison framework is a **transparent, deterministic** tool that compares a player's statistical performance rank against their market valuation. Unlike ML-based valuation models, every factor is visible and auditable.

## Core Concept

1. **Statistical Performance Rank (SPR)** — a score (0-100) combining published percentile ranks and the Statlas Index, adjusted for age
2. **Market Valuation** — the player's estimated market value from a licensed third-party source
3. **Valuation Gap** — the difference between SPR-implied value and market value
4. **Signal Strength** — confidence in the comparison based on data quality

## Stat-Based Value Proxy

### Inputs

| Factor | Weight | Source |
|--------|--------|--------|
| Average percentile rank | 60% | Published percentile snapshots (Phase 2) |
| Statlas Index score | 40% | Weighted index score (Phase 0) |
| Age adjustment | Multiplied | Per-position age curves (documented separately) |

### Formula

```
stat_value_score = (avg_percentile * 0.6 + index_score * 0.4) * age_adjustment
```

### EUR Mapping

To convert the 0-100 score to an approximate EUR value:

```
stat_value_eur = (stat_value_score / 100)² × €100M
```

This is a **quadratic mapping** — top performers (90th+) are valued exponentially higher than median performers, reflecting how the football transfer market prices elite talent disproportionately.

Examples:
- 95th percentile → (0.95)² × €100M = **€90.25M**
- 75th percentile → (0.75)² × €100M = **€56.25M**
- 50th percentile → (0.50)² × €100M = **€25.00M**
- 25th percentile → (0.25)² × €100M = **€6.25M**

This mapping is a documented simplification. The actual market value depends on many factors (contract, age, position scarcity, reputation) that this framework captures separately.

## Undervaluation Detection

A player is flagged as "potentially undervalued" when:

```
(stat_value_eur - market_value_eur) / market_value_eur > threshold
```

Default threshold: **20%** — meaning stat-based value exceeds market value by 20%+.

The threshold is configurable (0.0-1.0) and documented in every API response. Higher thresholds reduce false positives but may miss borderline cases.

## Signal Strength

| Level | Criteria |
|-------|----------|
| **Strong** | 10+ percentile metrics published AND market data confidence is "high" |
| **Moderate** | 6+ percentile metrics AND market data confidence is not "low" |
| **Weak** | Fewer metrics or lower market data confidence |

Signal strength is displayed alongside every valuation comparison so users can calibrate their confidence in the recommendation.

## Overvaluation

Overvaluation is flagged using the same logic inverted:

```
(market_value_eur - stat_value_eur) / stat_value_eur > threshold
```

**Important:** Overvaluation is NOT necessarily negative. Common legitimate reasons for overvaluation:
- Young player with high potential but low current stats
- Celebrity/brand factor increasing market value beyond pure performance
- Scarcity premium for rare position profiles
- Contract situation inflating transfer fee expectations

The framework surfaces the gap as information, not judgment.

## Limitations

1. **Simplified EUR mapping** — the quadratic formula is a rough approximation. Actual market values depend on many non-statistical factors.
2. **Market data currency** — valuations reflect the latest available data point, which may be weeks or months old.
3. **League context** — the same percentile performance may command different values in different leagues.
4. **No ML** — this is intentionally not an ML model. ML models can be more accurate but less explainable. This framework prioritizes transparency.

## Integration with Risk Module

The valuation comparison is paired with the risk assessment module (Part E) to provide:
- **Valuation confidence** — how certain is the market data?
- **Translation risk** — would this player perform similarly in a new context?
- **Contract situation** — how available is this player?

Together, these give a complete picture: "This player may be undervalued (stat-based value > market value), with high confidence in the valuation, medium transfer risk, and high availability (expiring contract)."

## Changelog

- **2026-08-19:** Initial methodology defined for Phase 15
