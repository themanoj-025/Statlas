/**
 * OG chart SVG tests (Phase 3 — Part C2 quality gate): the generated image
 * contains the REAL data values from the shared configuration — never a
 * static placeholder. Also asserts the trend image renders gap-breaks as
 * dashed segments (Part A honesty, carried into the shared preview).
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  OG_METRIC_DASHES,
  OG_PLAYER_COLORS,
  radarChartSvg,
  svgDataUrl,
  trendChartSvg,
} from "./chartSvg.ts";

test("radar OG svg bakes in player names, axis labels and real values", () => {
  const svg = radarChartSvg(
    [
      {
        name: "Erling Haaland",
        color: OG_PLAYER_COLORS[0],
        axes: [
          { name: "Goals per 90", value: 87 },
          { name: "xG per 90", value: 82 },
          { name: "Shots per 90", value: 74 },
        ],
      },
    ],
    { mode: "pct", title: "Percentile radar · 2025-26" }
  );
  assert.match(svg, /Erling Haaland/);
  assert.match(svg, /Goals per 90/);
  assert.match(svg, /Goals per 90 · 87/); // the real percentile in the legend
  assert.match(svg, /xG per 90 · 82/);
  assert.match(svg, /Shots per 90 · 74/);
  assert.match(svg, /fill="#0072B2"/);
  assert.match(svg, /Percentile radar/);
});

test("radar OG svg scales raw per-90 to the displayed max and labels it", () => {
  const svg = radarChartSvg(
    [
      {
        name: "Kevin De Bruyne",
        color: OG_PLAYER_COLORS[1],
        axes: [
          { name: "Progressive passes per 90", value: 6.2 },
          { name: "Progressive carries per 90", value: 1.8 },
        ],
      },
    ],
    { mode: "raw", title: "Raw per-90 comparison" }
  );
  assert.match(svg, /Kevin De Bruyne/);
  assert.match(svg, /6\.2/); // the real value string
  assert.match(svg, /Progressive passes per 90/);
});

test("trend OG svg draws a dashed gap-break, never an interpolation", () => {
  const svg = trendChartSvg(
    [
      {
        label: "Erling Haaland · Goals per 90",
        color: OG_PLAYER_COLORS[0],
        dash: OG_METRIC_DASHES[0],
        points: [
          { date: "2026-07-01", value: 0.8 },
          { date: "2026-07-08", value: 0.85 },
          { date: "2026-07-15", value: 0.9, gap_after: true },
          { date: "2026-07-29", value: 0.9 },
        ],
      },
    ],
    { mode: "raw", unit: "goals / 90", title: "Goals per 90 — snapshot history", granularityNote: "Weekly snapshots" }
  );
  assert.match(svg, /Erling Haaland · Goals per 90/);
  assert.match(svg, />0\.9</); // the final real value label in the image
  assert.match(svg, /stroke-dasharray="4 10"/); // the gap segment is dashed
  assert.match(svg, /2026-07-01/); // x labels from the real dates
});

test("trend OG svg percent mode pins the axis to 0-100", () => {
  const svg = trendChartSvg(
    [
      {
        label: "Percentile",
        color: OG_PLAYER_COLORS[0],
        dash: OG_METRIC_DASHES[0],
        points: [
          { date: "2026-07-01", value: 40 },
          { date: "2026-07-08", value: 60 },
        ],
      },
    ],
    { mode: "pct", unit: "percentile", title: "Percentile trend", granularityNote: "Weekly snapshots" }
  );
  assert.match(svg, />100</); // axis pinned to 100
  assert.match(svg, />60</); // final value label — real data in the image
  assert.match(svg, />50</); // mid gridline label
});

test("svgDataUrl base64-encodes for satori-safe <img> embedding", () => {
  const url = svgDataUrl("<svg></svg>");
  assert.ok(url.startsWith("data:image/svg+xml;base64,"));
  assert.ok(!url.includes("<svg"));
  const decoded = Buffer.from(url.split(",")[1], "base64").toString("utf8");
  assert.equal(decoded, "<svg></svg>"); // round-trips exactly
});
