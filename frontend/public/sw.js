// AI Health Archive — Service Worker v1.0
const CACHE_NAME = "healthsafe-v1";
const STATIC_ASSETS = [
  "/",
  "/dashboard",
  "/archive",
  "/trends",
  "/chat",
  "/manifest.json",
];

// ─── Install ────────────────────────────────────────────────────────────────
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// ─── Activate ───────────────────────────────────────────────────────────────
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ─── Fetch: Cache-first для статики, Network-first для API ─────────────────
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // API запросы — всегда сеть
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(event.request).catch(() =>
        new Response(JSON.stringify({ error: "Нет соединения" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        })
      )
    );
    return;
  }

  // Статика — cache first
  event.respondWith(
    caches.match(event.request).then(
      (cached) => cached || fetch(event.request).then((resp) => {
        const clone = resp.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        return resp;
      })
    )
  );
});

// ─── Push Notifications ─────────────────────────────────────────────────────
self.addEventListener("push", (event) => {
  const data = event.data?.json() ?? {};
  const title = data.title || "AI Health Archive";
  const options = {
    body: data.body || "Новое уведомление",
    icon: "/icons/icon-192.png",
    badge: "/icons/badge-72.png",
    data: data.url || "/dashboard",
    actions: [{ action: "open", title: "Открыть" }],
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data || "/dashboard";
  event.waitUntil(clients.openWindow(url));
});
