import keyboard
import yfinance as yf
import globales
from bd_conect import select_booktrading, insert_booktrading, min_fec_booktrading, select_inversion
from main_crypto import performa_asset
from bd_conect import *


def target_price_washlist():
    """
    @return: actualizar targetpreci en en tabla washlist a partir de información API yf.Ticker(symbol).info
    """
    sql = "SELECT count(*) FROM washList  WHERE ticket ='%s';"
    conn = connect_dbase("update.washList", False)
    cursor = conn.cursor()
    try:
        position = select_inversion(tipoin='Stock', ticket='all')
        asset = list()

        for keys in position:
            symbol = keys['ticket'].replace("USDT", "-USD")
            x = yf.Ticker(symbol).info
            asset.append(x)
            campos, values = [], []

            if 'targetMeanPrice' in x:
                campos.append('targetprice')
                values.append(x['targetMeanPrice'])
            else:
                if 'fiftyTwoWeekHigh' in x:
                    campos.append('targetprice')
                    values.append(x['fiftyTwoWeekHigh'])

            if 'beta' in x:
                campos.append('beta')
                values.append(x['beta'])

            if 'priceToSalesTrailing12Months' in x:
                campos.append('priceto_sales')
                values.append(x['priceToSalesTrailing12Months'])

            if 'priceToBook' in x:
                campos.append('priceto_book')
                values.append(x['priceToBook'])

            if 'forwardPE' in x:
                campos.append('forward_pe')
                values.append(x['forwardPE'])

            if 'trailingPE' in x:
                campos.append('trailing_pe')
                values.append(x['trailingPE'])

            if len(campos) > 1:
                cursor.execute(sql % symbol)
                found = cursor.fetchone()[0]

                if found:
                    update_washlist(cursor=cursor, upd=campos, val=values, ticket=symbol)
                    conn.commit()

    except Exception as error:
        print("[ target_price_washlist()]: {}".format(error))
