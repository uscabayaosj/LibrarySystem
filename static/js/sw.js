/* Library System — service worker.
   Exists only so the app has a controller scoped at '/': that's what lets
   navigator.setAppBadge() reliably persist a home-screen badge once the
   PWA is installed. No caching/offline behaviour yet -- every fetch just
   passes through to the network. */

self.addEventListener('install', function (event) {
    self.skipWaiting();
});

self.addEventListener('activate', function (event) {
    event.waitUntil(self.clients.claim());
});
