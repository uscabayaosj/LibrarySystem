/* Library System — service worker (rendered by app.py, see /sw.js).
   Three jobs, none of them caching: every fetch still goes to the network.
   1. Be the controller scoped at '/' that lets navigator.setAppBadge()
      persist a home-screen badge once the app is installed.
   2. Receive Web Push (push.py) and show it, setting the icon badge to the
      unread count the server put in the payload.
   3. Version the app: VERSION changes on every deploy, so the browser sees
      a new worker, and the page offers "Reload" rather than the new code
      taking over mid-task. See app.js for the other half. */

var VERSION = '{{ version }}';

self.addEventListener('install', function () {
    // Deliberately no skipWaiting(): the page decides when to switch, via
    // the SKIP_WAITING message below, once the member taps Reload.
});

self.addEventListener('activate', function (event) {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('message', function (event) {
    if (event.data && event.data.type === 'SKIP_WAITING') { self.skipWaiting(); }
});

function setBadge(count) {
    if (!('setAppBadge' in self.navigator)) { return Promise.resolve(); }
    var p = count > 0 ? self.navigator.setAppBadge(count) : self.navigator.clearAppBadge();
    return p.catch(function () {});
}

self.addEventListener('push', function (event) {
    var data = {};
    try { data = event.data ? event.data.json() : {}; } catch (e) {}
    var title = data.title || 'Library';
    var options = {
        body: data.body || '',
        icon: '{{ icon_url }}',
        badge: '{{ icon_url }}',
        tag: data.url || 'library-notice',
        renotify: true,
        data: { url: data.url || '/notifications' }
    };
    event.waitUntil(Promise.all([
        self.registration.showNotification(title, options),
        typeof data.badge === 'number' ? setBadge(data.badge) : Promise.resolve()
    ]));
});

self.addEventListener('notificationclick', function (event) {
    event.notification.close();
    var url = (event.notification.data && event.notification.data.url) || '/notifications';
    event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true })
        .then(function (list) {
            for (var i = 0; i < list.length; i++) {
                if ('focus' in list[i]) {
                    return list[i].focus().then(function (c) {
                        return c.navigate ? c.navigate(url) : c;
                    });
                }
            }
            return self.clients.openWindow(url);
        }));
});

/* The push service rotated this device's subscription. Re-subscribe with
   the same server key and tell the server, so notices keep arriving
   without the member having to toggle anything. */
self.addEventListener('pushsubscriptionchange', function (event) {
    var key = event.oldSubscription && event.oldSubscription.options
        ? event.oldSubscription.options.applicationServerKey : null;
    if (!key) { return; }
    event.waitUntil(
        self.registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: key })
            .then(function (sub) {
                return fetch('/push/subscribe', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(sub.toJSON())
                });
            }).catch(function () {})
    );
});
