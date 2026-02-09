from Class_vehiculo import BinanceClient
import time

client = BinanceClient(vehiculo="BotCrypto", env="PRODUCTION")

# 1. BALANCE REAL
print("=" * 50)
print("BALANCE REAL EN SUBCUENTA:")
print("=" * 50)
account = client.spot.account_spot()
for b in account["balances"]:
    free = float(b["free"])
    locked = float(b["locked"])
    if free > 0 or locked > 0:
        print(f"  {b['asset']}: free={free}, locked={locked}")

# 2. HISTORIAL DE TRADES (últimas 24h)
print("\n" + "=" * 50)
print("TRADES EJECUTADOS (últimas 24h):")
print("=" * 50)

now = int(time.time() * 1000)
yesterday = now - (24 * 60 * 60 * 1000)

for symbol in ["DOGEUSDT", "ADAUSDT"]:
    trades = client.spot.get_my_trades(symbol, limit=50, startTime=yesterday, endTime=now)
    if trades:
        print(f"\n{symbol}:")
        total_qty = 0
        total_cost = 0
        for t in trades:
            qty = float(t["qty"])
            price = float(t["price"])
            cost = float(t["quoteQty"])
            side = "BUY" if t["isBuyer"] else "SELL"
            print(f"  {side} | qty={qty:.2f} | price={price:.6f} | cost={cost:.4f} USDT")
            if t["isBuyer"]:
                total_qty += qty
                total_cost += cost
        print(f"  TOTAL COMPRADO: {total_qty:.2f} coins | {total_cost:.2f} USDT")
