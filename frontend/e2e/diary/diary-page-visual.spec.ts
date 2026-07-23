import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

import { diaryDate as localDate, expect, test, uniqueName } from "../foods/helpers";

const output = resolve("..", "docs", "ui-ux", "screenshots", "diary-page-refinement");

test("@diary @visual capture compact Diary page production states", async ({ page, foodsApi }) => {
  await mkdir(output, { recursive: true });
  await page.emulateMedia({ reducedMotion: "reduce" });
  const breakfast = await foodsApi.create({ name: uniqueName("بيض مسلوق Breakfast"), calories: 156, protein_g: 12.6, carb_g: 1.2, fat_g: 10.6, default_unit_type: "piece", unit_amount: 50 });
  const secondBreakfast = await foodsApi.create({ name: uniqueName("Toast Mixed توست طويل"), calories: 260, protein_g: 10, carb_g: 40, fat_g: 7, default_unit_type: "slice", unit_amount: 30 });
  const lunch = await foodsApi.create({ name: uniqueName("غداء عربي"), calories: 300 });
  const dinner = await foodsApi.create({ name: uniqueName("Dinner عشاء"), calories: 350 });
  const snack = await foodsApi.create({ name: uniqueName("سناك"), calories: 180 });
  await foodsApi.createDiary(breakfast.id, localDate(), 1, "breakfast");
  await foodsApi.createDiary(secondBreakfast.id, localDate(), 1, "breakfast");
  await foodsApi.createDiary(lunch.id, localDate(), 1, "lunch");
  await foodsApi.createDiary(dinner.id, localDate(), 1, "dinner");
  await foodsApi.createDiary(snack.id, localDate(), 1, "snack");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/diary");
  await expect(page.getByRole("heading", { name: breakfast.name })).toBeVisible();
  await page.screenshot({ path: resolve(output, "01-current-populated-breakfast-390.png") });
  await page.screenshot({ path: resolve(output, "02-all-four-meals-390.png"), fullPage: true });

  const emptyDate = localDate(-270);
  await page.getByLabel("اختيار تاريخ اليوميات").fill(emptyDate);
  await expect(page.getByText("لا توجد أطعمة مسجلة اليوم")).toBeVisible();
  await page.screenshot({ path: resolve(output, "03-empty-day-390.png"), fullPage: true });
  await page.screenshot({ path: resolve(output, "04-other-date-today-action-390.png") });

  const overDate = localDate();
  const over = await foodsApi.create({ name: uniqueName("Over targets"), calories: 2500, protein_g: 250, carb_g: 300, fat_g: 100 });
  await foodsApi.createDiary(over.id, overDate, 1, "breakfast");
  const refreshedWeek = page.waitForResponse((response) => response.url().includes("/diary/week?") && response.ok());
  await page.reload();
  await refreshedWeek;
  await expect(page.getByRole("heading", { name: over.name })).toBeVisible();
  await expect(page.getByText(/فوق الهدف/).first()).toBeVisible();
  await page.screenshot({ path: resolve(output, "05-above-calorie-target-390.png") });
  await page.screenshot({ path: resolve(output, "06-above-macro-target-390.png"), fullPage: true });

  await page.getByLabel("اختيار تاريخ اليوميات").fill(localDate());
  await expect(page.getByRole("heading", { name: secondBreakfast.name })).toBeVisible();
  await page.screenshot({ path: resolve(output, "07-expanded-meal-multiple-rows-390.png"), fullPage: true });
  await page.getByRole("button", { name: `خيارات ${breakfast.name}` }).click();
  await page.screenshot({ path: resolve(output, "08-food-options-menu-390.png") });
  await page.getByRole("menuitem", { name: "حذف" }).click();
  await page.screenshot({ path: resolve(output, "09-delete-confirmation-390.png") });
  await page.getByRole("button", { name: "إبقاء الطعام" }).click();

  let delay = true;
  await page.route("**/diary?entry_date=*", async (route) => {
    if (delay) await new Promise((resolveDelay) => setTimeout(resolveDelay, 900));
    return route.continue();
  });
  await page.getByLabel("اختيار تاريخ اليوميات").fill(localDate(-272));
  await expect(page.locator(".diary-entry-skeleton").first()).toBeVisible();
  await page.screenshot({ path: resolve(output, "10-date-loading-skeleton-390.png") });
  delay = false;
  await expect(page.locator(".diary-entry-skeleton")).toHaveCount(0);
  await page.unroute("**/diary?entry_date=*");

  await page.route("**/diary?entry_date=*", (route) => route.abort("failed"));
  await page.getByLabel("اختيار تاريخ اليوميات").fill(localDate(-273));
  await expect(page.getByText("تعذر تحميل بيانات هذا اليوم")).toBeVisible();
  await page.screenshot({ path: resolve(output, "11-day-load-error-390.png") });
  await page.unroute("**/diary?entry_date=*");

  for (const [index, width] of [[12, 320], [13, 390], [14, 430]] as const) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/diary");
    await expect(page.locator(".compact-week-nav")).toBeVisible();
    await expect(page.getByRole("heading", { name: "ملخص اليوم" })).toBeVisible();
    await page.screenshot({ path: resolve(output, `${index}-viewport-${width}.png`), fullPage: true });
  }
});
