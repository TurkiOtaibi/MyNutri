import { expect, navigateToOwnerLabs, offsetIsoDate, test } from "./helpers";

test("@issue151 search stays visible and «التصنيف» / «الترتيب» open from one toggle", async ({ labsPage: page }) => {
  await navigateToOwnerLabs(page);
  const toggle = page.getByRole("button", { name: "التصنيف والترتيب", exact: true });
  await expect(page.getByLabel("البحث في التحاليل", { exact: true })).toBeVisible();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(page.locator("label").filter({ hasText: /^الترتيب/ }).locator("select")).toBeHidden();
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await page.locator("label").filter({ hasText: /^الترتيب/ }).locator("select").selectOption("name_asc");
  await toggle.click();
  await expect(page.locator("label").filter({ hasText: /^الترتيب/ }).locator("select")).toBeHidden();
  // The active-filter count stays visible while the controls are collapsed.
  await expect(toggle).toContainText("1");
  await expect(page).toHaveURL(/\/labs$/);
});

test("@issue151 detail shows a range bar above the governed reference list and a non-negative axis", async ({ labsPage: page, labsApi }) => {
  const today = (await labsApi.overview()).server_today;
  await labsApi.create(offsetIsoDate(today, -400), [{ test_key: "ferritin", entered_value: "5.9", entered_unit: "ng/mL" }]);
  await labsApi.create(offsetIsoDate(today, -2), [{ test_key: "ferritin", entered_value: "12.4", entered_unit: "ng/mL" }]);
  await page.goto("/labs/ferritin");
  const reference = page.getByRole("region", { name: "القيم المرجعية للنظام" });
  const bar = reference.getByTestId("lab-range-bar");
  await expect(bar).toBeVisible();
  await expect(bar).toHaveAttribute("aria-hidden", "true");
  await expect(bar.locator("[data-tone]")).toHaveCount(await reference.locator("[data-reference-zone]").count());
  // The governed list stays the accessible source.
  await expect(reference.locator("[data-reference-zone]").first()).toBeVisible();
  const axis = await page.locator("svg text[text-anchor='end']").allTextContents();
  expect(axis.map(Number).every(value => value >= 0)).toBe(true);
});

test("@issue151 history «⋯» menu closes on Escape and returns focus to its trigger", async ({ labsPage: page, labsApi }) => {
  const today = (await labsApi.overview()).server_today;
  const { result_ids: [id] } = await labsApi.create(offsetIsoDate(today, -3), [{ test_key: "hba1c", entered_value: "5.4", entered_unit: "%" }]);
  await page.goto("/labs/hba1c");
  const row = page.locator(`[data-history-result="${id}"]`);
  const trigger = row.getByRole("button", { name: /^خيارات نتيجة/ });
  await expect(row.getByRole("button", { name: /^(تعديل|حذف) نتيجة/ })).toHaveCount(0);
  await trigger.click();
  await expect(trigger).toHaveAttribute("aria-expanded", "true");
  await expect(row.getByRole("menuitem", { name: /^تعديل نتيجة/ })).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(row.getByRole("menuitem", { name: /^حذف نتيجة/ })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(row.getByRole("menu")).toHaveCount(0);
  await expect(trigger).toBeFocused();
});
