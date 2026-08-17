# sharecase — Mineral Paper, Blue Signal (Direction B)

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

Every value measured against the **darkest surface it can land on** (`--bg #E9EAE3`).
All text clears **WCAG AA 4.5:1**; verified across all five pages, 0 failures.

### Surfaces
| Token | Hex | Role |
|---|---|---|
| `--bg` | `#E9EAE3` | page — cooler mineral paper. **Never `#ffffff`** |
| `--panel` | `#FCFCF8` | cards, nav, ledger |
| `--panel2` | `#F3F4EE` | insets, code, row hover |
| `--rule` / `--hair` | `#BCC3B8` | ledger row rules — 1.75:1, deliberately visible |
| `--rule-strong` / `--hair2` | `#A6AFA2` | structural rules, input borders — 2.20:1 |

### Ink
| Token | Hex | On `--bg` |
|---|---|---|
| `--tx` | `#18211D` | 15.0 |
| `--tx2` | `#46534C` | 6.7 |
| `--tx3` | `#5C6A61` | 4.7 |

### The core rule: action ≠ outcome
| Token | Hex | Means |
|---|---|---|
| `--em` / `--action` | `#155A78` | **an action is possible** — buttons, focus rings, links, current nav, selected tabs/toggles, imported-file state, step numbers |
| `--gain` | `#0B5B3A` | **a financial result is positive** — positive drift, gains, success states |
| `--ox` | `#A52A22` | a financial result is negative, or destructive |
| `--gold` | `#7A4E00` | warnings ("below minimum") |

Green must **never** appear on a button, on navigation, or on a focus ring. Blue must never
mark a gain. This separation is the whole point of the direction — Indian fintech collapses
action and outcome into one colour, which is why every app in the category reads the same.
Verified mechanically: 0 green-backgrounded action elements across all pages.

Decorative accents (KPI stripes, source badges) are **neutral**, not a second blue.
`--blue #2b5fc4` survives only inside categorical chart maps, where multiple hues are the point.

Never colour alone: a negative figure carries a `−`, a positive one a `+`.

**One deliberate exception.** In the rebalance table the `ACTION` column shows **green BUY /
red SELL**. Strictly these are instructions, not outcomes, so the rule above would make them
neutral. Green-buy/red-sell is near-universal in trading interfaces and materially helps
scanning a mixed order list where mistaking a sell for a buy is expensive and irreversible.
The exception is limited to that one column; drift in the same table stays amber-on-attention
rather than green/red, because drift-from-target is a distance, not a direction.

---

## Type

Self-hosted latin subsets in `fonts/` (71 KB total), no CDN, so the pages work offline.

| Role | Face | Notes |
|---|---|---|
| Headings, wordmark | **Barlow Semi Condensed 600** | compressed, instrument-like; sentence case |
| Body, labels, UI | **IBM Plex Sans** 400/600 | technical, more deliberate than Inter |
| Every number | **IBM Plex Mono** 400/500 | `tabular-nums`, right-aligned in columns |

**No serif** and **no Inter** — Inter is the "gave up on typography" signal, and all three
competitors use a licensed sans, so a default face is what makes a tool look generic.

*Known tradeoff:* a single emailed `basket.html` has no `fonts/` beside it and falls back to
system sans. Functionality is unaffected. Send the folder, or the hosted URL, to keep the type.

---

## The two risks this direction takes

1. **The calculation is the hero.** `.readout` renders one monospace line —
   `₹4,00,000 → 4 stocks → ₹3,98,055 deployed → ₹1,945 left` — as an instrument readout, not a
   form in a card. Every competitor leads with charts and tickers; this leads with the
   transformation that is the product's actual job. Leftover cash is stated, never hidden.
2. **Holdings are a ledger, not tiles.** `.ledger` uses horizontal rules only, no vertical
   rules, no zebra fill, 38px rows, tiny uppercase letterspaced heads, drift shown with a sign.
   On screens under ~430px the ledger scrolls **inside its own card** so the page never scrolls
   sideways and no column is dropped.


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
