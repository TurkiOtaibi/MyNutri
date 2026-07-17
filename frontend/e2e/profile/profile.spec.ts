import { expect, test as base, type APIRequestContext } from "@playwright/test";

import type { ProfileInput, ProfileResponse } from "../../lib/types";
import { API_TOKEN, API_URL } from "../foods/helpers";

const headers = { Authorization: `Bearer ${API_TOKEN}` };

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
  const response = await request.get(`${API_URL}/profile`, { headers });
  expect(response.status()).toBe(200);
  return response.json() as Promise<ProfileResponse>;
}

const test = base.extend<{ originalProfile: ProfileResponse }>({
  originalProfile: async ({ request }, use) => {
    const original = await readProfile(request);
    await use(original);
    await request.put(`${API_URL}/profile`, { headers, data: inputFrom(original) });
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
    const profileResponse = page.waitForResponse((response) =>
      new URL(response.url()).pathname === "/profile" &&
      response.request().method() === "GET" &&
      response.request().resourceType() === "fetch"
    );
    await page.goto("/profile");
    expect((await profileResponse).status()).toBe(200);
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

  test("@p0 preview uses server result, stays distinct, and save adopts confirmed response", async ({ page, originalProfile }) => {
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
    await confirmation.getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).dblclick();
    await expect(page.getByText("تم حفظ التغييرات")).toBeVisible();
    expect(activationRequests).toBe(1);
    await expect(page.locator(".profile-save-bar")).toHaveCount(0);
    await expect(preview).toHaveCount(0);
  });

  test("@p0 save failure preserves draft and Retry succeeds", async ({ page, originalProfile }) => {
    await page.goto("/profile");
    const nextHeight = originalProfile.height_cm + 1;
    await page.getByLabel("الطول").fill(String(nextHeight));
    let fail = true;
    await page.route("**/target-plans/**", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      if (fail) return route.abort("failed");
      return route.continue();
    });
    await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
    await page.getByRole("dialog").getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).click();
    await expect(page.getByText("تعذر حفظ التغييرات")).toBeVisible();
    await expect(page.getByLabel("الطول")).toHaveValue(String(nextHeight));
    fail = false;
    await page.getByRole("button", { name: "إعادة المحاولة" }).click();
    await page.getByRole("dialog").getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).click();
    await expect(page.getByText("تم حفظ التغييرات")).toBeVisible();
  });

  test("@p0 navigation guard preserves or discards dirty draft", async ({ page, originalProfile }) => {
    await page.goto("/profile");
    await page.getByLabel("الوزن").fill(String(originalProfile.weight_kg + 1));
    await page.getByRole("link", { name: "اليوميات" }).click();
    const dialog = page.getByRole("dialog", { name: "تجاهل التغييرات؟" });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "متابعة التعديل" }).click();
    await expect(page).toHaveURL(/\/profile$/);
    await expect(page.getByLabel("الوزن")).toHaveValue(String(originalProfile.weight_kg + 1));
    await page.getByRole("link", { name: "اليوميات" }).click();
    await page.getByRole("dialog", { name: "تجاهل التغييرات؟" }).getByRole("button", { name: "تجاهل التغييرات", exact: true }).click();
    await expect(page).toHaveURL(/\/diary$/);
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
    await page.route(profileApiPattern, async (route) => {
      if (
        route.request().method() !== "GET" ||
        route.request().resourceType() !== "fetch"
      ) return route.continue();
      const response = await route.fetch();
      await profileResponseBlocked;
      return route.fulfill({ response });
    });
    const navigation = page.goto("/profile");
    await expect(page.locator(".profile-card-skeleton").first()).toBeVisible();
    releaseProfileResponse();
    await navigation;
    await expect(page.getByLabel("الوزن")).toBeVisible();
    await page.unroute(profileApiPattern);
    await page.route(profileApiPattern, (route) =>
      route.request().method() === "GET" && route.request().resourceType() === "fetch"
        ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "unavailable" }) })
        : route.continue()
    );
    await page.goto("/profile?load-error=1");
    await expect(page.getByText("تعذر تحميل بياناتك")).toBeVisible();
    await expect(page.getByRole("button", { name: "إعادة المحاولة" })).toBeVisible();
    await expect(page.getByLabel("الوزن")).toHaveCount(0);
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
