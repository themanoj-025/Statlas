import type { Metadata } from "next";
import Link from "next/link";
import { BookOpen, FileText, Video, BarChart3, Download } from "lucide-react";

export const metadata: Metadata = {
  title: "Learning Resources",
  description:
    "Educational resources for football analytics: articles, guides, video tutorials, datasets, and methodology documentation.",
  alternates: { canonical: "/resources" },
};

const RESOURCE_CATEGORIES = [
  {
    icon: BookOpen,
    title: "Articles",
    description: "In-depth articles on methodology, analytics, and scouting.",
    links: [
      { label: "How we calculate percentiles", href: "/blog/how-we-calculate-percentiles" },
      { label: "Why trend charts draw gaps as gaps", href: "/blog/honest-trend-charts" },
      { label: "AI reports: what they can and cannot do", href: "/blog/ai-reports-verification" },
      { label: "The Statlas Index explained", href: "/blog/statlas-index-explained" },
      { label: "All articles", href: "/blog" },
    ],
  },
  {
    icon: FileText,
    title: "Guides",
    description: "Step-by-step guides for using Statlas features.",
    links: [
      { label: "Getting started with Statlas", href: "/docs/getting-started" },
      { label: "Understanding radar charts", href: "/docs/understanding-radar-charts" },
      { label: "Player comparison guide", href: "/docs/player-comparison" },
      { label: "Structured search tutorial", href: "/docs/structured-search" },
      { label: "Workspace & shortlists guide", href: "/docs/workspace-guide" },
    ],
  },
  {
    icon: Video,
    title: "Video Tutorials",
    description: "Video walkthroughs of key features.",
    links: [
      { label: "Video tutorials coming soon", href: "#" },
    ],
  },
  {
    icon: BarChart3,
    title: "Methodology",
    description: "The complete methodology documentation.",
    links: [
      { label: "Full methodology page", href: "/methodology" },
      { label: "Data coverage matrix", href: "/data-coverage" },
      { label: "API documentation", href: "/api-docs" },
    ],
  },
  {
    icon: Download,
    title: "Datasets",
    description: "Sample data for researchers and developers.",
    links: [
      { label: "Sample dataset (coming soon)", href: "#" },
      { label: "API documentation", href: "/api-docs" },
    ],
  },
];

export default function ResourcesPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Resources</p>
      <h1 className="page__title">Learning resources</h1>
      <p className="page__lede">
        Articles, guides, and documentation to help you get the most out of Statlas.
        Every resource links to the methodology it references.
      </p>

      <div style={{ display: "grid", gap: "var(--space-6)" }}>
        {RESOURCE_CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          return (
            <section key={cat.title}>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-3)" }}>
                <Icon size={18} color="var(--color-primary)" aria-hidden="true" />
                <h2 style={{ fontSize: "var(--text-xl)", margin: 0 }}>{cat.title}</h2>
              </div>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginBottom: "var(--space-3)" }}>
                {cat.description}
              </p>
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {cat.links.map((link) => (
                  <li
                    key={link.label}
                    style={{
                      padding: "var(--space-2) 0",
                      borderBottom: "1px solid var(--color-divider)",
                    }}
                  >
                    <Link href={link.href} style={{ fontSize: "var(--text-sm)" }}>
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}
