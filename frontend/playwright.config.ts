import { defineConfig, devices } from "@playwright/test";
import { networkInterfaces } from "node:os";

const frontendUrl = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";
const backendUrl = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";

const localHosts = new Set([
  "127.0.0.1",
  "localhost",
  ...Object.values(networkInterfaces())
    .flatMap((entries) => entries ?? [])
    .map((entry) => entry.address)
]);

for (const value of [frontendUrl, backendUrl]) {
  const hostname = new URL(value).hostname;
  if (!localHosts.has(hostname)) {
    throw new Error(`Foods E2E tests are local-only; refusing target ${value}`);
  }
}

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results",
  fullyParallel: false,
  workers: 1,
  forbidOnly: true,
  retries: 0,
  timeout: 45_000,
  expect: { timeout: 8_000 },
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/foods-results.json" }],
    ["html", { outputFolder: "playwright-report", open: "never" }]
  ],
  use: {
    baseURL: frontendUrl,
    serviceWorkers: "block",
    extraHTTPHeaders: { Authorization: `Bearer ${process.env.PLAYWRIGHT_API_TOKEN ?? "dev-token"}` },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    locale: "ar-SA",
    timezoneId: "Asia/Riyadh"
  },
  projects: [
    {
      name: "foods-chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
