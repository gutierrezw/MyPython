from API_vehiculos import BB
from Modulos_python import time, datetime, timedelta
from Modulos_Mysql import insert_booktrading, select_booktrading

cb = BB().spot

if cb.check_binance_connection():
    print('Online Binance')
else:
    print('Offline Binance')
