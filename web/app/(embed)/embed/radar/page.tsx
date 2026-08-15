"use client";

import { Suspense, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { EmbedRadar } from "@/components/EmbedRadar";
import { decodeRadarQuery } from "@/lib/share";

/**
 * /embed/radar — the iframe target for a shared radar comparison (Part C3).
 * Reproduces the exact chart state from the permalink's query string.
 */
export default function EmbedRadarPage() {
  return (
    <Suspense fallback={<div className="embed-widget"><p>Loading embed…</p></div>}>
      <EmbedRadarInner />
    </Suspense>
  );
}

function EmbedRadarInner() {
  const searchParams = useSearchParams();
  const config = useMemo(
    () => decodeRadarQuery(searchParams.toString()),
    [searchParams]
  );
  return <EmbedRadar slugs={config.players} mode={config.mode} />;
}
