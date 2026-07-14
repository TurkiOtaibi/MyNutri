import { test, expect } from "./helpers";

test.describe("Food permanent delete @foods", () => {
  test("[FOOD-TC-118] @p0 confirmation dialog shows Food name and permanent wording", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Delete-Dialog-${Date.now()}` });
    await page.goto("/foods");
    await openDeleteFromList(page, food.name);
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText(food.name);
    await expect(dialog).toContainText("نهائيًا");
  });

  test("[FOOD-TC-119] @p0 cancel closes dialog and keeps Food", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Delete-Cancel-${Date.now()}` });
    await page.goto("/foods");
    await openDeleteFromList(page, food.name);
    const dialog = page.getByRole("dialog");
    await expect(dialog).toContainText("ستبقى اليوميات السابقة");
    await dialog.getByRole("button", { name: "إلغاء" }).click();
    await expect(dialog).toHaveCount(0);
    expect((await foodsApi.list()).some((item) => item.id === food.id)).toBeTruthy();
  });

  test("[FOOD-TC-120] @p0 confirm permanently deletes Food", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Delete-Confirm-${Date.now()}` });
    await page.goto("/foods");
    await openDeleteFromList(page, food.name);
    await page.getByRole("dialog").getByRole("button", { name: "حذف نهائي" }).click();
    await expect(page.getByText(food.name, { exact: true })).toHaveCount(0);
    expect((await foodsApi.list()).some((item) => item.id === food.id)).toBeFalsy();
  });

  test("[FOOD-TC-121] @p0 deleted Food disappears from future Diary selection", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Delete-Picker-${Date.now()}` });
    await foodsApi.remove(food.id);
    await page.goto("/diary");
    await expect(page.getByRole("option", { name: new RegExp(food.name) })).toHaveCount(0);
  });

  test("[FOOD-TC-123] @p0 failed delete keeps Food and queues nothing", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Delete-Fail-${Date.now()}` });
    await page.goto("/foods");
    await openDeleteFromList(page, food.name);
    await page.route(`**/foods/${food.id}`, async (route) => {
      if (route.request().method() === "DELETE") return route.abort("failed");
      return route.continue();
    });
    await page.getByRole("dialog").getByRole("button", { name: "حذف نهائي" }).click();
    await expect(page.getByText("تعذر الاتصال بالخادم. لم يتم حفظ التغييرات.", { exact: true })).toBeVisible();
    expect((await foodsApi.list()).some((item) => item.id === food.id)).toBeTruthy();
    expect(await page.evaluate(() => indexedDB.databases().then((items) => items.length))).toBe(0);
  });

  test("[FOOD-TC-124] @p1 repeated confirm sends one delete request", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Delete-One-${Date.now()}` });
    let deletes = 0;
    page.on("request", (request) => {
      if (request.method() === "DELETE" && request.url().endsWith(`/foods/${food.id}`)) deletes += 1;
    });
    await page.goto("/foods");
    await openDeleteFromList(page, food.name);
    await page.getByRole("dialog").getByRole("button", { name: "حذف نهائي" }).dblclick();
    await expect(page.getByText(food.name, { exact: true })).toHaveCount(0);
    expect(deletes).toBe(1);
  });

  test("[FOOD-TC-125] @p0 delete uses no archive/inactive state", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-No-Archive-${Date.now()}` });
    const record = await foodsApi.get(food.id);
    expect(record).not.toHaveProperty("is_active");
    expect(record).not.toHaveProperty("archived_at");
    await page.goto(`/foods/${food.id}`);
    for (const text of ["مؤرشف", "غير نشط", "استعادة", "is_active", "archived_at"]) {
      await expect(page.getByText(text, { exact: false })).toHaveCount(0);
    }
  });

  test("[FOOD-TC-126] @p0 @a11y dialog supports focus, Escape, and focus restoration", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Delete-A11y-${Date.now()}` });
    await page.goto("/foods");
    const trigger = page.locator("tbody tr", { hasText: food.name }).locator(".icon-button");
    await trigger.focus();
    await trigger.press("Enter");
    await page.getByRole("menuitem", { name: "حذف" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toHaveAttribute("aria-modal", "true");
    await expect(dialog.getByRole("button", { name: "إلغاء" })).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(trigger).toBeFocused();
  });

  test("[FOOD-TC-127] @p0 unauthorized delete leaves Food unchanged", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Delete-Unauthorized-${Date.now()}` });
    await page.goto("/foods");
    await openDeleteFromList(page, food.name);
    await page.route(`**/foods/${food.id}`, async (route) => {
      if (route.request().method() === "DELETE") return route.fulfill({ status: 401, body: "unauthorized" });
      return route.continue();
    });
    await page.getByRole("dialog").getByRole("button", { name: "حذف نهائي" }).click();
    expect((await foodsApi.list()).some((item) => item.id === food.id)).toBeTruthy();
  });
});

async function openDeleteFromList(page: import("@playwright/test").Page, foodName: string) {
  const row = page.locator("tbody tr", { hasText: foodName });
  await row.locator(".icon-button").click();
  await row.locator(".danger-menu-item").click();
}
