const CACHE = 'rupeewa-v1';
const DYNAMIC_CACHE = 'rupeewa-dynamic-v1';

const PRECACHE_URLS = [
  '/',
  '/style.css',
  '/manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE && k !== DYNAMIC_CACHE).map(k => caches.delete(k))
    ))
  );
  self.clients.claim();
});

// Network first, fallback to cache
self.addEventListener('fetch', event => {
  const { request } = event;
  if (request.method !== 'GET') return;

  // API requests — network only
  if (request.url.includes('/api/')) {
    return;
  }

  event.respondWith(
    fetch(request)
      .then(response => {
        const clone = response.clone();
        caches.open(DYNAMIC_CACHE).then(cache => cache.put(request, clone));
        return response;
      })
      .catch(() => caches.match(request))
  );
});

// Push notifications
self.addEventListener('push', event => {
  if (!event.data) return;
  try {
    const data = event.data.json();
    self.registration.showNotification(data.title || 'Rupeewa News', {
      body: data.body || 'New article available',
      icon: '/icons/icon-192.svg',
      badge: '/icons/icon-192.svg',
      data: { url: data.url || '/' },
      vibrate: [200, 100, 200]
    });
  } catch {
    self.registration.showNotification('Rupeewa News', {
      body: event.data.text(),
      icon: '/icons/icon-192.svg'
    });
  }
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(clientsArr => {
      const had = clientsArr.some(client => {
        if (client.url === url && 'focus' in client) return client.focus();
        return false;
      });
      if (!had && clients.openWindow) clients.openWindow(url);
    })
  );
});
