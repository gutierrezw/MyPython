from pymysql import connect

ACCOUNT = "U4214563"
DB = {"user": "root", "password": "", "host": "localhost", "database": "bdinv"}

conn = connect(**DB)
c = conn.cursor()

c.execute("""
    SELECT symbol, shortName, categoriaActivo, encartera
    FROM market WHERE account=%s
    AND categoriaActivo='X'
    ORDER BY encartera DESC, symbol
""", (ACCOUNT,))
rows = c.fetchall()

print(f"{'Symbol':<10} {'Nombre':<45} {'Cat':>4} {'Cartera':>8}")
print("-" * 72)
for r in rows:
    print(f"{r[0]:<10} {(r[1] or '')[:44]:<45} {r[2]:>4} {r[3]:>8}")
print(f"\nTotal ETF/Fondos en market: {len(rows)}")

a_eliminar = [r[0] for r in rows if (r[3] or "").strip() != "Y"]
en_cartera  = [r[0] for r in rows if (r[3] or "").strip() == "Y"]

print(f"\nEn cartera (audit_portfolio los gestiona): {en_cartera}")
print(f"A eliminar (no en cartera, categoriaActivo=X): {a_eliminar}")

if not a_eliminar:
    print("\nNada que eliminar.")
else:
    resp = input(f"\n¿Eliminar {len(a_eliminar)} registros de market? [s/N]: ").strip().lower()
    if resp == "s":
        eliminados = 0
        for sym in a_eliminar:
            c.execute("DELETE FROM market WHERE symbol=%s AND account=%s", (sym, ACCOUNT))
            print(f"  eliminado: {sym}")
            eliminados += 1
        conn.commit()
        print(f"\nTotal eliminados: {eliminados}")
    else:
        print("Cancelado.")

conn.close()
