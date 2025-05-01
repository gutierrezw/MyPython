from API_vehiculos import SpotWebsocketAPIClient
from Modulos_python import (threading, logging, time, json, b64encode, b64decode, requests, hmac, hashlib, pprint,
                            load_pem_private_key, urlsafe_b64encode)

from cryptography.hazmat.primitives import serialization


class MyUserDataStreamClient(SpotWebsocketAPIClient):
    def __init__(self, mensaje_callback=None, stream_url=None):
        super().__init__(on_message=mensaje_callback or self.on_message,
                         on_close=self.on_close,
                         on_error=self.on_error)

        self.base_url = "https://api.binance.com"
        self.listen_key = None
        self.running = True
        self.renew_thread = None
        self.ws_thread = None
        self.api_key = "6jxGmHBk5oVT855IWuRqMNrLpWcEsotkH4W2Ng0xKcnFG3zkGytkomtagLff7TBS"

    def get_listen_key(self):
        BASE_URL = "https://api.binance.com"
        res = requests.post(f"{self.base_url}/api/v3/userDataStream", headers={"X-MBX-APIKEY": self.api_key})
        self.listen_key = res.json()["listenKey"]
        print(f"🔐 listenKey obtenido: {self.listen_key}")

    def start_keep_alive(self):
        def renew():
            while self.running:
                time.sleep(30 * 60)
                print("🔄 Renovando listenKey...")
                try:
                    requests.put(f"{self.base_url}/api/v3/userDataStream",
                                 headers={"X-MBX-APIKEY": self.api_key},
                                 params={"listenKey": self.listen_key})
                except Exception as e:
                    print(f"⚠️ Error al renovar listenKey: {e}")

        self.renew_thread = threading.Thread(target=renew, daemon=True)
        self.renew_thread.start()

    def subscribe_to_stream(self):
        def run_ws():
            try:
                print("🔌 Conectando al WebSocket privado...")
                self.user_data_stream(listenKey=self.listen_key)
            except Exception as e:
                print(f"⚠️ Error al conectar: {e}")
                self.reconnect()

    def signature_message(self, tipo='b64', REQUEST=None):

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
            PRIVATE_KEY_PATH = f"C:\\Users\\InversionesWildaga\\Documents\\MyPython\\keysSeguridad\\SP_Private_key.pem"

            # Load the private key.
            with open(PRIVATE_KEY_PATH, 'rb') as f:
                private_key = load_pem_private_key(data=f.read(),
                                                   password=None)
            s_params = {}

            # Sign request
            if tipo == 'b64':
                s_params = ed25519(self.api_key, private_key, p_params=REQUEST)
                return s_params

        except EncodingWarning as error:
            print("signature_message(): {}".format(error))

    def my_traders(self, assets=None):
        # 24 horas en milisegundos
        one_day_ms = 24 * 60 * 60 * 1000

        ini_time = int(time.time() * 1000)
        l_timestamp = [ini_time - i * one_day_ms for i in range(7)]
        l_timestamp.reverse()

        for i, start_time in enumerate(l_timestamp, 1):
            end_time = start_time + one_day_ms

            for symbol in assets:
                order = {
                    "symbol": symbol.upper(),
                    "startTime": start_time,
                    "endTime": end_time,
                    "limit": 10
                }

                params = self.signature_message(tipo='b64', REQUEST=order)

                auth_order = {
                    "id": "allOrders_5494febb",
                    "method": "allOrders",
                    "params": params
                }
                self.send(auth_order)

    def start(self):
        # self.get_listen_key()
        # self.start_keep_alive()
        # self.subscribe_to_stream()
        pass

    def stop(self):
        self.running = False
        print("🛑 Conexión detenida")


        self.ws_thread = threading.Thread(target=run_ws, daemon=True)
        self.ws_thread.start()

    def reconnect(self):
        print("♻️ Intentando reconectar...")
        self.stop()
        time.sleep(5)
        self.__init__()
        self.start()

    def on_close(self, code, reason):
        print(f"❌ WebSocket cerrado: {code}, motivo: {reason}")
        self.reconnect()

    def on_error(self, ws, error):
        print(f"⚠️ Error en WebSocket: {error}")
        self.reconnect()

 # asegura cerrar el thread
    def close_thread(self, sleep=1):
        if self.thread and self.thread.is_alive():
            self.thread.join()


# trata mensaje de precios
def message_handler_wss(ws, message):

    # Convertir string a JSON (diccionario)
    data = json.loads(message)

    if data["id"] != "allOrders_5494febb":
        print(data)

    # traders recientes en 24 horas
    elif data["id"] == "allOrders_5494febb":

        # request = OK
        if data['status'] == 200:
            l_orders = data['result']
            if l_orders:
                fields = ['symbol', 'price', 'orderId', 'origQty', 'status', 'timeInForce', 'type', 'side',
                          'stopPrice', 'updateTime']

                for items in l_orders:
                    order = {k: items[k] for k in fields if k in items}
                    print(order)
                    print('<>' * 40)


# 🔧 Uso
if __name__ == "__main__":

    try:
        wsc = MyUserDataStreamClient(stream_url="wss://ws-api.binance.com:443/ws-api/v3",
                                    mensaje_callback=message_handler_wss)
        wsc.start()
        symbols = ["adausdt", "filusdt", "vetusdt", "zilusdt", "polusdt", "icpusdt", "vthousdt"]

        while True:
            wsc.my_traders(assets=symbols)
            time.sleep(1)

    except KeyboardInterrupt:
        wsc.stop()
