// Service worker: makes the site installable as a PWA and keeps it working
// offline. Strategy:
//   - HTML / CSS / JS  -> network-first (always fresh when online; cache is
//     the offline fallback). This prevents stale pages, e.g. a cached nav
//     without the Compare link or with old colors.
//   - fonts / icons / manifest -> cache-first (they rarely change).
//   - API (cross-origin) -> network-first with cached fallback.

const CACHE_NAME = 'weather-watch-v18';

const APP_SHELL = [
    './',
    './index.html',
    './cities.html',
    './city.html',
    './compare.html',
    './info.html',
    './payment.html',
    './styles.css',
    './config.js',
    './i18n.js',
    './api.js',
    './chart.js',
    './map.js',
    './world-map.js',
    './compare.js',
    './home.js',
    './cities.js',
    './city.js',
    './info.js',
    './payment.js',
    './fonts/Vazirmatn-Regular.woff2',
    './fonts/Vazirmatn-Medium.woff2',
    './fonts/Vazirmatn-Bold.woff2',
    './manifest.webmanifest',
    './icons/icon-192.png',
    './icons/icon-512.png'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(APP_SHELL))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(keys => Promise.all(
                keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
            ))
            .then(() => self.clients.claim())
    );
});

function cacheFirst(request) {
    return caches.match(request).then(cached => {
        if (cached) return cached;
        return fetch(request).then(response => {
            if (response && response.ok) {
                const copy = response.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
            }
            return response;
        });
    });
}

function networkFirst(request) {
    return fetch(request)
        .then(response => {
            if (response && response.ok) {
                const copy = response.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
            }
            return response;
        })
        .catch(() => caches.match(request).then(cached => {
            if (cached) return cached;
            if (request.mode === 'navigate') return caches.match('./index.html');
            return Response.error();
        }));
}

// Hosts the service worker must not touch: analytics and the payment
// gateway must always go straight to the network, never be cached or
// served from cache.
const BYPASS_HOSTS = ['clarity.ms', 'zibal.ir'];

self.addEventListener('fetch', event => {
    const request = event.request;
    if (request.method !== 'GET') return;

    const url = new URL(request.url);
    if (BYPASS_HOSTS.some(h => url.hostname === h || url.hostname.endsWith('.' + h))) {
        return;  // let the browser handle it directly
    }

    const isSameOrigin = url.origin === self.location.origin;

    if (isSameOrigin && /\.(woff2|png|jpg|svg|webmanifest|ico)$/.test(url.pathname)) {
        event.respondWith(cacheFirst(request));
    } else {
        // Same-origin HTML/CSS/JS and cross-origin API: always try network
        // first so the user gets the latest, with cache as the fallback.
        event.respondWith(networkFirst(request));
    }
});
