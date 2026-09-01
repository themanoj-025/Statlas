function ReportViewer({ report }: { report: ReportSummary }) {
  const doc = report.report;
  const s = doc.sections;
  const [appendixOpen, setAppendixOpen] = useState(false);

  if (doc.verification.status === "needs_review") {
    return (
      <div className="report-viewer">
        <div className="state-block state-block--error" role="alert">
          <p className="state-block__title">Held for review</p>
          <p className="state-block__body">
            This report contains a claim that could not be verified against Statlas data. It is
            held rather than silently shipped — regenerate it with current data to produce a
            verified report. Exports are disabled in this state.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="report-viewer">
      <p className="report-viewer__snapshot">
        Generated {formatDate(doc.generated_at)} · data snapshot{" "}
        <strong>{doc.data_snapshot_date}</strong> — this report reflects data as of that date, not
        real-time.
      </p>

      <section className="report-section">
        <h2 className="report-section__title">Overview</h2>
        <p className="report-section__body">{s.overview.text}</p>
      </section>

      <section className="report-section">
        <h2 className="report-section__title">Statistical profile</h2>
        <div className="table-wrap">
          <table className="table report-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Percentile</th>
              </tr>
            </thead>
            <tbody>
              {s.statistical_profile.metrics.map((m) => (
                <tr key={m.metric}>
                  <td>{m.metric_name}</td>
                  <td>{m.value === null ? "—" : formatNumber(m.value)}</td>
                  <td>{m.percentile === null ? "—" : `${formatNumber(m.percentile)}th`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {s.role_and_position.text && (
        <section className="report-section">
          <h2 className="report-section__title">Role and position</h2>
          <p className="report-section__body">{s.role_and_position.text}</p>
        </section>
      )}

      <section className="report-section">
        <h2 className="report-section__title">Strengths</h2>
        <ul className="report-list">
          {s.strengths.map((item, i) => (
            <li key={i}>
              <p className="report-list__point">{item.point}</p>
              <p className="report-list__sub">
                {item.percentile !== null ? `${formatNumber(item.percentile)}th percentile` : ""}
                {item.value !== null ? ` · ${formatNumber(item.value)} per 90` : ""}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section className="report-section">
        <h2 className="report-section__title">Weaknesses</h2>
        <ul className="report-list">
          {s.weaknesses.map((item, i) => (
            <li key={i}>
              <p className="report-list__point">{item.point}</p>
              <p className="report-list__sub">
                {item.percentile !== null ? `${formatNumber(item.percentile)}th percentile` : ""}
                {item.value !== null ? ` · ${formatNumber(item.value)} per 90` : ""}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section className="report-section">
        <h2 className="report-section__title">Comparable players</h2>
        {s.comparable_players.length === 0 ? (
          <p className="report-section__body">No comparable players with published data were found.</p>
        ) : (
          <ul className="report-list">
            {s.comparable_players.map((c) => (
              <li key={c.player_id}>
                <p className="report-list__point">
                  <Link href={`/players/${c.player_id}`} className="report-list__link">
                    {c.name ?? `Player #${c.player_id}`}
                  </Link>{" "}
                  — {formatPercent(c.similarity)} similar
                </p>
                {c.explanation?.matched_strengths?.length ? (
                  <p className="report-list__sub">
                    Matched:{" "}
                    {c.explanation.matched_strengths.slice(0, 3).map((m) => m.metric_name).join(", ")}
                  </p>
                ) : null}
                {c.explanation?.key_differences?.length ? (
                  <p className="report-list__sub">
                    Key differences:{" "}
                    {c.explanation.key_differences.slice(0, 3).map((m) => m.metric_name).join(", ")}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="report-section">
        <h2 className="report-section__title">Development trajectory</h2>
        <p className="report-section__body">{s.development_trajectory.trend_summary}</p>
      </section>

      <section className="report-section">
        <h2 className="report-section__title">Risk factors</h2>
        <ul className="report-list">
          {s.risk_factors.map((r, i) => (
            <li key={i}>
              <p className="report-list__point">{r.point}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="report-section">
        <h2 className="report-section__title">Recommendation</h2>
        <p className="report-section__body">{s.recommendation.text}</p>
        <p className="report-section__confidence">
          Confidence: <strong>{s.recommendation.confidence_level}</strong> —{" "}
          {s.recommendation.confidence_rationale}
        </p>
      </section>

      {s.workspace_context && (
        <section className="report-section report-section--workspace">
          <h2 className="report-section__title">Workspace context</h2>
          <p className="report-section__sub">{s.workspace_context.label}</p>
          <p className="report-section__body">
            Status: <strong>{s.workspace_context.shortlist_status}</strong>
            {s.workspace_context.priority ? ` · Priority: ${s.workspace_context.priority}` : ""}
            {s.workspace_context.tags.length ? ` · Tags: ${s.workspace_context.tags.join(", ")}` : ""}
          </p>
          {s.workspace_context.recent_notes.length ? (
            <ul className="report-list">
              {s.workspace_context.recent_notes.map((n, i) => (
                <li key={i}>
                  <p className="report-list__sub">
                    “{n.note_text}” <em>({formatDate(n.created_at)})</em>
                  </p>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      )}

      <section className="report-section">
        <button
          type="button"
          className="report-section__appendix-toggle"
          aria-expanded={appendixOpen}
          onClick={() => setAppendixOpen((v) => !v)}
        >
          <ChevronDown
            size={14}
            aria-hidden="true"
            className={appendixOpen ? "report-card__chevron--open" : ""}
          />
          Evidence appendix — every claim traced to its source ({doc.evidence_appendix.length})
        </button>
        {appendixOpen && (
          <div className="table-wrap">
            <table className="table report-table">
              <thead>
                <tr>
                  <th>Claim</th>
                  <th>Source call</th>
                  <th>Raw result</th>
                </tr>
              </thead>
              <tbody>
                {doc.evidence_appendix.map((item, i) => (
                  <tr key={i}>
                    <td>{item.claim}</td>
                    <td>
                      <code>{item.source_call}</code>
                    </td>
                    <td>
                      <code>{JSON.stringify(item.raw_result)}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function formatNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}
