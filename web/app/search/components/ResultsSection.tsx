"use client";

import type { Meta, SearchResultEntry, SearchCondition, ConditionOperator, QueryDefinition } from "@/lib/types";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { AddToShortlist } from "@/components/AddToShortlist";
import { useAuth } from "@/components/AuthProvider";

function ResultsSection({
  results,
  sortBy,
  sortDir,
  onSort,
}: {
  results: SearchResults;
  sortBy: string;
  sortDir: "asc" | "desc";
  onSort: (by: string, dir: "asc" | "desc") => void;
}) {
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkMessage, setBulkMessage] = useState<string | null>(null);

  if (results.total === 0) {
    const most = results.diagnostics?.most_restrictive;
    return (
      <div className="state-block state-block--sunken" role="status">
        <p className="state-block__title">0 players match this query</p>
        {most && (
          <p className="state-block__body">
            The most restrictive condition is{" "}
            <strong>
              {most.metric_name} {most.operator === "percentile_gte" ? "≥" : most.operator === "percentile_lte" ? "≤" : ""}{" "}
              {most.value}
              {most.operator.startsWith("percentile") ? "th percentile" : ""}
            </strong>{" "}
            — only {most.passing_count} qualifying {most.passing_count === 1 ? "player passes" : "players pass"} it. Try
            lowering the threshold or removing that condition.
          </p>
        )}
        <p className="state-block__body">{results.note}</p>
      </div>
    );
  }

  return (
    <section className="card" aria-label="Search results">
      <div className="section-head">
        <h2 style={{ margin: 0 }}>
          Results <span className="field__hint">({results.total.toLocaleString()})</span>
        </h2>
        <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center", flexWrap: "wrap" }}>
          <select
            className="select select--sm"
            aria-label="Sort results"
            value={sortBy}
            onChange={(e) => onSort(e.target.value, sortDir)}
          >
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>
                Sort: {s.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="button button--sm button--secondary"
            onClick={() => onSort(sortBy, sortDir === "desc" ? "asc" : "desc")}
          >
            {sortDir === "desc" ? "High → low" : "Low → high"}
          </button>
          <div style={{ position: "relative" }}>
            <button type="button" className="button button--sm" aria-expanded={bulkOpen} onClick={() => setBulkOpen((v) => !v)}>
              <Plus size={13} aria-hidden="true" /> Add all to shortlist
            </button>
            {bulkOpen && <BulkAddPanel playerIds={results.entries.map((e) => e.player_id)} onClose={() => setBulkOpen(false)} onMessage={setBulkMessage} />}
          </div>
        </div>
      </div>

      {bulkMessage && (
        <p className="field__hint" role={bulkMessage.startsWith("Added") ? "status" : "alert"}>
          {bulkMessage}
        </p>
      )}

      <p className="field__hint">{results.note}</p>

      <div className="table-wrap">
        <table className="table" aria-label={`${results.total} matching players`}>
          <thead>
            <tr>
              <th scope="col">Player</th>
              <th scope="col">Pos</th>
              <th scope="col">Age</th>
              <th scope="col">Minutes</th>
              <th scope="col">Index</th>
              <th scope="col">Why they matched</th>
              <th scope="col">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {results.entries.map((entry) => (
              <ResultRow key={entry.player_id} entry={entry} />
            ))}
          </tbody>
        </table>
      </div>

      {results.has_more && (
        <p className="field__hint">
          Showing the first {results.entries.length} of {results.total.toLocaleString()} — the API is paginated
          (this view shows the top of the sort).
        </p>
      )}
    </section>
  );
}
