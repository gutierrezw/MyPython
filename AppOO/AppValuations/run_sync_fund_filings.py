import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.WARNING, format="%(message)s")

from edgar_13f import sync_fund_filings

TOP_N = 1500

print("=" * 70)
print(f"sync_fund_filings — descarga 13F-HR XMLs para todos los fondos con CIK (max {TOP_N})")
print("=" * 70)

result = sync_fund_filings(top_n=TOP_N)

print("=" * 70)
print(f"  fondos procesados : {result['funds']}")
print(f"  descargados       : {result['downloaded']}")
print(f"  skipped           : {result['skipped']}")
print(f"  fallidos          : {result['failed']}")
print("Listo.")
