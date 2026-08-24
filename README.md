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
- **Search** — Find books by title, author, ISBN, or category, and members by name or email, from a single search bar with a one-tap clear
- **Status Filters** — Filter borrowing history by active/overdue/returned
- **Colour-Coded Alerts** — Overdue items highlighted in red, due-soon in orange, meeting WCAG AA contrast in both light and dark appearance
- **Confirmation Dialogs** — Destructive or consequential actions (delete, renew, cancel reservation) show a dialog naming the exact record
- **Flash Messages** — Clear success/warning/danger/info feedback; errors and warnings stay until dismissed
- **Responsive Design** — The indigo navigation rail on desktop collapses to a drawer on mobile, and data tables become stacked cards so row actions stay reachable
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
1. Create a local SQLite database (`instance/library.db`) and run every migration
2. Seed an admin user: **admin / admin**

### Database migrations

Schema changes are managed with Flask-Migrate (Alembic). **You do not need to
run anything by hand on deploy, on either host** — `init_db()` brings the
database to the latest revision and seeds an admin if there isn't one, and
both hosts call it before serving:

| Host | What calls `init_db()` |
|---|---|
| Render | The `Procfile`'s `release:` step, before traffic reaches the app |
| Vercel | `_boot_migrate_if_requested()` at the bottom of `app.py`, at import time — Vercel has no release phase, so the import is the only hook available |

The Vercel path is gated on `MIGRATE_ON_BOOT`, which defaults to on whenever
Vercel's own `VERCEL` environment variable is present. Set it to `0` to opt a
deployment out, or to `1` to opt any other host in.

A boot migration that fails is **logged, not raised** — it prints
`Boot migration failed (...)` and the app carries on serving. Raising would
fail the module import and turn a partial breakage (some pages erroring on a
missing column) into a total one, including the pages you'd use to diagnose
it. So a failure here is quiet by design: if a schema change doesn't seem to
have landed, check the logs for that line, then apply it by hand — see
[7. Troubleshooting](#7-troubleshooting).

It handles all three states a database can be in:

| State | What happens |
|---|---|
| Brand-new database | Every migration runs from scratch |
| Already on migrations | Only outstanding migrations run |
| Created by the old `db.create_all()` (no `alembic_version`) | Stamped at the baseline revision first, so Alembic won't try to re-create existing tables, then anything newer is applied |

After changing a model, generate a migration and commit it alongside the code:

```bash
FLASK_APP=app.py flask db migrate -m "describe the change"
FLASK_APP=app.py flask db upgrade      # apply locally
```

Migrations are generated with `render_as_batch=True` so column changes work on
SQLite as well as Postgres.

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
| `MIGRATE_ON_BOOT` | on when `VERCEL` is set | Run migrations and seeding at import time, for hosts with no release phase. See [Database migrations](#database-migrations) |

For production: set a long random `SECRET_KEY`, keep `FLASK_DEBUG` unset/`0`, and change the seeded admin password.

`DATABASE_URL` accepts the `postgres://` form that most managed-database
providers hand out, as well as `postgresql://` — the app normalizes it, so the
connection string can be pasted in verbatim.

## Deployment runbook

**Live instance:** https://librarysystem-ng3s.onrender.com — Render appends a
random suffix to a service name when the plain one is taken, so the actual
host doesn't match `render.yaml`'s `name: library-system`. Check the service's
own page on the Render dashboard for the current URL rather than assuming it.

### 0. What this app needs from a host

One requirement drives everything below:

1. **A real database.** SQLite is a single file. It works locally, but on a
   host with an ephemeral filesystem it is wiped on every deploy and not shared
   between instances. Use managed Postgres in production — Render's own
   Postgres, [Neon](https://neon.tech), or any other `postgresql://` URL.

That's the only one. The uploaded organization logo and its generated icon set
are stored as bytes on the `organization_settings` row (see
`branding_images.py`'s module docstring), not as files on a mounted disk, so
there is no persistent-filesystem requirement to satisfy separately — whatever
already holds the database holds the logo too.

**This means the app now runs on both kinds of host:**

- **Container/VM hosts** (Render, Railway, Fly.io) — the two commands below,
  a long-running process, migrations run once at boot before traffic arrives.
- **Serverless platforms** (Vercel and similar) — zero config: Vercel's
  Flask preset detects the top-level `app` in `app.py` and runs it as a
  function per request. There is no boot hook to run migrations in, so
  they're applied as an explicit one-off step instead — see
  [1b. First deploy — Vercel + Neon](#1b-first-deploy--vercel--neon).

The two commands a container/VM host needs:

| | |
|---|---|
| **Build** | `pip install -r requirements.txt` |
| **Start** | `python -c "from app import init_db; init_db()" && gunicorn app:app --bind 0.0.0.0:$PORT --timeout 60` |

The start command migrates the database before gunicorn binds, so the schema is
current before the first request is served. The explicit `--bind 0.0.0.0:$PORT`
matters: gunicorn otherwise binds to `127.0.0.1`, which the host can't route to.

Worker count is deliberately not set. Gunicorn reads `WEB_CONCURRENCY`, which
hosts set from the instance's available CPU (Render does this automatically), so
leaving it off means the app scales with the instance instead of overriding it
with a hardcoded number that could exhaust memory on a small plan.

Hosts that read a `Procfile` (Railway, Fly, Heroku) can use the one in the repo
root instead — it splits the same work into a `release` and a `web` step.

---

### 1. First deploy — Render

The repo ships `render.yaml`, which declares the web service and the Postgres
database together.

**Blueprint (recommended).** Dashboard → **New → Blueprint** → pick this repo →
Apply. Then set `ADMIN_PASSWORD` in the service's Environment tab before the
first boot (see step 2). Everything else is already declared.

**Manual setup.** Dashboard → **New → Web Service** → pick this repo, then:

| Field | Value |
|---|---|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python -c "from app import init_db; init_db()" && gunicorn app:app --bind 0.0.0.0:$PORT --timeout 60` |
| Health Check Path | `/login` |

**Overwrite the Build Command Render pre-fills.** It detects `poetry.lock` and
suggests `poetry install`, which pulls in dev dependencies the production image
doesn't need. (It no longer *fails* — `package-mode = false` in
`pyproject.toml` handles that — but `pip install -r requirements.txt` is the
leaner build.)

Then, before deploying:

1. **New → Postgres.** Create the database, copy its **Internal Database URL**.
2. **Environment tab** — add:
   - `DATABASE_URL` — the Postgres URL from step 1. The `postgres://` form is
     fine; the app rewrites it to `postgresql://` at startup.
   - `SECRET_KEY` — a long random string. Generate one with
     `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
     **The app refuses to start in production without it.**
   - `FLASK_ENV` — `production`.
   - `ADMIN_PASSWORD` — the password for the seeded admin account.
   - `PYTHON_VERSION` — `3.12`.

No disk to configure — see [0](#0-what-this-app-needs-from-a-host).

---

### 1b. First deploy — Vercel + Neon

Vercel's Python runtime runs the same Flask app as a serverless function
rather than a long-running gunicorn process. No wrapper files are needed —
the Flask framework preset finds the top-level `app` in `app.py` on its own —
but three repo-level details exist specifically for its build, all already in
place: `pyproject.toml` carries a PEP 621 `[project]` table (Vercel resolves
dependencies with `uv`, which requires one and does not fall back to
`requirements.txt`), `[tool.uv] package = false` (the uv equivalent of
Poetry's `package-mode = false` — without it `uv sync` tries to build the app
itself as a wheel and fails), and `.python-version` pins `3.12` as
major.minor only (uv has no interpreter for an exact patch like `3.12.9`).

What changes operationally from the Render flow: there's no build-time disk to
worry about (see [0](#0-what-this-app-needs-from-a-host)). Migrations are *not*
one of the differences — Vercel has no release phase, so `app.py` runs
`init_db()` at import instead (see
[Database migrations](#database-migrations)). Both hosts migrate and seed
themselves on deploy.

> This was not always true. Until 2026-08-24 nothing on Vercel applied
> migrations at all, and this section told you to run them by hand. The step
> was easy to forget, and forgetting it took production down: migration
> `b7e2f4a91c36` added `user.onboarding_completed_at`, was never applied, and
> every `/login` POST returned 500 with `psycopg2.errors.UndefinedColumn`. The
> boot hook exists so that a missing migration is no longer one forgotten
> command away from an outage.

1. **Create the Neon project.** [neon.tech](https://neon.tech) → New Project.
   Copy the pooled connection string from the dashboard (starts
   `postgresql://` and already includes `?sslmode=require` — nothing to edit).

2. **Nothing to run.** The first request after deploying creates every table
   (`_apply_migrations()`'s brand-new-database case) and seeds the admin
   account — see [Database migrations](#database-migrations). Set
   `ADMIN_PASSWORD` in step 3 so that seed isn't `admin`/`admin`.

3. **Deploy.** `vercel link` once to connect the project, then set the
   environment variables Vercel needs (Project → Settings → Environment
   Variables, or `vercel env add <NAME>`):

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | the same Neon connection string |
   | `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` — refuses to start without it |
   | `FLASK_ENV` | `production` |
   | `ADMIN_PASSWORD` | the password to seed the admin account with |

   Then `vercel deploy --prod`.

   **Keep the Neon connection string somewhere you can get at it again.**
   Vercel stores `DATABASE_URL` as a *Sensitive* variable, which is write-only
   by design: `vercel env pull` returns the literal text `[SENSITIVE]`, and
   the dashboard won't reveal it either. The only place to recover it is the
   Neon console (your project → **Connection Details**).

4. **Every later schema change:** commit the migration with the code and push.
   The next deploy applies it on its first request. Nothing manual — see
   [4. Subsequent deploys](#4-subsequent-deploys).

---

### 2. First boot

The first start runs every migration and seeds one admin account:

- Username `admin`, password `$ADMIN_PASSWORD` (or `admin` if unset).

**Sign in and change that password immediately.** The seed only happens when no
admin exists, so it will not silently re-create or reset the account later.

### 3. Verify the deploy

```bash
curl -sf https://YOUR-APP.onrender.com/login   > /dev/null && echo "login OK"
curl -sf https://YOUR-APP.onrender.com/manifest.json | head -c 200
```

**Check the startup log for the database it actually connected to.** The
migration line names the backend:

- `Context impl PostgresqlImpl` — correct.
- `Context impl SQLiteImpl` — `DATABASE_URL` didn't take effect. The app will
  run perfectly and lose everything on the next deploy. Fix this before
  entering real data. Startup also prints an unmissable warning banner in this
  case.

Then in a browser:

- [ ] Sign in as admin
- [ ] **Admin → Settings** — set the organization name, upload a logo, pick a
      theme color, save
- [ ] Hard-refresh: the sidebar shows the logo and name, and the accent color
      changed
- [ ] Add a book, register a member account, borrow it
- [ ] On a phone: the bottom tab bar appears, and **Add to Home Screen** shows
      the uploaded logo as the app icon

### 4. Subsequent deploys

**Render:** push to `main`. The host rebuilds and re-runs the start command,
which applies any new migrations before serving. Nothing manual.

**Vercel:** push, or `vercel deploy --prod`. The first request after the
deploy applies any new migrations. Nothing manual.

Either host: after changing a model, generate the migration locally and commit
it with the code — see [Database migrations](#database-migrations). A deploy
whose migration file is missing will start fine and then fail at runtime on
the missing column, so treat the migration as part of the change, not a
follow-up. The boot hook can only apply migrations that were committed; it
can't invent one you forgot to generate.

### 5. Rollback

**Render:** **Deploys** tab → pick the last good deploy → **Redeploy**.

**Vercel:** **Deployments** tab → pick the last good one → **Promote to
Production** (or `vercel rollback`).

Either way, this rolls back *code*, not the *database*. Migrations don't
auto-revert: if the bad deploy added a column, the rollback leaves it in place,
which is harmless. If it *dropped* or rewrote one, restore the database from a
backup instead (Render Postgres keeps daily backups on paid plans; Neon keeps
point-in-time restore) and consider `flask db downgrade` locally against a
copy first to confirm the down-migration is correct.

### 6. Operations

**Open a shell** (Render → Shell tab). Vercel has no shell — run these
locally instead, with `DATABASE_URL` set to the Neon connection string from
the Neon console (Vercel won't give it back to you; see
[1b](#1b-first-deploy--vercel--neon)):

```bash
# Inspect migration state
FLASK_APP=app.py flask db current
FLASK_APP=app.py flask db history

# Reset a locked-out admin's password
python -c "
from app import app
from extensions import db
from models import User
with app.app_context():
    u = User.query.filter_by(username='admin').first()
    u.set_password('a-new-strong-password')
    db.session.commit()
    print('password updated')
"
```

**Locked out entirely** (no admin password, no shell). Register a normal
account through `/register` on the live site, then promote it in your
provider's SQL editor — Neon console → **SQL Editor**:

```sql
UPDATE "user" SET is_admin = true WHERE username = 'your-new-account';
```

The seed path won't help here: it only creates an admin when *no* admin row
exists, so it never resets or overwrites an account you've lost the password
to.

**Back up the database** (run locally, with the *External* database URL):

```bash
pg_dump "$EXTERNAL_DATABASE_URL" > backup-$(date +%F).sql
```

The uploaded logo lives in this same database (see
[0](#0-what-this-app-needs-from-a-host)), so there's nothing else to back up
separately.

**Free-tier caveat.** Render's free web services spin down after inactivity, so
the first request after an idle period takes ~30s. Free Postgres instances also
expire after 90 days. Fine for evaluation; move to a paid instance for real use.

### 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Deploy fails: `RuntimeError: SECRET_KEY environment variable must be set` | `FLASK_ENV=production` with no `SECRET_KEY` | Set `SECRET_KEY` in the environment |
| Deploy succeeds, host reports "no open ports detected" | gunicorn bound to `127.0.0.1` | Use the full start command, including `--bind 0.0.0.0:$PORT` |
| `Error: can't chdir to './app_dir'` (or any start command you don't recognise) | The Start Command field was left empty, so the host invented one | Paste the Start Command from the table above into the service's settings |
| `Can't load plugin: sqlalchemy.dialects:postgres` | Very old `DATABASE_URL` handling | Already handled — the app rewrites `postgres://`. Confirm you're on the current `main` |
| Build fails: `The current project could not be installed: No file/folder found for package library-system` | The host autodetected `poetry.lock` and ran a bare `poetry install`, which tries to install the app as a package | Already handled — `package-mode = false` in `pyproject.toml`. Confirm you're on current `main`. Setting the Build Command to `pip install -r requirements.txt` also avoids it |
| Build uses an unexpected Python version | No version pinned, so the host picks its default (Render currently defaults to 3.14) | Already handled — `.python-version` pins 3.12. `PYTHON_VERSION` in the environment overrides it |
| `ModuleNotFoundError: No module named 'psycopg2'` | Build didn't install requirements | Check the Build Command is `pip install -r requirements.txt` |
| `no such table` / `column ... does not exist` at runtime (e.g. every `/login` POST 500s) | A migration wasn't committed, or the boot migration failed and was logged rather than raised | Search the logs for `Boot migration failed`. If it's there, fix the cause and redeploy, or apply it by hand (below). If it isn't, the migration file was never generated or committed — generate and commit it. On Render, also confirm the `Procfile` `release:` step is intact |
| Boot migration needs applying by hand | The boot hook failed, or you're on a host with no release phase and `MIGRATE_ON_BOOT` off | `DATABASE_URL="<connection-string>" FLASK_APP=app.py flask db upgrade`. On Vercel the connection string must come from the Neon console — `vercel env pull` returns `[SENSITIVE]` for it |
| Sign-in appears to succeed but bounces back to `/login` | Cookie marked secure while served over plain HTTP | Serve over HTTPS (Render does this by default), or unset `SESSION_COOKIE_SECURE` for a non-TLS test host |
| Startup logs a `WARNING: running in production on SQLite` banner, or migrations log `Context impl SQLiteImpl` | `DATABASE_URL` isn't set, so the app is writing to a local file that the next deploy destroys | Attach a managed Postgres instance and set `DATABASE_URL`. Any data created in the meantime is lost on the next deploy |
| Data disappeared after a deploy | Same cause as above — the app was on SQLite, not Postgres | Set `DATABASE_URL` before putting real data in |

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
- **Frontend:** a self-contained design system — hand-written CSS
  and vanilla JS, inline SVG icons. **No CSS/JS frameworks and no CDN**, so the
  UI renders identically offline and on restricted networks.
- **Database:** SQLite (default) / PostgreSQL
- **Auth:** Werkzeug password hashing

## Interface

The interface is built on the department's own visual language — the accession
slip. A call number, an ISBN, and a due date are real identifying data, so they
are set in a monospace face and aligned in fixed columns rather than flowing
with the prose around them; a member's loan renders as a date-due card with a
stamped stub.

The brand palette doubles as the status system: **indigo** `#292168` for
identity and primary actions (and the navigation rail, the one large saturated
field in the product), **coral** `#f7636e` for overdue, **apricot** `#f9b78a`
for due soon, and **aqua** `#5dcbd1` for available/returned. Type is Fraunces
for display, Archivo for the interface, and IBM Plex Mono for data, all served
from `static/fonts` so nothing depends on a CDN. It ships with **light and dark appearance** — following the OS
by default, with a manual override in the account menu (remembered per browser).

| | |
|---|---|
| ![Member dashboard](docs/ui/member-dashboard-light.png) | ![Circulation, dark](docs/ui/admin-circulation-dark.png) |
| Member overview (light) | Circulation desk (dark) |

Design notes:

- **Colour** — the brand tints are too light to carry body text, so each has a
  darkened variant derived and checked with the same WCAG math as
  `theming.py`. Every foreground/background pair meets AA in both appearances.
- **Layout** — tables become stacked cards below 860px so row actions stay
  reachable on a phone; touch targets are 44px on coarse pointers.
- **Motion** — entering and exiting elements use one strong ease-out curve;
  hover lifts are gated behind `(hover: hover)` so they don't latch on touch.
  Under `prefers-reduced-motion` movement is dropped and the opacity and colour
  transitions are kept, since those aid comprehension without causing
  motion sickness.
- **Keyboard** — skip link, visible focus rings (light-on-indigo inside the
  rail), Escape closes menus and dialogs, and ⌘K / Ctrl-K jumps to search.

## What Changed (v3.5 — logo storage moved off the filesystem; Vercel + Neon)

- **The uploaded organization logo is now stored as bytes in the database**
  (`organization_settings.logo_data`), not as a file under
  `static/uploads/branding/`. `branding_images.py`'s module docstring has the
  full reasoning; the short version is that this app hit two hosts where "the
  app process has a persistent, writable disk" turned out not to hold — a
  Render disk that was declared in `render.yaml` but incompatible with the
  free plan it was paired with (persistent disks require a paid instance
  type, so it was never actually mounted), and Vercel's serverless functions,
  which have no persistent disk on any plan. A database column has no such
  dependency, and it fixes both at once rather than requiring a paid Render
  plan or a separate object-storage service.
- The six derived icons (favicon, apple-touch-icon, the manifest's
  `any`/`maskable` variants) are no longer pre-generated and written to disk
  either. They're rendered on request from the stored logo bytes by a new
  `/branding/*` route, so there's exactly one thing that can go stale (the
  logo row) instead of a set of files that could drift out of sync with it.
  Every response is cached hard (`Cache-Control: immutable`, one year) and
  invalidated by URL — a `?v=` stamp derived from the upload timestamp — the
  same pattern the app already used for ordinary static assets.
- `logo_upload.py` is replaced by `branding_images.py` (pure image
  validation/rendering, no filesystem I/O) and `routes/branding.py` (serves
  the bytes). `OrganizationSettings.logo_filename` is gone; `logo_ready` no
  longer has a "database and disk drifted apart" failure mode to guard
  against, because there's only one place the logo lives now.
- **`render.yaml`'s disk declaration is removed** — it's not just unnecessary
  now, it was never actually usable where it was declared (see above), which
  is the direct cause of an earlier problem where an uploaded logo would
  silently vanish on the next deploy.
- **Vercel support**, zero-config: the Flask preset detects `app.py`'s
  top-level `app` directly, so there are no wrapper files. `pyproject.toml`
  gained a PEP 621 `[project]` table and `[tool.uv] package = false` for
  Vercel's uv-based build, and `.python-version` is pinned as `3.12`
  (major.minor) rather than an exact patch. Since there's no host-provided
  hook to run migrations before traffic arrives the way Render's start
  command does, they're an explicit one-off step instead — see
  [1b. First deploy — Vercel + Neon](#1b-first-deploy--vercel--neon).
- `MAX_CONTENT_LENGTH` lowered from 5 MB to 4 MB, under Vercel's 4.5 MB hard
  limit on serverless function request bodies — the logo upload's own cap is
  2 MB regardless, so this only affects hosts where the platform limit
  applies and changes nothing for anyone else.

## What Changed (v3.4 — database migrations + deployment)

- **Flask-Migrate (Alembic).** Schema changes are now versioned. `init_db()`
  migrates to the latest revision on boot, so a deploy never needs a manual
  database step. A database created by the old `db.create_all()` is detected
  and stamped at the baseline revision rather than having Alembic try to
  re-create tables that already exist — existing deployments upgrade in place
  without losing data.
- **`Procfile`** with a `release` step (migrate) and a `web` step (gunicorn).
- **`postgres://` URLs are normalized** to `postgresql://`, so a managed
  provider's connection string can be pasted into `DATABASE_URL` as-is instead
  of failing at startup.
- Fixed a latent break in the generated `migrations/env.py`: it called
  `db.get_engine()`, removed in Flask-SQLAlchemy 3.2, which would have turned a
  routine dependency bump into a failed deploy.
- **`requirements.txt`** pinned from `poetry.lock`, since most hosts build with
  `pip install -r requirements.txt` out of the box. `pyproject.toml` remains
  the source of truth for local development.
- **`render.yaml`** blueprint declaring the web service, Postgres, and the
  persistent disk for logo uploads together.
- **A deployment runbook** in the README: first deploy, first boot, a
  post-deploy verification checklist, subsequent deploys, rollback (and what
  rollback does *not* undo), routine operations, and a troubleshooting table.

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

## What Changed (v3.0 — interface rebuild)

- **New design system.** Bootstrap and its CDN are gone, replaced by a
  self-contained stylesheet, vanilla JS, and inline SVG icons.
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
- **Interaction**: `confirm()` replaced by a dialog naming the exact
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