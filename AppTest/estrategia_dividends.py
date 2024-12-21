import pandas as pd
import pandas.api
from datetime import *
import pprint
import globales
import numpy as np
import keyboard
import yfinance as yf
from Modulos_python import *
from Modulos_Mysql import select_inversion, select_market
from Modulos_Utilitarios import convierte_ticket_crypto


# Crear una lista de fechas mensuales (al inicio de cada mes)
def meses_list():
    try:
        f_desde = datetime.now()
        dia = f_desde.day + 1
        f_desde = f_desde - timedelta(days=dia)
        f_hasta = f_desde + timedelta(days=360)

        meses = pd.date_range(start=f_desde, end=f_hasta, freq='MS')
        l_meses = [date.strftime('%B') for date in meses]

        return l_meses
    except Exception as error:
        print('[meses_list()]: {}'.format(error))


if __name__ == "__main__":

    symbols, dividendos, Date = [], [0] * 12, meses_list()
    print(Date)

    positions = select_inversion(tipoin='Stock', ticket='all')
    for position in positions:

        symbol = convierte_ticket_crypto(position['ticket'])
        (market, ix) = select_market(account='U4214563', symbol=symbol)
        if market:
            rate = market[0][ix.index('lastDividendValue')]
            meses = market[0][ix.index('monthDividendsPay')].split(",")
            if rate > 0:
                m_dividends = rate * position['position']
                symbols.append(position['ticket'])

                for mes in meses:
                    x_mes = mes.strip()
                    if x_mes in Date:
                        dividendos[Date.index(x_mes)] += m_dividends

    d_dividends = {'meses': Date, 'dividendos': dividendos}
    datos = pd.DataFrame(d_dividends, index=Date)
    print(datos)
    plt.figure(figsize=(10, 6))
    plt.bar(datos.index, datos['dividendos'], color='skyblue')
    plt.show()
