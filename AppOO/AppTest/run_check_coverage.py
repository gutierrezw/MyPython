import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from Modulos_Mysql import MarketScreen

mkt = MarketScreen()
conn = mkt._conectar(tabla="select.market")
c = conn.cursor()

# Símbolos en market con fh_count poblado vs NULL
c.execute("""
    SELECT
        COUNT(*) as total,
        SUM(fh_count IS NOT NULL AND fh_count > 0) as con_fh_count,
        SUM(fh_count IS NULL OR fh_count = 0) as sin_fh_count,
        SUM(inst_ownership_pct IS NOT NULL) as con_inst_pct
    FROM market WHERE account='U4214563'
""")
r = c.fetchone()
print(f"Total símbolos    : {r[0]:,}")
print(f"Con fh_count      : {r[1]:,}")
print(f"Sin fh_count      : {r[2]:,}")
print(f"Con inst_own%     : {r[3]:,}")

# Cuántos símbolos únicos hay en fund_holdings ahora
c.execute("SELECT COUNT(DISTINCT symbol) FROM fund_holdings WHERE option_type='STK'")
print(f"\nSímbolos en fund_holdings: {c.fetchone()[0]:,}")
conn.close()
