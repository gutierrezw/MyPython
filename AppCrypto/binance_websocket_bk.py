from API_vehiculos import BB, SpotWebsocketAPIClient, config_logging
from Modulos_python import threading, logging, time, json, b64encode, b64decode, requests, hmac, hashlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import nacl.signing


def message_handler_ticker_24hr(_, message):

    # Convertir string a JSON (diccionario)
    data = json.loads(message)
    items = data['result']

    fields = ['symbol', 'lastPrice', 'askPrice', 'bidPrice', 'openPrice', 'prevClosePrice']
    for rows in items:
        print({key: rows[key] for key in fields})

def message_handler_trades(_, message):
    global serverTime

    # Convertir string a JSON (diccionario)
    data = json.loads(message)
    print(data)

    # set time del servidor websocket
    if data['id'] == '1000-set-time':
        serverTime = data['result']['serverTime']



def signature_ed25519_pem():
    api_key = 'csNNBgZlT48NCm7tkfON2GnBUgbopQd744xRp384Y7gBxAXE3XRW8aeWbWR4JhmZ'
    PRIVATE_KEY_PATH = f"C:\\Users\\InversionesWildaga\\Documents\\MyPython\\keysSeguridad\\BB_Private_key.pem"

    # 📌 Leer la clave privada desde el archivo PEM
    with open(PRIVATE_KEY_PATH, "rb") as f:
        private_key_pem = f.read()

    print(private_key_pem)

    # Desencriptar la clave (asegúrate de usar .encode() en la contraseña)
    password = "wILDAGAINVERSIONES2004".encode()

    # 📌 Cargar la clave privada en formato Ed25519
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)

    # 📌 Firmar un mensaje vacío (requerido por Binance)
    message = b""
    signature = private_key.sign(message)

    # 📌 Convertir la firma a HEX y Base64
    signature_hex = signature.hex()
    timestamp = int(time.time() * 1000)
    print(signature_hex)

    return api_key, signature_hex, timestamp

def signature_ed25519_hmac_serializado_pem():
    api_key = 'csNNBgZlT48NCm7tkfON2GnBUgbopQd744xRp384Y7gBxAXE3XRW8aeWbWR4JhmZ'
    PRIVATE_KEY_PATH = f"C:\\Users\\InversionesWildaga\\Documents\\MyPython\\keysSeguridad\\BB_Private_key.pem"

    # 📌 Leer la clave privada desde el archivo PEM
    with open(PRIVATE_KEY_PATH, "rb") as f:
        private_key_pem = f.read()


    # 📌 Cargar la clave privada en formato Ed25519
    message = b""
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)

    # 3️⃣ Generar la firma HMAC SHA256
    timestamp = int(time.time() * 1000)
    # signature = hmac.new(private_key.private_bytes(encoding=serialization.Encoding.PEM,
    #                                               format=serialization.PrivateFormat.PKCS8,
    #                                               encryption_algorithm=serialization.NoEncryption()),
    #                                               message, hashlib.sha256).hexdigest()
    signature = hmac.new(private_key_pem, message, hashlib.sha256)
    signature_hex = signature.hexdigest()
    signature_base64 = base64.b64encode(signature.digest()).decode()

    print(signature.digest())
    print(signature_hex)
    print(signature_base64)

    return api_key, signature_hex, timestamp

def signature_ed25519_hmac_pem():
    api_key = 'csNNBgZlT48NCm7tkfON2GnBUgbopQd744xRp384Y7gBxAXE3XRW8aeWbWR4JhmZ'
    PRIVATE_KEY_PATH = f"C:\\Users\\InversionesWildaga\\Documents\\MyPython\\keysSeguridad\\BB_Private_key.pem"

    # 📌 Leer la clave privada desde el archivo PEM
    with open(PRIVATE_KEY_PATH, "rb") as f:
        private_key_pem = f.read()


    # 📌 Cargar la clave privada en formato Ed25519
    message = b""
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)

    # 3️⃣ Generar la firma HMAC SHA256
    timestamp = int(time.time() * 1000)
    signature = hmac.new(private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                                   format=serialization.PrivateFormat.PKCS8,
                                                   encryption_algorithm=serialization.NoEncryption()),
                                                   message, hashlib.sha256)
    signature_hex = signature.hexdigest()
    signature_base64 = base64.b64encode(signature.digest()).decode()

    print(signature_hex)
    print(signature_base64)


    return api_key, signature_hex, timestamp

def signature_ed25519_hmac_secretkey():
    bi = BB()
    api_key = bi.api_key
    key_data = bi.private_key

    private_key = key_data.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").strip()

    timestamp = int(time.time() * 1000)
    query_string = 'timestamp={}'.format(timestamp)
    query_string = b""

    print(key_data)
    print(private_key)
    print(query_string)

    # 3️⃣ Generar la firma HMAC SHA256
    # signature = hmac.new(private_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    signature = hmac.new(private_key.encode('utf-8'), query_string, hashlib.sha256).hexdigest()

    print(signature)

    return api_key, signature, timestamp

def signature_apikey():
    bi = BB()
    api_key = bi.api_key
    api_secret = bi.private_key
    timestamp = int(time.time() * 1000)

    print(api_key)
    print(api_secret)
    return api_key, api_secret, timestamp

def signature_ed25519_perplexity_e1():
    api_key = 'lwc8WIkg0gtNGIkSwkBbKe6N3OvSLKtf7L3O7AE5Ie4ylGfgJ7sLViR7ItT74Csr'
    PRIVATE_KEY_PATH = f"C:\\Users\\InversionesWildaga\\Documents\\MyPython\\keysSeguridad\\Bi_Private_key.pem"

    # 📌 Leer la clave privada desde el archivo PEM
    with open(PRIVATE_KEY_PATH, "rb") as f:
        private_key_pem = f.read()

    print(private_key_pem)

    # 📌 Cargar la clave privada en formato Ed25519
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)

    # 📌 Firmar un mensaje vacío (requerido por Binance)
    timestamp = int(time.time() * 1000)
    payload = b''
    # signature = private_key.sign(payload.encode()).hex()
    signature = private_key.sign(payload).hex()

    print(payload)
    print(signature)


    return api_key, signature[-32], timestamp

def signature_ed25519_perplexity_e2():
    api_key = 'lwc8WIkg0gtNGIkSwkBbKe6N3OvSLKtf7L3O7AE5Ie4ylGfgJ7sLViR7ItT74Csr'
    PRIVATE_KEY_PATH = f"C:\\Users\\InversionesWildaga\\Documents\\MyPython\\keysSeguridad\\Bi_Private_key.pem"

    # 📌 Leer la clave privada desde el archivo PEM
    with open(PRIVATE_KEY_PATH, "rb") as f:
        private_key_pem = f.read()

    print(private_key_pem)

    # 📌 Cargar la clave privada en formato Ed25519
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)

    # 📌 Firmar un mensaje vacío (requerido por Binance)
    # Firmar mensaje
    message = b""
    timestamp = int(time.time() * 1000)
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    print(payload)
    print(signature.hex())
    print(signature_base64)


    return api_key, signature, timestamp

def signature_ed25519_perplexity_e3():
    api_key = 'lwc8WIkg0gtNGIkSwkBbKe6N3OvSLKtf7L3O7AE5Ie4ylGfgJ7sLViR7ItT74Csr'
    private_key_pem = 'MC4CAQAwBQYDK2VwBCIEIO7gcvIIo7M5xGjp39JPAPcrsad0xc2mEZZi1m/u0hyR'


    private_key_bytes = base64.b64decode(private_key_pem)
    print(private_key_pem)
    private_key_bytes = private_key_bytes[-32:]
    print(private_key_bytes)

    signing_key = nacl.signing.SigningKey(private_key_bytes)

    # 📌 Firmar el timestamp con Ed25519
    timestamp = int(time.time() * 1000)
    signed = signing_key.sign(str(timestamp).encode())

    message = b""
    signed = signing_key.sign(message)
    signature = signed.signature.hex()

    print(signature)


    return api_key, signature, timestamp

def signature_ed25519_perplexity_e4():
    api_key = 'lwc8WIkg0gtNGIkSwkBbKe6N3OvSLKtf7L3O7AE5Ie4ylGfgJ7sLViR7ItT74Csr'
    private_key_pem = 'MC4CAQAwBQYDK2VwBCIEIO7gcvIIo7M5xGjp39JPAPcrsad0xc2mEZZi1m/u0hyR'

    private_key = private_key_pem.encode()
    print(f'private_key_pem={private_key_pem}')
    print(f'private_key={private_key}')

    # 📌 Firmar un mensaje vacío (requerido por Binance)
    # Firmar mensaje
    message = b""
    signature = hmac.new(private_key, message, hashlib.sha256).hexdigest()
    print(f'signature={signature}')
    print(f'len signature={len(signature)}')

    timestamp = int(time.time() * 1000)

    timestamp_2 = requests.get("https://api.binance.com/api/v3/time").json()["serverTime"]
    # timestamp_3 = requests.get("https://ws-api.binance.com:443/ws-api/v3/time").json()["serverTime"]

    print(timestamp_2, timestamp)

    return api_key, signature, timestamp


# Mantener la conexión abierta
try:

    global serverTime

    serverTime = 0
    API_KEY, SIGNATURE, timestamp = signature_ed25519_perplexity_e4()


    assets=["ADAUSDT", "FILUSDT", "VETUSDT", "ZILUSDT", "POLUSDT", "ICPUSDT", "VTHOUSDT"]


    # ws_price = SpotWebsocketAPIClient(on_message=message_handler_ticker_24hr)
    ws_trade = SpotWebsocketAPIClient(on_message=message_handler_trades)

    ws_trade.server_time(id='1000-set-time')

    auth_request = {
        "id": "auth_request_1",
        "method": "session.logon",
        "params": {
            "apiKey": API_KEY,
            "timestamp": serverTime,
            "signature": SIGNATURE
        }
    }

    ws_trade.send(auth_request)
    # ws_trade = SpotWebsocketAPIClient(stream_url="wss://ws-api.binance.com:443/ws-api/v3",
    #                                   on_message=message_handler_trades,
    #                                   api_key=API_KEY,
    #                                  api_secret=SIGNATURE)


    while True:
        # ws_price.ticker_24hr(symbols=assets)
        # print('-- price ', "-" * 20)
        # time.sleep(1)

        for keys in assets:
           ws_trade.order_history(symbol=keys, limit=10)

        print('-- trades ', "-" * 20)
        time.sleep(1)


except KeyboardInterrupt:
    ws_trade.stop()
    print("WebSockets cerrados.")

