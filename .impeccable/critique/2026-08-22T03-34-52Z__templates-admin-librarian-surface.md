---
target: templates/admin (librarian surface)
total_score: 25
max_score: 36
na_heuristics: 10
p0_count: 0
p1_count: 2
timestamp: 2026-08-22T03-34-52Z
slug: templates-admin-librarian-surface
---
Method: dual-agent (A: admin-design-review · B: admin-detector-evidence)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Confirmation sheets name the record and flash messages exist, but no form submit gives a pending/disabled state — double-click risk on Add Book/Delete/Check In. |
| 2 | Match Between System and Real World | 4 | Librarian vocabulary throughout ("Circulation," "Check In," mono ISBN/call-number treatment); no generic tech jargon. |
| 3 | User Control and Freedom | 2 | Add Book has no Cancel (Edit Book does); no undo after delete, only a confirm-sheet gate. |
| 4 | Consistency and Standards | 3 | Row-action patterns mostly consistent, but delete is icon-only on Members list vs. a full labeled `btn-block` on Member Detail for the identical action. |
| 5 | Error Prevention | 3 | Confirm sheets name the record; but Quantity can be edited below `available_quantity` with no guardrail — a real circulation-truth violation risk (PRODUCT.md Principle #1). |
| 6 | Recognition Rather Than Recall | 3 | Icons paired with text almost everywhere except row-action icons, which rely on `title`/`aria-label` with no visible label. |
| 7 | Flexibility and Efficiency of Use | 1 | No bulk actions anywhere — check-in, delete, and add are strictly one-row-at-a-time despite the desk's real job being batches of returns/new titles. |
| 8 | Aesthetic and Minimalist Design | 4 (design) / evidence-flagged | Clean, purposeful, color reserved for meaning. Detector found a hairline WCAG-AA contrast miss (4.49:1 vs. 4.5:1 required) for `--fg-tertiary` (`#8b83b8`) on `--bg-raised` (`#221e47`), present on every one of the 5 pages scanned — real, but at the threshold, not a severe failure. |
| 9 | Help Users Recognize, Diagnose, and Recover from Errors | 2 | Form errors preserve entered values (good) but no inline field-level error text found near individual inputs — likely a single disconnected flash banner. |
| 10 | Help and Documentation | n/a | Single-institution, staff-only desk tool; PRODUCT.md confirms no help system is planned, and none is warranted. |

**Total: 25/36 (heuristic 10 n/a) → 69% → Acceptable.**

## Design Specificity Verdict

**LLM assessment**: Authored, not generic. The accession-slip vocabulary, indigo rail identity, Fraunces display numerals on stat tiles, and monospace ISBN/call-number treatment are all present exactly as DESIGN.md specifies. The coral/apricot/aqua urgency ladder is applied correctly and consistently (overdue rows get `badge-red`/`row-alert`, on-loan gets `badge-accent`, returned gets `badge-green`). Category badges use the deterministic-hue trick rather than a hardcoded map. Confirmation sheets name the exact record ("Delete this book?" names the actual title), not a generic "Are you sure?".

**Deterministic scan**: CLI detector (`detect.mjs` against `templates/admin/*.html`, 7 files) returned **zero findings, exit code 0** — no static-markup anti-patterns. Live-DOM browser evidence (5 pages, desktop viewport) found 9-13 findings per page, dominated by three repeating rule types: `gray-on-color` (near-white text `#e9e6f5` on `#221e47`), the `low-contrast` 4.49:1 near-miss noted above, and `ai-color-palette` ("cyan neon" flags on `svg.icon-sm` elements, present on Dashboard/Books/Borrowing History). Books also showed one `text-occlusion` (the "Title" label ~80% covered by its own input) and Settings showed 3× `tiny-text` (11px body text).

**Assessment B flagged the `gray-on-color` finding as a likely false positive**: `#e9e6f5` is a faintly purple-tinted near-white deliberately matched to the brand hue (DESIGN.md's Independent-Mode Rule — dark-mode ink is re-derived, not a generic gray), not a neutral gray accidentally left on a colored surface. The detector's chroma heuristic can't distinguish the two cases from static analysis alone. The `ai-color-palette` "cyan neon" count is also likely inflated — Assessment B suspects one SVG icon's child nodes (rect/circle/path) are each triggering a separate finding for what is visually one icon, not 4-6 distinct instances.

**Where the two assessments agree**: both independently converged on contrast/data-density issues as real, if not severe — A's heuristic-9 score (2, inline error text) and B's `text-occlusion`/`tiny-text` findings point at the same underlying gap: form and data-dense surfaces (Books, Settings) get the least design attention of the admin surface.

## Overall Impression

A genuinely product-specific, well-crafted desk tool let down by one structural gap: it was clearly designed against a single-item mental model (one book added, one book deleted, one loan checked in) when the real job — per PRODUCT.md's own framing of "run the circulation desk" — is inherently batch-shaped. The biggest opportunity is closing that gap, not the visual system, which is already strong.

## What's Working

1. **The mono/data discipline is real, not decorative.** ISBNs, dates, and counts consistently use `.mono`/`.num` classes site-wide — this single convention does more to make the admin surface feel like a library system than any color choice would.
2. **The Explain-the-Block rule is honored in copy, not just components.** `edit_book.html:41` shows "N on the shelf now" next to the quantity field, a constraint surfaced right where the decision happens.
3. **Confirmation sheets consistently name the exact record** across delete-book, delete-member, and check-in flows — a genuinely disciplined pattern most admin CRUD surfaces skip.

## Priority Issues

**[P1] No bulk or multi-select actions anywhere in the circulation surface**
Why it matters: the librarian's actual desk job (per PRODUCT.md) is processing batches — a stack of returns, a shipment of new titles — but every action here is one row/one form at a time. This is the single biggest efficiency gap on the surface, and it's why Heuristic 7 scores a 1.
Fix: add row checkboxes + a bulk "Check In selected" action to Borrowing History; consider a CSV import path for cataloguing.
Suggested command: `$impeccable optimize`

**[P1] Add Book form has no inline field-level error feedback and no clear saved confirmation**
Why it matters: this is the highest-frequency data-entry task on the desk. A bad ISBN means a full page reload back to a long form with only a page-level flash, not a marker at the offending input — Assessment B's `text-occlusion` finding on this same form (the "Title" label buried under its own input) is independent evidence this exact form gets the least visual-QA attention on the surface.
Fix: render errors adjacent to each invalid field (red border + inline text under the input, matching the existing `.req` asterisk pattern) and add a success toast/highlight on the newly added row.
Suggested command: `$impeccable harden`

**[P2] Quantity can be edited below `available_quantity` with no guardrail**
Why it matters: dropping quantity below what's checked out produces a nonsensical negative "available" count downstream — exactly the circulation-truth violation Product Principle #1 says should never happen.
Fix: clamp min to the current active-loan count with an inline note ("2 currently on loan — can't go below 2"), or accept the lower number with an explicit warning rather than silent submission.
Suggested command: `$impeccable harden`

**[P2] Add Book has no Cancel/collapse control, unlike Edit Book**
Why it matters: two forms doing the same conceptual job (create/modify a book record) offer different exits — Edit Book has Cancel, Add Book only closes via re-clicking the disclosure summary, whose label text itself changes when form errors force it open.
Fix: add a Cancel/Close action inside the `<details>` panel body that also resets partially-entered values.
Suggested command: `$impeccable clarify`

**[P3] The hairline contrast miss (4.49:1 vs 4.5:1) on `--fg-tertiary` recurs on every page scanned**
Why it matters: it's a threshold miss, not a severe failure, but it's the one deterministic, repeatable finding across all 5 admin pages — worth a one-token fix since it would otherwise keep re-surfacing on every future audit.
Fix: nudge `--fg-tertiary` (`#8b83b8`) very slightly darker against `--bg-raised` (`#221e47`) to clear 4.5:1, or confirm current usage sites are all decorative/tertiary (never real data) per DESIGN.md's Tertiary-Is-Not-Data Rule, which would make this an acceptable, intentional floor rather than a defect.
Suggested command: `$impeccable audit`

## Persona Red Flags

**Alex (Power User)** — primary action: process a stack of five returned books.
- No batch check-in: five separate full round-trips (load page, find row, click Check In, confirm sheet, repeat) for a task that's conceptually one action.
- No keyboard shortcut evident on the circulation list; everything requires mouse-precision clicks on small icon buttons.
- The confirm-sheet-per-item pattern, excellent for a rare destructive action, becomes the "redundant confirmation for a routine low-risk action" red flag when applied five times in a row to check-in.

**Sam (Accessibility-Dependent User)** — primary action: catalog a new book via keyboard/screen reader only.
- The Add Book panel's native `<details>/<summary>` is genuinely good for keyboard/AT — a real strength.
- Table action cells rely on `aria-label`/`title` on icon-only buttons with no visible text — a low-vision user zoomed to 200% who can see icons but not read tooltips has no visible label distinguishing edit from delete.
- No `aria-describedby` linking a field to its error message was found in the Add/Edit forms — if validation fails server-side, a screen-reader user has no announced link between the flash and the specific bad field.

## Minor Observations

- The dashboard's "Process Reservations" and the Books page's "Add Book" both read as *the* primary toolbar action with equal `btn-primary` weight — correct individually, but the admin toolbar rarely offers a secondary/tertiary action, so its own flexibility is underused.
- Member Detail's reservation table truncates at a limit with only a count below, no link to see the rest.
- No loading/pending state on any submit button (Add Book, Delete, Check In, Save Settings) — folds into the P1 error-feedback fix above.
- Settings' theme-color picker changes the entire institution's brand color in one save with no live preview — worth a preview step given how consequential and hard-to-notice a wrong hex would be.

## Questions to Consider

- If the real workday involves a stack of returns, not one at a time, does the one-row-per-confirm-sheet pattern actually serve Alex, or was it designed only against the rare delete case and then applied everywhere by default?
- The Add Book `<details>` panel is the system's only progressive-disclosure gesture — what would a "quick add" (title/author/ISBN/copies) vs. an optional "full record" expansion look like?
- Given the theme-color picker repaints the whole institution's brand in one save, is a live preview or an "Apply" vs. "Save" split warranted?

## Run Notes

- Target: `templates/admin/*.html` (7 files) + `routes/admin.py` + `templates/base.html`, live app at `http://localhost:5050`, desktop viewport (1440×900).
- Ignore list: none (`.impeccable/critique/ignore.md` does not exist).
- Assessment independence: A and B ran as two isolated parallel sub-agents, neither saw the other's output.
- CLI detector: ran clean, 0 findings, exit 0.
- Browser visibility/injection: succeeded via `mcp__Claude_Browser` (native fallback; `claude-in-chrome` extension unreachable in this session) across 5 representative admin pages; live-server crashed once mid-run and was restarted without data loss, then stopped and confirmed dead before the assessment finished.
- Both assessments logged in as `admin`/`admin` against a locally seeded dev DB (test member + 4 books + 1 overdue/1 active loan + 1 reservation).
