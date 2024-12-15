from _datetime import *

import pandas as pd
import yfinance as yf

from rutinas import convierte_ticket_crypto, is_none, vehiculo_parm


def get_yfinance(ticket=None, vehiculo='Stock', period='5y', desde=None, hasta=None):
    """
    @param ticket: id de activo
    @param vehiculo: tipo de activo Crypto, stock
    @param period: intervalo de tiempo para la solicitud de datos historicos
    @param desde: fecha de inicio de intervalo para la solicitud de datos historicos
    @param hasta: fecha fin de intervalo para la solicitud de datos historicos
    @return: retorna structura yf.Ticker y/o Dataframe()
    """
    try:
        # unifica ticket Crypto al dominio yfinance
        symbol = convierte_ticket_crypto(ticket)

        # esta opción no retorna en pdatos la columna "Adj Close", pero entrega Dividends y Splits
        if vehiculo == 'Stock':
            activo = yf.Ticker(symbol)
            pdatos = activo.history(period=period)

        if vehiculo != 'Stock':

            # download sin fecha desde y hasta
            if is_none(desde) and is_none(hasta):
                pdatos = yf.download(symbol, period='5y')
                activo = dict()

            # download con fecha desde y hasta
            if not is_none(desde) and not is_none(hasta):
                pdatos = yf.download(symbol, start=desde, end=hasta)
                activo = dict()

        return activo, pdatos

    except (KeyError, ValueError) as error:
        print("[Error:: get_stock_info()]: {}".format(error))

    except Exception as error:
        print("[Error:: get_stock_info()]: {}".format(error))

    except EncodingWarning as error:
        print("[Error:: get_stock_info()]: {}".format(error))

    return None, None


def get_index_performa(vehiculo=None, date=None):
    """
    @param vehiculo: tipo de inversión stock, Crypto
    @param date:  fecha de inicio para cálculo de performa
    @return:  entrega DATAFRAME, desempeño de índice a partir de fecha de inicio. Cálculo logarithmic o arithmetic
    """

    hoy = datetime.now().date()
    f_inicio = date - timedelta(days=5)
    (symbol, rtn_index, cum_index, index_ref) = vehiculo_parm(vehiculo=vehiculo)
    performa = pd.DataFrame()

    (activo, datos) = get_yfinance(ticket=symbol, vehiculo='download', desde=f_inicio, hasta=hoy)

    performa[rtn_index] = datos['Adj Close'].pct_change()
    performa[cum_index] = (1 + performa[rtn_index]).cumprod() - 1

    return performa.iloc[-1][rtn_index], rtn_index, cum_index, index_ref