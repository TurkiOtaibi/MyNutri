import { API_URL, diaryDate, expect, test, uniqueName } from "../foods/helpers";
import type { Page } from "@playwright/test";

async function selectFood(page: Page, name: string) {
  await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
  const dialog = page.getByRole("dialog", { name: "إضافة طعام", exact: true });
  await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(name);
  await dialog.getByRole("button", { name: new RegExp(name) }).click();
  return dialog;
}

for (const basis of ["g", "ml"] as const) {
  test(`BR-DRY-019 converts ${basis} and preserves preview and payload`, async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Measured"), unit_basis: basis,
      nutrition_basis: basis === "g" ? "per_100g" : "per_100ml", default_unit_type: "cup", unit_amount: 200, calories: 100 });
    await page.goto("/diary");
    const dialog = await selectFood(page, food.name);
    const mode = dialog.getByRole("group", { name: "طريقة إدخال الكمية" });
    await mode.getByRole("button", { name: basis === "g" ? "جم" : "مل", exact: true }).click();
    const quantity = dialog.getByRole("textbox", { name: "الكمية", exact: true });
    await expect(quantity).toHaveValue("200");
    await quantity.fill("300");
    await expect(dialog.locator(".add-calorie-total strong")).toHaveText("300");
    await mode.getByRole("button").first().click();
    await expect(quantity).toHaveValue("1.5");
    await mode.getByRole("button").last().click();
    await expect(quantity).toHaveValue("300");
    await quantity.fill("10001");
    await expect(dialog.getByText("الكمية يجب ألا تتجاوز 50 كوب", { exact: true })).toBeVisible();
    await quantity.fill("300");
    await dialog.getByRole("button", { name: "إضافة إلى الفطور", exact: true }).click();
    await expect(dialog).toHaveCount(0);
    const saved = (await foodsApi.listDiary(diaryDate())).find((entry) => entry.food.id === food.id)!;
    expect(saved.quantity).toBe(1.5);
    expect(saved.totals.calories).toBe(300);
    await foodsApi.removeDiary(saved.id);
  });
}

test("BR-DRY-028 maps authoritative rejection and preserves the add draft", async ({ page, foodsApi }) => {
  const food = await foodsApi.create({ name: uniqueName("Future limit") });
  await page.goto("/diary");
  await page.getByLabel("اختيار تاريخ اليوميات").fill(diaryDate(8));
  const dialog = await selectFood(page, food.name);
  await dialog.getByRole("button", { name: "إضافة إلى الفطور", exact: true }).click();
  await expect(dialog.getByText("يمكن إضافة الأطعمة حتى 7 أيام قادمة فقط.", { exact: true })).toBeVisible();
  await expect(dialog.getByRole("textbox", { name: "الكمية", exact: true })).toHaveValue("1");
  expect((await foodsApi.listDiary(diaryDate(8))).some((entry) => entry.food.id === food.id)).toBe(false);
});

test("BR-DRY-032 deletes immediately and undo recreates once with a new ID", async ({ page, foodsApi }) => {
  const food = await foodsApi.create({ name: uniqueName("Undo") });
  const original = await foodsApi.createDiary(food.id, diaryDate(), 1.5, "breakfast");
  await page.goto("/diary");
  await page.getByRole("button", { name: new RegExp(`خيارات ${food.name}`) }).click();
  await page.getByRole("menuitem", { name: "حذف", exact: true }).click();
  await page.getByRole("dialog", { name: "حذف الطعام؟" }).getByRole("button", { name: "حذف", exact: true }).click();
  await expect(page.getByText("تم حذف الطعام", { exact: true })).toBeVisible();
  expect((await foodsApi.listDiary(diaryDate())).some((entry) => entry.id === original.id)).toBe(false);
  await page.getByRole("button", { name: "تراجع", exact: true }).click();
  await expect(page.getByText("تمت استعادة الطعام", { exact: true })).toBeVisible();
  const restored = (await foodsApi.listDiary(diaryDate())).filter((entry) => entry.food.id === food.id);
  expect(restored).toHaveLength(1);
  expect(restored[0]).toMatchObject({ entry_date: diaryDate(), meal_type: "breakfast", quantity: 1.5 });
  expect(restored[0].id).not.toBe(original.id);
  await foodsApi.removeDiary(restored[0].id);
});

test("BR-DRY-032 reports failed undo and expires its online-only action", async ({ page, foodsApi }) => {
  const food = await foodsApi.create({ name: uniqueName("Undo failure") });
  await foodsApi.createDiary(food.id, diaryDate(), 1, "breakfast");
  await page.goto("/diary");
  const remove = async () => {
    await page.getByRole("button", { name: new RegExp(`خيارات ${food.name}`) }).click();
    await page.getByRole("menuitem", { name: "حذف", exact: true }).click();
    await page.getByRole("dialog", { name: "حذف الطعام؟" }).getByRole("button", { name: "حذف", exact: true }).click();
    await expect(page.getByRole("button", { name: "تراجع", exact: true })).toBeVisible();
  };
  await remove();
  await page.route(`${API_URL}/diary/entries`, (route) => route.request().method() === "POST"
    ? route.fulfill({ status: 500, json: { detail: "synthetic undo failure" } }) : route.continue());
  await page.getByRole("button", { name: "تراجع", exact: true }).click();
  await expect(page.getByText("تعذر تأكيد استعادة الطعام. حدّث اليوم للتحقق.", { exact: true })).toBeVisible();
  expect((await foodsApi.listDiary(diaryDate())).some((entry) => entry.food.id === food.id)).toBe(false);
  await foodsApi.createDiary(food.id, diaryDate(), 1, "breakfast");
  await page.reload();
  await page.clock.install();
  await remove();
  await page.clock.fastForward(8001);
  await expect(page.getByRole("button", { name: "تراجع", exact: true })).toHaveCount(0);
});

test("BR-NAV-012 guards browser navigation while preserving local cancel and focus", async ({ page, foodsApi }) => {
  const food = await foodsApi.create({ name: uniqueName("Unsaved Diary") });
  await page.goto("/foods");
  await page.getByRole("link", { name: "اليوميات", exact: true }).click();
  const dialog = await selectFood(page, food.name);
  await page.goBack();
  const guard = page.getByRole("dialog", { name: "تغييرات غير محفوظة", exact: true });
  await expect(guard).toBeVisible();
  await expect(guard.getByRole("button", { name: "متابعة التعديل" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(guard).toHaveCount(0);
  await expect(dialog.getByText("إلغاء إضافة الطعام؟", { exact: true })).toHaveCount(0);
  await dialog.getByRole("button", { name: "إلغاء", exact: true }).click();
  const discard = page.getByRole("alertdialog", { name: "إلغاء إضافة الطعام؟" });
  await expect(discard).toBeVisible();
  await discard.getByRole("button", { name: "متابعة التعديل" }).click();
  await page.goBack();
  await guard.getByRole("button", { name: "تجاهل التغييرات والمغادرة" }).click();
  await expect(page).toHaveURL(/\/foods$/);
});

test("BR-DRY-032 an older undo completion cannot overwrite a newer deletion notice", async ({ page, foodsApi }) => {
  const first = await foodsApi.create({ name: uniqueName("Undo first") });
  const second = await foodsApi.create({ name: uniqueName("Undo second") });
  await foodsApi.createDiary(first.id, diaryDate(), 1, "breakfast");
  await foodsApi.createDiary(second.id, diaryDate(), 1, "breakfast");
  await page.goto("/diary");
  const remove = async (name: string) => {
    await page.getByRole("button", { name: new RegExp(`خيارات ${name}`) }).click();
    await page.getByRole("menuitem", { name: "حذف", exact: true }).click();
    await page.getByRole("dialog", { name: "حذف الطعام؟" }).getByRole("button", { name: "حذف", exact: true }).click();
    await expect(page.getByRole("button", { name: "تراجع", exact: true })).toBeVisible();
  };
  let release = () => {};
  let captured = () => {};
  const held = new Promise<void>((resolve) => { release = resolve; });
  const received = new Promise<void>((resolve) => { captured = resolve; });
  await page.route(`${API_URL}/diary/entries`, async (route) => {
    if (route.request().method() !== "POST" || route.request().postDataJSON().food_id !== first.id) return route.continue();
    const response = await route.fetch();
    captured();
    await held;
    await route.fulfill({ response });
  });
  try {
    await remove(first.name);
    await page.getByRole("button", { name: "تراجع", exact: true }).click();
    await received;
    await remove(second.name);
    await expect(page.getByRole("button", { name: "تراجع", exact: true })).toBeEnabled();
    await page.getByRole("button", { name: "تراجع", exact: true }).click();
    await expect(page.getByText("تمت استعادة الطعام", { exact: true })).toBeVisible();
    const reconciled = page.waitForResponse((response) => response.request().method() === "GET" && response.url().includes("/diary/entries?entry_date="));
    release();
    await reconciled;
    await expect(page.getByText("تمت استعادة الطعام", { exact: true })).toBeVisible();
    const entries = await foodsApi.listDiary(diaryDate());
    expect(entries.filter((entry) => [first.id, second.id].includes(entry.food.id))).toHaveLength(2);
  } finally {
    release();
  }
});
