import logging
from datetime import *
from decimal import Decimal
import pprint
from binance.spot import Spot as Client
from binance.lib.utils import config_logging
from bd_conect import select_booktrading, insert_booktrading

api_key = "FCd80qqWltu90UgrhPo4MiXCwC19sL9Aq8OTOriDdyTk6Ecok9HA9cyDprkpEeUF"
api_secret = "hwldFS13pBVayOXknxcnlYjdTWpjrFyJ4MgscvDGk2yEEOPfIikS2O8eLERuMzqc"

config_logging(logging, logging.DEBUG)

spot_client = Client(api_key, api_secret)
ifecha = datetime.strptime('2024-01-01', '%Y-%m-%d')
efecha = ifecha
ltrade = list()

xlist = ("ADAUSDT", "FILUSDT", "DOTUSDT", "VETUSDT", "MATICUSDT", "ZILUSDT", "BNBUSDT", "VTHOUSDT")

for ticket in xlist:
    utrading = select_booktrading(accion='last', symbol=ticket)
    if utrading:
        ifecha = utrading[0]['fechahora']
        #ifecha += timedelta(days=-1)
    else:
        ifecha = datetime.now()
        ifecha += timedelta(days=-15)

    efecha = ifecha
    ltrade = list()

    print('asset=', ticket, 'inicial=', efecha)
    hoy = datetime.now()
    while efecha <= hoy:
        efecha += timedelta(days=1)
        sfecha = efecha
        sfecha += timedelta(days=-1)
        print('asset=', ticket, sfecha, efecha)

        stime = int(sfecha.timestamp() * 1000)
        etime = int(efecha.timestamp() * 1000)
        field = {'symbol': 'simbolo', 'id': 'idtrans', 'qty': 'cantidad', 'price': 'preciotrans',
                 'quoteQty': 'producto', 'commission': 'tarifacomision', 'time': 'fechahora'}

        w_trade = spot_client.my_trades(ticket, limit=10, startTime=stime, endTime=etime)

        if w_trade:
            print(w_trade)
            for i in range(len(w_trade)):
                values = dict()

                values.update({'categoria': 'Crypto'})
                values.update({'divisa': 'USD'})
                values.update({'cuenta': 'B0000001'})
                for keys, vals in w_trade[i].items():
                    if keys in field.keys():
                        if keys == 'qty':
                            qty = Decimal(vals)
                            values.update({field[keys]: qty if w_trade[i]['isBuyer'] else - qty})

                        if keys == 'quoteQty':
                            quoteqty = Decimal(vals)
                            values.update({field[keys]: quoteqty if w_trade[i]['isBuyer'] else - quoteqty})

                        if keys == 'id':
                            values.update({field[keys]: str(vals)})

                        if keys == 'price':
                            price = Decimal(vals)
                            values.update({field[keys]: price})
                            values.update({'preciocierre': price})

                        if keys == 'commission':
                            commission = Decimal(vals)
                            values.update({'tarifacomision': commission})

                        if keys == 'time':
                            values.update({'fechahora': datetime.fromtimestamp(vals / 1000)})

                insert_booktrading(values, symbol=ticket)
                print('insert=', len(w_trade), values)

    # print(ltrade)
