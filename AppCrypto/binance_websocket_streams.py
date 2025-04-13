from API_vehiculos import BB, SpotWebsocketAPIClient, SpotWebsocketStreamClient, config_logging
from Modulos_python import threading, logging, time, pprint, json, datetime

class WebsocketBinanceStreams(SpotWebsocketStreamClient):
    def __init__(self, assets=None, mensaje_callback=None, stream_url=None):
        super().__init__(on_message=mensaje_callback, stream_url=stream_url)
        self.symbols = [f"{activo.lower()}@ticker" for activo in assets] or []

        self.stream_ws_price = None
        self.stop_threads = True
        self.thread = None

    def message_handler(self, message):
        # Convertir string a JSON (diccionario)
        data = json.loads(message)
        if 'e' in data.keys():
            if data['e'] == '24hrTicker':
                fields = [{'E': 'EvenTime'},  {'s': 'symbol'},     {'c': 'lastPrice'},
                          {'o': 'openPrice'}, {'p': 'priceChang'}, {'b': 'bidPrice'},
                          {'a': 'ask price'}, {'h': 'High price'}, {'l': 'Low price'}
                ]

                filtrados = {list(f.keys())[0]: data.get(list(f.keys())[0]) for f in fields}
                self.stream_ws_price = {f[k]: v for f in fields for k, v in filtrados.items() if k in f}
                print(self.stream_ws_price)

    def websocket_loop(self, limit=None):

        self.thread = threading.Thread(target=self.subscribe,
                                       name=f"wsc.subscribe(symbol={len(self.symbols)})",
                                       args=(self.symbols,))
        self.thread.start()

        print(f" WebSocket activo: {self.thread.name}, time:{datetime.now()}")
        time.sleep(limit)

    def run(self):
        try:
            while self.stop_threads:
                self.websocket_loop(limit=43200)
                self.stop()
                self.thread.join()

                print(f" WebSocket closet: {self.thread.name}")
                time.sleep(1)

        except EncodingWarning or KeyboardInterrupt:
            self.stop_threads = False
            self.stop()
            self.thread.join()
            print("WebSockets cerrados.")

if __name__ == "__main__":

    lista = ["adausdt", "filusdt", "vetusdt", "zilusdt", "polusdt", "ipcusdt", "vthousdt"]
    def on_mess(_, message):
        print(message)

    app = WebsocketBinanceStreams(stream_url='wss://stream.binance.com:9443',
                                  assets=lista,
                                  mensaje_callback=on_mess)
    app.run()



