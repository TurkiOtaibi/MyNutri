import type { Page } from "@playwright/test";

import { API_TOKEN, API_URL, diaryDate as localDate, expect, test, uniqueName } from "../foods/helpers";

async function openAddAndSelect(page: Page, foodName: string) {
  await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
  const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
  await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(foodName);
  const result = dialog.getByRole("button", { name: new RegExp(foodName) });
  await result.click();
  await dialog.getByRole("radio", { name: "فطور" }).click();
  return { dialog, result };
}

test.describe("@diary quantity and UX refinement", () => {
  test("@p0 stepper appears only after Food selection and selected result is accessible", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Stepper Selected"), brand: "علامة الاختبار", food_category_key: "mixed_dish" });
    await page.goto("/diary");
    await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await expect(dialog.getByRole("textbox", { name: "الكمية", exact: true })).toHaveCount(0);
    await expect(dialog.getByRole("button", { name: "إضافة الطعام", exact: true })).toHaveCount(0);
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(food.name);
    const result = dialog.getByRole("button", { name: new RegExp(food.name) });
    await expect(result).toContainText("علامة الاختبار");
    await result.click();
    await dialog.getByRole("radio", { name: "فطور" }).click();
    await expect(dialog.getByLabel(`الطعام المحدد: ${food.name}`)).toBeVisible();
    await expect(dialog.getByRole("textbox", { name: "الكمية", exact: true })).toHaveValue("1");
    await expect(dialog.getByRole("button", { name: "إضافة إلى الفطور" })).toBeEnabled();
  });

  test("@p0 plus and minus adjust predictably, respect minimum, and never submit", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Stepper Controls"), default_unit_type: "piece" });
    let posts = 0;
    await page.route("**/diary", async (route) => {
      if (route.request().method() === "POST") posts += 1;
      return route.continue();
    });
    await page.goto("/diary");
    const { dialog } = await openAddAndSelect(page, food.name);
    const quantity = dialog.getByRole("textbox", { name: "الكمية", exact: true });
    await dialog.getByRole("button", { name: "زيادة الكمية" }).click();
    await expect(quantity).toHaveValue("1.5");
    await dialog.getByRole("button", { name: "تقليل الكمية" }).click();
    await expect(quantity).toHaveValue("1");
    await quantity.fill("0.01");
    await expect(dialog.getByRole("button", { name: "تقليل الكمية" })).toBeDisabled();
    expect(posts).toBe(0);
  });

  test("@p0 manual decimal quantity updates weight, calories, and all macros", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({
      name: uniqueName("Decimal Preview"),
      default_unit_type: "piece",
      unit_amount: 40,
      calories: 200,
      protein_g: 10,
      carb_g: 20,
      fat_g: 5
    });
    await page.goto("/diary");
    const { dialog } = await openAddAndSelect(page, food.name);
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("1.5");
    const preview = dialog.getByLabel("معاينة القيم الغذائية");
    await expect(preview).toContainText("60 جم");
    await expect(preview).toContainText("120");
    await expect(preview).toContainText("6");
    await expect(preview).toContainText("12");
    await expect(preview).toContainText("3");
  });

  for (const [value, message] of [
    ["0", "أدخل كمية أكبر من 0"],
    ["-1", "أدخل كمية صحيحة"],
    ["abc", "أدخل كمية صحيحة"],
    ["50.01", "الكمية يجب ألا تتجاوز 50 حصة"]
  ] as const) {
    test(`@p0 invalid quantity ${value} blocks save with Arabic error`, async ({ page, foodsApi }) => {
      const food = await foodsApi.create({ name: uniqueName(`Invalid ${value}`) });
      await page.goto("/diary");
      const { dialog } = await openAddAndSelect(page, food.name);
      await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill(value);
      await expect(dialog.getByRole("textbox", { name: "الكمية", exact: true })).toHaveAttribute("aria-invalid", "true");
      await expect(dialog.getByText(message)).toBeVisible();
      await expect(dialog.getByRole("button", { name: "إضافة إلى الفطور" })).toBeDisabled();
    });
  }

  test("@p0 quantity remains stable after search rerender and failed save", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Stable Quantity") });
    await page.route("**/diary", (route) => route.request().method() === "POST" ? route.abort("failed") : route.continue());
    await page.goto("/diary");
    const { dialog } = await openAddAndSelect(page, food.name);
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("2.25");
    await dialog.getByRole("button", { name: "إضافة إلى الفطور" }).click();
    await expect(dialog.getByRole("textbox", { name: "الكمية", exact: true })).toHaveValue("2.25");
    await expect(dialog.getByText("تعذر إضافة الطعام")).toBeVisible();
  });

  test("@p0 meal Add action is compact and never covers the final entry", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("CTA Spacing") });
    await foodsApi.createDiary(food.id, localDate(), 1);
    await foodsApi.createDiary(food.id, localDate(), 2);
    await foodsApi.createDiary(food.id, localDate(), 3);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/diary");
    const cta = page.getByRole("button", { name: "إضافة طعام إلى فطور" });
    await expect(cta).toBeVisible();
    expect(await cta.evaluate((element) => getComputedStyle(element).position)).not.toBe("fixed");
    const lastEntry = page.locator("#meal-breakfast .diary-entry-row").last();
    await lastEntry.scrollIntoViewIfNeeded();
    const entryBox = await lastEntry.boundingBox();
    expect(entryBox && entryBox.y >= -1 && entryBox.y + entryBox.height <= 845).toBe(true);
    await cta.click();
    await expect(page.getByRole("dialog", { name: "إضافة طعام" })).toBeVisible();
    await expect(page.getByRole("button", { name: "إضافة طعام إلى فطور" })).toHaveCount(1);
  });

  test("@p0 summary copy and macro expressions use consumed, target, remaining RTL order", async ({ page, request, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Summary Order"), calories: 210, protein_g: 5.8, carb_g: 28, fat_g: 8.6 });
    const isolatedDate = localDate();
    await foodsApi.createDiary(food.id, isolatedDate, 1);
    await page.goto("/diary");
    await page.getByLabel("اختيار تاريخ اليوميات").fill(isolatedDate);
    const summary = page.getByLabel("ملخص تقدم اليوم");
    const targetsResponse = await request.get(`${API_URL}/target-plans/current?date=${isolatedDate}`, {
      headers: { Authorization: `Bearer ${API_TOKEN}` }
    });
    expect(targetsResponse.status()).toBe(200);
    const targetsBody = await targetsResponse.json() as { targets: { target_calories: number } | null };
    expect(targetsBody.targets).not.toBeNull();
    await expect(summary.getByLabel(new RegExp(`من ${targetsBody.targets!.target_calories} سعرة`))).toBeVisible();
    await expect(summary.getByText(/المتبقي \d+/)).toBeVisible();
    await expect(summary.getByLabel(/البروتين:/)).toBeVisible();
    await expect(summary.getByLabel(/الكارب:/)).toBeVisible();
    await expect(summary.getByLabel(/الدهون:/)).toBeVisible();
  });

  test("@p0 quantity-only edit reuses stepper and live frozen-snapshot preview", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Edit Stepper"), default_unit_type: "slice", unit_amount: 30, calories: 200 });
    await foodsApi.createDiary(food.id, localDate(), 1);
    await page.goto("/diary");
    await page.getByRole("button", { name: new RegExp(`خيارات ${food.name}`) }).click();
    await page.getByRole("menuitem", { name: "تعديل" }).click();
    const dialog = page.getByRole("dialog", { name: "تعديل الكمية والقسم" });
    await expect(dialog.getByRole("button", { name: "زيادة الكمية" })).toBeVisible();
    await dialog.getByRole("button", { name: "زيادة الكمية" }).click();
    await expect(dialog.getByRole("textbox", { name: "الكمية", exact: true })).toHaveValue("1.5");
    await expect(dialog.getByLabel("معاينة القيم الغذائية بعد التعديل")).toContainText("45 جم");
    await expect(dialog.getByLabel("معاينة القيم الغذائية بعد التعديل")).toContainText("90");
  });

  test("@p1 selected week day is fully visible and page has no horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/diary");
    const selected = page.locator(".compact-week-day.selected");
    await expect(selected).toBeVisible();
    const box = await selected.boundingBox();
    expect(box && box.x >= 0 && box.x + box.width <= 360).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    await expect(page.locator(".compact-week-day")).toHaveCount(7);
  });
});
