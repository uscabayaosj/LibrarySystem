/* Library System — UI behaviour.
   Replaces the former Bootstrap bundle: sidebar drawer, account menu,
   flash dismissal, appearance switching, and a macOS-style confirmation
   sheet in place of window.confirm(). No dependencies. */

(function () {
    'use strict';

    /* ---------------------------------------------------------------
       PWA install plumbing + home-screen badge
       The badge counts overdue loans (see /badge-count) -- the one thing
       on the member dashboard that actually needs the member's attention,
       same signal the "Loans" tab-bar badge already shows. Badging API
       support is still Chromium/iOS-Safari-16.4+ only, so everything here
       is feature-detected and a silent no-op elsewhere.
       --------------------------------------------------------------- */
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function () {
            navigator.serviceWorker.register('/sw.js').catch(function () {
                // Registration failing (e.g. served over plain HTTP in dev)
                // shouldn't block the rest of the app.
            });
        });
    }

    if ('setAppBadge' in navigator) {
        var applyBadge = function (count) {
            if (count > 0) { navigator.setAppBadge(count).catch(function () {}); }
            else { navigator.clearAppBadge().catch(function () {}); }
        };

        var refreshBadge = function () {
            fetch('/badge-count', { credentials: 'same-origin' })
                .then(function (res) { return res.ok ? res.json() : null; })
                .then(function (data) { if (data) { applyBadge(data.count); } })
                .catch(function () {});
        };

        document.addEventListener('DOMContentLoaded', function () {
            var initial = document.body.getAttribute('data-badge-count');
            if (initial === null) { navigator.clearAppBadge().catch(function () {}); return; }
            applyBadge(parseInt(initial, 10) || 0);

            // Refresh whenever the installed app is brought back to the
            // foreground, so the badge doesn't go stale between launches.
            document.addEventListener('visibilitychange', function () {
                if (document.visibilityState === 'visible') { refreshBadge(); }
            });
        });
    }

    /* ---------------------------------------------------------------
       Appearance (auto / light / dark), persisted in localStorage
       --------------------------------------------------------------- */
    var STORE_KEY = 'ls-appearance';

    function applyAppearance(value) {
        if (value === 'light' || value === 'dark') {
            document.documentElement.setAttribute('data-appearance', value);
        } else {
            document.documentElement.removeAttribute('data-appearance');
        }
    }

    function currentAppearance() {
        try { return localStorage.getItem(STORE_KEY) || 'auto'; } catch (e) { return 'auto'; }
    }

    function setAppearance(value) {
        try { localStorage.setItem(STORE_KEY, value); } catch (e) { /* private mode */ }
        applyAppearance(value);
        syncAppearanceUI(value);
    }

    function syncAppearanceUI(value) {
        document.querySelectorAll('[data-appearance-option]').forEach(function (el) {
            var on = el.getAttribute('data-appearance-option') === value;
            el.setAttribute('aria-checked', on ? 'true' : 'false');
            var check = el.querySelector('[data-check]');
            if (check) { check.style.visibility = on ? 'visible' : 'hidden'; }
        });
    }

    // Applied as early as possible to avoid a flash of the wrong appearance.
    applyAppearance(currentAppearance());

    /* ---------------------------------------------------------------
       Helpers
       --------------------------------------------------------------- */
    function on(el, evt, fn) { if (el) { el.addEventListener(evt, fn); } }

    function trapFocus(container, event) {
        var focusables = container.querySelectorAll(
            'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (!focusables.length) { return; }
        var first = focusables[0];
        var last = focusables[focusables.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault(); last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault(); first.focus();
        }
    }

    document.addEventListener('DOMContentLoaded', function () {

        /* -----------------------------------------------------------
           Sidebar drawer (small screens)
           ----------------------------------------------------------- */
        var sidebar = document.getElementById('sidebar');
        var scrim = document.getElementById('scrim');
        var toggle = document.getElementById('sidebar-toggle');
        var mainCol = document.getElementById('app-main-col');
        var sidebarLastFocus = null;

        /* The sidebar is a persistent, non-modal nav on desktop and an
           overlay drawer with modal behaviour on phones (see the 860px
           breakpoint in app.css) -- the same element serving two different
           interaction models. role/aria-modal, the focus trap, and inert-ing
           the page behind it are only ever applied here, on open, so a
           desktop screen reader never sees the always-visible sidebar as a
           dialog it can't leave. */
        function setSidebar(open) {
            if (!sidebar) { return; }
            sidebar.setAttribute('data-open', open ? 'true' : 'false');
            if (scrim) { scrim.setAttribute('data-open', open ? 'true' : 'false'); }
            if (toggle) { toggle.setAttribute('aria-expanded', open ? 'true' : 'false'); }
            document.body.style.overflow = open ? 'hidden' : '';

            if (open) {
                sidebar.setAttribute('role', 'dialog');
                sidebar.setAttribute('aria-modal', 'true');
                if (mainCol) { mainCol.inert = true; }
                sidebarLastFocus = document.activeElement;
                var firstFocusable = sidebar.querySelector(
                    'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])'
                );
                if (firstFocusable) { firstFocusable.focus(); }
            } else {
                sidebar.removeAttribute('role');
                sidebar.removeAttribute('aria-modal');
                if (mainCol) { mainCol.inert = false; }
                if (sidebarLastFocus) { sidebarLastFocus.focus(); }
                sidebarLastFocus = null;
            }
        }

        on(toggle, 'click', function () {
            setSidebar(sidebar.getAttribute('data-open') !== 'true');
        });
        on(scrim, 'click', function () { setSidebar(false); });

        /* -----------------------------------------------------------
           Account popover menu
           ----------------------------------------------------------- */
        var accountBtn = document.getElementById('account-btn');
        var accountMenu = document.getElementById('account-menu');

        function setMenu(open) {
            if (!accountMenu) { return; }
            accountMenu.setAttribute('data-open', open ? 'true' : 'false');
            if (accountBtn) { accountBtn.setAttribute('aria-expanded', open ? 'true' : 'false'); }
        }

        on(accountBtn, 'click', function (e) {
            e.stopPropagation();
            setMenu(accountMenu.getAttribute('data-open') !== 'true');
        });

        document.addEventListener('click', function (e) {
            if (accountMenu && accountMenu.getAttribute('data-open') === 'true' &&
                !accountMenu.contains(e.target) && e.target !== accountBtn) {
                setMenu(false);
            }
        });

        /* -----------------------------------------------------------
           Appearance options inside the account menu
           ----------------------------------------------------------- */
        document.querySelectorAll('[data-appearance-option]').forEach(function (el) {
            on(el, 'click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                setAppearance(el.getAttribute('data-appearance-option'));
            });
        });
        syncAppearanceUI(currentAppearance());

        /* -----------------------------------------------------------
           Flash messages
           Success/info retire on their own; warnings and errors stay
           until dismissed so they can't be missed.
           ----------------------------------------------------------- */
        document.querySelectorAll('.alert').forEach(function (alert) {
            var closeBtn = alert.querySelector('.alert-close');
            function dismiss() {
                alert.classList.add('is-leaving');
                setTimeout(function () { alert.remove(); }, 200);
            }
            on(closeBtn, 'click', dismiss);

            if (alert.classList.contains('alert-success') || alert.classList.contains('alert-info')) {
                setTimeout(dismiss, 6000);
            }
        });

        /* -----------------------------------------------------------
           Confirmation sheet
           Any form with [data-confirm] is intercepted; the sheet reads
           its title/body/label from data attributes.
           ----------------------------------------------------------- */
        var backdrop = document.getElementById('confirm-sheet');
        if (backdrop) {
            var sheetTitle = backdrop.querySelector('[data-sheet-title]');
            var sheetBody = backdrop.querySelector('[data-sheet-body]');
            var sheetOk = backdrop.querySelector('[data-sheet-confirm]');
            var sheetCancel = backdrop.querySelector('[data-sheet-cancel]');
            var pendingForm = null;
            var lastFocus = null;

            function closeSheet() {
                backdrop.setAttribute('data-open', 'false');
                pendingForm = null;
                if (lastFocus) { lastFocus.focus(); }
            }

            function openSheet(form) {
                pendingForm = form;
                lastFocus = document.activeElement;
                var isDanger = form.getAttribute('data-confirm-kind') === 'danger';
                sheetTitle.textContent = form.getAttribute('data-confirm-title') || 'Are you sure?';
                sheetBody.textContent = form.getAttribute('data-confirm') || '';
                sheetOk.textContent = form.getAttribute('data-confirm-label') || 'Confirm';
                sheetOk.className = 'btn ' + (isDanger ? 'btn-danger' : 'btn-primary');
                // The abort button is per-form: a destructive sheet whose confirm
                // reads "Cancel Reservation" must not sit beside a "Cancel" that
                // means the opposite. Default stays "Cancel" for everything else.
                sheetCancel.textContent = form.getAttribute('data-confirm-cancel') || 'Cancel';
                // Warning-triangle for destructive actions only; routine ones
                // (borrow, renew) get a neutral tone rather than an alarm.
                backdrop.setAttribute('data-kind', isDanger ? 'danger' : 'safe');
                backdrop.setAttribute('data-open', 'true');
                sheetCancel.focus();
            }

            document.querySelectorAll('form[data-confirm]').forEach(function (form) {
                on(form, 'submit', function (e) {
                    if (form.dataset.confirmed === 'yes') { return; }
                    e.preventDefault();
                    openSheet(form);
                });
            });

            on(sheetOk, 'click', function () {
                if (!pendingForm) { return; }
                var form = pendingForm;
                form.dataset.confirmed = 'yes';
                closeSheet();
                if (typeof form.requestSubmit === 'function') { form.requestSubmit(); }
                else { form.submit(); }
            });

            on(sheetCancel, 'click', closeSheet);
            on(backdrop, 'click', function (e) { if (e.target === backdrop) { closeSheet(); } });

            document.addEventListener('keydown', function (e) {
                if (backdrop.getAttribute('data-open') !== 'true') { return; }
                if (e.key === 'Escape') { closeSheet(); }
                if (e.key === 'Tab') { trapFocus(backdrop, e); }
            });
        }

        /* -----------------------------------------------------------
           Open a <details> when a link points at it.
           The "Add Book" toolbar button is <a href="#add-book">, and
           #add-book is a collapsed <details>. Following the anchor scrolls
           the summary into view but leaves the panel shut, so the form never
           appears -- the button looks broken. Opening the target here makes
           it a single click. Progressive enhancement: without JS the summary
           is still clickable, and a server re-render with form errors still
           opens the panel via the template's `open` attribute.
           ----------------------------------------------------------- */
        function openTargetDetails(hash) {
            if (!hash || hash.charAt(0) !== '#' || hash.length < 2) { return; }
            var target;
            try { target = document.getElementById(decodeURIComponent(hash.slice(1))); }
            catch (e) { return; }
            if (target && target.tagName === 'DETAILS') { target.open = true; }
        }
        document.querySelectorAll('a[href^="#"]').forEach(function (link) {
            on(link, 'click', function () { openTargetDetails(link.getAttribute('href')); });
        });
        // Also handle a deep link that lands directly on the hash.
        openTargetDetails(window.location.hash);

        /* -----------------------------------------------------------
           Large-title collapse (member phone experience)
           Mirrors iOS's large-title nav bar: the big title at the top of
           the content fades out and the compact toolbar title fades in
           once the page has scrolled past a small threshold. Harmless
           no-op outside that layout -- the CSS only reacts to
           .is-scrolled inside the mobile/member media query.
           ----------------------------------------------------------- */
        var toolbar = document.getElementById('toolbar');
        if (toolbar) {
            var scrollTicking = false;
            var THRESHOLD = 28;

            function updateScrolled() {
                var scrolled = (window.scrollY || document.documentElement.scrollTop) > THRESHOLD;
                toolbar.classList.toggle('is-scrolled', scrolled);
                scrollTicking = false;
            }

            updateScrolled();
            window.addEventListener('scroll', function () {
                if (!scrollTicking) {
                    scrollTicking = true;
                    window.requestAnimationFrame(updateScrolled);
                }
            }, { passive: true });
        }

        /* -----------------------------------------------------------
           Global keys
           ----------------------------------------------------------- */
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                setMenu(false);
                if (sidebar && sidebar.getAttribute('data-open') === 'true') { setSidebar(false); }
            }
            if (e.key === 'Tab' && sidebar && sidebar.getAttribute('data-open') === 'true') {
                trapFocus(sidebar, e);
            }
            // Cmd/Ctrl-K focuses search when the page offers one.
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
                var search = document.querySelector('[data-search-input]');
                if (search) { e.preventDefault(); search.focus(); search.select(); }
            }
        });
    });
})();
