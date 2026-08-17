"use client";

import Link from "next/link";
import { BellOff, BellRing, Settings2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import {
  ALERT_TYPE_LABELS,
  formatAlertDetail,
  formatAlertLong,
} from "@/lib/alertFormat";
import type { WatchAlertItem, WatchItem } from "@/lib/types";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; watches: WatchItem[]; alerts: WatchAlertItem[] };

export function WatchlistClient() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [openAlert, setOpenAlert] = useState<WatchAlertItem | null>(null);

  const load = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      const [watches, alerts] = await Promise.all([
        api.watches(),
        api.watchAlerts({ include_read: true, limit: 100 }),
      ]);
      setState({ kind: "ready", watches: watches.watches, alerts: alerts.alerts });
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof ApiError ? err.message : "Could not load your watchlist.",
      });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const unfollow = async (watch: WatchItem) => {
    setBusyId(watch.watch_id);
    setMessage(null);
    try {
      await api.unfollow(watch.watch_id);
      setMessage({ kind: "ok", text: `Unfollowed ${watch.entity_name}. Alert history is retained for audit.` });
      await load();
    } catch (err) {
      setMessage({ kind: "error", text: err instanceof ApiError ? err.message : "Could not unfollow." });
    } finally {
      setBusyId(null);
    }
  };

  const markRead = async (alert: WatchAlertItem) => {
    await api.markAlertRead(alert.alert_id).catch(() => undefined);
    setOpenAlert((prev) => (prev ? { ...prev, read_at: new Date().toISOString() } : prev));
  };

  if (state.kind === "loading") {
    return (
      <div aria-busy="true" aria-label="Loading your watchlist">
        {[0, 1, 2].map((i) => (
          <div key={i} className="skeleton" style={{ height: 72, marginBottom: "var(--space-3)" }} />
        ))}
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="state-card" role="alert">
        <p>{state.message}</p>
        <button type="button" className="button" onClick={() => void load()}>
          Retry
        </button>
      </div>
    );
  }

  const { watches, alerts } = state;

  if (watches.length === 0) {
    return (
      <div className="state-card">
        <p className="kicker">Nothing followed yet</p>
        <h2>Start with a player or team you&apos;re tracking</h2>
        <p>
          Open any player or team profile and hit <strong>Follow</strong>. Statlas watches the
          weekly data for meaningful changes — percentile jumps past a documented threshold,
          club moves, new season data, and data-coverage changes — and lets you know.
        </p>
        <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
          <Link href="/positions" className="button button--primary">
            Browse leaderboards
          </Link>
          <Link href="/search" className="button button--secondary">
            Build a search
          </Link>
        </div>
      </div>
    );
  }

  const alertsByWatch = new Map<number, WatchAlertItem[]>();
  for (const a of alerts) {
    const list = alertsByWatch.get(a.watch_id) ?? [];
    list.push(a);
    alertsByWatch.set(a.watch_id, list);
  }
  const recentAlerts = alerts.slice(0, 20);

  return (
    <div>
      <div className="section-head" style={{ marginBottom: "var(--space-3)" }}>
        <p className="page__lede" style={{ margin: 0 }}>
          {watches.length} followed {watches.length === 1 ? "entity" : "entities"}
        </p>
        <Link href="/watchlist/settings" className="button button--sm button--secondary">
          <Settings2 size={14} aria-hidden="true" /> Notification settings
        </Link>
      </div>

      {message && (
        <p role="status" className="inline-message" style={{ color: message.kind === "error" ? "var(--color-danger)" : "var(--color-success)" }}>
          {message.text}
        </p>
      )}

      <h2 className="section-title">Your watchlist</h2>
      <ul className="watchlist__list">
        {watches.map((watch) => {
          const href =
            watch.entity_type === "player"
              ? watch.slug
                ? `/players/${watch.slug}`
                : null
              : watch.slug && watch.league_slug
                ? `/clubs/${watch.league_slug}/${watch.slug}`
                : null;
          const unread = alertsByWatch.get(watch.watch_id)?.filter((a) => !a.read_at && !a.dismissed).length ?? 0;
          return (
            <li key={watch.watch_id} className="watchlist__item">
              <div className="watchlist__item-main">
                {href ? (
                  <Link href={href}>
                    <strong>{watch.entity_name}</strong>
                  </Link>
                ) : (
                  <strong>{watch.entity_name}</strong>
                )}
                <span className="watchlist__item-meta">
                  {watch.entity_type === "player"
                    ? [watch.position_group, watch.team].filter(Boolean).join(" · ")
                    : watch.league ?? "Team"}
                  {unread > 0 && (
                    <span className="chip chip--primary" aria-label={`${unread} unread`}>
                      {unread} new
                    </span>
                  )}
                </span>
                {(alertsByWatch.get(watch.watch_id) ?? []).slice(0, 2).map((a) => (
                  <button
                    key={a.alert_id}
                    type="button"
                    className="watchlist__alert-link"
                    onClick={() => {
                      setOpenAlert(a);
                      void markRead(a);
                    }}
                  >
                    <BellRing size={13} aria-hidden="true" /> {formatAlertDetail(a)}
                  </button>
                ))}
              </div>
              <button
                type="button"
                className="button button--sm button--ghost"
                onClick={() => void unfollow(watch)}
                disabled={busyId !== null}
                aria-label={`Unfollow ${watch.entity_name}`}
              >
                <BellOff size={14} aria-hidden="true" /> {busyId === watch.watch_id ? "Unfollowing…" : "Unfollow"}
              </button>
            </li>
          );
        })}
      </ul>

      <h2 className="section-title" style={{ marginTop: "var(--space-5)" }}>
        Recent alerts
      </h2>
      {recentAlerts.length === 0 ? (
        <p className="muted">
          No alerts yet. Alerts fire only on meaningful changes — a percentile jump of 15+
          points between weekly snapshots, a club move, new season data, or a data-coverage
          change — never on every refresh.
        </p>
      ) : (
        <ul className="watchlist__alerts">
          {recentAlerts.map((a) => (
            <li key={a.alert_id} className={a.read_at ? "" : "watchlist__alert-unread"}>
              <button
                type="button"
                className="watchlist__alert-row"
                onClick={() => {
                  setOpenAlert(a);
                  void markRead(a);
                }}
              >
                <span>
                  <strong>{a.entity_name}</strong> — {ALERT_TYPE_LABELS[a.alert_type]}
                </span>
                <span className="muted">{formatAlertDetail(a)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {openAlert && (
        <AlertDetailModal alert={openAlert} onClose={() => setOpenAlert(null)} />
      )}
    </div>
  );
}

function AlertDetailModal({ alert, onClose }: { alert: WatchAlertItem; onClose: () => void }) {
  const href =
    alert.entity_type === "player"
      ? alert.slug
        ? `/players/${alert.slug}`
        : null
      : alert.slug && alert.league_slug
        ? `/clubs/${alert.league_slug}/${alert.slug}`
        : null;
  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label={`${alert.entity_name} — ${ALERT_TYPE_LABELS[alert.alert_type]}`}
      onClick={onClose}
    >
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="section-head">
          <div>
            <p className="kicker">Alert detail</p>
            <h2>
              {alert.entity_name} — {ALERT_TYPE_LABELS[alert.alert_type]}
            </h2>
          </div>
          <button type="button" className="button button--sm button--ghost" onClick={onClose}>
            Close
          </button>
        </div>
        <dl className="alert-detail__list">
          {formatAlertLong(alert).map(({ label, value }) => (
            <div key={label} className="alert-detail__row">
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        <p className="muted" style={{ fontSize: "var(--font-sm)" }}>
          Every value above comes straight from the snapshot data that triggered this alert —
          checkable against the published percentile rows.
        </p>
        <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-3)" }}>
          {href && (
            <Link href={href} className="button button--sm">
              Open {alert.entity_type} profile
            </Link>
          )}
          <button
            type="button"
            className="button button--sm button--secondary"
            onClick={() => {
              void api.dismissAlert(alert.alert_id);
              onClose();
            }}
          >
            Dismiss alert
          </button>
        </div>
      </div>
    </div>
  );
}
