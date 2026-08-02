import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import type { Locator, Page } from "@playwright/test";

import { diaryDate as localDate, expect, test, uniqueName } from "../foods/helpers";

const output = resolve("..", "docs", "ui-ux", "screenshots", "diary-meal-sections");

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

test.describe("@diary @visual final meal sections", () => {
  test("capture required mobile and desktop states", async ({ page, foodsApi }) => {
    await mkdir(output, { recursive: true });
    const emptyDate = localDate(-150);
    const breakfast = await foodsApi.create({ name: uniqueName("بيض مسلوق Breakfast"), default_unit_type: "piece", unit_amount: 50, calories: 156, protein_g: 12.6, carb_g: 1.2, fat_g: 10.6 });
    const lunch = await foodsApi.create({ name: uniqueName("غداء عربي Mixed Lunch"), default_unit_type: "serving", unit_amount: 150, calories: 180 });
    const dinner = await foodsApi.create({ name: uniqueName("Dinner طويل بالعربية English"), default_unit_type: "serving", unit_amount: 120, calories: 210 });
    const snack = await foodsApi.create({ name: uniqueName("سناك"), default_unit_type: "piece", unit_amount: 20, calories: 300 });
    await foodsApi.createDiary(breakfast.id, localDate(), 1, "breakfast");
    await foodsApi.createDiary(lunch.id, localDate(), 1, "lunch");
    await foodsApi.createDiary(dinner.id, localDate(), 1, "dinner");
    await foodsApi.createDiary(snack.id, localDate(), 1, "snack");
    await foodsApi.createDiary(snack.id, localDate(), 0.5, "unspecified");

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/diary");
    await page.waitForFunction(() => {
      const input = document.querySelector('input[aria-label="اختيار تاريخ اليوميات"]');
      return input != null && Object.keys(input).some((key) => key.startsWith("__reactProps$"));
    });
    await page.getByLabel("اختيار تاريخ اليوميات").fill(emptyDate);
    await expect(page.locator(".meal-section")).toHaveCount(4);
    await page.screenshot({ path: resolve(output, "diary-mobile-empty-390.png"), fullPage: true });

    await page.getByLabel("اختيار تاريخ اليوميات").fill(localDate());
    await expect(page.getByRole("button", { name: /قسم فطور$/ })).toContainText(/طعام واحد|طعامان|\d+ أطعمة|\d+ طعامًا/);
    await page.screenshot({ path: resolve(output, "diary-mobile-populated-390.png"), fullPage: true });
    await page.screenshot({ path: resolve(output, "diary-mobile-breakfast-expanded-390.png") });

    for (const meal of ["غداء", "عشاء", "سناك"]) {
      const toggle = page.getByRole("button", { name: new RegExp(`قسم ${meal}$`) });
      if ((await toggle.getAttribute("aria-expanded")) !== "true") await toggle.click();
    }
    await page.screenshot({ path: resolve(output, "diary-mobile-multiple-expanded-390.png"), fullPage: true });

    const breakfastAdd = page.getByRole("button", { name: "إضافة طعام إلى فطور" });
    await breakfastAdd.click();
    await page.screenshot({ path: resolve(output, "diary-mobile-add-breakfast-390.png") });
    await page.keyboard.press("Escape");

    await breakfastAdd.click();
    let dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await page.screenshot({ path: resolve(output, "diary-mobile-global-add-390.png") });
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(breakfast.name);
    await dialog.getByRole("button", { name: new RegExp(breakfast.name) }).click();
    await dialog.getByRole("radio", { name: "فطور" }).click();
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("2");
    await page.screenshot({ path: resolve(output, "diary-mobile-quantity-stepper-390.png") });
    await dialog.getByRole("button", { name: "إضافة إلى الفطور" }).click();
    await expect(page.locator("#meal-breakfast").getByRole("heading", { name: breakfast.name })).toBeVisible();
    await page.screenshot({ path: resolve(output, "diary-mobile-success-toast-390.png") });

    await page.getByRole("button", { name: /قسم غير مصنف$/ }).click();
    await page.screenshot({ path: resolve(output, "diary-mobile-legacy-unspecified-390.png"), fullPage: true });
    await page.getByRole("heading", { name: new RegExp("Dinner طويل") }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: resolve(output, "diary-mobile-long-mixed-name-390.png") });

    await page.getByRole("button", { name: new RegExp(`خيارات ${breakfast.name}`) }).first().click();
    await page.getByRole("menuitem", { name: "تعديل" }).click();
    await page.screenshot({ path: resolve(output, "diary-mobile-edit-entry-390.png") });
    await page.keyboard.press("Escape");

    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByLabel("اختيار تاريخ اليوميات").fill(emptyDate);
    await page.screenshot({ path: resolve(output, "diary-desktop-empty-1440.png"), fullPage: true });
    await page.getByLabel("اختيار تاريخ اليوميات").fill(localDate());
    await page.screenshot({ path: resolve(output, "diary-desktop-populated-1440.png"), fullPage: true });
    await page.screenshot({ path: resolve(output, "diary-desktop-two-column-1440.png") });

    await breakfastAdd.click();
    dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(lunch.name);
    await dialog.getByRole("button", { name: new RegExp(lunch.name) }).click();
    await dialog.getByRole("radio", { name: "غداء" }).click();
    await page.screenshot({ path: resolve(output, "diary-desktop-add-dialog-1440.png") });
    await page.keyboard.press("Escape");
    await discardPortaledAddFoodDraft(page, breakfastAdd);

    await page.getByRole("button", { name: new RegExp(`خيارات ${breakfast.name}`) }).first().click();
    await page.getByRole("menuitem", { name: "تعديل" }).click();
    await page.screenshot({ path: resolve(output, "diary-desktop-edit-dialog-1440.png") });
    await page.keyboard.press("Escape");
    await page.screenshot({ path: resolve(output, "diary-desktop-expanded-meals-1440.png"), fullPage: true });
  });
});
