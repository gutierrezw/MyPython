import requests
import time
import hashlib
import hmac
import base64
from cryptography.hazmat.primitives.serialization import load_pem_private_key


# --  APIBinance
# API_KEY = "jzYp3GTw5iVdJehCASVdsWUi9ohY7ystIulaMwsGpdFq01vwFn4nGJcSLhRClIzg"
# API_SECRET = b"MC4CAQAwBQYDK2VwBCIEIAjUhYMxXTLWtw6wYRzWoKMbxUNiHaYNHgYdQtfUrysK"

# -- WebSocket_v2
API_KEY = "lwc8WIkg0gtNGIkSwkBbKe6N3OvSLKtf7L3O7AE5Ie4ylGfgJ7sLViR7ItT74Csr"
API_SECRET = "MC4CAQAwBQYDK2VwBCIEIO7gcvIIo7M5xGjp39JPAPcrsad0xc2mEZZi1m/u0hyR"
PRIVATE_KEY_PATH = f"C:\\Users\\InversionesWildaga\\Documents\\MyPython\\keysSeguridad\\Bi_Private_key.pem"

# Load the private key.
# In this example the key is expected to be stored without encryption,
# but we recommend using a strong password for improved security.
with open(PRIVATE_KEY_PATH, 'rb') as f:
    private_key = load_pem_private_key(data=f.read(),
                                       password=None)


BASE_URL = "https://api.binance.com"
endpoint = "/api/v3/account"

# Timestamp the request
timestamp = int(time.time() * 1000) # UNIX timestamp in milliseconds
params = {}
params['timestamp'] = timestamp

# Sign the request
payload = '&'.join([f'{param}={value}' for param, value in params.items()])
signature = base64.b64encode(private_key.sign(payload.encode('ASCII')))
params['signature'] = signature
print(private_key)
print(signature, f'len={len(signature)}')
print(f'len={len(signature.hex())}')

# Send the request
headers = {
    'X-MBX-APIKEY': API_KEY,
}
# Realizar la solicitud GET
headers = {"X-MBX-APIKEY": API_KEY}
response = requests.get(BASE_URL + endpoint, headers=headers, params={"timestamp": timestamp, "signature": signature})

print(response.json())
