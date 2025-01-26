import pathlib
from pprint import pprint
from Class_Ibrks import IBClient
#from configparser import ConfigParser


# Create a new session of the IB Web API.
ib_client = IBClient(
    username="guti2004",
    account="U4214563",
    is_server_running=True)

# create a new session
# ib_client.create_session()
# print('autenticado -- en session')
# print(ib_client.is_authenticated(False))

# grab the account data.
# pprint('account_data')
# account_data = ib_client.portfolio_accounts()
# pprint(account_data)

# # grab account portfolios
# pprint('account_positions')
# account_positions = ib_client.portfolio_account_positions(account_id="U4214563", page_id=0)
# pprint(account_positions)


# Grab current quotes
pprint('current_prices')
symbol = ib_client.symbol_search('HASI')[0]
print(symbol['conid'], symbol['description'])
quote_fields = [6070, 7282, 7284, 7290, 7293, 7294, 7655, 7674, 7675, 7676, 7677,
                7678, 7679, 7724, 7681, 7694, 7700, 7702, 7703, 7920]
current_prices = ib_client.market_data(conids=symbol['conid'], since='0', fields=quote_fields)
pprint(current_prices[0])

# pprint('datos1')
# datos = ib_client._data_analyst_forecast('13246')
# pprint('datos')

# datos = ib_client._fundamentals_summary(conid='13246')
# datos = ib_client._fundamentals_summary(conid=['13246'])
# pprint(datos)


#pprint("portfolio_account_ledger")
#datos = ib_client.portfolio_account_ledger(account_id="U4214563")
#pprint(datos)