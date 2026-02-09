from Class_vehiculo import BinanceClient
from Class_customer import TickerInfo

ib = BinanceClient().spot
Tib = TickerInfo(account='B0000001', vehiculo='Crypto', colors={})

# print(ib.account_spot())

response = Tib.crypto_wallet_free(symbol='all')
print(f"Wallet Free: {response}")

# Ajuste del LTV de un préstamo flexible
# respose = ib.get_flexible_adjust_ltv(loanCoin="USDT", collateralCoin="BTC", adjustType="ADDITIONAL", amount=0.001)
