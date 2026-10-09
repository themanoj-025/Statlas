import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Phase 5 — launch content e2e (Part A deliverables + Part D gate).
 *
 * Covers the NEW Phase 5 surfaces: methodology worked example, about, help,
 * pricing FAQ, and the report-a-data-error mechanism on player/team pages.
 * axe runs on every new page (the same CI-enforced standard from the
 * closeout and Phase 4); content assertions check the honesty requirements —
 * the worked example must show a real player with real numbers, the report
 * link must be a real (JS-free) mailto, and the pricing FAQ must answer the
 * downgrade question with the actual Phase 4 policy.
 */

const NEW_PAGES = ["/methodology", "/about", "/help", "/pricing"];

test("axe is green on all new Phase 5 pages", async ({ page }) => {
  for (const path of NEW_PAGES) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page }).analyze();
    expect(
      results.violations,
      `axe violations on ${path}: ${results.violations.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`,
    ).toEqual([]);
  }
});

test("methodology shows a worked example with real numbers", async ({ page }) => {
  await page.goto("/methodology");
  await page.getByRole("heading", { name: /worked example/i }).waitFor();
  // The real player used for the walkthrough (current dataset).
  await expect(page.getByText("Andrés Keller")).toBeVisible();
  // The weighted-sum row proves the math end to end.
  const table = page.getByRole("region", { name: /worked example/i });
  await expect(table.getByText("86.87")).toBeVisible();
  // Honesty clause: any mismatch is a bug to report, not a mystery.
  await expect(
    page.getByText(/if you spot any mismatch between this table and a number/i),
  ).toBeVisible();
});

test("about page states the solo-founder reality plainly", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByText(/one person\./i)).toBeVisible();
  await expect(page.getByText(/not a black box/i)).toBeVisible();
});

test("help page answers the missing-player question specifically", async ({ page }) => {
  await page.goto("/help");
  await page.getByRole("heading", { name: /help & faq/i }).waitFor();
  // Open the missing-player question, then check the concrete reasons.
  await page.getByText(/why is a player missing/i).click();
  await expect(page.getByText(/900 league minutes/i)).toBeVisible();
  await expect(page.getByText(/outside current data coverage/i)).toBeVisible();
});

test("pricing FAQ states the downgrade policy from Phase 4", async ({ page }) => {
  await page.goto("/pricing");
  const faq = page.getByRole("heading", { name: /questions worth asking/i });
  await faq.waitFor();
  // Downgrade question: saved work persists — the actual Phase 4 decision.
  const downgrade = page.getByText(/what happens to my saved comparisons/i).first();
  await downgrade.click();
  await expect(page.getByText(/everything you created while on pro stays yours/i)).toBeVisible();
});

test("report-a-data-error link exists on a player page and is a real mailto", async ({ page }) => {
  await page.goto("/players/andres-keller");
  const link = page.getByRole("link", { name: /report a data error/i });
  await expect(link).toBeVisible({ timeout: 15_000 });
  const href = await link.getAttribute("href");
  expect(href).toMatch(/^mailto:data@statlas\.com\?/);
  // Context pre-filled: the report names the player it is about.
  expect(href).toContain(encodeURIComponent("Andrés Keller"));
});

test("report-a-data-error link also exists on a team page", async ({ page }) => {
  await page.goto("/clubs/premier-league/brighton-hove-albion");
  const link = page.getByRole("link", { name: /report a data error/i });
  await expect(link).toBeVisible({ timeout: 15_000 });
  const href = await link.getAttribute("href");
  expect(href).toMatch(/^mailto:data@statlas\.com\?/);
});
