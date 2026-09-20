import { expect, test, type APIRequestContext, type Browser, type BrowserContext, type Page, type Request } from "@playwright/test";
import type { ProfileInput } from "../lib/types";
import { fillRequiredFoodForm, submitFoodForm } from "./foods/helpers";
import { applyProfileThroughTargetPlan } from "./profile-api";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const AUTH_URL = process.env.PLAYWRIGHT_SUPABASE_URL ?? "http://127.0.0.1:8765";
const PASSWORD = "Session-isolation-password-2026!";
const ADMIN_EMAIL = "admin.e2e@example.test";
const ADMIN_PASSWORD = "E2e-only-password-2026!";

async function token(email: string, password = PASSWORD): Promise<string> {
  const response = await fetch(`${AUTH_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apikey: "e2e-public-key", "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
  expect(response.status).toBe(200);
  return ((await response.json()) as { access_token: string }).access_token;
}

function headers(accessToken: string) {
  return { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" };
}

function tokenSubject(accessToken: string): string {
  const payload = accessToken.split(".")[1];
  if (!payload) throw new Error("fixture token has no JWT payload");
  const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
  return (JSON.parse(Buffer.from(normalized, "base64").toString("utf8")) as { sub: string }).sub;
}

function profile(weight: number): ProfileInput {
  return {
    sex: "male",
    birth_date: "1990-01-01",
    height_cm: 175,
    weight_kg: weight,
    activity_level: "moderate",
    goal: "maintain",
    protein_per_kg: 1.2,
    fat_pct: 0.25,
    selected_cut_intensity: 0.2
  };
}

async function authoritativeDiaryDate(accessToken: string): Promise<string> {
  const response = await fetch(`${API_URL}/account/calendar`, { headers: headers(accessToken) });
  expect(response.status).toBe(200);
  return ((await response.json()) as { current_diary_date: string }).current_diary_date;
}

async function signIn(page: Page, email: string, password: string, next: string) {
  await page.goto(`/auth/login?next=${encodeURIComponent(next)}`);
  await submitLogin(page, email, password, next);
}

async function submitLogin(page: Page, email: string, password: string, next: string, waitForDestination = true) {
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.locator('button[type="submit"]').click();
  if (waitForDestination) await page.waitForURL(new RegExp(`${next.replace("/", "\\/")}$`));
}

type ReturnPathCase = {
  name: string;
  next: string | null;
  destination: string;
};

const postLoginReturnPathCases: ReturnPathCase[] = [
  { name: "missing", next: null, destination: "/diary" },
  { name: "empty", next: "", destination: "/diary" },
  { name: "absolute https", next: "https://attacker.example/owned", destination: "/diary" },
  { name: "protocol relative", next: "//attacker.example/owned", destination: "/diary" },
  { name: "backslash", next: "/\\attacker.example/owned", destination: "/diary" },
  { name: "mixed slash and backslash", next: "/\\/attacker.example/owned", destination: "/diary" },
  { name: "leading whitespace", next: " /profile", destination: "/diary" },
  { name: "control-prefixed", next: "\t/profile", destination: "/diary" },
  { name: "encoded separators", next: "/%2f%2fattacker.example/owned", destination: "/diary" },
  { name: "double-encoded separators", next: "/%252f%252fattacker.example/owned", destination: "/diary" },
  { name: "dot normalization", next: "/.//attacker.example/owned", destination: "/diary" },
  { name: "encoded dot normalization", next: "/%2e//attacker.example/owned", destination: "/diary" },
  { name: "encoded dotdot normalization", next: "/%2e%2e//attacker.example/owned", destination: "/diary" },
  { name: "nested dotdot normalization", next: "/safe/%2e%2e//attacker.example/owned", destination: "/diary" },
  { name: "internal query and fragment", next: "/diary?date=2026-07-26#summary", destination: "/diary?date=2026-07-26#summary" },
  { name: "internal query and fragment with spaces", next: "/diary?note=hello world#daily summary", destination: "/diary?note=hello%20world#daily%20summary" },
  { name: "internal query and fragment with encoded percent", next: "/diary?discount=100%25#save%25", destination: "/diary?discount=100%25#save%25" },
  { name: "encoded internal profile", next: "/profile", destination: "/profile" }
];

function authUrl(mode: "login" | "sign-up", next: string | null) {
  return `/auth/${mode}${next === null ? "" : `?next=${encodeURIComponent(next)}`}`;
}

async function submitAuthForm(page: Page, mode: "login" | "sign-up", email: string) {
  if (mode === "sign-up") await page.locator('input[autocomplete="name"]').fill("Plan 006 E2E User");
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.locator('button[type="submit"]').click();
}

async function assertSafePostLoginDestination(page: Page, origin: string, destination: string, hostileRequests: string[]) {
  await page.waitForURL((url) => url.origin === origin && `${url.pathname}${url.search}${url.hash}` === destination);
  const finalUrl = new URL(page.url());
  expect(finalUrl.origin).toBe(origin);
  expect(`${finalUrl.pathname}${finalUrl.search}${finalUrl.hash}`).toBe(destination);
  expect(hostileRequests).toEqual([]);
}

async function installLeakObserver(page: Page, textMarkers: string[], exactInputValues: string[] = [], recordAfterClear = false) {
  await page.evaluate(({ observedTextMarkers, observedInputValues, waitForClear }) => {
    const records: string[] = [];
    let readyToRecord = !waitForClear;
    const snapshot = () => {
      const inputValues = Array.from(document.querySelectorAll("input")).map((input) => input.value);
      const hasLeakedText = observedTextMarkers.some((marker) => document.body.innerText.includes(marker));
      const hasLeakedInput = observedInputValues.some((value) => inputValues.includes(value));
      if (!hasLeakedText && !hasLeakedInput) {
        if (waitForClear) readyToRecord = true;
        return;
      }
      if (readyToRecord) records.push(document.body.innerText);
    };
    new MutationObserver(snapshot).observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true
    });
    snapshot();
    (window as Window & { __sessionLeakRecords?: string[] }).__sessionLeakRecords = records;
  }, { observedTextMarkers: textMarkers, observedInputValues: exactInputValues, waitForClear: recordAfterClear });
}

async function leakRecords(page: Page) {
  return page.evaluate(() => {
    const records = (window as Window & { __sessionLeakRecords?: string[] }).__sessionLeakRecords;
    if (!records) throw new Error("Session leak observer is missing.");
    return records;
  });
}

type SessionBoundaryRotation = {
  sequence: number;
  fromSubjectKey: string;
  toSubjectKey: string;
  previousAbortedBefore: boolean;
  previousAbortedAfter: boolean;
};

type SessionInspectionWindow = Window & {
  __mynutriE2ESessionSignalAborted?: () => boolean;
  __mynutriE2ERetainedSessionSignalAborted?: () => boolean;
  __mynutriE2ESessionSubjectKey?: () => string;
  __mynutriE2ESessionBoundaryRotations?: () => SessionBoundaryRotation[];
};

async function sessionSignalAborted(page: Page) {
  return page.evaluate(() => {
    const inspect = (window as SessionInspectionWindow).__mynutriE2ESessionSignalAborted;
    if (!inspect) throw new Error("E2E session signal inspection hook is unavailable.");
    return inspect();
  });
}

async function retainSessionSignalInspector(page: Page) {
  await page.evaluate(() => {
    const testWindow = window as SessionInspectionWindow;
    if (!testWindow.__mynutriE2ESessionSignalAborted) {
      throw new Error("E2E session signal inspection hook is unavailable.");
    }
    testWindow.__mynutriE2ERetainedSessionSignalAborted = testWindow.__mynutriE2ESessionSignalAborted;
  });
}

async function retainedSessionSignalAborted(page: Page) {
  return page.evaluate(() => {
    const inspect = (window as SessionInspectionWindow).__mynutriE2ERetainedSessionSignalAborted;
    if (!inspect) throw new Error("Retained E2E session signal inspection hook is unavailable.");
    return inspect();
  });
}

async function sessionSubjectKey(page: Page) {
  return page.evaluate(() => {
    const inspect = (window as SessionInspectionWindow).__mynutriE2ESessionSubjectKey;
    if (!inspect) throw new Error("E2E session subject inspection hook is unavailable.");
    return inspect();
  });
}

async function sessionBoundaryRotations(page: Page) {
  return page.evaluate(() => {
    const inspect = (window as SessionInspectionWindow).__mynutriE2ESessionBoundaryRotations;
    if (!inspect) throw new Error("E2E session boundary rotation hook is unavailable.");
    return inspect();
  });
}

function createReleaseGate() {
  let resolveGate!: () => void;
  let released = false;
  const promise = new Promise<void>((resolve) => { resolveGate = resolve; });
  return {
    promise,
    get released() {
      return released;
    },
    release() {
      if (released) return;
      released = true;
      resolveGate();
    }
  };
}

async function e2eAuthAction(page: Page, action: "refresh" | "signOut" | "signIn" | "duplicate", credentials?: { email: string; password: string }) {
  const result = await page.evaluate(async ({ operation, login }) => {
    const testWindow = window as Window & {
      __mynutriE2ERefreshSession?: () => Promise<{ error: { message: string } | null }>;
      __mynutriE2ESignOut?: () => Promise<{ error: { message: string } | null }>;
      __mynutriE2ESignInWithPassword?: (email: string, password: string) => Promise<{ error: { message: string } | null }>;
      __mynutriE2EDuplicateSession?: () => Promise<void>;
    };
    const call = operation === "refresh" ? testWindow.__mynutriE2ERefreshSession : testWindow.__mynutriE2ESignOut;
    if (operation === "signIn") {
      if (!testWindow.__mynutriE2ESignInWithPassword || !login) throw new Error("Local E2E auth control is unavailable.");
      return testWindow.__mynutriE2ESignInWithPassword(login.email, login.password);
    }
    if (operation === "duplicate") {
      if (!testWindow.__mynutriE2EDuplicateSession) throw new Error("Local E2E auth control is unavailable.");
      await testWindow.__mynutriE2EDuplicateSession();
      return { error: null };
    }
    if (!call) throw new Error("Local E2E auth control is unavailable.");
    return call();
  }, { operation: action, login: credentials });
  expect(result.error).toBeNull();
}

type LabsIsolationActor = {
  email: string;
  token: string;
  subject: string;
  principalId: string;
  resultId: string;
  displayValue: string;
};

async function prepareLabsIsolation(browser: Browser, request: APIRequestContext) {
  const suffix = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const trackedResults = new Map<string, Set<string>>();
  const gates = new Set<ReturnType<typeof createReleaseGate>>();
  const cleanupTrackedResults = async () => {
    const failures: unknown[] = [];
    for (const [accessToken, ids] of trackedResults) {
      for (const id of ids) {
        try {
          const removed = await request.delete(`${API_URL}/labs/results/${encodeURIComponent(id)}`, { headers: headers(accessToken) });
          expect([204, 404]).toContain(removed.status());
        } catch (error) { failures.push(error); }
      }
    }
    return failures;
  };

  const createActor = async (label: string, enteredValue: string): Promise<LabsIsolationActor> => {
    const email = `labs-isolation-${label}-${suffix}@example.test`;
    const accessToken = await token(email);
    await applyProfileThroughTargetPlan(request, accessToken, profile(label === "a" ? 71 : 89));
    const account = await request.get(`${API_URL}/account/me`, { headers: headers(accessToken) });
    expect(account.status()).toBe(200);
    const principalId = (await account.json() as { principal_id: string }).principal_id;
    const overview = await request.get(`${API_URL}/labs`, { headers: headers(accessToken) });
    expect(overview.status()).toBe(200);
    const serverToday = (await overview.json() as { server_today: string }).server_today;
    const day = new Date(`${serverToday}T00:00:00Z`);
    day.setUTCDate(day.getUTCDate() - 2);
    const testDate = day.toISOString().slice(0, 10);
    const created = await request.post(`${API_URL}/labs/results`, {
      headers: { ...headers(accessToken), "Idempotency-Key": `labs-isolation-${label}-${suffix}` },
      data: { test_date: testDate, results: [{ test_key: "hba1c", entered_value: enteredValue, entered_unit: "%" }] },
    });
    expect(created.status(), await created.text()).toBe(201);
    const resultId = (await created.json() as { result_ids: string[] }).result_ids[0];
    trackedResults.set(accessToken, new Set([resultId]));
    const detail = await request.get(`${API_URL}/labs/tests/hba1c`, { headers: headers(accessToken) });
    expect(detail.status()).toBe(200);
    const result = (await detail.json() as { results: Array<{ id: string; display_value: string }> }).results
      .find((item) => item.id === resultId);
    if (!result) throw new Error("Synthetic Labs isolation result is missing.");
    return { email, token: accessToken, subject: tokenSubject(accessToken), principalId, resultId, displayValue: result.display_value };
  };

  let actorA!: LabsIsolationActor;
  let actorB!: LabsIsolationActor;
  let context!: BrowserContext;
  let page!: Page;
  try {
    actorA = await createActor("a", "98.7654321");
    actorB = await createActor("b", "1.23456789");
    context = await browser.newContext({ storageState: undefined });
    page = await context.newPage();
  } catch (primaryFailure) {
    const cleanupFailures = await cleanupTrackedResults();
    if (context) {
      try { await context.close(); } catch (error) { cleanupFailures.push(error); }
    }
    if (cleanupFailures.length) throw new AggregateError([primaryFailure, ...cleanupFailures], "Labs isolation setup and cleanup failed.");
    throw primaryFailure;
  }

  const holdGet = async (pathname: string, accessToken: string) => {
    const delivery = createReleaseGate();
    const started = createReleaseGate();
    gates.add(delivery);
    const response = page.waitForResponse((candidate) => {
      const requestEvent = candidate.request();
      return new URL(candidate.url()).pathname === pathname && requestEvent.method() === "GET"
        && requestEvent.headers()["authorization"] === `Bearer ${accessToken}`;
    });
    void response.catch(() => undefined);
    await page.route((url) => url.origin === new URL(API_URL).origin && url.pathname === pathname, async (route) => {
      if (route.request().headers()["authorization"] !== `Bearer ${accessToken}`) {
        await route.continue();
        return;
      }
      const upstream = await route.fetch();
      started.release();
      await delivery.promise;
      await route.fulfill({ response: upstream });
    });
    return {
      started: started.promise,
      response,
      release() { delivery.release(); },
    };
  };

  const queryKeys = () => page.evaluate(() => {
    const inspect = (window as Window & { __mynutriE2EQueryKeys?: () => string[] }).__mynutriE2EQueryKeys;
    if (!inspect) throw new Error("E2E query inspection hook is unavailable.");
    return inspect();
  });

  const assertNoActorAValuesOrInputs = async () => {
    await expect(page.getByText(actorA.displayValue, { exact: false })).toHaveCount(0);
    await expect(page.locator(`input[value="${actorA.displayValue}"]`)).toHaveCount(0);
    await expect(page.getByRole("dialog", { name: "إضافة نتائج" })).toHaveCount(0);
    await expect(page.getByText(/تم حفظ النتائج\.|تم حفظ التعديل\.|تعذر تأكيد الحفظ/)).toHaveCount(0);
    await expect(page.getByRole("alert")).toHaveCount(0);
    expect(await leakRecords(page)).toEqual([]);
  };

  const assertNoActorAQueryKeysOrPendingBatch = async () => {
    expect((await queryKeys()).some((key) => key.includes(actorA.subject) || key.includes(actorA.principalId))).toBe(false);
    await expect(page.locator("#lab-batch-date, [id^='lab-'][id$='-value']")).toHaveCount(0);
  };

  const track = (accessToken: string, id: string) => {
    const actorResults = trackedResults.get(accessToken) ?? new Set<string>();
    actorResults.add(id);
    trackedResults.set(accessToken, actorResults);
  };

  const close = async () => {
    const failures: unknown[] = [];
    for (const gate of gates) gate.release();
    try { await page.unrouteAll({ behavior: "wait" }); } catch (error) { failures.push(error); }
    try { await context.close(); } catch (error) { failures.push(error); }
    failures.push(...await cleanupTrackedResults());
    if (failures.length) throw new AggregateError(failures, "Labs isolation cleanup failed.");
  };

  return {
    page, actorA, actorB, holdGet, track, close,
    login: (actor: LabsIsolationActor, next: string, password = PASSWORD) => signIn(page, actor.email, password, next),
    assertNoActorAValuesOrInputs,
    assertNoActorAQueryKeysOrPendingBatch,
  };
}

async function withLabsIsolation(
  browser: Browser,
  request: APIRequestContext,
  work: (fixture: Awaited<ReturnType<typeof prepareLabsIsolation>>) => Promise<void>,
) {
  const fixture = await prepareLabsIsolation(browser, request);
  let primaryFailure: unknown;
  try { await work(fixture); } catch (error) { primaryFailure = error; }
  let cleanupFailure: unknown;
  try { await fixture.close(); } catch (error) { cleanupFailure = error; }
  if (primaryFailure && cleanupFailure) {
    throw new AggregateError([primaryFailure, cleanupFailure], "Labs isolation assertion and cleanup failed.");
  }
  if (primaryFailure) throw primaryFailure;
  if (cleanupFailure) throw cleanupFailure;
}

test("@plan016 @strictmode development StrictMode replay keeps one session and History API owner live", async ({ browser }) => {
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await page.goto("/auth/login");
  await expect(page.locator('input[type="email"]')).toBeVisible();
  await page.waitForFunction(() =>
    typeof (window as SessionInspectionWindow).__mynutriE2ESessionSignalAborted === "function"
  );
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  expect(await sessionSignalAborted(page)).toBe(false);
  expect(await sessionBoundaryRotations(page)).toEqual([]);
  const historyOwnership = await page.evaluate(() => {
    const marker = "__mynutriHistoryPosition";
    const before = Number((history.state as Record<string, unknown> | null)?.[marker] ?? 0);
    history.pushState({ strictModeProbe: true }, "", window.location.href);
    const afterPush = Number((history.state as Record<string, unknown> | null)?.[marker] ?? -1);
    history.replaceState({ strictModeProbe: "replaced" }, "", window.location.href);
    const afterReplace = Number((history.state as Record<string, unknown> | null)?.[marker] ?? -1);
    return { before, afterPush, afterReplace };
  });
  expect(historyOwnership.afterPush - historyOwnership.before).toBe(1);
  expect(historyOwnership.afterReplace).toBe(historyOwnership.afterPush);
  await context.close();
});

for (const mode of ["login", "sign-up"] as const) {
  for (const [index, scenario] of postLoginReturnPathCases.entries()) {
    test(`@plan006 ${mode} post-auth return path: ${scenario.name}`, async ({ browser }) => {
      const context = await browser.newContext({ storageState: undefined });
      const page = await context.newPage();
      const hostileRequests: string[] = [];
      page.on("request", (request) => {
        if (new URL(request.url()).hostname === "attacker.example") hostileRequests.push(request.url());
      });
      const email = `plan006-${mode}-${Date.now()}-${index}@example.test`;

      try {
        await test.step(scenario.name, async () => {
          if (mode === "login") await token(email);
          await page.goto(authUrl(mode, scenario.next));
          const origin = new URL(page.url()).origin;
          await submitAuthForm(page, mode, email);
          await assertSafePostLoginDestination(page, origin, scenario.destination, hostileRequests);
        });
      } finally {
        await context.close();
      }
    });
  }
}

test("@plan006 confirmation-required sign-up keeps its confirmation state without navigating", async ({ browser }) => {
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  const hostileRequests: string[] = [];
  let confirmationSignups = 0;
  page.on("request", (request) => {
    if (new URL(request.url()).hostname === "attacker.example") hostileRequests.push(request.url());
  });
  const authOrigin = new URL(AUTH_URL).origin;
  await page.route((url) => url.origin === authOrigin && url.pathname === "/auth/v1/signup", async (route) => {
    confirmationSignups += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-4000-8000-000000000006",
        aud: "authenticated",
        role: "authenticated",
        email: "plan006-confirmation@example.test",
        confirmation_sent_at: new Date().toISOString()
      })
    });
  });

  try {
    await page.goto(authUrl("sign-up", "//attacker.example/owned"));
    const origin = new URL(page.url()).origin;
    await submitAuthForm(page, "sign-up", `plan006-confirmation-${Date.now()}@example.test`);
    await expect(page.locator('[role="status"]')).toHaveText("تم إنشاء الحساب. تحقق من بريدك الإلكتروني لإكمال التسجيل.");
    expect(confirmationSignups).toBe(1);
    expect(new URL(page.url()).origin).toBe(origin);
    expect(new URL(page.url()).pathname).toBe("/auth/sign-up");
    expect(hostileRequests).toEqual([]);
  } finally {
    await context.close();
  }
});

test("same browser context isolates cached profile and diary data across A to B to A", async ({ browser, request }) => {
  const suffix = Date.now();
  const emailA = `session-a-${suffix}@example.test`;
  const emailB = `session-b-${suffix}@example.test`;
  const tokenA = await token(emailA);
  const tokenB = await token(emailB);
  const adminToken = await token(ADMIN_EMAIL, ADMIN_PASSWORD);
  await applyProfileThroughTargetPlan(request, tokenA, profile(71));
  await applyProfileThroughTargetPlan(request, tokenB, profile(89));

  const diaryNameA = `A diary marker ${suffix}`;
  const foodResponse = await request.post(`${API_URL}/foods`, {
    headers: headers(adminToken),
    data: {
      name: diaryNameA,
      primary_category: "other",
      subcategory: "other",
      nutrition_basis: "per_100g",
      default_unit_type: "serving",
      unit_amount: 100,
      unit_basis: "g",
      calories: 200,
      protein_g: 10,
      carb_g: 25,
      fat_g: 7,
      nutrition_data_source: "estimated",
      ingredients: null
    }
  });
  expect(foodResponse.status()).toBe(201);
  const food = await foodResponse.json() as { id: string };
  const diaryDate = await authoritativeDiaryDate(tokenA);
  const diaryResponse = await request.post(`${API_URL}/diary/entries`, {
    headers: headers(tokenA),
    data: {
      entry_date: diaryDate,
      food_id: food.id,
      quantity: 1,
      meal_type: "breakfast"
    }
  });
  expect(diaryResponse.status()).toBe(201);

  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  const historyMarkerA = `A target history marker ${suffix}`;
  let blockHistoryB = false;
  let historyBWasBlocked = false;
  let releaseHistoryB!: () => void;
  const historyBBlocked = new Promise<void>((resolve) => { releaseHistoryB = resolve; });
  await page.route(`${API_URL}/target-plans*`, async (route) => {
    if (blockHistoryB) {
      historyBWasBlocked = true;
      await historyBBlocked;
      await route.fulfill({ contentType: "application/json", body: JSON.stringify({ items: [], next_cursor: null }) });
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [{ id: `plan-${suffix}`, effective_from: historyMarkerA, revision: 1, created_at: "2026-08-01T12:00:00Z", targets: { target_calories: 2100 } }],
        next_cursor: null
      })
    });
  });
  await signIn(page, emailA, PASSWORD, "/profile");
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("71");
  await expect(page.getByText(historyMarkerA, { exact: true })).toBeVisible();
  await page.goto("/diary");
  await expect(page.getByText(diaryNameA, { exact: true })).toBeVisible();

  await page.locator(".nav-signout").click();
  await page.waitForURL(/\/auth\/login(?:\?.*)?$/);
  await expect(page.locator('input[type="email"]')).toBeVisible();
  blockHistoryB = true;
  await installLeakObserver(page, [emailA, diaryNameA, historyMarkerA], ["71"]);
  let releaseProfileB!: () => void;
  let profileBWasBlocked = false;
  const profileBBlocked = new Promise<void>((resolve) => { releaseProfileB = resolve; });
  await page.route(`${API_URL}/profile`, async (route) => {
    profileBWasBlocked = true;
    await profileBBlocked;
    await route.continue();
  });
  let releaseDiaryB!: () => void;
  let diaryBWasBlocked = false;
  const diaryBBlocked = new Promise<void>((resolve) => { releaseDiaryB = resolve; });
  await page.route(`${API_URL}/diary/entries*`, async (route) => {
    diaryBWasBlocked = true;
    await diaryBBlocked;
    await route.continue();
  });
  const diaryBResponse = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/diary/entries"
  );
  await submitLogin(page, emailB, PASSWORD, "/profile", false);
  await expect(page.locator('a[href="/profile"]')).toBeVisible();
  await expect.poll(() => diaryBWasBlocked).toBe(true);
  await expect(page.getByText(diaryNameA, { exact: true })).toHaveCount(0);
  expect(await leakRecords(page)).toEqual([]);
  releaseDiaryB();
  const response = await diaryBResponse;
  expect(response.status()).toBe(200);
  expect(await response.finished()).toBeNull();
  await expect(page.getByText(diaryNameA, { exact: true })).toHaveCount(0);
  expect(await leakRecords(page)).toEqual([]);
  await page.locator('a[href="/profile"]').click();
  await page.waitForURL(/\/profile$/);
  await expect.poll(() => profileBWasBlocked).toBe(true);
  await expect.poll(() => historyBWasBlocked).toBe(true);
  await expect.poll(() => page.locator('input[aria-label="الوزن"]').count()).toBe(0);
  expect(await leakRecords(page)).toEqual([]);
  await expect(page.locator('a[href="/admin"]')).toHaveCount(0);
  releaseHistoryB();
  releaseProfileB();
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("89");
  expect(await leakRecords(page)).toEqual([]);

  await page.locator(".nav-signout").click();
  await page.waitForURL(/\/auth\/login(?:\?.*)?$/);
  await expect(page.locator('input[type="email"]')).toBeVisible();
  await signIn(page, emailA, PASSWORD, "/profile");
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("71");
  await context.close();
});

test("@plan016 external A to B subject change clears A's dirty Profile registration synchronously", async ({ browser, request }) => {
  const suffix = Date.now();
  const emailA = `plan016-a-${suffix}@example.test`;
  const emailB = `plan016-b-${suffix}@example.test`;
  const tokenA = await token(emailA);
  const tokenB = await token(emailB);
  await applyProfileThroughTargetPlan(request, tokenA, profile(71));
  await applyProfileThroughTargetPlan(request, tokenB, profile(89));

  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await signIn(page, emailA, PASSWORD, "/profile");
  const weight = page.locator('input[aria-label="الوزن"]');
  await expect(weight).toHaveValue("71");
  await weight.fill("72");
  await installLeakObserver(page, [], ["72"], true);
  await e2eAuthAction(page, "signOut");
  await e2eAuthAction(page, "signIn", { email: emailB, password: PASSWORD });
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("89");
  await expect(page.getByRole("dialog", { name: "تغييرات غير محفوظة" })).toHaveCount(0);
  await expect(page.getByText("توجد نسخة أحدث من بيانات الملف على الخادم. احتفظنا بتعديلاتك الحالية.")).toHaveCount(0);
  expect(await leakRecords(page)).toEqual([]);
  await context.close();
});

test("@plan016 external Admin to User subject change clears a dirty Food draft before exposure", async ({ browser }) => {
  const emailB = `plan016-food-b-${Date.now()}@example.test`;
  await token(emailB);
  const marker = `Plan016 Admin-only draft ${Date.now()}`;
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await signIn(page, ADMIN_EMAIL, ADMIN_PASSWORD, "/foods/new");
  const name = page.locator("form.food-form-layout input").first();
  await name.fill(marker);
  await installLeakObserver(page, [marker], [marker], true);
  await e2eAuthAction(page, "signOut");
  await e2eAuthAction(page, "signIn", { email: emailB, password: PASSWORD });
  await expect(page.locator("form.food-form-layout")).toHaveCount(0);
  await expect(page.getByRole("dialog", { name: "تغييرات غير محفوظة" })).toHaveCount(0);
  expect(await leakRecords(page)).toEqual([]);
  await context.close();
});

test("a delivered delayed Admin account response cannot restore Admin identity after User B takes over", async ({ browser }) => {
  const emailB = `race-b-${Date.now()}@example.test`;
  await token(emailB);
  let releaseAdminAccount!: () => void;
  let adminAccountWasBlocked = false;
  let bAccountRequestedOnAdminPage = false;
  let delayedAdminRequest: Request | null = null;
  const adminAccountBlocked = new Promise<void>((resolve) => { releaseAdminAccount = resolve; });
  const context = await browser.newContext({ storageState: undefined });
  const adminPage = await context.newPage();

  await adminPage.addInitScript(() => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = (input, init) => {
      const url = typeof input === "string" ? input : input instanceof Request ? input.url : input.href;
      if (new URL(url, window.location.href).pathname === "/account/me" && init?.signal) {
        const withoutSignal = { ...init };
        delete withoutSignal.signal;
        return originalFetch(input, withoutSignal);
      }
      return originalFetch(input, init);
    };
  });
  await adminPage.route(`${API_URL}/account/me`, async (route) => {
    if (!adminAccountWasBlocked) {
      adminAccountWasBlocked = true;
      delayedAdminRequest = route.request();
      await adminAccountBlocked;
    } else {
      bAccountRequestedOnAdminPage = true;
    }
    await route.continue();
  });
  await signIn(adminPage, ADMIN_EMAIL, ADMIN_PASSWORD, "/profile");
  await expect.poll(() => adminAccountWasBlocked).toBe(true);
  const delayedAdminResponse = adminPage.waitForResponse((response) => response.request() === delayedAdminRequest);
  await installLeakObserver(adminPage, [ADMIN_EMAIL, "الإدارة"]);
  await e2eAuthAction(adminPage, "signOut");
  await e2eAuthAction(adminPage, "signIn", { email: emailB, password: PASSWORD });
  await expect.poll(() => bAccountRequestedOnAdminPage).toBe(true);
  await expect(adminPage.locator(".nav-signout")).toBeVisible();
  await expect(adminPage.locator('a[href="/admin"]')).toHaveCount(0);

  releaseAdminAccount();
  const response = await delayedAdminResponse;
  expect(await response.finished()).toBeNull();
  await adminPage.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  expect(await leakRecords(adminPage)).toEqual([]);
  await expect(adminPage.locator('a[href="/admin"]')).toHaveCount(0);
  await context.close();
});

test("a delivered delayed Admin food create cannot navigate or reveal its result after User B takes over", async ({ browser }) => {
  const suffix = Date.now();
  const emailB = `food-write-race-b-${suffix}@example.test`;
  const marker = `Admin stale food marker ${suffix}`;
  const staleFoodId = "00000000-0000-4000-8000-000000000991";
  await token(emailB);

  let createWasBlocked = false;
  let createAuthorization: string | undefined;
  let createName: string | undefined;
  let adminAccountAuthorization: string | undefined;
  let bAccountWasBlocked = false;
  let bAccountWasSettled = false;
  let bAccountAuthorization: string | undefined;
  let staleDetailRequested = false;
  const createGate = createReleaseGate();
  const bAccountGate = createReleaseGate();
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();

  // Force delivery after the subject boundary aborts so callback guards are
  // exercised independently from transport cancellation.
  await page.addInitScript(() => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = (input, init) => {
      const url = typeof input === "string" ? input : input instanceof Request ? input.url : input.href;
      if (
        new URL(url, window.location.href).pathname === "/foods" &&
        init?.method?.toUpperCase() === "POST" &&
        init.signal
      ) {
        const withoutSignal = { ...init };
        delete withoutSignal.signal;
        return originalFetch(input, withoutSignal);
      }
      return originalFetch(input, init);
    };
  });
  page.on("request", (request) => {
    if (request.url() === `${API_URL}/account/me` && !adminAccountAuthorization) {
      adminAccountAuthorization = request.headers()["authorization"];
    }
  });

  await signIn(page, ADMIN_EMAIL, ADMIN_PASSWORD, "/foods/new");
  await expect(page.locator("form.food-form-layout")).toBeVisible();
  expect(await sessionSignalAborted(page)).toBe(false);
  const adminSubjectKey = await sessionSubjectKey(page);
  await retainSessionSignalInspector(page);
  expect(adminAccountAuthorization).toMatch(/^Bearer /);
  await fillRequiredFoodForm(page, { name: marker });
  const originalUrl = page.url();

  await page.route(`${API_URL}/foods`, async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    createAuthorization = route.request().headers()["authorization"];
    createName = (route.request().postDataJSON() as { name?: string }).name;
    createWasBlocked = true;
    await createGate.promise;
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({ id: staleFoodId, name: marker })
    });
  });
  await page.route(`${API_URL}/account/me`, async (route) => {
    const authorization = route.request().headers()["authorization"];
    if (!authorization || authorization === adminAccountAuthorization) {
      await route.continue();
      return;
    }
    bAccountAuthorization = authorization;
    bAccountWasBlocked = true;
    await bAccountGate.promise;
    await route.continue();
  });
  await page.route(`${API_URL}/foods/${staleFoodId}`, async (route) => {
    staleDetailRequested = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ id: staleFoodId, name: marker })
    });
  });

  try {
    const delayedCreateResponse = page.waitForResponse((response) =>
      response.url() === `${API_URL}/foods` && response.request().method() === "POST"
    );
    void delayedCreateResponse.catch(() => undefined);
    await submitFoodForm(page);
    await expect.poll(() => createWasBlocked).toBe(true);

    await installLeakObserver(page, [marker], [marker], true);
    const bAccountResponse = page.waitForResponse((response) =>
      response.url() === `${API_URL}/account/me` &&
      response.request().headers()["authorization"] !== adminAccountAuthorization
    ).then((response) => {
      bAccountWasSettled = true;
      return response;
    });
    void bAccountResponse.catch(() => undefined);
    await e2eAuthAction(page, "signIn", { email: emailB, password: PASSWORD });
    await expect.poll(() => bAccountWasBlocked).toBe(true);

    createGate.release();
    const response = await delayedCreateResponse;
    expect(response.status()).toBe(201);
    expect(await response.finished()).toBeNull();

    const bSubjectKey = await sessionSubjectKey(page);
    const rotations = await sessionBoundaryRotations(page);
    const subjectRotation = [...rotations].reverse().find((rotation) =>
      rotation.fromSubjectKey === adminSubjectKey && rotation.toSubjectKey === bSubjectKey
    );
    if (!subjectRotation) throw new Error("Expected direct Admin-to-User boundary rotation record was not captured.");
    expect(subjectRotation.sequence).toBeGreaterThan(0);
    expect(subjectRotation.previousAbortedBefore).toBe(false);
    expect(subjectRotation.previousAbortedAfter).toBe(true);
    expect(await retainedSessionSignalAborted(page)).toBe(true);
    expect(await sessionSignalAborted(page)).toBe(false);
    expect(bAccountGate.released).toBe(false);

    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    await page.waitForTimeout(100);
    expect(createName).toBe(marker);
    expect(bAccountAuthorization).toMatch(/^Bearer /);
    expect(createAuthorization).toBe(adminAccountAuthorization);
    expect(createAuthorization).not.toBe(bAccountAuthorization);
    expect(staleDetailRequested).toBe(false);
    expect(await leakRecords(page)).toEqual([]);
    await expect(page).toHaveURL(originalUrl);
    await expect(page.locator('a[href="/admin"]')).toHaveCount(0);
    await expect(page.locator("form.food-form-layout")).toHaveCount(0);
    await expect(page.getByText(marker, { exact: true })).toHaveCount(0);

    expect(bAccountGate.released).toBe(false);
    expect(bAccountWasSettled).toBe(false);
    bAccountGate.release();
    const bResponse = await bAccountResponse;
    expect(bAccountWasSettled).toBe(true);
    expect(bResponse.status()).toBe(200);
    expect(bResponse.request().headers()["authorization"]).toBe(bAccountAuthorization);
    const bAccount = await bResponse.json() as { email: string | null; role: "user" | "admin" };
    expect(bAccount.email).toBe(emailB);
    expect(bAccount.role).toBe("user");
    await expect(page.locator(".nav-signout")).toBeVisible();
    await expect(page.locator('.state-note[role="alert"]')).toHaveText("إدارة الأطعمة متاحة للمشرف فقط.");
    expect(await leakRecords(page)).toEqual([]);
  } finally {
    createGate.release();
    bAccountGate.release();
    await context.close().catch(() => undefined);
  }
});

test("a stale User A 401 cannot clear User B's same-page session", async ({ browser }) => {
  const emailB = `401-race-b-${Date.now()}@example.test`;
  await token(emailB);
  let releaseA401!: () => void;
  let aRequestWasBlocked = false;
  let bRequestWasSeen = false;
  let aRequest: Request | null = null;
  const a401Blocked = new Promise<void>((resolve) => { releaseA401 = resolve; });
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await page.addInitScript(() => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = (input, init) => {
      const url = typeof input === "string" ? input : input instanceof Request ? input.url : input.href;
      if (new URL(url, window.location.href).pathname === "/account/me" && init?.signal) {
        const withoutSignal = { ...init };
        delete withoutSignal.signal;
        return originalFetch(input, withoutSignal);
      }
      return originalFetch(input, init);
    };
  });
  await page.route(`${API_URL}/account/me`, async (route) => {
    if (!aRequestWasBlocked) {
      aRequestWasBlocked = true;
      aRequest = route.request();
      await a401Blocked;
      await route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "expired" }) });
      return;
    }
    bRequestWasSeen = true;
    await route.continue();
  });
  await signIn(page, ADMIN_EMAIL, ADMIN_PASSWORD, "/profile");
  await expect.poll(() => aRequestWasBlocked).toBe(true);
  const staleResponse = page.waitForResponse((response) => response.request() === aRequest);
  await installLeakObserver(page, [ADMIN_EMAIL, "الإدارة"]);
  await e2eAuthAction(page, "signOut");
  await e2eAuthAction(page, "signIn", { email: emailB, password: PASSWORD });
  await expect.poll(() => bRequestWasSeen).toBe(true);
  await expect(page.locator(".nav-signout")).toBeVisible();
  releaseA401();
  expect((await staleResponse).status()).toBe(401);
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await expect(page).not.toHaveURL(/\/auth\/login/);
  await expect(page.locator('a[href="/admin"]')).toHaveCount(0);
  expect(await leakRecords(page)).toEqual([]);
  await context.close();
});

test("a same-subject refresh during a held 401 fingerprint stage cannot redirect", async ({ browser }) => {
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  const owner = `held-fingerprint-${Date.now()}`;
  try {
    let firstAccountRequest = true;
    await page.route(`${API_URL}/account/me`, async (route) => {
      if (firstAccountRequest) {
        firstAccountRequest = false;
        await route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "expired" }) });
        return;
      }
      await route.continue();
    });
    await page.goto("/auth/login?next=%2Fprofile");
    await page.evaluate((hookOwner) => {
      type OwnedCallback = (() => void) & { __mynutriOwner?: string };
      type HeldFingerprintHook = (() => Promise<void>) & { __mynutriOwner?: string };
      const testWindow = window as Window & {
        __mynutriE2EHoldFingerprint?: HeldFingerprintHook;
        __releaseFingerprint?: OwnedCallback;
        __fingerprintHeld?: boolean;
      };
      let release!: OwnedCallback;
      const held = new Promise<void>((resolve) => {
        release = () => resolve();
      });
      release.__mynutriOwner = hookOwner;
      const holdFingerprint: HeldFingerprintHook = () => {
        testWindow.__fingerprintHeld = true;
        return held;
      };
      holdFingerprint.__mynutriOwner = hookOwner;
      testWindow.__mynutriE2EHoldFingerprint = holdFingerprint;
      testWindow.__releaseFingerprint = release;
    }, owner);
    await submitLogin(page, ADMIN_EMAIL, ADMIN_PASSWORD, "/profile", false);
    await expect.poll(() => page.evaluate(() => Boolean((window as Window & { __fingerprintHeld?: boolean }).__fingerprintHeld))).toBe(true);
    await e2eAuthAction(page, "refresh");
    await page.evaluate(() => (window as Window & { __releaseFingerprint?: () => void }).__releaseFingerprint?.());
    await expect(page.locator(".nav-signout")).toBeVisible();
    await expect(page).not.toHaveURL(/\/auth\/login/);
    expect(await page.evaluate(() => document.cookie.includes("mynutri-auth-invalid-token"))).toBe(false);
  } finally {
    await page.evaluate((hookOwner) => {
      type OwnedCallback = (() => void) & { __mynutriOwner?: string };
      type HeldFingerprintHook = (() => Promise<void>) & { __mynutriOwner?: string };
      const testWindow = window as Window & {
        __mynutriE2EHoldFingerprint?: HeldFingerprintHook;
        __releaseFingerprint?: OwnedCallback;
        __fingerprintHeld?: boolean;
      };
      const ownsHoldFingerprint = testWindow.__mynutriE2EHoldFingerprint?.__mynutriOwner === hookOwner;
      const ownsReleaseFingerprint = testWindow.__releaseFingerprint?.__mynutriOwner === hookOwner;
      if (ownsReleaseFingerprint) testWindow.__releaseFingerprint?.();
      if (ownsHoldFingerprint) {
        delete testWindow.__mynutriE2EHoldFingerprint;
        delete testWindow.__fingerprintHeld;
      }
      if (ownsReleaseFingerprint) delete testWindow.__releaseFingerprint;
    }, owner).catch(() => undefined);
    await context.close();
  }
});

test("a current account 401 clears the matching session before showing login", async ({ browser }) => {
  const emailB = `current-401-b-${Date.now()}@example.test`;
  await token(emailB);
  let aRequest = true;
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await page.route(`${API_URL}/account/me`, async (route) => {
    if (aRequest) {
      aRequest = false;
      await route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "expired" }) });
      return;
    }
    await route.continue();
  });
  await page.goto("/auth/login?next=%2Fprofile");
  const accountResponse = page.waitForResponse((response) => response.url() === `${API_URL}/account/me`);
  await submitLogin(page, ADMIN_EMAIL, ADMIN_PASSWORD, "/profile", false);
  expect((await accountResponse).status()).toBe(401);
  await page.waitForURL(/\/auth\/login(?:\?.*)?$/);
  expect(new URL(page.url()).searchParams.get("next")).toBe("/profile");
  await expect(page.locator('input[type="email"]')).toBeVisible();
  await expect(page.locator('a[href="/admin"]')).toHaveCount(0);
  expect(await page.evaluate(() => document.cookie.includes("mynutri-auth-invalid-token"))).toBe(true);
  await submitLogin(page, ADMIN_EMAIL, ADMIN_PASSWORD, "/profile", false);
  await expect(page.locator(".nav-signout")).toBeVisible();
  await expect(page.locator('a[href="/admin"]')).toBeVisible();
  await expect(page).not.toHaveURL(/\/auth\/login/);
  await page.locator(".nav-signout").click();
  await page.waitForURL(/\/auth\/login(?:\?.*)?$/);
  await submitLogin(page, emailB, PASSWORD, "/profile", false);
  await expect(page.locator(".nav-signout")).toBeVisible();
  await expect(page).not.toHaveURL(/\/auth\/login/);
  await expect(page.locator('a[href="/admin"]')).toHaveCount(0);
  await context.close();
});

test("Admin private list and detail caches disappear when the same browser context becomes User B", async ({ browser, request }) => {
  const suffix = Date.now();
  const emailB = `admin-cache-b-${suffix}@example.test`;
  const emailMonitored = `admin-cache-monitored-${suffix}@example.test`;
  const tokenB = await token(emailB);
  const tokenMonitored = await token(emailMonitored);
  const adminToken = await token(ADMIN_EMAIL, ADMIN_PASSWORD);
  await applyProfileThroughTargetPlan(request, tokenB, profile(83));
  const monitoredAccount = await request.get(`${API_URL}/account/me`, { headers: headers(tokenMonitored) });
  expect(monitoredAccount.status()).toBe(200);
  const monitoredPrincipalId = (await monitoredAccount.json() as { principal_id: string }).principal_id;
  expect((await request.get(`${API_URL}/account/me`, { headers: headers(adminToken) })).status()).toBe(200);

  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await signIn(page, ADMIN_EMAIL, ADMIN_PASSWORD, "/admin/users");
  await expect(page.getByText(emailMonitored, { exact: true })).toBeVisible();
  await page.locator(`a[href="/admin/users/${monitoredPrincipalId}"]`).click();
  await page.waitForURL(new RegExp(`/admin/users/${monitoredPrincipalId}$`));
  await expect(page.locator(".selected-user-banner")).toBeVisible();
  await expect(page.getByText(emailMonitored, { exact: true })).toBeVisible();
  expect(await page.evaluate(() => {
    const inspect = (window as Window & { __mynutriE2EQueryKeys?: () => string[] }).__mynutriE2EQueryKeys;
    if (!inspect) throw new Error("E2E query inspection hook is unavailable.");
    const roots = inspect().map((key) => JSON.parse(key)[0]);
    return roots.includes("admin-users") && roots.includes("admin-user");
  })).toBe(true);

  await page.locator(".nav-signout").click();
  await page.waitForURL(/\/auth\/login(?:\?.*)?$/);
  await expect(page.locator('input[type="email"]')).toBeVisible();
  await installLeakObserver(page, [emailMonitored, ADMIN_EMAIL]);
  let releaseProfileB!: () => void;
  let profileBWasBlocked = false;
  const profileBBlocked = new Promise<void>((resolve) => { releaseProfileB = resolve; });
  await page.route(`${API_URL}/profile`, async (route) => {
    profileBWasBlocked = true;
    await profileBBlocked;
    await route.continue();
  });
  await submitLogin(page, emailB, PASSWORD, "/profile", false);
  await expect(page.locator('a[href="/profile"]')).toBeVisible();
  await page.locator('a[href="/profile"]').click();
  await page.waitForURL(/\/profile$/);
  await expect.poll(() => profileBWasBlocked).toBe(true);
  await expect(page.locator(".selected-user-banner")).toHaveCount(0);
  await expect(page.locator(".admin-user-row")).toHaveCount(0);
  await expect(page.locator('a[href="/admin"]')).toHaveCount(0);
  expect(await page.evaluate(() => {
    const inspect = (window as Window & { __mynutriE2EQueryKeys?: () => string[] }).__mynutriE2EQueryKeys;
    if (!inspect) throw new Error("E2E query inspection hook is unavailable.");
    const roots = inspect().map((key) => JSON.parse(key)[0]);
    return roots.includes("admin-users") || roots.includes("admin-user");
  })).toBe(false);
  expect(await leakRecords(page)).toEqual([]);
  releaseProfileB();
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("83");
  expect(await leakRecords(page)).toEqual([]);
  await context.close();
});

test("a refresh-token session update keeps User A's query client and does not request another subject's profile", async ({ browser, request }) => {
  const suffix = Date.now();
  const emailA = `refresh-a-${suffix}@example.test`;
  const tokenA = await token(emailA);
  await applyProfileThroughTargetPlan(request, tokenA, profile(74));

  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await signIn(page, emailA, PASSWORD, "/profile");
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("74");
  let accountRequestsAfterRefresh = 0;
  let profileRequestsAfterRefresh = 0;
  page.on("request", (requestEvent) => {
    if (requestEvent.url() === `${API_URL}/account/me`) accountRequestsAfterRefresh += 1;
    if (requestEvent.url() === `${API_URL}/profile`) profileRequestsAfterRefresh += 1;
  });

  let releaseAccountRefresh!: () => void;
  let accountRefreshWasBlocked = false;
  const accountRefreshBlocked = new Promise<void>((resolve) => { releaseAccountRefresh = resolve; });
  await page.route(`${API_URL}/account/me`, async (route) => {
    accountRefreshWasBlocked = true;
    await accountRefreshBlocked;
    await route.continue();
  });
  await e2eAuthAction(page, "refresh");
  await expect.poll(() => accountRefreshWasBlocked).toBe(true);
  await e2eAuthAction(page, "duplicate");
  releaseAccountRefresh();
  await expect.poll(() => accountRequestsAfterRefresh).toBeGreaterThanOrEqual(1);
  await expect(page.locator(".nav-signout")).toBeVisible();
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("74");
  expect(profileRequestsAfterRefresh).toBe(0);
  await context.close();
});

test("@strictmode Labs old owner detail cannot repopulate a new actor session", async ({ browser, request }) => {
  await withLabsIsolation(browser, request, async (fixture) => {
    const { page, actorA, actorB } = fixture;
    await page.addInitScript(({ apiOrigin, path }) => {
      const original = window.fetch.bind(window);
      window.fetch = (input, init) => {
        const url = new URL(typeof input === "string" ? input : input instanceof Request ? input.url : input.href, location.href);
        if (url.origin === apiOrigin && url.pathname === path && (!init?.method || init.method === "GET")) {
          const withoutSignal = { ...init }; delete withoutSignal.signal;
          return original(input, withoutSignal);
        }
        return original(input, init);
      };
    }, { apiOrigin: new URL(API_URL).origin, path: "/labs/tests/hba1c" });
    await fixture.login(actorA, "/labs");
    await retainSessionSignalInspector(page);
    const pending = await fixture.holdGet("/labs/tests/hba1c", actorA.token);
    await page.getByRole("tab", { name: "كل التحاليل", exact: true }).click();
    await page.locator('[data-testid="lab-row"][data-test-key="hba1c"] a').click();
    await pending.started;
    await installLeakObserver(page, [actorA.displayValue, actorA.resultId], [actorA.displayValue], true);
    await e2eAuthAction(page, "signIn", { email: actorB.email, password: PASSWORD });
    expect(await retainedSessionSignalAborted(page)).toBe(true);
    await expect(page.getByText(actorB.displayValue, { exact: false })).toBeVisible();
    pending.release();
    expect((await pending.response).status()).toBe(200);
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    await expect(page).toHaveURL(/\/labs\/hba1c$/);
    await fixture.assertNoActorAValuesOrInputs();
    await fixture.assertNoActorAQueryKeysOrPendingBatch();
  });
});

test("@strictmode Labs committed POST delivered after takeover stays with its original actor", async ({ browser, request }) => {
  await withLabsIsolation(browser, request, async (fixture) => {
    const { page, actorA, actorB } = fixture;
    const enteredValue = "87.6543210";
    await page.addInitScript((apiOrigin) => {
      const original = window.fetch.bind(window);
      window.fetch = (input, init) => {
        const url = new URL(typeof input === "string" ? input : input instanceof Request ? input.url : input.href, location.href);
        if (url.origin === apiOrigin && url.pathname === "/labs/results" && init?.method === "POST") {
          const withoutSignal = { ...init }; delete withoutSignal.signal;
          return original(input, withoutSignal);
        }
        return original(input, init);
      };
    }, new URL(API_URL).origin);
    await fixture.login(actorA, "/labs");
    await retainSessionSignalInspector(page);
    await page.getByRole("tab", { name: "كل التحاليل", exact: true }).click();
    await page.locator('[data-testid="lab-row"][data-test-key="eosinophils_pct"]').getByRole("button", { name: "إضافة نتيجة" }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة نتائج" });
    await dialog.getByRole("button", { name: "التالي", exact: true }).click();
    await dialog.getByRole("button", { name: "التالي", exact: true }).click();
    await page.locator("#lab-eosinophils_pct-value").fill(enteredValue);

    const delivery = createReleaseGate();
    const started = createReleaseGate();
    let committedId = "";
    await page.route((url) => url.origin === new URL(API_URL).origin && url.pathname === "/labs/results", async (route) => {
      if (route.request().method() !== "POST") { await route.continue(); return; }
      const upstream = await route.fetch();
      const receipt = await upstream.json() as { result_ids: string[] };
      committedId = receipt.result_ids[0];
      fixture.track(actorA.token, committedId);
      started.release();
      await delivery.promise;
      await route.fulfill({ response: upstream });
    });
    try {
      const response = page.waitForResponse((candidate) => candidate.url() === `${API_URL}/labs/results` && candidate.request().method() === "POST");
      void response.catch(() => undefined);
      await dialog.getByRole("button", { name: "حفظ النتائج", exact: true }).click();
      await started.promise;
      await installLeakObserver(page, [enteredValue, committedId], [enteredValue], true);
      await e2eAuthAction(page, "signIn", { email: actorB.email, password: PASSWORD });
      expect(await retainedSessionSignalAborted(page)).toBe(true);
      delivery.release();
      expect((await response).status()).toBe(201);
      await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
      await expect(page).toHaveURL(/\/labs$/);
      await fixture.assertNoActorAValuesOrInputs();
      await fixture.assertNoActorAQueryKeysOrPendingBatch();
      const aDetail = await request.get(`${API_URL}/labs/tests/eosinophils_pct`, { headers: headers(actorA.token) });
      const bDetail = await request.get(`${API_URL}/labs/tests/eosinophils_pct`, { headers: headers(actorB.token) });
      expect(aDetail.status()).toBe(200); expect(bDetail.status()).toBe(200);
      expect((await aDetail.json() as { results: Array<{ id: string }> }).results.some((item) => item.id === committedId)).toBe(true);
      expect((await bDetail.json() as { results: Array<{ id: string }> }).results.some((item) => item.id === committedId)).toBe(false);
    } finally {
      delivery.release();
    }
  });
});

test("@strictmode held selected-user Labs GET cannot repaint after admin changes selected user", async ({ browser, request }) => {
  await withLabsIsolation(browser, request, async (fixture) => {
    const { page, actorA, actorB } = fixture;
    const heldPath = `/admin/users/${actorA.principalId}/labs/tests/hba1c`;
    await page.addInitScript(({ apiOrigin, path }) => {
      const original = window.fetch.bind(window);
      window.fetch = (input, init) => {
        const url = new URL(typeof input === "string" ? input : input instanceof Request ? input.url : input.href, location.href);
        if (url.origin === apiOrigin && url.pathname === path && (!init?.method || init.method === "GET")) {
          const withoutSignal = { ...init }; delete withoutSignal.signal;
          return original(input, withoutSignal);
        }
        return original(input, init);
      };
    }, { apiOrigin: new URL(API_URL).origin, path: heldPath });
    await fixture.login({ ...actorA, email: ADMIN_EMAIL }, `/admin/users/${actorA.principalId}/labs`, ADMIN_PASSWORD);
    expect(await sessionSignalAborted(page)).toBe(false);
    const adminToken = await token(ADMIN_EMAIL, ADMIN_PASSWORD);
    const pending = await fixture.holdGet(heldPath, adminToken);
    await page.locator('[data-testid="lab-row"][data-test-key="hba1c"] a').click();
    await pending.started;
    await installLeakObserver(page, [actorA.displayValue, actorA.resultId], [], true);
    await page.locator('a[href="/admin"]').click();
    await page.locator('a[href="/admin/users"]').click();
    await page.locator(`a[href="/admin/users/${actorB.principalId}"]`).click();
    await page.getByRole("link", { name: "عرض التحاليل", exact: true }).click();
    await expect(page.getByText(actorB.displayValue, { exact: false })).toBeVisible();
    expect(await sessionSignalAborted(page)).toBe(false);
    pending.release();
    expect((await pending.response).status()).toBe(200);
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    await expect(page).toHaveURL(new RegExp(`/admin/users/${actorB.principalId}/labs$`));
    expect(await leakRecords(page)).toEqual([]);
    await expect(page.getByText(actorA.displayValue, { exact: false })).toHaveCount(0);
    expect((await page.evaluate(() => (window as Window & { __mynutriE2EQueryKeys?: () => string[] }).__mynutriE2EQueryKeys?.() ?? []))
      .some((key) => key.includes(actorA.principalId))).toBe(false);
  });
});

test("@strictmode admin logout to ordinary actor clears selected-user Labs while its URL remains", async ({ browser, request }) => {
  await withLabsIsolation(browser, request, async (fixture) => {
    const { page, actorA, actorB } = fixture;
    await fixture.login({ ...actorA, email: ADMIN_EMAIL }, `/admin/users/${actorA.principalId}/labs`, ADMIN_PASSWORD);
    await expect(page.getByText(actorA.displayValue, { exact: false })).toBeVisible();
    const oldAdminSubject = await sessionSubjectKey(page);
    await retainSessionSignalInspector(page);
    await installLeakObserver(page, [actorA.displayValue, actorA.resultId, ADMIN_EMAIL], [], true);
    await e2eAuthAction(page, "signOut");
    await e2eAuthAction(page, "signIn", { email: actorB.email, password: PASSWORD });
    expect(await retainedSessionSignalAborted(page)).toBe(true);
    expect(new URL(page.url()).pathname).toBe(`/admin/users/${actorA.principalId}/labs`);
    await expect(page.locator('a[href="/admin"]')).toHaveCount(0);
    await expect(page.getByText(actorA.displayValue, { exact: false })).toHaveCount(0);
    expect((await page.evaluate(() => (window as Window & { __mynutriE2EQueryKeys?: () => string[] }).__mynutriE2EQueryKeys?.() ?? []))
      .some((key) => key.includes(oldAdminSubject))).toBe(false);
    await expect(page.getByRole("dialog", { name: "إضافة نتائج" })).toHaveCount(0);
    await expect(page.getByText(/تم حفظ النتائج\.|تعذر تأكيد الحفظ/)).toHaveCount(0);
    expect(await leakRecords(page)).toEqual([]);
  });
});
