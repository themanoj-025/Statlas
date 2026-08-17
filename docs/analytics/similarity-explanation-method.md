# Similarity Explanation — Method

*Phase 6 deliverable A1/A2/A3. This document specifies how the "why" behind every
"Player B is X% similar to Player A" result is computed and rendered, and why that
method was chosen over the alternatives. It is the reference for the implementation in
`app/queries/similar_players.py` and the copy templates in `web/components/SimilarPlayers.tsx`
— the numbers in the UI are real percentile values from `percentile_snapshots`, never
LLM narration.*

*Related documents: `methodology.md` (Statlas Index + percentile method) · `percentile-rules.md`
(grouping, cadence) · the Master Constitution §2/§3/§5 (design tokens, never fabricate a
number, methodology-as-code).*

---

## 1. The similarity score being explained

Similarity (Phase 2 B4) is **cosine similarity over the shared published-percentile
vector** within the same {position group, league tier} cohort:

```
similarity = Σ pᵢ·qᵢ / (‖p‖ · ‖q‖)      over the shared metric subset

where p, q are the two players' percentile vectors (0–100 each metric)
```

A metric missing for either player is excluded from that pair's score (a missing
percentile is N/A, never a zero — Constitution §3 null-vs-zero rule). A pair sharing
fewer than `min_shared_metrics` (5) metrics is not considered a comparison at all.

## 2. Chosen method: per-metric contribution decomposition (+ gap ranking for differences)

Two candidate approaches were evaluated (Phase 6 prompt, A1):

1. **Per-metric contribution decomposition** — for the metric already in use (cosine),
   compute each input metric's individual contribution to the overall similarity, then
   rank metrics by contribution.
2. **Metric-difference threshold approach** — rank metrics by absolute percentile-point
   gap; smallest gaps are "matched strengths", largest are "key differences".

**Decision: a hybrid, with the score-side derived from the decomposition (option 1) and
the difference-side derived from gaps (option 2), both computed over the same shared
vector and the same intermediate values that produced the score.**

Why:

- **Matched strengths must be derived from the same computation as the score.** The
  cosine score is the sum of per-metric contributions `cᵢ = pᵢ·qᵢ / (‖p‖·‖q‖)`. A
  "matched strength" is therefore ranked by `cᵢ` — the metric's actual contribution to
  the headline number. This is the mathematically honest answer to "why are these two
  similar?": *the metrics that moved the cosine score the most.* A separate heuristic
  that re-ranked metrics by some other rule could produce a "why" that contradicts the
  score it is supposed to explain; ranking by `cᵢ` makes that impossible by construction.
  Note that `pᵢ·qᵢ` is large exactly when *both* players rank highly on the metric, so
  contribution ranking inherently surfaces shared strengths, not shared mediocrity.
- **Contribution alone cannot state who is stronger.** `cᵢ` is symmetric and carries no
  direction. "Key differences" need direction (which player is stronger), which is a
  property of the signed percentile gap `pᵢ − qᵢ`, not of `cᵢ`. The gap ranking is a
  direct reading of the same vector, so it cannot disagree with the score either — the
  honest statement "these players diverge most on tackles" is a factual property of the
  shared vector that produced the score.
- A pure contribution approach would also report a metric where both players score at
  90/40 as a strong "match driver" (large `p·q`) even though the players are far apart on
  it — so matched strengths additionally require a small gap (see §3), which is the
  difference-side threshold applied as a *filter* on the contribution ranking.

The hard requirement holds: **every number in the explanation is a real value from the
same `percentile_snapshots` vector that produced the similarity score**, and the
score-side ranking uses the exact intermediate values of the score computation
(`_cosine_with_components` in `app/queries/similar_players.py` — the decomposition reuses
the dot product and norms already computed for ranking, never a second query or a
recompute).

## 3. Definitions and exact thresholds

Constants live in `app/queries/similar_players.py` (module-level, documented here):

| Constant | Value | Meaning |
|---|---|---|
| `MATCHED_STRENGTH_MIN_PERCENTILE` | 70.0 | both players must be at/above the 70th percentile on the metric |
| `MATCHED_STRENGTH_MAX_DIFF` | 20.0 | percentile-point gap at/under 20 |
| `KEY_DIFFERENCE_MIN_GAP` | 25.0 | absolute percentile-point gap at/over 25 |
| `MAX_EXPLAINED_ITEMS` | 3 | maximum items per list (bounded, most informative first) |

**Matched strength** — a metric where **all three** hold:

1. `pᵢ ≥ 70` and `qᵢ ≥ 70` (both players rank highly — this is what excludes the
   "both mediocre, coincidentally close" case),
2. `|pᵢ − qᵢ| ≤ 20` (genuinely close, not merely both-high-but-far-apart),
3. it ranks among the top `MAX_EXPLAINED_ITEMS` by contribution `cᵢ` (descending).

Ties in contribution break on metric id (deterministic). The example structure in the
Phase 6 prompt maps 1:1: `{metric, metric_name, player_a_percentile, player_b_percentile,
difference, contribution}`. `contribution` is included because it is the real, computed
reason the metric is listed — the UI may show it or not, but it is never fabricated.

**Key difference** — a metric where:

1. `|pᵢ − qᵢ| ≥ 25`,
2. it ranks among the top `MAX_EXPLAINED_ITEMS` by absolute gap (descending),
3. `stronger_player` = `"player_a"` when `pᵢ > qᵢ`, else `"player_b"` (direction is
   stated, never implied).

**Edge cases (documented, implemented):**

- **No meaningful differences.** If no metric has a gap ≥ 25, the key-differences list is
  empty and the UI says so plainly ("These players have very similar profiles across
  every measured metric") — it does **not** force-rank negligible gaps as if they were
  meaningful.
- **No shared standout strengths.** If no metric satisfies the matched-strength rule
  (e.g. two similar players whose alignment sits in mid-range metrics), the
  matched-strengths list is empty and the UI states the honest reading: the match is
  driven by consistent alignment across mid-range metrics, not shared top-decile
  strengths. An empty list is a finding, not a bug.
- **Boundary values are inclusive** (≥ and ≤ as defined above), so a gap of exactly 25 is
  a key difference and a gap of exactly 20 with both ≥ 70 is a matched strength. The two
  rules are mutually exclusive by construction (matched requires gap ≤ 20; key requires
  gap ≥ 25).

## 4. Missing / incomplete data (Constitution §3)

If either player lacks a published percentile for a metric (below the metric's sample
floor, insufficient minutes, or absent source data), that metric is **excluded from both
the similarity score and the explanation** — never treated as a zero or an average.

- `excluded_metrics` lists every metric of the position group's registry metric set that
  was not part of the shared comparison (i.e. not present for both players), each as
  `{metric, metric_name}` — the display name comes from the Metric Registry so the UI can
  name excluded metrics in the same terms as the Radar tool (D1).
- `excluded_reason` is the fixed, factual sentence: *"no published percentile for one or
  both players (a missing value is N/A, never a zero)"*.
- The UI renders the exclusion note visibly whenever `excluded_metrics` is non-empty, so
  the user knows the comparison is not across the full metric set. The shared-metric
  count (`shared_metrics`) is returned with every result, as it has been since Phase 2.

## 5. Consistency guarantees

- The decomposition reuses the dot product, norms, and shared-metric set computed for the
  ranking loop (`B2` of the phase prompt) — the explanation cannot diverge from the score
  because it is arithmetic on the same intermediates.
- `Σ cᵢ = similarity` (up to rounding); a unit test asserts this property on the
  hand-calculated fixture, and the verification script re-checks it on real pairs.
- Metric display names come from the Metric Registry (`metric_registry.json`), the same
  source the Radar tool and Methodology page read — D1 naming consistency is enforced by
  construction, not by convention.
