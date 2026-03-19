import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Class_Screener import audit_portfolio

ACCOUNT = "U4214563"

print("=" * 70)
print(f"audit_portfolio — cuenta: {ACCOUNT}")
print("=" * 70)

result = audit_portfolio(ACCOUNT)

print(f"\n  total        : {result['total']}")
print(f"  delistados   : {result['delistados']}")
print(f"  nombres_upd  : {result['nombres_upd']}")
print(f"  cusips_upd   : {result['cusips_upd']}")
print(f"  sin_precio   : {result['sin_precio']}")
print(f"  errores      : {result['errores']}")
print("\nListo.")
