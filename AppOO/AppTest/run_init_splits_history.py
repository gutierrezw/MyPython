"""
run_init_splits_history.py
===========================
Carga el historial completo de splits de yfinance para las posiciones abiertas
y los marca como aplicado='Y'.

POR QUÉ EXISTE
--------------
Los registros de booktrading ya reflejan los precios y cantidades históricas
tal como se ejecutaron. Cargar los splits históricos como aplicado='Y' evita
que Agente_SplitsControl los aplique dos veces en el futuro.
Después de esta inicialización el agente solo actuará sobre splits nuevos.

EJECUCIÓN
---------
    cd AppOO
    python AppTest/run_init_splits_history.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Mysql import BDsystem
from Modulos_python import yf, pd

ACCOUNT = "U4214563"


def get_posiciones_abiertas(cursor):
    cursor.execute(
        """SELECT b.simbolo
           FROM booktrading b
           JOIN (
               SELECT cuenta, simbolo, MAX(sec) AS max_sec
               FROM booktrading WHERE cuenta=%s AND delisted=0 GROUP BY cuenta, simbolo
           ) m ON b.cuenta=m.cuenta AND b.simbolo=m.simbolo AND b.sec=m.max_sec
           WHERE b.stock > 0
           ORDER BY b.simbolo""",
        (ACCOUNT,),
    )
    return [r[0] for r in cursor.fetchall()]


def upsert_split(cursor, symbol, split_date, ratio):
    cursor.execute(
        "SELECT id, aplicado FROM split WHERE ticket=%s AND date=%s",
        (symbol, split_date),
    )
    row = cursor.fetchone()
    if row:
        if row[1] != "Y":
            cursor.execute("UPDATE split SET aplicado='Y' WHERE id=%s", (row[0],))
            return "updated"
        return "skip"
    else:
        cursor.execute(
            "INSERT INTO split (ticket, date, split, preciocantidad, aplicado) VALUES (%s,%s,%s,'A','Y')",
            (symbol, split_date, float(ratio)),
        )
        return "inserted"


def main():
    print(__doc__)
    print(f"  Cuenta: {ACCOUNT}\n")

    conn = BDsystem.connect_dbase("init_splits")
    cursor = conn.cursor()

    symbols = get_posiciones_abiertas(cursor)
    print(f"  Posiciones abiertas: {len(symbols)} símbolos")
    print(f"  {', '.join(symbols)}\n")

    inserted, updated, skipped = 0, 0, 0

    for symbol in symbols:
        try:
            splits = yf.Ticker(symbol).splits
            if splits.empty:
                continue
            for split_date, ratio in splits.items():
                if ratio <= 0 or ratio == 1.0:
                    continue
                accion = upsert_split(cursor, symbol, split_date, float(ratio))
                if accion == "inserted":
                    inserted += 1
                    print(f"  {symbol:<10} {str(split_date.date()):<12} ratio={ratio:.4f}  [nuevo]")
                elif accion == "updated":
                    updated += 1
                    print(f"  {symbol:<10} {str(split_date.date()):<12} ratio={ratio:.4f}  [marcado Y]")
                else:
                    skipped += 1
            conn.commit()
        except Exception as e:
            print(f"  ERROR {symbol}: {e}")

    cursor.close()
    conn.close()

    print(f"\n  Insertados : {inserted}")
    print(f"  Actualizados (N→Y): {updated}")
    print(f"  Ya estaban OK: {skipped}")
    print("  Listo. El agente solo aplicará splits nuevos a partir de ahora.\n")


if __name__ == "__main__":
    main()
