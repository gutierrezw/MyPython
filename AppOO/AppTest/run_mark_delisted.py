"""
run_mark_delisted.py
=====================
Marca como delisted=1 en booktrading los símbolos que yfinance no puede descargar.

fecha_deliste: fecha en que dejó de cotizar.
  - Con fecha → detalle_book procesa hasta esa fecha y registra value=0 (pérdida total)
  - Sin fecha (None) → detalle_book saltea completamente (comportamiento actual)

EJECUCIÓN
---------
    cd AppOO
    python AppTest/run_mark_delisted.py
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Mysql import BDsystem

ACCOUNT = "U4214563"

# Clave: símbolo. fecha_deliste=None → skip total; date → procesa hasta esa fecha
SIMBOLOS_DELISTED = {
    "APHA": {"fecha_deliste": date(2021, 3, 27), "nota": "fusionado con Tilray → TLRY"},
    "AUY": {"fecha_deliste": date(2022, 2, 9), "nota": "fusionado con Agnico Eagle → AEM"},
    "ETM": {"fecha_deliste": None, "nota": "Entercom → renombrado/privada"},
    "GHSI": {"fecha_deliste": None, "nota": "Guardion Health Sciences — delistada"},
    "GPS": {"fecha_deliste": None, "nota": "The Gap — ticker cambiado"},
    "LLNW": {"fecha_deliste": date(2023, 11, 17), "nota": "Limelight → Edgio → delistada"},
    "NYMT": {"fecha_deliste": None, "nota": "NY Mortgage Trust — delistada"},
    "PBPB": {"fecha_deliste": None, "nota": "Potbelly — delistada"},
    "PLM": {"fecha_deliste": None, "nota": "Polymet Mining — tomada privada"},
    "SSUP": {"fecha_deliste": None, "nota": "Superior Industries — delistada"},
    "STON": {"fecha_deliste": None, "nota": "StoneMor Partners — privada"},
    "STOR": {"fecha_deliste": date(2023, 1, 23), "nota": "STORE Capital → adquirida por GIC"},
    "ZVO": {"fecha_deliste": date(2022, 10, 27), "nota": "Zovio — cerrada"},
    "ZY": {"fecha_deliste": None, "nota": "Zymergen → adquirida por Ginkgo Bioworks"},
    "CFRXQ": {"fecha_deliste": date(2023, 10, 1), "nota": "Correvio Pharma — quebrada, OTC detenida oct-2023"},
    "GOEVQ": {"fecha_deliste": date(2025, 1, 6), "nota": "Canoo Inc. — quiebra capítulo 7"},
    "BTC CRYPTO": {"fecha_deliste": None, "nota": "Bitcoin en cuenta IB Stock — posición cerrada"},
    "ETH CRYPTO": {"fecha_deliste": None, "nota": "Ethereum en cuenta IB Stock — posición cerrada"},
    "MATIC CRYPTO": {"fecha_deliste": None, "nota": "Polygon en cuenta IB Stock — posición cerrada"},
}

# Corrección stock anómalo: GOEVQ quedó en -0.8 por redondeo de fracciones al vender
STOCK_FIXES = {
    "GOEVQ": {"stock_actual": -0.8, "stock_correcto": 0.0},
}


def mostrar_estado(cursor):
    simbolos = list(SIMBOLOS_DELISTED.keys())
    ph = ",".join(["%s"] * len(simbolos))
    cursor.execute(
        f"""
        SELECT simbolo, delisted, fecha_deliste, COUNT(*) as filas,
               MAX(fechahora) as ultima, MAX(stock) as stock_max
        FROM booktrading
        WHERE cuenta=%s AND simbolo IN ({ph})
        GROUP BY simbolo, delisted, fecha_deliste
        ORDER BY simbolo
        """,
        [ACCOUNT] + simbolos,
    )
    rows = cursor.fetchall()
    print(f"\n  {'Símbolo':<12} {'del':>3} {'fecha_deliste':<14} {'filas':>5} {'stock_max':>10}  ultima_op")
    print(f"  {'-'*12} {'-'*3} {'-'*14} {'-'*5} {'-'*10}  {'-'*20}")
    for r in rows:
        fd = str(r[2]) if r[2] else "—"
        print(f"  {r[0]:<12} {r[1]:>3} {fd:<14} {r[3]:>5} {float(r[5] or 0):>10.2f}  {r[4]}")
    return rows


def main():
    print(__doc__)
    print(f"  Cuenta  : {ACCOUNT}")
    print(f"  Símbolos: {len(SIMBOLOS_DELISTED)}")

    conn = BDsystem.connect_dbase("mark_delisted")
    cursor = conn.cursor()

    print(f"\n{'='*65}")
    print("  ESTADO ANTES")
    print(f"{'='*65}")
    mostrar_estado(cursor)

    con_fecha = sum(1 for v in SIMBOLOS_DELISTED.values() if v["fecha_deliste"] is not None)
    sin_fecha = len(SIMBOLOS_DELISTED) - con_fecha
    print(f"\n  Con fecha_deliste : {con_fecha} (aportan hasta su fecha de cierre)")
    print(f"  Sin fecha_deliste : {sin_fecha} (skip total)")

    resp = input("\n  ¿Confirmar marcado como delisted=1 + fecha_deliste? (s/N): ").strip().lower()
    if resp != "s":
        print("  Cancelado.")
        cursor.close()
        conn.close()
        return

    actualizados = 0
    for simbolo, info in SIMBOLOS_DELISTED.items():
        fd = info["fecha_deliste"]
        if fd is not None:
            cursor.execute(
                "UPDATE booktrading SET delisted=1, fecha_deliste=%s WHERE cuenta=%s AND simbolo=%s",
                (fd, ACCOUNT, simbolo),
            )
        else:
            cursor.execute(
                "UPDATE booktrading SET delisted=1 WHERE cuenta=%s AND simbolo=%s",
                (ACCOUNT, simbolo),
            )
        actualizados += cursor.rowcount
        conn.commit()

    print(f"  Filas actualizadas: {actualizados}")

    for simbolo, fix in STOCK_FIXES.items():
        cursor.execute(
            "UPDATE booktrading SET stock=%s WHERE cuenta=%s AND simbolo=%s AND stock=%s",
            (fix["stock_correcto"], ACCOUNT, simbolo, fix["stock_actual"]),
        )
        filas = cursor.rowcount
        conn.commit()
        if filas:
            print(f"  {simbolo}: stock corregido {fix['stock_actual']} → {fix['stock_correcto']} ({filas} fila)")

    print(f"\n{'='*65}")
    print("  ESTADO DESPUÉS")
    print(f"{'='*65}")
    mostrar_estado(cursor)

    cursor.close()
    conn.close()
    print("\n  Listo.")
    print("  Próximo rebuild incluirá contribución de símbolos con fecha_deliste.\n")


if __name__ == "__main__":
    main()
