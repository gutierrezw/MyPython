import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from Modulos_Mysql import MarketScreen

mkt = MarketScreen()
conn = mkt._conectar(tabla="select.market")
c = conn.cursor()

c.execute("SELECT operation, COUNT(*) FROM fund_holdings WHERE option_type='STK' GROUP BY operation ORDER BY 2 DESC")
print("=== Distribución operations fund_holdings ===")
total = 0
for r in c.fetchall():
    print(f"  {r[0]:<8} {r[1]:>10,}")
    total += r[1]
print(f"  {'TOTAL':<8} {total:>10,}")
conn.close()
