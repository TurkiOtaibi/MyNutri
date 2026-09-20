import { randomUUID } from "node:crypto";
import type { Page } from "@playwright/test";
import type { LabCreateReceipt, LabCreateRequest, LabOverviewResponse } from "../../lib/types";
import { API_URL, expect, navigateToOwnerLabs, offsetIsoDate, test } from "./helpers";

const dialog = (page: Page) => page.getByRole("dialog", { name: "إضافة نتائج" });
const next = (page: Page) => dialog(page).getByRole("button", { name: "التالي", exact: true }).click();
const back = (page: Page) => dialog(page).getByRole("button", { name: "السابق", exact: true }).click();
const save = (page: Page) => dialog(page).getByRole("button", { name: "حفظ النتائج", exact: true }).click();

async function open(page: Page, keys: string[] = ["hba1c"], date?: string) {
  await page.getByRole("button", { name: "إضافة نتائج", exact: true }).click();
  await expect(dialog(page)).toBeVisible();
  if (date) await page.locator("#lab-batch-date").fill(date);
  await next(page);
  for (const key of keys) await page.locator(`[data-individual-key="${key}"]`).check();
  await next(page);
}

test.afterEach(async ({ labsApi }) => {
  // UI-created results belong only to this fresh synthetic fixture principal.
  for (const item of (await labsApi.overview()).items) {
    for (const result of (await labsApi.detail(item.test_key)).results) await labsApi.remove(result.id);
  }
});

test("a new session refreshes yesterday's cached server date and catalog action starts at date", async ({ labsPage: page, labsApi }) => {
  const today = (await labsApi.overview()).server_today;
  let reads = 0;
  await page.route(`${API_URL}/labs`, async (route) => {
    const response = await route.fetch();
    const body = await response.json() as LabOverviewResponse;
    reads += 1;
    await route.fulfill({ response, json: { ...body, server_today: reads === 1 ? offsetIsoDate(today, -1) : today } });
  });
  await navigateToOwnerLabs(page);
  await page.getByRole("tab", { name: "كل التحاليل" }).click();
  const opener = page.locator('[data-testid="lab-row"][data-test-key="hba1c"]').getByRole("button", { name: "إضافة نتيجة" });
  await opener.click();
  await expect(page.locator("#lab-batch-date")).toHaveValue(today);
  expect(reads).toBeGreaterThanOrEqual(2);
  await next(page);
  await expect(page.locator('[data-individual-key="hba1c"]')).toBeChecked();
  await next(page);
  await page.locator("#lab-hba1c-value").fill("5.270");
  await page.locator("#lab-hba1c-unit").selectOption("mmol/mol");
  await back(page); await back(page);
  await expect(page.locator("#lab-batch-date")).toHaveValue(today);
  await next(page); await next(page);
  await expect(page.locator("#lab-hba1c-value")).toHaveValue("5.270");
  await page.keyboard.press("Escape");
  await expect(dialog(page)).toHaveCount(0);
  await expect(opener).toBeFocused();
  await opener.click(); await next(page); await next(page);
  await expect(page.locator("#lab-hba1c-unit")).toHaveValue("%");
  await expect(page.locator("#lab-hba1c-value")).toHaveValue("");
});

test("panels plus individuals deduplicate, two panels render all rows, removing a panel retains individual values", async ({ labsPage: page }) => {
  await navigateToOwnerLabs(page);
  await page.getByRole("button", { name: "إضافة نتائج", exact: true }).click();
  await next(page);
  await page.locator('[data-panel-key="lipid_panel"]').check();
  await page.locator('[data-panel-key="iron_studies"]').check();
  await page.locator('[data-individual-key="ldl_c"]').check();
  await next(page);
  await expect(page.getByTestId("lab-batch-row")).toHaveCount(8);
  await expect(page.locator("#lab-ldl_c-value")).toHaveCount(1);
  await page.locator("#lab-ldl_c-value").fill("100.00");
  await page.locator("#lab-ldl_c-unit").selectOption("mmol/L");
  await back(page);
  await page.locator('[data-panel-key="lipid_panel"]').uncheck();
  await next(page);
  await expect(page.getByTestId("lab-batch-row")).toHaveCount(5);
  await expect(page.locator("#lab-ldl_c-value")).toHaveValue("100.00");
  await expect(page.locator("#lab-ldl_c-unit")).toHaveValue("mmol/L");
  expect(await page.getByTestId("lab-batch-row").evaluateAll((rows) => rows.map((row) => row.getAttribute("data-test-key"))))
    .toEqual(["ldl_c", "ferritin", "serum_iron", "tibc", "transferrin_saturation"]);
});

test("keyboard containment, previous steps, cancellation and reopening preserve or reset the appropriate state", async ({ labsPage: page }) => {
  await navigateToOwnerLabs(page);
  const opener = page.getByRole("button", { name: "إضافة نتائج", exact: true });
  await opener.focus(); await page.keyboard.press("Enter");
  await expect(page.locator("#lab-batch-date")).toBeFocused();
  for (let index = 0; index < 8; index += 1) {
    await page.keyboard.press(index % 2 ? "Shift+Tab" : "Tab");
    expect(await dialog(page).evaluate((element) => element.contains(document.activeElement))).toBe(true);
  }
  await next(page);
  await page.locator('[data-individual-key="hba1c"]').focus();
  await page.keyboard.press("Space");
  await next(page);
  await expect(page.locator("#lab-hba1c-value")).toBeFocused();
  await page.keyboard.type("5.270");
  await back(page); await next(page);
  await expect(page.locator("#lab-hba1c-value")).toHaveValue("5.270");
  await dialog(page).getByRole("button", { name: "إلغاء", exact: true }).click();
  await expect(opener).toBeFocused();
});

test("future-date rejection returns to the date step while retaining values and units", async ({ labsPage: page, labsApi }) => {
  const today = (await labsApi.overview()).server_today;
  await navigateToOwnerLabs(page);
  await open(page, ["hba1c"], offsetIsoDate(today, 1));
  await page.locator("#lab-hba1c-value").fill("35.00");
  await page.locator("#lab-hba1c-unit").selectOption("mmol/mol");
  await save(page);
  await expect(page.locator("#lab-batch-date")).toBeFocused();
  await expect(page.locator("#lab-batch-errors")).toContainText("لا يمكن اختيار تاريخ في المستقبل.");
  await page.locator("#lab-batch-date").fill(today);
  await next(page); await next(page);
  await expect(page.locator("#lab-hba1c-value")).toHaveValue("35.00");
  await expect(page.locator("#lab-hba1c-unit")).toHaveValue("mmol/mol");
  expect((await labsApi.detail("hba1c")).results).toHaveLength(0);
});

test("a later overview refresh never overwrites the active date or typed values", async ({ labsPage: page, labsApi }) => {
  const today = (await labsApi.overview()).server_today;
  await navigateToOwnerLabs(page);
  await open(page, ["hba1c"], offsetIsoDate(today, -2));
  await page.locator("#lab-hba1c-value").fill("5.270");
  const refreshed = page.waitForResponse((response) => response.url() === `${API_URL}/labs` && response.request().method() === "GET");
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  expect((await refreshed).status()).toBe(200);
  await expect(page.locator("#lab-hba1c-value")).toHaveValue("5.270");
  await back(page); await back(page);
  await expect(page.locator("#lab-batch-date")).toHaveValue(offsetIsoDate(today, -2));
});

test("whitespace is omitted, zero is saved, and no live medical status appears", async ({ labsPage: page, labsApi }) => {
  await navigateToOwnerLabs(page);
  const today = (await labsApi.overview()).server_today;
  await open(page, ["hba1c", "eosinophils_pct"], today);
  await expect(dialog(page).getByRole("button", { name: "حفظ النتائج" })).toBeDisabled();
  await page.locator("#lab-hba1c-value").fill(" \t");
  await page.locator("#lab-eosinophils_pct-value").fill("٠");
  await expect(dialog(page)).toContainText("سيتم حفظ 1 نتائج");
  await expect(dialog(page).locator("[data-tone]")).toHaveCount(0);
  const request = page.waitForRequest((request) => request.url() === `${API_URL}/labs/results` && request.method() === "POST");
  await save(page);
  expect((await request).postDataJSON()).toEqual({ test_date: today, results: [{ test_key: "eosinophils_pct", entered_value: "0", entered_unit: "%" }] });
  await expect(page.getByText("تم حفظ النتائج.", { exact: true })).toBeVisible();
  expect((await labsApi.detail("eosinophils_pct")).results).toHaveLength(1);
  expect((await labsApi.detail("hba1c")).results).toHaveLength(0);
});

for (const invalid of ["٬", "-2", "duplicate"]) {
  test(`atomic rejection preserves all fields and focuses first error: ${invalid}`, async ({ labsPage: page, labsApi }) => {
    await page.setViewportSize({ width: 390, height: 700 });
    const date = offsetIsoDate((await labsApi.overview()).server_today, -1);
    if (invalid === "duplicate") await labsApi.create(date, [{ test_key: "ferritin", entered_value: "7", entered_unit: "ng/mL" }]);
    await navigateToOwnerLabs(page);
    await open(page, ["hba1c", "ferritin"], date);
    await page.locator("#lab-hba1c-value").fill("5.270");
    await page.locator("#lab-ferritin-unit").selectOption("µg/L");
    await page.locator("#lab-ferritin-value").fill(invalid === "duplicate" ? "8" : invalid);
    await save(page);
    await expect(page.locator("#lab-ferritin-value")).toBeFocused();
    await expect(page.locator("#lab-ferritin-value")).toBeInViewport();
    await expect(page.locator("#lab-hba1c-value")).toHaveValue("5.270");
    await expect(page.locator("#lab-ferritin-value")).toHaveValue(invalid === "duplicate" ? "8" : invalid);
    await expect(page.locator("#lab-ferritin-unit")).toHaveValue("µg/L");
    await expect(dialog(page).locator("[data-tone]")).toHaveCount(0);
    expect((await labsApi.detail("hba1c")).results).toHaveLength(0);
    expect((await labsApi.detail("ferritin")).results).toHaveLength(invalid === "duplicate" ? 1 : 0);
    await back(page); await back(page);
    await expect(page.locator("#lab-batch-date")).toHaveValue(date);
  });
}

test("committed response loss freezes dismissal and retries the identical key/body/UUID receipt", async ({ labsPage: page, labsApi }) => {
  await navigateToOwnerLabs(page);
  const attempts: { key: string; body: string | null }[] = [];
  let committed: LabCreateReceipt | undefined;
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let committedReady!: () => void;
  const ready = new Promise<void>((resolve) => { committedReady = resolve; });
  await page.route(`${API_URL}/labs/results`, async (route) => {
    attempts.push({ key: route.request().headers()["idempotency-key"], body: route.request().postData() });
    const response = await route.fetch();
    expect(response.status()).toBe(201);
    if (attempts.length === 1) {
      committed = await response.json() as LabCreateReceipt;
      committedReady();
      await gate;
      await route.abort("connectionfailed");
    } else {
      expect(await response.json()).toEqual(committed);
      expect(response.headers()["idempotent-replayed"]).toBe("true");
      await route.fulfill({ response });
    }
  });
  try {
    await open(page);
    await page.locator("#lab-hba1c-value").fill("٥٫٢٧٠");
    await save(page);
    await ready;
    await page.keyboard.press("Escape");
    await expect(dialog(page)).toBeVisible();
    await expect(dialog(page).getByRole("button", { name: "إلغاء" })).toBeDisabled();
    release();
    await expect(dialog(page).getByRole("button", { name: "إعادة المحاولة" })).toBeVisible();
    await page.keyboard.press("Escape");
    await page.mouse.click(2, 2);
    await expect(dialog(page)).toBeVisible();
    await expect(page.locator("#lab-hba1c-value")).toBeDisabled();
    await dialog(page).getByRole("button", { name: "إعادة المحاولة" }).click();
    await expect(page.getByText("تم تأكيد نجاح عملية الحفظ السابقة.", { exact: true })).toBeVisible();
    expect(attempts).toHaveLength(2);
    expect(attempts[1]).toEqual(attempts[0]);
    expect((await labsApi.detail("hba1c")).results.map((result) => result.id)).toEqual(committed!.result_ids);
  } finally { release(); }
});

test("confirmed validation uses a new key after correction, and GET failure after save retries GET only", async ({ labsPage: page, labsApi }) => {
  await navigateToOwnerLabs(page);
  const attempts: { key: string; body: LabCreateRequest }[] = [];
  let failRead = false;
  await page.route(`${API_URL}/labs`, async (route) => {
    if (failRead) await route.fulfill({ status: 500, json: { detail: "unavailable" } });
    else await route.continue();
  });
  await page.route(`${API_URL}/labs/results`, async (route) => {
    attempts.push({ key: route.request().headers()["idempotency-key"], body: route.request().postDataJSON() as LabCreateRequest });
    const response = await route.fetch();
    if (response.status() === 201) failRead = true;
    await route.fulfill({ response });
  });
  await open(page);
  await page.locator("#lab-hba1c-value").fill("invalid");
  await save(page);
  await expect(page.locator("#lab-hba1c-value")).toBeFocused();
  await page.locator("#lab-hba1c-value").fill("5.270");
  await save(page);
  await expect(page.getByText("تم حفظ النتائج.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "إعادة تحميل التحاليل" })).toBeVisible();
  expect(attempts).toHaveLength(2);
  expect(attempts[0].key).not.toBe(attempts[1].key);
  failRead = false;
  await page.getByRole("button", { name: "إعادة تحميل التحاليل" }).click();
  await expect(page.getByTestId("lab-row")).toHaveCount(1);
  expect(attempts).toHaveLength(2);
  expect((await labsApi.detail("hba1c")).results).toHaveLength(1);
});

test("confirmed idempotency conflict keeps backend copy and editable draft, without ambiguous retry", async ({ labsPage: page }) => {
  await navigateToOwnerLabs(page);
  await page.route(`${API_URL}/labs/results`, (route) => route.fulfill({ status: 409, json: { detail: [{ loc: ["header", "Idempotency-Key"], field: "Idempotency-Key", code: "LAB_IDEMPOTENCY_CONFLICT", msg: "تغيّرت بيانات عملية سبق إرسالها بالمفتاح نفسه.", type: "LAB_IDEMPOTENCY_CONFLICT" }] } }));
  await open(page);
  await page.locator("#lab-hba1c-value").fill("5.270");
  await save(page);
  await expect(dialog(page).getByText("تغيّرت بيانات عملية سبق إرسالها بالمفتاح نفسه.", { exact: true })).toBeVisible();
  await expect(page.locator("#lab-hba1c-value")).toBeEnabled();
  await expect(page.locator("#lab-hba1c-value")).toHaveValue("5.270");
  await expect(dialog(page).getByRole("button", { name: "إعادة المحاولة" })).toHaveCount(0);
});

test("unknown 500 preserves the operation and deleted receipt results are never recreated by replay", async ({ labsPage: page, labsApi }) => {
  await navigateToOwnerLabs(page);
  let committed: LabCreateReceipt | undefined;
  const attempts: { key: string; body: string | null }[] = [];
  await page.route(`${API_URL}/labs/results`, async (route) => {
    attempts.push({ key: route.request().headers()["idempotency-key"], body: route.request().postData() });
    const response = await route.fetch();
    expect(response.status()).toBe(201);
    if (attempts.length === 1) {
      committed = await response.json() as LabCreateReceipt;
      await route.fulfill({ status: 500, json: { detail: "unknown outcome" } });
    } else {
      expect(await response.json()).toEqual(committed);
      await route.fulfill({ response });
    }
  });
  await open(page);
  await page.locator("#lab-hba1c-value").fill("5.270");
  await save(page);
  await expect(dialog(page).getByRole("button", { name: "إعادة المحاولة" })).toBeVisible();
  for (const id of committed!.result_ids) await labsApi.remove(id);
  await dialog(page).getByRole("button", { name: "إعادة المحاولة" }).click();
  await expect(page.getByText("تم تأكيد نجاح عملية الحفظ السابقة.", { exact: true })).toBeVisible();
  expect(attempts).toHaveLength(2);
  expect(attempts[1]).toEqual(attempts[0]);
  await expect(page.getByTestId("lab-row")).toHaveCount(0);
  expect((await labsApi.detail("hba1c")).results).toHaveLength(0);
});

test("delivered POST response after actor takeover cannot restore the old draft, toast, or query cache", async ({ labsPage: page, labsApi }) => {
  await page.addInitScript(() => {
    const original = window.fetch.bind(window);
    window.fetch = (input, init) => {
      const url = typeof input === "string" ? input : input instanceof Request ? input.url : input.href;
      if (new URL(url, location.href).pathname === "/labs/results" && init?.method === "POST") {
        const withoutSignal = { ...init }; delete withoutSignal.signal;
        return original(input, withoutSignal);
      }
      return original(input, init);
    };
  });
  await navigateToOwnerLabs(page);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let ready!: () => void;
  const started = new Promise<void>((resolve) => { ready = resolve; });
  await page.route(`${API_URL}/labs/results`, async (route) => {
    const response = await route.fetch();
    expect(response.status()).toBe(201);
    ready(); await gate; await route.fulfill({ response });
  });
  try {
    await open(page);
    await page.locator("#lab-hba1c-value").fill("5.270");
    await save(page); await started;
    const oldSubject = await page.evaluate(() => (window as Window & { __mynutriE2ESessionSubjectKey?: () => string }).__mynutriE2ESessionSubjectKey?.());
    const switched = await page.evaluate(async (email) => {
      const signIn = (window as Window & { __mynutriE2ESignInWithPassword?: (email: string, password: string) => Promise<{ error: unknown }> }).__mynutriE2ESignInWithPassword;
      if (!signIn) throw Error("Missing local auth fixture control");
      return signIn(email, "Labs-owner-password-2026!");
    }, `labs-takeover-${randomUUID()}@example.test`);
    expect(switched.error).toBeNull();
    await expect(dialog(page)).toHaveCount(0);
    const delivered = page.waitForResponse((response) => response.url() === `${API_URL}/labs/results` && response.request().method() === "POST");
    release();
    expect(await (await delivered).finished()).toBeNull();
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    await expect(page.getByText("تم حفظ النتائج.", { exact: true })).toHaveCount(0);
    await expect(page.getByText("تم تأكيد نجاح عملية الحفظ السابقة.", { exact: true })).toHaveCount(0);
    const keys = await page.evaluate(() => (window as Window & { __mynutriE2EQueryKeys?: () => string[] }).__mynutriE2EQueryKeys?.() ?? []);
    expect(keys.some((key) => key.includes(oldSubject!))).toBe(false);
    expect((await labsApi.detail("hba1c")).results).toHaveLength(1);
  } finally { release(); }
});
