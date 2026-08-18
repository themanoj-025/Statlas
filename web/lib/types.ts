// Types mirroring the Statlas API (/api/v1) payloads.

export type DatasetInfo = {
  mode: string;
  note: string;
};

export type Meta = {
  qualifying_minutes: number;
  display_floor_minutes: number;
  min_pool_size: number;
  index_metric_id: string;
  metrics: Record<string, MetricMeta>;
  position_groups: PositionGroupMeta[];
  tiers: { code: string; label: string; league_slugs: string[] }[];
  weekly_refresh: string;
  weekly_refresh_cadence: string;
  dataset: DatasetInfo;
};

export type MetricMeta = {
  id: string;
  name: string;
  unit: string;
  definition: string;
  direction: string;
  lower_is_better: boolean;
  null_vs_zero: string;
  display_floor?: { type: string; value: number } | null;
  kind: string;
};

export type PositionGroupMeta = {
  code: string;
  label: string;
  plural: string;
  metric_ids: string[];
  weights: Record<string, number>;
  qualifying_counts?: Record<string, number>;
};

export type Axis = MetricMeta & {
  raw: number | null;
  pct: number | null;
  status: "qualified" | "below_floor" | "no_data" | "unranked_pool";
};

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

export type LeagueSummary = {
  slug: string;
  name: string;
  country: string;
  tier: string;
  tier_label: string;
  team_count: number;
  has_fbref_coverage: boolean;
  seasons_available: string[];
  sources: string[];
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

export type RosterEntry = {
  player_id: number;
  name: string;
  slug: string | null;
  position_group: string | null;
  position_label: string | null;
  nationality: string | null;
  minutes: number;
  matches: number;
  index: number | null;
  snapshot_date: string;
  season: string;
};

export type TeamPayload = {
  team_id: number;
  name: string;
  slug: string;
  league_id: number;
  league: string;
  league_slug: string;
  tier: string;
  logo_url: string | null;
  founded_year: number | null;
  roster: RosterEntry[];
  squad_radar: {
    snapshot_date: string | null;
    n_players: number;
    metrics: { id: string; avg_pct: number; n: number }[];
  } | null;
  roster_count: number;
  qualified_count: number;
};

export type LeagueStatsRow = {
  player_id: number;
  name: string;
  slug: string | null;
  position_group: string | null;
  club: string | null;
  minutes: number;
  matches: number;
  value: number | null;
  status: string;
  snapshot_date: string;
  season: string;
};

// ---------------------------------------------------------------------------
// Phase 3 — trends (Part A)
// ---------------------------------------------------------------------------

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

export type StatsBombCompetition = {
  competition_id: string;
  season_id: string;
  competition_name: string;
  seasons_available: string[];
  last_successful_scrape: string | null;
  status: string;
};

export type EventCompetition = {
  competition_id: string;
  competition_name: string;
  season: string;
  matches: number;
};

export type EventCoverage = {
  has_coverage: boolean;
  competitions: EventCompetition[];
};

export type EventMatch = {
  match_id: string;
  competition_id: string;
  competition_name: string;
  season: string;
};

export type ShotEvent = {
  event_id: string;
  match_id: string;
  minute: number | null;
  x: number | null;
  y: number | null;
  outcome: string | null;
  competition_id: string;
  competition_name: string;
  season: string | null;
  xg: number | null;
  body_part: string | null;
  technique: string | null;
};

export type PassEvent = {
  event_id: string;
  match_id: string;
  minute: number | null;
  x: number | null;
  y: number | null;
  outcome: string | null;
  competition_id: string;
  competition_name: string;
  season: string | null;
  end_x: number | null;
  end_y: number | null;
  pass_type: string | null;
  recipient: string | null;
  length: number | null;
  angle: number | null;
  progressive: boolean;
};

// --- Phase 4: accounts + billing -------------------------------------------

export type Plan = "free" | "pro" | "api_business";

export type MePayload = {
  user_id: number;
  email: string;
  plan: Plan;
  has_pro: boolean;
  display_name: string | null;
  email_verified_at: string | null;
  account_status: string;
  timezone: string | null;
  locale: string | null;
};

export type SubscriptionStatusPayload = {
  has_pro: boolean;
  plan: Plan;
  status: string | null;
  current_period_end: string | null;
  grace_period_end: string | null;
  billing_configured: boolean;
  portal_enabled: boolean;
};

export type LimitsPayload = {
  plan: Plan;
  limits: Record<string, number | null>;
};

export type CheckoutPayload = { url: string; session_id: string };
export type PortalPayload = { url: string };

// --- Phase 4: AI assistant (Part B) -----------------------------------------

export type ToolCall = {
  name: string;
  input: Record<string, unknown>;
  result: unknown;
};

export type AssistantQuota = {
  used: number;
  limit: number;
  reset: string;
  remaining: number;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  tool_calls?: ToolCall[];
};

export type ChatResponse = {
  reply: string;
  tool_calls: ToolCall[];
  quota: AssistantQuota;
  grounded: boolean;
};

// --- Phase 7: scouting workspace --------------------------------------------

export type EntryStatus =
  | "discovered"
  | "monitoring"
  | "scouted"
  | "shortlisted"
  | "reviewed"
  | "rejected"
  | "signed";

export type EntryPriority = "low" | "medium" | "high" | null;

export type ShortlistSummary = {
  shortlist_id: number;
  name: string;
  description: string | null;
  entry_count: number;
  status_breakdown: Record<EntryStatus, number>;
  created_at: string;
  updated_at: string;
};

export type WorkspaceOverview = {
  plan: Plan;
  has_pro: boolean;
  limits: Record<string, number | null>;
  shortlists: ShortlistSummary[];
};

export type EntryNote = {
  id: number;
  author_user_id: number;
  note_text: string;
  created_at: string;
};

export type StatusHistoryRow = {
  from_status: EntryStatus | null;
  to_status: EntryStatus;
  changed_by_user_id: number;
  changed_at: string;
  reason_note: string | null;
};

export type ShortlistEntryDetail = {
  entry_id: number;
  player_id: number;
  name: string;
  slug: string | null;
  position_group: string | null;
  position_label: string | null;
  club: string | null;
  league: string | null;
  index: number | null;
  snapshot_date: string | null;
  status: EntryStatus;
  priority: EntryPriority;
  added_at: string;
  updated_at: string;
  added_by_note: string | null;
  notes: EntryNote[];
  tags: string[];
  status_history: StatusHistoryRow[];
};

export type ShortlistDetail = WorkspaceOverview & {
  shortlist_id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  entries: ShortlistEntryDetail[];
  entry_count: number;
  status_breakdown: Record<EntryStatus, number>;
};

export type TagSuggestions = { tags: string[] };
export type ShortlistMemberships = { shortlist_ids: number[] };

// ---------------------------------------------------------------------------
// Phase 8 — structured search (saved searches, presets, history)
// ---------------------------------------------------------------------------
// Grammar documented in docs/product/query-builder-scope.md. Backend enforces
// AND-only logic, max 8 conditions, and the always-applied minutes floor.

export type ConditionOperator =
  | "percentile_gte"
  | "percentile_lte"
  | "percentile_between"
  | "gte"
  | "lte"
  | "between"
  | "eq";

export type SearchCondition = {
  metric: string;
  operator: ConditionOperator;
  value: number;
  value_max?: number | null;
};

export type QueryDefinition = {
  position_group?: string[] | null;
  league_tier?: string | null;
  age_max?: number | null;
  conditions: SearchCondition[];
  condition_logic: "AND";
};

export type ConditionValueShown = {
  metric: string;
  metric_name: string;
  operator: ConditionOperator;
  value: number;
  value_max: number | null;
  actual: number | null;
  condition_type: "percentile" | "raw";
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

export type ReportConfidence = {
  level: "high" | "medium" | "low";
  rationale: string;
  composite: number;
  factors: {
    sample_size: { level: string; score: number; minutes_played: number; qualifying_minutes: number };
    data_completeness: { level: string; score: number; metrics_present: number; metrics_expected: number };
    recency: { level: string; score: number; days: number };
  };
};

export type ReportSection = {
  overview: { text: string; source_calls: string[] };
  statistical_profile: {
    metrics: { metric: string; metric_name: string; value: number | null; percentile: number | null }[];
    source_calls: string[];
  };
  role_and_position: { text: string; source_calls: string[] };
  strengths: {
    point: string;
    supporting_metric: string;
    value: number | null;
    percentile: number | null;
    source_calls: string[];
  }[];
  weaknesses: {
    point: string;
    supporting_metric: string;
    value: number | null;
    percentile: number | null;
    source_calls: string[];
  }[];
  comparable_players: {
    player_id: number;
    name: string | null;
    club: string | null;
    similarity: number;
    explanation: SimilarityExplanation;
  }[];
  development_trajectory: { trend_summary: string; metric: string; source_calls: string[] };
  risk_factors: { point: string; basis: string }[];
  recommendation: {
    text: string;
    confidence_level: "high" | "medium" | "low";
    confidence_rationale: string;
  };
  workspace_context: {
    shortlist_status: EntryStatus;
    priority: EntryPriority;
    tags: string[];
    recent_notes: { note_text: string; created_at: string }[];
    label: string;
  } | null;
};

export type ReportEvidenceItem = {
  claim: string;
  source_call: string;
  raw_result: Record<string, unknown>;
};

export type ReportDocument = {
  player_id: number;
  generated_at: string;
  generated_by_user_id: number;
  data_snapshot_date: string;
  source: "player_profile" | "shortlist_entry";
  shortlist_entry_id: number | null;
  sections: ReportSection;
  confidence: ReportConfidence;
  evidence_appendix: ReportEvidenceItem[];
  verification: { status: "passed" | "needs_review"; log: { attempts: number; unverified: unknown[]; passed: boolean } };
};

export type ReportSummary = {
  report_id: number;
  player_id: number;
  shortlist_entry_id: number | null;
  status: "generated" | "needs_review";
  data_snapshot_date: string;
  created_at: string;
  player_name: string | null;
  verification_status: "passed" | "needs_review";
  report: ReportDocument;
};

export type ReportsPayload = { reports: ReportSummary[] };

export type ReportQuotaPayload = {
  used: number;
  limit: number;
  reset: string;
  remaining: number;
  plan: Plan;
  has_pro: boolean;
};

// ---------------------------------------------------------------------------
// Phase 10 — watchlist & alerts
// ---------------------------------------------------------------------------
// Trigger definitions documented in docs/product/alert-trigger-definitions.md.
// Every alert `detail` holds real snapshot values — checkable, never
// fabricated. Delivery respects preferences absolutely (docs/product/
// notification-delivery.md).

export type AlertType =
  | "percentile_movement"
  | "club_change"
  | "new_season_data"
  | "data_coverage_change";

export type DigestFrequency = "immediate" | "daily_digest" | "weekly_digest";

export type WatchItem = {
  watch_id: number;
  entity_type: "player" | "team";
  entity_id: number;
  entity_name: string;
  slug: string | null;
  league_slug?: string | null;
  followed_metrics: string[] | null;
  created_at: string;
  unread_alert_count: number;
  team?: string | null;
  position_group?: string | null;
  league?: string | null;
};

export type WatchAlertItem = {
  alert_id: number;
  watch_id: number;
  entity_type: "player" | "team";
  entity_id: number;
  entity_name: string;
  slug: string | null;
  league_slug?: string | null;
  alert_type: AlertType;
  triggered_at: string;
  detail: Record<string, unknown>;
  delivered_at: string | null;
  read_at: string | null;
  dismissed: boolean;
};

export type WatchPreferences = {
  email_enabled: boolean;
  alert_type_preferences: Record<AlertType, boolean>;
  digest_frequency: DigestFrequency;
  updated_at: string;
};

// ---------------------------------------------------------------------------
// Phase 11 — league hub / emerging players
// ---------------------------------------------------------------------------

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

export type LeagueCategoryEntry = {
  player_id: number;
  name: string;
  slug: string | null;
  position_group: string | null;
  club: string | null;
  value: number | null;
  minutes: number;
};

export type LeagueHubPayload = {
  slug: string;
  name: string;
  country: string;
  tier: string;
  tier_label: string;
  season: string;
  team_count: number;
  player_count: number;
  has_fbref_coverage: boolean;
  has_understat_coverage: boolean;
  has_statsbomb_coverage: boolean;
  standings_available: boolean;
  latest_snapshot_date: string | null;
  categories: {
    key: string;
    label: string;
    metric: string;
    metric_name: string;
    entries: LeagueCategoryEntry[];
  }[];
  emerging_players: EmergingPlayerEntry[];
  teams: {
    team_id: number;
    name: string;
    slug: string;
    logo_url: string | null;
  }[];
  coverage: { source: string; status: string; seasons_available: string[] }[];
};

export type WatchesPayload = { watches: WatchItem[] };
export type WatchAlertsPayload = { alerts: WatchAlertItem[] };
export type WatchAlertDetail = WatchAlertItem;

export type LeagueIndexEntry = {
  slug: string;
  name: string;
  country: string;
  tier: string;
  tier_label: string;
  team_count: number;
  has_fbref_coverage: boolean;
  seasons_available: string[];
};

// Human-readable labels for alert types + digest frequencies (single source
// in the frontend; backend enum codes stay stable).
export const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  percentile_movement: "Percentile movement",
  club_change: "Club change",
  new_season_data: "New season data",
  data_coverage_change: "Data coverage change",
};

export const DIGEST_FREQUENCY_LABELS: Record<DigestFrequency, string> = {
  immediate: "Immediately (per alert)",
  daily_digest: "Daily digest",
  weekly_digest: "Weekly digest",
};

export const EMERGING_SCORE_THRESHOLD = 0.50;

// Phase 13 — dashboard types
export type DashboardActivityItem = {
  entity_type: string;
  entity_id: number;
  action_type: string;
  performed_at: string;
  player_name?: string;
  team_name?: string | null;
  position_group?: string;
};

export type DashboardWorkspace = {
  shortlist_count: number;
  saved_search_count: number;
  report_count: number;
  watch_count: number;
  unread_alert_count: number;
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

export type DashboardSummary = {
  recent_activity: DashboardActivityItem[];
  workspace: DashboardWorkspace;
  trending_players: DashboardTrendingPlayer[];
  recommended_players: DashboardRecommendedPlayer[];
  saved_players: DashboardSavedPlayer[];
};
