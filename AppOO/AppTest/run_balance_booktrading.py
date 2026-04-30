"""
run_balance_booktrading.py
===========================
Corrige residuos de stock en booktrading:
  1. stock < 0          → lleva a 0 (artefacto de redondeo al vender fracciones)
  2. 0 < |stock| < 0.01 → lleva a 0 (residuo mínimo, posición prácticamente cerrada)

Actúa sobre la ÚLTIMA fila de cada símbolo (la que determina la posición actual).
Solo símbolos no activos en inversiones: delisted=1 o sin posición en IB.

EJECUCIÓN
---------
    cd AppOO
    python AppTest/run_balance_booktrading.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Mysql import BDsystem

ACCOUNT = "U4214563"
UMBRAL = 0.01


def main():
    print(__doc__)

    conn = BDsystem.connect_dbase("balance_book")
    cursor = conn.cursor()

    # Última fila por símbolo donde el stock es anómalo
    cursor.execute(
        """
        SELECT b.simbolo, b.stock, b.basico, b.fechahora, b.sec, b.delisted
        FROM booktrading b
        INNER JOIN (
            SELECT simbolo, MAX(fechahora) as max_fecha
            FROM booktrading
            WHERE cuenta = %s AND codigo IN ('C', 'O')
            GROUP BY simbolo
        ) t ON b.simbolo = t.simbolo AND b.fechahora = t.max_fecha
        WHERE b.cuenta = %s
          AND (b.stock < 0 OR (ABS(b.stock) < %s AND b.stock != 0))
        ORDER BY b.simbolo
        """,
        (ACCOUNT, ACCOUNT, UMBRAL),
    )
    rows = cursor.fetchall()

    if not rows:
        print("  No se encontraron residuos de stock. Booktrading balanceado.")
        cursor.close()
        conn.close()
        return

    print(f"\n{'='*70}")
    print(f"  RESIDUOS ENCONTRADOS (umbral |stock| < {UMBRAL} o stock < 0)")
    print(f"{'='*70}")
    print(f"\n  {'Símbolo':<14} {'Stock':>12} {'Basico':>12} {'Delisted':>8}  Última operación")
    print(f"  {'-'*14} {'-'*12} {'-'*12} {'-'*8}  {'-'*20}")
    for sim, stock, basico, fecha, sec, delisted in rows:
        tipo = "neg" if stock < 0 else "residuo"
        print(f"  {sim:<14} {stock:>12.6f} ${basico:>11,.2f} {delisted:>8}  {str(fecha)[:19]}  [{tipo}]")

    print(f"\n  Total: {len(rows)} símbolo(s) con stock anómalo")
    resp = input("\n  ¿Corregir stock → 0 para todos? (s/N): ").strip().lower()
    if resp != "s":
        print("  Cancelado.")
        cursor.close()
        conn.close()
        return

    corregidos = 0
    for sim, stock, basico, fecha, sec, delisted in rows:
        cursor.execute(
            "UPDATE booktrading SET stock = 0 WHERE cuenta = %s AND simbolo = %s AND fechahora = %s AND sec = %s",
            (ACCOUNT, sim, fecha, sec),
        )
        filas = cursor.rowcount
        conn.commit()
        if filas:
            print(f"  {sim}: stock {stock:.6f} → 0  ({filas} fila)")
            corregidos += 1

    print(f"\n  Corregidos: {corregidos}/{len(rows)} símbolos")
    print("  Próximo rebuild no generará filas para estas posiciones cerradas.\n")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
