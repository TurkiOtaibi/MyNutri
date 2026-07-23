import path from "node:path";

import type { BrowserContext, Page } from "@playwright/test";

import { API_TOKEN, API_URL, expect, offsetIsoDate, test } from "../foods/helpers";

type Authority = {
  current_diary_date: string;
  calendar_timezone: string;
  next_rollover_at: string;
};

const BEFORE_ROLLOVER: Authority = {
  current_diary_date: "2026-07-22",
  calendar_timezone: "Asia/Riyadh",
  next_rollover_at: "2026-07-22T21:00:00.000Z"
};
const AFTER_ROLLOVER: Authority = {
  current_diary_date: "2026-07-23",
  calendar_timezone: "Asia/Riyadh",
  next_rollover_at: "2026-07-23T21:00:00.000Z"
};

async function contextWithTimezone(
  browser: import("@playwright/test").Browser,
  timezoneId: string
): Promise<BrowserContext> {
  return browser.newContext({
    timezoneId,
    locale: "ar-SA",
    serviceWorkers: "block",
    storageState: path.join(process.cwd(), "e2e", ".auth", "admin.json")
  });
}

async function mockAuthority(
  page: Page,
  resolveAuthority: () => Authority
): Promise<() => number> {
  let requests = 0;
  await page.route(`${API_URL}/account/calendar`, async (route) => {
    requests += 1;
    await route.fulfill({ status: 200, contentType: "application/json", json: resolveAuthority() });
  });
  return () => requests;
}

test.describe("@diary @calendar-authority authoritative Diary date", () => {
  test("@p0 ignores browser-local and UTC-runner dates and blocks Backend tomorrow", async ({ browser, request, foodsApi }) => {
    const context = await contextWithTimezone(browser, "America/Los_Angeles");
    const page = await context.newPage();
    await page.clock.install({ time: new Date("2026-07-22T20:30:00.000Z") });
    await mockAuthority(page, () => AFTER_ROLLOVER);

    await page.goto("/diary");
    const picker = page.locator('input[type="date"]');
    await expect(picker).toHaveValue(AFTER_ROLLOVER.current_diary_date);
    expect(await page.evaluate(() => new Date().getDate())).toBe(22);
    await expect(page.locator(".week-day-arrow.next")).toBeDisabled();

    const tomorrow = offsetIsoDate(AFTER_ROLLOVER.current_diary_date, 1);
    await picker.fill(tomorrow);
    await expect(picker).toHaveValue(AFTER_ROLLOVER.current_diary_date);
    await expect(page.locator(".date-error[role=alert]")).toBeVisible();

    const food = await foodsApi.create({ name: `E2E-Calendar-authority-${Date.now()}` });
    const actualAuthorityResponse = await request.get(`${API_URL}/account/calendar`, {
      headers: { Authorization: `Bearer ${API_TOKEN}` }
    });
    expect(actualAuthorityResponse.status()).toBe(200);
    const actualAuthority = await actualAuthorityResponse.json() as Authority;
    const response = await request.post(`${API_URL}/diary`, {
      headers: { Authorization: `Bearer ${API_TOKEN}` },
      data: { food_id: food.id, entry_date: offsetIsoDate(actualAuthority.current_diary_date, 1), quantity: 1 }
    });
    expect(response.status()).toBe(422);
    await context.close();
  });

  test("@p0 refreshes at absolute rollover and advances an open page that was on today", async ({ page }) => {
    const dueAuthority = {
      ...BEFORE_ROLLOVER,
      next_rollover_at: new Date(Date.now() - 1_000).toISOString()
    };
    const refreshedAuthority = {
      ...AFTER_ROLLOVER,
      next_rollover_at: new Date(Date.now() + 86_400_000).toISOString()
    };
    let requestCount = 0;
    let announceRolloverRequest!: () => void;
    const rolloverRequestStarted = new Promise<void>((resolve) => { announceRolloverRequest = resolve; });
    let announceRolloverRecheck!: () => void;
    const rolloverRecheckStarted = new Promise<void>((resolve) => { announceRolloverRecheck = resolve; });
    let releaseRolloverRecheck!: () => void;
    const rolloverRecheckRelease = new Promise<void>((resolve) => { releaseRolloverRecheck = resolve; });
    await page.route(`${API_URL}/account/calendar`, async (route) => {
      requestCount += 1;
      if (requestCount === 1) {
        await route.fulfill({ status: 200, contentType: "application/json", json: dueAuthority });
        return;
      }
      if (requestCount === 2) {
        announceRolloverRequest();
        await route.fulfill({ status: 200, contentType: "application/json", json: dueAuthority });
        return;
      }
      announceRolloverRecheck();
      await rolloverRecheckRelease;
      await route.fulfill({ status: 200, contentType: "application/json", json: refreshedAuthority });
    });

    await page.goto("/diary");
    const picker = page.locator('input[type="date"]');
    await expect(picker).toHaveValue(BEFORE_ROLLOVER.current_diary_date);

    await rolloverRequestStarted;
    await rolloverRecheckStarted;
    releaseRolloverRecheck();
    await expect(picker).toHaveValue(AFTER_ROLLOVER.current_diary_date);
    await expect(page.locator(".week-day-arrow.next")).toBeDisabled();
  });

  test("@p0 focus refresh after rollover preserves history, week navigation, and Today authority", async ({ page }) => {
    await page.clock.install({ time: new Date("2026-07-22T20:00:00.000Z") });
    let authority = BEFORE_ROLLOVER;
    const requestCount = await mockAuthority(page, () => authority);
    await page.goto("/diary");
    const picker = page.locator('input[type="date"]');
    await expect(picker).toHaveValue(BEFORE_ROLLOVER.current_diary_date);

    const historical = offsetIsoDate(BEFORE_ROLLOVER.current_diary_date, -9);
    await picker.fill(historical);
    await expect(picker).toHaveValue(historical);
    await page.locator(".week-day-arrow.previous").click();
    const previousHistorical = offsetIsoDate(historical, -1);
    await expect(picker).toHaveValue(previousHistorical);

    authority = AFTER_ROLLOVER;
    const requestsBeforeFocus = requestCount();
    await page.evaluate(() => window.dispatchEvent(new Event("focus")));
    await expect.poll(requestCount).toBeGreaterThan(requestsBeforeFocus);
    await expect(picker).toHaveValue(previousHistorical);
    await page.locator(".compact-today").click();
    await expect(picker).toHaveValue(AFTER_ROLLOVER.current_diary_date);
  });
});
