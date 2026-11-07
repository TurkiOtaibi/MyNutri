import { expect, navigateToOwnerLabs, offsetIsoDate, test } from "./helpers";

test("batch search, panel state and dirty dismissal retain exact input", async ({ labsPage: page }) => {
  await navigateToOwnerLabs(page);
  await page.getByRole("button", { name: "إضافة نتائج", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "إضافة نتائج", exact: true });
  await dialog.getByLabel("ملاحظة", { exact: true }).fill("ملاحظة غير محفوظة");
  await dialog.getByRole("button", { name: "التالي", exact: true }).click();
  await dialog.locator('[data-panel-key="iron_studies"]').check();
  const ferritin = dialog.locator('[data-individual-key="ferritin"]');
  await expect(ferritin).toBeChecked();
  await expect(ferritin).toBeDisabled();
  await dialog.getByRole("searchbox").fill("HbA1c");
  await dialog.locator('[data-individual-key="hba1c"]').check();
  await expect(dialog.getByTestId("lab-selection-summary")).toContainText("التحاليل المحددة");
  await dialog.getByRole("button", { name: "التالي", exact: true }).click();
  await dialog.locator("#lab-hba1c-value").fill("٥٫٢٧٠٠");
  await dialog.getByRole("button", { name: "السابق", exact: true }).click();
  await dialog.getByRole("button", { name: "التالي", exact: true }).click();
  await expect(dialog.locator("#lab-hba1c-value")).toHaveValue("٥٫٢٧٠٠");
  await page.keyboard.press("Escape");
  const discard = page.getByRole("alertdialog", { name: "تجاهل التغييرات؟" });
  await expect(discard).toBeVisible();
  await discard.getByRole("button", { name: "متابعة التعديل" }).click();
  await expect(dialog.locator("#lab-hba1c-value")).toHaveValue("٥٫٢٧٠٠");
  await dialog.getByRole("button", { name: "إلغاء", exact: true }).click();
  await discard.getByRole("button", { name: "تجاهل التغييرات", exact: true }).click();
  await expect(dialog).toBeHidden();
});


test("chart scale is explicit and changing it preserves selected exact reading and history", async ({ labsPage: page, labsApi }) => {
  const today = (await labsApi.overview()).server_today;
  const ids: string[] = [];
  try {
    for (const [offset, value] of [[-1, "5.2700"], [0, "5.2800"]] as const) {
      const receipt = await labsApi.create(offsetIsoDate(today, offset), [{ test_key: "hba1c", entered_value: value, entered_unit: "%" }]);
      ids.push(...receipt.result_ids);
    }
    await page.goto("/labs/hba1c");
    const reading = page.getByTestId("selected-lab-reading");
    const before = await reading.innerText();
    const scale = page.getByRole("combobox", { name: "مقياس الرسم", exact: true });
    await expect(scale).toHaveValue("references");
    await scale.selectOption("results");
    await expect(page.getByRole("status").filter({ hasText: "المحور مكبّر" })).toBeVisible();
    await expect(reading).toHaveText(before, { useInnerText: true });
    await expect(page.locator("[data-history-result]")).toHaveCount(2);
    const ticks = await page.locator("svg text[text-anchor='end']").allTextContents();
    expect(ticks.map(Number).every(Number.isFinite)).toBe(true);
    await scale.selectOption("references");
    await expect(reading).toHaveText(before, { useInnerText: true });
  } finally {
    for (const id of ids) await labsApi.remove(id);
  }
});
