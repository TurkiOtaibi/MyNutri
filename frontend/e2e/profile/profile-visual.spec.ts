import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

import type { ProfileInput, ProfileResponse } from "../../lib/types";
import { API_TOKEN, API_URL } from "../foods/helpers";

const output = resolve("..", "docs", "ui-ux", "screenshots", "profile-targets-redesign");
const headers = { Authorization: `Bearer ${API_TOKEN}` };
const escapedApiUrl = API_URL.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const profileApiPattern = new RegExp(`^${escapedApiUrl}/profile$`);
const targetPlanApiPattern = new RegExp(`^${escapedApiUrl}/target-plans/`);

function inputFrom(profile: ProfileResponse): ProfileInput {
  return {
    sex: profile.sex, birth_date: profile.birth_date, height_cm: profile.height_cm, weight_kg: profile.weight_kg,
    activity_level: profile.activity_level, goal: profile.goal, protein_per_kg: profile.protein_per_kg, fat_pct: profile.fat_pct,
    selected_cut_intensity: profile.selected_cut_intensity
  };
}

test("@profile @visual capture production Profile and Targets states", async ({ page, request }) => {
  await mkdir(output, { recursive: true });
  const originalResponse = await request.get(`${API_URL}/profile`, { headers });
  const original = (await originalResponse.json()) as ProfileResponse;
  await page.emulateMedia({ reducedMotion: "reduce" });

  try {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/profile");
    await expect(page.getByRole("heading", { name: "بياناتك وأهدافك" })).toBeVisible();
    await page.screenshot({ path: resolve(output, "01-profile-loaded-390.png"), fullPage: true });
    await page.getByRole("region", { name: "بيانات الجسم" }).screenshot({ path: resolve(output, "02-body-data-card-390.png") });

    await page.getByRole("button", { name: /تغيير الجنس/ }).click();
    await page.screenshot({ path: resolve(output, "03-sex-sheet-390.png") });
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: /تغيير مستوى النشاط/ }).click();
    await page.screenshot({ path: resolve(output, "04-activity-sheet-390.png") });
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: /تغيير الهدف/ }).click();
    await page.screenshot({ path: resolve(output, "05-goal-sheet-390.png") });
    await page.keyboard.press("Escape");

    await page.locator(".profile-advanced").screenshot({ path: resolve(output, "06-advanced-closed-390.png") });
    await page.getByRole("button", { name: "فتح الخيارات المتقدمة" }).click();
    await page.locator(".profile-advanced").screenshot({ path: resolve(output, "07-advanced-open-390.png") });

    await page.getByLabel("الوزن").fill(String(original.weight_kg + 1));
    await expect(page.locator(".profile-save-bar")).toBeVisible();
    await page.screenshot({ path: resolve(output, "08-dirty-save-bar-390.png") });
    await expect(page.getByRole("region", { name: "الأهداف المتوقعة بعد الحفظ" })).toBeVisible();
    await page.getByRole("region", { name: "الأهداف المتوقعة بعد الحفظ" }).screenshot({ path: resolve(output, "14-expected-target-preview-390.png") });

    await page.getByLabel("الطول").fill("0");
    await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
    await page.screenshot({ path: resolve(output, "09-validation-error-390.png") });
    await page.getByLabel("الطول").fill(String(original.height_cm));

    await page.route(targetPlanApiPattern, async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      const response = await route.fetch();
      await new Promise((resolveDelay) => setTimeout(resolveDelay, 900));
      return route.fulfill({ response });
    });
    await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
    await page.getByRole("dialog").getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).click();
    await expect(page.getByText("جارٍ تفعيل الخطة…")).toBeVisible();
    await page.screenshot({ path: resolve(output, "10-saving-state-390.png") });
    await expect(page.getByText("تم حفظ التغييرات")).toBeVisible();
    await page.screenshot({ path: resolve(output, "12-successful-saved-state-390.png") });
    await page.unroute(targetPlanApiPattern);

    await page.getByLabel("الوزن").fill(String(original.weight_kg + 2));
    await page.route(targetPlanApiPattern, (route) => route.request().method() === "POST" ? route.abort("failed") : route.continue());
    await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
    await page.getByRole("dialog").getByRole("button", { name: /^(تفعيل الخطة|استبدال الخطة)$/ }).click();
    await expect(page.getByText("تعذر حفظ التغييرات")).toBeVisible();
    await page.screenshot({ path: resolve(output, "11-save-failure-retry-390.png") });
    await page.unroute(targetPlanApiPattern);

    await page.getByRole("region", { name: "الأهداف اليومية" }).screenshot({ path: resolve(output, "13-unified-current-targets-390.png") });
    await page.getByRole("button", { name: "كيف حُسبت أهدافي؟" }).click();
    await page.screenshot({ path: resolve(output, "15-calculation-explanation-390.png") });
    await page.keyboard.press("Escape");

    await page.getByRole("link", { name: "اليوميات" }).click();
    await expect(page.getByRole("dialog", { name: "تجاهل التغييرات؟" })).toBeVisible();
    await page.screenshot({ path: resolve(output, "22-unsaved-navigation-confirmation-390.png") });
    await page.getByRole("dialog", { name: "تجاهل التغييرات؟" }).getByRole("button", { name: "متابعة التعديل" }).click();

    for (const width of [320, 390, 430]) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto("/profile");
      await expect(page.getByRole("heading", { name: "بياناتك وأهدافك" })).toBeVisible();
      await page.screenshot({ path: resolve(output, `${width === 320 ? 18 : width === 390 ? 19 : 20}-viewport-${width}.png`), fullPage: true });
    }
    await page.setViewportSize({ width: 390, height: 560 });
    await page.getByRole("button", { name: "فتح الخيارات المتقدمة" }).click();
    await page.getByLabel("نسبة الدهون").focus();
    await page.screenshot({ path: resolve(output, "21-keyboard-sized-viewport-390.png") });

    const loadingPage = await page.context().newPage();
    await loadingPage.setViewportSize({ width: 390, height: 844 });
    await loadingPage.route(profileApiPattern, async (route) => {
      const response = await route.fetch();
      await new Promise((resolveDelay) => setTimeout(resolveDelay, 900));
      return route.fulfill({ response });
    });
    await loadingPage.goto("/profile");
    await expect(loadingPage.locator(".profile-card-skeleton").first()).toBeVisible();
    await loadingPage.screenshot({ path: resolve(output, "16-initial-loading-390.png"), fullPage: true });
    await expect(loadingPage.getByLabel("الوزن")).toBeVisible();
    await loadingPage.close();

    const errorPage = await page.context().newPage();
    await errorPage.setViewportSize({ width: 390, height: 844 });
    await errorPage.route(profileApiPattern, (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "unavailable" }) }));
    await errorPage.goto("/profile");
    await expect(errorPage.getByText("تعذر تحميل بياناتك")).toBeVisible();
    await errorPage.screenshot({ path: resolve(output, "17-initial-load-error-390.png"), fullPage: true });
    await errorPage.close();
  } finally {
    await request.put(`${API_URL}/profile`, { headers, data: inputFrom(original) });
  }
});
