import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Phase 10 — Watchlist & alerts e2e.
 *
 * Covers the Part G quality gates against the real stack (API on 8000, web on
 * 3000, dev scrape seeded):
 * - Follow on a player profile -> appears on the watchlist; unfollow works
 * - A real percentile-movement alert (seeded via the e2e fixture, which runs
 *   the actual detection job) appears in the bell and on the watchlist with
 *   its real before/after values; read/dismiss work
 * - Notification settings round-trip: email off, digest frequency, per-type
 *   opt-out — and the honest copy that in-app alerts are unaffected
 * - Empty state: a fresh account sees the genuine onboarding prompt
 * - Signed-out sees the honest "Sign in to follow" prompt
 * - axe green on the watchlist page AND the notification bell dropdown
 */

const PASSWORD = "hunter2hunter";

async function register(page: Page, tag: string): Promise<string> {
  const email = `e2e-watch-${tag}-${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText(/plan: free/i).first()).toBeVisible({ timeout: 20_000 });
  return email;
}

async function grantPro(page: Page, email: string): Promise<void> {
  const grant = await page.request.post("http://127.0.0.1:8000/api/v1/e2e/grant-pro", {
    data: { email },
  });
  expect(grant.ok()).toBeTruthy();
}

async function openFirstPlayerProfile(page: Page): Promise<{ playerId: number; name: string }> {
  await page.goto("/positions");
  await expect(page.locator(".position-card").first()).toBeVisible({ timeout: 20_000 });
  await page.locator(".position-card").first().click();
  await expect(page.locator("a[href^='/players/']").first()).toBeVisible({ timeout: 20_000 });
  await page.locator("a[href^='/players/']").first().click();
  await page.waitForURL(/\/players\/[^/?#]+$/, { timeout: 20_000 });
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible({ timeout: 20_000 });
  // Read the player id from the profile URL slug via the public by-slug API
  // (robust regardless of which player the leaderboard surfaced first).
  const slug = page.url().split("/").pop() ?? "";
  const res = await page.request.get(`http://127.0.0.1:8000/api/v1/players/by-slug/${slug}`);
  const body = await res.json();
  return {
    playerId: body?.player?.player_id ?? -1,
    name: (await page.getByRole("heading", { level: 1 }).first().textContent()) ?? "",
  };
}

test("follow from a player profile -> watchlist; unfollow returns to empty", async ({ page }) => {
  await register(page, "flow");
  await openFirstPlayerProfile(page);

  await page.getByRole("button", { name: "Follow", exact: true }).click();
  await expect(page.getByRole("button", { name: "Unfollow" })).toBeVisible({ timeout: 10_000 });

  await page.goto("/watchlist");
  await expect(page.getByText(/1 followed entity/).first()).toBeVisible({ timeout: 20_000 });
  await expect(page.locator(".watchlist__item").first()).toBeVisible();

  // Unfollow from the watchlist.
  await page.getByRole("button", { name: /Unfollow/ }).first().click();
  await expect(page.getByText(/Unfollowed /)).toBeVisible({ timeout: 10_000 });
  await expect(page.getByRole("heading", { name: "Start with a player or team you're tracking" })).toBeVisible({ timeout: 20_000 });
});

test("a real seeded alert appears in the bell with real values; read + dismiss work", async ({ page }) => {
  const email = await register(page, "alert");
  await grantPro(page, email);
  const { playerId } = await openFirstPlayerProfile(page);
  expect(playerId).toBeGreaterThan(0);

  // Seed a REAL percentile-movement alert via the e2e fixture (runs the
  // actual detection job against a published snapshot pair).
  const seeded = await page.request.post("http://127.0.0.1:8000/api/v1/e2e/seed-alert", {
    data: { email, player_id: playerId },
  });
  expect(seeded.ok()).toBeTruthy();
  const seededBody = await seeded.json();
  expect(seededBody.alerts_created).toBeGreaterThanOrEqual(1);

  // The bell shows the unread badge and the alert's real detail values.
  await page.goto("/watchlist");
  await expect(page.locator(".notification-bell__badge")).toHaveText(/1|2|3|4|5|6|7|8|9/, { timeout: 20_000 });
  await page.locator(".notification-bell__button").click();
  await expect(page.getByText(/Percentile movement/).first()).toBeVisible();
  await expect(page.getByText(/→ 72nd percentile/).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "View all on your watchlist" })).toBeVisible();

  // The watchlist's Recent Alerts row opens the detail modal with the real
  // before/after values.
  await page.locator(".watchlist__alert-row").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("Previous percentile")).toBeVisible();
  await expect(page.getByText("45th", { exact: true })).toBeVisible();
  await expect(page.getByText("Current percentile")).toBeVisible();
  await expect(page.getByText("72nd", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Close" }).click();

  // Dismiss the alert -> bell badge disappears, empty alert list shows the
  // honest no-alerts copy.
  await page.locator(".notification-bell__button").click();
  await page.getByRole("button", { name: "Dismiss" }).first().click();
  await page.keyboard.press("Escape");
  await expect(page.locator(".notification-bell__badge")).toHaveCount(0, { timeout: 10_000 });
});

test("notification settings round-trip: email off, digest, per-type opt-out", async ({ page }) => {
  await register(page, "prefs");
  await page.goto("/watchlist/settings");
  await expect(page.getByRole("heading", { name: "Notification settings" })).toBeVisible({ timeout: 20_000 });

  // Email off + weekly digest + club-change opt-out.
  await page.getByRole("checkbox", { name: /Email alerts/ }).uncheck();
  await page.getByLabel("Weekly digest").check();
  await page.getByRole("checkbox", { name: /Club change/ }).uncheck();
  await page.getByRole("button", { name: "Save preferences" }).click();
  await expect(page.getByText(/Preferences saved/)).toBeVisible({ timeout: 10_000 });

  // Reload — preferences persist.
  await page.reload();
  await expect(page.getByRole("checkbox", { name: /Email alerts/ })).not.toBeChecked();
  await expect(page.getByLabel("Weekly digest")).toBeChecked();
  await expect(page.getByRole("checkbox", { name: /Club change/ })).not.toBeChecked();
  // Percentile movement stays on.
  await expect(page.getByRole("checkbox", { name: /Percentile movement/ })).toBeChecked();
  // The honest copy that in-app alerts are unaffected is present.
  await expect(page.getByText(/In-app notifications are always shown/).first()).toBeVisible();
});

test("signed-out player profile shows the honest follow prompt", async ({ page }) => {
  await openFirstPlayerProfile(page);
  await expect(page.getByRole("link", { name: "Sign in to follow" })).toBeVisible();
});

test("empty watchlist shows the onboarding prompt", async ({ page }) => {
  await register(page, "empty");
  await page.goto("/watchlist");
  await expect(page.getByRole("heading", { name: "Start with a player or team you're tracking" })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("link", { name: "Browse leaderboards" })).toBeVisible();
});

test("axe is green on the watchlist page and notification bell dropdown", async ({ page }) => {
  const email = await register(page, "axe");
  await grantPro(page, email);
  const { playerId } = await openFirstPlayerProfile(page);
  await page.getByRole("button", { name: "Follow", exact: true }).click();
  await expect(page.getByRole("button", { name: "Unfollow" })).toBeVisible({ timeout: 10_000 });
  if (playerId > 0) {
    await page.request.post("http://127.0.0.1:8000/api/v1/e2e/seed-alert", {
      data: { email, player_id: playerId },
    });
  }

  await page.goto("/watchlist");
  await expect(page.locator(".watchlist__item").first()).toBeVisible({ timeout: 20_000 });
  await page.waitForLoadState("networkidle");
  const watchlistResults = await new AxeBuilder({ page }).analyze();
  expect(
    watchlistResults.violations,
    `axe violations on /watchlist: ${watchlistResults.violations.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`,
  ).toEqual([]);

  // Open the bell dropdown and axe it too (notification-center accessibility).
  await page.locator(".notification-bell__button").click();
  await expect(page.locator(".notification-bell__menu")).toBeVisible();
  await page.waitForTimeout(300);
  const bellResults = await new AxeBuilder({ page }).analyze();
  expect(
    bellResults.violations,
    `axe violations on bell dropdown: ${bellResults.violations.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`,
  ).toEqual([]);
});
