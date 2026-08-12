#!/usr/bin/env python3
"""Portable basket interchange — share a weighted stock basket, size it to any capital.

  export <tag>                  build a shareable sheet from your captured basket
  md     <sheet.json>           render the sheet as markdown (human / LLM readable)
  orders <sheet.json> <amount> [--tag T]   size ANYONE's sheet to your capital
  record <tag> <label> <fills.json>        log an executed basket into the local map

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
    print(f"\n{s['label']}  (sheet as of {s.get('asof','?')})")
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
        case "demo":   demo()
        case _:        sys.exit(__doc__)
