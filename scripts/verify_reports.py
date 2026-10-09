"""Phase 9 — verify report grounding across 10+ real players.

Quality gate (Part E): for a sample of at least 10 real players, generate a
report through the full pipeline (deterministic narrator — the same verified
context and hard gate the LLM narrator uses) and confirm:

1. every report PASSES the verification gate (no unverified claim);
2. the confidence level matches the documented deterministic rules
   (scouting-reports.md §3): recompute it from the report's own factor inputs
   and require an exact match;
3. every comparable player in the report is a real Phase 6 result with the
   exact similarity score from the context;
4. every strength/weakness supporting metric is a registry metric with a
   value present in the evidence appendix.

Run against a real seeded DB:

    python scripts/verify_reports.py [--db data/dev.db] [--limit 12]

Exit code 0 = all reports grounded and consistent; 1 = any failure.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import reports
from app.models import Player


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/dev.db", help="path to the SQLite DB")
    parser.add_argument("--limit", type=int, default=12, help="max reports to verify")
    args = parser.parse_args()

    engine = create_engine(f"sqlite:///{args.db}")
    db = sessionmaker(bind=engine, expire_on_commit=False)()

    # Players that have any stat snapshot (a report cannot be grounded
    # otherwise) — the gather step further filters to published percentiles.
    from app.models import StatSnapshot

    player_ids = [row[0] for row in db.query(StatSnapshot.player_id).distinct().all()]
    players = (
        db.query(Player)
        .filter(Player.id.in_(player_ids))
        .order_by(Player.id)
        .limit(args.limit * 3)
        .all()
    )

    now = datetime.now(timezone.utc)
    verified = 0
    checked = 0
    failures = 0

    for player in players:
        if checked >= args.limit:
            break
        try:
            context = reports.gather_report_context(db, player.id)
        except reports.PlayerHasNoData:
            continue

        # Run the exact pipeline steps (gather -> narrate -> hard verify)
        # without the quota/storage gating, which is covered by the unit suite
        # and would cap at the Pro monthly allowance.
        draft = reports.deterministic_narrator(context)
        verification = reports.verify_report(draft, context)
        checked += 1
        snapshot = context["data_snapshot_date"]
        doc = {
            "verification": {
                "status": "passed" if verification["passed"] else "needs_review"
            },
            "data_snapshot_date": (
                snapshot.date().isoformat()
                if hasattr(snapshot, "date")
                else str(snapshot)[:10]
            ),
            "confidence": context["confidence"],
            "sections": draft["sections"],
            "evidence_appendix": reports._build_evidence_appendix(context),
            "player_id": player.id,
        }
        problems: list[str] = []

        # 1. The gate itself.
        if doc["verification"]["status"] != "passed":
            problems.append("verification failed")

        # 2. Confidence recomputed from the report's own factors must match.
        conf = doc["confidence"]
        recomputed = reports.compute_report_confidence(
            minutes_played=conf["factors"]["sample_size"]["minutes_played"],
            qualifying_minutes=conf["factors"]["sample_size"]["qualifying_minutes"],
            metrics_present=conf["factors"]["data_completeness"]["metrics_present"],
            metrics_expected=conf["factors"]["data_completeness"]["metrics_expected"],
            snapshot_date=datetime.fromisoformat(doc["data_snapshot_date"]),
            now=now,
        )
        if recomputed["level"] != conf["level"]:
            problems.append(
                f"confidence {conf['level']} != recomputed {recomputed['level']}"
            )
        if conf["level"] not in ("high", "medium", "low"):
            problems.append(f"confidence level '{conf['level']}' not a valid level")

        # 3. Comparables must be real Phase 6 results (subset check).
        context_comparables = {
            (c["player_id"], round(float(c["similarity"]), 4))
            for c in context["comparables"]
        }
        for comparable in doc["sections"]["comparable_players"]:
            key = (comparable["player_id"], round(float(comparable["similarity"]), 4))
            if key not in context_comparables:
                problems.append(
                    f"comparable {comparable['player_id']} not a real Phase 6 result"
                )

        # 4. Strength/weakness metrics traceable to the evidence appendix.
        appendix_metrics = {
            item["raw_result"].get("metric")
            for item in doc["evidence_appendix"]
            if isinstance(item.get("raw_result"), dict)
        }
        for item in doc["sections"]["strengths"] + doc["sections"]["weaknesses"]:
            if item["supporting_metric"] not in appendix_metrics:
                problems.append(
                    f"strength/weakness metric {item['supporting_metric']} not in appendix"
                )

        # 5. The workspace-context rule: ad hoc generation must omit it.
        if doc["sections"]["workspace_context"] is not None:
            problems.append("workspace_context present in an ad hoc report")

        status = "OK " if not problems else "FAIL"
        print(
            f"[{status}] {player.canonical_name:<28} conf={conf['level']:<6} "
            f"comps={len(doc['sections']['comparable_players'])} "
            f"appendix={len(doc['evidence_appendix'])}"
            + (f"  | {'; '.join(problems)}" if problems else "")
        )
        if not problems:
            verified += 1
        else:
            failures += 1

    db.close()
    engine.dispose()

    print(
        f"\n{verified}/{checked} reports verified grounded and consistent "
        f"({failures} failing)"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
