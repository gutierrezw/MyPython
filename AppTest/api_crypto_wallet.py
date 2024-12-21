import json
import pprint
import asyncio
from binance import Client
from binance import AsyncClient
import binance


api_key = "vxep6cM1R0KVPgY3J4mS2PvvgpPGzGaLVcIeMxeqHc82y6QuATBYlcBrRvBhivKs"
api_secret = "yvXIfJGvdVJ8iSQN2qZKfUxUQfY9tcLMrlkJZeVmlUdH0CBVJ4igM7yg8CqH4N8J"
proxies = {
    'http': 'http://192.168.0.23:3128',
    'https': 'http://192.168.0.23:1080'}



def main():
    try:
        client = Client(api_key, api_secret)

        res = client.get_account()
        print(json.dumps(res, indent=2))

    except binance.exceptions as error_binance:
        print("[Error] :", error_binance)

if __name__ == "__main__":
    main()
