/* Service worker de Prisma. Alcance: la subruta donde se publica (p. ej. /PrismaNews/).
 * - Páginas y datos: red primero (3 s) y, si falla, la última copia guardada -> la última portada funciona sin conexión.
 * - Recursos con hash (/_astro/, iconos, tipografías): caché primero.
 * - Imágenes de los medios (otro origen): no se guardan.
 * Sube VERSION para invalidar las cachés. */
const VERSION = "v2";
const CORE = `prisma-core-${VERSION}`;
const RUNTIME = `prisma-rt-${VERSION}`;
const SCOPE = self.registration.scope; // termina en "/"
const MAX_PAGES = 60;
const MATCH = { ignoreVary: true, ignoreSearch: false };

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CORE).then((c) =>
      Promise.allSettled([SCOPE, SCOPE + 'canarias/', SCOPE + 'sin-conexion/'].map((u) => c.add(u))),
    ).then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('prisma-') && k !== CORE && k !== RUNTIME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

async function trim(cache) {
  const keys = await cache.keys();
  const pages = keys.filter((r) => r.mode === 'navigate' || /\/$/.test(new URL(r.url).pathname));
  for (const k of pages.slice(0, Math.max(0, pages.length - MAX_PAGES))) await cache.delete(k);
}

function withTimeout(promise, ms) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error('timeout')), ms);
    promise.then((v) => { clearTimeout(t); resolve(v); }, (e) => { clearTimeout(t); reject(e); });
  });
}

async function networkFirst(request) {
  const cache = await caches.open(RUNTIME);
  try {
    const res = await withTimeout(fetch(request), 3000);
    if (res.ok) { cache.put(request, res.clone()); trim(cache); }
    return res;
  } catch {
    return (await caches.match(request, MATCH)) || (request.mode === 'navigate' ? await offlineFallback() : Response.error());
  }
}

async function offlineFallback() {
  return (await caches.match(SCOPE, MATCH)) || (await caches.match(SCOPE + 'sin-conexion/', MATCH)) || Response.error();
}

async function cacheFirst(request) {
  const hit = await caches.match(request, MATCH);
  if (hit) return hit;
  const res = await fetch(request);
  if (res.ok) (await caches.open(RUNTIME)).put(request, res.clone());
  return res;
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || !url.href.startsWith(SCOPE)) return;
  if (req.mode === 'navigate' || url.pathname.includes('/data/')) {
    event.respondWith(networkFirst(req));
  } else if (/\/(_astro|icons)\//.test(url.pathname) || /\.(woff2?|png|svg|webmanifest)$/.test(url.pathname)) {
    event.respondWith(cacheFirst(req));
  }
});

// Tras la primera visita la página envía sus recursos para dejarlos disponibles sin conexión.
self.addEventListener('message', (event) => {
  if (!event.data || event.data.type !== 'cache-urls') return;
  const urls = (event.data.urls || []).filter((u) => typeof u === 'string' && u.startsWith(SCOPE)).slice(0, 120);
  event.waitUntil(caches.open(RUNTIME).then((c) => Promise.allSettled(urls.map((u) => c.add(u)))));
});
