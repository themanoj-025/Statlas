import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Phase 7 — scouting workspace e2e.
 *
 * Covers the Part E quality gates on real seeded data:
 * - full CRUD flow: register -> default shortlist -> add from a player page ->
 *   status transitions (valid + explicitly-invalid rejected with the specific
 *   message) -> note -> tag -> soft-remove -> empty state
 * - free-tier gate: a free account attempting a second shortlist gets the
 *   honest upsell message (never a generic error)
 * - "Add to Shortlist" entry points: player profile, leaderboard rows, and
 *   similar-players results
 * - axe green on /workspace and the shortlist detail view (with the status
 *   change panel and note/tag forms open — the interactive states)
 * - no horizontal overflow on the workspace pages (light + dark)
 * - signed-out: /workspace shows the honest sign-in prompt
 */

const PASSWORD = "hunter2hunter";

async function register(page: Page, tag: string): Promise<void> {
  const email = `e2e-${tag}-${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  // Register redirects to /account — wait for the signed-in state.
  await expect(page.getByText(/plan: free/i).first()).toBeVisible({ timeout: 20_000 });
}

async function addFromProfile(page: Page): Promise<void> {
  await page.goto("/players/erling-haaland");
  const save = page.getByRole("button", { name: "Save" }).first();
  await expect(save).toBeVisible({ timeout: 20_000 });
  await save.click();
  await page.getByRole("menuitem", { name: /My Shortlist/ }).click();
  await expect(page.getByText(/Added to My Shortlist/i)).toBeVisible({ timeout: 10_000 });
}

test("full scouting CRUD flow with pipeline validation", async ({ page }) => {
  await register(page, "crud");

  // Default "My Shortlist" auto-created — the feature is never an empty void.
  await page.goto("/workspace");
  await expect(page.getByRole("link", { name: "My Shortlist" })).toBeVisible({ timeout: 20_000 });

  // Free-tier gate: a second shortlist is blocked with an honest upsell.
  await page.goto("/players/erling-haaland");
  await page.getByRole("button", { name: "Save" }).first().click();
  await page.getByLabel(/New shortlist/).fill("Second list");
  await page.getByRole("button", { name: /Create & add/ }).click();
  await expect(page.getByText(/Upgrade to Pro/i).first()).toBeVisible({ timeout: 10_000 });

  // Add the player from their profile page.
  await addFromProfile(page);

  // Open the shortlist from the workspace.
  await page.goto("/workspace");
  await page.getByRole("link", { name: "My Shortlist" }).click();
  await expect(page.getByRole("link", { name: "Erling Haaland" })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("1 player")).toBeVisible();

  // Valid transition with an optional reason note.
  await page.getByRole("button", { name: "Change", exact: true }).first().click();
  await page.getByLabel("Move to").selectOption("monitoring");
  await page.getByLabel(/Reason/).fill("Season started — tracking weekly minutes");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page.getByText("Monitoring", { exact: true }).first()).toBeVisible();

  // Terminal state: signed is valid from monitoring.
  await page.getByRole("button", { name: "Change", exact: true }).first().click();
  await page.getByLabel("Move to").selectOption("signed");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page.getByText("Signed", { exact: true }).first()).toBeVisible();

  // Invalid transition: signed -> monitoring must be rejected with the
  // specific terminal-status message.
  await page.getByRole("button", { name: "Change", exact: true }).first().click();
  await page.getByLabel("Move to").selectOption("monitoring");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page.getByText(/Signed is a terminal status/i)).toBeVisible({ timeout: 10_000 });

  // Note with timestamp display.
  await page.getByRole("button", { name: /Note/ }).click();
  await page.getByLabel(/New note for Erling Haaland/).fill("Watched vs Arsenal; strong press.");
  await page.getByRole("button", { name: "Add note" }).click();
  await expect(page.getByText("1 note")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/Watched vs Arsenal; strong press/)).toBeVisible();

  // Tag with remove.
  await page.getByRole("button", { name: /Tag/ }).click();
  await page.getByLabel(/New tag for Erling Haaland/).fill("left-footed");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByRole("button", { name: /Remove tag left-footed/ })).toBeVisible({ timeout: 10_000 });

  // Soft-remove: confirm dialog -> entry gone -> honest empty state.
  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByRole("button", { name: "Remove Erling Haaland" }).click();
  await expect(page.getByText("This shortlist is empty")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByRole("link", { name: "Erling Haaland" })).toHaveCount(0);
});

test("add-to-shortlist entry points: leaderboard row and similar players", async ({ page }) => {
  await register(page, "entrypoints");

  // Leaderboard row (the LeaderboardTable lives on the league position pages).
  await page.goto("/leagues/premier-league/positions/gk");
  const leaderboardSave = page.getByRole("button", { name: "Save" }).first();
  await expect(leaderboardSave).toBeVisible({ timeout: 20_000 });
  await leaderboardSave.click();
  await page.getByRole("menuitem", { name: /My Shortlist/ }).click();
  await expect(page.getByText(/Added to My Shortlist/i)).toBeVisible({ timeout: 10_000 });

  // Similar-players result on a profile page.
  await page.goto("/players/erling-haaland");
  const similarSection = page.getByRole("region", { name: "Similar players" });
  await expect(similarSection).toBeVisible({ timeout: 20_000 });
  const similarSave = similarSection.getByRole("button", { name: "Save" }).first();
  await similarSave.click();
  await page.getByRole("menuitem", { name: /My Shortlist/ }).click();
  await expect(similarSection.getByText(/Added to My Shortlist/i)).toBeVisible({ timeout: 10_000 });

  // Both land in the workspace.
  await page.goto("/workspace");
  await page.getByRole("link", { name: "My Shortlist" }).click();
  await expect(page.getByText("2 players")).toBeVisible({ timeout: 20_000 });
});

test("axe is green on workspace overview and shortlist detail", async ({ page }) => {
  await register(page, "axe");
  await addFromProfile(page);
  await page.goto("/workspace");
  await page.waitForLoadState("networkidle");

  // Overview (list of shortlist cards + status breakdown chips).
  let results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations,
    `axe violations on /workspace: ${results.violations.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`,
  ).toEqual([]);

  // Detail view with the interactive states OPEN (status panel, note form,
  // tag form) — the a11y-critical markup.
  await page.getByRole("link", { name: "My Shortlist" }).click();
  await expect(page.getByRole("link", { name: "Erling Haaland" })).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: "Change", exact: true }).first().click();
  await page.getByRole("button", { name: /Note/ }).click();
  await page.getByRole("button", { name: /Tag/ }).click();
  await page.waitForLoadState("networkidle");

  results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations,
    `axe violations on shortlist detail: ${results.violations.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`,
  ).toEqual([]);
});

test("no horizontal overflow on workspace pages (light + dark)", async ({ page }) => {
  await register(page, "overflow");
  await addFromProfile(page);

  await page.goto("/workspace");
  const href = await page.getByRole("link", { name: "My Shortlist" }).getAttribute("href");
  expect(href).toMatch(/^\/workspace\/\d+$/);

  for (const path of ["/workspace", href!]) {
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
      await toggle.click(); // back to light for the next path
    }
  }
});

test("signed-out /workspace shows the honest sign-in prompt", async ({ page }) => {
  await page.goto("/workspace");
  await expect(page.getByText("Workspace is per-account")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("link", { name: "Sign in" }).first()).toBeVisible();
});
