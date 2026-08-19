import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api";

export const metadata: Metadata = {
  title: "Player Archetypes",
  description:
    "Discover player archetypes — statistically-defined groups of similar playing styles. Browse archetype definitions, example players, and explore what makes each archetype unique.",
  alternates: { canonical: "/archetypes" },
};

export default async function ArchetypesPage() {
  let overview;
  try {
    overview = await api.archetypeOverview();
  } catch {
    overview = { model: null, archetypes: [], total_players: 0 };
  }

  const hasModel = overview.model !== null;

  return (
    <div className="container page">
      <p className="kicker">Discovery</p>
      <h1 className="page__title">Player Archetypes</h1>
      <p className="page__lede">
        Player archetypes are statistically-defined groups of players with similar
        playing styles, discovered through unsupervised clustering of per-90
        statistics. These are patterns in the data, not predictions about player
        ability.
      </p>

      {!hasModel && (
        <div className="empty-state" style={{ gridColumn: "1 / -1" }}>
          <h2>No archetype data available</h2>
          <p>
            Player archetypes require a trained clustering model and sufficient
            player data. The model will be trained during the next weekly refresh
            cycle.
          </p>
        </div>
      )}

      {hasModel && (
        <>
          <div className="model-info" style={{ gridColumn: "1 / -1" }}>
            <h2>Model Information</h2>
            <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
              <div>
                <dt style={{ color: "var(--color-text-secondary)" }}>Model</dt>
                <dd>{overview.model!.model_name} v{overview.model!.version}</dd>
              </div>
              <div>
                <dt style={{ color: "var(--color-text-secondary)" }}>Algorithm</dt>
                <dd>{overview.model!.algorithm}</dd>
              </div>
              <div>
                <dt style={{ color: "var(--color-text-secondary)" }}>Clusters</dt>
                <dd>{overview.model!.n_clusters}</dd>
              </div>
              <div>
                <dt style={{ color: "var(--color-text-secondary)" }}>Silhouette Score</dt>
                <dd>{overview.model!.silhouette_score?.toFixed(3) ?? "N/A"}</dd>
              </div>
              <div>
                <dt style={{ color: "var(--color-text-secondary)" }}>Total Players</dt>
                <dd>{overview.total_players.toLocaleString()}</dd>
              </div>
              <div>
                <dt style={{ color: "var(--color-text-secondary)" }}>Trained</dt>
                <dd>{overview.model!.training_date ? new Date(overview.model!.training_date).toLocaleDateString() : "N/A"}</dd>
              </div>
            </dl>
          </div>

          <div className="section-head">
            <h2>Archetypes</h2>
          </div>

          <div className="grid">
            {overview.archetypes.map((archetype) => (
              <Link
                key={archetype.cluster_id}
                href={`/archetypes/${archetype.cluster_id}`}
                className="position-card grid__span-3"
              >
                <span className="position-card__code" style={{ fontSize: "1.5rem" }}>
                  {archetype.cluster_id + 1}
                </span>
                <span className="position-card__name" style={{ display: "block" }}>
                  {archetype.name}
                </span>
                <span className="position-card__meta">
                  {archetype.player_count.toLocaleString()} players
                </span>
                {archetype.distinguishing_features.length > 0 && (
                  <span
                    className="position-card__meta"
                    style={{ marginTop: "8px", fontSize: "0.8rem" }}
                  >
                    Key: {archetype.distinguishing_features[0]?.feature?.replace("si_", "").replace("_p90", "").replace("_", " ") ?? ""}
                  </span>
                )}
              </Link>
            ))}
          </div>

          <div className="section-head">
            <h2>Methodology</h2>
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <p>
              Archetypes are discovered using k-means clustering on 17 per-90
              statistical features covering passing, carrying, pressing, defensive,
              attacking, and creative dimensions. Players are clustered separately
              by position group (midfielders, strikers, defenders) to produce
              position-appropriate archetypes.
            </p>
            <p style={{ marginTop: "8px" }}>
              Each archetype is named based on its distinguishing statistical
              characteristics — the features that differ most from the global
              average. Archetypes describe statistical similarity, not player
              quality or potential.
            </p>
            <p style={{ marginTop: "8px" }}>
              For full technical details, see the{" "}
              <Link href="/methodology">methodology page</Link> and the{" "}
              <Link href="/docs/ml/player_clustering_v1.md">model card</Link>.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
