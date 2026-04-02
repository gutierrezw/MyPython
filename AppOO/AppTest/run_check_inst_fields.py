import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from Modulos_Mysql import MarketScreen

mkt = MarketScreen()
conn = mkt._conectar(tabla="select.market")
c = conn.cursor()

c.execute("""
    SELECT symbol, fh_count, inst_ownership_pct, inst_score
    FROM market WHERE encartera='Y' AND account='U4214563'
    ORDER BY symbol
""")
print(f"{'Symbol':<8} {'fh_count':>10} {'inst_own%':>10} {'inst_score':>12}")
print("-" * 45)
for r in c.fetchall():
    print(f"{r[0]:<8} {str(r[1] or '-'):>10} {str(r[2] or '-'):>10} {str(r[3] or '-'):>12}")
conn.close()
