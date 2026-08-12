# Folio Terminal

Local portfolio analytics for Zerodha Kite, plus a portable format for sharing weighted stock baskets.

Three things it does:

1. **Dashboard** — turn a broker tradebook into FIFO-matched realised P&L, an equity curve, basket concentration, and a "what if I never sold" counterfactual. Single HTML file, no build step.
2. **Basket capture** — work out which holdings belong to which smallcase/basket by reading Kite **order tags** (the only place that link exists).
3. **Basket interchange** — export a basket as a portable sheet, and size *anyone's* sheet to *your* capital as a concrete order list.

Everything runs on your machine. No account, no server, no telemetry.

---

## Privacy

This repo contains **tooling and fake samples only**. Your real data — holdings, tradebook, basket constituents — is gitignored and never committed:

```
_holdings.json  _smallcase_map.json  live.json  *_sheet.json  *_BASKET.md
tradebook*.xlsx  tradebook*.csv  taxpnl*.xlsx  JOURNAL.md  ...
```

If you fork this, keep it that way. Basket constituents from a **paid** subscription are the subscription provider's IP — check their terms before sharing sheets with anyone.

---

## Requirements

Python 3.10+. Only dependency is `openpyxl`, and only if you feed it `.xlsx`:

```bash
pip install openpyxl        # skip if you only use CSV
```

---

## Quick start

```bash
# 1. build the data file from a tradebook (+ optional holdings)
python3 build_dashboard.py samples/sample_tradebook.csv \
        --holdings samples/sample_holdings.json

# 2. serve it — browsers block fetch() over file://
python3 -m http.server 8787

# 3. open
open http://localhost:8787/dashboard.html
```

The page polls `live.json` every 30s. You can also **drag an XLSX/CSV straight onto the page** — it parses and FIFO-matches in the browser, no Python needed.

---

## Workflow 1 — Dashboard from a tradebook

```
tradebook.xlsx ─┐
                ├─▶ build_dashboard.py ─▶ live.json ─▶ dashboard.html
holdings.json ──┘      FIFO + analytics
```

```bash
python3 build_dashboard.py <tradebook.xlsx|.csv> [options]

  --holdings holdings.json   adds unrealised P&L, basket grouping, stop-loss rail
  --pre <amount>             realised P&L booked before this tradebook's window
  --out live.json            output file (default: live.json)
  --updated "TEXT"           timestamp shown in the header
```

Column names are auto-detected across brokers (both `Trade Type` and `trade_type` work). Get a tradebook from Zerodha Console → Reports → Tradebook.

### `holdings.json` format

```json
[{"s":"RELIANCE","q":25,"avg":2820.0,"ltp":2965.5,"pnl":3638,
  "grp":"Core","day":0.82,"sl":2650,"dpnl":604}]
```

| field | meaning |
|---|---|
| `s` `q` `avg` `ltp` `pnl` | symbol, qty, average buy, last price, unrealised P&L |
| `grp` | basket label — drives grouping, concentration bar, allocation tiles |
| `day` | today's % change · `dpnl` today's P&L in ₹ |
| `sl` | stop-loss trigger, or `null` — drives the distance-to-stop bars |

---

## Workflow 2 — Which holdings belong to which basket

**The problem:** Kite's holdings API returns a flat list. There is no basket/smallcase field, and holdings from different baskets plus direct buys of the same stock get merged into one average price. Zerodha have confirmed holding tags are Console-only, not on Kite Connect.

**The trick:** basket platforms place their orders through Kite with a **shared order tag**. The orders API *does* return tags. So the link exists — in the order book.

```jsonc
// GET /orders  — every order from one basket carries the same second tag
{"tradingsymbol":"INFY", "tags":["aB3xY9zQ", "BATCH_0004"]}
{"tradingsymbol":"TCS",  "tags":["kL7mN2pR", "BATCH_0004"]}
```

> ⚠️ **Kite Connect returns only the current day's orders.** Capture the tag on the day the basket executes, or the link is gone for good.

Save what you find as `_smallcase_map.json` (gitignored):

```json
{"batches": {"BATCH_0004": {
  "label": "My Basket", "grp": "Basket", "executed": "2026-08-12",
  "holdings": {"INFY": {"q": 50, "avg": 1420.5},
               "TCS":  {"q": 20, "avg": 3850.0}}}}}
```

Then set each holding's `grp` from that map when you build `holdings.json`, and the dashboard groups by basket automatically.

---

## Workflow 3 — Share a basket

```bash
python3 basket.py export BATCH_0004      # → BATCH_0004_sheet.json
python3 basket.py md BATCH_0004_sheet.json   # → BATCH_0004_sheet.md (human/LLM readable)
```

The sheet is the entire format — four fields, broker-agnostic:

```json
{"label": "My Basket", "asof": "2026-08-12",
 "weights": {"INFY": 60.0, "TCS": 40.0},
 "prices":  {"INFY": 1420.5, "TCS": 3850.0}}
```

It carries **weights, not share counts** — deliberately. Share counts are only valid at one capital size and one moment's prices; weights survive both.

---

## Workflow 4 — Size someone else's basket to your capital

```bash
python3 basket.py orders their_sheet.json 200000
```

```
Sample 4-stock basket  (sheet as of 2026-08-12)
Amount ₹200,000 · minimum for whole shares ₹14,808

Stock          Qty     Price      Value  note
--------------------------------------------------------
RELIANCE        20     2,966     59,310
TCS             14     3,702     51,829
HDFCBANK        29     1,712     49,657
NTPC           114       352     40,082
--------------------------------------------------------
TOTAL                           200,878  (100.4% deployed)
```

**Minimum basket size** is reported because whole shares are lumpy: if the priciest stock sits at a small weight, you need a certain total before you can buy even one share of it. Below the minimum, those names are explicitly `SKIP`-ed rather than silently skewing your weights.

```bash
python3 basket.py demo    # self-check on the minimum-unit + skip logic
```

---

## For agents (Kite MCP)

An LLM with Kite MCP access can run the whole loop. Suggested sequence:

| Step | Tool | Notes |
|---|---|---|
| 1 | `login` | session expires daily (~6am IST); re-auth needed |
| 2 | `get_orders` | **same day only.** Group by the shared second tag → basket constituents |
| 3 | `get_holdings` | current book. Same-day buys appear as `t1_quantity`, not `quantity` |
| 4 | `get_ltp` | refresh the sheet's `prices` before sizing |
| 5 | `basket.py orders <sheet> <amount>` | produces the order list |
| 6 | `place_order` | `exchange=NSE`, `product=CNC`, `order_type=LIMIT` |

Guidance worth following:

- **Prefer LIMIT to MARKET on illiquid names.** Thin small-caps have shallow books; a market order walks it. Check `get_quotes` depth first.
- **Never place orders without showing the list and getting explicit confirmation.** Sizing is arithmetic; execution is real money.
- **Reconcile before placing.** Total sell orders across all GTTs plus new orders must not exceed shares held, or you oversell. GTTs are *not* validated against holdings at placement time.
- **Snapshot order tags the day a basket executes.** There is no way to recover them later.

---

## Files

| File | Role |
|---|---|
| `build_dashboard.py` | tradebook → FIFO round-trips → `live.json` |
| `dashboard.html` | renders `live.json`; also parses XLSX/CSV in-browser |
| `basket.py` | `export` / `md` / `orders` / `demo` |
| `samples/` | fake data so everything runs out of the box |

---

## Limits

- **No basket-platform API.** Constituents and rebalance signals are not exposed to retail subscribers by any public API — hence the order-tag approach. Rebalances have to be re-captured each time they execute.
- **Merged averages.** A stock held via two baskets shows one blended average in Kite. Only your own capture preserves which shares came from where.
- **Realised P&L is only as fresh as your tradebook.** Holdings update live; round-trips don't. Re-download and re-run.
- **GTT is not a trailing stop.** Kite GTTs are static triggers; "trailing" means ratcheting the trigger yourself.

---

Not investment advice. No warranty. Verify every order before you place it.
