"""
run_cleanup_order_trader.py — prueba manual del cleanup EOD de order_trader.
Ejecutar: python AppTest\run_cleanup_order_trader.py
"""

import os, sys, json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_Mysql import BDsystem, RepositorioOportunidadesBuySell

_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_PROFILE = os.path.join(_BASE, "profiles", "main.json")
if os.path.exists(_PROFILE):
    with open(_PROFILE, encoding="utf-8") as _f:
        _cfg = json.load(_f)
    if _cfg.get("db"):
        BDsystem.configure(_cfg["db"])
    if _cfg.get("tmp_path"):
        os.environ["APPOO_TMP"] = _cfg["tmp_path"]

ACCOUNT = "U4214563"

repo = RepositorioOportunidadesBuySell()

# Ver estado ANTES
print("\n=== ANTES del cleanup ===")
rows, ix = repo.select_order_trader_today(ACCOUNT, "Stock")
rows_c, ix_c = repo.select_order_trader_today(ACCOUNT, "Crypto")

for r in rows + rows_c:
    d = dict(zip(ix or ix_c, r))
    print(
        f"  {d.get('vehiculo','?'):6} | {d.get('symbol','?'):8} | {d.get('status','?'):15} | {d.get('orderType','?'):8} | {d.get('tif','?'):4} | {d.get('stampPlace','?')}"
    )

print(f"\n  Stock: {len(rows)} | Crypto: {len(rows_c)} | Total: {len(rows)+len(rows_c)}")

# Ejecutar cleanup
print("\n=== Ejecutando cleanup (preserva: Filled, Submitted, New) ===")
deleted = repo.cleanup_order_trader_eod(ACCOUNT)
print(f"  Eliminadas: {deleted}")

# Ver estado DESPUÉS
print("\n=== DESPUÉS del cleanup ===")
rows2, _ = repo.select_order_trader_today(ACCOUNT, "Stock")
rows2_c, _ = repo.select_order_trader_today(ACCOUNT, "Crypto")

for r in rows2 + rows2_c:
    d = dict(zip(ix or ix_c, r))
    print(
        f"  {d.get('vehiculo','?'):6} | {d.get('symbol','?'):8} | {d.get('status','?'):15} | {d.get('orderType','?'):8} | {d.get('tif','?'):4}"
    )

print(f"\n  Stock: {len(rows2)} | Crypto: {len(rows2_c)} | Total: {len(rows2)+len(rows2_c)}")
