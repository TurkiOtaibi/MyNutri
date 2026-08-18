import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const API_ORIGIN = new URL(API_URL).origin;

function analysisResponse(lifecycle: "current" | "stale" = "current") {
  const id = "00000000-0000-4000-8000-000000000032";
  const period = {
    value: 18,
    value_state: "known",
    amount_qualifier: "exact",
    complete_day_count: 5,
    numeric_day_count: 5,
    known_entry_count: 8,
    total_entry_count: 8,
    coverage_percent: 100,
    confidence: "strong",
    status: "below_target",
    evidence_refs: []
  };
  const metric = {
    metric_key: "nutrient:fiber_g",
    metric_kind: "daily_average",
    unit: "g/day",
    aggregation: "average_numeric_days",
    direction: "minimum",
    target: { type: "minimum", value: 25, lower: null, upper: null, source_plan_ids: [] },
    current: period,
    previous: { ...period, value: 16 },
    comparison: { status: "no_material_change", reason: "comparable", difference: 2, normalized_adverse_delta: -0.08 },
    persistence: { kind: "same_direction_two_period", qualifies: true, reason: "qualified" },
    contributors: { current: [], previous: [] }
  };
  return {
    source_analysis_id: id,
    source_analysis_revision: 1,
    lifecycle_status: lifecycle,
    stale_reasons: lifecycle === "stale" ? ["day_reopened"] : [],
    as_of_diary_date: "2026-08-17",
    period_start: "2026-08-11",
    period_end: "2026-08-17",
    previous_period_start: "2026-08-04",
    previous_period_end: "2026-08-10",
    complete_day_count: 5,
    previous_complete_day_count: 5,
    metric_summaries: [metric],
    source_versions: {
      analysis_rules_version: "w3-analysis-1.0.0",
      nutrition_registry_version: "2.0.0",
      calculation_engine_version: "2.0.0",
      food_group_rules_version: "1.0.0",
      source_reliability_rules_version: "1.0.0",
      nova_rules_version: "1.0.0",
      snapshot_schema_versions: [3],
      status_evidence_version: 1,
      rules_manifest_hash: "a".repeat(64),
      source_input_hash: "b".repeat(64),
      content_hash: "c".repeat(64)
    },
    priority_input: {
      interface_version: 1,
      principal_ref: "00000000-0000-4000-8000-000000000001",
      source_analysis_id: id,
      source_analysis_revision: 1,
      generated_at: "2026-08-17T09:00:00Z",
      as_of_diary_date: "2026-08-17",
      calendar_timezone: "Asia/Riyadh",
      period_start: "2026-08-11",
      period_end: "2026-08-17",
      previous_period_start: "2026-08-04",
      previous_period_end: "2026-08-10",
      analysis_rules_version: "w3-analysis-1.0.0",
      nutrition_registry_version: "2.0.0",
      food_group_rules_version: "1.0.0",
      nova_rules_version: "1.0.0",
      snapshot_schema_versions: [3],
      target_plan_refs: [],
      days: [],
      previous_period: [],
      metric_facts: [metric],
      safety_flags: []
    },
    generated_at: "2026-08-17T09:00:00Z",
    finalized_at: "2026-08-17T09:00:00Z",
    etag: `"analysis-${id}-r1"`
  };
}

async function routeEmptyAnalysis(page: Page) {
  await page.route((url) => url.origin === API_ORIGIN && url.pathname === "/progress/nutrition-analysis/current", (route) => route.fulfill({
    status: 404,
    contentType: "application/json",
    json: { error: { code: "ANALYSIS_NOT_FOUND", message_ar: "لا يوجد تحليل محفوظ بعد.", details: {}, request_id: "request-032" } }
  }));
  await page.route((url) => url.origin === API_ORIGIN && url.pathname === "/progress/nutrition-analysis/history", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    json: { items: [], next_cursor: null }
  }));
}

test.describe("@plan032 nutrition pattern analysis", () => {
  test("@p0 evaluates with version headers and renders Arabic non-color evidence", async ({ page }) => {
    await routeEmptyAnalysis(page);
    let requestHeaders: Record<string, string> = {};
    let requestBody = "";
    await page.route((url) => url.origin === API_ORIGIN && url.pathname === "/progress/nutrition-analysis/evaluate", async (route) => {
      requestHeaders = route.request().headers();
      requestBody = route.request().postData() ?? "";
      await route.fulfill({ status: 201, contentType: "application/json", json: analysisResponse() });
    });
    await page.goto("/progress");
    await expect(page.getByRole("heading", { name: "تحليل نمط التغذية" })).toBeVisible();
    await expect(page.getByText("التحليل غير متاح لعدم كفاية الأيام المكتملة")).toBeVisible();
    await page.getByRole("button", { name: "تحديث التحليل" }).click();
    await expect(page.getByText("الألياف")).toBeVisible();
    await expect(page.getByText("أقل من النطاق المستهدف")).toBeVisible();
    expect(requestHeaders["if-match"]).toBe('"analysis-none"');
    expect(requestHeaders["idempotency-key"]).toBeTruthy();
    expect(JSON.parse(requestBody)).toEqual({ expected_current_revision: null });
  });

  test("@p0 ambiguous retry preserves the exact idempotency command", async ({ page }) => {
    await routeEmptyAnalysis(page);
    const requests: Array<{ key: string; match: string; body: string | null }> = [];
    await page.route((url) => url.origin === API_ORIGIN && url.pathname === "/progress/nutrition-analysis/evaluate", async (route) => {
      requests.push({
        key: route.request().headers()["idempotency-key"],
        match: route.request().headers()["if-match"],
        body: route.request().postData()
      });
      if (requests.length === 1) await route.abort("connectionfailed");
      else await route.fulfill({ status: 201, contentType: "application/json", json: analysisResponse() });
    });
    await page.goto("/progress");
    await page.getByRole("button", { name: "تحديث التحليل" }).click();
    await expect(
      page.getByRole("alert").filter({ hasText: "تعذر تحديث التحليل" })
    ).toContainText("تعذر تحديث التحليل");
    await page.getByRole("button", { name: "تحديث التحليل" }).click();
    await expect(page.getByText("الألياف")).toBeVisible();
    expect(requests).toHaveLength(2);
    expect(requests[1]).toEqual(requests[0]);
  });

  test("stale state, RTL, accessibility, reduced motion, and mobile widths remain explicit", async ({ page }) => {
    await page.route((url) => url.origin === API_ORIGIN && url.pathname === "/progress/nutrition-analysis/current", (route) => route.fulfill({ status: 200, contentType: "application/json", json: analysisResponse("stale") }));
    await page.route((url) => url.origin === API_ORIGIN && url.pathname === "/progress/nutrition-analysis/history", (route) => route.fulfill({ status: 200, contentType: "application/json", json: { items: [], next_cursor: null } }));
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/progress");
    await expect(page.getByText("تغيرت بعض البيانات منذ هذه النسخة")).toBeVisible();
    const progressSurface = page.locator('main [dir="rtl"]');
    await expect(progressSurface).toBeVisible();
    const accessibility = await new AxeBuilder({ page })
      .include('main [dir="rtl"]')
      .analyze();
    expect(accessibility.violations).toEqual([]);
    for (const width of [320, 360, 390, 430]) {
      await page.setViewportSize({ width, height: 844 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    }
  });
});
