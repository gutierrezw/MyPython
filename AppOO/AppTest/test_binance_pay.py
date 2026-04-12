"""
Prueba de conexión a Binance Pay API.
Muestra las transacciones Pay del Q1 2026 sin escribir en BD.

Uso:
    python AppTest/test_binance_pay.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Class_ApiBinnace import BinanceClient

START_MS = 1735689600000  # 2026-01-01 00:00:00 UTC
END_MS = 1743465600000  # 2026-04-01 00:00:00 UTC


def main():
    client = BinanceClient(vehiculo="Crypto")

    print(f"Consultando Pay transactions 2026-01-01 → 2026-03-31 ...")
    try:
        txns = client.fetch_pay_transactions(START_MS, END_MS)
    except Exception as e:
        import requests as _req

        if isinstance(e, _req.HTTPError) and e.response is not None:
            print(f"HTTP {e.response.status_code}: {e.response.text}")
        else:
            print(f"ERROR: {e}")
        sys.exit(1)

    if not txns:
        print("Sin transacciones Pay en el período.")
        return

    print(f"\n{len(txns)} transacciones encontradas:\n")
    print(f"{'Fecha':<22} {'Tipo':<15} {'Monto':>10} {'Divisa':<6} {'Contraparte'}")
    print("-" * 75)
    for t in txns:
        ts = t.get("transactionTime", 0)
        from datetime import datetime, timezone

        fecha = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        tipo = t.get("orderType", "?")
        monto = t.get("amount", "?")
        divisa = t.get("currency", "?")
        recv = t.get("receiverInfo") or {}
        payer = t.get("payerInfo") or {}
        contraparte = recv.get("name") or recv.get("email") or payer.get("name") or "?"
        print(f"{fecha:<22} {tipo:<15} {float(monto):>10.4f} {divisa:<6} {contraparte}")


if __name__ == "__main__":
    main()
