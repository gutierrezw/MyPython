import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Class_InstitucionalScore import sync_institutional

ACCOUNT = "U4214563"

print("=" * 70)
print(f"sync_institutional — cuenta: {ACCOUNT}")
print("=" * 70)

result = sync_institutional(ACCOUNT)

print(f"\n  symbols   : {result['symbols_processed']}")
print(f"  updated   : {result['updated']}")
print("\nListo.")
