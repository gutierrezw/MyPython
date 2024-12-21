import keyboard
import yfinance as yf
import globales
from bd_conect import select_booktrading, insert_booktrading, min_fec_booktrading, select_inversion
from main_crypto import performa_asset
from bd_conect import *


sql = "SELECT count(*) FROM washList  WHERE ticket ='%s';"
conn = connect_dbase("update.washList", False)
cursor = conn.cursor()
try:
    book, ix = select_booktrading(accion='cuenta', account='B0000001', idivisa='USD')
    date, gain, fee, lost, enter = list(), list(), list(), list(), list()

    for keys in book:

        if keys[ix.index('gprealizadas')] > 0:
            gain.append(keys[ix.index('gprealizadas')])
            lost.append(0)
        else:
            lost.append(-keys[ix.index('gprealizadas')])
            gain.append(0)

        fee.append(keys[ix.index('tarifacomision')])
        date.append(keys[ix.index('fechahora')])

        if keys[ix.index('codigo')] == 'O':
            enter.append(keys[ix.index('producto')])
        else:
            enter.append(0)
    resum = pd.DataFrame()
    extract = pd.DataFrame({'Date': date, 'depositos': enter, 'crecimiento': gain, 'perdidas': lost, 'comision': fee})
    extract['year'] = extract['Date'].dt.year
    extract['mes'] = extract['Date'].dt.month

    xdato = extract.groupby(['year', 'mes'])['crecimiento'].sum().reset_index()
    xdato['depositos'] = extract.groupby(['year', 'mes'])['depositos'].sum().reset_index()['depositos']
    xdato['perdidas'] = extract.groupby(['year', 'mes'])['perdidas'].sum().reset_index()['perdidas']
    xdato['comision'] = extract.groupby(['year', 'mes'])['comision'].sum().reset_index()['comision']
    print(xdato)


except EncodingWarning as error:
    print("[Mysql error]: {}".format(error))
