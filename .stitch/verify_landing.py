#!/usr/bin/env python3
"""Guard the landing page's THE IDEA table: the numbers in the HTML must be the
numbers the sizing rule actually produces. If someone edits the copy, this fails."""
import math, re, sys, pathlib

P = {'TCS': 3180, 'RELIANCE': 1310, 'HDFCBANK': 1745}   # illustrative prices
W = {'TCS': 25, 'RELIANCE': 30, 'HDFCBANK': 45}         # target weights %

def size(amount):
    rows = {s: round(amount * W[s] / 100 / P[s]) for s in W}
    tot = sum(rows[s] * P[s] for s in W)
    return rows, {s: 100 * rows[s] * P[s] / tot for s in W}

html = pathlib.Path(__file__).parent.parent.joinpath('index.html').read_text()
bad = []
for amt in (400000, 80000):
    sh, pct = size(amt)
    for s in W:
        if not re.search(rf'{s}</td><td class="r mono">{sh[s]}</td>', html):
            bad.append(f'{s} @ {amt}: html should say {sh[s]} shares')
        if f'{pct[s]:.1f}%' not in html:
            bad.append(f'{s} @ {amt}: html should say {pct[s]:.1f}%')

mn = math.ceil(max(P[s] / (W[s] / 100) for s in W))
if f'{mn:,}' not in html:
    bad.append(f'minimum should read Rs {mn:,}')

_, p4 = size(400000); _, p8 = size(80000)
d4 = max(abs(p4[s] - W[s]) for s in W); d8 = max(abs(p8[s] - W[s]) for s in W)
if d8 <= d4:
    bad.append('claim broken: smaller capital must drift more')
if f'{d8:.1f}' not in html or f'{d4:.1f}' not in html:
    bad.append(f'drift figures should read {d8:.1f} and {d4:.1f} points')

print('\n'.join(bad) if bad else
      f'landing table OK: drift {d4:.1f}pp @4L vs {d8:.1f}pp @80k, minimum Rs {mn:,}')
sys.exit(1 if bad else 0)
