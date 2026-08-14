---
name: Library System
description: A self-contained macOS-flavoured circulation desk — source-list sidebar, translucent toolbar, native sheets, light and dark appearance
colors:
  window-gray: "#E8E8EA"
  content-white: "#FFFFFF"
  surface-raised: "#FFFFFF"
  sunken-gray: "#F2F2F4"
  ink: "rgba(0, 0, 0, 0.88)"
  ink-secondary: "rgba(0, 0, 0, 0.56)"
  ink-tertiary: "rgba(0, 0, 0, 0.42)"
  hairline: "rgba(0, 0, 0, 0.11)"
  system-blue: "#0069D9"
  system-blue-hover: "#0059B8"
  system-blue-soft: "rgba(0, 105, 217, 0.11)"
  system-red: "#D70015"
  system-red-soft: "rgba(215, 0, 21, 0.10)"
  accessible-amber: "#B54708"
  accessible-amber-soft: "rgba(181, 71, 8, 0.11)"
  accessible-forest: "#1E7A38"
  accessible-forest-soft: "rgba(30, 122, 56, 0.11)"
  deep-teal: "#0A6E82"
  deep-teal-soft: "rgba(10, 110, 130, 0.11)"
  muted-violet: "#7A3DB8"
typography:
  display:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', 'Segoe UI', Roboto, system-ui, sans-serif"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "normal"
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', 'Segoe UI', Roboto, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', 'Segoe UI', Roboto, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', 'Segoe UI', Roboto, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', 'Segoe UI', Roboto, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.02em"
rounded:
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "22px"
components:
  button-primary:
    backgroundColor: "{colors.system-blue}"
    textColor: "#FFFFFF"
    rounded: "{rounded.sm}"
    padding: "6px 13px"
    height: "30px"
  button-primary-hover:
    backgroundColor: "{colors.system-blue-hover}"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "6px 13px"
    height: "30px"
  button-secondary-hover:
    backgroundColor: "rgba(0, 0, 0, 0.045)"
  card:
    backgroundColor: "{colors.content-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "16px"
  badge-accent:
    backgroundColor: "{colors.system-blue-soft}"
    textColor: "{colors.system-blue}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
    typography: "{typography.label}"
  input-field:
    backgroundColor: "{colors.content-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "6px 10px"
    height: "30px"
  sheet:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "20px 22px 16px"
    width: "400px"
  sidebar-link-active:
    backgroundColor: "{colors.system-blue}"
    textColor: "#FFFFFF"
    rounded: "{rounded.sm}"
    padding: "6px 8px"
---

# Design System: Library System

## Overview

**Creative North Star: "The Circulation Desk as Finder"**

The interface is built around the librarian's actual desk: a source-list sidebar stands in for the shelf of collections (Dashboard, Books, Members, History), a translucent sticky toolbar holds the tools for whatever's open, and content panels behave like folders and documents — flat, hairline-bordered, quiet until you act on them. This isn't a library app wearing macOS chrome for polish; the desk metaphor is the actual information architecture. Everything native-feeling about it (traffic-light dots, SF-style type, frosted-glass overlays, sheet-style confirmations) exists to make that metaphor legible rather than as decoration for its own sake.

The system is self-contained by construction — hand-written CSS, vanilla JS, inline SVG icons, no CDN — so the desk metaphor renders identically offline and on restricted campus networks, which matters because the primary audience is a school library where that constraint is real, not aspirational.

Two sibling experiences share this system without diverging from it: the librarian's desk is desktop-only and dense; the borrower's side collapses to an iOS-style phone shell (bottom tab bar, large-title header) using the exact same tokens, just recomposed. One design system, two native-feeling shells.

**Key Characteristics:**
- Source-list sidebar + translucent sticky toolbar as the primary navigation grammar
- Flat, hairline-bordered panels; shadows are soft and ambient, never heavy
- Frosted-glass translucency reserved for floating/overlay chrome (sidebar, toolbar, glass icon buttons, sheets)
- A restrained accent (system blue) used only to mark selection, primary action, and links — never as page-level decoration
- Full light/dark appearance parity, with every token re-tuned per mode rather than just dimmed
- macOS-style confirmation sheets for anything destructive, naming the exact record being acted on

## Colors

The palette is desaturated and mostly neutral (window gray, content white, hairline separators); color is reserved for meaning — selection, status, and alerts — never for atmosphere. Every value below is the light-appearance canonical; the dark appearance re-derives each one independently rather than just inverting or dimming it (see Named Rules).

### Primary
- **System Blue** (`#0069D9` / dark: `#4C9DFF` text, `#0F6CDB` fill): the one accent in the system. Marks the active sidebar link, primary buttons, links, focus rings, and selected states. Used sparingly — its rarity is what makes "selected" and "primary" legible at a glance.

### Neutral
- **Window Gray** (`#E8E8EA` / dark: `#1A1A1C`): the outermost app background, one step behind every panel.
- **Content White** (`#FFFFFF` / dark: `#232326`): the base surface for panels, cards, and book covers.
- **Surface Raised** (`#FFFFFF` / dark: `#2A2A2E`): buttons, sheets, and menus — one step lighter than Content White in dark mode so floating chrome reads as sitting above the page.
- **Sunken Gray** (`#F2F2F4` / dark: `#1E1E21`): table headers, segmented-control tracks, book-card footers — surfaces that sit *behind* their content rather than holding it.
- **Ink** (`rgba(0,0,0,0.88)` / dark: `rgba(255,255,255,0.92)`): primary text.
- **Ink Secondary** (`rgba(0,0,0,0.56)` / dark: `rgba(255,255,255,0.60)`): metadata, sub-labels, secondary copy.
- **Ink Tertiary** (`rgba(0,0,0,0.42)` / dark: `rgba(255,255,255,0.42)`): placeholders, disabled/de-emphasized text, decorative icon fills.
- **Hairline** (`rgba(0,0,0,0.11)` / dark: `rgba(255,255,255,0.12)`): every panel border, table rule, and toolbar divider in the system.

### Status & Semantic
- **System Red** (`#D70015` / dark: `#FF6961`): overdue items, destructive actions, error alerts, required-field marks.
- **Accessible Amber** (`#B54708` / dark: `#FFA02E`): due-soon warnings, warning alerts. Deliberately darker than a typical system orange in light mode — a straight system-orange fails WCAG AA as text on white; this value was picked to clear 4.5:1 first.
- **Accessible Forest** (`#1E7A38` / dark: `#4CD97B`): success states, available/returned status. Same AA-first darkening as amber.
- **Deep Teal** (`#0A6E82` / dark: `#5AC8E8`): reservation-related stats and badges — its own semantic lane, distinct from the red/amber/green urgency ladder.
- **Muted Violet** (`#7A3DB8` / dark: `#C58AF9`): the **roster/people** lane — currently the Members count on the librarian's dashboard (`.stat-purple`). It exists so that "people" reads as a different kind of thing from the circulation ladder, not as urgency. Still not a second brand accent: it marks an entity class, never an action or a selection.

### Named Rules
**The Text/Fill Split Rule.** Every semantic color that appears both as text-on-page and as a filled surface holding white text gets two tokens (`system-blue` vs. its fill variant), because a blue tuned to be legible as text in dark mode is too light to hold white text as a button fill. Never reuse the text variant as a background-with-white-text, or vice versa — this exact mix-up has caused real contrast failures in this codebase (breadcrumbs, tab-bar labels, badges).

**The Independent-Mode Rule.** Dark appearance is never `filter: invert()` or a flat opacity dim — every single token is re-picked by hand for the dark surface it sits on, checked against the same WCAG math as light mode. Treat "add dark mode" as "derive a second, equally deliberate palette," not "darken the first one."

**The Cool-Is-Inventory Rule.** In a row of summary tiles, the cool lanes (blue, teal, violet) carry counts of what exists — titles, loans, members — and colour only the number. Warm red is reserved for the count that means something is wrong, and is the one lane that also tints its label. A tile row where every value is warm, or where one value alone is left uncoloured, has stopped encoding anything.

**The Tertiary-Is-Not-Data Rule.** `ink-tertiary` is for placeholders, disabled controls, and decorative icon fills — it measures ~3:1 and is deliberately below the body-text floor. A real value (a count of zero, an absent date) is data, however unremarkable, and takes `ink-secondary`. De-emphasis comes from the tone step, not from dropping under AA.

## Typography

**Display Font:** -apple-system / SF Pro Display, with Helvetica Neue → Segoe UI → Roboto → system-ui fallbacks
**Body Font:** -apple-system / SF Pro Text (same stack, text-optical-sized variant)
**Label/Mono Font:** ui-monospace / SF Mono, for ISBNs and other tabular/code-like data

**Character:** SF's native system stack end to end — the type never announces itself as a web font choice. Sizes run smaller than typical web defaults (13px body, matching "macOS control size") because the audience is reading dense tabular and list data at a desk or on a phone, not long-form prose.

### Hierarchy
- **Display** (600, 28px, 1.2): hero/marketing headline only (login, register, landing) — the single largest text in the system.
- **Headline** (600, 17px, 1.3, -0.01em): the toolbar page title — one real `<h1>` per page, and on the member phone shell it's echoed by a large 30px/700 decorative title above the fold.
- **Title** (600, 15px, 1.3, -0.01em): panel/section headings (`h2`, `h3`), book titles.
- **Body** (400–500, 13px, 1.5): every control, table cell, form field, and paragraph — the system's true base size.
- **Label** (600, 11px, 1.3, 0.02em uppercase): sidebar section headers, badges, tiny metadata tags.

### Named Rules
**The One-Heading Rule.** Exactly one real `<h1>` exists per page (the toolbar title); any larger decorative title (the member phone's large-title header) is `aria-hidden` and purely visual, so assistive tech and page structure never see two headings for one page.

## Layout

The shell is a two-column grid: a fixed 232px sidebar plus a fluid content column, collapsing at 860px into a single column with the sidebar becoming a fixed overlay drawer (with scrim) on top of content rather than pushing it. Content padding steps down with viewport: 22px desktop → 16px mobile. A 52px sticky toolbar caps every page.

Two responsive strategies apply below 860px depending on role:
- **Data tables** collapse from `<table>` layout into stacked cards — each row becomes a block with `data-label`-prefixed fields and actions moved to their own row, so touch targets never get clipped off-screen.
- **The member (borrower) shell** additionally swaps the sidebar's page navigation for a fixed iOS-style bottom tab bar, and crossfades a large decorative title into the compact toolbar title as the page scrolls. The librarian (admin) shell never gets this treatment — it stays desktop-only by design.

Grid helpers used throughout: `grid-stats` (auto-fit, 170px min, for stat tiles), `grid-2` (auto-fit, 320px min), `grid-cards` (auto-fill, 300px min, for book cards), and a `split` 1.65fr/1fr two-column layout for detail-plus-sidebar pages — all collapse to one column at 860px.

Spacing follows a loose 4px-rooted rhythm rather than a strict multiplier scale: 4px hairline gaps, 8px between related controls, 12–16px internal padding for cards and form grids, 22px for page/toolbar edges, and 28px between major page regions (`.region + .region`).

That last step is the one that carries grouping. Regions on a page (an alert, a row of summary tiles, the detail panels) share one surface and have no divider between them, so the only thing separating them is the gap — and at a uniform 16px a summary tile sits exactly as close to the alert above it as to its own sibling tile, which flattens the page into one undifferentiated stack. Inter-region spacing must stay visibly larger than the intra-region gap.

A third, content-driven breakpoint at **640px** governs the list-row component specifically (`.row-item`): below it, a row cannot hold a real book title and a status/actions column side by side, so the status group moves to its own line beneath the title. This threshold comes from the row's own content, not a device class — which is why it sits between the two shell breakpoints rather than replacing either.

Touch targets expand under `@media (pointer: coarse)`: buttons and pagination controls grow from 30px to 44px minimum height, matching the platform guidance for phones.

## Elevation & Depth

Layered with native depth: two distinct depth languages for two different jobs, not one shadow scale used everywhere. Resting surfaces (panels, cards, stat tiles, book cards) use soft, ambient shadows that barely lift them off the window background — depth is a hint, not a statement. Floating/overlay chrome (the sidebar, the sticky toolbar, the account menu popover, confirmation sheets, and the glass icon buttons for calendar/reminder actions) instead uses `backdrop-filter: saturate(180%) blur(...)` frosted-glass translucency, tinting and blurring whatever scrolls behind it rather than sitting as an opaque layer on top.

### Shadow Vocabulary
- **shadow-sm** (`0 1px 2px rgba(0,0,0,0.07), 0 0 0 0.5px rgba(0,0,0,0.05)`): resting panels, cards, stat tiles, book cards.
- **shadow-md** (`0 2px 8px rgba(0,0,0,0.09), 0 0 0 0.5px rgba(0,0,0,0.05)`): hover-lifted cards/stats, the auth card.
- **shadow-lg** (`0 12px 40px rgba(0,0,0,0.20), 0 0 0 0.5px rgba(0,0,0,0.10)`): menus, confirmation sheets, the open mobile sidebar drawer.
- **shadow-btn** (`0 1px 1.5px rgba(0,0,0,0.10), inset 0 0.5px 0 rgba(255,255,255,0.35)`): every default button — a hairline highlight on top plus a whisper of drop shadow, the thing that makes a flat control read as physically pressable.

### Named Rules
**The Glass-Is-Chrome Rule.** Frosted-glass blur is reserved for floating navigational/overlay chrome — sidebar, toolbar, menus, sheets, the round glass icon buttons — never for resting content surfaces. A panel or card is always opaque; only things that float over content get to blur it.
**The No-Blur Fallback Rule.** Every `backdrop-filter` use ships an `@supports not` fallback to a flat, opaque surface color — never a transparent layer with no blur, which would read as a rendering bug rather than a deliberate flat state.

## Shapes

Corner radius follows a five-step scale (4 / 6 / 8 / 12 / 16px) plus a full pill (999px) for badges and count indicators — the macOS Big Sur+ geometry of rounder-than-web-default but never fully rounded except on true pills and circular controls (avatar, glass icon buttons, the traffic-light dots). Borders are hairline (0.5–1px) and low-contrast, used to separate rather than to frame — most surfaces rely on background-color and shadow to read as distinct, not a border.

## Components

### Buttons
- **Shape:** 6px radius by default (`--r-sm`), 8px on large buttons (`--r-lg` variant), fully round only for icon-only glass buttons.
- **Primary:** system blue fill (`#0069D9`), white text, `shadow-btn`. Hover darkens to `#0059B8`.
- **Secondary (default `.btn`):** Surface Raised background, hairline border, `shadow-btn` — the same physical button shape as primary, just neutral instead of filled.
- **Danger / Success:** neutral button shape, text and hover-tint recolored to system red / accessible forest — used for renew/return/delete actions, never as a filled button.
- **Glass:** round, frosted, tinted with the accent color — reserved specifically for secondary floating actions like "add to calendar."
- **Press state:** every button scales to 0.975 on `:active` — a small physical squash that reinforces "this is a real control," not just a color change.
- **Touch:** grows to 44px minimum height under coarse-pointer media query.

### Cards / Containers
- **Corner style:** 12px radius (`--r-lg`).
- **Background:** Content White; no border, `shadow-sm` at rest.
- **Shadow strategy:** see Elevation — lifts to `shadow-md` with a 1px translateY on hover only where the card is a link (stat tiles, book cards).
- **Internal padding:** 16px body, with a hairline-separated header row for panels that have one.

### Inputs / Fields
- **Style:** Content White background, hairline border, 6px radius, 30px min height (44px on coarse pointers).
- **Focus:** border switches to system blue plus a 3px soft blue glow (`box-shadow: 0 0 0 3px` of the blue-soft token) — no color-only focus state; the glow is the primary signal.
- **Checkboxes/radios:** native elements themed via `accent-color`, not custom markup — keeps real keyboard/AT behavior for free.

### Navigation
- **Sidebar link:** 6px radius, transparent at rest, active state fills with system blue and switches text/icon to white — the same filled-selection language as a primary button, reused for "this is where you are."
- **Bottom tab bar (member/phone only):** fixed, frosted-glass, iOS-style. Active tab uses system-blue text (the text-tuned token, not the fill-tuned one — see Named Rules). Unread-style red badges for active loans/reservations.
- **Breadcrumbs:** sit directly on Window Gray rather than a content panel, so they use `accent-hover` in light mode and plain `accent` in dark mode — the one place the two blue tokens swap roles, because Window Gray's contrast math differs from Content White's.

### Book Cover (signature component)
No cover-art pipeline exists, so every book gets a deterministic gradient identity plus its title's initial — the same trick Apple Music/Podcasts/Contacts use for items without real artwork. The hue is derived from the book's ISBN; lightness is capped at 30%/18% (not more vivid) specifically because the hue rotates through the full wheel including yellow, and WCAG's luminance weighting makes yellow read far "brighter" than blue or red at equal HSL lightness — this cap keeps white text at 4.7:1 or better across all 360 hues, verified, not assumed.

### Category Badge
A second use of the same deterministic-hue trick as Book Cover, this time keyed off the book's category string instead of its ISBN, so "Fiction" reads as the same color everywhere without a hand-maintained category→color map — this is the system's **data category** role (a role the semantic red/amber/forest/teal ladder doesn't cover, since that ladder means urgency, not subject matter). Soft tinted background, saturated text — the same visual grammar as the other badge variants (`badge-red`, `badge-green`, etc.), just hue-parametrized instead of fixed. Light-mode text lightness is capped at 26% and dark-mode text lightness floored at 78%, each independently walked across all 360 hues to guarantee ≥4.5:1 (worst case 4.66:1 light, 6.16:1 dark) — the same rigor as Book Cover's own cap. A book with no category gets the plain neutral `.badge`, not a colored one: color here means "this is a real category," so the absence of one should look like absence, not get an arbitrary hue.

### Sheet (signature component)
A modal confirmation dialog styled after macOS's native sheet: centered near the top of the viewport (not vertically centered — it visually "drops from" the toolbar), scale+fade transition, always names the exact record being acted on rather than a generic "are you sure?" Reserved for destructive/consequential actions (delete, renew, cancel reservation).

### Named Rules
**The Explain-the-Block Rule.** When a control is disabled or an action is unavailable (renewal, reservation), the interface surfaces the specific reason as copy near the control rather than leaving a silently disabled button — this is a component behavior pattern, not just a copy guideline.

## Do's and Don'ts

### Do:
- **Do** keep color meaning-only: system blue for selection/primary/links, red/amber/forest/teal for status — never decorative color blocking on neutral surfaces.
- **Do** re-derive every color independently for dark mode and verify it against real WCAG contrast math; don't dim or invert.
- **Do** use frosted-glass blur only for floating/overlay chrome, and always ship a flat opaque `@supports not` fallback.
- **Do** collapse all motion under `prefers-reduced-motion: reduce` — every transition and animation in this system already does.
- **Do** keep the librarian (admin) shell desktop-only and the borrower (member) shell phone-optimized; treat them as two shells sharing one token set, not one responsive layout.
- **Do** name the exact record in any destructive-action confirmation sheet.

### Don't:
- **Don't** introduce a second brand accent alongside system blue — Muted Violet carries the roster/people lane and nothing else; it is not an invitation to add a second "brand" color.
- **Don't** use `ink-tertiary` for a real value. It sits below the AA floor by design; see The Tertiary-Is-Not-Data Rule.
- **Don't** use the fill-tuned accent token (`accent-fill`) as text color, or the text-tuned token (`accent`) as a background holding white text — they diverge in dark mode and this mix-up has already caused real contrast bugs (breadcrumbs, tab-bar labels).
- **Don't** add heavy drop shadows, flat Material-style colorful cards, or ripple/elevation effects — depth here is either a soft ambient hint or frosted glass, never a loud statement.
- **Don't** disable a control without explaining why next to it.
- **Don't** depend on a CDN, web font, icon font, or external asset for anything in this system — every icon is inline SVG and every font is a system stack, by design, so the app renders identically offline.
