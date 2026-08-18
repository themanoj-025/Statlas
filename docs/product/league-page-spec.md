# League Page Spec — Phase 11

## URL structure

| Route | Content | SSR |
|---|---|---|
| `/leagues` | League index — all leagues grouped by tier | Yes |
| `/leagues/{slug}` | League hub — overview, category leaders, emerging, teams | Yes |
| `/leagues/{slug}/stats` | Per-90 stats table (existing Phase 2) | Yes |
| `/leagues/{slug}/index` | Statlas Index leaderboard (existing Phase 2) | Yes |
| `/leagues/{slug}/positions/{group}` | Position leaderboard (existing Phase 2) | Yes |

Canonical URL rules: each route carries `alternates.canonical` pointing to itself.
The hub (`/leagues/{slug}`) is the primary landing page; sub-pages are
purpose-built deep-link targets.

## Hub page sections

1. **League header** — name, country, tier badge, season, team count, logo
   (honest placeholder if unavailable).
2. **Data freshness note** — last snapshot date, FBref/Understat/StatsBomb
   coverage status (per Constitution §3 transparency).
3. **Category leaderboards** — four curated 5-row leaderboards:
   - Top scorers (`si_gls_p90`, all positions)
   - Best creators (`si_kp_p90`, AM/W/CM/ST)
   - Best progressors (`si_pprb_p90`, all positions)
   - Best defenders (`si_tkl_p90`, DM/CB/FB)
   Each links to the full leaderboard filtered to that metric/position.
4. **Emerging players** — scored by the emerging-player formula
   (docs/analytics/emerging-player-methodology.md), max 8 players,
   with score, age, position, team, trend direction.
5. **Teams grid** — links to existing Phase 2 team profile pages.
6. **Standings** — only shown when match-result data is available. For MVP
   this section is absent; the honest note is: "Standings data is not
   currently available — Statlas focuses on player-level per-90 statistics."

## Honesty rules for missing data

- No standings section → explicit note, never a silently empty table.
- No emerging players for a league → "No players meet the emerging-player
  threshold in this league yet" (not "no data").
- Partial FBref coverage → coverage note reflects actual source status.

## Category leaderboard metric/position mappings

| Category | Metric | Position filter | Limit |
|---|---|---|---|
| Top scorers | `si_gls_p90` | None (all) | 5 |
| Best creators | `si_kp_p90` | AM, W, CM, ST | 5 |
| Best progressors | `si_pprb_p90` | None (all) | 5 |
| Best defenders | `si_tkl_p90` | DM, CB, FB | 5 |
