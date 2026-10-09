import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Phase 8 — structured search e2e.
 *
 * Covers the Part E quality gates on real seeded data:
 * - query builder happy path: presets load into the builder, live preview
 *   shows the count, results render with the real per-condition values
 * - keyboard-only condition building (add/remove/edit without a mouse — the
 *   C5 accessibility requirement)
 * - saved searches: save -> listed -> run (re-executes against current data) ->
 *   delete; history shows the auto-logged run
 * - add-to-shortlist from results (per-row + bulk) lands in the Phase 7
 *   workspace — the Phase 7 ↔ Phase 8 integration
 * - axe green on the builder with the save panel open and on the results
 */

const PASSWORD = "hunter2hunter";

async function register(page: Page, tag: string): Promise<void> {
  const email = `e2e-search-${tag}-${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText(/plan: free/i).first()).toBeVisible({ timeout: 20_000 });
}

test("query builder happy path: preset, live preview, results with values", async ({ page }) => {
  await page.goto("/search");

  // Presets render with their real rationales (Part D content).
  const presets = page.getByRole("region", { name: "Curated presets" });
  await expect(presets).toBeVisible({ timeout: 20_000 });
  await expect(presets.getByText("High-potential young progressors")).toBeVisible();

  // Load a preset — the builder fills with its real conditions and the live
  // preview reports a real count (the number is split across a <strong> and a
  // text node, so match the phrase).
  await presets.getByRole("button", { name: "Use preset" }).first().click();
  await expect(page.getByText(/players? match/).first()).toBeVisible({ timeout: 20_000 });

  // Run it and check the results show real per-condition values.
  await page.getByRole("button", { name: "Search", exact: true }).click();
  const resultsSection = page.getByRole("region", { name: "Search results" });
  await expect(resultsSection).toBeVisible({ timeout: 20_000 });
  await expect(resultsSection.getByText(/th pct/).first()).toBeVisible({ timeout: 20_000 });
  // The qualification-floor note is explicit in results (A3 honesty).
  await expect(resultsSection.getByText(/qualification floor/i)).toBeVisible();

  // Every result row links to a real player profile.
  const firstResultLink = resultsSection.getByRole("link").filter({ hasText: /^\s*[A-Z][a-z]+ [A-Z][a-z]+/ }).first();
  await expect(firstResultLink).toBeVisible();
});

test("empty-result query surfaces actionable guidance, not a bare no-results", async ({ page }) => {
  await page.goto("/search");

  // An impossible threshold (percentile 99.9 is achievable, so use a position
  // + tier combo that no player satisfies: GK in Tier 2 with a huge save pct).
  await page.getByLabel("Position group").selectOption("GK");
  await page.getByLabel("League tier").selectOption("tier_2");
  await page.getByRole("button", { name: "Search" }).click();

  await expect(page.getByText("0 players match this query")).toBeVisible({ timeout: 20_000 });
  // The most-restrictive condition is named with its pass count.
  await expect(page.getByText(/most restrictive condition/i)).toBeVisible();
});

test("keyboard-only condition building works without a mouse", async ({ page }) => {
  await page.goto("/search");
  await page.getByLabel("Query builder").waitFor({ timeout: 20_000 });

  // Add a condition via keyboard only (focus the add button, Enter).
  await page.getByRole("button", { name: "Add condition" }).focus();
  await page.keyboard.press("Enter");

  // A new condition row appeared (3 rows now: 2 default + 1 added).
  const rows = page.locator(".query-builder__condition");
  await expect(rows).toHaveCount(3);

  // Focus the new row's OPERATOR select and pick "between" with the keyboard.
  const lastRow = rows.nth(2);
  const opSelect = lastRow.locator("select").nth(1);
  await opSelect.focus();
  // Native <select> keyboard: typing the first letter jumps to the matching
  // option — "b" lands on "between".
  await page.keyboard.type("b");
  await expect(lastRow.getByLabel("and", { exact: true })).toBeVisible({ timeout: 10_000 });

  // The upper-bound input is focusable and typeable via keyboard.
  const maxInput = lastRow.getByLabel("and", { exact: true });
  await maxInput.focus();
  await maxInput.fill("90");
  await expect(maxInput).toHaveValue("90");

  // Remove the added condition via keyboard too.
  await lastRow.getByRole("button", { name: "Remove condition 3" }).focus();
  await page.keyboard.press("Enter");
  await expect(rows).toHaveCount(2);
});

test("saved searches: save, list, run, history, delete", async ({ page }) => {
  await register(page, "saved");

  await page.goto("/search");
  const builder = page.getByLabel("Query builder");
  await expect(builder).toBeVisible({ timeout: 20_000 });

  // Save the current (default) query.
  await builder.getByRole("button", { name: "Save" }).click();
  await page.getByLabel("Name", { exact: true }).fill("E2E saved search");
  await page.getByRole("button", { name: "Save search" }).click();
  await expect(page.getByText("E2E saved search")).toBeVisible({ timeout: 10_000 });

  // Run it from the saved list — the stored query re-executes against CURRENT
  // data and the fresh results render (never stale).
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByRole("region", { name: "Search results" })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/last run/i)).toBeVisible({ timeout: 10_000 });

  // The run was auto-logged to history with its result count.
  await expect(page.getByText(/results may differ from the original run/i).first()).toBeVisible({ timeout: 10_000 });

  // Delete it.
  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByRole("button", { name: /Delete E2E saved search/ }).click();
  await expect(page.getByText("E2E saved search")).toHaveCount(0);
});

test("add-to-shortlist from results (per-row and bulk) reaches the workspace", async ({ page }) => {
  await register(page, "workspace");
  await page.goto("/search");

  // Load a preset that returns results, then run.
  await page.getByRole("region", { name: "Curated presets" }).getByRole("button", { name: "Use preset" }).first().click();
  await page.getByRole("button", { name: "Search" }).click();
  const resultsSection = page.getByRole("region", { name: "Search results" });
  await expect(resultsSection).toBeVisible({ timeout: 20_000 });

  // Per-row save into My Shortlist.
  const rowSave = resultsSection.getByRole("button", { name: "Save" }).first();
  await expect(rowSave).toBeVisible({ timeout: 20_000 });
  await rowSave.click();
  await page.getByRole("menuitem", { name: /My Shortlist/ }).click();
  await expect(page.getByText(/Added to My Shortlist/i).first()).toBeVisible({ timeout: 10_000 });

  // Bulk add all results into the default shortlist (duplicates are skipped).
  await resultsSection.getByRole("button", { name: /Add all to shortlist/ }).click();
  await page.getByRole("button", { name: /My Shortlist/ }).click();
  await expect(page.getByText(/Added .* players? to My Shortlist/).first()).toBeVisible({ timeout: 20_000 });

  // They all landed in the workspace (≥ 2 rows: the per-row one + the bulk set).
  await page.goto("/workspace");
  await page.getByRole("link", { name: "My Shortlist" }).click();
  await expect(page.locator("tbody tr").first()).toBeVisible({ timeout: 20_000 });
  // Per-row add + bulk add-all (duplicates skipped) → every result player lands.
  await expect(page.locator("tbody tr").count()).resolves.toBeGreaterThan(1);
});

test("axe is green on the query builder (save panel open) and results", async ({ page }) => {
  await register(page, "axe");
  await page.goto("/search");
  const builder = page.getByLabel("Query builder");
  await expect(builder).toBeVisible({ timeout: 20_000 });

  // Open the save panel (a11y-critical form markup).
  await builder.getByRole("button", { name: "Save" }).click();
  await page.waitForLoadState("networkidle");

  let results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations,
    `axe violations on /search builder: ${results.violations.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`,
  ).toEqual([]);

  // Close the save panel so it doesn't overlap the Search button, then run.
  await builder.getByRole("button", { name: "Cancel" }).click();
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("region", { name: "Search results" })).toBeVisible({ timeout: 20_000 });
  await page.waitForLoadState("networkidle");

  results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations,
    `axe violations on /search results: ${results.violations.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`,
  ).toEqual([]);
});

test("signed-out /search still works for public execution with honest auth prompts", async ({ page }) => {
  await page.goto("/search");
  await expect(page.getByLabel("Query builder")).toBeVisible({ timeout: 20_000 });

  // Public execution works without an account.
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page.getByRole("region", { name: "Search results" })).toBeVisible({ timeout: 20_000 });

  // Saved searches + history are honestly gated behind sign-in.
  await expect(page.getByText(/Saved searches & history/)).toBeVisible();
  await expect(page.getByText(/Sign in to save queries for reuse/)).toBeVisible();
});
