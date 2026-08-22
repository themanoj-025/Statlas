import Link from "next/link";
import { Search } from "lucide-react";

export default function NotFound() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-sm)" }}>
      <div style={{ textAlign: "center", padding: "var(--space-9) 0" }}>
        <div
          style={{
            width: 80,
            height: 80,
            borderRadius: "var(--radius-xl)",
            background: "var(--color-surface-sunken)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto var(--space-4)",
          }}
        >
          <Search size={32} color="var(--color-text-muted)" aria-hidden="true" />
        </div>
        <h1 style={{ fontSize: "var(--text-2xl)", marginBottom: "var(--space-2)", color: "var(--color-text-primary)" }}>
          Page not found
        </h1>
        <p style={{ fontSize: "var(--text-lg)", color: "var(--color-text-secondary)", marginBottom: "var(--space-2)" }}>
          The page you are looking for does not exist.
        </p>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginBottom: "var(--space-5)", maxWidth: "40ch", margin: "0 auto var(--space-5)" }}>
          The URL may be misspelled, the player may be outside current data coverage, or
          the page may have moved.
        </p>
        <div className="state-block state-block--sunken" role="status" style={{ textAlign: "left", marginTop: "var(--space-4)" }}>
          <p className="state-block__title" style={{ fontSize: "var(--text-sm)" }}>Try one of these:</p>
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {[
              { label: "Search for a player", href: "/search" },
              { label: "Browse leaderboards", href: "/positions" },
              { label: "View data coverage", href: "/data-coverage" },
              { label: "Read the documentation", href: "/docs" },
              { label: "Contact support", href: "/contact" },
            ].map((link) => (
              <li key={link.href} style={{ padding: "var(--space-2) 0", borderBottom: "1px solid var(--color-divider)" }}>
                <Link href={link.href} style={{ fontSize: "var(--text-sm)" }}>{link.label}</Link>
              </li>
            ))}
          </ul>
        </div>
        <div style={{ marginTop: "var(--space-5)", display: "flex", gap: "var(--space-3)", justifyContent: "center" }}>
          <Link className="button button--sm" href="/">Back to home</Link>
          <Link className="button button--secondary button--sm" href="/contact">Report broken link</Link>
        </div>
      </div>
    </div>
  );
}
