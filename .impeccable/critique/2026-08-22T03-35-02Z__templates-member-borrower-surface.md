---
target: templates/member (borrower surface)
total_score: 25
max_score: 32
na_heuristics: 7,10
p0_count: 0
p1_count: 2
timestamp: 2026-08-22T03-35-02Z
slug: templates-member-borrower-surface
---
Method: dual-agent (A: borrower-design-review · B: borrower-detector-evidence)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 4 | Renew produced an immediate, specific flash with the exact new due date; live stat-tile/slip updates with no flicker gap; reservation queue position shown explicitly. |
| 2 | Match Between System and Real World | 4 | Plain academic-library language throughout ("You're next in line," "Overdue loans must be returned rather than renewed"), no jargon. |
| 3 | User Control and Freedom | 3 | Every committing action routes through a cancelable, named-record sheet; docked for search having no persisted recent-search recall, only a full Clear reload. |
| 4 | Consistency and Standards | 3 (design) / evidence-corroborated | Slip component, badges, buttons, and confirm-sheet pattern identical across dashboard/history/reservations. Detector found the same repeating `undersized-ui-text` (9.5px "Due" labels, 10px nav labels) and `tiny-text` (11px body) on every page scanned — a real, systemic micro-type floor issue that also reads as a consistency strength (it's consistent, just consistently small). |
| 5 | Error Prevention | 3 | Renew/borrow/reserve are confirmation-gated with named consequences; docked because the search form has no debounce/validation and can silently submit an empty query. |
| 6 | Recognition Rather Than Recall | 4 | Every tab-bar/toolbar icon is text-labeled; no icon-only nav found anywhere in the member shell. |
| 7 | Flexibility and Efficiency of Use | n/a | Correctly out of scope — PRODUCT.md scopes borrowers as casual phone users, not repeat operators needing shortcuts/bulk actions. |
| 8 | Aesthetic and Minimalist Design | 3 (design) / evidence-flagged | Dashboard is restrained (one alert, three tiles, two panels). Detector corroborated real crowding elsewhere: 2× `nested-cards` on dashboard, `cramped-padding` on a history panel, and the search page's filter chrome eating most of the first phone viewport (A's own P1 finding). |
| 9 | Help Users Recognize, Diagnose, and Recover from Errors | 3 | Block reasons are excellent and specific; no generic form-validation error state was found to test, scored conservatively rather than assumed. |
| 10 | Help and Documentation | n/a | No in-app help surface exists or is scoped by PRODUCT.md; defensible omission for a 4-screen single-institution tool. |

**Total: 25/32 (78%) → Good.**

## Design Specificity Verdict

**LLM assessment**: Authored, not generic. The accession-slip metaphor is load-bearing, not decorative — the stub literally is the due-date card, Fraunces for the day, Plex Mono for the month, and it holds up consistently across dashboard, history, and reservations. Book covers use a deterministic ISBN-hashed gradient confined to the brand's aqua→indigo arc rather than a stock placeholder. Status color is genuinely load-bearing: a live overdue slip restamped its whole stub coral while a not-yet-due loan stayed neutral, exactly matching the Cool-Is-Inventory rule. The tested confirm-sheet-to-flash renew loop named the book and the exact new date at both ends — no generic "Success!" anywhere. Where it slips toward interchangeable: the search page's filter chrome (a plain `<select>` + text input + two stacked full-width buttons) doesn't borrow the slip/mono vernacular at all — it's the one part of this surface that could belong to any CRUD app.

**Deterministic scan**: CLI detector (`detect.mjs` against `templates/member/*.html`, 4 files) returned **zero findings, exit code 0**. Live-DOM browser evidence (4 pages, phone viewport 390×844) told a different story — this is the sharpest agreement/disagreement split in either surface's critique: 16 findings on Dashboard, 17 on Search, 11 on History, 5 on Reservations. Repeating rule types: `gray-on-color` and the same 4.49:1 `low-contrast` near-miss found on the admin surface (both surfaces share the same dark-mode token pair, `#8b83b8` on `#221e47`) on every page; `undersized-ui-text` for the slip-stub's 9.5px "Due" label and the tab bar's 10px nav labels, repeating on literally every page since the tab bar is persistent chrome; `tiny-text` (11px body) on three of four pages; `side-tab` on the dashboard's accent stat tile; `ai-color-palette` ("cyan neon") concentrated on Dashboard/Search; `nested-cards` (2×) on Dashboard; `cramped-padding` on History.

**Where LLM and detector converge**: Assessment A independently flagged the search page's filter chrome as the surface's weakest moment (P1, eats the whole first phone viewport) — Assessment B's evidence that Search also carries the single highest raw finding count (17) of any page on either surface is corroborating, not coincidental: the same page both a human-judgment pass and a mechanical pass singled out as the surface's least-polished screen.

**Where the detector likely overcounts**: Assessment B itself flagged the `ai-color-palette` "cyan neon" findings as probably one visual icon's SVG child nodes (rect/circle/path) each triggering a separate console message rather than 4-5 distinct defects — treat Search's 17 and Dashboard's 16 as upper bounds, not literal defect counts. The `side-tab` finding on the stat-accent tile is very likely intentional per DESIGN.md's own documented accent-stripe pattern (already reviewed and scoped-ignored on the admin/shared CSS side this session), not new drift.

## Overall Impression

The strongest single component on either surface — the accession slip — lives here, and the core loan/renew/reservation loop is genuinely well-crafted end to end. The gap is legibility at the micro scale: this surface's persistent chrome (tab bar) and several data labels sit right at or below a readable floor on a phone, which matters more here than on the desktop-only admin surface, and it's the one place the detector's mechanical pass caught something the human pass under-weighted (A scored Aesthetic a 3 without flagging type size specifically).

## What's Working

1. **The accession-slip component is a genuine signature, not a skin** — perforated stub, monospace month, Fraunces day, brand-color restamping, consistent across every page it appears on.
2. **The Explain-the-Block rule is implemented, not just documented** — the overdue loan's disabled-renew state carries a specific, calm sentence exactly where the button would be.
3. **The confirm-sheet-to-flash loop is tight and specific** — renewing a book produced a sheet naming the title, then a flash naming the title and the exact new date.

## Priority Issues

**[P1] Search's filter chrome consumes the entire first phone viewport before any result appears — and independently carries the highest raw finding count of any page on either surface**
Why it matters: PRODUCT.md is explicit that borrowers search "overwhelmingly from a phone." At 390px, the scope-select + input + two full-width stacked buttons fill essentially the whole screen above the fold. Assessment B's 17 findings here (vs. 5-16 elsewhere) is the detector independently pointing at the same screen.
Fix: collapse the type-select into the search field itself (or a compact segmented toggle beside it) and drop "Clear" to a small icon inside the input.
Suggested command: `$impeccable distill`

**[P1] Persistent chrome and status micro-labels sit at or below a readable phone floor, and repeat on every screen**
Why it matters: the tab bar's 10px nav labels and the slip-stub's 9.5px "Due"/caption text are not one-off — they're structural chrome present on all four pages scanned, so this is a systemic legibility floor, not an isolated typo. On a phone, held one-handed, in variable lighting (Casey's actual usage context per PRODUCT.md), sub-11px functional text is a real strain point, not a nitpick.
Fix: raise the tab-bar label and slip-stub caption sizes to the Label role's 11px floor already documented in DESIGN.md's own type ramp, rather than the smaller ad hoc Micro/Rail-Label steps just added for the badge/stub digits specifically.
Suggested command: `$impeccable typeset`

**[P2] Renew and the calendar-export icon sit at near-equal visual weight on the loan slip**
Why it matters: Renew (`.btn-sm`, text) sits next to a round glass icon button for calendar export at nearly the same visual prominence — a secondary, occasional action reads with almost the same weight as the row's actual primary action.
Fix: promote Renew to a filled `.btn-primary` (DESIGN.md's own button hierarchy already supports this) or further recede the glass button at rest.
Suggested command: `$impeccable clarify`

**[P2] The reservation "calm color" policy has no copy explaining it to the user it protects**
Why it matters: the code deliberately keeps a lapsing hold's color calm rather than alarming, reasoning it's not the patron's fault — but that reasoning lives only in a CSS comment. A patron anxious about losing a hold gets a flatter signal than their anxiety, with nothing bridging the gap.
Fix: one line of copy near the hold status ("This lapses automatically if a copy isn't free by [date] — nothing you need to do") closes the entire gap.
Suggested command: `$impeccable clarify`

**[P3] Book-card status/action triad repeats with equal weight per card, with no scan shortcut**
Why it matters: on a page of 10+ results, each card requires full re-reading rather than a glanceable signal — the slip component elsewhere on this same surface already solved this with a colored left-edge bar.
Fix: borrow the slip's own left-edge accent-bar pattern onto book cards for skimmable status.
Suggested command: `$impeccable layout`

**[P3] Session/loan-state fragility observed during live testing — needs verification, not yet confirmed as a real defect**
Why it matters: the same test account briefly showed 0 loans/0 reservations mid-session with no explicit logout, which may be test-environment cross-talk from concurrent critique agents rather than a real bug — but if it reproduces for a genuine interrupted-and-returns patron (Casey's exact profile), losing visible loan state would be a trust-breaking P0, not a P3.
Suggested command: `$impeccable audit` (verify session/state persistence specifically)

## Persona Red Flags

**Casey (Distracted Mobile User)** — walked through Browse → Search → Borrow:
- The full-viewport filter chrome (P1 above) is her exact failure mode: one-handed, low patience, forced to re-scroll past 4 stacked controls every time.
- Positive: primary actions sit low enough on the card to be thumb-reachable; touch targets measured comfortably above 44px.
- The sub-11px persistent labels compound her problem — small text plus one-handed phone use plus "possibly on a slow connection" (her documented profile) is a legibility stack, not a single issue.

**Jordan (Confused First-Timer)** — walked through the dashboard → renew flow:
- No terminology red flags — every label reads in plain English.
- The confirm sheet is first-timer-friendly: names the book, states the exact consequence, uses a calm icon for a routine action.
- Minor flag: "All fields" as the default search scope-select value assumes prior understanding of what "fields" means before the user has typed anything, and the dropdown is visually no more prominent than the text input beside it.

**Sam (Accessibility-Dependent User)** — spot-checked via markup, not a full screen-reader pass:
- Positive: the decorative large-title is correctly `aria-hidden`, preserving a single real `<h1>` per page — the One-Heading Rule is genuinely implemented.
- Positive: status is never color-only — every slip/badge pairs color with an icon and text.
- The `undersized-ui-text`/`tiny-text` detector findings are directly relevant here too: sub-11px functional text is a low-vision accessibility concern, not just a phone-legibility one, and this is where Assessment B's mechanical evidence sharpens Assessment A's persona judgment rather than duplicating it.
- Unconfirmed: keyboard focus order through the slip's action row and focus-ring visibility against the coral overdue-stub background specifically — worth a dedicated keyboard-only pass.

## Minor Observations

- The dashboard's overdue-alert copy duplicates the same fact three times on one screen (alert body, stat tile, slip badge) — not wrong, but redundant given how restrained the page is otherwise.
- Search's "Clear" is a full page navigation (`<a href=...>`), not a client-side reset — a needless round trip on the slow campus connections PRODUCT.md explicitly names as an operating condition.
- The book-cover initial-letter treatment will collide constantly in a real academic catalog (many titles start with "The"/"A"/"An") — undermining the deterministic-identity idea for a meaningful fraction of any real shelf.

## Questions to Consider

- The reservation-hold "calm color" reasoning is good design thinking currently trapped in a code comment nobody using the app will read — what would it take to surface that intent as one line of on-screen copy?
- Search's filter row and the slip/book-card components speak two different visual languages in the same app — intentional ("filters are utility, slips are content"), or an area the system hasn't reached yet?
- Given the detector's sharpest, most-repeated finding on this surface is undersized persistent chrome text, is the current Label role (11px) actually the system's real floor, or does the newly documented Micro (9.5px) step need to be reconsidered rather than just accepted as intentional?

## Run Notes

- Target: `templates/member/*.html` (4 files) + `routes/member.py` + `templates/base.html` + `static/js/app.js`, live app at `http://localhost:5050`, phone viewport (390×844).
- Ignore list: none (`.impeccable/critique/ignore.md` does not exist).
- Assessment independence: A and B ran as two isolated parallel sub-agents, neither saw the other's output.
- CLI detector: ran clean, 0 findings, exit 0.
- Browser visibility/injection: succeeded via `mcp__Claude_Browser` (native fallback; `claude-in-chrome` extension unreachable) across 4 representative member pages at phone viewport; live-server (port 8400) stopped and confirmed dead before the assessment finished.
- Both assessments logged in as `testmember`/`testpass123` against a locally seeded dev DB (4 books, 1 overdue + 1 active loan, 1 reservation); Assessment B noted intermittent session drops during navigation, resolved by re-login, flagged as possibly relevant to A's session-fragility P3.
