# Dashboard Scope — Phase 13

## Layout decision

The v1 dashboard uses a **fixed widget layout** (no user customization).

Rationale:
- Custom widget reordering adds complexity (drag-and-drop, persistence, conflict
  resolution) with marginal value for a first launch where most users have fewer
  than 4 widgets with data.
- The fixed layout is easier to test, faster to load, and simpler to make
  accessible (no drag-and-drop keyboard equivalents needed).
- Widget customization can be added as a follow-up if user feedback requests it;
  the `dashboard_state.widget_config` column is already in the schema to support
  it without migration.

## Widget order (fixed)

1. **Workspace shortcuts** — top row, 4 cards (shortlists, saved searches, reports, watchlist)
2. **Recently viewed** — left/main column
3. **Trending this week** — left/main column, below recently viewed
4. **Saved players** — right side column
5. **Recommended for you** — right side column, below saved

## Data freshness

- Workspace counts: real-time (fast count queries)
- Recently viewed: real-time (indexed query on activity_log)
- Trending: computed during weekly refresh (Phase 1 orchestration)
- Recommended: computed on-demand from current percentiles

## Future enhancements (documented, not built)

- Widget reordering/visibility toggle via `dashboard_state.widget_config`
- Dismiss-recommendation decay (30-day expiry) — currently permanent until
  re-surfaced by algorithm changes
- "View all" links expanding each section into a full leaderboard view
