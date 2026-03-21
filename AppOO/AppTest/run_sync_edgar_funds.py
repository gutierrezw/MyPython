import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../AppValuations"))

logging.basicConfig(level=logging.WARNING, format="%(message)s")

from Class_InstitucionalScore import sync_edgar_funds

print("=" * 70)
print("sync_edgar_funds — carga filers 13F-HR de EDGAR en tabla funds")
print("=" * 70)

result = sync_edgar_funds()

print(f"\n  filers encontrados : {result['total']}")
print(f"  nuevos insertados  : {result['inserted']}")
print("\nListo.")
