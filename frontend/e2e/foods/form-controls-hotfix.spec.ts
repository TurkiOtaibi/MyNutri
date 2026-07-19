import { expect, fillRequiredFoodForm, submitFoodForm, test } from "./helpers";

test.describe("Food form disclosure and required select hotfix", () => {
  test("conditional required selects expose placeholders and persist explicit choices", async ({ page, foodsApi }) => {
    const bakedName = `E2E-Baked-Placeholder-${Date.now()}`;
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, { name: bakedName });
    await page.getByLabel(/فئة الطعام/).selectOption("baked_goods");

    const bakedType = page.getByLabel(/نوع المخبوزات/);
    await expect(bakedType).toHaveValue("");
    await expect(bakedType.locator('option[value=""]')).toHaveText("اختر نوع المخبوزات");
    expect(await bakedType.locator('option[value=""]').evaluate((option: HTMLOptionElement) => option.disabled)).toBe(true);
    await expect(bakedType.locator("option:checked")).toHaveText("اختر نوع المخبوزات");
    await expect(bakedType.locator("option:checked")).not.toHaveText("خبز عربي");

    await submitFoodForm(page);
    await expect(bakedType).toHaveAttribute("aria-invalid", "true");
    await expect(bakedType.locator("xpath=following-sibling::*[@class='field-error']")).toHaveText("هذا الحقل مطلوب.");

    await bakedType.selectOption("arabic_bread");
    await expect(bakedType).toHaveValue("arabic_bread");
    await expect(bakedType).toHaveAttribute("aria-invalid", "false");
    await expect(bakedType.locator("xpath=following-sibling::*[@class='field-error']")).toHaveCount(0);
    await submitFoodForm(page);
    await expect(page).toHaveURL(/\/foods\/[0-9a-f-]+$/);
    const bakedId = page.url().split("/").pop()!;
    expect((await foodsApi.get(bakedId)).baked_good_type).toBe("arabic_bread");

    const grainName = `E2E-Grain-Placeholder-${Date.now()}`;
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, { name: grainName });
    await page.getByLabel(/فئة الطعام/).selectOption("grains_starches");
    const grainType = page.getByLabel(/نوع الحبوب أو النشويات/);
    await expect(grainType).toHaveValue("");
    await expect(grainType.locator("option:checked")).toHaveText("اختر نوع الحبوب أو النشويات");
    await grainType.selectOption("rice");
    await expect(grainType).toHaveValue("rice");
    await submitFoodForm(page);
    await expect(page).toHaveURL(/\/foods\/[0-9a-f-]+$/);
    const grainId = page.url().split("/").pop()!;
    expect((await foodsApi.get(grainId)).grain_starch_type).toBe("rice");
  });

  test("category changes clear irrelevant values and stale conditional errors", async ({ page }) => {
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page);
    await page.getByLabel(/فئة الطعام/).selectOption("baked_goods");
    await submitFoodForm(page);
    await expect(page.getByLabel(/نوع المخبوزات/)).toHaveAttribute("aria-invalid", "true");

    await page.getByLabel(/فئة الطعام/).selectOption("grains_starches");
    await expect(page.getByLabel(/نوع المخبوزات/)).toHaveCount(0);
    const grainType = page.getByLabel(/نوع الحبوب أو النشويات/);
    await expect(grainType).toHaveValue("");
    await expect(grainType).toHaveAttribute("aria-invalid", "false");

    await grainType.selectOption("oats");
    await page.getByLabel(/فئة الطعام/).selectOption("fruits");
    await expect(page.getByLabel(/نوع الحبوب أو النشويات/)).toHaveCount(0);
    await page.getByLabel(/فئة الطعام/).selectOption("grains_starches");
    await expect(page.getByLabel(/نوع الحبوب أو النشويات/)).toHaveValue("");
  });

  test("advanced analysis is an obvious accessible disclosure and opens on validation error", async ({ page }) => {
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page);
    const advanced = page.locator("details.advanced-analysis");
    const summary = advanced.locator("summary");

    await expect(advanced).not.toHaveAttribute("open", "");
    await expect(summary).toContainText("اختياري");
    await expect(summary).toContainText("فتح وإدارة التحليل");
    await expect(summary.locator(".advanced-analysis-chevron")).toBeVisible();

    await summary.focus();
    await page.keyboard.press("Enter");
    await expect(advanced).toHaveAttribute("open", "");
    await expect(page.getByText("المجموعات الغذائية", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "إضافة مجموعة غذائية" })).toBeVisible();
    await expect(page.getByText("السمات التحليلية", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "عرض المزيد" })).toBeVisible();

    await page.getByRole("button", { name: "إضافة مجموعة غذائية" }).click();
    await page.getByLabel("المقدار من 100 (1)").fill("0");
    await summary.click();
    await expect(advanced).not.toHaveAttribute("open", "");
    await submitFoodForm(page);
    await expect(advanced).toHaveAttribute("open", "");
    await expect(advanced.getByRole("alert")).toContainText("يجب أن تكون كل مساهمة أكبر من صفر.");
  });

  for (const width of [320, 390, 430]) {
    test(`advanced analysis remains reachable above the sticky save bar at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 844 });
      await page.goto("/foods/new");
      const advanced = page.locator("details.advanced-analysis");
      await advanced.locator("summary").click();
      const addGroup = page.getByRole("button", { name: "إضافة مجموعة غذائية" });
      await addGroup.scrollIntoViewIfNeeded();
      const geometry = await page.evaluate(() => {
        const control = [...document.querySelectorAll("button")].find((item) => item.textContent?.includes("إضافة مجموعة غذائية"))?.getBoundingClientRect();
        const bar = document.querySelector(".form-actions-sticky")?.getBoundingClientRect();
        return {
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          controlBottom: control?.bottom ?? 0,
          barTop: bar?.top ?? innerHeight
        };
      });
      expect(geometry.overflow).toBeLessThanOrEqual(1);
      expect(geometry.controlBottom).toBeLessThanOrEqual(geometry.barTop);
    });
  }
});
