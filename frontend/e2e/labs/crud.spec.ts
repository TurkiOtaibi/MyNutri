import { randomUUID } from "node:crypto";
import type { Page } from "@playwright/test";
import type { LabTestDetailResponse } from "../../lib/types";
import { API_URL, expect, offsetIsoDate, test, type LabsApi } from "./helpers";

const edit = (page: Page) => page.getByRole("dialog", { name: "تعديل النتيجة" });
const deletion = (page: Page) => page.getByRole("alertdialog", { name: "حذف النتيجة" });
const row = (page: Page, id: string) => page.locator(`[data-history-result="${id}"]`);
const save = (page: Page) => edit(page).getByRole("button", { name: "حفظ التعديل", exact: true }).click();
const confirmDelete = (page: Page) => deletion(page).getByRole("button", { name: "حذف النتيجة", exact: true }).click();
async function seed(api: LabsApi, offset = -2, value = "38.797950") {
  const date = offsetIsoDate((await api.overview()).server_today, offset);
  const { result_ids: [id] } = await api.create(date, [{ test_key: "hba1c", entered_value: value, entered_unit: "mmol/mol" }]);
  return { id, date };
}
async function open(page: Page, id: string, kind: "edit" | "delete" = "edit") {
  await row(page, id).getByRole("button", { name: kind === "edit" ? /^تعديل نتيجة/ : /^حذف نتيجة/ }).click();
  await expect(kind === "edit" ? edit(page) : deletion(page)).toBeVisible();
}

test("edit uses full entered precision and supported units, immutable identity and contained focus", async ({ labsPage: page, labsApi }) => {
  const { id, date } = await seed(labsApi);
  await page.goto("/labs/hba1c"); await open(page, id);
  await expect(page.locator("#lab-edit-value")).toHaveValue("38.797950");
  await expect(page.locator("#lab-edit-value")).toBeFocused();
  await expect(page.locator("#lab-edit-unit")).toHaveValue("mmol/mol");
  await expect(page.locator("#lab-edit-date")).toHaveValue(date);
  expect(await page.locator("#lab-edit-unit option").evaluateAll(options => options.map(option => (option as HTMLOptionElement).value)))
    .toEqual((await labsApi.detail("hba1c")).test.supported_units);
  await expect(edit(page).locator("[data-tone]")).toHaveCount(0);
  await expect(edit(page).getByText("نطاق ما قبل السكري")).toHaveCount(0);
  await expect(edit(page).locator("select")).toHaveCount(1);
  for (let index = 0; index < 8; index += 1) {
    await page.keyboard.press(index % 2 ? "Shift+Tab" : "Tab");
    expect(await edit(page).evaluate(element => element.contains(document.activeElement))).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(edit(page)).toHaveCount(0);
  await expect(row(page, id).getByRole("button", { name: /^تعديل نتيجة/ })).toBeFocused();
});

test("duplicate edit preserves all fields and focuses backend test_date despite immutable test_key", async ({ labsPage: page, labsApi }) => {
  const first = await seed(labsApi, -3), second = await seed(labsApi, -1);
  await page.goto("/labs/hba1c"); await open(page, first.id);
  await page.locator("#lab-edit-date").fill(second.date);
  await page.locator("#lab-edit-value").fill("6.2500");
  await page.locator("#lab-edit-unit").selectOption("%");
  await save(page);
  await expect(page.locator("#lab-edit-errors")).toContainText("توجد نتيجة لهذا التحليل في التاريخ المحدد.");
  await expect(page.locator("#lab-edit-date")).toBeFocused();
  await expect(page.locator("#lab-edit-date")).toHaveAttribute("aria-invalid", "true");
  await expect(page.locator("#lab-edit-value")).toHaveValue("6.2500");
  await expect(page.locator("#lab-edit-unit")).toHaveValue("%");
  expect((await labsApi.detail("hba1c")).results.find(item => item.id === first.id)?.test_date).toBe(first.date);
});

for (const scenario of ["future", "pre18"] as const) {
  test(`rejects ${scenario} date without discarding the entered triplet`, async ({ labsPage: page, labsApi }) => {
    const { id } = await seed(labsApi);
    const date = scenario === "future" ? offsetIsoDate((await labsApi.overview()).server_today, 1) : "2007-12-31"; // Fixture DOB is 1990-01-01.
    await page.goto("/labs/hba1c"); await open(page, id);
    await page.locator("#lab-edit-date").fill(date);
    await page.locator("#lab-edit-value").fill("38.70000");
    await save(page);
    await expect(page.locator("#lab-edit-errors")).toContainText(scenario === "future" ? "لا يمكن اختيار تاريخ في المستقبل." : "يمكن إضافة نتائج أُجريت عند عمر 18 سنة فأكثر فقط.");
    await expect(page.locator("#lab-edit-date")).toBeFocused();
    await expect(page.locator("#lab-edit-date")).toHaveValue(date);
    await expect(page.locator("#lab-edit-value")).toHaveValue("38.70000");
    await expect(page.locator("#lab-edit-unit")).toHaveValue("mmol/mol");
  });
}

test("confirmed edit changes unit, retained scale and independent batch date using only the editable triplet", async ({ labsPage: page, labsApi }) => {
  const date = offsetIsoDate((await labsApi.overview()).server_today, -3);
  await labsApi.create(date, [
    { test_key: "hba1c", entered_value: "38.797950", entered_unit: "mmol/mol" },
    { test_key: "ferritin", entered_value: "25.00", entered_unit: "ng/mL" },
  ]);
  const id = (await labsApi.detail("hba1c")).results[0].id;
  await page.goto("/labs/hba1c"); await open(page, id);
  await page.locator("#lab-edit-date").fill(offsetIsoDate(date, 1));
  await page.locator("#lab-edit-value").fill(" ٥٫٧٠٠٠ ");
  await page.locator("#lab-edit-unit").selectOption("%");
  const sent = page.waitForRequest(request => request.method() === "PATCH" && request.url() === `${API_URL}/labs/results/${id}`);
  await save(page);
  expect((await sent).postDataJSON()).toEqual({ test_date: offsetIsoDate(date, 1), entered_value: "5.7000", entered_unit: "%" });
  await expect(edit(page)).toHaveCount(0);
  await expect(page.getByText("تم حفظ التعديل.", { exact: true })).toBeVisible();
  expect((await labsApi.detail("hba1c")).results[0]).toMatchObject({ id, entered_value: "5.7000", entered_unit: "%", test_date: offsetIsoDate(date, 1) });
  expect((await labsApi.detail("ferritin")).results[0]).toMatchObject({ test_date: date, entered_value: "25.00" });
  await open(page, id);
  await expect(page.locator("#lab-edit-value")).toHaveValue("5.7000");
  await expect(page.locator("#lab-edit-unit")).toHaveValue("%");
});

test("first server error controls focus order independently of field display order", async ({ labsPage: page, labsApi }) => {
  const { id } = await seed(labsApi);
  await page.goto("/labs/hba1c"); await open(page, id);
  await page.route(`${API_URL}/labs/results/${id}`, route => route.fulfill({ status: 422, json: { detail: [
    { loc: ["body", "entered_unit"], field: "entered_unit", test_key: "hba1c", code: "LAB_UNIT_UNSUPPORTED", msg: "اختر وحدة مدعومة لهذا التحليل.", type: "value_error" },
    { loc: ["body", "entered_value"], field: "entered_value", code: "LAB_DECIMAL_INVALID", msg: "أدخل قيمة رقمية صريحة غير سالبة.", type: "value_error" },
  ] } }));
  await page.locator("#lab-edit-value").fill("-3"); await save(page);
  await expect(page.locator("#lab-edit-unit")).toBeFocused();
  await expect(page.locator("#lab-edit-unit")).toHaveAttribute("aria-invalid", "true");
  await expect(page.locator("#lab-edit-value")).toHaveAttribute("aria-invalid", "true");
  await expect(page.locator("#lab-edit-value")).toHaveValue("-3");
});

for (const value of ["-1", "1".repeat(129)]) {
  test(`backend rejects ${value.length > 128 ? "overlong" : "invalid"} value and keeps the raw input`, async ({ labsPage: page, labsApi }) => {
    const { id, date } = await seed(labsApi);
    await page.goto("/labs/hba1c"); await open(page, id);
    await page.locator("#lab-edit-value").fill(value); await save(page);
    await expect(page.locator("#lab-edit-value")).toBeFocused();
    await expect(page.locator("#lab-edit-value")).toHaveValue(value);
    await expect(page.locator("#lab-edit-date")).toHaveValue(date);
    await expect(page.locator("#lab-edit-unit")).toHaveValue("mmol/mol");
    await expect(page.locator("#lab-edit-errors")).toContainText(value.length > 128 ? "تتجاوز القيمة حد التخزين المسموح." : "أدخل قيمة رقمية صريحة غير سالبة.");
  });
}

test("a 404 edit preserves its draft and never recreates a deleted result", async ({ labsPage: page, labsApi }) => {
  const { id } = await seed(labsApi);
  await page.goto("/labs/hba1c"); await open(page, id);
  await labsApi.remove(id);
  let posts = 0;
  page.on("request", request => { if (request.method() === "POST" && request.url() === `${API_URL}/labs/results`) posts += 1; });
  await page.locator("#lab-edit-value").fill("40.000"); await save(page);
  await expect(edit(page)).toContainText("هذه النتيجة لم تعد موجودة.");
  await expect(page.locator("#lab-edit-value")).toHaveValue("40.000");
  await expect(edit(page).getByRole("button", { name: "حفظ التعديل" })).toHaveCount(0);
  await edit(page).getByRole("button", { name: "إعادة قراءة النتيجة" }).click();
  await expect(edit(page)).toContainText("هذه النتيجة لم تعد موجودة.");
  expect(posts).toBe(0);
});

for (const status of [401, 403]) {
  test(`PATCH ${status} stays request-level and retains the draft`, async ({ labsPage: page, labsApi }) => {
    const { id } = await seed(labsApi);
    await page.goto("/labs/hba1c"); await open(page, id);
    await page.route(`${API_URL}/labs/results/${id}`, route => route.fulfill({ status, json: { detail: "تعذر حفظ النتيجة." } }));
    await page.locator("#lab-edit-value").fill("39.000"); await save(page);
    await expect(page.locator("#lab-edit-errors")).toBeFocused();
    await expect(page.locator("#lab-edit-value")).toHaveValue("39.000");
    await expect(edit(page).locator('[aria-invalid="true"]')).toHaveCount(0);
    await expect(page.getByText("تم حفظ التعديل.", { exact: true })).toHaveCount(0);
  });
}

for (const outcome of ["matches", "different", "absent", "failed"] as const) {
  test(`ambiguous PATCH ${outcome} preserves frozen facts and offers GET-only recovery`, async ({ labsPage: page, labsApi }) => {
    const { id, date } = await seed(labsApi);
    await page.goto("/labs/hba1c"); await open(page, id);
    let patches = 0, posts = 0, failRead = outcome === "failed";
    page.on("request", request => { if (request.method() === "POST" && request.url() === `${API_URL}/labs/results`) posts += 1; });
    await page.route(`${API_URL}/labs/results/${id}`, async route => {
      patches += 1;
      expect(route.request().postDataJSON()).toEqual({ test_date: date, entered_value: "40.000", entered_unit: "mmol/mol" });
      const committed = await route.fetch(); expect(committed.status()).toBe(200);
      if (outcome === "different") await labsApi.patch(id, { test_date: date, entered_value: "41.00", entered_unit: "mmol/mol" });
      if (outcome === "absent") await labsApi.remove(id);
      await route.fulfill({ status: 500, json: { detail: "unknown outcome" } });
    });
    await page.route(`${API_URL}/labs/tests/hba1c`, async route => {
      if (failRead) await route.fulfill({ status: 503, json: { detail: "current read unavailable" } });
      else await route.continue();
    });
    await page.locator("#lab-edit-value").fill(" ٤٠٫٠٠٠ "); await save(page);
    await expect(edit(page)).toContainText(outcome === "matches" ? "القيم الحالية على الخادم تطابق القيم المرسلة" : outcome === "different" ? "تختلف النتيجة الحالية" : outcome === "absent" ? "هذه النتيجة لم تعد موجودة" : "تعذر تأكيد الحفظ أو قراءة النتيجة الحالية");
    await expect(page.locator("#lab-edit-value")).toHaveValue(" ٤٠٫٠٠٠ ");
    await expect(page.locator("#lab-edit-value")).toBeDisabled();
    await expect(edit(page).getByRole("button", { name: "حفظ التعديل" })).toHaveCount(0);
    await expect(page.getByText("تم حفظ التعديل.", { exact: true })).toHaveCount(0);
    if (outcome === "different") await expect(page.getByTestId("lab-current-facts")).toContainText("41.00 mmol/mol");
    failRead = false;
    await edit(page).getByRole("button", { name: "إعادة قراءة النتيجة" }).click();
    await expect(edit(page).getByRole("button", { name: "إغلاق", exact: true })).toBeEnabled();
    await expect(page.locator("#lab-edit-value")).toHaveValue(" ٤٠٫٠٠٠ ");
    expect(patches).toBe(1); expect(posts).toBe(0);
    await edit(page).getByRole("button", { name: "إغلاق", exact: true }).click();
    await expect(edit(page)).toHaveCount(0);
    if (outcome !== "absent") {
      await open(page, id);
      await expect(page.locator("#lab-edit-value")).toHaveValue(outcome === "different" ? "41.00" : "40.000");
      await expect(edit(page).getByRole("button", { name: "حفظ التعديل" })).toBeEnabled();
    }
  });
}

test("confirmed PATCH remains saved when subsequent current-data GET fails", async ({ labsPage: page, labsApi }) => {
  const { id } = await seed(labsApi);
  await page.goto("/labs/hba1c"); await open(page, id);
  await page.route(`${API_URL}/labs/tests/hba1c`, route => route.fulfill({ status: 503, json: { detail: "read unavailable" } }));
  await page.locator("#lab-edit-value").fill("40.00"); await save(page);
  await expect(page.getByText("تم حفظ التعديل.", { exact: true })).toBeVisible();
  await expect(edit(page)).toHaveCount(0);
  await expect(page.getByRole("alert")).toContainText("تعذر تحميل التحاليل الحالية.");
  expect((await labsApi.detail("hba1c")).results[0].entered_value).toBe("40.00");
});

test("delete cancellation identifies test/date, starts at cancel, restores opener and sends no DELETE", async ({ labsPage: page, labsApi }) => {
  const { id, date } = await seed(labsApi);
  let deletes = 0;
  page.on("request", request => { if (request.method() === "DELETE") deletes += 1; });
  await page.goto("/labs/hba1c"); await open(page, id, "delete");
  await expect(deletion(page)).toContainText(date);
  await expect(deletion(page)).toContainText((await labsApi.detail("hba1c")).test.name_ar);
  await expect(deletion(page).getByRole("button", { name: "إلغاء", exact: true })).toBeFocused();
  await deletion(page).getByRole("button", { name: "إلغاء", exact: true }).click();
  await expect(deletion(page)).toHaveCount(0);
  await expect(row(page, id).getByRole("button", { name: /^حذف نتيجة/ })).toBeFocused();
  expect(deletes).toBe(0);
});

for (const position of ["latest", "oldest", "final"] as const) {
  test(`deleting ${position} updates history, latest reference and owned list without removing catalog availability`, async ({ labsPage: page, labsApi }) => {
    const oldest = await seed(labsApi, -4), latest = position === "final" ? oldest : await seed(labsApi, -1, "45.0");
    const target = position === "latest" ? latest : oldest;
    await page.goto("/labs/hba1c"); await open(page, target.id, "delete"); await confirmDelete(page);
    await expect(deletion(page)).toHaveCount(0);
    await expect(page.getByText("تم حذف النتيجة.", { exact: true })).toBeVisible();
    await expect(row(page, target.id)).toHaveCount(0);
    const fresh = await labsApi.detail("hba1c");
    expect(fresh.results).toHaveLength(position === "final" ? 0 : 1);
    if (position === "final") {
      await expect(page.getByText("لا توجد نتائج مسجلة لهذا التحليل.", { exact: true })).toBeVisible();
      await expect(page.getByRole("button", { name: "إضافة نتيجة", exact: true })).toBeVisible();
      await page.goto("/labs");
      await expect(page.getByTestId("lab-row")).toHaveCount(0);
      await page.getByRole("tab", { name: "كل التحاليل" }).click();
      await expect(page.locator('[data-testid="lab-row"][data-test-key="hba1c"]').getByRole("button", { name: "إضافة نتيجة" })).toBeVisible();
    } else {
      await expect(page.locator("[data-reference-date]")).toHaveAttribute("data-reference-date", fresh.results[0].test_date);
      await expect(page.locator("[data-history-result]")).toHaveCount(1);
    }
  });
}

test("ambiguous DELETE retries only its original id; a retry 404 requires same-id absence proof", async ({ labsPage: page, labsApi }) => {
  const first = await seed(labsApi, -3), other = await seed(labsApi, -1);
  await page.goto("/labs/hba1c"); await open(page, first.id, "delete");
  const targets: string[] = [];
  await page.route(`${API_URL}/labs/results/*`, async route => {
    targets.push(route.request().url());
    if (targets.length === 1) await route.fulfill({ status: 503, json: { detail: "unknown outcome" } });
    else { await labsApi.remove(first.id); const response = await route.fetch(); expect(response.status()).toBe(404); await route.fulfill({ response }); }
  });
  await confirmDelete(page);
  await expect(deletion(page)).toContainText("النتيجة ما زالت موجودة.");
  await expect(deletion(page).getByRole("button", { name: "حذف النتيجة", exact: true })).toBeEnabled();
  await confirmDelete(page);
  await expect(deletion(page)).toHaveCount(0);
  expect(targets).toEqual([`${API_URL}/labs/results/${first.id}`, `${API_URL}/labs/results/${first.id}`]);
  expect((await labsApi.detail("hba1c")).results.map(result => result.id)).toEqual([other.id]);
});

test("lost DELETE response and failed read retains its target until GET proves absence", async ({ labsPage: page, labsApi }) => {
  const { id } = await seed(labsApi);
  await page.goto("/labs/hba1c"); await open(page, id, "delete");
  let deletes = 0, failRead = true;
  await page.route(`${API_URL}/labs/results/${id}`, async route => {
    deletes += 1; const response = await route.fetch(); expect(response.status()).toBe(204);
    await route.fulfill({ status: 500, json: { detail: "unknown outcome" } });
  });
  await page.route(`${API_URL}/labs/tests/hba1c`, async route => {
    if (failRead) await route.fulfill({ status: 503, json: { detail: "read unavailable" } }); else await route.continue();
  });
  await confirmDelete(page);
  await expect(deletion(page)).toContainText("تعذر تأكيد الحذف.");
  await expect(deletion(page).getByRole("button", { name: "حذف النتيجة", exact: true })).toBeDisabled();
  failRead = false;
  await deletion(page).getByRole("button", { name: "إعادة قراءة النتيجة" }).click();
  await expect(deletion(page)).toHaveCount(0);
  await expect(page.getByText("تم حذف النتيجة.", { exact: true })).toBeVisible();
  expect(deletes).toBe(1);
});

for (const kind of ["edit", "delete"] as const) {
  test(`${kind} blocks double submission and dismissal until the confirmed response`, async ({ labsPage: page, labsApi }) => {
    const { id } = await seed(labsApi);
    await page.goto("/labs/hba1c"); await open(page, id, kind);
    let release!: () => void, ready!: () => void, count = 0;
    const gate = new Promise<void>(resolve => { release = resolve; });
    const started = new Promise<void>(resolve => { ready = resolve; });
    await page.route(`${API_URL}/labs/results/${id}`, async route => {
      count += 1; const response = await route.fetch(); ready(); await gate; await route.fulfill({ response });
    });
    try {
      const currentDialog = kind === "edit" ? edit(page) : deletion(page);
      const button = currentDialog.getByRole("button", { name: kind === "edit" ? "حفظ التعديل" : "حذف النتيجة", exact: true });
      await button.evaluate(element => { (element as HTMLButtonElement).click(); (element as HTMLButtonElement).click(); });
      await started;
      await expect(currentDialog.getByRole("button", { name: "إلغاء", exact: true })).toBeDisabled();
      await page.keyboard.press("Escape"); await expect(currentDialog).toBeVisible();
      expect(count).toBe(1); release();
      await expect(currentDialog).toHaveCount(0); expect(count).toBe(1);
    } finally { release(); }
  });
}

for (const method of ["PATCH", "DELETE"] as const) {
  test(`delivered ${method} after actor takeover cannot restore draft, feedback or old cache`, async ({ labsPage: page, labsApi }) => {
    const { id } = await seed(labsApi);
    await page.addInitScript(method => {
      const original = window.fetch.bind(window);
      window.fetch = (input, init) => {
        const url = typeof input === "string" ? input : input instanceof Request ? input.url : input.href;
        if (new URL(url, location.href).pathname.startsWith("/labs/results/") && init?.method === method) {
          const withoutSignal = { ...init }; delete withoutSignal.signal; return original(input, withoutSignal);
        }
        return original(input, init);
      };
    }, method);
    await page.goto("/labs/hba1c"); await open(page, id, method === "PATCH" ? "edit" : "delete");
    let release!: () => void, ready!: () => void;
    const gate = new Promise<void>(resolve => { release = resolve; });
    const started = new Promise<void>(resolve => { ready = resolve; });
    await page.route(`${API_URL}/labs/results/${id}`, async route => {
      const response = await route.fetch(); expect(response.status()).toBe(method === "PATCH" ? 200 : 204);
      ready(); await gate; await route.fulfill({ status: 500, json: { detail: "unknown old actor outcome" } });
    });
    try {
      if (method === "PATCH") await save(page); else await confirmDelete(page);
      await started;
      const oldSubject = await page.evaluate(() => (window as Window & { __mynutriE2ESessionSubjectKey?: () => string }).__mynutriE2ESessionSubjectKey?.());
      const switched = await page.evaluate(async email => {
        const signIn = (window as Window & { __mynutriE2ESignInWithPassword?: (email: string, password: string) => Promise<{ error: unknown }> }).__mynutriE2ESignInWithPassword;
        if (!signIn) throw Error("Missing local auth fixture control");
        return signIn(email, "Labs-owner-password-2026!");
      }, `labs-crud-takeover-${randomUUID()}@example.test`);
      expect(switched.error).toBeNull();
      await expect(edit(page)).toHaveCount(0); await expect(deletion(page)).toHaveCount(0);
      const delivered = page.waitForResponse(response => response.url() === `${API_URL}/labs/results/${id}` && response.request().method() === method);
      release(); expect(await (await delivered).finished()).toBeNull();
      await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
      await expect(edit(page)).toHaveCount(0); await expect(deletion(page)).toHaveCount(0);
      await expect(page.getByText(/تم حفظ التعديل\.|تم حذف النتيجة\.|القيم الحالية على الخادم تطابق/)).toHaveCount(0);
      const keys = await page.evaluate(() => (window as Window & { __mynutriE2EQueryKeys?: () => string[] }).__mynutriE2EQueryKeys?.() ?? []);
      expect(keys.some(key => key.includes(oldSubject!))).toBe(false);
    } finally { release(); }
  });
}

test("owner deletion remains available when current detail reports add ineligibility", async ({ labsPage: page, labsApi }) => {
  const { id } = await seed(labsApi);
  await page.route(`${API_URL}/labs/tests/hba1c`, async route => {
    const response = await route.fetch(); const body = await response.json() as LabTestDetailResponse;
    await route.fulfill({ response, json: { ...body, eligibility: { allowed: false, reason: "profile_required" } } });
  });
  await page.goto("/labs/hba1c");
  await expect(page.getByRole("button", { name: "إضافة نتيجة", exact: true })).toHaveCount(0);
  await open(page, id, "delete"); await confirmDelete(page);
  await expect(deletion(page)).toHaveCount(0);
  expect((await labsApi.detail("hba1c")).results).toHaveLength(0);
});

test("admin selected-user and own details never mount edit/delete dialogs or mutation actions", async ({ page, labsApi }) => {
  await seed(labsApi);
  const writes: string[] = [];
  page.on("request", request => {
    if (["POST", "PATCH", "DELETE"].includes(request.method()) && new URL(request.url()).pathname.startsWith("/labs/results")) writes.push(request.url());
  });
  for (const path of [`/admin/users/${labsApi.actor.principalId}/labs/hba1c`, "/labs/hba1c"]) {
    await page.goto(path);
    await expect(page.getByText("للقراءة فقط", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: /إضافة|تعديل|حذف/ })).toHaveCount(0);
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.getByRole("alertdialog")).toHaveCount(0);
  }
  expect(writes).toEqual([]);
});
