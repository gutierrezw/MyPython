from API_vehiculos import websocket, time
from Class_Ibrks import *


def on_message(ws, message):
    print(message)


def on_error(ws, error):
    print(error)


def on_close(ws):
    print("## CLOSED! ##")


def on_open(ws):
    print("Opened Connection")
    time.sleep(3)

    campos = {'last': '31',
              'symbol': '55',
              'vmarket': '73',
              'avgcost': '74',
              'unrealizedpnl': '75',
              'dgyp': '78',
              'realizedpml': '79',
              'change': '82',
              'empresa': '7051',
              'dividend': '7296',
              'dividendyield': '7287',
              'exdatedividendt': '7288',
              'costobase': '7292',
              'open': '7295',
              'close': '7296'}
    campos = {"last": "31",
              "symbol": "55",
              'stock': '76',
              "conid": '6008'}
    fields = {"fields": list(campos.values())}
    conids = ["4730124", "166090175", "2585769"]

    for conid in conids:
        print('smd+'+conid+'+{}'.format(fields))
        # ws.send('smd+'+conid+'+{}'.format(fields))
        ws.send('smd+'+conid+'+{"fields": ["31", "55", "7051"]}')



if __name__ == "__main__":
    # ib = IB(username=None, account=None)
    ib = IBClient(username='guti2004', account='U4214563')
    print(ib.portfolio_account_ledger(account_id=ib.account))

    ws = websocket.WebSocketApp(
        url="wss://localhost:5000/v1/api/ws",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    # ws.run_forever()