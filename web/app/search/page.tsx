import type { Metadata } from "next";
import { api } from "@/lib/api";
import { SearchClient } from "./SearchClient";

export const metadata: Metadata = {
  title: "Search — multi-condition query builder",
  description:
    "Build precise multi-condition queries across the Statlas metric registry — percentile thresholds, minutes, age, position and league tier — save them for reuse, or start from a curated preset.",
  alternates: { canonical: "/search" },
};

export default async function SearchPage() {
  const [meta, presets] = await Promise.all([api.meta(), api.searchPresets()]);

  return (
    <div className="container page">
      <p className="kicker">Structured search</p>
      <h1 className="page__title">Query builder</h1>
      <p className="page__lede">
        Combine multiple conditions into one precise query — percentile thresholds relative to
        position group × league tier, raw minutes, age, position and tier. Every result shows the
        real values behind each condition, and every query respects the{" "}
        {meta.qualifying_minutes}-minute qualification floor automatically.
      </p>

      <SearchClient meta={meta} presets={presets.presets} />
    </div>
  );
}
