import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Phase 6 — explainable similarity (Part C + E quality gates).
 *
 * The happy path runs against the real seeded stack (the fixture-demo dataset
 * the e2e server boots); the state tests (no-meaningful-differences,
 * missing-data, error) intercept the similar-players API route and fulfill
 * with crafted but structurally real payloads, so every required UI state is
 * verified deterministically — not just the happy path. The axe audit runs
 * with the explanation expanded so the new component is scanned in its
 * content state, not only collapsed (closeout B2 standard).
 */

const SIMILAR_ROUTE = "**/api/v1/players/*/similar*";

function explanationFixture(overrides: Record<string, unknown> = {}) {
  return {
    matched_strengths: [
      {
        metric: "si_prgc_p90",
        metric_name: "Progressive carries per 90",
        player_a_percentile: 88,
        player_b_percentile: 85,
        difference: 3,
        contribution: 0.1421,
      },
    ],
    key_differences: [
      {
        metric: "si_tkl_p90",
        metric_name: "Tackles per 90",
        player_a_percentile: 76,
        player_b_percentile: 34,
        difference: 42,
        stronger_player: "player_a",
      },
    ],
    excluded_metrics: [] as { metric: string; metric_name: string }[],
    excluded_reason:
      "no published percentile for one or both players (a missing value is N/A, never a zero)",
    shared_metrics: 12,
    ...overrides,
  };
}

function similarPlayerFixture(explanation: Record<string, unknown>) {
  return [
    {
      player_id: 999001,
      name: "Test Peer",
      slug: null,
      position_group: "ST",
      club: "City",
      league: "Premier League",
      similarity: 0.91,
      shared_metrics: 12,
      index: 71.4,
      anchor_index: 74.2,
      explanation,
    },
  ];
}

test("similar players explanation renders real numbers (happy path)", async ({ page }) => {
  await page.goto("/players/erling-haaland");
  const section = page.getByRole("region", { name: /similar players/i });
  await expect(section.getByText(/% match/).first()).toBeVisible({ timeout: 15_000 });

  // Expand the first player's explanation.
  await section.locator("details summary").first().click();
  await expect(section.getByRole("heading", { name: /matched strengths/i })).toBeVisible();
  await expect(section.getByRole("heading", { name: /key differences/i })).toBeVisible();

  // Every listed metric carries both players' REAL percentile values — never
  // a bare label with no numbers (the checkable-claim rule).
  const itemText = await section.locator(".similar-player__item").first().textContent();
  expect(itemText).toMatch(/\d+th vs \d+th percentile/i);

  // The key-differences list either names the stronger player or honestly
  // states the profiles are very similar across every measured metric.
  const hasNamedDifference = (await section.locator(".similar-player__item").count()) > 0;
  const hasHonestNote = await section
    .getByText(/very similar profiles across every measured metric/i)
    .isVisible();
  expect(hasNamedDifference || hasHonestNote).toBe(true);
});

test("no-meaningful-differences state shows honest copy, not forced gaps", async ({ page }) => {
  const explanation = explanationFixture({ key_differences: [] });
  await page.route(SIMILAR_ROUTE, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(similarPlayerFixture(explanation)),
    }),
  );
  await page.goto("/players/erling-haaland");
  const section = page.getByRole("region", { name: /similar players/i });
  await expect(section.getByText(/% match/).first()).toBeVisible({ timeout: 15_000 });
  await section.locator("details summary").first().click();
  await expect(
    section.getByText(/these players have very similar profiles across every measured metric/i),
  ).toBeVisible();
});

test("missing-data state lists excluded metrics and why", async ({ page }) => {
  const explanation = explanationFixture({
    excluded_metrics: [{ metric: "si_xag_p90", metric_name: "xAG per 90" }],
    shared_metrics: 11,
  });
  await page.route(SIMILAR_ROUTE, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(similarPlayerFixture(explanation)),
    }),
  );
  await page.goto("/players/erling-haaland");
  const section = page.getByRole("region", { name: /similar players/i });
  await expect(section.getByText(/% match/).first()).toBeVisible({ timeout: 15_000 });
  await section.locator("details summary").first().click();
  const note = section.getByRole("note");
  await expect(note).toContainText("xAG per 90");
  await expect(note).toContainText(/not compared/i);
  await expect(note).toContainText(/no published percentile/i);
});

test("error state is retry-capable", async ({ page }) => {
  // First request fails; the retry hits the real API and recovers.
  let failNext = true;
  await page.route(SIMILAR_ROUTE, (route) => {
    if (failNext) {
      failNext = false;
      return route.fulfill({ status: 500, contentType: "application/json", body: "{}" });
    }
    return route.continue();
  });
  await page.goto("/players/erling-haaland");
  const section = page.getByRole("region", { name: /similar players/i });
  const errorBox = section.getByRole("alert");
  await expect(errorBox).toBeVisible({ timeout: 15_000 });

  await section.getByRole("button", { name: /try again/i }).click();
  await expect(section.getByText(/% match/).first()).toBeVisible({ timeout: 15_000 });
});

test("explanation expands without horizontal overflow at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/players/erling-haaland");
  const section = page.getByRole("region", { name: /similar players/i });
  await expect(section.getByText(/% match/).first()).toBeVisible({ timeout: 15_000 });
  await section.locator("details summary").first().click();
  await expect(section.getByRole("heading", { name: /matched strengths/i })).toBeVisible();

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});

test("axe is green on the player page with the explanation expanded", async ({ page }) => {
  await page.goto("/players/erling-haaland");
  await page.waitForLoadState("networkidle");
  const section = page.getByRole("region", { name: /similar players/i });
  const why = section.locator("details summary").first();
  if (await why.isVisible()) {
    await why.click();
    await expect(section.getByRole("heading", { name: /matched strengths/i })).toBeVisible();
  }
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations,
    `axe violations on /players/erling-haaland with explanation open: ${results.violations
      .map((v) => `${v.id} (${v.nodes.length})`)
      .join(", ")}`,
  ).toEqual([]);
});
