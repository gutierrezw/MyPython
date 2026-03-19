import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.WARNING, format="%(message)s")

from edgar_13f import sync_13f_holdings

ACCOUNT = "U4214563"

print("=" * 70)
print(f"sync_13f_holdings — parsea XMLs 13F y pobla fund_holdings — cuenta: {ACCOUNT}")
print("=" * 70)

result = sync_13f_holdings(account=ACCOUNT)

print("=" * 70)
print(f"  archivos XML       : {result['xml_files']}")
print(f"  CUSIPs desconocidos: {result['unknown_cusips']}")
print(f"  holdings insertados: {result['inserted_holdings']}")
print(f"  stocks nuevos      : {0}")
print("Listo.")
