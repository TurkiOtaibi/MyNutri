import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import type { Page } from "@playwright/test";

import type { DaySummary, DiaryEntryResponse, WeekSummary } from "../../lib/types";
import { API_TOKEN, API_URL, diaryDate as localDate, expect, offsetIsoDate, test, uniqueName } from "../foods/helpers";

const output = resolve("..", "docs", "ui-ux", "screenshots", "diary-final-polish");
const apiOrigin = new URL(API_URL).origin;

function sundayStart(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  const weekday = new Date(Date.UTC(year, month - 1, day)).getUTCDay();
  return offsetIsoDate(value, -weekday);
}

function isExactDiaryResponse(
  response: import("@playwright/test").Response,
  pathname: string,
  queryKey: string,
  queryValue: string
) {
  const request = response.request();
  const url = new URL(response.url());
  return request.method() === "GET" &&
    url.origin === apiOrigin &&
    url.pathname === pathname &&
    url.searchParams.get(queryKey) === queryValue &&
    [...url.searchParams.keys()].length === 1 &&
    response.ok();
}

async function runDiaryTransition(page: Page, value: string, trigger: () => Promise<unknown>) {
  const weekStart = sundayStart(value);
  const [entriesResponse, weekResponse] = await Promise.all([
    page.waitForResponse((response) => isExactDiaryResponse(response, "/diary", "entry_date", value)),
    page.waitForResponse((response) => isExactDiaryResponse(response, "/diary/week", "start", weekStart)),
    trigger()
  ]);
  expect(entriesResponse.status()).toBe(200);
  expect(weekResponse.status()).toBe(200);
  const entries = await entriesResponse.json() as DiaryEntryResponse[];
  const week = await weekResponse.json() as WeekSummary;
  expect(Array.isArray(entries)).toBe(true);
  expect(Array.isArray(week.days)).toBe(true);
  return { entries, week };
}

async function expectStableSummary(page: Page) {
  await expect(page.locator(".diary-entry-skeleton")).toHaveCount(0);
  await expect(page.locator(".diary-summary-loading")).toHaveCount(0);
  const summary = page.locator(".diary-summary");
  await expect(summary).toHaveCount(1);
  await expect(summary).toBeVisible();
  await expect(page.locator(".diary-error-state")).toHaveCount(0);
  await expect(page.locator(".diary-summary-unavailable")).toHaveCount(0);
  await expect(page.locator(".week-inline-error")).toHaveCount(0);
}

async function expectPopulatedDiary(page: Page, minimumBreakfastRows: number, foodNames: string[]) {
  await expectStableSummary(page);
  const breakfast = page.locator("#meal-breakfast");
  await expect.poll(() => breakfast.locator(".diary-entry-row").count()).toBeGreaterThanOrEqual(minimumBreakfastRows);
  for (const name of foodNames) {
    await expect(breakfast.getByRole("heading", { name, exact: true })).toBeVisible();
  }
  await expect(page.locator(".diary-empty-note")).toHaveCount(0);
  const summary = page.locator(".diary-summary");
  await expect(summary.getByRole("heading", { name: "ملخص اليوم", exact: true })).toBeVisible();
  await expect(summary.getByRole("progressbar")).toHaveCount(4);
}

function selectedSummaryDay(week: WeekSummary, value: string) {
  const selectedDay = week.days.find((day) => day.date === value);
  expect(selectedDay).toBeDefined();
  return selectedDay!;
}

function expectZeroTotals(day: DaySummary) {
  expect(day.totals.calories).toBe(0);
  expect(day.totals.protein_g).toBe(0);
  expect(day.totals.carb_g).toBe(0);
  expect(day.totals.fat_g).toBe(0);
}

async function expectHistoricalEmptyDiary(
  page: Page,
  value: string,
  transition: Awaited<ReturnType<typeof runDiaryTransition>>
) {
  expect(transition.entries).toHaveLength(0);
  const selectedDay = selectedSummaryDay(transition.week, value);
  expectZeroTotals(selectedDay);
  if (selectedDay.targets === null) {
    expect(selectedDay.target_provenance).toBe("no_target_source");
  } else {
    expect(selectedDay.target_provenance).not.toBe("no_target_source");
  }

  await expectStableSummary(page);
  await expect(page.getByLabel("اختيار تاريخ اليوميات")).toHaveValue(value);
  await expect(page.locator(".diary-entry-row")).toHaveCount(0);
  await expect(page.locator(".diary-empty-note")).toBeVisible();
  const summary = page.locator(".diary-summary");
  await expect(summary.getByRole("heading", { name: "ملخص اليوم", exact: true })).toBeVisible();

  if (selectedDay.targets === null) {
    await expect(summary).toHaveAttribute("aria-label", "ملخص اليوم دون مصدر هدف");
    await expect(summary.locator(".target-provenance-label")).toHaveText("دون مصدر هدف محفوظ");
    await expect(summary.getByText("لا يوجد مصدر هدف محفوظ لهذا اليوم.", { exact: true })).toBeVisible();
    await expect(summary.getByRole("progressbar")).toHaveCount(0);
    return;
  }

  const provenanceLabel = selectedDay.target_provenance === "versioned_plan"
    ? "أهداف خطة محفوظة"
    : "أهداف قديمة غير محدثة";
  await expect(summary.locator(".target-provenance-label")).toHaveText(provenanceLabel);
  await expect(summary.getByRole("progressbar")).toHaveCount(4);
}

async function selectDate(page: Page, value: string) {
  const picker = page.getByLabel("اختيار تاريخ اليوميات");
  const transition = await runDiaryTransition(page, value, () => picker.fill(value));
  await expectHistoricalEmptyDiary(page, value, transition);
  return transition;
}

async function expectTargetBackedZeroDiary(
  page: Page,
  value: string,
  transition: Awaited<ReturnType<typeof runDiaryTransition>>
) {
  expect(transition.entries).toHaveLength(0);
  const selectedDay = selectedSummaryDay(transition.week, value);
  expect(selectedDay.targets).not.toBeNull();
  expect(selectedDay.target_provenance).not.toBe("no_target_source");
  expectZeroTotals(selectedDay);

  await expectStableSummary(page);
  await expect(page.getByLabel("اختيار تاريخ اليوميات")).toHaveValue(value);
  await expect(page.locator(".diary-entry-row")).toHaveCount(0);
  await expect(page.locator(".diary-empty-note")).toBeVisible();
  const summary = page.locator(".diary-summary");
  await expect(summary).toHaveCount(1);
  await expect(summary).toBeVisible();
  await expect(summary.getByText("لا يوجد مصدر هدف محفوظ لهذا اليوم.", { exact: true })).toHaveCount(0);
  const provenanceLabel = selectedDay.target_provenance === "versioned_plan"
    ? "أهداف خطة محفوظة"
    : "أهداف قديمة غير محدثة";
  await expect(summary.locator(".target-provenance-label")).toHaveText(provenanceLabel);
  const progressbars = summary.getByRole("progressbar");
  await expect(progressbars).toHaveCount(4);
  await expect(summary.locator('[role="progressbar"][aria-valuenow="0"]')).toHaveCount(4);
  for (const progressbar of [
    summary.getByRole("progressbar", { name: "0% من هدف السعرات", exact: true }),
    summary.getByRole("progressbar", { name: "البروتين", exact: true }),
    summary.getByRole("progressbar", { name: "الكارب", exact: true }),
    summary.getByRole("progressbar", { name: "الدهون", exact: true })
  ]) {
    await expect(progressbar).toHaveCount(1);
    await expect(progressbar).toHaveAttribute("aria-valuenow", "0");
  }
}

async function captureStableSummary(page: Page, path: string) {
  await expectStableSummary(page);
  const summary = page.locator(".diary-summary");
  await expect(summary).toHaveCount(1);
  await expect(summary).toBeVisible();
  await expect(page.locator(".diary-summary-loading")).toHaveCount(0);
  await summary.screenshot({ path });
}

async function captureStableElement(page: Page, selector: string, path: string) {
  await expectStableSummary(page);
  const target = page.locator(selector);
  await expect(target).toHaveCount(1);
  await expect(target).toBeVisible();
  await target.screenshot({ path });
}

test("@diary @visual capture final Diary polish states", async ({ page, request, foodsApi }) => {
  await mkdir(output, { recursive: true });
  await page.emulateMedia({ reducedMotion: "reduce" });

  const first = await foodsApi.create({
    name: uniqueName("بيض مسلوق"), calories: 78, protein_g: 12.6, carb_g: 1.2, fat_g: 10.6,
    default_unit_type: "piece", unit_amount: 50
  });
  const second = await foodsApi.create({
    name: uniqueName("توست Mixed Arabic English طويل للاختبار"), calories: 78,
    protein_g: 4, carb_g: 12, fat_g: 2, default_unit_type: "slice", unit_amount: 30
  });
  const firstEntry = await foodsApi.createDiary(first.id, localDate(), 1, "breakfast");
  const secondEntry = await foodsApi.createDiary(second.id, localDate(), 1, "breakfast");
  const currentDate = localDate();

  await page.setViewportSize({ width: 390, height: 844 });
  await runDiaryTransition(page, currentDate, () => page.goto("/diary"));
  await expect(page.getByLabel("اختيار تاريخ اليوميات")).toHaveValue(currentDate);
  await expectPopulatedDiary(page, 2, [first.name, second.name]);
  await page.screenshot({ path: resolve(output, "01-iphone-reference-populated-390.png"), fullPage: true });
  await expect(page.locator(".compact-week-day.selected")).toHaveCount(1);
  await captureStableElement(page, ".compact-week-nav", resolve(output, "02-current-date-selected-day-390.png"));
  await expect(page.locator("#meal-section-breakfast .meal-toggle")).toHaveAttribute("aria-expanded", "true");
  await captureStableElement(page, "#meal-section-breakfast", resolve(output, "04-breakfast-two-compact-rows-390.png"));
  for (const meal of ["غداء", "عشاء", "سناك"]) {
    await expect(page.getByRole("button", { name: `فتح قسم ${meal}`, exact: true })).toContainText("لا توجد أطعمة");
  }
  await captureStableElement(page, ".meal-sections", resolve(output, "05-empty-meal-rows-390.png"));

  const profile = await request.get(`${API_URL}/profile`, { headers: { Authorization: `Bearer ${API_TOKEN}` } });
  expect(profile.status()).toBe(200);
  const targets = (await profile.json()).targets as { target_calories: number; protein_g: number; carb_g: number; fat_g: number };
  await request.delete(`${API_URL}/diary/${firstEntry.id}`, { headers: { Authorization: `Bearer ${API_TOKEN}` } });
  await request.delete(`${API_URL}/diary/${secondEntry.id}`, { headers: { Authorization: `Bearer ${API_TOKEN}` } });
  const comparisonDate = localDate();
  const comparison = await foodsApi.create({
    name: uniqueName("Macro comparison"), calories: 100,
    protein_g: targets.protein_g * 0.09,
    carb_g: targets.carb_g * 0.01,
    fat_g: targets.fat_g * 0.22
  });
  await foodsApi.createDiary(comparison.id, comparisonDate, 1, "breakfast");
  await runDiaryTransition(page, comparisonDate, () => page.reload());
  await expect(page.getByLabel("اختيار تاريخ اليوميات")).toHaveValue(comparisonDate);
  await expectPopulatedDiary(page, 1, [comparison.name]);
  const comparisonBreakfast = page.locator("#meal-breakfast");
  await expect(comparisonBreakfast.getByRole("heading", { name: first.name, exact: true })).toHaveCount(0);
  await expect(comparisonBreakfast.getByRole("heading", { name: second.name, exact: true })).toHaveCount(0);
  const comparisonSummary = page.locator(".diary-summary");
  const proteinProgress = comparisonSummary.getByLabel(/البروتين:.*9%/);
  const carbProgress = comparisonSummary.getByLabel(/الكارب:.*1%/);
  const fatProgress = comparisonSummary.getByLabel(/الدهون:.*22%/);
  await expect(proteinProgress).toHaveCount(1);
  await expect(carbProgress).toHaveCount(1);
  await expect(fatProgress).toHaveCount(1);
  await expect(proteinProgress.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "9");
  await expect(carbProgress.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "1");
  await expect(fatProgress.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "22");
  await captureStableSummary(page, resolve(output, "03-summary-macros-9-1-22-390.png"));
  const comparisonEntries = await foodsApi.listDiary(comparisonDate);
  const comparisonEntry = comparisonEntries.find((entry) => entry.nutrition_snapshot.name === comparison.name);
  expect(comparisonEntry).toBeDefined();
  await request.delete(`${API_URL}/diary/${comparisonEntry!.id}`, { headers: { Authorization: `Bearer ${API_TOKEN}` } });

  const emptyDate = localDate(-340);
  await selectDate(page, emptyDate);
  await expect(page.getByRole("button", { name: "اليوم", exact: true })).toBeVisible();
  await page.screenshot({ path: resolve(output, "06-other-date-today-visible-empty-390.png"), fullPage: true });

  const zeroTargetBackedDate = localDate();
  const zeroTargetBackedTransition = await runDiaryTransition(page, zeroTargetBackedDate, () => page.reload());
  await expectTargetBackedZeroDiary(page, zeroTargetBackedDate, zeroTargetBackedTransition);
  await captureStableSummary(page, resolve(output, "07-summary-macros-zero-390.png"));

  const overDate = localDate();
  const over = await foodsApi.create({
    name: uniqueName("Macro full over"),
    calories: Math.min(3000, targets.target_calories + 300),
    protein_g: Math.min(300, targets.protein_g + 50),
    carb_g: Math.min(500, targets.carb_g + 50),
    fat_g: Math.min(300, targets.fat_g + 20)
  });
  await foodsApi.createDiary(over.id, overDate, 1, "breakfast");
  await runDiaryTransition(page, overDate, () => page.reload());
  await expect(page.getByLabel("اختيار تاريخ اليوميات")).toHaveValue(overDate);
  await expectPopulatedDiary(page, 1, [over.name]);
  await expect(page.locator("#meal-breakfast").getByRole("heading", { name: comparison.name, exact: true })).toHaveCount(0);
  const overSummary = page.locator(".diary-summary");
  await expect(overSummary.locator(".calorie-summary-primary p.over")).toContainText("فوق الهدف");
  await expect(overSummary.locator('.diary-progress-track.over[role="progressbar"][aria-valuenow="100"]')).toBeVisible();
  for (const label of ["البروتين", "الكارب", "الدهون"]) {
    const progress = overSummary.getByLabel(new RegExp(`^${label}:.*فوق الهدف`));
    await expect(progress).toHaveCount(1);
    const progressbar = progress.getByRole("progressbar");
    expect(Number(await progressbar.getAttribute("aria-valuenow"))).toBeGreaterThan(100);
    await expect(progressbar).toHaveAttribute("aria-valuetext", /فوق الهدف/);
  }
  await captureStableSummary(page, resolve(output, "08-summary-macros-100-over-390.png"));

  await foodsApi.createDiary(first.id, localDate(), 1, "breakfast");
  await foodsApi.createDiary(second.id, localDate(), 1, "breakfast");
  for (const width of [320, 430]) {
    await page.setViewportSize({ width, height: 844 });
    await runDiaryTransition(page, currentDate, () => page.goto("/diary"));
    await expect(page.getByLabel("اختيار تاريخ اليوميات")).toHaveValue(currentDate);
    await expectPopulatedDiary(page, 2, [first.name, second.name]);
    await page.screenshot({ path: resolve(output, `09-viewport-${width}.png`), fullPage: true });
  }
});
