"use client";

import { useEffect } from "react";

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
      <div
        className="state-block state-block--sunken"
        role="alert"
        style={{ marginTop: "var(--space-8)" }}
      >
        <p className="state-block__title">Something went wrong</p>
        <p className="state-block__body">
          An unexpected error occurred. You can try refreshing the page, or
          return to the homepage.
          {error.digest && (
            <span
              style={{
                display: "block",
                marginTop: "var(--space-2)",
                fontSize: "0.75rem",
                color: "var(--color-muted)",
              }}
            >
              Error ID: {error.digest}
            </span>
          )}
        </p>
        <div className="state-block__actions">
          <button className="button button--sm" onClick={() => reset()}>
            Try again
          </button>
          <a className="button button--secondary button--sm" href="/">
            Back to home
          </a>
        </div>
      </div>
    </div>
  );
}
