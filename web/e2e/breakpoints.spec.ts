import { expect, test } from "@playwright/test";

/**
 * Closeout B4 — automated breakpoint testing.
 *
 * Replaces the manually-documented "tested at 375/768/1440px" claim with an
 * automated layout assertion: at each breakpoint (and in both themes) every
 * core page must have NO horizontal overflow — the document scroll width must
 * equal the viewport width. A table or grid that escapes its container fails
 * the build instead of being noted in a doc.
 *
 * The three viewport sizes come from the Playwright project matrix
 * (mobile-375 / tablet-768 / desktop-1440); the theme toggle is exercised per
 * page because dark mode changes token values that could affect layout.
 */

const CORE_PAGES = [
  "/",
  "/compare",
  "/players/erling-haaland",
  "/clubs/premier-league/manchester-city",
  "/leagues/premier-league/stats",
  "/positions",
  "/methodology",
  "/data-coverage",
];

async function toggleDark(page: import("@playwright/test").Page) {
  const toggle = page.getByRole("button", { name: /theme|dark|light/i }).first();
  if (await toggle.isVisible()) {
    await toggle.click();
  }
}

test("no horizontal overflow at this breakpoint (light + dark)", async ({ page }) => {
  for (const path of CORE_PAGES) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");

    // Light theme.
    const overflowLight = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(
      overflowLight,
      `light theme horizontal overflow on ${path} at ${page.viewportSize()?.width}px`,
    ).toBeLessThanOrEqual(0);

    // Dark theme — toggle only if the control exists; the page may already be
    // dark (theme persists in localStorage across navigations).
    await toggleDark(page);
    await page.waitForTimeout(100);
    const overflowDark = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(
      overflowDark,
      `dark theme horizontal overflow on ${path} at ${page.viewportSize()?.width}px`,
    ).toBeLessThanOrEqual(0);
  }
});
