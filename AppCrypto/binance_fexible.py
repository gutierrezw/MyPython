import logging
from datetime import *
from decimal import Decimal
import pprint
from binance.lib.utils import config_logging
from API_vehiculos import BB


BI = BB().spot

# print('get_locked_rewards_history', '-' *20)
# response = BI.get_locked_rewards_history(asset='ADA', size=100, recvWindow=6000)
# print(response)




print('position en billetera earn flexible', '-' *20)
response = BI.w_get_flexible_product_position(current=1, size=100, recvWindow=5000)
for product in response['rows']:
    print(product)

# print('cryptos balance', '-' *20)# cryptos balance
# response = BI.account_spot()
# for product in response['balances']:
#     if float(product['free']) > 0 or float(product['locked']) > 0:
#        print(product)


# print('=' * 20)
# response = BI.get_flexible_redemption_record(size=100)
# for product in response['rows']:
#    print(product)


# print('=' * 20)
# response = BI.redeem_flexible_product(productId="VTHO001", amount=1000, recvWindow=5000)
# print(response)
