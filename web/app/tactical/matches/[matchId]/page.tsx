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

import { OverviewTab, NetworkTab, HeatmapTab, FormationTab } from "./tabs"
