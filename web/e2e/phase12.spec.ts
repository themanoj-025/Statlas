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

test.describe("Phase 12 — Account system", () => {
  test("register → account page shows profile fields", async ({ page }) => {
    await register(page, "profile");
    await expect(page.locator("h1")).toContainText("Account");
    // Profile section should show the email.
    await expect(page.locator("strong").filter({ hasText: "@example.com" }).first()).toBeVisible();
    // Profile form fields should be present.
    await expect(page.locator("#display-name")).toBeVisible();
    await expect(page.locator("#timezone")).toBeVisible();
  });

  test("login page has forgot-password link", async ({ page }) => {
    await goto(page, "/login");
    await expect(page.locator('a[href="/reset-password"]')).toBeVisible();
  });

  test("reset-password page renders request form", async ({ page }) => {
    await goto(page, "/reset-password");
    await expect(page.locator("h1")).toContainText("Reset password");
    await expect(page.locator("#reset-email")).toBeVisible();
  });

  test("account page has security section with password change", async ({ page }) => {
    await register(page, "security");
    await expect(page.locator("#current-pw")).toBeVisible();
    await expect(page.locator("#new-pw")).toBeVisible();
  });

  test("account page has danger zone with delete button", async ({ page }) => {
    await register(page, "danger");
    await expect(page.getByText("Danger zone")).toBeVisible();
    await expect(page.getByRole("button", { name: /delete my account/i })).toBeVisible();
  });

  test("axe: account page", async ({ page }) => {
    await register(page, "axe-acct");
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toHaveLength(0);
  });

  test("axe: reset-password page", async ({ page }) => {
    await goto(page, "/reset-password");
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toHaveLength(0);
  });

  test("axe: login page", async ({ page }) => {
    await goto(page, "/login");
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toHaveLength(0);
  });
});
