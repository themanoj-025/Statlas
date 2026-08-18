import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const BASE = process.env.BASE_URL ?? "http://127.0.0.1:3000";

async function goto(page: import("@playwright/test").Page, path: string) {
  await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
}

// Register a fresh user and return the email.
async function register(page: import("@playwright/test").Page, label: string) {
  const email = `${label}-${Date.now()}@example.com`;
  await goto(page, "/register");
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', "testpassword123");
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE}/account`, { timeout: 10000 });
  return email;
}

test.describe("Phase 13 — Dashboard", () => {
  test("signed-out user sees onboarding prompt", async ({ page }) => {
    await goto(page, "/dashboard");
    // Should show the sign-in prompt, not the dashboard content.
    await expect(page.getByText("Your personal dashboard")).toBeVisible();
    await expect(page.getByText("Sign in to see recently viewed")).toBeVisible();
    await expect(page.locator('a[href="/login"]').first()).toBeVisible();
    await expect(page.locator('a[href="/register"]').first()).toBeVisible();
  });

  test("signed-in user sees dashboard with workspace shortcuts", async ({ page }) => {
    await register(page, "dash-view");
    await goto(page, "/dashboard");

    // Dashboard title.
    await expect(page.locator("h1")).toContainText("Dashboard");

    // Workspace shortcuts section.
    await expect(page.getByText("Your workspace")).toBeVisible();
    await expect(page.getByText("Shortlists")).toBeVisible();
    await expect(page.getByText("Saved searches")).toBeVisible();
    await expect(page.getByText("Reports")).toBeVisible();
    await expect(page.getByText("Watchlist")).toBeVisible();

    // Recently viewed section (empty for new user).
    await expect(page.getByText("Recently viewed")).toBeVisible();

    // Trending section.
    await expect(page.getByText("Trending this week")).toBeVisible();

    // Saved players section.
    await expect(page.getByText("Saved players")).toBeVisible();

    // Recommended section.
    await expect(page.getByText("Recommended for you")).toBeVisible();
  });

  test("empty-state messages are present for new user", async ({ page }) => {
    await register(page, "dash-empty");
    await goto(page, "/dashboard");

    // Recently viewed empty state.
    await expect(
      page.getByText("Recently viewed players will appear here as you explore"),
    ).toBeVisible();

    // Trending empty state.
    await expect(
      page.getByText("Trending players will appear here based on sustained"),
    ).toBeVisible();

    // Saved players empty state.
    await expect(
      page.getByText("Bookmark players from their profile pages"),
    ).toBeVisible();

    // Recommended empty state.
    await expect(
      page.getByText("Recommended players will appear based on your interests"),
    ).toBeVisible();
  });

  test("workspace shortcut links navigate correctly", async ({ page }) => {
    await register(page, "dash-links");
    await goto(page, "/dashboard");

    // Click the Workspace shortcut card.
    await page.locator('a[href="/workspace"]').first().click();
    await page.waitForURL(`${BASE}/workspace`, { timeout: 10000 });
    await expect(page.locator("h1")).toContainText("Workspace");
  });

  test("header shows Dashboard link for signed-in users", async ({ page }) => {
    await register(page, "dash-header");
    await goto(page, "/dashboard");

    const dashLink = page.locator('header a[href="/dashboard"]');
    await expect(dashLink).toBeVisible();
    await expect(dashLink).toContainText("Dashboard");
  });

  test("axe: dashboard has no accessibility violations", async ({ page }) => {
    await register(page, "dash-axe");
    await goto(page, "/dashboard");

    const results = await new AxeBuilder({ page })
      .include("body")
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test("axe: signed-out dashboard has no accessibility violations", async ({
    page,
  }) => {
    await goto(page, "/dashboard");

    const results = await new AxeBuilder({ page })
      .include("body")
      .analyze();
    expect(results.violations).toEqual([]);
  });
});
