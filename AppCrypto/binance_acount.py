import logging
from datetime import *
from decimal import Decimal
import pprint
from binance.lib.utils import config_logging
from API_vehiculos import BB


BI = BB().spot
config_logging(logging, logging.DEBUG)


def snapshot():
    response = BI.account_snapshot(type='SPOT', limit=50, recvWindow=5000)
    i = len(response['snapshotVos']) - 1
    for keys in response['snapshotVos'][i]['data']['balances']:
        if float(keys['free']) > 10:
            print(keys)


def account():
    response = BI.account()
    for keys in response['balances']:
        if float(keys['free']) > 10:
            print(keys)


snapshot()
print("=" * 20)
account()
