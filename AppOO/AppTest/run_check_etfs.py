import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from Modulos_Mysql import MarketScreen

mkt = MarketScreen()
conn = mkt._conectar(tabla="select.market")
c = conn.cursor()

c.execute("""
    SELECT symbol, shortName, categoriaActivo, encartera
    FROM market WHERE account='U4214563'
    AND categoriaActivo='X'
    ORDER BY encartera DESC, symbol
""")
rows = c.fetchall()
print(f"{'Symbol':<10} {'Nombre':<45} {'Cat':>4} {'Cartera':>8}")
print("-" * 72)
for r in rows:
    print(f"{r[0]:<10} {(r[1] or '')[:44]:<45} {r[2]:>4} {r[3]:>8}")

print(f"\nTotal ETF/Fondos en market: {len(rows)}")
conn.close()
