import pandas as pd
from datetime import datetime, timedelta
from API_vehiculos import client_spot, ClientError
from binance.client import Client



# Ingresa tus claves de API
client =
Cb = client_spot()

# Definir el par de criptomonedas y el intervalo
symbol = 'BTCUSDT'  # Par de criptomonedas (Bitcoin a USDT)
interval = client.KLINE_INTERVAL_1DAY  # Intervalo de 1 día
interval = '1d'

# Fechas de inicio y fin
start_date = "2024-01-01"
end_date = "2024-01-10"


# Función para obtener los precios entre dos fechas
def get_data_between_dates(symbol, interval, start_date, end_date):
    # Obtener datos desde la fecha de inicio hasta la fecha final
    start_str = start_date
    end_str = end_date
    klines = client.get_historical_klines(symbol, interval, start_str=start_str, end_str=end_str)

    # Convertir los datos a un DataFrame de pandas
    df = pd.DataFrame(klines,
                      columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'CloseTime', 'QuoteAssetVolume',
                               'NumberOfTrades', 'TakerBuyBaseAssetVolume', 'TakerBuyQuoteAssetVolume', 'Ignore'])

    # Convertir Timestamp a formato legible
    df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')

    # Seleccionar solo las columnas relevantes
    df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

    return df


# Llamar a la función
df = get_data_between_dates(symbol, interval, start_date, end_date)

# Mostrar el DataFrame
print(df)
