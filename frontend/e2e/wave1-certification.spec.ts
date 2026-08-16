import AxeBuilder from "@axe-core/playwright";
import type { Page, Route } from "@playwright/test";
import { API_URL, expect, test } from "./foods/helpers";

const majorStates = [
  { path: "/profile", name: "Profile" },
  { path: "/foods", name: "Foods" },
  { path: "/foods/new", name: "Add Food" },
  { path: "/diary", name: "Diary" }
];

async function certifyDiaryLoadingState(page: Page, authoritativeDate: string) {
  const apiOrigin = new URL(API_URL).origin;
  const date = new Date(`${authoritativeDate}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() - date.getUTCDay());
  const authoritativeWeekStart = date.toISOString().slice(0, 10);
  const entriesPattern = (url: URL) =>
    url.origin === apiOrigin && url.pathname === "/diary/entries" && url.searchParams.get("entry_date") === authoritativeDate;
  const summaryPattern = (url: URL) =>
    url.origin === apiOrigin && url.pathname === "/diary/week" && url.searchParams.get("start") === authoritativeWeekStart;
  let entriesHits = 0;
  let summaryHits = 0;
  let entriesReleased = false;
  let summaryReleased = false;
  let resolveEntriesRelease!: () => void;
  let resolveSummaryRelease!: () => void;
  const entriesRelease = new Promise<void>((resolve) => { resolveEntriesRelease = resolve; });
  const summaryRelease = new Promise<void>((resolve) => { resolveSummaryRelease = resolve; });
  const releaseEntries = () => {
    if (entriesReleased) return;
    entriesReleased = true;
    resolveEntriesRelease();
  };
  const releaseSummary = () => {
    if (summaryReleased) return;
    summaryReleased = true;
    resolveSummaryRelease();
  };
  const holdEntries = async (route: Route) => {
    if (route.request().method() !== "GET") return route.continue();
    entriesHits += 1;
    await entriesRelease;
    await route.continue();
  };
  const holdSummary = async (route: Route) => {
    if (route.request().method() !== "GET") return route.continue();
    summaryHits += 1;
    await summaryRelease;
    await route.continue();
  };

  await page.route(entriesPattern, holdEntries);
  await page.route(summaryPattern, holdSummary);

  try {
    await page.goto("/diary");
    await expect.poll(() => entriesHits, { message: "The held Diary entries request must be reached once." }).toBe(1);
    await expect.poll(() => summaryHits, { message: "The held Diary summary request must be reached once." }).toBe(1);

    const entriesLoading = page.locator(".diary-entry-list");
    const summaryLoading = page.locator(".diary-summary-loading");
    await expect(entriesLoading).toHaveCount(1);
    await expect(summaryLoading).toHaveCount(1);
    await expect(entriesLoading.getByRole("status")).toHaveText("جارٍ تحميل وجبات اليوم");
    await expect(summaryLoading.getByRole("status")).toHaveText("جارٍ تحميل ملخص اليوم");
    await expect(entriesLoading).not.toHaveAttribute("aria-label", /.+/);
    await expect(summaryLoading).not.toHaveAttribute("aria-label", /.+/);
    await expect(page.locator(".meal-sections")).toHaveCount(0);
    await expect(page.locator(".diary-empty-note")).toHaveCount(0);
    await expect(page.locator(".diary-error-state")).toHaveCount(0);
    await expect(page.locator(".diary-progress-track")).toHaveCount(0);
    expect(entriesReleased).toBe(false);
    expect(summaryReleased).toBe(false);

    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const blocking = result.violations.filter((violation) =>
      violation.impact === "moderate" || violation.impact === "serious" || violation.impact === "critical"
    );

    expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);

    releaseEntries();
    releaseSummary();
    await expect(entriesLoading.getByRole("status")).toHaveCount(0);
    await expect(summaryLoading.getByRole("status")).toHaveCount(0);
    await expect(page.locator(".diary-empty-note")).toBeVisible();
    expect(entriesHits).toBe(1);
    expect(summaryHits).toBe(1);
  } finally {
    releaseEntries();
    releaseSummary();
    await page.unroute(entriesPattern, holdEntries);
    await page.unroute(summaryPattern, holdSummary);
  }
}

for (const state of majorStates) {
  test(`@certification ${state.name} has no serious or critical axe violations`, async ({ page, calendarAuthority }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    if (state.name === "Diary") {
      await certifyDiaryLoadingState(page, calendarAuthority.current_diary_date);
      return;
    }

    await page.goto(state.path);
    await expect(page.locator("main").first()).toBeVisible();

    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const blocking = result.violations.filter((violation) =>
      violation.impact === "serious" || violation.impact === "critical"
    );

    expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
  });
}
