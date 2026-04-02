"""
Reprocesa XMLs 13F para CUSIPs que no estaban en market cuando se corrió sync_13f_holdings.
Solo inserta/actualiza posiciones de los CUSIPs indicados, sin reprocesar todo el pipeline.
"""

import sys
import os
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Modulos_Mysql import MarketScreen
from AppValuations.edgar_13f import parse_13f_xml, _13F_SAVE_DIR

ACCOUNT = "U4214563"

# CUSIPs a reprocesar → symbol
TARGET_CUSIPS = {
    "72919P202": "PLUG",
    "65341B106": "XIFR",
}

print("=" * 70)
print("Reprocesar posiciones para CUSIPs faltantes")
print(f"Targets: {TARGET_CUSIPS}")
print("=" * 70)

market = MarketScreen()
# Metadata desde BD (reemplaza 13f_metadata.json)
metadata = {row["filename"]: row for row in market.load_fund_filings_all()}

# Obtener mapa completo de CUSIPs desde market (para load_fund_holdings_prev)
cusip_map = market.get_cusip_map(ACCOUNT)
print(f"\ncusip_map tiene {len(cusip_map)} entradas")
for c, s in cusip_map.items():
    if c in TARGET_CUSIPS:
        print(f"  {c} → {s}")

# Cargar estado previo de fund_holdings
print("\nCargando estado previo de fund_holdings...")
prev_map = market.load_fund_holdings_prev()

# Buscar XMLs en disco
all_xml_files = [f for f in os.listdir(_13F_SAVE_DIR) if f.endswith(".xml")]
print(f"Total XMLs en disco: {len(all_xml_files)}")

records = []
xmls_con_target = 0

for xml_file in all_xml_files:
    filepath = os.path.join(_13F_SAVE_DIR, xml_file)

    # Lectura rápida: ¿contiene alguno de los CUSIPs target?
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
    except Exception:
        continue

    cusips_presentes = [c for c in TARGET_CUSIPS if c in raw]
    if not cusips_presentes:
        continue

    meta = metadata.get(xml_file)
    if not meta:
        continue

    cik = meta["cik"]
    fund_id = market.get_fund_id_by_cik(cik)
    if not fund_id:
        continue

    filing_date = meta["filing_date"]
    positions = parse_13f_xml(filepath)
    xmls_con_target += 1

    for pos in positions:
        if pos["cusip"] not in TARGET_CUSIPS:
            continue
        symbol = cusip_map.get(pos["cusip"])
        if not symbol:
            continue

        opt = pos.get("option_type") or "STK"
        shares = pos["shares"]
        prev_key = (fund_id, pos["cusip"], opt)
        shares_prev = prev_map.get(prev_key)

        if shares_prev is None:
            operation, shares_delta, pct_change = "NEW", None, None
        elif shares > shares_prev:
            operation = "BUY"
            shares_delta = shares - shares_prev
            pct_change = round(shares_delta / shares_prev, 4) if shares_prev > 0 else None
        elif shares < shares_prev:
            operation = "SELL"
            shares_delta = shares - shares_prev
            pct_change = round(shares_delta / shares_prev, 4) if shares_prev > 0 else None
        else:
            operation, shares_delta, pct_change = "HOLD", 0, 0.0

        records.append(
            (
                fund_id,
                symbol,
                shares,
                shares_prev,
                shares_delta,
                pct_change,
                operation,
                filing_date,
                pos["value"],
                pos["cusip"],
                opt,
            )
        )

print(f"XMLs con target CUSIPs: {xmls_con_target}")
print(f"Registros a insertar  : {len(records)}")
if not records:
    print("\nNada que insertar.")
    sys.exit(0)

# Desglose por símbolo
from collections import Counter

by_sym = Counter(r[1] for r in records)
for sym, cnt in sorted(by_sym.items()):
    print(f"  {sym}: {cnt} registros")

print("\nInsertando en fund_holdings...")
market.bulk_upsert_fund_holdings(records)
print("Listo.")
