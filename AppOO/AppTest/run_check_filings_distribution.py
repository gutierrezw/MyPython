"""
run_check_filings_distribution.py
Muestra distribución mensual de filing_date en fund_filings para identificar
los dos clusters Q3 y Q4 dinámicamente.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_Mysql import MarketScreen

mkt = MarketScreen()
conn = mkt._conectar(tabla="select.market")
c = conn.cursor()

print("=== Distribución mensual de filings ===")
c.execute("""
    SELECT DATE_FORMAT(filing_date, '%Y-%m') as mes, COUNT(*) as cnt
    FROM fund_filings
    GROUP BY mes ORDER BY mes
""")
print(f"{'Mes':<10} {'Filings':>10}")
print("-" * 22)
for r in c.fetchall():
    print(f"{r[0]:<10} {r[1]:>10,}")

print()
print("=== Fondos con 2 filings (Q3 + Q4) ===")
c.execute("""
    SELECT COUNT(DISTINCT cik) as fondos_con_2q
    FROM fund_filings
    WHERE filing_date >= '2025-08-01'
    GROUP BY cik
    HAVING COUNT(DISTINCT DATE_FORMAT(filing_date, '%Y-%m')) >= 2
""")
rows = c.fetchall()
print(f"Fondos con filings en ≥2 meses distintos: {len(rows):,}")

print()
print("=== Fecha de corte sugerida entre Q3 y Q4 ===")
c.execute("""
    SELECT MIN(filing_date) as q4_start
    FROM fund_filings
    WHERE filing_date >= '2025-12-15'
""")
r = c.fetchone()
print(f"Primer filing Q4: {r[0]}")

conn.close()
