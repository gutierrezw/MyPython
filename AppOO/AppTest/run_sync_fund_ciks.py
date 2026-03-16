import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.WARNING, format="%(message)s")

from Class_InstitucionalScore import sync_fund_ciks

print("=" * 70)
print("sync_fund_ciks — busca CIK en EDGAR para fondos sin CIK")
print("=" * 70)

result = sync_fund_ciks()

print("=" * 70)
print(f"  total fondos sin CIK : {result['total']}")
print(f"  encontrados          : {result['found']}")
print(f"  fallidos             : {result['failed']}")
print("Listo.")
