import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Class_Screener import cleanup_market

ACCOUNT = "U4214563"

print("=" * 70)
print(f"cleanup_market — cuenta: {ACCOUNT}")
print("=" * 70)

result = cleanup_market(ACCOUNT)

print(f"\n  total             : {result['total']}")
print(f"  batches_ok        : {result['batches_ok']}")
print(f"  quote_actualizados: {result['quote_actualizados']}")
print(f"  preferreds_elim   : {result['preferreds_eliminados']}")
print(f"  eliminados        : {result['eliminados']}")
print(f"  fund_completados  : {result['fund_completados']}")
print("\nListo.")
