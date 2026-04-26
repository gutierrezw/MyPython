from API_vehiculos import WebsocketBinanceStreams
from Modulos_python import threading, logging, time, pprint, json, datetime


if __name__ == "__main__":

    lista = ["adausdt", "filusdt", "vetusdt", "zilusdt", "polusdt", "ipcusdt", "vthousdt"]
    def on_mess(_, message):
        print(message)

    app = WebsocketBinanceStreams(stream_url='wss://stream.binance.com:9443',
                                  assets=lista,
                                  mensaje_callback=on_mess)



