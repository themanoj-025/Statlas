import { formatDate, formatDateTime } from "@/lib/format";

export function RecencyLine({
  snapshotDate,
  computedDate,
  source,
}: {
  snapshotDate: string | null | undefined;
  computedDate?: string | null;
  source?: string | null;
}) {
  const parts = [
    snapshotDate ? `Data as of ${formatDate(snapshotDate)}` : null,
    computedDate ? `computed on ${formatDateTime(computedDate)}` : null,
    source ? `source: ${source}` : null,
  ].filter(Boolean);

  if (!parts.length) return null;
  return (
    <p className="recency">
      {parts.map((part) => (
        <span key={part}>{part}</span>
      ))}
    </p>
  );
}
