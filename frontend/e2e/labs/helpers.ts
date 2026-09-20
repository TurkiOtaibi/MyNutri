import { randomUUID } from "node:crypto";

import {
  expect,
  test as base,
  type APIRequestContext,
  type Browser,
  type BrowserContext,
  type Page,
  type Response,
} from "@playwright/test";
import { createChunks, stringToBase64URL } from "@supabase/ssr";

import type {
  LabCreateReceipt,
  LabCreateRequest,
  LabOverviewResponse,
  LabResultPatch,
  LabResultResponse,
  LabTestDetailResponse,
  ProfileInput,
} from "../../lib/types";
import { applyProfileThroughTargetPlan } from "../profile-api";

export const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const AUTH_URL = process.env.PLAYWRIGHT_SUPABASE_URL ?? "http://127.0.0.1:8765";
const PASSWORD = "Labs-owner-password-2026!";
const API_ORIGIN = new URL(API_URL).origin;
const AUTH_COOKIE_KEY = `sb-${new URL(AUTH_URL).hostname.split(".")[0]}-auth-token`;

for (const value of [API_URL, AUTH_URL]) {
  const hostname = new URL(value).hostname;
  if (hostname !== "127.0.0.1" && hostname !== "localhost") {
    throw new Error(`Labs E2E helper refuses non-loopback target ${value}`);
  }
}

export type LabsActor = {
  email: string;
  token: string;
  principalId: string;
  authCookies: Array<{
    name: string;
    value: string;
    expires: number;
  }>;
};

export type LabsApi = {
  actor: LabsActor;
  create: (
    date: string,
    rows: LabCreateRequest["results"],
    key?: string,
  ) => Promise<LabCreateReceipt>;
  overview: () => Promise<LabOverviewResponse>;
  detail: (testKey: string) => Promise<LabTestDetailResponse>;
  patch: (id: string, data: LabResultPatch) => Promise<LabResultResponse>;
  remove: (id: string) => Promise<void>;
};

type LabsFixtures = {
  initialLabsProfile: Partial<Pick<ProfileInput, "sex" | "birth_date">>;
  labsHasTouch: boolean;
  labsApi: LabsApi;
  labsPage: Page;
};

const profile: ProfileInput = {
  sex: "male",
  birth_date: "1990-01-01",
  height_cm: 175,
  weight_kg: 78,
  activity_level: "moderate",
  goal: "maintain",
  protein_per_kg: 1.2,
  fat_pct: 0.25,
  selected_cut_intensity: 0.2,
};

function headers(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export async function createActor(
  request: APIRequestContext,
  initialProfile: Partial<Pick<ProfileInput, "sex" | "birth_date">>,
): Promise<LabsActor> {
  const email = `labs-owner-${randomUUID()}@example.test`;
  const tokenResponse = await fetch(`${AUTH_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apikey: "e2e-public-key", "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: PASSWORD }),
  });
  expect(tokenResponse.status).toBe(200);
  const authSession = await tokenResponse.json() as {
    access_token: string;
    expires_at: number;
  } & Record<string, unknown>;
  const token = authSession.access_token;
  expect(Number.isFinite(authSession.expires_at)).toBe(true);
  const accountResponse = await request.get(`${API_URL}/account/me`, { headers: headers(token) });
  expect(accountResponse.status(), await accountResponse.text()).toBe(200);
  const account = await accountResponse.json() as { principal_id: string; role: string };
  expect(account.role).toBe("user");
  await applyProfileThroughTargetPlan(request, token, { ...profile, ...initialProfile });
  return {
    email,
    token,
    principalId: account.principal_id,
    authCookies: createChunks(
      AUTH_COOKIE_KEY,
      `base64-${stringToBase64URL(JSON.stringify(authSession))}`,
    ).map(({ name, value }) => ({ name, value, expires: authSession.expires_at })),
  };
}

export function createLabsApi(request: APIRequestContext, actor: LabsActor): LabsApi & { cleanup: () => Promise<void> } {
  const resultIds = new Set<string>();
  const actorHeaders = () => headers(actor.token);
  const api: LabsApi & { cleanup: () => Promise<void> } = {
    actor,
    async create(date, rows, key = `e2e-labs-${randomUUID()}`) {
      const response = await request.post(`${API_URL}/labs/results`, {
        headers: { ...actorHeaders(), "Idempotency-Key": key },
        data: { test_date: date, results: rows },
      });
      expect(response.status(), await response.text()).toBe(201);
      const receipt = await response.json() as LabCreateReceipt;
      for (const id of receipt.result_ids) resultIds.add(id);
      return receipt;
    },
    async overview() {
      const response = await request.get(`${API_URL}/labs`, { headers: actorHeaders() });
      expect(response.status(), await response.text()).toBe(200);
      return response.json() as Promise<LabOverviewResponse>;
    },
    async detail(testKey) {
      const response = await request.get(`${API_URL}/labs/tests/${encodeURIComponent(testKey)}`, {
        headers: actorHeaders(),
      });
      expect(response.status(), await response.text()).toBe(200);
      return response.json() as Promise<LabTestDetailResponse>;
    },
    async patch(id, data) {
      const response = await request.patch(`${API_URL}/labs/results/${encodeURIComponent(id)}`, {
        headers: actorHeaders(),
        data,
      });
      expect(response.status(), await response.text()).toBe(200);
      return response.json() as Promise<LabResultResponse>;
    },
    async remove(id) {
      const response = await request.delete(`${API_URL}/labs/results/${encodeURIComponent(id)}`, {
        headers: actorHeaders(),
      });
      expect([204, 404]).toContain(response.status());
      resultIds.delete(id);
    },
    async cleanup() {
      const failures: unknown[] = [];
      for (const id of resultIds) {
        try {
          const response = await request.delete(`${API_URL}/labs/results/${encodeURIComponent(id)}`, {
            headers: actorHeaders(),
          });
          expect([204, 404]).toContain(response.status());
        } catch (error) { failures.push(error); }
      }
      resultIds.clear();
      if (failures.length) throw new AggregateError(failures, "Labs fixture cleanup failed.");
    },
  };
  return api;
}

export async function loginOwner(browser: Browser, actor: LabsActor, hasTouch: boolean, allowServiceWorkers = false): Promise<{ context: BrowserContext; page: Page }> {
  const context = await browser.newContext({
    hasTouch,
    serviceWorkers: allowServiceWorkers ? "allow" : "block",
    storageState: {
      cookies: actor.authCookies.map(({ name, value, expires }) => ({
        name,
        value,
        domain: "127.0.0.1",
        path: "/",
        expires,
        httpOnly: false,
        secure: false,
        sameSite: "Lax",
      })),
      origins: [],
    },
  });
  const page = await context.newPage();
  return { context, page };
}

function isExactGet(response: Response, pathname: string) {
  const request = response.request();
  const url = new URL(response.url());
  return url.origin === API_ORIGIN &&
    url.pathname === pathname &&
    url.search === "" &&
    request.method() === "GET" &&
    request.resourceType() === "fetch";
}

export function waitForLabsGet(page: Page, pathname: string) {
  const response = page.waitForResponse((candidate) => isExactGet(candidate, pathname));
  void response.catch(() => undefined);
  return response;
}

export async function navigateToOwnerLabs(page: Page) {
  const accountResponse = waitForLabsGet(page, "/account/me");
  const catalogResponse = waitForLabsGet(page, "/labs/catalog");
  const overviewResponse = waitForLabsGet(page, "/labs");

  await page.goto("/labs");
  const [account, catalog, overview] = await Promise.all([
    accountResponse,
    catalogResponse,
    overviewResponse,
  ]);
  expect(account.status()).toBe(200);
  expect(catalog.status()).toBe(200);
  expect(overview.status()).toBe(200);
}

export const test = base.extend<LabsFixtures>({
  initialLabsProfile: [{}, { option: true }],
  labsHasTouch: [false, { option: true }],
  labsApi: async ({ request, initialLabsProfile }, fixtureUse) => {
    const actor = await createActor(request, initialLabsProfile);
    const api = createLabsApi(request, actor);
    try {
      await fixtureUse(api);
    } finally {
      await api.cleanup();
    }
  },
  labsPage: async ({ browser, labsApi, labsHasTouch }, fixtureUse) => {
    const { context, page } = await loginOwner(browser, labsApi.actor, labsHasTouch);
    try {
      await fixtureUse(page);
    } finally {
      await context.close();
    }
  },
});

export { expect } from "@playwright/test";

export function offsetIsoDate(input: string, days: number): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(input);
  if (!match) throw new Error(`Invalid Labs server date: ${input}`);
  return new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]) + days))
    .toISOString()
    .slice(0, 10);
}
