from api_binance import *
import pandas as pd
from datetime import *
import pprint
import globales
import numpy as np
import keyboard
import yfinance as yf
import rutinas
from bd_conect import select_booktrading, insert_booktrading, min_fec_booktrading, select_inversion
from main_crypto import performa_asset

account = 'U4214563'
vehiculo = 'Stock'
symbol, rtn_index, cum_index, index_ref = vehiculo_parm(vehiculo=vehiculo)
account = 'U4214563'


def performa_historia():
    book, ix = select_booktrading(accion='cuenta', account=account, idivisa='USD')
    wasset, wlist = asset, xlist

    for keys in book:
        ticket = keys[ix.index('simbolo')].replace("USDT", "-USD")
        ticket = keys[ix.index('simbolo')].replace(" CRYPTO", "-USD")

        if ticket not in wlist:
            wasset[ticket] = 0.02
            wlist.append(ticket)

    return wasset, wlist


def performa_position():
    positions = select_inversion(tipoin='Stock')
    for keys in positions:
        ticket = keys['ticket'].replace("USDT", "-USD")
        ticket = keys['ticket'].replace(" CRYPTO", "-USD")

        asset[ticket] = keys['peso']
        xlist.append(keys['ticket'])
    return asset, xlist


def index_performa():

    wperf['Adj Close'] = yf.download(symbol, start=start_date, end=hoy)['Adj Close']

    print(start_date, hoy, wperf.shape[0])
    wperf[rtn_index] = wperf['Adj Close'].pct_change()
    wperf[cum_index] = (1 + wperf[rtn_index]).cumprod() - 1
    wperf.insert(wperf.shape[1], '++ index', 0)
    wperf.insert(wperf.shape[1], 'gyp_dia', 0)
    wperf.fillna(0, inplace=True)


def asset_performa(filtro=None) -> list:
    def add_dataframe():
        print(keys, datx.shape[0])
        if not datx.empty:
            ticket = keys.replace("-USD", "")
            datx['Return ' + ticket] = datx['Adj Close'].pct_change()
            wperf['Cum ' + ticket] = (1 + datx['Return ' + ticket]).cumprod() - 1
            wperf['Cum ' + ticket] = wperf['Cum ' + ticket] * float(vals)
            wperf['++ index'] = wperf[['++ index', 'Cum ' + ticket]].sum(axis=1)
        else:
            adel.append(keys)
            # print('no existe yfinance()', keys, start_date)

    adel, datx = list(), pd.DataFrame()
    for keys, vals in asset.items():
        if is_none(filtro):
            datx = yf.download(keys, start=start_date.strftime("%Y-%m-%d"))
            add_dataframe()
        else:
            if filtro == keys:
                datx = yf.download(keys, start=start_date.strftime("%Y-%m-%d"))
                add_dataframe()
                datx = pd.DataFrame()
            else:
                add_dataframe()
    return adel


def elimina_asset(filtro=None):
    for i in (range(len(xlist))):
        if is_none(filtro):
            if xlist[i] in adel:
                asset.pop(xlist[i])


if __name__ == '__main__':

    wperf = pd.DataFrame()
    asset, xlist = dict(), list()
    asset, xlist = performa_position()
    asset, xlist = performa_historia()
    hoy = datetime.now().date()
    inicio = min_fec_booktrading(list_asset=xlist, account=account, idivisa='USD')
    start_date = inicio['ifecha'].date()

    index_performa()
    adel = asset_performa(filtro=None)
    print('inicio Insert_performa...', start_date, 'Index=', wperf.shape[0], 'assen Nro',
          len(asset), 'eliminar', len(adel))

    elimina_asset()
    display = False
    print('construye:: Insert_performa...', start_date, 'Index=', wperf.shape[0],
          'assen Nro', len(asset), 'DataFrame()=', wperf.columns)
    print(wperf[['Cum SPX', '++ index']])
    # ==============================================================================

    conn = connect_dbase("select.performa_inversion")
    cursor = conn.cursor()

    qry = """SELECT p_referencia FROM performa_inversion WHERE idcuenta = '%s'  AND vehiculo = '%s' 
                                                           AND fechaclose ='%s' AND referencia = '%s';"""

    upd = """UPDATE performa_inversion SET p_referencia = '%s', p_vehiculo = '%s'
                       WHERE idcuenta = '%s' AND vehiculo = '%s' AND referencia = '%s' AND fechaclose = '%s';"""

    for date, rows in wperf.iterrows():

        cursor.execute(qry % (account, vehiculo, date,  index_ref))
        sql = cursor.fetchone()
        if sql:
            # print(date, rows['Cum SPX'], sql)
            cum = Decimal(rows['Cum SPX'])
            veh = Decimal(rows['++ index'])
            cursor.execute(upd % (cum, veh, account, vehiculo, index_ref, date))
            conn.commit()
        else:
            print('no encontrado', date, rows['Cum SPX'], sql)



