import { ImageResponse } from "next/og";
import { svgDataUrl } from "./chartSvg";

/**
 * Shared OG card renderer (Phase 3 — Part C2). Wraps a chart SVG (built from
 * REAL data by the pure builders in chartSvg.ts) in the dark Statlas card with
 * a subtle wordmark — the legitimacy signal: a shared link's preview shows the
 * actual chart, not a site-wide banner. Satori cannot run React chart
 * components, so the SVG is embedded as a data-URL image.
 */
export function renderOgCard({
  title,
  subtitle,
  chartSvg,
  chartWidth,
  chartHeight,
  footer,
}: {
  title: string;
  subtitle: string;
  chartSvg: string;
  chartWidth: number;
  chartHeight: number;
  footer: string;
}): ImageResponse {
  const src = svgDataUrl(chartSvg);
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 44,
          background: "#12100D",
          color: "#F1EFE9",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 16, fontSize: 26, fontWeight: 700, color: "#5CAD82" }}>
          <div style={{ width: 16, height: 16, borderRadius: "50%", background: "#1F6E47", alignSelf: "center" }} />
          Statlas
          <span style={{ color: "#A8A296", fontWeight: 400, fontSize: 18 }}>— analytics that shows its work</span>
          <span style={{ marginLeft: "auto", color: "#F1EFE9", fontSize: 26, fontWeight: 700, maxWidth: 620, textAlign: "right" }}>
            {title}
          </span>
        </div>

        <div style={{ display: "flex", justifyContent: "center" }}>
          <img src={src} width={chartWidth} height={chartHeight} />
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", gap: 24, fontSize: 18, color: "#A8A296" }}>
          <span style={{ maxWidth: 820 }}>{subtitle}</span>
          <span style={{ whiteSpace: "nowrap" }}>{footer}</span>
        </div>
      </div>
    ),
    // The card URL encodes the full chart configuration, so the image is
    // cacheable: crawlers won't re-render it on every share preview.
    {
      width: 1200,
      height: 630,
      headers: new Headers({ "Cache-Control": "public, max-age=3600, s-maxage=86400" }),
    }
  );
}
