/**
 * Service Worker for Web Push Notifications
 * Rupeewa News Daily
 */
const CACHE_NAME = 'rupeewa-v1';
const VAPID_PUBLIC_KEY = 'BP3qGc-cn0TfGRDAkVrgfYAKqEEIvygeWxR77B1trmNN4Vy5oOj_pLDQLUpVY1Vi0-Bg9GhKFf-STnagdc1R3QM';

// Convert base64 string to Uint8Array for push subscription
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  return new Uint8Array([...rawData].map(char => char.charCodeAt(0)));
}

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(clients.claim());
});

// Handle push notification
self.addEventListener('push', event => {
  if (!event.data) return;
  
  const data = event.data.json();
  const options = {
    body: data.body || 'New update from Rupeewa News Daily',
    icon: data.icon || '/logo.jpg',
    badge: data.badge || '/logo.jpg',
    image: data.image,
    vibrate: [100, 50, 100],
    data: {
      url: data.url || 'https://rupeewa.vercel.app/',
      ...data.data
    },
    actions: data.actions || [
      { action: 'open', title: 'Open' },
      { action: 'close', title: 'Dismiss' }
    ],
    requireInteraction: true,
    tag: data.tag || 'rupeewa-notification',
    renotify: true
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title || 'Rupeewa News Daily', options)
  );
});

// Handle notification click
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  if (event.action === 'close') return;
  
  const url = event.notification.data?.url || 'https://rupeewa.vercel.app/';
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      // Focus existing tab if open
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      // Open new tab
      return clients.openWindow(url);
    })
  );
});

// Handle notification close
self.addEventListener('notificationclose', event => {
  console.log('Notification closed:', event.notification.tag);
});