# API.md — Statlas API Reference

| Field | Value |
|---|---|
| Version | v0.1 |
| Last Updated | 2026-08-14 |
| Owner | Staff Engineer |
| Status | In Review |

## 1. Overview

- **Base URL:** `http://127.0.0.1:8000` (dev) / `https://api.statlas.com` (prod, planned). Browser config: `NEXT_PUBLIC_STATLAS_API_URL`.
- **Auth:** none in v1 — all endpoints public read-only. Phase 4 introduces auth + rate limits (REQ-023).
- **Versioning:** path-prefixed `/api/v1/`. Breaking changes bump the prefix; additive changes do not.
- **Format:** JSON. Errors: `{"detail": "<message>"}` with appropriate HTTP status.
- **Implementation:** `app/api/main.py` (FastAPI) — thin handlers delegating to `app/queries/*` via `_with_session`.

## 2. Endpoint Reference

### EP-01 Health
| | |
|---|---|
| Method/Path | `GET /api/v1/health` |
| Auth | none |
| Response 200 | `{"status": "ok"}` |
| Errors | 500 if app can't boot |

### EP-02 Meta
| | |
|---|---|
| Method/Path | `GET /api/v1/meta` |
| Auth | none |
| Response 200 | `{ "dataset_mode": "fixture-demo", "dataset_note": "...", "schema_version": 1, "qualifying_minutes": 900 }` |
| Purpose | Powers DatasetBanner honesty label (REQ-016) |

### EP-03 Leagues
| | |
|---|---|
| Method/Path | `GET /api/v1/leagues` |
| Query | — |
| Response 200 | `[{ "id", "name", "country", "tier", "slug", "position_groups": [...] }]` |

### EP-04 League detail
| | |
|---|---|
| Method/Path | `GET /api/v1/leagues/{league_slug}` |
| Query | `season?` |
| Response 200 | league payload + teams |
| Errors | 404 unknown slug |

### EP-05 League stats
| | |
|---|---|
| Method/Path | `GET /api/v1/leagues/{league_slug}/stats` |
| Query | `metric?`, `season?`, `limit?` |
| Response 200 | per-90 raw-stats rows (SCR-06) |

### EP-06 Leaderboard
| | |
|---|---|
| Method/Path | `GET /api/v1/leaderboard` |
| Query | `league_id`, `position_group`, `metric`, `season`, `minutes_min`, `sort_by`, `order`, `page`, `page_size` (≤ 100) |
| Response 200 | `{ "items": [...], "total", "page", "page_size" }` — sortable columns incl. percentile + index |
| Purpose | SCR-06/07/08 (REQ-013) |

### EP-07 Player search
| | |
|---|---|
| Method/Path | `GET /api/v1/players/search` |
| Query | `q` (required), `limit` (≤ 25) |
| Response 200 | `[{ "id", "name", "slug", "team", "league", "position_group" }]` — alias-aware (US-001) |

### EP-08 Player by slug
| | |
|---|---|
| Method/Path | `GET /api/v1/players/by-slug/{slug}` |
| Query | `season?` |
| Response 200 | full profile payload: identity (name, team, position, nationality, age-from-DOB), percentiles (latest snapshot), key raw per-90 stats, recency (scrape_date), data sentence inputs, index score or pending-qualification |
| Errors | 404 unknown slug |

### EP-09 Similar players
| | |
|---|---|
| Method/Path | `GET /api/v1/players/{player_id}/similar` |
| Response 200 | `[{ "player", "score", "basis" }]` — nearest-neighbor over percentile vectors within position group (REQ-006) |

### EP-10 Player trend
| | |
|---|---|
| Method/Path | `GET /api/v1/players/{player_id}/trend` |
| Query | `metric?`, `season?` |
| Response 200 | time series over stat_snapshots (per-90, gap breaks, transfer annotations) (REQ-018) |

### EP-11 Event coverage
| | |
|---|---|
| Method/Path | `GET /api/v1/players/{player_id}/events` |
| Response 200 | which competitions/seasons have event data for this player (coverage gate, REQ-012) |

### EP-12 Event matches
| | |
|---|---|
| Method/Path | `GET /api/v1/players/{player_id}/events/matches` |
| Query | `competition?`, `season?` |
| Response 200 | list of matches with event availability |

### EP-13 Event shots
| | |
|---|---|
| Method/Path | `GET /api/v1/players/{player_id}/events/shots` |
| Response 200 | shots with x/y coords + outcome (ShotMap) |

### EP-14 Event passes
| | |
|---|---|
| Method/Path | `GET /api/v1/players/{player_id}/events/passes` |
| Response 200 | passes with x/y coords (PassMap) |

### EP-15 Team profile
| | |
|---|---|
| Method/Path | `GET /api/v1/clubs/{league_slug}/{team_slug}` |
| Query | `season?` |
| Response 200 | identity + roster + squad-average radar payload (REQ-010) |
| Errors | 404 unknown league/team |

### EP-16 Coverage
| | |
|---|---|
| Method/Path | `GET /api/v1/coverage` |
| Response 200 | per (league, source) coverage rows from `data_coverage` + matrix (SCR-12) |

### EP-17 Positions
| | |
|---|---|
| Method/Path | `GET /api/v1/positions` |
| Response 200 | position-group taxonomy + metric sets |

### EP-18 Methodology
| | |
|---|---|
| Method/Path | `GET /api/v1/methodology` |
| Response 200 | index formula, weights, normalization, threshold, limitations (REQ-015; also statically SSR'd on /methodology) |

## 3. Error Codes

| Code | Meaning | Handling |
|---|---|---|
| 400 | bad params (e.g., `limit > 25`) | validation detail |
| 404 | unknown slug/id | JSON `detail`; SSR pages map to 404 page (SCR-19) |
| 422 | schema validation (Pydantic) | field-level errors |
| 500 | unexpected | JSON `detail`; frontend error state with Retry (AppFlow.md §4) |

## 4. Auth Flow

None in v1 (N/A because all data is public; Phase 4 adds API keys/rate limits — see ImplementationPlan TASK-4.4). When added, this section will document the key/refresh flow with a Mermaid sequence diagram.

## 5. Example Request/Response

```
GET /api/v1/players/search?q=salah&limit=3
200
[ { "id": 42, "name": "Mohamed Salah", "slug": "mohamed-salah",
    "team": "Liverpool", "league": "Premier League", "position_group": "W" } ]
```

```
GET /api/v1/leaderboard?league_id=1&position_group=CM&metric=si_prgp_p90&sort_by=index_score&order=desc&page=1&page_size=20
200
{ "items": [ { "player_id", "name", "slug", "team", "index_score": 88.3,
               "metric_value": 6.1, "percentile": 96.2 } ], "total": 214, "page": 1, "page_size": 20 }
```

## 6. Rate Limits & Caching

- v1: none (public read-only). Underlying scrapers rate-limit *upstream* (TechSpec §5), not the API.
- Caching: none server-side yet; browser caching for static SSR pages. Phase 4: API keys + per-key quotas (REQ-023).

## 7. Versioning Policy

Path prefix `v1`; breaking changes → `v2` with deprecation notice ≥ 1 release cycle; additive fields are non-breaking. Any endpoint change updates this file in the same PR (Rules.md §7).

## 8. Related Documents

| Document | Relationship |
|---|---|
| [PRD.md](PRD.md) | REQs served by endpoints (EP↔REQ noted above) |
| [TechSpec.md](TechSpec.md) | Query layer behind every endpoint |
| [AppFlow.md](AppFlow.md) | Screens calling each EP |
| [Design.md](Design.md) | N/A |
| [Schema.md](Schema.md) | Tables each EP reads |
| [ImplementationPlan.md](ImplementationPlan.md) | Endpoints built per task |
| [Tracker.md](Tracker.md) | Endpoint status |
| [Rules.md](Rules.md) | RULE: endpoint docs sync |
| [SecurityAndCompliance.md](SecurityAndCompliance.md) | No-auth posture + Phase 4 plan |
| [Testing.md](Testing.md) | API contract tests (test_api.py) |
| [Deployment.md](Deployment.md) | Base URLs per env |
| [Glossary.md](Glossary.md) | Terms in payloads |
| [RiskRegister.md](RiskRegister.md) | N/A |
