"""
run_diag_missing_symbols.py
============================
Compara símbolos con stock > 0 en booktrading vs los que llegaron a diaria_performance
en una fecha específica. Muestra posibles fuentes de gaps en nr_gyp.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Mysql import BDsystem

ACCOUNT = "U4214563"
FECHA = "2026-04-28"

conn = BDsystem.connect_dbase("diag_missing")
cursor = conn.cursor()

print("=" * 70)
print(f"SÍMBOLOS CON POSICIÓN ABIERTA EN BOOKTRADING (stock > 0, delisted=0)")
print("=" * 70)

# Posiciones abiertas en booktrading: tomar la fila más reciente por símbolo
# que tenga stock > 0 y no esté delisted
cursor.execute(
    """
    SELECT simbolo, MAX(fechahora) as ultima, stock, basico, gprealizadas
    FROM booktrading
    WHERE cuenta = %s AND delisted = 0 AND codigo IN ('C', 'O')
    GROUP BY simbolo, stock, basico, gprealizadas
    HAVING stock > 0
    ORDER BY simbolo
""",
    (ACCOUNT,),
)
bt_rows = cursor.fetchall()

bt_simbolos = {r[0] for r in bt_rows}
print(f"\n  {len(bt_simbolos)} símbolos con stock > 0 en booktrading\n")
print(f"  {'Symbol':<12} {'Stock':>10} {'Basico':>12} {'GPRealizadas':>14} {'Última fecha'}")
print(f"  {'-'*12} {'-'*10} {'-'*12} {'-'*14} {'-'*19}")
for sim, ultima, stock, basico, gpr in bt_rows:
    print(f"  {sim:<12} {stock:>10.4f} ${basico:>11,.2f} ${gpr:>13,.2f} {str(ultima)[:19]}")

print("\n" + "=" * 70)
print(f"SÍMBOLOS EN diaria_performance EL {FECHA}")
print("=" * 70)

cursor.execute(
    """
    SELECT symbol, value
    FROM diaria_performance
    WHERE account = %s AND Date = %s
    ORDER BY symbol
""",
    (ACCOUNT, FECHA),
)
diaria_rows = cursor.fetchall()
diaria_simbolos = {r[0] for r in diaria_rows}
print(f"\n  {len(diaria_simbolos)} símbolos en diaria el {FECHA}")

print("\n" + "=" * 70)
print("SÍMBOLOS CON POSICIÓN ABIERTA QUE NO ESTÁN EN DIARIA")
print("=" * 70)

faltantes = bt_simbolos - diaria_simbolos
if faltantes:
    print(f"\n  {len(faltantes)} símbolo(s) faltante(s):\n")
    print(f"  {'Symbol':<12} {'Stock':>10} {'Basico':>12} {'GPRealizadas':>14}")
    print(f"  {'-'*12} {'-'*10} {'-'*12} {'-'*14}")
    for row in bt_rows:
        if row[0] in faltantes:
            sim, ultima, stock, basico, gpr = row
            print(f"  {sim:<12} {stock:>10.4f} ${basico:>11,.2f} ${gpr:>13,.2f}")
else:
    print("\n  Ninguno — todos los símbolos con posición están en diaria.")

print("\n" + "=" * 70)
print("SÍMBOLOS EN DIARIA QUE NO ESTÁN EN BOOKTRADING ACTIVO")
print("=" * 70)

sobrantes = diaria_simbolos - bt_simbolos
if sobrantes:
    print(f"\n  {len(sobrantes)} símbolo(s) en diaria sin posición activa: {sorted(sobrantes)}")
else:
    print("\n  Ninguno.")

# Delisted con posición (los que tienen stock > 0 pero delisted = 1)
print("\n" + "=" * 70)
print("DELISTED CON STOCK > 0 (pérdida no capturada)")
print("=" * 70)

cursor.execute(
    """
    SELECT simbolo, stock, basico, gprealizadas
    FROM booktrading
    WHERE cuenta = %s AND delisted = 1 AND codigo IN ('C', 'O') AND stock > 0
    ORDER BY simbolo
""",
    (ACCOUNT,),
)
delisted_rows = cursor.fetchall()
if delisted_rows:
    print(f"\n  {'Symbol':<12} {'Stock':>10} {'Basico':>12} {'GPRealizadas':>14}")
    print(f"  {'-'*12} {'-'*10} {'-'*12} {'-'*14}")
    for sim, stock, basico, gpr in delisted_rows:
        print(f"  {sim:<12} {stock:>10.4f} ${basico:>11,.2f} ${gpr:>13,.2f}")
else:
    print("\n  Ninguno.")

cursor.close()
conn.close()
print("\nDone.")
