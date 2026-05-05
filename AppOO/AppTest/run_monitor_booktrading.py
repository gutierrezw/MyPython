"""
run_monitor_booktrading.py
===========================
Compara el stock del último registro en booktrading contra inversion.position
(fuente de verdad sincronizada desde IB).

Detecta cuando booktrading.stock queda desincronizado del position real —
síntoma del bug de múltiples inserts mismo símbolo/fecha.

EJECUCIÓN
---------
    cd AppOO
    python AppTest/run_monitor_booktrading.py              # cuenta default U4214563
    python AppTest/run_monitor_booktrading.py B0000001     # otra cuenta
    python AppTest/run_monitor_booktrading.py U4214563 --fix  # muestra SQLs correctivos (no ejecuta)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Mysql import BDsystem

ACCOUNT_DEFAULT = "U4214563"
TOLERANCE = 0.5


def main():
    account = sys.argv[1] if len(sys.argv) > 1 else ACCOUNT_DEFAULT
    show_fix = "--fix" in sys.argv

    conn = BDsystem.connect_dbase("monitor_booktrading")
    cursor = conn.cursor()

    # Último stock por símbolo en booktrading (posiciones abiertas)
    cursor.execute(
        """
        SELECT b.simbolo, b.id, b.fechahora, b.sec, b.stock
        FROM booktrading b
        INNER JOIN (
            SELECT simbolo, MAX(fechahora) AS max_fh
            FROM booktrading
            WHERE cuenta = %s AND delisted = 0
            GROUP BY simbolo
        ) ult ON b.simbolo = ult.simbolo AND b.fechahora = ult.max_fh
        WHERE b.cuenta = %s AND b.delisted = 0
        ORDER BY b.simbolo ASC, b.sec DESC
        """,
        (account, account),
    )
    book_rows = {}
    for row in cursor.fetchall():
        simbolo, id_, fechahora, sec, stock = row
        if simbolo not in book_rows:
            book_rows[simbolo] = {"id": id_, "fechahora": fechahora, "sec": sec, "stock": float(stock or 0)}

    # Position real desde inversion (sincronizada desde IB)
    cursor.execute(
        "SELECT ticket, position FROM inversion WHERE useraccount = %s AND iactiva = 'Y'",
        (account,),
    )
    inv_rows = {r[0]: float(r[1] or 0) for r in cursor.fetchall()}

    cursor.close()
    conn.close()

    # Símbolos activos en inversion que también tienen booktrading
    todos = sorted(set(list(book_rows.keys())) | set(k for k, v in inv_rows.items() if v > 0))

    errores = []
    for sym in todos:
        book = book_rows.get(sym)
        inv_pos = inv_rows.get(sym, 0.0)
        book_stock = book["stock"] if book else 0.0

        diff = book_stock - inv_pos
        if abs(diff) > TOLERANCE:
            errores.append(
                {
                    "simbolo": sym,
                    "id": book["id"] if book else None,
                    "fechahora": book["fechahora"] if book else None,
                    "sec": book["sec"] if book else None,
                    "book_stock": book_stock,
                    "inv_pos": inv_pos,
                    "diff": diff,
                }
            )

    print("=" * 100)
    print(f"  MONITOR BOOKTRADING — cuenta {account}  ({len(book_rows)} símbolos en booktrading)")
    print("=" * 100)

    if not errores:
        print(f"\n  OK — booktrading.stock coincide con inversion.position en todos los símbolos.\n")
        return

    print(f"\n  ALERTAS: {len(errores)} símbolos con stock desincronizado\n")
    print(
        f"  {'Symbol':<8} {'ID':>8} {'Última op':>20} {'sec':>4} {'book.stock':>12} {'inv.position':>12} {'Diff':>10}"
    )
    print(f"  {'-'*8} {'-'*8} {'-'*20} {'-'*4} {'-'*12} {'-'*12} {'-'*10}")

    for e in errores:
        id_str = str(e["id"]) if e["id"] else "---"
        fh_str = str(e["fechahora"]) if e["fechahora"] else "---"
        sec_str = str(e["sec"]) if e["sec"] is not None else "---"
        print(
            f"  {e['simbolo']:<8} {id_str:>8} {fh_str:>20} {sec_str:>4} "
            f"{e['book_stock']:>12.2f} {e['inv_pos']:>12.2f} {e['diff']:>+10.2f}"
        )

    if show_fix:
        print("\n" + "=" * 100)
        print("  SQLs CORRECTIVOS — actualiza booktrading.stock al valor de inversion.position")
        print("  (revisar antes de ejecutar — confirmar que inv.position es el valor IB correcto)")
        print("=" * 100)
        for e in errores:
            if e["id"]:
                print(
                    f"  UPDATE booktrading SET stock = {e['inv_pos']:.4f} "
                    f"WHERE id = {e['id']};  -- {e['simbolo']} diff {e['diff']:+.2f}"
                )

    print()


if __name__ == "__main__":
    main()
