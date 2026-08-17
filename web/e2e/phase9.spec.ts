import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Phase 9 — AI scouting reports e2e.
 *
 * The API runs with REPORTS_DEV_NARRATOR=1 in e2e (scripts/e2e-server.sh): the
 * deterministic narrator can only emit verified context values, and the hard
 * verification gate runs on every generation exactly as with the LLM narrator.
 *
 * Covers the Part E quality gates:
 * - generate a report from a player profile (staged honest progress, lands in
 *   history with status "generated" — verification passed)
 * - the report viewer renders the structured sections and the expandable
 *   evidence appendix (claim-by-claim sourcing, no download required)
 * - regenerate creates a FRESH report against current data; delete works
 * - PDF / JSON / CSV exports download (derived from the verified object)
 * - generating from a shortlist entry includes the workspace context section;
 *   ad hoc generation omits it
 * - free tier gets the honest Pro upsell (not a generic error)
 * - axe green on the reports page with the appendix open
 */

const PASSWORD = "hunter2hunter";

async function registerPro(page: Page, tag: string): Promise<string> {
  const email = `e2e-report-${tag}-${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText(/plan: free/i).first()).toBeVisible({ timeout: 20_000 });
  // The reports feature is Pro-gated by design; the e2e fixture route grants
  // the same Subscription row the unit suite creates directly. It only exists
  // when the e2e-only flag is set (never in production).
  const grant = await page.request.post("http://127.0.0.1:8000/api/v1/e2e/grant-pro", {
    data: { email },
  });
  expect(grant.ok()).toBeTruthy();
  return email;
}

async function openFirstPlayerProfile(page: Page): Promise<void> {
  // /positions -> first position-group leaderboard -> first player row.
  await page.goto("/positions");
  await expect(page.locator(".position-card").first()).toBeVisible({ timeout: 20_000 });
  await page.locator(".position-card").first().click();
  await expect(page.locator("a[href^='/players/']").first()).toBeVisible({ timeout: 20_000 });
  await page.locator("a[href^='/players/']").first().click();
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible({ timeout: 20_000 });
}

test("generate a report from a player profile: staged progress, verified, stored", async ({ page }) => {
  await registerPro(page, "gen");
  await openFirstPlayerProfile(page);

  await page.getByRole("button", { name: "Generate report" }).click();
  // Honest staged progress rather than a black-box spinner.
  await expect(page.getByText(/Gathering player data…/).first()).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/Report generated and every claim verified/).first()).toBeVisible({ timeout: 30_000 });

  // The report is stored and opens in history (Reports is also in the
  // signed-in header nav).
  await page.goto("/reports");
  await expect(page.getByText(/data as of /).first()).toBeVisible({ timeout: 20_000 });
  // Quota reflects the consumption.
  await expect(page.getByText(/reports? remaining this period/i)).toBeVisible();
});

test("report history viewer: sections, evidence appendix, regenerate, delete", async ({ page }) => {
  await registerPro(page, "view");
  await openFirstPlayerProfile(page);
  await page.getByRole("button", { name: "Generate report" }).click();
  await expect(page.getByText(/Report generated and every claim verified/).first()).toBeVisible({ timeout: 30_000 });
  await page.goto("/reports");
  await expect(page.getByText(/data as of /).first()).toBeVisible({ timeout: 20_000 });

  // Expand the report card.
  await page.getByRole("button", { name: /data as of / }).first().click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Statistical profile" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Risk factors" })).toBeVisible();
  await expect(page.getByText(/Confidence: (high|medium|low)/)).toBeVisible();
  // Ad hoc generation must NOT include a workspace-context section.
  await expect(page.getByRole("heading", { name: "Workspace context" })).toHaveCount(0);
  // The evidence appendix is expandable without downloading anything.
  await page.getByRole("button", { name: /Evidence appendix/ }).click();
  await expect(page.getByRole("columnheader", { name: "Claim" })).toBeVisible();
  await expect(page.getByText(/percentile and raw value/i).first()).toBeVisible();

  // Regenerate creates a FRESH report (the list grows; the stored one is
  // never silently mutated).
  const countBefore = await page.locator(".report-card").count();
  await page.getByRole("button", { name: "Regenerate" }).first().click();
  await expect(page.getByText(/was created/i)).toBeVisible({ timeout: 30_000 });
  await expect(page.locator(".report-card")).toHaveCount(countBefore + 1);

  // Delete the first report.
  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByRole("button", { name: /^Delete/ }).first().click();
  await expect(page.locator(".report-card")).toHaveCount(countBefore);
});

test("PDF, JSON and CSV exports download from the verified report", async ({ page }) => {
  await registerPro(page, "export");
  await openFirstPlayerProfile(page);
  await page.getByRole("button", { name: "Generate report" }).click();
  await expect(page.getByText(/Report generated and every claim verified/).first()).toBeVisible({ timeout: 30_000 });
  await page.goto("/reports");
  await expect(page.getByText(/data as of /).first()).toBeVisible({ timeout: 20_000 });

  const downloadPdf = page.waitForEvent("download", { timeout: 20_000 });
  await page.getByRole("button", { name: "PDF", exact: true }).first().click();
  const pdf = await downloadPdf;
  expect(pdf.suggestedFilename()).toMatch(/statlas-report-\d+\.pdf$/);
  const pdfPath = await pdf.path();
  expect(require("fs").readFileSync(pdfPath).subarray(0, 4).toString()).toBe("%PDF");

  const downloadJson = page.waitForEvent("download", { timeout: 20_000 });
  await page.getByRole("button", { name: "JSON", exact: true }).first().click();
  const json = await downloadJson;
  expect(json.suggestedFilename()).toMatch(/report-\d+\.json$/);

  const downloadCsv = page.waitForEvent("download", { timeout: 20_000 });
  await page.getByRole("button", { name: "CSV", exact: true }).first().click();
  const csv = await downloadCsv;
  expect(csv.suggestedFilename()).toMatch(/statlas-report-\d+\.csv$/);
  const csvPath = await csv.path();
  expect(require("fs").readFileSync(csvPath, "utf8")).toContain("Statistical Profile");
});

test("generating from a shortlist entry includes workspace context; ad hoc omits it", async ({ page }) => {
  await registerPro(page, "ctx");
  await openFirstPlayerProfile(page);

  await page.getByRole("button", { name: /Save/ }).first().click();
  await page.getByRole("menuitem", { name: /My Shortlist/ }).click();
  await expect(page.getByText(/Added to My Shortlist/i).first()).toBeVisible({ timeout: 10_000 });

  // From the shortlist entry, generate a report — workspace context is
  // included and clearly labelled as the user's own input.
  await page.goto("/workspace");
  await page.getByRole("link", { name: "My Shortlist" }).click();
  await expect(page.locator("tbody tr").first()).toBeVisible({ timeout: 20_000 });
  await page.locator("tbody tr").first().getByRole("button", { name: "Generate report" }).click();
  await expect(page.getByText(/Report generated and every claim verified/).first()).toBeVisible({ timeout: 30_000 });
  // Compact rows show the confirmation without the inline link (no overlap
  // with the row's remove button) — navigate to history directly.
  await page.goto("/reports");
  await expect(page.getByText(/data as of /).first()).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: /data as of / }).first().click();
  await expect(page.getByRole("heading", { name: "Workspace context" })).toBeVisible();
  await expect(page.getByText(/user's own scouting notes/i)).toBeVisible();
  await expect(page.getByText(/Status: discovered/i)).toBeVisible();
});

test("free tier gets an honest Pro upsell when generating", async ({ page }) => {
  const email = `e2e-report-free-${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText(/plan: free/i).first()).toBeVisible({ timeout: 20_000 });

  await openFirstPlayerProfile(page);
  await page.getByRole("button", { name: "Generate report" }).click();
  await expect(page.getByText(/Reports are a Pro feature/).first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("link", { name: "See Pro" })).toBeVisible();
});

test("axe is green on the reports page with the evidence appendix open", async ({ page }) => {
  await registerPro(page, "axe");
  await openFirstPlayerProfile(page);
  await page.getByRole("button", { name: "Generate report" }).click();
  await expect(page.getByText(/Report generated and every claim verified/).first()).toBeVisible({ timeout: 30_000 });
  await page.goto("/reports");
  await expect(page.getByText(/data as of /).first()).toBeVisible({ timeout: 20_000 });

  await page.getByRole("button", { name: /data as of / }).first().click();
  await page.getByRole("button", { name: /Evidence appendix/ }).click();
  await expect(page.getByRole("columnheader", { name: "Claim" })).toBeVisible();
  await page.waitForLoadState("networkidle");

  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations,
    `axe violations on /reports: ${results.violations.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`,
  ).toEqual([]);
});
