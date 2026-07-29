# Codebase & UI/UX Audit — Library Management System

Audit of the Flask library system (branch `claude/codebase-uiux-audit-kclrd2`, based on commit `14144fa`).
Findings marked **Confirmed** were reproduced by running the app against an in-memory database and driving it with Flask's test client. The rest are read-review findings.

Severity legend: 🔴 Critical (crash / security) · 🟠 High · 🟡 Medium · 🔵 Low / polish.

---

## 1. Crashes (HTTP 500) — Confirmed

### 1.1 🔴 "My Reservations" page crashes for every member
- **Where:** `templates/member/reservations.html:28` → `{% set days_left = (reservation.expiration_date - now()).days %}`
- **Cause:** The template calls `now()` as a function, but the `reservations()` route (`routes/member.py:130`) does not pass `now`, and there is no `now` context processor. Jinja raises `UndefinedError: 'now' is undefined`.
- **Impact:** Any member with at least one active reservation who opens the "Reservations" nav link gets a 500. This is a core member feature and it is completely broken.
- **Note the inconsistency:** every other template receives `now` as a *variable* (e.g. `member/dashboard.html`, `admin/borrowing_history.html`). This one file uses `now()` as a call.
- **Fix options:** pass `now=datetime.utcnow()` from the route (matching the rest of the app), or register a global `@app.context_processor` that returns `{'now': datetime.utcnow}` and call it consistently everywhere.

### 1.2 🔴 Deleting a book that has *returned* borrowings crashes and breaks the session
- **Where:** `routes/admin.py:124` `delete_book()`
- **Cause:** The guard only blocks deletion when there are **active** borrowings (`status='active'`). Books with historical (returned) borrowings still have `Borrowing` rows pointing at them. On `db.session.delete(book)`, SQLAlchemy tries to NULL `borrowing.book_id`, which is `nullable=False` → `IntegrityError: NOT NULL constraint failed: borrowing.book_id` → 500. The same applies to `Reservation` rows.
- **Impact:** Librarians cannot delete any book that has ever been borrowed and returned — the operation 500s and leaves the DB session in a failed state.
- **Fix:** either block deletion when *any* borrowing/reservation history exists (and offer an "archive/deactivate" flag instead), or configure cascade delete on the relationships (`cascade='all, delete-orphan'` on the backref / `ondelete='CASCADE'` on the FK), or reassign history before delete. Recommendation: add an `is_active`/archived flag rather than hard-deleting catalogue records.

### 1.3 🔴 Same crash on member deletion (read-review, same root cause)
- **Where:** `routes/admin.py:185` `delete_member()`
- **Cause:** Identical pattern — only **active** borrowings block the delete. A member with returned-borrowing history will hit the same `NOT NULL constraint failed: borrowing.book_id`/`user_id` on delete.
- **Fix:** same as 1.2 (cascade or archive, not hard delete).

### 1.4 🔴 Editing a book to a duplicate ISBN crashes
- **Where:** `routes/admin.py:102` `edit_book()`
- **Cause:** `add_book()` checks for an existing ISBN before insert, but `edit_book()` does not. Saving an edit whose ISBN collides with another book violates the `UNIQUE` constraint → `IntegrityError: UNIQUE constraint failed: book.isbn` → 500.
- **Impact:** A simple typo during an edit produces a server error instead of a friendly validation message.
- **Fix:** re-run the uniqueness check in `edit_book` (excluding the current book id) and flash a warning on conflict.

---

## 2. Data integrity & business logic

### 2.1 🟠 Race condition on `available_quantity`
- **Where:** `routes/member.py:67` `borrow_book()` (and the reservation-fulfilment path in `admin.py:238`).
- **Cause:** Availability is a read-modify-write: `if book.is_available(): ... book.available_quantity -= 1`. Two concurrent requests for the last copy can both pass the check and both decrement → negative availability / over-lending. There is no row lock or atomic conditional update.
- **Fix:** perform an atomic guarded update (`UPDATE book SET available_quantity = available_quantity - 1 WHERE id = :id AND available_quantity > 0`) and check the affected-row count, or `SELECT ... FOR UPDATE` inside the transaction.

### 2.2 🟡 A member can borrow multiple copies of the same title — Confirmed
- **Where:** `routes/member.py:67` `borrow_book()`
- **Observed:** issuing two borrow requests for the same book id created **two** active borrowings for one member.
- **Cause:** No check for an existing active borrowing of the same book by the same user, and no overall per-member borrowing cap (only a gate that blocks borrowing when the member has ≥3 *overdue* items).
- **Fix:** reject a second active borrowing of the same book, and consider a total concurrent-loan limit.

### 2.3 🟡 `'overdue'` status is declared but never persisted
- **Where:** `models.py:72` (`status` comment lists `active, returned, overdue`) and README.
- **Reality:** Code only ever writes `'active'` and `'returned'`. Overdue is always computed on the fly from `due_date < now`. Not a bug, but the schema/README imply a state that never exists, which is misleading for future maintainers and for any query filtering on `status='overdue'`.
- **Fix:** drop `'overdue'` from the documented status set, or add a job that actually sets it.

### 2.4 🟡 `check_reservations` fulfils at most one reservation per book per run
- **Where:** `routes/admin.py:238` `check_reservations()`
- **Cause:** For each available book it fulfils only `get_active_reservation(book.id)` (the single oldest) and decrements once. A book that becomes available with quantity 3 and a queue of 3 will only clear one per click.
- **Fix:** loop while `available_quantity > 0` and reservations remain. Also note the `db.session.commit()` inside the per-book loop is chatty; batch it.

### 2.5 🔵 "We'll notify you" is never true
- **Where:** `templates/member/reservations.html:48` and `index.html` copy promise notification when a reserved copy frees up. There is no email/notification mechanism — fulfilment silently converts the reservation into a borrowing.
- **Fix:** either implement notification or soften the copy.

---

## 3. Security

### 3.1 🔴 `debug=True` is used in the deployed run command
- **Where:** `app.py:54` (`app.run(..., debug=True)`) and `.replit` `[deployment] run = ["sh","-c","python app.py"]`.
- **Impact:** The deployment target runs `python app.py`, which enables the Werkzeug interactive debugger. On any unhandled exception (see all the 500s above), an attacker gets an interactive Python console = remote code execution, plus full tracebacks/source disclosure.
- **Fix:** never run `debug=True` in deployment. Serve via a WSGI server (gunicorn) and gate debug behind an env var (`debug=os.environ.get('FLASK_DEBUG')=='1'`).

### 3.2 🟠 No CSRF protection on any state-changing form
- **Where:** every POST form — login, register, borrow, reserve, cancel, return, add/edit/delete book, delete member.
- **Cause:** Flask-WTF / CSRF tokens are not used. A malicious page can auto-submit e.g. `/admin/books/<id>/delete` or `/borrow/<id>` against a logged-in user.
- **Fix:** add Flask-WTF `CSRFProtect` and include `{{ csrf_token() }}` in every form (or use SameSite=strict cookies as a partial mitigation, but CSRF tokens are the real fix).

### 3.3 🟡 Login `next` redirect check is weak (open-redirect surface) — Confirmed
- **Where:** `routes/auth.py:27-32`
- **Cause:** It only checks `urlparse(next_page).netloc != ''`. A value like `next=https:/evil.com` has an empty netloc, so it passes and the app redirects to `https:///evil.com`. Scheme-relative and backslash tricks are not filtered.
- **Fix:** accept `next` only when it is a same-site relative path — e.g. require `url.scheme == '' and url.netloc == '' and next_page.startswith('/')` and reject `//`/`/\` prefixes; or use Werkzeug's `url_has_allowed_host_and_scheme`.

### 3.4 🟡 Weak default credentials & no password policy
- **Where:** `app.py:40-49` seeds `admin`/`admin`; `routes/auth.py:46` register accepts any non-empty password (single character allowed, not stripped).
- **Fix:** force an admin password change on first login (or read the seed password from env), and enforce a minimum password length.

### 3.5 🟡 `SECRET_KEY` regenerates on every process start when unset
- **Where:** `config.py:4-5` — falls back to `os.urandom(32).hex()` per process.
- **Impact:** Under multiple workers (gunicorn) each worker signs sessions with a different key, so users are randomly logged out; every restart invalidates all sessions. Silent misconfiguration in production.
- **Fix:** require `SECRET_KEY` in non-dev environments and fail fast if missing.

### 3.6 🔵 No rate limiting / lockout on login → brute-forceable
- **Fix:** add Flask-Limiter on the login route.

### 3.7 🔵 Email uniqueness is case-sensitive
- **Where:** `routes/auth.py:60` — `a@x.com` and `A@x.com` are treated as distinct accounts. Normalise email to lowercase before storing/checking.

---

## 4. Code quality & architecture

### 4.1 🟡 No database migrations
Schema is created via `db.create_all()` only. Adding/altering columns on an existing DB will not migrate. Introduce Alembic / Flask-Migrate.

### 4.2 🟡 N+1 queries on the admin members list
- **Where:** `templates/admin/members.html:49,57` call `member.active_borrowings` and `member.overdue_borrowings`, each a separate `COUNT` query, for every one of up to 20 rows → ~40 queries per page load.
- **Fix:** compute the counts with a single grouped aggregate query and pass a dict to the template.

### 4.3 🔵 No automated tests
There is no test suite. The four 500s above would all be caught by a handful of route smoke tests. Add `pytest` + Flask test-client tests covering each route and the borrow/return/reserve flows.

### 4.4 🔵 `init_db()` only runs under `python app.py`
Table creation and admin seeding live in the `__main__` block (`app.py:52`). This happens to work because deployment also runs `python app.py`, but it's fragile — a WSGI server importing `app` would start with no tables. Move seeding into an explicit CLI command / factory step.

### 4.5 🔵 Minor: broad `try`-free commits
Routes call `db.session.commit()` with no `try/except` + `rollback`, so the first integrity error (see §1) leaves the session unusable for the rest of the request. Wrap writes and roll back on failure.

---

## 5. UI / UX

### 5.1 🔴 Broken "Reservations" nav destination
Covered in §1.1 — the member "Reservations" link 500s. From a UX standpoint this is the most visible defect: a primary nav item leads to an error page.

### 5.2 🟠 Member search returns the entire catalogue unpaginated
- **Where:** `routes/member.py:57` — with no query, `Book.query.order_by(Book.title).all()` loads and renders **every** book as a card. Admin lists are paginated (20–30/page) but member search is not.
- **Impact:** On a real catalogue this is a slow page and a huge DOM. Add pagination (and ideally a sensible default like "recently added" rather than everything).

### 5.3 🟡 Add-book validation loses user input and never re-opens the form
- **Where:** `templates/admin/books.html:14` references `{% if form_errors %}show{% endif %}`, but no route ever passes `form_errors`, so the collapsible add-book form never auto-expands after a validation failure. Errors flash at the top while the form collapses and discards everything the librarian typed (add_book redirects on error — `admin.py:82,87`).
- **Fix:** re-render the page with the submitted values and `form_errors` set (or keep the form open and repopulate), instead of redirecting.

### 5.4 🟡 Icon-only action buttons are inaccessible
- **Where:** edit/delete/view buttons in `admin/books.html`, `admin/members.html` (e.g. `<button><i class="bi bi-trash"></i></button>`) have no text and no `aria-label`. Screen readers announce an empty button.
- **Fix:** add `aria-label="Delete book"` / `title="Delete"` etc., or visually-hidden text.

### 5.5 🟡 Flash messages (including errors) auto-dismiss after 6 seconds
- **Where:** `static/js/common.js:4-10` closes every `.alert-dismissible` after 6s.
- **Impact:** Important error/warning messages vanish before a slower reader or screen-reader user can consume them. Also the alert container has `role="alert"` per-message (good) but the auto-dismiss undermines it.
- **Fix:** auto-dismiss only success/info; keep warning/danger until dismissed.

### 5.6 🔵 Destructive confirmations use native `confirm()`
Works, but unstyled and easy to bypass if JS is disabled (the POST still fires server-side, which is fine — but there's no server-side "are you sure" step). Acceptable for now; a styled modal would be nicer.

### 5.7 🔵 Reserve/borrow card footer always shows "Due in 14 days"
- **Where:** `templates/member/search.html:91` shows "Due in 14 days" in the footer even when the visible action is **Reserve** or **Unavailable**, which is misleading. Show it only for the Borrow action.

### 5.8 🔵 Assorted polish
- Tables have no `scope="col"` on headers and no `<caption>` (minor a11y).
- No empty-`SECRET_KEY`/DB-health surfacing to the user; all failures are raw 500s (see §3.1). A custom 404/500 error page would improve both UX and security (no tracebacks).
- The stat cards and colour-coded badges are clear and consistent — this part of the UI is well done.

---

## 6. What's already good
- Clean blueprint separation (`auth` / `admin` / `member`) and sensible models with helper properties.
- Passwords are hashed with Werkzeug; admin area is guarded by a `before_request` role check.
- Search uses GET (bookmarkable), tables are paginated on the admin side, and destructive actions have confirmation prompts.
- Consistent Bootstrap 5 layout, good use of empty states, colour-coded due/overdue indicators, and a print stylesheet.

---

## 7. Suggested priority order
1. Fix the four confirmed 500s (§1.1–1.4) — these are user-facing breakage.
2. Turn off `debug=True` in deployment and require `SECRET_KEY` (§3.1, §3.5).
3. Add CSRF protection (§3.2).
4. Fix the availability race and duplicate-borrow gap (§2.1, §2.2).
5. Paginate member search; keep error flashes; label icon buttons (§5.2, §5.5, §5.4).
6. Add a minimal pytest smoke suite so these don't regress (§4.3).
