"""
Diagnóstico de WebSocket IB — conecta al gateway y subscribe a conids hardcodeados.
Usar solo para pruebas manuales con gateway activo.
    python AppTest/run_ib_websocket.py
"""

import sys
import os
import ssl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Mysql import BDsystem
from Class_Ibrks import IBClient
from API_vehiculos import websocket, time


def on_message(ws, message):
    print(message)


def on_error(ws, error):
    print(error)


def on_close(ws):
    print("## CLOSED! ##")


def on_open(ws):
    print("Opened Connection")
    time.sleep(3)
    conids = ["4730124", "166090175", "2585769"]
    for conid in conids:
        ws.send("smd+" + conid + '+{"fields": ["31", "55", "7051"]}')


if __name__ == "__main__":
    sesion = BDsystem.get_sesion_by_vehiculo("Stock")
    if not sesion:
        print("ERROR: No se encontró sesión vehiculo='Stock' en BD")
        sys.exit(1)

    username = sesion["iduser"]
    account = sesion["idcuenta"]
    print(f"Conectando como {username} / {account}")

    ib = IBClient(username=username, account=account)
    print(ib.portfolio_account_ledger(account_id=account))

    ws = websocket.WebSocketApp(
        url="wss://localhost:5501/v1/api/ws",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
