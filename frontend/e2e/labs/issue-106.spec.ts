import { API_URL, expect, navigateToOwnerLabs, test } from "./helpers";

test.afterEach(async ({ labsApi }) => {
  for (const item of (await labsApi.overview()).items) {
    for (const result of (await labsApi.detail(item.test_key)).results) await labsApi.remove(result.id);
  }
});

async function addNote(page: import("@playwright/test").Page) {
  await navigateToOwnerLabs(page);
  await page.getByRole("button", { name: "إضافة نتائج", exact: true }).click();
  await page.getByLabel("ملاحظة", { exact: true }).fill("  مختبر تجريبي  ");
  await page.getByRole("button", { name: "التالي", exact: true }).click();
  await page.locator('[data-individual-key="hba1c"]').check();
  await page.getByRole("button", { name: "التالي", exact: true }).click();
  await page.locator("#lab-hba1c-value").fill("5.270");
  await page.getByRole("button", { name: "حفظ النتائج", exact: true }).click();
  await expect(page.getByText("تم حفظ النتائج.", { exact: true })).toBeVisible();
}

test("batch note appears in history and real delete undo restores the same facts with a new ID", async ({ labsPage: page, labsApi }) => {
  await addNote(page);
  const before = (await labsApi.detail("hba1c")).results[0];
  expect(before.note).toBe("مختبر تجريبي");
  await page.goto("/labs/hba1c");
  await expect(page.locator(`[data-history-result="${before.id}"]`)).toContainText("مختبر تجريبي");
  await page.getByRole("button", { name: /^حذف نتيجة/ }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "حذف النتيجة", exact: true }).click();
  await expect(page.getByText("تم حذف النتيجة", { exact: true })).toBeVisible();
  expect((await labsApi.detail("hba1c")).results).toHaveLength(0);
  await page.getByRole("button", { name: "تراجع", exact: true }).click();
  await expect(page.getByText("تمت استعادة النتيجة", { exact: true })).toBeVisible();
  const after = (await labsApi.detail("hba1c")).results[0];
  expect(after.id).not.toBe(before.id);
  for (const key of ["test_key", "test_date", "entered_value", "entered_unit", "note"] as const) expect(after[key]).toBe(before[key]);
});

test("undo rejected by a new same-date result reports failure without replacing it", async ({ labsPage: page, labsApi }) => {
  await addNote(page);
  const before = (await labsApi.detail("hba1c")).results[0];
  await page.goto("/labs/hba1c");
  await page.getByRole("button", { name: /^حذف نتيجة/ }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "حذف النتيجة", exact: true }).click();
  await expect(page.getByText("تم حذف النتيجة", { exact: true })).toBeVisible();
  const replacement = await labsApi.create(before.test_date, [{ test_key: "hba1c", entered_value: "6", entered_unit: "%" }]);
  await page.getByRole("button", { name: "تراجع", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("تعذر تأكيد استعادة النتيجة. أعد تحميل التحاليل للتحقق.");
  await expect(page.getByText("تمت استعادة النتيجة", { exact: true })).toHaveCount(0);
  expect((await labsApi.detail("hba1c")).results.map(result => result.id)).toEqual(replacement.result_ids);
});

test("note-only draft guards browser navigation and preserves focus on continuing", async ({ labsPage: page }) => {
  await page.goto("/foods");
  await page.getByRole("navigation", { name: "التنقل الرئيسي" }).getByRole("link", { name: "التحاليل", exact: true }).click();
  await page.getByRole("button", { name: "إضافة نتائج", exact: true }).click();
  await page.getByLabel("ملاحظة", { exact: true }).fill("ملاحظة غير محفوظة");
  await page.goBack();
  const guard = page.getByRole("dialog", { name: "تغييرات غير محفوظة", exact: true });
  await expect(guard).toBeVisible();
  await guard.getByRole("button", { name: "متابعة التعديل", exact: true }).click();
  await expect(page.getByLabel("ملاحظة", { exact: true })).toHaveValue("ملاحظة غير محفوظة");
  await expect(page.getByLabel("ملاحظة", { exact: true })).toBeFocused();
  await page.goBack();
  await guard.getByRole("button", { name: "تجاهل التغييرات والمغادرة", exact: true }).click();
  await expect(page).toHaveURL(/\/foods$/);
});

test("note limit returns to the note field with the backend error", async ({ labsPage: page }) => {
  await navigateToOwnerLabs(page);
  await page.getByRole("button", { name: "إضافة نتائج", exact: true }).click();
  await page.getByLabel("ملاحظة", { exact: true }).fill("ن".repeat(501));
  await page.getByRole("button", { name: "التالي", exact: true }).click();
  await page.locator('[data-individual-key="hba1c"]').check();
  await page.getByRole("button", { name: "التالي", exact: true }).click();
  await page.locator("#lab-hba1c-value").fill("5.2");
  const response = page.waitForResponse(r => r.url() === `${API_URL}/labs/results` && r.request().method() === "POST");
  await page.getByRole("button", { name: "حفظ النتائج", exact: true }).click();
  expect((await response).status()).toBe(422);
  await expect(page.locator("#lab-note-error")).toHaveText("يجب ألا تتجاوز الملاحظة 500 حرف.");
  await expect(page.locator("#lab-batch-note")).toBeFocused();
});

test("undo expires after eight seconds without restoring or leaving focus on a removed button", async ({ labsPage: page, labsApi }) => {
  await addNote(page);
  await page.goto("/labs/hba1c");
  await page.clock.install();
  await page.getByRole("button", { name: /^حذف نتيجة/ }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "حذف النتيجة", exact: true }).click();
  const undo = page.getByRole("button", { name: "تراجع", exact: true });
  await expect(undo).toBeVisible();
  await undo.focus();
  await page.clock.fastForward(8001);
  await expect(undo).toHaveCount(0);
  await expect(page.locator('[role="status"][tabindex="-1"]')).toBeFocused();
  expect((await labsApi.detail("hba1c")).results).toHaveLength(0);
});

test("lost undo response reports uncertainty and refreshes the actual restored result", async ({ labsPage: page, labsApi }) => {
  await addNote(page);
  const before = (await labsApi.detail("hba1c")).results[0];
  await page.goto("/labs/hba1c");
  await page.getByRole("button", { name: /^حذف نتيجة/ }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "حذف النتيجة", exact: true }).click();
  await expect(page.getByText("تم حذف النتيجة", { exact: true })).toBeVisible();
  await page.route(`${API_URL}/labs/results`, async route => {
    const response = await route.fetch();
    expect(response.status()).toBe(201);
    labsApi.registerReceipt(await response.json());
    await route.abort("connectionfailed");
  });
  await page.getByRole("button", { name: "تراجع", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("تعذر تأكيد استعادة النتيجة. أعد تحميل التحاليل للتحقق.");
  await expect(page.getByText("تمت استعادة النتيجة", { exact: true })).toHaveCount(0);
  const restored = (await labsApi.detail("hba1c")).results;
  expect(restored).toHaveLength(1);
  expect(restored[0].id).not.toBe(before.id);
  expect(restored[0].note).toBe(before.note);
  await expect(page.locator(`[data-history-result="${restored[0].id}"]`)).toContainText(before.note!);
});
