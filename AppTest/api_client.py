from pprint import pprint
from Class_Ibrks import IBClient
import requests
import json
import urllib3
# from API_vehiculos import *

# Create a new session of the IB Web API.
ib_client = IBClient(
    username="guti2004",
    account="U4214563",
    is_server_running=True
)


def orderconfirm(replyId=None):
    base_url = "https://localhost:5000/v1/api/"
    endpoint = "iserver/reply/"
    reply_url = "".join([base_url, endpoint, replyId])
    json_body = {
        "confirmed": True
    }
    order_req = requests.post(url=reply_url, verify=False, json=json_body)
    order_json = json.dumps(order_req.json(), indent=2)
    print(order_req.status_code)
    print(order_json)


def orderRequest(account_id=None, order=None):
    base_url = "https://localhost:5000/v1/api/"
    endpoint = "iserver/account/{}/orders".format(account_id)
    json_body = order

    order_req = requests.post(url=base_url + endpoint, verify=False, json=json_body)
    order_json = json.dumps(order_req.json(), indent=2)
    print(base_url + endpoint)
    print(json_body)
    print(order_req.status_code)
    print(order_json)


def deleteorder(account_id: str, customer_order_id: str, conid: str):
        """ Provicional Deletes the order specified by the customer order ID.

          NAME: account_id
          DESC: The account ID you wish to place an order for.
          TYPE: String

          NAME: customer_order_id
          DESC: The customer order ID for the order you wish to DELETE.
          TYPE: String
          """

        # define request components
        base_url = 'https://localhost:5000/v1/api/'
        endpoint = 'iserver/account/{}/order/{}/{}'.format(account_id, customer_order_id, conid)
        req_type = 'DELETE'
        reply_url = "".join([base_url, endpoint])
        order_req = requests.post(url=reply_url, verify=False)
        content = json.dumps(order_req.json(), indent=2)

        return content

# create a new session
ib_client.create_session()


# pprint('place_order_scenario()')

orden = {"orders": [{"conid": 125815462,
                      "orderType": "LMT",
                      "price": 29,
                      "side": "BUY",
                      "tif": "GTC",
                      "quantity": 5, }
                     ]
            }

# pprint('place_order()')
# response = ib_client.place_order(account_id='U4214563', order=orden)
# pprint(response)
# pprint('--------------------------------------')

# print('orderRequest')
# order = ib_client.get_live_orders()
# pprint(order)
# pprint('--------------------------------------')

# pprint('delete_order()')
# response = ib_client.delete_order(account_id='U4214563', customer_order_id=str(517114816))
# response = deleteorder(account_id='U4214563', customer_order_id='1054791570', conid='9969533')
# pprint(response)
# orderRequest(account_id='U4214563', order=orden)
# orderconfirm(replyId='be28f00d-bb0a-4d57-8847-25e145939d2e')
# pprint('--------------------------------------')

# pprint('place_order_scenario()')
# response = ib_client.place_order_scenario(account_id='U4214563', order=orden)
# response = ib_client.place_order(account_id='U4214563', order=orden)
# pprint(response)
# orderRequest(account_id='U4214563', order=orden)
# orderconfirm(replyId='be28f00d-bb0a-4d57-8847-25e145939d2e')
# pprint('--------------------------------------')

# pprint('place_order_scenario()')
# response = ib_client.place_order(account_id='U4214563', order=orden)
# pprint(response)
# pprint('--------------------------------------')


# pprint('portfolio_account_ledger()')
# ledger = ib_client.portfolio_account_ledger(account_id='U4214563')
# pprint(ledger)
# pprint('--------------------------------------')

# pprint('portfolio_account_positions()')
# positions = ib_client.portfolio_account_positions(account_id='U4214563', page_id=0)
# print('len(positions)', len(positions))
# pprint(positions)
# pprint('--------------------------------------')

# grab the account data.
# pprint('portfolio_accounts()')
# account_data = ib_client.portfolio_accounts()
# pprint(account_data)
# pprint('--------------------------------------')

# pprint('Trade')
# account_pnl = ib_client.trades(account_id='U4214563', days=10)
# pprint(account_pnl)
# pprint('--------------------------------------')

# account_pnl = ib_client.trades(account_id='U4214563', days=10)
# pprint(account_pnl)
# pprint('--------------------------------------')
# response = ib_client.delete_order(account_id='U4214563,{symbol}')


# Grab current quotes
#pprint('market_data()')
# quote_fields = [55, 7296, 7295, 86, 70, 71, 84, 31]
#quote_fields = [7743, 7331, 7698, 7699]

#aapl_current_prices = ib_client.market_data(
#    conids=['4730124'],
#    since='0',
#    fields=quote_fields
#)
#pprint(aapl_current_prices)
#pprint('')


# Grab current quotes
#pprint('fundamentals_summary()')
##fundamental_summ = ib_client._fundamentals_summary(conid='265598')
#pprint(fundamental_summ)
#pprint('')

# verification localhost
is_localhost()
