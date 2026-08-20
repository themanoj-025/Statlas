"use client";

import Link from "next/link";
import {
  AlertTriangle,
  ChevronDown,
  Download,
  FileJson,
  FileText,
  RefreshCw,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { ReportQuotaPayload, ReportSummary } from "@/lib/types";

/**
 * Report history (D3) — stored reports, not ephemeral exports. Each report is
 * clearly labelled with its data_snapshot_date (an old report compared to
 * current data is understood to be outdated) and offers a "regenerate with
 * current data" action rather than implying the stored report auto-updates.
 *
 * The viewer renders the structured sections with the design system and an
 * expandable evidence appendix — a skeptical user can inspect the sourcing
 * without downloading the PDF first.
 */
export function ReportsClient() {
  const { status } = useAuth();
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [quota, setQuota] = useState<ReportQuotaPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [busy, setBusy] = useState<{ id: number; action: string } | null>(null);
  const [notice, setNotice] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [reportsRes, quotaRes] = await Promise.all([api.reports(), api.reportQuota()]);
      setReports(reportsRes.reports);
      setQuota(quotaRes);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load your reports.");
    }
  }, []);

  useEffect(() => {
    if (status !== "signed-in") return;
    void load();
  }, [status, attempt, load]);

  if (status === "signed-out") {
    return (
      <div className="state-block" role="status">
        <p className="state-block__body">
          Sign in to generate and review scouting reports — every claim verified against real
          Statlas data.
        </p>
        <Link href="/login" className="button">
          Sign in
        </Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="state-block state-block--error" role="alert">
        <p className="state-block__body">{error}</p>
        <button type="button" className="button" onClick={() => setAttempt((a) => a + 1)}>
          Try again
        </button>
      </div>
    );
  }

  if (reports === null) {
    return (
      <div aria-label="Loading reports" role="status">
        <div className="skeleton skeleton--row" />
        <div className="skeleton skeleton--row" />
        <div className="skeleton skeleton--row" />
      </div>
    );
  }

  if (reports.length === 0) {
    return (
      <div className="state-block" role="status">
        <p className="state-block__title">No reports yet</p>
        <p className="state-block__body">
          Generate a report from a player profile or a shortlist entry — the pipeline gathers
          real data, narrates it, and verifies every claim before the report is finalised. Every
          generated report is stored here so you can revisit it later.
        </p>
        <Link href="/search" className="button button--secondary">
          Find a player to scout
        </Link>
      </div>
    );
  }

  return (
    <div>
      {quota && (
        <div className="reports-quota" role="status">
          <ShieldCheck size={14} aria-hidden="true" />
          <span>
            {quota.has_pro ? (
              <>
                {quota.remaining} of {quota.limit} report{quota.limit === 1 ? "" : "s"} remaining
                this period (resets {quota.reset})
              </>
            ) : (
              <>
                Reports are a Pro feature. <Link href="/pricing">See Pro</Link>
              </>
            )}
          </span>
        </div>
      )}

      {notice && (
        <div className={`reports-notice reports-notice--${notice.kind}`} role={notice.kind === "ok" ? "status" : "alert"}>
          {notice.text}
        </div>
      )}

      <ul className="reports-list">
        {reports.map((report) => (
          <li key={report.report_id} className="report-card">
            <div className="report-card__header">
              <button
                type="button"
                className="report-card__summary"
                aria-expanded={expanded === report.report_id}
                onClick={() => setExpanded(expanded === report.report_id ? null : report.report_id)}
              >
                <FileText size={16} aria-hidden="true" />
                <span className="report-card__title">
                  {report.player_name ?? `Player #${report.player_id}`}
                </span>
                <span className="report-card__meta">
                  data as of {formatDate(report.data_snapshot_date)} · {formatDate(report.created_at)}
                </span>
                {report.verification_status === "needs_review" && (
                  <span className="chip chip--warning">
                    <AlertTriangle size={11} aria-hidden="true" /> Needs review
                  </span>
                )}
                <ChevronDown
                  size={15}
                  aria-hidden="true"
                  className={`report-card__chevron ${expanded === report.report_id ? "report-card__chevron--open" : ""}`}
                />
              </button>

              <div className="report-card__actions">
                <button
                  type="button"
                  className="button button--sm button--secondary"
                  disabled={busy !== null}
                  onClick={() => void regenerate(report, setBusy, setNotice, load)}
                  title="Regenerate against current data"
                >
                  <RefreshCw size={12} aria-hidden="true" /> Regenerate
                </button>
                <button
                  type="button"
                  className="button button--sm button--secondary"
                  disabled={busy !== null || report.status === "needs_review"}
                  onClick={() => void downloadExport(report.report_id, "pdf", setBusy, setNotice)}
                  title={report.status === "needs_review" ? "Exports are disabled while a report needs review" : "Download PDF"}
                >
                  <Download size={12} aria-hidden="true" /> PDF
                </button>
                <button
                  type="button"
                  className="button button--sm button--secondary"
                  disabled={busy !== null || report.status === "needs_review"}
                  onClick={() => void downloadExport(report.report_id, "json", setBusy, setNotice)}
                >
                  <FileJson size={12} aria-hidden="true" /> JSON
                </button>
                <button
                  type="button"
                  className="button button--sm button--secondary"
                  disabled={busy !== null || report.status === "needs_review"}
                  onClick={() => void downloadExport(report.report_id, "csv", setBusy, setNotice)}
                >
                  CSV
                </button>
                <button
                  type="button"
                  className="button button--sm button--danger-ghost"
                  disabled={busy !== null}
                  onClick={() => void remove(report.report_id, setBusy, setNotice, load)}
                  title="Delete this report"
                >
                  <Trash2 size={12} aria-hidden="true" />
                </button>
              </div>
            </div>

            {expanded === report.report_id && (
              <ReportViewer report={report} />
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

async function regenerate(
  report: ReportSummary,
  setBusy: (b: { id: number; action: string } | null) => void,
  setNotice: (n: { kind: "ok" | "error"; text: string }) => void,
  load: () => Promise<void>
) {
  setBusy({ id: report.report_id, action: "regenerate" });
  setNotice({ kind: "ok", text: "" });
  try {
    await api.regenerateReport(report.report_id);
    setNotice({
      kind: "ok",
      text: `Regenerated ${report.player_name ?? "report"} against current data — a fresh report was created.`,
    });
    await load();
  } catch (err) {
    setNotice({ kind: "error", text: err instanceof ApiError ? err.message : "Could not regenerate." });
  } finally {
    setBusy(null);
  }
}

async function remove(
  reportId: number,
  setBusy: (b: { id: number; action: string } | null) => void,
  setNotice: (n: { kind: "ok" | "error"; text: string }) => void,
  load: () => Promise<void>
) {
  setBusy({ id: reportId, action: "delete" });
  try {
    await api.deleteReport(reportId);
    setNotice({ kind: "ok", text: "Report deleted." });
    await load();
  } catch (err) {
    setNotice({ kind: "error", text: err instanceof ApiError ? err.message : "Could not delete." });
  } finally {
    setBusy(null);
  }
}

async function downloadExport(
  reportId: number,
  format: "pdf" | "json" | "csv",
  setBusy: (b: { id: number; action: string } | null) => void,
  setNotice: (n: { kind: "ok" | "error"; text: string }) => void
) {
  setBusy({ id: reportId, action: `export-${format}` });
  setNotice({ kind: "ok", text: "" });
  try {
    const url = api.reportExportUrl(reportId, format);
    const res = await fetch(url, { credentials: "include", cache: "no-store" });
    if (!res.ok) {
      let detail = `API ${res.status}`;
      try {
        const body = await res.json();
        if (typeof body.detail === "string") detail = body.detail;
        else if (body.error?.message) detail = body.error.message;
      } catch {
        /* non-JSON */
      }
      throw new ApiError(res.status, detail);
    }
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = `statlas-report-${reportId}.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objectUrl);
    setNotice({
      kind: "ok",
      text: format === "pdf"
        ? "PDF exported — branded with the Statlas design system and the data-snapshot footer."
        : format === "json"
          ? "JSON exported — the full verified report object, evidence appendix included."
          : "CSV exported — statistical profile and comparable players (narrative sections are omitted by design).",
    });
  } catch (err) {
    setNotice({
      kind: "error",
      text: err instanceof ApiError && err.status === 409
        ? "Export disabled — this report contains a claim that failed verification and is held for review."
        : err instanceof ApiError ? err.message : "Could not export.",
    });
  } finally {
    setBusy(null);
  }
}

// ---------------------------------------------------------------------------
// Report viewer — the structured sections + expandable evidence appendix
// ---------------------------------------------------------------------------

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
