import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../AppValuations"))

logging.basicConfig(level=logging.WARNING, format="%(message)s")

from edgar_13f import sync_fund_filings

print("=" * 70)
print("sync_fund_filings — descarga XMLs 13F para todos los fondos con CIK")
print("=" * 70)

result = sync_fund_filings()

print(f"\n  fondos procesados : {result['funds']}")
print(f"  descargados       : {result['downloaded']}")
print(f"  skipped (ya exist): {result['skipped']}")
print(f"  fallidos          : {result['failed']}")
print("\nListo.")
