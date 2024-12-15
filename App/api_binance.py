from binance.error import ClientError

from Spot_binance import *
from bd_conect import *

global alock
alock = threading.Lock()


def client_spot():

    sesion = select_sesion("select", vehiculo='Crypto')
    xapiuser = sesion['userapi'].decode('utf-8')
    xapipass = sesion['userpass'].decode('utf-8')
    client = Spot(api_key=xapiuser, api_secret=xapipass)
    return client


client = client_spot()


def search_asset(cpositions, key) -> int:
    """
    @param cpositions:
    @param key:
    @return: busca symbol en position crypto
    """
    for i in range(len(cpositions)):
        if key in tuple(cpositions[i].keys()):
            return i
    return -1


def wallet_snapshot() -> dict:
    """
    @return: posición de cryptos contenidas en binance
    """
    def update_positions():
        total = 0
        for i in cpositions:
            crypt = tuple(i.keys())
            key = i[crypt[1]]
            asset = crypt[0] + 'USDT'
            """
            @ rechaza USDT o quote_asset
            """
            if crypt[0] != 'USDT':
                row, tick_ok = insert_crypto(symbol=asset)
                if tick_ok:
                    prc = connect_avg_price(symbol=asset)
                    if prc:
                        if float(prc['lastPrice']) > 0:
                            tborrowed, tfree, tlocked, tnetasset, trewards = 0, 0, 0, 0, 0
                            tnetasset += Decimal(key['netAsset'])
                            tborrowed += Decimal(key['borrowed'])
                            trewards += Decimal(key['rewards'])
                            tlocked += Decimal(key['locked'])
                            tfree += Decimal(key['free'])

                            coss = Decimal(row[0]['avgcost']) * (tborrowed + tnetasset)
                            vmkt = Decimal(prc['lastPrice']) * (tborrowed + tnetasset)
                            div = Decimal(prc['lastPrice']) * trewards
                            gyp = vmkt - coss
                            total += coss
                            """
                            @  crea la position cuando el valor del activo es mayor 1$
                            """
                            if vmkt > 1:
                                cartera = select_inversion(tipoin='Crypto', ticket=asset)[0]
                                if cartera:
                                    rets = gyp / coss if coss > 0 else 0
                                    symbols.append(asset)
                                    d_symbol = {'ticket': asset, 'estrategia': cartera['estrategia'],
                                                 'contractDesc': asset,
                                                 'empresa': cartera['empresa'],
                                                 'position': tborrowed + tnetasset,
                                                 'Peso': 0.00,
                                                 'deuda': cartera['deuda'],
                                                 'mrkprice': Decimal(prc['lastPrice']),
                                                 'costobase': cartera['costobase'],
                                                 'open': prc['openPrice'],
                                                 'sector': 'Crypto activo',
                                                 'Adiv': div,
                                                 'conid': row[0]['idcrypto'],
                                                 'unrealizedpnl': gyp,
                                                 'CosS': coss,
                                                 'RetS': rets,
                                                 'Obje': cartera['objetivo']}

                                    symbols.append(asset)
                                    xpositions.append(d_symbol)
                                    price_washlist(key=d_symbol, precio=prc)
        """
        @ calculo piso de cada activo
        """
        for key in xpositions:
            key['Peso'] = key['CosS'] / total
            symbols.append(key['ticket'])

        return xpositions, symbols

    global alock

    cpositions = list()
    itru = True
    try:
        w_spot = connect_account_snapshot(tipo="SPOT")
        if w_spot:
            pos = len(w_spot) - 1
            w_spot = w_spot[pos]
            xdata = w_spot['data']['balances']
            for key in xdata:
                if float(key['free']) > 0 and key['asset'][0:2] != 'LD':
                    cpositions.append({key['asset']: 'asset', 'spot': {'borrowed': 0, 'free': key['free'],
                                                                           'locked': 0, 'netAsset': 0, 'rewards': 0}})

        xdata = connect_get_flexible_product_position()
        if xdata:
            for i in range(xdata['total']):
                key = xdata['rows'][i]
                found = search_asset(cpositions, key['asset'])

                if found == -1:
                    if float(key['collateralAmount']) != 0 or float(key['totalAmount']) != 0:
                        cpositions.append({key['asset']: 'asset', 'earn': {'borrowed':  key['collateralAmount'],
                                                                           'free': key['totalAmount'], 'locked': 0,
                                                                           'netAsset': key['totalAmount'],
                                                                           'rewards': key['cumulativeTotalRewards']}})

                else:

                    if float(key['collateralAmount']) != 0 or float(key['totalAmount']) != 0:
                        cpositions[found].update({'earn': {'borrowed':  key['collateralAmount'],
                                                           'free': key['totalAmount'], 'locked': 0,
                                                           'netAsset': key['totalAmount'],
                                                           'rewards': key['cumulativeTotalRewards']}})

    except ClientError as error:
        logger.error(
            "Found error. status: {}, error code: {}, error message: {}".format(
                error.status_code, error.error_code, error.error_message
            )
        )
        itrue = False

    xpositions, symbols, total = list(), list(), 0
    if itru:

        if len(cpositions) > 0:
            update_positions()

    return xpositions, symbols


def debit_wallet(positions=None) -> list:
    """
    @param positions:
    @return:  deuda en USDT para cada una de cryptos en earn
    """
    global alock

    itrue, wdeb = True, 0
    try:
        for keys in positions:
            ticket = keys['ticket'].replace("USDT", "")
            with alock:
                w_loan = client.flexible_loan_ongoing_orders(loanCoin="USDT", collateralCoin=ticket,
                                                                 current=1, limit=5, recvWindow=5000)
            if w_loan['total'] > 0:
                wrow = w_loan['rows'][0]
                wdeb += Decimal(wrow['totalDebt'])
                keys['deuda'] = wrow['totalDebt']

    except ClientError as error:
        logger.error(
            "Found error. status: {}, error code: {}, error message: {}".format(
                error.status_code, error.error_code, error.error_message
            )
        )
        itrue = False

    time.sleep(1)
    if itrue:
        return positions, wdeb
    else:
        return None, wdeb


def price_washlist(key=None, precio=None):
    """
    @param key: información de la positions del symbol
    @param precio: dict de API ticker_24hr
    @return: Mantiene actualizado el precio y otros datos en washlist
    """
    sql = "SELECT count(*) FROM washList  WHERE ticket ='%s';"
    conn = connect_dbase("update.washList", False)
    cursor = conn.cursor()
    campos = ['conid',
              'empresa',
              'estrategia',
              'last',
              'pchange',
              'open',
              'close',
              'low',
              'high',
              'targetprice',
              'div', 'hw52', 'lw52']

    try:
        values = [key['conid'],
                  key['empresa'],
                  key['estrategia'],
                  precio['lastPrice'],
                  precio['priceChange'],
                  precio['openPrice'],
                  precio['prevClosePrice'],
                  precio['lowPrice'],
                  precio['highPrice'],
                  key['Obje'],
                  0, 0, 0]

        cursor.execute(sql % (key['ticket']))
        found = cursor.fetchone()[0]

        if found:
            update_washlist(cursor=cursor, upd=campos, val=values, ticket=key['ticket'])
            conn.commit()
        else:
            insert_washlist(cursor=cursor, upd=campos, val=values, ticket=key['ticket'])
            conn.commit()

    except conn.ProgrammingError as error:
        print("[Mysql error]: {}".format(error))


def connect_avg_price(symbol=None) -> dict:
    """
    @param symbol:
    @return:
    """
    global alock
    avg = dict()
    try:
        # avg = client.avg_price(symbol)
        avg = client.ticker_24hr(symbol=symbol, type="FULL")

    except ClientError as error:
        if error.error_code != -1121:
            print("[binance:: connect_avg_price]: {}".format(error))
            time.sleep(5)

    return avg


def connect_account_snapshot(tipo=None, limit=1, window=5000) -> dict:
    """
    @param tipo:
    @param limit:
    @param window:
    @return:
    """
    global alock

    account = dict()
    try:
        with alock:
            account = client.account_snapshot(type=tipo, limit=limit, recvWindow=window)

        if 'snapshotVos' in account.keys():
            account = account['snapshotVos']

    except ClientError as error:
        if error.error_code == -1003:
            time.sleep(8)
        else:
            print("[binance::connect_account_snapshot: {} {}".format(datetime.now(), error))

    return account


def connect_get_flexible_product_position(current=1, size=10, window=5000) -> dict:
    """
    @param current:
    @param size:
    @param window:
    @return:
    """
    global alock

    account = dict()
    try:
        with alock:
            account = client.get_flexible_product_position(current=current, size=size, recvWindow=window)

    except ClientError as error:
        if error.error_code != -1121:
            print("[binance:: connect_get_flexible_product_position]: {}".format(error))
            time.sleep(5)
    return account


def trade_history(ticket, stime, etime) -> list:
    """
    @param ticket:
    @param stime: tiempo de inicio
    @param etime: tiempo fin
    @return:  retorna los trades realizados maximo en 24 horas(etime - stime)
    """
    global alock
    w_trade = dict()
    try:
        with alock:
            w_trade = client.my_trades(ticket, limit=20, startTime=stime, endTime=etime)
    except ClientError as error:
        if error.error_code != -1003:
            time.sleep(8)
        print("[binance:: trade_history]: {} {}".format(datetime.now(), error))

    time.sleep(0.5)
    return w_trade