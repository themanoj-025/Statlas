# Statlas Methodology — The Statlas Index

*Phase 0 deliverable A1. This document defines the Statlas Index (the composite player-performance metric) in full: input metrics, position-group weighting, normalization method, qualifying threshold, and the complete public-facing methodology page copy. It is the reference the Metric Registry (§5 of the Constitution) is generated from in Phase 1 — the metric IDs, source columns, and precedence rules below are the locked inputs for the data pipeline.*

*Related documents: `percentile-rules.md` (grouping, cadence, immutability) · `data-compliance-notes.md` (source terms) · `design-system.md` (presentation of percentiles and the index).*

---

## 1. What the Statlas Index is

The Statlas Index is a **descriptive composite score** that answers one question: *"How productive is this player's per-90 output relative to their positional peers in comparable leagues this season?"*

It is deliberately **not**:

- a prediction of future performance or transfer value;
- a rating of overall ability or "quality";
- a measure of role within a team's system, quality of opposition, or game state.

It is a **weighted average of percentile ranks**: each of a player's underlying per-90 statistics is converted into a percentile within their position group and league tier, and those percentiles are combined with position-specific weights. The result is a number from 0–100 where **100 means "ranked at the top of the peer group on every input metric."**

The formula is shown in full below. Statlas publishes its work; there is no hidden term in the index.

---

## 2. Input metrics

Thirteen outfield metrics and four goalkeeper metrics feed the index. Every metric name below is a **real sourceable column** on FBref (Sports Reference) or a real key in Understat's embedded JSON. The source, exact column, unit, and direction are fixed here and will be recorded per-metric in the Metric Registry.

### 2.1 Outfield metrics (12 + pass completion)

| # | Registry ID | Metric | Definition | Source · exact column | Unit | Direction |
|---|---|---|---|---|---|---|
| 1 | `si_gls_p90` | Goals per 90 | Goals scored per 90 minutes | FBref · Standard Stats · `Gls` (÷ `Min`) | goals/90 | higher is better |
| 2 | `si_xg_p90` | xG per 90 | Expected goals per 90 minutes | Understat JSON · `xG` (top-5 leagues); FBref · Standard Stats · `xG` elsewhere | xG/90 | higher is better |
| 3 | `si_sh_p90` | Shots per 90 | Total shots per 90 minutes | FBref · Shooting · `Sh` | shots/90 | higher is better |
| 4 | `si_prgp_p90` | Progressive passes per 90 | Completed passes that move the ball ≥10 yards toward the opponent's goal, or into the penalty area, per 90 | FBref · Passing · `PrgP` | passes/90 | higher is better |
| 5 | `si_prgc_p90` | Progressive carries per 90 | Carries that move the ball ≥10 yards toward the opponent's goal, or into the penalty area, per 90 | FBref · Possession · `PrgC` | carries/90 | higher is better |
| 6 | `si_xag_p90` | xAG per 90 | Expected assisted goals per 90 minutes | FBref · Passing · `xAG` | xAG/90 | higher is better |
| 7 | `si_kp_p90` | Key passes per 90 | Passes leading directly to a shot per 90 | FBref · Passing · `KP` (cross-check Understat JSON · `key_passes`) | passes/90 | higher is better |
| 8 | `si_tkl_p90` | Tackles per 90 | Number of players tackled (successful tackles) per 90 | FBref · Defense · `Tkl` | tackles/90 | higher is better |
| 9 | `si_int_p90` | Interceptions per 90 | Interceptions per 90 minutes | FBref · Defense · `Int` | interceptions/90 | higher is better |
| 10 | `si_press_p90` | Pressures per 90 | Total pressing actions (applying pressure to a player controlling the ball) per 90 | FBref · Defense · `Press` | pressures/90 | higher is better |
| 11 | `si_cmp_pct` | Pass completion % | Completed passes ÷ attempted passes | FBref · Passing · `Cmp%` | percentage | higher is better |
| 12 | `si_dis_p90` | Dispossessed per 90 | Times the player is dispossessed while attempting to control the ball, per 90 | FBref · Possession · `Dis` | events/90 | **lower is better** |

### 2.2 Goalkeeper metrics (4)

| # | Registry ID | Metric | Definition | Source · exact column | Unit | Direction |
|---|---|---|---|---|---|---|
| G1 | `si_save_pct` | Save percentage | Saves ÷ shots on target faced | FBref · Goalkeeping · `Save%` | percentage | higher is better |
| G2 | `si_psxg_ga_p90` | PSxG − GA per 90 | Post-shot expected goals faced minus goals conceded, per 90 (goals prevented above/below expectation) | Derived: FBref · Advanced Goalkeeping · `PSxG` − FBref · Goalkeeping · `GA`, ÷ `Min` | goals/90 | higher is better |
| G3 | `si_ga_p90` | Goals against per 90 | Goals conceded per 90 minutes | FBref · Goalkeeping · `GA` (÷ `Min`) | goals/90 | **lower is better** |
| G4 | `si_cross_pct` | Crosses stopped % | Percentage of crosses faced that the goalkeeper successfully stopped/claimed | FBref · Advanced Goalkeeping · `Cross+%` | percentage | higher is better |

### 2.3 xG model consistency rule

Understat and FBref use **different xG models** (Understat's neural-network model vs. FBref's Opta model). Mixing models inside one comparison group would bias percentiles, so the rule is fixed at the group level, not the player level:

- **Tier 1 (Big-5) percentiles: xG/xA inputs use the Understat model only** (Understat covers all five top leagues, giving one consistent model across the whole group).
- **Tier 2 and Tier 3 percentiles: xG/xA inputs use FBref's Opta-model columns only.**

Within any single percentile group, exactly one xG model is used. A documented consequence: **an xG percentile in Tier 1 is not directly comparable to an xG percentile in Tier 2** — the public page and the UI label this ("percentile computed within league tier, per methodology").

The same single-model-per-group rule applies to every metric where a cross-check source exists.

### 2.4 Metric display rules — null vs. zero and sample floors (registry-ready)

Constitution §3 requires every metric to define whether a missing value displays as **N/A or 0**, resolved per metric and never left to the rendering layer. The rules below are fixed here and recorded per-metric in the Metric Registry in Phase 1:

| Metrics | Insufficient sample → shows | Null-vs-zero policy when sample is met |
|---|---|---|
| `si_gls_p90`, `si_xg_p90`, `si_sh_p90`, `si_prgp_p90`, `si_prgc_p90`, `si_xag_p90`, `si_kp_p90`, `si_tkl_p90`, `si_int_p90`, `si_press_p90`, `si_dis_p90` | minutes < 180 → **N/A** | a genuine zero (e.g., 0 goals) displays as **0.00**; a missing/absent value (source gap) displays as **N/A** — the two are distinguishable and logged |
| `si_cmp_pct` | attempted passes < 50 → **N/A** (a completion % on fewer than 50 passes is noise) | percentage to one decimal; a 100% on 50+ passes displays as 100.0 |
| `si_save_pct` | shots on target faced < 20 → **N/A** | percentage; zero is not meaningful here so a genuine low value still shows its number |
| `si_psxg_ga_p90` | minutes < 180 → **N/A** | a genuine 0.00 (conceded exactly what post-shot xG expected) displays as 0.00 |
| `si_ga_p90` | minutes < 180 → **N/A** | a genuine 0.00 GA/90 displays as 0.00 |
| `si_cross_pct` | crosses faced < 10 → **N/A** | percentage |

**Index display rule:** below the 900-minute qualifying threshold the index shows "pending qualification — needs X more minutes", never a score and never 0 (Constitution §3; see §6).

---

## 3. Position groups and assignment

The index is computed within a position group. Statlas uses **eight outfield groups** and one goalkeeper group.

**Primary assignment — FBref player-page position label.** Position is taken from the natural-language position on the player's FBref profile page (e.g., "Right-Back", "Centre-Back", "Defensive Midfield", "Central Midfield", "Attacking Midfield", "Left Winger", "Right Winger", "Centre-Forward", "Second Striker", "Goalkeeper") and mapped via the label table below. This label is more granular than the Standard-Stats `Pos` code and is what correctly separates full-backs from centre-backs — both of which FBref's `Pos` code usually lists as plain `DF`.

| FBref player-page label (primary) | Statlas group |
|---|---|
| Goalkeeper | GK |
| Centre-Back | CB |
| Left-Back, Right-Back | FB |
| Defensive Midfield | DM |
| Central Midfield | CM |
| Attacking Midfield | AM |
| Left Winger, Right Winger | W |
| Centre-Forward, Second Striker | ST |

**Fallback — Standard-Stats `Pos` code.** When the player-page label is unavailable, the `Pos` code mapping below is used. Every fallback assignment is logged; anything unrecognised is flagged for manual review in the player-reconciliation step — never silently guessed.

| FBref `Pos` code (fallback) | Statlas group |
|---|---|
| `GK` | GK |
| `DF` | CB (fallback only — many full-backs are coded `DF`; the review log flags them) |
| `DF,MF` | FB |
| `MF` | CM |
| `MF,FW` | AM |
| `FW` | ST |
| `FW,MF` | W |

This is a deliberate simplification with a visible consequence: a full-back deployed as an auxiliary winger, or a centre-back asked to build play, is still scored against the group their listed position implies. Position assignment is a documented limitation (see §9), and the review log — the same mechanism used for player-name reconciliation — catches systematic misassignments.

---

## 4. Weighting: the Statlas Index formula

The Statlas Index is the weighted sum of the player's metric percentiles:

```
Statlas Index = Σ ( wᵢ × pᵢ )

where:
  pᵢ = player's percentile (0–100) on metric i, within {season, position group, league tier}
  wᵢ = position-group weight for metric i
  Σ wᵢ = 1.00  (every row sums to 1.0)
```

Percentiles are computed exactly as specified in `percentile-rules.md` (fractional-rank method, tie midpoint). The index is a weighted average of percentiles and is therefore itself bounded 0–100. It is **not** re-percentiled: a weighted average of ranks is simpler to audit than a second rank transform, and "the index is a weighted average of your percentile ranks" is the one-sentence explanation a scout can trust.

### 4.1 Outfield weights (columns are the 12 outfield metrics)

| Group | Gls | xG | Sh | PrgP | PrgC | xAG | KP | Tkl | Int | Press | Cmp% | Dis | Σ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **ST** | 0.30 | 0.20 | 0.10 | 0.05 | 0.05 | 0.10 | 0.05 | 0.02 | 0.02 | 0.05 | 0.05 | 0.01 | 1.00 |
| **W** | 0.15 | 0.10 | 0.05 | 0.10 | 0.15 | 0.20 | 0.10 | 0.02 | 0.02 | 0.05 | 0.05 | 0.01 | 1.00 |
| **AM** | 0.15 | 0.10 | 0.05 | 0.10 | 0.05 | 0.25 | 0.15 | 0.02 | 0.02 | 0.05 | 0.05 | 0.01 | 1.00 |
| **CM** | 0.05 | 0.05 | 0.02 | 0.20 | 0.10 | 0.15 | 0.10 | 0.08 | 0.05 | 0.08 | 0.10 | 0.02 | 1.00 |
| **DM** | 0.02 | 0.02 | 0.01 | 0.15 | 0.08 | 0.05 | 0.03 | 0.15 | 0.12 | 0.15 | 0.18 | 0.04 | 1.00 |
| **FB** | 0.03 | 0.03 | 0.02 | 0.18 | 0.18 | 0.10 | 0.05 | 0.12 | 0.10 | 0.08 | 0.08 | 0.03 | 1.00 |
| **CB** | 0.02 | 0.03 | 0.01 | 0.18 | 0.05 | 0.02 | 0.01 | 0.18 | 0.15 | 0.15 | 0.16 | 0.04 | 1.00 |

**Why each row is weighted this way** (one sentence per group):

- **ST** — Goals and xG are the primary outputs of the position, so 50% of the index rests on them, with shots (0.10) proxying volume of chances; creation and progression are rewarded modestly because modern centre-forwards are expected to contribute, and defensive and retention weights are kept near-zero because they are not the job.
- **W** — Creation (xAG 0.20, KP 0.10) and progressive carries (0.15) are a winger's main currency, so half the weight sits there, with finishing (0.25 combined) second and a token defensive weight for the pressing work wingers are asked to do.
- **AM** — The attacking midfielder is creation-first (xAG 0.25, KP 0.15), with finishing (0.25 combined) and progression (0.15) as secondary output channels and near-zero defensive weight.
- **CM** — The central midfielder is the balanced engine: progressive passing (0.20) is the single largest input, creation and carrying follow (0.25 combined), and the midfield defensive block (tackles, interceptions, pressures, completion) carries 0.31 combined because losing or winning midfield duels is the position's second job.
- **DM** — Retention and disruption dominate: pass completion (0.18), tackles (0.15), pressures (0.15) and interceptions (0.12) are 60% of the score, with progressive passing (0.15) covering build-up contribution and attacking output kept negligible.
- **FB** — The full-back's dual mandate is split almost evenly: progression by pass and carry (0.36 combined) and the defensive block (0.30 combined), with wide-area creation (xAG 0.10) as a meaningful third.
- **CB** — Defence and build-up are the centre-back's entire job: the defensive block (tackles, interceptions, pressures) plus retention (Cmp%) is 64% of the score, with progressive passing (0.18) recognising the modern centre-back's first-phase contribution; shooting and creation are near-zero.

### 4.2 Goalkeeper weights

Goalkeepers are scored on a separate four-metric model because none of the twelve outfield inputs meaningfully apply to them. These weights sum to 1.00.

| Metric | Weight | Why |
|---|---|---|
| Save% | 0.35 | Shot-stopping is the position's defining output, and save percentage is its cleanest per-90-free rate. |
| PSxG − GA per 90 | 0.30 | Quality-adjusted prevention: the single best available signal for stopping shots that should be stopped. |
| GA per 90 (inverted) | 0.20 | Contextual defensive weight: conceding few goals is part of the job even when shot-stopping is average. |
| Cross+% | 0.15 | Command of the box on crosses is a distinct, measurable duty; deliberately no passing metric, because FBref goalkeeper passing samples are small and noisy at MVP scope. |

---

## 5. Normalization method

**Chosen method: percentile rank within {season, position group, league tier}, mapped directly to 0–100.**

For a metric value `v` of a player in a group of `N` qualifying players:

```
P = ( B + 0.5 × E ) / N × 100

where:
  B = number of qualifying peers with a value strictly below v
  E = number of qualifying peers with a value exactly equal to v
```

- **Ties** (very common in integer per-90 stats after rounding) share the **midpoint** percentile — two identical values get the same percentile, and the reported value is the honest midpoint of their tied rank block.
- **Lower-is-better metrics** (`si_dis_p90`, `si_ga_p90`) invert the comparison: percentile is computed from the fraction of peers *above* the value, so a low rate still scores high.
- **Not z-scored.** Goals, xG, shots, and tackles per 90 are right-skewed; a z-score lets a handful of outliers stretch the scale and can produce negative scores that are hard to communicate. Percentiles are distribution-free, bounded 0–100, and directly interpretable: "a percentile of 87 means the player's value exceeds 87% of qualifying peers in the same position group and league tier this season."
- **No other scaling is applied anywhere.** There is no multiplier, no "form" factor, no league-strength fudge after the percentile transform. If a number in the pipeline is not one of the inputs above or a sum of weighted percentiles, it is not part of the index.

Grouping and its tradeoffs are specified in `percentile-rules.md`.

---

## 6. Qualifying threshold

**A player receives a Statlas Index score only after 900 league minutes in the current season.**

Justification, not assertion:

1. **Statistical reliability.** Per-90 rates of low-frequency events are noisy at small samples. For a goals rate λ (expected events over the season), the standard error of the per-90 rate is `sqrt(λ) / (minutes/90)`. At 450 minutes a 0.50-goals-per-90 player has a standard error of roughly ±0.32; at 900 minutes the same player's rate has a standard error of roughly ±0.22 — and each additional match adds progressively less precision. 900 minutes (≈ 10 full matches) is the point where the rate's noise drops below roughly half its value for the index's most event-driven inputs.
2. **Percentile stability.** A percentile rank's standard error shrinks with peer-group size: for a percentile near the median it is approximately `1/(2√N)` (the binomial standard error of a 0.5 proportion). A 900-minute floor keeps Tier 1 groups at roughly 150–400 qualifying players per position group deep into a season, which is the difference between a defensible percentile and a lottery.
3. **Product timing.** 900 minutes is reached around matchday 10–14 of a Big-5 season, which is when scouting questions become real questions. A lower floor (e.g., 450) would publish noise; a higher floor (e.g., 1,350) would exclude the emerging players scouts are looking for.

A player below 900 minutes sees an explicit **"pending qualification — needs X more minutes"** state, never a partial or estimated index score. The threshold is displayed next to every index value and in the methodology page (Constitution §3: "never hidden").

---

## 7. Worked example (illustrative arithmetic, not player data)

To make the formula legible, here is the arithmetic with a hypothetical profile. *No real player produced these numbers; this is a paper exercise.*

A Tier 1 striker this season, 1,400 minutes played:

| Metric | Raw per-90 | Percentile in group | Weight | Contribution |
|---|---|---|---|---|
| Goals | 0.72 | 88 | 0.30 | 26.4 |
| xG | 0.65 | 82 | 0.20 | 16.4 |
| Shots | 3.4 | 71 | 0.10 | 7.1 |
| Progressive passes | 2.1 | 55 | 0.05 | 2.75 |
| Progressive carries | 1.4 | 62 | 0.05 | 3.1 |
| xAG | 0.18 | 74 | 0.10 | 7.4 |
| Key passes | 1.6 | 68 | 0.05 | 3.4 |
| Tackles | 0.4 | 34 | 0.02 | 0.68 |
| Interceptions | 0.3 | 41 | 0.02 | 0.82 |
| Pressures | 14.1 | 47 | 0.05 | 2.35 |
| Pass completion | 71.5 | 39 | 0.05 | 1.95 |
| Dispossessed (inv.) | 1.9 | 45 | 0.01 | 0.45 |
| **Index** | | | **1.00** | **72.8** |

The player's index is 72.8, which reads as "72.8 = the weighted average of this striker's percentile ranks against Tier 1 strikers this season." No step in that arithmetic is hidden.

---

## 8. Public methodology page copy

*The following is the complete copy for the public `/methodology` page, in Statlas voice. It is generated from the Metric Registry in Phase 2 so it cannot drift from the code that produces the numbers (Constitution §5).*

---

# The Statlas Index — how it works

**Statlas publishes its formula.** Most analytics tools treat their composite score as a trade secret. We do not. Every number on this page traces to a documented calculation, and the calculation is the one the site uses. If you find a discrepancy between this page and a number you see, that is a bug — tell us.

## What the Index measures

The Statlas Index answers one question: **how productive is a player's per-90 output relative to their positional peers in comparable leagues this season?**

It is a weighted average of percentile ranks. Each underlying statistic is converted into a percentile within the player's position group and league tier, and those percentiles are combined with position-specific weights. Scores run 0–100. A score of 100 would mean "top of the peer group on every input metric."

The Index measures **per-90 output**. It does not measure talent, future value, or how good a player "is" in some general sense. Read it as what it is: a comparison of this season's per-90 production against a defined peer group.

## The inputs

The Index uses twelve outfield statistics and four goalkeeper statistics, all sourced from FBref and Understat. The exact source columns are:

**Outfield** — goals per 90, xG per 90, shots per 90, progressive passes per 90, progressive carries per 90, expected assisted goals per 90, key passes per 90, tackles per 90, interceptions per 90, pressures per 90, pass completion %, and times dispossessed per 90 (the last counts against the score: a lower rate is better).

**Goalkeepers** — save %, PSxG minus goals against per 90, goals against per 90 (lower is better), and percentage of crosses stopped.

## The weights

The Index does not treat every statistic equally, and the weights depend on position. A striker's index leans on goals and xG; a centre-back's leans on defensive actions and build-up. The full weighting table is below. Every row sums to 1.00.

**Outfield weights** (columns: Gls, xG, Sh, PrgP, PrgC, xAG, KP, Tkl, Int, Press, Cmp%, Dis)

| Group | Gls | xG | Sh | PrgP | PrgC | xAG | KP | Tkl | Int | Press | Cmp% | Dis |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ST | 0.30 | 0.20 | 0.10 | 0.05 | 0.05 | 0.10 | 0.05 | 0.02 | 0.02 | 0.05 | 0.05 | 0.01 |
| W | 0.15 | 0.10 | 0.05 | 0.10 | 0.15 | 0.20 | 0.10 | 0.02 | 0.02 | 0.05 | 0.05 | 0.01 |
| AM | 0.15 | 0.10 | 0.05 | 0.10 | 0.05 | 0.25 | 0.15 | 0.02 | 0.02 | 0.05 | 0.05 | 0.01 |
| CM | 0.05 | 0.05 | 0.02 | 0.20 | 0.10 | 0.15 | 0.10 | 0.08 | 0.05 | 0.08 | 0.10 | 0.02 |
| DM | 0.02 | 0.02 | 0.01 | 0.15 | 0.08 | 0.05 | 0.03 | 0.15 | 0.12 | 0.15 | 0.18 | 0.04 |
| FB | 0.03 | 0.03 | 0.02 | 0.18 | 0.18 | 0.10 | 0.05 | 0.12 | 0.10 | 0.08 | 0.08 | 0.03 |
| CB | 0.02 | 0.03 | 0.01 | 0.18 | 0.05 | 0.02 | 0.01 | 0.18 | 0.15 | 0.15 | 0.16 | 0.04 |

**Goalkeeper weights**

| Metric | Weight |
|---|---|
| Save% | 0.35 |
| PSxG − GA per 90 | 0.30 |
| GA per 90 (lower is better) | 0.20 |
| Cross+% | 0.15 |

Each weight is deliberate and documented in the changelog. We did not tune weights against any specific player's numbers, and we will publish any future change to them in the changelog before it takes effect.

## The normalization

A raw per-90 value is converted to a percentile within the player's position group and league tier this season:

```
P = ( B + 0.5 × E ) / N × 100
```

…where B is the number of qualifying peers below the player's value, E is the number exactly equal, and N is the total number of qualifying players in the group. Ties split the difference; the calculation is the standard fractional-rank percentile. Percentiles, not z-scores, because per-90 distributions are skewed and percentiles stay honest about that. A percentile of 87 means "exceeds 87% of qualifying peers in this group."

**League tiers.** Percentiles are computed within a league tier, not within a single league and not globally:

- **Tier 1** — the Big-5 first divisions: Premier League, La Liga, Serie A, Bundesliga, Ligue 1.
- **Tier 2** — Eredivisie, Primeira Liga, Belgian Pro League, Süper Lig, Scottish Premiership, Austrian Bundesliga, Swiss Super League, Greek Super League, Danish Superliga.
- **Tier 3** — Big-5 second divisions and other leagues as coverage expands (see the data coverage page).

Computing within a tier makes cross-league comparison within that tier meaningful while avoiding the distortion of comparing a striker against a pool that mixes five elite leagues with second divisions. Because of the tier structure, **percentiles are labelled with their tier** and cannot be read as global rankings. xG values use one model per tier (Understat for Tier 1, FBref for Tiers 2–3) so no percentile mixes two xG models.

## The qualifying threshold

A player receives an Index score after **900 league minutes** in the current season, about ten full matches. Below that, sample sizes make per-90 rates — especially goals and xG — too noisy to rank fairly. Below the threshold a player shows as "pending qualification," not as a low score. The threshold is a floor, not a target: it exists to keep the comparison honest.

## What the Index does not do

Honesty about limits is part of the method. The Index:

- does not account for **role within a system** — a full-back asked to tuck in and defend is compared to full-backs, not to the role they actually play;
- does not weight **quality of opposition** — a Tier 1 striker's percentile counts a match against a promoted side the same as one against the league leader;
- does not account for **game state** — a team defending a lead produces different per-90 output than one chasing the game;
- is not adjusted for **team strength** — playing for the league's best side inflates some inputs (chances created, touches in the box) relative to playing for a bottom-half side;
- does not correct **penalty kicks** in the goals and xG inputs (that is a known, documented simplification for MVP);
- is **not a prediction** of future performance, transfer value, or injury risk;
- uses one xG model per tier, so **an xG percentile in Tier 1 is not directly comparable to one in Tier 2**;
- is computed from **per-90 output, not minutes-weighted contribution** — a player who delivers in 20 minutes off the bench each week can score well while contributing little total volume. Volume is visible on the player page; it is deliberately not folded into the Index.

None of these limitations are fixable with a parameter tweak, and we are not going to pretend otherwise. If you need a model that adjusts for opposition quality and game state, this is not that model.

## Data and refresh

The Index is recomputed after every weekly data refresh (snapshot date is shown on every stat block). Each recomputation creates a new immutable snapshot of percentile and index values; past snapshots are preserved and never rewritten, so a percentile you saw two weeks ago is still verifiable. Source attribution: per-90 statistics from FBref (Sports Reference), xG/xA for the Big-5 from Understat, event data where shown from StatsBomb Open Data. Data as of the snapshot date displayed on each page.

## Change control

Any change to the formula, weights, threshold, or grouping ships in the same commit as this page's update and a dated changelog entry. A formula change without its methodology update is treated as a failed change.

---

## 9. Known limitations (internal working note)

The public page above states the user-facing limitations. The working team should also hold these:

- **Position assignment is coarse** (FBref `Pos` codes → 8 groups). System-role variance within a group is real and uncorrected.
- **No penalty adjustment** in goals/xG for MVP — noted on the public page.
- **GK metrics exclude passing/ball-playing contribution** — goalkeeper distribution (FBref Goalkeeping `Launch%`, `Att`, `Cmp%`) is deliberately out of scope for MVP because samples are small; revisit before a B2B tier.
- **Understat dependence for Tier 1 xG**: Understat publishes no express license (see `data-compliance-notes.md`). If Understat becomes unavailable, Tier 1 xG falls back to FBref Opta xG and the tier's percentile values must be recomputed under the new model with a changelog entry and a visible note ("xG model changed as of snapshot…"). The swappable-source architecture (Constitution §4) exists for exactly this event.
- **Cross-tier and cross-season comparability is not claimed** and the UI must not imply it.

---

## 10. Versioning

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-08-11 | Initial methodology: 12+4 input metrics, 8 position groups, weights per group, fractional-rank percentile normalization within season × position × tier, 900-minute qualifying threshold, public page copy. |
