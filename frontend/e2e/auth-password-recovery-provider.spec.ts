import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Browser, type BrowserContext, type Page, type Route } from "@playwright/test";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { randomBytes } from "node:crypto";

const APP_URL = requiredLoopbackUrl("PLAYWRIGHT_BASE_URL");
const PROVIDER_URL = requiredLoopbackUrl("PLAN020_SUPABASE_URL");
const MAILPIT_URL = requiredLoopbackUrl("PLAN020_MAILPIT_URL");
const ANON_KEY = requiredSecret("PLAN020_SUPABASE_ANON_KEY");
const SERVICE_ROLE_KEY = requiredSecret("PLAN020_SUPABASE_SERVICE_ROLE_KEY");
const RECOVERY_PATH = "/auth/reset-password";
const RECOVERY_REQUEST_PATH = "/auth/v1/recover";
const PASSWORD_UPDATE_PATH = "/auth/v1/user";
const TOKEN_EXCHANGE_PATH = "/auth/v1/token";
const RECOVERY_EXPIRY_SECONDS = Number(process.env.PLAN020_RECOVERY_EXPIRY_SECONDS ?? "20");

const INITIAL_PASSWORD = disposablePassword("initial");
const UPDATED_PASSWORD = disposablePassword("updated");
const RUN_ALIAS = `${Date.now()}-${process.pid}`;

type UserAlias = "user-a" | "user-b" | "request" | "expiry" | "replacement" | "isolation" | "history" | "reload" | "navigation";
type TestUser = { alias: UserAlias; email: string; id: string };
type MailpitAddress = { Address?: string };
type MailpitMessageSummary = {
  ID?: string;
  From?: MailpitAddress;
  To?: MailpitAddress[];
  Subject?: string;
};
type MailpitMessages = { messages?: MailpitMessageSummary[]; total?: number };
type MailpitMessage = MailpitMessageSummary & { HTML?: string; Text?: string };
type SafeRequestDiagnostic = {
  semanticCase: string;
  method: string;
  origin: string;
  pathname: string;
  queryKeys: string[];
  resourceType: string;
  isNavigation: boolean;
  hasAuthorization: boolean;
  hasCookie: boolean;
  contentType: string | null;
  bodyPresent: boolean;
  bodyByteLength: number;
};
type RecoveryVerifierState = Awaited<ReturnType<BrowserContext["storageState"]>>;
type RecoveryArtifact = { link: string; verifierState: RecoveryVerifierState };
type SafeActiveElement = {
  tagName: string;
  type: string | null;
  role: string | null;
  accessibleName: string | null;
  connected: boolean;
  disabled: boolean;
  visible: boolean;
  insideForm: boolean;
};
type SafeHistoryObservation = {
  phase: "establish" | "leave" | "back" | "forward" | "reload";
  source: "document-request" | "main-frame";
  pathname: string;
};

let admin: SupabaseClient | null = null;
const users = new Map<UserAlias, TestUser>();
const activeContexts = new Set<BrowserContext>();

function disposablePassword(label: string): string {
  return `Plan020-${label}-${randomBytes(18).toString("base64url")}!Aa1`;
}

function requiredSecret(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required local provider setting: ${name}.`);
  return value;
}

function requiredLoopbackUrl(name: string): URL {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required local provider URL: ${name}.`);
  const url = new URL(value);
  if (url.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(url.hostname)) {
    throw new Error(`${name} must target an HTTP loopback service.`);
  }
  url.hash = "";
  url.search = "";
  return url;
}

function user(alias: UserAlias): TestUser {
  const record = users.get(alias);
  if (!record) throw new Error(`Synthetic ${alias} was not provisioned.`);
  return record;
}

function safePath(page: Page): string {
  try {
    return new URL(page.url()).pathname;
  } catch {
    return "[unavailable]";
  }
}

function safeQueryKeys(url: URL): string[] {
  const sensitive = /(token|secret|session|auth|code|key|email|identifier)/i;
  return [...new Set([...url.searchParams.keys()].map((key) => sensitive.test(key) ? "[sensitive-key]" : key))].sort();
}

function sanitizeRequest(input: {
  semanticCase: string;
  method: string;
  url: string;
  headers: Record<string, string>;
  resourceType: string;
  isNavigation: boolean;
  body: string | null;
}): SafeRequestDiagnostic {
  const url = new URL(input.url);
  const normalizedHeaders = new Map(Object.entries(input.headers).map(([key, value]) => [key.toLowerCase(), value]));
  const bodyByteLength = input.body === null ? 0 : Buffer.byteLength(input.body, "utf8");
  return {
    semanticCase: input.semanticCase,
    method: input.method,
    origin: url.origin,
    pathname: url.pathname,
    queryKeys: safeQueryKeys(url),
    resourceType: input.resourceType,
    isNavigation: input.isNavigation,
    hasAuthorization: normalizedHeaders.has("authorization"),
    hasCookie: normalizedHeaders.has("cookie"),
    contentType: normalizedHeaders.get("content-type") ?? null,
    bodyPresent: input.body !== null,
    bodyByteLength
  };
}

function ensureSecretSafeDiagnostic(record: SafeRequestDiagnostic): void {
  const allowedKeys = new Set([
    "semanticCase",
    "method",
    "origin",
    "pathname",
    "queryKeys",
    "resourceType",
    "isNavigation",
    "hasAuthorization",
    "hasCookie",
    "contentType",
    "bodyPresent",
    "bodyByteLength"
  ]);
  for (const [key, value] of Object.entries(record)) {
    if (!allowedKeys.has(key)) throw new Error("Sanitized provider diagnostics retained a non-allowlisted field.");
    if (/(token|secret|credential|session|auth|cookie)/i.test(key) && typeof value !== "boolean") {
      throw new Error("A credential-like diagnostic field was not reduced to a boolean signal.");
    }
  }
  if (record.queryKeys.some((key) => key !== "[sensitive-key]" && /(token|secret|credential|session|auth|code|key|email|identifier)/i.test(key))) {
    throw new Error("Sanitized provider diagnostics retained a sensitive query-key name.");
  }
  const serialized = JSON.stringify(record).toLowerCase();
  const forbiddenKeys = ["access_token", "refresh_token", "set-cookie", "proxy-authorization", "x-api-key", "apikey"];
  if (forbiddenKeys.some((key) => serialized.includes(key))) {
    throw new Error("Sanitized provider diagnostics retained a forbidden key.");
  }
}

async function expectSafeFocusWithin(page: Page, selector: string, message: string): Promise<void> {
  await expect.poll(() => page.evaluate((rootSelector) => {
    const root = document.querySelector(rootSelector);
    const active = document.activeElement;
    if (!(root instanceof HTMLElement) || !(active instanceof HTMLElement) || !root.contains(active)) return false;
    if (active.matches(":disabled") || active.closest("[inert], [aria-hidden='true']")) return false;
    const style = getComputedStyle(active);
    return style.visibility !== "hidden" && style.display !== "none";
  }, selector), { message }).toBe(true);
}

async function safeActiveElement(page: Page): Promise<SafeActiveElement> {
  return page.evaluate(() => {
    const active = document.activeElement;
    const form = document.querySelector("form");
    if (!(active instanceof HTMLElement)) {
      return {
        tagName: "[none]",
        type: null,
        role: null,
        accessibleName: null,
        connected: false,
        disabled: false,
        visible: false,
        insideForm: false
      };
    }
    const style = getComputedStyle(active);
    const label = active instanceof HTMLInputElement
      ? active.labels?.[0]?.textContent?.trim() ?? null
      : active.getAttribute("aria-label") ?? (active instanceof HTMLButtonElement ? active.textContent?.trim() ?? null : null);
    return {
      tagName: active.tagName.toLowerCase(),
      type: active instanceof HTMLInputElement || active instanceof HTMLButtonElement ? active.type : null,
      role: active.getAttribute("role"),
      accessibleName: label,
      connected: active.isConnected,
      disabled: active.matches(":disabled"),
      visible: style.visibility !== "hidden" && style.display !== "none",
      insideForm: form instanceof HTMLFormElement && form.contains(active)
    };
  });
}

async function hasStoredAuthSession(page: Page): Promise<boolean> {
  return page.evaluate(() => Object.entries(localStorage).some(([key, value]) =>
    /auth-token$/i.test(key) && value.includes('"access_token"')
  ));
}

async function safeFetch(url: URL, init: RequestInit | undefined, operation: string): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch {
    throw new Error(`${operation} could not reach its loopback service.`);
  }
}

async function clearMailbox(): Promise<void> {
  const response = await safeFetch(new URL("/api/v1/messages", MAILPIT_URL), {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: "{}"
  }, "Mailbox cleanup");
  if (!response.ok) throw new Error(`Mailbox cleanup failed with status ${response.status}.`);
}

async function listMessages(): Promise<MailpitMessageSummary[]> {
  const response = await safeFetch(new URL("/api/v1/messages?limit=50", MAILPIT_URL), undefined, "Mailbox listing");
  if (!response.ok) throw new Error(`Mailbox listing failed with status ${response.status}.`);
  const result = await response.json() as MailpitMessages;
  return Array.isArray(result.messages) ? result.messages : [];
}

function messageTargets(message: MailpitMessageSummary, email: string): boolean {
  return Boolean(message.To?.some((address) => address.Address?.toLowerCase() === email.toLowerCase()));
}

async function matchingMessageCount(email: string): Promise<number> {
  return (await listMessages()).filter((message) => messageTargets(message, email)).length;
}

function decodeHtmlAttribute(value: string): string {
  return value
    .replaceAll("&amp;", "&")
    .replaceAll("&#38;", "&")
    .replaceAll("&quot;", "\"")
    .replaceAll("&#39;", "'");
}

function recoveryLinkFromBody(body: string): string | null {
  const candidates = [...body.matchAll(/https?:\/\/[^\s"'<>]+/g)].map((match) => decodeHtmlAttribute(match[0]));
  for (const candidate of candidates) {
    try {
      const url = new URL(candidate);
      if (url.origin !== PROVIDER_URL.origin || url.pathname !== "/auth/v1/verify") continue;
      if (url.searchParams.get("type") !== "recovery") continue;
      const redirect = url.searchParams.get("redirect_to");
      if (!redirect) continue;
      const redirectUrl = new URL(redirect);
      if (redirectUrl.origin !== APP_URL.origin || redirectUrl.pathname !== RECOVERY_PATH) continue;
      return candidate;
    } catch {
      // Ignore non-URL text without retaining it in diagnostics.
    }
  }
  return null;
}

async function takeRecoveryLink(alias: UserAlias): Promise<string> {
  const record = user(alias);
  await expect.poll(() => matchingMessageCount(record.email), {
    message: `A single recovery email must reach Mailpit for ${alias}.`
  }).toBe(1);
  const matches = (await listMessages()).filter((message) => messageTargets(message, record.email));
  const summary = matches[0];
  if (!summary?.ID) throw new Error(`Mailpit did not expose a safe message identifier for ${alias}.`);
  const response = await safeFetch(new URL(`/api/v1/message/${encodeURIComponent(summary.ID)}`, MAILPIT_URL), undefined, "Mailbox message read");
  if (!response.ok) throw new Error(`Mailbox message read failed with status ${response.status}.`);
  const message = await response.json() as MailpitMessage;
  const senderSafe = message.From?.Address?.toLowerCase() === "plan020-provider@example.test";
  const recipientSafe = messageTargets(message, record.email);
  const intentSafe = /recover|reset|password/i.test(message.Subject ?? "");
  if (!senderSafe || !recipientSafe || !intentSafe) {
    throw new Error(`Mailpit metadata did not certify the recovery intent for ${alias}.`);
  }
  const link = recoveryLinkFromBody(`${message.HTML ?? ""}\n${message.Text ?? ""}`);
  if (!link) throw new Error(`The provider-generated recovery link was not found for ${alias}.`);
  return link;
}

function trackContext(context: BrowserContext): BrowserContext {
  activeContexts.add(context);
  context.on("close", () => activeContexts.delete(context));
  return context;
}

async function closeActiveContexts(): Promise<void> {
  const results = await Promise.all([...activeContexts].map(async (context) => {
    try {
      await context.close();
      return true;
    } catch {
      return false;
    }
  }));
  activeContexts.clear();
  if (results.some((closed) => !closed)) throw new Error("One or more isolated browser contexts survived test cleanup.");
}

async function newAnonymousPage(
  browser: Browser,
  viewport?: { width: number; height: number },
  storageState?: RecoveryVerifierState
): Promise<{ context: BrowserContext; page: Page }> {
  const context = trackContext(await browser.newContext({ storageState, viewport }));
  const page = await context.newPage();
  return { context, page };
}

function isRecoveryVerifierKey(name: string): boolean {
  return /code-verifier(?:\.\d+)?$/i.test(name);
}

async function captureRecoveryVerifierState(context: BrowserContext): Promise<RecoveryVerifierState> {
  const state = await context.storageState();
  const verifierState: RecoveryVerifierState = {
    cookies: state.cookies.filter((cookie) => isRecoveryVerifierKey(cookie.name)),
    origins: state.origins
      .map((origin) => ({
        origin: origin.origin,
        localStorage: origin.localStorage.filter((entry) => isRecoveryVerifierKey(entry.name))
      }))
      .filter((origin) => origin.localStorage.length > 0)
  };
  const verifierParts = verifierState.cookies.length + verifierState.origins.reduce((count, origin) => count + origin.localStorage.length, 0);
  if (verifierParts === 0) throw new Error("The recovery request did not create isolated PKCE verifier state.");
  return verifierState;
}

async function submitRecovery(
  page: Page,
  record: TestUser,
  mode: "keyboard" | "double-submit" | "enter-plus-click" = "keyboard"
): Promise<{ requests: number; responses: number; status: number | null; publicMessage: string }> {
  let requests = 0;
  let responses = 0;
  let status: number | null = null;
  const providerOrigin = PROVIDER_URL.origin;
  const recoveryMatcher = (url: URL) => url.origin === providerOrigin && url.pathname === RECOVERY_REQUEST_PATH;
  let barrierMatches = 0;
  let firstRequestReachedBarrier = Promise.resolve();
  let firstRequestContinuationSettled = Promise.resolve();
  let releaseFirstRequest = () => {};
  let recoveryBarrierEnabled = false;
  let firstRequestReleased = false;
  let holdFirstRecoveryRequest: ((route: Route) => Promise<void>) | null = null;

  if (mode === "enter-plus-click") {
    recoveryBarrierEnabled = true;
    let markFirstRequestReached!: () => void;
    let markFirstRequestContinuationSettled!: () => void;
    firstRequestReachedBarrier = new Promise<void>((resolve) => { markFirstRequestReached = resolve; });
    firstRequestContinuationSettled = new Promise<void>((resolve) => { markFirstRequestContinuationSettled = resolve; });
    const firstRequestRelease = new Promise<void>((resolve) => { releaseFirstRequest = resolve; });
    holdFirstRecoveryRequest = async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }
      barrierMatches += 1;
      const isFirstRequest = barrierMatches === 1;
      try {
        if (isFirstRequest) {
          markFirstRequestReached();
          await firstRequestRelease;
        }
        await route.continue();
      } finally {
        if (isFirstRequest) markFirstRequestContinuationSettled();
      }
    };
    await page.route(recoveryMatcher, holdFirstRecoveryRequest);
  }
  const onRequest = (request: import("@playwright/test").Request) => {
    const url = new URL(request.url());
    if (url.origin === providerOrigin && url.pathname === RECOVERY_REQUEST_PATH && request.method() === "POST") requests += 1;
  };
  const onResponse = (response: import("@playwright/test").Response) => {
    const url = new URL(response.url());
    if (url.origin === providerOrigin && url.pathname === RECOVERY_REQUEST_PATH && response.request().method() === "POST") {
      responses += 1;
      status = response.status();
    }
  };
  page.on("request", onRequest);
  page.on("response", onResponse);
  try {
    await page.goto("/auth/forgot-password");
    const input = page.getByLabel("البريد الإلكتروني", { exact: true });
    const submitButton = page.locator('button[type="submit"]');
    await input.fill(record.email);
    await expect(input).toBeFocused();
    await expect(submitButton).toBeEnabled();
    await expect(submitButton).toHaveText("إرسال رابط الاستعادة");
    await expect(page.getByRole("status")).toHaveCount(0);
    expect(requests).toBe(0);
    expect(responses).toBe(0);
    if (mode === "double-submit") {
      await page.locator("form").evaluate((form: HTMLFormElement) => {
        form.requestSubmit();
        form.requestSubmit();
      });
    } else if (mode === "enter-plus-click") {
      await input.focus();
      const enterAttempt = input.press("Enter");
      await firstRequestReachedBarrier;
      await enterAttempt;
      await expect.poll(() => requests, { message: "The first Enter submission must reach the exact recovery endpoint once." }).toBe(1);
      expect(barrierMatches).toBe(1);
      expect(responses).toBe(0);
      await expect(submitButton).toBeDisabled();
      await expect(submitButton).toHaveText("جارٍ الإرسال...");
      await expect(page.getByRole("status")).toHaveCount(0);
      await expect(page.locator('.auth-message[role="alert"]')).toHaveCount(0);

      const clickAttempt = await submitButton.evaluate((button: HTMLButtonElement) => {
        const activeBefore = document.activeElement;
        const wasDisabled = button.disabled;
        button.click();
        return {
          wasDisabled,
          remainedDisabled: button.disabled,
          focusUnchanged: document.activeElement === activeBefore
        };
      });
      expect(clickAttempt).toEqual({ wasDisabled: true, remainedDisabled: true, focusUnchanged: true });

      await expect.poll(() => requests, { message: "The disabled click path must not emit a second recovery request." }).toBe(1);
      expect(barrierMatches).toBe(1);
      expect(responses).toBe(0);
      await expect(page.getByRole("status")).toHaveCount(0);
      await expect(page.locator('.auth-message[role="alert"]')).toHaveCount(0);
      await expectSafeFocusWithin(page, "form", "Focus must remain coherent while the first recovery request is pending.");

      firstRequestReleased = true;
      releaseFirstRequest();
    } else {
      await input.press("Enter");
    }
    const publicStatus = page.getByRole("status");
    await expect(publicStatus).toHaveCount(1);
    await expect(publicStatus).toBeVisible();
    await expect.poll(() => requests, { message: "The recovery UI must issue exactly one provider request." }).toBe(1);
    await expect.poll(() => responses, { message: "The recovery provider request must reach a terminal response." }).toBe(1);
    return { requests, responses, status, publicMessage: await publicStatus.innerText() };
  } finally {
    if (recoveryBarrierEnabled && !firstRequestReleased) releaseFirstRequest();
    if (barrierMatches > 0) await firstRequestContinuationSettled;
    if (holdFirstRecoveryRequest) await page.unroute(recoveryMatcher, holdFirstRecoveryRequest);
    page.off("request", onRequest);
    page.off("response", onResponse);
  }
}

async function assignProviderRecoveryLink(page: Page, link: string): Promise<void> {
  let assignmentLifecycle: "completed" | "context-replaced" = "completed";
  try {
    await page.evaluate((providerGeneratedTarget) => {
      window.location.assign(providerGeneratedTarget);
    }, link);
  } catch (error) {
    const expectedContextReplacement = error instanceof Error &&
      /(execution context was destroyed|context was destroyed|navigation|target page, context or browser has been closed)/i.test(error.message);
    if (!expectedContextReplacement) {
      throw new Error("Provider recovery navigation failed before a safe lifecycle classification was available.");
    }
    assignmentLifecycle = "context-replaced";
  }
  expect(["completed", "context-replaced"]).toContain(assignmentLifecycle);
  await expect.poll(() => safePath(page), { message: "The provider must redirect to the approved recovery pathname." }).toBe(RECOVERY_PATH);
}

async function openRecoveryLink(browser: Browser, artifact: RecoveryArtifact): Promise<{ context: BrowserContext; page: Page }> {
  const { context, page } = await newAnonymousPage(browser, undefined, artifact.verifierState);
  await page.goto("/auth/forgot-password");
  await assignProviderRecoveryLink(page, artifact.link);
  return { context, page };
}

async function expectRecoveryReady(page: Page): Promise<void> {
  await expect(page.getByRole("heading", { name: "تعيين كلمة مرور جديدة", exact: true })).toBeVisible();
  await expect(page.getByLabel("كلمة المرور الجديدة", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "حفظ كلمة المرور", exact: true })).toBeEnabled();
}

async function expectRecoveryInvalid(page: Page): Promise<void> {
  await expect(page.locator('.auth-message[role="alert"]')).toContainText("انتهت صلاحية الرابط");
  await expect(page.getByLabel("كلمة المرور الجديدة", { exact: true })).toHaveCount(0);
}

async function signInThroughUi(page: Page, record: TestUser, password: string, expectedSuccess: boolean): Promise<void> {
  const providerOrigin = PROVIDER_URL.origin;
  const passwordTokenMatcher = (url: URL) =>
    url.origin === providerOrigin &&
    url.pathname === TOKEN_EXCHANGE_PATH &&
    url.searchParams.get("grant_type") === "password";
  let requests = 0;
  let responses = 0;
  let responseStatus: number | null = null;
  let barrierMatches = 0;
  let requestReachedBarrier = Promise.resolve();
  let requestContinuationSettled = Promise.resolve();
  let releaseRequest = () => {};
  let requestReleased = false;
  let holdRejectedLogin: ((route: Route) => Promise<void>) | null = null;

  const onRequest = (request: import("@playwright/test").Request) => {
    const url = new URL(request.url());
    if (passwordTokenMatcher(url) && request.method() === "POST") requests += 1;
  };
  const onResponse = (response: import("@playwright/test").Response) => {
    const url = new URL(response.url());
    if (passwordTokenMatcher(url) && response.request().method() === "POST") {
      responses += 1;
      responseStatus = response.status();
    }
  };

  if (!expectedSuccess) {
    let markRequestReached!: () => void;
    let markContinuationSettled!: () => void;
    requestReachedBarrier = new Promise<void>((resolve) => { markRequestReached = resolve; });
    requestContinuationSettled = new Promise<void>((resolve) => { markContinuationSettled = resolve; });
    const heldRequest = new Promise<void>((resolve) => { releaseRequest = resolve; });
    holdRejectedLogin = async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }
      barrierMatches += 1;
      markRequestReached();
      try {
        await heldRequest;
        await route.continue();
      } finally {
        markContinuationSettled();
      }
    };
    await page.route(passwordTokenMatcher, holdRejectedLogin);
  }

  page.on("request", onRequest);
  page.on("response", onResponse);
  try {
    await page.goto("/auth/login");
    expect(safePath(page)).toBe("/auth/login");
    if (!expectedSuccess) expect(await hasStoredAuthSession(page)).toBe(false);

    const form = page.locator("form");
    const emailInput = page.getByLabel("البريد الإلكتروني", { exact: true });
    const passwordInput = page.getByLabel("كلمة المرور", { exact: true });
    const submitButton = form.locator('button[type="submit"]');
    await expect(form).toBeVisible();
    await emailInput.fill(record.email);
    await passwordInput.fill(password);
    await expect(page.getByRole("button", { name: "إظهار كلمة المرور", exact: true })).toBeVisible();
    await expect(submitButton).toBeEnabled();
    await expect(submitButton).toHaveAccessibleName("دخول");
    expect(requests).toBe(0);

    await submitButton.focus();
    await expect(submitButton).toBeFocused();
    const beforeSubmit = await safeActiveElement(page);
    expect(beforeSubmit).toMatchObject({
      tagName: "button",
      type: "submit",
      connected: true,
      disabled: false,
      visible: true,
      insideForm: true
    });

    const submitAttempt = submitButton.click();
    if (expectedSuccess) {
      await submitAttempt;
      await expect.poll(() => safePath(page), { message: "The accepted synthetic subject must reach Diary." }).toBe("/diary");
      expect(requests).toBe(1);
      expect(responses).toBe(1);
      return;
    }

    await requestReachedBarrier;
    await submitAttempt;
    await expect.poll(() => requests, { message: "The old-password attempt must reach the exact password sign-in endpoint once." }).toBe(1);
    expect(barrierMatches).toBe(1);
    expect(responses).toBe(0);
    await expect(submitButton).toBeDisabled();
    await expect(submitButton).toHaveAccessibleName("جارٍ الإرسال...");
    await expectSafeFocusWithin(page, "form", "Pending login must retain focus inside the active form.");
    const duringPending = await safeActiveElement(page);
    expect(duringPending).toMatchObject({
      tagName: "input",
      type: "password",
      connected: true,
      disabled: false,
      visible: true,
      insideForm: true
    });

    const duplicateAttempt = await submitButton.evaluate((button: HTMLButtonElement) => {
      const disabled = button.disabled;
      button.click();
      return { disabled, remainedDisabled: button.disabled };
    });
    expect(duplicateAttempt).toEqual({ disabled: true, remainedDisabled: true });
    expect(requests).toBe(1);
    expect(barrierMatches).toBe(1);
    expect(responses).toBe(0);

    requestReleased = true;
    releaseRequest();
    await expect.poll(() => responses, { message: "The rejected old-password request must reach one terminal provider response." }).toBe(1);
    expect(responseStatus).not.toBeNull();
    expect(responseStatus).toBeGreaterThanOrEqual(400);
    await expect(page.getByRole("status")).toHaveText("تعذر إكمال الطلب. تحقق من البيانات وحاول مرة أخرى.");
    await expect(submitButton).toBeEnabled();
    await expect(submitButton).toHaveAccessibleName("دخول");
    await expect(passwordInput).toBeFocused();
    await expect(passwordInput).toBeVisible();
    await expect(passwordInput).toBeEnabled();
    await expectSafeFocusWithin(page, "form", "A rejected login must leave focus on a safe control inside the login form.");
    const afterRejection = await safeActiveElement(page);
    expect(afterRejection).toMatchObject({
      tagName: "input",
      type: "password",
      connected: true,
      disabled: false,
      visible: true,
      insideForm: true
    });
    expect(requests).toBe(1);
    expect(responses).toBe(1);
    expect(safePath(page)).toBe("/auth/login");
    expect(await hasStoredAuthSession(page)).toBe(false);
    await expect(page.getByTitle("تسجيل الخروج", { exact: true })).toHaveCount(0);
  } finally {
    if (!expectedSuccess && !requestReleased) releaseRequest();
    if (!expectedSuccess && barrierMatches > 0) await requestContinuationSettled;
    if (holdRejectedLogin) await page.unroute(passwordTokenMatcher, holdRejectedLogin);
    page.off("request", onRequest);
    page.off("response", onResponse);
  }
}

async function requestLink(browser: Browser, alias: UserAlias): Promise<RecoveryArtifact> {
  await clearMailbox();
  const { context, page } = await newAnonymousPage(browser);
  try {
    const result = await submitRecovery(page, user(alias));
    if (result.requests !== 1 || result.responses !== 1 || result.status !== 200) {
      throw new Error(`Recovery request did not complete once with status 200 for ${alias}.`);
    }
    const link = await takeRecoveryLink(alias);
    const verifierState = await captureRecoveryVerifierState(context);
    return { link, verifierState };
  } finally {
    await context.close();
  }
}

test("@plan020-provider @plan020-sanitizer secret-safe diagnostics exclude synthetic markers", () => {
  const markers = {
    cookie: "synthetic-cookie-marker",
    authorization: "synthetic-authorization-marker",
    body: "synthetic-private-body-marker",
    query: "synthetic-token-query-marker"
  };
  const sanitized = sanitizeRequest({
    semanticCase: "synthetic-sanitizer-check",
    method: "POST",
    url: `${APP_URL.origin}${RECOVERY_PATH}?access_token=${markers.query}&safe=value`,
    headers: {
      cookie: markers.cookie,
      authorization: `Bearer ${markers.authorization}`,
      "content-type": "application/json"
    },
    resourceType: "fetch",
    isNavigation: false,
    body: markers.body
  });
  ensureSecretSafeDiagnostic(sanitized);
  const serialized = JSON.stringify(sanitized);
  const markersAbsent = Object.values(markers).every((marker) => !serialized.includes(marker));
  expect(markersAbsent, "Sanitized diagnostics must exclude every synthetic secret marker.").toBe(true);
  expect(sanitized.queryKeys).toEqual(["[sensitive-key]", "safe"]);
});

test.describe("Plan 020 isolated local provider acceptance", () => {
  test.beforeAll(async () => {
    admin = createClient(PROVIDER_URL.toString(), SERVICE_ROLE_KEY, {
      auth: { autoRefreshToken: false, detectSessionInUrl: false, persistSession: false }
    });
    for (const alias of ["user-a", "user-b", "request", "expiry", "replacement", "isolation", "history", "reload", "navigation"] as UserAlias[]) {
      const email = `plan020-${alias}-${RUN_ALIAS}@example.test`;
      const { data, error } = await admin.auth.admin.createUser({
        email,
        password: INITIAL_PASSWORD,
        email_confirm: true,
        user_metadata: { display_name: `Plan 020 ${alias}` }
      });
      if (error || !data.user) throw new Error(`Local provider user provisioning failed for ${alias}.`);
      users.set(alias, { alias, email, id: data.user.id });
    }
    await clearMailbox();
  });

  test.afterAll(async () => {
    let cleanupFailed = false;
    try {
      await closeActiveContexts();
    } catch {
      cleanupFailed = true;
    }
    try {
      await clearMailbox();
    } catch {
      cleanupFailed = true;
    }
    if (admin) {
      for (const record of users.values()) {
        const { error } = await admin.auth.admin.deleteUser(record.id);
        if (error) cleanupFailed = true;
      }
    }
    users.clear();
    if (cleanupFailed) throw new Error("The isolated provider test could not certify complete browser, mailbox, and user cleanup.");
  });

  test.afterEach(async () => {
    let cleanupFailed = false;
    try {
      await closeActiveContexts();
    } catch {
      cleanupFailed = true;
    }
    try {
      await clearMailbox();
    } catch {
      cleanupFailed = true;
    }
    if (cleanupFailed) throw new Error("The provider scenario could not certify browser and mailbox cleanup.");
  });

  test("@plan020-provider missing recovery session is inaccessible and sends zero updates", async ({ browser }) => {
    const { context, page } = await newAnonymousPage(browser, { width: 320, height: 700 });
    let updates = 0;
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.origin === PROVIDER_URL.origin && url.pathname === PASSWORD_UPDATE_PATH && request.method() === "PUT") updates += 1;
    });
    await page.goto(RECOVERY_PATH);
    await expectRecoveryInvalid(page);
    expect(updates).toBe(0);
    expect(await page.evaluate(() => document.documentElement.dir)).toBe("rtl");
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
    const axe = await new AxeBuilder({ page }).include(".auth-panel").analyze();
    expect(axe.violations.filter((violation) => ["serious", "critical"].includes(violation.impact ?? ""))).toEqual([]);
    await context.close();
  });

  test("@plan020-provider recovery requests are non-enumerating and Mailpit receives the real email", async ({ browser }) => {
    await clearMailbox();
    const existing = await newAnonymousPage(browser);
    const existingResult = await submitRecovery(existing.page, user("request"), "double-submit");
    expect(existingResult).toMatchObject({ requests: 1, responses: 1, status: 200 });
    await takeRecoveryLink("request");
    await existing.context.close();

    await clearMailbox();
    const unknownRecord: TestUser = {
      alias: "user-a",
      email: `plan020-unknown-${RUN_ALIAS}@example.test`,
      id: "not-provisioned"
    };
    const unknown = await newAnonymousPage(browser);
    const unknownResult = await submitRecovery(unknown.page, unknownRecord, "enter-plus-click");
    expect(unknownResult).toMatchObject({ requests: 1, responses: 1, status: 200 });
    expect(unknownResult.publicMessage).toBe(existingResult.publicMessage);
    expect(await matchingMessageCount(unknownRecord.email)).toBe(0);
    await unknown.context.close();
  });

  test("@plan020-provider real recovery updates once, logs in with the new password, rejects the old password, and rejects reuse", async ({ browser }) => {
    const artifact = await requestLink(browser, "user-a");
    const { context, page } = await openRecoveryLink(browser, artifact);
    let updates = 0;
    let releaseUpdate!: () => void;
    const updateHeld = new Promise<void>((resolve) => { releaseUpdate = resolve; });
    const updateMatcher = (url: URL) => url.origin === PROVIDER_URL.origin && url.pathname === PASSWORD_UPDATE_PATH;
    await page.route(updateMatcher, async (route) => {
      await updateHeld;
      await route.continue();
    });
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.origin === PROVIDER_URL.origin && url.pathname === PASSWORD_UPDATE_PATH && request.method() === "PUT") updates += 1;
    });
    await page.evaluate(() => {
      const state = { diaryReplacements: 0 };
      Object.defineProperty(window, "__plan020SafeNavigation", { value: state });
      const original = history.replaceState.bind(history);
      history.replaceState = (data, unused, url) => {
        if (url && new URL(String(url), window.location.origin).pathname === "/diary") state.diaryReplacements += 1;
        return original(data, unused, url);
      };
    });
    await expectRecoveryReady(page);
    const accessibility = await new AxeBuilder({ page }).include(".auth-panel").analyze();
    expect(accessibility.violations.filter((violation) => ["serious", "critical"].includes(violation.impact ?? ""))).toEqual([]);
    const password = page.getByLabel("كلمة المرور الجديدة", { exact: true });
    const recoveryForm = page.locator("form");
    try {
      await password.fill(UPDATED_PASSWORD);
      await password.focus();
      await page.keyboard.press("Enter");
      await expect.poll(() => updates, { message: "The recovery session must issue one password update." }).toBe(1);
      await expect(page.getByRole("button", { name: "جارٍ الإرسال...", exact: true })).toBeDisabled();
      await expect(password).toBeFocused();
      await expectSafeFocusWithin(page, "form", "The held duplicate lock must retain focus inside the recovery form.");
      await recoveryForm.evaluate((form: HTMLFormElement) => form.requestSubmit());
      expect(updates).toBe(1);
    } finally {
      releaseUpdate();
    }
    await expect.poll(() => safePath(page), { message: "A successful update must redirect to Diary." }).toBe("/diary");
    await page.unroute(updateMatcher);
    expect(updates).toBe(1);
    await expect(page.getByLabel("كلمة المرور الجديدة", { exact: true })).toHaveCount(0);
    const replacements = await page.evaluate(() => (window as Window & { __plan020SafeNavigation?: { diaryReplacements: number } }).__plan020SafeNavigation?.diaryReplacements ?? 0);
    expect(replacements).toBe(1);
    await page.reload();
    expect(safePath(page)).toBe("/diary");
    expect(updates).toBe(1);

    await expect(page.getByTitle("تسجيل الخروج", { exact: true })).toBeVisible();
    await page.getByTitle("تسجيل الخروج", { exact: true }).click();
    await expect.poll(() => safePath(page)).toBe("/auth/login");
    await signInThroughUi(page, user("user-a"), UPDATED_PASSWORD, true);
    await expect(page.getByTitle("تسجيل الخروج", { exact: true })).toBeVisible();
    await page.getByTitle("تسجيل الخروج", { exact: true }).click();
    await expect.poll(() => safePath(page)).toBe("/auth/login");
    const oldPasswordMailboxCount = await matchingMessageCount(user("user-a").email);
    await signInThroughUi(page, user("user-a"), INITIAL_PASSWORD, false);
    expect(await matchingMessageCount(user("user-a").email)).toBe(oldPasswordMailboxCount);
    await context.close();

    const reused = await openRecoveryLink(browser, artifact);
    let reusedUpdates = 0;
    reused.page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.origin === PROVIDER_URL.origin && url.pathname === PASSWORD_UPDATE_PATH && request.method() === "PUT") reusedUpdates += 1;
    });
    await expectRecoveryInvalid(reused.page);
    expect(reusedUpdates).toBe(0);
    await reused.context.close();
  });

  test("@plan020-provider a real provider recovery link expires and a fresh request remains possible", async ({ browser }) => {
    const artifact = await requestLink(browser, "expiry");
    const expiresAt = Date.now() + (RECOVERY_EXPIRY_SECONDS + 2) * 1000;
    await expect.poll(() => Date.now() >= expiresAt, {
      timeout: (RECOVERY_EXPIRY_SECONDS + 5) * 1000,
      message: "The configured local provider recovery lifetime must elapse."
    }).toBe(true);
    const expired = await openRecoveryLink(browser, artifact);
    let updates = 0;
    expired.page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.origin === PROVIDER_URL.origin && url.pathname === PASSWORD_UPDATE_PATH && request.method() === "PUT") updates += 1;
    });
    await expectRecoveryInvalid(expired.page);
    expect(updates).toBe(0);
    await expired.context.close();
    const replacementArtifact = await requestLink(browser, "expiry");
    const fresh = await openRecoveryLink(browser, replacementArtifact);
    await expectRecoveryReady(fresh.page);
    await fresh.context.close();
  });

  test("@plan020-provider a replacement subject invalidates recovery and sessions stay isolated", async ({ browser }) => {
    const artifact = await requestLink(browser, "replacement");
    const recovery = await openRecoveryLink(browser, artifact);
    await expectRecoveryReady(recovery.page);
    await recovery.page.getByLabel("كلمة المرور الجديدة", { exact: true }).fill(UPDATED_PASSWORD);
    let updates = 0;
    recovery.page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.origin === PROVIDER_URL.origin && url.pathname === PASSWORD_UPDATE_PATH && request.method() === "PUT") updates += 1;
    });
    const replacementPage = await recovery.context.newPage();
    await recovery.context.clearCookies();
    await signInThroughUi(replacementPage, user("user-b"), INITIAL_PASSWORD, true);
    await expectRecoveryInvalid(recovery.page);
    expect(updates).toBe(0);
    await recovery.context.close();

    const isolationArtifact = await requestLink(browser, "isolation");
    const isolatedRecovery = await openRecoveryLink(browser, isolationArtifact);
    await expectRecoveryReady(isolatedRecovery.page);
    const subjectB = await newAnonymousPage(browser);
    await signInThroughUi(subjectB.page, user("user-b"), INITIAL_PASSWORD, true);
    await subjectB.page.goto(RECOVERY_PATH);
    await expectRecoveryInvalid(subjectB.page);
    await expectRecoveryReady(isolatedRecovery.page);
    await subjectB.context.close();
    await expectRecoveryReady(isolatedRecovery.page);
    await isolatedRecovery.context.close();
    const afterClose = await newAnonymousPage(browser);
    await afterClose.page.goto(RECOVERY_PATH);
    await expectRecoveryInvalid(afterClose.page);
    await afterClose.context.close();
  });

  test("@plan020-provider Back, Forward, and reload cannot revive stale recovery ownership", async ({ browser }) => {
    const historyArtifact = await requestLink(browser, "history");
    const historyRecovery = await newAnonymousPage(browser, undefined, historyArtifact.verifierState);
    let historyUpdates = 0;
    let historyRecoveryEvents = 0;
    let historyPasswordSignIns = 0;
    let historyPhase: SafeHistoryObservation["phase"] = "establish";
    const historyObservations: SafeHistoryObservation[] = [];
    const recordHistoryObservation = (observation: SafeHistoryObservation) => {
      const previous = historyObservations.at(-1);
      if (
        previous?.phase === observation.phase &&
        previous.source === observation.source &&
        previous.pathname === observation.pathname
      ) return;
      historyObservations.push(observation);
    };
    const observedHistoryPath = (phase: SafeHistoryObservation["phase"], pathname: string) =>
      historyObservations.some((observation) => observation.phase === phase && observation.pathname === pathname);
    const safeHistoryDiagnostic = () => JSON.stringify({
      observations: historyObservations,
      recoveryEvents: historyRecoveryEvents,
      passwordUpdates: historyUpdates,
      passwordSignIns: historyPasswordSignIns,
      subject: "recovery-user-a"
    });
    historyRecovery.page.on("framenavigated", (frame) => {
      if (frame !== historyRecovery.page.mainFrame()) return;
      const url = new URL(frame.url());
      if (url.origin !== APP_URL.origin) return;
      recordHistoryObservation({ phase: historyPhase, source: "main-frame", pathname: url.pathname });
    });
    historyRecovery.page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.origin === PROVIDER_URL.origin && url.pathname === PASSWORD_UPDATE_PATH && request.method() === "PUT") historyUpdates += 1;
      if (
        url.origin === PROVIDER_URL.origin &&
        url.pathname === TOKEN_EXCHANGE_PATH &&
        url.searchParams.get("grant_type") === "password" &&
        request.method() === "POST"
      ) historyPasswordSignIns += 1;
      if (
        url.origin === APP_URL.origin &&
        request.method() === "GET" &&
        request.resourceType() === "document" &&
        request.isNavigationRequest()
      ) recordHistoryObservation({ phase: historyPhase, source: "document-request", pathname: url.pathname });
    });
    historyRecovery.page.on("response", (response) => {
      const url = new URL(response.url());
      if (
        url.origin === PROVIDER_URL.origin &&
        url.pathname === TOKEN_EXCHANGE_PATH &&
        url.searchParams.get("grant_type") === "pkce" &&
        response.request().method() === "POST" &&
        response.status() >= 200 &&
        response.status() < 300
      ) historyRecoveryEvents += 1;
    });
    await historyRecovery.page.goto("/auth/forgot-password");
    await assignProviderRecoveryLink(historyRecovery.page, historyArtifact.link);
    await expectRecoveryReady(historyRecovery.page);
    await expect(historyRecovery.page.getByLabel("كلمة المرور الجديدة", { exact: true })).toHaveValue("");
    expect(historyRecoveryEvents, safeHistoryDiagnostic()).toBe(1);
    expect(historyUpdates, safeHistoryDiagnostic()).toBe(0);
    expect(historyPasswordSignIns, safeHistoryDiagnostic()).toBe(0);

    historyPhase = "leave";
    await historyRecovery.page.goto("/diary");
    expect(safePath(historyRecovery.page)).toBe("/diary");
    expect(observedHistoryPath("leave", "/diary"), safeHistoryDiagnostic()).toBe(true);
    await expect(historyRecovery.page.getByLabel("كلمة المرور الجديدة", { exact: true })).toHaveCount(0);
    expect(historyRecoveryEvents, safeHistoryDiagnostic()).toBe(1);
    expect(historyUpdates, safeHistoryDiagnostic()).toBe(0);

    historyPhase = "back";
    await historyRecovery.page.goBack();
    expect(safePath(historyRecovery.page)).toBe(RECOVERY_PATH);
    expect(observedHistoryPath("back", RECOVERY_PATH), safeHistoryDiagnostic()).toBe(true);
    await expectRecoveryInvalid(historyRecovery.page);
    await expect(historyRecovery.page.getByLabel("كلمة المرور الجديدة", { exact: true })).toHaveCount(0);
    expect(historyRecoveryEvents, safeHistoryDiagnostic()).toBe(1);
    expect(historyUpdates, safeHistoryDiagnostic()).toBe(0);
    expect(historyPasswordSignIns, safeHistoryDiagnostic()).toBe(0);

    historyPhase = "forward";
    await historyRecovery.page.goForward();
    expect(safePath(historyRecovery.page)).toBe("/diary");
    expect(observedHistoryPath("forward", "/diary"), safeHistoryDiagnostic()).toBe(true);
    await expect(historyRecovery.page.getByLabel("كلمة المرور الجديدة", { exact: true })).toHaveCount(0);
    expect(historyRecoveryEvents, safeHistoryDiagnostic()).toBe(1);
    expect(historyUpdates, safeHistoryDiagnostic()).toBe(0);
    expect(historyPasswordSignIns, safeHistoryDiagnostic()).toBe(0);

    historyPhase = "reload";
    await historyRecovery.page.reload();
    expect(safePath(historyRecovery.page)).toBe("/diary");
    expect(observedHistoryPath("reload", "/diary"), safeHistoryDiagnostic()).toBe(true);
    await expect(historyRecovery.page.getByLabel("كلمة المرور الجديدة", { exact: true })).toHaveCount(0);
    expect(historyRecoveryEvents, safeHistoryDiagnostic()).toBe(1);
    expect(historyUpdates, safeHistoryDiagnostic()).toBe(0);
    expect(historyPasswordSignIns, safeHistoryDiagnostic()).toBe(0);
    await historyRecovery.context.close();

    const reloadArtifact = await requestLink(browser, "reload");
    const reloadRecovery = await newAnonymousPage(browser, undefined, reloadArtifact.verifierState);
    await reloadRecovery.page.goto("/auth/forgot-password");
    let reloadUpdates = 0;
    reloadRecovery.page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.origin === PROVIDER_URL.origin && url.pathname === PASSWORD_UPDATE_PATH && request.method() === "PUT") reloadUpdates += 1;
    });
    let exchangeRequests = 0;
    let releaseExchange!: () => void;
    const firstExchangeHeld = new Promise<void>((resolve) => { releaseExchange = resolve; });
    const exchangeMatcher = (url: URL) => url.origin === PROVIDER_URL.origin &&
      url.pathname === TOKEN_EXCHANGE_PATH && url.searchParams.get("grant_type") === "pkce";
    await reloadRecovery.page.route(exchangeMatcher, async (route) => {
      exchangeRequests += 1;
      if (exchangeRequests === 1) {
        await firstExchangeHeld;
        try {
          await route.abort("aborted");
        } catch {
          // Reload may already have cancelled the old document's exchange.
        }
        return;
      }
      await route.continue();
    });
    await assignProviderRecoveryLink(reloadRecovery.page, reloadArtifact.link);
    await expect.poll(() => exchangeRequests, { message: "The first real PKCE exchange must be held before readiness." }).toBe(1);
    await expect(reloadRecovery.page.getByRole("status")).toHaveText("جارٍ التحميل...");
    await expect(reloadRecovery.page.getByLabel("كلمة المرور الجديدة", { exact: true })).toHaveCount(0);
    try {
      await reloadRecovery.page.reload({ waitUntil: "commit" });
    } finally {
      releaseExchange();
    }
    await expectRecoveryReady(reloadRecovery.page);
    expect(exchangeRequests).toBe(2);
    await reloadRecovery.page.unroute(exchangeMatcher);
    await reloadRecovery.page.reload();
    await expectRecoveryInvalid(reloadRecovery.page);
    expect(reloadUpdates).toBe(0);
    await reloadRecovery.context.close();

    const navigationArtifact = await requestLink(browser, "navigation");
    const navigationRecovery = await openRecoveryLink(browser, navigationArtifact);
    await expectRecoveryReady(navigationRecovery.page);
    let navigationUpdates = 0;
    let navigationResponses = 0;
    let releaseUpdate!: () => void;
    const updateHeld = new Promise<void>((resolve) => { releaseUpdate = resolve; });
    const updateMatcher = (url: URL) => url.origin === PROVIDER_URL.origin && url.pathname === PASSWORD_UPDATE_PATH;
    await navigationRecovery.page.route(updateMatcher, async (route) => {
      await updateHeld;
      try {
        await route.continue();
      } catch {
        // Navigation may cancel the real provider-bound request before network fallthrough.
      }
    });
    navigationRecovery.page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.origin === PROVIDER_URL.origin && url.pathname === PASSWORD_UPDATE_PATH && request.method() === "PUT") navigationUpdates += 1;
    });
    navigationRecovery.page.on("response", (response) => {
      const url = new URL(response.url());
      if (url.origin === PROVIDER_URL.origin && url.pathname === PASSWORD_UPDATE_PATH && response.request().method() === "PUT") navigationResponses += 1;
    });
    const navigationPassword = navigationRecovery.page.getByLabel("كلمة المرور الجديدة", { exact: true });
    await navigationPassword.fill(UPDATED_PASSWORD);
    await navigationPassword.focus();
    await navigationRecovery.page.keyboard.press("Enter");
    await expect.poll(() => navigationUpdates, { message: "The pending-navigation scenario must issue one provider-bound update." }).toBe(1);
    await expect(navigationRecovery.page.getByRole("button", { name: "جارٍ الإرسال...", exact: true })).toBeDisabled();
    await expectSafeFocusWithin(navigationRecovery.page, "form", "Focus must remain coherent while navigation begins during a held update.");
    try {
      await navigationRecovery.page.goto("/diary", { waitUntil: "commit" });
    } finally {
      releaseUpdate();
    }
    await navigationRecovery.page.unroute(updateMatcher);
    expect(safePath(navigationRecovery.page)).toBe("/diary");
    expect(navigationUpdates).toBe(1);
    expect(navigationResponses).toBe(0);
    await navigationRecovery.context.close();

    const unchangedPassword = await newAnonymousPage(browser);
    await signInThroughUi(unchangedPassword.page, user("navigation"), INITIAL_PASSWORD, true);
    await unchangedPassword.context.close();
  });
});
