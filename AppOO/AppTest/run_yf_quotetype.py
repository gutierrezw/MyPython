"""
Verifica quoteType y campos clave de Yahoo Finance para PHYS.
Correr: python AppTest/run_yf_quotetype.py
"""

import yfinance as yf

FIELDS = ["quoteType", "shortName", "longName", "longBusinessSummary", "category", "fundFamily", "typeDisp"]

t = yf.Ticker("PHYS")
info = t.info

print(f"{'Campo':<30} Valor")
print("-" * 70)
for f in FIELDS:
    print(f"{f:<30} {info.get(f, '❌ no existe')!r}")
