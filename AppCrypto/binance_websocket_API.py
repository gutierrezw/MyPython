from API_vehiculos import BB, WebsocketBinanceApiClient
from Modulos_python import (threading, logging, time, json, b64encode, b64decode, requests, hmac, hashlib, pprint,
                            urlsafe_b64encode, serialization)


# trata mensaje de precios
def message_handler_wss(_, message):
    # Convertir string a JSON (diccionario)
    data = json.loads(message)
    print(data)

    if data["id"] != "allOrders_5494febb":
        print(data)

    # traders recientes en 24 horas
    elif data["id"] == "allOrders_5494febb":

        print(data)
        print('<>' * 40)

    elif data["id"] == "Orders_5494febb":
        print(data)
        print('<>' * 40)


if __name__ == "__main__":
    symbols = ["adausdt", "filusdt", "vetusdt", "zilusdt", "polusdt", "icpusdt", "vthousdt"]

    app = WebsocketBinanceApiClient(stream_url="wss://ws-api.binance.com:443/ws-api/v3",
                                    mensaje_callback=message_handler_wss)

    # app.my_allOrders(assets=symbols, limit=10, dias=16, sleep=1)
    app.my_Orders(symbol="ADAUSDT", idOrder=6853919884)


    app.stop()
    time.sleep(10)

