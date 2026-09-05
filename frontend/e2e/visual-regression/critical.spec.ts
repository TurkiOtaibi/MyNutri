import { type Page, type Route } from "@playwright/test";

import type { ProfileResponse, TargetResponse } from "../../lib/types";
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
    archived_at: status === "archived" ? FIXED_VISUAL_TIME : null,
    group_data_status: "unknown",
    group_data_completeness: "unknown",
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

function visualPatternAnalysis() {
  const id = "00000000-0000-4000-8000-000000000032";
  const evidence = { value: 18, value_state: "known", amount_qualifier: "exact", complete_day_count: 5, numeric_day_count: 5, known_entry_count: 8, total_entry_count: 8, coverage_percent: 100, confidence: "strong", status: "below_target", evidence_refs: [] };
  const metric = { metric_key: "nutrient:fiber_g", metric_kind: "daily_average", unit: "g/day", aggregation: "average_numeric_days", direction: "minimum", target: { type: "minimum", value: 25, lower: null, upper: null, source_plan_ids: [] }, current: evidence, previous: { ...evidence, value: 16 }, comparison: { status: "no_material_change", reason: "comparable", difference: 2, normalized_adverse_delta: -0.08 }, persistence: { kind: "same_direction_two_period", qualifies: true, reason: "qualified" }, contributors: { current: [], previous: [] } };
  return { source_analysis_id: id, source_analysis_revision: 1, lifecycle_status: "current", stale_reasons: [], as_of_diary_date: "2026-08-17", period_start: "2026-08-11", period_end: "2026-08-17", previous_period_start: "2026-08-04", previous_period_end: "2026-08-10", complete_day_count: 5, previous_complete_day_count: 5, metric_summaries: [metric], source_versions: { analysis_rules_version: "w3-analysis-2.0.0", nutrition_registry_version: "3.0.0", calculation_engine_version: "2.0.0", food_group_rules_version: "1.0.0", source_reliability_rules_version: "1.0.0", snapshot_schema_versions: [4], status_evidence_version: 1, rules_manifest_hash: "a".repeat(64), source_input_hash: "b".repeat(64), content_hash: "c".repeat(64) }, priority_input: { interface_version: 2, principal_ref: "00000000-0000-4000-8000-000000000001", source_analysis_id: id, source_analysis_revision: 1, generated_at: FIXED_VISUAL_TIME, as_of_diary_date: "2026-08-17", calendar_timezone: "Asia/Riyadh", period_start: "2026-08-11", period_end: "2026-08-17", previous_period_start: "2026-08-04", previous_period_end: "2026-08-10", analysis_rules_version: "w3-analysis-2.0.0", nutrition_registry_version: "3.0.0", food_group_rules_version: "1.0.0", snapshot_schema_versions: [4], target_plan_refs: [], days: [], previous_period: [], metric_facts: [metric], safety_flags: [] }, generated_at: FIXED_VISUAL_TIME, finalized_at: FIXED_VISUAL_TIME, etag: `"analysis-${id}-r1"` };
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
        const status = new URL(route.request().url()).searchParams.get("status") ?? "active";
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          json: adminPage(status === "archived" ? [{ ...food, status: "archived" as const }] : [food])
        });
      }
    );

    await page.goto("/admin/foods?visual=lifecycle");
    await page.getByLabel("الحالة").selectOption("archived");
    await page.getByRole("button", { name: `إجراءات ${food.name}` }).click();
    const lifecycle = page.locator("main");
    await expect(page.getByRole("menuitem", { name: "استعادة" })).toBeVisible();
    await stableRendering(page);

    await expect(lifecycle).toHaveScreenshot("admin-food-lifecycle-mobile.png");
  });

  test("Nutrition pattern analysis on mobile", async ({ page }) => {
    await page.route(
      (url) => isExactApiPath(url, "/progress/nutrition-analysis/v2/current"),
      (route) => route.fulfill({ status: 200, contentType: "application/json", json: visualPatternAnalysis() })
    );
    await page.route(
      (url) => isExactApiPath(url, "/progress/nutrition-analysis/v2/history"),
      (route) => route.fulfill({ status: 200, contentType: "application/json", json: { items: [], next_cursor: null } })
    );
    await page.goto("/progress?visual=pattern-analysis");
    await expect(page.getByText("الألياف")).toBeVisible();
    await stableRendering(page);
    await expect(page.locator("main")).toHaveScreenshot("nutrition-pattern-analysis-mobile.png");
  });

  test("Weekly priority remains inactive on mobile", async ({ page }) => {
    await page.route((url) => isExactApiPath(url, "/progress/nutrition-analysis/v2/current"),
      (route) => route.fulfill({ status: 200, contentType: "application/json", json: visualPatternAnalysis() }));
    await page.route((url) => isExactApiPath(url, "/progress/nutrition-analysis/v2/history"),
      (route) => route.fulfill({ status: 200, contentType: "application/json", json: { items: [], next_cursor: null } }));
    await page.goto("/progress?visual=weekly-priority-goal");
    await expect(page.getByRole("heading", { name: "زيادة الفواكه والخضروات" })).toHaveCount(0);
    await expect(page.getByText("الألياف")).toBeVisible();
    await stableRendering(page);
    await expect(page.locator("main")).toHaveScreenshot("weekly-priority-goal-mobile.png");
  });
});
