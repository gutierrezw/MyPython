import pandas as pd
import pandas.api
from datetime import *
import pprint
import numpy as np
import yfinance as yf

hoy = datetime.now()
# position = select_inversion(tipoin='Stock', ticket='all')
symbol = 'HASI'

activo = yf.Ticker('ADA-USD')
# datos = yf.download(symbol, period='5d')
print(f'activo :{activo.info["region"]} {activo.info["symbol"]} ')
# last = activo.history(period='1d')['Close'].index
# print(activo.info['symbol'], '>> info() :', last.date)
#div = activo.dividends
#print(activo.history()['Dividends'])

#year = pd.Timestamp.now().year - 1
#anual = div[div.index.year == year]
#meses = anual.index.strftime('%B')
#print(list(meses))


# datos = pd.DataFrame(div).reset_index()
# datos['fecha'] = pd.to_datetime('Date')
# print(datos)
# print(datos['Date'].month)
# datos['Mes'] = datos['Date'].month

# print(meses)

# if not m_div.empty:
#     pd.options.mode.copy_on_write = True
#    datos = activo.history(period='8y')[['Close', 'Splits']]
#    m_datos = datos[datos['Dividends'] != 0]
#    m_datos['Rendimiento'] = m_datos['Dividends'] / m_datos['Close']
#    ncolumn = m_datos.columns

    # y_datos = pd.DataFrame(columns=ncolumn)
    # y_datos['Close'] = m_datos['Close'].resample('YE').mean()
    # y_datos['Dividends'] = m_datos['Dividends'].resample('YE').sum()
    # y_datos['Rendimiento'] = m_datos['Rendimiento'].resample('YE').sum()

    # print(y_datos)
    # print(y_datos.describe())
    # print(activo.recommendations_summary)
    # print(activo.upgrades_downgrades)
    # print(activo.fast_info['lastPrice'])





