import type { MetadataRoute } from "next";

/**
 * Dynamic sitemap.xml — Constitution §5: public pages (methodology,
 * player profiles, league pages) must be crawlable for SEO.
 *
 * Static routes are listed here; dynamic routes (players, leagues)
 * would need a data fetch in production — for now, we include the
 * static routes and a note for future dynamic generation.
 */
export default function sitemap(): MetadataRoute.Sitemap {
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

  // TODO: In production, fetch player slugs and league slugs from the API
  // and add them as dynamic routes for full SEO coverage.
  // Example:
  // const players = await fetch(`${API_URL}/api/v1/players/search?q=a&limit=5000`);
  // const playerRoutes = players.map(p => ({
  //   url: `${baseUrl}/players/${p.slug}`,
  //   lastModified: now,
  //   changeFrequency: "weekly",
  //   priority: 0.8,
  // }));

  return staticRoutes;
}
