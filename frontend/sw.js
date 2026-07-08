// Service worker: makes the site installable as a PWA and keeps the app
// shell available offline. Static files are served cache-first; API calls
// go network-first with a cached fallback so the last seen data still
// shows when the user is offline.

const CACHE_NAME = 'weather-watch-v2';

const APP_SHELL = [
    './',
    './index.html',
    './cities.html',
    './city.html',
    './info.html',
    './styles.css',
    './config.js',
    './i18n.js',
    './api.js',
    './home.js',
    './cities.js',
    './city.js',
    './info.js',
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

self.addEventListener('fetch', event => {
    const request = event.request;
    if (request.method !== 'GET') {
        return;
    }

    const isSameOrigin = new URL(request.url).origin === self.location.origin;

    if (isSameOrigin) {
        // App shell: cache-first, fill the cache on miss.
        event.respondWith(
            caches.match(request).then(cached => {
                if (cached) {
                    return cached;
                }
                return fetch(request).then(response => {
                    if (response.ok) {
                        const copy = response.clone();
                        caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
                    }
                    return response;
                });
            })
        );
    } else {
        // API calls: network-first, fall back to the last cached answer.
        event.respondWith(
            fetch(request)
                .then(response => {
                    if (response.ok) {
                        const copy = response.clone();
                        caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
                    }
                    return response;
                })
                .catch(() => caches.match(request))
        );
    }
});
