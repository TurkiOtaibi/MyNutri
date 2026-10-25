import { API_URL, diaryDate, test, expect, uniqueName, fillRequiredFoodForm, submitFoodForm } from "./helpers";

for (const role of ["admin", "user"] as const) {
  test(`BR-FOD-013 ${role} opens the shared add flow with food and server today`, async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Details add") });
    if (role === "user") await page.route(`${API_URL}/account/me`, async (route) => {
      const response = await route.fetch();
      await route.fulfill({ response, json: { ...await response.json(), role: "user" } });
    });
    await page.goto(`/foods/${food.id}`);
    await expect(page.getByRole("link", { name: "تعديل", exact: true })).toHaveCount(role === "admin" ? 1 : 0);
    await page.getByRole("button", { name: "إضافة إلى اليوميات", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة طعام", exact: true });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(food.name, { exact: true })).toBeVisible();
    await expect(dialog.locator('[role="radio"][aria-checked="true"]')).toHaveCount(0);
    await dialog.getByRole("radio", { name: "غداء", exact: true }).click();
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("2");
    await dialog.getByRole("button", { name: "إضافة إلى الغداء", exact: true }).click();
    await expect(dialog).toHaveCount(0);
    await expect(page.getByRole("button", { name: "إضافة إلى اليوميات", exact: true })).toBeFocused();
    const entries = (await foodsApi.listDiary(diaryDate())).filter((entry) => entry.food.id === food.id);
    expect(entries).toHaveLength(1);
    expect(entries[0]).toMatchObject({ entry_date: diaryDate(), meal_type: "lunch", quantity: 2 });
  });
}

test("BR-FOD-029 warns on normalized names, permits different brand, excludes self on edit", async ({ page, foodsApi }) => {
  const food = await foodsApi.create({ name: uniqueName("Same Food"), brand: "Brand A" });
  await page.goto(`/foods/${food.id}/edit`);
  await expect(page.getByRole("button", { name: "حفظ التعديل" })).toBeEnabled();
  await expect(page.getByText("يوجد طعام بالاسم نفسه.", { exact: true })).toHaveCount(0);
  await page.goto("/foods/new");
  await fillRequiredFoodForm(page, { ...food, name: ` ${food.name.toUpperCase().replaceAll(" ", "   ")} `, brand: "Brand B" });
  await expect(page.getByText("يوجد طعام بالاسم نفسه.", { exact: true })).toBeVisible();
  await submitFoodForm(page);
  await expect(page).toHaveURL(/\/foods\/[0-9a-f-]+$/);
  await foodsApi.remove(page.url().split("/").at(-1)!);
});

test("BR-FOD-030 and BR-FOD-035 show aggregate impact before edit and delete", async ({ page, foodsApi }) => {
  const food = await foodsApi.create({ name: uniqueName("Impact") });
  await foodsApi.createDiary(food.id, diaryDate());
  await foodsApi.createDiary(food.id, diaryDate(-1));
  await page.goto(`/foods/${food.id}/edit`);
  await expect(page.getByText("هذا الطعام مسجّل في 2 يوميات، والتعديل سيغيّر مجاميعها السابقة.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "حذف", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "حذف الطعام؟" });
  await expect(dialog).toContainText("عدد سجلات اليوميات: 2 · عدد المستخدمين المتأثرين: 1");
  await expect(dialog).toContainText("سيتم حذف هذا الطعام نهائيًا، كما سيتم حذف جميع سجلات اليوميات المرتبطة به لجميع المستخدمين. لا يمكن التراجع عن هذا الإجراء.");
  await expect(dialog.getByRole("button", { name: "إلغاء", exact: true })).toBeFocused();
});

test("BR-FOD-029 a newly created Food invalidates its earlier empty name warning", async ({ page, foodsApi }) => {
  const name = uniqueName("Fresh name");
  await page.goto("/foods/new");
  await fillRequiredFoodForm(page, { name });
  await expect(page.getByRole("button", { name: "حفظ الطعام" })).toBeEnabled();
  await expect(page.getByText("يوجد طعام بالاسم نفسه.", { exact: true })).toHaveCount(0);
  await submitFoodForm(page);
  await expect(page).toHaveURL(/\/foods\/[0-9a-f-]+$/);
  const id = page.url().split("/").at(-1)!;
  try {
    await page.getByRole("link", { name: "رجوع إلى الأطعمة", exact: true }).click();
    await page.getByRole("link", { name: "إضافة طعام", exact: true }).click();
    await fillRequiredFoodForm(page, { name, brand: "Another brand" });
    await expect(page.getByText("يوجد طعام بالاسم نفسه.", { exact: true })).toBeVisible();
  } finally {
    await foodsApi.remove(id);
  }
});

test("BR-FOD-030 and BR-FOD-035 count failures stay visible and allow existing actions", async ({ page, foodsApi }) => {
  const food = await foodsApi.create({ name: uniqueName("Impact failure") });
  await page.route(`${API_URL}/foods/${food.id}/usage`, (route) => route.fulfill({ status: 500, json: { detail: "Synthetic failure" } }));
  await page.goto(`/foods/${food.id}/edit`);
  await expect(page.getByText("تعذر تحميل أعداد السجلات المتأثرة. يمكنك المتابعة دون الأعداد.")).toBeVisible();
  await submitFoodForm(page, "edit");
  await expect(page).toHaveURL(new RegExp(`/foods/${food.id}$`));
  await page.getByRole("button", { name: "حذف", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "حذف الطعام؟" });
  await expect(dialog.getByText("تعذر تحميل أعداد السجلات المتأثرة. يمكنك المتابعة دون الأعداد.")).toBeVisible();
  await dialog.getByRole("button", { name: "حذف نهائي", exact: true }).click();
  await expect(page).toHaveURL(/\/foods$/);
});

test("BR-FOD-013 calendar failure does not use the browser date", async ({ page, foodsApi }) => {
  const food = await foodsApi.create({ name: uniqueName("Date failure") });
  await page.route(`${API_URL}/account/calendar`, (route) => route.fulfill({ status: 500, json: { detail: "Synthetic failure" } }));
  await page.goto(`/foods/${food.id}`);
  await page.getByRole("button", { name: "إضافة إلى اليوميات", exact: true }).click();
  await expect(page.getByText("تعذر تحميل تاريخ اليوم. حاول مرة أخرى.", { exact: true })).toBeVisible();
  await expect(page.getByRole("dialog", { name: "إضافة طعام", exact: true })).toHaveCount(0);
});
