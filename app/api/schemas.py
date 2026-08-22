"""Pydantic response models for the top 10 most-hit API endpoints.

Adding response_model to FastAPI endpoints provides:
1. Runtime validation — malformed responses raise 500 instead of leaking internals
2. Accurate OpenAPI docs — the docs page shows real response shapes
3. IDE autocomplete — callers know exactly what fields exist

Models are lenient where the backend may return varying shapes (Optional fields,
extra="allow" for dicts that carry dynamic keys).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail


# ---------------------------------------------------------------------------
# 1. GET /api/v1/leaderboard
# ---------------------------------------------------------------------------


class LeaderboardEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    player_id: int
    name: str
    slug: str | None = None
    position_group: str
    club: str | None = None
    league: str | None = None
    league_slug: str | None = None
    tier: str | None = None
    minutes: float
    matches: float | None = None
    value: float
    snapshot_date: datetime | None = None


class LeaderboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[LeaderboardEntry]
    total: int
    limit: int
    offset: int
    has_more: bool


# ---------------------------------------------------------------------------
# 2. GET /api/v1/players/by-slug/{slug}  (player profile)
# ---------------------------------------------------------------------------


class PlayerProfile(BaseModel):
    model_config = ConfigDict(extra="allow")

    player_id: int
    name: str
    slug: str | None = None
    club: str | None = None
    position_group: str | None = None
    position_label: str | None = None
    nationality: str | None = None
    date_of_birth: Any = None
    age: int | None = None
    photo: str | None = None


class PercentilesSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    snapshot_date: datetime | None = None
    computed_date: datetime | None = None
    index: float | None = None


class RawStatsSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    snapshot_date: datetime | None = None
    season: str | None = None
    source: str | None = None
    minutes_played: float
    matches_played: float
    league: str | None = None
    league_slug: str | None = None
    league_tier: str | None = None
    team: str | None = None


class RadarAxis(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    unit: str
    definition: str
    direction: str
    lower_is_better: bool
    raw: float | None = None
    pct: float | None = None
    status: str


class PlayerProfileResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    player: PlayerProfile
    percentiles: PercentilesSummary
    raw: RawStatsSummary
    axes: list[RadarAxis]
    sentence: str | None = None
    similar: list[Any] = []
    has_event_data: bool = False
    event_coverage: dict[str, Any] = {}
    qualifying_minutes: float = 0
    min_pool_size: int = 0


# ---------------------------------------------------------------------------
# 3. GET /api/v1/players/{player_id}/similar
# ---------------------------------------------------------------------------


class SimilarExplanationMatchedStrength(BaseModel):
    model_config = ConfigDict(extra="allow")

    metric: str
    metric_name: str
    player_a_percentile: float
    player_b_percentile: float
    difference: float
    contribution: float


class SimilarExplanationKeyDifference(BaseModel):
    model_config = ConfigDict(extra="allow")

    metric: str
    metric_name: str
    player_a_percentile: float
    player_b_percentile: float
    difference: float
    stronger_player: str


class SimilarExplanation(BaseModel):
    model_config = ConfigDict(extra="allow")

    matched_strengths: list[SimilarExplanationMatchedStrength] = []
    key_differences: list[SimilarExplanationKeyDifference] = []
    excluded_metrics: list[dict[str, Any]] = []
    excluded_reason: str = ""
    shared_metrics: int = 0


class SimilarPlayerEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    player_id: int
    name: str
    slug: str | None = None
    position_group: str
    club: str | None = None
    league: str | None = None
    similarity: float
    shared_metrics: int
    index: float | None = None
    anchor_index: float | None = None
    explanation: SimilarExplanation = SimilarExplanation()


# ---------------------------------------------------------------------------
# 4. GET /api/v1/players/search
# ---------------------------------------------------------------------------


class PlayerSearchResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    player_id: int
    name: str
    slug: str | None = None
    position_group: str
    position_label: str | None = None
    club: str | None = None
    league: str | None = None
    league_slug: str | None = None
    nationality: str | None = None


# ---------------------------------------------------------------------------
# 5. GET /api/v1/meta
# ---------------------------------------------------------------------------


class MetricMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    unit: str
    definition: str
    direction: str
    lower_is_better: bool
    null_vs_zero: str
    display_floor: dict[str, Any] | None = None
    kind: str = "per90"


class PositionGroupMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str
    label: str
    plural: str
    metric_ids: list[str]
    weights: dict[str, Any] = {}


class TierMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str
    label: str
    league_slugs: list[str]


class MetaResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    qualifying_minutes: float
    display_floor_minutes: float
    min_pool_size: int
    index_metric_id: str
    metrics: dict[str, MetricMeta]
    position_groups: list[PositionGroupMeta]
    tiers: list[TierMeta]
    weekly_refresh: str
    dataset: dict[str, Any] | None = None
    weekly_refresh_cadence: str | None = None
    index_definition: str | None = None


# ---------------------------------------------------------------------------
# 6. GET /api/v1/positions
# ---------------------------------------------------------------------------


class PositionEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str
    label: str
    plural: str
    metric_ids: list[str]
    weights: dict[str, Any] = {}
    qualifying_counts: dict[str, int] = {}


# ---------------------------------------------------------------------------
# 7. GET /api/v1/leagues
# ---------------------------------------------------------------------------


class LeagueEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    slug: str
    name: str
    country: str
    tier: str
    tier_label: str
    has_fbref_coverage: bool
    team_count: int
    seasons_available: list[str]
    sources: list[str]


# ---------------------------------------------------------------------------
# 8. GET /api/v1/health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    database: str
    redis: str
    api_version: str
    dataset_mode: str


# ---------------------------------------------------------------------------
# 9. GET /api/v1/players/{player_id}/trend
# ---------------------------------------------------------------------------


class TrendPoint(BaseModel):
    model_config = ConfigDict(extra="allow")

    date: str
    raw: float | None = None
    pct: float | None = None
    team_id: int | None = None
    team: str | None = None
    source: str | None = None
    minutes: float | None = None
    matches: float | None = None
    gap_after: bool = False
    anomaly: bool = False


class TrendGap(BaseModel):
    model_config = ConfigDict(extra="allow")

    from_date: str
    to_date: str
    missed_dates: list[str]


class TrendEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    date: str
    type: str
    team_from: str | None = None
    team_to: str | None = None


class TrendResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    player_id: int
    player_name: str
    metric: dict[str, Any]
    window: int
    granularity: str
    granularity_note: str
    min_snapshots: int
    available: int
    insufficient: bool
    league: str | None = None
    season: str | None = None
    points: list[TrendPoint]
    gaps: list[TrendGap] = []
    events: list[TrendEvent] = []


# ---------------------------------------------------------------------------
# 10. GET /api/v1/coverage
# ---------------------------------------------------------------------------


class CoverageRow(BaseModel):
    model_config = ConfigDict(extra="allow")

    league_id: int | None = None
    source: str
    source_identifier: str
    seasons_available: list[str]
    last_successful_scrape: datetime | None = None
    status: str


class StatsBombCompetition(BaseModel):
    model_config = ConfigDict(extra="allow")

    competition_id: str
    season_id: str
    competition_name: str
    seasons_available: list[str]
    last_successful_scrape: datetime | None = None
    status: str


class CoverageAttribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statsbomb: str
    fbref: str
    understat: str


class CoverageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[CoverageRow]
    statsbomb_competitions: list[StatsBombCompetition]
    attribution: CoverageAttribution
    generated: str
