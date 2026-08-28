export type DatasetInfo = {
  mode: string;
  note: string;
};

export type Axis = MetricMeta & {
  raw: number | null;
  pct: number | null;
  status: "qualified" | "below_floor" | "no_data" | "unranked_pool";
};

export type LimitsPayload = {
  plan: Plan;
  limits: Record<string, number | null>;
};

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
export type ConditionOperator =
  | "percentile_gte"
  | "percentile_lte"
  | "percentile_between"
  | "gte"
  | "lte"
  | "between"
  | "eq";

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

export type WatchesPayload = { watches: WatchItem[] };
export type WatchAlertsPayload = { alerts: WatchAlertItem[] };
export type WatchAlertDetail = WatchAlertItem;

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

export type DashboardSummary = {
  recent_activity: DashboardActivityItem[];
  workspace: DashboardWorkspace;
  trending_players: DashboardTrendingPlayer[];
  recommended_players: DashboardRecommendedPlayer[];
  saved_players: DashboardSavedPlayer[];
  transfer_opportunities: OpportunityCard[];
};

// ---------------------------------------------------------------------------
// Phase 14 — Player Archetypes (ML clustering)
// ---------------------------------------------------------------------------
// Constitution Addendum §1.2: Archetypes are patterns, not predictions.
// Every archetype output is labeled as a statistical pattern.

export type ArchetypeModel = {
  model_id: number;
  model_name: string;
  version: string;
  algorithm: string;
  n_clusters: number;
  silhouette_score: number | null;
  training_date: string | null;
  deployed_at: string | null;
  training_data_source: string;
};

export type ArchetypeDefinition = {
  cluster_id: number;
  name: string;
  description: string;
  player_count: number;
  distinguishing_features: {
    feature: string;
    cluster_value: number;
    global_value: number;
    difference: number;
  }[];
  example_players: {
    player_id: number;
    name: string;
  }[];
};

export type ArchetypeOverview = {
  model: ArchetypeModel | null;
  archetypes: ArchetypeDefinition[];
  total_players: number;
};

export type ArchetypeDetail = {
  model_id: number;
  cluster_id: number;
  archetype_name: string;
  archetype_description: string;
  total: number;
  limit: number;
  offset: number;
  players: ArchetypePlayer[];
};

export type ValuationComparison = {
  player_id: number;
  player_name: string;
  stat_value_score: number;
  stat_value_eur: number;
  market_value_eur: number;
  market_source: string;
  market_confidence: string;
  valuation_gap_eur: number;
  valuation_gap_pct: number;
  label: string;
  signal_strength: string;
  explanation: string;
  age_adjustment: number;
  stat_snapshot_date: string;
};

export type TransferCandidate = {
  player_id: number;
  name: string;
  age: number | null;
  position_group: string;
  club: string | null;
  league: string | null;
  league_slug: string | null;
  index_score: number;
  market_value_eur: number | null;
  market_source: string | null;
  market_confidence: string | null;
  contract_status: string;
  contract_status_label: string;
  years_remaining: number | null;
  availability_score: number;
  composite_score: number;
  minutes_played: number;
};

export type TransferCandidateResult = {
  total: number;
  limit: number;
  offset: number;
  candidates: TransferCandidate[];
};

export type CandidateTemplate = {
  id: string;
  name: string;
  rationale: string;
  filters: Record<string, unknown>;
};

export type OpportunityCard = {
  player_id: number;
  name: string;
  age: number | null;
  position_group: string;
  club: string | null;
  league: string | null;
  index_score: number;
  market_value_eur: number | null;
  stat_value_eur: number;
  upside_eur: number;
  upside_pct?: number;
  confidence?: string;
  opportunity_type: string;
  opportunity_summary: string;
  risk_factors: string[];
};

export type TransferRisk = {
  player_id: number;
  risk_tier: string;
  risk_score: number;
  risk_factors: string[];
  mitigation_factors: string[];
};

export type ValuationConfidence = {
  player_id: number;
  confidence_score: number;
  confidence_level: string;
  factors: Record<string, { score: number; detail: string }>;
};

export type PositionScarcityOpportunity = {
  player_id: number;
  name: string;
  age: number | null;
  position_group: string;
  club: string | null;
  league: string | null;
  index_score: number;
  market_value_eur: number | null;
  premium_factor: number;
  opportunity_type: string;
  opportunity_summary: string;
  risk_factors: string[];
};

// ---------------------------------------------------------------------------
// Phase 16 — Organizations / Multi-Tenant
// ---------------------------------------------------------------------------

export type OrgSummary = {
  org_id: number;
  name: string;
  slug: string;
  role: string;
  tier: string;
  joined_at: string | null;
};

export type OrgDetail = {
  org_id: number;
  name: string;
  slug: string;
  tier: string;
  owner_user_id: number;
  member_count: number;
  created_at: string | null;
  country: string | null;
};

export type OrgInviteResult = {
  invite_id: number;
  email: string;
  role: string;
  expires_at: string;
  raw_token: string;
};

export type OrgJoinResult = {
  org_id: number;
  role: string;
  joined_at: string | null;
};

export type OrgSettings = {
  org_id: number;
  data_retention_days: number;
  workspace_name: string | null;
  enable_audit_logging: boolean;
  allow_public_reporting: boolean;
  require_2fa: boolean;
};

export type AuditEntry = {
  id: number;
  action: string;
  performed_by: string;
  performed_by_user_id: number;
  target_user_id: number | null;
  resource_type: string | null;
  resource_id: number | null;
  detail: Record<string, unknown>;
  created_at: string | null;
};

export type TacticalStyle = {
  style: string;
  confidence: number;
  factors: string[];
  metrics: {
    total_passes: number;
    avg_pass_distance: number;
    avg_success_rate: number;
    avg_betweenness: number;
    width_score: number;
  };
};

export type TacticalAnomaly = {
  type: string;
  player_id: number;
  severity: string;
  detail: string;
};

export type ZoneDensities = Record<string, number>;

export type PressureMap = {
  match_id: string;
  type: string;
  total_actions: number;
  zone_densities: ZoneDensities;
};

export type PossessionMap = {
  match_id: string;
  type: string;
  total_actions: number;
  zone_densities: ZoneDensities;
};

export type FormationWindow = {
  minute_start: number;
  minute_end: number;
  formation: string;
  formation_tuple: [number, number, number];
  confidence: number;
};

export type FormationChange = {
  from_formation: string;
  to_formation: string;
  approximate_minute: number;
};

export type FormationResult = {
  match_id: string;
  formation: {
    formation: [number, number, number];
    formation_str: string;
    confidence: number;
    player_lines: Record<number, string>;
  };
  stability: {
    windows: FormationWindow[];
    changes: FormationChange[];
    stability_score: number;
    dominant_formation: string;
  };
};

export type FormationStability = {
  windows: FormationWindow[];
  changes: FormationChange[];
  stability_score: number;
  dominant_formation: string;
};

export type TacticalOverview = {
  match_id: string;
  attribution: string;
  passing_network: {
    nodes: PassNode[];
    edges: PassEdge[];
    total_passes: number;
  };
  style: TacticalStyle;
  anomalies: TacticalAnomaly[];
  pressure_map: PressureMap;
  possession_map: PossessionMap;
  formation: FormationResult;
  formation_stability: FormationStability;
};

// ---------------------------------------------------------------------------
// Phase 18 — Internal Usage Analytics
// ---------------------------------------------------------------------------

export type DauResult = {
  date: string;
  dau_total: number;
  dau_free: number;
  dau_pro: number;
};

export type MauResult = {
  month: string;
  mau_total: number;
  mau_free: number;
  mau_pro: number;
};

export type FeatureUsageResult = {
  date: string;
  feature_name: string;
  adoption_count: number;
  adoption_pct: number;
  avg_engagement_minutes: number;
  actions_count: number;
};

export type ConversionFunnel = {
  period: string;
  step_1_signups: number;
  step_2_created_shortlist: number;
  step_2_rate: number;
  step_3_upgrade_attempted: number;
  step_3_rate: number;
  step_4_subscribed: number;
  step_4_rate: number;
  overall_conversion: number;
};

export type RetentionCohort = {
  cohort_month: string;
  months_since_signup: number;
  cohort_size: number;
  retained_count: number;
  retention_pct: number;
};

export type ChurnResult = {
  month: string;
  pro_users_at_start: number;
  cancellations: number;
  churn_rate_pct: number;
  annualized_churn_pct: number;
};

export type ArpuResult = {
  month: string;
  pro_users: number;
  mrr_eur: number;
  arpu_eur: number;
  upgrades: number;
  cancellations: number;
  estimated_lifetime_months: number;
  estimated_ltv_eur: number;
};

export type ExecutiveDashboard = {
  last_updated: string;
  data_confidence: string;
  caveat: string;
  dau: DauResult;
  mau: MauResult;
  conversion: ConversionFunnel;
  churn: ChurnResult;
  arpu: ArpuResult;
  feature_usage: FeatureUsageResult[];
};

export type AnalyticsAlert = {
  id: number;
  alert_name: string;
  metric_name: string;
  threshold_type: string;
  threshold_value: number;
  actual_value: number;
  message: string;
  fired_at: string | null;
  acknowledged_at: string | null;
};

export type AnomalyResult = {
  metric_name: string;
  anomaly_detected: boolean;
  anomaly: {
    metric_name: string;
    current_avg: number;
    historical_mean: number;
    std_dev: number;
    z_score: number;
    sigma_threshold: number;
    window_weeks: number;
    message: string;
  } | null;
};
