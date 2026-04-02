import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from Modulos_Mysql import MarketScreen

mkt = MarketScreen()
conn = mkt._conectar(tabla="select.market")
c = conn.cursor()

for sym in ("BABA", "XIFR", "BIL", "VGSH"):
    c.execute(
        """
        SELECT symbol, shortName, categoriaActivo, sector, industry, country,
               dividendRate, dividendYield, encartera
        FROM market WHERE symbol=%s AND account='U4214563'
    """,
        (sym,),
    )
    r = c.fetchone()
    if r:
        print(f"{r[0]}: cat={r[2]} sector={r[3]} industry={r[4]} country={r[5]} div={r[6]} yield={r[7]} cartera={r[8]}")
    else:
        print(f"{sym}: no encontrado")
conn.close()
