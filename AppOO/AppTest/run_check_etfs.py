import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from Modulos_Mysql import MarketScreen

ACCOUNT = "U4214563"

mkt = MarketScreen()
conn = mkt._conectar(tabla="select.market")
c = conn.cursor()

print("=== Símbolos EN CARTERA — categoriaActivo actual ===")
c.execute(
    """
    SELECT symbol, shortName, categoriaActivo, sector, industry
    FROM market
    WHERE account=%s AND encartera='Y'
    ORDER BY categoriaActivo, symbol
""",
    (ACCOUNT,),
)
rows = c.fetchall()

print(f"{'Symbol':<10} {'Cat':>4}  {'Nombre':<35} {'Sector':<25} {'Industry'}")
print("-" * 110)
for sym, nombre, cat, sector, industry in rows:
    print(f"  {sym:<10} {cat:>4}  {(nombre or '')[:34]:<35} {(sector or '')[:24]:<25} {(industry or '')[:40]}")

print(f"\nTotal en cartera: {len(rows)}")

cats = {}
for _, _, cat, _, _ in rows:
    cats[cat] = cats.get(cat, 0) + 1
print("Por categoría:", cats)

conn.close()
