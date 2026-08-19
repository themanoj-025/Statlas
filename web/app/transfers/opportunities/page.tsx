import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api";
import type { OpportunityCard, PositionScarcityOpportunity } from "@/lib/types";

export const metadata: Metadata = {
  title: "Transfer Opportunities — Statlas",
  description:
    "Discover hidden gems, age opportunities, and position-scarcity transfers — transparent opportunity detection grounded in statistical analysis.",
};

type AnyOpportunity = OpportunityCard | PositionScarcityOpportunity;

function OpportunityTable({ title, opportunities }: { title: string; opportunities: AnyOpportunity[] }) {
  if (opportunities.length === 0) {
    return (
      <div className="empty-state">
        <p>No opportunities found matching current criteria.</p>
      </div>
    );
  }

  return (
    <>
      <div className="section-head">
        <h2>{title}</h2>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Player</th>
            <th>Club</th>
            <th>Age</th>
            <th>Pos</th>
            <th>Index</th>
            <th>Market</th>
            <th>Upside</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {opportunities.map((opp) => (
            <tr key={opp.player_id}>
              <td>
                <Link href={`/players/${opp.player_id}`}>{opp.name}</Link>
              </td>
              <td>{opp.club ?? "—"}</td>
              <td>{opp.age ?? "—"}</td>
              <td>{opp.position_group}</td>
              <td>{opp.index_score.toFixed(0)}</td>
              <td>
                {opp.market_value_eur != null
                  ? `€${(opp.market_value_eur / 1e6).toFixed(1)}M`
                  : "—"}
              </td>
              <td style={{ color: "var(--color-positive, #22c55e)" }}>
                {"upside_eur" in opp && opp.upside_eur > 0
                  ? `+€${(opp.upside_eur / 1e6).toFixed(1)}M`
                  : "—"}
              </td>
              <td>
                <span className="badge badge--sm" style={{ fontSize: "0.75rem" }}>
                  {opp.risk_factors.length > 0 ? "See details" : "Low"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: "16px" }}>
        {opportunities.slice(0, 5).map((opp) => (
          <div
            key={opp.player_id}
            style={{
              padding: "12px 16px",
              border: "1px solid var(--color-border, #e5e7eb)",
              borderRadius: "8px",
              marginBottom: "8px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong>{opp.name}</strong>
              <span style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                {opp.club ?? "—"} · {opp.position_group}
              </span>
            </div>
            <p style={{ margin: "4px 0 0", fontSize: "0.9rem" }}>{opp.opportunity_summary}</p>
            {opp.risk_factors.length > 0 && (
              <p style={{ margin: "4px 0 0", fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>
                Risk: {opp.risk_factors.join(" · ")}
              </p>
            )}
          </div>
        ))}
      </div>
    </>
  );
}

export default async function OpportunitiesPage({
  searchParams,
}: {
  searchParams: Promise<{ type?: string }>;
}) {
  const params = await searchParams;
  const type = params.type ?? "hidden-gems";

  let hiddenGems, ageOpps, posOpps;
  try {
    [hiddenGems, ageOpps, posOpps] = await Promise.all([
      api.hiddenGems({ limit: 20 }),
      api.ageOpportunities({ limit: 20 }),
      api.positionScarcity({ limit: 20 }),
    ]);
  } catch {
    hiddenGems = { opportunities: [] };
    ageOpps = { opportunities: [] };
    posOpps = { opportunities: [] };
  }

  return (
    <div className="container page">
      <p className="kicker">Transfer Intelligence</p>
      <h1 className="page__title">Opportunity Finder</h1>
      <p className="page__lede">
        Discover market inefficiencies — players performing at high levels but
        not yet captured by major market valuations. Every opportunity is
        scored by upside potential with explicit risk factors.
      </p>

      {/* Type Tabs */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "24px", flexWrap: "wrap" }}>
        <Link
          href="/transfers/opportunities?type=hidden-gems"
          className={`button ${type === "hidden-gems" ? "button--primary" : "button--secondary"}`}
        >
          💎 Hidden Gems
        </Link>
        <Link
          href="/transfers/opportunities?type=age-opportunity"
          className={`button ${type === "age-opportunity" ? "button--primary" : "button--secondary"}`}
        >
          🌱 Age Opportunities
        </Link>
        <Link
          href="/transfers/opportunities?type=position-scarcity"
          className={`button ${type === "position-scarcity" ? "button--primary" : "button--secondary"}`}
        >
          🎯 Position Scarcity
        </Link>
      </div>

      {type === "hidden-gems" && (
        <OpportunityTable title="Hidden Gems" opportunities={hiddenGems.opportunities} />
      )}
      {type === "age-opportunity" && (
        <OpportunityTable title="Age Opportunities (U24)" opportunities={ageOpps.opportunities} />
      )}
      {type === "position-scarcity" && (
        <OpportunityTable title="Position Scarcity" opportunities={posOpps.opportunities} />
      )}

      <div className="section-head">
        <h2>Methodology</h2>
      </div>
      <div style={{ gridColumn: "1 / -1" }}>
        <p>
          <strong>Hidden Gems:</strong> Players with 75th+ percentile index
          score and market valuation below €30M. Upside = estimated
          stat-based value minus current market value.
        </p>
        <p style={{ marginTop: "8px" }}>
          <strong>Age Opportunities:</strong> Players under 24 with 75th+
          percentile scores but potentially undervalued due to limited sample
          size. Framed as "high-ceiling, uncertain" — not guaranteed.
        </p>
        <p style={{ marginTop: "8px" }}>
          <strong>Position Scarcity:</strong> Players in positions that
          command premium prices (wingers, creative midfielders, ball-playing
          CBs) who are performing at high levels.
        </p>
      </div>
    </div>
  );
}
