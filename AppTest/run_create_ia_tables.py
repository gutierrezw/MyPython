"""Crea las tablas ia_trace e ia_mejoras en bdinv. Ejecutar una sola vez."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "AppOO"))

import Modulos_python  # noqa: F401
from Modulos_Mysql import BDsystem

_profile = os.path.join(os.path.dirname(__file__), "..", "AppOO", "profiles", "main.json")
with open(_profile, encoding="utf-8") as _f:
    BDsystem.configure(json.load(_f).get("db", {}))

SQLS = [
    """
    CREATE TABLE IF NOT EXISTS ia_trace (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        timestamp   DATETIME         DEFAULT CURRENT_TIMESTAMP,
        vehiculo    VARCHAR(20)      NOT NULL,
        simbolo     VARCHAR(20),
        decision    ENUM('BUY','SELL','HOLD','ALERTA') NOT NULL,
        monto       DECIMAL(12,2)    DEFAULT 0,
        motivo      TEXT,
        gates_ok    JSON,
        estado      ENUM('PENDIENTE','APROBADO','IGNORADO','EJECUTADO','FALLIDO') DEFAULT 'PENDIENTE',
        telegram_id VARCHAR(50),
        INDEX idx_timestamp (timestamp),
        INDEX idx_vehiculo_decision (vehiculo, decision),
        INDEX idx_estado (estado)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS ia_mejoras (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        timestamp   DATETIME         DEFAULT CURRENT_TIMESTAMP,
        categoria   ENUM('agente','datos','proceso','decision','ui') NOT NULL,
        titulo      VARCHAR(200)     NOT NULL,
        descripcion TEXT,
        impacto     ENUM('alto','medio','bajo') DEFAULT 'medio',
        estado      ENUM('pendiente','en_revision','adoptado','descartado') DEFAULT 'pendiente',
        origen      VARCHAR(100),
        INDEX idx_estado (estado),
        INDEX idx_categoria (categoria)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

conn = BDsystem.connect_dbase("create_ia_tables", False)
cursor = conn.cursor()
for sql in SQLS:
    nombre = "ia_trace" if "ia_trace" in sql else "ia_mejoras"
    cursor.execute(sql.strip())
    print(f"OK — tabla {nombre} creada (o ya existía)")
conn.commit()
cursor.close()
conn.close()
print("\nListo. Ahora ejecutá: python AppTest/run_setup_agente_ia.py")
