"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { TrendingUp, Shield, AlertTriangle } from "lucide-react";
import type {
  ValuationComparison,
  TransferRisk,
  ValuationConfidence,
} from "@/lib/types";
import { ApiError } from "@/lib/api";

// ---------------------------------------------------------------------------
// Transfer Intelligence section for player profile pages
// Shows valuation comparison, risk assessment, and confidence scoring.
// ---------------------------------------------------------------------------

type TransferData = {
  valuation: ValuationComparison | null;
  risk: TransferRisk | null;
  confidence: ValuationConfidence | null;
  loading: boolean;
  error: string | null;
};

function formatEur(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    return `€${(value / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `€${(value / 1_000).toFixed(0)}K`;
  }
  return `€${value.toFixed(0)}`;
}

function ConfidenceBadge({ level }: { level: string }) {
  const color =
    level === "high"
      ? "var(--color-positive, #22c55e)"
      : level === "medium"
      ? "var(--color-warning, #f59e0b)"
      : "var(--color-negative, #ef4444)";
  return (
    <span
      className="badge badge--sm"
      style={{ color, fontSize: "0.75rem", fontWeight: 600 }}
    >
      {level} confidence
    </span>
  );
}

function RiskBadge({ tier }: { tier: string }) {
  const color =
    tier === "low"
      ? "var(--color-positive, #22c55e)"
      : tier === "medium"
      ? "var(--color-warning, #f59e0b)"
      : "var(--color-negative, #ef4444)";
  return (
    <span
      className="badge badge--sm"
      style={{ color, fontSize: "0.75rem", fontWeight: 600 }}
    >
      {tier} risk
    </span>
  );
}

export function PlayerTransferSection({ playerId }: { playerId: number }) {
  const [data, setData] = useState<TransferData>({
    valuation: null,
    risk: null,
    confidence: null,
    loading: true,
    error: null,
  });
  const [attempt, setAttempt] = useState(0);

  const load = useCallback(async () => {
    setData((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const API_URL =
        process.env.NEXT_PUBLIC_STATLAS_API_URL ?? "http://127.0.0.1:8000";
      const [valRes, riskRes, confRes] = await Promise.allSettled([
        fetch(`${API_URL}/api/v1/transfers/valuation/${playerId}`, {
          credentials: "include",
          cache: "no-store",
        }).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API_URL}/api/v1/transfers/risk/${playerId}`, {
          credentials: "include",
          cache: "no-store",
        }).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API_URL}/api/v1/transfers/confidence/${playerId}`, {
          credentials: "include",
          cache: "no-store",
        }).then((r) => (r.ok ? r.json() : null)),
      ]);

      setData({
        valuation:
          valRes.status === "fulfilled" ? valRes.value : null,
        risk:
          riskRes.status === "fulfilled" ? riskRes.value : null,
        confidence:
          confRes.status === "fulfilled" ? confRes.value : null,
        loading: false,
        error: null,
      });
    } catch (err) {
      setData((prev) => ({
        ...prev,
        loading: false,
        error:
          err instanceof ApiError
            ? err.message
            : "Could not load transfer intelligence data.",
      }));
    }
  }, [playerId, attempt]);

  useEffect(() => {
    void load();
  }, [load]);

  if (data.loading) {
    return (
      <section className="dashboard__section" aria-label="Transfer intelligence" aria-busy="true">
        <h2 className="dashboard__section-title">
          <TrendingUp size={18} className="dashboard__icon" />
          Transfer Intelligence
        </h2>
        <div className="skeleton skeleton--text" style={{ height: 60, marginBottom: 8 }} />
        <div className="skeleton skeleton--text" style={{ height: 40 }} />
      </section>
    );
  }

  // If no data at all, don't render the section
  if (!data.valuation && !data.risk && !data.confidence) {
    return null;
  }

  return (
    <section className="dashboard__section" aria-label="Transfer intelligence">
      <h2 className="dashboard__section-title">
        <TrendingUp size={18} className="dashboard__icon" />
        Transfer Intelligence
      </h2>

      {data.error && (
        <p style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
          {data.error}
        </p>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
        {/* Valuation Comparison */}
        {data.valuation && (
          <div
            style={{
              padding: "16px",
              border: "1px solid var(--color-border, #e5e7eb)",
              borderRadius: "8px",
            }}
          >
            <h3 style={{ margin: "0 0 8px", fontSize: "0.95rem" }}>Valuation Comparison</h3>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
              <span style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
                Stat-based value
              </span>
              <span style={{ fontWeight: 600 }}>{formatEur(data.valuation.stat_value_eur)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
              <span style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
                Market value
              </span>
              <span style={{ fontWeight: 600 }}>
                {formatEur(data.valuation.market_value_eur)}
                <span style={{ fontSize: "0.75rem", marginLeft: "4px", color: "var(--color-text-secondary)" }}>
                  ({data.valuation.market_source})
                </span>
              </span>
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                borderTop: "1px solid var(--color-border, #e5e7eb)",
                paddingTop: "8px",
                marginTop: "4px",
              }}
            >
              <span style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
                Gap
              </span>
              <span
                style={{
                  fontWeight: 600,
                  color:
                    data.valuation.valuation_gap_eur > 0
                      ? "var(--color-positive, #22c55e)"
                      : "var(--color-negative, #ef4444)",
                }}
              >
                {data.valuation.valuation_gap_eur > 0 ? "+" : ""}
                {formatEur(data.valuation.valuation_gap_eur)} (
                {data.valuation.valuation_gap_pct > 0 ? "+" : ""}
                {data.valuation.valuation_gap_pct.toFixed(0)}%)
              </span>
            </div>
            <p style={{ margin: "8px 0 0", fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>
              {data.valuation.label === "potentially undervalued"
                ? "Potentially undervalued — stat-based value exceeds market estimate"
                : "Potentially overvalued — market estimate exceeds stat-based value"}
              {" · "}
              <ConfidenceBadge level={data.valuation.market_confidence} />
            </p>
          </div>
        )}

        {/* Risk Assessment */}
        {data.risk && (
          <div
            style={{
              padding: "16px",
              border: "1px solid var(--color-border, #e5e7eb)",
              borderRadius: "8px",
            }}
          >
            <h3 style={{ margin: "0 0 8px", fontSize: "0.95rem" }}>Transfer Risk</h3>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
              <RiskBadge tier={data.risk.risk_tier} />
              <span style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
                Score: {data.risk.risk_score}/100
              </span>
            </div>
            {data.risk.risk_factors.length > 0 && (
              <div style={{ marginBottom: "8px" }}>
                <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--color-negative, #ef4444)" }}>
                  Risk factors:
                </span>
                <ul style={{ margin: "4px 0 0", paddingLeft: "16px", fontSize: "0.8rem" }}>
                  {data.risk.risk_factors.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </div>
            )}
            {data.risk.mitigation_factors.length > 0 && (
              <div>
                <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--color-positive, #22c55e)" }}>
                  Mitigations:
                </span>
                <ul style={{ margin: "4px 0 0", paddingLeft: "16px", fontSize: "0.8rem" }}>
                  {data.risk.mitigation_factors.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Valuation Confidence */}
        {data.confidence && (
          <div
            style={{
              padding: "16px",
              border: "1px solid var(--color-border, #e5e7eb)",
              borderRadius: "8px",
            }}
          >
            <h3 style={{ margin: "0 0 8px", fontSize: "0.95rem" }}>Valuation Confidence</h3>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
              <ConfidenceBadge level={data.confidence.confidence_level} />
              <span style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
                Score: {data.confidence.confidence_score}/100
              </span>
            </div>
            <div style={{ fontSize: "0.8rem" }}>
              {Object.entries(data.confidence.factors).map(([key, factor]) => (
                <div key={key} style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                  <span style={{ color: "var(--color-text-secondary)" }}>
                    {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                  </span>
                  <span>{factor.score.toFixed(0)}/25 — {factor.detail}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <p style={{ marginTop: "12px", fontSize: "0.75rem", color: "var(--color-text-secondary)" }}>
        Transfer intelligence is based on transparent, deterministic valuation comparison.
        See the <Link href="/methodology">methodology page</Link> for full details.
        Market valuations attributed per source on each data point.
      </p>
    </section>
  );
}
