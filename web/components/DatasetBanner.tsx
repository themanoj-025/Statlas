"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

export function DatasetBanner() {
  const pathname = usePathname();
  const [mode, setMode] = useState<string | null>(null);
  const [note, setNote] = useState<string>("");

  // Embed pages are bare iframe targets (Phase 3 C3): no banner inside embeds.
  if (pathname.startsWith("/embed/")) return null;

  useEffect(() => {
    let cancelled = false;
    fetch(`${process.env.NEXT_PUBLIC_STATLAS_API_URL}/api/v1/meta`, { cache: "no-store" })
      .then((res) => (res.ok ? res.json() : null))
      .then((meta) => {
        if (cancelled || !meta?.dataset) return;
        setMode(meta.dataset.mode);
        setNote(meta.dataset.note ?? "");
      })
      .catch(() => {
        /* banner is non-blocking; the error state lives on data pages */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (mode === "production") return null;

  return (
    <div className="dataset-banner" role="status">
      <span>
        <strong>Development dataset.</strong>{" "}
        {note ||
          "Serving labeled fixture data. A full data refresh must run before production launch."}
      </span>
    </div>
  );
}
