import { test, expect, fillRequiredFoodForm, submitFoodForm } from "./helpers";

test.describe("Foods online-only behavior @foods", () => {
  test("[FOOD-TC-137] @p0 API read failure does not use local personal data", async ({ page }) => {
    await page.route(/\/foods(?:\?.*)?$/, async (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      await route.abort("failed");
    });
    await page.goto("/foods");
    await expect(page.locator(".catalog-state[role=alert]")).toContainText("تعذر تحميل قائمة الأطعمة. تحقق من الاتصال وحاول مرة أخرى.");
    expect(await page.evaluate(() => indexedDB.databases().then((items) => items.length))).toBe(0);
    await expect(page.locator("tbody tr")).toHaveCount(0);
  });

  test("[FOOD-TC-138] @p0 failed write is not saved or queued offline", async ({ page, foodsApi }) => {
    const name = `E2E-No-Queue-${Date.now()}`;
    await page.route("**/foods", async (route) => {
      if (route.request().method() === "POST") return route.abort("failed");
      return route.continue();
    });
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, { name });
    await submitFoodForm(page);
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue(name);
    const body = await page.locator("body").innerText();
    expect(body).not.toContain("تم الحفظ محليًا");
    expect(body).not.toContain("سيتم المزامنة لاحقًا");
    expect(body).not.toContain("pending sync");
    expect(await page.evaluate(() => indexedDB.databases().then((items) => items.length))).toBe(0);
    expect((await foodsApi.list()).some((food) => food.name === name)).toBeFalsy();
  });
});
