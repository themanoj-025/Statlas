"""Search validation helpers for structured queries."""




def validate_query_definition(query_definition: dict[str, Any]) -> dict[str, Any]:
    """Validate + normalize a query definition; raise InvalidQuery on any
    violation of the grammar (query-builder-scope.md §1–2)."""
    if not isinstance(query_definition, dict):
        raise InvalidQuery("A query definition must be a JSON object.")

    logic = query_definition.get("condition_logic", "AND")
    if logic != "AND":
        raise InvalidQuery(
            f"condition_logic '{logic}' is not supported — v1 queries are AND-only "
            "(OR/grouped logic is a documented future enhancement)."
        )

    # position_group: a single group or a list (normalized to a list).
    position_group = query_definition.get("position_group")
    position_groups: list[str] | None = None
    if position_group is not None:
        raw = position_group if isinstance(position_group, list) else [position_group]
        if not raw:
            raise InvalidQuery(
                "position_group must be a group code or a list of group codes."
            )
        bad = [g for g in raw if g not in VALID_POSITION_GROUPS]
        if bad:
            raise InvalidQuery(
                f"unknown position group(s): {', '.join(map(str, bad))} — "
                f"valid groups: {', '.join(sorted(VALID_POSITION_GROUPS))}."
            )
        position_groups = list(dict.fromkeys(raw))

    league_tier = query_definition.get("league_tier")
    if league_tier is not None and league_tier not in VALID_TIERS:
        raise InvalidQuery(
            f"unknown league_tier '{league_tier}' — valid values: "
            f"{', '.join(sorted(VALID_TIERS))} (or omit for all tiers)."
        )

    age_max = query_definition.get("age_max")
    if age_max is not None:
        if not isinstance(age_max, (int, float)) or not (15 <= float(age_max) <= 60):
            raise InvalidQuery("age_max must be a number between 15 and 60.")

    conditions_raw = query_definition.get("conditions", [])
    if not isinstance(conditions_raw, list) or not conditions_raw:
        raise InvalidQuery("A query needs at least one condition.")
    if len(conditions_raw) > MAX_CONDITIONS:
        raise InvalidQuery(
            f"A query supports at most {MAX_CONDITIONS} conditions (you have {len(conditions_raw)})."
        )

    registry = load_registry()
    metrics = registry["metrics"]

    conditions: list[dict[str, Any]] = []
    for i, cond in enumerate(conditions_raw):
        if not isinstance(cond, dict):
            raise InvalidQuery(f"condition #{i + 1} must be an object.")
        metric = cond.get("metric")
        operator = cond.get("operator")
        value = cond.get("value")
        value_max = cond.get("value_max")

        if not isinstance(metric, str) or (
            metric not in metrics and metric != MINUTES_METRIC
        ):
            raise InvalidQuery(
                f"condition #{i + 1}: unknown metric '{metric}' — metric ids must come "
                "from the Metric Registry."
            )
        if metric == MINUTES_METRIC and operator not in RAW_OPERATORS:
            raise InvalidQuery(
                f"condition #{i + 1}: minutes_played only supports raw operators "
                f"({', '.join(sorted(RAW_OPERATORS))})."
            )
        if metric in metrics:
            valid = PERCENTILE_OPERATORS | RAW_OPERATORS
            if operator not in valid:
                raise InvalidQuery(
                    f"condition #{i + 1}: operator '{operator}' is not valid for metric "
                    f"'{metric}' — use {', '.join(sorted(valid))}."
                )
        if not isinstance(value, (int, float)) or not _finite(value):
            raise InvalidQuery(f"condition #{i + 1}: value must be a finite number.")

        is_percentile = operator in PERCENTILE_OPERATORS
        if is_percentile and not (0 <= float(value) <= 100):
            raise InvalidQuery(
                f"condition #{i + 1}: percentile values must be between 0 and 100."
            )
        if operator == "between":
            if not isinstance(value_max, (int, float)) or not _finite(value_max):
                raise InvalidQuery(
                    f"condition #{i + 1}: between needs a numeric value_max."
                )
            if value_max <= value:
                raise InvalidQuery(
                    f"condition #{i + 1}: value_max must be greater than value."
                )
            if is_percentile and not (0 <= float(value_max) <= 100):
                raise InvalidQuery(
                    f"condition #{i + 1}: percentile value_max must be between 0 and 100."
                )

        conditions.append(
            {
                "metric": metric,
                "operator": operator,
                "value": value,
                "value_max": (
                    value_max if operator in ("between", "percentile_between") else None
                ),
            }
        )

    return {
        "position_group": position_groups,
        "league_tier": league_tier,
        "age_max": float(age_max) if age_max is not None else None,
        "conditions": conditions,
        "condition_logic": "AND",
    }


def _finite(value: Any) -> bool:
    try:
        return value == value and abs(value) != float("inf")
    except TypeError:
        return False


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _age_at(dob: date | None, ref: datetime) -> int | None:
    """Full years between date of birth and the reference snapshot date."""
    if dob is None or ref is None:
        return None
    return ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))


def _team_name(db: Session, team_id: int | None) -> str | None:
    if team_id is None:
        return None
    team = db.get(Team, team_id)
    return team.name if team else None


def _eval_condition(cond: dict[str, Any], value: Any) -> bool:
    """Evaluate one condition against an actual value. A missing value (None)
    never passes — exclusion by design (query-builder-scope.md §3.2)."""
    if value is None:
        return False
    operator = cond["operator"]
    threshold = cond["value"]
    if operator == "percentile_gte" or operator == "gte":
        return value >= threshold
    if operator == "percentile_lte" or operator == "lte":
        return value <= threshold
    if operator == "eq":
        return value == threshold
    if operator == "between" or operator == "percentile_between":
        return cond["value_max"] >= value >= threshold
    return False


def execute_structured_query(
    db: Session,
    query_definition: dict[str, Any],
    *,
    user_id: int | None = None,
    log_history: bool = True,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "index",
    sort_dir: str | None = None,
    season: str | None = None,
) -> dict[str, Any]:
    """Execute a structured query against the published population.

    Returns a paginated result set where every entry carries the actual values
    behind each condition (`condition_values`) — the "why each result matched"
    transparency requirement (Part B1).
    """
    qd = validate_query_definition(query_definition)
    registry = load_registry()
    qualifying_minutes = registry["qualifying_minutes"]
    index_id = registry["index_metric_id"]
    metrics = registry["metrics"]

    # The current data set: latest season, latest snapshot date in it.
    if season is None:
        season = db.query(func.max(StatSnapshot.season)).scalar()
    if not season:
        raise InvalidQuery("No season data exists yet.")
    latest_date = (
        db.query(func.max(StatSnapshot.scrape_date))
        .filter(StatSnapshot.season == season)
        .scalar()
    )
    if latest_date is None:
        raise InvalidQuery(f"No snapshot data for season '{season}'.")

    # Metrics needed: the index row (defines the published population) +
    # every percentile-condition metric + the sort metric if it is a registry
    # metric not already covered.
    needed = {index_id}
    for cond in qd["conditions"]:
        if cond["operator"] in PERCENTILE_OPERATORS:
            needed.add(cond["metric"])
    if sort_by in metrics:
        needed.add(sort_by)

    rows = (
        db.query(PercentileSnapshot, StatSnapshot, Player, League)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .join(Player, StatSnapshot.player_id == Player.id)
        .join(League, StatSnapshot.league_id == League.id)
        .filter(
            PercentileSnapshot.is_published.is_(True),
            PercentileSnapshot.metric_name.in_(needed),
            StatSnapshot.scrape_date == latest_date,
            StatSnapshot.season == season,
        )
        .all()
    )

    # Assemble per-player data (at most one row per (player, metric) at the
    # latest date — the percentile unique key includes the snapshot).
    players: dict[int, dict[str, Any]] = {}
    for percentile, snap, player, league in rows:
        entry = players.setdefault(
            player.id,
            {
                "player_id": player.id,
                "name": player.canonical_name,
                "position_group": percentile.position_group,
                "club": _team_name(db, snap.team_id),
                "league": league.name,
                "league_slug": league.slug,
                "tier": league.tier,
                "minutes": snap.minutes_played,
                "matches": snap.matches_played,
                "age": _age_at(player.date_of_birth, snap.scrape_date),
                "dob_missing": player.date_of_birth is None,
                "raw_stats": snap.raw_stats or {},
                "snapshot_date": snap.scrape_date,
                "percentiles": {},
                "index": None,
            },
        )
        if percentile.metric_name == index_id:
            entry["index"] = percentile.index_score
        else:
            entry["percentiles"][percentile.metric_name] = percentile.percentile_value

    def _condition_actual(entry: dict[str, Any], cond: dict[str, Any]) -> Any:
        metric = cond["metric"]
        if metric == MINUTES_METRIC:
            return entry["minutes"]
        if cond["operator"] in PERCENTILE_OPERATORS:
            return entry["percentiles"].get(metric)
        return entry["raw_stats"].get(metric)

    # The always-applied qualification floor + scalar filters. Condition pass
    # counts are computed over this filtered population for diagnostics.
    candidates: list[dict[str, Any]] = []
    for entry in players.values():
        if entry["minutes"] < qualifying_minutes:
            continue
        if qd["position_group"] and entry["position_group"] not in qd["position_group"]:
            continue
        if qd["league_tier"] and entry["tier"] != qd["league_tier"]:
            continue
        if qd["age_max"] is not None:
            if entry["dob_missing"] or entry["age"] is None:
                continue  # cannot verify age -> excluded (missing data rule)
            if entry["age"] > qd["age_max"]:
                continue
        entry["condition_values"] = [
            {
                "metric": cond["metric"],
                "operator": cond["operator"],
                "value": cond["value"],
                "value_max": cond["value_max"],
                "actual": _condition_actual(entry, cond),
            }
            for cond in qd["conditions"]
        ]
        candidates.append(entry)

    # Per-condition individual pass counts (over the floor+scalar population)
    # — used for the "most restrictive condition" empty-result guidance.
    per_condition_counts = []
    for cond in qd["conditions"]:
        passing = sum(
            1
            for entry in candidates
            if _eval_condition(cond, _condition_actual(entry, cond))
        )
        per_condition_counts.append(
            {
                "metric": cond["metric"],
                "metric_name": metrics.get(cond["metric"], {}).get(
                    "name", cond["metric"]
                ),
                "operator": cond["operator"],
                "value": cond["value"],
                "value_max": cond["value_max"],
                "passing_count": passing,
            }
        )

    survivors = [
        entry
        for entry in candidates
        if all(
            _eval_condition(cond, entry["condition_values"][i]["actual"])
            for i, cond in enumerate(qd["conditions"])
        )
    ]

    # Sorting — direction-aware for registry metrics (mirrors leaderboard).
    if sort_by == "name":
        survivors.sort(
            key=lambda e: e["name"].lower(), reverse=(sort_dir or "asc") == "desc"
        )
    elif sort_by == "minutes":
        survivors.sort(
            key=lambda e: e["minutes"], reverse=(sort_dir or "desc") == "desc"
        )
    elif sort_by == "age":
        survivors.sort(
            key=lambda e: e["age"] or 0, reverse=(sort_dir or "desc") == "desc"
