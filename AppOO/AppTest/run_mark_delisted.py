"""
run_mark_delisted.py
=====================
Marca como delisted=1 en booktrading los símbolos que yfinance no puede
descargar (delistados hasta 2025-12-20).

Efecto: detalle_book saltea esos símbolos en bloque, eliminando los mensajes
"possibly delisted" repetidos durante la generación del CSV de performance.

Los símbolos con delisted=1 se saltan en:
  - detalle_book (genera csv_datos_Stock.csv / csv_app_Stock.csv)
  - cualquier accion= que ya filtra AND delisted=0 (last, select, etc.)

EJECUCIÓN
---------
    cd AppOO
    python AppTest/run_mark_delisted.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Mysql import BDsystem

ACCOUNT = "U4214563"

# Símbolos que fallan consistentemente en yfinance (verificado 2026-04-28)
# BGFV y VRLA ya tenían delisted=1 — solo los nuevos
SIMBOLOS_DELISTED = [
    "APHA",  # fusionado con Tilray → TLRY
    "AUY",  # fusionado con Agnico Eagle → AEM
    "ETM",  # Entercom → iHeartMedia, luego privada
    "GHSI",  # Guardion Health Sciences — delistada
    "GPS",  # The Gap — renombrado a GAP, ticker cambiado
    "LLNW",  # Limelight Networks → Edgio → delistada
    "NYMT",  # NY Mortgage Trust — delistada
    "PBPB",  # Potbelly — delistada
    "PLM",  # Polymet Mining — tomada privada
    "SSUP",  # Superior Industries — delistada
    "STON",  # StoneMor Partners — convertida en privada
    "STOR",  # STORE Capital → adquirida por GIC
    "ZVO",  # Zovio — cerrada
    "ZY",  # Zymergen → adquirida por Ginkgo Bioworks
    "CFRXQ",  # Correvio Pharma — quebrada, cotización OTC detenida desde oct-2023
    "GOEVQ",  # Canoo Inc. — quiebra, ticker OTC; stock=-0.8 (artefacto redondeo fracciones)
    "BTC CRYPTO",  # Bitcoin en cuenta IB Stock — es cripto, no Stock; posición cerrada (stock=0)
    "ETH CRYPTO",  # Ethereum en cuenta IB Stock — ídem BTC CRYPTO
    "MATIC CRYPTO",  # Polygon en cuenta IB Stock — ídem BTC CRYPTO
]

# Corrección stock anómalo: GOEVQ quedó en -0.8 por redondeo de fracciones al vender
# El UPDATE de stock=0 aplica solo a la última fila (la que tiene el -0.8 residual)
STOCK_FIXES = {
    "GOEVQ": {"stock_actual": -0.8, "stock_correcto": 0.0},
}


def mostrar_estado(cursor):
    ph = ",".join(["%s"] * len(SIMBOLOS_DELISTED))
    cursor.execute(
        f"""
        SELECT simbolo, delisted, COUNT(*) as filas, MAX(fechahora) as ultima, SUM(stock) as stock_total
        FROM booktrading
        WHERE cuenta=%s AND simbolo IN ({ph})
        GROUP BY simbolo, delisted
        ORDER BY simbolo
        """,
        [ACCOUNT] + SIMBOLOS_DELISTED,
    )
    rows = cursor.fetchall()
    print(f"\n  {'Símbolo':<12} {'delisted':>8} {'filas':>6} {'stock':>10}  ultima_op")
    print(f"  {'-'*12} {'-'*8} {'-'*6} {'-'*10}  {'-'*20}")
    for r in rows:
        print(f"  {r[0]:<12} {r[1]:>8} {r[2]:>6} {r[3]:>10.1f}  {r[4]}")
    return rows


def main():
    print(__doc__)
    print(f"  Cuenta  : {ACCOUNT}")
    print(f"  Símbolos: {SIMBOLOS_DELISTED}")

    conn = BDsystem.connect_dbase("mark_delisted")
    cursor = conn.cursor()

    print(f"\n{'='*65}")
    print("  ESTADO ANTES")
    print(f"{'='*65}")
    mostrar_estado(cursor)

    ph = ",".join(["%s"] * len(SIMBOLOS_DELISTED))
    cursor.execute(
        f"SELECT COUNT(*) FROM booktrading WHERE cuenta=%s AND simbolo IN ({ph}) AND delisted=0",
        [ACCOUNT] + SIMBOLOS_DELISTED,
    )
    total = cursor.fetchone()[0]
    print(f"\n  Filas a actualizar (delisted 0→1): {total}")

    resp = input("\n  ¿Confirmar marcado como delisted=1? (s/N): ").strip().lower()
    if resp != "s":
        print("  Cancelado.")
        cursor.close()
        conn.close()
        return

    cursor.execute(
        f"UPDATE booktrading SET delisted=1 WHERE cuenta=%s AND simbolo IN ({ph})",
        [ACCOUNT] + SIMBOLOS_DELISTED,
    )
    actualizados = cursor.rowcount
    conn.commit()
    print(f"  Filas actualizadas: {actualizados}")

    # Correcciones de stock anómalo
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
    print("\n  Listo. La próxima generación de CSV no descargará estos símbolos.\n")


if __name__ == "__main__":
    main()
