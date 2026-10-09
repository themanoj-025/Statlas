# Contributing to Statlas

Thanks for contributing. Statlas is a football analytics platform built on a
public, checkable methodology — the product's credibility depends on every
contribution holding the same data-integrity bar. Please read this page, then
the **Master Project Constitution** ([`CONSTITUTION.md`](CONSTITUTION.md)) —
every section of it is a hard requirement, not a suggestion.

> GitHub auto-links `docs/CONTRIBUTING.md` from the repository home page.

## Ground rules (the Constitution, distilled)

The full non-negotiable list is Constitution §6; these are the ones
contributors hit most often:

1. **Never fabricate a number — not even in a dev/demo environment.** A screen
   with no data shows an explicit "data pending" state, never made-up stats.
2. **Never ship placeholder/lorem-ipsum copy** to any environment users can
   see.
3. **Never claim data coverage the product doesn't have.** The coverage matrix
   (`data/coverage_matrix.json`, generated from the `data_coverage` table) is
   the arbiter; if you add or remove a source, league, or season, regenerate it
   in the same commit.
4. **Historical snapshots are append-only.** Never mutate, overwrite, or "fix"
   a snapshot in place; new scrapes insert new rows.
5. **No hardcoded secrets or API keys.** Environment variables only; document
   new ones in `.env.example`.
6. **Never silently swallow a pipeline error.** Log it and surface it; the
   anomaly gates exist so flagged values are never silently published.
7. **A metric change ships with its registry entry and methodology text** in
   the same commit (Constitution §5, §6 items 14 & 16).
8. **Scrapers are throttled by design.** Respect the delay/jitter settings in
   `config.py`; never bypass them in code that touches real hosts.
9. **No direct pushes to `main`.** Open a pull request; CI gates the merge.

## Environment setup

Prereqs: Python 3.12+ (CI runs 3.14), Node 20+ (CI runs 22).

```bash
python -m venv .venv
# Windows: .venv/Scripts/activate  |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cd web && npm ci && cd ..
```

Note: `config.py` reads `os.environ` directly (there is no dotenv loader).
`.env.example` documents every variable; nothing is required for the
fixture-demo run.

### Running the app

```bash
python scripts/seed_dev_db.py                                  # rebuild data/dev.db through the real pipeline
DATABASE_URL=sqlite+pysqlite:///./data/dev.db \
  python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000  # API on :8000
cd web && npm run dev                                          # Next.js on :3000
```

Full build plan and run guide: [`suite/ImplementationPlan.md`](suite/ImplementationPlan.md). The site labels itself
`fixture-demo` until a real scrape validates the sources
(`STATLAS_DATASET_MODE=production`) — keep that labeling honest.

## Before you open a PR — run these

```bash
# Python
python -m pytest -q            # 70 tests, in-memory SQLite, no network
ruff check .                   # enforced set F, E4/E7/E9, I (pyproject.toml)

# Web
cd web
npx tsc --noEmit
npm run build
```

These are exactly what CI runs ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)):
- **python job** — `pytest -q` and `ruff check .`
- **web job** — `npm ci`, `npx tsc --noEmit`, `npm run build`

If any check is red locally, fix it before pushing — CI blocks the merge
otherwise.

## Code conventions

- **`queries/` is the only data-access layer the UI may touch.** Frontend code
  goes through the FastAPI layer (`api/`), which wraps `queries/`. Do not query
  the database from components or server actions directly.
- **The query layer serves published rows only.** Nothing is queryable until
  anomaly checks passed and the run is marked published. Tests that seed
  directly must go through `tests/conftest.py::compute_and_publish`.
- **The Metric Registry (`config/metric_registry.json`) owns every metric**:
  id, formula, units, direction, floors, null-vs-zero display policy. Change a
  formula → update the registry, the methodology doc, and the tests in one
  commit.
- **Locked methodology numbers live in config, not code.** `config.py` loads
  `config/metric_registry.json` and `config/tiers.json`; weights and thresholds
  are never re-hardcoded elsewhere.
- **Type hints and a module docstring** on every new module (existing
  convention throughout the codebase).
- **Ruff is deliberately scoped.** The enforced set is `F, E4/E7/E9, I` (see
  `pyproject.toml`). Other rules (timezone policy, style simplifications, …)
  are tracked in [`suite/Rules.md`](suite/Rules.md) and `pyproject.toml` — if you
  resolve one, remove it from the deferred list; don't silently ignore it.
- **Web: design tokens, not inline values.** Colors, spacing, and typography
  come from `web/styles/tokens.css`; every component defines the full state set
  (default/loading/empty/error/disabled/hover/focus), tested at 375/768/1440px
  in both themes, axe-clean (Constitution §2).
- **Every parser/formula change needs a test.** Parsers are unit-tested against
  labeled fixtures in `tests/fixtures/`; new metrics need a registry entry,
  parser tests, and methodology text (Constitution §6 item 16).
- **Tests never hit the network.** Sources are exercised via fixtures or
  injected fakes; keep it that way so CI stays hermetic.

## Tests and fixtures

- Run a subset fast: `python -m pytest tests/test_percentiles.py -q`.
- Fixtures are **labeled synthetic representations** (fake ids and numbers),
  not production data — see [`suite/Testing.md`](suite/Testing.md) for what
  each one represents and how to extend them.
- When you change pipeline behavior, confirm the idempotency contract
  (`tests/test_idempotency.py`) still holds — re-running the refresh must leave
  the database identical.

## Documentation

- Code docstrings reference docs by name (e.g. `site-map.md`); keep those
  references valid when you move or rename docs.
- Update the docs index (`docs/README.md`) when you add or move a doc.
- Behavior changes ship with their docs in the same commit: coverage matrix,
  changelog (`web/app/changelog/`), and the relevant `docs/` area.

## Commits and PRs

- Commit messages say what **and why** (Constitution §4). No "update", "fix",
  or "wip" messages.
- One logical change per PR, with tests. PRs land after CI is green.
- If your change touches a documented "known deviation" (e.g. the tier
  completeness gate noted in `orchestration/weekly_refresh.py`), keep the
  documentation in sync with what the code actually does.

## License and known constraints

- **AGPL-3.0** ([`LICENSE`](../LICENSE)) — by opening a PR you agree your
  contribution is licensed under AGPL-3.0.
- **Docker**: `docker compose up -d --build --wait` runs the full stack
  (Postgres + API + web); `docker compose --profile seed run --rm seed` loads
  the labeled fixture-demo data. Full commands in the root `README.md`.
- The dataset is fixture-demo until a real scrape validates the sources
  (`docs/analytics/data-compliance-notes.md` tracks that validation step).
