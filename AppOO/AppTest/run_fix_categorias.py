import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from Modulos_Mysql import MarketScreen

ACCOUNT = "U4214563"
FIXES = [("BABA", "N"), ("XIFR", "N")]

mkt = MarketScreen()
conn = mkt._conectar(tabla="update.market")
c = conn.cursor()
for symbol, cat in FIXES:
    c.execute(
        "UPDATE market SET categoriaActivo=%s WHERE symbol=%s AND account=%s",
        (cat, symbol, ACCOUNT),
    )
    print(f"{symbol}: categoriaActivo → {cat}")
conn.commit()
conn.close()
