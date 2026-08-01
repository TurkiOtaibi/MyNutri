import { expect, test, type Page, type Request, type Route } from "@playwright/test";

const APP_CACHE_PREFIX = "mynutri-shell-";
const CURRENT_CACHE = "mynutri-shell-v3";
const GENERIC_PATHS = new Set(["/offline", "/manifest.json", "/icon.svg"]);

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

async function appCacheEntries(page: Page): Promise<Array<{ url: string; body: string }>> {
  return page.evaluate(async ({ prefix }) => {
    const entries: Array<{ url: string; body: string }> = [];
    for (const key of await caches.keys()) {
      if (!key.startsWith(prefix)) continue;
      const cache = await caches.open(key);
      for (const request of await cache.keys()) {
        const response = await cache.match(request);
        entries.push({ url: request.url, body: response ? await response.clone().text() : "" });
      }
    }
    return entries;
  }, { prefix: APP_CACHE_PREFIX });
}

function isExactRequest(request: Request, pathname: string, method = "GET"): boolean {
  const url = new URL(request.url());
  return request.method() === method && url.origin === "http://127.0.0.1:3000" && url.pathname === pathname;
}

type ProfileRequestObservation = {
  url: string;
  method: string;
  resourceType: string;
  isNavigation: boolean;
  query: string;
  isRsc: boolean;
  isPrefetch: boolean;
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

  return {
    url: request.url(),
    method: request.method(),
    resourceType: request.resourceType(),
    isNavigation: request.isNavigationRequest(),
    query: url.search,
    isRsc,
    isPrefetch
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
  const observed: string[] = [];
  const fulfill = async (route: Route) => {
    observed.push(`${route.request().method()} ${route.request().url()}`);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: { "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify({ marker: "plan017-personal-marker" })
    });
  };
  await page.route("**/api/plan017**", fulfill);
  await page.route("**/auth/v1/plan017**", fulfill);
  await page.route("**/diary?_rsc=plan017", fulfill);
  await page.route("**/foods?prefetch=plan017", fulfill);
  await page.route("**/_next/data/plan017/page.json", fulfill);
  await page.route("https://cross-origin.example/plan017", fulfill);
  await page.route("**/offline", async (route) => {
    if (route.request().method() === "POST") await fulfill(route);
    else await route.continue();
  });

  await page.evaluate(async () => {
    await fetch("/api/plan017?account=private");
    await fetch("/auth/v1/plan017?token=private");
    await fetch("/diary?_rsc=plan017", { headers: { RSC: "1" } });
    await fetch("/foods?prefetch=plan017", {
      headers: { "Next-Router-Prefetch": "1", Purpose: "prefetch" }
    });
    await fetch("/_next/data/plan017/page.json");
    await fetch("https://cross-origin.example/plan017");
    await fetch("/offline", { method: "POST", body: "private" });
  });

  expect(observed).toHaveLength(7);
  const entries = await appCacheEntries(page);
  expect(entries.some(({ url }) => /\/api\/|\/auth\/|_rsc|\/_next\/data\//.test(url))).toBe(false);
  expect(entries.some(({ body }) => body.includes("plan017-personal-marker"))).toBe(false);
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
  const profileRequests: ProfileRequestObservation[] = [];
  const dynamicProfileRequests: Request[] = [];
  const onRequest = (request: Request) => {
    const observation = observeProfileRequest(request);
    if (!observation) return;
    profileRequests.push(observation);
    if (observation.isRsc || observation.isPrefetch) dynamicProfileRequests.push(request);
  };
  page.on("request", onRequest);

  try {
    await waitForWorkerControl(page);
    for (const path of ["/profile", "/diary", "/foods", "/admin/users/00000000-0000-0000-0000-000000000001"]) {
      await page.goto(path);
    }
  } finally {
    page.off("request", onRequest);
  }

  const dynamicProfileOutcomes = await Promise.all(
    dynamicProfileRequests.map(async (request) => {
      const response = await request.response();
      if (!response) return "failed" as const;
      return response.fromServiceWorker() ? "service-worker" as const : "network" as const;
    })
  );

  const documentNavigations = profileRequests.filter(
    (request) => request.resourceType === "document" && request.isNavigation && !request.isRsc && !request.isPrefetch
  );
  const rscRequests = profileRequests.filter((request) => request.isRsc);
  const prefetchRequests = profileRequests.filter((request) => request.isPrefetch);
  const dynamicProfileObservations = profileRequests.filter((request) => request.isRsc || request.isPrefetch);
  const unclassifiedRequests = profileRequests.filter(
    (request) =>
      !(request.resourceType === "document" && request.isNavigation && !request.isRsc && !request.isPrefetch) &&
      !request.isRsc &&
      !request.isPrefetch
  );

  expect(documentNavigations, JSON.stringify(profileRequests, null, 2)).toHaveLength(1);
  expect(documentNavigations[0]).toMatchObject({
    method: "GET",
    resourceType: "document",
    isNavigation: true,
    query: "",
    isRsc: false,
    isPrefetch: false
  });
  expect(rscRequests.length).toBeGreaterThan(0);
  expect(prefetchRequests.every((request) => request.resourceType !== "document")).toBe(true);
  expect(unclassifiedRequests, JSON.stringify(profileRequests, null, 2)).toEqual([]);
  expect(dynamicProfileOutcomes).toHaveLength(dynamicProfileObservations.length);
  expect(dynamicProfileOutcomes).not.toContain("service-worker");

  const entries = await appCacheEntries(page);
  expect(entries.length).toBeGreaterThanOrEqual(3);
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
