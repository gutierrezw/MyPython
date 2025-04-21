from datetime import *
from decimal import Decimal
import pprint
from binance.lib.utils import config_logging
from API_vehiculos import BB


ib = BB().spot

response = ib.w_get_open_orders()
print(response)