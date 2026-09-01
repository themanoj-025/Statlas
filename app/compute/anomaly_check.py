"""Anomaly detection (Constitution §3: values outside plausible bounds are
flagged and blocked from publication until reviewed; never silently published).

Two passes:
1. check_snapshot_bounds — every metric value in every stat_snapshot is checked
   against its registry bounds (e.g. pass completion % in [0,100], no negative
   minutes, no statistically impossible values). Violations become
   ingestion_anomalies rows and the snapshot's status flips to 'flagged'.
2. cross_source_spot_check — for players present in both FBref and Understat,
   overlapping metrics (xG, shots) are compared and significant divergence is
   flagged for review (with a stat_snapshot_id of NULL — the anomaly is about
   the *relationship* between two sources, not one row).

blocked_player_ids() then feeds the percentile job so flagged players neither
rank nor are ranked.
"""

from __future__ import annotations

import logging
from datetime import datetime
from random import Random

from sqlalchemy.orm import Session

from app.config import load_registry
from app.models import IngestionAnomaly, League, StatSnapshot

logger = logging.getLogger(__name__)

_AUX_KEYS_PREFIX = (
    "_"  # raw_stats keys starting with '_' are sample-floor counts, not metrics
)


def check_snapshot_bounds(db: Session, snapshot_date: datetime | None = None) -> int:
    """Bounds-check every metric of every snapshot for a scrape date.

    Returns the number of newly flagged anomalies.
    """
    registry = load_registry()
    metrics = registry["metrics"]
    field_bounds = registry["anomaly"]["field_bounds"]
    flagged = 0

    snaps = db.query(StatSnapshot)
    if snapshot_date is not None:
        snaps = snaps.filter(StatSnapshot.scrape_date == snapshot_date)
    for snap in snaps.all():
        violations: list[tuple[str, str, str]] = []

        for field, (lo, hi) in field_bounds.items():
            value = getattr(snap, field)
            if value is not None and not (lo <= float(value) <= hi):
                violations.append((field, str(value), f"{lo}..{hi}"))

        # Fail-loudly guard for silent schema drift: an FBref snapshot with real
        # minutes but ZERO extracted registry metrics means the page structure
        # changed and nothing mapped (the scraper does not return partial rows,
        # but a wholesale rename would otherwise pass unnoticed). Partial
        # coverage is NOT flagged here — only the complete-empty case.
        if snap.source == "fbref" and snap.minutes_played > 0:
            metric_keys = [
                k for k in (snap.raw_stats or {}) if not k.startswith(_AUX_KEYS_PREFIX)
            ]
            if not metric_keys:
                violations.append(
                    (
                        "raw_stats",
                        "<empty>",
                        "at least one registry metric for a played fbref snapshot",
                    )
                )

        for key, value in (snap.raw_stats or {}).items():
            if key.startswith(_AUX_KEYS_PREFIX):
                continue
            spec = metrics.get(key)
            if spec is None:
                # An undocumented metric in the payload is itself an anomaly:
                # raw_stats must only contain registry metrics + '_' aux keys.
                violations.append((key, str(value), "not-in-registry"))
                continue
            lo, hi = spec["bounds"]
            if not (lo <= float(value) <= hi):
                violations.append((key, str(value), f"{lo}..{hi}"))

        for field, raw, expected in violations:
            if _has_unresolved(db, snap.id, field):
                continue
            db.add(
                IngestionAnomaly(
                    stat_snapshot_id=snap.id,
                    field_name=field,
                    raw_value=raw,
                    expected_range=expected,
                    resolved=False,
                )
            )
            flagged += 1
        if violations and snap.status == "ingested":
            snap.status = "flagged"
    db.commit()
    return flagged


def cross_source_spot_check(
    db: Session,
    *,
    snapshot_date: datetime | None = None,
    sample_size: int | None = None,
    seed: int = 42,
) -> int -> None:
    """Compare FBref vs Understat values for overlapping metrics on a sample of
    Tier-1 players. Returns the number of divergence flags written."""
    registry = load_registry()
    cfg = registry["anomaly"]["cross_source"]
    if not cfg.get("enabled", True):
        return 0
    sample_size = sample_size or cfg.get("sample_size", 20)
    metrics_cfg = cfg["metrics"]

    snaps = db.query(StatSnapshot).join(League, StatSnapshot.league_id == League.id)
    if snapshot_date is not None:
        snaps = snaps.filter(StatSnapshot.scrape_date == snapshot_date)

    pairs: dict[int, dict[str, StatSnapshot]] = {}
    for snap in snaps.all():
        if snap.league.tier != "tier_1":
            continue
        pairs.setdefault(snap.player_id, {})[snap.source] = snap

    flagged = 0
    rng = Random(seed)
    players = list(pairs.keys())
    rng.shuffle(players)
    for player_id in players[:sample_size]:
        both = pairs[player_id]
        fbref, understat = both.get("fbref"), both.get("understat")
        if fbref is None or understat is None:
            continue
        for mid, tol in metrics_cfg.items():
            a = (fbref.raw_stats or {}).get(mid)
            b = (understat.raw_stats or {}).get(mid)
            if a is None or b is None:
                continue
            if abs(a - b) > tol["absolute_tolerance"] and (
                abs(a - b) / max(abs(a), abs(b), 1e-9) > tol["relative_tolerance"]
            ):
                if _has_unresolved(
                    db, None, f"cross_source:{mid}", player_id=player_id
                ):
                    continue
                db.add(
                    IngestionAnomaly(
                        stat_snapshot_id=None,
                        field_name=f"cross_source:{mid}",
                        raw_value=f"fbref={a} understat={b}",
                        expected_range=(
                            f"abs diff <= {tol['absolute_tolerance']} or "
                            f"rel diff <= {tol['relative_tolerance']}"
                        ),
                        resolved=False,
                    )
                )
                flagged += 1
    db.commit()
    return flagged


def _has_unresolved(
    db: Session,
    stat_snapshot_id: int | None,
    field_name: str,
    player_id: int | None = None,
) -> bool:
    q = db.query(IngestionAnomaly).filter(
        IngestionAnomaly.resolved.is_(False),
        IngestionAnomaly.stat_snapshot_id == stat_snapshot_id,
        IngestionAnomaly.field_name == field_name,
    )
    return q.first() is not None


def blocked_player_ids(db: Session, snapshot_date: datetime | None = None) -> set[int]:
    """Player ids with an unresolved anomaly — excluded from percentile pools
    until the anomaly is resolved or explicitly overridden.

    The block is intentionally NOT scoped to a scrape date: an unresolved
    data-quality problem keeps the player out of every computation run (today's
    and future ones) until a human resolves it. `snapshot_date` is accepted for
    API symmetry with the other anomaly functions but deliberately ignored —
    narrowing the block to one scrape would silently re-admit a player whose
    earlier anomaly was never reviewed (Constitution: never silently published).
    """
    del snapshot_date  # intentional: blocking is global until resolved
    query = (
        db.query(StatSnapshot.player_id)
        .join(IngestionAnomaly, IngestionAnomaly.stat_snapshot_id == StatSnapshot.id)
        .filter(IngestionAnomaly.resolved.is_(False))
    )
    return {row[0] for row in query.all()}


def resolve_anomaly(
    db: Session,
    anomaly_id: int,
    *,
    note: str,
    resolved_by: str = "manual",
) -> IngestionAnomaly -> None:
    """Explicit human override — the only way a flagged value reaches
    publication. 'Never silently published' is implemented as 'must be reviewed'."""
    anomaly = db.get(IngestionAnomaly, anomaly_id)
    if anomaly is None:
        raise ValueError(f"no anomaly with id {anomaly_id}")
    anomaly.resolved = True
    anomaly.resolution_note = f"{note} (resolved by {resolved_by})"
    db.commit()
    return anomaly
