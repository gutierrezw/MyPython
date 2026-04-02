import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from Modulos_Mysql import MarketScreen

mkt = MarketScreen()
conn = mkt._conectar(tabla="select.market")
c = conn.cursor()

c.execute("""
    SELECT symbol, fh_count, inst_ownership_pct, inst_score, floatShares
    FROM market WHERE encartera='Y' AND account='U4214563'
    ORDER BY symbol
""")
rows = c.fetchall()
conn.close()

ok = sum(1 for r in rows if r[1])
sin = sum(1 for r in rows if not r[1])

print(f"{'Symbol':<8} {'13F Inst':>10} {'Inst %':>10} {'Score':>8} {'floatShares':>14}")
print("-" * 55)
for r in rows:
    print(f"{r[0]:<8} {str(r[1] or '-'):>10} {str(r[2] or '-'):>10} {str(r[3] or '-'):>8} {str(r[4] or '-'):>14}")

print(f"\nCon fh_count: {ok}  |  Sin fh_count: {sin}")
