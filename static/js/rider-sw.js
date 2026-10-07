const CACHE_NAME = 'jaunpur-rider-static-v1';
const STATIC_ASSETS = [new URL('../css/style.css', self.location.href).pathname, new URL('rider-offline.js', self.location.href).pathname];

self.addEventListener('install', event => {
    event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)));
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('jaunpur-rider-') && key !== CACHE_NAME).map(key => caches.delete(key)))));
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    const requestUrl = new URL(event.request.url);
    if (event.request.method !== 'GET' || !requestUrl.pathname.startsWith('/static/')) return;
    event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
});
