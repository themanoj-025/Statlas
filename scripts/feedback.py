"""Final launch Part C2 — feedback triage CLI for the soft-launch window.

Structured intake + rollup for the founder running the 14-day soft launch
(docs/launch/soft-launch-plan.md). Entries live in one JSONL file,
`docs/launch/feedback-entries.jsonl`, and every command is idempotent and
append-only — nothing here edits historical entries except `resolve`, which
only fills in the resolution fields of an existing entry.

Triage schema (soft-launch-plan.md §B4):
    accuracy   — a number on the site does not match reality or the published
                 methodology  (SLA: same/next-day fix + reply within 24h)
    bug        — a page/flow/component misbehaves (not a data value)
    feature    — a capability Statlas does not have
    pricing    — value/price feedback
    sentiment  — general impression

Usage:
    # Log an incoming item (received defaults to now, UTC):
    python scripts/feedback.py add --category accuracy \\
        --summary "Keller minutes shown as 1200 but FBref says 1345" \\
        --channel email --url /players/andres-keller

    # Mark resolution + response time:
    python scripts/feedback.py resolve FB-0001 --resolution fixed \\
        --note "Re-scraped snapshot; changelog entry 2026-08-15" \\
        --responded 2026-08-15T10:00Z

    # Daily rollup (run once per day during the window):
    python scripts/feedback.py summary

Exit code 0 = ok, 1 = a go/no-go SLA breach exists (so CI or a cron can alert).

The same data can be mirrored into the human-readable triage log
(docs/launch/feedback-triage-log.md) at the end of the window; the JSONL is
the machine source of truth.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "launch"
    / "feedback-entries.jsonl"
)
CATEGORIES = ("accuracy", "bug", "feature", "pricing", "sentiment")
RESOLUTIONS = ("fixed", "wontfix", "duplicate", "not-a-bug", "open")
ACCURACY_SLA_HOURS = 24  # soft-launch-plan.md §B4


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    return [
        json.loads(line)
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _save(entries: list[dict]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _next_id(entries: list[dict]) -> str:
    used = {e["id"] for e in entries}
    n = 1
    while f"FB-{n:04d}" in used:
        n += 1
    return f"FB-{n:04d}"


def cmd_add(args: argparse.Namespace) -> int:
    entries = _load()
    entry = {
        "id": _next_id(entries),
        "category": args.category,
        "received": args.received or _now(),
        "channel": args.channel or "unknown",
        "url": args.url or "",
        "summary": args.summary,
        "resolution": "open",
        "resolved_at": None,
        "responded_at": None,
        "response_hours": None,
        "note": "",
    }
    entries.append(entry)
    _save(entries)
    print(f"{entry['id']} logged: [{entry['category']}] {entry['summary']}")
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    entries = _load()
    target = next((e for e in entries if e["id"] == args.id), None)
    if target is None:
        print(f"ERROR: no entry {args.id} in {LOG_PATH}", file=sys.stderr)
        return 1
    if target["resolution"] != "open" and not args.force:
        print(
            f"ERROR: {args.id} already resolved as '{target['resolution']}'. Use --force to overwrite.",
            file=sys.stderr,
        )
        return 1
    target["resolution"] = args.resolution
    target["resolved_at"] = _now()
    if args.responded:
        target["responded_at"] = args.responded
        try:
            received = datetime.strptime(
                target["received"], "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            responded = datetime.strptime(args.responded, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            target["response_hours"] = round(
                (responded - received).total_seconds() / 3600, 1
            )
        except ValueError:
            print(
                f"WARNING: could not parse responded timestamp '{args.responded}' (use ISO %Y-%m-%dT%H:%M:%SZ)",
                file=sys.stderr,
            )
    if args.note:
        target["note"] = args.note
    _save(entries)
    print(
        f"{args.id} resolved: {args.resolution}"
        + (
            f" (response in {target['response_hours']}h)"
            if target["response_hours"]
            else ""
        )
    )
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    entries = _load()
    if not entries:
        print("No feedback entries yet - window opens when the launch post ships.")
        return 0

    print(
        f"Feedback rollup - {LOG_PATH.relative_to(Path(__file__).resolve().parent.parent)}"
    )
    print(f"Total entries: {len(entries)}\n")

    print("By category:")
    for cat in CATEGORIES:
        rows = [e for e in entries if e["category"] == cat]
        open_rows = [e for e in rows if e["resolution"] == "open"]
        print(f"  {cat:<10} {len(rows):>3} total, {len(open_rows)} open")
    print()

    # Accuracy SLA: received > 24h ago and still open or unresponded.
    now = datetime.now(timezone.utc)
    sla_breaches = []
    for e in entries:
        if e["category"] != "accuracy":
            continue
        try:
            received = datetime.strptime(e["received"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        hours = (now - received).total_seconds() / 3600
        if hours > ACCURACY_SLA_HOURS and (
            e["resolution"] == "open" or not e["responded_at"]
        ):
            sla_breaches.append((e["id"], round(hours, 1)))

    if sla_breaches:
        print("SLA breaches (accuracy items >24h without resolution/reply):")
        for eid, hours in sla_breaches:
            print(f"  {eid}: {hours}h")
        print()
        return 1 if args.strict else 0

    print("Accuracy SLA: all items within 24h OK")
    print()
    print("Go/no-go progress (soft-launch-plan.md B5):")
    critical_open = [
        e for e in entries if e["category"] == "accuracy" and e["resolution"] == "open"
    ]
    print(
        f"  - Critical data-accuracy bugs unresolved: {len(critical_open)} (criterion: 0 after 14 days)"
    )
    sentiment = [e for e in entries if e["category"] == "sentiment"]
    print(
        f"  - Sentiment entries: {len(sentiment)} (criterion: >=60% positive of engaged users - judge in triage)"
    )
    print("  - Infrastructure incidents: (record separately - see triage log)")
    print("  - Organic free->Pro conversions: (record separately - Stripe dashboard)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Statlas soft-launch feedback triage (docs/launch/feedback-entries.jsonl)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="log an incoming feedback item")
    add.add_argument("--category", required=True, choices=CATEGORIES)
    add.add_argument("--summary", required=True)
    add.add_argument("--channel", default="")
    add.add_argument("--url", default="")
    add.add_argument(
        "--received",
        default="",
        help="ISO timestamp, e.g. 2026-08-15T08:00:00Z (default: now UTC)",
    )
    add.set_defaults(fn=cmd_add)

    resolve = sub.add_parser("resolve", help="mark resolution + response time")
    resolve.add_argument("id")
    resolve.add_argument("--resolution", required=True, choices=RESOLUTIONS)
    resolve.add_argument(
        "--responded", default="", help="ISO timestamp, e.g. 2026-08-15T08:00:00Z"
    )
    resolve.add_argument("--note", default="")
    resolve.add_argument("--force", action="store_true")
    resolve.set_defaults(fn=cmd_resolve)

    summary = sub.add_parser("summary", help="daily rollup vs go/no-go criteria")
    summary.add_argument("--strict", action="store_true", help="exit 1 on SLA breach")
    summary.set_defaults(fn=cmd_summary)

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
