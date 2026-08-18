# Dashboard Recommendations Logic — Phase 13

## Trending players

**Definition:** Players with sustained upward percentile movement between the
two most recent published snapshot dates.

**Formula:**
1. For each player with data in both snapshots, compute the average percentile
   gain across all metrics where the player's percentile increased.
2. A player is "trending" if `avg_gain > 5.0` percentile points.
3. Exclude players the user has viewed or saved in the past 14 days.

**Scoring:** The `avg_gain` value itself serves as the ranking score — higher
gains rank higher.

**Limitations:**
- This reflects statistical trend only and does not account for underlying
  causes such as a change in role, an easier run of opposition, or a coaching
  change.
- A single-week snapshot comparison can be noisy; future versions may use a
  longer rolling window.

## Recommended players

**Definition:** Players similar to the ones the user has been viewing, ranked
by average percentile, excluding already-viewed and dismissed players.

**Algorithm:**
1. Find the user's recently viewed + saved players (last 30 days).
2. Count position groups across these players.
3. Select the top 2 most-viewed position groups.
4. Find players in those position groups the user hasn't seen, with published
   percentile data for the latest snapshot.
5. Rank by average percentile (higher = better broad quality proxy).
6. Exclude players the user has dismissed (permanent until re-surfaced by
   algorithm changes).

**Explainability:** Every recommendation includes a human-readable explanation
stating which position group the user has been viewing and how many players
in that group were viewed. Example: "Similar to the CM players you've
recently viewed (3 viewed), with an average 72.5th percentile rating."

**Limitations:**
- This is a simple position-group-based heuristic, not a full player-similarity
  model (which exists separately in Phase 6).
- Age, league tier, and playing style are not factored in v1 — only position
  group affinity based on viewing patterns.
- No ML models are involved; every recommendation is traceable to the user's
  own activity and the canonical percentile data.
