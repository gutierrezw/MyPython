"""
Reproceso: Inserta trades de BotCrypto en booktrading desde 07-feb-2025.
Usa el mismo formato que trader_binance() de DashMainV9_ia.py.
"""

from Class_ApiBinnace import BinanceClient
from Modulos_Mysql import RepositorioOportunidadesBuySell as RepositorioOportunidades
from datetime import datetime, timedelta
import time

# Configuración
ACCOUNT = "B0000002"
CATEGORIA = "BotCrypto"
DIVISA = "USD"
FECHA_DESDE = datetime(2026, 2, 7)
SYMBOLS = ["DOGEUSDT", "ADAUSDT", "XRPUSDT", "TRXUSDT", "FILUSDT", "VETUSDT", "ICPUSDT", "DOTUSDT", "POLUSDT"]

# Clientes
client = BinanceClient(vehiculo="BotCrypto", env="PRODUCTION")
repositorio = RepositorioOportunidades()

print("=" * 60)
print(f"REPROCESO BOOKTRADING: {ACCOUNT} desde {FECHA_DESDE.strftime('%d-%b-%Y')}")
print(f"Símbolos: {', '.join(SYMBOLS)}")
print("=" * 60)

total_insertados = 0
total_existentes = 0

for symbol in SYMBOLS:
    print(f"\n--- {symbol} ---")
    efecha = FECHA_DESDE
    hoy = datetime.now()
    sym_insertados = 0
    sym_existentes = 0

    while efecha <= hoy:
        sfecha = efecha
        efecha += timedelta(days=1)

        stime = int(sfecha.timestamp() * 1000)
        etime = int(efecha.timestamp() * 1000)

        if etime <= stime:
            continue

        trades = client.spot.get_my_trades(symbol, limit=50, startTime=stime, endTime=etime)

        if not trades:
            continue

        for trade in trades:
            try:
                qty = float(trade.get("qty", 0.0))
                qty = qty if trade["isBuyer"] else -1 * qty
                quoteqty = float(trade.get("quoteQty", 0.0))
                price = float(trade.get("price", 0.0))
                commission = float(trade.get("commission", 0.0)) * price
                fechahora = datetime.fromtimestamp(trade.get("time", 0) / 1000)

                registro = {
                    "categoria": CATEGORIA,
                    "divisa": DIVISA,
                    "cuenta": ACCOUNT,
                    "cantidad": qty,
                    "producto": quoteqty,
                    "idtrans": str(trade.get("id")),
                    "preciotrans": price,
                    "preciocierre": price,
                    "tarifacomision": commission,
                    "mtmgp": 0.00,
                    "fechahora": fechahora,
                }

                # Validar si ya existe
                found = repositorio.get_hash_booktrading(
                    accion="valida",
                    values=registro,
                    symbol=symbol,
                )

                if not found:
                    repositorio.insert_bottraderBook(values=registro, symbol=symbol, object="bottrader")
                    side = "BUY" if trade["isBuyer"] else "SELL"
                    print(
                        f"  + {fechahora.strftime('%d-%b %H:%M')} | {side:4} | qty={abs(qty):>10.4f} | price={price:.6f} | ${quoteqty:.2f}"
                    )
                    sym_insertados += 1
                else:
                    sym_existentes += 1

            except Exception as e:
                print(f"  ERROR: {e} | trade={trade}")

        # Espera para no saturar la API
        time.sleep(0.8)

    print(f"  {symbol}: {sym_insertados} insertados, {sym_existentes} ya existían")
    total_insertados += sym_insertados
    total_existentes += sym_existentes

print("\n" + "=" * 60)
print(f"TOTAL: {total_insertados} insertados | {total_existentes} ya existían")
print("=" * 60)
