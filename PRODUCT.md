# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two roles, each with a distinct job:

- **Librarians (Admins).** Run the circulation desk: catalog books, process
  returns, manage members, work the reservation queue, and (per-deployment)
  set the organization's name, logo, and theme color. Desktop-first — the
  circulation desk is where the role lives day to day — but no longer
  desktop-only: a librarian checking the queue from a tablet at the stacks,
  or triaging one overdue notice from a phone, needs the admin shell to work
  there too, not just degrade into it.
- **Borrowers (Members).** School/academic library patrons — students and
  faculty — who search the catalog, borrow and self-renew books, place and
  track reservations, and check due dates, overwhelmingly from a phone. This
  is the primary usage pattern the product optimizes for (bottom tab bar,
  installable PWA, calendar export of due dates).

## Product Purpose

A self-hostable library management system covering the full circulation
lifecycle — cataloging, borrowing with due-date tracking, self-service
renewal, reservation queues, and returns — for school/academic libraries that
want to run their own instance rather than adopt a shared multi-tenant SaaS.

## Positioning

Generic and multi-tenant-by-deployment: one codebase that different
institutions each self-host and independently rebrand (org name, logo, theme
color) from the admin UI, with no redeploy or code change required. This
differs from a typical library system in two durable, evidenced ways:
- **Self-contained, offline-capable frontend.** Hand-written CSS, vanilla JS,
  inline SVG icons — no CDN, no CSS/JS framework — so the UI renders
  identically on restricted campus networks or offline.
- **Phone-first for the member experience specifically**, while the admin
  circulation desk stays a desktop tool — an intentional split rather than one
  responsive-everywhere design.

## Operating Context

- Librarians work from a desktop at a circulation desk.
- Members overwhelmingly check the app from a phone — browsing, borrowing,
  renewing, watching reservation queue position, and adding due dates/holds
  to their phone's calendar.
- Each deployment belongs to one school/academic institution; branding
  (name/logo/theme color) is set once per deployment via Admin → Settings.
- Deployed to a container/VM host (Render, Railway, Fly.io) with managed
  Postgres and a persistent disk for the uploaded logo; serverless hosts are
  explicitly unsupported without a code change (logo storage would need to
  move to object storage).

## Capabilities and Constraints

- **Circulation rules (current defaults, configurable via env/config):**
  14-day loan period, 3-day reservation hold, max 2 self-renewals per loan,
  max 5 active loans per member, blocked after 3 overdue items.
- Self-renewal is blocked when a loan is overdue, has hit its renewal limit,
  or another member is waiting on that title — the UI must explain which.
- Reservation queue position is shown to the reserving member (e.g. "You're
  next in line" / "#2 in line").
- **SQLite is dev-only.** Production must use Postgres (persistent, ephemeral
  filesystem on most hosts otherwise loses data on every deploy); the app
  warns at startup and in logs when it detects SQLite in production.
- Uploaded logo and its generated PWA icon set live on a persistent disk —
  without one, branding is lost on redeploy.
- Auth: Werkzeug password hashing, Flask-Login sessions, optional 30-day
  "remember me". A single seeded admin account (`admin` / configurable
  password) is created on first boot only — the seed does not re-run or reset
  it later.
- Schema changes are versioned with Flask-Migrate/Alembic; `init_db()` brings
  the database to the latest revision on every boot, so no manual migration
  step is required at deploy time.

## Evidence on Hand

- README documents the full feature set, deployment runbook (Render-focused),
  environment variables, database schema, and a troubleshooting table for the
  most common deploy failures.
- `docs/ui/` holds representative production screenshots (member dashboard
  light, admin circulation dark, mobile admin books, mobile sidebar,
  confirmation sheet, browse light) — real interface, not mockups.
- `docs/uiux-audit/` holds screenshots of known past defects (a date
  contradiction on the member dashboard, offscreen mobile admin actions, an
  unstyled fallback state) — useful as regression evidence, not current state.
- No case studies, testimonials, or named customer deployments exist yet; do
  not fabricate any.

## Product Principles

1. **Circulation truth over convenience.** Due-date, overdue, and renewal
   logic is derived from one canonical set of model properties
   (`due_state`/`days_until_due` etc.) so every surface — dashboard, history,
   labels, colors — agrees; never let a screen compute its own due-date logic.
2. **Two shells, one responsive system.** The librarian's circulation desk
   and the borrower's phone-first experience are two different products
   sharing a backend and a token set, each responsive across phone/tablet/
   desktop in its own way — not one layout stretched across both, and not
   one of the two frozen at a single size. A mobile improvement to the
   borrower experience still doesn't imply the admin side needs the *same*
   mobile treatment; it has its own (desk-dense on desktop, task-focused on
   phone, hybrid on tablet).
3. **Rebrandable without a redeploy.** Organization identity (name, logo,
   theme color) is admin-configurable data, not something baked into a build
   — any new branding-adjacent feature should follow that pattern.
4. **Runs offline and on restricted networks.** No CDN or external asset
   dependency in the frontend; this is a hosting/reliability constraint for
   campus networks, not a stylistic choice.
5. **Explain blocks, don't just disable.** When an action is unavailable
   (renew, reserve, etc.), surface the specific reason rather than a
   disabled control with no explanation.

## Accessibility & Inclusion

WCAG AA is an established, already-verified commitment: every
foreground/background color pairing is checked from rendered pixels in both
light and dark appearance. Existing baseline also includes a skip link,
visible focus rings, Escape-to-close on menus/sheets, ⌘K/Ctrl-K search
shortcut, 44px touch targets on coarse pointers, and full motion collapse
under `prefers-reduced-motion`. Preserve these as a floor for any new UI.
