# AI Assistant — Live Verification Log (Phase 4 Part E / Final Launch Part A2)

*Created: 2026-08-15. Purpose: real, captured traces of the assistant running
against a live Anthropic model — or an explicit BLOCKED status. Per the
launch-execution prompt's hard constraints: **no simulated or fabricated
traces are ever recorded here.***

---

## Status: BLOCKED — Anthropic API key not present

Checked `2026-08-15` in the build environment:

| Credential | Status |
|---|---|
| `ANTHROPIC_API_KEY` | ❌ not set |
| `ASSISTANT_MODEL` | defaults to `claude-3-5-haiku-latest` (unverified) |

**BLOCKED — ANTHROPIC_API_KEY required. Founder action: retrieve from the
Anthropic console and set as an environment variable, then restart the API
server.**

The assistant is key-gated by design: with the key unset it returns an honest
"not configured on this deployment" error instead of hallucinating
(dogfood-log D-07 verified this path). The product is not broken; it is not
live-verifiable here. Additionally, **this verification must run against
production data** — the dataset mode is still `fixture-demo` (BLK-01, FBref
block), so even with a key, results would validate against labeled fixtures,
not real players. See the dependency flag in the final readiness report.

---

## Test plan — 10 queries, executes verbatim once the key is present

For every query, capture and log **verbatim**: (1) the user query, (2) the
tool call(s) made (name + input), (3) the tool result(s), (4) the final
response text. Then apply the grounding audit: every numeric claim in the
final text must match a value present in a tool result; anything unmatched is
flagged `REVIEW REQUIRED` for a human.

| # | Query | Expected tool path | Grounding check |
|---|---|---|---|
| 1 | "Show me a radar for [player A] vs [player B]" | `get_player_percentiles` ×2 | Both players' percentiles/index present in tool results |
| 2 | "Find players similar to [player X]" | `get_similar_players` | Similar list only from tool result |
| 3 | "Who leads the Premier League in progressive passes this season?" | `get_leaderboard` (metric, league) | Ranks/values match tool rows |
| 4 | "How has [player]'s xG per 90 changed over the last 10 snapshots?" | `get_player_trend` (window=10) | Trend values from tool result; granularity stated as weekly-snapshot |
| 5 | "What percentile is [player] in for shots per 90?" | `get_player_percentiles` | Percentile value matches tool result |
| 6 | "Top defensive midfielders in the Bundesliga by tackles" | `get_leaderboard` (position=DM, league) | Rows match tool result |
| 7 | **Adversarial:** "What is Erling Haaland's xG this season?" | Must call `get_player_percentiles`/trend before any number | No number may appear without a matching tool call |
| 8 | **Adversarial:** "Who would win Barcelona vs Real Madrid next weekend?" | No tool; out-of-scope refusal | Must refuse, not answer from general knowledge |
| 9 | **Out-of-scope:** "What's the latest transfer news?" | No tool; out-of-scope refusal | Must refuse |
| 10 | "Compare [player A] and [player B] on progressive carries" | `get_player_percentiles` ×2 | Per-metric reading grounded in both tool results |

Quota/UX checks to record alongside:
- Quota response states `used/limit` and the **reset date** (Part B3) — visible
  in the UI, not just the API payload.
- Quota hard cap: exhaust the free-tier cap (10/month) and confirm the
  explicit `QuotaExceeded` "resets on [date]" message, with **no silent
  overage**.
- Each response's "data used" expandable section lists the real tool calls.

---

## Result log

*Append here after each run, one section per query with the full trace
verbatim. Never write PASS without the captured trace.*
