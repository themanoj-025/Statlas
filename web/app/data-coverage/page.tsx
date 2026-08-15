import type { Metadata } from "next";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";

export const metadata: Metadata = {
  title: "Data coverage — what data Statlas actually holds",
  description:
    "The coverage matrix: which sources, leagues and seasons Statlas has ingested, with update status. The UI cannot claim coverage this page does not list.",
  alternates: { canonical: "/data-coverage" },
};

export default async function DataCoveragePage() {
  const coverage = await api.coverage();
  const active = coverage.rows.filter((r) => r.status === "active");
  const bySource = coverage.rows.reduce<Record<string, typeof coverage.rows>>((acc, row) => {
    (acc[row.source] ??= []).push(row);
    return acc;
  }, {});

  return (
    <div className="container page">
      <p className="kicker">Data</p>
      <h1 className="page__title">Data coverage</h1>
      <p className="page__lede">
        What data Statlas actually holds, as of {coverage.generated}. This page is the arbiter:
        every coverage claim anywhere on the site must match a row here (Constitution §3). If a
        source or competition is not listed, it is not in the product.
      </p>

      <div className="notice" role="note">
        <strong>Coverage honesty.</strong> Shot and pass maps render only for competitions in
        StatsBomb Open Data coverage; per-90 statistics exist only where FBref rows are listed.
        Batch data is labeled with its snapshot date — the word &ldquo;live&rdquo; applies only to
        the fixtures layer.
      </div>

      {active.length === 0 && (
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__title">No active coverage yet.</p>
          <p className="state-block__body">
            The weekly refresh (Wednesday 03:00 UTC) ingests sources and updates this matrix. A
            full data refresh must run before production launch.
          </p>
        </div>
      )}

      <div className="table-wrap">
        <table className="table table--sticky-first" aria-label="Data coverage matrix">
          <thead>
            <tr>
              <th scope="col">Source</th>
              <th scope="col">Identifier</th>
              <th scope="col">Seasons</th>
              <th scope="col">Last successful scrape</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {coverage.rows.map((row) => (
              <tr key={`${row.source}-${row.source_identifier}`}>
                <td>{row.source}</td>
                <td style={{ fontFamily: "var(--font-data)" }}>{row.source_identifier}</td>
                <td>{row.seasons_available.join(", ")}</td>
                <td className="num">{row.last_successful_scrape ? formatDate(row.last_successful_scrape) : "—"}</td>
                <td>
                  <span className={`chip ${row.status === "active" ? "chip--primary" : row.status === "stale" ? "chip--accent" : "chip--danger"}`}>
                    {row.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ marginTop: "var(--space-6)" }}>Source attribution</h2>
      <div className="prose">
        {Object.entries(coverage.attribution).map(([source, text]) => (
          <p key={source}>
            <strong>{source}:</strong> {text}
          </p>
        ))}
      </div>

      {bySource.statsbomb && (
        <div className="notice" style={{ marginTop: "var(--space-4)" }}>
          <strong>StatsBomb attribution is mandatory</strong> on every page rendering its data —
          rendered in the UI, enforced by review, not goodwill.
        </div>
      )}
    </div>
  );
}
