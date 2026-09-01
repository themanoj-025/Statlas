# ---------------------------------------------------------------------------
# Phase 3: multi-date snapshot history + event-map demo data
# ---------------------------------------------------------------------------
# Trend charts (Part A) read the versioned stat_snapshots table — a trend needs
# HISTORY. The seed therefore runs the REAL weekly pipeline once per scrape
# date (7 Wednesdays) instead of a single snapshot. Each date's records are the
# base records with a deterministic per-player, per-metric drift applied (some
# metrics trend up, some down — a readable demo line). Two demo cases are
# baked in and documented here:
#   - d000042 (synthetic PL full-back): missing from the 2026-07-22 scrape —
#     a deliberate gap the trend chart must break, not interpolate.
#   - d000099 (synthetic PL midfielder): moves Manchester City -> Liverpool
#     from the 2026-07-29 scrape — a real team_id change the trend annotates.

SNAPSHOT_DATES = [
    datetime(2026, 7, 1, 3, 0, 0, tzinfo=timezone.utc),
    datetime(2026, 7, 8, 3, 0, 0, tzinfo=timezone.utc),
    datetime(2026, 7, 15, 3, 0, 0, tzinfo=timezone.utc),
    datetime(2026, 7, 22, 3, 0, 0, tzinfo=timezone.utc),
    datetime(2026, 7, 29, 3, 0, 0, tzinfo=timezone.utc),
    datetime(2026, 8, 5, 3, 0, 0, tzinfo=timezone.utc),
    SNAPSHOT_DATE,
]

GAP_DEMO_EXTERNAL = "d000042"  # missing from the 2026-07-22 scrape (index 3)
GAP_DEMO_MISSED_INDEX = 3
TRANSFER_DEMO_EXTERNAL = "d000099"  # Man City -> Liverpool from index 4
TRANSFER_DEMO_INDEX = 4
TRANSFER_DEMO_TEAMS = ("Manchester City", "Liverpool")

# Demo event-map coverage (Part B): competition 12 (Premier League) with a
# labeled synthetic event set for Haaland + Salah. The whole dev DB is
# fixture-demo (banner + dataset_mode); these rows make the coverage-gated
# shot/pass map chain demonstrable end to end.
DEMO_STATSBOMB_IDENTIFIER = "statsbomb:12:2025"
DEMO_STATSBOMB_SEASON = "2025/2026"


class _BoundClamper:
    """Clamps drifted values to the registry's anomaly bounds (the anomaly
    check must stay green on every date — a clean seed flags nothing)."""

    def __init__(self) -> None:
        registry = load_registry()
        self.bounds = {
            mid: tuple(spec["bounds"]) for mid, spec in registry["metrics"].items()
        }

    def clamp(self, key: str, value: float) -> float:
        if key.startswith("_"):
            return max(1.0, value)
        bounds = self.bounds.get(key)
        if bounds:
            lo, hi = bounds
            return max(lo, min(hi, value))
        return max(0.0, value)


_CLAMPER = _BoundClamper()


def drift_record(
    record: RawPlayerStatRecord, rng: random.Random, progress: float
) -> RawPlayerStatRecord -> None:
    """Deterministic per-player, per-metric drift for one snapshot date.

    progress = (date_index / (n_dates - 1)) in [0, 1]. Each metric gets a fixed
    direction and magnitude drawn from a per-player seed, so the same player
    trends consistently across dates (readable demo lines) while staying inside
    the registry bounds (the anomaly gate stays clean). The same factor applies
    to the player's fbref AND understat records so Tier-1 cross-source
    tolerances are preserved.
    """
    identity = str(record.external_ids or record.player_name)
    seed = random.Random(f"{SEED}:{identity}")
    raw: dict[str, float] = {}
    for key, value in record.raw_stats.items():
        if not isinstance(value, (int, float)):
            raw[key] = value
            continue
        direction = 1.0 if seed.random() < 0.55 else -1.0
        magnitude = seed.uniform(0.04, 0.14)
        factor = 1.0 + direction * magnitude * progress
        raw[key] = round(_CLAMPER.clamp(key, value * factor), 4)
    return RawPlayerStatRecord(
        source=record.source,
        season=record.season,
        league_slug=record.league_slug,
        player_name=record.player_name,
        team_name=record.team_name,
        minutes_played=record.minutes_played,
        matches_played=record.matches_played,
        raw_stats=raw,
        position_group=record.position_group,
        external_ids=dict(record.external_ids or {}),
        dob_year=getattr(record, "dob_year", None),
        nation=getattr(record, "nation", None),
    )


def seed_statsbomb_demo_events(db, fbref_records: list[RawPlayerStatRecord]) -> None:
    """Synthetic (labeled fixture-demo) shot/pass events for two fixture
    players, backed by real data_coverage rows for the competition/season — the
    coverage-gated chain (Part B1) is what makes them renderable.
    """
    from app.models import DataCoverage, MatchEvent, Player

    rng = random.Random(SEED + 9000)

    # Coverage rows (the matrix arbiter) for the demo competition/season.
    row = (
        db.query(DataCoverage)
        .filter_by(source="statsbomb", source_identifier=DEMO_STATSBOMB_IDENTIFIER)
        .first()
    )
    if row is None:
        db.add(
            DataCoverage(
                source="statsbomb",
                source_identifier=DEMO_STATSBOMB_IDENTIFIER,
                seasons_available=[DEMO_STATSBOMB_SEASON],
                last_successful_scrape=SNAPSHOT_DATE,
                status="active",
            )
        )

    names = [r.player_name for r in fbref_records]
    players = db.query(Player).filter(Player.canonical_name.in_(names)).all()
    by_name = {p.canonical_name: p for p in players}
    targets = [
        p
        for p in by_name.values()
        if p.canonical_name in ("Erling Haaland", "Mohamed Salah")
    ]

    OUTCOME_SHAPES = ["Off Target"] * 4 + ["Saved"] * 3 + ["Blocked"] * 2 + ["Goal"]
    for player in targets:
        for match_index in (1, 2):
            match_id = f"demo-{player.id}-{match_index}"
            # Shots: attacking-half locations, xG-scaled, mixed outcomes.
            for _ in range(8):
                xg = round(rng.uniform(0.01, 0.45), 3)
                outcome = rng.choice(OUTCOME_SHAPES)
                if outcome == "Goal":
                    xg = round(max(xg, rng.uniform(0.15, 0.6)), 3)
                db.add(
                    MatchEvent(
                        match_id=match_id,
                        event_id=f"{match_id}-shot-{rng.randint(1000, 9999)}",
                        player_id=player.id,
                        event_type="Shot",
                        x_coordinate=round(rng.uniform(78, 118), 1),
                        y_coordinate=round(rng.uniform(6, 74), 1),
                        minute=round(rng.uniform(2, 92), 0),
                        outcome=outcome,
                        extra={
                            "player_name": player.canonical_name,
                            "xg": xg,
                            "body_part": rng.choice(
                                ["Right Foot", "Left Foot", "Head"]
                            ),
                            "technique": rng.choice(["Normal", "Volley", "Lob"]),
                        },
                        source_competition_id="12",
                        season=DEMO_STATSBOMB_SEASON,
                    )
                )
            # Passes: start/end coordinates, ~75% completed, some progressive.
            for _ in range(40):
                start_x, start_y = rng.uniform(30, 95), rng.uniform(8, 72)
                end_x = start_x + rng.uniform(-5, 22)
                end_y = rng.uniform(6, 74)
                completed = rng.random() < 0.75
                db.add(
                    MatchEvent(
                        match_id=match_id,
                        event_id=f"{match_id}-pass-{rng.randint(1000, 9999)}",
                        player_id=player.id,
                        event_type="Pass",
                        x_coordinate=round(start_x, 1),
                        y_coordinate=round(start_y, 1),
                        minute=round(rng.uniform(1, 93), 0),
                        outcome="Complete" if completed else "Incomplete",
                        extra={
                            "player_name": player.canonical_name,
                            "end_x": round(end_x, 1),
                            "end_y": round(end_y, 1),
                            "pass_type": rng.choice(["Pass", "Cross", "Through Ball"]),
                            "length": round(
                                abs(end_x - start_x) + abs(end_y - start_y), 1
                            ),
                        },
                        source_competition_id="12",
                        season=DEMO_STATSBOMB_SEASON,
                    )
                )
    db.commit()


def synthetic_leagues(
    per_league: int,
) -> tuple[list[RawPlayerStatRecord], list[RawPlayerStatRecord]] -> None:
    """Returns (fbref_records, understat_records).

    Covers every league in tiers.json. Premier League gets a full 20-club
    roster (the fixture only carries two clubs); Tier-1 leagues get understat
    overlays for every outfield player so the Tier-1 xG percentile uses ONE
    model (Understat) across the whole cohort — the methodology's xG model
    consistency rule.
    """
    rng = random.Random(SEED)
    gen = _DemoPlayerGen(rng)
    fbref_records: list[RawPlayerStatRecord] = []
    understat_records: list[RawPlayerStatRecord] = []
    used_names: set[str] = set()
    index = 0
    understat_counter = 900_000
    for league_slug in (
        ["premier-league"] + TIER_1_SYNTHETIC + TIER_2_SYNTHETIC + TIER_3_SYNTHETIC
    ):
        if league_slug == "premier-league":
            teams = PL_TEAMS
            count = 160
        else:
            teams = TEAMS_BY_LEAGUE[league_slug]
            count = per_league
        n_teams = len(teams)
        # balanced position distribution so every group has a realistic pool
        for i in range(count):
            group = POSITION_GROUPS[i % len(POSITION_GROUPS)]
            team = teams[(i * 7 + 3) % n_teams]
            index += 1
            record = gen.player(league_slug, team, group, index, used_names)
            fbref_records.append(record)
            if league_slug in ("premier-league", *TIER_1_SYNTHETIC):
                overlay = gen.understat_overlay(record, understat_counter)
                understat_counter += 1
                if overlay is not None:
                    understat_records.append(overlay)
    return fbref_records, understat_records


# ---------------------------------------------------------------------------
# Seed runner
# ---------------------------------------------------------------------------


class _FakeSource:
    def __init__(self, source_name: str, records: list[RawPlayerStatRecord]) -> Any:
        self.source_name = source_name
        self.records = records

    def fetch_league_stats(
        self, league_slug: str, season: str
    ) -> list[RawPlayerStatRecord] -> None:
        return [
            r
            for r in self.records
            if r.league_slug == league_slug and r.season == season
        ]

    def get_rate_limit_seconds(self) -> float:
        return 1.0


def build_base_records() -> tuple[list[RawPlayerStatRecord], list[RawPlayerStatRecord]]:
    """One season's base records (real parsers over fixtures + synthetic)."""
    fbref_records, understat_records = scrape_premier_league_from_fixtures()
    synthetic_fbref, synthetic_understat = synthetic_leagues(per_league=64)
    all_fbref = fbref_records + synthetic_fbref
    all_understat = list(understat_records) + list(synthetic_understat)

    # xG model rule: every Tier-1 outfield player needs an understat snapshot.
    # The fixture's own understat records cover Haaland/Salah; everyone else in
    # the fixture (e.g. De Bruyne) gets a labeled synthetic overlay so no Tier-1
    # xG percentile mixes models.
    rng = random.Random(SEED + 1)
    gen = _DemoPlayerGen(rng)
    covered = {(r.player_name.lower(), r.team_name.lower()) for r in understat_records}
    extra_overlays = []
    understat_counter = 950_000
    for record in fbref_records:
        if record.position_group == "GK":
            continue
        if (record.player_name.lower(), record.team_name.lower()) in covered:
            continue
        overlay = gen.understat_overlay(record, understat_counter)
        understat_counter += 1
        if overlay is not None:
            extra_overlays.append(overlay)
            covered.add((record.player_name.lower(), record.team_name.lower()))
    all_understat += extra_overlays
    return all_fbref, all_understat


def _apply_demo_cases(
    fbref: list[RawPlayerStatRecord],
    understat: list[RawPlayerStatRecord],
    date_index: int,
) -> tuple[list[RawPlayerStatRecord], list[RawPlayerStatRecord]]:
    """Apply the labeled demo gap/transfer cases for one scrape date.

    - Gap player: dropped entirely from the 2026-07-22 scrape (a missing
      snapshot the trend must break on, never interpolate).
    - Transfer player: team changes from the 2026-07-29 scrape onward (a real
      team_id change between consecutive snapshots — the trend annotation).
    """

    def _keep(records: list[RawPlayerStatRecord]) -> list[RawPlayerStatRecord]:
        # The gap demo player is dropped ONLY from the missed scrape date;
        # the transfer demo player stays present on every date (team changes).
        if date_index != GAP_DEMO_MISSED_INDEX:
            return records
        return [
            r
            for r in records
            if (r.external_ids or {}).get("fbref") != GAP_DEMO_EXTERNAL
        ]

    def _retarget(
        records: list[RawPlayerStatRecord], ext: str, team: str
    ) -> list[RawPlayerStatRecord]:
        return [
            RawPlayerStatRecord(
                source=r.source,
                season=r.season,
                league_slug=r.league_slug,
                player_name=r.player_name,
                team_name=(
                    team if (r.external_ids or {}).get("fbref") == ext else r.team_name
                ),
                minutes_played=r.minutes_played,
                matches_played=r.matches_played,
                raw_stats=dict(r.raw_stats),
                position_group=r.position_group,
                external_ids=dict(r.external_ids or {}),
                dob_year=getattr(r, "dob_year", None),
                nation=getattr(r, "nation", None),
            )
            for r in records
        ]

    fbref = _keep(fbref)
    understat = _keep(understat)
    if date_index >= TRANSFER_DEMO_INDEX:
        team = TRANSFER_DEMO_TEAMS[1]
        fbref = _retarget(fbref, TRANSFER_DEMO_EXTERNAL, team)
        understat = _retarget(understat, TRANSFER_DEMO_EXTERNAL, team)
    return fbref, understat


def main() -> int:
    if DEV_DB.exists():
        DEV_DB.unlink()
    (PROJECT_ROOT / "data").mkdir(exist_ok=True)

    create_schema()

    base_fbref, base_understat = build_base_records()

    with session_scope() as db:
        total_snapshots = 0
        for date_index, snapshot_date in enumerate(SNAPSHOT_DATES):
            rng = random.Random(SEED + date_index)
            progress = date_index / (len(SNAPSHOT_DATES) - 1)
            fbref = [drift_record(r, rng, progress) for r in base_fbref]
            understat = [drift_record(r, rng, progress) for r in base_understat]
            fbref, understat = _apply_demo_cases(fbref, understat, date_index)

            report = run_weekly_refresh(
                db,
                SEASON,
                snapshot_date=snapshot_date,
                fbref_source=_FakeSource("fbref", fbref),
                understat_source=_FakeSource("understat", understat),
            )
            total_snapshots += report.snapshots_inserted
            print(
                f"scrape {snapshot_date.date().isoformat()}: "
                f"+{report.snapshots_inserted} snapshots, "
                f"{report.percentile_rows} percentile rows, "
                f"{report.published_rows} published, errors={len(report.errors)}"
            )
            for err in report.errors:
                print(f"  ERROR: {err}")

        seed_statsbomb_demo_events(db, base_fbref)
        print("seeded demo event-map data (StatsBomb coverage + synthetic events)")

        print(
            f"=== seed complete: {total_snapshots} snapshots across {len(SNAPSHOT_DATES)} dates ==="
        )

        # Sanity checks against the query layer (what the UI will see).
        from app.models import League, Player, StatSnapshot

        players = db.query(Player).count()
        snaps = db.query(StatSnapshot).count()
        leagues = db.query(League).count()
        print(f"=== database === players={players} snapshots={snaps} leagues={leagues}")

        from app.queries.coverage_queries import get_data_coverage

        coverage = get_data_coverage(db)
        print(
            f"coverage rows: {[(c['source'], c['source_identifier']) for c in coverage]}"
        )

        # Honesty guard: a coverage row must be backed by at least one snapshot
        # for that (source, league) — never claim coverage the data doesn't hold.
        from app.models import DataCoverage
        from app.models import StatSnapshot as _SS

        pruned = 0
        for c in coverage:
            if c["source"] == "statsbomb":
                continue
            if c["league_id"] is None:
                continue
            backed = (
                db.query(_SS.id)
                .filter(_SS.source == c["source"], _SS.league_id == c["league_id"])
                .first()
                is not None
            )
            if not backed:
                db.query(DataCoverage).filter_by(
                    source=c["source"], source_identifier=c["source_identifier"]
                ).delete()
                pruned += 1
        if pruned:
            db.commit()
            print(f"pruned {pruned} unbacked coverage row(s)")
        coverage = get_data_coverage(db)

        # Export the coverage matrix (Constitution §3 machine-readable file).
        matrix_path = PROJECT_ROOT / "data" / "coverage_matrix.json"
        matrix_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "generated_from": "data_coverage table (Phase 1 implementation of the coverage matrix)",
                    "dataset_mode": "fixture-demo",
                    "rows": [
                        {
                            "source": c["source"],
                            "source_identifier": c["source_identifier"],
                            "seasons_available": c["seasons_available"],
                            "last_successful_scrape": (
                                c["last_successful_scrape"].isoformat()
                                if c["last_successful_scrape"]
                                else None
                            ),
                            "status": c["status"],
                        }
                        for c in coverage
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"wrote {matrix_path.relative_to(PROJECT_ROOT)}")

        # Show a couple of demo entry points so the UI can be checked quickly.
        from app.queries.player_queries import search_players

        for query in ("Haaland", "De Bruyne", "Salah"):
            hits = search_players(db, query, limit=3)
            print(f"search '{query}': {[(h['name'], h['club']) for h in hits]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
