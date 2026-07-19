import { test, expect, expectNoHorizontalOverflow } from "./helpers";

test.describe("Foods navigation and standalone pages @foods", () => {
  test("[FOOD-TC-001] @p0 navigates list, add, details, and edit routes", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: "E2E Navigation Rice" });
    await page.goto("/admin/foods");
    await page.getByRole("link", { name: "إضافة طعام" }).click();
    await expect(page).toHaveURL(/\/foods\/new$/);
    await page.goto("/admin/foods");
    await page.getByRole("link", { name: `عرض تفاصيل ${food.name}` }).first().click();
    await expect(page).toHaveURL(new RegExp(`/foods/${food.id}$`));
    await page.getByRole("link", { name: "تعديل" }).click();
    await expect(page).toHaveURL(new RegExp(`/foods/${food.id}/edit$`));
  });

  test("[FOOD-TC-002] @p0 add page has save/cancel/back and no delete", async ({ page }) => {
    await page.goto("/foods/new");
    await expect(page.getByRole("button", { name: "حفظ الطعام" })).toBeVisible();
    await expect(page.getByRole("link", { name: "إلغاء" })).toBeVisible();
    await expect(page.getByRole("link", { name: "رجوع" })).toBeVisible();
    await expect(page.getByRole("button", { name: /حذف/ })).toHaveCount(0);
  });

  test("[FOOD-TC-003] @p0 list page does not contain the Add Food form", async ({ page }) => {
    await page.goto("/foods");
    await expect(page.getByRole("heading", { name: "الأطعمة" })).toBeVisible();
    await expect(page.getByRole("link", { name: "إضافة طعام" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "حفظ الطعام" })).toHaveCount(0);
    await expect(page.locator("form.food-form-layout")).toHaveCount(0);
  });

  test("[FOOD-TC-004] @p1 edit reuses grouped Add Food structure", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: "E2E Edit Structure" });
    await page.goto(`/foods/${food.id}/edit`);
    await expect(page.getByRole("heading", { name: "تعديل الطعام" })).toBeVisible();
    for (const heading of ["معلومات الطعام الأساسية", "أساس القيم الغذائية", "القيم الغذائية الأساسية", "الوحدة الافتراضية", "ملاحظات ومصدر البيانات"]) {
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    }
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue(food.name);
    await expect(page.getByRole("button", { name: "حفظ التعديل" })).toBeVisible();
    await expect(page.getByRole("button", { name: "حذف" })).toBeVisible();
  });

  test("[FOOD-TC-005] @p1 @mobile standalone pages fit a 360px viewport", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    for (const route of ["/foods/new", "/foods"]) {
      await page.goto(route);
      await expectNoHorizontalOverflow(page);
    }
  });

  test("[FOOD-TC-006] @p1 cancel returns without saving", async ({ page, foodsApi }) => {
    const draft = `E2E-Draft-${Date.now()}`;
    await page.goto("/foods/new");
    await page.getByLabel(/اسم الطعام/).fill(draft);
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("link", { name: "إلغاء" }).click();
    await expect(page).toHaveURL(/\/foods$/);
    expect((await foodsApi.list()).some((food) => food.name === draft)).toBeFalsy();
  });

  test("[FOOD-TC-007] @p0 unauthorized Foods read exposes no catalog data", async ({ page }) => {
    await page.route(/\/foods(?:\?.*)?$/, async (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      await route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Unauthorized" }) });
    });
    await page.goto("/foods");
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(0);
  });
});
