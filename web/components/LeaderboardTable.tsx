"use client";

import Link from "next/link";
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type {
  LeaderboardEntry,
  LeaderboardResponse,
  MetricMeta,
  PositionGroupMeta,
} from "@/lib/types";
import { formatNumber, percentileBand, positionGroupLabel, tierLabel } from "@/lib/format";

type SortKey = "value" | "minutes" | "name" | "club";

type Filters = {
  league?: string;
  position?: string;
  metric: string;
  minMinutes?: number;
};

export function LeaderboardTable({
  initial,
  season,
  meta,
  fixedLeague,
  fixedPosition,
  fixedTier,
  metricOptions,
  title,
}: {
  initial: LeaderboardResponse;
  season: string;
  meta: {
    metrics: Record<string, MetricMeta>;
    position_groups: PositionGroupMeta[];
  };
  fixedLeague?: string;
  fixedPosition?: string;
  fixedTier?: string;
  metricOptions?: { id: string; name: string }[];
  title: string;
}) {
  const [data, setData] = useState<LeaderboardResponse>(initial);
  const [filters, setFilters] = useState<Filters>({
    league: fixedLeague,
    position: fixedPosition,
    metric: "si_index",
    minMinutes: undefined,
  });
  const [sortBy, setSortBy] = useState<SortKey>("value");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const options = metricOptions ?? [
    { id: "si_index", name: "Statlas Index" },
    ...Object.values(meta.metrics).map((m) => ({ id: m.id, name: m.name })),
  ];

  const load = useCallback(
    async (nextFilters: Filters, nextSortBy: SortKey, nextSortDir: "asc" | "desc", nextPage: number) => {
      setStatus("loading");
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_STATLAS_API_URL}/api/v1/leaderboard?${new URLSearchParams({
            metric: nextFilters.metric,
            season,
            ...(nextFilters.league ? { league: nextFilters.league } : {}),
            ...(fixedTier ? { tier: fixedTier } : {}),
            ...(nextFilters.position ? { position: nextFilters.position } : {}),
            ...(nextFilters.minMinutes ? { min_minutes: String(nextFilters.minMinutes) } : {}),
            sort_by: nextSortBy,
            ...(nextSortBy !== "value" ? { sort_dir: nextSortDir } : {}),
            page: String(nextPage),
            limit: "25",
          })}`,
          { cache: "no-store" }
        );
        if (!res.ok) throw new Error(`leaderboard ${res.status}`);
        setData(await res.json());
        setStatus("idle");
      } catch (err) {
        setStatus("error");
        setErrorMsg(err instanceof Error ? err.message : "query failed");
      }
    },
    [season, fixedTier]
  );

  useEffect(() => {
    void load(filters, sortBy, sortDir, page);
  }, [filters, sortBy, sortDir, page, load]);

  const toggleSort = (key: SortKey) => {
    if (sortBy === key) {
      setSortDir((dir) => (dir === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(key);
      setSortDir(key === "minutes" ? "desc" : key === "value" ? "desc" : "asc");
    }
    setPage(1);
  };

  const pageCount = Math.max(1, Math.ceil(data.total / 25));
  const metricSpec = meta.metrics[filters.metric];
  const valueLabel = filters.metric === "si_index" ? "Index" : metricSpec?.name ?? "Value";
  const lowerIsBetter = metricSpec?.lower_is_better ?? false;

  const header = (key: SortKey, label: string) => (
    <th
      scope="col"
      className="th-sort"
      aria-sort={sortBy === key ? (sortDir === "desc" ? "descending" : "ascending") : "none"}
      onClick={() => toggleSort(key)}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggleSort(key);
        }
      }}
    >
      {label}
      {sortBy === key &&
        (sortDir === "desc" ? (
          <ArrowDown className="th-sort__arrow" size={12} aria-hidden="true" />
        ) : (
          <ArrowUp className="th-sort__arrow" size={12} aria-hidden="true" />
        ))}
    </th>
  );

  return (
    <section aria-label={title}>
      <div className="toolbar">
        <div className="field">
          <label className="field__label" htmlFor="lb-metric">Metric</label>
          <select
            id="lb-metric"
            className="select"
            value={filters.metric}
            onChange={(e) => {
              setFilters((f) => ({ ...f, metric: e.target.value }));
              setPage(1);
            }}
          >
            {options.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>

        {!fixedLeague && (
          <div className="field">
            <label className="field__label" htmlFor="lb-league">League</label>
            <select
              id="lb-league"
              className="select"
              value={filters.league ?? ""}
              onChange={(e) => {
                setFilters((f) => ({ ...f, league: e.target.value || undefined }));
                setPage(1);
              }}
            >
              <option value="">All leagues in tier</option>
              <option value="premier-league">Premier League</option>
              <option value="la-liga">La Liga</option>
              <option value="serie-a">Serie A</option>
              <option value="bundesliga">Bundesliga</option>
              <option value="ligue-1">Ligue 1</option>
              <option value="eredivisie">Eredivisie</option>
              <option value="primeira-liga">Primeira Liga</option>
              <option value="championship">Championship</option>
            </select>
          </div>
        )}

        {!fixedPosition && (
          <div className="field">
            <label className="field__label" htmlFor="lb-position">Position group</label>
            <select
              id="lb-position"
              className="select"
              value={filters.position ?? ""}
              onChange={(e) => {
                setFilters((f) => ({ ...f, position: e.target.value || undefined }));
                setPage(1);
              }}
            >
              <option value="">All positions</option>
              {meta.position_groups.map((g) => (
                <option key={g.code} value={g.code}>
                  {g.plural}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="field">
          <label className="field__label" htmlFor="lb-minutes">Minutes threshold</label>
          <select
            id="lb-minutes"
            className="select"
            value={filters.minMinutes ?? ""}
            onChange={(e) => {
              setFilters((f) => ({ ...f, minMinutes: e.target.value ? Number(e.target.value) : undefined }));
              setPage(1);
            }}
          >
            <option value="">Qualifying only (900+)</option>
            <option value="1000">1,000+</option>
            <option value="1500">1,500+</option>
            <option value="2000">2,000+</option>
          </select>
        </div>
      </div>

      {status === "error" && (
        <div className="state-block state-block--error" role="alert" style={{ marginBottom: "var(--space-3)" }}>
          <p className="state-block__title">We couldn&rsquo;t load this leaderboard.</p>
          <p className="state-block__body">
            {errorMsg} It will rebuild on the next weekly refresh (Wednesday 03:00 UTC) — use Retry
            to check again now.
          </p>
          <div className="state-block__actions">
            <button type="button" className="button button--sm" onClick={() => void load(filters, sortBy, sortDir, page)}>
              Retry
            </button>
          </div>
        </div>
      )}

      <div className="table-wrap">
        <table
          className="table table--sticky-first"
          aria-label={`${title}, sorted by ${valueLabel}${lowerIsBetter ? " ascending (lower is better)" : " descending"}`}
        >
          <thead>
            <tr>
              <th scope="col">Rank</th>
              {header("name", "Player")}
              {header("club", "Club")}
              <th scope="col">Pos</th>
              {header("minutes", "Min")}
              <th scope="col">M</th>
              {header("value", valueLabel)}
            </tr>
          </thead>
          <tbody>
            {status === "loading" &&
              Array.from({ length: 8 }, (_, i) => (
                <tr key={`skeleton-${i}`} aria-hidden="true">
                  {Array.from({ length: 7 }, (_, j) => (
                    <td key={j}>
                      <span className="skeleton" style={{ display: "inline-block", width: j === 0 ? 24 : j === 6 ? 44 : 88, height: 14 }} />
                    </td>
                  ))}
                </tr>
              ))}

            {status !== "loading" &&
              data.entries.map((entry, index) => {
                const rank = (page - 1) * 25 + index + 1;
                return (
                  <tr key={entry.player_id}>
                    <td className="num">{rank}</td>
                    <td>
                      <Link href={entry.slug ? `/players/${entry.slug}` : "#"}>{entry.name}</Link>
                    </td>
                    <td>{entry.club ?? "—"}</td>
                    <td className="num">{entry.position_group}</td>
                    <td className="num">{Math.round(entry.minutes).toLocaleString()}</td>
                    <td className="num">{entry.matches}</td>
                    <td className="num" style={{ color: percentileBand(entry.value), fontWeight: 600 }}>
                      {formatNumber(entry.value, entry.value >= 100 ? 0 : 1)}
                    </td>
                  </tr>
                );
              })}

            {status !== "loading" && !data.entries.length && (
              <tr>
                <td colSpan={7}>
                  <div className="state-block state-block--sunken" role="status">
                    <p className="state-block__title">No players meet the qualifying threshold here yet.</p>
                    <p className="state-block__body">
                      No players pass the {filters.minMinutes ?? 900}-minute threshold for these
                      filters this season — check back after more matches are played, or loosen the
                      filters above.
                    </p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="pagination">
        <p className="pagination__info">
          {data.total.toLocaleString()} qualifying {data.total === 1 ? "player" : "players"}
          {filters.position ? ` · ${positionGroupLabel(filters.position)}` : ""}
          {fixedTier ? ` · ${tierLabel(fixedTier)}` : ""} · {season}
        </p>
        <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}>
          <button
            type="button"
            className="button button--secondary button--sm"
            disabled={page <= 1 || status === "loading"}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            aria-label="Previous page"
          >
            <ChevronLeft size={14} aria-hidden="true" /> Prev
          </button>
          <span className="pagination__info">
            Page {page} of {pageCount}
          </span>
          <button
            type="button"
            className="button button--secondary button--sm"
            disabled={!data.has_more || status === "loading"}
            onClick={() => setPage((p) => p + 1)}
            aria-label="Next page"
          >
            Next <ChevronRight size={14} aria-hidden="true" />
          </button>
        </div>
      </div>
    </section>
  );
}
