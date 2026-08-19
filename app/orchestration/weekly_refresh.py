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
        player = Player(
            canonical_name=record.player_name,
            position_group=getattr(record, "position_group", None),
            external_ids=dict(record.external_ids or {}),
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
    return player, created


# --------------------------------------------------------------------------
# Ingestion
# --------------------------------------------------------------------------


def ingest_source_records(
    db: Session,
    records: Sequence[Any],
    *,
    snapshot_date: datetime,
    reconciler: Reconciler,
    report: RefreshReport,
) -> None:
    """Insert stat_snapshots idempotently; unresolved records go to the queue."""
    for record in records:
        league = db.query(League).filter_by(slug=record.league_slug).first()
        if league is None:
            report.errors.append(
                f"unknown league slug '{record.league_slug}' for {record.player_name}"
            )
            continue
        team = get_or_create_team(db, record.team_name, league.id)
        player, _created = resolve_player_for_record(db, reconciler, record, team)

        report.records_ingested += 1

        # Idempotency: natural key includes scrape_date + source.
        existing = (
            db.query(StatSnapshot)
            .filter_by(
                player_id=player.id,
                team_id=team.id,
                league_id=league.id,
                season=record.season,
                source=record.source,
                scrape_date=snapshot_date,
            )
            .first()
        )
        if existing is not None:
            report.snapshots_existing += 1
            continue

        db.add(
            StatSnapshot(
                player_id=player.id,
                team_id=team.id,
                league_id=league.id,
                season=record.season,
                scrape_date=snapshot_date,
                source=record.source,
                raw_stats=record.raw_stats,
                minutes_played=record.minutes_played,
                matches_played=record.matches_played,
                status="ingested",
            )
        )
        report.snapshots_inserted += 1
    db.commit()


def update_coverage(
    db: Session, *, source: str, identifier: str, season: str, now: datetime
) -> None:
    """Upsert a data_coverage row for a scraped source.

    For league-scoped sources (fbref/understat/api_football) the identifier is
    the league slug, so league_id is resolved here — the schema's
    ck_coverage_league_optional CHECK only permits NULL league_id for the
    statsbomb source (whose identifier is 'statsbomb:<comp>:<season>').
    """
    league = None
    if source != "statsbomb":
        league = db.query(League).filter_by(slug=identifier).first()
    row = (
        db.query(DataCoverage)
        .filter_by(source=source, source_identifier=identifier)
        .first()
    )
    if row is None:
        db.add(
            DataCoverage(
                league_id=league.id if league is not None else None,
                source=source,
                source_identifier=identifier,
                seasons_available=[season],
                last_successful_scrape=now,
                status="active",
            )
        )
    else:
        if league is not None and row.league_id is None:
            row.league_id = league.id
        seasons = list(row.seasons_available or [])
        if season not in seasons:
            seasons.append(season)
        row.seasons_available = seasons
        row.last_successful_scrape = now
        row.status = "active"
    db.commit()


def publish_run(db: Session, computed_date: datetime) -> int:
    """Mark this computation run's percentile rows as published (the gate the
    query layer reads). Only rows from THIS run are touched."""
    from app.models import PercentileSnapshot

    rows = (
        db.query(PercentileSnapshot)
        .filter(
            PercentileSnapshot.computed_date == computed_date,
            PercentileSnapshot.is_published.is_(False),
        )
        .all()
    )
    for row in rows:
        row.is_published = True
    db.commit()
    return len(rows)


# --------------------------------------------------------------------------
# The weekly job
# --------------------------------------------------------------------------


def run_weekly_refresh(
    db: Session,
    season: str,
    *,
    snapshot_date: datetime | None = None,
    league_slugs: list[str] | None = None,
    fbref_source: Any | None = None,
    understat_source: Any | None = None,
    statsbomb_source: Any | None = None,
    api_football_source: Any | None = None,
    statsbomb_competitions: list[dict[str, Any]] | None = None,
    do_statsbomb: bool = False,
    do_fixtures: bool = False,
    require_tier_completeness: bool = False,
) -> RefreshReport:
    """Run the full weekly refresh for a season.

    Sources are injectable (tests pass fixture-backed fakes; production passes
    the real sources from `sources.*`). The sequence is fixed — see module
    docstring.
    """
    snapshot_date = snapshot_date or datetime.now(timezone.utc)
    report = RefreshReport(season=season, snapshot_date=snapshot_date)
    tiers_cfg = load_tiers()

    ensure_league_catalog(db)

    target_slugs = league_slugs or list(tiers_cfg["leagues"].keys())

    # --- 1+2. scrape + ingest ---------------------------------------------
    reconciler = Reconciler(db)
    # statsbomb event ingestion does not need the stat reconciler; player_id on
    # match_events stays NULL until a player-link step runs (explicit, logged).
    for league_slug in target_slugs:
        league_cfg = tiers_cfg["leagues"][league_slug]
        errors_before = len(report.errors)

        if fbref_source is not None:
            try:
                records = fbref_source.fetch_league_stats(league_slug, season)
                ingest_source_records(
                    db,
                    records,
                    snapshot_date=snapshot_date,
                    reconciler=reconciler,
                    report=report,
                )
                update_coverage(
                    db,
                    source="fbref",
                    identifier=league_slug,
                    season=season,
                    now=snapshot_date,
                )
                report.leagues_scraped.append(f"{league_slug}:fbref")
            except Exception as exc:
                report.errors.append(f"fbref {league_slug}: {exc}")
                logger.exception("fbref scrape failed for %s", league_slug)

        # Understat only covers Tier 1 (Big-5) — the documented xG model rule.
        if understat_source is not None and league_cfg["tier"] == "tier_1":
            try:
                records = understat_source.fetch_league_stats(league_slug, season)
                ingest_source_records(
                    db,
                    records,
                    snapshot_date=snapshot_date,
                    reconciler=reconciler,
                    report=report,
                )
                update_coverage(
                    db,
                    source="understat",
                    identifier=league_slug,
                    season=season,
                    now=snapshot_date,
                )
                report.leagues_scraped.append(f"{league_slug}:understat")
            except Exception as exc:
                report.errors.append(f"understat {league_slug}: {exc}")
                logger.exception("understat scrape failed for %s", league_slug)

        if len(report.errors) > errors_before:
            logger.warning(
                "league %s finished with %d error(s)",
                league_slug,
                len(report.errors) - errors_before,
            )

    # --- 3. reconcile (unmatched records already queued by ingest) ----------
    db.commit()

    # --- 4. anomaly detection ----------------------------------------------
    report.anomalies_bounds = check_snapshot_bounds(db, snapshot_date=snapshot_date)
    report.anomalies_cross_source = cross_source_spot_check(
        db, snapshot_date=snapshot_date
    )
    blocked = blocked_player_ids(db, snapshot_date=snapshot_date)
    report.blocked_players = len(blocked)

    # --- 5. percentiles + index ---------------------------------------------
    from app.compute.percentiles import compute_percentiles

    run_computed_at = datetime.now(timezone.utc)  # one timestamp for this whole run
    pc_report = compute_percentiles(
        db,
        snapshot_date=snapshot_date,
        season=season,
        blocked_player_ids=blocked,
        now=run_computed_at,
        require_tier_completeness=require_tier_completeness,
    )
    report.percentile_rows = pc_report.percentile_rows
    report.index_rows = pc_report.index_rows
    report.skipped_incomplete_tiers = pc_report.skipped_incomplete_tiers

    # --- 6. publish ----------------------------------------------------------
    report.published_rows = publish_run(db, run_computed_at)

    # --- 7. watch-trigger detection (Phase 10) --------------------------------
    # After publish: compare the freshly-published snapshot against the
    # preceding one for every active watch and write qualifying watch_alerts.
    # Idempotent via dedupe keys + the unique constraint (detection.py).
    from app.watch.detection import detect_watch_triggers

    watch_report = detect_watch_triggers(db, snapshot_date)
    report.alerts_created = watch_report.alerts_created
    report.alerts_by_type = dict(watch_report.by_type)

    # --- 8. emerging player scores (Phase 11) --------------------------------
    # After publish: compute emerging-player scores for all leagues.
    # Idempotent: re-running for the same computed_date replaces rows.
    from app.compute.emerging import compute_emerging_scores

    emerging_count = compute_emerging_scores(
        db,
        snapshot_date=snapshot_date,
        season=season,
    )
    report.emerging_scores = emerging_count

    # --- 9. player clustering & archetypes (Phase 14) -------------------------
    # After publish: assign all qualifying players to archetypes.
    # Idempotent: re-running for the same snapshot_date replaces assignments.
    try:
        from app.compute.clustering import (
            assign_all_players,
            check_model_staleness,
        )
        from app.models import ClusteringModel

        active_model = (
            db.query(ClusteringModel)
            .filter_by(status="in_production")
            .first()
        )
        if active_model is not None:
            # Check staleness before assignment
            if not check_model_staleness(db, active_model.id):
                assignment_report = assign_all_players(
                    db,
                    snapshot_date=snapshot_date,
                    model_id=active_model.id,
                    season=season,
                )
                report.archetype_assignments = assignment_report.players_assigned
                report.archetype_outliers = assignment_report.players_outlier
                report.archetype_churn = assignment_report.churn_rate
            else:
                report.errors.append(
                    f"Clustering model {active_model.model_name} v{active_model.version} "
                    f"is stale — archetype assignment skipped"
                )
        else:
            logger.info("No active clustering model — archetype assignment skipped")
    except Exception as exc:
        report.errors.append(f"archetype assignment: {exc}")
        logger.exception("archetype assignment failed")

    # --- optional extra layers -----------------------------------------------
    if do_statsbomb and statsbomb_source is not None:
        for competition in statsbomb_competitions or []:
            try:
                statsbomb_source.sync_competition(db, competition)
            except Exception as exc:
                report.errors.append(
                    f"statsbomb {competition.get('competition_id')}: {exc}"
                )

        # Phase 3 — player-link step: resolve the NULL-player_id events to
        # canonical players by exact normalized name (ambiguous names stay
        # unmatched for review — never a silent best-guess join).
        from app.orchestration.event_link import link_match_events

        link_report = link_match_events(db)
        report.events_linked = link_report.linked
        report.events_unmatched = link_report.unmatched

    if do_fixtures and api_football_source is not None:
        for league_slug in target_slugs:
            try:
                fixtures = api_football_source.fetch_fixtures(league_slug, season)
                store_fixtures(db, fixtures)
            except Exception as exc:
                report.errors.append(f"api_football {league_slug}: {exc}")

    db.commit()
    return report


def store_fixtures(db: Session, fixtures: Sequence[Any]) -> int:
    """Idempotent storage of normalized fixtures (natural key: api_fixture_id)."""
    from app.models import Fixture

    inserted = 0
    for fx in fixtures:
        league = db.query(League).filter_by(slug=fx.league_slug).first()
        if league is None:
            continue
        if (
            db.query(Fixture).filter_by(api_fixture_id=fx.api_fixture_id).first()
            is not None
        ):
            continue
        db.add(
            Fixture(
                league_id=league.id,
                season=fx.season,
                api_fixture_id=fx.api_fixture_id,
                home_team_name=fx.home_team_name,
                away_team_name=fx.away_team_name,
                kickoff_utc=fx.kickoff_utc,
                status=fx.status,
                raw=fx.raw,
            )
        )
        inserted += 1
    db.commit()
    return inserted
