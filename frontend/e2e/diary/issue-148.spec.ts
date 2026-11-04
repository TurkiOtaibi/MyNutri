import { diaryDate as localDate, expect, test, uniqueName } from "../foods/helpers";

test.describe("@diary @issue148 quick re-add from recent foods", () => {
  test("@p0 «أضف مجددًا» re-logs the last quantity into the selected meal in one tap", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Quick readd"), brand: "علامة أولى" });
    const other = await foodsApi.create({ name: food.name, brand: "علامة ثانية" });
    const today = localDate();
    await foodsApi.createDiary(food.id, today, 3, "snack");
    await foodsApi.createDiary(food.id, today, 2.5, "dinner");
    await foodsApi.createDiary(other.id, today, 2.5, "dinner");

    await page.goto("/diary");
    await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    const quickAdd = dialog.getByRole("button", { name: `أضف مجددًا: ${food.name}، ${food.brand}، 2.5 حصة`, exact: true });
    await expect(dialog.getByRole("button", { name: `أضف مجددًا: ${other.name}، ${other.brand}، 2.5 حصة`, exact: true })).toBeVisible();
    await expect(quickAdd).toBeVisible();
    await expect(quickAdd).toHaveText("أضف مجددًا");
    await quickAdd.click();
    await expect(dialog).toHaveCount(0);

    const saved = await foodsApi.listDiary(today);
    const entries = saved.filter((entry) => entry.food.id === food.id);
    expect(saved.filter((entry) => entry.food.id === other.id)).toHaveLength(1);
    expect(entries).toHaveLength(3);
    expect(entries.filter((entry) => entry.meal_type === "breakfast").map((entry) => Number(entry.quantity))).toEqual([2.5]);
  });

  test("@p1 choosing the recent food row still opens configuration without saving", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Quick configure") });
    const today = localDate();
    await foodsApi.createDiary(food.id, today, 2, "snack");

    await page.goto("/diary");
    await page.getByRole("button", { name: "إضافة طعام إلى غداء" }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await dialog.getByRole("button", { name: new RegExp(`^${food.name}`) }).click();
    await expect(dialog.getByRole("heading", { name: "قسم الوجبة" })).toBeVisible();
    await expect(dialog.getByRole("button", { name: /^أضف مجددًا/ })).toHaveCount(0);
    expect((await foodsApi.listDiary(today)).filter((entry) => entry.food.name === food.name)).toHaveLength(1);
  });
});
