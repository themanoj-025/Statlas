import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api";

export const metadata: Metadata = {
  title: "Transfer Candidates — Statlas",
  description:
    "Multi-condition transfer candidate search combining market valuations, statistical performance, contract situations, and archetype matching.",
};

export default async function CandidatesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const sp = await searchParams;
  const templateId = sp.template;

  let templates, candidates;
  try {
    templates = await api.candidateTemplates();
    const template = templates.templates.find((t) => t.id === templateId);
    const filters = template?.filters ?? {};

    candidates = await api.transferCandidates({
      position_group: typeof filters.position_group === "string" ? filters.position_group : undefined,
      min_age: typeof filters.max_age === "number" ? undefined : undefined,
      max_age: typeof filters.max_age === "number" ? filters.max_age : undefined,
      min_minutes: 900,
      limit: 50,
    });
  } catch {
    templates = { templates: [] };
    candidates = { total: 0, candidates: [] };
  }

  const activeTemplate = templates.templates.find((t) => t.id === templateId);

  return (
    <div className="container page">
      <p className="kicker">Transfer Intelligence</p>
      <h1 className="page__title">
        {activeTemplate?.name ?? "Transfer Candidates"}
      </h1>
      <p className="page__lede">
        {activeTemplate?.rationale ??
          "Multi-condition search combining market valuations, statistical performance, contract situations, and archetype matching."}
      </p>

      {/* Template Selector */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "24px", flexWrap: "wrap" }}>
        {templates.templates.map((t) => (
          <Link
            key={t.id}
            href={`/transfers/candidates?template=${t.id}`}
            className={`button ${t.id === templateId ? "button--primary" : "button--secondary"}`}
          >
            {t.name}
          </Link>
        ))}
      </div>

      {/* Results */}
      {candidates.candidates.length === 0 ? (
        <div className="empty-state">
          <h2>No candidates found</h2>
          <p>
            No transfer candidates match the current search criteria. Try
            adjusting filters or selecting a different template.
          </p>
        </div>
      ) : (
        <>
          <div className="section-head">
            <h2>
              {candidates.total} candidate{candidates.total !== 1 ? "s" : ""} found
            </h2>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Player</th>
                <th>Club</th>
                <th>Age</th>
                <th>Pos</th>
                <th>Index</th>
                <th>Market Value</th>
                <th>Contract</th>
                <th>Availability</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {candidates.candidates.map((c) => (
                <tr key={c.player_id}>
                  <td>
                    <Link href={`/players/${c.player_id}`}>{c.name}</Link>
                  </td>
                  <td>{c.club ?? "—"}</td>
                  <td>{c.age ?? "—"}</td>
                  <td>{c.position_group}</td>
                  <td>{c.index_score.toFixed(0)}</td>
                  <td>
                    {c.market_value_eur != null
                      ? `€${(c.market_value_eur / 1e6).toFixed(1)}M`
                      : "—"}
                  </td>
                  <td>
                    <span
                      className="badge badge--sm"
                      style={{
                        fontSize: "0.75rem",
                        color:
                          c.contract_status === "expiring_next_season"
                            ? "var(--color-positive, #22c55e)"
                            : c.contract_status === "active"
                            ? "var(--color-text-secondary)"
                            : undefined,
                      }}
                    >
                      {c.contract_status_label}
                    </span>
                  </td>
                  <td>{c.availability_score}/100</td>
                  <td style={{ fontWeight: 600 }}>{c.composite_score.toFixed(0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {/* Column Legend */}
      <div style={{ marginTop: "24px", padding: "16px", border: "1px solid var(--color-border, #e5e7eb)", borderRadius: "8px" }}>
        <h3 style={{ margin: "0 0 8px" }}>Score Breakdown</h3>
        <p style={{ fontSize: "0.85rem", margin: 0 }}>
          <strong>Composite Score</strong> combines: statistical performance (50%),
          market value attractiveness (25%), and contract availability (25%).
          Higher scores indicate stronger transfer targets relative to their
          cost and availability.
        </p>
      </div>
    </div>
  );
}
