"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { EmbedTrend } from "@/components/EmbedTrend";
import type { MetricMeta } from "@/lib/types";
import { decodeTrendQuery } from "@/lib/share";

/**
 * /embed/trend — the iframe target for a shared trend chart (Part C3).
 * Reproduces the exact lines/window/mode from the permalink's query string.
 */
export default function EmbedTrendPage() {
  return (
    <Suspense fallback={<div className="embed-widget"><p>Loading embed…</p></div>}>
      <EmbedTrendInner />
    </Suspense>
  );
}

function EmbedTrendInner() {
  const searchParams = useSearchParams();
  const [metricMeta, setMetricMeta] = useState<Record<string, MetricMeta>>({});
  const config = useMemo(
    () => decodeTrendQuery(searchParams.toString()),
    [searchParams]
  );

  useEffect(() => {
    let cancelled = false;
    fetch(`${process.env.NEXT_PUBLIC_STATLAS_API_URL}/api/v1/meta`, { cache: "no-store" })
      .then((res) => (res.ok ? (res.json() as Promise<{ metrics: Record<string, MetricMeta> }>) : null))
      .then((meta) => {
        if (!cancelled && meta) setMetricMeta(meta.metrics);
      })
      .catch(() => {
        /* the embed shows its empty state if metrics can't be named */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <EmbedTrend
      slugs={config.players}
      metrics={config.metrics}
      window={config.window}
      mode={config.mode}
      metricMeta={metricMeta}
    />
  );
}
