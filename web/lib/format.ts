// Formatting + small display helpers (tabular figures come from the data font).

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10); // YYYY-MM-DD — the recency-label format
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.toISOString().slice(0, 10)} ${d.toISOString().slice(11, 16)} UTC`;
}

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

export function formatPercentile(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `p${Math.round(value)}`;
}

export function ordinal(n: number): string {
  if (10 <= n % 100 && n % 100 <= 20) return `${n}th`;
  return `${n}${{ 1: "st", 2: "nd", 3: "rd" }[n % 10] ?? "th"}`;
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

// Percentile band token (design system: neutral -> pitch green ramp).
// Returns the TEXT-SAFE ramp tokens (--color-pct-text-N) — the chart-fill
// ramp (--color-pct-N) fails WCAG AA as text, and these labels are always
// rendered WITH the numeric value (never color alone, Constitution §2).
export function percentileBand(pct: number): string {
  if (pct >= 80) return "var(--color-pct-text-5)";
  if (pct >= 60) return "var(--color-pct-text-4)";
  if (pct >= 40) return "var(--color-pct-text-3)";
  if (pct >= 20) return "var(--color-pct-text-2)";
  return "var(--color-pct-text-1)";
}

export function positionGroupLabel(code: string | null): string {
  const labels: Record<string, string> = {
    GK: "Goalkeeper",
    CB: "Centre-back",
    FB: "Full-back",
    DM: "Defensive midfield",
    CM: "Central midfield",
    AM: "Attacking midfield",
    W: "Wide attacker",
    ST: "Striker",
  };
  return code ? (labels[code] ?? code) : "Position unknown";
}

export function tierLabel(tier: string | null | undefined): string {
  return { tier_1: "Tier 1", tier_2: "Tier 2", tier_3: "Tier 3" }[tier ?? ""] ?? tier ?? "";
}
