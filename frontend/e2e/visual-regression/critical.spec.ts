import { type Page, type Route } from "@playwright/test";

import type { ProfileResponse, TargetResponse } from "../../lib/types";
import {
  API_TOKEN,
  API_URL,
  diaryDate,
  expect,
  test,
  validFood
} from "../foods/helpers";

const profileHeaders = () => ({ Authorization: `Bearer ${API_TOKEN}` });

async function stableRendering(page: Page): Promise<void> {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.evaluate(() => document.fonts.ready);
}

async function fulfillBlockedPreview(route: Route): Promise<void> {
  if (route.request().method() !== "POST") return route.continue();
  const response = await route.fetch();
  const targets = await response.json() as TargetResponse;
  await route.fulfill({
    response,
    json: {
      ...targets,
      calories: 799,
      target_calories: 799,
      final_target_calories: 799,
      safety_outcome: "very_low_energy_blocked",
      can_activate: false
    }
  });
}

function adminFood(idSuffix: number, name: string, status: "active" | "archived" = "active") {
  return {
    ...validFood({ name }),
    id: `00000000-0000-4000-8000-${String(idSuffix).padStart(12, "0")}`,
    net_carbs_g: 20,
    status,
    archived_at: status === "archived" ? "2026-08-04T00:00:00Z" : null,
    group_data_status: "unknown",
    group_data_completeness: "unknown",
    created_at: "2026-08-04T00:00:00Z",
    updated_at: "2026-08-04T00:00:00Z"
  };
}

function adminPage(items: ReturnType<typeof adminFood>[]) {
  return {
    items,
    total: items.length,
    page: 1,
    page_size: 20,
    total_pages: 1,
    categories: ["other"],
    uncategorized_count: 0
  };
}

test.describe("critical visual regression", () => {
  test("Profile blocked-safety preview", async ({ page, request }) => {
    const profileResponse = await request.get(`${API_URL}/profile`, { headers: profileHeaders() });
    expect(profileResponse.status()).toBe(200);
    const profile = await profileResponse.json() as ProfileResponse;
    await page.route((url) => url.pathname === "/profile/preview", fulfillBlockedPreview);

    await page.goto("/profile?visual=blocked-safety");
    await page.getByLabel("الوزن").fill(String(profile.weight_kg + 1));
    const preview = page.getByRole("region", { name: "الأهداف المتوقعة بعد الحفظ" });
    await expect(preview).toContainText("799");
    await stableRendering(page);

    await expect(preview).toHaveScreenshot("profile-blocked-safety.png");
  });

  test("Diary populated day and week strip", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: "E2E-Visual-Diary-Food", calories: 240 });
    await foodsApi.createDiary(food.id, diaryDate(), 1, "breakfast");

    await page.goto("/diary?visual=populated");
    await expect(page.getByText(food.name, { exact: true })).toBeVisible();
    const diary = page.locator(".diary-page");
    await stableRendering(page);

    await expect(diary).toHaveScreenshot("diary-populated-week.png");
  });

  test("Diary Add-Food sheet open", async ({ page }) => {
    await page.goto("/diary?visual=add-food");
    await page.locator('[data-diary-add-trigger="meal-breakfast"]').click();
    const sheet = page.locator(".add-food-sheet-form");
    await expect(sheet).toBeVisible();
    await stableRendering(page);

    await expect(sheet).toHaveScreenshot("diary-add-food-open.png");
  });

  test("Admin Food lifecycle on mobile", async ({ page }) => {
    const food = adminFood(280, "Plan028 lifecycle visual");
    await page.route(/\/admin\/foods\?.*$/, async (route) => {
      const status = new URL(route.request().url()).searchParams.get("status") ?? "active";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        json: adminPage(status === "archived" ? [{ ...food, status: "archived" as const }] : [food])
      });
    });

    await page.goto("/admin/foods?visual=lifecycle");
    await page.getByLabel("الحالة").selectOption("archived");
    await page.getByRole("button", { name: `إجراءات ${food.name}` }).click();
    const lifecycle = page.locator("main");
    await expect(page.getByRole("menuitem", { name: "استعادة" })).toBeVisible();
    await stableRendering(page);

    await expect(lifecycle).toHaveScreenshot("admin-food-lifecycle-mobile.png");
  });
});
