import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Modulos_Mysql import MarketScreen

ACCOUNT = "U4214563"

# CUSIPs verificados en SEC EDGAR para activos en cartera sin CUSIP
# Verificar en: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=&CIK={TICKER}&type=13F
CUSIPS = {
    "BTI":  "G11103104",   # British American Tobacco
    "CCI":  "22822V101",   # Crown Castle Inc.
    "CNH":  "N20944109",   # CNH Industrial N.V.
    "CRNT": "M26659102",   # Ceragon Networks
    "CTRM": "M25264105",   # Castor Maritime
    "MPW":  "56576J101",   # Medical Properties Trust
    "NOMD": "G65318102",   # Nomad Foods
    "TU":   "87971M103",   # Telus Corporation
    "UUUU": "29278H103",   # Energy Fuels Inc
}

print("=" * 70)
print(f"Resolver CUSIPs en cartera — cuenta: {ACCOUNT}")
print("=" * 70)

market   = MarketScreen()
rows, ix = market.select(account=ACCOUNT, tipo="Dividends")
sin_cusip = {
    dict(zip(ix, r))["symbol"]
    for r in (rows or [])
    if dict(zip(ix, r)).get("encartera") == "Y" and not dict(zip(ix, r)).get("cusip")
}

print(f"\nActivos en cartera sin CUSIP: {len(sin_cusip)}")
a_actualizar = {sym: cusip for sym, cusip in CUSIPS.items() if sym in sin_cusip}
sin_cusip_mapeado = sin_cusip - set(CUSIPS.keys())

print("\nCon CUSIP conocido (listos para actualizar):")
for sym, cusip in sorted(a_actualizar.items()):
    print(f"  {sym:<10} → {cusip}")

if sin_cusip_mapeado:
    print("\nSin CUSIP conocido (requieren búsqueda manual):")
    for sym in sorted(sin_cusip_mapeado):
        print(f"  {sym:<10} → buscar en https://efts.sec.gov/LATEST/search-index?q=%22{sym}%22&forms=13F-HR")

if not a_actualizar:
    print("\nNada que actualizar.")
    sys.exit(0)

print(f"\n¿Actualizar {len(a_actualizar)} símbolos en market? (s/n): ", end="")
if input().strip().lower() != "s":
    print("Sin cambios.")
    sys.exit(0)

ok = 0
for sym, cusip in sorted(a_actualizar.items()):
    market.update_market_cusip(sym, ACCOUNT, cusip)
    print(f"  ✓ {sym:<10} cusip={cusip}")
    ok += 1

print(f"\nActualizados: {ok} símbolos.")
print("Siguiente paso: python AppTest/run_sync_13f_scores.py  (o re-correr Agente_13FHoldings)")
print("\nListo.")
