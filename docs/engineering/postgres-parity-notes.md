# Statlas — PostgreSQL Parity Verification

**Date:** 2026-08-14 · **Closeout C3** · Verifier: local Postgres 16 in Docker
(`postgres:16-alpine`, fresh volume).

## What was verified

| Check | Result |
|---|---|
| `schema.sql` applies cleanly on a fresh volume (all 11 tables, enums, indexes, the C1 `uq_percentile_snapshot_metric_tier` constraint) | ✅ |
| Full pipeline seed (`scripts/seed_dev_db.py`) against real Postgres — 1,316 players, 11,780 snapshots across 7 scrape dates, percentiles + index + publish, zero errors | ✅ |
| Query layer on Postgres: player search, slug resolution, percentiles, leaderboards (filtered + paginated), similar players, data-driven sentence, full player payload | ✅ |
| FastAPI `/api/v1` endpoints over Postgres (health, leagues, meta, coverage, positions, player search) | ✅ 200s |
| The deferred UP037 forward-ref annotations (`Mapped["Player"]`, `Mapped["Team | None"]`, …) at runtime on Postgres | ✅ no runtime discrepancy |

## Bug found and fixed (this is why C3 exists)

**Enum inserts failed on Postgres.** The ORM declared every enum column with
`native_enum=False`, so SQLAlchemy 2.0's bulk inserts (`INSERT … SELECT` with
`::VARCHAR` casts) sent character strings into PostgreSQL's real enum columns.
Postgres rejected them:

```
column "position_group" is of type position_group but expression is of type character varying
```

The SQLite test suite never caught this: SQLite has no native enums, so
`native_enum=False` and `native_enum=True` behave identically there.

**Fix (`app/models.py`):** switch the enum declarations to `native_enum=True`
(the SQLAlchemy default). On PostgreSQL this uses the real enum types that
`schema.sql`'s `CREATE TYPE` defines (same names), so the ORM and DDL agree.
On SQLite SQLAlchemy automatically falls back to VARCHAR + CHECK constraints,
so the in-memory test database still builds from the same models.

## Remaining parity notes (not blockers)

- **JSON vs JSONB:** the ORM uses SQLAlchemy `JSON` (→ Postgres `json`), while
  `schema.sql` declares `JSONB`. Both round-trip fine (verified by the seed +
  query checks); `jsonb` adds indexing/querying power the current queries don't
  need. If a future query needs JSONB operators, switch the models to
  `JSON().with_variant(JSONB(), "postgresql")`.
- **CI runs on SQLite** (in-memory), per `tests/conftest.py` and
  `ci.yml`. Postgres parity is exercised by applying `schema.sql` on fresh
  volumes (Docker) and by the verification above — not by a CI Postgres
  service. Documented deviation, unchanged.
- **Timezones:** verified the C2 UTC policy behaves identically on Postgres
  (`TIMESTAMPTZ` normalises to UTC; SQLite stores naive — the trend grouping
  key handles both, see `timezone-policy.md`).

## How to re-run

```bash
docker run -d --name statlas-pg-parity -e POSTGRES_USER=statlas \
  -e POSTGRES_PASSWORD=statlas -e POSTGRES_DB=statlas -p 54329:5432 postgres:16-alpine
docker exec -i statlas-pg-parity psql -U statlas -d statlas -v ON_ERROR_STOP=1 < app/schema.sql
DATABASE_URL="postgresql+psycopg2://statlas:statlas@127.0.0.1:54329/statlas" python scripts/seed_dev_db.py
```
