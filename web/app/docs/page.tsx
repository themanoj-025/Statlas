import type { Metadata } from "next";
import Link from "next/link";
import { BookOpen, Code, HelpCircle, AlertTriangle, MessageSquare } from "lucide-react";

export const metadata: Metadata = {
  title: "Documentation",
  description:
    "Statlas documentation: getting started, feature guides, API reference, troubleshooting, and FAQ.",
  alternates: { canonical: "/docs" },
};

const SECTIONS = [
  {
    icon: BookOpen,
    title: "Getting Started",
    description: "Quick start guide, first steps, and orientation.",
    links: [
      { label: "What is Statlas?", href: "/about" },
      { label: "How to read a radar chart", href: "/methodology" },
      { label: "Understanding percentiles", href: "/methodology" },
      { label: "Your first search", href: "/search" },
    ],
  },
  {
    icon: BookOpen,
    title: "Features Guide",
    description: "How to use every feature in Statlas.",
    links: [
      { label: "Player comparison", href: "/compare" },
      { label: "Trend analysis", href: "/trend" },
      { label: "Shot & pass maps", href: "/players/haaland" },
      { label: "AI scouting reports", href: "/reports" },
      { label: "Workspace & shortlists", href: "/workspace" },
      { label: "Structured search", href: "/search" },
      { label: "Watchlist & alerts", href: "/watchlist" },
      { label: "Methodology & Index", href: "/methodology" },
    ],
  },
  {
    icon: Code,
    title: "API Reference",
    description: "Versioned REST API with OpenAPI specification.",
    links: [
      { label: "API documentation", href: "/api-docs" },
      { label: "Authentication & keys", href: "/account" },
      { label: "Rate limits", href: "/api-docs" },
    ],
  },
  {
    icon: HelpCircle,
    title: "FAQ",
    description: "Common questions about data, billing, and methodology.",
    links: [
      { label: "Help & FAQ", href: "/help" },
      { label: "Data coverage", href: "/data-coverage" },
      { label: "Pricing & billing", href: "/pricing" },
    ],
  },
  {
    icon: AlertTriangle,
    title: "Troubleshooting",
    description: "When something is not working as expected.",
    links: [
      { label: "Report a data error", href: "mailto:data@statlas.com" },
      { label: "My data is not loading", href: "/help" },
      { label: "API requests failing", href: "/api-docs" },
    ],
  },
  {
    icon: MessageSquare,
    title: "Contact Support",
    description: "Get help from the Statlas team.",
    links: [
      { label: "Contact us", href: "/contact" },
      { label: "Email support", href: "mailto:data@statlas.com" },
    ],
  },
];

export default function DocsPage() {
  return (
    <div className="container page">
      <p className="kicker">Documentation</p>
      <h1 className="page__title">Documentation</h1>
      <p className="page__lede">
        Everything you need to use Statlas effectively. From first steps to API integration.
      </p>

      <div className="grid" style={{ marginTop: "var(--space-4)" }}>
        {SECTIONS.map((section) => {
          const Icon = section.icon;
          return (
            <div key={section.title} className="card grid__span-4" style={{ padding: "var(--space-5)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-3)" }}>
                <Icon size={20} color="var(--color-primary)" aria-hidden="true" />
                <h2 style={{ fontSize: "var(--text-base)", margin: 0 }}>{section.title}</h2>
              </div>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginBottom: "var(--space-3)" }}>
                {section.description}
              </p>
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {section.links.map((link) => (
                  <li key={link.label} style={{ marginBottom: "var(--space-1)" }}>
                    <Link href={link.href} style={{ fontSize: "var(--text-sm)" }}>{link.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      {/* Quick links */}
      <section style={{ marginTop: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Quick reference</h2>
        <div className="table-wrap" role="region" aria-label="Quick reference" tabIndex={0}>
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Topic</th>
                <th scope="col">Page</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>Percentile formula</td><td><Link href="/methodology#the-formula">Methodology</Link></td></tr>
              <tr><td>Statlas Index weights</td><td><Link href="/methodology#the-weights">Methodology</Link></td></tr>
              <tr><td>League tiers</td><td><Link href="/methodology#league-tiers">Methodology</Link></td></tr>
              <tr><td>Data coverage matrix</td><td><Link href="/data-coverage">Data coverage</Link></td></tr>
              <tr><td>API endpoints</td><td><Link href="/api-docs">API docs</Link></td></tr>
              <tr><td>Pricing plans</td><td><Link href="/pricing">Pricing</Link></td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
