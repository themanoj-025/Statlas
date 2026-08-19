# Valuation Model Performance

**Statlas Transfer Intelligence — How Well Does the Valuation Comparison Framework Work?**

## Overview

This document tracks the performance of the valuation comparison framework against real transfer data. The framework is intentionally simple (deterministic, non-ML) and prioritizes transparency over sophistication. Performance tracking helps calibrate expectations and identify areas for improvement.

## Model Description

The valuation comparison framework uses:
1. **Stat-based value proxy**: Average percentile rank (60%) + Statlas Index (40%), adjusted for age
2. **EUR mapping**: Quadratic formula `(score/100)² × €100M`
3. **Undervaluation detection**: Stat-based value > market value by configurable threshold (default 20%)

## Spot-Check Methodology

To validate the model, we spot-check recent high-profile transfers against what the model would have flagged:

### How to conduct a spot-check

1. Identify 10 recent major transfers with publicly reported fees
2. Before the transfer date, compute the valuation comparison for each player
3. Check whether the model would have flagged the player as undervalued (stat-based value > market value)
4. Document whether the transfer fee was above or below the market value at the time

### Performance metrics (to be populated with real data)

| Metric | Target | Actual |
|--------|--------|--------|
| True positive rate (flagged undervalued → transferred at premium) | ≥ 50% | TBD |
| False positive rate (flagged undervalued → no transfer or at discount) | ≤ 30% | TBD |
| Explanation accuracy (explanation matches the transfer narrative) | ≥ 80% | TBD |

## Known Model Limitations

1. **Quadratic EUR mapping is a simplification**: The actual market depends on many non-statistical factors (contract, reputation, negotiation leverage)
2. **No transfer fee prediction**: The model identifies relative value (undervalued vs. overvalued) but does not predict the exact transfer fee
3. **Static curves**: Age-adjustment curves are documented assumptions, not empirically calibrated
4. **Market data currency**: Valuations may be weeks or months old

## Calibration Recommendations

Based on the model's design, the following calibration is recommended:

- **Threshold 0.2 (20%)**: Good default for balanced sensitivity/specificity
- **Threshold 0.3 (30%)**: Higher precision, fewer false positives, but may miss borderline cases
- **Threshold 0.1 (10%)**: Higher recall, catches more cases, but more noise

## Changelog

- **2026-08-19:** Initial performance tracking document created for Phase 15
