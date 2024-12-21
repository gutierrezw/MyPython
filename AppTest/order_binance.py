from API_vehiculos import client_spot
from Class_Binance import Spot, ClientError
from Modulos_python import *
from Modulos_Mysql import select_sesion
import hmac
import hashlib


# ApiKey HMAC
def orden_hmac():
    # ClaseSecreta
    API_KEY = 'lLl295HUw94GnCXXOkWb0MH72JlnlKPndOEXpJYU2gLdjPGyEN7wWytzLl95KNOT'
    API_SECRET = 'mXSXCJz5dG6SzIaH4Gz5SwfSfu9v0rbnDC9TsqBFO1Lo2hgdqcpG6KqbvLSSmKLG'

    bi = Spot(api_key=API_KEY, api_secret=API_SECRET)

    # place = bi.new_order(symbol='ADAUSDT', side='SELL', type='LIMIT', price=.70, quantity=45, timeInForce='GTC')
    # place = bi.cancel_order(symbol='ADAUSDT', orderId=5125065830)
    # print(place)
    print(bi.get_open_orders())


def orden_ed25519():
    API_KEY = 'jzYp3GTw5iVdJehCASVdsWUi9ohY7ystIulaMwsGpdFq01vwFn4nGJcSLhRClIzg'
    PRIVATE_KEY_PATH = f"C:\\Users\\54911\\AppData\\Local\\Programs\\asymmetric-key-generator\\BiPrivate_key.txt"

    # but we recommend using a strong password for improved security.
    with open(PRIVATE_KEY_PATH, 'rb') as f:
        private_key = load_pem_private_key(data=f.read(),
                                           password=None)

    # Set up the request parameters
    params = {
        'symbol': 'ADAUSDT',
        'side': 'SELL',
        'type': 'LIMIT',
        'timeInForce': 'GTC',
        'quantity': '45',
        'price': '0.60',
    }

    timestamp = int(time.time() * 1000) # UNIX timestamp in milliseconds
    params['timestamp'] = timestamp

    # Sign the request
    payload = '&'.join([f'{param}={value}' for param, value in params.items()])
    signature = b64encode(private_key.sign(payload.encode('ASCII')))
    params['signature'] = signature

    # Send the request
    headers = {
        'X-MBX-APIKEY': API_KEY,
    }
    response = requests.post(
        'https://api.binance.com/api/v3/order',
        headers=headers,
        data=params,
    )
    print(response.json())
    print(bi.get_open_orders())


def orden_ed25519_plus():
    API_KEY = 'jzYp3GTw5iVdJehCASVdsWUi9ohY7ystIulaMwsGpdFq01vwFn4nGJcSLhRClIzg'
    PRIVATE_KEY_PATH = f"C:\\Users\\54911\\AppData\\Local\\Programs\\asymmetric-key-generator\\BiPrivate_key.txt"

    # but we recommend using a strong password for improved security.
    with open(PRIVATE_KEY_PATH, 'rb') as f:
        private_key = f.read()


    bi = Spot(api_key=API_KEY, private_key=private_key)
    # place = bi.new_order(symbol='ADAUSDT', side='SELL', type='LIMIT', price=.65, quantity=45, timeInForce='GTC')
    # print(place)
    print(bi.get_open_orders())


orden_ed25519_plus()
