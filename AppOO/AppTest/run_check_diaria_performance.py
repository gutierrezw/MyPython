import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Mysql import BDsystem

account = "U4214563"

conn = BDsystem.connect_dbase("check_diaria")
cursor = conn.cursor()

print("=" * 60)
print("diaria_performance — últimas fechas por symbol (Stock)")
print("=" * 60)
cursor.execute(
    """
    SELECT symbol, max(Date) as last_date, count(*) as total
    FROM diaria_performance
    WHERE account = %s
    GROUP BY symbol
    ORDER BY last_date DESC
    LIMIT 20
""",
    (account,),
)
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f"  {r[0]:<10} last={r[1]}  total={r[2]}")
else:
    print("  (sin datos)")

print()
print("=" * 60)
print("diaria_performance — max(Date) global")
print("=" * 60)
cursor.execute(
    """
    SELECT max(Date) as last_date, min(Date) as first_date, count(*) as total
    FROM diaria_performance
    WHERE account = %s
""",
    (account,),
)
row = cursor.fetchone()
print(f"  first={row[1]}  last={row[0]}  total={row[2]}")

print()
print("=" * 60)
print("performa_inversion — últimas fechas (Stock)")
print("=" * 60)
cursor.execute(
    """
    SELECT vehiculo, max(fechaclose) as last_date, count(*) as total
    FROM performa_inversion
    WHERE idcuenta = %s
    GROUP BY vehiculo
    ORDER BY last_date DESC
""",
    (account,),
)
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f"  {r[0]:<12} last={r[1]}  total={r[2]}")
else:
    print("  (sin datos)")

cursor.close()
conn.close()
print()
print("Done.")
