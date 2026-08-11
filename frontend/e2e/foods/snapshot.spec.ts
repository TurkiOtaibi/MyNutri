import type { Page, Response } from "@playwright/test";

import { weekStartSunday } from "../../lib/dates";
import type { DiaryEntryResponse, WeekSummary } from "../../lib/types";
import { API_URL, diaryDate, test, expect } from "./helpers";

const apiOrigin = new URL(API_URL).origin;

function isExactDiaryResponse(
  response: Response,
  pathname: "/diary" | "/diary/week",
  queryKey: "entry_date" | "start",
  queryValue: string
) {
  const request = response.request();
  const url = new URL(response.url());
  return request.method() === "GET" &&
    request.resourceType() === "fetch" &&
    url.origin === apiOrigin &&
    url.pathname === pathname &&
    url.searchParams.get(queryKey) === queryValue &&
    [...url.searchParams.keys()].length === 1;
}

async function navigateToSnapshotDiary(page: Page, value: string, entryId: string) {
  const weekStart = weekStartSunday(value);
  const entriesResponse = page.waitForResponse((response) =>
    isExactDiaryResponse(response, "/diary", "entry_date", value)
  );
  const weekResponse = page.waitForResponse((response) =>
    isExactDiaryResponse(response, "/diary/week", "start", weekStart)
  );

  await page.goto("/diary");
  const [entriesResult, weekResult] = await Promise.all([entriesResponse, weekResponse]);
  expect(entriesResult.status()).toBe(200);
  expect(weekResult.status()).toBe(200);

  const entries = await entriesResult.json() as DiaryEntryResponse[];
  const week = await weekResult.json() as WeekSummary;
  expect(entries.some((item) => item.id === entryId && item.entry_date === value)).toBe(true);
  expect(week.days.some((day) => day.date === value)).toBe(true);

  await expect(page.getByLabel("اختيار تاريخ اليوميات")).toHaveValue(value);
  await expect(page.locator(".diary-entry-skeleton")).toHaveCount(0);
  await expect(page.locator(".diary-summary-loading")).toHaveCount(0);
  await expect(page.getByRole("status").filter({ hasText: "جارٍ تحميل وجبات اليوم" })).toHaveCount(0);
  await expect(page.getByRole("status").filter({ hasText: "جارٍ تحميل ملخص اليوم" })).toHaveCount(0);
  await expect(page.locator(".diary-error-state")).toHaveCount(0);
  await expect(page.locator(".week-inline-error")).toHaveCount(0);
}

test.describe("Diary snapshot safety after Food delete @foods", () => {
  test("[FOOD-TC-122] @p0 historical Diary entry survives Food hard delete", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Snapshot-Delete-${Date.now()}`, calories: 175, protein_g: 8, carb_g: 20, fat_g: 7 });
    const date = diaryDate();
    const entry = await foodsApi.createDiary(food.id, date, 1.5);
    await foodsApi.remove(food.id);

    const stored = (await foodsApi.listDiary(date)).find((item) => item.id === entry.id)!;
    expect(stored.nutrition_snapshot.name).toBe(food.name);
    expect(stored.totals.calories).toBe(262.5);

    await navigateToSnapshotDiary(page, date, entry.id);
    await expect(page.getByText(food.name, { exact: true })).toBeVisible();
    await expect(page.getByText(/262\.5|263/).first()).toBeVisible();
  });
});
