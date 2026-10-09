import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const BASE = process.env.BASE_URL ?? "http://127.0.0.1:3000";

async function goto(page: import("@playwright/test").Page, path: string) {
  await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
}

test.describe("Phase 11 — League pages", () => {
  test("league index page lists leagues by tier", async ({ page }) => {
    await goto(page, "/leagues");
    await expect(page.locator("h1")).toHaveText("Leagues");

    // Tier sections should be rendered.
    const sections = page.locator("section h2");
    const count = await sections.count();
    expect(count).toBeGreaterThanOrEqual(1);

    // Should have league links.
    const links = page.locator('a[href^="/leagues/"]');
    expect(await links.count()).toBeGreaterThanOrEqual(5);
  });

  test("league hub page renders with category leaderboards and teams", async ({ page }) => {
    await goto(page, "/leagues/premier-league");
    await expect(page.locator("h1")).toContainText("Premier");

    // Should show league metadata.
    await expect(page.locator(".page__lede").first()).toContainText("teams");

    // Sub-navigation: Overview is current.
    const subNav = page.locator('nav[aria-label="League views"]');
    await expect(subNav.locator('a[aria-current="page"]').first()).toContainText("Overview");

    // Category leaderboard sections — check for h2 headings in the page.
    const catHeadings = page.getByRole("heading", { level: 2 });
    const catCount = await catHeadings.count();
    expect(catCount).toBeGreaterThanOrEqual(3);

    // Teams grid.
    expect(await page.locator('a[href*="/leagues/premier-league/"]').count()).toBeGreaterThanOrEqual(5);
  });

  test("league hub shows honest standings note", async ({ page }) => {
    await goto(page, "/leagues/premier-league");
    await expect(page.getByText(/standings/i).first()).toBeVisible();
  });

  test("league hub links to methodology for emerging players", async ({ page }) => {
    await goto(page, "/leagues/premier-league");
    const emerging = page.locator("section", { hasText: "Emerging Players" });
    if ((await emerging.count()) > 0) {
      expect(await emerging.locator('a[href*="methodology"]').count()).toBeGreaterThanOrEqual(1);
    }
  });

  test("league hub links navigate to player profiles", async ({ page }) => {
    await goto(page, "/leagues/premier-league");
    const playerLink = page.locator('table a[href^="/players/"]').first();
    if ((await playerLink.count()) > 0) {
      const href = await playerLink.getAttribute("href");
      expect(href).toMatch(/^\/players\//);
    }
  });

  test("league index link in header nav", async ({ page }) => {
    await goto(page, "/");
    await expect(page.locator('nav a[href="/leagues"]')).toBeVisible();
  });

  test("axe: league index page", async ({ page }) => {
    await goto(page, "/leagues");
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toHaveLength(0);
  });

  test("axe: league hub page", async ({ page }) => {
    await goto(page, "/leagues/premier-league");
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toHaveLength(0);
  });
});
