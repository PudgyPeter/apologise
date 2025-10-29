// Service Worker for PWA functionality
const CACHE_VERSION = 'v2.0.2';
const CACHE_NAME = `discord-logs-${CACHE_VERSION}`;
const urlsToCache = [
  '/',
  '/static/css/main.css',
  '/static/js/main.js',
  '/manifest.json'
];

// Install event - cache resources and skip waiting
self.addEventListener('install', (event) => {
  console.log('[SW] Installing new version:', CACHE_VERSION);
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
      .then(() => self.skipWaiting())
  );
});

// Fetch event - network first, then cache (but never cache API calls)
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Never cache API calls - always fetch fresh data
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }
  
  // For static assets, use network first strategy
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Clone and cache the response
        if (response && response.status === 200) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return response;
      })
      .catch(() => {
        // Fallback to cache if network fails
        return caches.match(event.request);
      })
  );
});

// Activate event - aggressively clean up ALL old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating new version:', CACHE_VERSION);
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      // Take control of all pages immediately
      return self.clients.claim();
    }).then(() => {
      // Reload all clients to get fresh content
      return self.clients.matchAll().then((clients) => {
        clients.forEach((client) => {
          client.postMessage({ type: 'CACHE_UPDATED', version: CACHE_VERSION });
        });
      });
    })
  );
});

// Background sync for offline data submission (if supported)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-hospitality-stats') {
    event.waitUntil(syncHospitalityStats());
  }
});

async function syncHospitalityStats() {
  // This would sync any offline-submitted stats when connection is restored
  console.log('Syncing hospitality stats...');
}
