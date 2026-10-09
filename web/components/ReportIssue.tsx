"use client";

import { Flag } from "lucide-react";
import { usePathname } from "next/navigation";

/**
 * Phase 5 A5 — "report an issue" mechanism on player/team pages.
 *
 * Opens a pre-filled email to the data-accuracy address naming the page the
 * user was on, so a report arrives with the right context and data-accuracy
 * reports are never a dead mailbox (Constitution §3 privacy/legal path).
 * Rendering as an <a href="mailto:..."> keeps it usable without JS.
 */
export function ReportIssue({ context }: { context: string }) {
  const pathname = usePathname();
  const subject = encodeURIComponent(`[data-accuracy] ${context}`);
  const body = encodeURIComponent(
    `Page: ${typeof window !== "undefined" ? window.location.origin : ""}${pathname}\n\n` +
      `What looks wrong (number, page, snapshot date):\n\n` +
      `Expected value / source, if known:\n`
  );
  return (
    <a
      className="button button--sm button--ghost"
      href={`mailto:data@statlas.com?subject=${subject}&body=${body}`}
      title="Report a data accuracy issue on this page"
    >
      <Flag size={13} aria-hidden="true" />
      Report a data error
    </a>
  );
}
