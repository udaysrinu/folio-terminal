#!/usr/bin/env python3
"""
Tradebook → Dashboard pipeline.

USAGE
  python3 build_dashboard.py <tradebook.xlsx|.csv> [options]

OPTIONS
  --holdings holdings.json   Live holdings (from Kite get_holdings) for unrealised P&L
  --pre <amount>             Pre-window booked realised P&L not in this file (e.g. 120000)
  --out live.json            Output data file the dashboard reads (default: live.json)
  --updated "TEXT"           "Last updated" stamp shown on the dashboard

WHAT IT DOES
  1. Parses a Zerodha equity tradebook (XLSX or CSV), auto-detecting the header row.
  2. FIFO-matches buys↔sells per symbol → realised round-trips (entry, exit, qty, P&L, %, hold days).
  3. Computes analytics: profit factor, win rate, reward:risk, expectancy, max drawdown,
     monthly P&L, net-by-counter, and a CUMULATIVE realised P&L curve (with optional pre-window base).
  4. Merges live holdings (if provided) for unrealised P&L, grouping, day-change, stop-loss.
  5. Writes a single live.json that dashboard.html renders.

The dashboard (dashboard.html) is a static template — it only reads live.json.
Re-run this script with a new file and refresh the browser; nothing else changes.
"""
import sys, json, argparse, csv, os
from collections import defaultdict, deque
from datetime import datetime

# ---- column aliases so it works across Zerodha/other broker exports ----
COL = {
    'symbol': ['symbol', 'tradingsymbol', 'instrument', 'scrip', 'stock'],
    'date':   ['trade date', 'date', 'order execution time'],
    'type':   ['trade type', 'transaction type', 'type', 'buy/sell', 'side'],
    'qty':    ['quantity', 'qty'],
    'price':  ['price', 'trade price', 'avg price', 'average price'],
    'time':   ['order execution time', 'trade date', 'time', 'date'],
}
# broker CSVs use snake_case where XLSX uses spaces — accept both
COL = {k: sorted({*v, *(a.replace(' ', '_') for a in v)}, key=len, reverse=True)
       for k, v in COL.items()}

def find_col(headers, key):
    low = [str(h).strip().lower() if h is not None else '' for h in headers]
    for alias in COL[key]:
        if alias in low:
            return low.index(alias)
    return None

def load_rows(path):
    """Return list of header-mapped trade dicts from xlsx or csv."""
    ext = os.path.splitext(path)[1].lower()
    rows = []
    if ext in ('.xlsx', '.xls'):
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    else:  # csv
        with open(path, newline='', encoding='utf-8-sig') as f:
            rows = [r for r in csv.reader(f)]

    # auto-detect header row: the row containing a 'symbol'-like AND a 'quantity'-like cell
    hdr_idx = None
    for i, r in enumerate(rows[:40]):
        low = [str(c).strip().lower() if c is not None else '' for c in r]
        if any(a in low for a in COL['symbol']) and any(a in low for a in COL['qty']):
            hdr_idx = i; break
    if hdr_idx is None:
        raise SystemExit("Could not find a header row with Symbol + Quantity columns.")

    headers = rows[hdr_idx]
    ci = {k: find_col(headers, k) for k in COL}
    if ci['symbol'] is None or ci['qty'] is None or ci['type'] is None or ci['price'] is None:
        raise SystemExit(f"Missing required columns. Found header: {headers}")

    trades = []
    for r in rows[hdr_idx + 1:]:
        if not r or ci['symbol'] >= len(r) or r[ci['symbol']] in (None, ''):
            continue
        try:
            qty = float(r[ci['qty']]); price = float(r[ci['price']])
        except (TypeError, ValueError):
            continue
        ttype = str(r[ci['type']]).strip().lower()
        ttype = 'buy' if 'b' in ttype[:1] else 'sell'  # buy/b → buy, sell/s → sell
        date = str(r[ci['date']]).strip() if ci['date'] is not None else ''
        time = str(r[ci['time']]).strip() if ci['time'] is not None else date
        trades.append({'sym': str(r[ci['symbol']]).strip(), 'date': date[:10] if date else '',
                       'type': ttype, 'qty': qty, 'price': price, 'time': time})
    return trades

def fifo(trades):
    """FIFO-match per symbol → round-trips + per-symbol realised + pre-window-sold flags."""
    by = defaultdict(list)
    for t in trades: by[t['sym']].append(t)
    for s in by: by[s].sort(key=lambda x: x['time'])

    roundtrips, realized, buyq, sellq, openq, pre_sold = [], defaultdict(float), defaultdict(float), defaultdict(float), {}, defaultdict(float)
    for sym, tl in by.items():
        lots = deque()
        for t in tl:
            q, p = t['qty'], t['price']
            if t['type'] == 'buy':
                buyq[sym] += q; lots.append([q, p, t['date']])
            else:
                sellq[sym] += q
                while q > 0 and lots:
                    lq, lp, ld = lots[0]; m = min(q, lq)
                    try: hd = (datetime.fromisoformat(t['date']) - datetime.fromisoformat(ld)).days
                    except Exception: hd = 0
                    roundtrips.append({'sym': sym, 'entry': ld, 'exit': t['date'], 'qty': m,
                                       'buy_px': lp, 'sell_px': p, 'pnl': (p-lp)*m,
                                       'ret': (p-lp)/lp*100 if lp else 0, 'hold': hd})
                    realized[sym] += (p-lp)*m
                    lq -= m; q -= m
                    if lq == 0: lots.popleft()
                    else: lots[0][0] = lq
                if q > 0: pre_sold[sym] += q
        openq[sym] = sum(l[0] for l in lots)
    return roundtrips, dict(realized), dict(pre_sold)

def build(args):
    trades = load_rows(args.tradebook)
    rt, realized, pre_sold = fifo(trades)
    rt_sorted = sorted(rt, key=lambda x: (x['exit'], x['entry']))

    wins = [t for t in rt if t['pnl'] > 0]; losses = [t for t in rt if t['pnl'] < 0]
    gw = sum(t['pnl'] for t in wins); gl = abs(sum(t['pnl'] for t in losses))
    inwindow = sum(t['pnl'] for t in rt)
    pre = float(args.pre or 0)
    cum_realized = inwindow + pre

    # cumulative realised curve (running total over exit dates), with optional pre-window base
    byday = defaultdict(list)
    for t in rt_sorted: byday[t['exit']].append(t)
    cumcurve = []
    run = pre
    if pre: cumcurve.append({'d': 'Pre-window', 'cum': round(pre), 'day_pnl': round(pre), 'label': 'Booked earlier'})
    for day in sorted(byday):
        dp = sum(t['pnl'] for t in byday[day]); run += dp
        cumcurve.append({'d': day, 'cum': round(run), 'day_pnl': round(dp), 'label': f"{len(byday[day])} trade(s)"})

    # equity curve (in-window only, from 0) + max drawdown
    eq, c = [], 0.0
    for day in sorted(byday):
        c += sum(t['pnl'] for t in byday[day]); eq.append({'d': day, 'cum': round(c)})
    peak = 0; maxdd = 0
    for p in eq:
        peak = max(peak, p['cum']); maxdd = min(maxdd, p['cum']-peak)

    monthly = defaultdict(float)
    for t in rt: monthly[t['exit'][:7]] += t['pnl']
    rtsym = defaultdict(float); rtcnt = defaultdict(int)
    for t in rt: rtsym[t['sym']] += t['pnl']; rtcnt[t['sym']] += 1

    out = {
        'updated': args.updated,
        'inwindow': round(inwindow), 'pre_april': round(pre), 'cum_realized': round(cum_realized),
        'gross_win': round(gw), 'gross_loss': round(-gl),
        'pf': round(gw/gl, 2) if gl else 0, 'wr': round(len(wins)/len(rt)*100) if rt else 0, 'nrt': len(rt),
        'avg_w': round(gw/len(wins)) if wins else 0, 'avg_l': round(-gl/len(losses)) if losses else 0,
        'nwin': len(wins), 'nloss': len(losses), 'max_dd': round(maxdd),
        'roundtrips': sorted(rt, key=lambda x: x['pnl']),
        'rtsym': sorted([{'s': k, 'v': round(v), 'n': rtcnt[k]} for k, v in rtsym.items()], key=lambda x: x['v']),
        'monthly': sorted([{'m': k, 'v': round(v)} for k, v in monthly.items()], key=lambda x: x['m']),
        'curve': eq, 'cumcurve': cumcurve, 'pre_sold': pre_sold,
        # raw trades so the in-browser "Never Sold" counterfactual works on first load
        '_trades': [{'sym': t['sym'], 'date': t['date'], 'type': t['type'],
                     'qty': t['qty'], 'price': t['price'], 'time': t['time']} for t in trades],
    }

    # ---- merge live holdings if provided ----
    if args.holdings and os.path.exists(args.holdings):
        H = json.load(open(args.holdings))
        unreal = sum(h['pnl'] for h in H)
        invested = sum(h['q']*h['avg'] for h in H); mkt = sum(h['q']*h['ltp'] for h in H)
        grp = defaultdict(lambda: [0.0, 0.0])
        for h in H: grp[h['grp']][0] += h['pnl']; grp[h['grp']][1] += h['q']*h['ltp']
        attention = []
        for h in H:
            if h.get('sl'):
                dist = (h['ltp']-h['sl'])/h['ltp']*100
                if dist < 12: attention.append({'t': 'SL', 's': h['s'], 'msg': f"{dist:.1f}% from stop ₹{h['sl']}", 'sev': 'hot' if dist < 7 else 'warn'})
            if abs(h.get('day', 0)) >= 2.5: attention.append({'t': 'MOVE', 's': h['s'], 'msg': f"{'+' if h['day']>=0 else ''}{h['day']:.1f}% today", 'sev': 'pos' if h['day'] > 0 else 'neg'})
        out.update({
            'holdings': sorted(H, key=lambda x: -x['pnl']),
            'unreal': round(unreal), 'invested': round(invested), 'mkt': round(mkt),
            'combined': round(cum_realized + unreal),
            # today's P&L across the book; dashboard shows this next to unrealised
            'day_total': round(sum(h.get('dpnl', 0) or 0 for h in H)),
            'groups': sorted([{'g': k, 'pnl': round(v[0]), 'val': round(v[1])} for k, v in grp.items()], key=lambda x: -x['val']),
            'attention': attention,
        })
    else:
        out.update({'holdings': [], 'unreal': 0, 'invested': 0, 'mkt': 0,
                    'combined': round(cum_realized), 'day_total': 0,
                    'groups': [], 'attention': []})

    json.dump(out, open(args.out, 'w'))
    print(f"✓ {args.out} written")
    print(f"  {len(trades)} fills → {len(rt)} round-trips")
    print(f"  In-window realised: ₹{inwindow:,.0f}" + (f"  +  pre-window ₹{pre:,.0f}  =  cumulative ₹{cum_realized:,.0f}" if pre else ""))
    print(f"  Win {out['wr']}% · PF {out['pf']} · max DD ₹{maxdd:,.0f}")
    if out['holdings']:
        print(f"  + {len(out['holdings'])} live holdings · unrealised ₹{out['unreal']:,.0f} · combined ₹{out['combined']:,.0f}")
    print(f"\n  Refresh the dashboard tab — it reads {args.out} automatically.")

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description="Zerodha tradebook → dashboard data pipeline")
    ap.add_argument('tradebook', help='Path to tradebook .xlsx or .csv')
    ap.add_argument('--holdings', help='Live holdings JSON (from Kite get_holdings)')
    ap.add_argument('--pre', type=float, default=0, help='Pre-window booked realised P&L')
    ap.add_argument('--out', default='live.json', help='Output data file (default live.json)')
    ap.add_argument('--updated', default=datetime.now().strftime('%Y-%m-%d %H:%M') if False else 'updated now', help='Last-updated stamp')
    build(ap.parse_args())
