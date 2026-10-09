import { ImageResponse } from "next/og";
import { api } from "@/lib/api";
import { formatNumber, positionGroupLabel } from "@/lib/format";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "Player statistics card";

export default async function PlayerOgImage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  let payload: Awaited<ReturnType<typeof api.playerBySlug>> | null = null;
  try {
    payload = await api.playerBySlug(slug);
  } catch {
    /* fall through to generic card */
  }

  const player = payload?.player;
  const axes = payload?.axes ?? [];
  const qualified = axes.filter((a) => a.status === "qualified" && a.pct !== null);
  const top = [...qualified].sort((a, b) => (b.pct ?? 0) - (a.pct ?? 0)).slice(0, 4);
  const index = payload?.percentiles?.index;
  const season = payload?.raw?.season ?? "";

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 64,
          background: "#12100D",
          color: "#F1EFE9",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 28, fontWeight: 700, color: "#5CAD82" }}>
          <div style={{ width: 18, height: 18, borderRadius: "50%", background: "#1F6E47" }} />
          Statlas
          <span style={{ color: "#A8A296", fontWeight: 400, fontSize: 20 }}>— analytics that shows its work</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 72, fontWeight: 700, letterSpacing: -1 }}>{player?.name ?? "Player"}</div>
          <div style={{ fontSize: 32, color: "#E8B45C" }}>
            {[player?.club, positionGroupLabel(player?.position_group ?? null), season].filter(Boolean).join(" · ")}
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 48 }}>
          <div style={{ display: "flex", gap: 40 }}>
            {top.length ? (
              top.map((axis) => (
                <div key={axis.id} style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontSize: 40, fontWeight: 700, color: "#6BC794", fontVariantNumeric: "tabular-nums" }}>
                    p{Math.round(axis.pct!)}
                  </span>
                  <span style={{ fontSize: 20, color: "#A8A296", maxWidth: 220 }}>{axis.name}</span>
                </div>
              ))
            ) : (
              <span style={{ fontSize: 24, color: "#A8A296" }}>
                Percentiles pending qualification this season
              </span>
            )}
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
            <span style={{ fontSize: 22, color: "#A8A296" }}>Statlas Index</span>
            <span style={{ fontSize: 64, fontWeight: 700, fontVariantNumeric: "tabular-nums", color: "#F1EFE9" }}>
              {index !== null ? formatNumber(index, 1) : "—"}
            </span>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 18, color: "#8A8578" }}>
          <span>{payload?.sentence ?? "Statlas — per-90 statistics with a published methodology"}</span>
          <span>{payload?.raw?.snapshot_date ? `Data as of ${payload.raw.snapshot_date.slice(0, 10)}` : ""}</span>
        </div>
      </div>
    ),
    { ...size }
  );
}
