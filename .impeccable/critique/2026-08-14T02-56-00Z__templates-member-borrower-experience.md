---
target: borrower (member) experience
total_score: 28
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
timestamp: 2026-08-14T02-56-00Z
slug: templates-member-borrower-experience
---
# Critique — Borrower (Member) Experience

Method: dual-agent (A: design-review · B: detector-evidence), both isolated & parallel. Detector counts folded in after the design verdict was formed.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3/4 | Reserve gives no inline queue-position feedback — you learn your spot only on the next page |
| 2 | Match System / Real World | 4/4 | Patron-native language throughout ("was due", "#2 in line", "Waiting in the queue") |
| 3 | User Control and Freedom | 3/4 | Escape-closes sheets & confirmable destructive actions, but no undo after a confirmed cancel |
| 4 | Consistency and Standards | 2/4 | Same healthy loan is GREEN on Overview, BLUE on My Loans; Borrow confirms but Reserve fires silently |
| 5 | Error Prevention | 2/4 | Cancel sheet pairs red "Cancel Reservation" (proceed) with neutral "Cancel" (abort) — mis-tap trap |
| 6 | Recognition Rather Than Recall | 3/4 | ⌘K search unhinted; calendar action is an icon-only glass button, no label on touch |
| 7 | Flexibility and Efficiency | 3/4 | ⌘K + inline renew + calendar export + PWA, but ⌘K is undiscoverable and desktop-only |
| 8 | Aesthetic and Minimalist | 3/4 | Overdue book stated 3× on the dashboard; "Browse Books" button duplicates the Browse tab |
| 9 | Error Recovery | 3/4 | Blocks well-explained on the dashboard, but My Loans buries the reason in a touch-invisible tooltip |
| 10 | Help and Documentation | 2/4 | Instructive empty states, but no first-run orientation and reservation-expiry semantics unexplained |
| **Total** | | **28/40** | **Good (address weak areas, solid foundation)** |

## Design Specificity Verdict — Highly specific, product-authentic

**LLM assessment:** This could not be reskinned as a generic app without gutting it. Every primary surface is built around circulation truth: loan rows carry a red/amber/green due-state ladder, the actions are the real verbs of a lending desk (Borrow / Renew / Reserve / Cancel), and blocked actions explain the circulation *rule* behind them ("Another member is waiting for this title"). Reservations show real queue mechanics ("#2 in line", "2 members waiting"); due dates export to the phone calendar. The "Circulation Desk as Finder" metaphor is genuine information architecture — source-list on desktop, iOS tab-bar + large-title on phone — not chrome. Deterministic book-cover gradients and subject-keyed category badges are a considered answer to "a library with no cover-art pipeline."

**Deterministic scan:** detect.mjs — member markup (`templates/member/`, `base.html`, `index.html`, `login.html`): exit 0, **0 findings**. `static/css/app.css`: 8 advisory findings, **all verified false positives** — traffic-light dot colors (documented native chrome), signature-component sizes (book-cover 26px, large-title 30px, tab label/badge 10/9px — all documented iOS/component intent), and a print-scope `#ccc` border. **Net real detector findings: 0.** The member templates positively uphold DESIGN.md's named rules (Explain-the-Block, meaning-only color / Text-Fill Split, decorative-aria).

The interesting split: the mechanical scan is spotless, but the design review surfaces five real issues it cannot see — all about cross-surface *consistency* and *touch-vs-hover parity*, which no per-file detector catches.

## What's Working
1. **Explain-the-block, done for real.** On the dashboard a blocked renewal states the actual circulation reason inline ("Another member is waiting for this title") — honoring the product's own Principle #5 with human copy where most systems just gray out a button.
2. **A coherent, meaning-only status system, fully re-derived in dark mode.** The red/amber/green due-ladder plus teal reservation lane reads instantly, and dark mode is hand-retuned (dark-red overdue tint, retuned stat values) rather than dimmed — verified in-browser.
3. **Consequence-aware confirmation sheets.** They name the exact record and the specific stake ("You'll lose your place in the queue for this title", "+14 days") — the right altitude for irreversible circulation actions.

## Priority Issues

**[P1] Renewal-block reason is invisible on the phone-primary My Loans screen.** The blocked row shows only "Can't renew," with the reason solely in a `title=` tooltip (`history.html:77`). Tooltips never fire on touch, so the primary (phone) audience hits a dead-end with no explanation — a violation of the Explain-the-Block rule that the dashboard already satisfies, and an a11y information-parity failure for low-vision touch users. Fix: render `renew_blocked_reason` as a visible `.row-note`, exactly as the dashboard does.

**[P1] Cross-screen due-state color inconsistency.** A healthy future loan is `badge-green` on Overview (`dashboard.html:85`) but `badge-accent`/blue on My Loans (`history.html:62`) — the same `due_state` maps to two colors on the two screens a student alternates between. Worse, green *also* means "Returned" on My Loans (`history.html:56`), so green carries two meanings across the surfaces. Directly contradicts the product's "every surface agrees" principle. Fix: one shared `due_state`→badge mapping.

**[P2] Confirmation-sheet label collision.** The cancel-reservation sheet's destructive button reads "Cancel Reservation" (red) while the abort button reads "Cancel" — two "Cancel"s meaning opposite things, a classic one-handed mis-tap trap at the exact moment the user is anxious. Fix: rename the abort to "Keep Reservation" / "Never mind".

**[P2] Reserve fires with no confirmation while Borrow shows a sheet.** Borrow has `data-confirm` (`search.html:92-95`); Reserve does not (`search.html:104-106`). Defensible (reserve is lower-stakes), but the asymmetry makes reserving feel *more* mysterious to a first-timer, not less. Fix: either confirm both or neither, consistently.

**[P2] Reservation-expiry countdown is shown in alarm color while the user is still #2 in line.** "Expires Aug 17 · 3 days left" in warning red/orange next to "#2 in line" implies imminent loss of a hold the user hasn't even been offered. Fix: label the state ("Hold starts when you reach the front") or suppress the countdown until the reservation is ready — this is partly a product-semantics question about what the 3-day clock means before you reach the front.

## Persona Red Flags
- **Casey (distracted, one-handed mobile):** the cancel sheet's red "Cancel Reservation" and neutral "Cancel" sit adjacent — a thumb aiming to abort can commit the destructive action. Calendar export is an unlabeled icon-only glass button. (Touch targets are correctly 44px.)
- **Sam (screen-reader / keyboard / low vision):** information parity fails on My Loans — the renewal reason lives only in `title=`, so a low-vision touch user sees just "Can't renew." Positives verified: decorative large-title is `aria-hidden`, focus rings present, sidebar drawer applies dialog/focus-trap only when modal, confirm sheet traps focus and closes on Escape.
- **Jordan (confused first-timer):** the bare calendar icon gives no hint it exports a due date; ⌘K is undiscoverable; Reserve-vs-Borrow confirmation asymmetry makes reserving feel riskier than it is; "Expires … 3 days left / #2 in line" is unparseable.
- **Busy university student checking due dates between classes (project persona):** the same book's due-status color differs between Overview and My Loans, so the one answer they came for — "what's due" — is the one the UI makes them second-guess.

## Minor Observations
- The confirmation sheet always shows a red warning-triangle icon (`base.html` sheet-icon is static), even for positive Borrow/Renew — slightly alarming tone for a routine action.
- "Browse Books" toolbar button duplicates the bottom "Browse" tab on the phone shell (and the dashboard hero).
- Reserve gives no inline "you're now #Nth" feedback at the moment of reserving (you POST, then see it on the next page).
- Inter-region spacing (`.region + .region: 28px` vs intra-region 16px) is correctly differentiated — the flattening risk is mitigated. `.row-note` correctly uses `--fg-secondary`, so visible block copy clears AA; the block-reason problem is purely tooltip-hiding, not contrast.

## Questions to Consider
1. If students open this app mainly to answer "when is X due," why does the same book's due-status wear a different color on the two screens they toggle between — and which screen is the source of truth?
2. The dashboard tells you *why* you can't renew; My Loans hides it in a tooltip a phone can't show. Why does the phone-primary screen know less than the desktop-friendly one?
3. A reservation you're #2 for shows a 3-day expiry countdown in alarm colors. Should that make a student feel safely in line, or afraid they're about to lose a book they were never offered?
