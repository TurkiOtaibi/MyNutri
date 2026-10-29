import { diaryDate as localDate, expect, test, uniqueName } from "../foods/helpers";

async function selectDate(page: import("@playwright/test").Page, value: string) {
  const picker = page.getByLabel("اختيار تاريخ اليوميات");
  await expect(picker).toBeEditable();
  await picker.fill(value);
  await expect(picker).toHaveValue(value);
  await expect(page.locator(".diary-entry-skeleton")).toHaveCount(0);
}

test.describe("@diary @polish-oct29 Diary summary and week polish", () => {
  test("@p1 empty week days hide «0 سعرة» visually but keep it for screen readers", async ({ page }) => {
    await page.goto("/diary");
    await selectDate(page, "2024-03-05");
    const days = page.locator(".compact-week-day");
    await expect(days).toHaveCount(7);
    for (const day of await days.all()) {
      await expect(day.locator("small")).toBeHidden();
      await expect(day.locator("i")).toHaveCount(0);
      await expect(day).toHaveAttribute("aria-label", /، 0 سعرة$/);
    }
  });

  test("@p1 summary shows whole grams, a ring progressbar, and meal icons never overlap their titles", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Decimal macros"), calories: 120, protein_g: 12.6, carb_g: 7.3, fat_g: 4.4 });
    await foodsApi.createDiary(food.id, localDate(), 1, "breakfast");
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/diary");
    await selectDate(page, localDate());

    const summary = page.locator(".diary-summary");
    await expect(summary.getByRole("progressbar", { name: /% من هدف السعرات$/ })).toHaveClass(/calorie-ring-progress/);
    for (const expression of await summary.locator(".macro-value-expression").all()) {
      await expect(expression).toHaveText(/^\d+ من \d+ جم$/);
    }

    for (const meal of ["breakfast", "lunch"]) {
      const toggle = page.locator(`#meal-section-${meal} .meal-toggle`);
      const icon = (await toggle.locator("> svg").first().boundingBox())!;
      const copy = (await toggle.locator(".meal-title-copy").boundingBox())!;
      // RTL: the icon sits on the right, so the title copy must end before the icon starts.
      expect(copy.x + copy.width).toBeLessThanOrEqual(icon.x + 0.5);
    }
  });
});
