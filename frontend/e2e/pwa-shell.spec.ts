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
  url: string;
  origin: string;
  pathname: string;
  query: string;
  body: string;
};

async function appCacheEntries(page: Page): Promise<AppCacheEntry[]> {
  return page.evaluate(async ({ prefix }) => {
    const entries: AppCacheEntry[] = [];
    for (const key of await caches.keys()) {
      if (!key.startsWith(prefix)) continue;
      const cache = await caches.open(key);
      for (const request of await cache.keys()) {
        const response = await cache.match(request);
        const url = new URL(request.url);
        entries.push({
          cacheName: key,
          method: request.method,
          url: request.url,
          origin: url.origin,
          pathname: url.pathname,
          query: url.search,
          body: response ? await response.clone().text() : ""
        });
      }
    }
    return entries.sort((left, right) =>
      `${left.cacheName}\u0000${left.method}\u0000${left.url}`.localeCompare(
        `${right.cacheName}\u0000${right.method}\u0000${right.url}`
      )
    );
  }, { prefix: APP_CACHE_PREFIX });
}

function isExactRequest(request: Request, pathname: string, method = "GET"): boolean {
  const url = new URL(request.url());
  return request.method() === method && url.origin === APP_ORIGIN && url.pathname === pathname;
}

type ProfileRequestObservation = {
  origin: string;
  pathname: string;
  url: string;
  method: string;
  resourceType: string;
  isNavigation: boolean;
  query: string;
  isRsc: boolean;
  isPrefetch: boolean;
  classification: "document-navigation" | "rsc" | "router-prefetch" | "next-route-data" | "unknown-dynamic";
  headers: {
    rsc: string | null;
    nextRouterPrefetch: string | null;
    nextRouterStateTree: string | null;
    nextRouterSegmentPrefetch: string | null;
    purpose: string | null;
    secPurpose: string | null;
  };
};

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
    url: request.url(),
    method: request.method(),
    resourceType: request.resourceType(),
    isNavigation,
    query: url.search,
    isRsc,
    isPrefetch,
    classification,
    headers: {
      rsc: headers.rsc ?? null,
      nextRouterPrefetch: headers["next-router-prefetch"] ?? null,
      nextRouterStateTree: headers["next-router-state-tree"] ?? null,
      nextRouterSegmentPrefetch: headers["next-router-segment-prefetch"] ?? null,
      purpose: headers.purpose ?? null,
      secPurpose: headers["sec-purpose"] ?? null
    }
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

test("@plan017 bypasses API Auth RSC prefetch cross-origin and non-GET traffic", async ({ page }) => {
  await waitForWorkerControl(page);
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
      url: string;
      method: string;
      resourceType: string;
      headers: Record<string, string>;
      postData: string | null;
    }>;
    responses: Array<{ url: string; status: number; fromServiceWorker: boolean }>;
    failures: Array<string | null>;
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
    observations.get(item.name)!.requests.push({
      url: request.url(),
      method: request.method(),
      resourceType: request.resourceType(),
      headers: request.headers(),
      postData: request.postData()
    });
  };
  const onResponse = (response: Awaited<ReturnType<Request["response"]>>) => {
    if (!response) return;
    const item = findCase(response.request());
    if (!item) return;
    observations.get(item.name)!.responses.push({
      url: response.url(),
      status: response.status(),
      fromServiceWorker: response.fromServiceWorker()
    });
  };
  const onRequestFailed = (request: Request) => {
    const item = findCase(request);
    if (!item) return;
    observations.get(item.name)!.failures.push(request.failure()?.errorText ?? null);
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
  page.on("request", onRequest);
  page.on("response", onResponse);
  page.on("requestfailed", onRequestFailed);
  await page.route("**/*", fulfillBypassCase);

  const browserResults: Array<{
    name: string;
    outcome: "fulfilled" | "rejected";
    status?: number;
    responseUrl?: string;
    errorName?: string;
    errorMessage?: string;
  }> = [];
  let postCacheBefore: AppCacheEntry[] = [];
  let postCacheAfter: AppCacheEntry[] = [];
  try {
    for (const item of cases) {
      if (item.name === "non-get-post") postCacheBefore = await appCacheEntries(page);
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
            responseUrl: response.url
          };
        } catch (error) {
          return {
            name: requestCase.name,
            outcome: "rejected" as const,
            errorName: error instanceof Error ? error.name : "UnknownError",
            errorMessage: error instanceof Error ? error.message : String(error)
          };
        }
      }, item);
      browserResults.push(result);
      if (item.name === "non-get-post") postCacheAfter = await appCacheEntries(page);
    }
  } finally {
    await page.unroute("**/*", fulfillBypassCase);
    page.off("request", onRequest);
    page.off("response", onResponse);
    page.off("requestfailed", onRequestFailed);
  }

  const entries = await appCacheEntries(page);
  for (const item of cases) {
    const observation = observations.get(item.name)!;
    const browserResult = browserResults.find((result) => result.name === item.name);
    const diagnostics = JSON.stringify({ item, browserResult, observation }, null, 2);
    expect(browserResult, diagnostics).toMatchObject({
      name: item.name,
      outcome: "fulfilled",
      status: 200,
      responseUrl: item.url
    });
    expect(observation.fixtureMatches, diagnostics).toBe(1);
    expect(observation.requests, diagnostics).toHaveLength(1);
    expect(observation.responses, diagnostics).toHaveLength(1);
    expect(observation.failures, diagnostics).toEqual([]);
    expect(observation.requests[0], diagnostics).toMatchObject({
      url: item.url,
      method: item.method,
      resourceType: "fetch"
    });
    expect(observation.responses[0], diagnostics).toMatchObject({
      url: item.url,
      status: 200,
      fromServiceWorker: false
    });
    for (const [name, value] of Object.entries(item.headers)) {
      expect(observation.requests[0].headers[name.toLowerCase()], diagnostics).toBe(value);
    }
    expect(observation.requests[0].postData, diagnostics).toBe(item.body ?? null);
    expect(entries.filter(({ method, url }) => method === item.method && url === item.url), diagnostics).toEqual([]);
  }
  expect(postCacheAfter).toEqual(postCacheBefore);
  expect(
    postCacheAfter.filter(
      ({ cacheName, method, origin, pathname, query }) =>
        cacheName === CURRENT_CACHE &&
        method === "GET" &&
        origin === APP_ORIGIN &&
        pathname === "/offline" &&
        query === ""
    )
  ).toHaveLength(1);
  expect(postCacheAfter.some(({ method, url }) => method === "POST" && url === `${APP_ORIGIN}/offline`)).toBe(false);
  expect(entries.some(({ body }) => body.includes("plan017-personal-marker"))).toBe(false);
  expect(entries.some(({ body }) => body.includes("plan017-private-post"))).toBe(false);
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
  expect((await appCacheEntries(page)).some(({ url }) => ["/diary", "/profile"].includes(new URL(url).pathname))).toBe(false);

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
    responseUrl: string | null;
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
      responseUrl: null,
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
    record.responseUrl = response.url();
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
    record.failureReason = request.failure()?.errorText ?? "unknown request failure";
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
    url: request.url,
    origin: request.origin,
    pathname: request.pathname,
    query: request.query,
    resourceType: request.resourceType,
    isNavigation: request.isNavigation,
    classification: request.classification,
    headers: request.headers,
    responseReceived: request.responseReceived,
    responseStatus: request.responseStatus,
    responseUrl: request.responseUrl,
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
    cacheEntryCount: profileReadyEntries.filter(({ method, url }) => method === request.method && url === request.url).length
  }));
  const lifecycleDiagnostics = JSON.stringify(lifecycleTable, null, 2);

  expect(documentNavigations, lifecycleDiagnostics).toHaveLength(1);
  expect(documentNavigations[0]).toMatchObject({
    method: "GET",
    resourceType: "document",
    isNavigation: true,
    query: "",
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
      profileReadyEntries.filter(({ method, url }) => method === request.method && url === request.url),
      lifecycleDiagnostics
    ).toEqual([]);
  }
  expect(profileReadyEntries.length).toBeGreaterThanOrEqual(3);
  expect(new Set(profileReadyEntries.map(({ cacheName }) => cacheName))).toEqual(new Set([CURRENT_CACHE]));
  expect(profileReadyEntries.some(({ pathname }) => pathname === "/profile")).toBe(false);
  for (const entry of profileReadyEntries) {
    expect(
      GENERIC_PATHS.has(entry.pathname) || entry.pathname.startsWith("/_next/static/"),
      `Unexpected cached request at Profile readiness: ${entry.method} ${entry.url}`
    ).toBe(true);
    expect(entry.query).toBe("");
    expect(entry.url).not.toMatch(/\/api\/|\/auth\/|_rsc|prefetch|token/i);
    expect(entry.body).not.toMatch(/admin\.e2e|V2 E2E baseline/i);
  }

  const entries = await appCacheEntries(page);
  expect(entries.length).toBeGreaterThanOrEqual(3);
  expect(new Set(entries.map(({ cacheName }) => cacheName))).toEqual(new Set([CURRENT_CACHE]));
  expect(entries.some(({ url }) => new URL(url).pathname === "/profile")).toBe(false);
  for (const entry of entries) {
    const url = new URL(entry.url);
    expect(
      GENERIC_PATHS.has(url.pathname) || url.pathname.startsWith("/_next/static/"),
      `Unexpected cached request: ${entry.url}`
    ).toBe(true);
    expect(url.search).toBe("");
    expect(entry.url).not.toMatch(/\/api\/|\/auth\/|_rsc|prefetch|token/i);
    expect(entry.body).not.toMatch(/admin\.e2e|V2 E2E baseline/i);
  }
  expect(await page.evaluate(() => indexedDB.databases().then((databases) => databases.length))).toBe(0);
});
