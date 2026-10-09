"use client";

import type { TeamPayload } from "@/lib/types";
import { RadarChart, type RadarPlayer } from "./RadarChart";

export function SquadRadar({
  radar,
  leagueSlug,
  teamName,
}: {
  radar: TeamPayload["squad_radar"];
  leagueSlug: string;
  teamName: string;
}) {
  if (!radar) {
    return (
      <section className="card" aria-label="Squad average radar">
        <h2 className="card__title" style={{ fontSize: "var(--text-lg)" }}>Squad average radar</h2>
        <div className="state-block state-block--sunken" role="status" style={{ padding: "var(--space-3)" }}>
          <p className="state-block__body">
            Not enough qualifying players in this squad yet — the squad radar needs at least 5
            players with a published Statlas Index this season.
          </p>
        </div>
      </section>
    );
  }

  // The squad radar averages published percentiles per metric — plot it as a
  // single "squad" player on the percentile scale.
  const player: RadarPlayer = {
    id: 0,
    name: teamName,
    color: "var(--color-primary)",
    axes: radar.metrics.map((m) => ({
      id: m.id,
      name: m.id,
      unit: "",
      definition: "Squad-average percentile across qualifying players.",
      direction: "higher_is_better",
      lower_is_better: false,
      null_vs_zero: "zero_when_genuine",
      kind: "per90",
      raw: null,
      pct: m.avg_pct,
      status: "qualified",
    })),
    index: null,
  };

  return (
    <RadarChart
      players={[player]}
      mode="pct"
      title={`Squad average — ${teamName}`}
      subtitle={`Average published percentile per metric across ${radar.n_players} qualifying players (latest snapshot)`}
      recency={radar.snapshot_date ? radar.snapshot_date.slice(0, 10) : null}
    />
  );
}
