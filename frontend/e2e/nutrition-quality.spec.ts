import { API_TOKEN, API_URL, expect, test, uniqueName } from "./foods/helpers";

function localDate(days = 0): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
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
    await page.getByLabel("اختيار تاريخ اليوميات").fill(date);
    const breakfast = page.locator("#meal-section-breakfast");
    await expect(breakfast).toContainText("بروتين 12.6 جم");
    await expect(breakfast).toContainText("كارب 1.2 جم");
    await expect(breakfast).toContainText("دهون 10.6 جم");
    await page.getByRole("button", { name: "عرض التفاصيل الغذائية" }).click();
    const sheet = page.getByRole("dialog", { name: "التفاصيل الغذائية لليوم" });
    await expect(sheet).toContainText("الألياف");
    await expect(sheet).toContainText("0 جم");
    await expect(sheet).toContainText("تغطية البيانات 100%");
    await expect(sheet).toContainText("الصوديوم");
    await expect(sheet).toContainText("على الأقل");
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
