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

alteraciones = [
    "ALTER TABLE market ADD COLUMN IF NOT EXISTS new_entrants INT DEFAULT NULL",
    "ALTER TABLE market ADD COLUMN IF NOT EXISTS full_exits INT DEFAULT NULL",
    "ALTER TABLE market ADD COLUMN IF NOT EXISTS delta_call_shares BIGINT DEFAULT NULL",
    "ALTER TABLE market ADD COLUMN IF NOT EXISTS delta_put_shares BIGINT DEFAULT NULL",
]

for sql in alteraciones:
    try:
        c.execute(sql)
        conn.commit()
        col = sql.split("COLUMN IF NOT EXISTS ")[1].split(" ")[0]
        print(f"OK: {col}")
    except Exception as e:
        print(f"ERROR: {e}")

conn.close()
print("Listo.")
