from threading import Timer

from bd_conect import *


class portafolio_api_tsw(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def error(self, req_id, errorcode, errorstring, advancedorderrejectjson=" "):
        if errorcode not in (2104, 2106, 2158):
            print("[Error]: ", req_id, " ", errorcode, " ", errorstring, " ", advancedorderrejectjson)

    def nextValidId(self, order_id):
        self.start()

    def updatePortfolio(self, contract: Contract, position: float, marketprice: float, marketvalue: float,
                        averagecost: float, unrealizedpnl: float, realizedpnl: float, accountname: str):
        global xpositions
        xpositions.append({'contractDesc': contract.symbol, 'conid': contract.conId,
                           'currency': contract.currency, 'assetClass': contract.secType,
                           'position': Decimal(position), 'mktPrice': Decimal(marketprice),
                           'mktValue': Decimal(marketvalue), 'avgCost': Decimal(averagecost),
                           'realizedPnl': Decimal(realizedpnl), 'unrealizedpnl': Decimal(unrealizedpnl),
                           'accountname': accountname})

    def start(self):
        self.reqAccountUpdates(True, "")

    def stop(self):
        self.reqAccountUpdates(False, "")
        self.done = True
        self.disconnect()


def positions_account(account_id=None) -> dict:
    global xpositions
    positions, xpositions,  tcos = list(), list(), 0
    in_positions = select_inversion(tipoin='Stock')

    if apilocal['isApiweb'] and ib_sapiweb(apilocal['ib_client']):
        cartera = apilocal['ib_client'].portfolio_account_positions(account_id=apilocal['account'], page_id=0)
        for key in cartera:
            if key['position'] > 0:
                p = dict()
                p['contractDesc'] = key['contractDesc']
                p['unrealizedpnl'] = Decimal(key['unrealizedPnl'])
                p['estrategia'] = 'A99'
                p['position'] = Decimal(key['position'])
                p['mrkprice'] = Decimal(key['mktPrice'])
                p['empresa'] = ' '
                p['sector'] = key['sector'] if 'sector' in key else 'buscar'
                p['ticket'] = key['contractDesc']
                p['deuda'] = 0
                p['conid'] = key['conid']
                p['CosS'] = Decimal(key['avgCost'] * key['position'])
                p['RetS'] = (Decimal(key['mktValue']) - p['CosS']) / p['CosS']
                p['Peso'] = 0
                p['Adiv'] = 0
                p['Obje'] = 0
                tcos += p['CosS']
                """
                @ obtiene la positions anterior, la estrategia y otros valores
                """
                for i in range(len(in_positions)):

                    if in_positions[i]['ticket'] == p['ticket']:
                        p['estrategia'] = in_positions[i]['estrategia']
                        p['empresa'] = key['name'] if 'name' in tuple(key.keys()) else in_positions[i]['empresa']
                        p['Adiv'] = in_positions[i]['dividendo']

                        if in_positions[i]['targetprice'] > 0:
                            p['Obje'] = in_positions[i]['targetprice']
                        else:
                            p['Obje'] = in_positions[i]['hw52']
                        break

                positions.append(p)

    if apilocal['isApiTsw']:
        bill = portafolio_api_tsw()
        bill.connect(apilocal['hostlocal'], apilocal['port'], apilocal['client'])
        Timer(4, bill.stop).start()
        bill.run()

        for i in range(0, len(xpositions)):
            if xpositions[i]['position'] > 0:
                p = dict()
                ticket = xpositions[i]['contractDesc'] if xpositions[i]['assetClass'] == 'STK' \
                    else xpositions[i]['contractDesc'] + ' CRYPTO'
                p['unrealizedpnl'] = Decimal(xpositions[i]['unrealizedpnl'])
                p['contractDesc'] = ticket
                p['estrategia'] = 'A99'
                p['position'] = Decimal(xpositions[i]['position'])
                p['ticket'] = p['contractDesc']
                p['sector'] = key['sector'] if 'sector' in xpositions[i] else 'buscar'

                p['conid'] = xpositions[i]['conid']
                p['deuda'] = 0
                p['CosS'] = Decimal(xpositions[i]['avgCost']) * Decimal(xpositions[i]['position'])
                p['RetS'] = (Decimal(xpositions[i]['mktValue']) - p['CosS']) / p['CosS']

                p['Peso'] = 0
                tcos += p['CosS']
                """
                @ obtiene la positions anterior, la estrategia y otros valores
                """
                for j in range(0, len(in_positions)):
                    if in_positions[j]['ticket'] == p['ticker']:
                        p['estrategia'] = in_positions[j]['estrategia']
                        p['empresa'] = in_positions[j]['empresa']
                        p['Adiv'] = in_positions[j]['dividendo']
                        p['Obje'] = in_positions[j]['objetivo']
                        break

                positions.append(p)
    """
    @ actualiza positions a partir de positions de las API's
    @ previo al calcula el peso de cada activo 
    """
    if positions:
        for pkey in positions:
            pkey['Peso'] = pkey['CosS'] / tcos

        update_inversion(positions=positions, tipo='Stock')
        return positions
    else:
        return in_positions


class Precio_api(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def error(self, req_id, errorcode, errorstring, advancedorderrejectjson=" "):
        if errorcode not in (2104, 2106, 2158):
            print("Error: ", req_id, " ", errorcode, " ", errorstring)

    def nextValidId(self, order_id: int):
        global prkt, mycontract

        self.reqMarketDataType(3)
        if mycontract.symbol in ('BTC CRYPTO', 'ETH CRYPTO', 'BTC', 'ETH'):
            mycontract.symbol = mycontract.symbol[0:3]
            mycontract.secType = "CRYPTO"
            mycontract.exchange = "PAXOS"
            mycontract.currency = "USD"
            self.reqMktData(order_id, mycontract, "165", 0, 0, [])
        else:
            mycontract.secType = "STK"
            mycontract.exchange = "SMART"
            mycontract.currency = "USD"
            self.reqMktData(order_id, mycontract, "165, 456", 0, 0, [])

        time.sleep(.4)
        self.disconnect()

    def tickPrice(self, req_id, ticktype, price, attrib):
        global prkt
        prkt.update({TickTypeEnum.to_str(ticktype): float(price)})

    def tickSize(self, req_id, ticktype, size):
        global prkt
        prkt.update({TickTypeEnum.to_str(ticktype): float(size)})

    def tickString(self, req_id: TickerId, ticktype: TickType, value: str):
        global prkt
        if TickTypeEnum.to_str(ticktype) == 'IB_DIVIDENDS':
            if value != ',,,':
                ibdiv = value.rsplit(",")
                ibdiv[0] = float(ibdiv[0]) if ibdiv[0] != '' else 0
                ibdiv[1] = float(ibdiv[1]) if ibdiv[1] != '' else 0
                ibdiv[3] = float(ibdiv[3]) if ibdiv[3] != '' else 0
                prkt.update({'past12Months': float(ibdiv[0]),
                             'next12Months': float(ibdiv[1]),
                             'nextDate': ibdiv[2],
                             'nextAmount': float(ibdiv[3])})


def datosmarket_api(positions):
    """
    @param positions:
    @return: actualiza tabla washlist con atributos pasados desde las API
    """
    global prkt, mycontract
    sql = "SELECT count(*) FROM washList  WHERE ticket ='%s';"
    conn = connect_dbase("update.washList", False)
    cursor = conn.cursor()
    fieldx = {'last': '31', 'high': '70', 'low': '71', 'change': '82', 'hw52': '7293', 'lw52': '7294',
              'open': '7295', 'close': '7296', 'div': '7286', 'yieldp': '7287', 'exdiv': '7288', 'dvttm': '7672'}

    fieldy = {'last': 'LAST', 'high': 'HIGH', 'low': 'LOW', 'change': 'CHANGE',  'hw52': 'HIGH_26_WEEK',
              'lw52': 'LOW_26_WEEK', 'open': 'OPEN', 'close': 'CLOSE', 'div': 'next12Months', 'yieldp': 'yieldp',
              'exdiv': 'nextDate', 'dvttm': 'past12Months'}
    prkt, p = dict(), dict()
    try:
        apilis = {'MARK_PRICE': '31', 'OPEN': '7295', 'CLOSE': '7296', 'HIGH': '70', 'LOW': '71', 'CHANGE': '82',
                  'HIGH_52_WEEK': '7293', 'LOW_52_WEEK': '7294', 'next12Months': '7286', 'nextDate': '7288'}
        alist = ['MARK_PRICE', 'OPEN', 'CLOSE', 'HIGH', 'LOW', 'CHANGE', 'HIGH_52_WEEK', 'LOW_52_WEEK',
                 'next12Months', 'nextDate']

    except Exception as e:
        print("[error]:", e)

    conid_list = list_ticket(positions)
    mkt_dato = list()
    lcampos = list()
    for key in fieldx:
        lcampos.append(fieldx[key])

    if apilocal['isApiweb']:

        mkt_dato = apilocal['ib_client'].market_data(conids=conid_list, since='1000', fields=lcampos)
        for i in range(len(positions)):
            for j in range(len(mkt_dato)):

                if positions[i]['conid'] == mkt_dato[j]['conid']:
                    campos, values = list(), list()

                    """
                    @ asignacion de valores necesarios para positions
                    """
                    campos.append('conid')
                    values.append(mkt_dato[j]['conid'])
                    campos.append('estrategia')
                    values.append(positions[i]['estrategia'])

                    for key, val in fieldx.items():
                        if val in tuple(mkt_dato[j].keys()):
                            campos.append(key)
                            values.append(mkt_dato[j][val])

                    cursor.execute(sql % (positions[i]['ticket']))
                    found = cursor.fetchone()[0]
                    if found:
                        update_washlist(cursor=cursor, upd=campos, val=values, ticket=positions[i]['ticket'])
                    else:
                        insert_washlist(cursor=cursor, upd=campos, val=values, ticket=positions[i]['ticket'])

                    conn.commit()
                    break

    if apilocal['isApiTsw']:
        precio = Precio_api()
        for key in positions:
            prkt = {'ticket': key['ticket']}
            precio.connect(apilocal['hostlocal'], apilocal['port'], apilocal['client'])
            mycontract = Contract()
            mycontract.symbol = key['ticket']
            precio.run()
            if prkt:
                campos, values = list(), list()
                campos.append('conid')
                values.append(key['conid'])
                for pkey, val in fieldy.items():
                    if val in tuple(prkt.keys()):
                        if val == 'nextDate' and prkt['next12Months'] > 0:
                            fectxt = prkt['nextDate'][0:4] + '-' + prkt['nextDate'][4:6] + '-' + prkt['nextDate'][6:8]
                            valid, fecha = validar_fecha(fecha_str=fectxt)
                            campos.append(pkey)
                            values.append("{:%b %d'%y}".format(fecha))

                            campos.append('yieldp')
                            values.append("{:.1%}".format(prkt['next12Months'] / prkt['CLOSE']))
                        else:
                            if val == 'LAST':
                                campos.append('last')
                                values.append(prkt[val])

                                campos.append('change')
                                values.append(prkt['LAST'] - prkt['OPEN'] if 'OPEN' in tuple(prkt.keys()) else 0)
                            else:
                                campos.append(pkey)
                                values.append(prkt[val])
                    else:
                        if val == 'LAST':
                            campos.append('last')
                            values.append(prkt['CLOSE'] if 'CLOSE' in tuple(prkt.keys()) else 0)

                            campos.append('change')
                            values.append(prkt['CLOSE'] - prkt['OPEN'] if 'OPEN' in tuple(prkt.keys()) else 0)

                cursor.execute(sql % (key['ticket']))
                found = cursor.fetchone()[0]

                if found:
                    update_washlist(cursor=cursor, upd=campos, val=values, ticket=key['ticket'])
                else:
                    insert_washlist(cursor=cursor, upd=campos, val=values, ticket=key['ticket'])
                conn.commit()

    cursor.close()
    conn.close()


class summary_api(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def error(self, req_id, errorcode, errorstring, advancedorderrejectjson=" "):
        if errorcode not in (2104, 2106, 2158):
            print("[Error]: ", req_id, " ", errorcode, " ", errorstring, " ", advancedorderrejectjson)

    def nextValidId(self, order_id):
        global divisa
        self.reqAccountSummary(order_id, "All", "$LEDGER:"+divisa)

    def accountSummary(self, req_id: int, account: str, tag: str, value: str, currency: str):
        global paccount
        super().accountSummary(req_id, account, tag, value, currency)
        paccount.update({tag: float(value) if is_numeric(value) else value})

    def accountSummaryEnd(self, req_id: int):
        super().accountSummaryEnd(req_id)
        self.disconnect()


def account_summary(account_id=None) -> dict:
    global paccount, divisa
    summary = dict()

    paccount = {'acctcode': account_id}
    divisa = 'USD'
    usd = summary_api()
    usd.connect(apilocal['hostlocal'], apilocal['port'], apilocal['client'])
    usd.run()
    summary[divisa]=paccount

    paccount = {'acctcode': account_id}
    divisa = 'BASE'
    base = summary_api()
    base.connect(apilocal['hostlocal'], apilocal['port'], apilocal['client'])
    base.run()
    summary[divisa] = paccount
    return summary


def summary_account_api(account) -> dict:
    """
    @param account:
    @return:  obtiene snapshot de la cuenta id
    """
    global paccount, divisa
    daccount = list()
    if apilocal['isApiweb']:
        daccount = apilocal['ib_client'].portfolio_account_ledger(account_id=account)
    else:
        daccount = account_summary(account_id=account)
        daccount['USD']['netliquidationvalue'] = daccount['USD']['NetLiquidationByCurrency'] \
                                                 if 'NetLiquidationByCurrency' in daccount['USD'] else 0
        daccount["USD"]['cryptocurrencyvalue'] = daccount['USD']['Cryptocurrency'] \
                                                 if 'Cryptocurrency' in daccount['USD'] else 0
        daccount["USD"]['stockmarketvalue'] = daccount['USD']['StockMarketValue'] \
                                                 if 'StockMarketValue' in daccount['USD'] else 0
        daccount["USD"]['unrealizedpnl'] = daccount['USD']['UnrealizedPnL'] \
                                                 if 'UnrealizedPnL' in daccount['USD'] else 0
        daccount["USD"]['realizedpnl'] = daccount['USD']['RealizedPnL'] \
                                                 if 'RealizedPnL' in daccount['USD'] else 0
        daccount["USD"]['dividends'] = daccount['USD']['NetDividend'] \
                                                 if 'NetDividend' in daccount['USD'] else 0
        daccount["USD"]['cashbalance'] = daccount['USD']['CashBalance'] \
                                                 if 'CashBalance' in daccount['USD'] else 0

    return daccount


def trades_api(account_id=None) -> dict:
    """
    @param account_id:  id de la cuenta
    @return:  obtiene trades de 7 días atras
    """
    trades = dict()
    try:
        if apilocal['isApiweb']:
            trades = apilocal['ib_client'].trades(account_id=account_id, days=10)
        else:
            pass

    except EncodingWarning as error:
        print("trades_ap::]: {}".format(error))

    return trades