# Player Valuation Age Curves

**Statlas Transfer Intelligence — Age-Adjustment Methodology**

This document defines the age-value curves used in the valuation comparison framework (Phase 15 Part B2). These are explicit, documented parameterizations — not ML-learned curves.

## Overview

Players of different ages have different value curves. A 21-year-old with 75th percentile stats is generally more valuable than a 32-year-old with identical stats, all else equal, because:

1. **Development potential** — younger players have more upside
2. **Contract horizon** — younger players can contribute for more years
3. **Resale value** — younger players retain resale value

The adjustment is **not** a prediction of future ability — it's a documented assumption about how the market typically prices age.

## Age-Value Curves by Position Group

### Strikers (ST)
- **Peak age:** 27
- **Rise rate:** 0.08 per year before peak
- **Decline rate:** 0.06 per year after peak

Rationale: Strikers peak relatively early due to physical demands. Young strikers develop quickly; decline is moderate as experience partially offsets physical decline.

### Attacking Midfielders (AM)
- **Peak age:** 26
- **Rise rate:** 0.07 per year before peak
- **Decline rate:** 0.07 per year after peak

Rationale: Creative players peak early but decline faster as pace and dynamism fade. Experience helps but less than for central midfielders.

### Wingers (W)
- **Peak age:** 26
- **Rise rate:** 0.08 per year before peak
- **Decline rate:** 0.06 per year after peak

Rationale: Wingers rely heavily on pace and acceleration, peaking early. Decline is steeper than CMs but wingers can transition to inside-forward roles.

### Central Midfielders (CM)
- **Peak age:** 27
- **Rise rate:** 0.06 per year before peak
- **Decline rate:** 0.05 per year after peak

Rationale: Box-to-box midfielders peak around 27. Experience, reading of the game, and positioning offset some physical decline.

### Defensive Midfielders (DM)
- **Peak age:** 28
- **Rise rate:** 0.05 per year before peak
- **Decline rate:** 0.04 per year after peak

Rationale: Defensive midfielders peak later — game intelligence and positioning matter more than raw athleticism. Decline is gradual.

### Full-Backs (FB)
- **Peak age:** 27
- **Rise rate:** 0.06 per year before peak
- **Decline rate:** 0.05 per year after peak

Rationale: Modern full-backs need both physical and technical ability. Peak around 27; decline moderate as they can shift to inverted roles.

### Center-Backs (CB)
- **Peak age:** 28
- **Rise rate:** 0.05 per year before peak
- **Decline rate:** 0.04 per year after peak

Rationale: Center-backs peak later — aerial ability, positioning, and leadership compensate for pace decline. Decline is the slowest of outfield positions.

### Goalkeepers (GK)
- **Peak age:** 29
- **Rise rate:** 0.04 per year before peak
- **Decline rate:** 0.03 per year after peak

Rationale: Goalkeepers peak latest of all positions. Reflexes and distribution improve with experience; decline is very gradual.

## Formula

```
age_adjustment(age, position) =
    if age <= peak_age:
        max(0.5, 1.0 - (peak_age - age) * rise_rate)
    else:
        max(0.4, 1.0 - (age - peak_age) * decline_rate)
```

The adjustment is clamped between 0.4 and 1.0+:
- **1.0** = at peak age
- **0.5-0.99** = below peak (development years)
- **0.4-0.99** = above peak (decline years)

The floor of 0.4 ensures very old players still have some residual value (experience, leadership) rather than being valued at zero.

## Application

The age adjustment is multiplied into the stat-based value proxy:

```
stat_value = (avg_percentile * 0.6 + index_score * 0.4) * age_adjustment
```

This means a 21-year-old CM with 75th percentile stats gets:
```
age_adj = 1.0 - (27 - 21) * 0.06 = 1.0 - 0.36 = 0.64
stat_value = 75 * 0.64 = 48.0
```

While a 27-year-old CM with the same stats gets:
```
age_adj = 1.0
stat_value = 75 * 1.0 = 75.0
```

The 21-year-old scores lower because the market typically discounts younger players' current output in favor of future potential — but the gap is smaller than raw stats alone would suggest because the younger player's potential adds value.

## Limitations

1. **These are market-typical curves, not universal rules.** Individual players deviate significantly — a world-class 32-year-old is worth more than a mediocre 22-year-old.

2. **League context matters.** These curves are calibrated for top-5 leagues. Value trajectories differ in lower leagues.

3. **The curves do not account for injury history, contract situation, or off-field factors.** These are handled separately by the risk module.

4. **The curves are explicitly not ML-learned.** They are parameterized assumptions documented here so they can be debated, adjusted, and audited.

## References

- FIFA 22 Player Rating methodology (partial inspiration for peak-age assumptions)
- Transfermarkt historical value data (market validation of age curves)
- Academic literature on athlete aging curves (Rosen & Spaeter, 1984; Berri et al., 2004)

## Changelog

- **2026-08-19:** Initial curves defined for Phase 15
