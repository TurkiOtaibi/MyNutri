import { type Page, type Route } from "@playwright/test";

import type { LabChartZoneSegment, LabOverviewResponse, LabTestDetailResponse, ProfileResponse, TargetResponse, WeekSummary } from "../../lib/types";
import { catalogFixture, ferritinAge51Segments, ferritinFemaleHistory } from "../../tests/unit/fixtures/labs";
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
          days: week.days.map((day) => ({
            ...day,
            targets: null,
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

function adminFood(idSuffix: number, name: string) {
  return {
    ...validFood({ name }),
    id: `00000000-0000-4000-8000-${String(idSuffix).padStart(12, "0")}`,
    net_carbs_g: 20,
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
    categories: ["other"]
  };
}

const visualLabSegments: LabChartZoneSegment[] = ferritinAge51Segments.map((segment) => ({
  ...segment,
  zones: segment.zones.map((zone) => ({
    ...zone,
    status: { ...zone.status, tone: zone.status.code === "in_range" ? "within" : "outside" },
  })),
}));

const visualLabResults = ferritinFemaleHistory.map((result, index) => ({
  ...result,
  display_value: index === 0 ? "5.900" : "12.40",
  display_unit: "ng/mL",
  status: index === 0
    ? { code: "low", label_ar: "منخفض", tone: "outside" }
    : { code: "in_range", label_ar: "ضمن النطاق", tone: "within" },
  reference_zones: visualLabSegments[index].zones,
})).reverse();

const visualLabOverview: LabOverviewResponse = {
  items: [{
    test_key: "ferritin",
    latest: visualLabResults[0],
    last_updated_at: visualLabResults[0].updated_at,
  }],
  eligibility: { allowed: true, reason: null },
  server_today: FIXED_VISUAL_DATE,
  medical_rules_version: "labs-v1",
  read_only: false,
};

const visualLabDetail: LabTestDetailResponse = {
  test: catalogFixture.tests[0],
  results: visualLabResults,
  chart_zones: visualLabSegments,
  reference_at_date: visualLabResults[0].test_date,
  reference_zones: visualLabResults[0].reference_zones,
  eligibility: { allowed: true, reason: null },
  server_today: FIXED_VISUAL_DATE,
  medical_rules_version: "labs-v1",
  read_only: false,
};

async function routeVisualLabs(page: Page, principalId?: string) {
  await page.route((url) => isExactApiPath(url, "/labs/catalog"), (route) => route.fulfill({ json: catalogFixture }));
  const overviewPath = principalId ? `/admin/users/${principalId}/labs` : "/labs";
  const detailPath = principalId ? `/admin/users/${principalId}/labs/tests/ferritin` : "/labs/tests/ferritin";
  await page.route((url) => isExactApiPath(url, overviewPath), (route) => route.fulfill({
    json: { ...visualLabOverview, read_only: Boolean(principalId) },
  }));
  await page.route((url) => isExactApiPath(url, detailPath), (route) => route.fulfill({
    json: { ...visualLabDetail, read_only: Boolean(principalId) },
  }));
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

    await expect(preview).toHaveScreenshot("profile-blocked-safety.png", {
      maxDiffPixelRatio: 0.01
    });
  });

  test("Diary populated day and week strip", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: "E2E-Visual-Diary-Food", calories: 240 });
    await foodsApi.createDiary(food.id, FIXED_VISUAL_DATE, 1, "breakfast");
    await routeFixedCalendar(page);
    await routeNoTargetWeek(page);

    await page.goto("/diary?visual=populated");
    await expect(page.getByText(food.name, { exact: true })).toBeVisible();
    const diary = page.locator(".diary-page");
    await expect(
      diary.getByText("لا يوجد مصدر هدف محفوظ لهذا اليوم.", { exact: true })
    ).toBeVisible();
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

  test("Foods admin actions on mobile", async ({ page }) => {
    test.setTimeout(120_000);
    const food = adminFood(280, "Plan028 admin actions visual");
    await page.route(
      (url) => isExactApiPath(url, "/foods"),
      async (route) => {
        if (route.request().method() !== "GET") return route.continue();
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          json: adminPage([food])
        });
      }
    );

    await page.goto("/foods?visual=admin-actions");
    await stableRendering(page);
    await page.getByRole("button", { name: `إجراءات ${food.name}` }).click();
    await expect(page.getByRole("menuitem", { name: "تعديل" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "حذف" })).toBeVisible();

    await expect(page).toHaveScreenshot("foods-admin-actions-mobile.png", {
      timeout: 20_000
    });
  });

  test("Labs populated overview", async ({ page }) => {
    await routeVisualLabs(page);
    await page.goto("/labs?visual=overview");
    await expect(page.locator('[data-testid="lab-row"][data-test-key="ferritin"]')).toBeVisible();
    await stableRendering(page);
    await expect(page).toHaveScreenshot("labs-overview-populated.png");
  });

  test("Labs populated batch values", async ({ page }) => {
    await routeVisualLabs(page);
    await page.goto("/labs?visual=batch");
    await page.getByRole("button", { name: "إضافة نتائج", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة نتائج" });
    await dialog.getByRole("button", { name: "التالي", exact: true }).click();
    await page.locator('[data-panel-key="iron_studies"]').check();
    await dialog.getByRole("button", { name: "التالي", exact: true }).click();
    await page.locator("#lab-ferritin-value").fill("12.400");
    await stableRendering(page);
    await expect(dialog).toHaveScreenshot("labs-batch-populated.png");
  });

  test("Labs detail at an age-zone boundary", async ({ page }) => {
    await routeVisualLabs(page);
    await page.goto("/labs/ferritin?visual=age-zone");
    await expect(page.getByTestId("lab-detail")).toBeVisible();
    await stableRendering(page);
    await expect(page.getByTestId("lab-detail")).toHaveScreenshot("labs-detail-age-zone.png");
  });

  test("Labs selected-user read-only admin detail", async ({ page }) => {
    const principalId = "00000000-0000-4000-8000-000000000015";
    await routeVisualLabs(page, principalId);
    await page.goto(`/admin/users/${principalId}/labs/ferritin?visual=admin-readonly`);
    await expect(page.getByTestId("lab-detail")).toContainText("للقراءة فقط");
    await stableRendering(page);
    await expect(page.getByTestId("lab-detail")).toHaveScreenshot("labs-admin-detail-readonly.png");
  });

});
