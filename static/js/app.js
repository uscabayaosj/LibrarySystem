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
                // Reset from any prior use of the sheet -- a disable left over
                // from the last confirm must not leak into this one.
                sheetOk.disabled = false;
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
                if (!pendingForm || sheetOk.disabled) { return; }
                var form = pendingForm;
                // Double-tapping "Confirm" on a slow campus connection must not
                // fire the borrow/renew/reserve/cancel request twice -- these
                // mutate real inventory (a copy count, a queue slot), so a
                // second race-condition POST either double-decrements stock or
                // just errors, neither of which the member should be able to
                // trigger by accident. openSheet() clears this disable on the
                // next use, and the pageshow/timeout guard below clears it if
                // the POST never actually leaves the page -- the point is to
                // block a double-tap, not to brick the control.
                sheetOk.disabled = true;
                disableFormSubmit(form);
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
           Double-submit protection for plain (non-sheet) POST forms
           Add Book, Save Changes (edit book / settings), and Process
           Reservations don't go through the confirmation sheet, but they're
           still a plain POST-and-redirect with no in-page "saving…" state --
           an impatient repeat click can fire the request twice. Reuses
           disableFormSubmit()/restoreDisabledSubmits() below (defined for
           the confirm-sheet path) so these get the same bfcache/timeout
           recovery instead of a second, lesser mechanism. Sheet-routed forms
           already call disableFormSubmit() themselves once confirmed, and
           calling it again here is a no-op (it bails if already disabled).
           ----------------------------------------------------------- */
        document.addEventListener('submit', function (e) {
            var form = e.target;
            if (!form || !form.matches || !form.matches('form')) { return; }
            if ((form.method || 'get').toLowerCase() !== 'post') { return; }
            // An unconfirmed [data-confirm] form isn't really submitting --
            // the sheet just intercepted it and called preventDefault().
            if (form.hasAttribute('data-confirm') && form.dataset.confirmed !== 'yes') { return; }
            disableFormSubmit(form);
        });

        /* -----------------------------------------------------------
           Double-submit guard for the form's own trigger button
           These forms navigate the whole page on submit (no fetch/XHR), so a
           successful submit always unloads this DOM -- but a failed one
           (offline, timeout) can leave the page in place, or the browser can
           restore it later from the back-forward cache with the button still
           disabled from the earlier attempt. Both cases must recover on their
           own without a reload, since re-tapping "Borrow"/"Renew" is the
           user's only path forward on a flaky connection.
           ----------------------------------------------------------- */
        function disableFormSubmit(form) {
            var btn = form.querySelector('button[type="submit"], button:not([type])');
            if (!btn || btn.disabled) { return; }
            btn.disabled = true;
            btn.dataset.wasDisabledForSubmit = 'yes';
        }

        function restoreDisabledSubmits() {
            document.querySelectorAll('[data-was-disabled-for-submit="yes"]').forEach(function (btn) {
                btn.disabled = false;
                delete btn.dataset.wasDisabledForSubmit;
            });
        }

        // A safety net for the case where the POST never actually leaves the
        // page (offline, DNS failure, etc.) -- without this, "Borrow" stays
        // permanently disabled with no way to retry.
        window.addEventListener('pageshow', function (e) {
            if (e.persisted) { restoreDisabledSubmits(); }
        });
        window.setTimeout(restoreDisabledSubmits, 12000);

        /* -----------------------------------------------------------
           Cancel button inside a <details> panel (e.g. Add Book).
           type="reset" already clears the form's own fields; this closes
           the disclosure too, matching the Cancel button on Edit Book
           (which simply navigates back).
           ----------------------------------------------------------- */
        document.querySelectorAll('[data-collapse-details]').forEach(function (btn) {
            on(btn, 'click', function () {
                var target = document.getElementById(btn.getAttribute('data-collapse-details'));
                if (target && target.tagName === 'DETAILS') {
                    // Let the native reset happen first, then collapse.
                    window.setTimeout(function () { target.open = false; }, 0);
                }
            });
        });

        /* -----------------------------------------------------------
           Bulk row selection (Borrowing History active-loan check-ins)
           A header checkbox toggles every selectable row checkbox; the
           "Check In Selected" button stays disabled until at least one row
           is checked, and its confirm-sheet body is filled in with a count
           right before the sheet reads the form's data-confirm attribute.
           ----------------------------------------------------------- */
        var bulkForm = document.querySelector('[data-bulk-form]');
        if (bulkForm) {
            // The row checkboxes and header "select all" live inside the
            // table, not nested inside this <form> -- a per-row Check In
            // button is itself a <form>, and forms can't nest -- so they're
            // associated to it via form="bulk-checkin" instead of DOM
            // position, and found here the same way: by that association.
            var selectAll = document.querySelector('[data-select-all]');
            var rowChecks = Array.prototype.slice.call(document.querySelectorAll('[data-row-check]'));
            var bulkSubmit = document.querySelector('[data-bulk-submit]');

            function syncBulkState() {
                var checked = rowChecks.filter(function (c) { return c.checked; });
                var count = checked.length;
                if (bulkSubmit) { bulkSubmit.disabled = count === 0; }
                bulkForm.setAttribute(
                    'data-confirm',
                    count + ' book' + (count === 1 ? '' : 's') + ' will be marked returned and put back on the shelf.'
                );
                if (selectAll) {
                    selectAll.checked = rowChecks.length > 0 && count === rowChecks.length;
                    selectAll.indeterminate = count > 0 && count < rowChecks.length;
                }
            }

            on(selectAll, 'change', function () {
                rowChecks.forEach(function (c) { c.checked = selectAll.checked; });
                syncBulkState();
            });
            rowChecks.forEach(function (c) { on(c, 'change', syncBulkState); });
            syncBulkState();
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
