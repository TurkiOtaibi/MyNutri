import { test, expect, diaryDate, uniqueName, validFood } from "../foods/helpers";

test("search-only Add dismissal has no discard confirmation", async ({ page }) => {
  await page.goto("/diary");
  await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
  const dialog = page.getByRole("dialog", { name: "إضافة طعام", exact: true });
  await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill("search-only");
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("alertdialog")).toHaveCount(0);
});

test("uncertain create retry keeps the same UUID and payload", async ({ page, foodsApi }) => {
  const food = await foodsApi.create({ name: uniqueName("Uncertain Diary create") });
  const submitted: unknown[] = [];
  await page.route("**/diary/entries", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    submitted.push(route.request().postDataJSON());
    if (submitted.length === 1) {
      const response = await route.fetch();
      expect(response.ok()).toBe(true);
      return route.abort("failed");
    }
    return route.continue();
  });
  await page.goto("/diary");
  await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
  const dialog = page.getByRole("dialog", { name: "إضافة طعام", exact: true });
  await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(food.name);
  await dialog.getByRole("button", { name: new RegExp(food.name) }).click();
  await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("١٫٥");
  await dialog.getByRole("button", { name: "إضافة إلى الفطور" }).click();
  await expect(dialog.getByRole("button", { name: "إعادة المحاولة", exact: true })).toBeVisible();
  await expect(dialog.getByRole("textbox", { name: "الكمية", exact: true })).toBeDisabled();
  await dialog.getByRole("button", { name: "إعادة المحاولة", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  expect(submitted).toHaveLength(2);
  expect(submitted[1]).toEqual(submitted[0]);
  expect(submitted[0]).toMatchObject({ id: expect.any(String), quantity: 1.5 });
  await expect(page.getByRole("button", { name: new RegExp(`خيارات ${food.name}`) })).toHaveCount(1);
});

test("edit converts captured serving measurements and guards actual edits", async ({ page, foodsApi }) => {
  const food = await foodsApi.create({ name: uniqueName("Captured serving"), default_unit_type: "cup", unit_amount: 40 });
  await foodsApi.createDiary(food.id, diaryDate(), 1);
  const changed = await foodsApi.update(food.id, validFood({ name: food.name, default_unit_type: "cup", unit_amount: 100 }));
  expect(changed.ok()).toBe(true);
  await page.goto("/diary");
  await page.getByRole("button", { name: new RegExp(`خيارات ${food.name}`) }).click();
  await page.getByRole("menuitem", { name: "تعديل", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "تعديل الكمية والقسم" });
  await dialog.getByRole("button", { name: "جم", exact: true }).click();
  const quantity = dialog.getByRole("textbox", { name: "الكمية", exact: true });
  await expect(quantity).toHaveValue("40");
  await quantity.fill("٨٠");
  await expect(dialog.getByLabel("معاينة القيم الغذائية بعد التعديل")).toContainText("80 جم");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("alertdialog")).toBeVisible();
  await page.getByRole("button", { name: "متابعة التعديل", exact: true }).click();
  await expect(quantity).toHaveValue("٨٠");
  await quantity.fill("٤٠");
  await dialog.getByRole("button", { name: "إلغاء", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("alertdialog")).toHaveCount(0);
});
