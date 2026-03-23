import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from Modulos_python import yf

for sym in ("BABA", "XIFR"):
    info = yf.Ticker(sym).info
    print(f"\n{sym}:")
    print(f"  dividendRate              : {info.get('dividendRate')}")
    print(f"  dividendYield             : {info.get('dividendYield')}")
    print(f"  lastDividendValue         : {info.get('lastDividendValue')}")
    print(f"  trailingAnnualDividendRate: {info.get('trailingAnnualDividendRate')}")
    print(f"  ttmDividends              : {info.get('ttmDividends')}")
    print(f"  lastDividendDate          : {info.get('lastDividendDate')}")
