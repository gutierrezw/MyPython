from Class_debugging import ManagerEvents, MangerAfterEvents, Debugging
from Class_DataFrame import (
    char_estrategia,
    setup_fear_greed,
    grupo_sector,
    grupo_dividendo,
    InfoYfinance,
    sectores,
    Agente_income_Manager,
    grupo_region,
    CacheHut,
)
from API_vehiculos import BB, IB
from Class_gestion import GestionInversion
from Modulos_Mysql import (
    EstrategiaInversion,
    PlanInversion,
    MarketScreen,
    RepositorioOportunidadesBuySell,
    BDsystem,
)
from Modulos_Utilitarios import (
    style_app,
    spaces,
    convierte_ticket_crypto,
    sort_positions,
    buscar_ticker,
    meses_list,
    W,
    is_null,
    is_vacio,
    is_numeric,
    str_float,
)
from Class_customer import (
    CustomTreeview,
    MyWebsocket,
    MyMessageBox,
    DataHub,
    TickerInfo,
    MyOrders,
    WidgetVehiculo,
)
from Modulos_python import (
    tk,
    ttk,
    datetime,
    threading,
    Figure,
    FigureCanvasTkAgg,
    time,
    json,
    timedelta,
    pd,
    plt,
    animation,
    itemgetter,
    schedule,
    logging,
    mpatches,
    ticker,
)
from Class_FondosInversion import ArsFondosInversion
from Class_Screener import Screener
from Class_DashBot import AsistenteChatbot


# class para manipular vehiculo
class DatosVehivulo(TickerInfo, MyOrders):
    def __init__(self, account, vehiculo):
        MyOrders.__init__(self, account, vehiculo)
        TickerInfo.__init__(self, account, vehiculo)

        # comparte lista de procesos Datahub
        self.procesos = DataHub.procesos
        self.orders = DataHub.orders
        self.account_fiat = "ARS-0001"
        self.colors = DataHub.colors

        self.ti = 30
        self.itera = 0
        self.WsStock = None

        # Accesos MySql ---------------------------------------------------------------------------------------------------------
        self.Market = MarketScreen()
        self.RepositorioOportunidades = RepositorioOportunidadesBuySell()

        # Programa la tarea comunes todos los vehiculos -------------------------------------------------------------------------
        RemoteOrder = f"schedule_order_remote({self.vehiculo})"
        oportunidad = f"schedule_oportunidades({self.vehiculo})"
        operativo = f"schedule_operativo({self.vehiculo})"
        diario = f"schedule_diario({self.vehiculo})"
        trader = f"schedule_trader({self.vehiculo})"

        # planifiaciones DataHub
        DataHub.manager_events.register_job(
            name=operativo,
            interval_sec=60,
            func=self.schedule_operativo,
        )
        DataHub.manager_events.register_job(
            name=oportunidad,
            interval_sec=15,
            func=self.schedule_oportunidades,
        )
        DataHub.manager_events.register_job(
            name=trader,
            interval_sec=140,
            func=self.schedule_trader,
        )
        DataHub.manager_events.register_job(
            name=diario,
            interval_sec=10800,
            func=self.schedule_diario,
        )
        DataHub.manager_events.register_job(
            name=RemoteOrder,
            interval_sec=1,
            func=self.schedule_order_remote,
        )

    # Actualiza el diccionario DataHub.info[symbol] con el precio recibido
    def update_precio_DataHubInfo(self, symbol=None, conid=None, precio=None):
        with DataHub.lockInfo:
            if symbol in self.info.keys():
                self.info[symbol].update(
                    {
                        "conid": conid,
                        "account": self.account,
                        "vehiculo": self.vehiculo,
                        "websocket": precio[symbol],
                    }
                )

            elif symbol is not None:
                if symbol not in self.info.keys():
                    self.info.update(
                        {
                            symbol: {
                                "conid": conid,
                                "account": self.account,
                                "vehiculo": self.vehiculo,
                                "websocket": precio[symbol],
                            }
                        }
                    )

    # temporal para unificar parametros de entrada
    def on_message_binance_websocket(self, _, message):
        # captura de evento de precio
        def procesa_stream_crypto(x_message):
            try:
                symbol, conid, d_precio = None, None, {}
                if "e" in x_message.keys():

                    symbol = x_message["s"]
                    timestamp = x_message["E"] / 1000  # Convertir a segundos
                    Stimestamp = datetime.fromtimestamp(timestamp).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    d_precio = {
                        symbol: {
                            "last": float(x_message.get("c", 0)),
                            "open": float(x_message.get("o", 0)),
                            "ask": float(x_message.get("a", 0)),
                            "bid": float(x_message.get("b", 0)),
                            "high": float(x_message.get("h", 0)),
                            "low": float(x_message.get("l", 0)),
                            "timestamp": Stimestamp,
                        }
                    }

                    # obtiene conid para vehículo crypto
                    crypto, found = self.RepositorioOportunidades.select_otros_activos(
                        symbol=symbol
                    )
                    conid = crypto[0]["idcrypto"]

                    # procesa_crypto(symbol, d_precio)
                    if d_precio and ("position" in self.assets[symbol].keys()):
                        wallet = self.assets[symbol]["position"]

                        stock = wallet["netAsset"] + wallet["borrowed"]
                        last = d_precio[symbol]["last"]

                        struct = dict()
                        struct["useraccount"] = self.account
                        struct["costobase"] = float(crypto[0]["avgcost"]) * stock
                        struct["dividendo"] = wallet["rewards"] * last
                        struct["objetivo"] = crypto[0]["objetivo"]
                        struct["mrkprice"] = last
                        struct["position"] = stock
                        struct["mktvalue"] = last * stock
                        struct["ticket"] = symbol
                        struct["sector"] = "Crypto activo"
                        struct["deuda"] = wallet["debit USDT"]
                        struct["conid"] = crypto[0]["idcrypto"]
                        struct["open"] = d_precio[symbol]["open"]
                        struct["peso"] = 0.0
                        struct["dgyp"] = (last - struct["open"]) * stock
                        struct["unrealizedpnl"] = (
                            struct["mktvalue"] - struct["costobase"]
                        )
                        struct["retorno"] = (
                            struct["unrealizedpnl"] / struct["costobase"]
                            if struct["costobase"] > 0
                            else 0
                        )

                        # actualiza estructura positions y luego treeview para el symbol en cuestión
                        ix = self.update_symbol_en_positions(struct)

                        # agrega precio update a info()
                        self.update_precio_DataHubInfo(
                            symbol=symbol, conid=conid, precio=d_precio
                        )

                    self.WStreams.counter += 1
                    socket = "WebsocketBinanceStream_OnMessage(Crypto)"
                    DataHub.update_self_procesos(
                        proces="widget", tarea=socket, itera=self.WStreams.counter
                    )

            except (EncodingWarning, Exception) as e:
                print("procesa_stream_crypto(): {}".format(e))

        # ubica y almacenar en lista de órdenes: trasladado a get_orders_binance()
        def procesa_orders_crypto(x_message):
            try:
                if "result" in x_message:
                    response, orders = x_message["result"], []
                    if response:
                        for i, order in enumerate(response):

                            found, position = buscar_ticker(
                                self.positions, order["symbol"]
                            )
                            lista = {
                                "account": self.account,
                                "conid": position["conid"],
                                "symbol": order["symbol"],
                                "side": order["side"],
                                "orderType": order["type"],
                                "price": float(order["price"]),
                                "quantity": float(order["origQty"]),
                                "tif": order["timeInForce"],
                                "status": order["status"],
                                "id_order": order["orderId"],
                                "id_enviar": None,
                                "stampPlace": order["time"],
                                "stampSubmit": order["workingTime"],
                            }
                            orders.append(lista)

                        self.orders.update({"Crypto": orders})

                # contabiliza cada iteración
                self.WsClient.counter += 1
                DataHub.update_self_procesos(
                    proces="running",
                    tarea="schedule_WebsocketBinanceApiClient(Crypto)",
                    itera=self.WsClient.counter,
                )

            except EncodingWarning as e:
                print("procesa_orders_crypto(): {}".format(e))

        try:
            data = json.loads(message)

            # captura de evento de precio
            if "e" in data.keys():
                if data["e"] == "24hrTicker":
                    procesa_stream_crypto(data)

            # captura otros eventos id Client: trasladado a get_orders_binance()
            # elif 'id' in data.keys():
            #         if data["id"] == "allOrders_5494febb":
            #            procesa_orders_crypto(data)

        except json.JSONDecodeError or EncodingWarning as error:
            print("[on_message_binance_websocket()]: {}".format(error))
            time.sleep(1)

    # reemplaza  on_message_websocket() de websocket
    def on_message_IBrks_websocket(self, message):
        def procesa_stock(d_precio=None):
            try:
                # ubicado symbol en el mensaje procede con la actualización
                if conid in self.assets.keys():

                    # symbol = self.assets[conid]['symbol']
                    last = d_precio["last"]
                    change = d_precio["change"]
                    xopen = d_precio["open"]
                    stock = d_precio["stock"]
                    costo = d_precio["costobase"]

                    # ver si puedo tomar esta información del message
                    stock = self.assets[conid]["position"] if stock == 0.0 else stock
                    costo = self.assets[conid]["costobase"] if costo == 0.0 else costo
                    amount = self.assets[conid]["amount_div"]
                    objetivo = self.assets[conid]["objetivo"]
                    unrealizedpnl = self.assets[conid]["unrealizedpnl"]

                    struct = {}
                    struct["useraccount"] = self.account
                    struct["costobase"] = costo
                    struct["dividendo"] = amount * stock
                    struct["objetivo"] = objetivo
                    struct["mrkprice"] = last
                    struct["position"] = stock
                    struct["mktvalue"] = last * stock
                    struct["ticket"] = symbol
                    struct["deuda"] = 0.0
                    struct["conid"] = conid
                    struct["open"] = xopen
                    struct["peso"] = 0.0
                    struct["dgyp"] = change * stock
                    struct["unrealizedpnl"] = struct["mktvalue"] - struct["costobase"]
                    struct["retorno"] = (
                        (struct["unrealizedpnl"] / costo) if costo > 0 else 0
                    )

                    # actualiza estructura positions y luego treeview para el symbol en cuestión
                    ix = self.update_symbol_en_positions(struct)

            except EncodingWarning as e:
                print("[procesa_stock()]: {}".format(e))

        def decodifica_message_websocket(x_message):
            try:
                ix = {
                    "last": "31",
                    "symbol": "55",
                    "change": "82",
                    "bid": "84",
                    "ask": "86",
                    "stock": "76",
                    "open": "7295",
                    "close": "7296",
                    "high": "70",
                    "low": "71",
                    "empresa": "7051",
                    "costobase": "7292_raw",
                }

                x_conid, x_symbol, x_dato = None, None, {}
                if "conidEx" in x_message.keys():

                    x_conid = x_message["conidEx"]
                    if x_conid not in self.conid_inicio.keys():
                        self.conid_inicio.update(
                            {
                                x_conid: {
                                    "symbol": None,
                                    "empresa": None,
                                    "last": 0.0,
                                    "change": 0.0,
                                    "open": 0.0,
                                    "close": 0.0,
                                    "bid": 0.0,
                                    "ask": 0.0,
                                    "costobase": 0.0,
                                    "stock": 0.0,
                                }
                            }
                        )

                    if ix["empresa"] in x_message.keys():
                        self.conid_inicio[x_conid].update(
                            {"empresa": x_message[ix["empresa"]]}
                        )

                    if ix["symbol"] in x_message.keys():
                        self.conid_inicio[x_conid].update(
                            {"symbol": x_message[ix["symbol"]]}
                        )

                    if ix["last"] in x_message.keys():
                        if is_numeric(x_message[ix["last"]]):
                            self.conid_inicio[x_conid].update(
                                {"last": float(x_message[ix["last"]])}
                            )

                    if ix["change"] in x_message.keys():
                        if is_numeric(x_message[ix["change"]]):
                            self.conid_inicio[x_conid].update(
                                {"change": float(x_message[ix["change"]])}
                            )

                    if ix["open"] in x_message.keys():
                        if is_numeric(x_message[ix["open"]]):
                            self.conid_inicio[x_conid].update(
                                {"open": float(x_message[ix["open"]])}
                            )

                    if ix["close"] in x_message.keys():
                        if is_numeric(x_message[ix["close"]]):
                            self.conid_inicio[x_conid].update(
                                {"close": float(x_message[ix["close"]])}
                            )

                    if ix["bid"] in x_message.keys():
                        if is_numeric(x_message[ix["bid"]]):
                            self.conid_inicio[x_conid].update(
                                {"bid": float(x_message[ix["bid"]])}
                            )

                    if ix["ask"] in x_message.keys():
                        if is_numeric(x_message[ix["ask"]]):
                            self.conid_inicio[x_conid].update(
                                {"ask": float(x_message[ix["ask"]])}
                            )

                    high = x_message.get(ix["high"], 0)
                    if is_numeric(high):
                        self.conid_inicio[x_conid].update({"high": float(high)})

                    low = x_message.get(ix["low"], 0)
                    if is_numeric(low):
                        # fix: update 'low' with the correct low value instead of mistakenly using high
                        self.conid_inicio[x_conid].update({"low": float(low)})

                    if ix["costobase"] in x_message.keys():
                        if is_numeric(x_message[ix["costobase"]]):
                            self.conid_inicio[x_conid].update(
                                {"costobase": float(x_message[ix["costobase"]])}
                            )

                    if ix["stock"] in x_message.keys():
                        if is_numeric(x_message[ix["stock"]]):
                            self.conid_inicio[x_conid].update(
                                {"stock": float(x_message[ix["stock"]])}
                            )

                    timestamp = x_message["_updated"] / 1000  # Convertir a segundos
                    Stimestamp = datetime.fromtimestamp(timestamp).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                    # copia dict para
                    x_precio = self.conid_inicio[x_conid].copy()
                    x_precio.update({"timestamp": Stimestamp})
                    x_symbol = self.conid_inicio[x_conid]["symbol"]

                    x_dato.update({x_symbol: x_precio})

                return x_dato, x_conid, x_symbol
            except (
                Exception,
                ValueError,
                Warning,
                EncodingWarning,
                SyntaxWarning,
            ) as e:
                print("[decodifica_message_websocket()]: {} {}".format(e, x_dato))

        try:
            data = json.loads(message)

            # captura precios
            if data["topic"].startswith("smd"):
                n_precio, conid, symbol = decodifica_message_websocket(data)

                # agrega precio info() y contabiliza DataHub
                if n_precio:
                    self.update_precio_DataHubInfo(
                        symbol=symbol, conid=conid, precio=n_precio
                    )
                    procesa_stock(d_precio=n_precio[symbol])

                    # cuenta las iteraciones websocket stock
                    self.WsStock.counter += 1

                    socket = f"WebsocketStream_OnMessage({self.vehiculo})"
                    DataHub.update_self_procesos(
                        proces="widget", tarea=socket, itera=self.WsStock.counter
                    )

            elif not data["topic"].startswith("prefijo"):
                # print(f"data=={data}")
                pass

        except Exception as error:
            print("[on_message_IBrks_websocket({})]: {}".format(self.vehiculo, error))
            time.sleep(1)

    # actualiza self.positions
    def update_symbol_en_positions(self, struct):
        def update_position():
            try:
                position["unrealizedpnl"] = struct["unrealizedpnl"]
                position["useraccount"] = struct["useraccount"]
                position["dividendo"] = struct["dividendo"]
                position["costobase"] = struct["costobase"]
                position["mrkprice"] = struct["mrkprice"]
                position["position"] = struct["position"]
                position["mktvalue"] = struct["mktvalue"]
                position["objetivo"] = struct["objetivo"]
                position["retorno"] = struct["retorno"]
                position["deuda"] = struct["deuda"]
                position["conid"] = struct["conid"]
                position["open"] = struct["open"]
                position["dgyp"] = struct["dgyp"]
                position["gypp"] = (
                    struct["position"] * struct["objetivo"] - struct["costobase"]
                )
                position["v_prc"] = 0.0
                position["v_gan"] = 0.0

                # rescribe el peso de la position
                position["peso"] = position["costobase"] / self.update_peso_position()
            except EncodingWarning as e:
                print("[update_position({})]: {}".format(self.vehiculo, e))

        try:
            (
                ix,
                symbol,
            ) = (
                -1,
                struct["ticket"],
            )
            for ix, position in enumerate(self.positions[:]):
                if position["ticket"] == symbol:
                    update_position()
                    break
            return ix
        except EncodingWarning as e:
            print("[update_symbol_en_positions({})]: {}".format(self.vehiculo, e))

    # calcula peso de symbols dentro de positions
    def update_peso_position(self):
        try:
            inversion = sum(position["costobase"] for position in self.positions)
            return inversion
        except EncodingWarning as e:
            print("[update_peso_position({})]: {}".format(self.vehiculo, e))

    # mantiene self.position igual a la tabla inversiones
    def update_self_positions(self, in_positions=None):
        try:
            ibook = enumerate(in_positions)
            eof_ibook, i_position = next(ibook, (None, None))

            sbook = enumerate(self.positions)
            eof_sbook, position = next(sbook, (None, None))

            # aparea positions y assets para construir positions actualizada
            while (eof_ibook is not None) and (eof_sbook is not None):

                if position["ticket"] == i_position["ticket"]:
                    eof_ibook, i_position = next(ibook, (None, None))
                    eof_sbook, position = next(sbook, (None, None))
                else:
                    if position["ticket"] > i_position["ticket"]:

                        # inserta position
                        self.positions.append(i_position)
                        eof_ibook, i_position = next(ibook, (None, None))
                    else:
                        # elimina position
                        self.positions.pop(eof_sbook)
                        eof_sbook, position = next(sbook, (None, None))
        except EncodingWarning as e:
            print("[update_positions({})]: {}".format(self.vehiculo, e))

    # almacena en ts_yfinance_symbol information de buy y sell
    def ts_oportunidades_symbol(self, symbol, datos=None):
        try:
            d_buy, d_sell, d_dividends = {}, {}, {}

            # caso actualiza oportunidades sobre info()
            if symbol in self.info.keys():
                if datos is not None:
                    if "sell" in datos.keys():
                        self.info[symbol]["sell"] = datos["sell"]

                    elif "buy" in datos.keys():
                        self.info[symbol]["buy"] = datos["buy"]

                    elif "dividends" in datos.keys():
                        self.info[symbol]["dividends"] = datos["dividends"]

            else:
                if self.vehiculo == "Crypto":
                    key = list(datos.keys())
                    if len(key) > 0:
                        self.info.update({symbol: {key[0]: datos[key[0]]}})

            # siempre return ultima info()
            if symbol in self.info.keys():

                if "buy" in self.info[symbol].keys():
                    d_buy = self.info[symbol]["buy"]

                elif "sell" in self.info[symbol].keys():
                    d_sell = self.info[symbol]["sell"]

                elif "dividends" in self.info[symbol].keys():
                    d_dividends = self.info[symbol]["dividends"]
                    return d_buy, d_dividends

            return d_buy, d_sell
        except EncodingWarning as e:
            print("[ts_oportunidades_symbol()]: {}".format(e))

    # recorre positions para actualizar info() con las oportunidades de sell
    def oportunidades_sell(self):
        def obtiene_lotes(symbol=None):
            nonlocal datos
            try:

                profit, costCum, lotes, sell, datos = 0.0, 0.0, 0.0, 0.0, {}

                last = position["mrkprice"]
                l_gain = DataHub.get_lotesGainLost(
                    opcion="gain", account=self.account, symbol=symbol, last=last
                )

                if l_gain:
                    for lotes, gain in enumerate(l_gain, 1):
                        profit += gain["gyp"]
                        costCum += gain["costo lote"]
                        sell += gain["cantidad"]

                    disponible = sell
                    if self.vehiculo == "Crypto":
                        if symbol in self.assets:
                            max_sell = self.assets[symbol]["position"]["netAsset"]
                            disponible = max_sell if sell > max_sell else sell

                    roi = (profit / costCum) if costCum > 0 else 0
                    datos = {
                        "sell": {
                            "profit": profit,
                            "cantidad lotes": lotes,
                            "cantidad sell": sell,
                            "last": last,
                            "costoCum": costCum,
                            "roi": roi,
                            "costobase": position["costobase"],
                            "position": position["position"],
                            "disponible": disponible,
                        }
                    }
                return datos
            except Exception as error:
                print("[obtiene_lotes()]: {}".format(error))

        try:
            for position in self.positions:
                symbol = position["ticket"]
                datos = obtiene_lotes(symbol=symbol)

                # actualiza en diccionario self.info()
                (d_buy, d_sell) = self.ts_oportunidades_symbol(symbol, datos)
        except Exception as e:
            print("[oportunidades_sell()]: {}".format(e))

    # recorre positions para actualizar oportunidades buy general
    def oportunidades_buy(self):
        try:
            invertir = self.sesion["Pinvertir"]
            for position in self.positions:
                symbol = position["ticket"]

                if (
                    (position["mrkprice"] > 0.000001)
                    and (invertir > 0)
                    and (position["position"] > 0)
                ):
                    stock = int(invertir / position["mrkprice"])
                    stockNew = stock + position["position"]
                    avgCost = position["costobase"] / position["position"]
                    dividendo = position["dividendo"] / position["position"]
                    gypInicial = (
                        position["objetivo"] - avgCost + dividendo
                    ) * position["position"]
                    precioNew = (
                        position["costobase"] + stock * position["mrkprice"] + 0.4
                    ) / stockNew

                    gypPrecio = (precioNew - avgCost) / avgCost if avgCost > 0 else 0
                    gypProyect = (
                        position["objetivo"] - precioNew + dividendo
                    ) * stockNew
                    gainInversion = (gypProyect - gypInicial) / invertir

                    datos = {}
                    if (
                        (gypPrecio < -0.001)
                        and (gainInversion < 100)
                        and (position["dividendo"] == 0)
                    ):
                        datos = {
                            "buy": {
                                "ganancia precio": gypPrecio,
                                "ganancia inversión": gainInversion,
                                "cantidad buy": stock,
                                "last": position["mrkprice"],
                                "avgcost": avgCost,
                                "cantidad post": stockNew,
                                "avgCost post": precioNew,
                                "retorno post": gypProyect,
                                "objetivo": position["objetivo"],
                                "pre dividendos": position["dividendo"],
                                "post dividendos": dividendo * stockNew,
                                "pre costobase": position["costobase"],
                                "post costobase": precioNew * stockNew,
                            }
                        }

                    # actualiza en diccionario self.info()
                    (d_buy, d_sell) = self.ts_oportunidades_symbol(symbol, datos)
        except EncodingWarning as e:
            print("[oportunidades_buy()]: {}".format(e))

    # recorre positions para actualizar info() oportunidades dividends
    def oportunidades_dividends(self):
        try:
            invertir = self.sesion["Pinvertir"]
            for position in self.positions:
                symbol = position["ticket"]

                if (
                    position["mrkprice"] > 0.000001
                    and invertir > 0
                    and position["position"] > 0
                ):
                    stock = int(invertir / position["mrkprice"])
                    stockNew = stock + position["position"]
                    avgCost = position["costobase"] / position["position"]
                    dividendo = position["dividendo"] / position["position"]
                    gypInicial = (
                        position["objetivo"] - avgCost + dividendo
                    ) * position["position"]
                    precioNew = (
                        position["costobase"] + stock * position["mrkprice"] + 0.4
                    ) / stockNew

                    gypPrecio = (precioNew - avgCost) / avgCost if avgCost > 0 else 0
                    gypProyect = (
                        position["objetivo"] - precioNew + dividendo
                    ) * stockNew
                    gainInversion = (gypProyect - gypInicial) / invertir

                    datos = {}
                    # if (gypPrecio < -0.001) and (position['dividendo'] > 0):
                    if position["dividendo"] > 0:

                        tasa_efectiva = (
                            position["dividendo"] / position["costobase"]
                            if position["costobase"] > 0
                            else 0
                        )
                        tasa_nominal = position["dividendYield"] / 100
                        ex_dividends = position["exDividendDate"].strftime("%d-%b'%y")

                        datos = {
                            "dividends": {
                                "ganancia precio": gypPrecio,
                                "ganancia inversión": gainInversion,
                                "cantidad buy": stock,
                                "last": position["mrkprice"],
                                "avgcost": avgCost,
                                "cantidad post": stockNew,
                                "avgCost post": precioNew,
                                "retorno post": gypProyect,
                                "objetivo": position["objetivo"],
                                "dividendYield": tasa_nominal,
                                "YieldEfectiva": tasa_efectiva,
                                "exDividendDate": ex_dividends,
                                "pre dividendos": position["dividendo"],
                                "post dividendos": dividendo * stockNew,
                                "pre costobase": position["costobase"],
                                "post costobase": precioNew * stockNew,
                            }
                        }

                    # actualiza en diccionario self.info()
                    (d_buy, d_dividend) = self.ts_oportunidades_symbol(symbol, datos)
        except EncodingWarning as e:
            print("[oportunidades_dividends()]: {}".format(e))

    # recorre positions para actualizar info() oportunidades por sector y dividends
    def oportunidades_sector(self):
        try:
            invertir = self.sesion["Pinvertir"]
            orden = [{"Sector": "sector"}, "DES"]
            cartera = sort_positions(self.positions, orden)

            for position in cartera:
                symbol = position["ticket"]

                if (
                    position["mrkprice"] > 0.000001
                    and invertir > 0
                    and position["position"] > 0
                ):
                    stock = int(invertir / position["mrkprice"])
                    stockNew = stock + position["position"]
                    avgCost = position["costobase"] / position["position"]
                    dividendo = position["dividendo"] / position["position"]
                    gypInicial = (
                        position["objetivo"] - avgCost + dividendo
                    ) * position["position"]
                    precioNew = (
                        position["costobase"] + stock * position["mrkprice"] + 0.4
                    ) / stockNew

                    gypPrecio = (precioNew - avgCost) / avgCost if avgCost > 0 else 0
                    gypProyect = (
                        position["objetivo"] - precioNew + dividendo
                    ) * stockNew
                    gainInversion = (gypProyect - gypInicial) / invertir

                    datos = {}
                    # if (gypPrecio < -0.001) and (position['dividendo'] > 0):
                    if position["dividendo"] > 0:

                        tasa_efectiva = position["dividendo"] / position["costobase"]
                        tasa_nominal = position["dividendYield"] / 100
                        ex_dividends = position["exDividendDate"].strftime("%d-%b'%y")

                        datos = {
                            "sector": {
                                "ganancia precio": gypPrecio,
                                "ganancia inversión": gainInversion,
                                "cantidad buy": stock,
                                "last": position["mrkprice"],
                                "avgcost": avgCost,
                                "cantidad post": stockNew,
                                "avgCost post": precioNew,
                                "retorno post": gypProyect,
                                "objetivo": position["objetivo"],
                                "dividendYield": tasa_nominal,
                                "YieldEfectiva": tasa_efectiva,
                                "exDividendDate": ex_dividends,
                                "pre dividendos": position["dividendo"],
                                "post dividendos": dividendo * stockNew,
                                "pre costobase": position["costobase"],
                                "post costobase": precioNew * stockNew,
                            }
                        }

                    # actualiza en diccionario self.info()
                    (d_buy, d_dividend) = self.ts_oportunidades_symbol(symbol, datos)
        except EncodingWarning as e:
            print("[oportunidades_dividends()]: {}".format(e))

    # captura operaciones compra y ventas de activos
    def trader_api_vehiculo(self):
        # obtiene trader para las Cryptos
        def trader_binance():
            try:
                if self.activos:

                    # extrae trader mas reciente en la cuenta
                    if DataHub.ultimoTraderCrypto is None:
                        utrading, ix = self.RepositorioOportunidades.select_booktrading(
                            accion="timestamp", account=self.account, idivisa="USD"
                        )
                        DataHub.ultimoTraderCrypto = utrading[0]["fechahora"]

                    hoy = datetime.now()

                    # explora sobre los activos de la cuenta y ultima fecha
                    for ticket in self.activos:
                        efecha = DataHub.ultimoTraderCrypto - timedelta(days=-1)
                        ltrade = []

                        while efecha <= hoy:
                            efecha += timedelta(days=1)
                            sfecha = efecha
                            sfecha += timedelta(days=-1)

                            stime = int(sfecha.timestamp() * 1000)
                            etime = int(efecha.timestamp() * 1000)

                            w_trade = []
                            if etime > stime:
                                w_trade = self.BClient.get_my_trades(
                                    ticket, limit=20, startTime=stime, endTime=etime
                                )
                                if w_trade:
                                    for i in range(len(w_trade)):
                                        try:
                                            registro = dict()
                                            if w_trade[i]:

                                                registro.update(
                                                    {"categoria": self.vehiculo}
                                                )
                                                registro.update({"divisa": "USD"})
                                                registro.update(
                                                    {"cuenta": self.account}
                                                )

                                                qty = float(w_trade[i].get("qty", 0.0))
                                                qty = (
                                                    qty
                                                    if w_trade[i]["isBuyer"]
                                                    else -1 * qty
                                                )
                                                quoteqty = float(
                                                    w_trade[i].get("quoteQty", 0.0)
                                                )
                                                registro.update({"cantidad": qty})
                                                registro.update({"producto": quoteqty})

                                                price = float(
                                                    w_trade[i].get("price", 0.0)
                                                )
                                                registro.update(
                                                    {
                                                        "idtrans": str(
                                                            w_trade[i].get("id")
                                                        )
                                                    }
                                                )
                                                registro.update({"preciotrans": price})
                                                registro.update({"preciocierre": price})

                                                comision = (
                                                    float(
                                                        w_trade[i].get(
                                                            "commission", 0.0
                                                        )
                                                    )
                                                    * registro["preciotrans"]
                                                )
                                                registro.update(
                                                    {"tarifacomision": comision}
                                                )
                                                registro.update({"mtmgp": 0.00})

                                                fechahora = datetime.fromtimestamp(
                                                    w_trade[i].get("time", 0) / 1000
                                                )
                                                registro.update(
                                                    {"fechahora": fechahora}
                                                )

                                                # valida existencia del trader
                                                found_hashId = self.RepositorioOportunidades.get_hash_booktrading(
                                                    accion="valida",
                                                    values=registro,
                                                    symbol=ticket,
                                                )

                                                if not found_hashId:
                                                    self.RepositorioOportunidades.insert_booktrading(
                                                        values=registro, symbol=ticket
                                                    )
                                        except (ValueError, Exception) as error:
                                            print(
                                                f"Error en w_trade {i} - {w_trade[i]}: {error}"
                                            )
                            # espera para no saturar la API
                            time.sleep(0.8)

                    # Almacena ultima fecha en session que exploro API get_my_trades()
                    if efecha > DataHub.ultimoTraderCrypto:
                        DataHub.ultimoTraderCrypto = hoy + timedelta(days=-1)
            except (EncodingWarning, Exception) as error:
                print("[trader_binance()]: {}".format(error))

        # obtiene orders para las Cryptos
        def get_orders_binance():
            try:
                response = self.BClient.Myget_open_orders()
                if response:
                    orders = []
                    for i, order in enumerate(response):
                        found, position = buscar_ticker(self.positions, order["symbol"])
                        lista = {
                            "account": self.account,
                            "conid": position["conid"],
                            "symbol": order["symbol"],
                            "side": order["side"],
                            "orderType": order["type"],
                            "price": float(order["price"]),
                            "quantity": float(order["origQty"]),
                            "tif": order["timeInForce"],
                            "status": order["status"],
                            "id_order": order["orderId"],
                            "id_enviar": None,
                            "stampPlace": order["time"],
                            "stampSubmit": order["workingTime"],
                        }
                        orders.append(lista)

                    self.orders.update({"Crypto": orders})
            except (EncodingWarning, Exception) as e:
                print(f"get_orders_binance(): {e}")

        # cargas ultimas compras de USDT
        def trade_USDT_diario():
            def get_trader_insert_fiat(trama=None):
                try:
                    fiat, symbol, trader = "ARS", "USDT", []
                    for keys, values in trama.items():
                        if keys == "data":
                            for i, rows in enumerate(values):

                                date = datetime.fromtimestamp(rows["createTime"] / 1000)
                                if (
                                    (rows["tradeType"] == "BUY")
                                    and (rows["orderStatus"] == "COMPLETED")
                                    and (rows["fiat"] == fiat)
                                ):
                                    values = {}

                                    values.update({"categoria": rows["fiat"]})
                                    values.update({"divisa": "USD"})
                                    values.update({"cuenta": rows["fiat"] + "-0001"})
                                    values.update({"fechahora": date})
                                    values.update({"idtrans": rows["advNo"]})
                                    values.update(
                                        {"cantidad": float(rows["takerAmount"])}
                                    )
                                    values.update(
                                        {"preciotrans": float(rows["unitPrice"])}
                                    )
                                    values.update(
                                        {"preciocierre": float(rows["unitPrice"])}
                                    )
                                    values.update(
                                        {"producto": float(rows["totalPrice"])}
                                    )
                                    values.update({"tarifacomision": 0.0})
                                    values.update({"gprealizadas": 0.0})
                                    values.update({"mtmgp": 0.0})
                                    values.update({"codigo": "O"})
                                    trader.append(values)

                    # orden de mas descendete los trader's
                    asc_trader = sorted(
                        trader, key=lambda x: x["fechahora"], reverse=False
                    )

                    # valida los trader antes de insert booktrading
                    for i, registro in enumerate(asc_trader):
                        found_hashId = (
                            self.RepositorioOportunidades.get_hash_booktrading(
                                accion="valida", values=registro, symbol=symbol
                            )
                        )

                        if not found_hashId:
                            self.RepositorioOportunidades.insert_booktrading(
                                values=registro, symbol=symbol
                            )

                    return asc_trader
                except EncodingWarning as error:
                    print(f"get_trader_insert_fiat(): {e}")

            try:
                hasta = datetime.today()
                desde = hasta - timedelta(days=60)
                start_time = int(desde.timestamp() * 1000)
                end_time = int(hasta.timestamp() * 1000)

                response = self.BClient.get_c2c_trade_history(
                    tradeType="BUY", startTimestamp=start_time, endTimestamp=end_time
                )
                if response:
                    x_trader = get_trader_insert_fiat(trama=response)
            except (EncodingWarning, Exception) as e:
                print(f"trade_USDT_diario(): {e}")

        # obtiene orders para las Stock
        def get_orders_iteractive():

            def verifica_status(orden=None):

                # busca orders para symbol contenido en parametro=order
                symbol, iid_order, clientOrderId, now = (
                    order["ticker"],
                    "",
                    order["orderId"],
                    datetime.now(),
                )
                trader, ix = self.RepositorioOportunidades.select_order_trader(
                    account=self.account, symbol=symbol
                )

                if trader:
                    for preOrder in trader:

                        # cuando sea la Orden Cliente y este Inactive -- es cambiado el status
                        iid_order = trader[ix.index("id_order")]

                        if (
                            preOrder[ix.index("clientOrderId")] == clientOrderId
                            and preOrder[ix.index("status")] == "Inactive"
                        ):

                            stamp = order["lastExecutionTime_r"] / 1000
                            values = {
                                "status": trader["status"],
                                "stampSubmit": datetime.fromtimestamp(stamp),
                            }

                            self.RepositorioOportunidades.update_order_trader(
                                account=self.account,
                                values=values,
                                symbol=symbol,
                                orderid=iid_order,
                            )
                            return True, iid_order, clientOrderId

                        # para mostrar las orders del dia
                        elif preOrder[ix.index("stampSubmit")].date() == now.date():

                            return True, id_order, clientOrderId

                # no se cumplió ninguna condición no es mostrada la orden
                return False, id_order, clientOrderId

            # asocia los confirm con las Órdenes almacenadas en la tabla
            def ubica_confirm(
                orden=None, conid=None, orderid=None, account=None, vehiculo=None
            ):
                try:
                    trader, ix = self.RepositorioOportunidades.select_order_trader(
                        account=account, vehiculo=vehiculo, conid=conid
                    )

                    clientOrderId, iid_order = "", ""
                    for keys in trader:

                        # caso que NO está informada la clientOrderId (tabla order_trade)
                        if (
                            keys[ix.index("quantity")] == orden["totalSize"]
                            and keys[ix.index("price")] == float(orden["price"])
                            and keys[ix.index("side")] in orden["orderDesc"].upper()
                            and orden["timeInForce"] == "CLOSE"
                            and (
                                is_null(keys[ix.index("clientOrderId")])
                                or is_vacio(keys[ix.index("clientOrderId")])
                            )
                        ):

                            # obtiene los datos necesarios para establecer relación get_live_orders()
                            symbol = orden["ticker"]
                            iid_order = keys[ix.index("id_order")]
                            values = {"clientOrderId": orden["orderId"]}
                            self.RepositorioOportunidades.update_order_trader(
                                account=account,
                                values=values,
                                symbol=symbol,
                                orderid=iid_order,
                            )

                            return True, values["clientOrderId"], iid_order
                        else:

                            # caso que clientOrderId a la orden activa de la API
                            if is_numeric(keys[ix.index("clientOrderId")]):
                                if (
                                    int(keys[ix.index("clientOrderId")])
                                    == orden["orderId"]
                                ):
                                    return (
                                        True,
                                        orden["orderId"],
                                        keys[ix.index("id_order")],
                                    )
                    return False, clientOrderId, id_order
                except EncodingWarning as e:
                    print("ubica_confirm(): {}".format(e))

            try:
                orders = []
                response = self.IClient.get_live_orders()
                if response:
                    listOrder = response["orders"]
                    for i, order in enumerate(listOrder):
                        insert, id_order, id_enviar = False, "", ""

                        if order["status"] == "Inactive":
                            found, id_order, id_enviar = ubica_confirm(
                                orden=order,
                                conid=order["conid"],
                                orderid=order["orderId"],
                                account=self.account,
                                vehiculo=self.vehiculo,
                            )
                            insert = True if found else False

                        if order["status"] == "Submitted":

                            # verifica si la orden será mostrada en las activas y cambia status
                            insert, id_order, id_enviar = verifica_status(order)

                        # ubica conid para almacenar en lista de órdenes
                        if insert:
                            lista = {
                                "account": self.account,
                                "conid": order["conid"],
                                "symbol": order["ticker"],
                                "side": order["side"],
                                "orderType": order["origOrderType"],
                                "price": order["price"],
                                "quantity": order["totalSize"],
                                "tif": order["timeInForce"],
                                "status": order["status"],
                                "id_order": id_order,
                                "id_enviar": id_enviar,
                                "stampPlace": order["lastExecutionTime_r"],
                                "stampSubmit": " ",
                            }
                            orders.append(lista)

                    # almacena orders activas
                    self.orders.update({"Stock": orders})
            except (EncodingWarning, Exception) as e:
                print("[get_orders_binance()]: {}".format(e))

        # obtiene trader para las acciones
        def trader_iteractive():
            try:
                datos = list()
                trades = self.IClient.trades(account_id=self.account, days=10)
                if trades:
                    for keys in trades:
                        values = {}
                        values.update({"simbolo": keys["symbol"]})
                        values.update({"categoria": "Stock"})
                        values.update({"divisa": "USD"})
                        values.update({"cuenta": keys["accountCode"]})
                        timestamp = int(keys["trade_time_r"] / 1000)
                        values.update({"fechahora": datetime.fromtimestamp(timestamp)})
                        values.update({"idtrans": keys["execution_id"]})

                        values.update({"preciotrans": float(keys["price"])})
                        values.update({"preciocierre": float(keys["price"])})
                        values.update({"tarifacomision": float(keys["commission"])})
                        values.update({"producto": float(keys["net_amount"])})

                        if keys["side"] == "B":
                            values.update({"cantidad": float(keys["size"])})
                            values.update({"gprealizadas": 0.00})
                            values.update({"mtmgp": 0.00})
                            values.update({"codigo": "O"})

                        if keys["side"] == "S":
                            values.update({"cantidad": -float(keys["size"])})
                            values.update({"gprealizadas": 0.00})
                            values.update({"mtmgp": 0.00})
                            values.update({"codigo": "C"})

                        datos.append(values)

                # si no es vaciá - procede con insertar en booktrading
                if datos:
                    datos_ord = sorted(
                        datos,
                        key=itemgetter(
                            "cuenta",
                            "simbolo",
                            "fechahora",
                        ),
                    )

                    for registro in datos_ord:
                        simbolo = registro["simbolo"]
                        values = registro.pop("simbolo")

                        # valida existencia del trader
                        found_hashId = (
                            self.RepositorioOportunidades.get_hash_booktrading(
                                accion="valida", values=registro, symbol=simbolo
                            )
                        )

                        # inserta trade en booktrading
                        if not found_hashId:
                            self.RepositorioOportunidades.insert_booktrading(
                                values=registro, symbol=simbolo
                            )
            except (EncodingWarning, Exception) as e:
                print(f"trader_iteractive(): {e}")

        try:
            if self.vehiculo == "Crypto":
                trade_USDT_diario()
                trader_binance()
                get_orders_binance()

            if self.vehiculo == "Stock":
                get_orders_iteractive()
                trader_iteractive()
        except (Exception, EnvironmentError, ExceptionGroup) as e:
            print(f"trader_api_vehiculo({self.vehiculo}): {e}")

    # declara las api para binance
    def api_vehiculo_binance(self):
        def update_inversion_crypto(api=None, in_positions=None) -> list:
            try:
                x_positions: list[dict] = []

                # ordena por ticket (assets) para el apareamiento
                x_assets: dict = {key: api[key] for key in sorted(api)}
                abook = enumerate(x_assets.items())
                eof_abook, (asset, values) = next(abook, (None, None))

                # ordena por ticket (in_positions) para el apareamiento
                pbook = enumerate(in_positions)
                eof_pbook, position = next(pbook, (None, None))

                # aparea positions y assets para construir positions actualizada
                while (eof_pbook is not None) and (eof_abook is not None):

                    # actualiza position
                    if position["ticket"] == asset:

                        crypto, found = (
                            self.RepositorioOportunidades.select_otros_activos(
                                symbol=asset
                            )
                        )
                        found, self_position = buscar_ticker(self.positions, asset)

                        # obtiene información de dividendos
                        (yf_activo, datos, ind_update) = self.ts_yfinance_symbol(
                            symbol=asset, vehiculo=self.vehiculo
                        )

                        keys_asset = values["position"]
                        position["mrkprice"] = self_position["mrkprice"]
                        position["dgyp"] = self_position["dgyp"]
                        position["open"] = self_position["open"]

                        position["position"] = (
                            keys_asset["borrowed"] + keys_asset["netAsset"]
                        )
                        position["objetivo"] = crypto[0]["objetivo"]
                        position["empresa"] = crypto[0]["descripcion"]
                        position["costobase"] = (
                            crypto[0]["avgcost"] * position["position"]
                        )
                        position["dividendo"] = (
                            keys_asset["rewards"] * position["mrkprice"]
                        )
                        position["mktvalue"] = (
                            position["mrkprice"] * position["position"]
                        )

                        position["unrealizedpnl"] = (
                            position["mktvalue"] - position["costobase"]
                        )

                        if position["costobase"] > 0:
                            position["retorno"] = (
                                position["unrealizedpnl"] / position["costobase"]
                            )
                        else:
                            position["retorno"] = 0
                        position["deuda"] = keys_asset["debit USDT"]

                        # rescribe el peso de la position
                        position["peso"] = (
                            position["costobase"] / self.update_peso_position()
                        )

                        position["region"], position["country"] = (
                            "Global",
                            "Digital",
                        )
                        if "region" in yf_activo:
                            position["region"] = yf_activo["region"]
                        if "country" in yf_activo:
                            position["country"] = yf_activo["country"]

                        x_positions.append(position)

                        eof_abook, (asset, values) = next(abook, (None, (None, None)))
                        eof_pbook, position = next(pbook, (None, None))
                    else:
                        # inserta position
                        if position["ticket"] > asset:
                            p = {}
                            crypto, found = (
                                self.RepositorioOportunidades.select_otros_activos(
                                    symbol=asset
                                )
                            )
                            if not found:
                                crypto, found = (
                                    self.RepositorioOportunidades.insert_otros_activos(
                                        symbol=asset
                                    )
                                )

                            keys_asset = values["position"]
                            p["ticket"] = asset
                            p["empresa"] = crypto[0]["descripcion"]
                            p["sector"] = "Crypto activo"
                            p["conid"] = str(crypto[0]["idcrypto"])
                            p["fealta"] = crypto[0]["fecupdate"].date()
                            p["febaja"] = "9999-12-31"
                            p["iactiva"] = "Y"
                            p["tipoinv"] = "Crypto"
                            p["estrategia"] = "P03"
                            p["exDividendDate"] = "9999-12-31"
                            p["dividendYield"] = 0

                            p["position"] = (
                                keys_asset["borrowed"] + keys_asset["netAsset"]
                            )
                            p["objetivo"] = crypto[0]["objetivo"]
                            p["mrkprice"] = crypto[0]["avgcost"]
                            p["costobase"] = crypto[0]["avgcost"] * p["position"]
                            p["dividendo"] = keys_asset["rewards"] * p["mrkprice"]
                            p["mktvalue"] = p["mrkprice"] * p["position"]

                            p["unrealizedpnl"] = p["mktvalue"] - p["costobase"]
                            p["retorno"] = (
                                p["unrealizedpnl"] / p["costobase"]
                                if p["costobase"] > 0
                                else 0
                            )
                            p["deuda"] = keys_asset["debit USDT"]
                            p["open"] = 0.0
                            p["dgyp"] = 0.0

                            # rescribe el peso de la position
                            p["peso"] = p["costobase"] / self.update_peso_position()

                            p["region"], p["country"] = "Global", "Digital"
                            if "region" in yf_activo:
                                p["region"] = yf_activo["region"]
                            if "country" in yf_activo:
                                p["country"] = yf_activo["country"]

                            x_positions.append(p)

                            eof_abook, (asset, values) = next(abook, (None, None))
                        else:
                            eof_pbook, position = next(pbook, (None, None))

                return x_positions
            except (EncodingWarning, Exception) as e:
                print("update_inversion_crypto(): {}".format(e))

        # obtiene activos de wallet spot y margin
        def get_balance_spot_earn():
            try:
                response = self.crypto_wallet_free(symbol="all")
                if response:
                    symbol = None
                    for asset, keys in response.items():
                        # verifica asset uso corriente
                        if asset == "USDT":
                            cash = keys.get("free", 0)
                            if " Cash       :" in self.resumen.keys():
                                self.resumen[" Cash       :"] = f"{cash:>11.2f}"
                            continue

                        # almacena disponible para cada asset spot
                        elif asset.startswith("LD"):
                            symbol = asset.replace("LD", "") + "USDT"
                            free = keys.get("free", 0)
                            lock = keys.get("locked", 0)
                            netAsset = 0.0

                        # almacena disponible para cada asset margin cruzado
                        elif asset.startswith("MC"):
                            symbol = asset.replace("MC", "") + "USDT"
                            free = keys.get("free", 0)
                            lock = keys.get("lock", 0)
                            netAsset = free

                        # validadación para considerar
                        elif not asset.endswith("UP") and asset.endswith("DOWN"):
                            symbol = asset + "USDT"
                            free = keys.get("free", 0)
                            lock = keys.get("locked", 0)
                            netAsset = 0.0

                            # suma lo que esta lock o en orders activas
                            free += lock
                        else:
                            continue

                        # total free, locked (symbol)
                        if free > 0 or lock > 0:

                            # si existe el symbol en assets, suma lo que tiene
                            if symbol in assets.keys():
                                free += assets[symbol]["spot"]["free"]
                                lock += assets[symbol]["spot"]["locked"]

                            assets.update(
                                {
                                    symbol: {
                                        "spot": {
                                            "borrowed": 0,
                                            "free": free,
                                            "locked": lock,
                                            "netAsset": netAsset,
                                            "rewards": 0,
                                        }
                                    }
                                }
                            )
            except (EncodingWarning, Exception) as e:
                print("get_balance_spot_earn(): {}".format(e))

        # Agrega position a dict: assets los productos fexible
        def get_balance_flexible_producto():
            response = self.BClient.Myget_flexible_product_position()
            if response:
                for keys in response["rows"]:
                    if keys["asset"] != "USDT":

                        collateralAmount = float(keys["collateralAmount"])
                        totalAmount = float(keys["totalAmount"])
                        if collateralAmount != 0 or totalAmount != 0:

                            free, lock, Rewards = 0.0, 0.0, 0.0
                            symbol = (
                                keys["asset"] + "USDT"
                                if keys["asset"] != "USDT"
                                else keys["asset"]
                            )

                            # sum free obtenido en spot a lo disponible en earn
                            if symbol in assets.keys():
                                lock += assets[symbol]["spot"]["locked"]
                                free += assets[symbol]["spot"]["free"]
                                totalAmount += assets[symbol]["spot"]["netAsset"]

                                Rewards = float(keys["cumulativeTotalRewards"])
                                totalAmount += lock

                            assets.update(
                                {
                                    symbol: {
                                        "position": {
                                            "borrowed": collateralAmount,
                                            "free": free,
                                            "locked": lock,
                                            "netAsset": totalAmount,
                                            "rewards": Rewards,
                                            "debit USDT": 0.0,
                                        }
                                    }
                                }
                            )
                            activos.append(symbol)

        # obtiene prestamos sobre activos
        def get_loan_activos():
            for keys in activos:
                coin = keys.replace("USDT", "")
                response = self.BClient.get_flexible_loan_ongoing_orders(
                    loanCoin="USDT",
                    collateralCoin=coin,
                    current=1,
                    limit=5,
                    recvWindow=5000,
                )
                if response:
                    if response["total"] > 0:
                        field = response["rows"][0]
                        assets[keys]["position"]["debit USDT"] = float(
                            field["totalDebt"]
                        )

        # actualiza tablas y variables globales
        def update_entorno_e_inversion():
            positions = self.RepositorioOportunidades.select_inversion(
                tipoin=self.vehiculo, ticket="all"
            )

            self.assets, self.activos = {}, []
            for keys, value in assets.items():
                if "position" in value.keys():
                    self.assets.update({keys: value})
                    self.activos.append(keys)

            # si hay position en assets e in_position != [] actualiza la tabla inversion
            if positions and self.assets:
                out_positions = update_inversion_crypto(
                    api=self.assets, in_positions=positions
                )

                # self.update_self_positions(in_positions=out_positions)
                self.RepositorioOportunidades.update_inversion(
                    account=self.account,
                    vehiculo=self.vehiculo,
                    positions=out_positions,
                )

        try:
            assets, activos = {}, []

            # obtiene saldos de activos en spot y earning
            get_balance_spot_earn()

            # obtiene activos de wallet earn
            get_balance_flexible_producto()

            # obtiene préstamos activos
            get_loan_activos()

            # válida que exista positions (caso especial para inicio de sesion)
            update_entorno_e_inversion()
        except EncodingWarning as e:
            print("[api_vehiculo_binance()]: {}".format(e))

    # declara las api de Interactive Brockers
    def api_vehiculo_iteractive(self):
        # obtiene las diferentes divisas que maneja el portafolio
        def currency_account(ledger):

            for moneda, value in ledger.items():
                self.currency.update({moneda: value["exchangerate"]})

        # p_cartera instancia API vs p_positions tabla inversión
        def update_inversion_stock(p_cartera, p_positions):
            try:
                self.activos, x_positions = [], []
                for key in p_cartera:

                    symbol = key["contractDesc"]
                    if symbol.endswith(".OLD"):
                        pass
                    else:
                        # encuentra factor de conversión para las positions que no están USD
                        p, exDividendDate, dividendYield, dividendo = (
                            {},
                            0.0,
                            0.0,
                            0.0,
                        )
                        factor = self.currency[key["currency"]]
                        symbol = key["contractDesc"]

                        # obtiene información de dividendos
                        (yf_activo, datos, ind_update) = self.ts_yfinance_symbol(
                            symbol=symbol, vehiculo=self.vehiculo
                        )

                        objetivo, x_open, price, empresa = 0.0, 0.0, 0.0, ""
                        sector = key["sector"] if "sector" in key else "buscar"

                        if yf_activo:
                            dividendo, dividendYield, exDividendDate = (
                                0.0,
                                0.0,
                                "9999-12-31",
                            )

                        price = key["mktPrice"]
                        if "dividendYield" in yf_activo:
                            dividendYield = yf_activo["dividendYield"]
                            if "previousClose" in yf_activo:
                                price = yf_activo["previousClose"]
                            dividendo = price * dividendYield / 100

                        if "dividendRate" in yf_activo:
                            dividendo = yf_activo["dividendRate"]

                        if "exDividendDate" in yf_activo:
                            exDividendDate = datetime.fromtimestamp(
                                yf_activo["exDividendDate"]
                            )

                        if "open" in yf_activo:
                            x_open = yf_activo["open"] * factor

                        # fija precio objetivo
                        if "targetMeanPrice" in yf_activo:
                            objetivo = yf_activo["targetMeanPrice"]
                        elif "targetHighPrice" in yf_activo:
                            objetivo = yf_activo["targetHighPrice"]
                        elif "targetLowPrice" in yf_activo:
                            objetivo = yf_activo["targetLowPrice"]
                        elif "fiftyTwoWeekHigh" in yf_activo:
                            objetivo = yf_activo["fiftyTwoWeekHigh"]

                        # asegura un sector, para los activos
                        if "sector" in yf_activo:
                            sector = yf_activo["sector"]
                            if is_vacio(sector) or is_null(sector):
                                sector = sectores(symbol=symbol)
                        else:
                            sector = sectores(symbol=symbol)

                        if "longName" in yf_activo:
                            empresa = yf_activo["longName"]

                        p["region"], p["country"] = "Global", "US"
                        if "region" in yf_activo:
                            p["region"] = yf_activo["region"]
                        if "country" in yf_activo:
                            p["country"] = yf_activo["country"]

                        p["unrealizedpnl"] = key["unrealizedPnl"]
                        p["exDividendDate"] = exDividendDate
                        p["dividendYield"] = dividendYield
                        p["estrategia"] = "P02"
                        p["empresa"] = key["name"] if "name" in key else empresa
                        p["dividendo"] = dividendo * factor
                        p["costobase"] = key["avgCost"] * key["position"] * factor
                        p["objetivo"] = objetivo * factor
                        p["position"] = key["position"]
                        p["mrkprice"] = key["mktPrice"] * factor
                        p["mktvalue"] = key["mktPrice"] * key["position"] * factor
                        p["retorno"] = (
                            (key["mktValue"] - p["costobase"]) / p["costobase"]
                            if p["costobase"] > 0
                            else 0
                        )
                        p["sector"] = sector
                        p["ticket"] = symbol
                        p["deuda"] = 0
                        p["conid"] = str(key["conid"])
                        p["open"] = x_open
                        p["dgyp"] = p["mrkprice"] - p["open"] if p["open"] > 0 else 0
                        p["peso"] = 0

                        # obtiene la positions anterior, la estrategia y otros valores
                        for position in p_positions:
                            if position["ticket"] == p["ticket"]:
                                p["estrategia"] = position["estrategia"]
                                p["objetivo"] = (
                                    position["objetivo"]
                                    if p["objetivo"] == 0
                                    else p["objetivo"]
                                )

                                if "name" in key.keys():
                                    p["empresa"] = key["name"]
                                else:
                                    p["empresa"] = position["empresa"]

                                break

                        # actualiza variables de la clase
                        self.assets.update(
                            {
                                p["conid"]: {
                                    "symbol": symbol,
                                    "position": p["position"],
                                    "costobase": p["costobase"],
                                    "unrealizedpnl": p["unrealizedpnl"],
                                    "last": p["mrkprice"],
                                    "amount_div": p["dividendo"],
                                    "objetivo": p["objetivo"],
                                }
                            }
                        )
                        self.activos.append(p["conid"])
                        x_positions.append(p)
                return x_positions
            except (EncodingWarning, Exception) as e:
                print("update_inversion_stock(): {}".format(e))

        try:
            response = self.IClient.portfolio_account_ledger(account_id=self.account)
            if response:
                # almacena las currency para aplicar conversión a las posiciones
                currency_account(response)
                self.summary = response

                # obtiene positions a partir de API
                cartera = self.IClient.portfolio_account_positions(
                    account_id=self.account, page_id=0
                )
                in_positions = self.RepositorioOportunidades.select_inversion(
                    tipoin=self.vehiculo, ticket="all"
                )

                # actualiza inversiones globales self.assets y self.activos
                if cartera and in_positions:
                    positions = update_inversion_stock(cartera, in_positions)

                    # actualiza tabla de inversiones con última información de la API
                    self.RepositorioOportunidades.update_inversion(
                        account=self.account,
                        vehiculo=self.vehiculo,
                        positions=positions,
                    )
        except Exception as e:
            print("[api_vehiculo_iteractive()]: {}".format(e))

    # construye assets y symbol para el websocket vehiculo
    def conector_api_vehiclo(self):
        try:
            if self.vehiculo == "Crypto":
                self.api_vehiculo_binance()

            elif self.vehiculo == "Stock":
                self.api_vehiculo_iteractive()
        except (EncodingWarning, Exception) as error:
            print(f"conector_api_vehiclo({self.vehiculo}): {error}")
            time.sleep(5)

    # actualiza stock en tabla market -- estrategia de dividendos para el portfolio
    def dividends_en_market_stock(self, activos):
        # update tabla market
        def update_tabla_market(x_symbol, campo, value):
            try:
                found, iy = self.Market.select(account="U4214563", symbol=x_symbol)

                if not found:
                    self.Market.insert(upd=campo, val=value, symbol=x_symbol)
                else:
                    self.Market.update(upd=campo, val=value, symbol=x_symbol)
            except EncodingWarning as error:
                print("[update_tabla_market()]: {}".format(error))

        # estructura información de dividendos
        def construct_info_dividends(x_symbol, activo, pdatos, campos):
            try:
                ddatos, x_categoria, x_meses = self.rendimiento_dividends(
                    activo=activo, datos=pdatos, symbol=x_symbol
                )
                if not ddatos.empty:
                    d_json = ddatos.to_json(orient="split")
                    campos.update({"categoriaActivo": x_categoria[0]})
                    campos.update({"trazaDividends": d_json})
                else:
                    campos.update({"categoriaActivo": "X"})
                return campos, x_categoria[0], x_meses
            except EncodingWarning as error:
                print("[construct_info_dividends()]: {}".format(error))

        try:
            columnas, values, meses = [], [], []
            if self.vehiculo == "Stock":
                for symbol in activos:
                    # actualiza lista
                    ticket = convierte_ticket_crypto(symbol)
                    (yf_activo, datos, ind_update) = self.ts_yfinance_symbol(
                        symbol=ticket, vehiculo=self.vehiculo
                    )

                    # actualiza dividendos si update=False -- deja pasar los ETF
                    # if (not ind_update and ('dividendYield' in yf_activo) and
                    #         (yf_activo['quoteType'] != 'ETF') and 'Dividends' in datos):
                    if (
                        not ind_update
                        and ("dividendYield" in yf_activo)
                        and ("Dividends" in datos)
                    ):

                        (market, ix) = self.Market.select(
                            account=self.account, symbol=ticket
                        )

                        # obtiene información del activo
                        x_campos = InfoYfinance(symbol, yf_activo)
                        fields, categoria, meses = construct_info_dividends(
                            ticket, yf_activo, datos, x_campos.info
                        )

                        columnas, values = [], []
                        for keys, info in fields.items():
                            if isinstance(info, (int, float)):
                                columnas.append(keys)
                                values.append(info)
                            else:
                                info = (
                                    info
                                    if info not in ("Infinity", "nan", "NaN")
                                    else 0
                                )
                                columnas.append(keys)
                                values.append(info)

                        # agrega meses de pago de dividendos
                        columnas.append("monthDividendsPay")
                        values.append(", ".join(meses))

                        # indicador de que esta o estuvo en cartera
                        columnas.append("encartera")
                        values.append("Y")

                        # update en tabla market
                        update_tabla_market(symbol, columnas, values)
                        if symbol in self.info.keys():
                            # gwi001  eliminar self.analisis.info[symbol]['update'] = True
                            self.info[symbol]["update"] = True
        except EncodingWarning as e:
            print("[dividends_en_market_stock()]: {}".format(e))

    def run(self):
        def run_cryptos():
            # planifica y ejecuta una vez actualización de precios Cryptos
            def websocket_stream(limit, task):
                nonlocal iteraStream
                try:
                    while True:
                        DataHub.update_self_procesos(
                            proces="thread", tarea=task, itera=iteraStream
                        )
                        self.schedule_WebsocketBinanceStream(limit=limit)
                        iteraStream += 1

                except Exception as e:
                    print(f"websocket_stream() error: {e}")

            def websocket_client(limit, task):
                nonlocal iteraClient
                try:
                    while True:
                        DataHub.update_self_procesos(
                            proces="thread", tarea=task, itera=iteraClient
                        )
                        self.schedule_WebsocketBinanceApiClient(limit=limit)
                        iteraClient += 1

                except Exception as e:
                    print(f"websocket_client() error: {e}")

            try:
                # Start de positions -------------------------------------------------------------------------------
                self.carga_inversion_en_positions()
                self.conector_api_vehiclo()
                print(f"Start:(run_positions({self.vehiculo},{len(self.positions)})")

                # Start thread Websocket -----------------------------------------------------------------------------
                TSocket, iteraStream = 7200, 1
                stream = f"run_websocket_stream({self.vehiculo})"

                DataHub.procesos.append({"thread": {stream: iteraStream}})
                DataHub.manager_events.register_thread(
                    name=stream,
                    target=websocket_stream,
                    limit=TSocket,
                    task=stream,
                )

                socket = "WebsocketBinanceStream_OnMessage(Crypto)"
                DataHub.procesos.append({"widget": {socket: 0}})

                # Start de Websocket Client (orders, trader) ------------------------------------------------------
                TSocket, iteraClient = 360, 1
            except EncodingWarning as e:
                print(f"run_cryptos(): {e}")

        def run_stock():
            # invoca websocket y suscribe symbols
            def websocket_stream(limit, task):
                nonlocal iteraStream
                try:
                    url = "wss://localhost:5000/v1/api/ws"
                    while True:

                        self.WsStock = MyWebsocket(
                            url=url,
                            logger=False,
                            vehiculo=self.vehiculo,
                            assets=self.assets,
                            idsymbol=self.activos,
                        )

                        iteraStream += 1
                        self.WsStock.my_message = self.on_message_IBrks_websocket
                        DataHub.update_self_procesos(
                            proces="thread", tarea=task, itera=iteraStream
                        )
                        self.WsStock.websocket_loop(limit=limit)

                except (EncodingWarning, Exception) as e:
                    print(f"websocket_stream() error: {e}")

            try:
                self.ib_connection = self.IClient.create_session()

                if self.IClient.ib_is_connet():
                    # invoca API y actualiza inversiones
                    self.carga_inversion_en_positions()
                    self.conector_api_vehiclo()
                    print(
                        f"Start:(run_positions({self.vehiculo},{len(self.positions)})"
                    )

                    # Start thread Websocket -----------------------------------------------------------------------------
                    TSocket, iteraStream = 7200, 1
                    stream = f"run_websocket_stream({self.vehiculo})"

                    DataHub.procesos.append({"thread": {stream: iteraStream}})
                    DataHub.manager_events.register_thread(
                        name=stream,
                        target=websocket_stream,
                        limit=TSocket,
                        task=stream,
                    )

                    socket = f"WebsocketStream_OnMessage({self.vehiculo})"
                    self.procesos.append({"widget": {socket: 0}})

                else:
                    raise ValueError(
                        "run_stock()]: {}".format("No hay conección con IBKR's")
                    )
            except (EncodingWarning, Exception) as error:
                print("[run_stock]: {}".format(error))

        try:
            # instancia para vehiculo Crypto
            if self.vehiculo == "Crypto":
                run_cryptos()

            # instancia para vehiculo Stock
            if self.vehiculo == "Stock":
                run_stock()
        except EncodingWarning as e:
            print("run_vehiculo({}): {}".format(self.vehiculo, e))


# modulo principal
class DashMain:
    def __init__(self, ibrks=False):
        self.stock_ts = None
        self.stock = None
        self.crypto_ts = None
        self.crypto = None
        self.ars = None
        self.ars_ts = None

        self.root = tk.Tk()
        self.modules = []
        self.cartera = []
        self.it_crypto = 0
        self.it_stock = 0

        # colores pantallas y gráficos
        self.bgcolor = DataHub.bgcolor
        self.cgcolor = DataHub.cgcolor

        self.cchart = DataHub.cchart
        self.colors = DataHub.colors
        self.dw = DataHub.colors.get("dw")
        self.dh = DataHub.colors.get("dh")
        self.df = DataHub.colors.get("df")
        self.max_dw = self.root.winfo_screenwidth()
        self.max_dh = self.root.winfo_screenheight()

        # actualiza dimensiones de la pantalla
        DataHub.colors["max_dw"] = self.root.winfo_screenwidth()
        DataHub.colors["max_dh"] = self.root.winfo_screenheight()

        # Accesos MySql ----------------------------------------------------------------------------------------------
        self.Market = MarketScreen()
        self.PlanInversion = PlanInversion()
        self.Estrategia = EstrategiaInversion()
        self.RepositorioOportunidades = RepositorioOportunidadesBuySell()

        self.program = "Dashmain(v9.ia)"
        self.dimension = "%dx%d+0+0" % (self.max_dw, self.max_dh)
        self.root.geometry(self.dimension)
        self.root.config(bg=self.colors["bgcolor"])
        self.root.protocol("WM_DELETE_WINDOW", self.eexit)
        self.root.title(self.program)
        self.root.state("zoomed")

        # frame principal
        self.style = style_app(main=self.root)
        self.root_note = ttk.Frame(self.root, padding=(1, 1, 1, 1), style="C.TFrame")
        self.root_note.pack(side=tk.TOP, expand=True, anchor=tk.NW)

        self.nb = ttk.Notebook(
            self.root_note, style="C.TNotebook", width=self.dw, height=self.dh
        )
        self.nb.pack(anchor="nw", pady=10, expand=True)
        self.root_note.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.win0 = ttk.Frame(self.nb, style="C.TFrame", width=self.dw, height=self.dh)
        self.win1 = ttk.Frame(self.nb, style="C.TFrame", width=self.dw, height=self.dh)
        self.win2 = ttk.Frame(self.nb, style="C.TFrame", width=self.dw, height=self.dh)
        self.win3 = ttk.Frame(self.nb, style="C.TFrame", width=self.dw, height=self.dh)
        self.win4 = ttk.Frame(self.nb, style="C.TFrame", width=self.dw, height=self.dh)
        self.win5 = ttk.Frame(self.nb, style="C.TFrame", width=self.dw, height=self.dh)
        self.win6 = ttk.Frame(self.nb, style="C.TFrame", width=self.dw, height=self.dh)

        # Añadir padding a los frames
        self.win0.pack(fill="both", expand=True)
        self.win1.pack(fill="both", expand=True)
        self.win2.pack(fill="both", expand=True)
        self.win3.pack(fill="both", expand=True)
        self.win4.pack(fill="both", expand=True)
        self.win5.pack(fill="both", expand=True)
        self.win6.pack(fill="both", expand=True)

        self.nb.add(self.win1, text="Crypto         ")
        self.nb.add(self.win0, text="Stock          ")
        self.nb.add(self.win4, text="Ars            ")
        self.nb.add(self.win6, text="FuturoCrypto   ")
        self.nb.add(self.win2, text="Screener       ")
        self.nb.add(self.win3, text="Gestión        ")
        self.nb.add(self.win5, text="System         ")

        # frames de Gráficos y figuras principales
        pn0 = ttk.Frame(self.root, padding=(1, 1, 1, 1), style="C.TFrame")
        pn1 = tk.Frame(
            self.root, bg="white", border=2
        )  # frame desemenño ultimos 6 meses
        pn2 = tk.Frame(self.root, bg="white", border=2)  # frame Fear and Greed
        pn3 = tk.Frame(
            self.root, bg="white", border=2
        )  # frame Diversificacion por dividendos
        pn4 = tk.Frame(
            self.root, bg="white", border=2
        )  # frame Diversificacion por sector
        pn5 = tk.Frame(
            self.root, bg="white", border=2
        )  # frame Diversificacion por tipo de activo
        pn6 = tk.Frame(
            self.root, bg="white", border=2
        )  # frame Diversificacion por region

        pn0.place(x=self.df + 5, y=10)
        pn1.place(x=self.df + 5, y=190)
        pn2.place(x=self.df + 310, y=190)
        pn3.place(x=self.df + 5, y=470)
        pn4.pack(pady=2, padx=2, side=tk.LEFT)
        pn5.pack(pady=2, padx=2, side=tk.LEFT)
        pn6.pack(pady=2, padx=2, side=tk.LEFT)

        # perfil de usuario y salida del sistema ---------------------------------------------------------------------
        lpn = ttk.Frame(pn0, style="C.TFrame")
        rpn = ttk.Frame(pn0, style="C.TFrame")
        lpn.pack(side=tk.LEFT, fill=tk.X)
        rpn.pack(side=tk.RIGHT, fill=tk.X)

        # información usuario -----------------------------------------------------------------------------------------
        self.line = tk.Label(
            lpn, text="Inversionista, ", font=("Arial", 14), bg=self.colors["bgcolor"]
        )
        imagen_tk = BDsystem.select_image(idd=11, size=(32, 32))

        now = datetime.now()
        self.user = tk.Button(
            lpn, image=imagen_tk, bg=self.colors["bgcolor"], relief=tk.FLAT
        )
        self.user.imagen = imagen_tk

        self.line.pack(side=tk.LEFT, fill=tk.X)
        self.user.pack(side=tk.LEFT, fill=tk.X)

        # órdenes y salida del sistema --------------------------------------------------------------------------------
        imagen_tk = BDsystem.select_image(idd=14, size=(32, 32))

        self.cart = tk.Button(
            rpn,
            image=imagen_tk,
            bg=self.colors["bgcolor"],
            relief=tk.FLAT,
            command=lambda: self.car_ordenes_activas(),
        )
        self.cart.imagen = imagen_tk

        # inserta espacios para alinear botones en la lineas
        self.line = tk.Label(rpn, text=spaces(125), bg=self.colors["bgcolor"])
        imagen_tk = BDsystem.select_image(idd=12, size=(32, 32))

        self.exit = tk.Button(
            rpn,
            image=imagen_tk,
            bg=self.colors["bgcolor"],
            relief=tk.FLAT,
            command=lambda: self.eexit(),
        )
        self.exit.imagen = imagen_tk
        self.exit.pack(side=tk.RIGHT, fill=tk.X)
        self.cart.pack(side=tk.RIGHT, fill=tk.X)
        self.line.pack(side=tk.RIGHT, fill=tk.X)

        # áreas y figuras de gráficos principales --------------------------------------------------------------------
        self.rg0 = Figure(
            figsize=(2.77, 2.4), dpi=110, layout="tight"
        )  # firgura de rendimiento ultimos 6 meses
        self.rg1 = Figure(figsize=(2.77, 2.4), dpi=110)  # figura de Fear and Greed
        self.rg2 = Figure(
            figsize=(5.55, 2.4), dpi=110, layout="tight"
        )  # figura de Diversificación por dividendos
        self.rg3 = Figure(
            figsize=(5.75, 2.9), dpi=110, layout="tight"
        )  # figura de Diversificación por sector
        self.rg4 = Figure(
            figsize=(5.75, 2.9), dpi=110, layout="tight"
        )  # figura de Diversificación por tipo de activo
        self.rg5 = Figure(
            figsize=(5.75, 2.9), dpi=110, layout="tight"
        )  # figura de Diversificación por region

        self.rv0 = FigureCanvasTkAgg(
            self.rg0, master=pn1
        )  # canvas de rendimiento ultimos 6 meses
        self.rv1 = FigureCanvasTkAgg(self.rg1, master=pn2)  # canvas de Fear and Greed
        self.rv2 = FigureCanvasTkAgg(
            self.rg2, master=pn3
        )  # canvas de Diversificación por dividendos
        self.rv3 = FigureCanvasTkAgg(
            self.rg3, master=pn4
        )  # canvas de Diversificación por sector
        self.rv4 = FigureCanvasTkAgg(
            self.rg4, master=pn5
        )  # canvas de Diversificación por tipo de activo
        self.rv5 = FigureCanvasTkAgg(
            self.rg5, master=pn6
        )  # canvas de Diversificación por region

        self.rg0.set_facecolor(self.colors["bgcolor"])
        self.rg1.set_facecolor(self.colors["bgcolor"])
        self.rg2.set_facecolor(self.colors["bgcolor"])
        self.rg3.set_facecolor(self.colors["bgcolor"])
        self.rg4.set_facecolor(self.colors["bgcolor"])
        self.rg5.set_facecolor(self.colors["bgcolor"])

        self.rv0.draw()
        self.rv1.draw()
        self.rv2.draw()
        self.rv3.draw()
        self.rv4.draw()
        self.rv5.draw()
        self.rv0.get_tk_widget().pack()
        self.rv1.get_tk_widget().pack()
        self.rv2.get_tk_widget().pack()
        self.rv3.get_tk_widget().pack()
        self.rv4.get_tk_widget().pack()
        self.rv5.get_tk_widget().pack()

        # Icono detalle para bottom de gráfica ------------------------------------------------------------------------
        imagen_tk = BDsystem.select_image(idd=17, size=(24, 24))

        # define button de gráficas Riesgo, sector y dividendo
        bt1 = tk.Button(
            pn1,
            text="3m",
            width=2,
            bg=self.bgcolor,
            fg=self.cgcolor,
            relief=tk.FLAT,
            command=lambda: self.setup_graph_region("3"),
        )
        bt2 = tk.Button(
            pn1,
            text="6m",
            width=2,
            bg=self.bgcolor,
            fg=self.cgcolor,
            relief=tk.FLAT,
            command=lambda: self.setup_graph_region("6"),
        )
        bt3 = tk.Button(
            pn1,
            text="1y",
            width=2,
            bg=self.bgcolor,
            fg=self.cgcolor,
            relief=tk.FLAT,
            command=lambda: self.setup_graph_region("12"),
        )

        gt3 = tk.Button(
            pn3,
            image=imagen_tk,
            bg=self.colors["bgcolor"],
            relief=tk.FLAT,
            command=lambda: self.detalle_graph("Dividendos"),
        )
        gt4 = tk.Button(
            pn4,
            image=imagen_tk,
            bg=self.colors["bgcolor"],
            relief=tk.FLAT,
            command=lambda: self.detalle_graph("Sector"),
        )
        gt5 = tk.Button(
            pn5,
            image=imagen_tk,
            bg=self.colors["bgcolor"],
            relief=tk.FLAT,
            command=lambda: self.detalle_graph("Activo"),
        )
        gt6 = tk.Button(pn6, image=imagen_tk, bg=self.colors["bgcolor"], relief=tk.FLAT)

        gt3.imagen = imagen_tk
        gt4.imagen = imagen_tk
        gt5.imagen = imagen_tk
        gt6.imagen = imagen_tk

        bt1.place(y=20, x=10)
        bt2.place(y=20, x=30)
        bt3.place(y=20, x=50)
        gt3.place(y=10, x=10)
        gt4.place(y=10, x=10)
        gt5.place(y=10, x=10)
        gt6.place(y=10, x=10)

        # comparte lista de procesos Datahub
        self.procesos = DataHub.procesos
        self.orders = DataHub.orders
        self.info = DataHub.info

        self.messagebox = MyMessageBox(self.root)

        self.sesion_crypto = None
        self.sesion_stock = None
        self.ibrks = "No"
        self.gestion = None
        self.fci = None
        self.screener = None
        self.chatbot = None

        # Inicializa maganer de eventos -------------------------------------------------------------------------------
        DataHub.manager_events = ManagerEvents(logger="root", GlobalHub=DataHub)
        DataHub.manager_events.run_scheduler()

        # DashMain.manager_after = MangerAfterEvents(AppRoot=self.root, logger="root")

    # cambia estilo notebook -----------------------------------------------------------------------------------------
    def on_tab_changed(self, event):
        selected = event.widget.index("current")
        for i in range(self.root_note.index("end")):
            if i == selected:
                self.root_note.tab(i, style="Custom.TNotebook.Tab")
            else:
                self.root_note.tab(i, style="TNotebook.Tab")  # estilo por defecto

    # contendor para iniciar widget cryptos
    def start_crypto(self, account=None, vehiculo=None):
        def update_pane_crypto():
            nav, unpyl, dgyp, unprofit, costo = 0.0, 0.0, 0.0, 0.0, 0.0
            for keys in self.crypto.positions:
                nav += keys["mktvalue"]
                unpyl += keys["unrealizedpnl"]
                costo += keys["costobase"]
                dgyp += keys["dgyp"]
                unprofit += keys["unrealizedpnl"] if keys["unrealizedpnl"] > 0 else 0

            per = costo / unprofit if unprofit > 0 else 0

            self.crypto.set_header_panel(
                Dgyp=dgyp, Nav=nav, Unpyl=unpyl, Unprofit=unprofit, Per=per
            )
            self.crypto.header_panel()

        try:
            cb = BB().spot
            self.crypto = WidgetVehiculo(
                master=self.win1, account=account, vehiculo=vehiculo
            )

            if cb.check_binance_connection():

                self.crypto_ts = DatosVehivulo(account=account, vehiculo=vehiculo)
                self.crypto_ts.run()

                self.procesos.append(
                    {"widget": {"update_widget(Crypto)": self.it_crypto}}
                )

                # información para widgetCrypto
                self.crypto.positions = self.crypto_ts.positions
                self.crypto.resumen = self.crypto_ts.resumen

                self.crypto.inicio_widget_treeview(self.crypto.positions)
                self.crypto.run_graficos()
                self.update_widget(vehiculo=vehiculo)

            # para widget offline
            elif not cb.check_binance_connection():

                self.crypto.carga_inversion_en_positions()
                update_pane_crypto()

                self.crypto.inicio_widget_treeview(self.crypto.positions)
                self.crypto.run_graficos()
        except (EncodingWarning, Exception) as e:
            print(f"start_cryptos({e})")

    # contendor para iniciar widget de stock
    def start_stock(self, account=None, vehiculo=None):
        def update_pane_stock():
            nav, unpyl, dgyp, unprofit, costo = 0.0, 0.0, 0.0, 0.0, 0.0
            for keys in self.stock.positions:

                nav += keys["mktvalue"]
                unpyl += keys["unrealizedpnl"]
                costo += keys["costobase"]
                dgyp += keys["dgyp"]
                unprofit += keys["unrealizedpnl"] if keys["unrealizedpnl"] > 0 else 0

            per = costo / unprofit if unprofit > 0 else 0

            self.stock.set_header_panel(
                Dgyp=dgyp,
                Nav=nav,
                Unpyl=unpyl,
                Unprofit=unprofit,
                Per=per,
                Sesion="Offline",
            )
            self.stock.header_panel()

        try:
            ib = IB()
            self.stock = WidgetVehiculo(
                master=self.win0, account=account, vehiculo=vehiculo
            )

            if ib.is_localhost():
                self.stock_ts = DatosVehivulo(account=account, vehiculo=vehiculo)
                self.stock_ts.run()

                self.procesos.append(
                    {"widget": {"update_widget(Stock)": self.it_stock}}
                )

                # información para widgetCrypto
                self.stock.positions = self.stock_ts.positions
                self.stock.resumen = self.stock_ts.resumen

                self.stock.inicio_widget_treeview(self.stock.positions)
                self.stock.run_graficos()
                self.update_widget(vehiculo=vehiculo)

            # para widget offline
            else:
                self.stock.carga_inversion_en_positions()
                update_pane_stock()

                self.stock.inicio_widget_treeview(self.stock.positions)
                self.stock.run_graficos()
        except (EncodingWarning, Exception) as e:
            print("start_stock(): {}".format(e))

    # chatbot y/o asistente ------------------------------------------------------------------------------------------
    def start_chatbot(self):
        try:
            self.chatbot = AsistenteChatbot(
                root=self.root,
            )
        except (EncodingWarning, Exception) as e:
            print("start_chatbot(): {}".format(e))

    # update widget del crypto
    def update_widget(self, vehiculo=None):
        try:

            # información para widgetCrypto
            if vehiculo == "Crypto":

                self.it_crypto += 1
                self.crypto.header_panel()
                DataHub.update_self_procesos(
                    proces="widget", tarea="update_widget(Crypto)", itera=self.it_crypto
                )

                self.crypto.update_panelVehiculo(orden=self.crypto.orden)

            # información para widgetStock
            if vehiculo == "Stock":

                self.it_stock += 1

                self.stock.summary = self.stock_ts.summary

                self.stock.header_panel()
                DataHub.update_self_procesos(
                    proces="widget", tarea="update_widget(Stock)", itera=self.it_stock
                )

                self.stock.update_panelVehiculo(orden=self.stock.orden)
                # self.stock.schedule_order_remote()

            # actualiza cada 1/2'' segundos
            self.root.after(500, lambda: self.update_widget(vehiculo=vehiculo))
            # DataHub.manager_after._safe(
            #    500, lambda: self.update_widget(vehiculo=vehiculo), name="update_widget"
            # )

        except (EncodingWarning, Exception) as e:
            print("update_widget({}}): {}".format(vehiculo, e))

    def car_ordenes_activas(self):
        def eexit():
            rnb.destroy()

        # construye treeview con todas las orders
        def config_treeview_ordenes(tree, heard):
            try:
                heard.column("#0", width=70, minwidth=70, anchor=tk.W)
                heard.heading("#0", text="Nro.")
                tree.column("#0", width=70, minwidth=70, anchor=tk.W)
                tree.heading("#0", text="Nro")

                for i, key in enumerate(cols):
                    width = 100 if key != "id" else 100
                    width = 100 if key != "id_enviar" else 100

                    # oculta columnas en panel de orders activas
                    width = 0 if key in ("account", "conid", "del", "sub") else width

                    tree.column(key, width=width, minwidth=width, anchor=tk.E)
                    tree.heading(key, text=cols[i])

                    heard.column(key, width=width, minwidth=width, anchor=tk.E)
                    heard.heading(key, text=cols[i])

                tree.tag_configure("green", background="green", foreground="white")
                tree.tag_configure("red", background="red", foreground="white")
            except (EncodingWarning, Exception) as e:
                print("treeview_ordenes(): {}".format(e))

        # sincroniza scroll de treeview orders
        def sync_scroll(*args):
            heard.xview(*args)
            tree.xview(*args)

        # agregas orders a treeview
        def insert_ordenes_treeview(tree):
            try:
                for orders, values in self.orders.items():
                    for i, orden in enumerate(values):
                        insert, id_order, id_enviar = (
                            True,
                            orden["id_order"],
                            orden["id_enviar"],
                        )

                        # agregar a lista de órdenes pendientes
                        if insert:
                            values = [
                                orden["account"],
                                orden["conid"],
                                orden["symbol"],
                                orden["side"],
                                orden["orderType"],
                                orden["price"],
                                orden["quantity"],
                                orden["status"],
                                orden["tif"],
                                orden["id_order"],
                                orden["id_enviar"],
                            ]

                            if orders == "Crypto":
                                tree.insert(
                                    Crypto,
                                    "end",
                                    text="{:>3.0f}".format(i + 1),
                                    values=values,
                                )

                            if orders == "Stock":
                                tree.insert(
                                    Stock,
                                    "end",
                                    text="{:>3.0f}".format(i + 1),
                                    values=values,
                                )

            except EncodingWarning as e:
                print("insert_ordenes_treeview(): {}".format(e))

        # controla selección de items en orders activas
        def on_button_click(accion, fields):
            selected_item = tree.selection()
            if selected_item:
                values = tree.item(selected_item)["values"]
                items = tree.parent(selected_item)
                vehiculo = tree.item(items, "text")

                print(f"Botón en la fila seleccionada: {accion} {vehiculo} {values}")
                if accion == "elimina":
                    eliminar_orden(vehiculo, fields, values)

                if accion == "enviar":
                    envia_orders_stock(vehiculo, fields, values)

        # cancela orders en espera para su ejecución
        def eliminar_orden(vehiculo, fields, values):
            try:
                if vehiculo == "Crypto":
                    symbol = values[fields.index("symbol")]
                    orderId = values[fields.index("id")]
                    account = values[fields.index("account")]

                    # ejecuta API y actualiza order_trader
                    response = self.crypto_ts.BClient.get_cancel_order(
                        symbol=symbol, orderId=orderId
                    )
                    if response:
                        timestamp = response["transactTime"] / 1000.0
                        stamp = datetime.fromtimestamp(timestamp)
                        values = {"status": "CANCELED", "stampSubmit": stamp}

                        self.RepositorioOportunidades.update_order_trader(
                            account=account,
                            values=values,
                            symbol=symbol,
                            orderid=orderId,
                        )

                if vehiculo == "Stock":
                    symbol = values[fields.index("symbol")]
                    orderId = str(values[fields.index("id")])
                    account = values[fields.index("account")]

                    # ejecuta API y actualiza order_trader
                    # response = self.stock_ts.IClient.delete_order(account_id=account, customer_order_id=orderId)

                    response = self.stock_ts.IClient.deleteorder(
                        account_id=account, customer_order_id=orderId
                    )

                    if response:
                        timestamp = response["transactTime"] / 1000.0
                        stamp = datetime.fromtimestamp(timestamp)
                        values = {"status": "CANCELED", "stampSubmit": stamp}

                        self.RepositorioOportunidades.update_order_trader(
                            account=account,
                            values=values,
                            symbol=symbol,
                            orderid=orderId,
                        )

            except EncodingWarning as e:
                print("eliminar_orden(): {}".format(e))

        # refresca ordenes en treeview
        def update_treeview_ordenes():
            try:
                # Obtener todos los elementos padres del Treeview
                padres = tree.get_children()
                for padre in padres:
                    # print(f"Padre: {padre}, Valores: {tree.item(padre)['values']}")

                    # Obtener los hijos del padre
                    hijos = tree.get_children(padre)
                    for hijo in hijos:
                        # print(f"  Hijo: {hijo}, Valores: {tree.item(hijo)['values']}")
                        tree.delete(hijo)

                insert_ordenes_treeview(tree)
            except EncodingWarning as e:
                print("update_treeview_ordenes(): {}".format(e))

        def envia_orders_stock(vehiculo, fields, values):
            try:
                if vehiculo == "Stock":
                    print(fields)
                    symbol = values[fields.index("symbol")]
                    orderId = values[fields.index("id_enviar")]
                    account = values[fields.index("account")]

                    # provisional
                    response = self.stock_ts.IClient.orderconfirm(replyid=orderId)
                    if response:
                        pass
                        # timestamp = response['transactTime'] / 1000.0
                        # stamp = datetime.fromtimestamp(timestamp)
                        # values = {'status': 'Submitted', 'stampSubmit': stamp}

                        # update_order_trader(account=account, values=values, symbol=symbol, orderid=orderId)
            except EncodingWarning as e:
                print("envia_orders_stock(): {}".format(e))

        try:
            rnb = tk.Toplevel()
            title = "Lista de Ordenes"
            dimension = "%dx%d+%d+%d" % (740, 500, self.colors["df"] - 140, 65)
            rnb.geometry(dimension)
            rnb.resizable(False, False)
            rnb.attributes("-toolwindow", 1)
            rnb.config(bg=self.colors["bgcolor"])
            rnb.title(title)
            rnb.focus()
            rnb.grab_set()
            rnb.protocol("WM_DELETE_WINDOW", eexit)

            win1 = ttk.Frame(rnb, padding=(1, 1, 1, 1), style="C.TFrame", width=520)
            win2 = ttk.Frame(rnb, padding=(1, 1, 1, 1), style="C.TFrame", width=520)
            win3 = ttk.Frame(rnb, padding=(1, 1, 1, 1), style="C.TFrame", width=520)
            win1.pack(fill=tk.X)
            win2.pack(fill=tk.X)
            win3.pack(fill=tk.X)

            # Configurar el Treeview
            cols = [
                "account",
                "conid",
                "symbol",
                "side",
                "orderType",
                "price",
                "quantity",
                "status",
                "tiempo",
                "id",
                "id_enviar",
                "sub",
                "del",
            ]
            heard = ttk.Treeview(win1, columns=cols, height=1, style="TFrame")
            tree = ttk.Treeview(
                win2, columns=cols, height=18, style="TFrame", show="tree"
            )

            config_treeview_ordenes(tree, heard)

            # Configurar el Treeview para usar los scrollbars
            hscroll = ttk.Scrollbar(win2, orient="horizontal", command=sync_scroll)

            ct1 = tk.Button(
                win3,
                text="Eliminar",
                width=8,
                bg="gray",
                fg="white",
                command=lambda: on_button_click("elimina", cols),
            )
            ct2 = tk.Button(
                win3,
                text="Modificar",
                width=8,
                bg="gray",
                fg="white",
                command=lambda: on_button_click("modifica", cols),
            )
            ct3 = tk.Button(
                win3,
                text="Enviar",
                width=8,
                bg="gray",
                fg="white",
                command=lambda: on_button_click("enviar", cols),
            )
            ct4 = tk.Button(
                win3,
                text="Update",
                width=8,
                bg="gray",
                fg="white",
                command=lambda: update_treeview_ordenes(),
            )

            ct5 = tk.Button(
                win3,
                text="Cancel",
                width=8,
                bg="gray",
                fg="white",
                command=lambda: eexit(),
            )

            ct1.pack(side=tk.LEFT, padx=5, pady=20)
            ct2.pack(side=tk.LEFT, padx=5, pady=20)
            ct3.pack(side=tk.LEFT, padx=5, pady=20)
            ct4.pack(side=tk.LEFT, padx=5, pady=20)
            ct5.pack(side=tk.LEFT, padx=40, pady=20)

            ct2.config(state="disabled")

            heard.config(xscrollcommand=hscroll.set)
            tree.config(xscrollcommand=hscroll.set)

            heard.pack(fill=tk.X, expand=True)
            tree.pack(fill=tk.X, expand=True)
            hscroll.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # declara y Expande los hijos de tree
            Stock = tree.insert(
                "",
                "end",
                text="Stock",
                values=("", "", "", "", "", "", "", "", "", "", "", "", ""),
            )
            Crypto = tree.insert(
                "",
                "end",
                text="Crypto",
                values=("", "", "", "", "", "", "", "", "", "", "", "", ""),
            )
            tree.item(Stock, open=True)
            tree.item(Crypto, open=True)

            insert_ordenes_treeview(tree)
        except EncodingWarning as e:
            print("car_ordenes_activas(): {}".format(e))

    # despliega ventana con detalle para el gráfico
    def detalle_graph(self, tipo=None):

        # controla salida de window_estrategia()
        def eexit():
            rnb.destroy()

        # Ubica información de yfinance. Ticker, para mostrar gráfico de dividends
        def grafico_rendimiento_symbol(symbol=None, windows=None):
            try:

                # if symbol in self.stock_ts.info:
                activo, datos, update = self.crypto_ts.ts_yfinance_symbol(
                    symbol=symbol, vehiculo="Stock"
                )
                self.crypto_ts.rendimiento_dividends(
                    fg=rg, activo=activo, datos=datos, symbol=symbol, plot="yes"
                )
                rv.draw()

                # resultados del simbolo
                inicial = datos["Close"].iloc[0]
                final = datos["Close"].iloc[-1]
                growth = (final - inicial) / inicial
                analisis = {
                    "symbol": symbol,
                    "Precio": "{:>10.2f}".format(inicial)
                    + " - "
                    + "{:>10.2f}".format(final),
                    "Growth": "{:>10.2%}".format(growth),
                    "Dividend Yield": "{:>10.2%}".format(
                        activo.get("dividendYield", 0)
                    ),
                    "Dividend Rate": "{:>10.2f}".format(activo.get("dividendRate", 0)),
                    "P/E Ratio": "{:>10.2f}".format(activo.get("trailingPE", 0)),
                    "Beta": "{:>10.2f}".format(activo.get("beta", 0)),
                }

                for i, (key, value) in enumerate(analisis.items()):
                    lbl = tk.Label(
                        windows,
                        text=str(key),
                        bg=self.bgcolor,
                        font=("Arial", 9, "bold"),
                    )
                    lbv = tk.Label(
                        windows, text=str(value), bg=self.bgcolor, font=("Arial", 9)
                    )
                    lbv.grid(row=i + 1, column=1, padx=5, pady=1, sticky=W)
                    lbl.grid(row=i + 1, column=0, padx=5, pady=1, sticky=W)

            except EncodingWarning as e:
                print("grafico_rendimiento_symbol(): {}".format(e))

        # selecciona desde treeview
        def item_selected(event, tree, windows):
            selected_item = tree.selection()
            item = tree.item(selected_item)
            values, symbol = item["values"], ""

            if tipo == "Dividendos":
                symbol = values[0]
                grafico_rendimiento_symbol(symbol=symbol, windows=windows)

            elif tipo == "Sector":
                if str_float(values[4]) > 0.0:
                    symbol = values[1]
                    grafico_rendimiento_symbol(symbol=symbol, windows=windows)

                else:
                    symbol = values[1]
                    message = "symbol :" + symbol + " No informa pago de dividendos"
                    self.messagebox.showwarning("Advertencia", message)

            elif tipo == "Azctivo":
                if str_float(values[4]) > 0.0:
                    symbol = values[1]
                    grafico_rendimiento_symbol(symbol=symbol, windows=windows)

                else:
                    symbol = values[1]
                    message = "symbol :" + symbol + " No informa pago de dividendos"
                    self.messagebox.showwarning("Advertencia", message)

        # selecciona y clasifica detalle por symbol y dividendos
        def detalle_dividendos(meses):
            book, date = {}, datetime.now().month
            positions = self.PlanInversion.select_inversion(
                tipoin="Stock", ticket="all"
            )
            for position in positions:
                symbol = convierte_ticket_crypto(position["ticket"])
                (market, ix) = self.Market.select(account="U4214563", symbol=symbol)

                if market:
                    last = market[0][ix.index("lastDividendValue")]
                    div = market[0][ix.index("dividendRate")]
                    string = market[0][ix.index("monthDividendsPay")]
                    fecha = market[0][ix.index("exDividendDate")]
                    exdiv = fecha.strftime("%d-%b") if fecha.month == date else " "
                    avgcost = position["costobase"] / position["position"]

                    dividends = [0] * 12
                    a_meses = meses if string is None else string.split(",")

                    # calcula la cantidad de pagos
                    distribuir = [s.strip()[:3] for s in a_meses]
                    rata = div / len(distribuir) if len(distribuir) > 0 else last

                    # asume pago de dividends son iguales
                    for i, mes in enumerate(distribuir):
                        dividends[meses.index(mes)] = rata * position["position"]

                    # recalculo de rendimiento en función avgcost
                    rend = div / avgcost if avgcost > 0 else 0

                    book.update(
                        {
                            symbol: {
                                "dividends": dividends,
                                "costobase": position["costobase"],
                                "exdiv": exdiv,
                                "yield": rend,
                            }
                        }
                    )
            return book

        # selecciona y clasifica detalle por symbol y sector
        def detalle_sector(meses):
            book, date = {}, datetime.now().month
            positions = self.PlanInversion.select_inversion(
                tipoin="Stock", ticket="all"
            )
            orden = [{"Sector": "sector"}, "DES"]
            cartera = sort_positions(positions, orden)

            for position in cartera:
                symbol = convierte_ticket_crypto(position["ticket"])
                (market, ix) = self.Market.select(account="U4214563", symbol=symbol)

                exdiv, rend, dividends = "", 0.0, [0] * 12
                if market:
                    last = market[0][ix.index("lastDividendValue")]
                    div = market[0][ix.index("dividendRate")]
                    string = market[0][ix.index("monthDividendsPay")]
                    fecha = market[0][ix.index("exDividendDate")]
                    exdiv = fecha.strftime("%d-%b") if fecha.month == date else " "
                    avgcost = position["costobase"] / position["position"]

                    a_meses = meses if string is None else string.split(",")

                    # calcula la cantidad de pagos
                    distribuir = [s.strip()[:3] for s in a_meses]
                    rata = div / len(distribuir) if len(distribuir) > 0 else last

                    # asume pago de dividends son iguales
                    for i, mes in enumerate(distribuir):
                        dividends[meses.index(mes)] = rata * position["position"]

                    # recalculo de rendimiento en función avgcost
                    rend = div / avgcost if avgcost > 0 else 0

                book.update(
                    {
                        symbol: {
                            "dividends": dividends,
                            "costobase": position["costobase"],
                            "sector": position["sector"],
                            "exdiv": exdiv,
                            "yield": rend,
                        }
                    }
                )
            return book

        # selecciona y clasifica detalle por symbol y tipo activo
        def detalle_activo(meses):
            book, date = {}, datetime.now().month
            positions = self.PlanInversion.select_inversion(
                tipoin="activo", ticket="all"
            )

            orden = [{"Activo": "tipoActivo"}, "DES"]
            cartera = sort_positions(positions, orden)

            for position in cartera:
                symbol = convierte_ticket_crypto(position["ticket"])
                (market, ix) = self.Market.select(account="U4214563", symbol=symbol)

                exdiv, rend, dividends = "", 0.0, [0] * 12
                if market:
                    last = market[0][ix.index("lastDividendValue")]
                    div = market[0][ix.index("dividendRate")]
                    string = market[0][ix.index("monthDividendsPay")]
                    fecha = market[0][ix.index("exDividendDate")]
                    exdiv = fecha.strftime("%d-%b") if fecha.month == date else " "
                    avgcost = position["costobase"] / position["position"]

                    a_meses = meses if string is None else string.split(",")

                    # calcula la cantidad de pagos
                    distribuir = [s.strip()[:3] for s in a_meses]
                    rata = div / len(distribuir) if len(distribuir) > 0 else last

                    # asume pago de dividends son iguales
                    for i, mes in enumerate(distribuir):
                        dividends[meses.index(mes)] = rata * position["position"]

                    # recalculo de rendimiento en función avgcost
                    rend = div / avgcost if avgcost > 0 else 0

                book.update(
                    {
                        symbol: {
                            "dividends": dividends,
                            "costobase": position["costobase"],
                            "activo": position["tipoActivo"],
                            "exdiv": exdiv,
                            "yield": rend,
                        }
                    }
                )
            return book

        # obtiene información de dividendos
        def resumen_cartera(option=None, meses=None):
            book = {}
            if option == "Dividendos":
                book = detalle_dividendos(meses)

            elif option == "Sector":
                book = detalle_sector(meses)

            elif option == "Activo":
                book = detalle_activo(meses)

            return book

        def treeview_dividendos(option=None, windows=None):
            try:

                # Configurar el Treeview para usar los scrollbars
                columns, meses = [], meses_list(mask="%b")
                fixed_columns = ["symbol", "CostBase", "Exdiv.", "Year", "%Yield"]
                alignments = {mes: {"width": 90, "anchor": "e"} for mes in meses}
                alignments.update({"symbol": {"width": 60, "anchor": "w"}})
                alignments.update({"CostBase": {"width": 90, "anchor": "w"}})
                alignments.update({"Exdiv.": {"width": 60, "anchor": "center"}})
                alignments.update({"Year": {"width": 60, "anchor": "e"}})
                alignments.update({"%Yield": {"width": 70, "anchor": "e"}})

                columns.extend(list(alignments.keys()))

                tree = CustomTreeview(
                    master=frm1,
                    columns=columns,
                    fixed_columns=fixed_columns,
                    fixed_row=True,
                    show_vscroll=True,
                    show_hscroll=True,
                    height=17,
                    column_alignments=alignments,
                    style="Treeview",
                )

                tree.tree_fixed.bind(
                    "<<TreeviewSelect>>",
                    lambda event: item_selected(event, tree.tree_fixed, windows),
                )

                # construye e inserta symbol y proyecta los dividends
                resumen_mes, producto, costobase, min_base, ticket = (
                    [0] * 12,
                    0.0,
                    0.0,
                    pow(10, 9),
                    "",
                )
                book = resumen_cartera(option=option, meses=meses)

                for symbol, activo in book.items():
                    t_symbol, total = [""] * 12, 0.0
                    for i in range(12):
                        t_symbol[i] = (
                            "{:4.1f}".format(activo["dividends"][i])
                            if activo["dividends"][i] > 0
                            else ""
                        )
                        resumen_mes[i] += activo["dividends"][i]

                    total_row = "{:4.1f}".format(sum(activo["dividends"]))
                    costo = "{:9.1f}".format(activo["costobase"])
                    producto += sum(activo["dividends"])
                    costobase += activo["costobase"]
                    if min_base > activo["costobase"]:
                        min_base = activo["costobase"]
                        ticket = symbol

                    rend = "{:4.2%}".format(activo["yield"])
                    values = [
                        symbol,
                        costo,
                        activo["exdiv"],
                        total_row,
                        rend,
                    ] + t_symbol
                    tree.insert_row(values=values)

                # totaliza e inserta en heard
                total = "{:4.1f}".format(sum(resumen_mes))
                costo = "{:9.1f}".format(costobase)
                rend = "{:4.2%}".format(sum(resumen_mes) / costobase)
                t_symbol = ["{:4.1f}".format(s) for s in resumen_mes]

                summary = ["", costo, "", total, rend] + t_symbol
                tree.insert_row(summary=summary)

                # gráfica symbol con menor base de inversión
                grafico_rendimiento_symbol(symbol=ticket, windows=windows)
            except EncodingWarning as e:
                print("treeview_dividendos(): {}".format(e))

        def treeview_sector(option=None, windows=None):
            try:
                # Configurar el Treeview para usar los scrollbars
                columns, meses = [], meses_list(mask="%b")
                fixed_columns = [
                    "Sector",
                    "symbol",
                    "CostBase",
                    "Exdiv.",
                    "Year",
                    "%Yield",
                ]
                alignments = {mes: {"width": 90, "anchor": "e"} for mes in meses}
                alignments.update({"Sector": {"width": 150, "anchor": "w"}})
                alignments.update({"symbol": {"width": 50, "anchor": "w"}})
                alignments.update({"CostBase": {"width": 90, "anchor": "w"}})
                alignments.update({"Exdiv.": {"width": 60, "anchor": "center"}})
                alignments.update({"Year": {"width": 60, "anchor": "e"}})
                alignments.update({"%Yield": {"width": 70, "anchor": "e"}})

                columns.extend(list(alignments.keys()))
                tree = CustomTreeview(
                    master=frm1,
                    columns=columns,
                    fixed_columns=fixed_columns,
                    fixed_row=True,
                    show_vscroll=True,
                    show_hscroll=True,
                    height=17,
                    column_alignments=alignments,
                    style="Treeview",
                )

                tree.tree_fixed.bind(
                    "<<TreeviewSelect>>",
                    lambda event: item_selected(event, tree.tree_fixed, windows),
                )

                # construye e inserta symbol y proyecta los dividends
                resumen_mes, producto, costobase = [0] * 12, 0.0, 0.0
                book = resumen_cartera(option="Sector", meses=meses)
                sector, div_sector, min_base, ticket = "", 0.0, pow(10, 9), ""

                for symbol, activo in book.items():

                    if activo["sector"] != sector:
                        sector, values = activo["sector"], [""] * 17
                        values[0] = sector
                        tree.insert_row(texto=sector, padre=None, values=values)

                    t_symbol, total = [""] * 12, 0.0
                    for i in range(12):
                        t_symbol[i] = (
                            "{:4.1f}".format(activo["dividends"][i])
                            if activo["dividends"][i] > 0
                            else ""
                        )
                        resumen_mes[i] += activo["dividends"][i]

                    if min_base > activo["costobase"]:
                        min_base = activo["costobase"]
                        ticket = symbol

                    total_row = "{:4.1f}".format(sum(activo["dividends"]))
                    costo = "{:9.1f}".format(activo["costobase"])
                    producto += sum(activo["dividends"])
                    costobase += activo["costobase"]
                    rend = "{:4.2%}".format(activo["yield"])

                    values = [
                        "",
                        symbol,
                        costo,
                        activo["exdiv"],
                        total_row,
                        rend,
                    ] + t_symbol
                    tree.insert_row(texto=None, padre=sector, values=values)

                # totaliza e inserta en heard
                total = "{:4.1f}".format(sum(resumen_mes))
                costo = "{:9.1f}".format(costobase)
                rend = "{:4.2%}".format(sum(resumen_mes) / costobase)
                t_symbol = ["{:4.1f}".format(s) for s in resumen_mes]
                summary = ["", "", costo, "", total, rend] + t_symbol
                tree.insert_row(summary=summary)

                # gráfica symbol con menor base de inversión
                grafico_rendimiento_symbol(symbol=ticket, windows=windows)
            except EncodingWarning as e:
                print("treeview_sector(): {}".format(e))

        def treeview_TipoActivo(option=None, windows=None):
            try:
                # Configurar el Treeview para usar los scrollbars
                columns, meses = [], meses_list(mask="%b")
                fixed_columns = [
                    "Activo",
                    "symbol",
                    "CostBase",
                    "Exdiv.",
                    "Year",
                    "%Yield",
                ]
                alignments = {mes: {"width": 90, "anchor": "e"} for mes in meses}
                alignments.update({"Tipo Activo": {"width": 60, "anchor": "w"}})
                alignments.update({"symbol": {"width": 150, "anchor": "w"}})
                alignments.update({"CostBase": {"width": 90, "anchor": "w"}})
                alignments.update({"Exdiv.": {"width": 60, "anchor": "center"}})
                alignments.update({"Year": {"width": 60, "anchor": "e"}})
                alignments.update({"%Yield": {"width": 70, "anchor": "e"}})

                columns.extend(list(alignments.keys()))
                tree = CustomTreeview(
                    master=frm1,
                    columns=columns,
                    fixed_columns=fixed_columns,
                    fixed_row=True,
                    show_vscroll=True,
                    show_hscroll=True,
                    height=17,
                    column_alignments=alignments,
                    style="Treeview",
                )

                tree.tree_fixed.bind(
                    "<<TreeviewSelect>>",
                    lambda event: item_selected(event, tree.tree_fixed, windows),
                )

                # construye e inserta symbol y proyecta los dividends
                resumen_mes, producto, costobase = [0] * 12, 0.0, 0.0
                book = resumen_cartera(option="Activo", meses=meses)
                TActivo, div_sector, min_base, ticket = "", 0.0, pow(10, 9), ""

                for symbol, activo in book.items():

                    if activo["activo"] != TActivo:
                        TActivo, values = activo["activo"], [""] * 17
                        values[0] = TActivo
                        tree.insert_row(texto=TActivo, padre=None, values=values)

                    t_symbol, total = [""] * 12, 0.0
                    for i in range(12):
                        t_symbol[i] = (
                            "{:4.1f}".format(activo["dividends"][i])
                            if activo["dividends"][i] > 0
                            else ""
                        )
                        resumen_mes[i] += activo["dividends"][i]

                    if min_base > activo["costobase"]:
                        min_base = activo["costobase"]
                        ticket = symbol

                    total_row = "{:4.1f}".format(sum(activo["dividends"]))
                    costo = "{:9.1f}".format(activo["costobase"])
                    producto += sum(activo["dividends"])
                    costobase += activo["costobase"]
                    rend = "{:4.2%}".format(activo["yield"])

                    values = [
                        "",
                        symbol,
                        costo,
                        activo["exdiv"],
                        total_row,
                        rend,
                    ] + t_symbol
                    tree.insert_row(texto=None, padre=TActivo, values=values)

                # totaliza e inserta en heard
                total = "{:4.1f}".format(sum(resumen_mes))
                costo = "{:9.1f}".format(costobase)
                rend = "{:4.2%}".format(sum(resumen_mes) / costobase)
                t_symbol = ["{:4.1f}".format(s) for s in resumen_mes]
                summary = ["", "", costo, "", total, rend] + t_symbol
                tree.insert_row(summary=summary)

                # gráfica symbol con menor base de inversión
                grafico_rendimiento_symbol(symbol=ticket, windows=windows)
            except EncodingWarning as e:
                print("treeview_TipoActivo(): {}".format(e))

        try:
            # define titulo de la pantalla
            title = "Diversificación vs pago Dividendos"
            if tipo == "Sector":
                title = "Diversificación vs Performance Sector"
            elif tipo == "Activo":
                title = "Diversificación vs Tipo Activo"

            rnb = tk.Toplevel()
            dimension = "%dx%d+%d+%d" % (847, 665, self.df - 240, 65)
            rnb.geometry(dimension)
            rnb.resizable(False, False)
            rnb.attributes("-toolwindow", 1)
            rnb.config(bg=self.bgcolor)
            rnb.title(title)
            rnb.focus()
            rnb.grab_set()
            rnb.protocol("WM_DELETE_WINDOW", eexit)

            frm1 = ttk.Frame(
                rnb, padding=(2, 10, 2, 2), style="C.TFrame", width=600, height=300
            )
            frm2 = ttk.Frame(
                rnb, padding=(2, 10, 2, 2), style="C.TFrame", width=600, height=200
            )

            fr20 = ttk.Frame(frm2, padding=(0, 0, 0, 0), style="C.TFrame")
            fr21 = ttk.Frame(frm2, padding=(0, 0, 0, 0))

            frm1.pack(side=tk.TOP)
            frm2.pack(side=tk.TOP)
            fr20.pack(side=tk.LEFT)
            fr21.pack(side=tk.LEFT)

            # área y figura de graficos
            rg = Figure(figsize=(5.0, 6.0), dpi=110, layout="tight")
            rv = FigureCanvasTkAgg(rg, master=fr21)
            rg.set_facecolor(self.colors["cgcolor"])
            rv.draw()
            rv.get_tk_widget().pack()

            # detalle para el tipo de graph dividendos
            if tipo == "Dividendos":
                treeview_dividendos(option=tipo, windows=fr20)

            # detalle para el tipo de graph sector
            elif tipo == "Sector":
                treeview_sector(option=tipo, windows=fr20)

            # detalle para el tipo de graph activo
            elif tipo == "Activo":
                treeview_TipoActivo(option=tipo, windows=fr20)

            # boton de salida ---------------------------------------------------------------------------------------------------
            ft1 = tk.Button(
                fr20,
                text="Cancel",
                width=8,
                bg="gray",
                fg="white",
                command=lambda: eexit(),
            )
            ft1.grid(pady=10)
        except EncodingWarning as e:
            print("detalle_graph(): {}".format(e))

    # performace de  ultimos n meses
    def setup_graph_region(self, tipo=None):

        parm = {
            "titulo": "Ingresos",
            "periodo": tipo,
            "cchart": self.cchart,
            "legend": "upper right",
            "aspect": 0.60,
        }
        Agente_income_Manager(fg=self.rg0, parm=parm)
        self.rv0.draw()

    # graficos windows main
    def graficos_main(self):

        # inicia performace de  ultimos 6 meses
        self.setup_graph_region(tipo="6")

        # indicador de miedo y VIX
        parm = {
            "titulo": "CNN Fear and Greed Index",
            "cchart": self.cchart,
            "legend": "upper right",
            "aspect": 0.60,
        }
        setup_fear_greed(fg=self.rg1, parm=parm)
        self.rv1.draw()

        # Diversificación por dividendo
        parm = {
            "titulo": "Proyección y Cobro Dividendos",
            "account": "U4214563",
            "vehiculo": "Stock",
            "cchart": self.cchart,
            "legend": "outside upper right",
            "aspect": 0.35,
        }
        grupo_dividendo(fg=self.rg2, parm=parm)
        self.rv2.draw()

        # Diversificación por sector
        parm = {
            "titulo": "Diversificación vs Sector",
            "cchart": self.cchart,
            "aspect": 0.30,
        }
        grupo_sector(fig=self.rg3, parm=parm)
        self.rv3.draw()

        # Diversificación vs. tipo activo
        xestrategia = self.Estrategia.read()
        parm = {
            "titulo": "Diversificación vs Activos",
            "cchart": self.cchart,
            "legend": "outside upper right",
            "aspect": 0.30,
        }
        char_estrategia(fg=self.rg4, parm=parm, strategy=xestrategia)
        self.rv4.draw()

        # Diversificación vs. región
        parm = {
            "titulo": "Diversificación vs Región",
            "cchart": self.cchart,
            "legend": "outside upper right",
            "aspect": 0.30,
        }
        grupo_region(fg=self.rg5, strategy=xestrategia, parm=parm)
        self.rv5.draw()

        # mantiene actualizado los graficos cada 20m o 1200.000ms
        self.root.after(1200000, lambda: self.graficos_main())
        # DataHub.manager_after._safe(1200000, self.graficos_main(), name="graficos_main")

    # Detener cada módulo de forma ordenada
    def eexit(self):

        # DataHub.manager_after.after_cancel_all()
        self.root.destroy()

        # cierra todos los threads & Job's pendientes
        DataHub.manager_events.stop_all()

    # Inicia el dashboard
    def run(self):

        # inicializa logging y excepciones globales ------------------------------------------------------------------
        debug = Debugging(DisplayConsole=False, GlobalHub=DataHub)

        # monitorea CPU/RAM cada 5s
        DataHub.manager_events.register_thread(
            name="SystemMonitor",
            target=debug.monitor_system,
            interval=5,
        )

        DataHub.logger = debug.logger
        DataHub.DCpu = debug.cpu_data
        DataHub.DMem = debug.mem_data
        DataHub.CpuLock = debug.lock
        DataHub.display = debug.display
        DataHub.max_points = debug.max_points

        # define widget principales Crypto ---------------------------------------------------------------
        self.sesion_crypto = self.PlanInversion.select_sesion(
            datetime.now(), accion="select", vehiculo="Crypto"
        )
        self.start_crypto(account=self.sesion_crypto["idcuenta"], vehiculo="Crypto")
        self.graficos_main()

        # define widget principales Stock-----------------------------------------------------------------
        self.sesion_stock = self.PlanInversion.select_sesion(
            datetime.now(), accion="select", vehiculo="Stock"
        )
        self.start_stock(account=self.sesion_stock["idcuenta"], vehiculo="Stock")

        # inicia otros modulos ---------------------------------------------------------------------------
        self.gestion = GestionInversion(
            parent=self.root, master=self.win3, colores=self.colors
        )
        self.gestion.pack()

        self.fci = ArsFondosInversion(
            parent=self.root, master=self.win4, colores=self.colors
        )
        self.fci.pack()

        self.system = system_status(master=self.win5, colores=self.colors)

        self.screener = Screener(
            master=self.win2, account=self.sesion_stock["idcuenta"], colors=self.colors
        )
        self.screener.pack()

        # Start ayudante y agentes del sistema------------------------------------------------------------
        self.start_chatbot()

        self.root.mainloop()


# clase paar monitorear el estado del sistema
class system_status(tk.Frame):
    def __init__(self, master=None, colores=None):
        self.system = master
        self.colors = colores
        self.itemsInfo = None

        self.process = ttk.Frame(self.system, padding=(1, 10, 1, 1), style="C.TFrame")
        self.right = ttk.Frame(self.system, padding=(1, 10, 1, 1), style="C.TFrame")
        self.bottom = ttk.Frame(self.system, padding=(1, 1, 1, 1), style="C.TFrame")

        self.datahub = ttk.Frame(self.bottom, padding=(1, 1, 1, 1), style="C.TFrame")
        self.cache = ttk.Frame(self.bottom, padding=(1, 1, 1, 1), style="C.TFrame")
        self.figura = ttk.Frame(self.right, padding=(5, 1, 1, 5), style="C.TFrame")
        self.performa = ttk.Frame(self.right, padding=(1, 1, 1, 1), style="C.TFrame")
        self.debugging = ttk.Frame(self.right, padding=(1, 1, 1, 1), style="C.TFrame")
        self.connect = ttk.Frame(self.right, padding=(1, 1, 1, 1), style="C.TFrame")

        # establece figura performance system
        self.fg = Figure(figsize=(3.8, 1.7), dpi=110, layout="tight")
        self.rv = FigureCanvasTkAgg(self.fg, master=self.right)
        self.fg.set_facecolor("DodgerBlue")

        self.rv.draw()
        self.rv.get_tk_widget().pack()

        self.performa.pack(fill=tk.X)
        self.debugging.pack(fill=tk.X)
        self.figura.pack(fill=tk.X)
        self.connect.pack(side=tk.RIGHT, fill="both")

        self.right.pack(side=tk.RIGHT, fill="both")
        self.process.pack(side=tk.TOP, fill="both")
        self.bottom.pack(side=tk.BOTTOM, fill="both")
        self.datahub.pack(side=tk.LEFT, fill="both")
        self.cache.pack(side=tk.LEFT, fill="both")

        self.process_system()

    # detalla los procesos y schedule del system
    def process_system(self):
        # extrae information de thread y schedule
        def obtener_datos():
            nonlocal procesos
            try:

                procesos = {"widget": {}, "thread": {}, "jobs": {}}

                # Ordena los threads por nombre antes de procesarlos
                for keys in sorted(threading.enumerate(), key=lambda t: t.name):
                    # obtiene contador de actividad (Running) para el job
                    itera = DataHub.update_self_procesos(
                        proces="thread", tarea=keys.name
                    )
                    status = f"Run({itera})" if keys.is_alive() else "Stop()"

                    # cuando existe la task en DataHub
                    if keys.ident in procesos["thread"]:
                        procesos["thread"][keys.ident].update(
                            {"tarea": keys.name, "params": status}
                        )
                    else:
                        # casos donde nose a agregado la task en DataHub
                        procesos["thread"].update(
                            {keys.ident: {"tarea": keys.name, "params": status}}
                        )

                # Ordena los jobs por tag antes de mostrar
                jobs_sorted = sorted(
                    schedule.jobs, key=lambda job: list(job.tags)[0] if job.tags else ""
                )

                for job in jobs_sorted:
                    # obtiene contador de actividad (Running) para el job
                    job_tags = list(job.tags)[0]
                    itera = DataHub.update_self_procesos(
                        proces="running", tarea=job_tags
                    )

                    if job_tags in procesos["jobs"]:
                        procesos["jobs"][job_tags].update(
                            {
                                "tarea": job.next_run,
                                "params": f"Run({itera}), cada: {job.interval}/{job.unit[0]}",
                            }
                        )
                    else:
                        procesos["jobs"].update(
                            {
                                job_tags: {
                                    "tarea": job.next_run,
                                    "params": f"Run({itera}), cada: {job.interval}/{job.unit[0]}",
                                }
                            }
                        )

                # cargar datos de widget
                widget = [item for item in DataHub.procesos if "widget" in item]

                # Ordena el arreglo widget por keys antes de procesarlo
                for proceso in sorted(
                    widget, key=lambda x: list(x["widget"].keys())[0]
                ):
                    grupo = proceso["widget"]
                    for task in sorted(grupo.keys()):
                        values = grupo[task]
                        name = task.split("_", 1)[1]
                        status = f"Run({values})"
                        procesos["widget"].update(
                            {name: {"tarea": task, "params": status}}
                        )

                return procesos
            except (EncodingWarning, Exception) as e:
                print(f"obtener_datos(): {e}")

        def buscar_item_treeview(keys=None, iid=None, sobre="text"):
            for item_id in tree.get_children(padre[keys]):
                info = tree.item(item_id)
                if info["text"] == iid:
                    return item_id
                elif info["values"][0] == iid:
                    return item_id

            return None

        # control para mantener lista de procesos actualizados
        def delete_items():
            nonlocal contador

            if contador > limite - 1:
                for padre_id in tree.get_children():
                    for item_id in tree.get_children(padre_id):
                        tree.delete(item_id)
                return tree

        # reset de control de procesos actualizados
        def reset_contador():
            nonlocal contador

            contador += 1
            if contador > limite:
                contador = 0
            return contador

        # update de treeview
        def update_status():
            obtener_datos()

            # verifica si es tiempo de refrescar lista
            delete_items()

            # mueve nuevos valores de proceso a treeview
            for keys, grupo in procesos.items():

                if (
                    keys == "thread"
                ):  # ------------------------------------------------------------------------------
                    for clave, vals in grupo.items():
                        if vals["params"] == "Stop()":
                            pass
                        if vals["params"] != "Stop()":
                            Bitems = buscar_item_treeview(keys=keys, iid=clave)
                            if Bitems is None:
                                tree.insert(
                                    Thread,
                                    "end",
                                    text=clave,
                                    values=(vals["tarea"], vals["params"]),
                                )
                            else:
                                tree.item(
                                    Bitems,
                                    values=(
                                        vals["tarea"],
                                        vals["params"],
                                    ),
                                )

                if keys == "jobs":
                    for clave, vals in grupo.items():
                        Bitems = buscar_item_treeview(
                            keys=keys, iid=clave, sobre="values"
                        )

                        if Bitems is None:
                            tree.insert(
                                Jobs,
                                "end",
                                text=vals["tarea"],
                                values=(clave, vals["params"]),
                            )
                        else:
                            tree.item(
                                Bitems,
                                text=vals["tarea"],
                                values=(
                                    clave,
                                    vals["params"],
                                ),
                            )

                if keys == "widget":
                    for clave, vals in grupo.items():
                        Bitems = buscar_item_treeview(keys=keys, iid=clave)

                        if Bitems is None:
                            tree.insert(
                                Widget,
                                "end",
                                text=clave,
                                values=(vals["tarea"], vals["params"]),
                            )
                        else:
                            tree.item(
                                Bitems,
                                values=(
                                    vals["tarea"],
                                    vals["params"],
                                ),
                            )

            reset_contador()
            self.system.after(2000, update_status)
            # DataHub.manager_after._safe(2000, update_status(), name="update_status")

        try:
            # Configurar el Treeview
            cols = ["Tarea", "Parámetros"]
            tree = ttk.Treeview(self.process, columns=cols, height=18, style="TFrame")
            for i, fields in enumerate(cols):
                if i == 0:
                    tree.heading("#0", text="Id - proceso")
                    tree.column("#0", width=60, minwidth=60)

                tree.heading(fields, text=fields)
                tree.column(fields, width=80, minwidth=80)
            tree.pack(fill="both")

            Widget = tree.insert("", "end", text="Widget", values=("", ""))
            Thread = tree.insert("", "end", text="Thread", values=("", ""))
            Jobs = tree.insert("", "end", text="Schedule", values=("", ""))
            padre = {"thread": Thread, "jobs": Jobs, "widget": Widget}

            tree.item(Widget, open=True)
            tree.item(Thread, open=True)
            tree.item(Jobs, open=True)

            # declara y Expande los hijos de tree
            procesos, contador, limite = {}, 0, 21

            # mustra e iterea los moitores del sistema -------------------------------------------------------------------------
            self.datahub_system()
            self.connect_api()
            self.debugging_system()
            # self.monitor_realtime()
            self.monitor_cache()
            update_status()
        except (EncodingWarning, Exception) as e:
            print(f"process_system(): {e}")

    # modulo principal para recorre Datahub()
    def datahub_system(self):

        # Selecciona y actualiza el detalle del primer elemento.
        def display_first_item():

            symbol = search_lista(first=True)
            display_items_lista(symbol)
            self.itemsInfo = symbol

        # display items del activo
        def display_items_lista(symbol):

            # Limpiar el treeview de detalles
            for item in detalle.get_children():
                detalle.delete(item)

            # fija timestamp para el gryupo de datos
            Shora = DataHub.info[symbol]["websocket"]["timestamp"]
            detalle.insert(
                "", "end", text=f"Update: {Shora} - {symbol}", tags=("colorTex",)
            )

            # Display detalle del activo
            for key, value in DataHub.info[symbol].items():
                if isinstance(value, dict):
                    node = detalle.insert("", "end", text=key, tags=("colorGroup",))

                    # detalle.item(node, open=True)
                    for fields, valor in value.items():
                        detalle.insert(
                            node, "end", text=f"{fields}: {valor}", tags=("colorTex",)
                        )
                else:
                    if isinstance(value, pd.DataFrame):
                        df = {
                            "DataFrames": {
                                "Rows": value.shape[0],
                                "Columns": value.columns,
                            }
                        }
                        detalle.insert(
                            "", "end", text=f"{key}: {df}", tags=("colorTex",)
                        )
                    else:
                        detalle.insert(
                            "", "end", text=f"{key}: {value}", tags=("colorTex",)
                        )

        # Obtener el ítem seleccionado (la tupla de IDs de la selección)
        def on_item_selected(event):

            selected_items = lista.selection()
            if selected_items:
                selected_id = selected_items[0]

                symbol = lista.item(selected_id, "text")
                if symbol in DataHub.info:
                    display_items_lista(symbol)

        # busca activo en lista
        def search_lista(first=None, symbol=None):
            log = False
            for padre_id in lista.get_children():
                padre = lista.item(padre_id, "text")
                for item_id in lista.get_children(padre_id):
                    if first is None:
                        if symbol == lista.item(item_id, "text"):
                            log = True
                            break
                    elif first is not None:
                        # return first de la lista
                        if padre != lastClose:
                            return lista.item(item_id, "text")
            return log

        # inserta lista los values de campo
        def insert_process(parent):
            for key, campo in DataHub.last_process.items():
                if isinstance(campo, dict):
                    lista.insert(
                        parent,
                        "end",
                        text=f" {key}: {campo['diaria_book_performance'].date()}",
                        tags=("colorTex",),
                    )

        # recorre e inserta hijos por cada nodo
        def insert_lista(parent=None, struct="info()"):

            if struct == "Last Daily()":
                # for padre_id in lista.get_children():
                #    if ": Last Process " = lista.item(padre_id, "text")

                # for item_id in lista.get_children(padre_id):
                #    lista.item(item_id, textalues=(nuevos_datos["nombre"],))
                pass

            elif struct == "info()":
                for key, value in DataHub.info.items():

                    if key == "TimeDataHub":
                        continue
                    else:
                        if not search_lista(symbol=key):
                            lista.insert(parent, "end", text=key)

                # start con la infor del primer Items
                if not self.itemsInfo:
                    display_first_item()
                else:
                    display_items_lista(self.itemsInfo)

            return lista

        # Itera  y update Treeview cada 3 seg
        def update_datahub():

            lista.item(root, open=True)
            insert_lista(parent=root)
            self.system.after(30000, update_datahub)
            # DataHub.manager_after._safe(30000, update_datahub(), name="update_datahub")

        try:
            # define TreeView para mostras  Lista y detalle de items DataHub.Info()
            lista = ttk.Treeview(self.datahub, height=18, style="TFrame")
            detalle = ttk.Treeview(self.datahub, height=18, style="TFrame")

            lista.heading("#0", text="DataHub")
            detalle.heading("#0", text="Información del Activo")

            lista.pack(side=tk.LEFT, pady=10)
            detalle.pack(side=tk.LEFT, expand=True, fill="both", pady=10)
            detalle.tag_configure("colorTex", foreground="orange")
            detalle.tag_configure("colorGroup", foreground=DataHub.bgcolor)
            lista.bind("<<TreeviewSelect>>", on_item_selected)

            # inicia insert de lista
            lastClose = ": Close Market(last) "
            process = lista.insert("", "end", text=lastClose)
            insert_process(process)

            root = lista.insert("", "end", text=f": {DataHub.info['TimeDataHub']}")

            update_datahub()
        except (EncodingWarning, Exception) as e:
            print("datahub_system(): {}".format(e))

    # detalla uso de cache
    def monitor_cache(self):
        """
        Clase para monitorear el estado del sistema y visualizar el contenido del TTLCache.
        Permite:
            ✅ Ver claves actuales del cache
            ✅ Refrescar el contenido
            ✅ Eliminar entradas manualmente
            ✅ Ver los primeros registros de un DataFrame asociado
        """

        #   FUNCIONALIDAD PRINCIPAL
        def refresh_cache():
            """Recarga la lista de claves desde el cache."""
            for item in tree.get_children():
                self.tree.delete(item)

            for k, v in CacheHut.cache.items():
                tipo = type(v).__name__
                tree.insert(
                    "",
                    tk.END,
                    values=(str(k), tipo, datetime.now().strftime("%H:%M:%S")),
                )

        def remove_selected_key():
            """Elimina la clave seleccionada del cache."""
            item = tree.selection()
            if not item:
                self.messagebox.showinfo(
                    "Información", "Seleccione una clave para eliminar."
                )
                return

            key = tree.item(item[0], "values")[0]
            if key in CacheHut.cache:
                del CacheHut.cache[key]
                self.messagebox.showinfo(
                    "Cache", f"✅ Clave '{key}' eliminada del cache."
                )
                self.refresh_cache()
            else:
                self.messagebox.showwarning(
                    "Cache", f"⚠️ Clave '{key}' no encontrada o ya expirada."
                )

        #   EVENTOS DE INTERFAZ
        def _on_double_click(event):
            """Maneja doble clic sobre una clave: muestra el DataFrame si existe."""
            item = tree.selection()
            if not item:
                return

            key = tree.item(item[0], "values")[0]
            df = CacheHut.cache.get(key)

            if isinstance(df, pd.DataFrame):
                self._show_dataframe(df, str(key))
            else:
                self.messagebox.showwarning(
                    "Cache", f"La clave '{key}' no contiene un DataFrame."
                )

        #   VISUALIZACIÓN DE DATAFRAME
        def _show_dataframe(df: pd.DataFrame, title="DataFrame"):
            """Muestra un DataFrame en una nueva ventana."""
            win = tk.Toplevel(self.root)
            win.title(f"📊 Vista de Datos - {title}")
            win.geometry("900x450")

            # Convertir a texto
            text = tk.Text(win, wrap="none", font=("Consolas", 10))
            text.pack(fill=tk.BOTH, expand=True)

            # Mostrar primeras filas
            content = df.head(50).to_string()
            text.insert("1.0", content)

            # Scrollbars
            yscroll = ttk.Scrollbar(win, orient="vertical", command=text.yview)
            yscroll.pack(side="right", fill="y")
            text.configure(yscrollcommand=yscroll.set)

            ttk.Button(win, text="Cerrar", command=win.destroy).pack(
                side="bottom", pady=5
            )

        try:

            # --- Tabla de claves ---
            tree = ttk.Treeview(
                self.cache,
                columns=("key", "type", "timestamp"),
                show="headings",
                style="TFrame",
            )
            tree.heading("key", text="Clave de Cache")
            tree.heading("type", text="Tipo de Dato")
            tree.heading("timestamp", text="Hora de Registro")
            tree.pack(fill=tk.BOTH, expand=True)

            # --- Scrollbars ---
            hsb = ttk.Scrollbar(tree, orient=tk.HORIZONTAL, command=tree.yview)
            tree.configure(xscroll=hsb.set)
            hsb.pack(side=tk.BOTTOM, fill=tk.X)

            # --- Botonera ---
            frame_btn = ttk.Frame(self.cache)
            frame_btn.pack(fill=tk.X, pady=5)

            ttk.Button(frame_btn, text="🔄 Refrescar", command=refresh_cache).pack(
                side=tk.LEFT, padx=5
            )
            ttk.Button(
                frame_btn, text="🧹 Eliminar Clave", command=remove_selected_key
            ).pack(side=tk.LEFT, padx=5)
            # ttk.Button(frame_btn, text="❌ Cerrar", command=cache.destroy).pack(
            #    side=tk.RIGHT, padx=5
            # )

            # --- Bind para doble clic ---
            tree.bind("<Double-1>", _on_double_click)

            # --- Carga inicial ---
            refresh_cache()
        except (EncodingWarning, Exception) as e:
            print(f"monitor_cache(): {e}")

    # detalla estados de conexiones
    def connect_api(self):
        try:

            tree = ttk.Treeview(self.connect, height=10, style="TFrame")
            tree.heading("#0", text="Estados Connect")
            tree.pack(fill="both")

            api = {"Binance": True, "Ibrks": True, "Yfinance": True, "Finviz": True}
            for key, value in api.items():
                tree.insert("", "end", text=f"{key}: {value}")

        except (EncodingWarning, Exception) as e:
            print("connect_api(): {}".format(e))

    # detalla estados de conexiones
    def debugging_system(self):
        try:

            cols = ["Option"]
            tree = ttk.Treeview(self.performa, columns=cols, height=8, style="TFrame")
            tree.heading("#0", text="Debugging")
            tree.heading("Option", text="Option")

            tree.column("#0", width=100, minwidth=100)
            tree.column("Option", width=10, minwidth=10)
            tree.pack(expand=True, fill="both", pady=10)

            for key, handler in DataHub.logger.items():
                tree.insert(
                    "",
                    "end",
                    text=f"{key}",
                    values=f"{logging.getLevelName(handler.level)}",
                )

        except (EncodingWarning, Exception) as e:
            print("debugging_system(): {}".format(e))

    # plot uso %CPU y %RAM
    def monitor_realtime(self):
        """
        Dibuja el gráfico en tiempo real de CPU y RAM.
        """

        # valida se debe mostrar o no performance
        if not DataHub.display:
            return

        # variables de entorno
        colorfondo = DataHub.cchart["plot5"]
        colorCpu = DataHub.cchart["plot4"]
        colorRam = DataHub.cchart["plot2"]
        ColorAx = DataHub.cchart["texto"]
        ColorAy = DataHub.cchart["texto"]
        ColorTt = DataHub.cchart["titulo"]

        self.fg.clear()
        self.ax = self.fg.add_subplot()
        self.ax.set_facecolor(colorfondo)

        # plot graficos
        (line_cpu,) = self.ax.plot([], [], color=colorCpu)
        (line_mem,) = self.ax.plot([], [], color=colorRam)
        yTicks = [0, 25, 50, 75, 100]

        # legend y label
        p_legend, etiquetas = [], ["Cpu %", "Ram %"]
        p_legend.append(mpatches.Patch(color=colorCpu, label=etiquetas[0]))
        p_legend.append(mpatches.Patch(color=colorRam, label=etiquetas[1]))

        self.ax.set_ylim(0, 100)

        self.ax.set_xlim(0, DataHub.max_points)
        self.ax.set_xlabel("Tiempo (últimos segundos)", fontsize=7, color=ColorAx)
        self.ax.set_ylabel("Uso (%)", fontsize=7, color=ColorAy)
        self.ax.grid(True, color=ColorAy, linewidth=0.1)
        self.ax.spines[["top", "right"]].set_visible(False)

        plt.setp(self.ax.get_xticklabels(), ha="right", fontsize=6, color=ColorAx)
        plt.setp(self.ax.get_yticklabels(), ha="right", fontsize=6, color=ColorAy)
        plt.yticks(yTicks)

        self.fg.legend(loc="upper right", handles=p_legend, fontsize=6)
        self.fg.suptitle("Monitor de CPU y Memoria", fontsize="medium", color=ColorTt)

        # toma series de datos desde DataHub
        def update(frame):
            with DataHub.CpuLock:
                x = list(range(len(DataHub.DCpu)))
                line_cpu.set_data(x, DataHub.DCpu)
                line_mem.set_data(x, DataHub.DMem)
                self.ax.set_xlim(0, DataHub.max_points)
            return line_cpu, line_mem

        ani = animation.FuncAnimation(
            self.fg,
            update,
            interval=DataHub.interval * 3000,
            blit=True,
            cache_frame_data=False,
        )
        self.rv.draw()


if __name__ == "__main__":
    app = DashMain()
    app.run()
