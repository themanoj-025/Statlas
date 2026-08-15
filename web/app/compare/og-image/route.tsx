import type { NextRequest } from "next/server";
import { api } from "@/lib/api";
import { OG_PLAYER_COLORS, ogFooter, radarChartSvg } from "@/lib/chartSvg";
import { renderOgCard } from "@/lib/ogRender";
import { decodeRadarQuery } from "@/lib/share";

export const runtime = "nodejs";

/**
 * Dynamic OG image for a shared radar comparison (Part C2). Renders the ACTUAL
 * radar polygons for the ACTUAL players/mode in the permalink — a generic
 * site banner would read as fake; this preview reads as the real chart.
 */
export async function GET(request: NextRequest) {
  const config = decodeRadarQuery(request.nextUrl.searchParams.toString());

  const resolved = await Promise.all(
    config.players.map((slug) =>
      api.playerBySlug(slug).catch(() => null)
    )
  );
  const payloads = resolved.filter((p): p is NonNullable<typeof p> => p !== null);

  if (!payloads.length) {
    return renderOgCard({
      title: "Player comparison",
      subtitle: "Open the link to build a comparison — no players could be resolved for this preview.",
      chartSvg: radarChartSvg([], { mode: config.mode, title: "Player comparison" }),
      chartWidth: 700,
      chartHeight: 532,
      footer: "Statlas",
    });
  }

  const players = payloads.map((payload, index) => ({
    name: payload.player.name,
    color: OG_PLAYER_COLORS[index % OG_PLAYER_COLORS.length],
    axes: payload.axes
      .filter((a) => a.status === "qualified")
      .map((a) => ({
        name: a.name,
        value: config.mode === "pct" ? a.pct : a.raw,
      })),
  }));

  const season = payloads[0]?.raw.season ?? "";
  const title = `Player comparison — ${players.map((p) => p.name).join(" vs ")}`;
  const svg = radarChartSvg(players, {
    mode: config.mode,
    title,
    subtitle:
      config.mode === "pct"
        ? "Percentile ranks vs position-group × league-tier peers"
        : "Raw per-90 values, each axis scaled to the highest displayed value",
  });

  const recency = payloads[0]?.percentiles.snapshot_date ?? payloads[0]?.raw.snapshot_date ?? null;
  return renderOgCard({
    title,
    subtitle: `Percentile radar · ${season}`.trim(),
    chartSvg: svg,
    chartWidth: 700,
    chartHeight: 532,
    footer: ogFooter(config.mode === "pct" ? "Percentile view" : "Raw per-90 view", recency ? recency.slice(0, 10) : null),
  });
}
