import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Modulos_Mysql import MarketScreen

market = MarketScreen()

print("=" * 70)
print("fix fund_holdings — eliminar duplicados + reparar UNIQUE KEY")
print("=" * 70)

conn = market._conectar(tabla="update.market")
cur = conn.cursor()

try:
    # 1. Contar estado actual
    cur.execute("SELECT COUNT(*) FROM fund_holdings")
    total_antes = cur.fetchone()[0]
    print(f"\nTotal filas antes : {total_antes:,}")

    cur.execute("""
        SELECT SUM(cnt - 1) FROM (
            SELECT COUNT(*) cnt
            FROM fund_holdings
            GROUP BY fund_id, cusip, report_date, COALESCE(option_type, 'STK')
            HAVING cnt > 1
        ) t
    """)
    extras = cur.fetchone()[0] or 0
    print(f"Filas extra (dup) : {extras:,}")

    if extras == 0:
        print("\nSin duplicados — nada que limpiar.")
    else:
        # 2. Eliminar duplicados conservando el id más bajo por grupo
        print("\nEliminando duplicados (conserva menor id por grupo)...")
        cur.execute("""
            DELETE fh1 FROM fund_holdings fh1
            INNER JOIN fund_holdings fh2
              ON  fh1.fund_id     = fh2.fund_id
              AND fh1.cusip       = fh2.cusip
              AND fh1.report_date = fh2.report_date
              AND COALESCE(fh1.option_type, 'STK') = COALESCE(fh2.option_type, 'STK')
              AND fh1.id > fh2.id
        """)
        conn.commit()
        eliminados = cur.rowcount
        print(f"  filas eliminadas: {eliminados:,}")

    # 3. Normalizar option_type NULL → 'STK' (posición en acciones, no opción)
    print("\nNormalizando option_type NULL → 'STK'...")
    cur.execute("UPDATE fund_holdings SET option_type = 'STK' WHERE option_type IS NULL")
    conn.commit()
    print(f"  filas normalizadas: {cur.rowcount:,}")

    # 4. Reparar el UNIQUE KEY para incluir option_type como NOT NULL
    print("\nReparando UNIQUE KEY uq_holding...")
    cur.execute("ALTER TABLE fund_holdings DROP INDEX uq_holding")
    conn.commit()
    cur.execute("""
        ALTER TABLE fund_holdings
        MODIFY COLUMN option_type VARCHAR(10) NOT NULL DEFAULT 'STK',
        ADD UNIQUE KEY uq_holding (fund_id, cusip, report_date, option_type)
    """)
    conn.commit()
    print("  UNIQUE KEY recreado con option_type NOT NULL DEFAULT 'STK'")

    # 5. Estado final
    cur.execute("SELECT COUNT(*) FROM fund_holdings")
    total_despues = cur.fetchone()[0]
    print(f"\nTotal filas después : {total_despues:,}")
    print(f"Reducción           : {total_antes - total_despues:,} filas")

finally:
    cur.close()
    conn.close()

print("\nListo.")
