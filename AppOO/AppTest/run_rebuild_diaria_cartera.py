"""
run_rebuild_diaria_cartera.py
==============================
Reconstruye diaria_performance desde booktrading completo (accion="cartera").

POR QUÉ EXISTE
--------------
schedule_diario usa accion="diaria_app" que solo devuelve compras recientes.
Para reconstruir historia completa desde una fecha purgada se necesita
accion="cartera" que trae TODO el booktrading de la cuenta.

QUÉ HACE
--------
1. select_booktrading(accion="cartera") → historia completa
2. detalle_book(option="inicio") → escribe csv_datos_Stock.csv (no colisiona con app)
3. read_csv_insert_diaria(insert=True) → inserta solo fechas > last_date por símbolo
4. proceso_update_performance → reconstruye performa_inversion desde el último gap

EJECUCIÓN
---------
    cd AppOO
    python AppTest/run_rebuild_diaria_cartera.py

NOTA: Puede tardar 5-15 min — descarga yfinance para cada símbolo.
      La app puede estar corriendo en paralelo (CSV distinto, no colisiona).
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Mysql import IPerformance, RepositorioOportunidadesBuySell, BDsystem
from Modulos_Comunes import detalle_book, read_csv_insert_diaria, actualiza_performa_inversion
from Modulos_Utilitarios import read_json_tmp, write_json_tmp

# ── CONFIGURACIÓN ──────────────────────────────────────────────────────────────
ACCOUNT = "U4214563"
VEHICULO = "Stock"
FECHA_PURGA = date(2025, 12, 20)
SCHEDULE_FILE = "agents_schedule.json"
SCHEDULE_KEY = f"diaria_{VEHICULO}"
# ──────────────────────────────────────────────────────────────────────────────


def estado(label):
    conn = BDsystem.connect_dbase("rebuild_check")
    cursor = conn.cursor()
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    cursor.execute(
        """
        SELECT MIN(Date), MAX(Date), COUNT(DISTINCT Date), COUNT(*)
        FROM diaria_performance WHERE account=%s
    """,
        (ACCOUNT,),
    )
    r = cursor.fetchone()
    print(f"  diaria_performance: {r[2]} fechas  {r[3]} filas  ({r[0]} → {r[1]})")

    cursor.execute(
        """
        SELECT MIN(fechaclose), MAX(fechaclose), COUNT(*)
        FROM performa_inversion WHERE idcuenta=%s AND vehiculo=%s
    """,
        (ACCOUNT, VEHICULO),
    )
    r = cursor.fetchone()
    print(f"  performa_inversion: {r[2]} filas  ({r[0]} → {r[1]})")
    cursor.close()
    conn.close()


def purgar_datos(conn):
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM diaria_performance WHERE account=%s AND Date >= %s",
        (ACCOUNT, FECHA_PURGA),
    )
    borrados_diaria = cursor.rowcount
    conn.commit()

    cursor.execute(
        "DELETE FROM performa_inversion WHERE idcuenta=%s AND vehiculo=%s AND fechaclose >= %s",
        (ACCOUNT, VEHICULO, FECHA_PURGA),
    )
    borrados_perf = cursor.rowcount
    conn.commit()

    cursor.close()
    print(f"        diaria_performance eliminados : {borrados_diaria}")
    print(f"        performa_inversion eliminados : {borrados_perf}")

    data = read_json_tmp(SCHEDULE_FILE)
    if SCHEDULE_KEY in data:
        del data[SCHEDULE_KEY]
        write_json_tmp(SCHEDULE_FILE, data)
        print(f"        Schedule key '{SCHEDULE_KEY}' reseteada")


def main():
    print(__doc__)
    estado("ESTADO INICIAL")

    print(f"\n  ATENCIÓN: Se purgarán diaria_performance y performa_inversion desde {FECHA_PURGA}.")
    print(f"  Esto borra datos que schedule_diario escribió con accion='diaria_app' (incompletos).")
    resp = input("\n  ¿Iniciar purga + reconstrucción completa? (s/N): ").strip().lower()
    if resp != "s":
        print("  Cancelado.")
        return

    print(f"\n  [0/4] Purgando datos desde {FECHA_PURGA} (diaria + performa)...")
    conn_purga = BDsystem.connect_dbase("rebuild_purga")
    purgar_datos(conn_purga)
    conn_purga.close()

    estado("ESTADO POST PURGA")

    ROp = RepositorioOportunidadesBuySell()

    print("\n  [1/4] Descargando booktrading completo (accion='cartera')...")
    book, ix = ROp.select_booktrading(accion="cartera", account=ACCOUNT)
    print(f"        {len(book)} entradas en booktrading")

    print(f"\n  [2/4] Generando CSV con yfinance (csv_datos_{VEHICULO}.csv)...")
    print(f"        Esto puede tardar varios minutos...")
    path = detalle_book(account=ACCOUNT, vehiculo=VEHICULO, book=book, ix=ix, option="inicio")
    if not path:
        print("  ERROR: detalle_book no generó el CSV. Abortando.")
        return
    print(f"        CSV generado: {path}")

    print(f"\n  [3/4] Insertando en diaria_performance (solo fechas faltantes)...")
    diaria, iy = read_csv_insert_diaria(path=path, insert=True)
    print(f"        {len(diaria)} filas en CSV procesadas")

    estado("ESTADO POST diaria_performance")

    print(f"\n  [4/4] Reconstruyendo performa_inversion...")
    actualiza_performa_inversion(account=ACCOUNT, vehiculo=VEHICULO)

    estado("ESTADO FINAL")
    print("\n  Listo. Reinicia la app para ver el gráfico actualizado.\n")


if __name__ == "__main__":
    main()
