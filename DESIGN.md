# Folio Terminal — Warm Paper (Light)

Portfolio analytics and shareable stock baskets for Indian equity investors.
The feeling is a **printed brokerage statement**, not a trading terminal: warm paper,
one ink colour for action, numbers that sit still and are easy to read.

Two hard constraints shape every decision here:

1. **No build step.** Five standalone HTML files, vanilla CSS + JS, no npm, no framework.
   Pages must open from `file://` so a basket can be emailed as two files and double-clicked.
   This rules out component libraries (shadcn, Radix, Tailwind) — their *design language*
   is borrowed, their runtime is not.
2. **No server.** No price feed, no login, no telemetry. Prices come from the user.

---

## Platform

- **Web, desktop-first**, degrading cleanly to 375px. Nav scrolls horizontally rather than wrapping.
- Content widths vary by page and that is intentional: prose reads narrow, data reads wide.
  `friends` 720 · `onboarding` 760 · `index` 880 · `basket` 1000 · `dashboard` 1280.
  **The nav must not inherit these widths** — see Chrome below.

---

## Palette

Every value below is measured against the **darkest surface it can land on** (`--bg #e8e8de`),
because that is the binding constraint. All text tokens clear **WCAG AA 4.5:1**.

### Surfaces
| Token | Hex | Role |
|---|---|---|
| `--bg` | `#e8e8de` | page — warm grey paper |
| `--panel` | `#fbfaf6` | cards, nav bar |
| `--panel2` | `#f4f2ea` | insets, code, table hover |
| `--hair` | `#e2e0d4` | hairline dividers, card borders |
| `--hair2` | `#ccc9ba` | input borders (needs to be seen) |

### Ink — all AA-verified
| Token | Hex | On `--bg` | Role |
|---|---|---|---|
| `--tx` | `#1b1b19` | 14.9 | headings, figures, primary text |
| `--tx2` | `#5b5a50` | **5.63** | body copy, descriptions, labels — the workhorse |
| `--tx3` | `#67665b` | **4.69** | footers, placeholders, timestamps |

### Accents — one green for action, semantics for money
| Token | Hex | On `--bg` | White on it | Role |
|---|---|---|---|---|
| `--em` | `#0f6b42` | **5.32** | **6.56** | primary action, links, active nav, gains |
| `--ox` | `#b52d23` | **5.06** | 6.24 | losses, destructive, blocking errors |
| `--gold` | `#856011` | **4.63** | — | warnings, "below minimum" notices |
| `--blue` | `#2b5fc4` | 4.9 | — | neutral category fill (charts only) |

> **Do not lighten these.** The previous palette (`--tx2 #87867a`, `--em #12784a`,
> `--ox #c8352a`, `--gold #a8791a`) looked tasteful and failed AA on every surface —
> body copy sat at **2.98:1**. Muted-grey-on-cream is the standard way a warm light
> theme fails accessibility, because the aesthetic goal and the contrast goal pull
> in opposite directions. Verify with a luminance calculation, never by eye.

---

## Type

**Inter** for everything, `system-ui` fallback. **No serif** — a serif display face was
tried and explicitly rejected; it read as a magazine, not a statement.
**`ui-monospace`** for money, symbols, tickers, and API keys — anything meant to be
compared down a column or copied exactly.

| Role | Size | Weight | Notes |
|---|---|---|---|
| Page title | 29–34px | 800 | `letter-spacing:-.02em` |
| Section label | 11.5px | 600 | uppercase, `.13em` tracking, hairline rule after |
| Body | 15–16.5px | 400 | `line-height` 1.55–1.6 |
| Card / step body | 13.5–14px | 400 | `--tx2` |
| Table cell | 13.5px | 400 | mono for numerals |
| Micro / footer | 11–12.5px | 400 | `--tx3` |

Money always uses **tabular numerals, right-aligned**, with `--em`/`--ox` for sign.
Never colour alone: a loss shows a `−` as well as red.

---

## Geometry

One radius scale. Before this existed the app used **14 different values** (2,3,5,6,8,9,
10,11,12,13,14,16,18,20,999), which is most of why it read as homemade.

```css
--radius:10px;        /* base — buttons, inputs, alerts, nav items */
--radius-xs:3px;      /* chart segments, tiny bars */
--radius-sm:6px;      /* inline code, chips, compact buttons */
--radius-md:12px;     /* nested panels */
--radius-lg:16px;     /* cards, main panels */
--radius-full:999px;  /* pills, badges */
```

Spacing: `4 / 8 / 12 / 16 / 24 / 32`. Elevation is minimal — one soft card shadow
(`0 1px 2px rgba(0,0,0,.04), 0 10px 26px -12px rgba(0,0,0,.10)`); depth otherwise comes
from surface tone and hairlines, not borders stacked on borders.

---

## Chrome

The nav is **full-bleed, outside the content wrapper**, with its own fixed inner width:

```css
.ftbar{width:100%;border-bottom:1px solid var(--hair);background:var(--panel)}
.ftnav{max-width:1180px;margin:0 auto;flex-wrap:nowrap;overflow-x:auto;padding:9px 20px}
.ftnav a{line-height:1}   /* else each page's body line-height resizes the bar */
```

**Verified 1180 × 52px on all five pages.** Two separate bugs made it "reshape":
living inside `.wrap` (width changed per page) and inheriting `body` line-height
(height changed by 1.3px per page). Both are content-jumping, not animation problems.

---

## Motion

One timing token, used everywhere: **170ms `cubic-bezier(.22,.61,.36,1)`**.

- Hover **lifts 1px** (`translateY`). Never `scale` — it shifts layout.
- **One** entrance animation per user action (the result panel), not per element.
- `:focus-visible` gets a 2px ring offset by 2px from the element, in `--em`.
- Full `prefers-reduced-motion: reduce` block disables all of it.

---

## Components

- **Buttons** — size variants only, radius constant: `sm` 32px · default 36px · `lg` 44px+
  for the single primary action on a page. Disabled = 50% opacity + `pointer-events:none`.
- **Inputs** — 36px min height, `--hair2` border, `--em` border + soft glow on focus.
  Textareas holding JSON size to their content, not a fixed 3 rows.
- **Tables** — 40px rows, horizontal hairlines only, no vertical rules, muted 500-weight
  heads. Denser than a typical data table because portfolios run long.
- **Alerts** — `--gold` for "you can't do this yet" (below basket minimum),
  `--ox` for "this failed", `--em` for confirmation. Always say what to do next.
- **Icons** — inline SVG, 24×24 viewBox, `stroke:currentColor`, 1.9 stroke width.
  **Never emoji.** They render differently on every platform.

---

## Principles

1. **Buttons, not commands.** Every capability is reachable by clicking. A Python CLI
   exists alongside, but the web app must never require it.
2. **Weights travel, share counts don't.** A basket is percentages plus reference prices.
   Never render a shared basket as somebody else's share counts.
3. **Block, don't silently degrade.** Below a basket's minimum, refuse and show workable
   amounts. Quietly dropping the expensive stock produces a different portfolio.
4. **Say where data goes — every time it's asked for.** "Runs entirely in your browser,
   nothing uploaded" appears next to any input touching holdings or an API key.
5. **State beats events.** Share the current target basket, not a rebalance diff — a diff
   is meaningless without the recipient's prior state.
6. **Never dark mode.** Explicitly rejected. This is a light, warm, paper product.
7. **Not advice.** Every page that produces orders says so, and nothing is placed
   without the user confirming in their broker.
