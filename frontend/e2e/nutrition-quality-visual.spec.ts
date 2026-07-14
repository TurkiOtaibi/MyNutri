import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test, uniqueName } from "./foods/helpers";

const output = resolve(process.cwd(), "..", "docs", "ui-ux", "screenshots", "nutrition-quality");

test.beforeAll(async () => mkdir(output, { recursive: true }));

test("capture Profile targets and additional nutrients", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/profile");
  await expect(page.getByRole("region", { name: "أهداف غذائية إضافية" })).toBeVisible();
  await page.screenshot({ path: resolve(output, "01-profile-additional-targets-390.png"), fullPage: true });
  await page.getByRole("button", { name: /فتح الخيارات المتقدمة/ }).click();
  await page.screenshot({ path: resolve(output, "02-profile-macro-defaults-390.png"), fullPage: true });
});

test("capture Diary meal macros and nutritional details", async ({ page, foodsApi }) => {
  const food = await foodsApi.create({ name: uniqueName("Visual nutrients"), calories: 156, protein_g: 12.6, carb_g: 24, fat_g: 10.6, fiber_g: 18, sodium_mg: 840, saturated_fat_g: 2.5, added_sugar_g: 0, potassium_mg: null, cholesterol_mg: 220 });
  const date = new Date(); date.setDate(date.getDate() - 360);
  const input = new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
  await foodsApi.createDiary(food.id, input, 1, "breakfast");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/diary");
  await page.getByLabel("اختيار تاريخ اليوميات").fill(input);
  await expect(page.locator("#meal-section-breakfast")).toContainText("بروتين 12.6 جم");
  await page.screenshot({ path: resolve(output, "03-diary-meal-macros-390.png"), fullPage: true });
  await page.getByRole("button", { name: "عرض التفاصيل الغذائية" }).click();
  await page.screenshot({ path: resolve(output, "04-diary-nutrition-details-390.png"), fullPage: true });
  await page.locator(".nutrition-coverage-notice").screenshot({ path: resolve(output, "05-diary-coverage-notice.png") });
});

test("capture Food completeness compact, expanded, and narrow", async ({ page, foodsApi }) => {
  const food = await foodsApi.create({ name: uniqueName("Completeness visual"), fiber_g: 0, sodium_mg: null, saturated_fat_g: 0, added_sugar_g: null, potassium_mg: 410, cholesterol_mg: null });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/foods/${food.id}`);
  const card = page.getByRole("region", { name: /اكتمال البيانات الغذائية/ });
  await card.screenshot({ path: resolve(output, "06-food-completeness-compact-390.png") });
  await card.getByRole("button", { name: "عرض التفاصيل" }).click();
  await card.screenshot({ path: resolve(output, "07-food-completeness-expanded-390.png") });
  await page.setViewportSize({ width: 320, height: 760 });
  await page.screenshot({ path: resolve(output, "08-food-details-nutrients-320.png"), fullPage: true });
});
