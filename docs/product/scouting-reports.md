# Scouting Reports — design and rules (Phase 9)

A scouting report is a persisted, shareable artifact: it outlives the session
that generated it and carries more implied authority than a chart on a page.
The core discipline of this phase is therefore **architectural grounding**: the
report generator must be *incapable* of including a claim that doesn't trace to
a real tool-call result, not merely instructed not to via a system prompt.

This document fixes the design decisions. It mirrors the transparency standard
of the similarity-explanation and query-builder scope docs: a reader should be
able to reconstruct exactly how every number in a report got there.

---

## 1. Report structure (per-claim traceability)

Every report is a single JSON document stored verbatim in `reports.report_json`.
The structure follows the roadmap's section list, with one load-bearing rule:
**every leaf-level factual claim carries a `source_calls` reference** (or lives
in `workspace_context`, which is the user's own Phase 7 data and is labeled as
such, never blended into AI-narrated sections).

```jsonc
{
  "report_id": 12,
  "player_id": 731,
  "generated_at": "2026-08-17T09:30:00Z",
  "generated_by_user_id": 3,
  "data_snapshot_date": "2026-08-12",
  "source": "player_profile" | "shortlist_entry",
  "shortlist_entry_id": null | 45,
  "sections": {
    "overview": { "text": "…", "source_calls": ["percentiles", "raw_stats"] },
    "statistical_profile": { "metrics": [ {metric, value, percentile, pctile_label} ], "source_calls": ["percentiles", "raw_stats"] },
    "role_and_position": { "text": "…", "source_calls": ["profile", "raw_stats"] },
    "strengths": [ { "point": "…", "supporting_metric": "si_prgp_p90", "value": 1.94, "percentile": 91, "source_calls": ["percentiles"] } ],
    "weaknesses": [ { … } ],
    "comparable_players": [ { "player_id": 512, "name": "…", "similarity": 0.91, "explanation": { …Phase 6 verbatim… } } ],
    "development_trajectory": { "trend_summary": "…", "metric": "si_index", "source_calls": ["trend"] },
    "risk_factors": [ { "point": "…", "basis": "real signal name" } ],
    "recommendation": { "text": "…", "confidence_level": "high|medium|low", "confidence_rationale": "…" },
    "workspace_context": { "shortlist_status": "monitoring", "priority": "high", "tags": ["left-footed"], "recent_notes": [ { "note_text": "…", "created_at": "…" } ], "label": "user's own scouting notes" }
  },
  "evidence_appendix": [ { "claim": "…", "source_call": "percentiles", "raw_result": {…} } ],
  "confidence": { "level": "high", "rationale": "…", "factors": { "sample_size": …, "data_completeness": …, "recency_days": … } },
  "verification": { "status": "passed" | "needs_review", "log": [ … ] }
}
```

`source_calls` values are keys into the deterministic context object (§2) that
was assembled before generation. A claim that names no source is a verification
failure.

## 2. Generation pipeline (B1) — never one freeform LLM call

```
1. gather_report_context(db, player_id, entry_id?)   # deterministic, all real data
2. narrate(context)                                   # LLM or injected narrator; may only
                                                      #   reorganize/narrate context values
3. verify_report(report, context)                     # HARD gate (below)
4. on failure: one auto-correction retry with the mismatch list fed back
               → still failing ⇒ status = "needs_review" (never silently shipped)
```

**Step 1** uses the exact query functions the rest of the product uses — no
parallel data access (the Phase 4 assistant's rule, reused verbatim):

- `player_queries.get_player_profile` / `get_player_percentiles` / `get_player_raw_stats`
- `similar_players.get_similar_players` (Phase 6 — comparables come from here
  **verbatim**, including the `explanation` object; the LLM never computes or
  narrates similarity independently, B3)
- `trend_queries.get_player_trend` (index metric, window 5)
- `workspace_queries.get_shortlist_detail` + entry lookup (B4, only when a
  `shortlist_entry_id` is supplied)

The context object also carries a **verification corpus**: every number that
appears anywhere in the context (percentiles, raw values, index, minutes,
matches, similarity scores, ages, snapshot dates, season label) plus the set of
metric display names. This corpus is what step 3 checks against.

**Step 2** is a single LLM narration call (the "section by section" work is
the prompt structure, not N separate API calls): the model receives the full
structured context and is instructed to produce the report JSON, explicitly
forbidden from introducing any statistic not present in the context. Because
the corpus is exhaustive, the model has nothing to gain by inventing numbers —
the verification gate would catch them anyway.

**Step 3** (`verify_report`) is code, not a system prompt:

- Every number appearing in any narrative text field is extracted and checked
  against the corpus with a tight tolerance (values are stored both raw and
  rounded to 1 dp and to an integer, so "88th" matches a true 87.6–88.4; a
  fabricated "94th" does not).
- Every metric display name mentioned in prose must exist in the context's
  metric set.
- `comparable_players` must be a subset of the actual Phase 6 results (ids and
  similarity values from context, never invented comparables).
- `confidence_level` must equal the deterministic value from §3 — the LLM may
  narrate confidence in prose but may not change the level.

**Step 4**: on failure the pipeline retries once with the mismatch list fed
back for correction; if it fails again the report is stored with
`verification.status = "needs_review"` and the UI shows an explicit "held for
review" state (§6). We implement **retry-with-correction then honest hold**
rather than endless silent retries or an unbounded loop — the hard gate always
gets a vote.

Every generation logs `verification.log` (pass/fail, unverified claims) so
grounding quality is monitorable; these outcomes are reviewed in the same
accuracy-monitoring process as Phase 4's chat logs.

## 3. Confidence level (A2) — computed, never vibes

`compute_report_confidence(...)` is a pure deterministic function of three
real, checkable factors:

| Factor | Signal | Scoring |
|---|---|---|
| `sample_size` | minutes played ÷ qualifying threshold (900) | ≥3.0 full-season (1.0); ≥1.5 solid (0.8); ≥1.0 qualifying (0.6); <1.0 below-threshold (0.3) |
| `data_completeness` | fraction of the player's position-group metric set present in the percentile snapshot | ≥0.9 complete (1.0); ≥0.6 partial (0.7); <0.6 sparse (0.4) |
| `recency_days` | days between `data_snapshot_date` and generation | ≤7 current (1.0); ≤30 recent (0.8); ≤60 (0.6); >60 stale (0.4) |

Composite = weighted mean (sample 0.5, completeness 0.3, recency 0.2).
`high` ≥ 0.85, `medium` ≥ 0.60, else `low`. The `confidence_rationale` text
states the actual factors ("Based on 2,100 minutes played — well above the
900-minute qualification threshold — and complete data across all relevant
metrics"), and the JSON `factors` object carries the raw inputs so the UI can
show the reasoning.

## 4. Risk factors (A3) — derived from real signals only

Risk factors are generated by a deterministic function over real data, never
narrated from general knowledge. Valid signals:

- **Limited sample**: minutes below 2× the qualification threshold.
- **Single-season assessment**: only one distinct season in the player's
  `stat_snapshots` history.
- **No event-level data**: zero `match_events` rows for the player (no tactical
  assessment possible from shot/pass maps).
- **Age vs. position development curve**: age outside the documented typical
  peak range for the position group (GK/CB 26–33; FB/DM/CM 24–30; AM/W 22–28;
  ST 23–29) — stated as "below/above the typical peak age range for {position}".

The generator explicitly **forbids** inventing risk factors about things Statlas
has no data on — injury history, personality/attitude, off-field conduct. Every
report's risk section instead closes with the plain statement: "Not assessed:
injury history, attitude and off-field factors are outside what Statlas data
can support." This prevents silent omission from implying completeness.

## 5. Ownership, quotas, tier gating (D4/D5)

- **Ownership**: reports are per-user data. Every read/write verifies
  `user_id`; foreign or missing report ids raise `ReportNotFound` → HTTP 404
  (the Phase 7/8 rule: never a 403 that leaks existence).
- **Quota**: reports consume a **separate `report_quotas` allowance**, not the
  Phase 4 chat quota — sharing one pool would cause confusing "why did my chat
  quota drop" experiences. Same hard-cap, same calendar-month reset, same
  explicit `reset` date in responses. The allowance lives in pricing.json
  (`report_quotas_per_period`): Free 0, Pro 10, API-Business 100.
- **Tier gate**: Free users receive an honest, specific upsell ("Reports are a
  Pro feature — …") identical in tone to the Phase 7/8 caps. Generation is
  gated on the subscription (via `auth.has_pro_access`), not on the quota row
  alone.

## 6. UI honesty states (D2)

- Generation progress shows the real pipeline stages ("Gathering player data…
  Analyzing comparables… Verifying claims…") — the endpoint runs the stages in
  that order, so the messaging is truthful, not a fake spinner narrative.
- A `needs_review` report is presented as "This report flagged a claim we
  couldn't verify against our data and has been held for review" — never
  hidden, never presented as a normal report.
- Every stored report is labeled with its `data_snapshot_date` ("reflects data
  as of …") and offers "regenerate with current data" — stored reports never
  auto-update.
- Export files carry the same snapshot-date footer ("Data as of … — not
  real-time").

## 7. Exports (C) — one verified object, three views

JSON, PDF and CSV are all derived from the single verified report object —
never independently generated.

- **JSON**: the report document verbatim (canonical, most auditable).
- **PDF**: generated with ReportLab, styled with the product design tokens
  (type scale, brand colour, grayscale-safe semantic colours), including the
  player header, all narrative sections, a vector mini radar chart (ReportLab
  graphics, mirroring the percentile radar), the evidence appendix, and the
  snapshot-date footer. Tagged structure where ReportLab supports it.
- **CSV**: tabular only — statistical profile rows and comparable players
  (id/name/similarity + the explanation's matched strengths). The export UI
  states plainly that narrative sections are not included in CSV.
