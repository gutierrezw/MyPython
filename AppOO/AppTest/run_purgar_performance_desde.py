"""
run_purgar_performance_desde.py
===============================
Herramienta de reparación de datos de performance.

PROPÓSITO
---------
Elimina todos los registros de diaria_performance y performa_inversion
a partir de una fecha dada, y resetea el schedule diario para que el
proceso automático (schedule_diario) reconstruya ambas tablas desde cero
en el próximo ciclo.

CUÁNDO USAR
-----------
- Cuando yfinance devuelve precios corruptos para algún símbolo y esos
  valores ya fueron procesados e insertados en las tablas.
- Cuando se detectan valores absurdos en nr_gyp, value o costo_base
  (ej: value 1000x mayor o 100x menor al costo promedio del activo).
- Después de corregir datos en booktrading que afectan el cálculo histórico.

QUÉ HACE
--------
1. Muestra el estado actual de ambas tablas (fechas y totales).
2. Pide confirmación antes de eliminar.
3. Elimina desde FECHA_PURGA (inclusive) en:
     - diaria_performance  (filtro: account + Date)
     - performa_inversion  (filtro: idcuenta + vehiculo + fechaclose)
4. Resetea la clave del schedule JSON para que schedule_diario reprocese.
5. Muestra el estado resultante para verificar.

CÓMO CONFIGURAR
---------------
Ajustar las constantes en la sección "CONFIGURACIÓN" antes de correr.

EJECUCIÓN
---------
    cd AppOO
    python AppTest/run_purgar_performance_desde.py
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Mysql import IPerformance, BDsystem
from Modulos_Utilitarios import read_json_tmp, write_json_tmp

# ── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
ACCOUNT = "U4214563"
VEHICULO = "Stock"
FECHA_PURGA = date(2026, 4, 15)  # fecha inclusive desde donde se purga
SCHEDULE_FILE = "agents_schedule.json"
SCHEDULE_KEY = f"diaria_{VEHICULO}"
# ──────────────────────────────────────────────────────────────────────────────


def mostrar_estado(conn, label):
    cursor = conn.cursor()
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")

    cursor.execute(
        """
        SELECT min(Date) as first, max(Date) as last, count(*) as total
        FROM diaria_performance
        WHERE account = %s
        """,
        (ACCOUNT,),
    )
    row = cursor.fetchone()
    print(f"  diaria_performance : first={row[0]}  last={row[1]}  total={row[2]}")

    cursor.execute(
        """
        SELECT min(fechaclose) as first, max(fechaclose) as last, count(*) as total
        FROM performa_inversion
        WHERE idcuenta = %s AND vehiculo = %s
        """,
        (ACCOUNT, VEHICULO),
    )
    row = cursor.fetchone()
    print(f"  performa_inversion : first={row[0]}  last={row[1]}  total={row[2]}")

    cursor.close()


def main():
    print(__doc__)
    print(f"  Cuenta   : {ACCOUNT}")
    print(f"  Vehículo : {VEHICULO}")
    print(f"  Purgar desde: {FECHA_PURGA}  (inclusive)")

    conn_check = BDsystem.connect_dbase("check_purgar")
    mostrar_estado(conn_check, "ESTADO ANTES DE LA PURGA")
    conn_check.close()

    print(f"\n  Se eliminarán registros con Date / fechaclose >= {FECHA_PURGA}")
    print(f"  También se reseteará '{SCHEDULE_KEY}' en {SCHEDULE_FILE}")
    resp = input("\n  ¿Confirmar purga? (s/N): ").strip().lower()
    if resp != "s":
        print("  Operación cancelada.")
        return

    print("\n  Ejecutando purga...")
    Performa = IPerformance()
    resultado = Performa.purgar_desde(account=ACCOUNT, vehiculo=VEHICULO, desde=FECHA_PURGA)
    print(f"  diaria_performance eliminados : {resultado['diaria']}")
    print(f"  performa_inversion eliminados : {resultado['performa']}")

    data = read_json_tmp(SCHEDULE_FILE)
    if SCHEDULE_KEY in data:
        del data[SCHEDULE_KEY]
        write_json_tmp(SCHEDULE_FILE, data)
        print(f"  Schedule key '{SCHEDULE_KEY}' reseteada en {SCHEDULE_FILE}")
    else:
        print(f"  Schedule key '{SCHEDULE_KEY}' no existía en {SCHEDULE_FILE} (sin cambios)")

    conn_check = BDsystem.connect_dbase("check_purgar_post")
    mostrar_estado(conn_check, "ESTADO DESPUÉS DE LA PURGA")
    conn_check.close()

    print("\n  Listo. En el próximo ciclo schedule_diario reconstruye desde la última")
    print(f"  fecha válida en diaria_performance hasta hoy.")


if __name__ == "__main__":
    main()
