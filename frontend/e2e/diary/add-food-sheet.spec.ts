import AxeBuilder from "@axe-core/playwright";
import type { Locator, Page } from "@playwright/test";

import {
  API_TOKEN,
  API_URL,
  diaryDate as localDate,
  expect,
  test,
  uniqueName
} from "../foods/helpers";

function pickerItem(index: number, name = `Picker Food ${index}`) {
  return {
    id: `00000000-0000-4000-8000-${String(index).padStart(12, "0")}`,
    name,
    brand: null,
    nutrition_basis: "per_100g",
    default_unit_type: "serving",
    unit_amount: 100,
    unit_basis: "g",
    calories: 100,
    protein_g: 10,
    carb_g: 15,
    fat_g: 3
  };
}

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((complete) => {
    resolve = complete;
  });
  return { promise, resolve };
}

type SafeActiveElementState = {
  tagName: string;
  role: string | null;
  accessibleName: string | null;
  id: string | null;
  disabled: boolean;
  connected: boolean;
  insideDialog: boolean;
  insideInert: boolean;
  insideAriaHidden: boolean;
  isBody: boolean;
  isDocumentElement: boolean;
};

async function safeActiveElementState(dialog: Locator): Promise<SafeActiveElementState> {
  return dialog.evaluate((panel) => {
    const active = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const safeNames = new Set([
      "إضافة طعام",
      "إضافة إلى الفطور",
      "جارٍ الإضافة…",
      "إعادة المحاولة",
      "إلغاء",
      "اسحب لأسفل لإغلاق إضافة الطعام",
      "إغلاق إضافة الطعام"
    ]);
    const normalize = (value: string | null | undefined) => value?.replace(/\s+/g, " ").trim() || null;
    const labelledBy = active?.getAttribute("aria-labelledby")
      ?.split(/\s+/)
      .map((id) => document.getElementById(id)?.textContent ?? "")
      .join(" ");
    const nameCandidate = normalize(active?.getAttribute("aria-label"))
      ?? normalize(labelledBy)
      ?? (active?.tagName === "BUTTON" ? normalize(active.textContent) : null);
    const safeId = active?.id && /^[A-Za-z][\w:.-]{0,79}$/.test(active.id) ? active.id : null;
    const implicitRole = active?.tagName === "BUTTON"
      ? "button"
      : active?.tagName === "INPUT"
        ? "textbox"
        : null;
    return {
      tagName: active?.tagName.toLowerCase() ?? "none",
      role: active?.getAttribute("role") ?? implicitRole,
      accessibleName: nameCandidate && safeNames.has(nameCandidate) ? nameCandidate : null,
      id: safeId,
      disabled: Boolean(active?.matches(":disabled") || active?.getAttribute("aria-disabled") === "true"),
      connected: Boolean(active?.isConnected),
      insideDialog: Boolean(active && panel.contains(active)),
      insideInert: Boolean(active?.closest("[inert]")),
      insideAriaHidden: Boolean(active?.closest('[aria-hidden="true"]')),
      isBody: active === document.body,
      isDocumentElement: active === document.documentElement
    };
  });
}

async function openGeneral(page: Page) {
  await page.goto("/diary");
  await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
  return page.getByRole("dialog", { name: "إضافة طعام" });
}

async function selectFood(page: Page, name: string) {
  const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
  await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(name);
  await dialog.getByRole("button", { name: new RegExp(name) }).click();
  return dialog;
}

test.describe("@diary @add-food-sheet focused Add Food experience", () => {
  test("@plan014 @p0 picker reads are bounded and never use full Food or lifetime Diary endpoints", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Bounded picker") });
    const apiOrigin = new URL(API_URL).origin;
    const pickerAudits: Array<Promise<void>> = [];
    const getUrls: URL[] = [];
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (request.method() === "GET" && url.origin === apiOrigin) getUrls.push(url);
    });
    page.on("response", (response) => {
      const url = new URL(response.url());
      if (url.origin !== apiOrigin || url.pathname !== "/foods/picker" || !response.ok()) return;
      pickerAudits.push((async () => {
        const requestedLimit = Number(url.searchParams.get("limit"));
        const body = await response.json() as { items: unknown[]; recent_items: unknown[] };
        expect(requestedLimit).toBeGreaterThanOrEqual(1);
        expect(requestedLimit).toBeLessThanOrEqual(30);
        expect(body.items.length).toBeLessThanOrEqual(requestedLimit);
        expect(body.recent_items.length).toBeLessThanOrEqual(5);
      })());
    });

    const dialog = await openGeneral(page);
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(food.name);
    await expect(dialog.getByRole("button", { name: new RegExp(food.name) })).toBeVisible();
    await Promise.all(pickerAudits);

    expect(getUrls.filter((url) => url.pathname === "/foods/picker").length).toBeGreaterThan(0);
    expect(getUrls.filter((url) => url.pathname === "/foods" && !url.search)).toHaveLength(0);
    expect(getUrls.filter((url) => url.pathname === "/diary" && !url.search)).toHaveLength(0);
  });

  test("@plan014 @p0 pagination appends stable bounded pages without duplicate Food IDs", async ({ page }) => {
    const firstPage = Array.from({ length: 30 }, (_, index) => pickerItem(index + 1));
    const secondPage = [pickerItem(31)];
    const cursors: Array<string | null> = [];
    await page.route("**/foods/picker?*", async (route) => {
      const cursor = new URL(route.request().url()).searchParams.get("cursor");
      cursors.push(cursor);
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          items: cursor ? secondPage : firstPage,
          recent_items: [],
          next_cursor: cursor ? null : "opaque-next"
        })
      });
    });

    const dialog = await openGeneral(page);
    const options = dialog.locator(".diary-food-option");
    await expect(dialog.getByRole("button", { name: /^Picker Food 1،/ })).toHaveCount(1);
    await expect(options).toHaveCount(30);
    await dialog.getByRole("button", { name: "عرض المزيد" }).click();
    await expect(dialog.getByRole("button", { name: /^Picker Food 31،/ })).toHaveCount(1);
    await expect(options).toHaveCount(31);
    for (let index = 1; index <= 31; index += 1) {
      await expect(dialog.getByRole("button", { name: new RegExp(`^Picker Food ${index}،`) })).toHaveCount(1);
    }
    expect(
      await options.evaluateAll((elements) =>
        elements.map((element) => element.getAttribute("aria-label")?.split("،", 1)[0])
      )
    ).toEqual([...firstPage, ...secondPage].map((food) => food.name));
    expect(cursors).toEqual([null, "opaque-next"]);
  });

  test("@plan014 @p0 stale search is cancelled and cannot replace the latest results", async ({ page }) => {
    const slowStarted = deferred();
    const releaseSlow = deferred();
    const slowFinished = deferred();
    const slowCancellationObserved = deferred();
    let slowCancellationKind: "request-failed" | "fulfill-rejected" | null = null;
    page.on("requestfailed", (request) => {
      const url = new URL(request.url());
      if (url.pathname === "/foods/picker" && url.searchParams.get("search") === "slow") {
        slowCancellationKind = "request-failed";
        slowCancellationObserved.resolve();
      }
    });
    await page.route("**/foods/picker?*", async (route) => {
      const search = new URL(route.request().url()).searchParams.get("search") ?? "";
      if (search === "slow") {
        slowStarted.resolve();
        await releaseSlow.promise;
        try {
          await route.fulfill({
            contentType: "application/json",
            body: JSON.stringify({
              items: [pickerItem(101, "slow result")],
              recent_items: [],
              next_cursor: null
            })
          });
        } catch {
          slowCancellationKind = "fulfill-rejected";
          slowCancellationObserved.resolve();
        } finally {
          slowFinished.resolve();
        }
        return;
      }
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          items: search ? [pickerItem(102, `${search} result`)] : [],
          recent_items: [],
          next_cursor: null
        })
      });
    });

    const dialog = await openGeneral(page);
    const search = dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية");
    await search.fill("slow");
    await slowStarted.promise;
    await search.fill("fast");
    await expect(dialog.getByRole("button", { name: /fast result/ })).toBeVisible();
    releaseSlow.resolve();
    await slowFinished.promise;
    await slowCancellationObserved.promise;
    await expect(dialog.getByRole("button", { name: /slow result/ })).toHaveCount(0);
    expect(slowCancellationKind).toMatch(/request-failed|fulfill-rejected/);
  });

  test("@p0 general Add opens search state with recent foods and no premature configure controls", async ({ page, foodsApi }) => {
    const recent = await foodsApi.create({ name: uniqueName("Recent sheet") });
    await foodsApi.createDiary(recent.id, localDate(), 1, "snack");
    const dialog = await openGeneral(page);
    await expect(dialog.getByRole("heading", { name: "إضافة طعام" })).toBeVisible();
    await expect(dialog.getByText("المستخدمة مؤخرًا", { exact: true })).toBeVisible();
    await expect(dialog.getByRole("button", { name: new RegExp(recent.name) })).toBeVisible();
    await expect(dialog.getByRole("heading", { name: "قسم الوجبة" })).toHaveCount(0);
    await expect(dialog.getByRole("button", { name: "إضافة الطعام", exact: true })).toHaveCount(0);
  });

  test("@plan014 @p0 recents de-duplicate repeated entries and exclude archived and deleted Foods", async ({ page, request, foodsApi }) => {
    const repeated = await foodsApi.create({ name: uniqueName("Repeated recent") });
    const archived = await foodsApi.create({ name: uniqueName("Archived recent") });
    const deleted = await foodsApi.create({ name: uniqueName("Deleted picker") });
    await foodsApi.createDiary(repeated.id, localDate(), 1, "snack");
    await foodsApi.createDiary(repeated.id, localDate(), 2, "lunch");
    await foodsApi.createDiary(archived.id, localDate(), 1, "snack");
    const headers = { Authorization: `Bearer ${API_TOKEN}` };
    const archivedResponse = await request.delete(`${API_URL}/admin/foods/${archived.id}`, { headers });
    expect(archivedResponse.status()).toBe(200);
    expect((await archivedResponse.json()).disposition).toBe("archived");
    const deletedResponse = await request.delete(`${API_URL}/admin/foods/${deleted.id}`, { headers });
    expect(deletedResponse.status()).toBe(200);
    expect((await deletedResponse.json()).disposition).toBe("deleted");

    const dialog = await openGeneral(page);
    await expect(dialog.getByRole("button", { name: new RegExp(repeated.name) })).toHaveCount(1);
    await expect(dialog.getByRole("button", { name: new RegExp(archived.name) })).toHaveCount(0);
    const search = dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية");
    await search.fill(deleted.name);
    await expect(dialog.getByRole("button", { name: new RegExp(deleted.name) })).toHaveCount(0);
  });

  test("@plan018 @p0 each meal Add action preserves its preselected meal and opener focus", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Meal preselect") });
    await page.goto("/diary");
    for (const [meal, label] of [["فطور", "الفطور"], ["غداء", "الغداء"], ["عشاء", "العشاء"], ["سناك", "السناك"]] as const) {
      const trigger = page.getByRole("button", { name: `إضافة طعام إلى ${meal}` });
      await trigger.click();
      const dialog = await selectFood(page, food.name);
      await expect(dialog.getByRole("radio", { name: meal })).toHaveAttribute("aria-checked", "true");
      await expect(dialog.getByRole("button", { name: `إضافة إلى ${label}` })).toBeEnabled();
      await dialog.getByRole("button", { name: "إلغاء" }).click();
      await page.getByRole("alertdialog", { name: "إلغاء إضافة الطعام؟" }).getByRole("button", { name: "إلغاء الإضافة" }).click();
      await expect(dialog).toHaveCount(0);
      await expect(trigger).toBeFocused();
    }
  });

  test("@p0 search supports Food name, brand, clear focus, and no-results copy", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Search name"), brand: uniqueName("BrandSearch") });
    const dialog = await openGeneral(page);
    const search = dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية");
    await search.fill(food.name);
    await expect(dialog.getByRole("button", { name: new RegExp(food.name) })).toBeVisible();
    await search.fill(food.brand!);
    await expect(dialog.getByRole("button", { name: new RegExp(food.name) })).toBeVisible();
    await dialog.getByRole("button", { name: "مسح البحث" }).click();
    await expect(search).toBeFocused();
    await search.fill(`No match ${Date.now()}`);
    await expect(dialog.getByText("لم نجد طعامًا مطابقًا")).toBeVisible();
    await expect(dialog.getByText("جرّب اسمًا آخر أو ابحث بالعلامة التجارية")).toBeVisible();
  });

  test("@plan014 @p0 picker result can be selected with the keyboard", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Keyboard picker") });
    const dialog = await openGeneral(page);
    const pickerResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return (
        url.origin === new URL(API_URL).origin
        && url.pathname === "/foods/picker"
        && response.request().method() === "GET"
        && response.request().resourceType() === "fetch"
        && url.searchParams.get("limit") === "30"
        && url.searchParams.get("search") === food.name
        && !url.searchParams.has("cursor")
      );
    });
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(food.name);
    const response = await pickerResponse;
    expect(response.status()).toBe(200);
    const body = await response.json() as { items: Array<{ id: string }> };
    expect(body.items.filter((item) => item.id === food.id)).toHaveLength(1);
    const option = dialog.getByRole("button", { name: new RegExp(food.name) });
    await expect(option).toHaveCount(1);
    await expect(option).toBeVisible();
    await option.focus();
    await expect(option).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(dialog.getByLabel(`الطعام المحدد: ${food.name}`)).toBeVisible();
  });

  test("@p1 loading, search error, and Retry are explicit without blank alerts", async ({ page }) => {
    const apiOrigin = new URL(API_URL).origin;
    const firstRequestStarted = deferred();
    const releaseFirstRequest = deferred();
    const pickerRequests: Array<{ method: string; origin: string; pathname: string }> = [];
    await page.route((url) => url.origin === apiOrigin && url.pathname === "/foods/picker", async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      pickerRequests.push({ method: request.method(), origin: url.origin, pathname: url.pathname });
      if (pickerRequests.length === 1) {
        firstRequestStarted.resolve();
        await releaseFirstRequest.promise;
      }
      if (pickerRequests.length <= 2) {
        return route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: "INTERNAL_ERROR",
              message_ar: "تعذر تحميل الأطعمة",
              details: {},
              request_id: "00000000-0000-4000-8000-000000000500"
            }
          })
        });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [pickerItem(500, "Retry picker result")],
          recent_items: [],
          next_cursor: null
        })
      });
    });
    const dialog = await openGeneral(page);
    await firstRequestStarted.promise;
    const loading = dialog.getByRole("status", { name: "جارٍ تحميل الأطعمة" });
    await expect(loading).toBeVisible();
    await expect(dialog.locator('[role="alert"]:empty')).toHaveCount(0);
    releaseFirstRequest.resolve();
    await expect(dialog.getByText("تعذر تحميل الأطعمة", { exact: true })).toBeVisible();
    await expect(loading).toHaveCount(0);
    await expect(dialog.locator(".diary-food-option")).toHaveCount(0);
    expect(pickerRequests).toHaveLength(2);
    await dialog.getByRole("button", { name: "إعادة المحاولة" }).click();
    await expect(dialog.getByRole("button", { name: /^Retry picker result،/ })).toHaveCount(1);
    await expect(dialog.getByText("تعذر تحميل الأطعمة", { exact: true })).toHaveCount(0);
    await expect(dialog.locator(".diary-food-option")).toHaveCount(1);
    expect(pickerRequests).toEqual([
      { method: "GET", origin: apiOrigin, pathname: "/foods/picker" },
      { method: "GET", origin: apiOrigin, pathname: "/foods/picker" },
      { method: "GET", origin: apiOrigin, pathname: "/foods/picker" }
    ]);
    await expect(dialog.locator('[role="alert"]:empty')).toHaveCount(0);
  });

  test("@p0 selection hides search and shows compact summary; Change restores query and resets next Food quantity", async ({ page, foodsApi }) => {
    const first = await foodsApi.create({ name: uniqueName("First select"), brand: "علامة أولى", default_unit_type: "piece", unit_amount: 14, calories: 493 });
    const second = await foodsApi.create({ name: uniqueName("Second select"), default_unit_type: "slice", unit_amount: 30 });
    const dialog = await openGeneral(page);
    const search = dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية");
    await search.fill(first.name);
    await dialog.getByRole("button", { name: new RegExp(first.name) }).click();
    await expect(search).toHaveCount(0);
    const summary = dialog.getByLabel(`الطعام المحدد: ${first.name}`);
    await expect(summary).toContainText("علامة أولى");
    await expect(summary).toContainText("14 جم");
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("2.5");
    await dialog.getByRole("button", { name: "تغيير الطعام" }).click();
    await expect(dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية")).toHaveValue(first.name);
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(second.name);
    await dialog.getByRole("button", { name: new RegExp(second.name) }).click();
    await expect(dialog.getByRole("textbox", { name: "الكمية", exact: true })).toHaveValue("1");
  });

  test("@p0 meal selection controls dynamic label and decimal preview", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Dynamic label"), default_unit_type: "piece", unit_amount: 20, calories: 250, protein_g: 10, carb_g: 20, fat_g: 5 });
    const dialog = await openGeneral(page);
    await selectFood(page, food.name);
    await expect(dialog.getByRole("radio", { name: "فطور" })).toHaveAttribute("aria-checked", "true");
    await dialog.getByRole("radio", { name: "غداء" }).click();
    await expect(dialog.getByRole("button", { name: "إضافة إلى الغداء" })).toBeEnabled();
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("2.5");
    const preview = dialog.getByLabel("معاينة القيم الغذائية");
    await expect(preview).toContainText("50 جم");
    await expect(preview).toContainText("125");
    await expect(preview).toContainText("5 جم");
    await expect(preview).toContainText("10 جم");
    await expect(preview).toContainText("2.5 جم");
  });

  test("@p0 save is single-submit, exposes saving state, and inserts into selected meal", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Single modern save") });
    const trigger = page.getByRole("button", { name: "إضافة طعام إلى فطور" });
    let posts = 0;
    const createPayloads: Array<Record<string, unknown>> = [];
    await page.route("**/diary", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      posts += 1;
      createPayloads.push(route.request().postDataJSON() as Record<string, unknown>);
      await new Promise((resolve) => setTimeout(resolve, 300));
      return route.continue();
    });
    const dialog = await openGeneral(page);
    await selectFood(page, food.name);
    await dialog.getByRole("radio", { name: "عشاء" }).click();
    const save = dialog.getByRole("button", { name: "إضافة إلى العشاء" });
    await save.dblclick();
    await expect(dialog.getByRole("button", { name: /جارٍ الإضافة|تمت الإضافة/ })).toBeVisible();
    await expect(dialog).toHaveCount(0);
    await expect(trigger).toBeFocused();
    expect(posts).toBe(1);
    expect(Object.keys(createPayloads[0] ?? {}).sort()).toEqual(["entry_date", "food_id", "meal_type", "quantity"]);
    expect(createPayloads[0]?.food_id).toBe(food.id);
    const dinner = page.locator("#meal-dinner");
    await expect(dinner.getByRole("heading", { name: food.name })).toBeVisible();
  });

  test("@p0 failed save preserves Food, meal, quantity and provides Retry", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Modern failed save") });
    await page.route("**/diary", (route) => route.request().method() === "POST" ? route.abort("failed") : route.continue());
    const dialog = await openGeneral(page);
    await selectFood(page, food.name);
    await dialog.getByRole("radio", { name: "سناك" }).click();
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("1.5");
    await dialog.getByRole("button", { name: "إضافة إلى السناك" }).click();
    await expect(dialog.getByText("تعذر إضافة الطعام")).toBeVisible();
    await expect(dialog.getByText("حاول مرة أخرى.")).toBeVisible();
    await expect(dialog.getByRole("button", { name: "إعادة المحاولة" })).toBeVisible();
    await expect(dialog.getByLabel(`الطعام المحدد: ${food.name}`)).toBeVisible();
    await expect(dialog.getByRole("radio", { name: "سناك" })).toHaveAttribute("aria-checked", "true");
    await expect(dialog.getByRole("textbox", { name: "الكمية", exact: true })).toHaveValue("1.5");
  });

  test("@plan018 @p0 Add Food owns forward and backward keyboard focus", async ({ page }) => {
    const trigger = page.getByRole("button", { name: "إضافة طعام إلى فطور" });
    await page.goto("/diary");
    await trigger.click();
    const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    const search = dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية");
    const dragHandle = dialog.getByRole("button", { name: "اسحب لأسفل لإغلاق إضافة الطعام" });
    const cancel = dialog.getByRole("button", { name: "إلغاء", exact: true });

    await expect(dialog).toHaveAccessibleDescription(/.+/);
    await expect(search).toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await page.keyboard.press("Shift+Tab");
    await page.keyboard.press("Shift+Tab");
    await expect(cancel).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(dragHandle).toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await expect(cancel).toBeFocused();

    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(trigger).toBeFocused();
  });

  test("@plan018 @p0 discard confirmation is the only active focus scope", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Nested focus") });
    const trigger = page.getByRole("button", { name: "إضافة طعام إلى فطور" });
    await page.goto("/diary");
    await trigger.click();
    const dialog = await selectFood(page, food.name);
    const parentCancel = dialog.getByRole("button", { name: "إلغاء", exact: true });
    await parentCancel.click();

    const confirmation = page.getByRole("alertdialog", { name: "إلغاء إضافة الطعام؟" });
    const continueEditing = confirmation.getByRole("button", { name: "متابعة التعديل" });
    const discard = confirmation.getByRole("button", { name: "إلغاء الإضافة" });
    const parentPanel = page.locator(".entry-sheet .diary-modal-panel");
    await expect(confirmation).toHaveAccessibleDescription("ستفقد التغييرات الحالية.");
    await expect(continueEditing).toBeFocused();
    await expect(parentPanel).toHaveAttribute("inert", "");
    await page.keyboard.press("Shift+Tab");
    await expect(discard).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(continueEditing).toBeFocused();
    const accessibility = await new AxeBuilder({ page }).include(".discard-confirm").analyze();
    expect(accessibility.violations.filter((violation) => ["serious", "critical"].includes(violation.impact ?? ""))).toEqual([]);
    await page.keyboard.press("Escape");
    await expect(confirmation).toHaveCount(0);
    await expect(parentCancel).toBeFocused();
    await expect(parentPanel).not.toHaveAttribute("inert", "");
    await expect(dialog.getByLabel(`الطعام المحدد: ${food.name}`)).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(confirmation).toBeVisible();
    await expect(continueEditing).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(parentCancel).toBeFocused();
    await parentCancel.click();
    await discard.click();
    await expect(dialog).toHaveCount(0);
    await expect(trigger).toBeFocused();
  });

  test("@plan018 @p1 rerenders keep focus inside the active Add Food scope", async ({ page }) => {
    const dialog = await openGeneral(page);
    const search = dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية");
    await search.fill(`focus stability ${Date.now()}`);
    await expect(search).toBeFocused();
    await expect(dialog.getByText("لم نجد طعامًا مطابقًا")).toBeVisible();
    await expect(search).toBeFocused();
    await expect.poll(() => page.evaluate(() => document.body.classList.contains("modal-open"))).toBe(true);

    const accessibility = await new AxeBuilder({ page }).include(".diary-modal-panel").analyze();
    expect(accessibility.violations.filter((violation) => ["serious", "critical"].includes(violation.impact ?? ""))).toEqual([]);
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
  });

  test("@plan018 @p0 pending save blocks dismissal without releasing focus", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Pending focus") });
    const requestStarted = deferred();
    const releaseResponse = deferred();
    const apiOrigin = new URL(API_URL).origin;
    let postCount = 0;
    await page.route((url) => url.origin === apiOrigin && url.pathname === "/diary", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      postCount += 1;
      requestStarted.resolve();
      await releaseResponse.promise;
      await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "fixture failure" }) });
    });

    const trigger = page.getByRole("button", { name: "إضافة طعام إلى فطور" });
    await page.goto("/diary");
    await trigger.click();
    const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await selectFood(page, food.name);
    const submit = dialog.getByRole("button", { name: "إضافة إلى الفطور" });
    const cancel = dialog.getByRole("button", { name: "إلغاء", exact: true });
    await page.keyboard.press("Shift+Tab");
    await expect(cancel).toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await expect(submit).toBeFocused();
    const beforeSubmit = await safeActiveElementState(dialog);
    expect(beforeSubmit.insideDialog, `before submit: ${JSON.stringify(beforeSubmit)}`).toBe(true);
    expect(beforeSubmit.accessibleName, `before submit: ${JSON.stringify(beforeSubmit)}`).toBe("إضافة إلى الفطور");
    await page.keyboard.press("Enter");
    await requestStarted.promise;
    expect(postCount).toBe(1);
    const pendingSubmit = dialog.getByRole("button", { name: "جارٍ الإضافة…" });
    await expect(pendingSubmit).toBeVisible();
    await expect(pendingSubmit).toBeDisabled();
    const duringPending = await safeActiveElementState(dialog);
    expect(duringPending.insideDialog, `during pending: ${JSON.stringify(duringPending)}`).toBe(true);
    expect(duringPending.isBody, `during pending: ${JSON.stringify(duringPending)}`).toBe(false);
    expect(duringPending.insideInert, `during pending: ${JSON.stringify(duringPending)}`).toBe(false);
    expect(duringPending.insideAriaHidden, `during pending: ${JSON.stringify(duringPending)}`).toBe(false);
    await expect(trigger).not.toBeFocused();
    const accessibility = await new AxeBuilder({ page }).include(".entry-sheet .diary-modal-panel").analyze();
    expect(accessibility.violations.filter((violation) => ["serious", "critical"].includes(violation.impact ?? ""))).toEqual([]);
    await page.keyboard.press("Escape");
    await expect(dialog).toBeVisible();
    await expect(page.getByRole("alertdialog", { name: "إلغاء إضافة الطعام؟" })).toHaveCount(0);
    let pendingFocus = await safeActiveElementState(dialog);
    expect(pendingFocus.insideDialog, `after pending Escape: ${JSON.stringify(pendingFocus)}`).toBe(true);
    await page.locator(".entry-sheet.diary-modal-backdrop").click({ position: { x: 2, y: 2 } });
    await expect(dialog).toBeVisible();
    await expect(page.getByRole("alertdialog", { name: "إلغاء إضافة الطعام؟" })).toHaveCount(0);
    pendingFocus = await safeActiveElementState(dialog);
    expect(pendingFocus.insideDialog, `after pending backdrop: ${JSON.stringify(pendingFocus)}`).toBe(true);
    await page.keyboard.press("Tab");
    pendingFocus = await safeActiveElementState(dialog);
    expect(pendingFocus.insideDialog, `after pending Tab: ${JSON.stringify(pendingFocus)}`).toBe(true);
    await page.keyboard.press("Shift+Tab");
    pendingFocus = await safeActiveElementState(dialog);
    expect(pendingFocus.insideDialog, `after pending Shift+Tab: ${JSON.stringify(pendingFocus)}`).toBe(true);
    expect(postCount).toBe(1);

    releaseResponse.resolve();
    await expect(dialog.getByText("تعذر إضافة الطعام")).toBeVisible();
    await expect(dialog.getByLabel(`الطعام المحدد: ${food.name}`)).toBeVisible();
    const afterFailure = await safeActiveElementState(dialog);
    expect(afterFailure.insideDialog, `after failure: ${JSON.stringify(afterFailure)}`).toBe(true);
    expect(afterFailure.isBody, `after failure: ${JSON.stringify(afterFailure)}`).toBe(false);
    expect(postCount).toBe(1);
    await page.keyboard.press("Escape");
    const confirmation = page.getByRole("alertdialog", { name: "إلغاء إضافة الطعام؟" });
    await expect(confirmation).toBeVisible();
    await confirmation.getByRole("button", { name: "إلغاء الإضافة" }).click();
    await expect(dialog).toHaveCount(0);
  });

  test("@p0 clean cancel closes immediately; meaningful changes require discard confirmation", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Discard") });
    let dialog = await openGeneral(page);
    await dialog.getByRole("button", { name: "إلغاء" }).click();
    await expect(dialog).toHaveCount(0);

    dialog = await openGeneral(page);
    await selectFood(page, food.name);
    await dialog.getByRole("button", { name: "إلغاء" }).click();
    const confirmation = page.getByRole("alertdialog", { name: "إلغاء إضافة الطعام؟" });
    await expect(confirmation).toContainText("ستفقد التغييرات الحالية.");
    await expect(confirmation.getByRole("button", { name: "متابعة التعديل" })).toBeFocused();
    await confirmation.getByRole("button", { name: "متابعة التعديل" }).click();
    await expect(dialog.getByLabel(`الطعام المحدد: ${food.name}`)).toBeVisible();
    await dialog.getByRole("button", { name: "إلغاء" }).click();
    await page.getByRole("alertdialog", { name: "إلغاء إضافة الطعام؟" }).getByRole("button", { name: "إلغاء الإضافة" }).click();
    await expect(dialog).toHaveCount(0);
  });

  test("@p1 responsive, safe-area, reduced-motion, and accessibility basics hold", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    for (const width of [320, 360, 390, 430]) {
      await page.setViewportSize({ width, height: 700 });
      const dialog = await openGeneral(page);
      await expect(dialog.getByRole("heading", { name: "إضافة طعام" })).toBeVisible();
      await expect(dialog.getByRole("button", { name: "إغلاق إضافة الطعام", exact: true })).toBeVisible();
      await expect(dialog.getByRole("button", { name: "اسحب لأسفل لإغلاق إضافة الطعام" })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
      const footer = dialog.locator(".add-sheet-footer");
      expect(await footer.evaluate((element) => getComputedStyle(element).paddingBottom)).not.toBe("0px");
      expect(await dialog.locator(".add-food-search-state").evaluate((element) => getComputedStyle(element).animationName)).toBe("none");
      await dialog.getByRole("button", { name: "إلغاء" }).click();
    }
  });
});
