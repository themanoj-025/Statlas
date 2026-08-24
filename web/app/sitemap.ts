import type { MetadataRoute } from "next";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || "http://localhost:8000";

/**
 * Fetch slugs from the API with a timeout and fallback.
 * Returns an empty array on any failure — sitemap always builds.
 */
async function fetchSlugs(path: string, timeoutMs = 5000): Promise<string[]> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const res = await fetch(`${API_URL}${path}`, {
      signal: controller.signal,
      next: { revalidate: 3600 },
    });
    clearTimeout(timer);
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

/**
 * Dynamic sitemap.xml — Constitution §5: public pages (methodology,
 * player profiles, league pages) must be crawlable for SEO.
 *
 * Static routes are always included. Dynamic routes (players, leagues)
 * are fetched from the API at build time with a timeout + fallback.
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl =
    process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

  const now = new Date();

  // Static public routes — always crawlable
  const staticRoutes: MetadataRoute.Sitemap = [
    { url: baseUrl, lastModified: now, changeFrequency: "daily", priority: 1.0 },
    { url: `${baseUrl}/positions`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${baseUrl}/compare`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${baseUrl}/trend`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${baseUrl}/search`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: `${baseUrl}/data-coverage`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${baseUrl}/methodology`, lastModified: now, changeFrequency: "monthly", priority: 0.7 },
    { url: `${baseUrl}/archetypes`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: `${baseUrl}/about`, lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    { url: `${baseUrl}/pricing`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${baseUrl}/changelog`, lastModified: now, changeFrequency: "weekly", priority: 0.4 },
    { url: `${baseUrl}/help`, lastModified: now, changeFrequency: "monthly", priority: 0.4 },
    // Transfer intelligence pages
    { url: `${baseUrl}/transfers`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: `${baseUrl}/transfers/candidates`, lastModified: now, changeFrequency: "weekly", priority: 0.6 },
    { url: `${baseUrl}/transfers/opportunities`, lastModified: now, changeFrequency: "weekly", priority: 0.6 },
    // Legal pages
    { url: `${baseUrl}/legal/terms`, lastModified: now, changeFrequency: "yearly", priority: 0.2 },
    { url: `${baseUrl}/legal/privacy`, lastModified: now, changeFrequency: "yearly", priority: 0.2 },
  ];

  // Dynamic routes — fetch player and league slugs from the API
  const [playerSlugs, leagueSlugs] = await Promise.all([
    fetchSlugs("/api/v1/players/search?q=a&limit=5000"),
    fetchSlugs("/api/v1/leagues?limit=200"),
  ]);

  const playerRoutes: MetadataRoute.Sitemap = playerSlugs.map((slug) => ({
    url: `${baseUrl}/players/${slug}`,
    lastModified: now,
    changeFrequency: "weekly" as const,
    priority: 0.8,
  }));

  const leagueRoutes: MetadataRoute.Sitemap = leagueSlugs.map((slug) => ({
    url: `${baseUrl}/leagues/${slug}`,
    lastModified: now,
    changeFrequency: "weekly" as const,
    priority: 0.7,
  }));

  return [...staticRoutes, ...playerRoutes, ...leagueRoutes];
}
