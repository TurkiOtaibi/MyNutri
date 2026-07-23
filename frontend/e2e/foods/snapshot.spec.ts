import { diaryDate, test, expect } from "./helpers";

test.describe("Diary snapshot safety after Food delete @foods", () => {
  test("[FOOD-TC-122] @p0 historical Diary entry survives Food hard delete", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Snapshot-Delete-${Date.now()}`, calories: 175, protein_g: 8, carb_g: 20, fat_g: 7 });
    const date = diaryDate();
    const entry = await foodsApi.createDiary(food.id, date, 1.5);
    await foodsApi.remove(food.id);

    const stored = (await foodsApi.listDiary(date)).find((item) => item.id === entry.id)!;
    expect(stored.nutrition_snapshot.name).toBe(food.name);
    expect(stored.totals.calories).toBe(262.5);

    await page.goto("/diary");
    await expect(page.getByText(food.name, { exact: true })).toBeVisible();
    await expect(page.getByText(/262\.5|263/).first()).toBeVisible();
  });
});
