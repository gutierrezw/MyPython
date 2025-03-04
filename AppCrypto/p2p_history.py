from API_vehiculos import BB
from Modulos_python import time, datetime


cb = BB()

# Obtener timestamps actuales
start_time = int(time.time() * 1000) - (360 * 24 * 60 * 60 * 1000)  # Hace 30 días
end_time = int(time.time() * 1000)  # Ahora

x_response = cb.w_c2c_trade_history(tradeType='BUY', startTimestamp=start_time, endTimestamp=end_time)
for keys, values in x_response.items():
    if keys == 'data':
        for i, rows in enumerate(values):

            date = datetime.fromtimestamp(rows['createTime'] / 1000)

            print('i..', i, ' rows...', date, rows['unitPrice'], rows['takerAmount'], rows['orderStatus'])


