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
| Query | `limit` (1–10, default 5) |
| Response 200 | `SimilarPlayer[]` — nearest-neighbour over percentile vectors within position group (REQ-006). Each entry carries `{ player_id, name, slug, position_group, club, league, similarity, shared_metrics, index, anchor_index, explanation }` where `explanation` is `{ matched_strengths[], key_differences[], excluded_metrics[], excluded_reason, shared_metrics }` — matched strengths are the metrics that contributed most to the cosine score where both players rank ≥ 70th percentile within 20 points; key differences are the largest gaps (≥ 25 points) with `stronger_player` (`player_a` = the profile player, `player_b` = the candidate); excluded metrics are position-group metrics without a published percentile for one/both players (Phase 6, see `docs/analytics/similarity-explanation-method.md`). |

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

### EP-19 Workspace overview (Phase 7)
| | |
|---|---|
| Method/Path | `GET /api/v1/workspace` |
| Auth | session cookie (401 otherwise) |
| Response 200 | `{ plan, has_pro, limits, shortlists: [{ shortlist_id, name, description, entry_count, status_breakdown, created_at, updated_at }] }` — the user's shortlists with per-status counts; lazily creates the default "My Shortlist" for a user with none |
| Purpose | per-user scouting workspace (docs/product/scouting-pipeline.md) |

### EP-20 Create shortlist
| | |
|---|---|
| Method/Path | `POST /api/v1/workspace` |
| Auth | session cookie |
| Body | `{ name (1–128), description? (≤2000) }` |
| Response 201 | `{ shortlist_id, name }` |
| Errors | 403 free plan at the 1-shortlist cap (honest upsell detail); 400 validation |

### EP-21 Shortlist detail
| | |
|---|---|
| Method/Path | `GET /api/v1/workspace/{shortlist_id}` |
| Auth | session cookie; ownership required |
| Response 200 | `{ shortlist_id, name, description, plan, has_pro, limits, entry_count, status_breakdown, entries: [...] }` — each entry joins player summary (name, slug, position, club, league, latest published index + snapshot date), status, priority, added/updated dates, added-by note, notes (timestamped), tags, and the full status_history audit trail |
| Errors | 404 unknown OR another user's shortlist (existence never leaks) |

### EP-22 Add player to shortlist
| | |
|---|---|
| Method/Path | `POST /api/v1/workspace/{shortlist_id}/entries` |
| Auth | session cookie; ownership required |
| Body | `{ player_id, initial_note? (≤2000) }` |
| Response 201 | `{ entry_id, status }` — status defaults to `discovered`; writes the initial status_history row |
| Errors | 404 unknown player/shortlist; 409 player already in this shortlist; 403 free plan at the 10-entry cap (honest upsell) |

### EP-23 Entry status change
| | |
|---|---|
| Method/Path | `POST /api/v1/workspace/entries/{entry_id}/status` |
| Auth | session cookie; ownership required |
| Body | `{ status, reason_note? (≤1000) }` |
| Response 200 | `{ entry_id, status, history_written }` — transition validated against the pipeline rules; a history row is written on every real change |
| Errors | 400 invalid transition (specific message — e.g. signed is terminal, rejected exits only via monitoring); 404 foreign entry |

### EP-24 Entry priority / notes / tags / removal
| | |
|---|---|
| Method/Path | `POST /api/v1/workspace/entries/{entry_id}/priority` · `/notes` · `/tags` · `/tags/remove` · `/remove` |
| Auth | session cookie; ownership required |
| Bodies | priority `{ priority: low|medium|high|null }`; notes `{ note_text (1–4000) }`; tags `{ tag_text (1–64) }` (lowercased; adding an existing tag is a no-op) |
| Response | 200 / 201; `/remove` soft-deletes the entry (removed_at) — notes, tags and status_history are preserved for audit |
| Errors | 404 foreign entry; 400 validation |

### EP-25 Shortlist removal
| | |
|---|---|
| Method/Path | `POST /api/v1/workspace/{shortlist_id}/remove` |
| Auth | session cookie; ownership required |
| Response 200 | `{ ok: true }` — soft delete (deleted_at); entries removed, history preserved |
| Errors | 404 unknown/foreign |

### EP-26 Tag suggestions
| | |
|---|---|
| Method/Path | `GET /api/v1/workspace/tag-suggestions?prefix=&limit=` |
| Auth | session cookie |
| Response 200 | `{ tags: [...] }` — most-used tags from the user's OWN shortlists only (never another user's private vocabulary) |

### EP-27 Shortlist memberships
| | |
|---|---|
| Method/Path | `GET /api/v1/workspace/memberships?player_id=` |
| Auth | session cookie |
| Response 200 | `{ shortlist_ids: [...] }` — which of the user's shortlists already contain this player (drives the Add-to-Shortlist UI) |

### EP-28 Execute structured query (Phase 8)
| | |
|---|---|
| Method/Path | `POST /api/v1/search/execute` |
| Auth | none (public); signed-in users get their run logged to search_history |
| Body | `{ query_definition: { position_group?, league_tier?, age_max?, conditions: [{ metric, operator, value, value_max? }], condition_logic: "AND" }, limit? (1–100), offset?, sort_by? (index|minutes|age|name|metric_id), sort_dir?, log_history? }` |
| Response 200 | `{ query, season, snapshot_date, qualifying_minutes, note, total, limit, offset, has_more, entries, diagnostics }` — every entry carries `condition_values` (the real stored value behind each condition, with `metric_name` + `condition_type: percentile|raw`); when `total == 0`, `diagnostics.per_condition_counts` + `most_restrictive` identify the condition that filtered hardest |
| Errors | 400 grammar violation (specific message — AND-only, max 8 conditions, metric must be in the Metric Registry, value_max required for between, percentile range 0–100); 400 no season data |
| Purpose | multi-condition structured search (docs/product/query-builder-scope.md) |

### EP-29 Presets
| | |
|---|---|
| Method/Path | `GET /api/v1/search/presets` |
| Auth | none (public — presets are not user-owned) |
| Response 200 | `{ presets: [{ id, name, rationale, query_definition }] }` — Statlas-authored, curated starting points from app/config/search_presets.json |

### EP-30 Saved searches
| | |
|---|---|
| Method/Path | `GET /api/v1/search/saved` · `POST /api/v1/search/saved` |
| Auth | session cookie |
| Bodies | POST `{ name (1–128), description? (≤2000), query_definition }` |
| Response | GET 200 `{ searches: [...] }`; POST 201 saved-search payload incl. `condition_count`, `last_run_at` (null until first run) |
| Errors | 401 signed out; 403 free plan at the 5-saved-searches cap (honest upsell); 400 grammar/name validation |

### EP-31 Run / delete saved search
| | |
|---|---|
| Method/Path | `POST /api/v1/search/saved/{search_id}/run` · `DELETE /api/v1/search/saved/{search_id}` |
| Auth | session cookie; ownership required |
| Body | run: `{ limit?, offset?, sort_by?, sort_dir? }` — the STORED query_definition is re-executed (no definition in the body) |
| Response | run 200 `{ saved, results }` — results against CURRENT data (weekly refresh is explicit, never silently stale), `saved.last_run_at` updated; delete 200 `{ ok: true }` |
| Errors | 404 unknown OR another user's search (existence never leaks) |

### EP-32 Search history
| | |
|---|---|
| Method/Path | `GET /api/v1/search/history?limit=` (1–50, default 20) |
| Auth | session cookie |
| Response 200 | `{ entries: [{ history_id, query_definition, executed_at, result_count, summary }] }` — newest-first; retention cap 50 per user (enforced on insert) |

### EP-33 Re-run history entry
| | |
|---|---|
| Method/Path | `POST /api/v1/search/history/{history_id}/rerun` |
| Auth | session cookie; ownership required |
| Body | `{ limit?, offset?, sort_by?, sort_dir? }` |
| Response 200 | `{ reran: { history_id }, results }` — the new run is logged as a NEW history entry |
| Errors | 404 unknown OR another user's history entry |

## 3. Error Codes

| Code | Meaning | Handling |
|---|---|---|
| 400 | bad params (e.g., `limit > 25`) | validation detail |
| 404 | unknown slug/id | JSON `detail`; SSR pages map to 404 page (SCR-19) |
| 422 | schema validation (Pydantic) | field-level errors |
| 500 | unexpected | JSON `detail`; frontend error state with Retry (AppFlow.md §4) |

## 4. Auth Flow

**Public read-only endpoints:** none (v1 posture).

**Session endpoints (Phase 4/7/8 — workspace, billing, assistant, saved searches):** cookie-based sessions set by the API (`statlas_session`, HttpOnly, SameSite=Lax). The web app forwards the cookie to client components; ALL credentialed requests (GET, POST, DELETE) send `credentials: "include"` — without this, cross-origin GETs omit the session cookie and every signed-in read silently 401s. Ownership is enforced at the query layer: a shortlist/entry/search that is missing OR owned by another user returns **404** (never 403 — a 403 would confirm it exists). Phase 4 API keys/rate limits for the public API are documented separately (key auth is for `/api/v1/` public endpoints only).

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
