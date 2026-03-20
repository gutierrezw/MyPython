import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../AppValuations"))

logging.basicConfig(level=logging.WARNING, format="%(message)s")

from Class_InstitucionalScore import sync_13f_scores

ACCOUNT = "U4214563"

print("=" * 70)
print(f"sync_13f_scores — recalcula inst_score blendando yfinance + 13F — cuenta: {ACCOUNT}")
print("=" * 70)

result = sync_13f_scores(account=ACCOUNT)

print(f"\n  símbolos   : {result['symbols']}")
print(f"  actualizados: {result['updated']}")
print(f"  skipped     : {result['skipped']}")
print("\nListo.")
