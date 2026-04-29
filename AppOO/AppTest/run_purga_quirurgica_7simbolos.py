"""
run_purga_quirurgica_7simbolos.py
==================================
Purga quirúrgica de 7 símbolos con gaps en diaria_performance desde 2025-12-20.

QUÉ HACE
--------
1. Borra en diaria_performance SOLO los 7 símbolos desde FECHA_PURGA.
   El resto de los 38 símbolos NO se toca.
2. Borra performa_inversion completo desde FECHA_PURGA (es agregado de cartera,
   necesita recalcularse con los datos corregidos de los 7 símbolos).
3. Resetea la clave del schedule JSON para que schedule_diario reprocese.

RESULTADO ESPERADO
------------------
- Los 7 símbolos quedan con last_date = día anterior a FECHA_PURGA en diaria_performance.
- El próximo schedule_diario descarga yfinance desde esa fecha y rellena
  el gap con el fix de Series aplicado (sin colisión de columnas duplicadas).
- performa_inversion se reconstruye automáticamente desde FECHA_PURGA.

EJECUCIÓN
---------
    cd AppOO
    python AppTest/run_purga_quirurgica_7simbolos.py
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Mysql import BDsystem
from Modulos_Utilitarios import read_json_tmp, write_json_tmp

# ── CONFIGURACIÓN ──────────────────────────────────────────────────────────────
ACCOUNT = "U4214563"
VEHICULO = "Stock"
FECHA_PURGA = date(2025, 12, 20)
SIMBOLOS = ["BBAI", "CHPT", "PFE", "SKLZ", "SNDL", "TLRY", "UUUU"]
SCHEDULE_FILE = "agents_schedule.json"
SCHEDULE_KEY = f"diaria_{VEHICULO}"
# ──────────────────────────────────────────────────────────────────────────────

PH = ",".join(["%s"] * len(SIMBOLOS))


def mostrar_estado(cursor, label):
    print(f"\n{'=' * 65}")
    print(f"  {label}")
    print(f"{'=' * 65}")

    print(f"\n  diaria_performance — 7 símbolos:")
    cursor.execute(
        f"""
        SELECT symbol, MIN(Date) as first, MAX(Date) as last, COUNT(*) as n
        FROM diaria_performance
        WHERE account=%s AND symbol IN ({PH})
        GROUP BY symbol ORDER BY symbol
    """,
        [ACCOUNT] + SIMBOLOS,
    )
    for r in cursor.fetchall():
        print(f"    {r[0]:<8}  first={r[1]}  last={r[2]}  rows={r[3]}")

    cursor.execute(
        f"""
        SELECT MIN(Date), MAX(Date), COUNT(*)
        FROM diaria_performance
        WHERE account=%s AND symbol IN ({PH})
        AND Date >= %s
    """,
        [ACCOUNT] + SIMBOLOS + [FECHA_PURGA],
    )
    r = cursor.fetchone()
    print(f"\n  Filas >= {FECHA_PURGA}: {r[2]}  (first={r[0]}  last={r[1]})")

    print(f"\n  performa_inversion — cartera completa:")
    cursor.execute(
        """
        SELECT MIN(fechaclose), MAX(fechaclose), COUNT(*)
        FROM performa_inversion
        WHERE idcuenta=%s AND vehiculo=%s AND fechaclose >= %s
    """,
        (ACCOUNT, VEHICULO, FECHA_PURGA),
    )
    r = cursor.fetchone()
    print(f"  Filas >= {FECHA_PURGA}: {r[2]}  (first={r[0]}  last={r[1]})")


def main():
    print(__doc__)
    print(f"  Cuenta    : {ACCOUNT}")
    print(f"  Vehículo  : {VEHICULO}")
    print(f"  Fecha purga: {FECHA_PURGA}  (inclusive)")
    print(f"  Símbolos  : {SIMBOLOS}")

    conn = BDsystem.connect_dbase("purga_quirurgica")
    cursor = conn.cursor()

    mostrar_estado(cursor, "ESTADO ANTES DE LA PURGA")

    # preview exacto de lo que se borrará
    cursor.execute(
        f"""
        SELECT symbol, COUNT(*) as n, MIN(Date), MAX(Date)
        FROM diaria_performance
        WHERE account=%s AND symbol IN ({PH}) AND Date >= %s
        GROUP BY symbol ORDER BY symbol
    """,
        [ACCOUNT] + SIMBOLOS + [FECHA_PURGA],
    )
    rows_diaria = cursor.fetchall()

    cursor.execute(
        """
        SELECT COUNT(*), MIN(fechaclose), MAX(fechaclose)
        FROM performa_inversion
        WHERE idcuenta=%s AND vehiculo=%s AND fechaclose >= %s
    """,
        (ACCOUNT, VEHICULO, FECHA_PURGA),
    )
    r_perf = cursor.fetchone()

    print(f"\n  {'─'*60}")
    print(f"  SE BORRARÁN:")
    print(f"  diaria_performance (7 símbolos desde {FECHA_PURGA}):")
    total_diaria = 0
    for r in rows_diaria:
        print(f"    {r[0]:<8}  {r[1]:>4} filas  ({r[2]} → {r[3]})")
        total_diaria += r[1]
    print(f"    Total: {total_diaria} filas")
    print(f"  performa_inversion (cartera completa desde {FECHA_PURGA}):")
    print(f"    {r_perf[0]} filas  ({r_perf[1]} → {r_perf[2]})")

    resp = input(f"\n  ¿Confirmar purga? (s/N): ").strip().lower()
    if resp != "s":
        print("  Operación cancelada.")
        cursor.close()
        conn.close()
        return

    print("\n  Ejecutando purga...")

    # 1. Borrar diaria_performance solo los 7 simbolos
    cursor.execute(
        f"""
        DELETE FROM diaria_performance
        WHERE account=%s AND symbol IN ({PH}) AND Date >= %s
    """,
        [ACCOUNT] + SIMBOLOS + [FECHA_PURGA],
    )
    borrados_diaria = cursor.rowcount
    conn.commit()
    print(f"  diaria_performance eliminados : {borrados_diaria}")

    # 2. Borrar performa_inversion completo desde fecha (es agregado, recalcula todo)
    cursor.execute(
        """
        DELETE FROM performa_inversion
        WHERE idcuenta=%s AND vehiculo=%s AND fechaclose >= %s
    """,
        (ACCOUNT, VEHICULO, FECHA_PURGA),
    )
    borrados_perf = cursor.rowcount
    conn.commit()
    print(f"  performa_inversion eliminados : {borrados_perf}")

    # 3. Resetear schedule key
    data = read_json_tmp(SCHEDULE_FILE)
    if SCHEDULE_KEY in data:
        del data[SCHEDULE_KEY]
        write_json_tmp(SCHEDULE_FILE, data)
        print(f"  Schedule key '{SCHEDULE_KEY}' reseteada")
    else:
        print(f"  Schedule key '{SCHEDULE_KEY}' no existía (sin cambios)")

    mostrar_estado(cursor, "ESTADO DESPUÉS DE LA PURGA")

    cursor.close()
    conn.close()

    print(f"""
  Listo. El próximo schedule_diario reconstruirá:
  - Los 7 símbolos desde su last_date hasta hoy (yfinance con fix de Series)
  - performa_inversion desde {FECHA_PURGA} en adelante
  Puede tardar varios minutos la primera ejecución (descarga histórica).
""")


if __name__ == "__main__":
    main()
