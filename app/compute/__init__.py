"""Statlas computation layer: percentiles, index, anomaly detection.

These modules implement, exactly and testably, the locked definitions from
`methodology.md` and `percentile-rules.md`:
- fractional-rank percentile with tie midpoint:  P = (B + 0.5E) / N * 100
- grouping within {season, position group, league tier}
- 900-minute qualifying threshold, 30-player minimum pool
- index = weighted mean of metric percentiles, weights from config (never
  hardcoded numbers in code).
"""
