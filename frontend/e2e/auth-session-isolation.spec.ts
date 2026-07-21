import { expect, test, type Page, type Request } from "@playwright/test";
import { fillRequiredFoodForm, submitFoodForm } from "./foods/helpers";

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

function profile(weight: number) {
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

function riyadhToday() {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Riyadh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).formatToParts(new Date());
  const value = (type: Intl.DateTimeFormatPartTypes) => parts.find((part) => part.type === type)?.value;
  return `${value("year")}-${value("month")}-${value("day")}`;
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

test("development StrictMode replay keeps the anonymous session boundary signal live", async ({ browser }) => {
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
  await context.close();
});

test("same browser context isolates cached profile and diary data across A to B to A", async ({ browser, request }) => {
  const suffix = Date.now();
  const emailA = `session-a-${suffix}@example.test`;
  const emailB = `session-b-${suffix}@example.test`;
  const tokenA = await token(emailA);
  const tokenB = await token(emailB);
  const adminToken = await token(ADMIN_EMAIL, ADMIN_PASSWORD);
  expect((await request.put(`${API_URL}/profile`, { headers: headers(tokenA), data: profile(71) })).status()).toBe(200);
  expect((await request.put(`${API_URL}/profile`, { headers: headers(tokenB), data: profile(89) })).status()).toBe(200);

  const diaryNameA = `A diary marker ${suffix}`;
  const foodResponse = await request.post(`${API_URL}/foods`, {
    headers: headers(adminToken),
    data: {
      name: diaryNameA,
      food_category_key: "other",
      food_kind: "simple",
      nutrition_basis: "per_100g",
      default_unit_type: "serving",
      unit_amount: 100,
      unit_basis: "g",
      calories: 200,
      protein_g: 10,
      carb_g: 25,
      fat_g: 7,
      nutrition_source: { type: "unknown", name: null, reference: null },
      ingredients: { text: null, source_type: null, source_name: null, source_reference: null },
      nova: null,
      group_contributions: [],
      analytical_traits: []
    }
  });
  expect(foodResponse.status()).toBe(201);
  const food = await foodResponse.json() as { id: string };
  const diaryResponse = await request.post(`${API_URL}/diary`, {
    headers: headers(tokenA),
    data: {
      entry_date: riyadhToday(),
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
        items: [{ id: `plan-${suffix}`, status: "active", effective_from: historyMarkerA, effective_to: null, targets: { target_calories: 2100 } }],
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
  await page.route(`${API_URL}/diary*`, async (route) => {
    diaryBWasBlocked = true;
    await diaryBBlocked;
    await route.continue();
  });
  const diaryBResponse = page.waitForResponse((response) => new URL(response.url()).pathname === "/diary");
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
        const { signal: _signal, ...withoutSignal } = init;
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

  let releaseCreate!: () => void;
  let createWasBlocked = false;
  let createAuthorization: string | undefined;
  let createName: string | undefined;
  let adminAccountAuthorization: string | undefined;
  let staleDetailRequested = false;
  const createBlocked = new Promise<void>((resolve) => { releaseCreate = resolve; });
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
        const { signal: _signal, ...withoutSignal } = init;
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
    await createBlocked;
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({ id: staleFoodId, name: marker })
    });
  });
  await page.route(`${API_URL}/foods/${staleFoodId}`, async (route) => {
    staleDetailRequested = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ id: staleFoodId, name: marker })
    });
  });

  const delayedCreateResponse = page.waitForResponse((response) =>
    response.url() === `${API_URL}/foods` && response.request().method() === "POST"
  );
  await submitFoodForm(page);
  await expect.poll(() => createWasBlocked).toBe(true);

  await installLeakObserver(page, [marker], [marker], true);
  const bAccountResponse = page.waitForResponse((response) =>
    response.url() === `${API_URL}/account/me` &&
    response.request().headers()["authorization"] !== adminAccountAuthorization
  );
  await e2eAuthAction(page, "signIn", { email: emailB, password: PASSWORD });
  releaseCreate();
  const [bResponse, response] = await Promise.all([bAccountResponse, delayedCreateResponse]);
  expect(bResponse.status()).toBe(200);
  expect(response.status()).toBe(201);
  expect(await response.finished()).toBeNull();
  const bAccount = await bResponse.json() as { email: string | null; role: "user" | "admin" };
  expect(bAccount.email).toBe(emailB);
  expect(bAccount.role).toBe("user");
  const bAccountAuthorization = bResponse.request().headers()["authorization"];
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

  await expect(page).toHaveURL(originalUrl);
  await expect(page.locator(".nav-signout")).toBeVisible();
  await expect(page.locator('a[href="/admin"]')).toHaveCount(0);
  await expect(page.locator("form.food-form-layout")).toHaveCount(0);
  await expect(page.locator('.state-note[role="alert"]')).toHaveText("إدارة الأطعمة متاحة للمشرف فقط.");
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await page.waitForTimeout(100);

  expect(createName).toBe(marker);
  expect(createAuthorization).toBe(adminAccountAuthorization);
  expect(createAuthorization).not.toBe(bAccountAuthorization);
  expect(staleDetailRequested).toBe(false);
  expect(await leakRecords(page)).toEqual([]);
  await expect(page).toHaveURL(originalUrl);
  await expect(page.locator('a[href="/admin"]')).toHaveCount(0);
  await expect(page.locator("form.food-form-layout")).toHaveCount(0);
  await expect(page.locator('.state-note[role="alert"]')).toHaveText("إدارة الأطعمة متاحة للمشرف فقط.");
  await expect(page.getByText(marker, { exact: true })).toHaveCount(0);
  await context.close();
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
        const { signal: _signal, ...withoutSignal } = init;
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
  expect((await request.put(`${API_URL}/profile`, { headers: headers(tokenB), data: profile(83) })).status()).toBe(200);
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
  expect((await request.put(`${API_URL}/profile`, { headers: headers(tokenA), data: profile(74) })).status()).toBe(200);

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
