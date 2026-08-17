"use client";

import Link from "next/link";
import { Bell, BellOff } from "lucide-react";
import { useState } from "react";
import { useAuth } from "./AuthProvider";
import { api, ApiError } from "@/lib/api";

/**
 * "Follow" — the Phase 10 entry point on player/team profile pages,
 * consistent with the Add-to-Shortlist action pattern (Phase 7/8/9):
 * - signed out        -> honest "Sign in to follow" link
 * - signed in         -> Follow / Unfollow with an explicit toggle
 * - free-tier cap hit -> the API's honest upsell message with a pricing link
 * The button reads the user's current watch state lazily on mount; a follow
 * that already exists (idempotent server-side) is reflected as "Following".
 */
export function FollowButton({
  entityType,
  entityId,
  entityName,
  compact = false,
}: {
  entityType: "player" | "team";
  entityId: number;
  entityName: string;
  compact?: boolean;
}) {
  const { status } = useAuth();
  const [following, setFollowing] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error" | "upsell"; text: string } | null>(null);
  const [loaded, setLoaded] = useState(false);

  // Lazy: only check follow state when signed in and not yet loaded.
  if (status === "signed-in" && !loaded) {
    setLoaded(true);
    void (async () => {
      try {
        const { watches } = await api.watches();
        const mine = watches.find(
          (w) => w.entity_type === entityType && w.entity_id === entityId
        );
        setFollowing(Boolean(mine));
      } catch {
        setFollowing(false);
      }
    })();
  }

  if (status === "signed-out") {
    return (
      <Link href="/login" className={`button button--secondary ${compact ? "button--sm" : ""}`}>
        <Bell size={14} aria-hidden="true" /> Sign in to follow
      </Link>
    );
  }
  if (status === "loading") return null;

  const toggle = async () => {
    setBusy(true);
    setMessage(null);
    try {
      if (following) {
        // Unfollow: we know the watch id from a fresh list read.
        const { watches } = await api.watches();
        const mine = watches.find(
          (w) => w.entity_type === entityType && w.entity_id === entityId
        );
        if (mine) await api.unfollow(mine.watch_id);
        setFollowing(false);
        setMessage({ kind: "ok", text: `Unfollowed ${entityName}` });
      } else {
        await api.follow(entityType, entityId);
        setFollowing(true);
        setMessage({ kind: "ok", text: `Following ${entityName} — you'll get alerts on meaningful changes` });
      }
    } catch (err) {
      const text = err instanceof ApiError ? err.message : "Could not update your watchlist.";
      if (err instanceof ApiError && err.status === 403) {
        setMessage({ kind: "upsell", text });
      } else {
        setMessage({ kind: "error", text });
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
      <button
        type="button"
        className={`button ${following ? "button--secondary" : ""} ${compact ? "button--sm" : ""}`}
        aria-pressed={following === true}
        onClick={() => void toggle()}
        disabled={busy}
      >
        {following ? (
          <>
            <BellOff size={14} aria-hidden="true" /> {busy ? "Updating…" : "Unfollow"}
          </>
        ) : (
          <>
            <Bell size={14} aria-hidden="true" /> {busy ? "Following…" : "Follow"}
          </>
        )}
      </button>
      {message && (
        <p
          className="follow-button__message"
          role={message.kind === "ok" ? "status" : "alert"}
          style={{ color: message.kind === "upsell" ? "var(--color-danger)" : undefined }}
        >
          {message.kind === "upsell" ? (
            <>
              {message.text} <Link href="/pricing">See Pro</Link>
            </>
          ) : (
            message.text
          )}
        </p>
      )}
    </div>
  );
}
