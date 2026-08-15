"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function Footer() {
  const pathname = usePathname();

  // Embed pages are bare iframe targets (Phase 3 C3): no site chrome.
  if (pathname.startsWith("/embed/")) return null;

  return (
    <footer className="site-footer no-print">
      <div className="container container--xl">
        <div className="site-footer__grid">
          <div>
            <p className="site-footer__title">Statlas</p>
            <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--text-sm)", maxWidth: "40ch" }}>
              A football analytics platform that shows its work. Every metric on
              this site traces to a published methodology.
            </p>
          </div>
          <div>
            <p className="site-footer__title">Product</p>
            <ul>
              <li><Link href="/positions">Leaderboards</Link></li>
              <li><Link href="/compare">Compare</Link></li>
              <li><Link href="/methodology">Methodology</Link></li>
              <li><Link href="/pricing">Pricing</Link></li>
              <li><Link href="/help">Help &amp; FAQ</Link></li>
              <li><Link href="/about">About</Link></li>
            </ul>
          </div>
          <div>
            <p className="site-footer__title">Data</p>
            <ul>
              <li><Link href="/data-coverage">Data coverage</Link></li>
              <li><Link href="/changelog">Changelog</Link></li>
              <li><Link href="/leagues/premier-league/stats">Premier League</Link></li>
              <li><Link href="/leagues/la-liga/stats">La Liga</Link></li>
            </ul>
          </div>
          <div>
            <p className="site-footer__title">Developers</p>
            <ul>
              <li><Link href="/api-docs">API documentation</Link></li>
              <li><Link href="/account">Account &amp; API keys</Link></li>
            </ul>
          </div>
          <div>
            <p className="site-footer__title">Legal</p>
            <ul>
              <li><Link href="/legal/terms">Terms of service</Link></li>
              <li><Link href="/legal/privacy">Privacy policy</Link></li>
              <li>
                <a href="mailto:data@statlas.com">data@statlas.com</a>
              </li>
            </ul>
          </div>
        </div>
        <p className="footnote">
          Per-90 statistics from FBref (Sports Reference) · xG/xA for the Big-5
          from Understat · event data, where shown, from StatsBomb Open Data
          (attribution required and rendered on every such page). Batch data is
          never presented as live; each stat block carries its snapshot date.
        </p>
      </div>
    </footer>
  );
}
