import type { Page } from "@playwright/test";

import { expect, test, uniqueName } from "../foods/helpers";

function localDate(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

async function openGeneral(page: Page) {
  await page.goto("/diary");
  await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
  return page.getByRole("dialog", { name: "إضافة طعام" });
}

async function selectFood(page: Page, name: string) {
  const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
  await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(name);
  await dialog.getByRole("button", { name: new RegExp(name) }).click();
  return dialog;
}

test.describe("@diary @add-food-sheet focused Add Food experience", () => {
  test("@p0 general Add opens search state with recent foods and no premature configure controls", async ({ page, foodsApi }) => {
    const recent = await foodsApi.create({ name: uniqueName("Recent sheet") });
    await foodsApi.createDiary(recent.id, localDate(), 1, "snack");
    const dialog = await openGeneral(page);
    await expect(dialog.getByRole("heading", { name: "إضافة طعام" })).toBeVisible();
    await expect(dialog.getByText("المستخدمة مؤخرًا", { exact: true })).toBeVisible();
    await expect(dialog.getByRole("button", { name: new RegExp(recent.name) })).toBeVisible();
    await expect(dialog.getByRole("heading", { name: "قسم الوجبة" })).toHaveCount(0);
    await expect(dialog.getByRole("button", { name: "إضافة الطعام", exact: true })).toHaveCount(0);
  });

  test("@p0 each meal Add action preserves its preselected meal after Food selection", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Meal preselect") });
    await page.goto("/diary");
    for (const [meal, label] of [["فطور", "الفطور"], ["غداء", "الغداء"], ["عشاء", "العشاء"], ["سناك", "السناك"]] as const) {
      await page.getByRole("button", { name: `إضافة طعام إلى ${meal}` }).click();
      const dialog = await selectFood(page, food.name);
      await expect(dialog.getByRole("radio", { name: meal })).toHaveAttribute("aria-checked", "true");
      await expect(dialog.getByRole("button", { name: `إضافة إلى ${label}` })).toBeEnabled();
      await dialog.getByRole("button", { name: "إلغاء" }).click();
      await dialog.getByRole("button", { name: "إلغاء الإضافة" }).click();
    }
  });

  test("@p0 search supports Food name, brand, clear focus, and no-results copy", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Search name"), brand: uniqueName("BrandSearch") });
    const dialog = await openGeneral(page);
    const search = dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية");
    await search.fill(food.name);
    await expect(dialog.getByRole("button", { name: new RegExp(food.name) })).toBeVisible();
    await search.fill(food.brand!);
    await expect(dialog.getByRole("button", { name: new RegExp(food.name) })).toBeVisible();
    await dialog.getByRole("button", { name: "مسح البحث" }).click();
    await expect(search).toBeFocused();
    await search.fill(`No match ${Date.now()}`);
    await expect(dialog.getByText("لم نجد طعامًا مطابقًا")).toBeVisible();
    await expect(dialog.getByText("جرّب اسمًا آخر أو ابحث بالعلامة التجارية")).toBeVisible();
  });

  test("@p1 loading, search error, and Retry are explicit without blank alerts", async ({ page }) => {
    let fail = true;
    await page.route("**/foods*", async (route) => {
      if (fail) return route.abort("failed");
      return route.continue();
    });
    const dialog = await openGeneral(page);
    await expect(dialog.getByText("تعذر تحميل الأطعمة", { exact: true })).toBeVisible();
    fail = false;
    await dialog.getByRole("button", { name: "إعادة المحاولة" }).click();
    await expect(dialog.getByText("جميع الأطعمة", { exact: true })).toBeVisible();
    await expect(dialog.locator('[role="alert"]:empty')).toHaveCount(0);
  });

  test("@p0 selection hides search and shows compact summary; Change restores query and resets next Food quantity", async ({ page, foodsApi }) => {
    const first = await foodsApi.create({ name: uniqueName("First select"), brand: "علامة أولى", default_unit_type: "piece", unit_amount: 14, calories: 493 });
    const second = await foodsApi.create({ name: uniqueName("Second select"), default_unit_type: "slice", unit_amount: 30 });
    const dialog = await openGeneral(page);
    const search = dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية");
    await search.fill(first.name);
    await dialog.getByRole("button", { name: new RegExp(first.name) }).click();
    await expect(search).toHaveCount(0);
    const summary = dialog.getByLabel(`الطعام المحدد: ${first.name}`);
    await expect(summary).toContainText("علامة أولى");
    await expect(summary).toContainText("14 جم");
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("2.5");
    await dialog.getByRole("button", { name: "تغيير الطعام" }).click();
    await expect(dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية")).toHaveValue(first.name);
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(second.name);
    await dialog.getByRole("button", { name: new RegExp(second.name) }).click();
    await expect(dialog.getByRole("textbox", { name: "الكمية", exact: true })).toHaveValue("1");
  });

  test("@p0 meal selection controls dynamic label and decimal preview", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Dynamic label"), default_unit_type: "piece", unit_amount: 20, calories: 250, protein_g: 10, carb_g: 20, fat_g: 5 });
    const dialog = await openGeneral(page);
    await selectFood(page, food.name);
    await expect(dialog.getByRole("radio", { name: "فطور" })).toHaveAttribute("aria-checked", "true");
    await dialog.getByRole("radio", { name: "غداء" }).click();
    await expect(dialog.getByRole("button", { name: "إضافة إلى الغداء" })).toBeEnabled();
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("2.5");
    const preview = dialog.getByLabel("معاينة القيم الغذائية");
    await expect(preview).toContainText("50 جم");
    await expect(preview).toContainText("125");
    await expect(preview).toContainText("5 جم");
    await expect(preview).toContainText("10 جم");
    await expect(preview).toContainText("2.5 جم");
  });

  test("@p0 save is single-submit, exposes saving state, and inserts into selected meal", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Single modern save") });
    let posts = 0;
    await page.route("**/diary", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      posts += 1;
      await new Promise((resolve) => setTimeout(resolve, 300));
      return route.continue();
    });
    const dialog = await openGeneral(page);
    await selectFood(page, food.name);
    await dialog.getByRole("radio", { name: "عشاء" }).click();
    const save = dialog.getByRole("button", { name: "إضافة إلى العشاء" });
    await save.dblclick();
    await expect(dialog.getByRole("button", { name: /جارٍ الإضافة|تمت الإضافة/ })).toBeVisible();
    await expect(dialog).toHaveCount(0);
    expect(posts).toBe(1);
    const dinner = page.locator("#meal-dinner");
    await expect(dinner.getByRole("heading", { name: food.name })).toBeVisible();
  });

  test("@p0 failed save preserves Food, meal, quantity and provides Retry", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Modern failed save") });
    await page.route("**/diary", (route) => route.request().method() === "POST" ? route.abort("failed") : route.continue());
    const dialog = await openGeneral(page);
    await selectFood(page, food.name);
    await dialog.getByRole("radio", { name: "سناك" }).click();
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("1.5");
    await dialog.getByRole("button", { name: "إضافة إلى السناك" }).click();
    await expect(dialog.getByText("تعذر إضافة الطعام")).toBeVisible();
    await expect(dialog.getByText("حاول مرة أخرى.")).toBeVisible();
    await expect(dialog.getByRole("button", { name: "إعادة المحاولة" })).toBeVisible();
    await expect(dialog.getByLabel(`الطعام المحدد: ${food.name}`)).toBeVisible();
    await expect(dialog.getByRole("radio", { name: "سناك" })).toHaveAttribute("aria-checked", "true");
    await expect(dialog.getByRole("textbox", { name: "الكمية", exact: true })).toHaveValue("1.5");
  });

  test("@p0 clean cancel closes immediately; meaningful changes require discard confirmation", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Discard") });
    let dialog = await openGeneral(page);
    await dialog.getByRole("button", { name: "إلغاء" }).click();
    await expect(dialog).toHaveCount(0);

    dialog = await openGeneral(page);
    await selectFood(page, food.name);
    await dialog.getByRole("button", { name: "إلغاء" }).click();
    const confirmation = dialog.getByRole("alertdialog", { name: "إلغاء إضافة الطعام؟" });
    await expect(confirmation).toContainText("ستفقد التغييرات الحالية.");
    await expect(confirmation.getByRole("button", { name: "متابعة التعديل" })).toBeFocused();
    await confirmation.getByRole("button", { name: "متابعة التعديل" }).click();
    await expect(dialog.getByLabel(`الطعام المحدد: ${food.name}`)).toBeVisible();
    await dialog.getByRole("button", { name: "إلغاء" }).click();
    await dialog.getByRole("button", { name: "إلغاء الإضافة" }).click();
    await expect(dialog).toHaveCount(0);
  });

  test("@p1 responsive, safe-area, reduced-motion, and accessibility basics hold", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    for (const width of [320, 360, 390, 430]) {
      await page.setViewportSize({ width, height: 700 });
      const dialog = await openGeneral(page);
      await expect(dialog.getByRole("heading", { name: "إضافة طعام" })).toBeVisible();
      await expect(dialog.getByRole("button", { name: "إغلاق إضافة الطعام", exact: true })).toBeVisible();
      await expect(dialog.getByRole("button", { name: "اسحب لأسفل لإغلاق إضافة الطعام" })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
      const footer = dialog.locator(".add-sheet-footer");
      expect(await footer.evaluate((element) => getComputedStyle(element).paddingBottom)).not.toBe("0px");
      expect(await dialog.locator(".add-food-search-state").evaluate((element) => getComputedStyle(element).animationName)).toBe("none");
      await dialog.getByRole("button", { name: "إلغاء" }).click();
    }
  });
});
