import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api";

export const metadata: Metadata = {
  title: "Transfer Intelligence — Statlas",
  description:
    "Discover transfer opportunities: undervalued players, hidden gems, contract bargains, and candidate discovery powered by transparent valuation analysis.",
  alternates: { canonical: "/transfers" },
};

export default async function TransfersPage() {
  let templates;
  let hiddenGems;
  try {
    [templates, hiddenGems] = await Promise.all([
      api.candidateTemplates(),
      api.hiddenGems({ limit: 6 }),
    ]);
  } catch {
    templates = { templates: [] };
    hiddenGems = { opportunities: [] };
  }

  return (
    <div className="container page">
      <p className="kicker">Transfer Intelligence</p>
      <h1 className="page__title">Transfer Intelligence</h1>
      <p className="page__lede">
        Transparent, data-driven transfer analysis. Every recommendation is
        grounded in verifiable statistical performance, market valuation
        comparisons, and documented methodology — no black-box scoring.
      </p>

      {/* Opportunity Type Cards */}
      <div className="section-head">
        <h2>Opportunity Types</h2>
      </div>
      <div className="grid">
        <Link href="/transfers/opportunities?type=hidden-gems" className="position-card grid__span-3">
          <span className="position-card__code">💎</span>
          <span className="position-card__name">Hidden Gems</span>
          <span className="position-card__meta">
            High performers with low market valuations — potential upside before
            the market catches up.
          </span>
        </Link>

        <Link href="/transfers/opportunities?type=age-opportunity" className="position-card grid__span-3">
          <span className="position-card__code">🌱</span>
          <span className="position-card__name">Age Opportunities</span>
          <span className="position-card__meta">
            Young players (U24) performing at elite levels but valued
            conservatively — high-ceiling prospects.
          </span>
        </Link>

        <Link href="/transfers/opportunities?type=position-scarcity" className="position-card grid__span-3">
          <span className="position-card__code">🎯</span>
          <span className="position-card__name">Position Scarcity</span>
          <span className="position-card__meta">
            Players in scarce position profiles (wingers, ball-playing CBs) who
            are undervalued relative to their profile premium.
          </span>
        </Link>
      </div>

      {/* Search Templates */}
      {templates.templates.length > 0 && (
        <>
          <div className="section-head">
            <h2>Quick Searches</h2>
          </div>
          <div className="grid">
            {templates.templates.map((t) => (
              <Link
                key={t.id}
                href={`/transfers/candidates?template=${t.id}`}
                className="position-card grid__span-3"
              >
                <span className="position-card__name">{t.name}</span>
                <span className="position-card__meta">{t.rationale}</span>
              </Link>
            ))}
          </div>
        </>
      )}

      {/* Top Hidden Gems Preview */}
      {hiddenGems.opportunities.length > 0 && (
        <>
          <div className="section-head">
            <h2>Top Hidden Gems</h2>
            <Link href="/transfers/opportunities?type=hidden-gems" style={{ marginLeft: "auto" }}>
              View all →
            </Link>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Player</th>
                <th>Club</th>
                <th>Age</th>
                <th>Position</th>
                <th>Index</th>
                <th>Market Value</th>
                <th>Stat Value</th>
                <th>Upside</th>
              </tr>
            </thead>
            <tbody>
              {hiddenGems.opportunities.map((opp) => (
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
                  <td>€{(opp.stat_value_eur / 1e6).toFixed(1)}M</td>
                  <td style={{ color: "var(--color-positive, #22c55e)" }}>
                    +€{(opp.upside_eur / 1e6).toFixed(1)}M
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {/* Methodology Note */}
      <div className="section-head">
        <h2>Methodology</h2>
      </div>
      <div style={{ gridColumn: "1 / -1" }}>
        <p>
          Transfer intelligence is built on transparent, deterministic
          valuation comparison — not ML black boxes. Every recommendation
          traces to specific factors:
        </p>
        <ul style={{ marginTop: "8px", paddingLeft: "24px" }}>
          <li>
            <strong>Statistical performance rank</strong> — percentile scores
            and Statlas Index compared against market valuation
          </li>
          <li>
            <strong>Age adjustment</strong> — documented age-value curves per
            position (young potential valued higher, veterans declining)
          </li>
          <li>
            <strong>Contract situation</strong> — availability scoring based
            on contract status and years remaining
          </li>
          <li>
            <strong>Risk assessment</strong> — league transition, position
            change, sample size, and archetype transferability
          </li>
        </ul>
        <p style={{ marginTop: "8px" }}>
          Market valuations are sourced from licensed third-party providers and
          attributed on every display. See the{" "}
          <Link href="/methodology">methodology page</Link> for full details.
        </p>
      </div>
    </div>
  );
}
