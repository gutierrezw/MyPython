from binance.lib.utils import config_logging
from API_vehiculos import BB
from Modulos_Mysql import select_booktrading
from Modulos_python import pprint, timedelta, datetime

ib = BB().spot

(utrading, ix) = select_booktrading(accion='timestamp',
                                    account='B0000001',
                                    idivisa='USD')
ifecha = utrading[0]['fechahora']
print(ifecha)
ifecha += timedelta(days=-13)
efecha = ifecha

symbols = ["adausdt", "filusdt", "vetusdt", "zilusdt", "polusdt", "icpusdt", "vthousdt"]
hoy = datetime.now()
while efecha <= hoy:
    efecha += timedelta(days=1)
    sfecha = efecha
    sfecha += timedelta(days=-1)

    stime = int(sfecha.timestamp() * 1000)
    etime = int(efecha.timestamp() * 1000)

    for keys in symbols:
        response = ib.w_trade = ib.w_my_trades(keys.upper(), limit=20, startTime=stime, endTime=etime)
        if response:
            print(f'ini: [{sfecha}:{efecha}]', response)