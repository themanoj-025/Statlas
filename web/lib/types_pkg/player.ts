export type SimilarityExplanation = {
  matched_strengths: {
    metric: string;
    metric_name: string;
    player_a_percentile: number;
    player_b_percentile: number;
    difference: number;
    contribution: number;
  }[];
  key_differences: {
    metric: string;
    metric_name: string;
    player_a_percentile: number;
    player_b_percentile: number;
    difference: number;
    stronger_player: "player_a" | "player_b";
  }[];
  excluded_metrics: { metric: string; metric_name: string }[];
  excluded_reason: string;
  shared_metrics: number;
};

export type SimilarPlayer = {
  player_id: number;
  name: string;
  slug: string | null;
  position_group: string | null;
  club: string | null;
  league: string | null;
  similarity: number;
  shared_metrics: number;
  index: number | null;
  anchor_index: number | null;
  explanation: SimilarityExplanation;
};

export type PlayerPayload = {
  player: {
    player_id: number;
    name: string;
    slug: string | null;
    canonical_slug?: string;
    is_canonical?: boolean;
    club: string | null;
    position_group: string | null;
    position_label: string | null;
    nationality: string | null;
    date_of_birth: string | null;
    age: number | null;
    photo: string | null;
  };
  event_coverage: EventCoverage;
  percentiles: {
    snapshot_date: string | null;
    computed_date: string | null;
    index: number | null;
  };
  raw: {
    snapshot_date: string | null;
    season: string | null;
    source: string | null;
    minutes_played: number;
    matches_played: number;
    league: string | null;
    league_slug: string | null;
    league_tier: string | null;
    team: string | null;
  };
  axes: Axis[];
  sentence: string;
  similar: SimilarPlayer[];
  has_event_data: boolean;
  qualifying_minutes: number;
  min_pool_size: number;
};

export type LeaderboardEntry = {
  player_id: number;
  name: string;
  slug: string | null;
  position_group: string;
  club: string | null;
  league: string;
  league_slug: string;
  tier: string;
  minutes: number;
  matches: number;
  value: number;
  snapshot_date: string;
};

export type LeaderboardResponse = {
  entries: LeaderboardEntry[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
};

export type SearchResult = {
  player_id: number;
  name: string;
  slug: string | null;
  position_group: string | null;
  position_label: string | null;
  club: string | null;
  league: string | null;
  league_slug: string | null;
  nationality: string | null;
};

export type CoverageRow = {
  league_id: number | null;
  source: string;
  source_identifier: string;
  seasons_available: string[];
  last_successful_scrape: string | null;
  status: string;
};

export type CoveragePayload = {
  rows: CoverageRow[];
  statsbomb_competitions: StatsBombCompetition[];
  attribution: Record<string, string>;
  generated: string;
};

export type TrendPoint = {
  date: string;
  raw: number | null;
  pct: number | null;
  team_id: number | null;
  team: string | null;
  source: string;
  minutes: number;
  matches: number;
  gap_after: boolean;
  anomaly: boolean;
};

export type TrendGap = {
  from_date: string;
  to_date: string;
  missed_dates: string[];
};

export type TrendEvent = {
  date: string;
  type: "transfer";
  team_from: string | null;
  team_to: string | null;
};

export type TrendPayload = {
  player_id: number;
  player_name: string;
  metric: MetricMeta;
  window: number;
  granularity: "snapshot";
  granularity_note: string;
  min_snapshots: number;
  available: number;
  insufficient: boolean;
  league: string | null;
  season: string;
  points: TrendPoint[];
  gaps: TrendGap[];
  events: TrendEvent[];
};

// ---------------------------------------------------------------------------
// Phase 3 — shot / pass maps (Part B)
// ---------------------------------------------------------------------------

export type EventCoverage = {
  has_coverage: boolean;
  competitions: EventCompetition[];
};

export type SearchCondition = {
  metric: string;
  operator: ConditionOperator;
  value: number;
  value_max?: number | null;
};

export type SearchResultEntry = {
  player_id: number;
  name: string;
  slug: string | null;
  position_group: string | null;
  club: string | null;
  league: string | null;
  league_slug: string | null;
  tier: string | null;
  minutes: number;
  matches: number;
  age: number | null;
  index: number | null;
  snapshot_date: string;
  condition_values: ConditionValueShown[];
};

export type SearchResults = {
  query: QueryDefinition;
  season: string;
  snapshot_date: string;
  qualifying_minutes: number;
  note: string;
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  entries: SearchResultEntry[];
  diagnostics: {
    per_condition_counts: {
      metric: string;
      metric_name: string;
      operator: ConditionOperator;
      value: number;
      value_max: number | null;
      passing_count: number;
    }[];
    most_restrictive: {
      metric: string;
      metric_name: string;
      operator: ConditionOperator;
      value: number;
      value_max: number | null;
      passing_count: number;
    } | null;
  } | null;
};

export type SearchPreset = {
  id: string;
  name: string;
  rationale: string;
  query_definition: QueryDefinition;
};

export type SavedSearchSummary = {
  search_id: number;
  name: string;
  description: string | null;
  query_definition: QueryDefinition;
  condition_count: number;
  position_group: string[] | null;
  league_tier: string | null;
  age_max: number | null;
  created_at: string;
  updated_at: string;
  last_run_at: string | null;
};

export type SavedSearchesPayload = { searches: SavedSearchSummary[] };

export type SearchHistoryEntry = {
  history_id: number;
  query_definition: QueryDefinition;
  executed_at: string;
  result_count: number;
  summary: string;
};

export type SearchHistoryPayload = { entries: SearchHistoryEntry[] };

// ---------------------------------------------------------------------------
// Phase 9 — AI scouting reports
// ---------------------------------------------------------------------------
// Report structure documented in docs/product/scouting-reports.md. Every
// factual claim carries source_calls tracing to the verified context; the
// evidence appendix makes the whole report checkable.

export type EmergingPlayerEntry = {
  player_id: number;
  name: string;
  slug: string | null;
  position_group: string | null;
  team: string | null;
  score: number;
  trend_magnitude: number;
  trend_consistency: number;
  age_weight: number;
  sample_weight: number;
  snapshot_date: string;
};

export type DashboardTrendingPlayer = {
  player_id: number;
  player_name: string;
  team_name: string | null;
  position_group: string | null;
  avg_gain: number;
  explanation: string;
};

export type DashboardRecommendedPlayer = {
  player_id: number;
  player_name: string;
  team_name: string | null;
  position_group: string | null;
  avg_percentile: number;
  explanation: string;
};

export type DashboardSavedPlayer = {
  player_id: number;
  player_name: string;
  team_name: string | null;
  position_group: string | null;
  saved_at: string;
  category: string | null;
};

export type ArchetypePlayer = {
  player_id: number;
  name: string;
  position_group: string | null;
  club: string | null;
  league: string | null;
  league_slug: string | null;
  distance_to_center: number;
  typicality: number;
  top_distinguishing_features: {
    feature: string;
    player_value: number;
    archetype_average: number;
  }[];
  minutes_played: number | null;
};

export type PlayerArchetype = {
  player_id: number;
  model_version: string;
  cluster_id: number | null;
  archetype_name: string | null;
  archetype_description: string | null;
  distance_to_center: number | null;
  typicality: number | null;
  is_outlier: boolean | null;
  top_distinguishing_features: {
    feature: string;
    player_value: number;
    archetype_average: number;
  }[];
  computed_date: string | null;
  snapshot_date: string | null;
  note?: string;
};

// ---------------------------------------------------------------------------
// Phase 15 — Transfer Intelligence
// ---------------------------------------------------------------------------

export type ValuationGapPlayer = {
  player_id: number;
  name: string;
  position_group: string;
  club: string | null;
  league: string | null;
  stat_value_score: number;
  stat_value_eur: number;
  market_value_eur: number;
  market_source: string;
  valuation_gap_eur: number;
  valuation_gap_pct: number;
  age: number | null;
  signal_strength: string;
  note?: string;
};

