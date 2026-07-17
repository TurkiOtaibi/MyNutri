import type { Page } from "@playwright/test";

import { API_TOKEN, API_URL, expect, test, uniqueName } from "./foods/helpers";

function localDate(days = 0): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

async function selectDiaryDate(page: Page, value: string) {
  await page.waitForFunction(() => {
    const picker = document.querySelector('input[aria-label="اختيار تاريخ اليوميات"]');
    return picker != null && Object.keys(picker).some((key) => key.startsWith("__reactProps$"));
  });
  const picker = page.getByLabel("اختيار تاريخ اليوميات");
  await picker.fill(value);
  await expect(picker).toHaveValue(value);
}

test.describe("@nutrition-quality", () => {
  test("Profile exposes approved additional targets without fabricated limits", async ({ page }) => {
    await page.goto("/profile");
    const card = page.getByRole("region", { name: "أهداف غذائية إضافية" });
    await expect(card).toContainText("الألياف");
    await expect(card).toContainText("30 جم");
    await expect(card).toContainText("حد أدنى");
    await expect(card).toContainText("البوتاسيوم");
    await expect(card).toContainText("كمية كافية");
    await expect(card).toContainText("الفولات (DFE)");
    await expect(card).toContainText("فيتامين أ (RAE)");
    await expect(card).toContainText("الكوليسترول");
    await expect(card).toContainText("متابعة فقط");
    await expect(card.locator(".profile-additional-target-row")).toHaveCount(16);
  });

  test("Diary meal macros and nutritional coverage use frozen snapshot values", async ({ page, foodsApi }) => {
    const date = localDate(-340);
    const food = await foodsApi.create({ name: uniqueName("Nutrition quality"), calories: 156, protein_g: 12.6, carb_g: 1.2, fat_g: 10.6, fiber_g: 0, sodium_mg: null, potassium_mg: 410 });
    await foodsApi.createDiary(food.id, date, 1, "breakfast");
    await page.goto("/diary");
    await selectDiaryDate(page, date);
    const breakfast = page.locator("#meal-section-breakfast");
    await expect(breakfast).toContainText("بروتين 12.6 جم");
    await expect(breakfast).toContainText("كارب 1.2 جم");
    await expect(breakfast).toContainText("دهون 10.6 جم");
    await page.getByRole("button", { name: "عرض التفاصيل الغذائية" }).click();
    const sheet = page.getByRole("dialog", { name: "التفاصيل الغذائية لليوم" });
    await expect(sheet).toContainText("الألياف");
    await expect(sheet).toContainText("0 جم");
    await expect(sheet).toContainText("تغطية البيانات 100%");
    const sodium = sheet.locator(".daily-nutrient-row").filter({ hasText: "الصوديوم" });
    await expect(sodium).toContainText("غير متوفر");
    await expect(sodium).toContainText("تغطية البيانات 0%");
    await expect(sodium).not.toContainText("على الأقل");
  });

  test("Diary partial coverage renders the Backend confirmed minimum without a remaining allowance", async ({ page, foodsApi }) => {
    const date = localDate();
    const known = await foodsApi.create({ name: uniqueName("Known fiber"), fiber_g: 5, sodium_mg: 0 });
    const unknown = await foodsApi.create({ name: uniqueName("Unknown fiber"), fiber_g: null, sodium_mg: null });
    await foodsApi.createDiary(known.id, date, 1, "breakfast");
    await foodsApi.createDiary(unknown.id, date, 1, "lunch");

    await page.goto("/diary");
    await selectDiaryDate(page, date);
    await expect(page.locator("#meal-section-breakfast")).toContainText(known.name);
    await expect(page.locator("#meal-section-lunch")).toContainText(unknown.name);
    await page.getByRole("button", { name: "عرض التفاصيل الغذائية" }).click();

    const sheet = page.getByRole("dialog", { name: "التفاصيل الغذائية لليوم" });
    const fiber = sheet.locator(".daily-nutrient-row").filter({ hasText: "الألياف" });
    await expect(fiber).toContainText("5 جم");
    await expect(fiber).toContainText("على الأقل");
    await expect(fiber).toContainText("تغطية البيانات 50%");
    await expect(fiber).toContainText("لا يمكن تحديد الحالة مع التغطية الجزئية");
    await expect(fiber).not.toContainText("المتبقي");
  });

  test("Food Details distinguishes explicit zero from missing values and limits completeness to Details", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Completeness"), fiber_g: 0, sodium_mg: null, saturated_fat_g: 0, added_sugar_g: null, potassium_mg: 0, cholesterol_mg: null });
    await page.goto(`/foods/${food.id}`);
    const completeness = page.getByRole("region", { name: /اكتمال البيانات الغذائية/ });
    await expect(completeness).toBeVisible();
    await completeness.getByRole("button", { name: "عرض التفاصيل" }).click();
    await expect(completeness).toContainText("الصوديوم");
    await expect(completeness).toContainText("السكر المضاف");
    await expect(completeness).toContainText("الكوليسترول");
    await expect(completeness).not.toContainText("الألياف", { useInnerText: true });
    await page.goto("/foods");
    await expect(page.getByText("اكتمال البيانات الغذائية")).toHaveCount(0);
  });
});
