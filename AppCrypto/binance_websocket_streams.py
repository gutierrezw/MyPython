from API_vehiculos import BB, SpotWebsocketAPIClient, SpotWebsocketStreamClient, config_logging
from Modulos_python import threading, logging, time

def message_handler(_, message):
    print(message)

# ws_client = SpotWebsocketStreamClient(on_message=message_handler)
lista = ["adausdt", "filusdt", "vetusdt", "zilusdt", "polusdt", "ipcusdt", "vthousdt"]


# Mantener la conexión abierta
try:
    wss = []
    for symbol in lista:
        ws_client = SpotWebsocketStreamClient(on_message=message_handler)
        thread = threading.Thread(target=ws_client.ticker, args=(symbol,))
        thread.start()
        wss.append(ws_client)

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    ws_client.stop()
    print("WebSockets cerrados.")

