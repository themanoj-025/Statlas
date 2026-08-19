# Phase 17 — Tactical Intelligence Data Coverage

## Event-Level Data Dependency

Phase 17 (passing networks, pressure/zone maps, formation analysis) depends entirely
on **event-level match data with exact x/y coordinates** for every action. This data
is only available from StatsBomb Open Data for specific released competitions.

**StatsBomb Open Data coverage** (as of August 2026):

| Competition | Seasons Available | Event Data |
|---|---|---|
| UEFA Champions League | 2017/18 – 2024/25 | Full event-level with coordinates |
| FA Cup | 2017/18 – 2024/25 | Full event-level with coordinates |
| La Liga | 2020/21 | Full event-level with coordinates |
| Premier League | 2017/18, 2019/20 | Full event-level with coordinates |
| FIFA World Cup | 2018, 2022 | Full event-level with coordinates |
| UEFA Euro | 2020/21 | Full event-level with coordinates |
| FA Women's Super League | 2018/19 – 2020/21 | Full event-level with coordinates |
| UEFA Women's Champions League | 2018/19 – 2020/21 | Full event-level with coordinates |

## Coverage Gating

Before any Phase 17 feature renders:

1. **Check `data_coverage`** table for `source='statsbomb'` matching the competition/season
2. **Check `match_events`** table for events with the specific `match_id`
3. If neither check passes: **show explicit message**: "Event-level tactical data not available for this match — Statlas currently has passing networks for [specific competitions]."

**Never** show empty/broken tactical views. **Never** imply universal coverage.

## Data Limitations

- StatsBomb Open Data is **public GitHub data** — not live/current-season data for most leagues
- Event coordinates use StatsBomb's 120×80 coordinate system
- Player positions in event data are **not** explicit — must be inferred from event sequences
- Formation data is often **not included** in StatsBomb events — must be detected from positioning

## Coverage Check Function

The function `_coverage_confirms(db, competition_id, season)` from
`app/queries/event_queries.py` is the single source of truth for whether
event-level data exists for a given competition/season combination.

All tactical analysis endpoints must call this function before processing.
