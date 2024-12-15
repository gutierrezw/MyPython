from api_binance import *
from api_yfinance import *


def actualiza_booktrading_performa(xlist=None, asset=None, account=None, vehiculo=None):
    """
    @param xlist:  list() de symbol's para actualizar en tabla booktrading
    @param asset:  lista de activos y su peso en cartera
    @param account: cuentaid, donde se actualizará la tabla booktrading
    @param vehiculo: tipo de activo a tratar
    @return: Actualiza booktrading en funcion de últimas operaciones de trading
    """
    if xlist:
        for ticket in xlist:
            utrading = select_booktrading(accion='timestamp',  account=account, idivisa='USD')
            ifecha = utrading[0]['fechahora']
            ifecha += timedelta(days=-2)

            efecha = ifecha
            ltrade = list()

            hoy = datetime.now()
            while efecha <= hoy:
                efecha += timedelta(days=1)
                sfecha = efecha
                sfecha += timedelta(days=-1)

                stime = int(sfecha.timestamp() * 1000)
                etime = int(efecha.timestamp() * 1000)
                field = {'symbol': 'simbolo', 'id': 'idtrans', 'qty': 'cantidad', 'price': 'preciotrans',
                         'quoteQty': 'producto', 'commission': 'tarifacomision', 'time': 'fechahora'}

                w_trade = trade_history(ticket, stime, etime)
                if w_trade:
                    for i in range(len(w_trade)):

                        values = dict()
                        values.update({'categoria': vehiculo})
                        values.update({'divisa': 'USD'})
                        values.update({'cuenta': account})

                        for keys, vals in w_trade[i].items():
                            if keys in field.keys():
                                if keys == 'qty':
                                    qty = Decimal(vals)
                                    values.update({field[keys]: qty if w_trade[i]['isBuyer'] else - qty})

                                if keys == 'quoteQty':
                                    quoteqty = Decimal(vals)
                                    values.update({field[keys]: quoteqty if w_trade[i]['isBuyer'] else - quoteqty})

                                if keys == 'id':
                                    values.update({field[keys]: str(vals)})

                                if keys == 'price':
                                    price = Decimal(vals)
                                    values.update({field[keys]: price})
                                    values.update({'preciocierre': price})

                                if keys == 'commission':
                                    """
                                    @ convierte tarifacomision en USDT, vienen en funcion de cantidad de token
                                    """
                                    commission = Decimal(vals) * values['preciotrans']
                                    values.update({'tarifacomision': commission})

                                if keys == 'time':
                                    values.update({'fechahora': datetime.fromtimestamp(vals / 1000)})

                        insert_booktrading(values, symbol=ticket)
        # gwi001
        # sacar este metodo ya que debe reemplazar por el calculo que da la tabla diaria_performance()
        # actualiza_performa_inversion(xlist=xlist, asset=asset, account=account, vehiculo=vehiculo)


def performa_asset(account=None, vehiculo=None, tipo=None, asset=None) -> pd.DataFrame():
    """
    @param account:  identifica cuentaid
    @param vehiculo:  identifica tipo cálculo para el activo (Crypto, Stock..)
    @param tipo:  identifica tipo de acción portafolio o activo individual
    @param asset: list() de symbol's
    @return: Dataframe historica del performa para el tipo de activo
    """
    #
    #
    datos = pd.DataFrame()
    try:
        symbol, rtn_index, cum_index, index_ref = vehiculo_parm(vehiculo=vehiculo)
        columnas = ['Date', 'p_referencia', 'p_vehiculo', 'nr_gyp', 'value', 'costo_base']
        sql = select_performa_inversion(account=account, vehiculo=vehiculo)
        d_datos = {columnas: columna for columnas, columna in zip(columnas, zip(*sql[0]))}
        #
        # obtiene DataFrame para portafolios
        if tipo in ('Stock', 'Crypto'):
            if sql:
                datos = pd.DataFrame(d_datos, index=d_datos['Date'])
                datos[index_ref] = (1 + datos['p_referencia']).cumprod() - 1
                if vehiculo == 'Crypto':
                    datos['++ index'] = (1 + datos['p_vehiculo']).cumprod()

                if vehiculo == 'Stock':
                    datos['++ index'] = (1 + datos['p_vehiculo']).cumprod() - 1


        # obtiene DataFrame para un activo que esté en la tabla diaria
        #
        if tipo == 'token':
            wperf = pd.DataFrame(d_datos, index=d_datos['Date'])
            cols = ['nr_gyp', 'value', 'p_vehiculo', 'costo_base']
            wperf = wperf.drop(cols, axis=1)

            (diaria, iy) = select_diaria_performance(account=account, symbol=asset)

            pdatos = pd.DataFrame(diaria, columns=iy)
            cols = ['id', 'account', 'cantidad', 'gyp_dia', 'comisiones', 'symbol']
            pdatos = pdatos.drop(cols, axis=1)

            datos = pd.merge(pdatos, wperf, on='Date', how='inner')
            datos.set_index('Date', inplace=True)
            datos[index_ref] = (1 + datos['p_referencia']).cumprod() - 1
            datos['retorno'] = datos['AdjClose'].pct_change()
            datos['++ index'] = (1 + datos['retorno']).cumprod()

        return datos

    except EncodingWarning as error:
        print("performa_asset()]: {}".format(error))


def dict_peso_positions(vehiculo=None) -> dict:
    """
    @param vehiculo: tipo de activo
    @return: obtiene dict y lista con cos asset y pesos respectivos den portafolio
    """
    positions = select_inversion(tipoin=vehiculo, ticket='hist')
    asset, xlist = dict(), list()
    for keys in positions:
        ticket = keys['ticket'].replace("USDT", "-USD")
        asset[ticket] = keys['peso']
        xlist.append(keys['ticket'])

    return asset, xlist


def diaria_book_performance(account=None, vehiculo=None, asset=None):
    """
    @param account:
    @param vehiculo:
    @param asset:
    @return:
    """

    def expande_book(row, stock, cant, basic, gyp, fee, keys, index, account):

        value = row['Adj Close'] * stock
        costo = basic * stock

        if costo > 0:
            nr_gyp = value - costo
            perf = nr_gyp / costo

        if (costo <= 0) and (gyp != 0):
            nr_gyp = .0
            costo = basic * abs(cant)
            perf = (gyp / costo) if x_cost > 0 else .0

        values = dict()
        values.update({'account': account})
        values.update({'Date': index.date()})
        values.update({'AdjClose': row['Adj Close']})
        values.update({'value': value})
        values.update({'cantidad': stock})
        values.update({'costo_base': costo})
        values.update({'performa': perf})
        values.update({'gyp_dia': gyp})
        values.update({'nr_gyp': nr_gyp})
        values.update({'comisiones': fee})
        insert_diaria_performance(values=values, symbol=keys)

    # itera para recorrer los activos de inversión e insertar performance dia(s) anteriores
    #
    try:
        for keys in asset:
            book = select_booktrading(accion='last', account=account, symbol=keys)
            if book:
                diaria, ix = select_diaria_performance(accion='last', account=account, symbol=keys)
                f_desde = diaria[ix.index('Date')] if diaria else book[0]['fechahora'].date()
                f_desde = f_desde + timedelta(days=1)
                f_hasta = datetime.now().date()
                f_fin = f_hasta - timedelta(days=1)
                #
                # f_desde debe ser menor a f_hasta - de lo contario no hay diaria
                # print('diaria=', keys, f_desde, f_hasta, diaria)
                if f_desde < f_hasta:
                    stock = float(book[0]['stock'])
                    basic = float(book[0]['basico'])
                    cant = float(book[0]['cantidad'])
                    gyp = float(book[0]['gprealizadas'])
                    fee = float(book[0]['tarifacomision'])

                    activo, datos = get_yfinance(ticket=keys, vehiculo='download', desde=f_desde, hasta=f_hasta)
                    if not datos.empty:
                        for index, row in datos.iterrows():
                            expande_book(row, stock, cant,  basic, gyp, fee, keys, index, account)
        #
        #  finalizada update de la diaria, se procede con la actualización de performa_inversión
        new_actualiza_performa_inversion(account=account, vehiculo=vehiculo)

    except EncodingWarning as error:
        print("diaria_book_performance()]: {}".format(error))


def new_actualiza_performa_inversion(account=None, vehiculo=None):
    """
    @param account:  cuenta asociada a los activos en cuestión
    @param vehiculo: Crypto, Stock
    @return: inserta en performa_inversiones desempeño del indice y los activos de la cartera
    """
    def buscar_rendimiento_anterior(f_desde):
        f_inicio = f_desde - timedelta(days=5)
        (diaria, iy) = select_diaria_performance(account=account, date=f_inicio, accion='desde')

        datos = pd.DataFrame(diaria, columns=iy)
        datos.set_index('Date', inplace=True)
        pdatos = datos.groupby('Date')[['value', 'gyp_dia', 'nr_gyp', 'costo_base', "performa"]].sum().reset_index()
        # pdatos['performa'] = pdatos['nr_gyp'] / pdatos['costo_base']
        pdatos['retorno'] = pdatos['performa'].pct_change()
        #
        # retorna valores ultima fila
        retorno = pdatos.iloc[-1]['retorno']
        value = pdatos.iloc[-1]['value']
        costo = pdatos.iloc[-1]['costo_base']
        gyp_dia = pdatos.iloc[-1]['gyp_dia']
        nr_gyp = pdatos.iloc[-1]['nr_gyp']

        return gyp_dia, nr_gyp, value, costo, retorno

    def update(account, vehiculo, date, gyp_dia, nr_gyp, value, costo, p_referencia, p_vehiculo):

        values = dict()
        values.update({'idcuenta': account})
        values.update({'vehiculo': vehiculo})
        values.update({'fechaclose': date})
        values.update({'referencia': index_ref})
        values.update({'p_referencia': p_referencia})
        values.update({'p_vehiculo': p_vehiculo})
        values.update({'gyp_dia': gyp_dia})
        values.update({'nr_gyp': nr_gyp})
        values.update({'value': value})
        values.update({'costo_base': costo})

        insert_performa_inversion(values)

    try:
        (last_update, ix) = select_performa_inversion(account=account, vehiculo=vehiculo, accion='last')
        if last_update:
            p_anterior = last_update[ix.index('p_vehiculo')]
            i_anterior = last_update[ix.index('p_referencia')]
            l_fecha = last_update[ix.index('fechaclose')]

            f_desde = l_fecha + timedelta(days=1)
            #
            # ejecuta siempre con fecha menor a current.date()
            if f_desde < datetime.now().date():
                print('new_actualiza_performa_inversion()', f_desde, '<',  datetime.now().date())
                #
                # cálculo de performa del index, alineado a como se carga masivamente la tabla inversiones
                # performa
                (p_referencia, rtn_index, cum_index, index_ref) = get_index_performa(vehiculo=vehiculo, date=f_desde)
                #
                # cálculo de performa del vehículo, alineado a como se carga masivamente la tabla inversiones
                (gyp_dia, nr_gyp, value, costo, p_vehiculo) = buscar_rendimiento_anterior(f_desde)

                print('vehiculo fecha=', f_desde, p_vehiculo, gyp_dia, nr_gyp, value, costo)
                update(account, vehiculo, f_desde, gyp_dia, nr_gyp, value, costo, p_referencia, p_vehiculo)

    except EncodingWarning as error:
        print("new_actualiza_performa_inversion()]: {}".format(error))

