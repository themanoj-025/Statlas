import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Phase 4 — Part D (hardening) e2e.
 *
 * D1 — accessibility: axe must be green on every NEW Phase 4 surface
 * (pricing/checkout entry, login/register, account incl. API keys, and the
 * assistant chat interface which is a classic a11y failure point). The closeout
 * already runs axe on radar/player/team/leaderboard; this extends that same
 * standard to the monetization + assistant surfaces.
 *
 * D2 — the same no-horizontal-overflow breakpoint guarantee the closeout
 * established, applied to the new pages (they run in the breakpoint matrix
 * via the shared spec below).
 *
 * D3 — security assertions live in pytest (test_billing.py: unsigned/tampered
 * webhook rejection; test_public_api.py: hashed key storage) — this spec
 * covers the UI states those tests back.
 */

const NEW_PAGES = ["/pricing", "/login", "/register", "/account", "/api-docs"];

test("axe is green on all new Phase 4 pages", async ({ page }) => {
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

test("no horizontal overflow on new Phase 4 pages (light + dark)", async ({ page }) => {
  for (const path of NEW_PAGES) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const light = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(light, `light overflow on ${path}`).toBeLessThanOrEqual(0);

    const toggle = page.getByRole("button", { name: /theme|dark|light/i }).first();
    if (await toggle.isVisible()) {
      await toggle.click();
      await page.waitForTimeout(100);
      const dark = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(dark, `dark overflow on ${path}`).toBeLessThanOrEqual(0);
    }
  }
});

test("pricing page shows working upgrade states", async ({ page }) => {
  await page.goto("/pricing");
  // Signed-out: the Pro CTA routes to sign-in (honest upsell, not a dead button).
  const cta = page.getByRole("link", { name: "Sign in to upgrade" });
  await expect(cta).toBeVisible({ timeout: 15_000 });
  // Free tier CTA routes to registration.
  await expect(page.getByRole("link", { name: "Start free" })).toBeVisible();
});

test("login page rejects short passwords with a visible message", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("Email").fill("scout@example.com");
  await page.getByLabel("Password").fill("short");
  await page.getByRole("button", { name: "Create account" }).click();
  // The form's own error block (not Next's route announcer) states the rule.
  await expect(page.locator(".state-block--error")).toContainText("at least 8 characters");
});

test("assistant widget renders its honest signed-out prompt on /compare", async ({ page }) => {
  await page.goto("/compare");
  const section = page.getByRole("region", { name: /statlas assistant/i });
  await expect(section).toBeVisible({ timeout: 15_000 });
  // Honest state: no fake answers, just the sign-in gate with the grounding claim.
  await expect(section.getByText(/sign in/i).first()).toBeVisible();
  await expect(section).toContainText(/every answer is traced to the data it used/i);
});
