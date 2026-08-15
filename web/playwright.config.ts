import { defineConfig, devices } from "@playwright/test";

/**
 * Statlas e2e suite (closeout B3/B2/B4):
 * - e2e: radar generation (search -> add -> chart), leaderboard search/filter
 * - axe: automated accessibility audit on radar, player, team, leaderboard
 * - breakpoints: no horizontal overflow at 375/768/1440px, light + dark themes
 *
 * The webServer command boots the whole stack (seed -> FastAPI -> Next) via
 * scripts/e2e-server.sh; baseURL is the Next dev server on :3000.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // share one seeded stack; keep runs deterministic
  workers: 1,
  timeout: 60_000,
  retries: 1, // flaky first-visit (dev-mode compile) tolerated once
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
  projects: [
    // Core e2e flows run once at desktop; breakpoint + theme coverage is its
    // own project matrix so overflow regressions fail loudly per viewport.
    { name: "e2e", testMatch: /e2e\/.*\.spec\.ts/ },
    {
      name: "mobile-375",
      testMatch: /e2e\/breakpoints\.spec\.ts/,
      use: { viewport: { width: 375, height: 812 } }, // 375px breakpoint
    },
    {
      name: "tablet-768",
      testMatch: /e2e\/breakpoints\.spec\.ts/,
      use: { viewport: { width: 768, height: 1024 } },
    },
    {
      name: "desktop-1440",
      testMatch: /e2e\/breakpoints\.spec\.ts/,
      use: { viewport: { width: 1440, height: 900 } },
    },
  ],
  webServer: {
    command: "bash scripts/e2e-server.sh",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
