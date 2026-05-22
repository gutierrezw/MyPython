import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_Mysql import BDsystem

_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_PROFILE = os.path.join(_BASE, "profiles", "main.json")
if os.path.exists(_PROFILE):
    with open(_PROFILE, encoding="utf-8") as _f:
        _cfg = json.load(_f)
    if _cfg.get("db"):
        BDsystem.configure(_cfg["db"])
    if _cfg.get("tmp_path"):
        os.environ["APPOO_TMP"] = _cfg["tmp_path"]

SQL_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS market_sentiment (
        symbol          VARCHAR(10)  NOT NULL,
        fecha_hora      DATETIME     NOT NULL,
        sentimiento     TINYINT      NOT NULL,
        headlines_count TINYINT      DEFAULT 0,
        fuente          VARCHAR(10)  DEFAULT 'yahoo',
        PRIMARY KEY (symbol, fecha_hora),
        INDEX idx_symbol_fecha (symbol, fecha_hora)
    )""",
    """CREATE TABLE IF NOT EXISTS market_sentiment_analysis (
        symbol          VARCHAR(10)  NOT NULL,
        fecha           DATE         NOT NULL,
        interpretacion  TEXT,
        patron          VARCHAR(20)  DEFAULT 'neutro',
        PRIMARY KEY (symbol, fecha)
    )""",
]

if __name__ == "__main__":
    conn = BDsystem.connect_dbase("create.sentiment_tables")
    if not conn:
        print("ERROR: no se pudo conectar a la base de datos")
        sys.exit(1)

    cursor = conn.cursor()
    for sql in SQL_STATEMENTS:
        table_name = sql.split("EXISTS")[1].strip().split()[0]
        try:
            cursor.execute(sql)
            conn.commit()
            print(f"OK: {table_name}")
        except Exception as e:
            print(f"ERROR en {table_name}: {e}")

    cursor.close()
    conn.close()
    print("Listo.")
