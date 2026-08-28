"use client";

import type { Meta, SearchResultEntry, SearchCondition, ConditionOperator, QueryDefinition } from "@/lib/types";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { AddToShortlist } from "@/components/AddToShortlist";
import { useAuth } from "@/components/AuthProvider";

function ResultRow({ entry }: { entry: SearchResultEntry }) {
  return (
    <tr>
      <td>
        <Link href={entry.slug ? `/players/${entry.slug}` : "#"} className="shortlist-entry__name">
          {entry.name}
        </Link>
        <span className="shortlist-entry__meta">
          {[entry.club, entry.league].filter(Boolean).join(" · ")}
        </span>
      </td>
      <td>{entry.position_group ? positionGroupLabel(entry.position_group) : "—"}</td>
      <td>{entry.age ?? "—"}</td>
      <td>{Math.round(entry.minutes).toLocaleString()}</td>
      <td>{entry.index !== null && entry.index !== undefined ? formatNumber(entry.index, 1) : "—"}</td>
      <td>
        <ul className="result-conditions" aria-label="Condition values">
          {entry.condition_values.map((cv) => (
            <li key={`${cv.metric}-${cv.operator}`} className="result-conditions__item">
              <span className="field__hint">{cv.metric_name}:</span>{" "}
              {cv.actual === null || cv.actual === undefined ? (
                <em className="field__hint">no data</em>
              ) : cv.condition_type === "percentile" ? (
                <strong>{formatNumber(cv.actual, 0)}th pct</strong>
              ) : (
                <strong>{formatNumber(cv.actual, cv.metric === "minutes_played" ? 0 : 2)}</strong>
              )}
            </li>
          ))}
        </ul>
      </td>
      <td>
        <AddToShortlist playerId={entry.player_id} playerName={entry.name} compact />
      </td>
    </tr>
  );
}
