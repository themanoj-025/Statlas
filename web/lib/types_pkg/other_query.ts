export type ConditionOperator =
  | "percentile_gte"
  | "percentile_lte"
  | "percentile_between"
  | "gte"
  | "lte"
  | "between"
  | "eq";

export type QueryDefinition = {
  position_group?: string[] | null;
  league_tier?: string | null;
  age_max?: number | null;
  conditions: SearchCondition[];
  condition_logic: "AND";
};

export type ConditionValueShown = {
  metric: string;
  metric_name: string;
  operator: ConditionOperator;
  value: number;
  value_max: number | null;
  actual: number | null;
  condition_type: "percentile" | "raw";
};

