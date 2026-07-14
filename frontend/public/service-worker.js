const CACHE_NAME = "mynutri-shell-v2";
const SHELL_URLS = ["/", "/diary", "/foods", "/profile", "/offline", "/manifest.json", "/icon.svg"];
const SHELL_PATHS = new Set(SHELL_URLS);

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_URLS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  if (url.origin !== self.location.origin || !SHELL_PATHS.has(url.pathname)) {
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(async () => {
        const cached = await caches.match(url.pathname);
        if (cached) return cached;
        if (request.mode === "navigate") return caches.match("/offline");
        throw new Error("Offline and no cached response available.");
      })
  );
});
