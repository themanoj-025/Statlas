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
