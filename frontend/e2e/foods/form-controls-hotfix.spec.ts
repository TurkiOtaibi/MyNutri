import { expect, fillRequiredFoodForm, submitFoodForm, test } from "./helpers";

test.describe("Food two-level taxonomy controls", () => {
  test("dependent taxonomy persists approved primary and subcategory keys", async ({ page, foodsApi }) => {
    const name = `E2E-Bakery-${Date.now()}`;
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, {
      name,
      primary_category: "bakery",
      subcategory: "bread"
    });

    await submitFoodForm(page);
    await expect(page).toHaveURL(/\/foods\/[0-9a-f-]+$/);
    const id = page.url().split("/").pop()!;
    const food = await foodsApi.get(id);
    expect(food.primary_category).toBe("bakery");
    expect(food.subcategory).toBe("bread");
  });

  test("changing primary category clears an incompatible subcategory", async ({ page }) => {
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, {
      primary_category: "grains_and_starches",
      subcategory: "rice"
    });
    await expect(page.getByLabel("التصنيف الفرعي")).toHaveValue("rice");

    await page.getByLabel("التصنيف الرئيسي").selectOption("bakery");
    await expect(page.getByLabel("التصنيف الفرعي")).toHaveValue("bread");
    await expect(page.getByLabel("التصنيف الفرعي").locator('option[value="rice"]')).toHaveCount(0);
  });

  for (const width of [320, 390, 430]) {
    test(`taxonomy and source controls remain reachable at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 844 });
      await page.goto("/foods/new");
      const source = page.getByLabel("مصدر البيانات الغذائية");
      await source.scrollIntoViewIfNeeded();
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
    });
  }
});
