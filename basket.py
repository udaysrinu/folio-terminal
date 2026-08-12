#!/usr/bin/env python3
"""Portable basket interchange — share a weighted stock basket, size it to any capital.

  export <tag>                  build a shareable sheet from your captured basket
  md     <sheet.json>           render the sheet as markdown (human / LLM readable)
  orders <sheet.json> <amount> [--tag T]   size ANYONE's sheet to your capital
  record <tag> <label> <fills.json>        log an executed basket into the local map
  new    <label> <prices.json> [w.json] [--theme T] [--risk low|moderate|high]
  rebalance <sheet.json> <holdings.json>   drift vs target + the orders to correct it

Sheet schema (this is the whole format):
  {"label":"Basket name", "asof":"YYYY-MM-DD",
   "weights":{"SYM": 11.0, ...},     # percent, need not sum to exactly 100
   "prices" :{"SYM": 1543.4, ...}}   # reference price per symbol
"""
import json, sys

def load_sheet(path):
    s = json.load(open(path))
    for k in ("label", "weights", "prices"):
        if k not in s: sys.exit(f"sheet missing '{k}'")
    if miss := set(s["weights"]) - set(s["prices"]):
        sys.exit(f"no price for: {', '.join(sorted(miss))}")
    if bad := [k for k, v in s["prices"].items() if not v > 0]:
        sys.exit(f"price must be > 0 for: {', '.join(sorted(bad))}")
    tot = sum(s["weights"].values())
    if tot <= 0: sys.exit("weights must sum to more than zero")
    # weights are relative proportions — normalise so sizing matches what we report
    if abs(tot - 100) > 0.01:
        s["weights"] = {k: v / tot * 100 for k, v in s["weights"].items()}
    return s

def min_unit(w, p):
    """Smallest basket size where every symbol affords >=1 whole share."""
    return max(p[s] / (w[s] / 100) for s in w)

def size(sheet, amount):
    """→ ([(sym, qty, price, value, note)], total_cost, minimum_unit)"""
    w, p = sheet["weights"], sheet["prices"]
    rows, cost = [], 0.0
    for s in sorted(w, key=lambda x: -w[x]):
        q = round(amount * (w[s] / 100) / p[s])
        if q < 1:
            rows.append((s, 0, p[s], 0.0, "SKIP (below 1 share)")); continue
        cost += q * p[s]
        rows.append((s, q, p[s], q * p[s], ""))
    return rows, cost, min_unit(w, p)

def cmd_export(tag):
    b = json.load(open("_smallcase_map.json"))["batches"][tag]
    h = b["holdings"]
    inv = sum(v["q"] * v["avg"] for v in h.values())
    sheet = {"label": b["label"], "asof": b["executed"],
             "weights": {s: round(v["q"] * v["avg"] / inv * 100, 2) for s, v in h.items()},
             "prices":  {s: v["avg"] for s, v in h.items()}}
    out = f"{tag}_sheet.json"
    json.dump(sheet, open(out, "w"), indent=1)
    print(f"wrote {out}")

def cmd_md(path, tiers=(1, 2, 3)):
    s = load_sheet(path); w, p = s["weights"], s["prices"]
    mu = min_unit(w, p); amts = [mu * t for t in tiers]
    order = sorted(w, key=lambda x: -w[x])
    L = [f"# {s['label']} — order sheet", "",
         f"Weights as of {s.get('asof','?')}. "
         f"**Minimum for whole shares ≈ ₹{mu:,.0f}** (binding: {max(w, key=lambda x: p[x]/w[x])}).",
         "", "| Stock | Weight | Price | " + " | ".join(f"₹{a/1e5:.2f}L" for a in amts) + " |",
         "|---|---|---|" + "---|" * len(amts)]
    for sym in order:
        qs = [str(size(s, a)[0][order.index(sym)][1]) for a in amts]
        L.append(f"| {sym} | {w[sym]:.1f}% | ₹{p[sym]:,.0f} | " + " | ".join(qs) + " |")
    L += ["", "NSE · CNC (delivery) · market or limit. Re-run `orders` for live prices.",
          "Not investment advice.", ""]
    out = path.replace(".json", "") + ".md"
    open(out, "w").write("\n".join(L)); print(f"wrote {out}")

def cmd_new(label, prices_path, weights_path=None, theme=None, risk=None):
    """Build your own basket. Equal-weight unless you pass explicit weights."""
    prices = json.load(open(prices_path))                 # {"SYM": ltp}
    if weights_path:
        w = json.load(open(weights_path))
        tot = sum(w.values())
        w = {k: round(v / tot * 100, 2) for k, v in w.items()}   # normalise to 100
        if miss := set(w) - set(prices): sys.exit(f"no price for: {', '.join(sorted(miss))}")
    else:
        w = {k: round(100 / len(prices), 2) for k in prices}
    import datetime
    sheet = {"label": label, "asof": datetime.date.today().isoformat()}
    if theme: sheet["theme"] = theme
    if risk:
        if risk not in ("low", "moderate", "high"): sys.exit("risk: low|moderate|high")
        sheet["risk"] = risk
    sheet |= {"weights": w, "prices": {k: prices[k] for k in w}}
    eff = 1 / sum((v / sum(w.values())) ** 2 for v in w.values())   # 1/HHI
    out = label.lower().replace(" ", "_") + "_sheet.json"
    json.dump(sheet, open(out, "w"), indent=1)
    print(f"wrote {out} — {len(w)} stocks, "
          f"{'equal-weight' if not weights_path else 'custom weights'}, "
          f"min ₹{min_unit(sheet['weights'], sheet['prices']):,.0f}, "
          f"{eff:.1f} effective holdings")

def cmd_rebalance(sheet_path, holdings_path):
    """Compare what you hold against the sheet's target weights → correcting orders."""
    sh = load_sheet(sheet_path)
    H = {h["s"]: h for h in json.load(open(holdings_path))}
    w, p = sh["weights"], dict(sh["prices"])
    for sym in w:                                   # prefer live ltp from holdings
        if sym in H and H[sym].get("ltp"): p[sym] = H[sym]["ltp"]
    held = {sym: H.get(sym, {}).get("q", 0) for sym in w}
    value = sum(held[s] * p[s] for s in w)
    if value <= 0: sys.exit("you hold none of this basket — use `orders` to buy in")

    print(f"\n{sh['label']} — rebalance on ₹{value:,.0f} currently held")
    print(f"\n{'Stock':13}{'Now%':>7}{'Tgt%':>7}{'Drift':>8}{'Action':>7}{'Qty':>6}{'Value':>10}")
    print("-" * 58)
    buys = sells = 0.0
    for sym in sorted(w, key=lambda x: -w[x]):
        now = held[sym] * p[sym] / value * 100
        tgt_q = round(value * (w[sym] / 100) / p[sym])
        d = tgt_q - held[sym]
        act = "BUY" if d > 0 else "SELL" if d < 0 else "-"
        if d > 0: buys += d * p[sym]
        elif d < 0: sells += -d * p[sym]
        print(f"{sym:13}{now:>6.1f}%{w[sym]:>6.1f}%{now-w[sym]:>+7.1f}%"
              f"{act:>7}{abs(d):>6}{abs(d)*p[sym]:>10,.0f}")
    print("-" * 58)
    print(f"buy ₹{buys:,.0f} · sell ₹{sells:,.0f} · net ₹{buys-sells:+,.0f}")
    print("\nTag these orders too, so the basket stays groupable. Not investment advice.")

def cmd_record(tag, label, fills_path):
    """Log a basket you executed yourself, so it groups in the dashboard like any other."""
    import datetime, os
    fills = json.load(open(fills_path))          # {"SYM": {"q": n, "avg": p}, ...}
    m = json.load(open("_smallcase_map.json")) if os.path.exists("_smallcase_map.json") else {"batches": {}}
    m.setdefault("batches", {})[tag] = {
        "label": label, "grp": label.split()[0],
        "executed": datetime.date.today().isoformat(), "holdings": fills,
        "invested": round(sum(v["q"] * v["avg"] for v in fills.values())),
    }
    json.dump(m, open("_smallcase_map.json", "w"), indent=1)
    print(f"recorded {tag}: {label} — {len(fills)} stocks, "
          f"₹{m['batches'][tag]['invested']:,}")

def cmd_orders(path, amount, tag=None):
    s = load_sheet(path); rows, cost, mu = size(s, amount)
    meta = " · ".join(filter(None, [s.get("theme"),
                     f"{s['risk']} risk" if s.get("risk") else None,
                     f"as of {s.get('asof','?')}"]))
    print(f"\n{s['label']}  ({meta})")
    print(f"Amount ₹{amount:,.0f} · minimum for whole shares ₹{mu:,.0f}"
          + ("   !! BELOW MINIMUM" if amount < mu else ""))
    print(f"\n{'Stock':13}{'Qty':>5}{'Price':>10}{'Value':>11}  note\n" + "-" * 56)
    for sym, q, px, v, note in rows:
        print(f"{sym:13}{q:>5}{px:>10,.0f}{v:>11,.0f}  {note}")
    print("-" * 56 + f"\n{'TOTAL':13}{'':>5}{'':>10}{cost:>11,.0f}  ({cost/amount*100:.1f}% deployed)")
    if tag:
        print(f"\nPass tag=\"{tag}\" on every order — that is what makes this basket")
        print(f"groupable later. Then: basket.py record {tag} \"<label>\" fills.json")
    print("\nNSE · CNC · market or limit. Not investment advice.")

def demo():
    """Self-check: minimum-unit maths and the below-minimum skip branch."""
    s = {"label": "t", "weights": {"A": 50, "B": 50}, "prices": {"A": 100, "B": 1000}}
    assert min_unit(s["weights"], s["prices"]) == 2000, "B at 50% needs a 2000 basket"
    assert [r[1] for r in size(s, 2000)[0]] == [10, 1], "at minimum: 10xA, 1xB"
    assert any(r[4] for r in size(s, 500)[0]), "below minimum must skip"
    assert not any(r[4] for r in size(s, 2000)[0]), "at minimum must not skip"
    # a sheet whose weights don't sum to 100 must still deploy the full amount
    import tempfile as _tf, json as _J, os as _os
    _d = _tf.mkdtemp(); _sp = _os.path.join(_d, "s.json")
    _J.dump({"label": "n", "weights": {"A": 30, "B": 20},        # sums to 50
             "prices": {"A": 100, "B": 100}}, open(_sp, "w"))
    _s = load_sheet(_sp)
    assert abs(sum(_s["weights"].values()) - 100) < 0.01, _s["weights"]
    _rows, _cost, _ = size(_s, 100000)
    assert abs(_cost - 100000) / 100000 < 0.02, f"under-deployed: {_cost}"
    # equal-weight normalises to 100
    import tempfile, os, json as J
    d = tempfile.mkdtemp(); pj = os.path.join(d, "p.json")
    J.dump({"A": 100.0, "B": 200.0, "C": 400.0}, open(pj, "w"))
    cwd = os.getcwd(); os.chdir(d)
    cmd_new("EqTest", pj)
    got = J.load(open("eqtest_sheet.json"))
    assert abs(sum(got["weights"].values()) - 100) < 0.1, got["weights"]
    os.chdir(cwd)
    print("demo OK")

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    match a[0]:
        case "export": cmd_export(a[1] if len(a) > 1 else sys.exit("need <tag>"))
        case "md":     cmd_md(a[1])
        case "orders": cmd_orders(a[1], float(a[2]),
                                   a[a.index("--tag")+1] if "--tag" in a else None)
        case "record": cmd_record(a[1], a[2], a[3])
        case "new":
            opt = lambda f: a[a.index(f) + 1] if f in a else None
            pos = [x for x in a[3:] if not x.startswith("--")
                   and x not in (opt("--theme"), opt("--risk"))]
            cmd_new(a[1], a[2], pos[0] if pos else None, opt("--theme"), opt("--risk"))
        case "rebalance": cmd_rebalance(a[1], a[2])
        case "demo":   demo()
        case _:        sys.exit(__doc__)
