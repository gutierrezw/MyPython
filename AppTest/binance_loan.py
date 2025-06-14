import logging
from datetime import *
from decimal import Decimal
import pprint
from binance.lib.utils import config_logging
from API_vehiculos import BB


BI = BB().spot


print('loan_borrow_history', '-' *20)
response = BI.loan_borrow_history(loanCoin='USDT', collateralCoin='ADA')

print(response)

