---
name: sharecase
description: Use when analysing a Zerodha Kite portfolio, building the folio dashboard from a tradebook, recovering which holdings belong to which smallcase/basket via order tags, or sharing/sizing a weighted stock basket. Triggers on "build my dashboard", "analyse my portfolio", "which smallcase is this stock from", "share this basket", "size this basket to my capital", "export my holdings", "realised P&L", "tradebook".
---

# sharecase

Local Kite portfolio analytics + portable basket sheets. Full detail in `README.md` — read it before a first run. This file is the operating order.

## Before anything

1. **Check Kite MCP is authed** — call `get_profile`. If it errors or *hangs for minutes*, the session expired (daily, ~6am IST): reconnect the server, then `login`, and wait for the user to confirm the browser redirect completed.
2. **Never place an order without showing the full list and getting explicit confirmation.** Sizing is arithmetic; execution is real money.

## Build / refresh the dashboard

```bash
python3 build_dashboard.py <tradebook.xlsx|.csv> --holdings _holdings.json --pre <amount>
python3 -m http.server 8787      # then open dashboard.html
```

- `_holdings.json` is built from `get_holdings` (schema in README). Set each position's `grp` from `_smallcase_map.json` so the dashboard splits by basket.
- The tradebook must be downloaded manually from Console — **there is no API for it**. If the user's realised numbers look stale, that's why: tell them to re-download and drag it onto the page.
- `--pre` is realised P&L booked before the tradebook window (from Console → Reports → P&L).

## Recover basket identity (time-critical)

Kite holdings carry **no** basket field. The link exists only in **order tags**, and `get_orders` returns **today's orders only**.

1. On the day a basket executes, call `get_orders`.
2. Group orders by their **shared** second tag (each order also has a unique random first tag).
3. Persist to `_smallcase_map.json` (schema in README) — **this is unrecoverable if missed.**

If the user mentions a smallcase/basket bought today, capture this *before* doing anything else.

**When the user executes a received sheet themselves,** skip discovery entirely: choose a tag,
pass it on every `place_order` call, then `basket.py record <tag> "<label>" fills.json` from the
actual fills. Self-set tags never expire, so this path has no time pressure.

## Share / size a basket

```bash
python3 basket.py export <tag>              # your basket  → portable sheet
python3 basket.py md     <sheet.json>       # sheet        → markdown for humans/LLMs
python3 basket.py orders <sheet.json> <amt> # anyone's sheet → your order list
python3 basket.py demo                      # self-check
```

Sheets carry **weights, not share counts** — weights survive different capital and different prices.

## Own baskets / rebalancing

```bash
python3 basket.py new "<label>" prices.json [weights.json]   # yours to share, no subscription IP
python3 basket.py rebalance <sheet.json> <holdings.json>     # drift + correcting orders
```

Before acting on a drift figure, check `_smallcase_map.json`: a stock held via two baskets shows
one merged quantity in Kite, which fabricates drift against either basket's target. Say so rather
than issuing the trade.

## Recipient has no MCP / no terminal

Send them `basket.html` plus the sheet `.json`. It runs from `file://`, sizes the basket to their
capital, exports copy-paste orders or broker CSV, and will rebalance against a holdings XLSX/CSV.
No Python, no server, no broker connection.

## Executing an order list

- `exchange=NSE`, `product=CNC`, `order_type=LIMIT` for delivery.
- **Prefer LIMIT over MARKET on illiquid names.** Check `get_quotes` depth first — thin small-caps have shallow books and a market order walks them.
- **Reconcile sell exposure before placing.** GTTs are *not* validated against holdings at placement, so a new stop plus existing GTTs can exceed shares held and oversell. Sum all pending sells first.
- A GTT is a **static** trigger, not a trailing stop. "Trailing" means the agent ratchets the trigger up manually — never down.

## Honest-reporting rules

- Report realised P&L as **net** (gross profit − gross loss), and say when the tradebook is stale.
- The "Never Sold" view is hindsight only — it cannot price the losses that stops prevented. Don't present it as proof an exit was wrong.
- Basket constituents from a **paid** subscription are the provider's IP. Sharing sheets derived from one may breach their terms; flag it once, then respect the user's decision.
