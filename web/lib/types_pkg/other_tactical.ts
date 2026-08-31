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
