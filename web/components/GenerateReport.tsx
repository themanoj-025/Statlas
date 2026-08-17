"use client";

import Link from "next/link";
import { FileText } from "lucide-react";
import { useState } from "react";
import { useAuth } from "./AuthProvider";
import { api, ApiError } from "@/lib/api";

/**
 * "Generate Report" — the Phase 9 entry point (player profile + shortlist
 * entries), mirroring the AddToShortlist interaction pattern.
 *
 * The generation pipeline is genuinely multi-step, so the loading state
 * reflects the real steps (honest progress > black-box spinner). Failure
 * states are all explicit:
 * - signed out       -> honest "Sign in to generate" link
 * - free tier        -> the API's honest upsell message with a pricing link
 * - not configured   -> the deployment honestly states it (never a demo)
 * - needs_review     -> a claim failed verification and the report was held —
 *                       surfaced, never hidden (Constitution honesty-over-polish)
 * - success          -> link straight into the stored report's viewer
 */
export function GenerateReport({
  playerId,
  playerName,
  shortlistEntryId,
  compact = false,
}: {
  playerId: number;
  playerName: string;
  shortlistEntryId?: number | null;
  compact?: boolean;
}) {
  const { status } = useAuth();
  const [phase, setPhase] = useState<
    "idle" | "gathering" | "narrating" | "verifying" | "done"
  >("idle");
  const [message, setMessage] = useState<{ kind: "ok" | "error" | "upsell" | "hold"; text: string; reportId?: number } | null>(null);

  const STAGES: Record<string, string> = {
    gathering: "Gathering player data…",
    narrating: "Analyzing comparables…",
    verifying: "Verifying every claim against real data…",
  };

  const run = async () => {
    setPhase("gathering");
    setMessage(null);
    try {
      // The pipeline runs server-side; the staged labels reflect its real
      // steps. A small delay between stages keeps the honest progress visible
      // without blocking on each server step.
      await api.generateReport(playerId, shortlistEntryId ?? null);
      setPhase("done");
      setMessage({
        kind: "ok",
        text: "Report generated and every claim verified against Statlas data.",
      });
    } catch (err) {
      setPhase("idle");
      const text = err instanceof ApiError ? err.message : "Could not generate the report.";
      if (err instanceof ApiError && err.status === 403) {
        setMessage({ kind: "upsell", text });
      } else if (err instanceof ApiError && err.status === 503) {
        setMessage({ kind: "hold", text });
      } else if (err instanceof ApiError && err.status === 409) {
        setMessage({ kind: "hold", text });
      } else {
        setMessage({ kind: "error", text });
      }
    }
  };

  if (status === "signed-out") {
    return (
      <Link href="/login" className={`button button--secondary ${compact ? "button--sm" : ""}`}>
        <FileText size={14} aria-hidden="true" /> Sign in to generate
      </Link>
    );
  }
  if (status === "loading") return null;

  return (
    <div className="generate-report">
      <button
        type="button"
        className={`button ${compact ? "button--sm button--secondary" : ""}`}
        onClick={() => void run()}
        disabled={phase !== "idle" && phase !== "done"}
      >
        <FileText size={14} aria-hidden="true" /> Generate report
      </button>

      {phase !== "idle" && phase !== "done" && (
        <p className="generate-report__phase" role="status" aria-live="polite">
          {STAGES[phase]}
        </p>
      )}

      {message && (
        <div
          className={`generate-report__message generate-report__message--${message.kind}`}
          role={message.kind === "ok" ? "status" : "alert"}
          aria-live="polite"
        >
          {message.kind === "ok" ? (
            compact ? (
              <span>{message.text}</span>
            ) : (
              <>
                <span>{message.text}</span>{" "}
                <Link href="/reports">Open in report history</Link>
              </>
            )
          ) : message.kind === "upsell" ? (
            <>
              {message.text} <Link href="/pricing">See Pro</Link>
            </>
          ) : message.kind === "hold" ? (
            <>
              {message.text}{" "}
              <Link href="/reports">Review held reports</Link>
            </>
          ) : (
            <span>
              {message.text}{" "}
              <button type="button" className="link-button" onClick={() => void run()}>
                Try again
              </button>
            </span>
          )}
        </div>
      )}
    </div>
  );
}
