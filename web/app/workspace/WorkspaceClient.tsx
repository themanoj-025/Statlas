"use client";

import Link from "next/link";
import { Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { api, ApiError } from "@/lib/api";
import { relativeAndAbsolute } from "@/lib/format";
import type { EntryStatus, WorkspaceOverview } from "@/lib/types";
import { STATUS_CHIP_CLASS, STATUS_LABELS, STATUS_ORDER } from "@/lib/workspace";

export function WorkspaceClient() {
  const { status } = useAuth();
  const [data, setData] = useState<WorkspaceOverview | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [busyDelete, setBusyDelete] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setData(await api.workspace());
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Could not load your workspace.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, attempt]);

  if (status === "loading") {
    return <WorkspaceSkeleton />;
  }

  if (status === "signed-out") {
    return (
      <div className="state-block state-block--sunken" role="status">
        <p className="state-block__title">Workspace is per-account</p>
        <p className="state-block__body">
          Shortlists, notes and status history are private to your account.{" "}
          <Link href="/login">Sign in</Link> to open yours, or{" "}
          <Link href="/register">create a free account</Link> (the free tier includes one
          shortlist with up to 10 players — a genuine taste of the workflow).
        </p>
      </div>
    );
  }

  if (loadError && !data) {
    return (
      <div className="state-block state-block--error" role="alert">
        <p className="state-block__title">We couldn&rsquo;t load your workspace.</p>
        <p className="state-block__body">{loadError}</p>
        <div className="state-block__actions">
          <button type="button" className="button button--sm" onClick={() => setAttempt((a) => a + 1)}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return <WorkspaceSkeleton />;

  const { shortlists, limits } = data;
  const maxShortlists = limits.shortlists_max;
  const atShortlistCap = maxShortlists !== null && shortlists.length >= maxShortlists;

  const create = async () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setSubmitting(true);
    setFormError(null);
    try {
      const created = await api.createShortlist(trimmed, description.trim() || null);
      setShowForm(false);
      setName("");
      setDescription("");
      setData(await api.workspace());
      window.location.href = `/workspace/${created.shortlist_id}`;
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create the shortlist.");
    } finally {
      setSubmitting(false);
    }
  };

  const remove = async (shortlistId: number) => {
    if (!window.confirm("Remove this shortlist? Its players, notes and status history are kept for audit.")) return;
    setBusyDelete(shortlistId);
    try {
      await api.removeShortlist(shortlistId);
      setData(await api.workspace());
    } catch (err) {
      window.alert(err instanceof ApiError ? err.message : "Could not remove the shortlist.");
    } finally {
      setBusyDelete(null);
    }
  };

  return (
    <div style={{ display: "grid", gap: "var(--space-4)", marginTop: "var(--space-4)" }}>
      {loadError && (
        <div className="state-block state-block--error" role="alert">
          <p className="state-block__body">{loadError}</p>
          <div className="state-block__actions">
            <button type="button" className="button button--sm" onClick={() => void load()}>
              Retry
            </button>
          </div>
        </div>
      )}

      <div className="section-head">
        <h2 style={{ margin: 0 }}>Shortlists</h2>
        {!atShortlistCap ? (
          <button type="button" className="button button--sm" onClick={() => setShowForm((v) => !v)}>
            <Plus size={14} aria-hidden="true" /> New shortlist
          </button>
        ) : (
          <span className="chip chip--accent">Free plan: 1 shortlist used — upgrade for more</span>
        )}
      </div>

      {showForm && (
        <section className="card" aria-label="Create a shortlist">
          <div style={{ display: "grid", gap: "var(--space-2)" }}>
            <div className="field">
              <label className="field__label" htmlFor="ws-name">
                Name
              </label>
              <input
                id="ws-name"
                className="input"
                type="text"
                value={name}
                maxLength={128}
                placeholder="e.g. Summer 2027 CB targets"
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="ws-desc">
                Description <span className="field__hint">(optional)</span>
              </label>
              <textarea
                id="ws-desc"
                className="input"
                rows={2}
                value={description}
                maxLength={2000}
                placeholder="What is this list for?"
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            {formError && (
              <p className="field__hint" role="alert" style={{ color: "var(--color-danger)" }}>
                {formError}
              </p>
            )}
            <div style={{ display: "flex", gap: "var(--space-2)" }}>
              <button type="button" className="button button--sm" onClick={() => void create()} disabled={!name.trim() || submitting}>
                {submitting ? "Creating…" : "Create shortlist"}
              </button>
              <button type="button" className="button button--sm button--secondary" onClick={() => setShowForm(false)}>
                Cancel
              </button>
            </div>
          </div>
        </section>
      )}

      {shortlists.length === 0 ? (
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__title">Build your first shortlist</p>
          <p className="state-block__body">
            A shortlist is a named group of players you&rsquo;re tracking — for example
            &ldquo;Summer 2027 CB targets&rdquo;. Open any player page and hit{" "}
            <em>Add to shortlist</em>, or create a list here first.
          </p>
        </div>
      ) : (
        <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: "var(--space-3)" }}>
          {shortlists.map((sl) => (
            <li key={sl.shortlist_id}>
              <div className="card shortlist-card">
                <div className="shortlist-card__main">
                  <Link href={`/workspace/${sl.shortlist_id}`} className="shortlist-card__name">
                    {sl.name}
                  </Link>
                  {sl.description && <p className="shortlist-card__desc">{sl.description}</p>}
                  <p className="shortlist-card__meta">
                    {sl.entry_count} {sl.entry_count === 1 ? "player" : "players"} · updated{" "}
                    {relativeAndAbsolute(sl.updated_at) ?? "recently"}
                  </p>
                  <ul className="shortlist-card__statuses" aria-label="Status breakdown">
                    {STATUS_ORDER.filter((s) => (sl.status_breakdown[s] ?? 0) > 0).map((s: EntryStatus) => (
                      <li key={s}>
                        <span className={STATUS_CHIP_CLASS[s]}>
                          {sl.status_breakdown[s]} {STATUS_LABELS[s]}
                        </span>
                      </li>
                    ))}
                    {sl.entry_count === 0 && <li className="chip">No players yet</li>}
                  </ul>
                </div>
                <button
                  type="button"
                  className="button button--sm button--ghost"
                  aria-label={`Remove ${sl.name}`}
                  disabled={busyDelete === sl.shortlist_id}
                  onClick={() => void remove(sl.shortlist_id)}
                >
                  <Trash2 size={14} aria-hidden="true" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {maxShortlists !== null && (
        <p className="field__hint">
          Free plan: {shortlists.length} of {maxShortlists} shortlist
          {maxShortlists === 1 ? "" : "s"} used · up to {limits.shortlist_entries_max} players per
          shortlist.{" "}
          <Link href="/pricing">
            Upgrade to Pro
          </Link>{" "}
          for unlimited shortlists and player tracking — your saved players, notes and tags all stay
          put.
        </p>
      )}
    </div>
  );
}

function WorkspaceSkeleton() {
  return (
    <div role="status" aria-label="Loading your workspace" style={{ display: "grid", gap: "var(--space-3)", marginTop: "var(--space-4)" }}>
      <div className="card" aria-hidden="true">
        <span className="skeleton" style={{ display: "block", width: "40%", height: 18, marginBottom: "var(--space-2)" }} />
        <span className="skeleton" style={{ display: "block", width: "70%", height: 12 }} />
      </div>
      <div className="card" aria-hidden="true">
        <span className="skeleton" style={{ display: "block", width: "35%", height: 18, marginBottom: "var(--space-2)" }} />
        <span className="skeleton" style={{ display: "block", width: "60%", height: 12 }} />
      </div>
    </div>
  );
}
