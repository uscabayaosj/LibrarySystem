---
name: Library System
description: An accession-slip circulation desk for a self-hosted academic library — indigo identity rail, brand color as a status system, Fraunces/Archivo/Plex Mono type, offline-first by construction
colors:
  indigo: "#292168"
  indigo-deep: "#1f1950"
  coral: "#c0303c"
  coral-vivid: "#f7636e"
  coral-fill: "#c0303c"
  apricot: "#f9b78a"
  apricot-ink: "#9c5116"
  aqua: "#5dcbd1"
  aqua-ink: "#0f6c72"
  violet: "#4a3fa8"
  bg-window: "#ececec"
  bg-content: "#ffffff"
  bg-raised: "#ffffff"
  bg-sunken: "#f7f5f4"
  ink: "#1a1541"
  ink-secondary: "#5b5480"
  ink-tertiary: "#6f6892"
  separator: "rgba(41, 33, 104, 0.13)"
  separator-strong: "rgba(41, 33, 104, 0.22)"
  apricot-stub-ink: "#4a2408"
  coral-badge-ink: "#45060b"
typography:
  scale:
    micro: "9.5px"
    book-cover-sm: "17px"
    avatar: "22px"
    figure-sm: "26px"
    hero-sm: "28px"
    figure: "30px"
    hero: "33px"
  display:
    fontFamily: "Fraunces, 'Iowan Old Style', Georgia, serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.14
    letterSpacing: "-0.014em"
  headline:
    fontFamily: "Archivo, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif"
    fontSize: "19px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.011em"
  title:
    fontFamily: "Archivo, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.011em"
  body:
    fontFamily: "Archivo, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  label:
    fontFamily: "Archivo, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.09em"
  mono:
    fontFamily: "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.3
    letterSpacing: "-0.01em"
rounded:
  xxs: "2px"
  xs: "3px"
  sm: "5px"
  md: "8px"
  lg: "12px"
  xl: "18px"
  pill: "999px"
spacing:
  unit: "4px"
components:
  button-primary:
    backgroundColor: "{colors.indigo}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "7px 15px"
    height: "34px"
  button-primary-hover:
    backgroundColor: "#3d3490"
  button-secondary:
    backgroundColor: "{colors.bg-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "7px 15px"
    height: "34px"
  button-secondary-hover:
    backgroundColor: "rgba(41, 33, 104, 0.045)"
  input-field:
    backgroundColor: "{colors.bg-content}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
    height: "38px"
  badge-status:
    backgroundColor: "rgba(247, 99, 110, 0.16)"
    textColor: "{colors.coral}"
    rounded: "{rounded.pill}"
    padding: "3px 9px"
    typography: "{typography.label}"
  panel:
    backgroundColor: "{colors.bg-content}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "18px"
  slip:
    backgroundColor: "{colors.bg-content}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
  sidebar-link-active:
    backgroundColor: "rgba(255, 255, 255, 0.16)"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "8px 10px"
---

# Design System: Library System

## Overview

**Creative North Star: "The Accession Slip"**

The whole system is built out of one physical object: a specimen tag, a hand-assigned accession number, a due-date card tucked in a paper pocket. That vernacular is structurally true here, not a skin over generic UI — a call number, an ISBN, a due date are real identifying data, so they are set in a fixed-width monospace face and aligned in columns rather than left to flow with surrounding prose. The system's signature component, the `.slip`, is this object made literal: a perforated indigo stub holding a stamped date on the left, the record itself on the right, exactly like a due-date card in a library pocket.

Color works as a status system, not decoration. Indigo (`#292168`) is the department's own identity color — it owns the navigation rail in both light and dark appearance, so the app is recognizable at a glance regardless of theme. Coral marks overdue, apricot marks due-soon, aqua marks available/returned: three brand tints doing the job a generic red/yellow/green traffic light would do elsewhere, except these three are the institution's own palette, reused rather than invented. Every one of these pairings — and every neutral pairing beside it — was checked against real WCAG contrast math, in both appearances independently.

The system is self-contained by construction: Fraunces, Archivo, and IBM Plex Mono are all served from `static/fonts`, every icon is inline SVG, and nothing depends on a CDN. This isn't an aesthetic choice — it's what lets the accession-slip vernacular render identically on a restricted campus network or fully offline, which is the actual operating condition for a school library. Two sibling shells share this one system without diverging from it: the librarian's circulation desk stays dense on desktop but now adapts down through a tablet icon-rail and a phone bottom-tab-bar of its own, while the borrower's side runs the same four-tier structure the other way — phone-first, with a tablet hybrid and a desktop ceiling — both built from the same rail tokens.

**Key Characteristics:**
- The accession slip (`.slip`/`.slip-stub`) as the system's signature component and the source of its whole vernacular — monospace data in fixed columns, brand color as status
- A single saturated indigo field (the rail) that never changes between light and dark appearance, anchoring identity
- Brand color used as meaning only: coral/apricot/aqua map to overdue/due-soon/available, never to decoration
- Two depth languages: soft ambient ink-tinted shadows for resting content, frosted glass strictly for floating chrome
- Full light/dark appearance parity, every token independently re-picked and re-verified against WCAG, never inverted or dimmed
- Fraunces at large optical sizes for numbers and page titles — the one place display type is allowed to be expressive; Archivo and Plex Mono keep everything else quiet and legible

## Colors

The palette pairs one saturated brand identity (indigo) with three brand-tint status colors (coral, apricot, aqua) against a warm, near-neutral paper ground — color is reserved for identity and meaning, never used to decorate a resting surface.

### Primary
- **Indigo** (`#292168`, dark accent text `#9d94ef` / dark accent fill `#4a3fa8`): the department's identity color. Owns the navigation rail solidly in both appearances (`--rail-bg`/`--rail-bg-deep`), and is the system's one accent — primary buttons, links, focus rings, selected states, segmented-control selection. Light mode uses one token for both text and fill (indigo clears 12.8:1 on white either way); dark mode splits into a lighter text tone and a deeper fill tone (see Named Rules).

### Secondary
- **Apricot** (`#f9b78a`): the rail's own marker color (`--rail-marker`) — the leading-edge rule on the active sidebar link, the top-edge rule on the active phone tab, the avatar background. Doubles as the due-soon status color (`--orange`, darkened to `#9c5116` for light-mode text).

### Status & Semantic
- **Coral** (`--red`: `#c0303c` light / `#f7636e` dark, `--red-fill`: `#c0303c` both modes): overdue items, destructive actions, error alerts, required-field marks, the overdue slip's restamped stub. `--red-fill` stays the same darker value in both appearances specifically because it always carries white text (a filled danger button, an overdue stub) — see the Text/Fill Split Rule.
- **Apricot** (`--orange`: `#9c5116` light / `#f9b78a` dark): due-soon warnings, warning alerts, the due-soon slip's restamped stub. The due-soon stub is the one place apricot fills a whole surface — it's too light to carry white text, so the stub re-points its foreground tokens at **Apricot Ink** (`#4a2408`) instead, verified at 7.9:1 for the date and 4.6:1 for the smallest caption.
- **Aqua** (`--green`/`--teal`: `#0f6c72` light / `#5dcbd1` dark): success states, available/returned status, reservation-related stats and badges. Aqua covers two semantic roles (success and info/reservation) that happen to share one hue in this palette.
- **Coral Badge Ink** (`#45060b`): the count text inside the coral tab-bar/nav count badge — coral at full saturation is a fill color, not a text color (see the Text/Fill Split Rule), so its badge text drops to this near-black coral-tinted ink rather than white, the same "restamp to a dark ink" move Apricot Ink makes on the due-soon stub.
- **Muted Violet** (`--purple`: `#4a3fa8` light / `#b3a9f5` dark): the roster/people lane — the Members count on the librarian's dashboard. An entity class, not an urgency signal; see the Cool-Is-Inventory Rule.

### Neutral
- **Window** (`--bg-window`: `#ececec` light / `#12102a` dark): the outermost app background, one step behind every panel. In dark mode this is indigo taken down to near-black, not a neutral grey — the rail still belongs to the page it sits beside.
- **Content** (`--bg-content`: `#ffffff` light / `#191634` dark): the base surface for panels, cards, book covers, slips.
- **Raised** (`--bg-raised`: `#ffffff` light / `#221e47` dark): buttons, menus, sheets — one step lighter than Content in dark mode so floating chrome reads as sitting above the page.
- **Sunken** (`--bg-sunken`: `#f7f5f4` light / `#14122f` dark): table headers, book-card footers, segmented-control tracks — surfaces that sit behind their content rather than holding it.
- **Ink** (`--fg`: `#1a1541` light / `#e9e6f5` dark): primary text.
- **Ink Secondary** (`--fg-secondary`: `#5b5480` light / `#a49dc8` dark): metadata, sub-labels, secondary copy, row explanations.
- **Ink Tertiary** (`--fg-tertiary`: `#6f6892` light / `#8f89bd` dark): placeholders, disabled controls, decorative icon fills — below the body-text floor by design. Nudged from an earlier `#8b83b8` (4.49:1, a hairline AA miss caught by audit) to `#8f89bd` (4.82:1).
- **Separator** (`rgba(41,33,104,0.13)` light / `rgba(255,255,255,0.11)` dark): panel borders, table rules, toolbar dividers — all tinted indigo rather than neutral black/white.

### Named Rules
**The Text/Fill Split Rule.** `--accent`/`--accent-fill` (and `--red`/`--red-fill`) are two separate tokens because a value tuned to be legible as text on a dark surface is too light to hold white text as a button or stub fill. In light mode both halves of a pair share one value; in dark mode they diverge (`--accent` `#9d94ef`, `--accent-fill` `#4a3fa8`; `--red` `#f7636e`, `--red-fill` `#c0303c`). Never use the text-tuned token as a background holding white text, or the fill-tuned token as page text — this exact mix-up is called out by name in the CSS as a source of real contrast bugs (breadcrumbs, tab-bar labels).

**The Independent-Mode Rule.** Dark appearance ("midnight") is never `filter: invert()` or a flat opacity dim — every token is re-derived by hand for the indigo-toned dark ground it sits on and checked against the same WCAG math as light mode ("paper"). Treat "add dark mode" as deriving a second, equally deliberate palette.

**The Cool-Is-Inventory Rule.** In a row of summary tiles, the cool lanes (indigo, aqua, violet) color only the number — they carry counts of what exists. Coral is the one lane that also tints its label, because it's the count that means something is wrong. A tile row where every value is coral, or where one cool value alone is left uncolored, has stopped encoding anything.

**The Tertiary-Is-Not-Data Rule.** `--fg-tertiary` is for placeholders, disabled controls, and decorative icon fills. A real value — a zero count, an absent date, a row explanation — is data however unremarkable, and takes `--fg-secondary` instead; the CSS itself corrects this in the row-note comment, noting tertiary measures 2.96:1 on an alert row and fails AA.

## Typography

**Display Font:** Fraunces, with 'Iowan Old Style' → Georgia → serif fallbacks
**Body Font:** Archivo, with the system sans-serif stack as fallback
**Label/Mono Font:** IBM Plex Mono, for call numbers, ISBNs, accession lines, and every date/count that needs to align in a column

**Character:** Fraunces carries the display voice — its SOFT and WONK variable-font axes give large numerals and page titles a warmth a system face can't — while Archivo does the quiet interface work everywhere else. Plex Mono is reserved for genuine identifying data: it's what makes a call number or a due date read as a record rather than as prose.

### Hierarchy
- **Display** (600, `--text-xl` 24px, 1.14, Fraunces at `opsz 72 / SOFT 22 / WONK 1`): the toolbar `<h1>` and hero/auth headlines — the one real heading per page.
- **Headline** (600, `--text-lg` 19px, 1.2, Archivo): panel/section headings (`h2`), the member phone shell's decorative large-title (`aria-hidden`, purely visual — see the One-Heading Rule).
- **Title** (600, `--text-md` 16px, 1.2, Archivo): `h3`, book titles, slip titles.
- **Body** (400–550, `--text-base` 14px, 1.55, Archivo): every control, table cell, form field, paragraph — the system's true base size.
- **Label** (600, `--text-xs` 11px, 1.3, 0.09em uppercase, Archivo): the "eyebrow" class — column headers, sidebar section headings, field labels, badge text.
- **Data/Mono** (400–600, `--text-sm` 12.5px, tabular-nums, IBM Plex Mono): ISBNs, accession numbers, dates, counts — anything that must align in a fixed column rather than flow.

A large Fraunces treatment (`opsz 110/SOFT 24/WONK 1`, `--text-2xl` 34px) is reserved specifically for stat-tile values — numerals are the one place a figure is allowed to be beautiful rather than merely aligned.

A handful of further sizes exist outside the six named roles, each reused deliberately rather than a one-off:
- **Figure** (30px, 26px at the ≤520px compact breakpoint): the slip-stub's stamped day and the book-cover initial — both a step down from the stat-tile's 34px because they sit inside a much smaller card, not a full tile.
- **Hero** (33px, 28px at the ≤520px compact breakpoint): the marketing/auth landing `h1`, a Display-family size reserved for the one page that isn't the app shell.
- **Book Cover (small)** (17px): the compact 42px book-cover variant used in list rows, scaled down from Figure to fit.
- **Avatar** (22px): the member-detail avatar's initial, sized to its 56px circle.
- **Micro** (9.5px): the tab-bar count badge's digit — smaller than Label (11px) because it sits inside an already-tiny chip and reads as a single glance, not running text. The slip-stub's month/label caption and the tab-bar's nav labels were raised to the Label floor (11px, `--text-xs`) after a phone-legibility review found the smaller step sitting below a readable minimum on persistent chrome.

### Named Rules
**The One-Heading Rule.** Exactly one real `<h1>` exists per page (the toolbar title); the member phone shell's larger decorative title is `aria-hidden` and purely visual, so assistive tech never sees two headings for one page.

**The Data-Is-Monospace Rule.** Any string that is a real identifier — an ISBN, a call number, an accession line, a due date, a count — is set in `--font-mono` with `font-variant-numeric: tabular-nums`, never left in the body face. This is what makes a ledger of loans read as aligned data instead of ragged prose.

## Layout

The shell is a two-column grid: a fixed 244px indigo rail (`--sidebar-w`) plus a fluid content column. Content padding steps from 26px desktop to 20px tablet to 16px phone. A 60px sticky, frosted toolbar caps every page.

Four responsive tiers apply, each triggered by a different threshold — both shells are now fully responsive across phone/tablet/desktop, sharing this same tier structure rather than one shell freezing at desktop:
- **1024px+ (desktop):** the full 244px rail is always visible; both shells run their densest layout (admin's multi-column tables and forms, member's `split` dashboard).
- **768–1023px (tablet):** the rail collapses to a **persistent 72px icon rail** (not a hidden drawer) — the librarian and the borrower both keep one-tap access to every section without losing horizontal space to a full label rail; each icon carries its label as a native `title` tooltip plus visually-hidden text for screen readers, so nothing is unlabeled, just visually compact. Data tables stay as real `<table>` layout (a 768px iPad-portrait content column still fits them) rather than dropping to stacked cards early. This tier is genuinely hybrid, not a shrunk desktop or a stretched phone — it's deliberately the boundary a real tablet in portrait lands inside, not on top of.
- **<768px (phone, shell breakpoint):** the icon rail collapses to a fixed overlay drawer (with a `rgba(18,16,42,0.44)` scrim); data tables switch from `<table>` layout to stacked cards (`table.stacked`), each row becoming a block with `data-label`-prefixed fields so actions stay reachable. Both shells now get a persistent bottom tab bar below this width (the librarian's carries Dashboard/Books/Members/Circulation; the borrower's is unchanged) — the member shell additionally crossfades a large decorative title into the compact toolbar title as the page scrolls, a treatment the admin shell doesn't need since it has no equivalent hero header.
- **640px (row-stack, content-driven):** the `.row-item` list component specifically — below this width a row can't hold a real book title and a status/actions column side by side, so the status group drops to its own line under the title. This threshold comes from the row's own content, not a device class, which is why it sits inside the phone tier rather than replacing it.
- **520px (compact):** the stat grid drops to 2 columns, hero padding tightens, the searchbar stacks vertically, and the slip's stub column narrows from 92px to 78px.

Grid helpers used throughout: `grid-stats` (auto-fit, 178px min), `grid-2` (auto-fit, 320px min), `grid-cards` (auto-fill, 300px min, for book cards), and a `split` 1.65fr/1fr layout for detail-plus-sidebar pages — all collapse to one column at 860px. Within the 768–1023px tablet tier specifically, a standalone `.slips` list that sits directly in the content column (the borrower's Reservations page, not nested inside a narrower `.split` panel like the dashboard's Currently Borrowed list) becomes a two-column grid — one full-width slip card at the ~748px tablet content width leaves as much empty space as content, so two holds run side by side instead, the hybrid two-column pattern a tablet calls for.

Spacing is rooted in a 4px unit rather than a named scale: hairline gaps, 7–9px between related controls, 14–18px internal panel/card padding, 26px page/toolbar edges. The one deliberate exception is inter-region spacing: `.region + .region` gets 28px specifically because page regions (an alert, a row of stat tiles, detail panels) share one background and have no divider between them — the gap alone has to carry the grouping, so it must read as visibly larger than the intra-region gap or the page flattens into one undifferentiated stack.

Touch targets expand under `@media (pointer: coarse)`: buttons, badges, and pagination controls grow from 34px to 44px minimum height.

## Elevation & Depth

**Ink-on-paper.** This is a two-depth-language system, not one shadow scale reused everywhere. Resting surfaces — panels, stat tiles, book cards, slips — use shadows that are warm and indigo-tinted rather than neutral black (`rgba(26,21,65,...)` in light mode, still colored rather than pure black in dark mode), reading as ink bleeding softly into paper rather than an object physically lifted off it. Floating/overlay chrome — the sticky toolbar, the account menu popover, confirmation sheets, the frosted glass icon buttons — instead uses `backdrop-filter: saturate(...) blur(...)`, a true material effect that tints and blurs whatever scrolls behind it. This is the one place depth stops being an ambient hint and becomes an actual physical material.

### Shadow Vocabulary
- **shadow-sm** (`0 1px 2px rgba(26,21,65,0.07), 0 0 0 1px rgba(41,33,104,0.06)` light / `0 1px 2px rgba(0,0,0,0.40), 0 0 0 1px rgba(255,255,255,0.06)` dark): resting panels, cards, stat tiles, book cards, slips.
- **shadow-md** (`0 3px 12px rgba(26,21,65,0.10), 0 0 0 1px rgba(41,33,104,0.06)` light / `0 3px 14px rgba(0,0,0,0.48), 0 0 0 1px rgba(255,255,255,0.07)` dark): hover-lifted cards, stat tiles, slips, the auth card.
- **shadow-lg** (`0 18px 48px rgba(26,21,65,0.22), 0 0 0 1px rgba(41,33,104,0.08)` light / `0 18px 52px rgba(0,0,0,0.62), 0 0 0 1px rgba(255,255,255,0.10)` dark): menus, confirmation sheets, the open mobile drawer.
- **shadow-btn** (`0 1px 1.5px rgba(26,21,65,0.08)` light / `0 1px 1.5px rgba(0,0,0,0.35)` dark): every default button.
- **glass-shadow** (`0 1px 3px rgba(26,21,65,0.12), 0 0 0 1px rgba(41,33,104,0.06), inset 0 1px 0 rgba(255,255,255,0.85)` light, analogous inset-white-line in dark): the frosted glass icon button only.

### Named Rules
**The Ink-on-Paper Shadow Rule.** Every shadow value is tinted with the brand indigo (or, in dark mode, deepened toward black but still paired with a subtle white-tinted 1px ring) rather than neutral black — a stacked surface should read as belonging to this palette even in its shadow, not as a generic Material elevation.

**The Glass-Is-Chrome Rule.** Frosted-glass blur is reserved for floating navigational/overlay chrome — the sticky toolbar, the account menu, confirmation-sheet backdrops, the round glass icon buttons — never for resting content surfaces. A panel, card, or slip is always opaque; only things that float over content get to blur it.

**The No-Blur Fallback Rule.** Every `backdrop-filter` use ships an `@supports not` fallback to a flat, opaque surface color (e.g. the toolbar falls back to `--bg-content`, the glass button falls back to `--bg-raised`) — never a transparent layer with no blur, which would read as a rendering bug rather than a deliberate flat state.

## Shapes

Corner radius follows a five-step scale (`--r-xs` 3px / `--r-sm` 5px / `--r-md` 8px / `--r-lg` 12px / `--r-xl` 18px) plus a full pill (999px) for badges, tags, and count indicators, with one micro-step (2px) below the floor for the rounded end-caps on the rail's thin 3px "you are here" marker rule — a detail too small to read as a real corner, just enough to keep a hard-edged sliver from looking clipped. The geometry is "cut-paper": slips and panels stay close to square, not fully rounded — only genuinely pill-shaped things (status badges, the count bubble on sidebar links) go fully round, matching the accession-slip's own cut-card silhouette. Borders are hairline (1px), colored with the indigo-tinted separator tokens rather than neutral grey, and used to separate rather than frame — most surfaces rely on background color and shadow to read as distinct.

## Components

### Buttons
- **Shape:** 5px radius by default (`--r-sm`), 8px on large buttons (`--r-md`), fully round only for the glass icon button.
- **Primary:** indigo fill (`--accent-fill`), white text, `shadow-btn`. Hover moves to `--accent-hover`.
- **Secondary (default `.btn`):** `--bg-raised` background, `--separator-strong` border, `shadow-btn` — same physical shape as primary, neutral instead of filled.
- **Danger / Success:** neutral button shape, text and hover-tint recolored to coral/aqua — reserved for renew/return/delete, never filled by default. Inside a confirmation sheet specifically, danger flips to a filled coral button (`--red-fill`, white text, hover `#a82833`) because it's the dialog's one primary action.
- **Glass:** round, frosted (`saturate(180%) blur(14px)`), tinted with the accent color — reserved for secondary floating actions like "add to calendar."
- **Press state:** every button scales to `0.98` on `:active` (`0.975` on the phone tab bar) — a small physical squash reinforcing "this is a real control."
- **Touch:** grows to 44px minimum height under `@media (pointer: coarse)`.

### Cards / Containers (Panel, Stat Tile, Book Card)
- **Corner style:** 12px radius (`--r-lg`).
- **Background:** `--bg-content`; no border, `shadow-sm` at rest.
- **Shadow strategy:** see Elevation — lifts to `shadow-md` with a small `translateY` on hover only where the card is itself a link (stat tiles, book cards, slips).
- **Internal padding:** 16–18px body; panels with a header get a hairline-separated `.panel-head` row.
- **Stat tiles** specifically carry a 3px top-edge accent rule in their status color, and set their value in Fraunces at a large optical size — the number is the content.

### Inputs / Fields
- **Style:** `--bg-field` background, `--separator-strong` border, 5px radius, 38px min height (44px on coarse pointers).
- **Focus:** border switches to `--accent` plus a 3px `--accent-soft` glow — never a color-only signal.
- **Checkboxes/radios:** native elements themed via `accent-color`, not custom markup, to keep real keyboard/AT behavior for free.

### Navigation
- **Rail link:** transparent at rest; the active page fills with `--rail-active` and gains a 3px apricot rule at its leading edge — the rail marks "you are here" with a rule rather than a filled pill, so the rail itself stays one uninterrupted field of indigo.
- **Bottom tab bar (member/phone only):** fixed, opaque indigo (the rail laid on its side, not glass), with the same apricot marker rule now on the top edge of the active tab. Unread-style coral badges (`#f7636e` fill, `#45060b` text) for active loans/reservations.
- **Breadcrumbs:** sit directly on `--bg-window` rather than a content panel, using `--accent` (not `--accent-fill`) — the one place a single accent token works unmodified in both appearances, because Window's contrast math differs from Content's.

### The Accession Slip (signature component)
A loan or reservation is rendered as a physical card in a pocket: a 92px perforated indigo stub on the left, stamped with the due date in Fraunces (day) and Plex Mono (month), and the record itself on the right. The perforation is drawn with a repeating radial gradient rather than an image, so it stays crisp at any pixel density. Overdue restamps the whole stub in `--red-fill`; due-soon restamps it in apricot at full strength and re-points the stub's own foreground tokens to a dark burnt ink (`#4a2408`) rather than introduce a muddy darkened orange, because straight white fails against apricot. This is the object the entire system's vernacular is named after and modeled on.

### Book Cover (signature component)
No cover-art pipeline exists, so every book gets a deterministic gradient identity plus its title's initial — the same trick Apple Music/Podcasts/Contacts use for items without real artwork. The hue is derived from the book's ISBN and confined to the brand arc (aqua 184° through indigo 250°) rather than the full color wheel, so covers always read as belonging to this palette; white text clears 5.68:1 at the arc's worst point.

### Category Badge
The same deterministic-hue trick as Book Cover, keyed off the category string instead of the ISBN, confined to the same aqua-through-indigo arc, so "Fiction" reads as one stable color everywhere without a hand-maintained category map — this is the system's data-category role, distinct from the coral/apricot/aqua urgency ladder. A book with no category gets the plain neutral `.badge`, never an arbitrary hue.

### Sheet (signature component)
A modal confirmation styled after a native macOS sheet: dropped near the top of the viewport rather than vertically centered, scale+fade transition, and it always names the exact record being acted on rather than a generic "are you sure?" Carries a soft accent-tinted icon for a routine confirm (borrow, renew) and a coral warning icon for anything destructive — `data-kind="safe"` on the backdrop swaps which glyph and tint show.

### Named Rules
**The Explain-the-Block Rule.** When a control is disabled or an action is unavailable (renewal, reservation), the interface surfaces the specific reason as copy near the control (`.row-note`) rather than leaving a silently disabled button.

## Do's and Don'ts

### Do:
- **Do** keep color meaning-only: indigo for identity/selection/primary, coral/apricot/aqua for overdue/due-soon/available — never decorative color blocking on a neutral surface.
- **Do** re-derive every color independently for dark appearance and verify it against real WCAG contrast math; never dim or invert.
- **Do** set any real identifying data — ISBN, call number, accession line, due date, count — in `--font-mono` with tabular numerals, never in the body face.
- **Do** use frosted-glass blur only for floating/overlay chrome, and always ship a flat, opaque `@supports not` fallback.
- **Do** tint shadows with the brand indigo rather than neutral black — depth in this system stays "ink," never generic Material grey.
- **Do** collapse all motion under `prefers-reduced-motion: reduce` — every transition in this system already does.
- **Do** treat the librarian (admin) and borrower (member) shells as two shells sharing one token set and one four-tier breakpoint structure, each adapted for its own primary device rather than one generic responsive layout stretched across both.
- **Do** name the exact record in any destructive-action confirmation sheet.

### Don't:
- **Don't** introduce a second brand accent alongside indigo — Muted Violet exists specifically as the roster/people lane and is not an invitation to add a second "brand" color.
- **Don't** use `--fg-tertiary` for a real value; it sits below the AA floor by design — see the Tertiary-Is-Not-Data Rule.
- **Don't** use a fill-tuned token (`--accent-fill`, `--red-fill`) as page text, or a text-tuned token (`--accent`, `--red`) as a background holding white text — they diverge in dark mode and this exact mix-up has already caused real contrast bugs (breadcrumbs, tab-bar labels).
- **Don't** add heavy neutral drop shadows, flat Material-style colorful cards, or ripple/elevation effects — depth here is either a soft ink-tinted hint or true frosted glass, never a loud generic statement.
- **Don't** disable a control without explaining why next to it.
- **Don't** depend on a CDN, web font service, icon font, or any external asset — every icon is inline SVG and every font is self-hosted from `static/fonts`, so the app renders identically offline and on restricted campus networks.
