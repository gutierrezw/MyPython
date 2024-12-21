import time
from pprint import *
from decimal import *
import logging
import requests
from _datetime import datetime, date, timedelta
from binance.spot import Spot
from binance.error import *
from binance.lib.utils import check_required_parameters
from binance.lib.utils import config_logging
from binance.error import ClientError
import globales
from bd_conect import *

xapi_key = 'FCd80qqWltu90UgrhPo4MiXCwC19sL9Aq8OTOriDdyTk6Ecok9HA9cyDprkpEeUF'
xapi_secret = 'hwldFS13pBVayOXknxcnlYjdTWpjrFyJ4MgscvDGk2yEEOPfIikS2O8eLERuMzqc'

ticket = ['ADA', 'VET', 'MAT', 'DOT']


def main(ticket):
    try:
        client = Spot(api_key=xapi_key, api_secret=xapi_secret)
        data = list()

        #print(client.get_account())
        res = client.account_snapshot(type='SPOT', limit=1, recvWindow=5000)
        x = res['snapshotVos']
        print(len(x), x[6])

        x = enumerate(res['snapshotVos'])
        for key in res['snapshotVos']:
            print('i==', datetime.fromtimestamp(key['updateTime'] / 1000))

    except ClientError as error:
        print("[Error] :", error)



if __name__ == "__main__":
    main(ticket)
