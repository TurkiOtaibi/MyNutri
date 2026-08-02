import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import type { Locator, Page } from "@playwright/test";

import { diaryDate as localDate, expect, test, uniqueName } from "../foods/helpers";

const output = resolve("..", "docs", "ui-ux", "screenshots", "diary-quantity-refinement");

async function discardPortaledAddFoodDraft(page: Page, opener: Locator) {
  const discardDialog = page.getByRole("alertdialog", {
    name: "إلغاء إضافة الطعام؟",
    exact: true
  });
  const parentPanel = page.locator(".entry-sheet .diary-modal-panel");

  await expect(discardDialog).toHaveCount(1);
  await expect(discardDialog).toBeVisible();
  await expect(discardDialog.getByRole("button", { name: "متابعة التعديل", exact: true })).toBeFocused();
  await expect(parentPanel).toHaveCount(1);
  await expect(parentPanel).toBeVisible();
  await expect(parentPanel).toHaveAttribute("inert", "");
  await expect(parentPanel).toHaveAttribute("aria-hidden", "true");
  expect(await discardDialog.evaluate((element) => element.contains(document.activeElement))).toBe(true);
  expect(await parentPanel.evaluate((element) => element.contains(document.activeElement))).toBe(false);
  await expect(opener).not.toBeFocused();
  await expect(page.locator("body")).toHaveClass(/modal-open/);

  await discardDialog.getByRole("button", { name: "إلغاء الإضافة", exact: true }).click();

  await expect(discardDialog).toHaveCount(0);
  await expect(parentPanel).toHaveCount(0);
  await expect(opener).toBeFocused();
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

    const breakfastAdd = page.getByRole("button", { name: "إضافة طعام إلى فطور" });
    await breakfastAdd.click();
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
    await discardPortaledAddFoodDraft(page, breakfastAdd);

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

    await breakfastAdd.click();
    dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await expect(dialog).toBeVisible();
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(standard.name);
    await dialog.getByRole("button", { name: new RegExp(standard.name) }).click();
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("2");
    await page.screenshot({ path: resolve(output, "diary-desktop-add-stepper-1440.png") });
    await page.keyboard.press("Escape");
    await discardPortaledAddFoodDraft(page, breakfastAdd);

    await page.getByRole("button", { name: new RegExp(`خيارات ${standard.name}`) }).click();
    await page.getByRole("menuitem", { name: "تعديل" }).click();
    await expect(page.getByRole("dialog", { name: "تعديل الكمية والقسم" })).toBeVisible();
    await page.screenshot({ path: resolve(output, "diary-desktop-edit-quantity-1440.png") });
  });
});
