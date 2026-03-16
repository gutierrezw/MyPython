import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Class_InstitucionalScore import _search_edgar_cik

for fund_name in ["Vanguard Group Inc", "Blackrock Inc.", "State Street Corporation",
                  "Geode Capital Management, LLC", "FMR, LLC"]:
    cik = _search_edgar_cik(fund_name)
    print(f"  {fund_name!r:45s} → {cik}")
