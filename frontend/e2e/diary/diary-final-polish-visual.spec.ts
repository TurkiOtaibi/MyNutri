import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

import { API_TOKEN, API_URL, expect, test, uniqueName } from "../foods/helpers";

const output = resolve("..", "docs", "ui-ux", "screenshots", "diary-final-polish");

function localDate(days = 0): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

async function selectDate(page: import("@playwright/test").Page, value: string) {
  await page.getByLabel("اختيار تاريخ اليوميات").fill(value);
  await expect(page.locator(".diary-entry-skeleton")).toHaveCount(0);
}

test("@diary @visual capture final Diary polish states", async ({ page, request, foodsApi }) => {
  await mkdir(output, { recursive: true });
  await page.emulateMedia({ reducedMotion: "reduce" });

  const first = await foodsApi.create({
    name: uniqueName("بيض مسلوق"), calories: 78, protein_g: 12.6, carb_g: 1.2, fat_g: 10.6,
    default_unit_type: "piece", unit_amount: 50
  });
  const second = await foodsApi.create({
    name: uniqueName("توست Mixed Arabic English طويل للاختبار"), calories: 78,
    protein_g: 4, carb_g: 12, fat_g: 2, default_unit_type: "slice", unit_amount: 30
  });
  const firstEntry = await foodsApi.createDiary(first.id, localDate(), 1, "breakfast");
  const secondEntry = await foodsApi.createDiary(second.id, localDate(), 1, "breakfast");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/diary");
  await expect.poll(() => page.locator("#meal-breakfast .diary-entry-row").count()).toBeGreaterThanOrEqual(2);
  await page.screenshot({ path: resolve(output, "01-iphone-reference-populated-390.png"), fullPage: true });
  await page.locator(".compact-week-nav").screenshot({ path: resolve(output, "02-current-date-selected-day-390.png") });
  await page.locator("#meal-section-breakfast").screenshot({ path: resolve(output, "04-breakfast-two-compact-rows-390.png") });
  await page.locator(".meal-sections").screenshot({ path: resolve(output, "05-empty-meal-rows-390.png") });

  const profile = await request.get(`${API_URL}/profile`, { headers: { Authorization: `Bearer ${API_TOKEN}` } });
  const targets = (await profile.json()).targets as { protein_g: number; carb_g: number; fat_g: number };
  await request.delete(`${API_URL}/diary/${firstEntry.id}`, { headers: { Authorization: `Bearer ${API_TOKEN}` } });
  await request.delete(`${API_URL}/diary/${secondEntry.id}`, { headers: { Authorization: `Bearer ${API_TOKEN}` } });
  const comparisonDate = localDate();
  const comparison = await foodsApi.create({
    name: uniqueName("Macro comparison"), calories: 100,
    protein_g: targets.protein_g * 0.09,
    carb_g: targets.carb_g * 0.01,
    fat_g: targets.fat_g * 0.22
  });
  await foodsApi.createDiary(comparison.id, comparisonDate, 1, "breakfast");
  const refreshedWeek = page.waitForResponse((response) => response.url().includes("/diary/week?") && response.ok());
  await page.reload();
  await refreshedWeek;
  await expect(page.getByRole("heading", { name: comparison.name })).toBeVisible();
  await expect(page.locator(".macro-progress-row").nth(0)).toContainText("9%");
  await expect(page.locator(".macro-progress-row").nth(1)).toContainText("1%");
  await expect(page.locator(".macro-progress-row").nth(2)).toContainText("22%");
  await page.locator(".diary-summary").screenshot({ path: resolve(output, "03-summary-macros-9-1-22-390.png") });
  const comparisonEntries = await foodsApi.listDiary(comparisonDate);
  const comparisonEntry = comparisonEntries.find((entry) => entry.nutrition_snapshot.name === comparison.name);
  expect(comparisonEntry).toBeDefined();
  await request.delete(`${API_URL}/diary/${comparisonEntry!.id}`, { headers: { Authorization: `Bearer ${API_TOKEN}` } });

  const emptyDate = localDate(-340);
  await selectDate(page, emptyDate);
  await page.screenshot({ path: resolve(output, "06-other-date-today-visible-empty-390.png"), fullPage: true });
  await page.locator(".diary-summary").screenshot({ path: resolve(output, "07-summary-macros-zero-390.png") });

  const overDate = localDate();
  const over = await foodsApi.create({ name: uniqueName("Macro full over"), calories: 1800, protein_g: 160, carb_g: 172.3, fat_g: 60 });
  await foodsApi.createDiary(over.id, overDate, 1, "breakfast");
  const refreshedOverWeek = page.waitForResponse((response) => response.url().includes("/diary/week?") && response.ok());
  await page.reload();
  await refreshedOverWeek;
  await expect(page.getByRole("heading", { name: over.name })).toBeVisible();
  await page.locator(".diary-summary").screenshot({ path: resolve(output, "08-summary-macros-100-over-390.png") });

  await foodsApi.createDiary(first.id, localDate(), 1, "breakfast");
  await foodsApi.createDiary(second.id, localDate(), 1, "breakfast");
  for (const width of [320, 430]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/diary");
    await expect.poll(() => page.locator("#meal-breakfast .diary-entry-row").count()).toBeGreaterThanOrEqual(2);
    await page.screenshot({ path: resolve(output, `09-viewport-${width}.png`), fullPage: true });
  }
});
