"""
Configura el bloque "agente_ia" en la llave_privada del vehículo Stock.
Hace merge con el JSON existente (no sobrescribe preservation ni otros bloques).
Ejecutar una sola vez.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "AppOO"))

import Modulos_python  # noqa: F401 — inicializa imports compartidos
from Modulos_Mysql import BDsystem

_profile = os.path.join(os.path.dirname(__file__), "..", "AppOO", "profiles", "main.json")
with open(_profile, encoding="utf-8") as _f:
    _cfg = json.load(_f)
BDsystem.configure(_cfg.get("db", {}))

VEHICULO = "Stock"

AGENTE_IA_DEFAULTS = {
    "activo": False,
    "modo": "autorizado",
    "monto_por_trade": 170,
    "deuda_max_pct": 35,
    "leverage_max": 1.8,
    "risk_real_max": 2.0,
    "gate_consenso_min": 4,
    "gate_inst_score_min": 0.5,
    "yield_min_sobre_costo": True,
}

conn = BDsystem.connect_dbase("setup_agente_ia", False)
cursor = conn.cursor()
cursor.execute("SELECT parameters FROM sesion WHERE vehiculo = %s", (VEHICULO,))
row = cursor.fetchone()
if not row:
    print(f"ERROR: vehículo '{VEHICULO}' no encontrado en sesion")
    sys.exit(1)

raw = row[0]
params = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw) if raw else {}
print(f"JSON actual: {json.dumps(params, indent=2)}")

if "agente_ia" in params:
    print("\nagente_ia ya existe — actualizando solo claves faltantes...")
    for k, v in AGENTE_IA_DEFAULTS.items():
        params["agente_ia"].setdefault(k, v)
else:
    params["agente_ia"] = AGENTE_IA_DEFAULTS
    print("\nagente_ia agregado.")

nuevo_json = json.dumps(params, ensure_ascii=False)
cursor.execute("UPDATE sesion SET parameters = %s WHERE vehiculo = %s", (nuevo_json, VEHICULO))
conn.commit()
cursor.close()
conn.close()
print(f"\nOK — parameters actualizado para '{VEHICULO}'")
print(f"agente_ia.activo = {params['agente_ia']['activo']}  (cambiar a True cuando estés listo)")
