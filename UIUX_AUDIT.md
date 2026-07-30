# UI/UX Audit — Library Management System

Audit of the **current merged `main`** (commit `368d319`), after the earlier codebase audit fixes landed.
Scope: interface, interaction, content, and accessibility. (Backend/security findings were covered in `AUDIT.md`.)

## Method

This audit was run against the live application, not just the templates:

1. Seeded a realistic dataset — 12 catalogue titles, 4 members, and loans spanning **overdue, due-today, due-soon, comfortable, and returned** states, plus a fully-borrowed title with an active reservation.
2. Drove the app with Playwright at **1280×900 (desktop)** and **390×844 (mobile)**, capturing every member and admin screen.
3. Ran DOM probes on each rendered page for landmarks, heading order, accessible names, label association, table semantics, tap-target size, and horizontal overflow.
4. Computed **actual WCAG contrast ratios** from rendered pixels (resolving real effective background colours), not from the stylesheet.

Findings below are grouped by severity. Ratios and duplicated values are measured, not estimated.

Severity: 🔴 Critical · 🟠 High · 🟡 Medium · 🔵 Polish

**Evidence** (captured during this audit, in `docs/uiux-audit/`):

| File | Shows |
|---|---|
| `member-dashboard-date-contradiction.png` | §1 — "7 day(s) overdue" and "8 day(s) overdue" for the same book on one screen |
| `mobile-admin-books-actions-offscreen.png` | §4 — books table at 390px with Category / Available / Actions cut off |
| `unstyled-fallback.png` | §14 — how every page degrades when the CDN assets don't load |

---

## 1. 🔴 The app reports two different due-date numbers for the same book, on the same page

The single most damaging finding, because it undermines trust in the one number this system exists to communicate.

On the member dashboard, the overdue banner and the loan list disagree:

| Book | Overdue banner | Loan list below it |
|---|---|---|
| Argonauts of the Western Pacific | "**7** day(s) overdue" | "**8** day(s) overdue" |
| The Interpretation of Cultures | "**0** day(s) overdue" | "**1** day(s) overdue" |

**Cause.** The two code paths subtract in opposite directions, and Python's `timedelta.days` floors toward negative infinity:

- `templates/member/dashboard.html:18` → `(now - item.due_date).days` → `7`
- `templates/member/dashboard.html:71` → `(b.due_date - now).days` then `|abs` → `8`

For a loan 7 days and 6 hours overdue, `(now-due).days == 7` but `abs((due-now).days) == 8`. Verified directly:

```
overdue by 7d6h:  (now-due).days = 7        abs((due-now).days) = 8
overdue by 1h:    (now-due).days = 0        abs((due-now).days) = 1
due in 1d18h:     (due-now).days = 1   ← displayed as "1 day(s) left"
```

**Three distinct user-facing defects fall out of this:**

1. **Contradiction.** The same page states two different overdue counts for one loan.
2. **"0 day(s) overdue"** is meaningless copy shown to a member whose book *is* overdue.
3. **"Days left" is short by one.** A book due in 1 day 18 hours reads "1 day(s) left". Members are consistently told they have less time than they do — and a book due tomorrow evening can read "0 day(s) left" today.

The same mixed conventions appear in `templates/member/history.html:45` vs `:50` (both directions **in one file**) and `templates/admin/borrowing_history.html:60`.

**Fix.** Compare *calendar dates*, not timestamps, in one shared helper — due dates are day-granular, so the hour component should never influence the count:

```python
days_left = (borrowing.due_date.date() - date.today()).days
```

Then express state from that single value: `> 0` → "Due in N days", `== 0` → "Due today", `< 0` → "N days overdue". Expose it as a model property (`Borrowing.days_remaining`) and use it everywhere so the two directions can't drift again.

---

## 2. 🔴 Colour contrast fails WCAG AA across the entire status vocabulary

Measured from rendered pixels. The status colours that carry the system's most important meaning are the least legible.

| Element | Where | Measured | Required |
|---|---|---|---|
| `text-warning` on white — "1 day(s) left", "All borrowed — reserve to queue", reservation expiry | dashboard, search, reservations | **1.63:1** | 4.5:1 |
| `.badge.bg-info` white-on-cyan — every ISBN badge, "Reserved" badge | search, reservations | **1.96:1** | 4.5:1 |
| `text-info` — "My Borrowing History", "Manage Members" buttons | dashboards | **1.96:1** | 4.5:1 |
| Overdue stat number (40px `text-warning`) | dashboards | **1.63:1** | 3.0:1 |
| Reservations stat number (40px `text-info`) | dashboards | **1.96:1** | 3.0:1 |
| `text-danger` on the pink overdue row | dashboard, admin history | **3.39:1** | 4.5:1 |
| Book title links on overdue rows | admin history | **3.37:1** | 4.5:1 |
| `btn-outline-primary` / `btn-outline-success` on `#f8f9fa` | admin history filters | **4.27 / 4.30:1** | 4.5:1 |

`text-warning` at **1.63:1** is the headline: amber `#ffc107` on white is close to invisible for low-vision users, and it is precisely the colour used for "due soon" — a warning nobody can read is not a warning. The large stat numbers fail even the relaxed 3:1 large-text threshold.

**Fix.** Bootstrap's raw `warning`/`info` palette is designed for *fills*, not text on white. Either:
- use the darker text variants (`.text-warning-emphasis`, `.text-info-emphasis` in BS 5.3) for text, and
- switch `.badge.bg-info` to `.text-bg-info` (which pairs dark text with the cyan fill), or define project tokens: amber `#946200`, cyan `#087990`, both ≥4.5:1 on white.

For the overdue rows, darken the danger text or lighten the row tint so the pair clears 4.5:1.

---

## 3. 🔴 Form fields are visually labelled but not programmatically labelled

Every `<label>` in the app is a bare `<label class="form-label">` with no `for`, and the inputs have `name` but no `id`. Sighted users see labels; screen readers announce an unlabelled edit field.

Affected (measured on the live DOM):
- **Add-book form** — all 8 fields: `title`, `author`, `isbn`, `category`, `quantity`, `publisher`, `publication_year`, `description` (`templates/admin/books.html:24+`)
- **Edit-book form** — same pattern (`templates/admin/edit_book.html`)
- **Member search** — the type `<select>` and query input (`templates/member/search.html:16,24`)
- **Admin search** — books and members search inputs

Login and register are the only correctly-associated forms (they use `id`/`for`).

This is a WCAG 1.3.1 / 4.1.2 failure and the highest-value accessibility fix available, because it is purely mechanical.

**Fix.** Add `id` to each input and `for` to each label. (Placeholders are not labels — the search inputs rely on placeholder text that disappears on focus.)

---

## 4. 🔴 Librarians lose the Edit and Delete actions on mobile

At 390px the books table renders **Title, Author, ISBN** and nothing more. Category, Available, and the entire **Actions** column sit outside the viewport inside `.table-responsive`'s horizontal scroll — with no scrollbar, gradient, or any other affordance signalling that content continues.

The page itself does not overflow (measured: 0px document overflow), so the user gets no cue at all. A librarian on a phone or a narrow tablet simply cannot reach the primary actions of the books screen.

The same applies to the members table (View/Delete) and borrowing history (the **Return** button — the single most-used librarian action).

Row height compounds it: the description snippet and wrapped titles push the 12-row books table to ~2,900px on mobile.

**Fix.** Below `md`, switch tables to a stacked card layout (title + key facts + action buttons per card) rather than a scrolling grid. If the table is kept, pin the Actions column and add a visible scroll affordance. Drop the description snippet from the mobile table — it is the largest contributor to row height and the least scannable.

---

## 5. 🟠 The "Overdue Items" drill-down doesn't filter to overdue

On the admin dashboard, the **Active Loans** and **Overdue Items** cards both link to the identical URL:

- `templates/admin/dashboard.html:33` → `borrowing_history(status='active')`
- `templates/admin/dashboard.html:44` → `borrowing_history(status='active')`

Clicking "View all" under a red-flagged count of overdue items lands the librarian on *all* active loans, unfiltered. The number that prompted the click cannot be isolated.

Borrowing history also has no **Overdue** filter chip at all — only All / Active / Returned — even though overdue is the one status that demands action.

**Fix.** Add `status=overdue` handling to the route (`status == 'active' AND due_date < now`), add the matching filter chip, and point the dashboard card at it.

---

## 6. 🟠 Search results are blind to what the member already has

The catalogue offers actions that contradict the member's own state:

- A book the member **currently has borrowed** still shows an enabled **Borrow** button (e.g. *The Interpretation of Cultures*, 1/2 available, already on loan to the viewer).
- A fully-borrowed book the member already **holds a copy of** shows **Reserve** (e.g. *The Gift*).

The server now rejects both correctly — that was fixed in the previous pass — but the interface still *invites* the action and only reveals the problem after a round-trip and an error flash. Offering an action that is guaranteed to fail is a preventable dead end.

**Fix.** Pass the viewer's active borrowing and reservation book-ids into the search context and render state-aware affordances: "**You have this — due Jul 31**", "**Reserved — expires Aug 2**", with the button suppressed or disabled.

---

## 7. 🟠 The search-type dropdown contradicts its own placeholder

The type selector defaults to **Title**, while the input beside it reads *"Search by title, author, ISBN, or category…"* (`templates/member/search.html:24`).

The placeholder promises a multi-field search the control does not perform. A member typing "Geertz" with the default selection gets **zero results** for a book the library owns — the single most likely first interaction on this page, and it fails silently.

**Fix.** Add an **"All fields"** option, make it the default (matching the admin search, which already searches all four fields at once), and make the placeholder track the selected type.

---

## 8. 🟠 Heading structure is decorative rather than semantic

Measured heading order on the member dashboard:

```
H2: Welcome, jdelacruz!
H5: Overdue Books!
H1: 4          ← stat number
H1: 2          ← stat number
H1: 1          ← stat number
H5: Currently Borrowed …
```

The three `<h1>` elements are the **stat digits** (`templates/member/dashboard.html:30,38,46`), because `display-6` was applied to `<h1>`. The admin dashboard has four. A screen-reader user navigating by heading hears "heading level 1: 4".

Meanwhile **every other page has no `<h1>` at all** (login, register, search, history, reservations, all admin list pages — page titles are `<h2>`), and levels skip from `h2` to `h5` throughout.

**Fix.** One `<h1>` per page carrying the page title; render stat numbers as `<p class="display-6">` or `<span>`; use `h2`/`h3` for card headers instead of `h5`.

---

## 9. 🟠 Missing landmarks, skip link, and an unnamed menu button

Measured on **every** page:

- **No `<main>` landmark** — nothing to jump to; assistive tech users traverse the full nav on each page load.
- **No skip link** — the same cost for keyboard users.
- **The mobile menu button has no accessible name** (`templates/base.html:17`): `<button class="navbar-toggler">` wraps only a decorative `<span>`. It announces as "button". On mobile this is the *only* navigation control.
- **All table headers lack `scope`** — 5–7 `<th>` per table across all six tables, so cell/header association is left to heuristics.

**Fix.** Wrap the content block in `<main id="main">`, add a `visually-hidden-focusable` skip link, add `aria-label="Toggle navigation"` to the toggler, and add `scope="col"` to every `<th>`. All are one-line changes.

---

## 10. 🟡 Severity colours are inconsistent between components

Overdue is encoded three different ways on one screen:

- Dashboard **banner** — red (`alert-danger`)
- Dashboard **stat card** — amber (`border-warning` / `text-warning`)
- Dashboard **loan row** — red (`list-group-item-danger`)

The stat card is the element users scan first, and it is the one that downgrades overdue to a warning. Reservations use `info` (cyan) in the stat card but `warning` (amber) for the expiry text on the reservations page.

**Fix.** Fix the vocabulary — overdue = danger, due-soon = warning, informational = neutral — and apply it identically across banner, stat, badge, and row.

---

## 11. 🟡 Members can see problems but can do nothing about them

The member dashboard reports overdue books and urges "please return them to avoid penalties", but the member interface offers **no action whatsoever** on an existing loan: no renew, no return request, no "how do I return this", no contact route. Every loan is a read-only row until a librarian acts.

Likewise, once a book is reserved there is no queue-position indicator ("you are #2"), so the reservations page cannot answer the only question a member has.

**Fix.** At minimum, add renewal (with a policy check for overdue/reserved titles) — the highest-value missing member feature. Short of that, replace the bare warning with actionable instructions.

> **Update:** Self-service renewal (with exactly this policy check — blocked when overdue, at the renewal limit, or reserved by another member) shipped in v3.1. The queue-position indicator on the reservations page remains open.

---

## 12. 🟡 Navigation from the history table is inconsistent and surprising

- **Book titles link to the *edit* form** (`templates/admin/borrowing_history.html:50`). Clicking a title in an informational log opens an editable metadata form — one stray keystroke away from mutating the catalogue.
- **Member names are not links at all** (`:54`), even though `admin.member_detail` exists. The natural workflow — "*lbautista* is 7 days overdue, show me their record" — requires leaving the page and searching Members by hand.

**Fix.** Link member names to `member_detail`; point book titles at a read-only book detail view (or remove the link) rather than the edit form.

---

## 13. 🟡 Dashboard panels duplicate content and waste the prime slot

- **Quick Links** reproduces the top navigation exactly (Search / History / Reservations) — three links to destinations already one click away in the navbar, occupying the top of the right column.
- **Recent Activity** lists the same books already shown in *Currently Borrowed* (it queries all borrowings, so open loans dominate), making it a near-duplicate of the panel beside it.

Net effect: roughly a third of the dashboard restates what the rest already says, and the right column still bottoms out in empty space.

**Fix.** Drop Quick Links. Restrict Recent Activity to *completed* events (returns), or replace both with something actionable — reservations ready for pickup, or recommendations.

---

## 14. 🔵 Front-end assets are CDN-only, with no fallback and no integrity check

`templates/base.html:7,8,123` load Bootstrap CSS, Bootstrap Icons, and Bootstrap JS from `cdn.jsdelivr.net` with **no local fallback and no `integrity`/SRI attribute**.

If those requests fail, the application degrades to unstyled HTML: the navbar becomes a bullet list, stat cards become bare digits, every icon disappears, and dismissible alerts and the mobile menu (Bootstrap JS) stop working entirely. I captured this state directly — see `docs/uiux-audit/unstyled-fallback.png`.

To be precise about the evidence: the CDN was blocked by *my* sandbox's egress proxy, not observed failing in production. The screenshot demonstrates the **degradation mode**, not an outage. The finding stands on the dependency itself: a campus network with restrictive egress, an offline reading room, or a CDN incident produces exactly that page, and SRI is absent regardless.

**Fix.** Vendor Bootstrap into `static/vendor/` (it is ~60 KB gzipped and already a pinned version), or keep the CDN and add `integrity` + `crossorigin` plus a local fallback. Self-hosting also removes a third-party request from every page load.

---

## 15. 🔵 Smaller items

- **Tap targets.** `btn-sm` action buttons render ~31px tall — below the 44px touch guidance. Measured 12 undersized targets on member search and 22 on admin history.
- **No result count or sort on member search.** The catalogue shows neither "showing X of Y" nor any sort/filter control (availability, category); admin lists show a total badge but members get nothing.
- **The critical overdue banner is dismissible** and, being regenerated per request, reappears on every navigation — training users to dismiss it reflexively.
- **Tables have no `<caption>`**, so they are unannounced in screen-reader table lists.
- **ISBN is given badge prominence** equal to category on every search card, competing with the title for attention despite being the least useful field to a browsing member.
- **Date formats are good** — `Jul 26, 2026` is unambiguous and used consistently. Worth preserving.

---

## What works well

Genuinely solid, and worth protecting through any redesign:

- **Status is never colour-only.** Overdue rows carry a badge, a text label, *and* a row tint — so the contrast failures above degrade legibility, not comprehension.
- **Empty states are excellent** — every list has a purpose-built empty state with an icon, an explanation, and a call to action, including the reservations page explaining what reservations are *for*.
- **The layout is coherent and predictable.** Card-based structure, consistent page headers, and a stable navbar make the two roles feel like one product.
- **Zero horizontal page overflow at 390px** — the responsive grid itself is sound; the table issue in §4 is contained scroll, not a broken layout.
- **Destructive actions are consistently confirmed**, and admin lists are paginated with a visible total.

---

## Priority order

1. **§1 due-date arithmetic** — one shared date-based helper. Corrects three visible defects and restores trust in the core number.
2. **§3 label association + §9 landmarks/skip link/toggler name + `th scope`** — mechanical, one-line fixes; the largest accessibility gain per unit of effort.
3. **§2 contrast tokens** — a palette change in one stylesheet, fixing every listed failure at once.
4. **§4 mobile tables** — restores librarian actions on small screens.
5. **§5 overdue filter + §6 state-aware search + §7 search default** — the three highest-value interaction corrections.
6. **§8 heading semantics, §10 colour vocabulary, §12 history links** — consistency pass.
7. **§11 renewals, §13 dashboard rework, §14 vendored assets** — larger changes, worth scheduling deliberately.
