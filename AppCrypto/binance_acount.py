import logging
import sys
import os
from datetime import *
from decimal import Decimal
import pprint
from binance.lib.utils import config_logging

# Agregar el directorio AppOO al path para importar API_vehiculos
appoo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "AppOO")
if appoo_path not in sys.path:
    sys.path.insert(0, appoo_path)

from API_vehiculos import BB


BI = BB().spot
config_logging(logging, logging.DEBUG)


def snapshot():
    response = BI.account_snapshot(type="SPOT", limit=50, recvWindow=5000)
    i = len(response["snapshotVos"]) - 1
    for keys in response["snapshotVos"][i]["data"]["balances"]:
        if float(keys["free"]) > 10:
            print(keys)


def account():
    response = BI.account()
    for keys in response["balances"]:
        if float(keys["free"]) > 10:
            print(keys)


def detalle():
    resposne = BI.asset_detail()
    for keys in resposne:
        if keys in ("ADA", "VET", "FIL", "ICP"):
            print(keys)


# snapshot()
print("=" * 20)
# account()
detalle()
