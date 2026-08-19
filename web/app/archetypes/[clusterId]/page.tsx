import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api";
import { notFound } from "next/navigation";

type Props = {
  params: Promise<{ clusterId: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { clusterId } = await params;
  try {
    const detail = await api.archetypeDetail(Number(clusterId));
    return {
      title: `${detail.archetype_name} — Player Archetype`,
      description: detail.archetype_description,
      alternates: { canonical: `/archetypes/${clusterId}` },
    };
  } catch {
    return {
      title: "Archetype Not Found",
      description: "The requested archetype could not be found.",
    };
  }
}

export default async function ArchetypeDetailPage({ params }: Props) {
  const { clusterId } = await params;
  const id = Number(clusterId);

  if (isNaN(id)) {
    notFound();
  }

  let detail;
  try {
    detail = await api.archetypeDetail(id);
  } catch {
    notFound();
  }

  const featureLabels: Record<string, string> = {
    si_cmp_pct: "Pass Completion %",
    si_prgr_passes_p90: "Progressive Passes p90",
    si_final_third_p90: "Passes into Final Third p90",
    si_prgr_carries_p90: "Progressive Carries p90",
    si_carry_final_third_p90: "Carries into Final Third p90",
    si_pressures_p90: "Pressures p90",
    si_press_success_pct: "Pressing Success Rate",
    si_tkl_p90: "Tackles p90",
    si_int_p90: "Interceptions p90",
    si_blocks_p90: "Blocks p90",
    si_aerial_pct: "Aerial Duel Success",
    si_shots_p90: "Shots p90",
    si_xg_p90: "xG p90",
    si_gls_p90: "Goals p90",
    si_key_passes_p90: "Key Passes p90",
    si_xa_p90: "xA p90",
    si_ast_p90: "Assists p90",
  };

  return (
    <div className="container page">
      <p className="kicker">
        <Link href="/archetypes">Archetypes</Link> / Archetype {id + 1}
      </p>
      <h1 className="page__title">{detail.archetype_name}</h1>
      <p className="page__lede">{detail.archetype_description}</p>

      <div style={{ marginBottom: "32px" }}>
        <span
          style={{
            display: "inline-block",
            padding: "4px 12px",
            borderRadius: "4px",
            backgroundColor: "var(--color-surface-alt)",
            fontSize: "0.875rem",
            marginRight: "8px",
          }}
        >
          {detail.total.toLocaleString()} players
        </span>
        <span
          style={{
            display: "inline-block",
            padding: "4px 12px",
            borderRadius: "4px",
            backgroundColor: "var(--color-surface-alt)",
            fontSize: "0.875rem",
          }}
        >
          Sorted by typicality (most typical first)
        </span>
      </div>

      {detail.players.length === 0 ? (
        <div className="empty-state">
          <h2>No players in this archetype</h2>
          <p>
            No qualifying players have been assigned to this archetype yet.
          </p>
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <table className="table table--striped">
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Position</th>
                  <th>Club</th>
                  <th>League</th>
                  <th style={{ textAlign: "right" }}>Typicality</th>
                  <th style={{ textAlign: "right" }}>Distance</th>
                </tr>
              </thead>
              <tbody>
                {detail.players.map((player) => (
                  <tr key={player.player_id}>
                    <td>
                      <Link
                        href={player.name ? `/players/${encodeURIComponent(player.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-+$/, ""))}` : "#"}
                        style={{ fontWeight: 500 }}
                      >
                        {player.name}
                      </Link>
                    </td>
                    <td>{player.position_group}</td>
                    <td>{player.club ?? "—"}</td>
                    <td>{player.league ?? "—"}</td>
                    <td style={{ textAlign: "right", fontFamily: "var(--font-data)" }}>
                      <span
                        style={{
                          color: player.typicality >= 80
                            ? "var(--color-data-positive)"
                            : player.typicality >= 50
                              ? "var(--color-text-primary)"
                              : "var(--color-data-negative)",
                        }}
                      >
                        {player.typicality.toFixed(0)}%
                      </span>
                    </td>
                    <td style={{ textAlign: "right", fontFamily: "var(--font-data)" }}>
                      {player.distance_to_center.toFixed(3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {detail.total > detail.players.length && (
            <p style={{ marginTop: "16px", color: "var(--color-text-secondary)" }}>
              Showing {detail.players.length} of {detail.total.toLocaleString()} players.
            </p>
          )}
        </>
      )}

      {detail.players.length > 0 && detail.players[0].top_distinguishing_features.length > 0 && (
        <>
          <div className="section-head">
            <h2>What defines this archetype</h2>
          </div>
          <p style={{ marginBottom: "16px" }}>
            The features that most distinguish this archetype from the global average:
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "16px" }}>
            {detail.players[0].top_distinguishing_features.map((feat, idx) => (
              <div
                key={idx}
                style={{
                  padding: "16px",
                  borderRadius: "8px",
                  border: "1px solid var(--color-border)",
                  backgroundColor: "var(--color-surface)",
                }}
              >
                <div style={{ color: "var(--color-text-secondary)", fontSize: "0.8rem", marginBottom: "4px" }}>
                  {featureLabels[feat.feature] ?? feat.feature}
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                  <span style={{ fontFamily: "var(--font-data)", fontWeight: 600 }}>
                    {feat.player_value.toFixed(2)}
                  </span>
                  <span style={{ color: "var(--color-text-secondary)", fontSize: "0.8rem" }}>
                    archetype avg: {feat.archetype_average.toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
