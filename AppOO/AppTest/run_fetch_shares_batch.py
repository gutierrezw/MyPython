"""
run_fetch_shares_batch.py
Pobla floatShares y sharesOutstanding para todos los símbolos sin ellos.
Usa yfinance directamente (maneja auth propia, no depende de crumb Yahoo).
Solo actualiza si el campo está vacío o NULL.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_python import time, yf, ThreadPoolExecutor, threading
from Modulos_Mysql import MarketScreen

ACCOUNT = "U4214563"
MAX_WORKERS = 5
SLEEP_BETWEEN = 0.3


def _fetch_shares(sym):
    """Retorna (symbol, floatShares, sharesOutstanding) o None en error."""
    try:
        info = yf.Ticker(sym).fast_info
        fs = getattr(info, "float_shares", None)
        so = getattr(info, "shares", None)
        if not fs and not so:
            return sym, None, None
        return sym, fs, so
    except Exception as e:
        return sym, None, None


def main():
    mkt = MarketScreen()
    conn = mkt._conectar(tabla="select.market")
    c = conn.cursor()
    c.execute(
        "SELECT symbol FROM market "
        "WHERE account=%s AND (floatShares IS NULL OR sharesOutstanding IS NULL) "
        "AND categoriaActivo NOT IN ('X') "
        "ORDER BY symbol",
        (ACCOUNT,),
    )
    simbolos = [r[0] for r in c.fetchall()]
    conn.close()

    total = len(simbolos)
    print(f"Símbolos sin floatShares/sharesOutstanding: {total}")

    updated = 0
    skipped = 0
    errores = 0
    lock = threading.Lock()

    def process(sym):
        nonlocal updated, skipped, errores
        time.sleep(SLEEP_BETWEEN)
        sym_r, fs, so = _fetch_shares(sym)
        if not fs and not so:
            with lock:
                skipped += 1
            return
        try:
            conn2 = mkt._conectar(tabla="update.market")
            c2 = conn2.cursor()
            c2.execute(
                "UPDATE market SET floatShares=%s, sharesOutstanding=%s " "WHERE symbol=%s AND account=%s",
                (fs, so, sym_r, ACCOUNT),
            )
            conn2.commit()
            conn2.close()
            with lock:
                updated += 1
                done = updated + skipped + errores
                if done % 50 == 0:
                    print(f"  Progreso: {done}/{total} — actualizados={updated} sin_datos={skipped} err={errores}")
        except Exception as e:
            with lock:
                errores += 1
            print(f"  DB error {sym_r}: {e}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(process, simbolos)

    print(f"\nResumen — actualizados: {updated}  sin datos: {skipped}  errores: {errores}")
    print("Próximo paso: python AppTest/run_sync_13f_scores.py")


if __name__ == "__main__":
    main()
