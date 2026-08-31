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
