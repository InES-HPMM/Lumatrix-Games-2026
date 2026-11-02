// Service Worker: hält die Seite im Browser vorrätig, damit die installierte App auch ohne
// laufenden lokalen Server startet. Läuft der Server, holt er im Hintergrund die neueste Fassung.
// Anfragen an Open-Meteo gehen unverändert ins Netz.

const CACHE = "lumatrix-wetter-v1";
const DATEIEN = [
    "./",
    "index.html",
    "stil.css",
    "app.js",
    "lib/openmeteo.js",
    "lib/nachricht.js",
    "lib/zeitplan.js",
    "manifest.webmanifest",
    "icons/icon-192.png",
    "icons/icon-512.png",
];

self.addEventListener("install", (e) => {
    e.waitUntil(caches.open(CACHE).then((c) => c.addAll(DATEIEN)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
    e.waitUntil(
        caches
            .keys()
            .then((namen) => Promise.all(namen.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
            .then(() => self.clients.claim()),
    );
});

self.addEventListener("fetch", (e) => {
    const url = new URL(e.request.url);
    if (url.origin !== self.location.origin || e.request.method !== "GET") return;
    e.respondWith(
        caches.open(CACHE).then(async (cache) => {
            const vorrat = await cache.match(e.request, { ignoreSearch: true });
            const neu = fetch(e.request)
                .then((antwort) => {
                    if (antwort.ok) cache.put(e.request, antwort.clone());
                    return antwort;
                })
                .catch(() => vorrat);
            return vorrat ?? neu;
        }),
    );
});
