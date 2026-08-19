"use client";

import { useState } from "react";

export default function TacticalPage() {
  const [matchId, setMatchId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!matchId.trim()) return;
    setLoading(true);
    setError(null);
    // Navigate to the match tactical page
    window.location.href = `/tactical/matches/${matchId.trim()}`;
  };

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-2">Tactical Intelligence</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-8">
        Passing networks, pressure maps, possession heatmaps, and formation analysis
        powered by event-level data from StatsBomb.
      </p>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">Match Analysis</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Enter a match ID to view tactical analysis. Event-level tactical data is
          currently available for select StatsBomb Open Data competitions.
        </p>
        <div className="flex gap-3">
          <input
            type="text"
            value={matchId}
            onChange={(e) => setMatchId(e.target.value)}
            placeholder="Enter match ID (e.g. 7576 from StatsBomb)"
            className="flex-1 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2
                       bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                       focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <button
            onClick={handleSearch}
            disabled={loading || !matchId.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700
                       disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "Loading..." : "Analyze"}
          </button>
        </div>
        {error && (
          <p className="mt-3 text-red-600 dark:text-red-400 text-sm">{error}</p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <FeatureCard
          title="Passing Networks"
          description="Interactive directed graph showing pass flows, player centrality, and tactical style detection."
          icon="⚽"
        />
        <FeatureCard
          title="Pressure & Possession Maps"
          description="Zone-based heatmaps showing where teams press and where they spend possession time."
          icon="🗺️"
        />
        <FeatureCard
          title="Formation Analysis"
          description="Automatic formation detection, stability tracking, and player conformity analysis."
          icon="📐"
        />
      </div>

      <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 text-sm">
        <p className="font-semibold text-blue-800 dark:text-blue-300">Data Coverage Notice</p>
        <p className="text-blue-700 dark:text-blue-400 mt-1">
          Tactical analysis requires event-level match data with exact player coordinates.
          This data is currently available for select StatsBomb Open Data competitions
          (UEFA Champions League, FA Cup, select World Cup matches, and other released
          competitions). Coverage is never implied beyond what has been synced.
        </p>
      </div>
    </main>
  );
}

function FeatureCard({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon: string;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-5">
      <div className="text-3xl mb-3">{icon}</div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
    </div>
  );
}
