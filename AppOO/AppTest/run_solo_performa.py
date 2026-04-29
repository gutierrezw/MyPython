"""
run_solo_performa.py
====================
Reconstruye performa_inversion desde el último gap en diaria_performance.
Usar cuando diaria_performance ya está correcta pero performa_inversion quedó desactualizada.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Comunes import actualiza_performa_inversion
from Modulos_Mysql import BDsystem

ACCOUNT = "U4214563"
VEHICULO = "Stock"


def estado():
    conn = BDsystem.connect_dbase("check_performa")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT MIN(fechaclose), MAX(fechaclose), COUNT(*) FROM performa_inversion WHERE idcuenta=%s AND vehiculo=%s",
        (ACCOUNT, VEHICULO),
    )
    r = cursor.fetchone()
    print(f"  performa_inversion: {r[2]} filas  ({r[0]} → {r[1]})")
    cursor.close()
    conn.close()


print("Estado antes:")
estado()

print("\nReconstruyendo performa_inversion...")
actualiza_performa_inversion(account=ACCOUNT, vehiculo=VEHICULO)

print("\nEstado después:")
estado()
print("\nListo.")
