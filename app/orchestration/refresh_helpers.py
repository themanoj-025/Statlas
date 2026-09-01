"""Weekly refresh orchestration (percentile-rules.md §3: every Wednesday).

Job sequence (locked by the Constitution's pipeline requirements):

    scrape -> ingest -> reconcile -> anomaly-check -> percentiles+index -> publish

Idempotency: re-running the weekly job for a date that already has data does
not duplicate rows —
- stat_snapshots use the natural key (player, team, league, season, source,
  scrape_date): existing rows are skipped, never overwritten;
- percentile rows are skipped when the winning snapshot already has rows for
  this computation run;
- data_coverage upserts.

The 'published' flag is the gate the query layer reads: nothing is queryable
until anomaly checks passed and the run is marked published.

TIER-COMPLETENESS GATE (closeout C1): percentile-rules.md §1.4 requires a
tier's percentiles to be withheld until EVERY league in that tier has been
ingested for the season (coverage matrix as arbiter). The gate is implemented
in compute.percentiles (require_tier_completeness=True) and wired through this
job: production weekly runs pass require_tier_completeness=True (the CLI does),
so a tier missing any league is withheld entirely. It defaults to False so the
documented single-league integration contract keeps working in tests/fixtures.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.compute.anomaly_check import (
    blocked_player_ids,
    check_snapshot_bounds,
    cross_source_spot_check,
)
from app.config import load_tiers
from app.models import DataCoverage, League, Player, StatSnapshot, Team
from app.reconciliation import Reconciler
from app.sources.market_data import FixtureMarketDataSource
from app.sources.transfermarkt import TransfermarktSource

logger = logging.getLogger(__name__)


@dataclass
class RefreshReport:
    season: str = ""
    snapshot_date: datetime | None = None
    leagues_scraped: list[str] = field(default_factory=list)
    records_ingested: int = 0
    snapshots_inserted: int = 0
    snapshots_existing: int = 0
    records_unmatched: int = 0
    anomalies_bounds: int = 0
    anomalies_cross_source: int = 0
    blocked_players: int = 0
    percentile_rows: int = 0
    index_rows: int = 0
    published_rows: int = 0
    skipped_incomplete_tiers: list[str] = field(default_factory=list)
    events_linked: int = 0
    events_unmatched: int = 0
    alerts_created: int = 0
    alerts_by_type: dict[str, int] = field(default_factory=dict)
    emerging_scores: int = 0
    archetype_assignments: int = 0
    archetype_outliers: int = 0
    archetype_churn: float = 0.0
    market_valuations_inserted: int = 0
    market_valuations_flagged: int = 0
    market_contracts_inserted: int = 0
    errors: list[str] = field(default_factory=list)

    def add(self, **kw: Any) -> None:
        for key, value in kw.items():
            if hasattr(self, key):
                setattr(self, key, getattr(self, key) + value)


# --------------------------------------------------------------------------
# Catalog & entity helpers
# --------------------------------------------------------------------------


def ensure_league_catalog(db: Session) -> None:
    """Upsert leagues from config/tiers.json (the single list of supported leagues)."""
    for slug, cfg in load_tiers()["leagues"].items():
        league = db.query(League).filter_by(slug=slug).first()
        if league is None:
            db.add(
                League(
                    slug=slug,
                    name=cfg["name"],
                    country=cfg["country"],
                    tier=cfg["tier"],
                    external_ids=cfg["external_ids"],
                )
            )
    db.commit()


def get_or_create_team(db: Session, name: str, league_id: int) -> Team:
    team = db.query(Team).filter_by(name=name, league_id=league_id).first()
    if team is None:
        team = Team(name=name, league_id=league_id, external_ids={})
        db.add(team)
        db.flush()
    return team


def resolve_player_for_record(
    db: Session, reconciler: Reconciler, record: Any, team: Team
) -> tuple[Player, bool]:
    """Resolve a record to its canonical player; create one when nothing matches.

    Matching is never fuzzy (reconciliation.py): external id -> alias -> exact
    normalized name/team/DOB. A record that matches nothing becomes a canonical
    player carrying its own stable external id; only records with NO external id
    and no match are queued as possible duplicates (never silently guessed).
    Position group is set from the record when the player has none (the
    documented Pos-code fallback mapping); position is never overwritten once set.
    """
    player = reconciler.match_existing(record)
    created = player is None
    if created:
        ext_ids = dict(record.external_ids or {})
        tm_id = ext_ids.get("transfermarkt")
        player = Player(
            canonical_name=record.player_name,
            position_group=getattr(record, "position_group", None),
            external_ids=ext_ids,
            transfermarkt_id=int(tm_id) if tm_id else None,
        )
        db.add(player)
        db.flush()
        reconciler.register_player(player)
        if not (record.external_ids or {}):
            reconciler.enqueue(
                record,
                note="new player created without a stable external id; verify identity",
            )
    else:
        reconciler.ensure_alias(player, record)

    if player.position_group is None and getattr(record, "position_group", None):
        player.position_group = record.position_group
    if player.current_team_id is None:
        player.current_team_id = team.id
    if getattr(record, "dob_year", None) and player.date_of_birth is None:
        try:
            # date_of_birth is a DATE column (no time-of-day) — build a date
            # object directly, never a timezone-naive datetime (timezone-policy.md).
            from datetime import date as date_cls

            player.date_of_birth = date_cls(int(record.dob_year), 1, 1)
        except (ValueError, TypeError):
            pass
    if getattr(record, "nation", None) and player.nationality is None:
        player.nationality = record.nation
    # Backfill transfermarkt_id from external_ids if missing
    if player.transfermarkt_id is None:
        tm_id = (player.external_ids or {}).get("transfermarkt")
        if tm_id:
            player.transfermarkt_id = int(tm_id)
    return player, created

