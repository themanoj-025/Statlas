# Statlas — Post-Launch Iteration Cadence

*Created: 2026-08-14 (Phase 5 — Part C4). Owner: founder (solo).*

The soft launch is a window; this document defines what happens **after** it —
an ongoing practice, not an abrupt stop. It also covers Part C3 (data-refresh
transparency), because the cadence and the freshness guarantee are the same
discipline: users should never have to guess how current the data is, and
feedback should never sit without an owner.

---

## C3 — Data-refresh transparency

### Visible freshness (implemented)

Every stat surface carries its snapshot date, rendered by `RecencyLine`
("Data as of YYYY-MM-DD · computed on … · source: …"):

| Surface | Where |
|---|---|
| Player profiles | header, below the data-driven sentence |
| Team profiles | header |
| League leaderboards | above the table |
| Position-group pages | above the table |
| Radar / trend charts | chart recency line |
| OG images (shared links) | "Data as of …" baked into the image |

Coverage statements and the dataset mode (`fixture-demo` banner today,
`production` after the validated flip) are site-wide and driven by the coverage
matrix + `/api/v1/meta` — never hand-written claims.

### Operational refresh entries (decision)

Each successful weekly refresh updates the **changelog** with a dated
operational entry (category: "data update") listing leagues scraped, records
ingested, anomalies found/blocked, and events linked — taken from the
`RefreshReport` the job already returns. This is a manual-but-cheap step
appended to the refresh runbook rather than an automated commit, because
changelog entries are read by humans and the pipeline's alerting already pages
on failure. The alternative (a machine-generated status page) is noted as a
future option in `docs/engineering/infra-plan.md` if refresh volume grows.

**Refresh runbook addition (per weekly run, after `run_weekly_refresh`):**
1. Read the run's `RefreshReport` (leagues scraped, rows ingested, anomalies,
   blocked players, events linked).
2. Add one dated changelog entry under "data update" with the report numbers.
3. Fix/queue anything from `report.errors` per the alerting rules — a silent
   failure is a failure.

**StatsBomb sync compliance checks (per run that syncs StatsBomb):**
4. **§2.2 registration note (one-time + verify):** the StatsBomb Public Data
   User Agreement asks users to register (name + email) at
   `statsbomb.com/resource-centre` before accessing the Service. Register the
   `data@statlas.com` mailbox once and note it here; re-verify the ask still
   stands whenever the agreement is re-read. This is an ask, not a hard gate —
   but an unfulfilled recorded obligation is a compliance smell, not a fix.
5. **§1.4 attribution check (every run):** confirm the StatsBomb attribution
   renders on every surface showing event data — the on-map note
   (`web/components/EventMaps.tsx`, class `statsbomb-attribution`), the
   `/data-coverage` attribution block (driven by `/api/v1/coverage`), and the
   StatsBomb logo/source statement on maps. **Also verify the license label
   text itself still matches the current agreement terms** — this check exists
   because the label drifted once already (the shipped "CC BY-NC-SA 4.0"
   string was corrected to "StatsBomb Public Data User Agreement" on
   2026-08-15 after the LICENSE.pdf re-read).
6. If either check fails, fix before the changelog entry is written — the
   changelog must never announce a sync whose attribution state is wrong.

---

## C4 — Ongoing iteration cadence

### Weekly triage review (ongoing)

Every week, one recurring review session:

1. **Triage the feedback mailbox** (data@statlas.com + feedback@statlas.com)
   against the categories in `soft-launch-plan.md` §B4. Data-accuracy items
   keep their 24h SLA; everything else is triaged here.
2. **Verify the refresh report** (C3 above) and add its changelog entry.
3. **Pick the top 1–3 items** for the week and add them to the tracker as
   tasks with owners (solo founder = one owner). Every item gets a resolution:
   fixed, explicitly declined with reason, or parked with a revisit date —
   nothing dies silently.
4. **Update the public changelog** with any fixes shipped that week (dated,
   specific, category-tagged). This is the visible proof that feedback lands.

### Public roadmap

A short, honest roadmap section on the About or Help page lists what is being
worked on and what is explicitly not planned — so feature requests that are
declined are declined visibly, not silently dropped. (Planned: fold into the
next content pass; the roadmap lives in `docs/suite/ImplementationPlan.md`
until then.)

### Escalation rules

- **Data-accuracy reports**: always acted on within 24h, regardless of triage
  day — the SLA is absolute.
- **Payment/billing issues**: treated as critical; any report is investigated
  the same day (billing bugs are the highest-cost category).
- **Everything else**: weekly cadence.

---

## Next body of work (post soft-launch, per the original startup plan)

Once the soft-launch go/no-go passes, the next work is not another numbered
build phase but operational growth:

1. **Go-to-market execution at wider scale** — SEO on the server-rendered
   player/team pages, embeddable widgets as the backlink loop, non-English
   locale expansion.
2. **B2B / licensed data feeds evaluation** — migrating from free-tier scraped
   sources (FBref/Understat) to a licensed feed (Wyscout/Opta/Sportmonks) as
   revenue and user trust justify the cost. The data-source layer is already
   modular behind the `StatsSource` interface precisely so this swap does not
   rearchitect the app.

---

## Related documents

| Document | Relationship |
|---|---|
| `docs/launch/soft-launch-plan.md` | The soft-launch contract this cadence continues |
| `docs/launch/feedback-triage-log.md` | The triage log this cadence feeds |
| `docs/suite/ImplementationPlan.md` | Roadmap / task source of truth |
| `docs/engineering/infra-plan.md` | Monitoring + backup plan the refresh runbook assumes |
| `docs/analytics/production-validation-log.md` | The data-validation evidence for the production flip |
