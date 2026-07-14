import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test, uniqueName } from "../foods/helpers";

const output = resolve("..", "docs", "ui-ux", "screenshots", "diary-add-food-sheet");

function localDate(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

test("@diary @visual capture production-style Add Food sheet states", async ({ page, foodsApi }) => {
  await mkdir(output, { recursive: true });
  await page.emulateMedia({ reducedMotion: "reduce" });
  const food = await foodsApi.create({ name: uniqueName("بسكويت الشوفان الداكن Modern"), brand: "Gullón Oaty", default_unit_type: "piece", unit_amount: 14, calories: 492.86, protein_g: 7.86, carb_g: 68.11, fat_g: 22.14 });
  await foodsApi.createDiary(food.id, localDate(), 1, "snack");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/diary");
  await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
  let dialog = page.getByRole("dialog", { name: "إضافة طعام" });
  await expect(dialog.getByText("المستخدمة مؤخرًا", { exact: true })).toBeVisible();
  await page.screenshot({ path: resolve(output, "01-search-recent-390.png") });

  let search = dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية");
  await page.setViewportSize({ width: 390, height: 560 });
  await search.fill("Gullón");
  await expect(dialog.getByRole("button", { name: new RegExp(food.name) })).toBeVisible();
  await page.screenshot({ path: resolve(output, "02-active-search-keyboard-390.png") });

  await search.fill(`not-found-${Date.now()}`);
  await expect(dialog.getByText("لم نجد طعامًا مطابقًا")).toBeVisible();
  await page.screenshot({ path: resolve(output, "03-no-results-390.png") });

  await dialog.getByRole("button", { name: "إلغاء" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/diary");
  await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
  dialog = page.getByRole("dialog", { name: "إضافة طعام" });
  search = dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية");
  await search.fill(food.name);
  await dialog.getByRole("button", { name: new RegExp(food.name) }).click();
  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  await page.waitForTimeout(220);
  await expect(dialog.getByRole("radio", { name: "فطور" })).toHaveAttribute("aria-checked", "true");
  await page.screenshot({ path: resolve(output, "04-selected-no-meal-390.png") });

  await dialog.getByRole("radio", { name: "فطور" }).click();
  await page.screenshot({ path: resolve(output, "05-breakfast-selected-390.png") });
  await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("2.5");
  await page.screenshot({ path: resolve(output, "06-decimal-quantity-2.5-390.png") });

  await page.route("**/diary", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 900));
    return route.abort("failed");
  });
  await dialog.getByRole("button", { name: "إضافة إلى الفطور" }).click();
  await expect(dialog.getByRole("button", { name: "جارٍ الإضافة…" })).toBeVisible();
  await page.screenshot({ path: resolve(output, "07-saving-state-390.png") });
  await expect(dialog.getByText("تعذر إضافة الطعام")).toBeVisible();
  await page.screenshot({ path: resolve(output, "08-save-error-390.png") });

  await dialog.getByRole("button", { name: "إلغاء" }).click();
  await expect(dialog.getByRole("alertdialog", { name: "إلغاء إضافة الطعام؟" })).toBeVisible();
  await page.screenshot({ path: resolve(output, "09-unsaved-confirmation-390.png") });
  await dialog.getByRole("button", { name: "إلغاء الإضافة" }).click();

  for (const [index, width] of [[10, 320], [11, 390], [12, 430]] as const) {
    await page.setViewportSize({ width, height: 760 });
    await page.goto("/diary");
    await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
    dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await expect(dialog).toBeVisible();
    await page.screenshot({ path: resolve(output, `${index}-viewport-${width}.png`) });
    await dialog.getByRole("button", { name: "إلغاء" }).click();
  }
});
