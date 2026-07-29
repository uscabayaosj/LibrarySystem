# Library Management System

A Flask-based library management system with separate **Librarian (Admin)** and **Borrower (Member)** dashboards. Supports book cataloguing, borrowing with due-date tracking, returns, reservations, and member management.

## Features

### 👤 For Members (Borrowers)
- **Search & Browse** — Find books by title, author, ISBN, or category
- **Borrow Books** — 14-day loan period with automatic due-date tracking
- **Reserve Books** — Queue for books when all copies are borrowed (3-day hold)
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
- **Status Filters** — Filter borrowing history by active/returned
- **Colour-Coded Alerts** — Overdue items highlighted in red, due-soon in yellow
- **Confirmation Dialogs** — Destructive actions (delete, cancel reservation) require confirmation
- **Flash Messages** — Clear success/warning/danger/info feedback with auto-dismiss
- **Responsive Design** — Works on desktop and mobile via Bootstrap 5
- **Bootstrap Icons** — Intuitive iconography throughout

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

## Database Schema

| Table | Key Columns |
|-------|-------------|
| **User** | id, username, email, password_hash, is_admin, phone, member_since |
| **Book** | id, title, author, isbn, category, publisher, publication_year, description, quantity, available_quantity |
| **Borrowing** | id, user_id, book_id, borrow_date, due_date, return_date, status (active/returned) |
| **Reservation** | id, user_id, book_id, reservation_date, expiration_date, status (active/fulfilled/expired/cancelled) |

## Tech Stack

- **Backend:** Flask 3.x, Flask-SQLAlchemy, Flask-Login
- **Frontend:** Bootstrap 5, Bootstrap Icons
- **Database:** SQLite (default) / PostgreSQL
- **Auth:** Werkzeug password hashing

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