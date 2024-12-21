import time
from pprint import *
from decimal import *
import logging
import requests
from binance.spot import Spot
from binance.error import *
from binance.lib.utils import check_required_parameters
from binance.lib.utils import config_logging
from binance.error import ClientError
import globales
from bd_conect import *

xapi_key = 'FCd80qqWltu90UgrhPo4MiXCwC19sL9Aq8OTOriDdyTk6Ecok9HA9cyDprkpEeUF'
xapi_secret = 'hwldFS13pBVayOXknxcnlYjdTWpjrFyJ4MgscvDGk2yEEOPfIikS2O8eLERuMzqc'


def main(ticket):
    try:
        client = Spot(api_key=xapi_key, api_secret=xapi_secret)
        response = client.account_snapshot(type='SPOT', limit=1, recvWindow=5000)

        assets = dict()
        if response:
            for keys in response['snapshotVos'][0]['data']['balances']:
                if float(keys['free']) > 0 and not keys['asset'].startswith('LD'):
                    assets.update({keys['asset']: {'sopt': {'borrowed': 0, 'free': keys['free'], 'locked': 0,
                                                            'netAsset': 0, 'rewards': 0}}})

        response = client.get_flexible_product_position(current=1, size=100, window=5000)
        if response:
            for keys in response['rows']:
                if float(keys['collateralAmount']) != 0 or float(keys['totalAmount']) != 0:
                    free = float(keys['totalAmount'])
                    if keys['asset'] in list(assets.keys()):
                        free += float(assets[keys['asset']]['spot']['free'])

                assets.update({keys['asset']: {'earn': {'borrowed': keys['collateralAmount'],
                                                        'free': free, 'locked': 0,
                                                        'netAsset': keys['totalAmount'],
                                                        'rewards': keys['cumulativeTotalRewards']}}})

        print(assets)


    except ClientError as error:
        print("[Error] :", error)


if __name__ == "__main__":
    main('DOTUSDT')
