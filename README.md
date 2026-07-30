# Library Management System

[![Tests](https://github.com/uscabayaosj/LibrarySystem/actions/workflows/tests.yml/badge.svg)](https://github.com/uscabayaosj/LibrarySystem/actions/workflows/tests.yml)

A Flask-based library management system with separate **Librarian (Admin)** and **Borrower (Member)** dashboards. Supports book cataloguing, borrowing with due-date tracking, returns, renewals, reservations, and member management.

## Features

### 👤 For Members (Borrowers)
- **Search & Browse** — Find books by title, author, ISBN, or category
- **Borrow Books** — 14-day loan period with automatic due-date tracking
- **Renew Books** — Extend a loan yourself for a fresh loan period, as long as it isn't overdue, hasn't hit the renewal limit, and no one else is waiting for it
- **Reserve Books** — Queue for books when all copies are borrowed (3-day hold), with a queue-position indicator ("You're next in line" / "#2 in line") so you know where you stand
- **Dashboard** — See currently borrowed books, overdue items, and recent activity at a glance
- **History** — Complete borrowing and return history

### 👑 For Librarians (Admins)
- **Dashboard** — Live stats: total books, active loans, overdue items, members
- **Book Management** — Add, edit, search, and delete books with rich metadata (publisher, year, description)
- **Member Management** — View all members, search/filter, see borrowing stats, delete
- **Member Detail** — Per-member view with full borrowing history and reservations
- **Returns** — Process returns with a single click
- **Borrowing History** — Full history with status filter (all / active / returned) and pagination
- **Reservation Queue** — Process pending reservations automatically when copies become available

### 💡 UX Improvements
- **Pagination** on all data tables (books, members, borrowing history)
- **Search-as-You-Type** — Search books, members with instant results
- **Status Filters** — Filter borrowing history by active/overdue/returned
- **Colour-Coded Alerts** — Overdue items highlighted in red, due-soon in orange, meeting WCAG AA contrast in both light and dark appearance
- **Confirmation Sheets** — Destructive or consequential actions (delete, renew, cancel reservation) show a macOS-style sheet naming the exact record
- **Flash Messages** — Clear success/warning/danger/info feedback; errors and warnings stay until dismissed
- **Responsive Design** — A source-list sidebar on desktop collapses to a drawer on mobile, and data tables become stacked cards so row actions stay reachable
- **Self-contained UI** — Hand-written CSS, vanilla JS, and inline SVG icons; no CDN, so the app renders identically offline

### 📱 Phone-First for Members
- **Bottom tab bar** on phones (Overview / Browse / Loans / Reserved), with a collapsing large-title header — the admin side stays desktop-only
- **Installable app** — Add to Home Screen for a standalone app with its own icon
- **Remember me** — optional 30-day persistent login
- **Calendar export** — one tap adds a loan's due date or a reservation's expiry to the phone's own Calendar app, with a day-before reminder built in

### 🎨 Organization Branding
- **Custom name, logo, and theme color** — set from Admin → Settings, no redeploy required
- Uploaded logos are validated, re-encoded, and used to regenerate the installed-app icon set
- A single brand color yields a full light/dark accent palette, derived and WCAG-AA-verified automatically

## Quick Start

### Prerequisites
- Python 3.11+
- pip or poetry

### Installation

```bash
# Clone the repo
git clone https://github.com/uscabayaosj/LibrarySystem.git
cd LibrarySystem

# Install dependencies (choose one)
pip install flask flask-sqlalchemy flask-login
# OR
poetry install

# Initialize the database and start the server
python app.py
```

The first run will:
1. Create a local SQLite database (`instance/library.db`)
2. Seed an admin user: **admin / admin**

### Default Login

| Role | Username | Password |
|------|----------|----------|
| **Librarian** | `admin` | `admin` |
| **Member** | Register a new account | - |

## Configuration

Set environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | dev fallback (required in prod) | Flask session signing key. **Required** when `FLASK_ENV=production` and debug is off — the app refuses to start without it. |
| `DATABASE_URL` | `sqlite:///library.db` | Database connection string |
| `FLASK_ENV` | `development` | Set to `production` to enforce `SECRET_KEY` and secure cookies |
| `FLASK_DEBUG` | `0` | Set to `1` **only** in local development to enable the debugger |
| `SESSION_COOKIE_SECURE` | `1` in production | Send session cookie over HTTPS only |
| `ADMIN_PASSWORD` | `admin` | Password for the seeded admin account on first run |

For production: set a long random `SECRET_KEY`, keep `FLASK_DEBUG` unset/`0`, and change the seeded admin password.

### Running tests

```bash
pip install pytest flask-wtf
pytest
```

CI (`.github/workflows/tests.yml`) runs the same suite on every push and pull
request against `main`, on Python 3.11 and 3.12.

## Database Schema

| Table | Key Columns |
|-------|-------------|
| **User** | id, username, email, password_hash, is_admin, phone, member_since |
| **Book** | id, title, author, isbn, category, publisher, publication_year, description, quantity, available_quantity |
| **Borrowing** | id, user_id, book_id, borrow_date, due_date, return_date, status (active/returned), renewal_count |
| **Reservation** | id, user_id, book_id, reservation_date, expiration_date, status (active/fulfilled/expired/cancelled) |

## Tech Stack

- **Backend:** Flask 3.x, Flask-SQLAlchemy, Flask-Login, Flask-WTF (CSRF)
- **Frontend:** a self-contained macOS-style design system — hand-written CSS
  and vanilla JS, inline SVG icons. **No CSS/JS frameworks and no CDN**, so the
  UI renders identically offline and on restricted networks.
- **Database:** SQLite (default) / PostgreSQL
- **Auth:** Werkzeug password hashing

## Interface

The UI follows macOS conventions: a source-list sidebar, a translucent sticky
toolbar, SF system typography, hairline separators, and macOS-style sheets for
confirmations. It ships with **light and dark appearance** — following the OS
by default, with a manual override in the account menu (remembered per browser).

| | |
|---|---|
| ![Member dashboard](docs/ui/member-dashboard-light.png) | ![Circulation, dark](docs/ui/admin-circulation-dark.png) |
| Member overview (light) | Circulation desk (dark) |

Design notes:

- **Colour** — text colours use Apple's accessible palette variants. Every
  foreground/background pair in the app meets WCAG AA, verified from rendered
  pixels in both appearances.
- **Layout** — tables become stacked cards below 860px so row actions stay
  reachable on a phone; touch targets are 44px on coarse pointers.
- **Motion** — all transitions collapse under `prefers-reduced-motion`.
- **Keyboard** — skip link, visible focus rings, Escape closes menus and
  sheets, and ⌘K / Ctrl-K jumps to the search field.

## What Changed (v3.3 — phone-first member experience + organization branding)

This release has two parts: making the app genuinely usable for borrowers on a
phone (the primary way most members actually use it), and making the app
itself deployable for a different organization without touching code.

**Phone-first member experience:**
- **Bottom tab bar.** Members on a phone (≤860px) get an iOS-style translucent,
  blurred tab bar (Overview / Browse / Loans / Reserved) instead of the desktop
  sidebar, with unread-style badges for active loans/reservations. Admins
  always keep the desktop sidebar — this is a borrower-only change.
- **Large-title collapse.** Page headings render large at the top of the
  scroll and shrink into the toolbar as you scroll down, mirroring
  `UINavigationBar` large titles.
- **Generated cover art.** Books without a photo get a deterministic
  "Music/Podcasts-style" colour tile (stable per-ISBN hash, not random —
  the colour doesn't change on server restart) instead of a blank icon.
- **Remember me.** An optional 30-day persistent login cookie so a phone
  borrower isn't signed out between short visits.
- **Installable app.** A web manifest + icon set so "Add to Home Screen" gives
  a real standalone app with its own icon, not a bare bookmark tab.
- **Calendar export.** Every active loan and reservation has an "add to
  calendar" button that downloads an `.ics` file with a built-in
  day-before reminder — due dates and expiries land in the phone's own
  Calendar app without this project needing any push-notification backend.
- **Glassmorphic action buttons.** The calendar buttons use a frosted,
  translucent circular style (`.btn-glass`) rather than a flat icon button.
- Fixed three WCAG AA contrast regressions introduced by this work (tab-bar
  label/badge/active-state colours, and the generated cover-art gradient at
  certain hues), all found and fixed using the same fill-vs-text token
  pattern already established in the design system.

**Organization branding:**
- **Settings page** (Admin → Settings): set the organization's display name,
  upload a logo, and pick a theme color, all from the UI — no redeploy.
- **Logo.** Square PNG/JPEG/WEBP, ideally 512×512–1024×1024px (transparent PNG
  recommended), max 2 MB. Uploads are re-validated and re-encoded through
  Pillow (not saved as-is) and used to regenerate the installed-app icon set
  (favicon, apple-touch-icon, manifest icons) so "Add to Home Screen" shows
  the organization's own mark.
- **Theme color.** One brand color is enough — a light and dark accent
  variant (plus the separate "holds white text" fill shade this design system
  already needs) are derived algorithmically and verified against real WCAG
  contrast math, so an arbitrary brand color can't silently break readability.
- The org name now appears in the sidebar, page titles, the login page, the
  installed-app name, and the PWA manifest.

## What Changed (v3.2 — reservation queue position)

- **Queue-position indicator.** The reservations page (audit `UIUX_AUDIT.md`
  §11) now shows exactly where each reservation stands: "You're next in
  line" for the head of the queue, "#N in line" further back, plus a note
  when other members are waiting. The librarian's per-member detail view
  shows the same data as a neutral "#N of M" for whichever member they're
  looking at.
- Position is computed consistently with which reservation is actually
  fulfilled first (ties broken by id, matching `get_active_reservation`),
  so "#1" never disagrees with reality.
- Fixed a pre-existing contrast gap found while verifying this: breadcrumb
  links sit directly on the window background rather than a card, and the
  shared accent colour used everywhere else fell to 4.27:1 there in light
  mode. Scoped fix, not a change to the shared token.

## What Changed (v3.1 — renewals + CI)

- **Self-service renewals.** Members can renew an active loan for a fresh
  loan period from the dashboard or My Loans, as long as it isn't overdue,
  hasn't reached the renewal limit (`MAX_RENEWALS`, default 2), and no other
  member is waiting on a reservation for that title. Blocked loans show the
  specific reason instead of just disabling the button.
- **Continuous integration.** A GitHub Actions workflow runs the pytest suite
  on every push and pull request against `main`.
- **Fixed a broken documented install path.** `poetry.lock` had drifted out of
  sync with `pyproject.toml` since Flask-WTF and pytest were added, so
  `poetry install` — the README's own alternate install command — would fail
  on a clean checkout. Regenerated.

## What Changed (v3.0 — macOS-style interface)

- **New design system.** Bootstrap and its CDN are gone, replaced by a
  self-contained macOS-flavoured stylesheet, vanilla JS, and inline SVG icons.
  Sidebar navigation, translucent toolbar, and native-feeling controls.
- **Light and dark appearance**, following the OS with a manual override.
- **Due dates are now consistent.** All due/overdue copy derives from one
  calendar-date property, fixing the case where a single loan displayed as both
  "7 days overdue" and "8 days overdue", the meaningless "0 days overdue", and
  the off-by-one in "days left".
- **Accessibility**: every form control is properly labelled, one `<h1>` per
  page, `<main>` landmark and skip link, scoped table headers, named icon
  buttons, and AA-compliant contrast throughout both appearances.
- **Mobile**: tables become stacked cards, so Edit / Delete / Check In are
  reachable on a phone instead of scrolling off-screen.
- **Interaction**: `confirm()` replaced by a macOS-style sheet naming the exact
  record; the overdue dashboard tile now filters to overdue; browse results
  show what you already have on loan instead of offering a doomed Borrow button.

## What Changed (v2.1 — audit fixes)

- **Fixed 4 crashes:** the My Reservations page (`now` undefined), deleting books/members with borrowing history (FK cascade), and editing a book to a duplicate ISBN now validate/cascade instead of returning HTTP 500.
- **Security:** `debug` is now env-gated (off by default), `SECRET_KEY` is required in production, CSRF protection (Flask-WTF) added to every form, the login `next` redirect is restricted to same-site paths, emails are normalized, and a minimum password length is enforced.
- **Data integrity:** borrowing uses an atomic availability decrement (no over-lending race), members can't borrow duplicate copies of a title, there's a max-concurrent-loan cap, and the reservation queue now drains fully.
- **UI/UX & a11y:** member search is paginated, the add-book form preserves input and re-opens on error, icon-only buttons have `aria-label`s, only success/info flashes auto-dismiss (errors persist), and there are styled 403/404/500 pages.
- **Quality:** removed the N+1 on the members list, added a `pytest` regression suite, and writes roll back cleanly on error.

See `AUDIT.md` for the full findings this release addresses.

## What Changed (v2.0)

- **Critical fix:** Database no longer wiped on every app start (`recreate_db()` removed from import time)
- **New schema:** Book publisher/year/description fields, User phone/member_since, Borrowing status tracking
- **Admin dashboard:** Live stats, recent activity feed, quick actions panel
- **Member dashboard:** Current loans list, overdue alerts, recent activity
- **Member detail page:** Full per-member history with borrowing stats
- **Return system:** Admin can mark books as returned (updates availability)
- **Pagination:** All data tables paginated (20-30 items per page)
- **GET-based search:** Search uses query parameters (bookmarkable URLs)
- **Search/filter:** Filter members by username/email, filter history by status
- **Confirmation dialogs:** All destructive actions require confirmation
- **Flash messages:** Categorized with icons, auto-dismiss after 6 seconds
- **Bootstrap 5 + Icons:** Polished UI with responsive layout
- **Member delete:** Admin can delete members (with safety checks for active loans)