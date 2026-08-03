import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Locator, type Page } from "@playwright/test";

const AUTH_URL = process.env.PLAYWRIGHT_SUPABASE_URL ?? "http://127.0.0.1:8765";
const ADMIN_EMAIL = "admin.e2e@example.test";
const PASSWORD = "Plan-020-password-2026!";

type RecoveryWindow = Window & {
  __mynutriE2EVerifyRecoveryOtp?: (email: string, token: string) => Promise<{ error: unknown }>;
  __mynutriE2ERefreshSession?: () => Promise<{ error: unknown }>;
  __mynutriE2ESignOut?: () => Promise<{ error: unknown }>;
  __mynutriE2ESignInWithPassword?: (email: string, password: string) => Promise<{ error: unknown }>;
};

async function waitForAuthControls(page: Page) {
  await page.waitForFunction(() =>
    typeof (window as RecoveryWindow).__mynutriE2EVerifyRecoveryOtp === "function"
  );
}

async function verifyRecovery(page: Page, code: string) {
  await waitForAuthControls(page);
  return page.evaluate(async ({ email, recoveryCode }) => {
    const verify = (window as RecoveryWindow).__mynutriE2EVerifyRecoveryOtp;
    if (!verify) throw new Error("Local recovery control is unavailable.");
    const result = await verify(email, recoveryCode);
    return { ok: !result.error };
  }, { email: ADMIN_EMAIL, recoveryCode: code });
}

async function openReadyReset(page: Page, suffix: string) {
  await page.goto("/auth/reset-password");
  await expect(page.locator('.auth-message[role="alert"]')).toContainText("انتهت صلاحية الرابط");
  expect(await verifyRecovery(page, `valid-recovery-code-${suffix}`)).toEqual({ ok: true });
  await expect(page.getByLabel("كلمة المرور الجديدة", { exact: true })).toBeVisible();
}

async function callAuthControl(page: Page, action: "refresh" | "signOut") {
  const ok = await page.evaluate(async (operation) => {
    const testWindow = window as RecoveryWindow;
    const control = operation === "refresh"
      ? testWindow.__mynutriE2ERefreshSession
      : testWindow.__mynutriE2ESignOut;
    if (!control) throw new Error("Local auth control is unavailable.");
    return !(await control()).error;
  }, action);
  expect(ok).toBe(true);
}

async function inputMatches(input: Locator, expected: string) {
  return input.evaluate((element: HTMLInputElement, value) => element.value === value, expected);
}

test("@plan020 recovery request is neutral for known and unknown addresses", async ({ browser }) => {
  const messages: string[] = [];
  for (const email of [ADMIN_EMAIL, `unknown-${Date.now()}@example.test`]) {
    const context = await browser.newContext({ storageState: undefined });
    const page = await context.newPage();
    let requests = 0;
    await page.route((url) => url.origin === new URL(AUTH_URL).origin && url.pathname === "/auth/v1/recover", async (route) => {
      requests += 1;
      await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
    });
    await page.goto("/auth/forgot-password");
    await page.getByLabel("البريد الإلكتروني", { exact: true }).fill(email);
    await page.getByRole("button", { name: "إرسال رابط الاستعادة", exact: true }).click();
    const status = page.getByRole("status");
    await expect(status).toBeVisible();
    messages.push(await status.innerText());
    expect(requests).toBe(1);
    await context.close();
  }
  expect(messages).toEqual(["تحقق من بريدك لإكمال العملية.", "تحقق من بريدك لإكمال العملية."]);
});

test("@plan020 returned request failure unlocks exactly one retry and duplicate submit is locked", async ({ browser }) => {
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  let requests = 0;
  let releaseFirst!: () => void;
  const firstHeld = new Promise<void>((resolve) => { releaseFirst = resolve; });
  await page.route((url) => url.origin === new URL(AUTH_URL).origin && url.pathname === "/auth/v1/recover", async (route) => {
    requests += 1;
    if (requests === 1) {
      await firstHeld;
      await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ message: "private provider detail" }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });
  await page.goto("/auth/forgot-password");
  await page.getByLabel("البريد الإلكتروني", { exact: true }).fill(ADMIN_EMAIL);
  await page.locator("form").evaluate((form: HTMLFormElement) => {
    form.requestSubmit();
    form.requestSubmit();
  });
  await expect.poll(() => requests).toBe(1);
  await expect(page.getByRole("button", { name: "جارٍ الإرسال...", exact: true })).toBeDisabled();
  releaseFirst();
  await expect(page.locator('.auth-message[role="alert"]')).toHaveText("تعذر إكمال الطلب. تحقق من الاتصال وحاول مرة أخرى.");
  await expect(page.getByText("private provider detail", { exact: false })).toHaveCount(0);
  await page.getByRole("button", { name: "إرسال رابط الاستعادة", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("تحقق من بريدك لإكمال العملية.");
  expect(requests).toBe(2);
  await context.close();
});

test("@plan020 thrown recovery request failure unlocks a successful retry", async ({ browser }) => {
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  let requests = 0;
  await page.route((url) => url.origin === new URL(AUTH_URL).origin && url.pathname === "/auth/v1/recover", async (route) => {
    requests += 1;
    if (requests === 1) await route.abort("connectionfailed");
    else await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });
  await page.goto("/auth/forgot-password");
  await page.getByLabel("البريد الإلكتروني", { exact: true }).fill(ADMIN_EMAIL);
  await page.getByRole("button", { name: "إرسال رابط الاستعادة", exact: true }).click();
  await expect(page.locator('.auth-message[role="alert"]')).toBeVisible();
  await page.getByRole("button", { name: "إرسال رابط الاستعادة", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("تحقق من بريدك لإكمال العملية.");
  expect(requests).toBe(2);
  await context.close();
});

test("@plan020 missing and expired recovery state send zero password updates", async ({ browser }) => {
  for (const code of [null, "expired-recovery-code"] as const) {
    const context = await browser.newContext({ storageState: undefined });
    const page = await context.newPage();
    let updates = 0;
    page.on("request", (request) => {
      if (request.method() === "PUT" && new URL(request.url()).pathname === "/auth/v1/user") updates += 1;
    });
    await page.goto("/auth/reset-password");
    await expect(page.locator('.auth-message[role="alert"]')).toContainText("انتهت صلاحية الرابط");
    if (code) expect(await verifyRecovery(page, code)).toEqual({ ok: false });
    await expect(page.getByLabel("كلمة المرور الجديدة", { exact: true })).toHaveCount(0);
    expect(updates).toBe(0);
    await context.close();
  }
});

test("@plan020 update provider failure preserves password and retry succeeds", async ({ browser }) => {
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  let updates = 0;
  await page.route((url) => url.origin === new URL(AUTH_URL).origin && url.pathname === "/auth/v1/user", async (route) => {
    updates += 1;
    if (updates === 1) {
      await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ message: "private update detail" }) });
      return;
    }
    await route.continue();
  });
  await openReadyReset(page, `retry-${Date.now()}`);
  const password = page.getByLabel("كلمة المرور الجديدة", { exact: true });
  await password.fill(PASSWORD);
  await page.getByRole("button", { name: "حفظ كلمة المرور", exact: true }).click();
  await expect(page.locator('.auth-message[role="alert"]')).toHaveText("تعذر إكمال الطلب. تحقق من الاتصال وحاول مرة أخرى.");
  expect(await inputMatches(password, PASSWORD)).toBe(true);
  await expect(page.getByText("private update detail", { exact: false })).toHaveCount(0);
  await page.getByRole("button", { name: "حفظ كلمة المرور", exact: true }).click();
  await page.waitForURL(/\/diary$/);
  expect(updates).toBe(2);
  await context.close();
});

test("@plan020 aborted password update preserves input and unlocks one successful retry", async ({ browser }) => {
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  let updates = 0;
  await page.route((url) => url.origin === new URL(AUTH_URL).origin && url.pathname === "/auth/v1/user", async (route) => {
    updates += 1;
    if (updates === 1) {
      await route.abort("connectionfailed");
      return;
    }
    await route.continue();
  });
  await openReadyReset(page, `aborted-update-${Date.now()}`);
  const password = page.getByLabel("كلمة المرور الجديدة", { exact: true });
  await password.fill(PASSWORD);
  await page.getByRole("button", { name: "حفظ كلمة المرور", exact: true }).click();
  await expect(page.locator('.auth-message[role="alert"]')).toHaveText("تعذر إكمال الطلب. تحقق من الاتصال وحاول مرة أخرى.");
  expect(await inputMatches(password, PASSWORD)).toBe(true);
  expect(updates).toBe(1);
  await page.getByRole("button", { name: "حفظ كلمة المرور", exact: true }).click();
  await page.waitForURL(/\/diary$/);
  expect(updates).toBe(2);
  await context.close();
});

test("@plan020 duplicate reset submit sends one update and redirects only after success", async ({ browser }) => {
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  let updates = 0;
  let releaseUpdate!: () => void;
  const updateHeld = new Promise<void>((resolve) => { releaseUpdate = resolve; });
  await page.route((url) => url.origin === new URL(AUTH_URL).origin && url.pathname === "/auth/v1/user", async (route) => {
    updates += 1;
    await updateHeld;
    await route.continue();
  });
  await openReadyReset(page, `duplicate-${Date.now()}`);
  await page.getByLabel("كلمة المرور الجديدة", { exact: true }).fill(PASSWORD);
  await page.locator("form").evaluate((form: HTMLFormElement) => {
    form.requestSubmit();
    form.requestSubmit();
  });
  await expect.poll(() => updates).toBe(1);
  await expect(page.getByRole("button", { name: "جارٍ الإرسال...", exact: true })).toBeDisabled();
  await expect(page).toHaveURL(/\/auth\/reset-password$/);
  releaseUpdate();
  await page.waitForURL(/\/diary$/);
  expect(updates).toBe(1);
  await context.close();
});

test("@plan020 refresh preserves recovery readiness while sign-out invalidates it", async ({ browser }) => {
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await openReadyReset(page, `lifecycle-${Date.now()}`);
  const password = page.getByLabel("كلمة المرور الجديدة", { exact: true });
  await password.fill(PASSWORD);
  await callAuthControl(page, "refresh");
  expect(await inputMatches(password, PASSWORD)).toBe(true);
  await callAuthControl(page, "signOut");
  await expect(page.locator('.auth-message[role="alert"]')).toContainText("انتهت صلاحية الرابط");
  await expect(page.getByLabel("كلمة المرور الجديدة", { exact: true })).toHaveCount(0);
  await context.close();
});

test("@plan020 a replacement subject invalidates the previous recovery action", async ({ browser }) => {
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await openReadyReset(page, `subject-${Date.now()}`);
  const password = page.getByLabel("كلمة المرور الجديدة", { exact: true });
  await password.fill(PASSWORD);
  const signedIn = await page.evaluate(async ({ email, replacementPassword }) => {
    const signIn = (window as RecoveryWindow).__mynutriE2ESignInWithPassword;
    if (!signIn) throw new Error("Local sign-in control is unavailable.");
    return !(await signIn(email, replacementPassword)).error;
  }, { email: `plan020-subject-${Date.now()}@example.test`, replacementPassword: PASSWORD });
  expect(signedIn).toBe(true);
  await expect(page.locator('.auth-message[role="alert"]')).toContainText("انتهت صلاحية الرابط");
  await expect(password).toHaveCount(0);
  await expect(page.locator('input[type="password"]')).toHaveCount(0);
  await context.close();
});

test("@plan020 recovery UI is accessible at supported mobile width", async ({ browser }) => {
  const context = await browser.newContext({ storageState: undefined, viewport: { width: 320, height: 700 } });
  const page = await context.newPage();
  await openReadyReset(page, `axe-${Date.now()}`);
  const accessibility = await new AxeBuilder({ page }).include(".auth-panel").analyze();
  expect(accessibility.violations.filter((violation) => ["serious", "critical"].includes(violation.impact ?? ""))).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
  await context.close();
});
