"use client";

import type { Meta, SearchResultEntry, SearchCondition, ConditionOperator, QueryDefinition } from "@/lib/types";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { AddToShortlist } from "@/components/AddToShortlist";
import { useAuth } from "@/components/AuthProvider";

export function ConditionRow({
  index,
  cond,
  meta,
  onChange,
  onRemove,
}: {
  index: number;
  cond: SearchCondition;
  meta: Meta;
  onChange: (patch: Partial<SearchCondition>) => void;
  onRemove: () => void;
}) {
  const metric = meta.metrics[cond.metric];
  const isPercentile = cond.operator.startsWith("percentile");
  const operators = isPercentile ? PERCENTILE_OPERATORS : RAW_OPERATORS;
  const rowId = `cond-${index}`;

  // Metric options grouped by position applicability (same sets as the Radar
  // tool: outfield vs GK), plus a Raw values group for minutes.
  const outfieldMetrics = meta.position_groups.filter((g) => g.code !== "GK").flatMap((g) => g.metric_ids);
  const gkMetrics = meta.position_groups.find((g) => g.code === "GK")?.metric_ids ?? [];
  const allOutfield = Array.from(new Set(outfieldMetrics));
  const allGk = Array.from(new Set(gkMetrics));
  const shown = metric ? (allOutfield.includes(cond.metric) ? allOutfield : allGk) : allOutfield;

  return (
    <li className="query-builder__condition">
      <div className="query-builder__condition-metric">
        <label className="field__label" htmlFor={`${rowId}-metric`}>
          Metric
        </label>
        <select
          id={`${rowId}-metric`}
          className="select"
          value={cond.metric}
          onChange={(e) => {
            const next = e.target.value;
            // Switching between percentile/raw metrics resets the operator to
            // something valid for the new metric's condition type.
            const isRaw = next === "minutes_played";
            onChange({
              metric: next,
              operator: isRaw ? "gte" : "percentile_gte",
              value: isRaw ? 1500 : 70,
              value_max: null,
            });
          }}
        >
          <optgroup label="Outfield">
            {allOutfield.map((mid) => (
              <option key={mid} value={mid}>
                {meta.metrics[mid]?.name ?? mid}
              </option>
            ))}
          </optgroup>
          <optgroup label="Goalkeeper">
            {allGk.map((mid) => (
              <option key={mid} value={mid}>
                {meta.metrics[mid]?.name ?? mid}
              </option>
            ))}
          </optgroup>
          <optgroup label="Raw values">
            <option value="minutes_played">Minutes played</option>
          </optgroup>
        </select>
      </div>

      <div className="query-builder__condition-op">
        <label className="field__label" htmlFor={`${rowId}-op`}>
          {isPercentile ? "Percentile" : "Value"}
        </label>
        <select
          id={`${rowId}-op`}
          className="select"
          value={cond.operator}
          onChange={(e) => onChange({ operator: e.target.value as ConditionOperator, value_max: null })}
        >
          {operators.map((op) => (
            <option key={op.value} value={op.value}>
              {op.label}
            </option>
          ))}
        </select>
      </div>

      <div className="query-builder__condition-value">
        <label className="field__label" htmlFor={`${rowId}-value`}>
          {isPercentile ? "Percentile" : cond.metric === "minutes_played" ? "Minutes" : "Value"}
        </label>
        <input
          id={`${rowId}-value`}
          className="input"
          type="number"
          min={isPercentile ? 0 : 0}
          max={isPercentile ? 100 : undefined}
          value={Number.isFinite(cond.value) ? cond.value : ""}
          onChange={(e) => onChange({ value: e.target.value === "" ? 0 : Number(e.target.value) })}
        />
      </div>

      {(cond.operator === "between" || cond.operator === "percentile_between") && (
        <div className="query-builder__condition-value">
          <label className="field__label" htmlFor={`${rowId}-max`}>
            and
          </label>
          <input
            id={`${rowId}-max`}
            className="input"
            type="number"
            min={isPercentile ? 0 : 0}
            max={isPercentile ? 100 : undefined}
            value={Number.isFinite(cond.value_max ?? 0) ? (cond.value_max ?? 0) : ""}
            onChange={(e) => onChange({ value_max: e.target.value === "" ? 0 : Number(e.target.value) })}
          />
        </div>
      )}

      <div className="query-builder__condition-note">
        {metric ? (
          <span className="field__hint">
            {metric.name} — {metric.definition}
          </span>
        ) : (
          <span className="field__hint">Raw minutes played across the season.</span>
        )}
      </div>

      <button type="button" className="button button--sm button--ghost query-builder__remove" aria-label={`Remove condition ${index + 1}`} onClick={onRemove}>
        <X size={13} aria-hidden="true" />
      </button>
    </li>
  );
}
