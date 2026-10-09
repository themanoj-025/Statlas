"use client";

import Link from "next/link";
import { Check, Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "./AuthProvider";
import { api, ApiError } from "@/lib/api";
import type { ShortlistSummary } from "@/lib/types";

/**
 * "Add to Shortlist" — the entry point that makes the Phase 7 workspace get
 * used (player profile, leaderboard rows, similar-player results).
 *
 * Lazy by design: nothing is fetched until the button is first clicked, so a
 * leaderboard of 25 rows costs zero requests until a scout actually saves a
 * player. States are all explicit:
 * - signed out          -> honest "Sign in to save" link (no dead button)
 * - signed in, loading  -> spinner in the menu
 * - already in a list   -> checked + disabled (can't duplicate; server 409s)
 * - multiple shortlists -> real selector + inline "New shortlist…"
 * - free-tier cap hit   -> the API's honest upsell message, with a pricing link
 */
export function AddToShortlist({
  playerId,
  playerName,
  compact = false,
}: {
  playerId: number;
  playerName: string;
  compact?: boolean;
}) {
  const { status } = useAuth();
  const [open, setOpen] = useState(false);
  const [shortlists, setShortlists] = useState<ShortlistSummary[] | null>(null);
  const [memberships, setMemberships] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [message, setMessage] = useState<{ kind: "ok" | "error" | "upsell"; text: string; addedId?: number } | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  const close = () => {
    setOpen(false);
    setShortlists(null);
    setMessage(null);
  };

  // Click-outside + Escape close (accessible menu behavior).
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

  const openMenu = async () => {
    setOpen(true);
    setLoading(true);
    setMessage(null);
    try {
      const [overview, members] = await Promise.all([
        api.workspace(),
        api.shortlistMemberships(playerId),
      ]);
      setShortlists(overview.shortlists);
      setMemberships(members.shortlist_ids);
    } catch (err) {
      setMessage({
        kind: "error",
        text: err instanceof ApiError ? err.message : "Could not load your shortlists.",
      });
    } finally {
      setLoading(false);
    }
  };

  const add = async (shortlistId: number, name: string) => {
    setBusyId(shortlistId);
    setMessage(null);
    try {
      await api.addToShortlist(shortlistId, playerId);
      setMemberships((prev) => [...prev, shortlistId]);
      setMessage({ kind: "ok", text: `Added to ${name}`, addedId: shortlistId });
      setOpen(false);
      setShortlists(null);
    } catch (err) {
      const text = err instanceof ApiError ? err.message : "Could not add the player.";
      if (err instanceof ApiError && err.status === 403) {
        setMessage({ kind: "upsell", text });
      } else {
        setMessage({ kind: "error", text });
      }
    } finally {
      setBusyId(null);
    }
  };

  const createAndAdd = async () => {
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    setMessage(null);
    try {
      const created = await api.createShortlist(name);
      await add(created.shortlist_id, created.name);
      setCreating(false);
    } catch (err) {
      setCreating(false);
      const text = err instanceof ApiError ? err.message : "Could not create the shortlist.";
      if (err instanceof ApiError && err.status === 403) {
        setMessage({ kind: "upsell", text });
      } else {
        setMessage({ kind: "error", text });
      }
    }
  };

  if (status === "signed-out") {
    return (
      <Link href="/login" className={`button button--secondary ${compact ? "button--sm" : ""}`}>
        <Plus size={14} aria-hidden="true" /> Sign in to save
      </Link>
    );
  }
  if (status === "loading") return null;

  return (
    <div className="add-to-shortlist" ref={wrapRef}>
      <button
        type="button"
        className={`button button--secondary ${compact ? "button--sm" : ""}`}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => (open ? close() : void openMenu())}
      >
        <Plus size={14} aria-hidden="true" /> {compact ? "Save" : "Add to shortlist"}
      </button>

      {message && !open && (
        <div className="add-to-shortlist__message" role={message.kind === "ok" ? "status" : "alert"}>
          {message.kind === "ok" && message.addedId ? (
            <>
              <Check size={13} aria-hidden="true" /> {message.text} ·{" "}
              <Link href={`/workspace/${message.addedId}`}>Open shortlist</Link>
            </>
          ) : message.kind === "upsell" ? (
            <>
              {message.text} <Link href="/pricing">See Pro</Link>
            </>
          ) : (
            message.text
          )}
        </div>
      )}

      {open && (
        <div className="add-to-shortlist__menu" role="menu" aria-label={`Add ${playerName} to a shortlist`}>
          {loading && (
            <p className="add-to-shortlist__hint" role="status">
              Loading your shortlists…
            </p>
          )}

          {!loading && shortlists && (
            <>
              {message && (
                <p className="add-to-shortlist__hint" role="alert" style={{ color: "var(--color-danger)" }}>
                  {message.text} {message.kind === "upsell" && <Link href="/pricing">See Pro</Link>}
                </p>
              )}
              {shortlists.length === 0 ? (
                <p className="add-to-shortlist__hint">No shortlists yet — create one below.</p>
              ) : (
                <ul className="add-to-shortlist__list">
                  {shortlists.map((sl) => {
                    const already = memberships.includes(sl.shortlist_id);
                    return (
                      <li key={sl.shortlist_id}>
                        <button
                          type="button"
                          role="menuitem"
                          className="add-to-shortlist__item"
                          disabled={already || busyId !== null}
                          onClick={() => void add(sl.shortlist_id, sl.name)}
                        >
                          <span>
                            {sl.name}
                            <span className="add-to-shortlist__count">
                              {sl.entry_count} {sl.entry_count === 1 ? "player" : "players"}
                            </span>
                          </span>
                          {already ? (
                            <span className="add-to-shortlist__check">
                              <Check size={13} aria-hidden="true" /> Already saved
                            </span>
                          ) : busyId === sl.shortlist_id ? (
                            "Adding…"
                          ) : null}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}

              {creating ? (
                <p className="add-to-shortlist__hint" role="status">
                  Creating…
                </p>
              ) : (
                <div className="add-to-shortlist__new">
                  <label className="add-to-shortlist__new-label" htmlFor={`ats-new-${playerId}`}>
                    New shortlist
                  </label>
                  <div className="add-to-shortlist__new-row">
                    <input
                      id={`ats-new-${playerId}`}
                      className="input"
                      type="text"
                      placeholder="e.g. Summer 2027 targets"
                      value={newName}
                      maxLength={128}
                      onChange={(e) => setNewName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") void createAndAdd();
                      }}
                    />
                    <button
                      type="button"
                      className="button button--sm"
                      onClick={() => void createAndAdd()}
                      disabled={!newName.trim()}
                    >
                      Create &amp; add
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
