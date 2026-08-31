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

