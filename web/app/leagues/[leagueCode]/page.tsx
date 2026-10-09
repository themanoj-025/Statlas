import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { formatNumber, percentileBand } from "@/lib/format";

type Props = {
  params: Promise<{ leagueCode: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { leagueCode } = await params;
  try {
    const hub = await api.leagueHub(leagueCode);
    return {
      title: `${hub.name} — league intelligence`,
      description: `League hub for ${hub.name}: category leaderboards, emerging players, and team overview. ${hub.tier_label}.`,
      alternates: { canonical: `/leagues/${leagueCode}` },
    };
  } catch {
    return { title: "League not found" };
  }
}

export default async function LeagueHubPage({ params }: Props) {
  const { leagueCode } = await params;

  let hub;
  try {
    hub = await api.leagueHub(leagueCode);
  } catch {
    notFound();
  }

  const coverageNote = hub.coverage
    .filter((c) => c.status === "active")
    .map((c) => c.source)
    .join(", ") || "none";

  return (
    <div className="container page">
      <Breadcrumbs
        crumbs={[
          { label: "Leagues", href: "/leagues" },
          { label: hub.name },
        ]}
      />

      {/* ---- Header ---- */}
      <header style={{ marginBottom: "var(--space-6)" }}>
        <h1 className="page__title">{hub.name}</h1>
        <p className="page__lede">
          {hub.country} · {hub.tier_label} · {hub.season} · {hub.team_count} teams ·{" "}
          {hub.player_count.toLocaleString()} qualifying players
        </p>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
          Standings data is not currently available for this league — Statlas focuses on player-level
          per-90 statistics. Data sources: {coverageNote}.
          {hub.latest_snapshot_date && (
            <> Last updated: {hub.latest_snapshot_date}.</>
          )}
        </p>
      </header>

      {/* ---- Sub-navigation ---- */}
      <nav aria-label="League views" style={{ marginBottom: "var(--space-5)" }}>
        <ul style={{ listStyle: "none", display: "flex", gap: "var(--space-2)", margin: 0, padding: 0 }}>
          <li>
            <Link
              href={`/leagues/${leagueCode}`}
              aria-current="page"
              style={{
                background: "var(--color-primary-muted)",
                padding: "var(--space-1) var(--space-3)",
                borderRadius: "var(--radius-pill)",
                fontSize: "var(--text-sm)",
                fontWeight: 600,
              }}
            >
              Overview
            </Link>
          </li>
          <li>
            <Link
              href={`/leagues/${leagueCode}/stats`}
              style={{ fontSize: "var(--text-sm)", padding: "var(--space-1) var(--space-3)" }}
            >
              Per-90 stats
            </Link>
          </li>
          <li>
            <Link
              href={`/leagues/${leagueCode}/index`}
              style={{ fontSize: "var(--text-sm)", padding: "var(--space-1) var(--space-3)" }}
            >
              Statlas Index
            </Link>
          </li>
        </ul>
      </nav>

      {/* ---- Emerging Players ---- */}
      {hub.emerging_players.length > 0 && (
        <section style={{ marginBottom: "var(--space-6)" }}>
          <h2 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-3)" }}>
            Emerging Players
          </h2>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginBottom: "var(--space-3)" }}>
            Players with strong, sustained upward percentile trends weighted by age and sample size.
            <Link
              href="/methodology#emerging-players"
              style={{ marginLeft: "var(--space-2)", fontSize: "var(--text-xs)" }}
            >
              Methodology →
            </Link>
          </p>
          <div className="table-wrap">
            <table className="table" aria-label="Emerging players">
              <thead>
                <tr>
                  <th scope="col">#</th>
                  <th scope="col">Player</th>
                  <th scope="col">Pos</th>
                  <th scope="col">Team</th>
                  <th scope="col">Score</th>
                  <th scope="col">Trend</th>
                  <th scope="col">Consistency</th>
                </tr>
              </thead>
              <tbody>
                {hub.emerging_players.map((ep, i) => (
                  <tr key={ep.player_id}>
                    <td className="num">{i + 1}</td>
                    <td>
                      {ep.slug ? (
                        <Link href={`/players/${ep.slug}`}>{ep.name}</Link>
                      ) : (
                        ep.name
                      )}
                    </td>
                    <td className="num">{ep.position_group ?? "—"}</td>
                    <td>{ep.team ?? "—"}</td>
                    <td className="num" style={{ fontWeight: 600 }}>
                      {formatNumber(ep.score, 2)}
                    </td>
                    <td className="num">{formatNumber(ep.trend_magnitude, 2)}</td>
                    <td className="num">{formatNumber(ep.trend_consistency, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ---- Category Leaderboards ---- */}
      {hub.categories.map((cat) => (
        <section key={cat.key} style={{ marginBottom: "var(--space-6)" }}>
          <h2 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-3)" }}>
            {cat.label}
          </h2>
          <div className="table-wrap">
            <table className="table table--sticky-first" aria-label={cat.label}>
              <thead>
                <tr>
                  <th scope="col">#</th>
                  <th scope="col">Player</th>
                  <th scope="col">Pos</th>
                  <th scope="col">Club</th>
                  <th scope="col">{cat.metric_name}</th>
                  <th scope="col">Min</th>
                </tr>
              </thead>
              <tbody>
                {cat.entries.map((entry, i) => (
                  <tr key={entry.player_id}>
                    <td className="num">{i + 1}</td>
                    <td>
                      {entry.slug ? (
                        <Link href={`/players/${entry.slug}`}>{entry.name}</Link>
                      ) : (
                        entry.name
                      )}
                    </td>
                    <td className="num">{entry.position_group ?? "—"}</td>
                    <td>{entry.club ?? "—"}</td>
                    <td
                      className="num"
                      style={{
                        color: percentileBand(entry.value ?? 0),
                        fontWeight: 600,
                      }}
                    >
                      {entry.value !== null ? formatNumber(entry.value, 2) : "N/A"}
                    </td>
                    <td className="num">{Math.round(entry.minutes).toLocaleString()}</td>
                  </tr>
                ))}
                {cat.entries.length === 0 && (
                  <tr>
                    <td colSpan={6}>
                      <p style={{ color: "var(--color-text-muted)", textAlign: "center", padding: "var(--space-3)" }}>
                        No qualifying players for this category yet.
                      </p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      ))}

      {/* ---- Teams Grid ---- */}
      <section style={{ marginBottom: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-3)" }}>
          Teams
        </h2>
        <ul
          style={{
            listStyle: "none",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
            gap: "var(--space-3)",
            margin: 0,
            padding: 0,
          }}
        >
          {hub.teams.map((t) => (
            <li key={t.team_id}>
              <Link
                href={`/leagues/${leagueCode}/${t.slug}`}
                style={{
                  display: "block",
                  padding: "var(--space-3)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius)",
                  fontSize: "var(--text-sm)",
                }}
              >
                {t.name}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
