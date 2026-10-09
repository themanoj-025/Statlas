import type { Axis } from "@/lib/types";
import { formatNumber } from "@/lib/format";

const STATUS_HINT: Record<Axis["status"], string> = {
  qualified: "",
  below_floor: "Below the metric's sample floor — shown N/A, never a zero.",
  unranked_pool: "Qualified value, but the position-group pool was below the minimum size for this metric.",
  no_data: "No value for this metric in the latest snapshot.",
};

export function KeyStats({ axes }: { axes: Axis[] }) {
  return (
    <section className="card" aria-label="Key statistics">
      <h2 className="card__title" style={{ fontSize: "var(--text-lg)" }}>
        Key statistics
      </h2>
      <p className="card__subtitle">Real per-90 values from the latest stat snapshot.</p>
      <ul className="stat-list" style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {axes.map((axis) => (
          <li key={axis.id} className="stat-item">
            <span className="stat-item__label">
              {axis.name}
              <span className="chip" title={axis.definition}>
                {axis.unit}
              </span>
            </span>
            <span className="stat-item__value">
              {axis.status === "qualified" ? (
                <>
                  {formatNumber(axis.raw, 2)}
                  {axis.pct !== null && (
                    <span style={{ color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
                      {" "}
                      · p{Math.round(axis.pct)}
                    </span>
                  )}
                </>
              ) : (
                "N/A"
              )}
            </span>
            {STATUS_HINT[axis.status] && (
              <span className="stat-item__hint">{STATUS_HINT[axis.status]}</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
