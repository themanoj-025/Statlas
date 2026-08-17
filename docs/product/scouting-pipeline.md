# Scouting Workspace — Status Pipeline & Data Rules (Phase 7)

This document defines the exact rules that govern the scouting workspace:
the status pipeline, entry integrity, soft-delete semantics, and ownership
boundaries. Every rule here is enforced in code (`app/queries/workspace_queries.py`)
and covered by tests (`tests/test_workspace.py`) — nothing here is a UI-level
suggestion.

## 1. The pipeline

An entry (a player saved into a shortlist) always carries exactly one status,
chosen from these 7:

```
discovered → monitoring → scouted → shortlisted → reviewed
```

plus two **terminal-but-reversible** states:

```
rejected    — terminal: the player is not currently a target
signed      — terminal: the player has been signed / the deal is done
```

### 1.1 Transition rules (validated server-side, never free text)

1. **Forward movement** within the chain may **skip stages** — `discovered → shortlisted`
   is valid. A scout does not have to burn intermediate states.
2. **Backward movement** within the chain is allowed — `shortlisted → monitoring`
   is valid. Status reflects the *current assessment*; the audit trail
   (`status_history`) preserves the path, so nothing is lost by moving back.
3. **Any** non-terminal status may move to `rejected` or `signed` directly.
4. **`rejected` is reversible but only through `monitoring`** — a rejected
   player who is reconsidered must move `rejected → monitoring` first, then
   proceed normally. Direct `rejected → scouted` (or any other jump out of
   `rejected`) is **invalid** and rejected with a specific error. This keeps
   the audit trail readable: every exit from `rejected` is an explicit
   "reconsideration" event.
5. **`signed` is terminal and not reversible through the pipeline.** If the
   situation changes after a signing (player does not work out, deal collapses),
   remove the entry (soft delete — full history preserved) and re-add if
   needed. `signed → anything` is **invalid** and rejected with a specific
   error.
6. **Same-status is a no-op**: setting the status to its current value does
   not write a `status_history` row (no noise in the audit trail).

### 1.2 What the states mean

| Status       | Meaning                                                        |
| ------------ | -------------------------------------------------------------- |
| discovered   | Just found the player; no assessment yet (default on add).     |
| monitoring   | Tracking over time; data collection in progress.               |
| scouted      | Watched live / on film; first-hand assessment exists.          |
| shortlisted  | On the active list of targets for a decision.                  |
| reviewed     | Full assessment done; decision pending.                        |
| rejected     | Assessed and passed over — terminal unless reconsidered.       |
| signed       | Deal done — terminal.                                          |

## 2. Entry integrity

- **One player, once per shortlist.** `UNIQUE (shortlist_id, player_id)` — a
  player can appear in *multiple* shortlists (different scouting projects) but
  never twice in the same one. Adding a duplicate raises `DuplicateEntry`
  (409), it never silently duplicates.
- **Re-adding a removed player** un-removes the existing entry (clears
  `removed_at`, keeps status and full history) rather than creating a second row.

## 3. Soft delete — history is never destroyed

- `remove_entry` sets `shortlist_entries.removed_at`; `delete_shortlist` sets
  `shortlists.deleted_at` and removes all its entries (soft). Entries with
  `removed_at` set disappear from lists/details but **notes, tags and the
  complete `status_history` remain queryable** — the audit trail survives
  removal, so "why did we drop this player" stays answerable.
- Tags are the one exception: removing a tag deletes the row outright (a tag
  is vocabulary, not audit data).

## 4. Ownership & authorization

- Every row is reachable only through `shortlists.user_id`. Every query
  function takes the requesting `user_id` and verifies ownership on every read
  and write.
- A shortlist or entry that is **missing OR owned by another user** raises the
  same `ShortlistNotFound` (→ HTTP 404). We deliberately return 404 rather
  than 403: a 403 would *confirm the shortlist exists* to someone probing ids.
  A scout's shortlist reveals real recruitment intentions; existence must not
  leak.
- Tier caps (Free: 1 shortlist, 10 entries per shortlist; Pro/API-Business:
  unlimited) return 403 with an explicit, honest upsell message naming the
  plan's allowance — never a generic error.
- `get_user_tag_suggestions` reads **only the requesting user's own tags** —
  other users' private vocabulary is never surfaced.

## 5. Player merges (name reconciliation)

`shortlist_entries.player_id` references the canonical `players` row. When
name reconciliation merges two players, the merge flow must **reassign
`shortlist_entries.player_id` to the surviving canonical id** (the FK is
RESTRICT, so a merge can never silently orphan scouting rows). The
`UNIQUE (shortlist_id, player_id)` constraint then guarantees a merged player
never ends up twice in one shortlist. No live merge flow exists yet
(reconciliation is a manual queue); this rule is documented so the future
merge implementation is forced to handle it.
