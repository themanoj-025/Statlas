"""Weekly refresh data ingestion helpers."""

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
            except (OSError, ValueError, ConnectionError) as exc:
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
            except (OSError, ValueError, ConnectionError) as exc:
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
            db.query(ClusteringModel).filter_by(status="in_production").first()
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
    except (ValueError, TypeError, OSError) as exc:
        report.errors.append(f"archetype assignment: {exc}")
        logger.exception("archetype assignment failed")

    # --- 10. market data ingestion (Phase 15) ---------------------------------
    # Idempotent: valuations use (player_id, source, valuation_date) natural
    # key — re-running for the same date skips duplicates.
    try:
        from app.models import ContractStatus, MarketValuation

        # Collect all player IDs (and names) that have qualifying snapshots this run.
        # Names are needed by TransfermarktSource to build correct URL slugs.
        from app.models.player import Player

        qualifying_rows = (
            db.query(StatSnapshot.player_id, Player.canonical_name)
            .join(Player, Player.id == StatSnapshot.player_id)
            .filter(
                StatSnapshot.scrape_date == snapshot_date,
                StatSnapshot.minutes_played >= 900,
            )
            .distinct()
            .all()
        )
        qualifying_player_ids = [pid for (pid, _name) in qualifying_rows]
        qualifying_player_names = [name for (_pid, name) in qualifying_rows]

        if qualifying_player_ids:
            # Fetch and store market valuations (real Transfermarkt or fixture fallback)
            try:
                market_source = TransfermarktSource()
                logger.info("using real Transfermarkt source for market data")
            except (ImportError, OSError, ValueError):
                market_source = FixtureMarketDataSource(seed=42)
                logger.info("Transfermarkt unavailable, using fixture market data")
            valuation_records = market_source.fetch_valuations(
                qualifying_player_ids, as_of=snapshot_date,
                player_names=qualifying_player_names,
            )
            from app.compute.market_validation import validate_valuation

            val_inserted = 0
            val_flagged = 0
            for rec in valuation_records:
                # Validate before insertion (Constitution §3: reject implausible)
                mv = MarketValuation(
                    player_id=rec.player_id,
                    source=rec.source,
                    valuation_amount_eur=rec.valuation_amount_eur,
                    valuation_date=rec.valuation_date,
                    low_range=rec.low_range,
                    high_range=rec.high_range,
                    confidence_level=rec.confidence_level,
                    raw=rec.raw,
                )
                val_result = validate_valuation(mv, db)
                if not val_result.is_valid:
                    val_flagged += 1
                    for issue in val_result.issues:
                        report.errors.append(
                            f"market valuation player={rec.player_id}: {issue}"
                        )
                    if val_result.severity == "error":
                        continue  # Block error-severity records from publication
                existing = (
                    db.query(MarketValuation)
                    .filter_by(
                        player_id=rec.player_id,
                        source=rec.source,
                        valuation_date=rec.valuation_date,
                    )
                    .first()
                )
                if existing is not None:
                    continue
                db.add(mv)
                val_inserted += 1
            report.market_valuations_inserted = val_inserted
            report.market_valuations_flagged = val_flagged

            # Fetch and store contract statuses
            contract_records = market_source.fetch_contracts(
                qualifying_player_ids, as_of=snapshot_date,
                player_names=qualifying_player_names,
            )
            contracts_inserted = 0
            for rec in contract_records:
                existing = (
                    db.query(ContractStatus)
                    .filter_by(
                        player_id=rec.player_id,
                        source=rec.source,
                        snapshot_date=rec.snapshot_date,
                    )
                    .first()
                )
                if existing is not None:
                    continue
                db.add(
                    ContractStatus(
                        player_id=rec.player_id,
                        current_team_id=rec.current_team_id,
                        contract_end_date=rec.contract_end_date,
                        contract_value_per_year_eur=rec.contract_value_per_year_eur,
                        contract_status=rec.contract_status,
                        source=rec.source,
                        snapshot_date=rec.snapshot_date,
                        raw=rec.raw,
                    )
                )
                contracts_inserted += 1
            report.market_contracts_inserted = contracts_inserted

            report.leagues_scraped.append("market_data")
    except (OSError, ValueError, ImportError) as exc:
        report.errors.append(f"market data ingestion: {exc}")
        logger.exception("market data ingestion failed")

    # --- optional extra layers -----------------------------------------------
    if do_statsbomb and statsbomb_source is not None:
        for competition in statsbomb_competitions or []:
            try:
                statsbomb_source.sync_competition(db, competition)
            except (OSError, ValueError) as exc:
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
            except (OSError, ValueError) as exc:
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
