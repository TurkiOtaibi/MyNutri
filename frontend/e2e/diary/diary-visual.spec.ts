import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test, uniqueName } from "../foods/helpers";

const output = resolve("..", "docs", "ui-ux", "screenshots", "diary-quantity-refinement");

function localDate(days = 0): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

test.describe("@diary @visual Diary redesign screenshots", () => {
  test("capture mobile and desktop Diary states with temporary local fixtures", async ({ page, foodsApi }) => {
    await mkdir(output, { recursive: true });
    const emptyDate = localDate(-120);

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/diary");
    await page.getByLabel("اختيار تاريخ اليوميات").fill(emptyDate);
    await expect(page.getByText("لا توجد أطعمة مسجلة اليوم")).toBeVisible();
    await page.screenshot({ path: resolve(output, "diary-mobile-empty-390.png") });

    const standard = await foodsApi.create({
      name: uniqueName("Visual Diary"),
      default_unit_type: "piece",
      unit_amount: 30,
      calories: 240,
      protein_g: 12,
      carb_g: 30,
      fat_g: 8
    });
    const longName = await foodsApi.create({
      name: `بسكويت الشوفان بالشوكولاتة الداكنة بدون سكر - Long Mixed English Name ${uniqueName("Visual RTL")}`,
      default_unit_type: "piece",
      unit_amount: 14,
      calories: 493,
      protein_g: 7.9,
      carb_g: 68,
      fat_g: 22
    });
    await foodsApi.createDiary(standard.id, localDate(), 1);
    await foodsApi.createDiary(longName.id, localDate(), 2);

    await page.goto("/diary");
    await expect(page.getByRole("heading", { name: longName.name })).toBeVisible();
    await page.screenshot({ path: resolve(output, "diary-mobile-populated-390.png") });
    await page.getByRole("heading", { name: longName.name }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: resolve(output, "diary-mobile-long-name-390.png") });

    await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
    await expect(page.getByRole("dialog", { name: "إضافة طعام" })).toBeVisible();
    await page.screenshot({ path: resolve(output, "diary-mobile-add-search-390.png") });
    let dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(standard.name);
    await dialog.getByRole("button", { name: new RegExp(standard.name) }).click();
    await page.screenshot({ path: resolve(output, "diary-mobile-food-selected-390.png") });
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("2");
    await page.screenshot({ path: resolve(output, "diary-mobile-quantity-2-390.png") });
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("1.5");
    await page.screenshot({ path: resolve(output, "diary-mobile-quantity-1.5-390.png") });
    await page.keyboard.press("Escape");
    await dialog.getByRole("button", { name: "إلغاء الإضافة" }).click();

    await page.getByRole("button", { name: new RegExp(`خيارات ${standard.name}`) }).click();
    await page.getByRole("menuitem", { name: "تعديل" }).click();
    await expect(page.getByRole("dialog", { name: "تعديل الكمية والقسم" })).toBeVisible();
    await page.screenshot({ path: resolve(output, "diary-mobile-edit-quantity-390.png") });
    await page.keyboard.press("Escape");

    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByLabel("اختيار تاريخ اليوميات").fill(emptyDate);
    await expect(page.getByText("لا توجد أطعمة مسجلة اليوم")).toBeVisible();
    await page.screenshot({ path: resolve(output, "diary-desktop-empty-1440.png") });

    await page.getByLabel("اختيار تاريخ اليوميات").fill(localDate());
    await expect(page.getByRole("heading", { name: longName.name })).toBeVisible();
    await page.screenshot({ path: resolve(output, "diary-desktop-populated-1440.png") });

    await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
    dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await expect(dialog).toBeVisible();
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(standard.name);
    await dialog.getByRole("button", { name: new RegExp(standard.name) }).click();
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("2");
    await page.screenshot({ path: resolve(output, "diary-desktop-add-stepper-1440.png") });
    await page.keyboard.press("Escape");
    await dialog.getByRole("button", { name: "إلغاء الإضافة" }).click();

    await page.getByRole("button", { name: new RegExp(`خيارات ${standard.name}`) }).click();
    await page.getByRole("menuitem", { name: "تعديل" }).click();
    await expect(page.getByRole("dialog", { name: "تعديل الكمية والقسم" })).toBeVisible();
    await page.screenshot({ path: resolve(output, "diary-desktop-edit-quantity-1440.png") });
  });
});
