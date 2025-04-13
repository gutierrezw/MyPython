from API_vehiculos import BB
from Modulos_python import time, datetime, timedelta
from Modulos_Mysql import insert_booktrading, select_booktrading


def generar_timestamps(inicio=None, fin=None, intervalo_meses=6):
    timestamps = []
    fecha_actual = inicio

    while fecha_actual < fin:
        fecha_fin = fecha_actual + timedelta(days=intervalo_meses * 30)  # Aproximación de 6 meses
        if fecha_fin > fin:
            fecha_fin = fin

        timestamps.append((int(fecha_actual.timestamp() * 1000), int(fecha_fin.timestamp() * 1000)))
        fecha_actual = fecha_fin

    return timestamps

def get_trader_insert_fiat(Response=None):
    trader = []
    for keys, values in Response.items():
        if keys == 'data':
            for i, rows in enumerate(values):

                date = datetime.fromtimestamp(rows['createTime'] / 1000)

                if (rows['tradeType'] == 'BUY') and (rows['orderStatus'] == 'COMPLETED') and (rows['fiat'] == 'ARS'):
                    values = {}

                    values.update({'categoria': rows['fiat']})
                    values.update({'divisa': 'USD'})
                    values.update({'cuenta':  rows['fiat']+ '-0001'})
                    values.update({'fechahora': date})
                    values.update({'idtrans': rows['advNo']})
                    values.update({'cantidad': float(rows['takerAmount'])})
                    values.update({'preciotrans': float(rows['unitPrice'])})
                    values.update({'preciocierre': float(rows['unitPrice'])})
                    values.update({'producto': float(rows['totalPrice'])})
                    values.update({'tarifacomision': .0})
                    values.update({'gprealizadas': .0})
                    values.update({'mtmgp': .0})
                    values.update({'codigo': .0})
                    trader.append(values)

    # valida e inserta booktrading
    last_trader, ix = select_booktrading(accion='last', account='ARS-0001', idivisa='USD')
    last_date = last_trader[0]['fechahora'] if last_trader else datetime(2000, 1, 1)
    asc_trader = sorted(trader, key=lambda x: x['fechahora'], reverse=False)

    for i, values in enumerate(asc_trader):
        if last_date < values['fechahora']:
            insert_booktrading(values, symbol=rows['asset'])

    return asc_trader

if __name__ == '__main__':

    cb = BB()
    desde = datetime(2021, 1, 1)
    hasta = datetime.today()

    intervalos = generar_timestamps(inicio=desde, fin=hasta)

    for start_time, end_time in intervalos:
        f_desde = datetime.fromtimestamp(start_time / 1000)
        f_hasta = datetime.fromtimestamp(end_time / 1000)

        response = cb.w_c2c_trade_history(tradeType='BUY', startTimestamp=start_time, endTimestamp=end_time)
        if response:
            x_trader = get_trader_insert_fiat(Response=response)
            print(f_desde.date(), f_hasta.date(), 'trader==', len(x_trader))






