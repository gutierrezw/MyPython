"""
run_diag_abev_yfinance.py
Diagnostica el precio que yfinance devuelve para ABEV y sus ajustes de splits/dividendos.
Uso: python AppTest/run_diag_abev_yfinance.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import yfinance as yf
import pandas as pd

TICKET = "BP"
HASTA = "2026-05-06"

# f_desde reales según booktrading:
# sec=1  primera compra    : 2025-08-08
# sec=13 primera activa(Y) : 2026-02-23
DESDE_TESTS = [
    "2026-03-10",  # ← f_desde real para BP (última transacción)
    "2026-03-01",  # un poco antes
    "2026-01-01",  # control 5 meses
    "2025-01-01",  # control 1 año
]


def _raw_download(desde):
    """Reproduce exactamente lo que hace get_yfinance vehiculo=Dividends."""
    df = yf.download(TICKET, start=desde, end=HASTA, auto_adjust=True, progress=False)
    print(f"  columns type  : {type(df.columns).__name__}")
    print(f"  columns.nlevels: {df.columns.nlevels}")
    print(f"  columns raw   : {df.columns.tolist()[:6]}")
    df.columns = df.columns.get_level_values(0)
    print(f"  columns post-L0: {df.columns.tolist()}")
    df = df.loc[:, ~df.columns.duplicated()]
    print(f"  columns post-dedup: {df.columns.tolist()}")
    return df


def main():
    print(f"\n{'='*60}")
    print(f"Diagnóstico yfinance {TICKET} — reproducción exacta de detalle_book")
    print(f"{'='*60}\n")

    for desde in DESDE_TESTS:
        print(f"\n{'─'*60}")
        print(f"start = {desde}  →  end = {HASTA}")
        print(f"{'─'*60}")
        try:
            df = _raw_download(desde)
            if df.empty:
                print("  DataFrame VACÍO")
                continue
            # últimos 5 días — los mismos que aparecen en el CSV corrupto
            cols = [c for c in ["Open", "Close", "High", "Low", "Volume"] if c in df.columns]
            print(df[cols].tail(5).to_string())
            if "Close" in df.columns:
                may1_idx = [i for i in df.index.strftime("%Y-%m-%d") if i == "2026-05-01"]
                if may1_idx:
                    print(f"\n  Close 01-may-2026 : {df.loc['2026-05-01', 'Close']}")
                else:
                    print("\n  01-may-2026 no está en el índice")
            else:
                print("\n  ⚠  columna 'Close' NO existe en el DataFrame")
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
