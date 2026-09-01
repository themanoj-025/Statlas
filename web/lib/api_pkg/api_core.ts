import type {
  AssistantQuota,
  ChatResponse,
  CheckoutPayload,
  CoveragePayload,
  DashboardSummary,
  EventCoverage,
  EventMatch,
  LeagueHubPayload,
  LeagueIndexEntry,
  LeaderboardResponse,
  LeagueStatsRow,
  LeagueSummary,
  LimitsPayload,
  MePayload,
  Meta,
  PassEvent,
  PlayerPayload,
  PortalPayload,
  PositionGroupMeta,
  ReportQuotaPayload,
  ReportsPayload,
  ReportSummary,
  SearchResult,
  ShotEvent,
  ShortlistDetail,
  ShortlistMemberships,
  SimilarPlayer,
  SubscriptionStatusPayload,
  SavedSearchesPayload,
  SearchHistoryPayload,
  SearchPreset,
  SearchResults,
  TagSuggestions,
  TeamPayload,
  TrendPayload,
  WatchAlertsPayload,
  WatchAlertDetail,
  WatchPreferences,
  WatchesPayload,
  WorkspaceOverview,
  ArchetypeOverview,
  ArchetypeDetail,
  PlayerArchetype,
  ValuationComparison,
  TransferCandidateResult,
  CandidateTemplate,
  OpportunityCard,
  TransferRisk,
  ValuationConfidence,
  ValuationGapPlayer,
  PositionScarcityOpportunity,
  OrgSummary,
  OrgDetail,
  OrgMember,
  OrgInviteResult,
  OrgJoinResult,
  OrgSettings,
  AuditEntry,
  Comment,
  PassingNetworkResult,
  PressureMap,
  PossessionMap,
  FormationResult,
  TacticalOverview,
  DauResult,
  MauResult,
  FeatureUsageResult,
  ConversionFunnel,
  RetentionCohort,
  ChurnResult,
  ArpuResult,
  ExecutiveDashboard,
  AnalyticsAlert,
  AnomalyResult,
} from "./types";

// Server components read the API at STATLAS_API_URL (no CORS involved);
// client components read NEXT_PUBLIC_STATLAS_API_URL (CORS configured on the
// API for localhost). Both default to the local FastAPI dev server.
const API_URL =
  typeof window === "undefined"
    ? (process.env.STATLAS_API_URL ?? "http://127.0.0.1:8000")
    : (process.env.NEXT_PUBLIC_STATLAS_API_URL ?? "http://127.0.0.1:8000");

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    // The API and web app are different origins (8000 vs 3000), so the
    // session cookie is only sent on credentialed requests — without this,
    // every signed-in GET (me, subscription, workspace…) silently 401s.
    credentials: "include",
    cache: "no-store",
    headers: { Accept: "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = `API ${res.status}`;
    try {
      const body = await res.json();
      // Support both legacy {detail} and new {error: {message}} envelopes
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.error?.message) detail = body.error.message;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const q = search.toString();
  return q ? `?${q}` : "";
}
