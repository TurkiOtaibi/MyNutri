import { type Page, type Route } from "@playwright/test";

import type { ProfileResponse, TargetResponse, WeekSummary } from "../../lib/types";
import {
  API_TOKEN,
  API_URL,
  expect,
  test,
  validFood
} from "../foods/helpers";

const API_ORIGIN = new URL(API_URL).origin;
const FIXED_VISUAL_DATE = "2026-08-01";
const FIXED_VISUAL_TIME = "2026-08-01T12:00:00.000Z";
const FIXED_NEXT_ROLLOVER = "2026-08-01T21:00:00.000Z";
const profileHeaders = () => ({ Authorization: `Bearer ${API_TOKEN}` });

function isExactApiPath(url: URL, pathname: string): boolean {
  return url.origin === API_ORIGIN && url.pathname === pathname;
}

async function routeFixedCalendar(page: Page): Promise<void> {
  await page.route(
    (url) => isExactApiPath(url, "/account/calendar"),
    async (route) => {
      if (route.request().method() !== "GET") return route.continue();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        json: {
          current_diary_date: FIXED_VISUAL_DATE,
          calendar_timezone: "Asia/Riyadh",
          next_rollover_at: FIXED_NEXT_ROLLOVER
        }
      });
    }
  );
}

async function routeNoTargetWeek(page: Page): Promise<void> {
  await page.route(
    (url) => isExactApiPath(url, "/diary/week"),
    async (route) => {
      if (route.request().method() !== "GET") return route.continue();
      const response = await route.fetch();
      const week = await response.json() as WeekSummary;
      await route.fulfill({
        response,
        json: {
          ...week,
          targets: null,
          days: week.days.map((day) => ({
            ...day,
            targets: null,
            target_provenance: "no_target_source",
            nutrient_aggregates: day.nutrient_aggregates.map((aggregate) => ({
              ...aggregate,
              target: null,
              evaluation: null,
              progress_percent: null,
              remaining: null
            }))
          }))
        }
      });
    }
  );
}

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

function adminFood(idSuffix: number, name: string, archived = false) {
  return {
    ...validFood({ name }),
    id: `00000000-0000-4000-8000-${String(idSuffix).padStart(12, "0")}`,
    net_carbs_g: 20,
    archived_at: archived ? FIXED_VISUAL_TIME : null,
    created_at: FIXED_VISUAL_TIME,
    updated_at: FIXED_VISUAL_TIME
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
  test.beforeEach(async ({ page }) => {
    await page.clock.install({ time: FIXED_VISUAL_TIME });
  });

  test("Profile blocked-safety preview", async ({ page, request }) => {
    const profileResponse = await request.get(`${API_URL}/profile`, { headers: profileHeaders() });
    expect(profileResponse.status()).toBe(200);
    const currentProfile = await profileResponse.json() as ProfileResponse;
    const profile: ProfileResponse = {
      ...currentProfile,
      birth_date: "1990-01-01",
      height_cm: 175,
      weight_kg: 80,
      activity_level: "moderate",
      goal: "maintain",
      effective_plan: null,
      pending_plan: null,
      updated_at: FIXED_VISUAL_TIME
    };
    await page.route(
      (url) => isExactApiPath(url, "/profile"),
      async (route) => {
        if (route.request().method() !== "GET") return route.continue();
        await route.fulfill({ status: 200, contentType: "application/json", json: profile });
      }
    );
    await page.route(
      (url) => isExactApiPath(url, "/profile/preview"),
      fulfillBlockedPreview
    );
    await page.route(
      (url) => isExactApiPath(url, "/target-plans"),
      async (route) => {
        if (route.request().method() !== "GET") return route.continue();
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          json: { items: [], next_cursor: null }
        });
      }
    );

    await page.goto("/profile?visual=blocked-safety");
    await page.getByLabel("الوزن").fill(String(profile.weight_kg + 1));
    const preview = page.getByRole("region", { name: "الأهداف المتوقعة بعد الحفظ" });
    await expect(preview).toContainText("799");
    await stableRendering(page);

    await expect(preview).toHaveScreenshot("profile-blocked-safety.png");
  });

  test("Diary populated day and week strip", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: "E2E-Visual-Diary-Food", calories: 240 });
    await foodsApi.createDiary(food.id, FIXED_VISUAL_DATE, 1, "breakfast");
    await routeFixedCalendar(page);
    await routeNoTargetWeek(page);

    await page.goto("/diary?visual=populated");
    await expect(page.getByText(food.name, { exact: true })).toBeVisible();
    const diary = page.locator(".diary-page");
    await stableRendering(page);

    await expect(diary).toHaveScreenshot("diary-populated-week.png");
  });

  test("Diary Add-Food sheet open", async ({ page }) => {
    const pickerFood = adminFood(281, "Plan028 frozen picker food");
    await routeFixedCalendar(page);
    await page.route(
      (url) => isExactApiPath(url, "/foods/picker"),
      async (route) => {
        if (route.request().method() !== "GET") return route.continue();
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          json: {
            items: [pickerFood],
            recent_items: [],
            next_cursor: null
          }
        });
      }
    );
    await page.goto("/diary?visual=add-food");
    await page.locator('[data-diary-add-trigger="meal-breakfast"]').click();
    const sheet = page.locator(".add-food-sheet-form");
    await expect(sheet).toBeVisible();
    await stableRendering(page);

    await expect(sheet).toHaveScreenshot("diary-add-food-open.png");
  });

  test("Admin Food lifecycle on mobile", async ({ page }) => {
    const food = adminFood(280, "Plan028 lifecycle visual");
    await page.route(
      (url) => isExactApiPath(url, "/admin/foods"),
      async (route) => {
        if (route.request().method() !== "GET") return route.continue();
        const archived = new URL(route.request().url()).searchParams.get("archived") === "true";
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          json: adminPage(archived ? [{ ...food, archived_at: FIXED_VISUAL_TIME }] : [food])
        });
      }
    );

    await page.goto("/admin/foods?visual=lifecycle");
    await page.getByLabel("عرض الأرشيف").selectOption("archived");
    await page.getByRole("button", { name: `إجراءات ${food.name}` }).click();
    const lifecycle = page.locator("main");
    await expect(page.getByRole("menuitem", { name: "استعادة" })).toBeVisible();
    await stableRendering(page);

    await expect(lifecycle).toHaveScreenshot("admin-food-lifecycle-mobile.png");
  });

});
