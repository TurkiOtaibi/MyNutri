import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const API_ORIGIN = new URL(API_URL).origin;
const GOAL_ID = "00000000-0000-4000-8000-000000000033";
const RECOMMENDATION_ID = "00000000-0000-4000-8000-000000000334";

function recommendation() {
  const priority = {
    rule_key: "sodium_overage", rank: "main", category: "limit",
    title_ar: "تقليل الصوديوم",
    reason_ar: "تجاوز متوسط الصوديوم الحد المرجعي في يومين مكتملين أو أكثر.",
    confidence: "strong", coverage_percent: 100, complete_day_count: 5,
    action_key: "replace_high_sodium_choice",
    action_ar: "استبدل خيارًا مرتفع الصوديوم بخيار أقل صوديومًا هذا الأسبوع.",
    action_mode: "replace", rules_version: "w3-priority-1.0.0",
    copy_version: "w3-priority-ar-1.0.0", facts_used: [], evidence_refs: [], conflict_decisions: []
  };
  return {
    schema_version: 1, recommendation_id: RECOMMENDATION_ID,
    source_analysis_id: "00000000-0000-4000-8000-000000000032",
    source_analysis_revision: 2, period_start: "2026-08-11", period_end: "2026-08-17",
    generated_at: "2026-08-17T09:00:00Z", expires_at: "2026-08-19T12:00:00Z",
    status: "selected", rules_version: "w3-priority-1.0.0",
    copy_version: "w3-priority-ar-1.0.0", analysis_rules_version: "w3-analysis-1.1.0",
    nutrition_registry_version: "2.0.0", food_group_rules_version: "1.0.0",
    nova_rules_version: "1.0.0", snapshot_schema_versions: [3], target_plan_refs: [],
    main: priority, secondary: null, excluded_alternatives: [], none_reason: null,
    etag: `"weekly-priority-${RECOMMENDATION_ID}"`
  };
}

function goal(state = "active", version = 2) {
  return {
    schema_version: 1, goal_id: GOAL_ID, root_goal_id: GOAL_ID, previous_goal_id: null,
    sequence_number: 1, state, version, rule_key: "sodium_overage",
    action_key: "replace_high_sodium_choice", weekly_target_count: 3, scheduled_day_mask: [],
    owner_note: null, window_start: "2026-08-18", window_end: "2026-08-24",
    source_recommendation_id: RECOMMENDATION_ID, source_rules_version: "w3-priority-1.0.0",
    source_copy_version: "w3-priority-ar-1.0.0",
    progress: { window_start: "2026-08-18", window_end: "2026-08-24", progress_count: 1,
      target_count: 3, progress_percent: 33, complete_day_count: 2, partial_day_count: 1,
      unregistered_day_count: 4, status: "in_progress", as_of_diary_date: "2026-08-20",
      source_day_versions: { "2026-08-18": 2 }, calculation_rules_version: "w3-priority-1.0.0",
      last_recomputed_at: "2026-08-20T09:00:00Z" },
    allowed_actions: ["edit", "change", "pause", "end"], reminder_preference: "disabled",
    offered_at: "2026-08-18T09:00:00Z", accepted_at: "2026-08-18T09:05:00Z",
    deferred_at: null, deferred_until: null, changed_at: null, paused_at: null, resumed_at: null,
    completed_at: null, reviewed_at: null, rejected_at: null, ended_at: null, archived_at: null,
    calendar: { current_diary_date: "2026-08-20", calendar_timezone: "Asia/Riyadh",
      next_rollover_at: "2026-08-20T21:00:00Z" },
    created_at: "2026-08-18T09:00:00Z", updated_at: "2026-08-20T09:00:00Z",
    etag: `"goal-${version}"`
  };
}

async function routePlan033(page: Page) {
  await page.route((url) => url.origin === API_ORIGIN && url.pathname === "/progress/weekly-priorities/current",
    (route) => route.fulfill({ status: 200, contentType: "application/json", json: recommendation() }));
  await page.route((url) => url.origin === API_ORIGIN && url.pathname === "/progress/behavior-goals/current",
    (route) => route.fulfill({ status: 200, contentType: "application/json", json: { recommendation: recommendation(), goal: goal() } }));
  await page.route((url) => url.origin === API_ORIGIN && url.pathname === "/progress/behavior-goals/history",
    (route) => route.fulfill({ status: 200, contentType: "application/json", json: { items: [], next_cursor: null } }));
}

test.describe("@plan033 weekly priorities and behavior goals", () => {
  test("Arabic RTL goal is accessible, responsive, and Escape cancels the command", async ({ page }) => {
    await routePlan033(page);
    await page.goto("/progress");
    await expect(page.getByRole("heading", { name: "تقليل الصوديوم" })).toBeVisible();
    await expect(page.getByText("1 من 3 أيام")).toBeVisible();
    await page.getByRole("button", { name: "إيقاف مؤقت" }).click();
    const dialog = page.getByRole("dialog", { name: "تأكيد الإجراء" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("button", { name: "إلغاء" })).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    const accessibility = await new AxeBuilder({ page }).include('main [dir="rtl"]').analyze();
    expect(accessibility.violations).toEqual([]);
    for (const width of [320, 360, 390, 430]) {
      await page.setViewportSize({ width, height: 844 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    }
  });

  test("command carries stable idempotency and expected version and does not duplicate replay announcement", async ({ page }) => {
    await routePlan033(page);
    const requests: Array<{ key: string | undefined; body: unknown }> = [];
    await page.route((url) => url.origin === API_ORIGIN && url.pathname === `/progress/behavior-goals/${GOAL_ID}/commands`, async (route) => {
      requests.push({ key: route.request().headers()["idempotency-key"], body: route.request().postDataJSON() });
      await route.fulfill({ status: 200, headers: { "Idempotent-Replayed": "true", "Access-Control-Expose-Headers": "Idempotent-Replayed" }, contentType: "application/json",
        json: { result: "paused", previous_goal: null, goal: { ...goal("paused", 3), allowed_actions: ["resume", "end"] }, recommendation: recommendation() } });
    });
    await page.goto("/progress");
    await page.getByRole("button", { name: "إيقاف مؤقت" }).click();
    await page.getByRole("button", { name: "تأكيد" }).click();
    await expect(page.getByRole("heading", { name: "متوقف مؤقتًا" })).toBeFocused();
    expect(requests).toHaveLength(1);
    expect(requests[0].key).toBeTruthy();
    expect(requests[0].body).toMatchObject({ event: "pause", expected_version: 2 });
    await expect(page.locator('[aria-live="polite"]')).not.toContainText("تم تحديث الهدف");
  });
});
