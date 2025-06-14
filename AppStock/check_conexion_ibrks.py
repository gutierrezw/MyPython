from API_vehiculos import IB
from Modulos_python import time, datetime, timedelta, json
from Modulos_Mysql import insert_booktrading, select_booktrading

ib = IB()

if ib.is_localhost():
    print('Online Ibrks')
else:
    print('Offline Ibrks')
