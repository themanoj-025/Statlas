"""Percentile computation (percentile-rules.md, methodology.md §5).

For each qualifying player (>= 900 minutes) in each {position group, league
tier} cohort, computes the fractional-rank percentile for every input metric:

    P = (B + 0.5 * E) / N * 100

B = number of peers strictly below (above for lower-is-better metrics),
E = number of peers exactly equal (ties share the midpoint),
N = total qualifying players in the cohort.

Results are written as NEW rows in percentile_snapshots keyed by
(stat_snapshot_id, metric_name) — never updates to existing rows
(Constitution: append-only, immutable snapshots). Re-running the job for an
already-computed snapshot is a no-op (idempotency).

Value resolution honours the per-metric source precedence from the registry
(e.g. Tier 1 xG comes from Understat, Tiers 2/3 from FBref — one xG model per
cohort, never mixed) and the per-metric display floors (a player below the
pass-attempt/SoTA/cross floor contributes no value for that metric).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import load_registry, load_tiers
from app.models import League, PercentileSnapshot, Player, StatSnapshot

logger = logging.getLogger(__name__)

REGISTRY_FLOOR_KEYS = {
    "si_cmp_pct": ("_cmp_attempts", 50),
    "si_save_pct": ("_sota_faced", 20),
    "si_cross_pct": ("_crosses_faced", 10),
}
MIN_REQUIRED_METRICS = {"outfield": 8, "gk": 3}


@dataclass
class PercentileReport:
    snapshot_date: datetime | None = None
    cohorts: int = 0
    percentile_rows: int = 0
    index_rows: int = 0
    skipped_small_pool: list[str] = field(default_factory=list)
    skipped_blocked: int = 0
    skipped_incomplete_tiers: list[str] = field(default_factory=list)


def latest_snapshot_date(db: Session) -> datetime | None:
    row = db.execute(
        select(StatSnapshot.scrape_date)
        .order_by(StatSnapshot.scrape_date.desc())
        .limit(1)
    ).first()
    return row[0] if row else None


def _precedence_for(spec: dict[str, Any], tier: str) -> list[str]:
    precedence = spec.get("precedence")
    if precedence:
        return precedence.get(tier, precedence.get("default", ["fbref"]))
    return ["fbref"]


def _floor_met(raw_stats: dict[str, float], mid: str) -> bool:
    floor = REGISTRY_FLOOR_KEYS.get(mid)
    if floor is None:
        return True
    key, minimum = floor
    return raw_stats.get(key, 0) >= minimum


def resolve_metric_value(
    player_id: int,
    mid: str,
    tier: str,
    snapshots_by_player_source: dict[tuple[int, str], StatSnapshot],
    registry: dict[str, Any],
) -> tuple[float | None, StatSnapshot | None] -> None:
    """Resolve the value + winning snapshot for (player, metric) using the
    registry's per-metric source precedence.

    Keys are (player_id, source) — callers must scope the map to ONE tier
    (percentiles does; the cross-tier-transfer fix keys by tier) so a
    same-season cross-tier transfer never resolves the wrong tier's snapshot.
    """
    spec = registry["metrics"][mid]
    for source_name in _precedence_for(spec, tier):
        snap = snapshots_by_player_source.get((player_id, source_name))
        if snap is None:
            continue
        raw = snap.raw_stats or {}
        if mid not in raw:
            continue
        if not _floor_met(raw, mid):
            return None, snap  # present but below the display floor -> N/A
        return float(raw[mid]), snap
    return None, None


def fractional_rank(value: float, all_values: list[float], invert: bool) -> float:
    """P = (B + 0.5E)/N*100 with the direction applied to the comparison.

    B and E count PEERS only — the player's own value is excluded, so a
    single-player pool ranks 0, a tied pair shares the midpoint of their
    block, and the cohort maximum is 100 - 50/N (never a false perfect 100).
    N is the full cohort size (including the player).
    """
    n = len(all_values)
    if n == 0:
        return 0.0
    if invert:
        # lower-is-better: peers above the value count as "better"
        below = sum(1 for v in all_values if v > value)
    else:
        below = sum(1 for v in all_values if v < value)
    equal = sum(1 for v in all_values if v == value) - 1  # peers only
    return (below + 0.5 * equal) / n * 100.0


def compute_index_score(
    percentiles: dict[str, float], group: str, registry: dict[str, Any]
) -> float | None -> None:
    """Weighted mean of the player's metric percentiles for their position group.

    Weights come from the registry (derived from methodology.md §4). When a
    metric is missing (N/A), weights are renormalised over the present set; if
    too few metrics are present the index is not computed (NULL -> displayed as
    pending, never as a low score).
    """
    weights = registry["position_weights"].get(group)
    if not weights:
        return None
    present = {mid: p for mid, p in percentiles.items() if mid in weights}
    if not present:
        return None
    kind = "gk" if group == "GK" else "outfield"
    if len(present) < MIN_REQUIRED_METRICS[kind]:
        return None
    total_weight = sum(weights[mid] for mid in present)
    if total_weight <= 0:
        return None
    return round(
        sum((weights[mid] / total_weight) * p for mid, p in present.items()), 2
    )


def tier_completeness(
    db: Session,
    *,
    season: str | None = None,
    tier: str | None = None,
) -> list[str] -> None:
    """Leagues of each tier that are NOT fully ingested for the season.

    percentile-rules.md §1.4: a tier's percentiles are only computed when the
    pool is complete for its tier — every league in the tier must be present
    for the season (coverage matrix as arbiter, Constitution §3). Returns the
    slugs of incomplete tiers (empty list = all tiers complete).
    """
    from app.models import DataCoverage, League

    tiers_cfg = load_tiers()
    incomplete: list[str] = []
    for slug, cfg in tiers_cfg["leagues"].items():
        if tier and cfg["tier"] != tier:
            continue
        coverage_row = (
            db.query(DataCoverage)
            .join(League, DataCoverage.league_id == League.id)
            .filter(
                DataCoverage.source == "fbref",
                League.slug == slug,
                DataCoverage.status == "active",
            )
            .first()
        )
        covered = coverage_row is not None
        if covered and season is not None:
            covered = season in (coverage_row.seasons_available or [])
        if not covered:
            incomplete.append(slug)
    return incomplete


def compute_percentiles(
    db: Session,
    *,
    snapshot_date: datetime | None = None,
    season: str | None = None,
    tier: str | None = None,
    blocked_player_ids: set[int] | None = None,
    now: datetime | None = None,
    require_tier_completeness: bool = False,
) -> PercentileReport -> None:
    """Compute percentiles + index scores for all qualifying players.

    - snapshot_date: the scrape date whose data forms the pools (default: latest).
    - blocked_player_ids: players excluded from pools (unresolved anomalies);
      they neither rank nor are ranked.
    - require_tier_completeness: when True (production weekly runs), a tier is
      withheld unless EVERY league in it is ingested for the season (the §1.4
      completeness gate). Defaults to False to preserve the documented
      single-league integration contract for tests.
    - Re-running for an already-computed snapshot_date is a no-op per snapshot.
    """
    registry = load_registry()
    now = now or datetime.now(timezone.utc)
    report = PercentileReport()
    blocked = blocked_player_ids or set()

    if snapshot_date is None:
        snapshot_date = latest_snapshot_date(db)
    if snapshot_date is None:
        logger.warning("compute_percentiles: no snapshots in database; nothing to do")
        return report
    report.snapshot_date = snapshot_date

    qualifying_minutes = registry["qualifying_minutes"]
    min_pool = registry["min_pool_size"]

    # §1.4 tier-completeness gate (closeout C1): withhold a tier when its
    # league list is only partially ingested for the season. The coverage
    # matrix is the arbiter. Applied per-tier when the gate is on.
    withheld_tiers: set[str] = set()
    if require_tier_completeness:
        incomplete = tier_completeness(db, season=season, tier=tier)
        if incomplete:
            tiers_cfg = load_tiers()
            for slug in incomplete:
                t = tiers_cfg["leagues"][slug]["tier"]
                withheld_tiers.add(t)
                if t not in report.skipped_incomplete_tiers:
                    report.skipped_incomplete_tiers.append(t)
            logger.warning(
                "tier-completeness gate: withholding %s (incomplete leagues: %s)",
                sorted(withheld_tiers),
                incomplete,
            )

    snaps = (
        db.query(StatSnapshot)
        .join(Player, StatSnapshot.player_id == Player.id)
        .join(League, StatSnapshot.league_id == League.id)
        .filter(
            StatSnapshot.scrape_date == snapshot_date,
            StatSnapshot.minutes_played >= qualifying_minutes,
        )
        .all()
    )
    report.skipped_blocked = sum(1 for s in snaps if s.player_id in blocked)
    snaps = [s for s in snaps if s.player_id not in blocked]

    # Idempotency sets, captured BEFORE any inserts in this run. Checking these
    # live would flush this run's pending rows mid-loop (autoflush), making a
    # later metric see earlier metrics' rows and skip every player. Precomputing
    # means: re-running for an already-computed snapshot_date is a no-op, while
    # one fresh run computes every metric exactly once.
    index_metric_id = registry["index_metric_id"]
    snapshots_with_rows = {
        r[0] for r in db.query(PercentileSnapshot.stat_snapshot_id).all()
    }
    snapshots_with_index = {
        r[0]
        for r in db.query(PercentileSnapshot.stat_snapshot_id).filter(
            PercentileSnapshot.metric_name == index_metric_id
        )
    }

    # Index by cohort and by player. snapshots_by_player_source is keyed by
    # (player_id, source) PER TIER (the C1 fix): a same-season cross-tier
    # transfer has two qualifying snapshots in two leagues; a tier-agnostic
    # (player, source) key would silently keep only the first and resolve the
    # wrong tier's snapshot for the other cohort (and collide on the
    # percentile unique key). Each cohort resolves against ITS OWN tier's map.
    by_cohort: dict[tuple[str, str], list[StatSnapshot]] = defaultdict(list)
    snapshots_by_tier: dict[str, dict[tuple[int, str], StatSnapshot]] = defaultdict(
        dict
    )
    for snap in snaps:
        group = snap.player.position_group
        league_tier = snap.league.tier
        if group is None or league_tier is None:
            continue
        if tier and league_tier != tier:
            continue
        if season and snap.season != season:
            continue
        if league_tier in withheld_tiers:
            continue  # §1.4 gate: never rank a partially-ingested tier
        by_cohort[(league_tier, group)].append(snap)
        key = (snap.player_id, snap.source)
        snapshots_by_tier[league_tier].setdefault(key, snap)

    for (league_tier, group), cohort_snaps in sorted(by_cohort.items()):
        metric_ids = (
            registry["gk_metrics"] if group == "GK" else registry["outfield_metrics"]
        )
        snapshots_by_player_source = snapshots_by_tier[league_tier]

        # Per-player primary snapshot (index row attachment target): prefer fbref.
        players = {s.player_id: s for s in cohort_snaps}
        primary_snapshot: dict[int, StatSnapshot] = {}
        for player_id, snap in players.items():
            primary_snapshot[player_id] = players.get(player_id)
        for player_id, snap in players.items():
            fbref = snapshots_by_player_source.get((player_id, "fbref"))
            if fbref is not None:
                primary_snapshot[player_id] = fbref

        metric_values: dict[str, list[tuple[int, float, StatSnapshot]]] = defaultdict(
            list
        )
        for mid in metric_ids:
            spec = registry["metrics"][mid]
            invert = spec["direction"] == "lower_is_better"
            entries: list[tuple[int, float, StatSnapshot]] = []
            for player_id in players:
                value, winner = resolve_metric_value(
                    player_id, mid, league_tier, snapshots_by_player_source, registry
                )
                if value is None or winner is None:
                    continue
                # idempotency: skip players whose percentile rows already exist
                # (precomputed set — never a live query, see above)
                if winner.id in snapshots_with_rows:
                    continue
                entries.append((player_id, value, winner))
            n = len(entries)
            if n < min_pool:
                report.skipped_small_pool.append(f"{league_tier}/{group}/{mid} (N={n})")
                logger.info(
                    "pool below %d for %s/%s/%s — skipping percentile",
                    min_pool,
                    league_tier,
                    group,
                    mid,
                )
                continue
            values = [v for _, v, _ in entries]
            for player_id, value, winner in entries:
                p = round(fractional_rank(value, values, invert), 2)
                db.add(
                    PercentileSnapshot(
                        stat_snapshot_id=winner.id,
                        computed_date=now,
                        position_group=group,
                        league_tier=league_tier,
                        metric_name=mid,
                        percentile_value=p,
                        index_score=None,
                        is_published=False,
                    )
                )
                metric_values[mid].append((player_id, p))
                report.percentile_rows += 1

        # Index score per player in the cohort (from this run's metric rows).
        player_percentiles: dict[int, dict[str, float]] = defaultdict(dict)
        for mid, entries in metric_values.items():
            for player_id, p in entries:
                player_percentiles[player_id][mid] = p
        for player_id, percentiles in player_percentiles.items():
            score = compute_index_score(percentiles, group, registry)
            if score is None:
                continue
            primary = primary_snapshot.get(player_id)
            if primary is None:
                continue
            if primary.id in snapshots_with_index:
                continue
            db.add(
                PercentileSnapshot(
                    stat_snapshot_id=primary.id,
                    computed_date=now,
                    position_group=group,
                    league_tier=league_tier,
                    metric_name=registry["index_metric_id"],
                    percentile_value=None,
                    index_score=score,
                    is_published=False,
                )
            )
            report.index_rows += 1
        report.cohorts += 1

    db.commit()
    return report
