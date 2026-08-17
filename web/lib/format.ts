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

// Relative + absolute timestamp pair (Phase 7 D1) — "3 weeks ago — Oct 12, 2026"
// so a scout can reconstruct their timeline across sessions and devices.
export function relativeTime(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return null;
  const seconds = Math.round((Date.now() - then.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days} day${days === 1 ? "" : "s"} ago`;
  const weeks = Math.round(days / 7);
  if (weeks < 5) return `${weeks} week${weeks === 1 ? "" : "s"} ago`;
  const months = Math.round(days / 30);
  if (months < 12) return `${months} month${months === 1 ? "" : "s"} ago`;
  const years = Math.round(days / 365);
  return `${years} year${years === 1 ? "" : "s"} ago`;
}

export function absoluteDate(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

// "3 weeks ago — Oct 12, 2026" (Phase 7 D1).
export function relativeAndAbsolute(iso: string | null | undefined): string | null {
  const relative = relativeTime(iso);
  const absolute = absoluteDate(iso);
  if (!relative && !absolute) return null;
  if (!relative) return absolute;
  if (!absolute) return relative;
  return `${relative} — ${absolute}`;
}
