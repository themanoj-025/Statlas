"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Uncaught error:", error);
  }, [error]);

  return (
    <div className="container page" style={{ maxWidth: "var(--container-sm)" }}>
      <div style={{ textAlign: "center", padding: "var(--space-9) 0" }}>
        <div
          style={{
            width: 80,
            height: 80,
            borderRadius: "var(--radius-xl)",
            background: "var(--color-danger-muted)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto var(--space-4)",
          }}
        >
          <AlertTriangle size={32} color="var(--color-danger)" aria-hidden="true" />
        </div>
        <h1 style={{ fontSize: "var(--text-2xl)", marginBottom: "var(--space-2)", color: "var(--color-text-primary)" }}>
          Something went wrong
        </h1>
        <p style={{ fontSize: "var(--text-lg)", color: "var(--color-text-secondary)", marginBottom: "var(--space-2)" }}>
          An unexpected error occurred.
        </p>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginBottom: "var(--space-5)", maxWidth: "40ch", margin: "0 auto var(--space-5)" }}>
          You can try refreshing the page, or return to the homepage.
          {error.digest && (
            <span style={{ display: "block", marginTop: "var(--space-2)", fontSize: "var(--text-xs)" }}>
              Error ID: {error.digest}
            </span>
          )}
        </p>
        <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "center" }}>
          <button className="button button--sm" onClick={() => reset()}>
            Try again
          </button>
          <Link className="button button--secondary button--sm" href="/">
            Back to home
          </Link>
        </div>
        <p style={{ marginTop: "var(--space-4)", fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
          If this persists, <a href="mailto:data@statlas.com">contact support</a> with the error ID above.
        </p>
      </div>
    </div>
  );
}
