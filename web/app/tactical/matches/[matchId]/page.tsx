"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type {
  PassingNetworkResult,
  PressureMap,
  PossessionMap,
  FormationResult,
  TacticalOverview,
} from "@/lib/types";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "network", label: "Passing Network" },
  { id: "pressure", label: "Pressure Map" },
  { id: "possession", label: "Possession Map" },
  { id: "formation", label: "Formation" },
] as const;

export default function MatchTacticalPage() {
  const params = useParams();
  const matchId = params.matchId as string;
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overview, setOverview] = useState<TacticalOverview | null>(null);

  useEffect(() => {
    if (!matchId) return;
    setLoading(true);
    setError(null);

    api.tacticalCoverage(matchId)
      .then((coverage) => {
        if (!coverage.has_coverage) {
          setError(coverage.message);
          setLoading(false);
          return null;
        }
        return api.tacticalOverview(matchId);
      })
      .then((data) => {
        if (data && !('detail' in data)) {
          setOverview(data as TacticalOverview);
        } else if (data) {
          setError((data as { detail?: string }).detail || "Failed to load tactical data");
        }
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : err.message))
      .finally(() => setLoading(false));
  }, [matchId]);

  if (loading) {
    return (
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-center py-20">
          <div className="text-gray-500 dark:text-gray-400">Loading tactical analysis...</div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-yellow-800 dark:text-yellow-300 mb-2">
            Tactical Data Not Available
          </h2>
          <p className="text-yellow-700 dark:text-yellow-400">{error}</p>
          <p className="text-sm text-yellow-600 dark:text-yellow-500 mt-3">
            Event-level tactical data is currently available for select StatsBomb Open Data
            competitions. Check the coverage page for available competitions.
          </p>
        </div>
      </main>
    );
  }

  if (!overview) return null;

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Match Tactical Analysis</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Match {matchId} · {overview.attribution}
        </p>
      </div>

      {/* Tab navigation */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 mb-6 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
              activeTab === tab.id
                ? "border-b-2 border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400"
                : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "overview" && <OverviewTab overview={overview} />}
      {activeTab === "network" && <NetworkTab data={overview} />}
      {activeTab === "pressure" && <HeatmapTab data={overview.pressure_map} title="Pressure Map" />}
      {activeTab === "possession" && <HeatmapTab data={overview.possession_map} title="Possession Map" />}
      {activeTab === "formation" && <FormationTab data={overview} />}
    </main>
  );
}

// ---------------------------------------------------------------------------
// Overview Tab
// ---------------------------------------------------------------------------

function OverviewTab({ overview }: { overview: TacticalOverview }) {
  const { style, formation, formation_stability, pressure_map, possession_map } = overview;
  const nodes = overview.passing_network.nodes;

  return (
    <div className="space-y-6">
      {/* Tactical Style */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-3">Tactical Style</h2>
        <div className="flex items-center gap-4 mb-3">
          <span className="text-2xl font-bold text-blue-600 dark:text-blue-400 capitalize">
            {style.style.replace("_", " ")}
          </span>
          <span className="text-sm text-gray-500">
            Confidence: {Math.round(style.confidence * 100)}%
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Total Passes</span>
            <p className="font-semibold">{style.metrics.total_passes}</p>
          </div>
          <div>
            <span className="text-gray-500">Avg Distance</span>
            <p className="font-semibold">{style.metrics.avg_pass_distance} yds</p>
          </div>
          <div>
            <span className="text-gray-500">Success Rate</span>
            <p className="font-semibold">{style.metrics.avg_success_rate}%</p>
          </div>
          <div>
            <span className="text-gray-500">Width Score</span>
            <p className="font-semibold">{Math.round(style.metrics.width_score * 100)}%</p>
          </div>
        </div>
        {style.factors.length > 0 && (
          <div className="mt-3 text-sm text-gray-600 dark:text-gray-400">
            <ul className="list-disc list-inside space-y-1">
              {style.factors.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          </div>
        )}
      </div>

      {/* Formation */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-3">Formation</h2>
        <div className="flex items-center gap-4">
          <span className="text-2xl font-bold">{formation.formation.formation_str}</span>
          <span className="text-sm text-gray-500">
            Stability: {Math.round(formation_stability.stability_score * 100)}%
          </span>
          {formation_stability.changes.length > 0 && (
            <span className="text-sm text-orange-600">
              {formation_stability.changes.length} formation change(s) detected
            </span>
          )}
        </div>
      </div>

      {/* Heatmap summaries */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <MiniHeatmap
          title="Pressure Density"
          data={pressure_map.zone_densities}
          total={pressure_map.total_actions}
        />
        <MiniHeatmap
          title="Possession Density"
          data={possession_map.zone_densities}
          total={possession_map.total_actions}
        />
      </div>

      {/* Anomalies */}
      {overview.anomalies.length > 0 && (
        <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4">
          <h3 className="font-semibold text-orange-800 dark:text-orange-300 mb-2">
            Tactical Anomalies
          </h3>
          <ul className="text-sm space-y-1">
            {overview.anomalies.map((a, i) => (
              <li key={i} className="text-orange-700 dark:text-orange-400">
                {a.detail}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Passing Network Tab
// ---------------------------------------------------------------------------

function NetworkTab({ data }: { data: TacticalOverview }) {
  const { nodes, edges, total_passes } = data.passing_network;
  const sortedNodes = [...nodes].sort(
    (a, b) => b.betweenness_centrality - a.betweenness_centrality
  );

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Passing Network ({total_passes} passes)</h2>

        {/* Player metrics table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b dark:border-gray-700">
                <th className="text-left py-2 px-3">Player</th>
                <th className="text-right py-2 px-3">Passes</th>
                <th className="text-right py-2 px-3">Success %</th>
                <th className="text-right py-2 px-3">Degree</th>
                <th className="text-right py-2 px-3">Betweenness</th>
                <th className="text-right py-2 px-3">Clustering</th>
              </tr>
            </thead>
            <tbody>
              {sortedNodes.map((node) => (
                <tr key={node.player_id} className="border-b dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="py-2 px-3 font-medium">Player {node.player_id}</td>
                  <td className="text-right py-2 px-3">{node.pass_count}</td>
                  <td className="text-right py-2 px-3">{node.pass_success_rate}%</td>
                  <td className="text-right py-2 px-3">{(node.degree_centrality * 100).toFixed(1)}%</td>
                  <td className="text-right py-2 px-3">{node.betweenness_centrality.toFixed(4)}</td>
                  <td className="text-right py-2 px-3">{node.clustering_coefficient.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top connections */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-3">Top Pass Connections</h3>
        <div className="space-y-2">
          {[...edges]
            .sort((a, b) => b.weight - a.weight)
            .slice(0, 10)
            .map((edge, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <div className="flex-1 flex items-center gap-2">
                  <span className="font-medium">Player {edge.from}</span>
                  <span className="text-gray-400">→</span>
                  <span className="font-medium">Player {edge.to}</span>
                </div>
                <div className="w-32 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{
                      width: `${(edge.weight / (edges[0]?.weight || 1)) * 100}%`,
                    }}
                  />
                </div>
                <span className="w-8 text-right text-gray-500">{edge.weight}</span>
              </div>
            ))}
        </div>
      </div>

      {/* Metrics explanation */}
      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 text-sm text-gray-600 dark:text-gray-400">
        <h4 className="font-semibold mb-2">Metric Definitions</h4>
        <ul className="space-y-1">
          <li><strong>Degree Centrality:</strong> Fraction of teammates this player passes to (connectivity).</li>
          <li><strong>Betweenness Centrality:</strong> How often this player sits on shortest paths between teammates (hub importance).</li>
          <li><strong>Clustering Coefficient:</strong> How interconnected this player&apos;s passing partners are (tight vs dispersed).</li>
        </ul>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Heatmap Tab
// ---------------------------------------------------------------------------

function HeatmapTab({
  data,
  title,
}: {
  data: PressureMap | PossessionMap;
  title: string;
}) {
  const zones = data.zone_densities;
  const maxVal = Math.max(...Object.values(zones), 0.01);

  // Grid layout: rows are defensive→attacking, cols are left→right
  const gridRows = ["attacking", "mid_attacking", "mid_defensive", "defensive"];
  const gridCols = ["left", "center", "right"];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold mb-2">{title}</h2>
      <p className="text-sm text-gray-500 mb-4">
        Total actions: {data.total_actions}
      </p>

      {/* Heatmap grid */}
      <div className="grid grid-cols-3 gap-1 max-w-md mx-auto mb-6">
        {gridRows.map((row) =>
          gridCols.map((col) => {
            const zone = `${row}_${col}`;
            const value = zones[zone] ?? 0;
            const intensity = value / maxVal;
            return (
              <div
                key={zone}
                className="aspect-square flex items-center justify-center rounded text-xs font-medium relative group"
                style={{
                  backgroundColor: `rgba(59, 130, 246, ${intensity * 0.8 + 0.05})`,
                  color: intensity > 0.5 ? "white" : "inherit",
                }}
                title={`${zone}: ${(value * 100).toFixed(1)}%`}
              >
                <span>{(value * 100).toFixed(1)}%</span>
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block
                                bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap z-10">
                  {zone}: {(value * 100).toFixed(1)}%
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Data table (accessible alternative) */}
      <details className="mt-4">
        <summary className="text-sm font-medium cursor-pointer text-blue-600 dark:text-blue-400">
          View data table (accessible)
        </summary>
        <table className="w-full text-sm mt-2">
          <thead>
            <tr className="border-b dark:border-gray-700">
              <th className="text-left py-2 px-3">Zone</th>
              <th className="text-right py-2 px-3">Density</th>
              <th className="text-right py-2 px-3">Count (est.)</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(zones)
              .sort(([, a], [, b]) => b - a)
              .map(([zone, density]) => (
                <tr key={zone} className="border-b dark:border-gray-700/50">
                  <td className="py-2 px-3 capitalize">{zone.replace(/_/g, " ")}</td>
                  <td className="text-right py-2 px-3">{(density * 100).toFixed(1)}%</td>
                  <td className="text-right py-2 px-3">
                    {Math.round(density * data.total_actions)}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Formation Tab
// ---------------------------------------------------------------------------

function FormationTab({ data }: { data: TacticalOverview }) {
  const { formation, formation_stability } = data;

  return (
    <div className="space-y-6">
      {/* Detected Formation */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-3">Detected Formation</h2>
        <div className="flex items-center gap-4 mb-4">
          <span className="text-3xl font-bold">{formation.formation.formation_str}</span>
          <span className="text-sm text-gray-500">
            Confidence: {Math.round(formation.formation.confidence * 100)}%
          </span>
        </div>

        <div className="grid grid-cols-4 gap-2 max-w-md text-center text-sm">
          <div className="font-semibold text-gray-500">GK</div>
          <div className="font-semibold text-gray-500">DEF</div>
          <div className="font-semibold text-gray-500">MID</div>
          <div className="font-semibold text-gray-500">FWD</div>
          {(() => {
            const lines = Object.values(formation.formation.player_lines);
            const gk = lines.filter((l) => l === "GK").length;
            const def = lines.filter((l) => l === "DEF").length;
            const mid = lines.filter((l) => l === "MID").length;
            const fwd = lines.filter((l) => l === "FWD").length;
            return (
              <>
                <div className="text-lg font-bold">{gk}</div>
                <div className="text-lg font-bold">{def}</div>
                <div className="text-lg font-bold">{mid}</div>
                <div className="text-lg font-bold">{fwd}</div>
              </>
            );
          })()}
        </div>
      </div>

      {/* Stability Timeline */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-3">Formation Stability</h2>
        <div className="flex items-center gap-4 mb-4">
          <span className="text-sm">
            Dominant: <strong>{formation_stability.dominant_formation}</strong>
          </span>
          <span className="text-sm text-gray-500">
            Stability: {Math.round(formation_stability.stability_score * 100)}%
          </span>
        </div>

        {/* Timeline */}
        <div className="space-y-1">
          {formation_stability.windows.map((w, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              <span className="w-20 text-gray-500 text-right">
                {w.minute_start}&apos;
              </span>
              <div
                className="flex-1 h-6 rounded flex items-center px-2 text-xs font-medium"
                style={{
                  backgroundColor:
                    w.formation === formation_stability.dominant_formation
                      ? "rgba(59, 130, 246, 0.2)"
                      : "rgba(249, 115, 22, 0.2)",
                  borderLeft: "3px solid",
                  borderColor:
                    w.formation === formation_stability.dominant_formation
                      ? "#3b82f6"
                      : "#f97316",
                }}
              >
                {w.formation}
              </div>
            </div>
          ))}
        </div>

        {/* Changes */}
        {formation_stability.changes.length > 0 && (
          <div className="mt-4 space-y-2">
            <h3 className="text-sm font-semibold text-orange-600">Formation Changes</h3>
            {formation_stability.changes.map((change, i) => (
              <div key={i} className="text-sm text-gray-600 dark:text-gray-400">
                ~{change.approximate_minute}&apos;: {change.from_formation} → {change.to_formation}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mini heatmap for overview
// ---------------------------------------------------------------------------

function MiniHeatmap({
  title,
  data,
  total,
}: {
  title: string;
  data: Record<string, number>;
  total: number;
}) {
  const maxVal = Math.max(...Object.values(data), 0.01);
  const gridRows = ["attacking", "mid_attacking", "mid_defensive", "defensive"];
  const gridCols = ["left", "center", "right"];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-sm font-semibold mb-2">{title} ({total} actions)</h3>
      <div className="grid grid-cols-3 gap-0.5">
        {gridRows.map((row) =>
          gridCols.map((col) => {
            const zone = `${row}_${col}`;
            const value = data[zone] ?? 0;
            const intensity = value / maxVal;
            return (
              <div
                key={zone}
                className="aspect-square rounded-sm"
                style={{
                  backgroundColor: `rgba(59, 130, 246, ${intensity * 0.8 + 0.05})`,
                }}
                title={`${zone}: ${(value * 100).toFixed(1)}%`}
              />
            );
          })
        )}
      </div>
    </div>
  );
}
