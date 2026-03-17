import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
logging.basicConfig(level=logging.WARNING, format="%(message)s")

from Modulos_Mysql import MarketScreen

market = MarketScreen()
n = market.cleanup_fund_holdings_nulls()
print(f"eliminadas={n} filas NULL de fund_holdings")
