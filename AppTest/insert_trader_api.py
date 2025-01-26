import csv
from operator import itemgetter
from globales import *
from rutinas import *
from bd_conect import *
from Class_Ibrks import IBClient

# Create a new session of the IB Web API.
ib_client = IBClient(
    username="guti2004",
    account="4214563",
    is_server_running=True
)
ix = ['Trades', 'Header', 'DataDiscriminator', 'Asset Category', 'Currency', 'Account', 'Symbol',
      'Date/Time', 'Exchange', 'Quantity', 'T. Price', 'C. Price', 'Proceeds', 'Comm/Fee', 'Basis',
      'Realized P/L', 'MTM P/L', 'Code']
datos = list()
trades = trades_api(account_id='U4214563')
print(trades)

for keys in trades:
    values = dict()
    values.update({'simbolo': keys['symbol']})
    values.update({'categoria': 'Stock'})
    values.update({'divisa': 'USD'})
    values.update({'cuenta': keys['accountCode']})
    timestamp = int(keys['trade_time_r'] / 1000)
    values.update({'fechahora': datetime.fromtimestamp(timestamp)})
    values.update({'idtrans': keys['execution_id']})

    values.update({'preciotrans': Decimal(keys['price'])})
    values.update({'preciocierre': Decimal(keys['price'])})
    values.update({'tarifacomision': Decimal(keys['commission'])})
    values.update({'producto': Decimal(keys['net_amount'])})

    if keys['side'] == 'B':
        values.update({'cantidad':  Decimal(keys['size'])})
        values.update({'gprealizadas': 0.00})
        values.update({'mtmgp': 0.00})
        values.update({'codigo': 'O'})

    if keys['side'] == 'S':
        values.update({'cantidad':  Decimal(keys['size'])})
        values.update({'gprealizadas': 0.00})
        values.update({'mtmgp': 0.00})
        values.update({'codigo': 'C'})

    datos.append(values)

datos_ord = sorted(datos, key=itemgetter('cuenta', 'simbolo', 'fechahora', ))
print(len(datos_ord))
for key in datos_ord:

    simbolo = key['simbolo']
    values = key.pop('simbolo')
    print(simbolo, key['fechahora'], key)
    insert_booktrading(values=key, symbol=simbolo)

