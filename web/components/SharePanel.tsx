"use client";

import { useId, useMemo, useState } from "react";
import { Check, Code2, Link2, Share2, X } from "lucide-react";
import {
  buildEmbedCode,
  ogImageUrl,
  sharePageUrl,
  socialShareUrls,
} from "@/lib/share";

// lucide-react v1+ removed brand icons; render the LinkedIn glyph inline.
function LinkedinIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M20.45 20.45h-3.55v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.47-.9 1.63-1.85 3.36-1.85 3.6 0 4.27 2.37 4.27 5.45v6.29zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56v11.45z" />
    </svg>
  );
}

type Feedback = { kind: "success" | "error"; message: string } | null;

/**
 * Consistent sharing panel for Radar / Trend tools (Phase 3 — Part C4).
 * Every action reports its outcome ("Link copied" is announced, never a
 * silent success); clipboard failures degrade to a selectable input instead
 * of pretending. The embed snippet is a real, tested iframe (share.test.ts).
 */
export function SharePanel({
  kind,
  query,
  title,
  shareTitle,
  compact = false,
}: {
  kind: "radar" | "trend";
  query: string;
  title: string;
  shareTitle?: string;
  compact?: boolean;
}) {
  const panelId = useId().replace(/:/g, "");
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [showEmbed, setShowEmbed] = useState(false);

  const path = sharePageUrl(kind, query);
  const origin = useMemo(
    () => (typeof window === "undefined" ? undefined : window.location.origin),
    []
  );
  const absoluteUrl = useMemo(
    () => (origin ? `${origin}${path}` : path),
    [origin, path]
  );
  // The embed snippet needs an absolute origin or it breaks on third-party pages.
  const embedCode = buildEmbedCode(kind, query, { title, origin });
  const social = socialShareUrls(absoluteUrl, shareTitle ?? title);
  const ogPath = ogImageUrl(kind, query);

  const announce = (message: string) => {
    setFeedback({ kind: "success", message });
  };
  const fail = (message: string) => {
    setFeedback({ kind: "error", message });
  };

  const copy = async (text: string, okMessage: string) => {
    try {
      await navigator.clipboard.writeText(text);
      announce(okMessage);
    } catch {
      fail("Clipboard is unavailable in this browser — select the link below and copy manually.");
    }
  };

  const clearFeedback = () => setFeedback(null);

  return (
    <section className="share-panel" aria-label="Share this chart">
      <div className="share-panel__row">
        <span className="share-panel__label">
          <Share2 size={14} strokeWidth={1.5} aria-hidden="true" /> Share
        </span>

        <button type="button" className="button button--sm" onClick={() => void copy(absoluteUrl, "Link copied")}>
          <Link2 size={14} strokeWidth={1.5} aria-hidden="true" /> Copy link
        </button>
        <button
          type="button"
          className="button button--sm button--secondary"
          aria-expanded={showEmbed}
          onClick={() => setShowEmbed((open) => !open)}
        >
          <Code2 size={14} strokeWidth={1.5} aria-hidden="true" /> Embed
        </button>
        <a className="button button--sm button--secondary" href={social.x} target="_blank" rel="noopener noreferrer">
          Share on X
        </a>
        <a className="button button--sm button--secondary" href={social.linkedin} target="_blank" rel="noopener noreferrer">
          <LinkedinIcon size={14} /> LinkedIn
        </a>

        {feedback && (
          <span
            role="status"
            className={`share-panel__feedback ${feedback.kind === "error" ? "share-panel__feedback--error" : ""}`}
            aria-live="polite"
          >
            {feedback.kind === "error" ? <X size={13} aria-hidden="true" /> : <Check size={13} aria-hidden="true" />}
            {feedback.message}
          </span>
        )}
      </div>

      {/* Always-visible permalink field: the accessible copy path and the
          honest preview target (og:image renders the actual chart). */}
      <div className="share-panel__url">
        <label htmlFor={`${panelId}-url`} className="visually-hidden">
          Permalink
        </label>
        <input
          id={`${panelId}-url`}
          className="input"
          readOnly
          value={absoluteUrl}
          onFocus={(e) => e.currentTarget.select()}
          onClick={(e) => e.currentTarget.select()}
        />
        <span className="share-panel__og" role="note">
          Shared previews render this chart&rsquo;s real data via the{" "}
          <a href={ogPath} rel="nofollow">
            generated image
          </a>
          .
        </span>
      </div>

      {showEmbed && (
        <div className="share-panel__embed" id={`${panelId}-embed`}>
          <p className="share-panel__embed-title">
            Embed this chart on any page — responsive iframe, lazy-loaded, attributed to Statlas.
          </p>
          <button type="button" className="button button--sm" onClick={() => void copy(embedCode, "Embed code copied")}>
            Copy embed code
          </button>
          <pre className="share-panel__code" tabIndex={0}>
            <code>{embedCode}</code>
          </pre>
        </div>
      )}
    </section>
  );
}
