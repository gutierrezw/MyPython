from API_vehiculos import BB, SpotWebsocketAPIClient, config_logging
from Modulos_python import (threading, logging, time, json, b64encode, b64decode, requests, hmac, hashlib, pprint,
                            load_pem_private_key, urlsafe_b64encode)

from cryptography.hazmat.primitives import serialization

class websocketApiBinance():
    def __init__(self):
        self.serverTime = 0
        self.wss = None

        self.run()

    # trata mensaje de precios
    def message_handler_wss(self, _, message):

        # Convertir string a JSON (diccionario)
        data = json.loads(message)

        if data["id"] == "ticker_24hr":
            items = data['result']
            fields = ['symbol', 'lastPrice', 'askPrice', 'bidPrice', 'openPrice', 'prevClosePrice']
            for rows in items:
                print({key: rows[key] for key in fields})

        elif data["id"] == "auth_request_5494febb":
            print(data)

        # traders recientes en 24 horas
        elif data["id"] == "my_trader_5494febb":
            print(data)

            # request = OK
            if data['status'] == 200:
                fields = ['symbol', 'price', 'orderId', 'origQty', 'status', 'timeInForce', 'type', 'side'
                          'stopPrice', 'updateTime']

                l_traders = data['result']
                for items in l_traders:
                    trader = {k: items[k] for k in fields if k in items}
                    print(trader)

        else:
            print('<>' * 40)
            print(data)

        self.serverTime = int(time.time() * 1000)

    @staticmethod
    def signature_message(tipo='b64', REQUEST=None):

        # Set up the request parameters  y auth_request
        def ed25519(a_key, p_key, p_params=None):

            # Sign the request
            p_params['timestamp'] = int(time.time() * 1000)
            p_params['apiKey'] = a_key

            payload = '&'.join([f'{param}={value}' for param, value in sorted(p_params.items())])
            signature = b64encode(p_key.sign(payload.encode('utf-8')))
            p_params['signature'] = signature.decode('utf-8')

            return p_params

        try:
            # -- WebSocket_v3_SP
            api_key = "6jxGmHBk5oVT855IWuRqMNrLpWcEsotkH4W2Ng0xKcnFG3zkGytkomtagLff7TBS"
            PRIVATE_KEY_PATH = f"C:\\Users\\InversionesWildaga\\Documents\\MyPython\\keysSeguridad\\SP_Private_key.pem"

            # Load the private key.
            with open(PRIVATE_KEY_PATH, 'rb') as f:
                private_key = load_pem_private_key(data=f.read(),
                                                   password=None)
            s_params = {}

            # Sign request
            if tipo == 'b64':
                s_params = ed25519(api_key, private_key, p_params=REQUEST)
                return s_params

        except EncodingWarning as error:
            print("signature_message(): {}".format(error))

    @staticmethod
    def ticker_24hr(assets=None):
        ticker = {
                    "id": "ticker_24hr",
                    "method": "ticker.24hr",
                    "params": {
                    "symbols": assets
                 }
        }
        return ticker

    # autenticación websocket
    def logon_wss(self):
        auth = {
            'apiKey': None,
            'timestamp': None
        }

        params = self.signature_message(REQUEST=auth)
        auth_request = {
            "id": "auth_request_5494febb",
            "method": "session.logon",
            "params": params
        }
        self.wss.send(auth_request)

    def my_traders(self, assets=None):
        end_time = int(time.time() * 1000)
        start_time = end_time - (24 * 60 * 60 * 1000)

        for symbol in assets:
            order = {
                      "symbol": symbol,
                      "startTime": start_time,
                      "endTime": end_time,
                      "limit": 10
            }

            params = self.signature_message(tipo='b64', REQUEST=order)

            auth_order = {
                            "id": "my_trader_5494febb",
                            "method": "myTrades",
                            "params": params
            }
            self.wss.send(auth_order)

    def open_OCO(self, assets=None):

        for symbol in assets:
            oco = {
            }

            params = self.signature_message(tipo='b64', REQUEST=oco)

            auth_oco = {
                "id": "my_open_oco_5494febb",
                "method": "openOrderLists.status",
                "params": params
            }
            self.wss.send(auth_oco)

    def run(self):
        try:

            assets=["ADAUSDT", "FILUSDT", "VETUSDT", "ZILUSDT", "POLUSDT", "ICPUSDT", "VTHOUSDT"]


            # Mantener la conexión abierta
            self.wss = SpotWebsocketAPIClient(stream_url="wss://ws-api.binance.com:443/ws-api/v3",
                                              on_message=self.message_handler_wss,
                                              time_unit='microsecond')


            # autenticación websocket
            # self.logon_wss()

            # precisos lista assets
            auth_ticker = self.ticker_24hr(assets=assets)
            # self.wss.send(auth_ticker)
            # self.wss.ticker_24hr(symbols=assets, type="FULL")

            # traders history
            self.my_traders(assets=assets)



            #while True:
            #    self.ws_price.ticker_24hr(symbols=assets)
            #    print('-- price ', "-" * 20)
            #    time.sleep(1)

                # for keys in assets:
                    #   self.ws_order.get_open_orders(symbol='ADAUSDT')

                # print('-- trades ', "-" * 20)
                # time.sleep(1)

        except KeyboardInterrupt:
            self.wss.stop()
            print("WebSockets cerrados.")


if __name__ == "__main__":
    app = websocketApiBinance()

    app.run()
