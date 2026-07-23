import { API_TOKEN, API_URL, diaryDate as localDate, expect, test, uniqueName } from "../foods/helpers";

test.describe("@diary @meals Gregorian meal sections", () => {
  test("@p0 Gregorian date hydrates without server/client mismatch", async ({ page }) => {
    const hydrationErrors: string[] = [];
    page.on("console", (message) => {
      if (/hydration|server rendered text didn't match/i.test(message.text())) hydrationErrors.push(message.text());
    });
    page.on("pageerror", (error) => {
      if (/hydration|server rendered text didn't match/i.test(error.message)) hydrationErrors.push(error.message);
    });
    await page.goto("/diary");
    await expect(page.locator(".compact-selected-date h2")).not.toContainText(/\d{4}/);
    await page.waitForTimeout(500);
    expect(hydrationErrors).toEqual([]);
  });

  test("@p0 renders Gregorian date with Western numerals and seven accessible days", async ({ page }) => {
    await page.goto("/diary");
    const nav = page.getByLabel(/التنقل بين أيام اليوميات/);
    await expect(nav).toBeVisible();
    await expect(nav.locator(".compact-week-day")).toHaveCount(7);
    await expect(nav.locator('[role="tab"][aria-selected="true"]')).toHaveCount(1);
    const text = await nav.innerText();
    expect(text).not.toMatch(/[٠-٩]/);
    expect(text).not.toMatch(/محرم|صفر|ربيع|جمادى|رجب|شعبان|رمضان|شوال|القعدة|الحجة/);
  });

  test("@p0 renders four compact meal sections and legacy only when needed", async ({ page }) => {
    await page.goto("/diary");
    const emptyDate = localDate(-120);
    await page.getByLabel("اختيار تاريخ اليوميات").fill(emptyDate);
    for (const meal of ["فطور", "غداء", "عشاء", "سناك"]) {
      await expect(page.getByRole("button", { name: new RegExp(`قسم ${meal}$`) })).toBeVisible();
    }
    await expect(page.getByRole("button", { name: /قسم غير مصنف$/ })).toHaveCount(0);
    await expect(page.locator(".meal-section")).toHaveCount(4);
  });

  test("@p0 section Add preselects meal and saves into that expanded section", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Lunch meal") });
    await page.goto("/diary");
    await page.getByRole("button", { name: "إضافة طعام إلى غداء" }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(food.name);
    await dialog.getByRole("button", { name: new RegExp(food.name) }).click();
    await expect(dialog.getByRole("radio", { name: "غداء" })).toHaveAttribute("aria-checked", "true");
    await dialog.getByRole("button", { name: "إضافة إلى الغداء" }).click();
    const lunch = page.locator("#meal-section-lunch");
    await expect(lunch.getByRole("heading", { name: food.name })).toBeVisible();
  });

  test("@p0 Diary exposes only meal-specific Add actions", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Required meal") });
    await page.goto("/diary");
    await expect(page.getByRole("button", { name: "إضافة طعام", exact: true })).toHaveCount(0);
    await page.getByRole("button", { name: "إضافة طعام إلى سناك" }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(food.name);
    await dialog.getByRole("button", { name: new RegExp(food.name) }).click();
    await expect(dialog.getByRole("radio", { name: "سناك" })).toHaveAttribute("aria-checked", "true");
    await expect(dialog.getByRole("button", { name: "إضافة إلى السناك" })).toBeEnabled();
  });

  test("@p0 API accepts standard meals, defaults omitted values, and rejects tampering", async ({ request, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Meal API") });
    const base = { food_id: food.id, entry_date: localDate(), quantity: 1 };
    const headers = { Authorization: `Bearer ${API_TOKEN}` };
    const omitted = await request.post(`${API_URL}/diary`, { headers, data: base });
    expect(omitted.status()).toBe(201);
    expect((await omitted.json()).meal_type).toBe("unspecified");
    const invalid = await request.post(`${API_URL}/diary`, { headers, data: { ...base, meal_type: "brunch" } });
    expect(invalid.status()).toBe(422);
    await request.delete(`${API_URL}/diary/${(await omitted.json()).id}`, { headers });
  });

  test("@p0 edit moves entry between meals without exposing immutable fields", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Move meal") });
    await foodsApi.createDiary(food.id, localDate(), 1, "breakfast");
    await page.goto("/diary");
    await page.getByRole("button", { name: new RegExp(`خيارات ${food.name}`) }).click();
    await page.getByRole("menuitem", { name: "تعديل" }).click();
    const dialog = page.getByRole("dialog", { name: "تعديل الكمية والقسم" });
    await dialog.getByRole("radio", { name: "عشاء" }).click();
    await dialog.getByRole("button", { name: "حفظ التغييرات" }).click();
    const dinnerToggle = page.getByRole("button", { name: /قسم عشاء$/ });
    await expect(dinnerToggle).toContainText("طعام واحد");
    if ((await dinnerToggle.getAttribute("aria-expanded")) !== "true") await dinnerToggle.click();
    await expect(dinnerToggle).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator("#meal-dinner").getByRole("heading", { name: food.name })).toBeVisible();
  });
});
