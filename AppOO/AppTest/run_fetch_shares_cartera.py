"""
run_fetch_shares_cartera.py
Pobla sharesOutstanding y floatShares desde Yahoo para los símbolos en cartera.
Solo actualiza si el valor está vacío o es NULL.

Correr:  python AppTest/run_fetch_shares_cartera.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_python import yf, time
from Modulos_Mysql import MarketScreen

ACCOUNT = "U4214563"


def main():
    mkt = MarketScreen()
    conn = mkt._conectar(tabla="select.market")
    c = conn.cursor()
    c.execute(
        "SELECT symbol, sharesOutstanding, floatShares FROM market "
        "WHERE encartera='Y' AND account=%s ORDER BY symbol",
        (ACCOUNT,),
    )
    rows = c.fetchall()
    conn.close()

    print(f"Símbolos en cartera: {len(rows)}")
    print(f"{'Symbol':<8} {'sharesOutst':>14} {'floatShares':>14}  → acción")
    print("-" * 50)

    updated = 0
    for symbol, shares_out, float_sh in rows:
        if shares_out and float_sh:
            print(f"{symbol:<8} {'ok':>14} {'ok':>14}  → skip")
            continue
        try:
            info = yf.Ticker(symbol).info
            new_so = info.get("sharesOutstanding")
            new_fs = info.get("floatShares")
            print(f"{symbol:<8} {str(new_so or '-'):>14} {str(new_fs or '-'):>14}  → update")
            if new_so or new_fs:
                conn2 = mkt._conectar(tabla="update.market")
                c2 = conn2.cursor()
                c2.execute(
                    "UPDATE market SET sharesOutstanding=%s, floatShares=%s "
                    "WHERE symbol=%s AND account=%s",
                    (new_so, new_fs, symbol, ACCOUNT),
                )
                conn2.commit()
                conn2.close()
                updated += 1
        except Exception as e:
            print(f"{symbol:<8} ERROR: {e}")
        time.sleep(0.5)

    print(f"\nActualizados: {updated}/{len(rows)}")


if __name__ == "__main__":
    main()
