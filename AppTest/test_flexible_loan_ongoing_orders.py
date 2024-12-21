import responses
import requests
# from binance.spot import Spot as Client
from util import random_str
from urllib.parse import urlencode
from util import mock_http_response
import logging
from Spot_binance import *


api_key = 'FCd80qqWltu90UgrhPo4MiXCwC19sL9Aq8OTOriDdyTk6Ecok9HA9cyDprkpEeUF'
api_secret = 'hwldFS13pBVayOXknxcnlYjdTWpjrFyJ4MgscvDGk2yEEOPfIikS2O8eLERuMzqc'

config_logging(logging, logging.DEBUG)
logger = logging.getLogger(__name__)

client = Spot(api_key, api_secret)

try:
    response = client.loan_ongoing_orders(loanCoin="USDT", collateralCoin="ADA",
                                               current=1, limit=5, recvWindow=5000)

    logger.info(response)
except ClientError as error:
    logger.error(
        "Found error. status: {}, error code: {}, error message: {}".format(
            error.status_code, error.error_code, error.error_message
        )
    )


print(response)
