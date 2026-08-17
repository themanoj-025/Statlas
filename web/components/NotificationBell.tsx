"use client";

import Link from "next/link";
import { Bell } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "./AuthProvider";
import { ALERT_TYPE_LABELS, entityHref, formatAlertDetail, type WatchAlertItem } from "@/lib/alertFormat";

/**
 * In-app notification center (Phase 10 E3/E4). An accessible bell:
 * - unread count is announced to screen readers (aria-label + live region)
 * - dropdown is fully keyboard-navigable (Escape closes, links focusable)
 * - read/dismiss actions are explicit buttons with text labels (never
 *   icon-only meaning)
 * - every alert links to the entity's profile page, where the full
 *   supporting detail is shown (before/after values, snapshot dates)
 */
export function NotificationBell() {
  const { status } = useAuth();
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState<WatchAlertItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  const unread = alerts?.filter((a) => !a.read_at && !a.dismissed).length ?? 0;

  const close = () => {
    setOpen(false);
    setAlerts(null);
  };

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) close();
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const openBell = async () => {
    setOpen(true);
    setLoading(true);
    setError(null);
    try {
      const payload = await api.watchAlerts({ limit: 20 });
      setAlerts(payload.alerts);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load notifications.");
    } finally {
      setLoading(false);
    }
  };

  const markRead = async (alertId: number) => {
    await api.markAlertRead(alertId).catch(() => undefined);
    setAlerts((prev) => {
      if (!prev) return prev;
      return prev.map((a) =>
        a.alert_id === alertId ? { ...a, read_at: new Date().toISOString() } : a
      );
    });
  };

  const dismiss = async (alertId: number) => {
    await api.dismissAlert(alertId).catch(() => undefined);
    setAlerts((prev) => {
      if (!prev) return prev;
      return prev.map((a) => (a.alert_id === alertId ? { ...a, dismissed: true } : a));
    });
  };

  if (status !== "signed-in") return null;

  const visible = alerts?.filter((a) => !a.dismissed) ?? [];

  return (
    <div className="notification-bell" ref={wrapRef}>
      <button
        type="button"
        className="notification-bell__button"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={`Notifications${unread > 0 ? ` — ${unread} unread` : ""}`}
        onClick={() => (open ? close() : void openBell())}
      >
        <Bell size={17} aria-hidden="true" />
        {unread > 0 && (
          <span className="notification-bell__badge" aria-hidden="true">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {/* Live region announces the unread count to screen readers. */}
      <span className="sr-only" role="status" aria-live="polite">
        {unread > 0 ? `${unread} unread notification${unread === 1 ? "" : "s"}` : ""}
      </span>

      {open && (
        <div className="notification-bell__menu" role="menu" aria-label="Notifications">
          <p className="notification-bell__title">Notifications</p>
          {loading && (
            <p className="notification-bell__hint" role="status">
              Loading notifications…
            </p>
          )}
          {error && (
            <p className="notification-bell__hint" role="alert">
              {error}{" "}
              <button
                type="button"
                className="link-button"
                onClick={() => {
                  setError(null);
                  void openBell();
                }}
              >
                Retry
              </button>
            </p>
          )}
          {!loading && !error && visible.length === 0 && (
            <p className="notification-bell__hint">
              No notifications yet. Follow players or teams to get alerted on meaningful changes.
            </p>
          )}
          {!loading &&
            !error &&
            visible.map((alert) => (
              <div className="notification-bell__item" key={alert.alert_id}>
                <div className="notification-bell__item-main">
                  <Link
                    href={entityHref(alert)}
                    onClick={() => void markRead(alert.alert_id)}
                  >
                    <strong>{alert.entity_name}</strong> — {ALERT_TYPE_LABELS[alert.alert_type]}
                  </Link>
                  <p className="notification-bell__item-detail">{formatAlertDetail(alert)}</p>
                </div>
                <div className="notification-bell__item-actions">
                  {!alert.read_at && (
                    <button type="button" className="link-button" onClick={() => void markRead(alert.alert_id)}>
                      Mark read
                    </button>
                  )}
                  <button type="button" className="link-button" onClick={() => void dismiss(alert.alert_id)}>
                    Dismiss
                  </button>
                </div>
              </div>
            ))}
          {!loading && !error && (
            <Link href="/watchlist" className="notification-bell__footer">
              View all on your watchlist
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
