"""
run_reprocess_13f_scores.py
Script one-time: reprocessa holdings 13F con baseline del trimestre anterior
y recalcula inst_score para todos los símbolos.

Flujo:
  1. sync_13f_holdings  → procesa filings en orden cronológico (prev=NEW, current=BUY/SELL/HOLD)
  2. sync_13f_scores    → recalcula inst_score con fh_buy_ratio real

Correr desde AppTest/:  python run_reprocess_13f_scores.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_python import logging
from AppValuations.edgar_13f import sync_13f_holdings
from Class_InstitucionalScore import sync_13f_scores

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(message)s")

ACCOUNT = "U4214563"


def main():
    print("=== PASO 1: sync_13f_holdings ===")
    print("Procesando filings en orden cronológico (prev quarter primero)...")
    result = sync_13f_holdings(ACCOUNT)
    print(f"  Resultado: {result}")

    print("\n=== PASO 2: sync_13f_scores ===")
    print("Recalculando inst_score con fh_buy_ratio real...")
    result2 = sync_13f_scores(ACCOUNT)
    print(f"  Resultado: {result2}")

    print("\nListo. Abre Screener/Consenso para ver 13F Buy% y 13F Sell% actualizados.")


if __name__ == "__main__":
    main()
