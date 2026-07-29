/* Library System — UI behaviour.
   Replaces the former Bootstrap bundle: sidebar drawer, account menu,
   flash dismissal, appearance switching, and a macOS-style confirmation
   sheet in place of window.confirm(). No dependencies. */

(function () {
    'use strict';

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

        function setSidebar(open) {
            if (!sidebar) { return; }
            sidebar.setAttribute('data-open', open ? 'true' : 'false');
            if (scrim) { scrim.setAttribute('data-open', open ? 'true' : 'false'); }
            if (toggle) { toggle.setAttribute('aria-expanded', open ? 'true' : 'false'); }
            document.body.style.overflow = open ? 'hidden' : '';
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
                sheetTitle.textContent = form.getAttribute('data-confirm-title') || 'Are you sure?';
                sheetBody.textContent = form.getAttribute('data-confirm') || '';
                sheetOk.textContent = form.getAttribute('data-confirm-label') || 'Confirm';
                sheetOk.className = 'btn ' +
                    (form.getAttribute('data-confirm-kind') === 'danger' ? 'btn-danger' : 'btn-primary');
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
           Global keys
           ----------------------------------------------------------- */
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                setMenu(false);
                if (sidebar && sidebar.getAttribute('data-open') === 'true') { setSidebar(false); }
            }
            // Cmd/Ctrl-K focuses search when the page offers one.
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
                var search = document.querySelector('[data-search-input]');
                if (search) { e.preventDefault(); search.focus(); search.select(); }
            }
        });
    });
})();
