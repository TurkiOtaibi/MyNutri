import AxeBuilder from "@axe-core/playwright";
import { expect, test as base, type APIRequestContext, type Page, type Route } from "@playwright/test";

import type { CalendarAuthority } from "../../lib/api";
import type { ProfileInput, ProfileResponse, TargetResponse } from "../../lib/types";
import { API_TOKEN, API_URL } from "../foods/helpers";

const apiHeaders = () => ({ Authorization: `Bearer ${API_TOKEN}` });
const AUTH_URL = process.env.PLAYWRIGHT_SUPABASE_URL ?? "http://127.0.0.1:8765";
const API_ORIGIN = new URL(API_URL).origin;
const AUTH_ORIGIN = new URL(AUTH_URL).origin;
const ADMIN_EMAIL = "admin.e2e@example.test";
const ADMIN_PASSWORD = "E2e-only-password-2026!";
const LOCAL_TEST_PASSWORD = "Acceptance-only-password-2026!";
const SPECIALIST_REVIEW_REQUIRED =
  "لا يمكن تفعيل هذا الهدف لأنه غير مناسب لحالتك الحالية. إذا رغبت في اتباع هذا الهدف، فاستشر أخصائي تغذية قبل اعتماده.";
const VERY_LOW_ENERGY_TARGET_BLOCKED =
  "لا يمكن تفعيل هذا الهدف لأن السعرات المستهدفة منخفضة جدًا ولا تحقق الحد الأدنى الآمن المعتمد في النظام.";
const BLOCKED_PREVIEW_DESCRIPTION = "هذه معاينة توضيحية فقط، ولا يمكن تفعيل هذا الهدف.";
const profilePath = (url: URL) => url.origin === API_ORIGIN && url.pathname === "/profile";
const previewPath = (url: URL) => url.pathname === "/profile/preview";
const calendarPath = (url: URL) => url.pathname === "/account/calendar";
const activationPath = (url: URL) =>
  url.pathname === "/target-plans/activate" || url.pathname === "/target-plans/pending/replace";

if (!["127.0.0.1", "localhost"].includes(new URL(AUTH_URL).hostname)) {
  throw new Error(`Profile tests refuse non-local auth target ${AUTH_URL}`);
}

async function changedWeight(page: Page, originalProfile: ProfileResponse, offset = 1): Promise<string> {
  const nextWeight = String(originalProfile.weight_kg + offset);
  await page.getByLabel("الوزن").fill(nextWeight);
  return nextWeight;
}

async function fulfillPreview(
  route: Route,
  transform: (targets: TargetResponse) => TargetResponse
): Promise<void> {
  if (route.request().method() !== "POST") return route.continue();
  const response = await route.fetch();
  const targets = await response.json() as TargetResponse;
  await route.fulfill({ response, json: transform(targets) });
}

async function assertBlockedResponsiveAndAxe(page: Page, message: string): Promise<void> {
  const panel = page.locator(".profile-safety-decision").filter({ hasText: message });
  const reviewButton = page.getByRole("button", { name: "مراجعة وتأكيد" });

  for (const width of [320, 360, 390, 430]) {
    await page.setViewportSize({ width, height: 844 });
    await expect(panel).toBeVisible();
    await expect(panel.getByText(message, { exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);

    const panelBox = await panel.boundingBox();
    expect(panelBox).not.toBeNull();
    expect(panelBox!.x).toBeGreaterThanOrEqual(0);
    expect(panelBox!.x + panelBox!.width).toBeLessThanOrEqual(width + 1);

    const buttonBox = await reviewButton.boundingBox();
    expect(buttonBox).not.toBeNull();
    expect(buttonBox!.height).toBeGreaterThanOrEqual(44);
    expect(buttonBox!.x + buttonBox!.width).toBeLessThanOrEqual(width + 1);

    await panel.focus();
    await expect(panel).toBeFocused();
  }

  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations.filter((violation) => ["serious", "critical"].includes(violation.impact ?? ""))).toEqual([]);
}

function activationPlan(profile: ProfileResponse, targets: TargetResponse) {
  const existing = profile.pending_plan ?? profile.effective_plan;
  return existing
    ? { ...existing, targets }
    : {
        id: "00000000-0000-4000-8000-000000000005",
        status: "scheduled",
        effective_from: "2026-07-25",
        effective_to: null,
        calendar_timezone: "Asia/Riyadh",
        predecessor_plan_id: null,
        superseded_by_plan_id: null,
        targets,
        created_at: "2026-07-24T00:00:00Z",
        activated_at: "2026-07-24T00:00:00Z",
        closed_at: null,
        superseded_at: null
      };
}

function plan011ActivationPlan(profile: ProfileResponse, targets: TargetResponse) {
  return {
    ...activationPlan(profile, targets),
    id: "00000000-0000-4000-8000-000000000011",
    targets
  };
}

async function mockPlan011Preview(page: Page, originalProfile: ProfileResponse): Promise<TargetResponse> {
  const targets: TargetResponse = {
    ...originalProfile.targets,
    calories: 1777,
    target_calories: 1777,
    final_target_calories: 1777,
    preview_hash: "plan011-preview-hash",
    can_activate: true,
    safety_outcome: "normal"
  };
  await page.route(previewPath, (route) => route.request().method() === "POST"
    ? route.fulfill({ status: 200, contentType: "application/json", json: targets })
    : route.continue());
  return targets;
}

function inputFrom(profile: ProfileResponse): ProfileInput {
  return {
    sex: profile.sex,
    birth_date: profile.birth_date,
    height_cm: profile.height_cm,
    weight_kg: profile.weight_kg,
    activity_level: profile.activity_level,
    goal: profile.goal,
    protein_per_kg: profile.protein_per_kg,
    fat_pct: profile.fat_pct,
    selected_cut_intensity: profile.selected_cut_intensity
  };
}

async function readProfile(request: APIRequestContext): Promise<ProfileResponse> {
  const response = await request.get(`${API_URL}/profile`, { headers: apiHeaders() });
  expect(response.status()).toBe(200);
  return response.json() as Promise<ProfileResponse>;
}

const test = base.extend<{ originalProfile: ProfileResponse }>({
  originalProfile: async ({ request }, use) => {
    const original = await readProfile(request);
    await use(original);
    await request.put(`${API_URL}/profile`, { headers: apiHeaders(), data: inputFrom(original) });
  }
});

test.describe("@profile Profile and targets redesign", () => {
  test("@p0 renders approved structure without technical header copy", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/profile");
    await expect(page.getByRole("heading", { name: "بياناتك وأهدافك" })).toBeVisible();
    await expect(page.getByText("حدّث بياناتك لنحسب احتياجك اليومي.")).toBeVisible();
    await expect(page.getByText(/الخادم|server/i)).toHaveCount(0);
    await expect(page.locator(".profile-page-head").getByText(/Mifflin/i)).toHaveCount(0);
    const body = page.getByRole("region", { name: "بيانات الجسم" });
    await expect(body).toBeVisible();
    for (const label of ["الجنس", "تاريخ الميلاد", "الطول", "الوزن"]) await expect(body.getByText(label, { exact: true })).toBeVisible();
    await expect(body.getByText("مستوى النشاط")).toHaveCount(0);
    await expect(body.getByText("الهدف", { exact: true })).toHaveCount(0);
    await expect(page.locator(".profile-selection-card")).toHaveCount(2);
  });

  test("@p0 sex sheet is accessible and changes draft without persistence", async ({ page, request, originalProfile }) => {
    await page.goto("/profile");
    const currentLabel = originalProfile.sex === "male" ? "ذكر" : "أنثى";
    const nextLabel = originalProfile.sex === "male" ? "أنثى" : "ذكر";
    await page.getByRole("button", { name: new RegExp(`تغيير الجنس، القيمة الحالية ${currentLabel}`) }).click();
    const sheet = page.getByRole("dialog", { name: "اختر الجنس" });
    await expect(sheet).toBeVisible();
    await expect(sheet.getByRole("radio", { name: currentLabel })).toHaveAttribute("aria-checked", "true");
    await sheet.getByRole("radio", { name: nextLabel }).click();
    await expect(page.getByRole("button", { name: new RegExp(`القيمة الحالية ${nextLabel}`) })).toBeVisible();
    await expect(page.getByText("تغييرات غير محفوظة")).toBeVisible();
    expect((await readProfile(request)).sex).toBe(originalProfile.sex);
  });

  test("@p0 birth date is Gregorian Arabic with Western numerals and numeric units are stable", async ({ page, originalProfile }) => {
    await page.goto("/profile");
    const body = page.getByRole("region", { name: "بيانات الجسم" });
    await expect(body).toContainText(/\d{1,2} [\u0600-\u06FF]+ \d{4}/);
    await expect(body).not.toContainText(/[٠-٩]/);
    const height = page.getByLabel("الطول");
    const weight = page.getByLabel("الوزن");
    await expect(height).toHaveAttribute("inputmode", "decimal");
    await expect(weight).toHaveAttribute("inputmode", "decimal");
    await expect(height).toHaveValue(String(originalProfile.height_cm));
    await expect(weight).toHaveValue(String(originalProfile.weight_kg));
    await expect(body.getByText("سم", { exact: true })).toBeVisible();
    await expect(body.getByText("كجم", { exact: true })).toBeVisible();
  });

  test("@p0 activity and goal sheets expose exact backend choices and remain draft-only", async ({ page, request, originalProfile }) => {
    await page.goto("/profile");
    await page.getByRole("button", { name: /تغيير مستوى النشاط/ }).click();
    const activity = page.getByRole("dialog", { name: "اختر مستوى النشاط" });
    await expect(activity.getByRole("radio")).toHaveCount(5);
    await expect(activity).toContainText("خامل");
    await expect(activity).toContainText("نشاط خفيف");
    await expect(activity).toContainText("نشاط متوسط");
    await expect(activity).toContainText("نشاط مرتفع جدًا");
    await activity.getByRole("radio", { name: /نشاط خفيف/ }).click();
    await page.getByRole("button", { name: /تغيير الهدف/ }).click();
    const goal = page.getByRole("dialog", { name: "اختر هدفك" });
    for (const label of ["تنشيف", "المحافظة", "زيادة الوزن"]) await expect(goal.getByRole("radio", { name: new RegExp(label) })).toBeVisible();
    await goal.getByRole("radio", { name: /المحافظة/ }).click();
    const persisted = await readProfile(request);
    expect(persisted.activity_level).toBe(originalProfile.activity_level);
    expect(persisted.goal).toBe(originalProfile.goal);
  });

  test("@p0 advanced options preserve ratio semantics and restore defaults as unsaved draft", async ({ page, originalProfile }) => {
    await page.goto("/profile");
    const toggle = page.getByRole("button", { name: "فتح الخيارات المتقدمة" });
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await toggle.click();
    await expect(page.getByLabel("البروتين لكل كجم")).toHaveValue(String(originalProfile.protein_per_kg));
    await expect(page.getByLabel("نسبة الدهون")).toHaveValue(String(originalProfile.fat_pct * 100));
    await expect(page.getByText("جم/كجم", { exact: true })).toBeVisible();
    await expect(page.getByText("%", { exact: true })).toBeVisible();
    await page.getByLabel("البروتين لكل كجم").fill("2.1");
    await page.getByLabel("نسبة الدهون").fill("28");
    await page.getByRole("button", { name: "استعادة القيم الافتراضية" }).click();
    const confirm = page.getByRole("dialog", { name: "استعادة القيم الافتراضية؟" });
    await confirm.getByRole("button", { name: "استعادة القيم", exact: true }).click();
    await expect(page.getByLabel("البروتين لكل كجم")).toHaveValue("1.2");
    await expect(page.getByLabel("نسبة الدهون")).toHaveValue(originalProfile.sex === "female" ? "30" : "25");
    const originalUsesDefaults = originalProfile.protein_per_kg === 1.2 && originalProfile.fat_pct === (originalProfile.sex === "female" ? 0.3 : 0.25);
    if (originalUsesDefaults) await expect(page.locator(".profile-save-bar")).toHaveCount(0);
    else await expect(page.getByText("تغييرات غير محفوظة")).toBeVisible();
  });

  test("@p0 dirty state normalizes values, validates fields, and blocks invalid saves", async ({ page, originalProfile }) => {
    const profileResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return profilePath(url)
        && response.request().method() === "GET"
        && response.request().resourceType() === "fetch";
    });
    const calendarResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.origin === API_ORIGIN
        && calendarPath(url)
        && response.request().method() === "GET"
        && response.request().resourceType() === "fetch";
    });
    await page.goto("/profile");
    const [profileResult, calendarResult] = await Promise.all([
      profileResponse,
      calendarResponse
    ]);
    expect(profileResult.status()).toBe(200);
    expect(calendarResult.status()).toBe(200);
    const profileBody = await profileResult.json() as ProfileResponse;
    expect(profileBody.weight_kg).toBe(originalProfile.weight_kg);
    const calendarBody = await calendarResult.json() as CalendarAuthority;
    expect(calendarBody).toEqual(expect.objectContaining({
      current_diary_date: expect.any(String),
      calendar_timezone: expect.any(String),
      next_rollover_at: expect.any(String)
    }));
    const weight = page.getByLabel("الوزن");
    await expect(page.locator(".profile-card-skeleton")).toHaveCount(0);
    await expect(weight).toHaveValue(String(originalProfile.weight_kg));
    const original = await weight.inputValue();
    await weight.fill(`${Number(original).toFixed(1)}`);
    await expect(page.locator(".profile-save-bar")).toHaveCount(0);
    await weight.fill("0");
    await expect(page.locator(".profile-save-bar")).toBeVisible();
    let activations = 0;
    await page.route("**/target-plans/**", async (route) => {
      if (route.request().method() === "POST") activations += 1;
      await route.continue();
    });
    await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
    await expect(page.getByText("أدخل وزنًا صحيحًا")).toBeVisible();
    await expect(weight).toBeFocused();
    expect(activations).toBe(0);
    await weight.fill(original);
    await expect(page.locator(".profile-save-bar")).toHaveCount(0);
  });

  test("@plan008 authoritative calendar bounds the birth date and Backend 422 preserves the draft", async ({ browser }) => {
    const context = await browser.newContext({
      baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000",
      storageState: "e2e/.auth/admin.json",
      locale: "ar-SA",
      timezoneId: "Pacific/Honolulu",
      serviceWorkers: "block"
    });
    const page = await context.newPage();
    let previewRequests = 0;
    await page.route(calendarPath, (route) => route.fulfill({
      status: 200,
      contentType: "application/json",
      json: {
        current_diary_date: "2030-01-02",
        calendar_timezone: "Asia/Riyadh",
        next_rollover_at: "2030-01-03T00:00:00+03:00"
      }
    }));
    await page.route(previewPath, async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      previewRequests += 1;
      await route.fulfill({
        status: 422,
        contentType: "application/json",
        json: {
          detail: [{
            type: "profile_age_below_minimum",
            loc: ["body", "birth_date"],
            msg: "Age must be at least 10 on the authoritative effective date.",
            input: "2021-01-01"
          }]
        }
      });
    });

    try {
      await page.goto("/profile?plan008-calendar=1");
      const birthDate = page.getByLabel("تاريخ الميلاد");
      await expect(birthDate).toHaveAttribute("max", "2030-01-02");

      await birthDate.fill("2030-01-03");
      await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
      await expect(birthDate).toHaveAttribute("aria-invalid", "true");
      expect(previewRequests).toBe(0);

      await birthDate.fill("2021-01-01");
      await expect.poll(() => previewRequests).toBe(1);
      await expect(birthDate).toHaveValue("2021-01-01");
      await expect(birthDate).toHaveAttribute("aria-invalid", "true");
      await expect(page.getByText("اختر تاريخ ميلاد صحيحًا")).toBeVisible();
    } finally {
      await context.close();
    }
  });

  test("@plan008 numeric guidance enforces exact practical boundaries", async ({ page, originalProfile }) => {
    let previewRequests = 0;
    await page.route(previewPath, async (route) => {
      if (route.request().method() === "POST") previewRequests += 1;
      await route.continue();
    });
    await page.goto("/profile?plan008-numeric-bounds=1");
    const height = page.getByLabel("الطول");
    const weight = page.getByLabel("الوزن");
    await expect(height).toHaveAttribute("min", "100");
    await expect(height).toHaveAttribute("max", "250");
    await expect(weight).toHaveAttribute("min", "20");
    await expect(weight).toHaveAttribute("max", "300");

    for (const scenario of [
      { input: height, invalid: "99.9", boundary: "100", original: String(originalProfile.height_cm) },
      { input: height, invalid: "250.1", boundary: "250", original: String(originalProfile.height_cm) },
      { input: weight, invalid: "19.9", boundary: "20", original: String(originalProfile.weight_kg) },
      { input: weight, invalid: "300.1", boundary: "300", original: String(originalProfile.weight_kg) }
    ]) {
      await scenario.input.fill(scenario.invalid);
      await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
      await expect(scenario.input).toHaveAttribute("aria-invalid", "true");
      const before = previewRequests;
      await scenario.input.fill(scenario.boundary);
      await expect.poll(() => previewRequests).toBeGreaterThan(before);
      await scenario.input.fill(scenario.original);
    }

    await page.getByRole("button", { name: /فتح الخيارات المتقدمة/ }).click();
    const protein = page.getByLabel("البروتين لكل كجم");
    const fat = page.getByLabel("نسبة الدهون");
    await expect(protein).toHaveAttribute("min", "1");
    await expect(protein).toHaveAttribute("max", "3");
    await expect(fat).toHaveAttribute("min", "15");
    await expect(fat).toHaveAttribute("max", "40");

    await height.fill("100");
    await weight.fill("300");
    await protein.fill("3");
    await fat.fill("15");
    const preview = page.getByRole("region", { name: "الأهداف المتوقعة بعد الحفظ" });
    await expect(preview).toBeVisible();
    await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
    const confirmation = page.getByRole("dialog", { name: /تأكيد الأهداف الجديدة|استبدال الخطة المجدولة/ });
    await confirmation.getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).click();
    await expect(page.getByText("تم حفظ التغييرات")).toBeVisible();
    await expect(height).toHaveValue("100");
    await expect(weight).toHaveValue("300");
    await expect(protein).toHaveValue("3");
    await expect(fat).toHaveValue("15");

    const stored = await readProfile(page.request);
    expect(stored.height_cm).toBe(100);
    expect(stored.weight_kg).toBe(300);
    expect(stored.protein_per_kg).toBe(3);
    expect(stored.fat_pct).toBe(0.15);
  });

  test("@p0 @plan011 @plan016 successful activation adopts the accepted response and clears navigation guard", async ({ page, originalProfile }) => {
    await page.goto("/profile");
    const nextWeight = originalProfile.weight_kg + 1;
    let previewRequests = 0;
    let activationRequests = 0;
    await page.route("**/profile/preview", async (route) => { previewRequests += 1; await route.continue(); });
    await page.route("**/target-plans/**", async (route) => { if (route.request().method() === "POST") activationRequests += 1; await route.continue(); });
    await page.getByLabel("الوزن").fill(String(nextWeight));
    const preview = page.getByRole("region", { name: "الأهداف المتوقعة بعد الحفظ" });
    await expect(preview).toBeVisible();
    await expect(preview.getByText("معاينة", { exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: "الأهداف اليومية" })).toBeVisible();
    await expect.poll(() => previewRequests).toBe(1);
    const save = page.getByRole("button", { name: "مراجعة وتأكيد" });
    await save.click();
    const confirmation = page.getByRole("dialog", { name: /تأكيد الأهداف الجديدة|استبدال الخطة المجدولة/ });
    await confirmation.getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).evaluate((element) => {
      const button = element as HTMLButtonElement;
      button.click();
      button.click();
    });
    await expect(page.getByText("تم حفظ التغييرات")).toBeVisible();
    expect(activationRequests).toBe(1);
    await expect(page.locator(".profile-save-bar")).toHaveCount(0);
    await expect(preview).toHaveCount(0);
    await page.getByRole("link", { name: "اليوميات" }).click();
    await expect(page.getByRole("dialog", { name: "تغييرات غير محفوظة" })).toHaveCount(0);
    await expect(page).toHaveURL(/\/diary$/);
  });

  test("@plan011 @plan016 pending activation keeps its draft and guard until acceptance", async ({ page, originalProfile }) => {
    const targets = await mockPlan011Preview(page, originalProfile);
    let activationRequests = 0;
    let releaseActivation!: () => void;
    const activationGate = new Promise<void>((resolve) => { releaseActivation = resolve; });
    await page.route(activationPath, async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      activationRequests += 1;
      await activationGate;
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        json: { plan: plan011ActivationPlan(originalProfile, targets), replaced_plan: null }
      });
    });

    await page.goto("/profile?plan011-pending=1");
    const heldDraft = await changedWeight(page, originalProfile);
    await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
    const dialog = page.getByRole("dialog", { name: /تأكيد الأهداف الجديدة|استبدال الخطة المجدولة/ });
    const confirm = dialog.getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ });
    await confirm.evaluate((element) => {
      const button = element as HTMLButtonElement;
      button.click();
      button.click();
    });
    await expect.poll(() => activationRequests).toBe(1);
    await expect(dialog).toHaveAttribute("aria-busy", "true");
    await expect(dialog).toBeFocused();
    await expect(dialog.getByRole("button", { name: /إغلاق/ })).toBeDisabled();
    await expect(dialog.getByRole("button", { name: "متابعة المراجعة" })).toBeDisabled();
    let profileRefetches = 0;
    await page.route(profilePath, async (route) => {
      if (route.request().method() !== "GET") return route.continue();
      profileRefetches += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        json: { ...originalProfile, weight_kg: originalProfile.weight_kg + 9 }
      });
    });
    const refetched = page.waitForResponse((response) =>
      new URL(response.url()).origin === API_ORIGIN
        && profilePath(new URL(response.url()))
        && response.request().method() === "GET"
    );
    await page.clock.install({ time: new Date() });
    await page.clock.fastForward(20_001);
    await page.context().setOffline(true);
    await page.context().setOffline(false);
    await refetched;
    expect(profileRefetches).toBe(1);
    await expect(page.getByLabel("الوزن")).toHaveValue(heldDraft);
    await expect(page.getByText("توجد نسخة أحدث من بيانات الملف على الخادم. احتفظنا بتعديلاتك الحالية.")).toBeVisible();
    await page.getByRole("link", { name: "اليوميات" }).dispatchEvent("click");
    const unsaved = page.getByRole("dialog", { name: "تغييرات غير محفوظة" });
    await expect(unsaved).toBeVisible();
    await unsaved.getByRole("button", { name: "متابعة التعديل" }).click();
    await expect(page).toHaveURL(/\/profile\?plan011-pending=1$/);
    await expect(page.getByLabel("الوزن")).toHaveValue(heldDraft);
    await page.keyboard.press("Escape");
    await page.locator(".profile-sheet-backdrop").dispatchEvent("mousedown");
    await expect(dialog).toBeVisible();
    expect(activationRequests).toBe(1);

    await page.unroute(profilePath);
    releaseActivation();
    await expect(dialog).toHaveCount(0);
    await expect(page.getByText("تم حفظ التغييرات")).toBeVisible();
  });

  for (const reconciliation of ["error", "empty", "stale"] as const) {
    test(`@plan011 accepted activation survives ${reconciliation} Profile reconciliation`, async ({ page, originalProfile }) => {
      const targets = await mockPlan011Preview(page, originalProfile);
      const acceptedPlan = plan011ActivationPlan(originalProfile, targets);
      let accepted = false;
      let allowFresh = false;
      let acceptedPayload: ProfileInput | null = null;
      let activationRequests = 0;
      await page.route(profilePath, (route) => {
        if (route.request().method() !== "GET" || route.request().resourceType() !== "fetch") return route.continue();
        if (!accepted) {
          return route.fulfill({ status: 200, contentType: "application/json", json: originalProfile });
        }
        if (allowFresh) {
          return route.fulfill({
            status: 200,
            contentType: "application/json",
            json: {
              ...originalProfile,
              ...acceptedPayload,
              targets,
              pending_plan: acceptedPlan
            }
          });
        }
        if (reconciliation === "error") {
          return route.fulfill({ status: 500, contentType: "application/json", json: { detail: "unavailable" } });
        }
        if (reconciliation === "empty") {
          return route.fulfill({ status: 404, contentType: "application/json", json: { detail: "not found" } });
        }
        return route.fulfill({ status: 200, contentType: "application/json", json: originalProfile });
      });
      await page.route(activationPath, async (route) => {
        if (route.request().method() !== "POST") return route.continue();
        activationRequests += 1;
        acceptedPayload = route.request().postDataJSON() as ProfileInput;
        accepted = true;
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          json: { plan: acceptedPlan, replaced_plan: null }
        });
      });

      await page.goto(`/profile?plan011-reconciliation=${reconciliation}`);
      const acceptedWeight = await changedWeight(page, originalProfile);
      await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
      await page.getByRole("dialog").getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).click();

      const recovery = page.getByRole("status").filter({ hasText: "تعذر تحديث البيانات المعروضة" });
      await expect(recovery).toBeVisible();
      await expect(recovery.getByRole("button", { name: "إعادة تحديث البيانات" })).toBeEnabled();
      await expect(page.getByLabel("الوزن")).toHaveValue(acceptedWeight);
      await expect(page.getByLabel("الوزن")).toBeEnabled();
      await expect(page.getByRole("region", { name: "الأهداف اليومية" })).toContainText("1777");
      await expect(page.locator(".profile-save-bar")).toHaveCount(0);
      expect(activationRequests).toBe(1);
      if (reconciliation === "stale") {
        allowFresh = true;
        await recovery.getByRole("button", { name: "إعادة تحديث البيانات" }).click();
        await expect(recovery).toHaveCount(0);
        await expect(page.getByText("تم حفظ التغييرات")).toBeVisible();
        expect(activationRequests).toBe(1);
      }
    });
  }

  test("@plan011 first Profile activation retains accepted truth when reconciliation is empty", async ({ page, originalProfile }) => {
    const targets = await mockPlan011Preview(page, originalProfile);
    const acceptedPlan = plan011ActivationPlan(originalProfile, targets);
    let activationRequests = 0;
    await page.route(profilePath, (route) =>
      route.request().method() === "GET" && route.request().resourceType() === "fetch"
        ? route.fulfill({ status: 404, contentType: "application/json", json: { detail: "not found" } })
        : route.continue()
    );
    await page.route(activationPath, async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      activationRequests += 1;
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        json: { plan: acceptedPlan, replaced_plan: null }
      });
    });

    await page.goto("/profile?plan011-first-profile=1");
    await page.getByLabel("تاريخ الميلاد").fill("1990-01-01");
    await page.getByLabel("الطول").fill("170");
    await page.getByLabel("الوزن").fill("70");
    await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
    await page.getByRole("dialog").getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).click();

    await expect(page.getByRole("status").filter({ hasText: "تعذر تحديث البيانات المعروضة" })).toBeVisible();
    await expect(page.getByLabel("الوزن")).toHaveValue("70");
    await expect(page.getByRole("region", { name: "الأهداف اليومية" })).toContainText("1777");
    expect(activationRequests).toBe(1);
  });

  test("@p0 cut intensity survives edits and activation payloads", async ({ page, originalProfile }) => {
    let currentProfile = structuredClone(originalProfile);
    let expectedIntensity: 0.15 | 0.25 = 0.15;
    let latestTargets = originalProfile.targets;
    const previewPayloads: ProfileInput[] = [];
    const activationPayloads: Array<ProfileInput & { expected_preview_hash: string }> = [];

    await page.route(profilePath, (route) =>
      route.request().method() === "GET" && route.request().resourceType() === "fetch"
        ? route.fulfill({ status: 200, contentType: "application/json", json: currentProfile })
        : route.continue()
    );
    await page.route(previewPath, async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      const payload = route.request().postDataJSON() as ProfileInput;
      previewPayloads.push(payload);
      expect(payload.selected_cut_intensity).toBe(expectedIntensity);
      await fulfillPreview(route, (targets) => {
        latestTargets = { ...targets, selected_cut_intensity: expectedIntensity };
        return latestTargets;
      });
    });
    await page.route(activationPath, async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      const payload = route.request().postDataJSON() as ProfileInput & { expected_preview_hash: string };
      activationPayloads.push(payload);
      expect(payload.selected_cut_intensity).toBe(expectedIntensity);
      currentProfile = {
        ...currentProfile,
        ...payload,
        selected_cut_intensity: expectedIntensity,
        targets: latestTargets
      };
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        json: { plan: activationPlan(currentProfile, latestTargets), replaced_plan: null }
      });
    });

    for (const [index, intensity] of ([0.15, 0.25] as const).entries()) {
      await test.step(`preserves ${intensity}`, async () => {
        expectedIntensity = intensity;
        currentProfile = {
          ...currentProfile,
          goal: "cut",
          selected_cut_intensity: intensity,
          targets: { ...currentProfile.targets, selected_cut_intensity: intensity }
        };
        await page.goto(`/profile?cut-payload=${index}`);
        const cutGroup = page.getByRole("radiogroup", { name: "شدة خفض الوزن" });
        await expect(cutGroup).toBeVisible();
        const checkedIntensity = cutGroup.getByRole("radio", { checked: true });
        await expect(checkedIntensity).toBeChecked();
        await expect(checkedIntensity).toHaveAccessibleName(new RegExp(`${intensity * 100}%`));
        await changedWeight(page, currentProfile, index + 1);
        await expect.poll(() => previewPayloads.length).toBe(index + 1);
        await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
        const confirmation = page.getByRole("dialog", { name: /تأكيد الأهداف الجديدة|استبدال الخطة المجدولة/ });
        await confirmation.getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).click();
        await expect.poll(() => activationPayloads.length).toBe(index + 1);
        await expect(page.getByText("تم حفظ التغييرات")).toBeVisible();
        expect(currentProfile.selected_cut_intensity).toBe(intensity);
      });
    }
  });

  test("@p0 cut preference defaults and survives non-cut goals", async ({ browser }) => {
    const context = await browser.newContext({ storageState: undefined });
    const page = await context.newPage();
    const previewPayloads: ProfileInput[] = [];
    const activationPayloads: ProfileInput[] = [];
    await page.route(previewPath, (route) => {
      if (route.request().method() !== "POST") return route.continue();
      const previewPayload = route.request().postDataJSON() as ProfileInput;
      previewPayloads.push(previewPayload);
      return route.continue();
    });
    await page.route(activationPath, (route) => {
      if (route.request().method() !== "POST") return route.continue();
      const activationPayload = route.request().postDataJSON() as ProfileInput;
      activationPayloads.push(activationPayload);
      return route.continue();
    });

    try {
      const email = `profile-cut-${Date.now()}-${test.info().parallelIndex}@example.test`;
      await page.goto("/auth/login");
      await page.locator('input[type="email"]').fill(email);
      await page.locator('input[type="password"]').fill(LOCAL_TEST_PASSWORD);
      await page.locator('button[type="submit"]').click();
      await page.waitForURL(/\/diary$/);
      await page.goto("/profile?blank-cut-preference=1");
      const cutGroup = page.getByRole("radiogroup", { name: "شدة خفض الوزن" });
      const recommended = cutGroup.getByRole("radio", { name: /عادي.*20%.*موصى به/ });
      await expect(recommended).toBeChecked();
      await page.getByLabel("تاريخ الميلاد").fill("1990-01-01");
      await page.getByLabel("الطول").fill("170");
      await page.getByLabel("الوزن").fill("70");
      const light = cutGroup.getByRole("radio", { name: /خفيف.*15%/ });
      await recommended.focus();
      await page.keyboard.press("ArrowUp");
      await expect(light).toBeChecked();
      await page.keyboard.press("Tab");
      await expect(light).not.toBeFocused();

      for (const width of [320, 360, 390, 430]) {
        await page.setViewportSize({ width, height: 844 });
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
        const choices = page.getByRole("radiogroup", { name: "شدة خفض الوزن" }).getByRole("radio");
        await expect(choices).toHaveCount(3);
        for (const choice of await choices.all()) expect((await choice.boundingBox())!.height).toBeGreaterThanOrEqual(44);
      }
      const accessibility = await new AxeBuilder({ page }).analyze();
      expect(accessibility.violations.filter((violation) => ["serious", "critical"].includes(violation.impact ?? ""))).toEqual([]);

      await page.getByRole("button", { name: /تغيير الهدف/ }).click();
      await page.getByRole("dialog", { name: "اختر هدفك" }).getByRole("radio", { name: /المحافظة/ }).click();
      await expect(cutGroup).toHaveCount(0);
      await expect.poll(() => previewPayloads.at(-1)?.goal).toBe("maintain");
      expect(previewPayloads.at(-1)?.selected_cut_intensity).toBe(0.15);

      await page.getByRole("button", { name: /تغيير الهدف/ }).click();
      await page.getByRole("dialog", { name: "اختر هدفك" }).getByRole("radio", { name: /تنشيف/ }).click();
      await expect(page.getByRole("radiogroup", { name: "شدة خفض الوزن" }).getByRole("radio", { name: /خفيف.*15%/ }))
        .toBeChecked();

      await page.getByRole("button", { name: /تغيير الهدف/ }).click();
      await page.getByRole("dialog", { name: "اختر هدفك" }).getByRole("radio", { name: /المحافظة/ }).click();
      await expect.poll(() => previewPayloads.at(-1)?.goal).toBe("maintain");
      await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
      await page.getByRole("dialog", { name: /تأكيد الأهداف الجديدة/ })
        .getByRole("button", { name: "تفعيل الخطة" }).click();
      await expect.poll(() => activationPayloads.at(-1)?.goal).toBe("maintain");
      expect(activationPayloads.at(-1)?.selected_cut_intensity).toBe(0.15);
      await expect(page.getByText("تم حفظ التغييرات")).toBeVisible();
    } finally {
      await context.close();
    }
  });

  test("@p0 specialist review preview blocks activation", async ({ page, originalProfile }) => {
    let boundary = 800;
    let activationPosts = 0;
    await page.route(previewPath, (route) => fulfillPreview(route, (targets) => ({
      ...targets,
      calories: boundary,
      target_calories: boundary,
      final_target_calories: boundary,
      safety_outcome: "specialist_review_required",
      can_activate: false
    })));
    await page.route(activationPath, async (route) => {
      if (route.request().method() === "POST") activationPosts += 1;
      await route.continue();
    });
    await page.goto("/profile?specialist-boundaries=1");

    for (const [index, calories] of [800, 1200].entries()) {
      boundary = calories;
      await changedWeight(page, originalProfile, index + 1);
      const preview = page.getByRole("region", { name: "الأهداف المتوقعة بعد الحفظ" });
      await expect(preview.getByText(SPECIALIST_REVIEW_REQUIRED, { exact: true })).toBeVisible();
      await expect(preview).toContainText(String(calories));
      await expect(preview.getByText(BLOCKED_PREVIEW_DESCRIPTION, { exact: true })).toBeVisible();
      const passiveExplanation = preview.locator(".profile-safety-decision").filter({ hasText: SPECIALIST_REVIEW_REQUIRED });
      await expect(passiveExplanation).not.toHaveAttribute("role", "alert");
      await expect(passiveExplanation).not.toHaveAttribute("aria-live", "assertive");
      await expect(preview.getByRole("alert").filter({ hasText: SPECIALIST_REVIEW_REQUIRED })).toHaveCount(0);

      const reviewButton = page.getByRole("button", { name: "مراجعة وتأكيد" });
      await reviewButton.click();
      let explanation = preview.getByRole("alert").filter({ hasText: SPECIALIST_REVIEW_REQUIRED });
      await expect(explanation.getByText(SPECIALIST_REVIEW_REQUIRED, { exact: true })).toBeVisible();
      await expect(explanation).toHaveAttribute("aria-live", "assertive");
      await expect(explanation).toBeFocused();
      await expect(page.getByRole("dialog", { name: /تأكيد الأهداف الجديدة|استبدال الخطة المجدولة/ })).toHaveCount(0);
      expect(activationPosts).toBe(0);

      if (index === 0) {
        await reviewButton.focus();
        await reviewButton.click();
        explanation = preview.getByRole("alert").filter({ hasText: SPECIALIST_REVIEW_REQUIRED });
        await expect(explanation).toBeFocused();
        await expect(page.getByRole("dialog", { name: /تأكيد الأهداف الجديدة|استبدال الخطة المجدولة/ })).toHaveCount(0);
        expect(activationPosts).toBe(0);
        await assertBlockedResponsiveAndAxe(page, SPECIALIST_REVIEW_REQUIRED);
      }
    }
  });

  test("@p0 very low energy preview blocks activation", async ({ page, originalProfile }) => {
    let activationPosts = 0;
    await page.route(previewPath, (route) => fulfillPreview(route, (targets) => ({
      ...targets,
      calories: 799,
      target_calories: 799,
      final_target_calories: 799,
      safety_outcome: "very_low_energy_blocked",
      can_activate: false
    })));
    await page.route(activationPath, async (route) => {
      if (route.request().method() === "POST") activationPosts += 1;
      await route.continue();
    });
    await page.goto("/profile?very-low-boundary=799");
    await changedWeight(page, originalProfile);
    const preview = page.getByRole("region", { name: "الأهداف المتوقعة بعد الحفظ" });
    await expect(preview.getByText(VERY_LOW_ENERGY_TARGET_BLOCKED, { exact: true })).toBeVisible();
    await expect(preview).toContainText("799");
    await expect(preview.getByText(BLOCKED_PREVIEW_DESCRIPTION, { exact: true })).toBeVisible();
    const passiveExplanation = preview.locator(".profile-safety-decision").filter({ hasText: VERY_LOW_ENERGY_TARGET_BLOCKED });
    await expect(passiveExplanation).not.toHaveAttribute("role", "alert");
    await expect(passiveExplanation).not.toHaveAttribute("aria-live", "assertive");
    await expect(preview.getByRole("alert").filter({ hasText: VERY_LOW_ENERGY_TARGET_BLOCKED })).toHaveCount(0);
    await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
    const explanation = preview.getByRole("alert").filter({ hasText: VERY_LOW_ENERGY_TARGET_BLOCKED });
    await expect(explanation.getByText(VERY_LOW_ENERGY_TARGET_BLOCKED, { exact: true })).toBeVisible();
    await expect(explanation).toHaveAttribute("aria-live", "assertive");
    await expect(explanation).toBeFocused();
    await expect(page.getByRole("dialog", { name: /تأكيد الأهداف الجديدة|استبدال الخطة المجدولة/ })).toHaveCount(0);
    expect(activationPosts).toBe(0);
    await assertBlockedResponsiveAndAxe(page, VERY_LOW_ENERGY_TARGET_BLOCKED);
  });

  test("@p0 preview discloses cap and server calculation warnings", async ({ page, originalProfile }) => {
    let adjustedBasis = true;
    let activationPosts = 0;
    let latestTargets = originalProfile.targets;
    await page.route(previewPath, (route) => fulfillPreview(route, (targets) => {
      latestTargets = {
        ...targets,
        calories: 1201,
        target_calories: 1201,
        final_target_calories: 1201,
        requested_deficit_kcal: 900,
        applied_deficit_kcal: 750,
        deficit_cap_applied: true,
        safety_outcome: "normal",
        can_activate: true,
        calculation_warnings: [{
          code: "CARBOHYDRATE_BELOW_GENERAL_REFERENCE",
          severity: "warning",
          dimension: "carbohydrate",
          value: 91.5,
          reference_value: 130,
          message_ar: "رسالة تحذير سلطوية من الخادم"
        }],
        protein_calculation: adjustedBasis
          ? {
              ...targets.protein_calculation,
              basis: "adjusted_weight",
              bmi_used: 31.25,
              actual_weight_kg: 100,
              reference_weight_kg: 80,
              calculation_weight_kg: 86.6,
              protein_per_kg: 1.2,
              target_g: 103.9,
              explanation_ar: "حُسب البروتين باستخدام وزن مرجعي معدل.",
              reference_weight_label_ar: "وزن مرجعي للحساب"
            }
          : {
              ...targets.protein_calculation,
              basis: "actual_weight",
              bmi_used: 24.5,
              actual_weight_kg: 70,
              reference_weight_kg: null,
              calculation_weight_kg: 70,
              protein_per_kg: 1.2,
              target_g: 84,
              explanation_ar: "حُسب البروتين باستخدام الوزن الفعلي.",
              reference_weight_label_ar: "وزن مرجعي للحساب"
            }
      };
      return latestTargets;
    }));
    await page.route(activationPath, async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      activationPosts += 1;
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        json: { plan: activationPlan(originalProfile, latestTargets), replaced_plan: null }
      });
    });
    await page.goto("/profile?authoritative-disclosures=1");
    await changedWeight(page, originalProfile);
    const preview = page.getByRole("region", { name: "الأهداف المتوقعة بعد الحفظ" });
    await expect(preview).toContainText("1201");
    await expect(preview).toContainText("900");
    await expect(preview).toContainText("750");
    await expect(preview).toContainText("رسالة تحذير سلطوية من الخادم");
    await expect(preview).toContainText("91.5");
    await expect(preview).toContainText("130");
    await expect(preview).toContainText("حُسب البروتين باستخدام وزن مرجعي معدل.");
    await expect(preview).toContainText("وزن مرجعي للحساب");
    for (const value of ["31.3", "100", "80", "86.6", "1.2", "103.9"]) await expect(preview).toContainText(value);
    adjustedBasis = false;
    await changedWeight(page, originalProfile, 2);
    await expect(preview).toContainText("حُسب البروتين باستخدام الوزن الفعلي.");
    await expect(preview).toContainText("70");
    await expect(preview).not.toContainText("null");
    await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
    const confirmation = page.getByRole("dialog", { name: /تأكيد الأهداف الجديدة|استبدال الخطة المجدولة/ });
    await expect(confirmation).toBeVisible();
    await confirmation.getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).click();
    await expect.poll(() => activationPosts).toBe(1);
    await expect(page.getByText("تم حفظ التغييرات")).toBeVisible();
  });

  test("@p0 activation safety errors preserve the draft", async ({ page, originalProfile }) => {
    const cases = [
      ["SPECIALIST_REVIEW_REQUIRED", SPECIALIST_REVIEW_REQUIRED],
      ["VERY_LOW_ENERGY_TARGET_BLOCKED", VERY_LOW_ENERGY_TARGET_BLOCKED]
    ] as const;
    let activeCase: readonly [string, string] = cases[0];
    let previewRequests = 0;
    let activationPosts = 0;
    await page.route(previewPath, (route) => {
      previewRequests += 1;
      return fulfillPreview(route, (targets) => ({ ...targets, safety_outcome: "normal", can_activate: true }));
    });
    await page.route(activationPath, async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      activationPosts += 1;
      await route.fulfill({
        status: 422,
        contentType: "application/json",
        json: { error: { code: activeCase[0], message_ar: "لا يمكن تفعيل هذه النتيجة وفق سياسة السلامة.", details: {}, request_id: crypto.randomUUID() } }
      });
    });

    for (const [index, scenario] of cases.entries()) {
      activeCase = scenario;
      await page.goto(`/profile?activation-safety-recovery=${index}`);
      const retainedWeight = await changedWeight(page, originalProfile, index + 1);
      const previewsBeforeActivation = previewRequests;
      await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
      await page.getByRole("dialog", { name: /تأكيد الأهداف الجديدة|استبدال الخطة المجدولة/ })
        .getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).click();
      const recovery = page.getByRole("alert").filter({ hasText: scenario[1] });
      await expect(recovery.getByText(scenario[1], { exact: true })).toBeVisible();
      await expect(recovery).toBeFocused();
      await expect(page.getByLabel("الوزن")).toHaveValue(retainedWeight);
      await expect(page.getByRole("dialog", { name: /تأكيد الأهداف الجديدة|استبدال الخطة المجدولة/ })).toHaveCount(0);
      await page.getByRole("button", { name: "تحديث المعاينة" }).click();
      await expect.poll(() => previewRequests).toBeGreaterThan(previewsBeforeActivation);
      expect(activationPosts).toBe(index + 1);
    }
  });

  test("@p0 @plan011 pre-accept failure preserves draft and Retry reuses the key", async ({ page, originalProfile }) => {
    await page.goto("/profile");
    const nextHeight = originalProfile.height_cm + 1;
    await page.getByLabel("الطول").fill(String(nextHeight));
    let fail = true;
    const idempotencyKeys: string[] = [];
    await page.route("**/target-plans/**", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      idempotencyKeys.push(route.request().headers()["idempotency-key"]);
      if (fail) return route.abort("failed");
      return route.continue();
    });
    await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
    await page.getByRole("dialog").getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).click();
    await expect(page.getByText("تعذر حفظ التغييرات")).toBeVisible();
    await expect(page.getByLabel("الطول")).toHaveValue(String(nextHeight));
    let profileRefetches = 0;
    await page.route(profilePath, async (route) => {
      if (route.request().method() !== "GET") return route.continue();
      profileRefetches += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        json: { ...originalProfile, height_cm: originalProfile.height_cm + 8 }
      });
    });
    await page.clock.install({ time: new Date() });
    await page.clock.fastForward(20_001);
    await page.context().setOffline(true);
    const refetched = page.waitForResponse((response) =>
      new URL(response.url()).origin === API_ORIGIN
        && profilePath(new URL(response.url()))
        && response.request().method() === "GET"
    );
    await page.context().setOffline(false);
    await refetched;
    expect(profileRefetches).toBe(1);
    await expect(page.getByText("توجد نسخة أحدث من بيانات الملف على الخادم. احتفظنا بتعديلاتك الحالية.")).toBeVisible();
    await expect(page.getByLabel("الطول")).toHaveValue(String(nextHeight));
    await page.getByRole("link", { name: "اليوميات" }).click();
    await page.getByRole("dialog", { name: "تغييرات غير محفوظة" }).getByRole("button", { name: "متابعة التعديل" }).click();
    await expect(page).toHaveURL(/\/profile$/);
    await expect(page.getByLabel("الطول")).toHaveValue(String(nextHeight));
    await page.unroute(profilePath);
    fail = false;
    await page.getByRole("button", { name: "إعادة المحاولة" }).click();
    await page.getByRole("dialog").getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).click();
    await expect(page.getByText("تم حفظ التغييرات")).toBeVisible();
    expect(idempotencyKeys).toHaveLength(2);
    expect(idempotencyKeys[1]).toBe(idempotencyKeys[0]);
  });

  test("@p0 @plan016 navigation guard preserves or discards dirty draft", async ({ page, originalProfile }) => {
    await page.goto("/profile");
    await page.getByLabel("الوزن").fill(String(originalProfile.weight_kg + 1));
    const opener = page.getByRole("link", { name: "اليوميات" });
    await opener.focus();
    await opener.click();
    const dialog = page.getByRole("dialog", { name: "تغييرات غير محفوظة" });
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute("aria-labelledby", "unsaved-dialog-title");
    await expect(dialog).toHaveAttribute("aria-describedby", "unsaved-dialog-description");
    await expect(dialog.getByRole("button", { name: "متابعة التعديل" })).toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await expect(dialog.getByRole("button", { name: "تجاهل التغييرات والمغادرة" })).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(dialog.getByRole("button", { name: "متابعة التعديل" })).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(opener).toBeFocused();
    await opener.click();
    await dialog.getByRole("button", { name: "متابعة التعديل" }).click();
    await expect(page).toHaveURL(/\/profile$/);
    await expect(page.getByLabel("الوزن")).toHaveValue(String(originalProfile.weight_kg + 1));
    await page.getByRole("link", { name: "اليوميات" }).click();
    await page.getByRole("dialog", { name: "تغييرات غير محفوظة" }).getByRole("button", { name: "تجاهل التغييرات والمغادرة" }).click();
    await expect(page).toHaveURL(/\/diary$/);
  });

  test("@plan016 dirty Profile keeps its exact draft when a same-resource refetch arrives", async ({ page, originalProfile }) => {
    await page.goto("/diary");
    await expect(page.getByRole("link", { name: "الإدارة" })).toBeVisible();

    let requestPhase: "initial" | "refetch" = "initial";
    const reads = { initial: 0, refetch: 0 };
    await page.route(profilePath, async (route) => {
      if (route.request().method() !== "GET") return route.continue();
      reads[requestPhase] += 1;
      if (requestPhase === "initial") return route.continue();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        json: { ...originalProfile, weight_kg: originalProfile.weight_kg + 9 }
      });
    });
    const initialRead = page.waitForResponse((response) =>
      profilePath(new URL(response.url())) && response.request().method() === "GET"
    );
    await page.getByRole("link", { name: "الملف" }).click();
    await initialRead;
    await expect(page).toHaveURL(/\/profile$/);
    const input = page.getByLabel("الوزن");
    const draft = String(originalProfile.weight_kg + 1);
    expect(reads).toEqual({ initial: 1, refetch: 0 });
    await input.fill(draft);
    await expect(page.getByText("تغييرات غير محفوظة")).toBeVisible();
    requestPhase = "refetch";
    await page.clock.install({ time: new Date() });
    await page.clock.fastForward(20_001);
    await page.context().setOffline(true);
    const refetched = page.waitForResponse((response) =>
      new URL(response.url()).origin === API_ORIGIN
        && profilePath(new URL(response.url()))
        && response.request().method() === "GET"
    );
    await page.context().setOffline(false);
    await refetched;
    expect(reads).toEqual({ initial: 1, refetch: 1 });
    await expect(page.getByText("توجد نسخة أحدث من بيانات الملف على الخادم. احتفظنا بتعديلاتك الحالية.")).toBeVisible();
    await expect(input).toHaveValue(draft);
    await page.getByRole("button", { name: "تحميل نسخة الخادم" }).click();
    await page.getByRole("dialog", { name: "تغييرات غير محفوظة" }).getByRole("button", { name: "متابعة التعديل" }).click();
    await expect(input).toHaveValue(draft);
    await page.getByRole("button", { name: "تحميل نسخة الخادم" }).click();
    await page.getByRole("dialog", { name: "تغييرات غير محفوظة" }).getByRole("button", { name: "تجاهل التغييرات والمغادرة" }).click();
    await expect(input).toHaveValue(String(originalProfile.weight_kg + 9));
  });

  test("@plan016 browser Back cancel preserves the Profile draft and discard traverses once", async ({ page, originalProfile }) => {
    await page.goto("/diary");
    await page.getByRole("link", { name: "الملف" }).click();
    const input = page.getByLabel("الوزن");
    const draft = String(originalProfile.weight_kg + 2);
    await input.fill(draft);
    const dialog = page.getByRole("dialog", { name: "تغييرات غير محفوظة" });
    await page.getByRole("link", { name: "اليوميات" }).click();
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveCount(1);
    await expect(page).toHaveURL(/\/profile$/);
    await expect(input).toHaveValue(draft);
    await dialog.getByRole("button", { name: "متابعة التعديل" }).click();
    await expect(dialog).toHaveCount(0);
    await expect(page).toHaveURL(/\/profile$/);
    await expect(input).toHaveValue(draft);
    await page.goBack();
    await expect(page).toHaveURL(/\/profile$/);
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "متابعة التعديل" }).click();
    await expect(page).toHaveURL(/\/profile$/);
    await expect(input).toHaveValue(draft);
    await page.goBack();
    await expect(page).toHaveURL(/\/profile$/);
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "تجاهل التغييرات والمغادرة" }).click();
    await expect(page).toHaveURL(/\/diary$/);
  });

  test("@plan016 sign-out cancel retains the draft and confirmed remote failure signs out locally", async ({ page, originalProfile }) => {
    let logoutCalls = 0;
    await page.route((url) => url.origin === AUTH_ORIGIN && url.pathname === "/auth/v1/logout", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      logoutCalls += 1;
      await route.fulfill({ status: 500, contentType: "application/json", json: { message: "forced remote revocation failure" } });
    });
    await page.goto("/profile");
    const weight = page.getByLabel("الوزن");
    const draft = String(originalProfile.weight_kg + 3);
    await weight.fill(draft);
    await page.locator(".nav-signout").click();
    const dialog = page.getByRole("dialog", { name: "تغييرات غير محفوظة" });
    await dialog.getByRole("button", { name: "متابعة التعديل" }).click();
    expect(logoutCalls).toBe(0);
    await expect(page).toHaveURL(/\/profile$/);
    await expect(page.locator(".nav-signout")).toBeVisible();
    await expect(weight).toHaveValue(draft);

    await page.getByRole("link", { name: "اليوميات" }).click();
    await expect(dialog).toBeVisible();
    await expect(page).toHaveURL(/\/profile$/);
    await expect(weight).toHaveValue(draft);
    await dialog.getByRole("button", { name: "متابعة التعديل" }).click();
    expect(logoutCalls).toBe(0);

    await page.locator(".nav-signout").click();
    await dialog.getByRole("button", { name: "تجاهل التغييرات والمغادرة" }).click();
    await expect(page).toHaveURL(/\/auth\/login(?:\?.*)?$/);
    expect(logoutCalls).toBe(1);
    await expect(page.locator(".profile-form")).toHaveCount(0);
    await expect(page.getByLabel("الوزن")).toHaveCount(0);
    await expect(page.locator(".nav-signout")).toHaveCount(0);
    await expect(dialog).toHaveCount(0);

    await page.locator('input[type="email"]').fill(ADMIN_EMAIL);
    await page.locator('input[type="password"]').fill(ADMIN_PASSWORD);
    await page.locator('button[type="submit"]').click();
    await page.waitForURL(/\/(diary|profile)$/);
    await page.goto("/profile");
    await expect(page.getByLabel("الوزن")).toHaveValue(String(originalProfile.weight_kg));
    await expect(page.getByLabel("الوزن")).not.toHaveValue(draft);
    await expect(dialog).toHaveCount(0);
  });

  test("@p1 calculation sheet is user-facing and targets are unified read-only values", async ({ page, originalProfile }) => {
    await page.goto("/profile");
    const targets = page.getByRole("region", { name: "الأهداف اليومية" });
    await expect(targets.locator(".profile-calorie-target")).toContainText(String(originalProfile.targets.target_calories));
    await expect(targets.locator(".profile-macro-targets > div")).toHaveCount(3);
    await expect(targets.locator("input, [role='progressbar']")).toHaveCount(0);
    await expect(page.locator(".metric-tile")).toHaveCount(0);
    await page.getByRole("button", { name: "كيف حُسبت أهدافي؟" }).click();
    const sheet = page.getByRole("dialog", { name: "طريقة حساب أهدافك" });
    await expect(sheet).toContainText("Mifflin–St Jeor");
    await expect(sheet).not.toContainText(/localhost|127\.0\.0\.1|API|backend/i);
  });

  test("@p1 initial loading and load failure never expose a fabricated editable form", async ({ page }) => {
    const profileApiPattern = (url: URL) => url.pathname === "/profile";
    let releaseProfileResponse: () => void = () => undefined;
    const profileResponseBlocked = new Promise<void>((resolve) => {
      releaseProfileResponse = resolve;
    });
    let releaseFirstFetch: () => void = () => undefined;
    const firstProfileFetched = new Promise<void>((resolve) => {
      releaseFirstFetch = resolve;
    });
    let releaseFirstFulfill: () => void = () => undefined;
    const firstProfileFulfilled = new Promise<void>((resolve) => {
      releaseFirstFulfill = resolve;
    });
    let delayedFirstProfileRequest = false;
    await page.route(profileApiPattern, async (route) => {
      if (
        route.request().method() !== "GET" ||
        route.request().resourceType() !== "fetch"
      ) return route.continue();
      if (delayedFirstProfileRequest) return route.continue();
      delayedFirstProfileRequest = true;
      const response = await route.fetch();
      releaseFirstFetch();
      await profileResponseBlocked;
      await route.fulfill({ response });
      releaseFirstFulfill();
    });
    const navigation = page.goto("/profile");
    await expect(page.locator(".profile-card-skeleton").first()).toBeVisible();
    await firstProfileFetched;
    releaseProfileResponse();
    await firstProfileFulfilled;
    await navigation;
    await expect(page.getByLabel("الوزن")).toBeVisible();
    const errorPage = await page.context().newPage();
    await errorPage.goto("/diary");
    await expect(errorPage.getByRole("link", { name: "الإدارة" })).toBeVisible();
    let errorProfileRequests = 0;
    let failProfileRequests = true;
    await errorPage.route(profilePath, (route) => {
      if (route.request().method() !== "GET") return route.continue();
      errorProfileRequests += 1;
      return failProfileRequests
        ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "unavailable" }) })
        : route.continue();
    });
    await errorPage.getByRole("link", { name: "الملف" }).click();
    const errorAlert = errorPage.getByRole("alert").filter({ hasText: "تعذر تحميل بياناتك" });
    await expect(errorAlert).toBeVisible();
    await expect(errorAlert).toHaveCount(1);
    await expect(errorAlert).toContainText("تحقق من الاتصال ثم أعد المحاولة");
    expect(errorProfileRequests).toBe(2);
    await expect(errorPage.getByLabel("الوزن")).toHaveCount(0);
    failProfileRequests = false;
    await errorPage.getByRole("button", { name: "إعادة المحاولة" }).click();
    await expect(errorPage.getByLabel("الوزن")).toBeVisible();
    await expect(errorAlert).toHaveCount(0);
    expect(errorProfileRequests).toBe(3);
    await errorPage.close();
  });

  test("@p1 Registry unavailable and incompatible states block activation without fabricated metadata", async ({ page, originalProfile }) => {
    await page.route("**/nutrition/registry", (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "unavailable" }) }));
    await page.goto("/profile?registry-unavailable=1");
    await expect(page.getByRole("alert").filter({ hasText: "تعذر تحميل البيانات الغذائية" })).toBeVisible();
    await page.getByLabel("الوزن").fill(String(originalProfile.weight_kg + 1));
    await expect(page.getByRole("button", { name: "مراجعة وتأكيد" })).toBeDisabled();

    await page.unroute("**/nutrition/registry");
    await page.route("**/nutrition/registry", async (route) => {
      const response = await route.fetch();
      const registry = await response.json() as Record<string, unknown>;
      await route.fulfill({ response, json: { ...registry, registry_schema_version: 99 } });
    });
    await page.goto("/profile?registry-incompatible=1");
    await expect(page.getByRole("alert").filter({ hasText: "إصدار سجل التغذية غير متوافق" })).toBeVisible();
    await page.getByLabel("الوزن").fill(String(originalProfile.weight_kg + 1));
    await expect(page.getByRole("button", { name: "مراجعة وتأكيد" })).toBeDisabled();
  });

  test("@p1 target plan history exposes lifecycle state without raw plan documents", async ({ page, originalProfile }) => {
    await page.route("**/target-plans?**", (route) => route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [{
          id: "00000000-0000-0000-0000-000000000901",
          status: "superseded_before_effective",
          effective_from: "2026-07-18",
          effective_to: null,
          calendar_timezone: "Asia/Riyadh",
          predecessor_plan_id: null,
          superseded_by_plan_id: "00000000-0000-0000-0000-000000000902",
          targets: originalProfile.targets,
          created_at: "2026-07-17T09:00:00Z",
          activated_at: null,
          closed_at: null,
          superseded_at: "2026-07-17T10:00:00Z"
        }],
        next_cursor: null
      })
    }));
    await page.goto("/profile?plan-history=1");
    const history = page.getByRole("region", { name: "سجل الخطط" });
    await expect(history).toContainText("استُبدلت قبل أن تبدأ");
    await expect(history).toContainText("2026-07-18");
    await expect(history).not.toContainText("preview_hash");
  });

  test("@p1 stale activation responses require a fresh preview without discarding the draft", async ({ page, originalProfile }) => {
    await page.route("**/target-plans/**", (route) => {
      if (route.request().method() !== "POST") return route.continue();
      return route.fulfill({
        status: 409,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "PREVIEW_RESULT_CHANGED", message_ar: "تغيّرت نتيجة المعاينة؛ راجعها ثم أكد مجددًا." } })
      });
    });
    await page.goto("/profile?stale-preview=1");
    const nextWeight = originalProfile.weight_kg + 1;
    await page.getByLabel("الوزن").fill(String(nextWeight));
    await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
    await page.getByRole("dialog").getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).click();
    await expect(page.getByText("تغيّرت المعاينة. راجع الأهداف المحدثة ثم أكد مجددًا")).toBeVisible();
    await expect(page.getByLabel("الوزن")).toHaveValue(String(nextWeight));
    await expect(page.getByRole("button", { name: "مراجعة المعاينة" })).toBeEnabled();
  });

  test("@p1 responsive layout, touch targets, alerts, and focus restoration hold", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    for (const width of [320, 360, 390, 430]) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto("/profile");
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
      const sexButton = page.getByRole("button", { name: /تغيير الجنس/ });
      expect((await sexButton.boundingBox())!.height).toBeGreaterThanOrEqual(44);
      await sexButton.click();
      const sheet = page.getByRole("dialog", { name: "اختر الجنس" });
      await expect(sheet).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(sexButton).toBeFocused();
      await expect(page.locator('.profile-page [role="alert"]:empty')).toHaveCount(0);
    }
  });
});
