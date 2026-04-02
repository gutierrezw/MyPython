import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Modulos_Mysql import MarketScreen
from Class_InstitucionalScore import InstitucionalScore

ACCOUNT = "U4214563"

# Símbolos en cartera que no tienen dividendos y no están en market
SYMBOLS_MISSING = ["PLUG", "XIFR"]

market = MarketScreen()
inst = InstitucionalScore()

print("=" * 70)
print(f"Paso 1 — Insertar símbolos faltantes en market: {ACCOUNT}")
print("=" * 70)

inserted = []
for sym in SYMBOLS_MISSING:
    rows, _ = market.select(account=ACCOUNT, symbol=sym)
    if rows:
        print(f"  {sym}: ya existe en market — skip")
    else:
        market.insert(
            upd=["encartera", "categoriaActivo", "account"],
            val=["Y", "N", ACCOUNT],
            symbol=sym,
        )
        inserted.append(sym)
        print(f"  {sym}: insertado (encartera=Y, categoriaActivo=N)")

print()
print("=" * 70)
print(f"Paso 2 — sync_institutional solo para símbolos insertados")
print("=" * 70)

campos = [
    "inst_ownership_pct",
    "insider_ownership_pct",
    "inst_top_holder",
    "inst_top_holder_shares",
    "inst_score",
    "inst_funds",
    "analyst_rec",
    "analyst_mean",
    "analyst_count",
]

for sym in inserted:
    print(f"  {sym}: fetching yfinance...", end="", flush=True)
    raw = inst._fetch_ownership(sym)
    if not raw:
        print(" sin datos")
        continue
    inst_pct = raw.get("inst_ownership_pct")
    score = round(inst_pct, 4) if inst_pct is not None else None
    valores = [
        inst_pct,
        raw.get("insider_ownership_pct"),
        raw.get("inst_top_holder"),
        raw.get("inst_top_holder_shares"),
        score,
        raw.get("inst_funds"),
        raw.get("analyst_rec"),
        raw.get("analyst_mean"),
        raw.get("analyst_count"),
    ]
    ok = market.update(upd=campos, val=valores, symbol=sym, account=ACCOUNT)
    rec = raw.get("analyst_rec") or "—"
    inst_pct = raw.get("inst_ownership_pct")
    inst_str = f"{inst_pct:.1%}" if inst_pct else "—"
    print(f" OK  inst={inst_str}  analyst={rec}")

print("\nListo.")
