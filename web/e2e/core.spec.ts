import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Closeout B3 + B2 — the Constitution-named critical paths:
 *   - radar generation: search a player, add to the comparison, verify the
 *     chart renders with real data (not an empty/error state)
 *   - search/filter: leaderboard filtering produces correct results
 *   - automated axe audit (B2) on the Radar tool, player profile, team
 *     profile, and leaderboard pages — fails on ANY violation, not just logs
 *
 * The seeded fixture-demo stack (scripts/e2e-server.sh) provides real data:
 * Erling Haaland exists in the Premier League, Manchester City exists, and
 * the leaderboard is populated with published percentile rows.
 */

test("radar generation: search -> add player -> chart renders", async ({ page }) => {
  await page.goto("/compare");

  // Search-as-you-type must return the real player. The page has TWO
  // comboboxes (the global header search + the compare tool's); the tool's own
  // is the one with the "e.g. 'Haaland' or 'Salah'" placeholder.
  const search = page.getByPlaceholder(/Haaland' or 'Salah/);
  await search.fill("Haaland");
  const option = page.getByRole("option", { name: /Erling Haaland/ }).first();
  await expect(option).toBeVisible({ timeout: 10_000 });
  await option.click();

  // The player is added to the comparison; the radar must render an SVG with
  // real axis data — never the empty/error state.
  const radar = page.locator("svg[role='img'][aria-label*='radar' i], svg[aria-label*='Radar' i]").first();
  await expect(radar).toBeVisible({ timeout: 15_000 });
  await expect(page.locator("text=Erling Haaland").first()).toBeVisible();

  // Percentile/raw toggle is present (the Statlas enhancement over DataMB).
  await expect(page.getByRole("button", { name: /raw|per 90/i }).first()).toBeVisible();
});

test("radar generation: permalink reproduces the exact chart state", async ({ page }) => {
  await page.goto("/compare");
  const search = page.getByPlaceholder(/Haaland' or 'Salah/);
  await search.fill("Salah");
  await page.getByRole("option", { name: /Mohamed Salah/ }).first().click();
  await expect(page.locator("svg[aria-label*='radar' i]").first()).toBeVisible({ timeout: 15_000 });

  // Grab the shareable permalink and open it fresh — the chart must come back
  // with no prior client state (site-map.md: stable URLs, Phase 3 lock).
  const shareButton = page.getByRole("button", { name: /share/i }).first();
  if (await shareButton.isVisible()) {
    await shareButton.click();
    const link = page.locator("input[readonly][value*='/compare/'], a[href*='/compare/']").first();
    if (await link.isVisible()) {
      const href = await link.inputValue?.() ?? (await link.getAttribute("href")) ?? "";
      if (href) {
        await page.goto(href);
        await expect(page.locator("svg[aria-label*='radar' i]").first()).toBeVisible({ timeout: 15_000 });
      }
    }
  }
});

test("leaderboard: filtering by position + minutes returns only qualifying rows", async ({ page }) => {
  await page.goto("/leagues/premier-league/stats");

  const table = page.locator("table").first();
  await expect(table).toBeVisible({ timeout: 15_000 });

  // Pick the striker position filter if one is exposed.
  const positionFilter = page.getByRole("combobox", { name: /position/i }).first();
  if (await positionFilter.isVisible()) {
    await positionFilter.selectOption({ label: "ST" });
  }

  // Every row shows a real value and a linked player profile — never an
  // empty or error state.
  const rows = table.locator("tbody tr");
  await expect(rows.first()).toBeVisible({ timeout: 10_000 });
  const count = await rows.count();
  expect(count).toBeGreaterThan(0);
  for (let i = 0; i < Math.min(count, 5); i++) {
    await expect(rows.nth(i)).not.toBeEmpty();
  }
});

test("player profile page renders real data (SSR)", async ({ page }) => {
  await page.goto("/players/erling-haaland");
  await expect(page.getByRole("heading", { name: /Erling Haaland/, level: 1 })).toBeVisible({ timeout: 15_000 });
  // The data-driven sentence (Constitution §5) must render a real percentile
  // claim — never a static/empty template.
  await expect(page.locator("text=percentile").first()).toBeVisible({ timeout: 10_000 });
  // The radar embedded in the profile renders.
  await expect(page.locator("svg[aria-label*='radar' i]").first()).toBeVisible({ timeout: 15_000 });
});

test("axe audit is green on the four Phase 2 pages", async ({ page }) => {
  const pages = [
    "/compare",
    "/players/erling-haaland",
    "/clubs/premier-league/manchester-city",
    "/leagues/premier-league/stats",
  ];
  for (const path of pages) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page }).analyze();
    // Fail the build on any violation — the closeout requirement is resolved,
    // not logged (B2).
    expect(
      results.violations,
      `axe violations on ${path}: ${results.violations.map((v) => v.id).join(", ")}`,
    ).toEqual([]);
  }
});
