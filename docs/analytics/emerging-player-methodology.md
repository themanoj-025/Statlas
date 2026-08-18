# Emerging Player Detection — Methodology

*Phase 11 · linked from /methodology*

## What this signal measures

The emerging-player score identifies players whose statistical output is on a
sustained upward trajectory relative to their positional peers. It answers one
scouting question: **who is getting notably better, recently, in a way that
is statistically meaningful rather than a single-snapshot fluke?**

This signal reflects statistical trend only. It does not account for
underlying causes such as a change in tactical role, an easier run of
opposition, a coaching change, or a return from injury. A flagged player
is not necessarily about to break through — they are a player worth watching
more closely.

## Formula

The emerging-player score is a weighted composite of three factors:

```
score = trend_magnitude × trend_consistency × age_weight × sample_weight
```

All factors are 0.0–1.0, so the final score is also 0.0–1.0. Players
scoring above **0.50** are displayed on the league page; the threshold is
configurable per deployment.

### 1. Trend magnitude (weight: 0.45)

The average percentile-point improvement across the player's tracked metrics
over the most recent **5 snapshots** (the default trend window per
`trend_queries.py`).

```
trend_magnitude = mean(max(pct_latest - pct_oldest, 0)) / 100
```

Only positive changes contribute — a player declining on some metrics but
rising on others gets credit for the improvements, not a penalty for the
declines. This is deliberate: the signal is "emerging," not "consistently
excellent."

### 2. Trend consistency (weight: 0.30)

What fraction of the tracked metrics showed a **sustained** upward trend
(positive slope across at least 3 of the 5 snapshots, not just a
start-to-end jump that could be a single-week spike).

```
trend_consistency = count(metrics_with_monotonic_upward / total_metrics)
```

A player who improves on 8 of 10 metrics scores 0.80; a player who
improves on 2 of 10 scores 0.20 regardless of how large those 2 jumps
were. Consistency across metrics is the stronger signal of genuine
development.

### 3. Age weight (weight: 0.15)

Younger players score higher on this factor, using a sigmoid curve centred
at age 24 (the typical peak-development window boundary):

```
age_weight = 1 / (1 + exp((age - 24) / 3))
```

This produces:
- Age 20 → 0.77
- Age 23 → 0.57
- Age 24 → 0.50
- Age 26 → 0.38
- Age 30 → 0.17

Age is a **weighting factor, not a hard cutoff**. A 28-year-old late bloomer
with strong trend signals still surfaces — they just score lower on this
dimension than an identical 21-year-old. The age is computed from
`date_of_birth` on the player record; players without a DOB get age_weight
= 0.50 (neutral).

### 4. Sample weight (weight: 0.10)

Confidence based on minutes played relative to the qualification threshold:

```
sample_weight = min(minutes_played / qualifying_minutes, 1.0)
```

Where `qualifying_minutes` is the same threshold used for the Statlas Index
(900 minutes). A player with 2,000+ minutes scores 1.0; a player with
exactly 900 scores 1.0; a player with 500 minutes is not eligible (below
threshold → excluded entirely, not downweighted).

## Eligibility

- Player must meet the standard minutes qualification threshold (900 minutes
  in the current season) — the same floor the Statlas Index uses. This
  excludes small-sample flukes.
- Player must have at least **3 snapshots** with published percentile data
  for at least **3 metrics** — fewer than this and the trend is not
  meaningful.
- Only players in the queried league are considered.

## Metrics tracked

For each player, the formula tracks percentile trends across the same
registry metrics used for the Statlas Index. Metrics missing for a player
(excluded due to insufficient data) are simply omitted from the trend
calculation — never treated as zero (Constitution §3 null-vs-zero policy).

## Limitations

- Snapshot granularity (weekly scrape intervals, not per-match) means
  short-term form spikes within a week are invisible.
- A player who transfers mid-season may show a trend discontinuity from the
  team/league change; this is not filtered out because it is real data.
- The formula does not distinguish between a player improving because they
  developed vs. one who moved to a weaker league — both look like upward
  trends in percentile terms.
- Age data is approximate (year of birth only, set to January 1).
