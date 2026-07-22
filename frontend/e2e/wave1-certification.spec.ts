import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./foods/helpers";

const majorStates = [
  { path: "/profile", name: "Profile" },
  { path: "/foods", name: "Foods" },
  { path: "/foods/new", name: "Add Food" },
  { path: "/diary", name: "Diary" }
];

for (const state of majorStates) {
  test(`@certification ${state.name} has no serious or critical axe violations`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto(state.path);
    await expect(page.locator("main").first()).toBeVisible();

    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const blocking = result.violations.filter((violation) =>
      violation.impact === "serious" || violation.impact === "critical"
    );

    expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
  });
}

test("@certification PWA shell registers without creating offline personal-data authority", async ({ browser, baseURL, request }) => {
  const manifestResponse = await request.get(`${baseURL}/manifest.json`);
  expect(manifestResponse.status()).toBe(200);
  const manifest = await manifestResponse.json() as {
    start_url: string;
    scope: string;
    display: string;
    dir: string;
    lang: string;
  };
  expect(manifest).toMatchObject({
    start_url: "/diary",
    scope: "/",
    display: "standalone",
    dir: "rtl",
    lang: "ar"
  });

  const workerResponse = await request.get(`${baseURL}/service-worker.js`);
  expect(workerResponse.status()).toBe(200);
  const workerSource = await workerResponse.text();
  expect(workerSource).not.toContain("/api/");
  expect(workerSource).not.toContain("indexedDB");

  const context = await browser.newContext({ baseURL, serviceWorkers: "allow" });
  const page = await context.newPage();
  await page.goto("/diary");
  const scriptUrl = await page.evaluate(async () => {
    const registration = await navigator.serviceWorker.ready;
    return registration.active?.scriptURL ?? "";
  });
  expect(scriptUrl).toMatch(/\/service-worker\.js$/);
  expect(await page.evaluate(() => indexedDB.databases().then((items) => items.length))).toBe(0);
  await context.close();
});
