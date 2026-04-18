// web/static/js/sw.js — Push notification service worker
self.addEventListener('push', function(event) {
  if (!event.data) return;
  var data;
  try { data = event.data.json(); } catch(e) { data = {title:'Koda', body: event.data.text()}; }
  event.waitUntil(
    self.registration.showNotification(data.title || 'Koda Nutrition', {
      body: data.body || '',
      vibrate: [200, 100, 200],
      data: {url: '/nutrition'},
    })
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data && event.notification.data.url ? event.notification.data.url : '/nutrition'));
});
