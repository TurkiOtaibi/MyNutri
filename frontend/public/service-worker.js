const CACHE_PREFIX = "mynutri-shell-";
const CACHE_NAME = `${CACHE_PREFIX}v3`;
const OFFLINE_URL = "/offline";
const PRECACHE_URLS = [OFFLINE_URL, "/manifest.json", "/icon.svg"];
const PRECACHE_PATHS = new Set(PRECACHE_URLS);

function isNextDataOrPrefetch(request, url) {
  return (
    url.pathname.startsWith("/_next/data/") ||
    url.searchParams.has("_rsc") ||
    request.headers.get("RSC") === "1" ||
    request.headers.get("Next-Router-Prefetch") === "1" ||
    request.headers.has("Next-Router-State-Tree") ||
    request.headers.has("Next-Router-Segment-Prefetch") ||
    request.headers.get("Purpose")?.toLowerCase() === "prefetch" ||
    request.headers.get("Sec-Purpose")?.toLowerCase() === "prefetch"
  );
}

function isBypassedRequest(request, url) {
  return (
    request.method !== "GET" ||
    url.origin !== self.location.origin ||
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/auth/") ||
    isNextDataOrPrefetch(request, url)
  );
}

async function networkFirstNavigation(request) {
  try {
    return await fetch(request);
  } catch {
    const cache = await caches.open(CACHE_NAME);
    const fallback = await cache.match(OFFLINE_URL);
    if (fallback) return fallback;
    throw new Error("Offline shell is unavailable.");
  }
}

async function cacheFirstStatic(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  const responseUrl = new URL(response.url);
  if (
    response.ok &&
    !response.redirected &&
    responseUrl.origin === self.location.origin &&
    responseUrl.pathname === new URL(request.url).pathname
  ) {
    await cache.put(request, response.clone());
  }
  return response;
}

async function precacheShell() {
  const cache = await caches.open(CACHE_NAME);
  for (const path of PRECACHE_URLS) {
    const response = await fetch(new Request(path, { cache: "reload" }));
    const responseUrl = new URL(response.url);
    if (!response.ok || response.redirected || responseUrl.origin !== self.location.origin || responseUrl.pathname !== path) {
      throw new Error(`Static shell asset was not served directly: ${path}`);
    }
    await cache.put(path, response);
  }
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      await precacheShell();
      await self.skipWaiting();
    })()
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      );
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (isBypassedRequest(request, url)) return;

  if (request.mode === "navigate") {
    event.respondWith(networkFirstNavigation(request));
    return;
  }

  const isPrecachedAsset = PRECACHE_PATHS.has(url.pathname) && url.search === "";
  const isImmutableNextAsset = url.pathname.startsWith("/_next/static/") && url.search === "";
  if (isPrecachedAsset || isImmutableNextAsset) {
    event.respondWith(cacheFirstStatic(request));
  }
});
