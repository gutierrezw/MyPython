"""
run_fix_hasi_stock.py
======================
Diagnostica y corrige el campo stock de HASI en booktrading.

Situación: IB tenía 19 acciones pero booktrading acumuló 24 → diferencia de 5.
Las dos ventas del 2026-04-30 dejaron stock=16 y stock=8 en lugar de 11 y 3.

EJECUCIÓN
---------
    cd AppOO
    python AppTest/run_fix_hasi_stock.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Mysql import BDsystem

ACCOUNT = "U4214563"
SYMBOL = "HASI"
DIVISA = "USD"
STOCK_CORRECTO = 19  # posición real en IB antes de las dos ventas del 2026-04-30


def main():
    print(__doc__)

    conn = BDsystem.connect_dbase("fix_hasi")
    cursor = conn.cursor()

    # Historial completo ordenado por sec
    cursor.execute(
        """
        SELECT id, sec, fechahora, cantidad, stock, basico, codigo, gprealizadas
        FROM booktrading
        WHERE cuenta = %s AND simbolo = %s AND divisa = %s
        ORDER BY sec ASC
        """,
        (ACCOUNT, SYMBOL, DIVISA),
    )
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]

    print(f"\n{'='*90}")
    print(f"  Historial HASI — {len(rows)} registros")
    print(f"{'='*90}")
    print(
        f"  {'sec':>4}  {'id':>5}  {'fecha':<20}  {'cant':>6}  {'stock':>6}  {'stock_ok':>8}  {'codigo'}  {'gpreal':>8}"
    )
    print(f"  {'-'*4}  {'-'*5}  {'-'*20}  {'-'*6}  {'-'*6}  {'-'*8}  {'-'*6}  {'-'*8}")

    # Recalcula stock correcto acumulando cantidad
    stock_acum = 0.0
    correcciones = []
    for r in rows:
        d = dict(zip(cols, r))
        stock_acum += float(d["cantidad"])
        diff = round(float(d["stock"]) - stock_acum, 6)
        marker = " ← ERROR" if abs(diff) > 0.001 else ""
        print(
            f"  {d['sec']:>4}  {d['id']:>5}  {str(d['fechahora'])[:19]}  {d['cantidad']:>6}  {d['stock']:>6.1f}  {stock_acum:>8.1f}  {d['codigo']:>6}  {d['gprealizadas']:>8.2f}{marker}"
        )
        if abs(diff) > 0.001:
            correcciones.append((d["id"], d["sec"], float(d["stock"]), stock_acum))

    print(f"\n  Registros con stock incorrecto: {len(correcciones)}")
    if not correcciones:
        print("  Stock acumulado cuadra. Verificar si la diferencia viene de inversiones vs booktrading.")
        cursor.close()
        conn.close()
        return

    print(f"\n{'='*90}")
    print("  CORRECCIONES NECESARIAS")
    print(f"{'='*90}")
    for id_, sec, stock_actual, stock_correcto in correcciones:
        print(f"  id={id_}  sec={sec}  stock actual={stock_actual:.1f}  →  stock correcto={stock_correcto:.1f}")

    resp = input("\n  ¿Aplicar correcciones? (s/N): ").strip().lower()
    if resp != "s":
        print("  Cancelado.")
        cursor.close()
        conn.close()
        return

    for id_, sec, stock_actual, stock_correcto in correcciones:
        cursor.execute(
            "UPDATE booktrading SET stock = %s WHERE id = %s",
            (stock_correcto, id_),
        )
        conn.commit()
        print(f"  id={id_} sec={sec}: {stock_actual:.1f} → {stock_correcto:.1f}")

    print(f"\n  {len(correcciones)} registros corregidos.")
    cursor.close()
    conn.close()
    print("\n  Listo. Podés continuar con el rebuild.\n")


if __name__ == "__main__":
    main()
