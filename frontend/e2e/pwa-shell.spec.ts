import { expect, test, type Page, type Request, type Response, type Route } from "@playwright/test";

const APP_CACHE_PREFIX = "mynutri-shell-";
const CURRENT_CACHE = "mynutri-shell-v3";
const GENERIC_PATHS = new Set(["/offline", "/manifest.json", "/icon.svg"]);
const APP_ORIGIN = "http://127.0.0.1:3000";

async function waitForWorkerControl(page: Page): Promise<void> {
  await page.goto("/offline");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
    if (navigator.serviceWorker.controller) return;
    await new Promise<void>((resolve) => {
      navigator.serviceWorker.addEventListener("controllerchange", () => resolve(), { once: true });
    });
  });
}

type AppCacheEntry = {
  cacheName: string;
  method: string;
  origin: string;
  pathname: string;
  queryKeys: string[];
  urlDigest: string;
  bodyDigest: string;
  bodyByteLength: number;
  containsPrivateMarker: boolean;
};

async function appCacheEntries(page: Page): Promise<AppCacheEntry[]> {
  return page.evaluate(async ({ prefix }) => {
    const digest = async (value: string) => Array.from(
      new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)))
    ).map((byte) => byte.toString(16).padStart(2, "0")).join("");
    const entries: AppCacheEntry[] = [];
    for (const key of await caches.keys()) {
      if (!key.startsWith(prefix)) continue;
      const cache = await caches.open(key);
      for (const request of await cache.keys()) {
        const response = await cache.match(request);
        const url = new URL(request.url);
        const body = response ? await response.clone().text() : "";
        entries.push({
          cacheName: key,
          method: request.method,
          origin: url.origin,
          pathname: url.pathname,
          queryKeys: [...url.searchParams.keys()]
            .map((name) => /token|code|key|secret|session|auth|email/i.test(name) ? "[sensitive-key]" : name)
            .sort(),
          urlDigest: await digest(request.url),
          bodyDigest: await digest(body),
          bodyByteLength: new TextEncoder().encode(body).byteLength,
          containsPrivateMarker: /plan017-(?:personal-marker|private-post)|admin\.e2e|V2 E2E baseline/i.test(body)
        });
      }
    }
    return entries.sort((left, right) =>
      `${left.cacheName}\u0000${left.method}\u0000${left.urlDigest}`.localeCompare(
        `${right.cacheName}\u0000${right.method}\u0000${right.urlDigest}`
      )
    );
  }, { prefix: APP_CACHE_PREFIX });
}

type ImmutableRequestTracker = {
  inFlight: Set<Request>;
  generation: number;
};

function isImmutableNextStaticRequest(request: Request): boolean {
  const url = new URL(request.url());
  return (
    request.method() === "GET" &&
    url.origin === APP_ORIGIN &&
    url.pathname.startsWith("/_next/static/") &&
    url.search === ""
  );
}

async function waitForImmutableCacheSettlement(
  page: Page,
  tracker: ImmutableRequestTracker
): Promise<AppCacheEntry[]> {
  const startedAt = Date.now();
  let quietStartedAt: number | null = null;
  let previousInventory = "";
  let previousGeneration = tracker.generation;

  while (Date.now() - startedAt < 10_000) {
    const entries = await appCacheEntries(page);
    const inventory = JSON.stringify(entries);
    const now = Date.now();
    const changed = inventory !== previousInventory || tracker.generation !== previousGeneration;

    if (changed || tracker.inFlight.size > 0) {
      previousInventory = inventory;
      previousGeneration = tracker.generation;
      quietStartedAt = tracker.inFlight.size === 0 ? now : null;
    } else if (quietStartedAt === null) {
      quietStartedAt = now;
    } else if (now - quietStartedAt >= 750) {
      return entries;
    }

    await new Promise<void>((resolve) => setTimeout(resolve, 100));
  }

  throw new Error("PWA IMMUTABLE CACHE SETTLEMENT TIMEOUT");
}

function isExactRequest(request: Request, pathname: string, method = "GET"): boolean {
  const url = new URL(request.url());
  return request.method() === method && url.origin === APP_ORIGIN && url.pathname === pathname;
}

type ProfileRequestObservation = {
  origin: string;
  pathname: string;
  method: string;
  resourceType: string;
  isNavigation: boolean;
  queryKeys: string[];
  isRsc: boolean;
  isPrefetch: boolean;
  classification: "document-navigation" | "rsc" | "router-prefetch" | "next-route-data" | "unknown-dynamic";
  hasRscHeader: boolean;
  hasNextRouterPrefetchHeader: boolean;
  hasNextRouterStateTreeHeader: boolean;
  hasNextRouterSegmentPrefetchHeader: boolean;
  hasPurposePrefetch: boolean;
  hasSecPurposePrefetch: boolean;
  acceptsRsc: boolean;
};

const FORBIDDEN_DIAGNOSTIC_KEY = /cookie|authorization|set-cookie|access_token|refresh_token|token|secret|credential|session|auth/i;

function safeUrl(urlValue: string) {
  const url = new URL(urlValue);
  const queryKeys = [...url.searchParams.keys()]
    .map((key) => /token|code|key|secret|session|auth|email/i.test(key) ? "[sensitive-key]" : key)
    .sort();
  return { origin: url.origin, pathname: url.pathname, queryKeys };
}

function safeErrorCategory(errorText: string | null | undefined): "aborted" | "connection" | "blocked" | "other" | null {
  if (!errorText) return null;
  const value = errorText.toLowerCase();
  if (value.includes("abort") || value.includes("cancel")) return "aborted";
  if (value.includes("connection") || value.includes("failed")) return "connection";
  if (value.includes("block") || value.includes("cors")) return "blocked";
  return "other";
}

function stringifySafeDiagnostic(value: unknown): string {
  const inspect = (candidate: unknown): void => {
    if (!candidate || typeof candidate !== "object") return;
    for (const [key, nested] of Object.entries(candidate)) {
      if (FORBIDDEN_DIAGNOSTIC_KEY.test(key)) throw new Error(`Unsafe diagnostic key: ${key}`);
      inspect(nested);
    }
  };
  inspect(value);
  return JSON.stringify(value, null, 2);
}

function sanitizeSyntheticRequest(input: {
  url: string;
  headers: Record<string, string>;
  body: string | null;
  expectedBody: string | null;
}) {
  const names = Object.keys(input.headers).map((name) => name.toLowerCase());
  return {
    ...safeUrl(input.url),
    contentType: input.headers["Content-Type"] ?? input.headers["content-type"] ?? null,
    hasRestrictedHeader: names.some((name) =>
      /cookie|authorization|token|secret|credential|session|auth/i.test(name)
    ),
    bodyPresent: input.body !== null,
    bodyByteLength: input.body === null ? 0 : Buffer.byteLength(input.body),
    bodyMatchesExpected: input.body === input.expectedBody
  };
}

function observeProfileRequest(request: Request): ProfileRequestObservation | null {
  if (!isExactRequest(request, "/profile")) return null;

  const url = new URL(request.url());
  const headers = request.headers();
  const purpose = `${headers.purpose ?? ""} ${headers["sec-purpose"] ?? ""}`.toLowerCase();
  const isPrefetch =
    headers["next-router-prefetch"] === "1" ||
    "next-router-segment-prefetch" in headers ||
    purpose.includes("prefetch");
  const isRsc =
    url.searchParams.has("_rsc") ||
    headers.rsc === "1" ||
    "next-router-state-tree" in headers ||
    "next-router-segment-prefetch" in headers;
  const isNavigation = request.isNavigationRequest();
  const classification = isNavigation && request.resourceType() === "document"
    ? "document-navigation"
    : isPrefetch
      ? "router-prefetch"
      : isRsc
        ? "rsc"
        : url.pathname.startsWith("/_next/data/")
          ? "next-route-data"
          : "unknown-dynamic";

  return {
    origin: url.origin,
    pathname: url.pathname,
    method: request.method(),
    resourceType: request.resourceType(),
    isNavigation,
    queryKeys: [...url.searchParams.keys()]
      .map((key) => /token|code|key|secret|session|auth|email/i.test(key) ? "[sensitive-key]" : key)
      .sort(),
    isRsc,
    isPrefetch,
    classification,
    hasRscHeader: headers.rsc === "1",
    hasNextRouterPrefetchHeader: headers["next-router-prefetch"] === "1",
    hasNextRouterStateTreeHeader: "next-router-state-tree" in headers,
    hasNextRouterSegmentPrefetchHeader: "next-router-segment-prefetch" in headers,
    hasPurposePrefetch: (headers.purpose ?? "").toLowerCase().includes("prefetch"),
    hasSecPurposePrefetch: (headers["sec-purpose"] ?? "").toLowerCase().includes("prefetch"),
    acceptsRsc: (headers.accept ?? "").toLowerCase().includes("text/x-component")
  };
}

test("@plan017 worker activation awaits shell population and removes only obsolete app caches", async ({ page }) => {
  await page.goto("/manifest.json");
  await page.evaluate(async () => {
    await caches.open("mynutri-shell-v1");
    await caches.open("unrelated-cache");
    await navigator.serviceWorker.register("/service-worker.js");
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller) {
      await new Promise<void>((resolve) => {
        navigator.serviceWorker.addEventListener("controllerchange", () => resolve(), { once: true });
      });
    }
  });

  const state = await page.evaluate(async () => {
    const keys = await caches.keys();
    const cache = await caches.open("mynutri-shell-v3");
    const urls = (await cache.keys()).map((request) => new URL(request.url).pathname).sort();
    const registration = await navigator.serviceWorker.ready;
    return {
      controlled: navigator.serviceWorker.controller?.scriptURL ?? "",
      active: registration.active?.scriptURL ?? "",
      keys,
      urls
    };
  });

  expect(state.controlled).toMatch(/\/service-worker\.js$/);
  expect(state.active).toMatch(/\/service-worker\.js$/);
  expect(state.keys).toContain(CURRENT_CACHE);
  expect(state.keys).toContain("unrelated-cache");
  expect(state.keys).not.toContain("mynutri-shell-v1");
  expect(state.urls).toEqual(["/icon.svg", "/manifest.json", "/offline"]);
  const manifest = await page.evaluate(async () => {
    const response = await (await caches.open("mynutri-shell-v3")).match("/manifest.json");
    return response?.json();
  });
  expect(manifest).toMatchObject({
    start_url: "/diary",
    scope: "/",
    display: "standalone",
    dir: "rtl",
    lang: "ar"
  });
});

test("@plan017 bypasses API Auth RSC prefetch cross-origin and non-GET traffic", async ({ context }, testInfo) => {
  type BypassCase = {
    name: string;
    url: string;
    method: "GET" | "POST";
    headers: Record<string, string>;
    body?: string;
    mode: "same-origin" | "cors";
    credentials: "same-origin" | "omit";
  };
  type BypassObservation = {
    requests: Array<{
      method: string;
      origin: string;
      pathname: string;
      queryKeys: string[];
      resourceType: string;
      contentType: string | null;
      hasRscHeader: boolean;
      hasNextRouterPrefetchHeader: boolean;
      hasPurposePrefetch: boolean;
      bodyPresent: boolean;
      bodyByteLength: number;
      bodyMatchesExpected: boolean;
      contentTypeMatchesExpected: boolean;
    }>;
    responses: Array<{ origin: string; pathname: string; queryKeys: string[]; status: number; fromServiceWorker: boolean }>;
    failures: Array<"aborted" | "connection" | "blocked" | "other" | null>;
    fixtureMatches: number;
  };

  const cases: BypassCase[] = [
    {
      name: "api-get",
      url: `${APP_ORIGIN}/api/plan017?account=private`,
      method: "GET",
      headers: {},
      mode: "same-origin",
      credentials: "same-origin"
    },
    {
      name: "auth-get",
      url: "http://127.0.0.1:8765/auth/v1/plan017?token=private",
      method: "GET",
      headers: {},
      mode: "cors",
      credentials: "omit"
    },
    {
      name: "rsc-get",
      url: `${APP_ORIGIN}/diary?_rsc=plan017`,
      method: "GET",
      headers: { RSC: "1" },
      mode: "same-origin",
      credentials: "same-origin"
    },
    {
      name: "prefetch-get",
      url: `${APP_ORIGIN}/foods?prefetch=plan017`,
      method: "GET",
      headers: { "Next-Router-Prefetch": "1", Purpose: "prefetch" },
      mode: "same-origin",
      credentials: "same-origin"
    },
    {
      name: "next-data-get",
      url: `${APP_ORIGIN}/_next/data/plan017/page.json`,
      method: "GET",
      headers: {},
      mode: "same-origin",
      credentials: "same-origin"
    },
    {
      name: "cross-origin-get",
      url: "http://127.0.0.1:9876/plan017-cross-origin",
      method: "GET",
      headers: {},
      mode: "cors",
      credentials: "omit"
    },
    {
      name: "non-get-post",
      url: `${APP_ORIGIN}/offline`,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ marker: "plan017-private-post" }),
      mode: "same-origin",
      credentials: "same-origin"
    }
  ];
  const caseByRequest = new Map(cases.map((item) => [`${item.method} ${item.url}`, item]));
  const observations = new Map<string, BypassObservation>(
    cases.map((item) => [
      item.name,
      { requests: [], responses: [], failures: [], fixtureMatches: 0 }
    ])
  );
  const findCase = (request: Request) => caseByRequest.get(`${request.method()} ${request.url()}`);
  const onRequest = (request: Request) => {
    const item = findCase(request);
    if (!item) return;
    const headers = request.headers();
    const body = request.postData();
    observations.get(item.name)!.requests.push({
      method: request.method(),
      ...safeUrl(request.url()),
      resourceType: request.resourceType(),
      contentType: headers["content-type"] ?? null,
      hasRscHeader: headers.rsc === "1",
      hasNextRouterPrefetchHeader: headers["next-router-prefetch"] === "1",
      hasPurposePrefetch: (headers.purpose ?? "").toLowerCase().includes("prefetch"),
      bodyPresent: body !== null,
      bodyByteLength: body === null ? 0 : Buffer.byteLength(body),
      bodyMatchesExpected: body === (item.body ?? null),
      contentTypeMatchesExpected: (headers["content-type"] ?? null) === (item.headers["Content-Type"] ?? null)
    });
  };
  const onResponse = (response: Awaited<ReturnType<Request["response"]>>) => {
    if (!response) return;
    const item = findCase(response.request());
    if (!item) return;
    observations.get(item.name)!.responses.push({
      ...safeUrl(response.url()),
      status: response.status(),
      fromServiceWorker: response.fromServiceWorker()
    });
  };
  const onRequestFailed = (request: Request) => {
    const item = findCase(request);
    if (!item) return;
    observations.get(item.name)!.failures.push(safeErrorCategory(request.failure()?.errorText));
  };
  const immutableTracker: ImmutableRequestTracker = { inFlight: new Set(), generation: 0 };
  const onImmutableRequest = (request: Request) => {
    if (!isImmutableNextStaticRequest(request)) return;
    immutableTracker.inFlight.add(request);
    immutableTracker.generation += 1;
  };
  const onImmutableRequestComplete = (request: Request) => {
    immutableTracker.inFlight.delete(request);
  };
  const fulfillBypassCase = async (route: Route) => {
    const item = findCase(route.request());
    if (!item) {
      await route.continue();
      return;
    }
    observations.get(item.name)!.fixtureMatches += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: { "Access-Control-Allow-Origin": APP_ORIGIN },
      body: JSON.stringify({ marker: "plan017-personal-marker", case: item.name })
    });
  };
  context.on("request", onRequest);
  context.on("response", onResponse);
  context.on("requestfailed", onRequestFailed);
  context.on("request", onImmutableRequest);
  context.on("requestfinished", onImmutableRequestComplete);
  context.on("requestfailed", onImmutableRequestComplete);
  await context.route("**/*", fulfillBypassCase);
  const page = await context.newPage();

  const browserResults: Array<{
    name: string;
    outcome: "fulfilled" | "rejected";
    status?: number;
    responseOrigin?: string;
    responsePathname?: string;
    responseQueryKeys?: string[];
    responseUrlMatchesExpected?: boolean;
    errorName?: string;
    errorCategory?: "network" | "other";
  }> = [];
  let postCacheBefore: AppCacheEntry[] = [];
  let postCacheAfter: AppCacheEntry[] = [];
  let prePostSettlementDurationMs = 0;
  let postSettlementDurationMs = 0;
  try {
    await waitForWorkerControl(page);
    for (const item of cases) {
      if (item.name === "non-get-post") {
        const settlementStartedAt = Date.now();
        postCacheBefore = await waitForImmutableCacheSettlement(page, immutableTracker);
        prePostSettlementDurationMs = Date.now() - settlementStartedAt;
        expect(prePostSettlementDurationMs).toBeLessThan(10_000);
        expect(immutableTracker.inFlight.size).toBe(0);
      }
      const result = await page.evaluate(async (requestCase) => {
        try {
          const response = await fetch(requestCase.url, {
            method: requestCase.method,
            headers: requestCase.headers,
            body: requestCase.body,
            mode: requestCase.mode,
            credentials: requestCase.credentials,
            redirect: "follow"
          });
          return {
            name: requestCase.name,
            outcome: "fulfilled" as const,
            status: response.status,
            responseOrigin: new URL(response.url).origin,
            responsePathname: new URL(response.url).pathname,
            responseQueryKeys: [...new URL(response.url).searchParams.keys()]
              .map((key) => /token|code|key|secret|session|auth|email/i.test(key) ? "[sensitive-key]" : key)
              .sort(),
            responseUrlMatchesExpected: response.url === requestCase.url
          };
        } catch (error) {
          return {
            name: requestCase.name,
            outcome: "rejected" as const,
            errorName: error instanceof Error ? error.name : "UnknownError",
            errorCategory: error instanceof TypeError ? "network" as const : "other" as const
          };
        }
      }, item);
      browserResults.push(result);
      if (item.name === "non-get-post") {
        const settlementStartedAt = Date.now();
        postCacheAfter = await waitForImmutableCacheSettlement(page, immutableTracker);
        postSettlementDurationMs = Date.now() - settlementStartedAt;
        expect(postSettlementDurationMs).toBeLessThan(10_000);
        expect(immutableTracker.inFlight.size).toBe(0);
      }
    }
  } finally {
    await context.unroute("**/*", fulfillBypassCase);
    context.off("request", onRequest);
    context.off("response", onResponse);
    context.off("requestfailed", onRequestFailed);
    context.off("request", onImmutableRequest);
    context.off("requestfinished", onImmutableRequestComplete);
    context.off("requestfailed", onImmutableRequestComplete);
  }

  testInfo.annotations.push(
    {
      type: "pwa-immutable-settlement-before-post",
      description: `duration_ms=${prePostSettlementDurationMs};cache_entries=${postCacheBefore.length}`
    },
    {
      type: "pwa-immutable-settlement-after-post",
      description: `duration_ms=${postSettlementDurationMs};cache_entries=${postCacheAfter.length}`
    }
  );

  const entries = await appCacheEntries(page);
  const syntheticSanitized = sanitizeSyntheticRequest({
    url: "http://127.0.0.1:3000/profile?access_token=SYNTHETIC_QUERY_SECRET",
    headers: {
      Cookie: "SYNTHETIC_COOKIE_MARKER",
      Authorization: "SYNTHETIC_AUTHORIZATION_MARKER",
      "Content-Type": "application/json"
    },
    body: "SYNTHETIC_PRIVATE_BODY",
    expectedBody: "SYNTHETIC_PRIVATE_BODY"
  });
  const syntheticSerialized = stringifySafeDiagnostic(syntheticSanitized);
  expect(syntheticSerialized).not.toContain("SYNTHETIC_QUERY_SECRET");
  expect(syntheticSerialized).not.toContain("access_token");
  expect(syntheticSerialized).not.toContain("SYNTHETIC_PRIVATE_BODY");
  expect(syntheticSerialized).not.toContain("SYNTHETIC_COOKIE_MARKER");
  expect(syntheticSerialized).not.toContain("SYNTHETIC_AUTHORIZATION_MARKER");
  for (const item of cases) {
    const observation = observations.get(item.name)!;
    const browserResult = browserResults.find((result) => result.name === item.name);
    const itemUrl = safeUrl(item.url);
    const diagnostics = stringifySafeDiagnostic({
      item: {
        name: item.name,
        method: item.method,
        ...itemUrl,
        expectedContentType: item.headers["Content-Type"] ?? null,
        expectedBodyByteLength: item.body ? Buffer.byteLength(item.body) : 0
      },
      browserResult,
      observation
    });
    expect(browserResult, diagnostics).toMatchObject({
      name: item.name,
      outcome: "fulfilled",
      status: 200,
      responseOrigin: itemUrl.origin,
      responsePathname: itemUrl.pathname,
      responseQueryKeys: itemUrl.queryKeys,
      responseUrlMatchesExpected: true
    });
    expect(observation.fixtureMatches, diagnostics).toBe(1);
    expect(observation.requests, diagnostics).toHaveLength(1);
    expect(observation.responses, diagnostics).toHaveLength(1);
    expect(observation.failures, diagnostics).toEqual([]);
    expect(observation.requests[0], diagnostics).toMatchObject({
      ...itemUrl,
      method: item.method,
      resourceType: "fetch",
      bodyPresent: item.body !== undefined,
      bodyByteLength: item.body ? Buffer.byteLength(item.body) : 0,
      bodyMatchesExpected: true,
      contentTypeMatchesExpected: true
    });
    expect(observation.responses[0], diagnostics).toMatchObject({
      ...itemUrl,
      status: 200,
      fromServiceWorker: false
    });
    if (item.name === "rsc-get") expect(observation.requests[0].hasRscHeader, diagnostics).toBe(true);
    if (item.name === "prefetch-get") {
      expect(observation.requests[0].hasNextRouterPrefetchHeader, diagnostics).toBe(true);
      expect(observation.requests[0].hasPurposePrefetch, diagnostics).toBe(true);
    }
    if (item.name === "non-get-post") {
      expect(observation.requests[0].contentType, diagnostics).toBe("application/json");
      expect(observation.requests[0].bodyMatchesExpected, diagnostics).toBe(true);
    }
    expect(
      entries.filter(({ method, origin, pathname, queryKeys }) =>
        method === item.method && origin === itemUrl.origin && pathname === itemUrl.pathname &&
        JSON.stringify(queryKeys) === JSON.stringify(itemUrl.queryKeys)
      ),
      diagnostics
    ).toEqual([]);
  }
  expect(postCacheAfter).toEqual(postCacheBefore);
  expect(
    postCacheAfter.filter(
      ({ cacheName, method, origin, pathname, queryKeys }) =>
        cacheName === CURRENT_CACHE &&
        method === "GET" &&
        origin === APP_ORIGIN &&
        pathname === "/offline" &&
        queryKeys.length === 0
    )
  ).toHaveLength(1);
  expect(postCacheAfter.some(({ method, origin, pathname }) => method === "POST" && origin === APP_ORIGIN && pathname === "/offline")).toBe(false);
  expect(entries.some(({ containsPrivateMarker }) => containsPrivateMarker)).toBe(false);
});

test("@plan017 reuses only immutable Next static assets while offline", async ({ page, context }) => {
  await waitForWorkerControl(page);
  await page.reload();

  const staticUrl = await page.evaluate(async () => {
    const cache = await caches.open("mynutri-shell-v3");
    const request = (await cache.keys()).find((candidate) => new URL(candidate.url).pathname.startsWith("/_next/static/"));
    return request?.url ?? "";
  });
  expect(staticUrl).toMatch(/\/_next\/static\//);

  await context.setOffline(true);
  const result = await page.evaluate(async (url) => {
    const response = await fetch(url);
    return { ok: response.ok, size: (await response.arrayBuffer()).byteLength };
  }, staticUrl);
  expect(result.ok).toBe(true);
  expect(result.size).toBeGreaterThan(0);
});

test("@plan017 deep navigations return the exact generic offline document", async ({ page, context }) => {
  await waitForWorkerControl(page);
  const offline = await page.evaluate(async () => {
    const response = await (await caches.open("mynutri-shell-v3")).match("/offline");
    if (!response) throw new Error("Offline document was not precached.");
    return {
      body: await response.clone().text(),
      contentType: response.headers.get("content-type"),
      url: response.url
    };
  });
  expect(new URL(offline.url).pathname).toBe("/offline");

  await page.goto("/diary");
  await page.goto("/profile");
  expect((await appCacheEntries(page)).some(({ pathname }) => ["/diary", "/profile"].includes(pathname))).toBe(false);

  await context.setOffline(true);
  for (const path of ["/diary", "/foods/plan017/edit", "/admin/users/plan017"]) {
    const response = await page.goto(path);
    expect(response).not.toBeNull();
    expect(await response!.text()).toBe(offline.body);
    expect(response!.headers()["content-type"]).toBe(offline.contentType);
    await expect(page).toHaveURL(new RegExp(`${path.replaceAll("/", "\\/")}$`));
    await expect(page.getByText("myNutri v1", { exact: false })).toBeVisible();
    await expect(page.locator("body")).not.toContainText(/admin\.e2e|V2 E2E baseline|access_token/i);
  }
});

test("@plan017 CacheStorage contains only generic and immutable static resources", async ({ page }) => {
  type ProfileRequestLifecycle = ProfileRequestObservation & {
    id: string;
    sequence: number;
    responseReceived: boolean;
    responseStatus: number | null;
    responseOrigin: string | null;
    responsePathname: string | null;
    responseQueryKeys: string[];
    fromServiceWorker: boolean | null;
    finished: boolean;
    failed: boolean;
    failureReason: string | null;
    stillOpenAtReadiness: boolean;
  };
  const profileRequests: ProfileRequestLifecycle[] = [];
  const lifecycleByRequest = new Map<Request, ProfileRequestLifecycle>();
  let sequence = 0;
  const onRequest = (request: Request) => {
    const observation = observeProfileRequest(request);
    if (!observation) return;
    const record: ProfileRequestLifecycle = {
      ...observation,
      id: `profile-${++sequence}`,
      sequence,
      responseReceived: false,
      responseStatus: null,
      responseOrigin: null,
      responsePathname: null,
      responseQueryKeys: [],
      fromServiceWorker: null,
      finished: false,
      failed: false,
      failureReason: null,
      stillOpenAtReadiness: false
    };
    profileRequests.push(record);
    lifecycleByRequest.set(request, record);
  };
  const onResponse = (response: Response) => {
    const record = lifecycleByRequest.get(response.request());
    if (!record) return;
    record.responseReceived = true;
    record.responseStatus = response.status();
    const responseUrl = safeUrl(response.url());
    record.responseOrigin = responseUrl.origin;
    record.responsePathname = responseUrl.pathname;
    record.responseQueryKeys = responseUrl.queryKeys;
    record.fromServiceWorker = response.fromServiceWorker();
  };
  const onRequestFinished = (request: Request) => {
    const record = lifecycleByRequest.get(request);
    if (record) record.finished = true;
  };
  const onRequestFailed = (request: Request) => {
    const record = lifecycleByRequest.get(request);
    if (!record) return;
    record.failed = true;
    record.failureReason = safeErrorCategory(request.failure()?.errorText) ?? "other";
  };
  page.on("request", onRequest);
  page.on("response", onResponse);
  page.on("requestfinished", onRequestFinished);
  page.on("requestfailed", onRequestFailed);

  let profileReadyEntries: AppCacheEntry[] = [];
  try {
    await waitForWorkerControl(page);
    await page.goto("/profile");
    await expect(page.getByRole("heading", { name: "بياناتك وأهدافك", exact: true })).toBeVisible();
    await expect(page.getByLabel("الوزن", { exact: true })).toBeVisible();
    await expect(page.getByLabel("جارٍ تحميل بياناتك", { exact: true })).toHaveCount(0);
    for (const record of profileRequests) {
      record.stillOpenAtReadiness = !record.finished && !record.failed;
    }
    profileReadyEntries = await appCacheEntries(page);
    for (const path of ["/diary", "/foods", "/admin/users/00000000-0000-0000-0000-000000000001"]) {
      await page.goto(path);
    }
  } finally {
    page.off("request", onRequest);
    page.off("response", onResponse);
    page.off("requestfinished", onRequestFinished);
    page.off("requestfailed", onRequestFailed);
  }

  const documentNavigations = profileRequests.filter(
    (request) => request.classification === "document-navigation"
  );
  const rscRequests = profileRequests.filter((request) => request.isRsc);
  const prefetchRequests = profileRequests.filter((request) => request.isPrefetch);
  const dynamicProfileObservations = profileRequests.filter((request) => request.isRsc || request.isPrefetch);
  const unclassifiedRequests = profileRequests.filter(
    (request) => request.classification === "unknown-dynamic"
  );
  const lifecycleTable = profileRequests.map((request) => ({
    index: request.sequence,
    id: request.id,
    method: request.method,
    origin: request.origin,
    pathname: request.pathname,
    queryKeys: request.queryKeys,
    resourceType: request.resourceType,
    isNavigation: request.isNavigation,
    classification: request.classification,
    hasRscHeader: request.hasRscHeader,
    hasNextRouterPrefetchHeader: request.hasNextRouterPrefetchHeader,
    hasNextRouterStateTreeHeader: request.hasNextRouterStateTreeHeader,
    hasNextRouterSegmentPrefetchHeader: request.hasNextRouterSegmentPrefetchHeader,
    hasPurposePrefetch: request.hasPurposePrefetch,
    hasSecPurposePrefetch: request.hasSecPurposePrefetch,
    acceptsRsc: request.acceptsRsc,
    responseReceived: request.responseReceived,
    responseStatus: request.responseStatus,
    responseOrigin: request.responseOrigin,
    responsePathname: request.responsePathname,
    responseQueryKeys: request.responseQueryKeys,
    fromServiceWorker: request.fromServiceWorker,
    finished: request.finished,
    failed: request.failed,
    failureReason: request.failureReason,
    stillOpenAtReadiness: request.stillOpenAtReadiness,
    lifecycleOutcome: request.failed
      ? "failed"
      : request.responseReceived && request.finished
        ? "response-finished"
        : request.responseReceived
          ? "response-streaming"
          : "in-flight",
    cacheEntryCount: profileReadyEntries.filter(({ method, origin, pathname, queryKeys }) =>
      method === request.method && origin === request.origin && pathname === request.pathname &&
      JSON.stringify(queryKeys) === JSON.stringify(request.queryKeys)
    ).length
  }));
  const lifecycleDiagnostics = stringifySafeDiagnostic(lifecycleTable);

  expect(documentNavigations, lifecycleDiagnostics).toHaveLength(1);
  expect(documentNavigations[0]).toMatchObject({
    method: "GET",
    resourceType: "document",
    isNavigation: true,
    queryKeys: [],
    isRsc: false,
    isPrefetch: false
  });
  expect(dynamicProfileObservations.length, lifecycleDiagnostics).toBeGreaterThan(0);
  expect(rscRequests.length, lifecycleDiagnostics).toBeGreaterThan(0);
  expect(prefetchRequests.every((request) => request.resourceType !== "document")).toBe(true);
  expect(unclassifiedRequests, lifecycleDiagnostics).toEqual([]);
  for (const request of dynamicProfileObservations) {
    expect(request.fromServiceWorker, lifecycleDiagnostics).not.toBe(true);
    expect(
      profileReadyEntries.filter(({ method, origin, pathname, queryKeys }) =>
        method === request.method && origin === request.origin && pathname === request.pathname &&
        JSON.stringify(queryKeys) === JSON.stringify(request.queryKeys)
      ),
      lifecycleDiagnostics
    ).toEqual([]);
  }
  expect(profileReadyEntries.length).toBeGreaterThanOrEqual(3);
  expect(new Set(profileReadyEntries.map(({ cacheName }) => cacheName))).toEqual(new Set([CURRENT_CACHE]));
  expect(profileReadyEntries.some(({ pathname }) => pathname === "/profile")).toBe(false);
  for (const entry of profileReadyEntries) {
    expect(
      GENERIC_PATHS.has(entry.pathname) || entry.pathname.startsWith("/_next/static/"),
      `Unexpected cached request at Profile readiness: ${entry.method} ${entry.origin}${entry.pathname} query keys=${entry.queryKeys.join(",")}`
    ).toBe(true);
    expect(entry.queryKeys).toEqual([]);
    expect(`${entry.origin}${entry.pathname}`).not.toMatch(/\/api\/|\/auth\//i);
    expect(entry.containsPrivateMarker).toBe(false);
  }

  const entries = await appCacheEntries(page);
  expect(entries.length).toBeGreaterThanOrEqual(3);
  expect(new Set(entries.map(({ cacheName }) => cacheName))).toEqual(new Set([CURRENT_CACHE]));
  expect(entries.some(({ pathname }) => pathname === "/profile")).toBe(false);
  for (const entry of entries) {
    expect(
      GENERIC_PATHS.has(entry.pathname) || entry.pathname.startsWith("/_next/static/"),
      `Unexpected cached request: ${entry.method} ${entry.origin}${entry.pathname} query keys=${entry.queryKeys.join(",")}`
    ).toBe(true);
    expect(entry.queryKeys).toEqual([]);
    expect(`${entry.origin}${entry.pathname}`).not.toMatch(/\/api\/|\/auth\//i);
    expect(entry.containsPrivateMarker).toBe(false);
  }
  expect(await page.evaluate(() => indexedDB.databases().then((databases) => databases.length))).toBe(0);
});
