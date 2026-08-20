"""Phase 8 — validate every curated search preset against CURRENT data.

Quality gate (Part E): every preset in app/config/search_presets.json must
execute against the published population and return a real, sensible,
non-empty result set — never a placeholder or a query that silently matches
nothing. Each preset's one-line rationale is also printed so a human can spot
a preset whose copy no longer matches what the data returns.

Usage:
    python scripts/validate_search_presets.py [--db data/dev.db] [--json]

Exit code 0 = every preset ran and returned results; 1 = any failure.
"""

from __future__ import annotations

import argparse
import json
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.queries.structured_search import execute_structured_query, list_presets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/dev.db", help="path to the SQLite DB")
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON instead"
    )
    args = parser.parse_args()

    engine = create_engine(f"sqlite:///{args.db}")
    db = sessionmaker(bind=engine, expire_on_commit=False)()

    presets = list_presets()
    rows = []
    failures = 0

    for preset in presets:
        try:
            result = execute_structured_query(
                db, preset["query_definition"], user_id=None, log_history=False, limit=5
            )
            total = result["total"]
            top = [e["name"] for e in result["entries"][:3]]
            ok = total > 0
            if not ok:
                failures += 1
            rows.append(
                {
                    "id": preset["id"],
                    "name": preset["name"],
                    "rationale": preset["rationale"],
                    "total": total,
                    "top": top,
                    "ok": ok,
                }
            )
            print(
                f"[{'OK ' if ok else 'FAIL'}] {preset['name']:<42} -> {total:>4} players"
                + (f"  | {', '.join(top)}" if top else "")
            )
        except Exception as exc:  # noqa: BLE001 — a broken preset is a failure
            failures += 1
            rows.append(
                {
                    "id": preset["id"],
                    "name": preset["name"],
                    "error": str(exc),
                    "ok": False,
                }
            )
            print(f"[FAIL] {preset['name']:<42} -> error: {exc}")

    db.close()
    engine.dispose()

    if args.json:
        print(json.dumps({"presets": rows, "failures": failures}, indent=2))
    print(
        f"\n{len(rows) - failures}/{len(rows)} presets validated "
        f"({failures} failing)"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
