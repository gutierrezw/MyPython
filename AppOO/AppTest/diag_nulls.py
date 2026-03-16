import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Modulos_Mysql import MarketScreen

ACCOUNT = "U4214563"
market = MarketScreen()

rows, ix = market.select(account=ACCOUNT, tipo="Dividends")

idx = {col: i for i, col in enumerate(ix)}

sin_precio = []
sin_inst = []

for row in rows:
    cat = row[idx["categoriaActivo"]]
    if cat in ("I", "S", "X"):
        continue
    sym = row[idx["symbol"]]
    price = row[idx.get("lastPrice", -1)] if "lastPrice" in idx else None
    inst = row[idx.get("inst_score", -1)] if "inst_score" in idx else None
    enc = row[idx.get("encartera", -1)] if "encartera" in idx else None

    if price is None:
        sin_precio.append((sym, enc))
    if inst is None:
        sin_inst.append((sym, enc))

print(f"Sin precio ({len(sin_precio)}):")
for sym, enc in sorted(sin_precio):
    print(f"  {sym:12s}  encartera={enc}")

print(f"\nSin inst_score ({len(sin_inst)}):")
for sym, enc in sorted(sin_inst):
    print(f"  {sym:12s}  encartera={enc}")
