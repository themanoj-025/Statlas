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
              Football analytics that shows its work. Every metric on
              this site traces to a published methodology.
            </p>
          </div>
          <div>
            <p className="site-footer__title">Product</p>
            <ul>
              <li><Link href="/features">Features</Link></li>
              <li><Link href="/positions">Leaderboards</Link></li>
              <li><Link href="/compare">Compare</Link></li>
              <li><Link href="/methodology">Methodology</Link></li>
              <li><Link href="/pricing">Pricing</Link></li>
              <li><Link href="/comparison">Comparison</Link></li>
            </ul>
          </div>
          <div>
            <p className="site-footer__title">Use Cases</p>
            <ul>
              <li><Link href="/use-cases/scout">For Scouts</Link></li>
              <li><Link href="/use-cases/agent">For Agents</Link></li>
              <li><Link href="/use-cases/analyst">For Analysts</Link></li>
              <li><Link href="/use-cases/media">For Media</Link></li>
              <li><Link href="/use-cases/fan">For Fans</Link></li>
            </ul>
          </div>
          <div>
            <p className="site-footer__title">Resources</p>
            <ul>
              <li><Link href="/docs">Documentation</Link></li>
              <li><Link href="/api-docs">API docs</Link></li>
              <li><Link href="/blog">Blog</Link></li>
              <li><Link href="/help">Help &amp; FAQ</Link></li>
              <li><Link href="/data-coverage">Data coverage</Link></li>
              <li><Link href="/changelog">Changelog</Link></li>
            </ul>
          </div>
          <div>
            <p className="site-footer__title">Company</p>
            <ul>
              <li><Link href="/about">About</Link></li>
              <li><Link href="/careers">Careers</Link></li>
              <li><Link href="/contact">Contact</Link></li>
              <li><Link href="/status">Status</Link></li>
              <li><Link href="/legal/terms">Terms</Link></li>
              <li><Link href="/legal/privacy">Privacy</Link></li>
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
