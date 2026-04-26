import websocket
import json
import threading
import time


class BinanceWebSocket:
    def __init__(self, cryptos):
        self.cryptos = cryptos
        self.ws = None
        self.cn = 0
        self.lock = threading.Lock()

    def on_message(self, ws, message):
        data = json.loads(message)
        if 'e' in data:
            self.cn += 1
            event_type = data['e']
            if event_type == '24hrMiniTicker':
                self.handle_ticker(data)

    @staticmethod
    def on_error(self, ws, error):
        print(f"BinanceWebSocket.on_error():: {error}")

    @staticmethod
    def on_close(self, ws):
        print("BinanceWebSocket.on_close()")

    def on_open(self, ws):
        print("Connection opened")
        self.subscribe_to_cryptos()

    def handle_ticker(self, data):
        """
        {
            "e": "24hrMiniTicker",      // Event type
            "E": 1672515782136,         // Event time
            "s": "BNBBTC",              // Symbol
            "c": "0.0025",              // Close price
            "o": "0.0010",              // Open price
        }
        """

        datos = f"Ticker: {data['s']} - Price: {data['c']} - Open: {data['o']}"
        print(datos, '--', self.cn)

    def subscribe_to_cryptos(self):
        with self.lock:
            params = [f"{crypto.lower()}@miniTicker" for crypto in self.cryptos]
            self.ws.send(json.dumps({
                "method": "SUBSCRIBE",
                "params": params,
                "id": 1
            }))
            print("Subscription message sent for cryptos:", self.cryptos)

    def update_cryptos(self, new_cryptos):
        with self.lock:
            unsubscribe_params = [f"{crypto.lower()}@miniTicker" for crypto in self.cryptos]
            self.ws.send(json.dumps({
                "method": "UNSUBSCRIBE",
                "params": unsubscribe_params,
                "id": 2
            }))

            print("Unsubscribed from cryptos:", self.cryptos)
            self.cryptos = new_cryptos
            time.sleep(5)
            self.subscribe_to_cryptos()

    def run(self):
        try:
            websocket.enableTrace(False)
            self.ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws",
                                             on_open=self.on_open,
                                             on_message=self.on_message,
                                             on_error=self.on_error,
                                             on_close=self.on_close)
            self.ws.run_forever()
        except Exception as e:
            print(f"Exception occurred: {e}")
            time.sleep(5)  # Espera antes de intentar reconectar


if __name__ == "__main__":
    initial_cryptos = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    binance_ws = BinanceWebSocket(initial_cryptos)

    # Run WebSocket in a separate thread
    ws_thread = threading.Thread(target=binance_ws.run)
    ws_thread.start()

    # Simulate updating the list of cryptos after some time

    #time.sleep(10)
    #new_cryptos = ['ADAUSDT', 'XRPUSDT', 'SOLUSDT']
    #binance_ws.update_cryptos(new_cryptos)
