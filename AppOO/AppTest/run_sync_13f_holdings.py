import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../AppValuations"))

from edgar_13f import sync_13f_holdings

ACCOUNT = "U4214563"

print("=" * 70)
print(f"sync_13f_holdings — cuenta: {ACCOUNT}")
print("=" * 70)

result = sync_13f_holdings(ACCOUNT)

print(f"\n  xml_files         : {result['xml_files']}")
print(f"  inserted_holdings : {result['inserted_holdings']}  (acciones directas)")
print(f"  inserted_options  : {result['inserted_options']}  (CALL/PUT)")
print(f"  total             : {result['inserted_holdings'] + result['inserted_options']}")
print("\nListo.")
