# Statlas — Timezone Policy

**Decision (closeout C2, 2026-08-14): UTC everywhere in the backend; explicit
conversion only at display time.**

## The policy

1. **Storage** — every `TIMESTAMPTZ` column (scrape_date, computed_date,
   kickoff_utc, flagged_at, created_at, …) is written in UTC and queried in
   UTC. PostgreSQL `TIMESTAMPTZ` normalises to UTC internally; the ORM models
   declare `DateTime(timezone=True)` to match.
2. **Computation** — all `datetime.now()` calls in pipeline code use
   `datetime.now(timezone.utc)`. A naive "today" is never used as a source of
   truth (the date boundary must be the UTC one, not the server's local one).
3. **Date-only columns** — `players.date_of_birth` is a Postgres `DATE`
   (no time-of-day, no zone). Code that builds it constructs a `date` object
   directly, never a timezone-naive `datetime` (which DTZ001 would flag).
4. **Display** — the frontend renders dates in the user's local zone **only
   at the moment of rendering** (e.g. `toLocaleDateString`), and the API
   always returns ISO-8601 UTC timestamps. No backend code converts to a local
   zone for storage or comparison.
5. **Grouping keys** — dates used as dictionary keys (trend `by_date`) are
   normalised to UTC and then the tzinfo is dropped **explicitly and
   intentionally** for the key comparison; the underlying values keep their
   zone.

## Enforcement

- `DTZ` rules are in the enforced ruff set in `pyproject.toml`
  (`select = [..., "DTZ"]`), so any new naive `datetime()`/`date.today()`
  fails CI before merge.
- Exception: none in backend code. Test files follow the same rule so the
  suite models production behaviour.

## Rationale

- A weekly-refresh pipeline runs on a server whose local timezone may change
  (deploy region, daylight saving). Using UTC for the scrape-date versioning
  key makes snapshot boundaries deterministic and idempotency checks stable.
- `date.today()` in the API-Football budget file made the "daily" reset
  depend on the host's zone — two servers in different zones would disagree
  about when a day resets. UTC fixes that.
