import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { emptyFoodForm, normalizeFoodForm } from "../features/foods/food-form-model";
import { catalogFixture, resultFixture } from "../tests/unit/fixtures/labs";
import type { AccountResponse } from "../lib/generated/openapi";
import type { CalendarAuthorityResponse, FoodResponse, LabResultResponse, LabOverviewResponse, LabTestDetailResponse } from "../lib/types";

// Presentation-only synthetic responses. No backend, authentication, or persistence proof.
test.use({ storageState: { cookies: [], origins: [] }, serviceWorkers: "block" });
const actor = "00000000-0000-4000-8000-000000000001";
const subject = "00000000-0000-4000-8000-000000000002";
const today = "2026-11-07";
const account: AccountResponse = { principal_id: actor, auth_user_id: null, email: "fixture@example.test", display_name: "مستخدم تجريبي", username: "fixture", role: "user", status: "active", must_change_password: false };
const calendar: CalendarAuthorityResponse = { current_diary_date: today, calendar_timezone: "Asia/Riyadh", next_rollover_at: "2099-01-01T00:00:00Z" };
const results: LabResultResponse[] = ["2026-11-07", "2026-11-06"].map((date, index) => ({ ...resultFixture("hba1c", date, date), entered_value: index ? "5.2700" : "5.2800", display_value: index ? "5.27" : "5.28", reference_zones: [{ low: "0", high: "1000", low_inclusive: true, high_inclusive: true, status: { code: "fixture", label_ar: "نطاق تجريبي", tone: "positive" } }] }));
const overview: LabOverviewResponse = { eligibility: { allowed: true, reason: null }, items: [], medical_rules_version: "labs-v1", read_only: false, server_today: today };
const detail: LabTestDetailResponse = { test: catalogFixture.tests[2], results, chart_zones: [{ from_date: "2026-11-06", to_date_exclusive: "2026-11-08", age_min: 30, zones: results[0].reference_zones }], reference_at_date: today, reference_zones: results[0].reference_zones, eligibility: overview.eligibility, server_today: today, medical_rules_version: "labs-v1", read_only: false };
const food: FoodResponse = { ...normalizeFoodForm(emptyFoodForm), vitamin_a_mcg: null, folate_mcg: null, created_by_label: null, updated_by_label: null, id: "00000000-0000-4000-8000-000000000003", name: "طعام تجريبي", calories: 200, protein_g: 10, carb_g: 20, fat_g: 8, net_carbs_g: 20, default_unit_type: "serving", unit_amount: 50, unit_basis: "g", nutrition_basis: "per_100g", nutrition_data_source: "official", primary_category: "other", subcategory: "other", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", legacy_nutrition: { vitamin_a_mcg: null, folate_mcg: null, meaning_ar: "قيمة قديمة غير محددة المعيار" }, vitamin_c_mg: 4 };
const registry = {
  rules_manifest_hash: "a".repeat(64), calculation_policy: {},
  nutrients: [{ key: "vitamin_c_mg", storage_field: "vitamin_c_mg", label_ar: "فيتامين ج", unit: "mg", display_precision: 1, display_order: 8, target_type: "recommended", target_source: "registry", target_rule: {}, completeness_participation: true, diary_coverage_participation: false }],
  target_types: ["recommended"], primary_categories: ["other"], food_taxonomy: [{ key: "other", label_ar: "أخرى", subcategories: [{ key: "other", label_ar: "أخرى" }] }], nutrition_data_sources: [{ key: "official", label_ar: "رسمي" }],
};

async function fixtures(page: Page, options: { admin?: boolean; signedOut?: boolean; populatedFood?: boolean } = {}) {
  const api = new URL(process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000");
  const frontend = new URL(process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000");
  for (const url of [api, frontend]) expect(["127.0.0.1", "localhost"]).toContain(url.hostname);
  const unexpected: string[] = [];
  await page.addInitScript(({ signedOut }) => {
    localStorage.clear();
    if (!signedOut) localStorage.setItem("mynutri-session-token", "mn1_fixture");
  }, { signedOut: Boolean(options.signedOut) });
  await page.route("**/*", async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin === frontend.origin) return route.continue();
    if (url.origin !== api.origin || request.method() !== "GET") {
      unexpected.push(`${request.method()} ${url.origin}${url.pathname}`);
      return route.abort();
    }
    const responses: Record<string, unknown> = {
      "/account/me": { ...account, role: options.admin ? "admin" : "user" }, "/account/calendar": calendar,
      "/labs/catalog": catalogFixture, "/labs": overview, "/labs/tests/hba1c": detail,
      "/nutrition/registry": registry, "/target-plans": { items: [], next_cursor: null },
      "/foods": { items: options.populatedFood ? [food] : [], categories: options.populatedFood ? ["other"] : [], page: 1, page_size: 20, total: options.populatedFood ? 1 : 0, total_pages: options.populatedFood ? 1 : 0 },
      [`/foods/${food.id}`]: food,
      [`/admin/users/${subject}/labs`]: { ...overview, read_only: true, eligibility: { allowed: false, reason: "profile_required" } },
      [`/admin/users/${subject}`]: { account: { ...account, principal_id: subject, display_name: "المستخدم المحدد", status: "disabled", profile_complete: false, current_goal: null, last_activity_at: null, created_at: "2026-01-01T00:00:00Z" }, profile: null, current_target: null, plan_history: { items: [], next_cursor: null } },
    };
    if (url.pathname === "/profile") return route.fulfill({ status: 404, json: { detail: "لا يوجد ملف شخصي." } });
    if (url.pathname in responses) return route.fulfill({ status: 200, json: responses[url.pathname] });
    unexpected.push(`${request.method()} ${url.pathname}`);
    return route.fulfill({ status: 500, json: { detail: "Unexpected fixture endpoint" } });
  });
  return () => expect(unexpected, "All API traffic must be explicitly synthetic").toEqual([]);
}

async function shell(page: Page, title: RegExp) {
  await expect(page).toHaveTitle(title);
  await expect(page.getByRole("main")).toHaveCount(1);
  const skip = page.getByRole("link", { name: "انتقل إلى المحتوى الرئيسي" });
  await page.keyboard.press("Control+Home");
  await skip.focus();
  await expect(skip).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("main")).toBeFocused();
  await expect(page.getByRole("main")).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
}

for (const width of [320, 390, 768, 1440]) for (const colorScheme of ["light", "dark"] as const) {
  test(`fixture Labs keyboard and reflow ${width} ${colorScheme}`, async ({ page }, testInfo) => {
    const verify = await fixtures(page);
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ colorScheme, reducedMotion: "reduce" });
    await page.goto("/labs");
    await expect(page.getByRole("button", { name: "إضافة نتائج", exact: true })).toBeVisible();
    await shell(page, /التحاليل/);
    await page.getByRole("button", { name: "إضافة نتائج", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة نتائج", exact: true });
    await dialog.getByRole("button", { name: "التالي", exact: true }).click();
    await dialog.getByRole("searchbox").fill("HbA1c");
    await dialog.locator('[data-individual-key="hba1c"]').check();
    await dialog.getByRole("button", { name: "التالي", exact: true }).click();
    const value = dialog.locator("#lab-hba1c-value");
    await value.fill("٥٫٢٧٠٠");
    await dialog.getByRole("button", { name: "السابق", exact: true }).click();
    await dialog.getByRole("button", { name: "التالي", exact: true }).click();
    await expect(value).toHaveValue("٥٫٢٧٠٠");
    await page.keyboard.press("Escape");
    const discard = page.getByRole("alertdialog", { name: "تجاهل التغييرات؟" });
    await expect(discard.getByRole("button", { name: "متابعة التعديل" })).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(value).toHaveValue("٥٫٢٧٠٠");
    await expect(dialog.getByRole("button", { name: "حفظ النتائج" })).toBeInViewport();
    expect(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
    await dialog.getByRole("button", { name: "إلغاء", exact: true }).click();
    await discard.getByRole("button", { name: "تجاهل التغييرات", exact: true }).click();
    await expect(dialog).toBeHidden();
    await page.goto("/labs/hba1c");
    await expect(page.getByTestId("selected-lab-reading")).toBeVisible();
    const reading = await page.getByTestId("selected-lab-reading").innerText();
    await page.getByRole("combobox", { name: "مقياس الرسم", exact: true }).selectOption("results");
    await expect(page.getByTestId("selected-lab-reading")).toHaveText(reading, { useInnerText: true });
    await expect(page.getByRole("status").filter({ hasText: "المحور مكبّر" })).toBeVisible();
    await page.locator("summary").filter({ hasText: "تفاصيل القيم المرجعية" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.locator("[data-reference-zone]").first()).toBeVisible();
    await page.locator('[data-chart-point][tabindex="0"]').focus();
    await page.keyboard.press("Home");
    await expect(page.locator(`[data-chart-point="${results[1].id}"]`)).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(axe.violations).toEqual([]);
    await page.evaluate(() => window.scrollTo(0, 0));
    await testInfo.attach(`labs-${width}-${colorScheme}`, { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
    verify();
  });
}

test("fixture selected-user incomplete Labs remains read-only with clear filters", async ({ page }) => {
  const verify = await fixtures(page, { admin: true });
  await page.goto(`/admin/users/${subject}/labs`);
  await expect(page.getByText("ملف المستخدم غير مكتمل. التحاليل للقراءة فقط.")).toBeVisible();
  await expect(page.getByRole("link", { name: "إكمال الملف" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "إضافة نتائج" })).toHaveCount(0);
  await expect(page.getByText("عرض مستخدم آخر: المستخدم المحدد")).toBeVisible();
  await page.getByRole("button", { name: "التصنيف والترتيب" }).click();
  await page.getByRole("combobox", { name: "التصنيف", exact: true }).selectOption("iron");
  await page.getByRole("button", { name: "التصنيف والترتيب" }).click();
  await expect(page.locator("#labs-filter-summary")).toBeVisible();
  await page.getByRole("button", { name: "مسح البحث والتصفية" }).click();
  await expect(page.getByRole("searchbox")).toBeFocused();
  verify();
});

test("fixture empty Food and Profile pages keep a usable narrow shell", async ({ page }) => {
  const verify = await fixtures(page);
  await page.setViewportSize({ width: 320, height: 900 });
  for (const [path, title] of [["/foods", /الأطعمة/], ["/profile", /الملف الشخصي/]] as const) {
    await page.goto(path);
    await shell(page, title);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  }
  // CSS scaling is a desktop reflow probe only; this does not claim true browser 200% zoom.
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.evaluate(() => { document.documentElement.style.zoom = "2"; });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  verify();
});

test("fixture signed-out auth has a unique main and keyboard skip target", async ({ page }) => {
  const verify = await fixtures(page, { signedOut: true });
  await page.goto("/auth/login");
  await shell(page, /تسجيل الدخول/);
  await expect(page.getByRole("textbox").first()).toBeVisible();
  verify();
});


test("fixture Food catalog/detail preserves basis context across mobile and desktop", async ({ page }, testInfo) => {
  const verify = await fixtures(page, { populatedFood: true });
  for (const width of [320, 1440]) for (const colorScheme of ["light", "dark"] as const) {
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ colorScheme });
    await page.goto("/foods");
    await expect(page.getByRole("link", { name: `عرض تفاصيل ${food.name}`, exact: true }).first()).toBeVisible();
    await page.goto(`/foods/${food.id}`);
    await expect(page.getByRole("heading", { name: food.name, exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "إضافة إلى اليوميات", exact: true })).toBeVisible();
    const mode = page.getByRole("group", { name: "طريقة عرض القيم الغذائية" });
    await mode.getByRole("button", { name: "الحصة الافتراضية", exact: true }).focus();
    await page.keyboard.press("Tab");
    await page.keyboard.press("Enter");
    await expect(mode.getByRole("button").nth(1)).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("status").filter({ hasText: "القيم المعروضة:" })).toContainText("100");
    await testInfo.attach(`food-detail-${width}-${colorScheme}`, { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  verify();
});

test("fixture Food menu supports keyboard entry and numeric drafts preserve partial Arabic decimals", async ({ page }) => {
  const verify = await fixtures(page, { admin: true, populatedFood: true });
  await page.goto("/foods");
  const trigger = page.getByRole("button", { name: `إجراءات ${food.name}`, exact: true }).first();
  await trigger.focus();
  await page.keyboard.press("ArrowUp");
  await expect(page.getByRole("menuitem", { name: "حذف", exact: true })).toBeFocused();
  await page.keyboard.press("ArrowUp");
  await expect(page.getByRole("menuitem", { name: "تعديل", exact: true })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await page.goto("/foods/new");
  const calories = page.locator("#food-calories");
  await calories.fill("١٫");
  await page.keyboard.press("Tab");
  await expect(calories).toHaveValue("١٫");
  await calories.fill("۱٫۵");
  await page.keyboard.press("Tab");
  await expect(calories).toHaveValue("۱٫۵");
  verify();
});
