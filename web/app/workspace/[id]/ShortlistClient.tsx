"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronLeft, Plus, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { GenerateReport } from "@/components/GenerateReport";
import { api, ApiError } from "@/lib/api";
import { formatNumber, positionGroupLabel, relativeAndAbsolute } from "@/lib/format";
import type {
  EntryPriority,
  EntryStatus,
  ShortlistDetail,
  ShortlistEntryDetail,
} from "@/lib/types";
import { PRIORITY_CHIP_CLASS, STATUS_CHIP_CLASS, STATUS_LABELS, STATUS_ORDER } from "@/lib/workspace";
import { EntryRow, StatusControl, PriorityControl, TagControl, NoteControl } from './ShortlistComponents'
import { ShortlistSkeleton } from './ShortlistSkeleton'

export function ShortlistClient() {
  const { id } = useParams<{ id: string }>();
  const shortlistId = Number(id);
  const { status: authStatus } = useAuth();

  const [detail, setDetail] = useState<ShortlistDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [filter, setFilter] = useState<EntryStatus | "all">("all");

  const load = useCallback(async () => {
    setError(null);
    try {
      setDetail(await api.shortlistDetail(shortlistId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load this shortlist.");
    }
  }, [shortlistId]);

  useEffect(() => {
    void load();
  }, [load, attempt]);

  if (authStatus === "loading") return <ShortlistSkeleton />;

  if (authStatus === "signed-out") {
    return (
      <div className="state-block state-block--sunken" role="status">
        <p className="state-block__title">Sign in to view this shortlist</p>
        <p className="state-block__body">
          Shortlists are private to the account that created them.{" "}
          <Link href="/login">Sign in</Link> to continue.
        </p>
      </div>
    );
  }

  if (error && !detail) {
    return (
      <div className="state-block state-block--error" role="alert">
        <p className="state-block__title">We couldn&rsquo;t load this shortlist.</p>
        <p className="state-block__body">{error}</p>
        <div className="state-block__actions">
          <button type="button" className="button button--sm" onClick={() => setAttempt((a) => a + 1)}>
            Retry
          </button>
          <Link href="/workspace" className="button button--sm button--secondary">
            Back to workspace
          </Link>
        </div>
      </div>
    );
  }

  if (!detail) return <ShortlistSkeleton />;

  const entries = filter === "all" ? detail.entries : detail.entries.filter((e) => e.status === filter);
  const atEntryCap =
    detail.limits.shortlist_entries_max !== null &&
    detail.entry_count >= detail.limits.shortlist_entries_max;

  return (
    <div style={{ display: "grid", gap: "var(--space-4)" }}>
      <div>
        <Link href="/workspace" className="back-link">
          <ChevronLeft size={14} aria-hidden="true" /> All shortlists
        </Link>
        <h1 className="page__title" style={{ marginTop: "var(--space-1)" }}>
          {detail.name}
        </h1>
        {detail.description && <p className="page__lede">{detail.description}</p>}
        <p className="field__hint">
          {detail.entry_count} {detail.entry_count === 1 ? "player" : "players"}
          {atEntryCap
            ? ` — you've reached the free plan's limit of ${detail.limits.shortlist_entries_max} players per shortlist. ` +
              "Remove a player to free a slot, or upgrade to Pro for unlimited tracking."
            : ` · up to ${detail.limits.shortlist_entries_max ?? "unlimited"} players (${detail.plan} plan)`}
        </p>
        {error && (
          <div className="state-block state-block--error" role="alert">
            <p className="state-block__body">{error}</p>
            <div className="state-block__actions">
              <button type="button" className="button button--sm" onClick={() => void load()}>
                Retry
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="toolbar" role="group" aria-label="Filter by status">
        <button
          type="button"
          className={`button button--sm button--secondary ${filter === "all" ? "button--active" : ""}`}
          onClick={() => setFilter("all")}
        >
          All ({detail.entry_count})
        </button>
        {STATUS_ORDER.map((s) => (
          <button
            key={s}
            type="button"
            className={`button button--sm button--secondary ${filter === s ? "button--active" : ""}`}
            onClick={() => setFilter(s)}
          >
            {STATUS_LABELS[s]} ({detail.status_breakdown[s]})
          </button>
        ))}
      </div>

      {detail.entry_count === 0 ? (
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__title">This shortlist is empty</p>
          <p className="state-block__body">
            Add players from anywhere they appear: open a{" "}
            <Link href="/positions">leaderboard</Link>, a{" "}
            <Link href="/compare">comparison</Link>, or any{" "}
            <Link href="/players/erling-haaland">player page</Link> and hit{" "}
            <em>Add to shortlist</em>.
          </p>
        </div>
      ) : entries.length === 0 ? (
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__body">
            No players in the {STATUS_LABELS[filter as EntryStatus]} stage right now.
          </p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="table" aria-label={`${detail.name} — ${entries.length} players`}>
            <thead>
              <tr>
                <th scope="col">Player</th>
                <th scope="col">Status</th>
                <th scope="col">Priority</th>
                <th scope="col">Tags</th>
                <th scope="col">Notes</th>
                <th scope="col">Added</th>
                <th scope="col">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <EntryRow
                  key={entry.entry_id}
                  entry={entry}
                  onMutated={() => void load()}
                  onError={(msg) => setError(msg)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ShortlistSkeleton() {
  return (
    <div role="status" aria-label="Loading this shortlist" style={{ display: "grid", gap: "var(--space-3)", marginTop: "var(--space-3)" }}>
      <span className="skeleton" style={{ display: "block", width: 180, height: 26 }} />
      <div className="table-wrap" aria-hidden="true">
        <table className="table">
          <tbody>
            {Array.from({ length: 4 }, (_, i) => (
              <tr key={i}>
                {Array.from({ length: 6 }, (_, j) => (
                  <td key={j}>
                    <span className="skeleton" style={{ display: "inline-block", width: j === 0 ? 140 : 70, height: 14 }} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
