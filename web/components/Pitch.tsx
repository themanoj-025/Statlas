"use client";

/**
 * Pitch diagram (Phase 3 — Part B2/B3). Rendered in StatsBomb coordinates
 * (120 × 80) mapped to a real pitch's proportions: every marking is computed
 * from FIFA pitch dimensions (105 × 68 m) scaled by 120/105 — the drawing is
 * never distorted. Events plot via `soccerToPitch(x, y)` (identity in SB
 * space; the mapping lives here so a future licensed feed can swap it once).
 */
export function soccerToPitch(x: number | null, y: number | null): { x: number; y: number } | null {
  if (x === null || y === null) return null;
  return { x, y };
}

// Pitch markings in StatsBomb units (real metres × 120/105).
const SCALE = 120 / 105;
const PEN_DEPTH = 16.5 * SCALE; // 18.86
const PEN_WIDTH = 40.32 * SCALE; // 46.08
const BOX_DEPTH = 5.5 * SCALE; // 6.29
const BOX_WIDTH = 18.32 * SCALE; // 20.94
const SPOT_X = 120 - 11 * SCALE; // 107.43
const ARC_R = 9.15 * SCALE; // 10.46
const CENTER_R = 9.15 * SCALE;

export function Pitch({
  children,
  ariaLabel,
}: {
  children?: React.ReactNode;
  ariaLabel: string;
}) {
  const boxY = (80 - PEN_WIDTH) / 2;
  const goalY = (80 - BOX_WIDTH) / 2;
  const spotX = 11 * SCALE;

  // Penalty-arc endpoints: where the arc circle (radius ARC_R centred on the
  // spot) crosses the penalty-box line — computed, never eyeballed.
  const arcDy = Math.sqrt(ARC_R * ARC_R - (1 + PEN_DEPTH - spotX) ** 2);
  const arcTop = 40 - arcDy;
  const arcBottom = 40 + arcDy;
  const boxLineLeft = 1 + PEN_DEPTH;
  const boxLineRight = 120 - 1 - PEN_DEPTH;

  return (
    <svg viewBox="0 0 120 80" className="pitch" role="img" aria-label={ariaLabel} preserveAspectRatio="xMidYMid meet">
      {/* surface */}
      <rect className="pitch__surface" x="0" y="0" width="120" height="80" />
      {/* outer boundary */}
      <rect className="pitch__line" x="1" y="1" width="118" height="78" />
      {/* halfway line + centre circle + spot */}
      <line className="pitch__line" x1="60" y1="1" x2="60" y2="79" />
      <circle className="pitch__line" cx="60" cy="40" r={CENTER_R} fill="none" />
      <circle className="pitch__line" cx="60" cy="40" r="0.8" />
      {/* left penalty area (defending end) */}
      <rect className="pitch__line" x="1" y={boxY} width={PEN_DEPTH} height={PEN_WIDTH} fill="none" />
      <rect className="pitch__line" x="1" y={goalY} width={BOX_DEPTH} height={BOX_WIDTH} fill="none" />
      <circle className="pitch__line" cx={spotX} cy="40" r="0.8" />
      <path className="pitch__line" d={`M ${boxLineLeft} ${arcTop} A ${ARC_R} ${ARC_R} 0 0 1 ${boxLineLeft} ${arcBottom}`} fill="none" />
      {/* right penalty area (attacking end) */}
      <rect className="pitch__line" x={boxLineRight} y={boxY} width={PEN_DEPTH} height={PEN_WIDTH} fill="none" />
      <rect className="pitch__line" x={boxLineRight} y={goalY} width={BOX_DEPTH} height={BOX_WIDTH} fill="none" />
      <circle className="pitch__line" cx={SPOT_X} cy="40" r="0.8" />
      <path className="pitch__line" d={`M ${boxLineRight} ${arcTop} A ${ARC_R} ${ARC_R} 0 0 0 ${boxLineRight} ${arcBottom}`} fill="none" />
      {/* goals */}
      <rect className="pitch__goal" x="0" y={goalY - 1.5} width="1.2" height={BOX_WIDTH + 3} />
      <rect className="pitch__goal" x={120 - 1.2} y={goalY - 1.5} width="1.2" height={BOX_WIDTH + 3} />

      {children}
    </svg>
  );
}
