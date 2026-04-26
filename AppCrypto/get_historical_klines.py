from API_vehiculos import BB
from Modulos_python import datetime, pd

# Claves (pueden estar vacías si solo hacés consultas públicas)
api_key = ''
api_secret = ''
# client = Client(api_key, api_secret)
client = BB().spot

# Define tu par y rango de fechas
symbol = 'POLUSDT'
interval = '1d'
i_fecha = datetime.strptime("2020-09-30", "%Y-%m-%d")
f_fecha = datetime.strptime("2025-04-30", "%Y-%m-%d")

start = int(i_fecha.timestamp() * 1000)
end = int(f_fecha.timestamp() * 1000)
print(f'inicio {start} y fin {end}')

# Obtener datos históricos de velas
klines = client.klines(symbol=symbol, interval=interval, startTime=start, endTime=end, limit=1000)

#Index(['Close', 'High', 'Low', 'Open', 'Volume'], dtype='object', name='Price')
# Convertir a DataFrame
df = pd.DataFrame(klines, columns=[
    'Open Time',  'Open', 'High', 'Low', 'Close', 'Volume',
    'Close_time', 'quote_asset_volume', 'number_of_trades',
    'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
])

# Convertir tiempos y dar formato a columnas como yfinance
df["Date"] = pd.to_datetime(df["Open Time"], unit='ms')
df.drop(columns=[
    "Open Time", 'Close_time', 'quote_asset_volume', 'number_of_trades',
    'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'], inplace=True)
df.set_index("Date", inplace=True)

print(df)
