"""Player-related API routes."""


# ---------------------------------------------------------------------------
# Leaderboards
# ---------------------------------------------------------------------------


@app.get("/api/v1/leaderboard", response_model=LeaderboardResponse)
def leaderboard(
    metric: str = Query("si_index"),
    season: str = CURRENT_SEASON,
    league: str | None = Query(
        None, description="league slug (omitting = whole tier/all)"
    ),
    tier: str | None = Query(None, description="tier_1|tier_2|tier_3"),
    position: str | None = Query(None, description="GK|CB|FB|DM|CM|AM|W|ST"),
    min_minutes: float | None = Query(None, ge=0),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    sort_by: str = Query("value"),
    sort_dir: str | None = Query(None),
) -> dict[str, Any]:
    from app.cache import get_cache
    from app.queries.leaderboard_queries import get_leaderboard_filtered

    if position is not None and position not in VALID_POSITIONS:
        raise HTTPException(
            status_code=400, detail=f"unknown position group '{position}'"
        )
    if tier is not None and tier not in {"tier_1", "tier_2", "tier_3"}:
        raise HTTPException(status_code=400, detail=f"unknown tier '{tier}'")
    if sort_by not in {"value", "minutes", "name", "club"}:
        raise HTTPException(status_code=400, detail=f"unknown sort_by '{sort_by}'")
    if sort_dir is not None and sort_dir.lower() not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail=f"sort_dir must be 'asc' or 'desc', got '{sort_dir}'")

    # Cache key: includes all query params that affect the result.
    # TTL 300s (5 min) — data refreshes weekly, short TTL keeps responses
    # fresh during rapid navigation while eliminating redundant DB hits.
    cache = get_cache()
    cache_key = (
        f"api:lb:{metric}:{season}:{league or '_'}:{tier or '_'}:"
        f"{position or '_'}:{min_minutes or '_'}:{page}:{limit}:"
        f"{sort_by}:{sort_dir or '_'}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        try:
            return _json.loads(cached)
        except (ValueError, TypeError, _json.JSONDecodeError):
            pass

    with session_scope() as db:
        result = get_leaderboard_filtered(
            db,
            metric=metric,
            season=season,
            league_slugs=[league] if league else None,
            tier=tier,
            position_group=position,
            min_minutes=min_minutes,
            limit=limit,
            offset=(page - 1) * limit,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    with suppress(Exception):
        cache.set(cache_key, _json.dumps(result, default=str), 300)
    return result


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------


@app.get("/api/v1/players/search", response_model=list[PlayerSearchResult])
def player_search(
    q: str = Query(..., min_length=1, max_length=64), limit: int = Query(8, ge=1, le=25)
) -> list[dict[str, Any]]:
    from app.queries.player_queries import search_players

    return _with_session(search_players, q, limit=limit)


@app.get("/api/v1/players/by-slug/{slug}", response_model=PlayerProfileResponse)
def player_by_slug(slug: str, request: Request) -> dict[str, Any]:
    from app.api.player_view import build_player_payload
    from app.cache import get_cache
    from app.queries.player_queries import resolve_player_slug

    # Cache: player profiles are read-heavy, change only on weekly refresh.
    # TTL 300s (5 min). Activity logging runs regardless of cache hit.
    cache = get_cache()
    cache_key = f"api:player:{slug}"
    cached = cache.get(cache_key)
    if cached is not None:
        try:
            payload = _json.loads(cached)
            # Activity logging still runs on cache hit (best-effort)
            _log_player_view(request, payload["player"]["player_id"])
            return payload
        except (ValueError, TypeError, _json.JSONDecodeError):
            pass

    with session_scope() as db:
        resolved = resolve_player_slug(db, slug)
        if resolved is None:
            raise HTTPException(
                status_code=404, detail=f"no player matches slug '{slug}'"
            )
        payload = build_player_payload(db, resolved["player_id"])
        if payload is None:
            raise HTTPException(status_code=404, detail="player has no profile data")
        payload["player"]["canonical_slug"] = resolved["canonical_slug"]
        payload["player"]["is_canonical"] = resolved["canonical"]

        # Phase 13: log view activity (deduplicated, best-effort)
        _log_player_view(request, resolved["player_id"])

    with suppress(Exception):
        cache.set(cache_key, _json.dumps(payload, default=str), 300)
    return payload


@app.get("/api/v1/players/{player_id}/similar", response_model=list[SimilarPlayerEntry])
def player_similar(player_id: int, limit: int = Query(5, ge=1, le=10)) -> list[dict[str, Any]]:
    from app.cache import get_cache
    from app.queries.player_queries import get_player_profile
    from app.queries.similar_players import get_similar_players

    # Cache: similar players depend on percentile data (weekly refresh).
    # TTL 300s (5 min) — same rationale as leaderboard.
    cache = get_cache()
    cache_key = f"api:similar:{player_id}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        try:
            return _json.loads(cached)
        except (ValueError, TypeError, _json.JSONDecodeError):
            pass

    with session_scope() as db:
        if get_player_profile(db, player_id) is None:
            raise HTTPException(status_code=404, detail=f"unknown player {player_id}")
        result = get_similar_players(db, player_id, limit=limit)
    with suppress(Exception):
        cache.set(cache_key, _json.dumps(result, default=str), 300)
    return result


# ---------------------------------------------------------------------------
# Phase 3 — trend / time-series (Part A)
# ---------------------------------------------------------------------------


@app.get("/api/v1/players/{player_id}/trend", response_model=TrendResponse)
def player_trend(
    player_id: int,
    metric: str = Query(...),
    window: int = Query(5, ge=1, le=50),
) -> dict[str, Any]:
    from app.queries.trend_queries import get_player_trend

    with session_scope() as db:
        trend = get_player_trend(db, player_id, metric, window=window)
        if trend is None:
            raise HTTPException(status_code=404, detail=f"unknown player {player_id}")
        return trend


# ---------------------------------------------------------------------------
# Phase 3 — shot / pass maps (Part B, coverage-gated)
# ---------------------------------------------------------------------------


@app.get("/api/v1/players/{player_id}/events")
def player_event_coverage(player_id: int) -> dict[str, Any]:
    from app.queries.event_queries import get_player_event_coverage

    return _with_session(get_player_event_coverage, player_id)


@app.get("/api/v1/players/{player_id}/events/matches")
def player_event_matches(
    player_id: int,
    competition: str | None = None,
    season: str | None = None,
) -> list[dict[str, Any]]:
    from app.queries.event_queries import get_player_event_matches

    return _with_session(
        get_player_event_matches, player_id, competition_id=competition, season=season
    )


@app.get("/api/v1/players/{player_id}/events/shots")
def player_event_shots(
    player_id: int,
    match: str | None = None,
    competition: str | None = None,
    season: str | None = None,
) -> list[dict[str, Any]]:
    from app.queries.event_queries import get_player_events

    return _with_session(
        get_player_events,
        player_id,
        event_type="Shot",
        match_id=match,
        competition_id=competition,
        season=season,
    )


@app.get("/api/v1/players/{player_id}/events/passes")
def player_event_passes(
    player_id: int,
    match: str | None = None,
    competition: str | None = None,
    season: str | None = None,
) -> list[dict[str, Any]]:
    from app.queries.event_queries import get_player_events

    return _with_session(
        get_player_events,
        player_id,
        event_type="Pass",
        match_id=match,
        competition_id=competition,
        season=season,
    )


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------


@app.get("/api/v1/clubs/{league_slug}/{team_slug}")
def team_profile(league_slug: str, team_slug: str, season: str | None = None) -> dict[str, Any]:
    from app.queries.team_queries import get_team_profile

    with session_scope() as db:
        payload = get_team_profile(
            db, league_slug=league_slug, team_slug=team_slug, season=season
        )
        if payload is None:
            raise HTTPException(
                status_code=404,
                detail=f"no team '{team_slug}' in league '{league_slug}'",
            )
        return payload


# ---------------------------------------------------------------------------
# Coverage / methodology / positions
# ---------------------------------------------------------------------------


@app.get("/api/v1/coverage", response_model=CoverageResponse)
def coverage(league_id: int | None = None) -> dict[str, Any]:
    from app.queries.coverage_queries import get_data_coverage
    from app.queries.event_queries import get_statsbomb_competitions

    with session_scope() as db:
        rows = get_data_coverage(db, league_id=league_id)
        return {
            "rows": rows,
            "statsbomb_competitions": get_statsbomb_competitions(db),
            "attribution": {
                "statsbomb": "Data by StatsBomb — open data (StatsBomb Public Data User Agreement; research use with attribution). Shot and pass maps render only for competitions in StatsBomb Open Data coverage.",
                "fbref": "Per-90 statistics from FBref (Sports Reference). Published as derived, normalized metrics only.",
                "understat": "xG/xA for the Big-5 from Understat (Tier 1 model).",
            },
            "generated": datetime.now(timezone.utc)
            .date()
            .isoformat(),  # UTC policy (timezone-policy.md)
        }


@app.get("/api/v1/positions", response_model=list[PositionEntry])
def positions() -> list[dict[str, Any]]:
    from app.cache import get_cache
    meta = public_meta()
    from app.queries.leaderboard_queries import get_qualifying_counts

    cache = get_cache()
    cache_key = f"api:positions:{CURRENT_SEASON}"
    cached = cache.get(cache_key)
    if cached is not None:
        try:
            return _json.loads(cached)
        except (ValueError, TypeError, _json.JSONDecodeError):
            pass

    with session_scope() as db:
        counts_by_group = get_qualifying_counts(
            db, metric=meta["index_metric_id"], season=CURRENT_SEASON,
        )
        out = []
        for group in meta["position_groups"]:
            out.append({**group, "qualifying_counts": counts_by_group.get(group["code"], {})})
        result = out
    with suppress(Exception):
        cache.set(cache_key, _json.dumps(result, default=str), ttl=300)
    return result


@app.get("/api/v1/methodology")
def methodology() -> dict[str, Any]:
    return public_meta()


# ---------------------------------------------------------------------------
# Prometheus metrics endpoint (Phase 19 — observability)
# ---------------------------------------------------------------------------


@app.get("/metrics")
def metrics() -> Any:
    """Prometheus-format metrics for production monitoring.

    Exposes request counts, durations (histogram), error counts, cache stats,
    and uptime. Designed to be scraped by Prometheus without any external
    dependencies (no prometheus_client library required).
    """
    from fastapi.responses import PlainTextResponse

    from app.metrics import get_metrics_collector

    return PlainTextResponse(
        content=get_metrics_collector().render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
