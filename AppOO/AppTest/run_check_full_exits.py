"""
run_check_full_exits.py
Analiza si el concepto 'full exit' (fondo que liquida completamente) está en BD
y cómo se representa en fund_holdings.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_Mysql import MarketScreen

mkt = MarketScreen()
conn = mkt._conectar(tabla="select.market")
c = conn.cursor()

print("=== 1. Distribución de operation + shares para option_type='STK' ===")
c.execute("""
    SELECT operation, shares, COUNT(*) as cnt
    FROM fund_holdings
    WHERE option_type = 'STK'
    GROUP BY operation, shares
    ORDER BY operation, shares
    LIMIT 20
""")
print(f"{'operation':<12} {'shares':>12} {'count':>12}")
print("-" * 38)
for r in c.fetchall():
    print(f"{str(r[0]):<12} {r[1]:>12} {r[2]:>12,}")

print()
print("=== 2. ¿Existen registros con shares=0? ===")
c.execute("SELECT COUNT(*) FROM fund_holdings WHERE shares = 0 AND option_type = 'STK'")
print(f"Registros STK con shares=0: {c.fetchone()[0]:,}")

print()
print("=== 3. ¿Fondos que tenían CCI en Q3 pero no en Q4? (ejemplo de 'salida real') ===")
c.execute("""
    SELECT COUNT(DISTINCT q3.fund_id) as salidas_reales
    FROM (
        SELECT DISTINCT fund_id FROM fund_holdings
        WHERE symbol='CCI' AND option_type='STK'
          AND report_date = (SELECT MIN(report_date) FROM fund_holdings WHERE symbol='CCI' AND option_type='STK')
    ) q3
    LEFT JOIN (
        SELECT DISTINCT fund_id FROM fund_holdings
        WHERE symbol='CCI' AND option_type='STK'
          AND report_date = (SELECT MAX(report_date) FROM fund_holdings WHERE symbol='CCI' AND option_type='STK')
    ) q4 ON q3.fund_id = q4.fund_id
    WHERE q4.fund_id IS NULL
""")
print(f"CCI — fondos que estaban en Q3 y no en Q4 (salidas reales): {c.fetchone()[0]:,}")

print()
print("=== 4. Fechas disponibles para CCI ===")
c.execute("""
    SELECT report_date, COUNT(DISTINCT fund_id) as fondos
    FROM fund_holdings WHERE symbol='CCI' AND option_type='STK'
    GROUP BY report_date ORDER BY report_date
""")
for r in c.fetchall():
    print(f"  {r[0]}  →  {r[1]:,} fondos")

conn.close()
