# Statlas — Soft Launch Announcement (post text)

*Created: 2026-08-14 (Phase 5 — Part B3). Ready to post to the target
communities named in `soft-launch-plan.md`. Adjust the first line per
community norms (Twitter/X thread vs Reddit post vs Discord message).*

---

## Post

I built a football analytics site that publishes its formula.

It's called **Statlas** — per-90 stats, percentile ranks, and a composite index
for players across a set of leagues and tiers. The unusual part: the index
formula, every input metric, the position weights, and the qualifying threshold
are all published on the methodology page, generated from the same registry the
code reads. There is no black box to take on faith. The page even walks through
a worked example — a real player in the current dataset, percentile by
percentile, weight by weight, so you can reproduce the index with a calculator.

The site: **statlas.com**

A few honest notes up front, because you'll find them out anyway:

- It is **new and early-stage**. The data pipeline is real (per-90 stats,
  event data for shot/pass maps in covered competitions, weekly refresh), but
  this is a young dataset being shown to real users for the first time.
- Every stat block carries its **snapshot date** — nothing is presented as
  live except the fixtures layer. Coverage claims are enforced against a
  machine-readable matrix, so the site can't imply it has data it doesn't.
- **I want you to try to break it.** If you look up a player you know well and
  a number is wrong, or the methodology page doesn't match what the site
  shows, that is the most useful feedback there is. Every player and team page
  has a "Report a data error" button; accuracy reports are read first and
  fixed fast.

What's there: player profiles with radar + percentile ranks and the published
index, team pages, leaderboards, trend charts over snapshot history (with
honest gap handling — no invented interpolation), shot and pass maps where
event coverage exists (StatsBomb open data, attributed), a compare tool with
shareable permalinks, and an AI assistant that answers questions by calling the
real query functions — every answer is traced to the data it used, and it is
not allowed to invent numbers.

Free tier is genuinely useful. Pro is €7/month. There is also an API tier for
media/agents/smaller clubs.

Methodology first: **statlas.com/methodology**

Critical feedback is the point of this launch, not a side effect. Tell me what
breaks.

---

## Posting checklist

- [ ] Post to the target communities named in `soft-launch-plan.md` (analytics
      Twitter/X, r/footballanalysis + r/soccer, analytics Discords) — targeted,
      not a general announcement
- [ ] Include the feedback channel (feedback@statlas.com / thread) in the post
- [ ] Add the post URL + date to `feedback-triage-log.md` §"Execution record"
- [ ] Monitor the triage mailbox daily during the window (SLA in
      `soft-launch-plan.md` §B4)
