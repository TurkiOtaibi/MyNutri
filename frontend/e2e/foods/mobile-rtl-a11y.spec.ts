import { test, expect, expectNoHorizontalOverflow, fillRequiredFoodForm, submitFoodForm } from "./helpers";

test.describe("Foods mobile, RTL, and accessibility @foods", () => {
  test("[FOOD-TC-135] @p1 @a11y field errors are associated with invalid inputs", async ({ page }) => {
    await page.goto("/foods/new");
    await submitFoodForm(page);
    const name = page.getByLabel(/اسم الطعام/);
    await expect(name).toHaveAttribute("aria-invalid", "true");
    const errorId = await name.getAttribute("aria-describedby");
    expect(errorId).toBeTruthy();
    await expect(page.locator(`#${errorId}`)).toHaveText("هذا الحقل مطلوب.");
    await expect(page.locator(".state-note[role=alert]")).toBeVisible();
  });

  test("[FOOD-TC-136] @p1 @a11y icon actions have contextual accessible names", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Accessible-Actions-${Date.now()}` });
    await page.goto("/foods");
    await expect(page.getByRole("link", { name: `عرض تفاصيل ${food.name}` }).first()).toBeVisible();
    const actions = page.getByRole("button", { name: `إجراءات ${food.name}` });
    await expect(actions).toBeVisible();
    await actions.click();
    await expect(page.getByRole("menuitem", { name: "تعديل" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "حذف" })).toBeVisible();
  });

  test("[FOOD-TC-139] @p1 @mobile required viewport matrix has no horizontal page overflow", async ({ page, foodsApi }) => {
    await foodsApi.create({ name: `طعام E2E Mixed Long ${"اسم ".repeat(15)}`.slice(0, 120) });
    for (const width of [360, 390, 430, 768, 1280]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/foods");
      await expectNoHorizontalOverflow(page);
      expect(await page.locator("html").getAttribute("dir")).toBe("rtl");
      if (width <= 920) await expect(page.locator(".food-card-list")).toBeVisible();
      else await expect(page.locator(".food-table-wrap")).toBeVisible();
    }
  });
});
