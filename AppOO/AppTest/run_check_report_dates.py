"""
run_check_report_dates.py
Muestra distribución de report_date en fund_holdings para entender la historia disponible.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_Mysql import MarketScreen

mkt = MarketScreen()
conn = mkt._conectar(tabla="select.market")
c = conn.cursor()

c.execute("""
    SELECT DATE_FORMAT(report_date, '%Y-%m') as mes,
    COUNT(DISTINCT fund_id) as fondos, COUNT(*) as holdings
    FROM fund_holdings WHERE option_type='STK'
    GROUP BY mes ORDER BY mes DESC LIMIT 15
""")

print(f"{'Mes':<12} {'Fondos':>8} {'Holdings':>12}")
print("-" * 34)
for r in c.fetchall():
    print(f"{r[0]:<12} {r[1]:>8,} {r[2]:>12,}")

conn.close()
