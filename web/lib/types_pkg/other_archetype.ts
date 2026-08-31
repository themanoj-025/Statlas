export type ArchetypeModel = {
  model_id: number;
  model_name: string;
  version: string;
  algorithm: string;
  n_clusters: number;
  silhouette_score: number | null;
  training_date: string | null;
  deployed_at: string | null;
  training_data_source: string;
};

export type ArchetypeDefinition = {
  cluster_id: number;
  name: string;
  description: string;
  player_count: number;
  distinguishing_features: {
    feature: string;
    cluster_value: number;
    global_value: number;
    difference: number;
  }[];
  example_players: {
    player_id: number;
    name: string;
  }[];
};

export type ArchetypeOverview = {
  model: ArchetypeModel | null;
  archetypes: ArchetypeDefinition[];
  total_players: number;
};

export type ArchetypeDetail = {
  model_id: number;
  cluster_id: number;
  archetype_name: string;
  archetype_description: string;
  total: number;
  limit: number;
  offset: number;
  players: ArchetypePlayer[];
};
