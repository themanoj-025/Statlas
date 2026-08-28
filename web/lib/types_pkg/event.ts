export type StatsBombCompetition = {
  competition_id: string;
  season_id: string;
  competition_name: string;
  seasons_available: string[];
  last_successful_scrape: string | null;
  status: string;
};

export type EventCompetition = {
  competition_id: string;
  competition_name: string;
  season: string;
  matches: number;
};

export type EventMatch = {
  match_id: string;
  competition_id: string;
  competition_name: string;
  season: string;
};

export type ShotEvent = {
  event_id: string;
  match_id: string;
  minute: number | null;
  x: number | null;
  y: number | null;
  outcome: string | null;
  competition_id: string;
  competition_name: string;
  season: string | null;
  xg: number | null;
  body_part: string | null;
  technique: string | null;
};

export type PassEvent = {
  event_id: string;
  match_id: string;
  minute: number | null;
  x: number | null;
  y: number | null;
  outcome: string | null;
  competition_id: string;
  competition_name: string;
  season: string | null;
  end_x: number | null;
  end_y: number | null;
  pass_type: string | null;
  recipient: string | null;
  length: number | null;
  angle: number | null;
  progressive: boolean;
};

// --- Phase 4: accounts + billing -------------------------------------------

export type PassNode = {
  player_id: number;
  degree_centrality: number;
  betweenness_centrality: number;
  clustering_coefficient: number;
  pass_count: number;
  pass_success_rate: number;
  avg_x: number | null;
  avg_y: number | null;
};

export type PassEdge = {
  from: number;
  to: number;
  weight: number;
};

export type PassingNetworkResult = {
  match_id: string;
  phase: string;
  attribution: string;
  network: {
    nodes: PassNode[];
    edges: PassEdge[];
    total_passes: number;
  };
  style: TacticalStyle;
  anomalies: TacticalAnomaly[];
};

