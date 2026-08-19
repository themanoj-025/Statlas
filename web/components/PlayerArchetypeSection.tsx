"use client";

import Link from "next/link";
import { api } from "@/lib/api";
import { useEffect, useState } from "react";
import type { PlayerArchetype } from "@/lib/types";

type Props = {
  playerId: number;
  playerName: string;
};

const FEATURE_LABELS: Record<string, string> = {
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

function typicalityColor(typicality: number): string {
  if (typicality >= 80) return "var(--color-data-positive)";
  if (typicality >= 50) return "var(--color-text-primary)";
  return "var(--color-data-negative)";
}

export function PlayerArchetypeSection({ playerId, playerName }: Props) {
  const [archetype, setArchetype] = useState<PlayerArchetype | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .playerArchetype(playerId)
      .then(setArchetype)
      .catch(() => setArchetype(null))
      .finally(() => setLoading(false));
  }, [playerId]);

  if (loading) {
    return (
      <div style={{ marginTop: "var(--space-4)" }}>
        <div className="section-head">
          <h2>Player Archetype</h2>
        </div>
        <div className="skeleton" style={{ height: 120, borderRadius: 8 }} />
      </div>
    );
  }

  if (!archetype || !archetype.cluster_id) {
    return null; // Don't show section if no archetype data
  }

  return (
    <div style={{ marginTop: "var(--space-4)" }}>
      <div className="section-head">
        <h2>Player Archetype</h2>
        <Link
          href={`/archetypes/${archetype.cluster_id}`}
          className="button button--sm button--secondary"
        >
          View archetype
        </Link>
      </div>

      <div
        style={{
          padding: "16px",
          borderRadius: "8px",
          border: "1px solid var(--color-border)",
          backgroundColor: "var(--color-surface)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
          <span
            style={{
              padding: "4px 12px",
              borderRadius: "4px",
              backgroundColor: "var(--color-primary)",
              color: "var(--color-text-inverse, #fff)",
              fontSize: "0.875rem",
              fontWeight: 600,
            }}
          >
            {archetype.archetype_name}
          </span>
          {archetype.typicality !== null && (
            <span style={{ fontSize: "0.875rem" }}>
              Typicality:{" "}
              <span
                style={{
                  fontFamily: "var(--font-data)",
                  fontWeight: 600,
                  color: typicalityColor(archetype.typicality),
                }}
              >
                {archetype.typicality.toFixed(0)}%
              </span>
            </span>
          )}
          {archetype.is_outlier && (
            <span
              style={{
                padding: "2px 8px",
                borderRadius: "4px",
                backgroundColor: "var(--color-warning-bg, #fff3cd)",
                fontSize: "0.75rem",
                color: "var(--color-warning-text, #856404)",
              }}
            >
              Unusual profile
            </span>
          )}
        </div>

        <p style={{ fontSize: "0.875rem", color: "var(--color-text-secondary)", marginBottom: "12px" }}>
          {archetype.archetype_description}
        </p>

        {archetype.top_distinguishing_features.length > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "8px" }}>
            {archetype.top_distinguishing_features.map((feat, idx) => (
              <div
                key={idx}
                style={{
                  padding: "8px",
                  borderRadius: "4px",
                  backgroundColor: "var(--color-surface-alt)",
                  fontSize: "0.8rem",
                }}
              >
                <div style={{ color: "var(--color-text-secondary)" }}>
                  {FEATURE_LABELS[feat.feature] ?? feat.feature}
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: "4px" }}>
                  <span style={{ fontFamily: "var(--font-data)", fontWeight: 600 }}>
                    {feat.player_value.toFixed(2)}
                  </span>
                  <span style={{ color: "var(--color-text-secondary)", fontSize: "0.75rem" }}>
                    avg: {feat.archetype_average.toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
