import json
from pprint import pprint

# import pandas_datareader.data as web
import requests


def status_marckets(mkt: list=['United States']) -> list():
    try:
        url = 'https://www.alphavantage.co/query?function=MARKET_STATUS&apikey=0RQQPRMXSM0QTQHU'
        r = requests.get(url)
        data = r.json()
        smkt = list()

    except json.JSONDecodeError as error:
        print("[AlfaV error]: {}".format(error))

    for key in data['markets']:
        if key['region'] in mkt:
            smkt.append(key)
    return smkt


def analytics(symbols: list):
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = ('https://alphavantageapi.co/timeseries/analytics?SYMBOLS={}&RANGE=3year&'
           'INTERVAL=DAILY&OHLC=close&CALCULATIONS=MEAN,STDDEV,CUMULATIVE_RETURN'
           '&apikey=0RQQPRMXSM0QTQHU'.format(symbols))
    r = requests.get(url)
    data = r.json()

    print(data)


def sectores():
    api_key = '0RQQPRMXSM0QTQHU'
    url = f'https://www.alphavantage.co/query?function=SECTOR&apikey={api_key}'

    # Realizar la solicitud a la API
    response = requests.get(url)
    data = response.json()

    print(data)

    # Mostrar los datos
    if 'Rank A: Real-Time Performance' in data:
        real_time_performance = data['Rank A: Real-Time Performance']
        for sector, performance in real_time_performance.items():
            print(f'{sector}: {performance}')
    else:
        print("Error al obtener los datos del rendimiento sectorial.")


def fudamentales(ticket=None):
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = "https://www.alphavantage.co/query?function=OVERVIEW&symbol={}&apikey=0RQQPRMXSM0QTQHU".format(ticket)
    r = requests.get(url)
    data = r.json()

    pprint(data)


def inflacion():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=INFLATION&apikey=0RQQPRMXSM0QTQHU'
    r = requests.get(url)
    data = r.json()

    return data


def retail():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=RETAIL_SALES&apikey=0RQQPRMXSM0QTQHU'
    r = requests.get(url)
    data = r.json()

    pprint(data)


def cpi():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=CPI&interval=monthly&apikey=0RQQPRMXSM0QTQHU'
    r = requests.get(url)
    data = r.json()

    pprint(data)


def commodities():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=ALL_COMMODITIES&interval=monthly&apikey=0RQQPRMXSM0QTQHU'
    r = requests.get(url)
    data = r.json()

    pprint(data)


def simbolos():
    # URL de la API de IEX Cloud para obtener los símbolos
    url = 'https://cloud.iexapis.com/stable/ref-data/symbols?token=0RQQPRMXSM0QTQHU'

    # Hacer la solicitud GET a la API
    r = requests.get(url)
    print(r)

    # Convertir la respuesta en formato JSON
    # symbols_data = response.json()
    symbols_data = r.json()

    # Filtrar los símbolos que pertenecen al NASDAQ
    data = [symbol['symbol'] for symbol in symbols_data if symbol['exchange'] == 'NASDAQ']
    print(data)



# print('=====> estatus market')
# print(status_marckets())

# print('=====>   fudamentales()')
# print(fudamentales(ticket='HASI'))

# print('=====> analytics()')
# print(analytics(symbols='CTRM,CHPT,CCI,HASI'))

# print('=====> sectores()')
# print(sectores())

