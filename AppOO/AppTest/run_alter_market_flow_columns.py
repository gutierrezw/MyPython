"""
run_alter_market_flow_columns.py
Agrega las 4 columnas de señales de flujo institucional a la tabla market.
Ejecutar una sola vez.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_Mysql import MarketScreen

mkt = MarketScreen()
conn = mkt._conectar(tabla="select.market")
c = conn.cursor()

nuevas = [
    ("new_entrants", "INT DEFAULT NULL"),
    ("full_exits", "INT DEFAULT NULL"),
    ("delta_call_shares", "BIGINT DEFAULT NULL"),
    ("delta_put_shares", "BIGINT DEFAULT NULL"),
]

c.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='market'")
existentes = {r[0] for r in c.fetchall()}

for col, typedef in nuevas:
    if col in existentes:
        print(f"YA EXISTE: {col}")
        continue
    try:
        c.execute(f"ALTER TABLE market ADD COLUMN {col} {typedef}")
        conn.commit()
        print(f"OK: {col}")
    except Exception as e:
        print(f"ERROR {col}: {e}")

conn.close()
print("Listo.")
