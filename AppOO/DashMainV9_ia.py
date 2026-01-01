from Class_debugging import ManagerEvents, MangerAfterEvents, Debugging
from Class_DataFrame import (
    grupo_activos,
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
    ProgressBar,
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
    filedialog,
    traceback,
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

            except Exception as e:
                print("[procesa_stock()]: {}".format(e))

        def decodifica_message_websocket(x_message):
            """
            Decodifica mensajes del websocket de Interactive Brokers y actualiza precios.

            Args:
                x_message: Mensaje JSON del websocket con datos de mercado

            Returns:
                tuple: (x_dato, x_conid, x_symbol) con información procesada
            """
            # Mapeo de campos lógicos a códigos IB API
            FIELD_MAP = {
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
                "categoria": "7281",
                "dividendos": "7286",
                "%dDividendos": "7287",
                "ExDividendos": "7288",
                "TTMDividemdos": "7672",
                "NextDividendos": "7671",
            }

            # Campos numéricos que requieren conversión a float
            NUMERIC_FIELDS = {
                "last",
                "change",
                "bid",
                "ask",
                "open",
                "close",
                "high",
                "low",
                "costobase",
                "stock",
                "dividendos",
                "%dDividendos",
                "TTMDividemdos",
                "NextDividendos",
            }

            # Campos de texto (sin conversión numérica)
            STRING_FIELDS = {"symbol", "empresa", "ExDividendos"}

            # Mapeo de campos IB a nombres internos para dividendos
            DIVIDEND_FIELD_MAPPING = {
                "dividendos": "dividendo",
                "%dDividendos": "dividend_yield",
                "ExDividendos": "ex_dividend_date",
                "TTMDividemdos": "ttm_dividends",
                "NextDividendos": "next_dividend",
            }

            def update_field(conid, field_name, api_code, convert_to_float=True):
                """
                Actualiza un campo en self.conid_inicio si existe en el mensaje.

                Args:
                    conid: Contract ID del activo
                    field_name: Nombre del campo interno
                    api_code: Código del campo en IB API
                    convert_to_float: Si True, convierte a float (para campos numéricos)
                """
                if api_code not in x_message:
                    return

                value = x_message[api_code]

                if convert_to_float:
                    # Caso especial: dividend_yield viene como "6.6%" (string con %)
                    if field_name == "dividend_yield" and isinstance(value, str):
                        try:
                            # Remover el % y convertir a float
                            self.conid_inicio[conid][field_name] = float(
                                value.rstrip("%")
                            )
                        except (ValueError, AttributeError):
                            self.conid_inicio[conid][field_name] = 0.0
                    elif is_numeric(value):
                        self.conid_inicio[conid][field_name] = float(value)
                else:
                    self.conid_inicio[conid][field_name] = value

            try:
                x_conid, x_symbol, x_dato = None, None, {}

                if "conidEx" not in x_message:
                    return x_dato, x_conid, x_symbol

                x_conid = x_message["conidEx"]

                # Inicializar estructura de datos si no existe
                if x_conid not in self.conid_inicio:
                    self.conid_inicio[x_conid] = {
                        "symbol": None,
                        "empresa": None,
                        "last": 0.0,
                        "change": 0.0,
                        "open": 0.0,
                        "close": 0.0,
                        "bid": 0.0,
                        "ask": 0.0,
                        "high": 0.0,
                        "low": 0.0,
                        "costobase": 0.0,
                        "stock": 0.0,
                        # Campos de dividendos de IB API
                        "dividendo": 0.0,  # 7286: Dividendo actual
                        "dividend_yield": 0.0,  # 7287: % Dividend yield
                        "ex_dividend_date": None,  # 7288: Ex-dividend date
                        "ttm_dividends": 0.0,  # 7672: TTM Dividends
                        "next_dividend": 0.0,  # 7671: Next dividend amount
                    }

                # Procesar campos de texto
                for field in STRING_FIELDS:
                    internal_name = DIVIDEND_FIELD_MAPPING.get(field, field)
                    update_field(
                        x_conid, internal_name, FIELD_MAP[field], convert_to_float=False
                    )

                # Procesar campos numéricos
                for field in NUMERIC_FIELDS:
                    internal_name = DIVIDEND_FIELD_MAPPING.get(field, field)
                    update_field(
                        x_conid, internal_name, FIELD_MAP[field], convert_to_float=True
                    )

                # Procesar timestamp
                timestamp = x_message["_updated"] / 1000  # Convertir a segundos
                timestamp_str = datetime.fromtimestamp(timestamp).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                # Preparar datos de salida
                x_precio = self.conid_inicio[x_conid].copy()
                x_precio["timestamp"] = timestamp_str
                x_symbol = self.conid_inicio[x_conid]["symbol"]

                if x_symbol:
                    x_dato[x_symbol] = x_precio

                return x_dato, x_conid, x_symbol

            except Exception as e:
                print(f"[decodifica_message_websocket()]: {e} {x_dato}")
                return {}, None, None

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
            except Exception as e:
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

    # mantiene self.position igual a la tabla inversionesError
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
    # Helper: obtiene conid desde symbol buscando en positions
    def _get_conid_from_symbol(self, symbol):
        """
        Busca el conid correspondiente a un símbolo en self.positions.

        Args:
            symbol: Símbolo del activo (ej: "AAPL", "MSFT")

        Returns:
            conid si se encuentra, None si no existe
        """
        try:
            for position in self.positions:
                if position["ticket"] == symbol:
                    return position["conid"]
            return None
        except Exception as e:
            print(f"[_get_conid_from_symbol({symbol})]: {e}")
            return None

    # Helper: calcula meses de pago desde ex-dividend date
    def _parse_ib_date(self, date_str):
        """
        Parsea fecha de IB en formato "Mar13'26" a datetime.

        Args:
            date_str: String con formato "MonDD'YY" (ej: "Mar13'26")

        Returns:
            datetime object o None si falla
        """
        try:
            if not date_str or date_str == "":
                return None

            # Formato IB: "Mar13'26" -> Marzo 13, 2026
            exdiv_date = datetime.strptime(date_str, "%b%d'%y")
            return exdiv_date
        except Exception as e:
            print(f"[_parse_ib_date({date_str})]: {e}")
            return None

    def _calcular_meses_desde_ex_date(
        self,
        ex_dividend_date,
        dividend_yield,
        symbol=None,
        dividendo_individual=0.0,
        ttm_dividends=0.0,
    ):
        """
        Calcula los meses de pago de dividendos usando MÉTODO HÍBRIDO:
        1. Intenta obtener historial real de yfinance (más preciso)
        2. Si falla, infiere frecuencia desde datos de IB

        Args:
            ex_dividend_date: Fecha ex-dividend (formato IB "Mar13'26" o datetime)
            dividend_yield: Rendimiento del dividendo (para validar que paga)
            symbol: Símbolo del activo (para consultar yfinance)
            dividendo_individual: Dividendo por pago individual (campo 7286)
            ttm_dividends: Total anualizado TTM (campo 7672)

        Returns:
            Lista de nombres de meses donde se paga dividendo
        """
        try:
            # Si no hay dividend yield o es 0, no hay dividendos
            if not dividend_yield or dividend_yield == 0:
                return []

            # Si no hay fecha ex-dividend, retornar vacío
            if not ex_dividend_date:
                return []

            # Parsear la fecha según el tipo
            if isinstance(ex_dividend_date, datetime):
                exdiv_date = ex_dividend_date
            elif isinstance(ex_dividend_date, str):
                exdiv_date = self._parse_ib_date(ex_dividend_date)
                if not exdiv_date:
                    return []
            else:
                return []

            # MÉTODO 1: Intentar obtener historial de yfinance (solo para meses, no valores)
            if symbol:
                try:
                    import yfinance as yf

                    ticket = yf.Ticker(symbol)
                    hist = ticket.history(
                        period="2y"
                    )  # 2 años para tener suficiente historial

                    if "Dividends" in hist.columns:
                        # Filtrar solo pagos de dividendos del año pasado
                        year = pd.Timestamp.now().year - 1
                        m_div = hist[hist["Dividends"] != 0]
                        anual = m_div[m_div.index.year == year]

                        if not anual.empty:
                            # Extraer meses únicos donde hubo pagos
                            meses = list(anual.index.strftime("%B").unique())
                            if meses:
                                return meses
                except Exception as e:
                    # Si falla yfinance, continuar con método de inferencia
                    pass

            # MÉTODO 2: Inferir frecuencia desde datos de IB
            mes_exdiv = exdiv_date.strftime("%B")

            # Si tenemos TTM y dividendo individual, inferir frecuencia
            if ttm_dividends > 0 and dividendo_individual > 0:
                # Calcular cuántos pagos al año
                pagos_por_año = round(ttm_dividends / dividendo_individual)

                # Limitar a valores razonables (1, 2, 4, 12)
                if pagos_por_año >= 12:
                    # Pago mensual
                    return [
                        "January",
                        "February",
                        "March",
                        "April",
                        "May",
                        "June",
                        "July",
                        "August",
                        "September",
                        "October",
                        "November",
                        "December",
                    ]
                elif pagos_por_año >= 4:
                    # Pago trimestral - inferir desde mes ex-dividend
                    mes_num = exdiv_date.month
                    meses_trimestral = []
                    for i in range(4):
                        mes_idx = ((mes_num - 1 + i * 3) % 12) + 1
                        meses_trimestral.append(
                            datetime(2000, mes_idx, 1).strftime("%B")
                        )
                    return meses_trimestral
                elif pagos_por_año >= 2:
                    # Pago semestral
                    mes_num = exdiv_date.month
                    mes_idx2 = ((mes_num - 1 + 6) % 12) + 1
                    return [mes_exdiv, datetime(2000, mes_idx2, 1).strftime("%B")]
                else:
                    # Pago anual
                    return [mes_exdiv]

            # FALLBACK: Si no tenemos suficiente info, retornar solo mes ex-dividend
            return [mes_exdiv]

        except Exception as e:
            print(f"[_calcular_meses_desde_ex_date()]: {e}")
            return []

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
                            # EXCLUIR categoriaActivo para no sobrescribir el valor existente
                            if keys == "categoriaActivo":
                                continue

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
                    url = f"wss://localhost:{DataHub.ib_gateway_port}/v1/api/ws"
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

        # Sistema de cleanup para after() callbacks
        self.after_ids = []
        self.is_running = True

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
        self.win7 = ttk.Frame(self.nb, style="C.TFrame", width=self.dw, height=self.dh)
        self.win8 = ttk.Frame(self.nb, style="C.TFrame", width=self.dw, height=self.dh)

        # Añadir padding a los frames
        self.win0.pack(fill=tk.BOTH, expand=True)
        self.win1.pack(fill=tk.BOTH, expand=True)
        self.win2.pack(fill=tk.BOTH, expand=True)
        self.win3.pack(fill=tk.BOTH, expand=True)
        self.win4.pack(fill=tk.BOTH, expand=True)
        self.win5.pack(fill=tk.BOTH, expand=True)
        self.win6.pack(fill=tk.BOTH, expand=True)
        self.win7.pack(fill=tk.BOTH, expand=True)
        self.win8.pack(fill=tk.BOTH, expand=True)

        self.nb.add(self.win1, text="Crypto         ")
        self.nb.add(self.win0, text="Stock          ")
        self.nb.add(self.win4, text="Ars            ")
        self.nb.add(self.win7, text="Ves            ", state="disabled")
        self.nb.add(self.win8, text="Crowfonding    ", state="disabled")
        self.nb.add(self.win6, text="FuturoCrypto   ", state="disabled")
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
        topPn0 = ttk.Frame(pn0, style="C.TFrame")
        botPn0 = ttk.Frame(pn0, style="C.TFrame")
        lineLeft = ttk.Frame(topPn0, style="C.TFrame")
        lineRight = ttk.Frame(topPn0, style="C.TFrame")
        gypBottom = ttk.Frame(botPn0, style="C.TFrame")
        InvBottom = ttk.Frame(botPn0, style="C.TFrame")

        topPn0.pack(side=tk.TOP)
        botPn0.pack(side=tk.BOTTOM)
        lineLeft.pack(side=tk.LEFT, fill=tk.X)
        lineRight.pack(side=tk.RIGHT, fill=tk.X)
        gypBottom.pack(side=tk.TOP)
        InvBottom.pack(side=tk.BOTTOM)

        # información usuario -----------------------------------------------------------------------------------------
        self.line = tk.Label(
            lineLeft,
            text="Inversionista, ",
            font=("Arial", 14),
            bg=self.colors["bgcolor"],
        )
        imagen_tk = BDsystem.select_image(idd=11, size=(32, 32))

        now = datetime.now()
        self.user = tk.Button(
            lineLeft,
            image=imagen_tk,
            bg=self.colors["bgcolor"],
            relief=tk.FLAT,
            command=lambda: self.setup(),
        )
        self.user.imagen = imagen_tk

        self.line.pack(side=tk.LEFT, fill=tk.X)
        self.user.pack(side=tk.LEFT, fill=tk.X)

        # órdenes y salida del sistema --------------------------------------------------------------------------------
        imagen_tk = BDsystem.select_image(idd=14, size=(32, 32))

        self.cart = tk.Button(
            lineRight,
            image=imagen_tk,
            bg=self.colors["bgcolor"],
            relief=tk.FLAT,
            command=lambda: self.car_ordenes_activas(),
        )
        self.cart.imagen = imagen_tk

        # inserta espacios para alinear botones en la lineas
        self.line = tk.Label(lineRight, text=spaces(125), bg=self.colors["bgcolor"])
        imagen_tk = BDsystem.select_image(idd=12, size=(32, 32))

        self.exit = tk.Button(
            lineRight,
            image=imagen_tk,
            bg=self.colors["bgcolor"],
            relief=tk.FLAT,
            command=lambda: self.eexit(),
        )
        self.exit.imagen = imagen_tk
        self.exit.pack(side=tk.RIGHT, fill=tk.X)
        self.cart.pack(side=tk.RIGHT, fill=tk.X)
        self.line.pack(side=tk.RIGHT, fill=tk.X)

        # Progreso inversion gyp diarias ------------------------------------------------------------------------------
        self.GypProgress = ProgressBar(
            gypBottom,
            # 1234567890123456789012345
            label="Ganancias Diarias  ",
            avance=0,
            proyeccion=1_000,
            width=130,
            height=10,
            bg_color=self.colors["bgcolor"],
        )
        self.InvProgress = ProgressBar(
            InvBottom,
            # 1234567890123456789012345
            label="Total Inversión      ",
            avance=0,
            proyeccion=1_000_000,
            width=130,
            height=10,
            bg_color=self.colors["bgcolor"],
        )
        self.GypProgress.pack(side=tk.LEFT, pady=5)
        self.InvProgress.pack(side=tk.LEFT, pady=5)

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
        self.rg0.set_facecolor(self.colors["bgcolor"])
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
            command=lambda: self.setup_graph_income("3"),
        )
        bt2 = tk.Button(
            pn1,
            text="6m",
            width=2,
            bg=self.bgcolor,
            fg=self.cgcolor,
            relief=tk.FLAT,
            command=lambda: self.setup_graph_income("6"),
        )
        bt3 = tk.Button(
            pn1,
            text="1y",
            width=2,
            bg=self.bgcolor,
            fg=self.cgcolor,
            relief=tk.FLAT,
            command=lambda: self.setup_graph_income("12"),
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
        self.sesion_FCI = None
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
            # Verificar si debemos continuar ejecutando
            if not self.is_running:
                return

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
            # Verificar si debemos continuar ejecutando
            if self.is_running:
                after_id = self.root.after(
                    500, lambda: self.update_widget(vehiculo=vehiculo)
                )
                self.after_ids.append(after_id)
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
                    exdiv = (
                        fecha.strftime("%d-%b")
                        if fecha and fecha.month == date
                        else " "
                    )
                    avgcost = position["costobase"] / position["position"]

                    dividends = [0] * 12
                    a_meses = (
                        meses if string is None or string == "" else string.split(",")
                    )

                    # calcula la cantidad de pagos - filtrar cadenas vacías
                    distribuir = [s.strip()[:3] for s in a_meses if s.strip()]
                    rata = div / len(distribuir) if len(distribuir) > 0 else last

                    # asume pago de dividends son iguales
                    for i, mes in enumerate(distribuir):
                        if mes in meses:  # Validar que el mes existe en la lista
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
                    exdiv = (
                        fecha.strftime("%d-%b")
                        if fecha and fecha.month == date
                        else " "
                    )
                    avgcost = position["costobase"] / position["position"]

                    a_meses = (
                        meses if string is None or string == "" else string.split(",")
                    )

                    # calcula la cantidad de pagos - filtrar cadenas vacías
                    distribuir = [s.strip()[:3] for s in a_meses if s.strip()]
                    rata = div / len(distribuir) if len(distribuir) > 0 else last

                    # asume pago de dividends son iguales
                    for i, mes in enumerate(distribuir):
                        if mes in meses:  # Validar que el mes existe en la lista
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
                    exdiv = (
                        fecha.strftime("%d-%b")
                        if fecha and fecha.month == date
                        else " "
                    )
                    avgcost = position["costobase"] / position["position"]

                    a_meses = (
                        meses if string is None or string == "" else string.split(",")
                    )

                    # calcula la cantidad de pagos - filtrar cadenas vacías
                    distribuir = [s.strip()[:3] for s in a_meses if s.strip()]
                    rata = div / len(distribuir) if len(distribuir) > 0 else last

                    # asume pago de dividends son iguales
                    for i, mes in enumerate(distribuir):
                        if mes in meses:  # Validar que el mes existe en la lista
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
    def setup_graph_income(self, tipo=None):

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
        # Verificar si debemos continuar ejecutando
        if not self.is_running:
            return

        # inicia performace de  ultimos 6 meses
        self.setup_graph_income(tipo="3")

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
        DataHub.manager_buysell["dividends"] = grupo_dividendo(fg=self.rg2, parm=parm)
        self.rv2.draw()

        # Diversificación por sector
        parm = {
            "titulo": "Diversificación vs Sector",
            "cchart": self.cchart,
            "aspect": 0.30,
        }
        DataHub.manager_buysell["sector"] = grupo_sector(fig=self.rg3, parm=parm)
        self.rv3.draw()

        # Diversificación vs. tipo activo
        xestrategia = self.Estrategia.read()
        parm = {
            "titulo": "Diversificación vs Activos",
            "cchart": self.cchart,
            "legend": "outside upper right",
            "aspect": 0.30,
        }
        DataHub.manager_buysell["activos"] = grupo_activos(
            fg=self.rg4, parm=parm, strategy=xestrategia
        )
        self.rv4.draw()

        # Diversificación vs. región
        parm = {
            "titulo": "Diversificación vs Región",
            "cchart": self.cchart,
            "legend": "outside upper right",
            "aspect": 0.30,
        }
        DataHub.manager_buysell["region"] = grupo_region(
            fg=self.rg5, strategy=xestrategia, parm=parm
        )
        self.rv5.draw()

        # mantiene actualizado los graficos cada 20m o 1200.000ms
        # Verificar si debemos continuar ejecutando
        if self.is_running:
            after_id = self.root.after(1200000, lambda: self.graficos_main())
            self.after_ids.append(after_id)
        # DataHub.manager_after._safe(1200000, self.graficos_main(), name="graficos_main")

    # Detener cada módulo de forma ordenada
    def setup(self):
        """
        Abre ventana de gestión de sesiones con operaciones CRUD.
        Crea ventana Toplevel posicionada para no solapar el notebook principal.
        """
        # Variable para almacenar referencia al tree y session_window
        tree = None
        session_window = None

        def refresh_sessions():
            """Recarga datos de sesión desde BD y actualiza TreeView"""
            nonlocal tree, session_window
            try:
                # Limpiar TreeView
                for item in tree.tree_fixed.get_children():
                    tree.tree_fixed.delete(item)
                for item in tree.tree_scroll.get_children():
                    tree.tree_scroll.delete(item)

                # Cargar datos desde BD
                sessions = BDsystem.select_all_sesion()

                for session in sessions:
                    # Formatear fechas
                    fesesion_str = (
                        session["fesesion"].strftime("%Y-%m-%d %H:%M")
                        if session.get("fesesion")
                        else ""
                    )
                    fiscalYear_str = (
                        session["fiscalYear"].strftime("%Y-%m-%d")
                        if session.get("fiscalYear")
                        else ""
                    )
                    fefund_str = (
                        session["fefund"].strftime("%Y-%m-%d")
                        if session.get("fefund")
                        else ""
                    )

                    # Solo incluir campos visibles (sin id, orcartera, xstrategy, userapi, userpass, private_key, public_key)
                    row_values = [
                        session.get("vehiculo", ""),
                        fiscalYear_str,
                        session.get("iduser", ""),
                        session.get("idcuenta", ""),
                        fesesion_str,
                        session.get("Pinvertir", 0),
                    ]

                    tree.insert_row(values=row_values)

            except Exception as e:
                print(f"[refresh_sessions()]: {e}")
                MyMessageBox(session_window).showerror(
                    "Error", f"Error al cargar sesiones: {str(e)}"
                )

        def on_double_click(event):
            """Maneja doble-click en fila para abrir editor"""
            nonlocal tree
            try:
                selected_fixed = tree.tree_fixed.selection()

                if selected_fixed:
                    # Obtener índice de la fila
                    item_id = selected_fixed[0]
                    index = tree.tree_fixed.index(item_id)

                    # Recuperar datos completos de BD
                    sessions = BDsystem.select_all_sesion()
                    if index < len(sessions):
                        selected_session = sessions[index]
                        open_session_editor(selected_session, edit_mode=True)
            except Exception as e:
                print(f"[on_double_click()]: {e}")

        def on_add_click():
            """Maneja botón Agregar"""
            open_session_editor(session_data=None, edit_mode=False)

        def on_delete_click():
            """Maneja botón Eliminar con confirmación"""
            nonlocal tree, session_window
            try:
                selected_fixed = tree.tree_fixed.selection()

                if not selected_fixed:
                    MyMessageBox(session_window).showwarning(
                        "Advertencia", "Por favor seleccione una sesión para eliminar"
                    )
                    return

                # Confirmar eliminación
                response = MyMessageBox(session_window).askquestion(
                    "Confirmar Eliminación",
                    "¿Está seguro de que desea eliminar esta sesión?\nEsta acción no se puede deshacer.",
                )

                if response == "yes":
                    # Obtener datos de la fila
                    item_id = selected_fixed[0]
                    index = tree.tree_fixed.index(item_id)
                    sessions = BDsystem.select_all_sesion()

                    if index < len(sessions):
                        session = sessions[index]
                        success = BDsystem.delete_sesion(
                            session["id"], session["vehiculo"]
                        )

                        if success:
                            MyMessageBox(session_window).showinfo(
                                "Éxito", "Sesión eliminada correctamente"
                            )
                            refresh_sessions()
                        else:
                            MyMessageBox(session_window).showerror(
                                "Error", "No se pudo eliminar la sesión"
                            )
            except Exception as e:
                print(f"[on_delete_click()]: {e}")
                MyMessageBox(session_window).showerror(
                    "Error", f"Error al eliminar sesión: {str(e)}"
                )

        def open_session_editor(session_data, edit_mode):
            """
            Abre ventana Toplevel para editar/crear sesión

            Args:
                session_data: dict con datos (None para nueva sesión)
                edit_mode: True=editar, False=crear
            """

            def save_session():
                """Valida y guarda sesión"""
                try:
                    # Recopilar valores del formulario
                    values = {
                        "vehiculo": entry_vehiculo.get().strip(),
                        "fesesion": entry_fesesion.get().strip(),
                        "iduser": entry_iduser.get().strip(),
                        "idcuenta": entry_idcuenta.get().strip(),
                        "orcartera": entry_orcartera.get().strip(),
                        "fiscalYear": entry_fiscalYear.get().strip(),
                        "fefund": entry_fefund.get().strip(),
                        "Pinvertir": entry_Pinvertir.get().strip(),
                        "xstrategy": entry_xstrategy.get().strip(),
                        "userapi": (
                            blob_userapi.get("1.0", tk.END).strip().encode("utf-8")
                            if blob_userapi.get("1.0", tk.END).strip()
                            else None
                        ),
                        "userpass": (
                            blob_userpass.get("1.0", tk.END).strip().encode("utf-8")
                            if blob_userpass.get("1.0", tk.END).strip()
                            else None
                        ),
                        "private_key": (
                            blob_private_key.get("1.0", tk.END).strip().encode("utf-8")
                            if blob_private_key.get("1.0", tk.END).strip()
                            else None
                        ),
                        "public_key": (
                            blob_public_key.get("1.0", tk.END).strip().encode("utf-8")
                            if blob_public_key.get("1.0", tk.END).strip()
                            else None
                        ),
                        "port": entry_port.get().strip(),
                    }

                    # Validación de campos requeridos
                    if not values["vehiculo"]:
                        MyMessageBox(session_window).showerror(
                            "Error de Validación", "El campo 'vehiculo' es requerido"
                        )
                        return

                    # Convertir fechas a formato apropiado
                    try:
                        if values["fesesion"]:
                            values["fesesion"] = datetime.strptime(
                                values["fesesion"], "%Y-%m-%d %H:%M:%S"
                            )
                        else:
                            values["fesesion"] = None

                        if values["fiscalYear"]:
                            values["fiscalYear"] = datetime.strptime(
                                values["fiscalYear"], "%Y-%m-%d"
                            ).date()
                        else:
                            values["fiscalYear"] = None

                        if values["fefund"]:
                            values["fefund"] = datetime.strptime(
                                values["fefund"], "%Y-%m-%d"
                            ).date()
                        else:
                            values["fefund"] = None
                    except ValueError as ve:
                        MyMessageBox(session_window).showerror(
                            "Error de Validación", f"Formato de fecha inválido: {ve}"
                        )
                        return

                    # Convertir Pinvertir a int
                    try:
                        values["Pinvertir"] = (
                            int(values["Pinvertir"]) if values["Pinvertir"] else 0
                        )
                    except ValueError:
                        MyMessageBox(session_window).showerror(
                            "Error de Validación", "Pinvertir debe ser un número"
                        )
                        return

                    # Convertir port a int
                    try:
                        values["port"] = int(values["port"]) if values["port"] else None
                    except ValueError:
                        MyMessageBox(session_window).showerror(
                            "Error de Validación", "Port debe ser un número entero"
                        )
                        return

                    # Validar rango de port
                    if values["port"] is not None and (
                        values["port"] < 1 or values["port"] > 65535
                    ):
                        MyMessageBox(session_window).showerror(
                            "Error de Validación", "Port debe estar entre 1 y 65535"
                        )
                        return

                    # Guardar en BD
                    if edit_mode:
                        success = BDsystem.update_sesion(
                            session_data["id"], session_data["vehiculo"], values
                        )
                        msg = (
                            "Sesión actualizada correctamente"
                            if success
                            else "No se pudo actualizar la sesión"
                        )
                    else:
                        success = BDsystem.insert_sesion(values)
                        msg = (
                            "Sesión creada correctamente"
                            if success
                            else "No se pudo crear la sesión"
                        )

                    if success:
                        MyMessageBox(session_window).showinfo("Éxito", msg)
                        editor_window.destroy()
                        refresh_sessions()
                    else:
                        MyMessageBox(session_window).showerror("Error", msg)

                except Exception as e:
                    print(f"[save_session()]: {e}")
                    MyMessageBox(session_window).showerror(
                        "Error", f"Error al guardar sesión: {str(e)}"
                    )

            def import_blob_file(text_widget):
                """Abre diálogo para importar archivo a campo BLOB"""
                try:
                    file_path = filedialog.askopenfilename(
                        title="Seleccionar archivo para importar",
                        filetypes=[
                            ("Todos los archivos", "*.*"),
                            ("Archivos de texto", "*.txt"),
                            ("Archivos PEM", "*.pem"),
                        ],
                    )
                    if file_path:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            text_widget.delete("1.0", tk.END)
                            text_widget.insert("1.0", content)
                except Exception as e:
                    MyMessageBox(session_window).showerror(
                        "Error", f"Error al importar archivo: {str(e)}"
                    )

            def cancel_edit():
                """Cierra editor sin guardar"""
                editor_window.destroy()

            # Crear ventana del editor
            editor_window = tk.Toplevel(session_window)
            title = "Editar Vehículo" if edit_mode else "Nueva Vehículo"
            editor_window.title(title)

            # Posicionar a la derecha de la ventana de sesiones
            session_x = session_window.winfo_x()
            session_y = session_window.winfo_y()
            session_width = session_window.winfo_width()
            editor_window.geometry(
                f"700x700+{session_x + session_width + 10}+{session_y}"
            )

            editor_window.resizable(False, False)
            editor_window.config(bg=self.colors["bgcolor"])
            editor_window.grab_set()
            editor_window.focus()

            # Crear canvas scrollable
            canvas = tk.Canvas(editor_window, bg=self.colors["bgcolor"])
            scrollbar = ttk.Scrollbar(
                editor_window, orient="vertical", command=canvas.yview
            )
            scrollable_frame = ttk.Frame(canvas, style="C.TFrame")

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # Campos del formulario
            row = 0

            # Campos normales con Entry
            fields_config = [
                (
                    "vehiculo",
                    "Vehículo (char 10):",
                    "disabled" if not edit_mode else "normal",
                ),
                ("fesesion", "Fecha Sesión (YYYY-MM-DD HH:MM:SS):", "normal"),
                ("iduser", "ID Usuario (char 10):", "normal"),
                ("idcuenta", "ID Cuenta (char 10):", "normal"),
                ("orcartera", "Orden Cartera (char 50):", "normal"),
                (
                    "fiscalYear",
                    "Año Fiscal (YYYY-MM-DD):",
                    "disabled" if not edit_mode else "normal",
                ),
                (
                    "fefund",
                    "Fecha Fundación (YYYY-MM-DD):",
                    "disabled" if not edit_mode else "normal",
                ),
                ("Pinvertir", "Monto a Invertir (int):", "normal"),
                ("xstrategy", "Estrategia (char 60):", "normal"),
                ("port", "Puerto (int 1-65535):", "normal"),
            ]

            # Crear widgets de entrada
            entry_vehiculo = None
            entry_fesesion = None
            entry_iduser = None
            entry_idcuenta = None
            entry_orcartera = None
            entry_fiscalYear = None
            entry_fefund = None
            entry_Pinvertir = None
            entry_xstrategy = None
            entry_port = None

            for field_name, label_text, state in fields_config:
                label = tk.Label(
                    scrollable_frame,
                    text=label_text,
                    bg=self.colors["bgcolor"],
                    fg="white",
                    anchor="w",
                )
                label.grid(row=row, column=0, sticky="w", padx=10, pady=5)

                entry = tk.Entry(scrollable_frame, width=50, state=state)
                entry.grid(row=row, column=1, padx=10, pady=5)

                # Poblar con datos existentes si está en modo edición
                if edit_mode and session_data:
                    value = session_data.get(field_name, "")
                    if value:
                        if field_name == "fesesion" and hasattr(value, "strftime"):
                            entry.insert(0, value.strftime("%Y-%m-%d %H:%M:%S"))
                        elif field_name in ["fiscalYear", "fefund"] and hasattr(
                            value, "strftime"
                        ):
                            entry.insert(0, value.strftime("%Y-%m-%d"))
                        else:
                            entry.insert(0, str(value))

                # Asignar a variable
                if field_name == "vehiculo":
                    entry_vehiculo = entry
                elif field_name == "fesesion":
                    entry_fesesion = entry
                elif field_name == "iduser":
                    entry_iduser = entry
                elif field_name == "idcuenta":
                    entry_idcuenta = entry
                elif field_name == "orcartera":
                    entry_orcartera = entry
                elif field_name == "fiscalYear":
                    entry_fiscalYear = entry
                elif field_name == "fefund":
                    entry_fefund = entry
                elif field_name == "Pinvertir":
                    entry_Pinvertir = entry
                elif field_name == "xstrategy":
                    entry_xstrategy = entry
                elif field_name == "port":
                    entry_port = entry

                row += 1

            # Campos BLOB con Text widget
            blob_fields = [
                ("userapi", "API Key Usuario (BLOB):"),
                ("userpass", "Password Usuario (BLOB):"),
                ("private_key", "Llave Privada (BLOB):"),
                ("public_key", "Llave Pública (BLOB):"),
            ]

            blob_userapi = None
            blob_userpass = None
            blob_private_key = None
            blob_public_key = None

            for field_name, label_text in blob_fields:
                # Label
                label = tk.Label(
                    scrollable_frame,
                    text=label_text,
                    bg=self.colors["bgcolor"],
                    fg="white",
                    anchor="w",
                )
                label.grid(row=row, column=0, sticky="w", padx=10, pady=5)

                # Frame para Text + Botón
                blob_frame = tk.Frame(scrollable_frame, bg=self.colors["bgcolor"])
                blob_frame.grid(row=row, column=1, padx=20, pady=5, sticky="ew")

                # Text widget
                text_widget = tk.Text(blob_frame, width=30, height=3)
                text_widget.pack(side=tk.LEFT)

                # Botón de importar
                import_btn = tk.Button(
                    blob_frame,
                    text="Importar",
                    command=lambda tw=text_widget: import_blob_file(tw),
                )
                import_btn.pack(side=tk.LEFT, padx=5)

                # Poblar con datos existentes si está en modo edición
                if edit_mode and session_data:
                    blob_value = session_data.get(field_name)
                    if blob_value:
                        try:
                            # Intentar decodificar si es bytes
                            if isinstance(blob_value, bytes):
                                text_widget.insert("1.0", blob_value.decode("utf-8"))
                            else:
                                text_widget.insert("1.0", str(blob_value))
                        except:
                            text_widget.insert("1.0", "[Datos binarios]")

                # Asignar a variable
                if field_name == "userapi":
                    blob_userapi = text_widget
                elif field_name == "userpass":
                    blob_userpass = text_widget
                elif field_name == "private_key":
                    blob_private_key = text_widget
                elif field_name == "public_key":
                    blob_public_key = text_widget

                row += 1

            # Frame de botones
            btn_frame = tk.Frame(scrollable_frame, bg=self.colors["bgcolor"])
            btn_frame.grid(row=row, column=0, columnspan=2, pady=20)

            save_btn = tk.Button(
                btn_frame, text="Guardar", width=10, command=save_session
            )
            save_btn.pack(side=tk.LEFT, padx=10)

            cancel_btn = tk.Button(
                btn_frame, text="Cancel", width=10, command=cancel_edit
            )
            cancel_btn.pack(side=tk.LEFT, padx=10)

            # Empaquetar canvas y scrollbar
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def eexit():
            session_window.destroy()

        # Crear ventana principal de gestión de sesiones
        try:
            # Ventana Toplevel
            session_window = tk.Toplevel(self.root)
            session_window.title("Setup - Inversionista")

            # Cargar datos desde BD
            sessions = BDsystem.select_all_sesion()
            height = max(2, len(sessions) + 1)

            # Posicionamiento (izquierda de la pantalla para dejar espacio al editor)
            window_width = 620
            window_height = min(550, 30 + height * 25)
            x_position = 400
            y_position = 110
            session_window.geometry(
                f"{window_width}x{window_height}+{x_position}+{y_position}"
            )
            session_window.config(bg=self.colors["bgcolor"])
            session_window.resizable(True, True)

            # Panel de control con botones
            control_frame = ttk.Frame(
                session_window, style="C.TFrame", padding=(10, 10)
            )
            control_frame.pack(side=tk.BOTTOM, fill=tk.X)

            add_btn = tk.Button(
                control_frame, text="Agregar", width=10, command=on_add_click
            )
            add_btn.pack(side=tk.LEFT, padx=5)

            delete_btn = tk.Button(
                control_frame, text="Eliminar", width=10, command=on_delete_click
            )
            delete_btn.pack(side=tk.LEFT, padx=5)

            refresh_btn = tk.Button(
                control_frame, text="Refrescar", width=10, command=refresh_sessions
            )
            refresh_btn.pack(side=tk.LEFT, padx=5)

            cancel_btn = tk.Button(
                control_frame, text="Cancel", width=10, command=eexit
            )
            cancel_btn.pack(side=tk.LEFT, padx=5)

            # Frame para TreeView
            tree_frame = ttk.Frame(session_window, style="C.TFrame")
            tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Definición de columnas (sin id, orcartera, xstrategy, userapi, userpass, private_key, public_key)
            columns = [
                "vehiculo",
                "fiscalYear",
                "iduser",
                "idcuenta",
                "fesesion",
                "Pinvertir",
            ]

            fixed_columns = ["vehiculo", "fiscalYear"]

            column_alignments = {
                "vehiculo": {"width": 80, "anchor": "w"},
                "fiscalYear": {"width": 80, "anchor": "w"},
                "iduser": {"width": 80, "anchor": "w"},
                "idcuenta": {"width": 80, "anchor": "w"},
                "fesesion": {"width": 140, "anchor": "w"},
                "Pinvertir": {"width": 90, "anchor": "e"},
            }

            # Crear CustomTreeview
            tree = CustomTreeview(
                master=tree_frame,
                columns=columns,
                fixed_columns=fixed_columns,
                column_alignments=column_alignments,
                height=height,
                show_vscroll=False,
                show_hscroll=False,
                sort_columns=True,
            )

            # Vincular eventos
            tree.tree_fixed.bind("<Double-1>", on_double_click)
            tree.tree_scroll.bind("<Double-1>", on_double_click)

            # Carga inicial
            refresh_sessions()
        except Exception as e:
            print(f"[setup()]: {e}")
            MyMessageBox(session_window).showerror(
                "Error", f"Error al abrir gestor de sesiones: {str(e)}"
            )

    # Cierra la aplicación de forma ordenada
    def eexit(self):
        # Marcar como no ejecutando para detener nuevos callbacks
        self.is_running = False

        # Cancelar todos los after() callbacks pendientes
        for after_id in self.after_ids:
            try:
                self.root.after_cancel(after_id)
            except:
                pass

        # Limpiar lista
        self.after_ids.clear()

        # Cancelar TODOS los callbacks pendientes de Tkinter (incluso los no rastreados)
        try:
            for after_info in self.root.tk.call("after", "info"):
                try:
                    self.root.after_cancel(after_info)
                except:
                    pass
        except:
            pass

        # Cerrar figuras de matplotlib si existen
        try:
            import matplotlib.pyplot as plt

            plt.close("all")
        except:
            pass

        print("✅ DashMain: Recursos liberados correctamente")

        # cierra todos los threads & Job's pendientes
        try:
            DataHub.manager_events.stop_all()
        except:
            pass

        # DataHub.manager_after.after_cancel_all()
        # Destruir ventana de forma segura sin crear nuevos callbacks
        try:
            # Deshabilitar el protocolo de cierre para evitar loops
            self.root.protocol("WM_DELETE_WINDOW", lambda: None)

            # Ocultar ventana inmediatamente
            self.root.withdraw()

            # Update para procesar eventos pendientes
            self.root.update_idletasks()

            # Terminar mainloop
            self.root.quit()

        except Exception as e:
            print(f"[eexit error]: {e}")

        # Forzar salida limpia del programa
        import sys

        sys.exit(0)

    # toma limites de barraProgress
    def get_limite_inversion(self):
        traz = self.PlanInversion.select_trazaplan(
            idcuenta=self.sesion_stock["idcuenta"]
        )
        if traz:
            for tkey in traz:
                if tkey.get("status") == "Ejecucion":

                    inversion = tkey["vision"]
                    gypDiaria = int(inversion / 100)
                    return inversion, gypDiaria

    def actualizar_totales_inversiones(self):
        """
        Actualiza los labels de ganancia diaria y costo base con datos de la tabla inversiones.
        Se ejecuta periódicamente cada 30 segundos.
        """
        try:
            # Verificar si debemos continuar ejecutando
            if not self.is_running:
                return

            # Obtener totales desde la base de datos
            totales = self.RepositorioOportunidades.get_totales_inversiones()

            # Formatear valores
            ganancias_dia = totales["total_ganancia_dia"]
            costo_base = totales["total_costo_base"]
            limit_costoB, limit_gyp = self.get_limite_inversion()
            low_limit_gyp = -2 * limit_gyp
            high_limit_gyp = 2 * limit_gyp

            # update progressos
            self.GypProgress.update_values(low_limit_gyp, ganancias_dia, high_limit_gyp)
            self.InvProgress.update_values(0, costo_base, limit_costoB)

            # Programar siguiente actualización (cada 30 segundos)
            if self.is_running:
                after_id = self.root.after(30000, self.actualizar_totales_inversiones)
                self.after_ids.append(after_id)

        except Exception as e:
            print(f"[actualizar_totales_inversiones()]: {e}")
            # Intentar nuevamente en 30 segundos aunque haya error
            if self.is_running:
                after_id = self.root.after(30000, self.actualizar_totales_inversiones)
                self.after_ids.append(after_id)

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
        self.sesion_crypto = self.PlanInversion.get_sesion_by_vehiculo("Crypto")
        if self.sesion_crypto:
            self.start_crypto(account=self.sesion_crypto["idcuenta"], vehiculo="Crypto")
            self.graficos_main()

        # define widget principales Stock-----------------------------------------------------------------
        self.sesion_stock = self.PlanInversion.get_sesion_by_vehiculo("Stock")
        if self.sesion_stock:
            self.start_stock(account=self.sesion_stock["idcuenta"], vehiculo="Stock")

        # inicia otros modulos ---------------------------------------------------------------------------
        self.gestion = GestionInversion(
            parent=self.root, master=self.win3, colores=self.colors
        )
        self.gestion.pack()

        # define widget principales FCI-------------------------------------------------------------------
        self.sesion_FCI = self.PlanInversion.get_sesion_by_vehiculo("SANT.ARS")
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

        # Iniciar actualización de totales de inversiones
        self.actualizar_totales_inversiones()

        self.root.mainloop()


# clase paar monitorear el estado del sistema
class system_status(tk.Frame):
    def __init__(self, master=None, colores=None):
        self.system = master
        self.colors = colores
        self.itemsInfo = None

        # Lista para rastrear todos los after() callbacks
        self.after_ids = []
        self.is_running = True  # Flag para controlar loops

        self.messagebox = MyMessageBox(self.system)

        self.process = ttk.Frame(self.system, padding=(1, 10, 1, 1), style="C.TFrame")
        self.right = ttk.Frame(self.system, padding=(1, 10, 1, 1), style="C.TFrame")

        # Cambio: usar Notebook (tabs) en lugar de frames individuales
        self.bottom = ttk.Notebook(self.system)

        # Crear frames para cada tab
        self.datahub = ttk.Frame(self.bottom, padding=(1, 1, 1, 1), style="C.TFrame")
        self.cache = ttk.Frame(self.bottom, padding=(1, 1, 1, 1), style="C.TFrame")
        self.buysell = ttk.Frame(self.bottom, padding=(1, 1, 1, 1), style="C.TFrame")
        self.debugging = ttk.Frame(self.bottom, padding=(1, 1, 1, 1), style="C.TFrame")

        # Frames para la derecha
        self.figura = ttk.Frame(self.right, padding=(5, 1, 1, 5), style="C.TFrame")
        self.performa = ttk.Frame(self.right, padding=(1, 1, 1, 1), style="C.TFrame")
        self.connect = ttk.Frame(self.right, padding=(1, 1, 1, 1), style="C.TFrame")

        # establece figura performance system
        self.fg = Figure(figsize=(3.8, 1.7), dpi=110, layout="tight")
        self.rv = FigureCanvasTkAgg(self.fg, master=self.right)
        self.fg.set_facecolor("DodgerBlue")

        self.rv.draw()
        self.rv.get_tk_widget().pack()

        self.performa.pack(fill=tk.X)
        self.figura.pack(fill=tk.X)
        self.connect.pack(side=tk.RIGHT, fill=tk.BOTH)

        # Agregar tabs al Notebook
        self.bottom.add(self.datahub, text="DataHub")
        self.bottom.add(self.cache, text="Cache")
        self.bottom.add(self.buysell, text="Manager BuySell")
        self.bottom.add(self.debugging, text="Debugging")

        self.bottom.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.right.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.process.pack(side=tk.TOP, fill=tk.BOTH)

        # Bind cleanup al destruir la ventana
        self.system.bind("<Destroy>", self._on_destroy)

        self.process_system()

    def _on_destroy(self, event):
        """Limpia recursos al cerrar la ventana"""
        if event.widget == self.system:
            self.cleanup()

    def cleanup(self):
        """Cancela todos los after() callbacks y detiene animaciones"""
        try:
            # Marcar como no ejecutando
            self.is_running = False

            # Cancelar todos los after() callbacks
            for after_id in self.after_ids:
                try:
                    self.system.after_cancel(after_id)
                except:
                    pass

            # Limpiar lista
            self.after_ids.clear()

            # Detener animación de monitor_realtime si existe
            if hasattr(self, "monitor_animation") and self.monitor_animation:
                try:
                    self.monitor_animation.event_source.stop()
                    self.monitor_animation = None
                except:
                    pass

            print("✅ system_status: Recursos liberados correctamente")

        except Exception as e:
            print(f"[cleanup]: {e}")

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
            # Verificar si debemos continuar ejecutando
            if not self.is_running:
                return

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
            # Registrar el after_id para poder cancelarlo luego
            after_id = self.system.after(2000, update_status)
            self.after_ids.append(after_id)
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
            self.monitor_realtime()  # Activado con optimizaciones (actualiza cada 10s)
            self.monitor_cache()
            self.manager_buysell_system()
            update_status()
        except (EncodingWarning, Exception) as e:
            print(f"process_system(): {e}")

    # modulo principal para recorre Datahub()
    def datahub_system(self):
        """
        Visualiza DataHub.info con patrón lista-detalle mejorado.
        - LISTA (izquierda): Símbolos disponibles en DataHub.info
        - DETALLE (derecha): Información completa del símbolo seleccionado
        - Evento: Doble click o selección simple para ver detalle
        """

        # Selecciona y actualiza el detalle del primer elemento.
        def display_first_item():
            symbol = search_lista(first=True)
            if symbol:
                display_items_lista(symbol)
                self.itemsInfo = symbol

        # display items del activo con formato mejorado
        def display_items_lista(symbol):
            """Muestra detalle del símbolo seleccionado en DataHub.info"""
            try:
                # Limpiar el treeview de detalles
                for item in detalle.get_children():
                    detalle.delete(item)

                # Verificar que el símbolo existe
                if symbol not in DataHub.info:
                    detalle.insert(
                        "", "end", text=f"⚠️ {symbol}: No disponible", tags=("warning",)
                    )
                    return

                data = DataHub.info[symbol]

                # Header con símbolo y timestamp
                if "websocket" in data and "timestamp" in data["websocket"]:
                    timestamp = data["websocket"]["timestamp"]
                    detalle.insert(
                        "", "end", text=f"📊 Symbol: {symbol.upper()}", tags=("header",)
                    )
                    detalle.insert(
                        "", "end", text=f"⏰ Update: {timestamp}", tags=("info",)
                    )
                else:
                    detalle.insert(
                        "", "end", text=f"📊 Symbol: {symbol.upper()}", tags=("header",)
                    )

                detalle.insert("", "end", text="", tags=("spacer",))

                # Display detalle del activo con estructura mejorada
                for key, value in data.items():
                    if isinstance(value, dict):
                        # Crear nodo para diccionarios
                        node = detalle.insert(
                            "", "end", text=f"📂 {key}", tags=("section",)
                        )

                        for fields, valor in value.items():
                            # Formatear valores según tipo
                            if isinstance(valor, float):
                                valor_str = (
                                    f"{valor:,.4f}"
                                    if abs(valor) < 1000
                                    else f"{valor:,.2f}"
                                )
                            elif isinstance(valor, (int, str)):
                                valor_str = str(valor)
                            else:
                                valor_str = str(valor)

                            detalle.insert(
                                node,
                                "end",
                                text=f"  {fields}: {valor_str}",
                                tags=("value",),
                            )

                        # Expandir nodos importantes
                        if key in ["websocket", "market", "position"]:
                            detalle.item(node, open=True)

                    elif isinstance(value, pd.DataFrame):
                        # Mostrar información de DataFrames
                        node = detalle.insert(
                            "", "end", text=f"📋 {key}", tags=("section",)
                        )
                        detalle.insert(
                            node,
                            "end",
                            text=f"  Filas: {value.shape[0]}",
                            tags=("summary",),
                        )
                        detalle.insert(
                            node,
                            "end",
                            text=f"  Columnas: {value.shape[1]}",
                            tags=("summary",),
                        )
                        detalle.insert(
                            node,
                            "end",
                            text=f"  Nombres: {list(value.columns)[:5]}{'...' if len(value.columns) > 5 else ''}",
                            tags=("summary",),
                        )

                    else:
                        # Valores simples
                        if isinstance(value, float):
                            value_str = (
                                f"{value:,.4f}"
                                if abs(value) < 1000
                                else f"{value:,.2f}"
                            )
                        else:
                            value_str = str(value)
                        detalle.insert(
                            "", "end", text=f"🔹 {key}: {value_str}", tags=("value",)
                        )

            except Exception as e:
                detalle.insert(
                    "", "end", text=f"❌ Error al mostrar detalle: {e}", tags=("error",)
                )
                print(f"[display_items_lista({symbol})]: {e}")

        # Obtener el ítem seleccionado con un solo click
        def on_item_selected(event):
            """Maneja selección simple en la lista"""
            selected_items = lista.selection()
            if selected_items:
                selected_id = selected_items[0]
                symbol = lista.item(selected_id, "text")

                # Verificar que no sea un nodo padre
                if symbol and not symbol.startswith(":"):
                    if symbol in DataHub.info:
                        display_items_lista(symbol)
                        self.itemsInfo = symbol

        # Doble click para expandir/contraer o mostrar detalle
        def on_double_click(event):
            """Maneja doble click en la lista"""
            selected_items = lista.selection()
            if selected_items:
                selected_id = selected_items[0]
                symbol = lista.item(selected_id, "text")

                # Si no es un nodo padre, mostrar detalle
                if symbol and not symbol.startswith(":"):
                    if symbol in DataHub.info:
                        display_items_lista(symbol)
                        self.itemsInfo = symbol

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
            # Verificar si debemos continuar ejecutando
            if not self.is_running:
                return

            lista.item(root, open=True)
            insert_lista(parent=root)
            # Registrar el after_id para poder cancelarlo luego
            after_id = self.system.after(30000, update_datahub)
            self.after_ids.append(after_id)
            # DataHub.manager_after._safe(30000, update_datahub(), name="update_datahub")

        try:
            # define TreeView para mostras  Lista y detalle de items DataHub.Info()
            lista = ttk.Treeview(self.datahub, style="TFrame")
            detalle = ttk.Treeview(self.datahub, style="TFrame")

            # Configurar headers
            lista.heading("#0", text="DataHub - Símbolos")
            detalle.heading("#0", text="Información Detallada del Activo")

            # Configurar anchos
            lista.column("#0", width=180, minwidth=150)

            # Pack widgets
            lista.pack(side=tk.LEFT, fill=tk.BOTH, pady=5, padx=(5, 2))
            detalle.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, pady=5, padx=(2, 5))

            # Configurar colores y estilos mejorados (consistente con manager_buysell)
            detalle.tag_configure(
                "header", foreground="cyan", font=("TkDefaultFont", 10, "bold")
            )
            detalle.tag_configure(
                "section", foreground="yellow", font=("TkDefaultFont", 9, "bold")
            )
            detalle.tag_configure("info", foreground="lightgreen")
            detalle.tag_configure("summary", foreground="orange")
            detalle.tag_configure("value", foreground="white")
            detalle.tag_configure("error", foreground="red")
            detalle.tag_configure("warning", foreground="orange")

            # Tags antiguos para compatibilidad
            detalle.tag_configure("colorTex", foreground="orange")
            detalle.tag_configure("colorGroup", foreground=DataHub.bgcolor)

            # Bind eventos
            lista.bind("<<TreeviewSelect>>", on_item_selected)
            lista.bind("<Double-Button-1>", on_double_click)

            # --- Scrollbars ---
            hsb = ttk.Scrollbar(detalle, orient=tk.HORIZONTAL, command=detalle.xview)
            detalle.configure(xscroll=hsb.set)
            hsb.pack(side=tk.BOTTOM, fill=tk.X)

            # inicia insert de lista
            lastClose = ": Close Market(last) "
            process = lista.insert("", "end", text=lastClose)
            insert_process(process)

            root = lista.insert("", "end", text=f": {DataHub.info['TimeDataHub']}")

            # Mostrar mensaje inicial en detalle
            detalle.insert(
                "",
                "end",
                text="👈 Selecciona un símbolo de la izquierda",
                tags=("info",),
            )
            detalle.insert(
                "", "end", text="para ver su información detallada", tags=("info",)
            )
            detalle.insert("", "end", text="", tags=("spacer",))
            detalle.insert(
                "",
                "end",
                text="💡 Click simple o doble click para ver detalles",
                tags=("summary",),
            )

            update_datahub()
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"datahub_system(): {e}")

    # detalla uso de cache
    def monitor_cache(self):
        """
        Visualiza CacheHut.cache con patrón lista-detalle mejorado.
        - LISTA (izquierda): Claves del cache con información resumida
        - DETALLE (derecha): Información completa del item en cache
        - Evento: Doble click para ver detalle completo

        Características:
            ✅ Ver claves actuales del cache
            ✅ Información de tipo, tamaño y timestamp
            ✅ Refrescar contenido automático
            ✅ Eliminar entradas manualmente
            ✅ Ver detalles completos de DataFrames y otros objetos
        """

        #   FUNCIONALIDAD PRINCIPAL
        def refresh_cache_list():
            """Recarga la lista de claves desde el cache."""
            try:
                # Limpiar lista
                for item in lista.get_children():
                    lista.delete(item)

                # Contador de elementos
                total_items = 0

                # Insertar items del cache
                for k, v in CacheHut.cache.items():
                    tipo = type(v).__name__

                    # Calcular tamaño aproximado
                    try:
                        import sys

                        size_bytes = sys.getsizeof(v)
                        if size_bytes < 1024:
                            size_str = f"{size_bytes}B"
                        elif size_bytes < 1024 * 1024:
                            size_str = f"{size_bytes/1024:.1f}KB"
                        else:
                            size_str = f"{size_bytes/(1024*1024):.1f}MB"
                    except:
                        size_str = "N/A"

                    # Insertar en lista con icono según tipo
                    if tipo == "DataFrame":
                        icon = "📊"
                    elif tipo in ["dict", "DotMap"]:
                        icon = "📂"
                    elif tipo in ["list", "tuple"]:
                        icon = "📋"
                    else:
                        icon = "📦"

                    lista.insert(
                        "",
                        tk.END,
                        text=f"{icon} {k}",
                        values=(tipo, size_str),
                        tags=("item",),
                    )
                    total_items += 1

                # Actualizar header con contador
                lista.heading("#0", text=f"Cache Keys ({total_items} items)")

                # Si no hay items
                if total_items == 0:
                    lista.insert(
                        "", "end", text="(Vacío - sin datos en cache)", tags=("empty",)
                    )

            except Exception as e:
                print(f"[refresh_cache_list()]: {e}")

        def display_cache_detail(key):
            """Muestra detalle completo del item seleccionado en cache"""
            try:
                # Limpiar detalle
                for item in detalle.get_children():
                    detalle.delete(item)

                # Obtener datos del cache
                data = CacheHut.cache.get(key)

                if data is None:
                    detalle.insert(
                        "",
                        "end",
                        text=f"⚠️ {key}: No disponible o expirado",
                        tags=("warning",),
                    )
                    return

                # Header con el nombre de la clave
                detalle.insert("", "end", text=f"🔑 Key: {key}", tags=("header",))
                detalle.insert("", "end", text="", tags=("spacer",))

                # Información del tipo de objeto
                tipo_data = type(data).__name__
                detalle.insert("", "end", text=f"📦 Tipo: {tipo_data}", tags=("info",))

                # Tamaño del objeto
                try:
                    import sys

                    size_bytes = sys.getsizeof(data)
                    if size_bytes < 1024:
                        size_str = f"{size_bytes} bytes"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes/1024:.2f} KB"
                    else:
                        size_str = f"{size_bytes/(1024*1024):.2f} MB"
                    detalle.insert(
                        "", "end", text=f"💾 Tamaño: {size_str}", tags=("info",)
                    )
                except:
                    pass

                # Timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                detalle.insert(
                    "", "end", text=f"⏰ Consultado: {timestamp}", tags=("info",)
                )
                detalle.insert("", "end", text="", tags=("spacer",))

                # Mostrar contenido según el tipo
                if isinstance(data, pd.DataFrame):
                    # DataFrame
                    detalle.insert(
                        "", "end", text="📊 DataFrame - Resumen", tags=("section",)
                    )
                    detalle.insert(
                        "", "end", text=f"  Filas: {data.shape[0]:,}", tags=("summary",)
                    )
                    detalle.insert(
                        "",
                        "end",
                        text=f"  Columnas: {data.shape[1]}",
                        tags=("summary",),
                    )
                    detalle.insert(
                        "",
                        "end",
                        text=f"  Nombres: {list(data.columns)[:8]}",
                        tags=("summary",),
                    )
                    if len(data.columns) > 8:
                        detalle.insert(
                            "",
                            "end",
                            text=f"  ... y {len(data.columns) - 8} más",
                            tags=("summary",),
                        )

                    # Mostrar primeras filas
                    detalle.insert("", "end", text="", tags=("spacer",))
                    node = detalle.insert(
                        "",
                        "end",
                        text="📋 Primeras 5 filas (haz doble click para ver completo)",
                        tags=("section",),
                    )
                    df_string = data.head(5).to_string()
                    for line in df_string.split("\n")[:15]:  # Limitar líneas
                        detalle.insert(node, "end", text=line, tags=("data",))

                elif isinstance(data, dict):
                    # Diccionario
                    detalle.insert(
                        "", "end", text="📂 Diccionario - Contenido", tags=("section",)
                    )
                    detalle.insert(
                        "",
                        "end",
                        text=f"  Total de claves: {len(data)}",
                        tags=("summary",),
                    )
                    detalle.insert("", "end", text="", tags=("spacer",))

                    node = detalle.insert(
                        "", "end", text="🔹 Estructura", tags=("section",)
                    )
                    for idx, (k, v) in enumerate(data.items()):
                        if idx >= 20:  # Limitar a 20 items
                            detalle.insert(
                                node,
                                "end",
                                text=f"  ... y {len(data) - 20} más",
                                tags=("value",),
                            )
                            break
                        v_str = str(v)[:100] + "..." if len(str(v)) > 100 else str(v)
                        detalle.insert(
                            node, "end", text=f"  {k}: {v_str}", tags=("value",)
                        )

                elif isinstance(data, (list, tuple)):
                    # Lista o tupla
                    detalle.insert(
                        "", "end", text=f"📋 {tipo_data} - Contenido", tags=("section",)
                    )
                    detalle.insert(
                        "",
                        "end",
                        text=f"  Total de elementos: {len(data)}",
                        tags=("summary",),
                    )
                    detalle.insert("", "end", text="", tags=("spacer",))

                    node = detalle.insert(
                        "", "end", text="🔹 Elementos", tags=("section",)
                    )
                    for idx, item in enumerate(data):
                        if idx >= 20:  # Limitar a 20 items
                            detalle.insert(
                                node,
                                "end",
                                text=f"  ... y {len(data) - 20} más",
                                tags=("value",),
                            )
                            break
                        item_str = (
                            str(item)[:100] + "..."
                            if len(str(item)) > 100
                            else str(item)
                        )
                        detalle.insert(
                            node, "end", text=f"  [{idx}]: {item_str}", tags=("value",)
                        )

                else:
                    # Otros tipos
                    detalle.insert("", "end", text="📦 Valor", tags=("section",))
                    value_str = (
                        str(data)[:500] + "..." if len(str(data)) > 500 else str(data)
                    )
                    detalle.insert("", "end", text=value_str, tags=("value",))

            except Exception as e:
                detalle.insert(
                    "", "end", text=f"❌ Error al mostrar detalle: {e}", tags=("error",)
                )
                print(f"[display_cache_detail({key})]: {e}")

        def remove_selected_key():
            """Elimina la clave seleccionada del cache."""
            selected = lista.selection()
            if not selected:
                self.messagebox.showinfo(
                    "Información", "Seleccione una clave para eliminar."
                )
                return

            # Extraer key del texto (remover icono)
            item_text = lista.item(selected[0], "text")
            key = item_text.split(" ", 1)[1] if " " in item_text else item_text

            if key in CacheHut.cache:
                del CacheHut.cache[key]
                self.messagebox.showinfo(
                    "Cache", f"✅ Clave '{key}' eliminada del cache."
                )
                refresh_cache_list()
                # Limpiar detalle
                for item in detalle.get_children():
                    detalle.delete(item)
                detalle.insert(
                    "",
                    "end",
                    text="👈 Selecciona un item de la izquierda",
                    tags=("info",),
                )
            else:
                self.messagebox.showwarning(
                    "Cache", f"⚠️ Clave '{key}' no encontrada o ya expirada."
                )

        #   EVENTOS DE INTERFAZ
        def on_double_click(event):
            """Maneja doble clic sobre una clave: muestra detalle completo."""
            selected = lista.selection()
            if not selected:
                return

            # Extraer key del texto (remover icono)
            item_text = lista.item(selected[0], "text")
            if item_text.startswith("("):  # Es el mensaje de vacío
                return

            key = item_text.split(" ", 1)[1] if " " in item_text else item_text
            display_cache_detail(key)

        def on_item_selected(event):
            """Maneja selección simple en la lista"""
            selected = lista.selection()
            if selected:
                item_text = lista.item(selected[0], "text")
                if not item_text.startswith("("):  # No es mensaje de vacío
                    key = item_text.split(" ", 1)[1] if " " in item_text else item_text
                    display_cache_detail(key)

        def auto_refresh():
            """Auto-actualiza la lista cada 30 segundos"""
            # Verificar si debemos continuar ejecutando
            if not self.is_running:
                return

            refresh_cache_list()
            # Registrar el after_id para poder cancelarlo luego
            after_id = self.system.after(30000, auto_refresh)
            self.after_ids.append(after_id)

        try:
            # Crear TreeViews para lista y detalle
            lista = ttk.Treeview(self.cache, columns=("tipo", "tamaño"), style="TFrame")
            detalle = ttk.Treeview(self.cache, style="TFrame")

            # Configurar headers y columnas de lista
            lista.heading("#0", text="Cache Keys")
            lista.heading("tipo", text="Tipo")
            lista.heading("tamaño", text="Tamaño")

            lista.column("#0", width=200, minwidth=150)
            lista.column("tipo", width=100, minwidth=80)
            lista.column("tamaño", width=80, minwidth=60)

            # Configurar header de detalle
            detalle.heading("#0", text="Información Detallada")

            # Pack widgets
            lista.pack(side=tk.LEFT, fill=tk.BOTH, pady=5, padx=(5, 2))
            detalle.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5, padx=(2, 5))

            # Configurar colores y estilos (consistente con otros módulos)
            detalle.tag_configure(
                "header", foreground="cyan", font=("TkDefaultFont", 10, "bold")
            )
            detalle.tag_configure(
                "section", foreground="yellow", font=("TkDefaultFont", 9, "bold")
            )
            detalle.tag_configure("info", foreground="lightgreen")
            detalle.tag_configure("summary", foreground="orange")
            detalle.tag_configure("value", foreground="white")
            detalle.tag_configure("data", foreground="lightgray", font=("Courier", 8))
            detalle.tag_configure("error", foreground="red")
            detalle.tag_configure("warning", foreground="orange")

            lista.tag_configure("item", foreground="lightgreen")
            lista.tag_configure("empty", foreground="gray")

            # --- Scrollbars ---
            hsb = ttk.Scrollbar(detalle, orient=tk.HORIZONTAL, command=detalle.xview)
            detalle.configure(xscroll=hsb.set)
            hsb.pack(side=tk.BOTTOM, fill=tk.X)

            # --- Botonera ---
            frame_btn = ttk.Frame(self.cache)
            frame_btn.pack(fill=tk.X, pady=(0, 5), padx=5)

            ttk.Button(frame_btn, text="🔄 Refrescar", command=refresh_cache_list).pack(
                side=tk.LEFT, padx=5
            )
            ttk.Button(frame_btn, text="🗑️ Eliminar", command=remove_selected_key).pack(
                side=tk.LEFT, padx=5
            )

            # --- Bind eventos ---
            lista.bind("<Double-Button-1>", on_double_click)
            lista.bind("<<TreeviewSelect>>", on_item_selected)

            # Mostrar mensaje inicial en detalle
            detalle.insert(
                "", "end", text="👈 Selecciona un item de la izquierda", tags=("info",)
            )
            detalle.insert(
                "", "end", text="para ver su información detallada", tags=("info",)
            )
            detalle.insert("", "end", text="", tags=("spacer",))
            detalle.insert(
                "",
                "end",
                text="💡 Click simple o doble click para ver detalles",
                tags=("summary",),
            )

            # --- Carga inicial y auto-refresh ---
            refresh_cache_list()
            auto_refresh()

        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"monitor_cache(): {e}")

    # detalla estados de conexiones
    def connect_api(self):
        """
        Visualiza estado de conexiones API en lista compacta.
        - LISTA: APIs disponibles con estado e icono
        - EVENTO: Doble click abre ventana con detalles completos

        APIs monitoreadas:
            ✅ Binance (WebSocket Streams & API Client)
            ✅ Interactive Brokers (IBKR)
            ✅ Yahoo Finance
            ✅ Finviz
        """

        def get_api_status():
            """Obtiene el estado actual de las APIs"""
            apis = {}

            try:
                # Binance WebSocket Streams
                try:
                    binance_ws = (
                        hasattr(DataHub, "WStreams") and DataHub.WStreams is not None
                    )
                    apis["Binance WebSocket"] = {
                        "status": "🟢 Conectado" if binance_ws else "🔴 Desconectado",
                        "type": "WebSocket Streams",
                        "endpoint": "wss://stream.binance.com:9443",
                        "connected": binance_ws,
                        "description": "Streaming de precios en tiempo real",
                    }
                except:
                    apis["Binance WebSocket"] = {
                        "status": "⚪ No Disponible",
                        "type": "WebSocket Streams",
                        "endpoint": "N/A",
                        "connected": False,
                        "description": "Streaming de precios en tiempo real",
                    }

                # Binance API Client
                try:
                    binance_api = (
                        hasattr(DataHub, "WsClient") and DataHub.WsClient is not None
                    )
                    apis["Binance API"] = {
                        "status": "🟢 Conectado" if binance_api else "🔴 Desconectado",
                        "type": "WebSocket API Client",
                        "endpoint": "wss://ws-api.binance.com:443/ws-api/v3",
                        "connected": binance_api,
                        "description": "API de trading y consultas",
                    }
                except:
                    apis["Binance API"] = {
                        "status": "⚪ No Disponible",
                        "type": "WebSocket API Client",
                        "endpoint": "N/A",
                        "connected": False,
                        "description": "API de trading y consultas",
                    }

                # Yahoo Finance
                try:
                    yfinance = DataHub.SessionYfinance is not None
                    apis["Yahoo Finance"] = {
                        "status": "🟢 Activo" if yfinance else "🔴 Inactivo",
                        "type": "HTTP REST API",
                        "endpoint": "https://query1.finance.yahoo.com",
                        "connected": yfinance,
                        "description": "Datos de mercado y fundamentales",
                    }
                except:
                    apis["Yahoo Finance"] = {
                        "status": "⚪ No Disponible",
                        "type": "HTTP REST API",
                        "endpoint": "N/A",
                        "connected": False,
                        "description": "Datos de mercado y fundamentales",
                    }

                # Interactive Brokers
                apis["Interactive Brokers"] = {
                    "status": "🟡 Configurado",
                    "type": "TWS API",
                    "endpoint": "localhost:7497",
                    "connected": True,  # Asumir configurado
                    "description": "Trading y datos de mercado",
                }

                # Finviz
                apis["Finviz"] = {
                    "status": "🟢 Disponible",
                    "type": "Web Scraping",
                    "endpoint": "https://finviz.com",
                    "connected": True,  # Siempre disponible si hay internet
                    "description": "Análisis técnico y fundamentales",
                }

            except Exception as e:
                print(f"[get_api_status()]: {e}")

            return apis

        def refresh_api_list():
            """Actualiza la lista de APIs"""
            try:
                # Limpiar lista
                for item in lista.get_children():
                    lista.delete(item)

                # Obtener estado de APIs
                apis = get_api_status()

                # Contador de conectadas
                connected_count = sum(
                    1 for api in apis.values() if api.get("connected")
                )
                total_count = len(apis)

                # Insertar APIs en la lista con tres columnas
                for name, info in apis.items():
                    status = info["status"]
                    api_type = info["type"]

                    # Extraer solo el emoji de estado
                    status_emoji = status.split()[0] if status else "⚪"

                    lista.insert(
                        "",
                        tk.END,
                        text=name,  # Nombre de API
                        values=(api_type, status),  # Tipo y Estado completo
                        tags=("item",),
                    )

                # Actualizar header con contador
                lista.heading(
                    "#0", text=f"API ({connected_count}/{total_count} activas)"
                )

            except Exception as e:
                print(f"[refresh_api_list()]: {e}")

        def show_api_detail_window(api_name):
            """Abre ventana emergente con detalles de la API seleccionada"""
            try:
                # El nombre ya viene limpio (sin emoji)
                clean_name = api_name

                # Obtener información de la API
                apis = get_api_status()
                api_info = apis.get(clean_name)

                if not api_info:
                    self.messagebox.showwarning(
                        "API Info", f"⚠️ {clean_name}: No encontrada"
                    )
                    return

                # Crear ventana Toplevel
                detail_window = tk.Toplevel(self.system)
                detail_window.title(f"🌐 Información de API - {clean_name}")
                detail_window.geometry("600x450")
                detail_window.transient(self.system)  # Ventana modal relativa al padre

                # Frame principal con scrollbar
                main_frame = ttk.Frame(detail_window, padding=10)
                main_frame.pack(fill=tk.BOTH, expand=True)

                # Treeview para mostrar información
                tree = ttk.Treeview(main_frame, style="TFrame")
                tree.heading("#0", text=f"Detalles de {clean_name}")
                tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

                # Configurar colores
                tree.tag_configure(
                    "header", foreground="cyan", font=("TkDefaultFont", 11, "bold")
                )
                tree.tag_configure(
                    "section", foreground="yellow", font=("TkDefaultFont", 9, "bold")
                )
                tree.tag_configure("info", foreground="lightgreen")
                tree.tag_configure("summary", foreground="orange")
                tree.tag_configure("value", foreground="white")

                # Scrollbar
                vsb = ttk.Scrollbar(tree, orient=tk.VERTICAL, command=tree.yview)
                tree.configure(yscroll=vsb.set)
                vsb.pack(side=tk.RIGHT, fill=tk.Y)

                # Header
                tree.insert("", "end", text=f"🌐 API: {clean_name}", tags=("header",))
                tree.insert("", "end", text="", tags=("spacer",))

                # Información básica
                tree.insert(
                    "", "end", text=f"📊 Estado: {api_info['status']}", tags=("info",)
                )
                tree.insert(
                    "", "end", text=f"🔧 Tipo: {api_info['type']}", tags=("info",)
                )
                tree.insert(
                    "",
                    "end",
                    text=f"🔗 Endpoint: {api_info['endpoint']}",
                    tags=("value",),
                )
                tree.insert(
                    "",
                    "end",
                    text=f"📝 Descripción: {api_info['description']}",
                    tags=("summary",),
                )

                # Timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                tree.insert(
                    "", "end", text=f"⏰ Consultado: {timestamp}", tags=("info",)
                )
                tree.insert("", "end", text="", tags=("spacer",))

                # Información adicional según API
                node = tree.insert(
                    "", "end", text="📋 Información Adicional", tags=("section",)
                )

                if "Binance" in clean_name:
                    tree.insert(
                        node,
                        "end",
                        text="  • Mercado: Cryptocurrencies",
                        tags=("value",),
                    )
                    tree.insert(
                        node, "end", text="  • Frecuencia: Tiempo real", tags=("value",)
                    )
                    tree.insert(
                        node,
                        "end",
                        text="  • Límites: Sin límite en WebSocket",
                        tags=("value",),
                    )
                    tree.insert(
                        node,
                        "end",
                        text="  • Documentación: https://binance-docs.github.io",
                        tags=("value",),
                    )

                elif "Yahoo Finance" in clean_name:
                    tree.insert(
                        node,
                        "end",
                        text="  • Mercado: Stocks, ETFs, Indices",
                        tags=("value",),
                    )
                    tree.insert(
                        node,
                        "end",
                        text="  • Frecuencia: 15 min delay (free)",
                        tags=("value",),
                    )
                    tree.insert(
                        node, "end", text="  • Límites: 2000 req/hora", tags=("value",)
                    )
                    tree.insert(
                        node, "end", text="  • Cobertura: Global", tags=("value",)
                    )

                elif "Interactive Brokers" in clean_name:
                    tree.insert(
                        node,
                        "end",
                        text="  • Mercado: Global (Stocks, Forex, etc)",
                        tags=("value",),
                    )
                    tree.insert(
                        node, "end", text="  • Frecuencia: Tiempo real", tags=("value",)
                    )
                    tree.insert(
                        node,
                        "end",
                        text="  • Requiere: TWS o IB Gateway activo",
                        tags=("value",),
                    )
                    tree.insert(
                        node,
                        "end",
                        text="  • Puerto: 7497 (TWS) / 4002 (Gateway)",
                        tags=("value",),
                    )

                elif "Finviz" in clean_name:
                    tree.insert(
                        node, "end", text="  • Mercado: US Stocks", tags=("value",)
                    )
                    tree.insert(
                        node,
                        "end",
                        text="  • Datos: Screener, Charts, News",
                        tags=("value",),
                    )
                    tree.insert(
                        node, "end", text="  • Método: Web Scraping", tags=("value",)
                    )
                    tree.insert(
                        node,
                        "end",
                        text="  • Limitaciones: Requiere acceso web",
                        tags=("value",),
                    )

                # Expandir nodo
                tree.item(node, open=True)

                # Botón cerrar
                btn_frame = ttk.Frame(main_frame)
                btn_frame.pack(fill=tk.X, pady=(5, 0))

                ttk.Button(
                    btn_frame, text="✖️ Cerrar", command=detail_window.destroy
                ).pack(side=tk.RIGHT, padx=5)

                # Centrar ventana
                detail_window.update_idletasks()
                x = (detail_window.winfo_screenwidth() // 2) - (600 // 2)
                y = (detail_window.winfo_screenheight() // 2) - (450 // 2)
                detail_window.geometry(f"600x450+{x}+{y}")

            except Exception as e:
                import traceback

                traceback.print_exc()
                print(f"[show_api_detail_window({api_name})]: {e}")
                self.messagebox.showerror("Error", f"❌ Error al mostrar detalle: {e}")

        def on_double_click(event):
            """Maneja doble click para abrir ventana de detalle"""
            selected = lista.selection()
            if selected:
                api_name = lista.item(selected[0], "text")
                show_api_detail_window(api_name)

        def auto_refresh():
            """Auto-actualiza la lista cada 30 segundos"""
            # Verificar si debemos continuar ejecutando
            if not self.is_running:
                return

            refresh_api_list()
            # Registrar el after_id para poder cancelarlo luego
            after_id = self.system.after(30000, auto_refresh)
            self.after_ids.append(after_id)

        try:
            # Frame contenedor principal
            main_frame = ttk.Frame(self.connect)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Label de instrucciones
            info_frame = ttk.Frame(main_frame)
            info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

            ttk.Label(
                info_frame,
                text="💡 Doble click en una API para ver detalles completos",
                foreground="orange",
                font=("TkDefaultFont", 8, "italic"),
            ).pack(side=tk.LEFT)

            # Crear TreeView solo para lista (más espacio)
            lista = ttk.Treeview(
                main_frame, columns=("tipo", "estado"), style="TFrame", height=12
            )

            # Configurar headers y columnas
            lista.heading("#0", text="API")
            lista.heading("tipo", text="Tipo de Conexión")
            lista.heading("estado", text="Estado")

            lista.column("#0", width=180, minwidth=150)
            lista.column("tipo", width=150, minwidth=120)
            lista.column("estado", width=120, minwidth=100)

            # Pack lista con scrollbar
            lista.pack(fill=tk.BOTH, expand=True)

            # Configurar colores
            lista.tag_configure("item", foreground="lightgreen")

            # --- Scrollbars ---
            vsb = ttk.Scrollbar(lista, orient=tk.VERTICAL, command=lista.yview)
            lista.configure(yscroll=vsb.set)
            vsb.pack(side=tk.RIGHT, fill=tk.Y)

            # --- Bind evento doble click ---
            lista.bind("<Double-Button-1>", on_double_click)

            # --- Carga inicial y auto-refresh ---
            refresh_api_list()
            auto_refresh()
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"connect_api(): {e}")

    # detalla estados de conexiones
    def debugging_system(self):
        try:

            cols = ["Option"]
            tree = ttk.Treeview(self.debugging, columns=cols, height=15, style="TFrame")
            tree.heading("#0", text="Logger")
            tree.heading("Option", text="Level")

            tree.column("#0", width=200, minwidth=100)
            tree.column("Option", width=80, minwidth=80)
            tree.pack(expand=True, fill="both", pady=5, padx=(5, 5))

            for key, handler in DataHub.logger.items():
                tree.insert(
                    "",
                    "end",
                    text=f"{key}",
                    values=f"{logging.getLevelName(handler.level)}",
                )
        except (EncodingWarning, Exception) as e:
            print("debugging_system(): {}".format(e))

    # visualiza manager_buysell con lista-detalle
    def manager_buysell_system(self):
        """
        Visualiza DataHub.manager_buysell con patrón lista-detalle.
        - LISTA (izquierda): Keys de manager_buysell (dividends, sector, activos, region)
        - DETALLE (derecha): Información completa y resumen del item seleccionado
        - Evento: Doble click para ver detalle
        """

        def display_buysell_detail(key):
            """Muestra detalle del item seleccionado en manager_buysell"""
            try:
                # Limpiar detalle
                for item in detalle.get_children():
                    detalle.delete(item)

                # Obtener datos
                data = DataHub.manager_buysell.get(key)

                if data is None:
                    detalle.insert(
                        "", "end", text=f"⚠️ {key}: No disponible aún", tags=("warning",)
                    )
                    return

                # Header con el nombre del item
                detalle.insert(
                    "", "end", text=f"📊 Item: {key.upper()}", tags=("header",)
                )
                detalle.insert("", "end", text="", tags=("spacer",))

                # Información del tipo de objeto
                tipo_data = type(data).__name__
                detalle.insert(
                    "", "end", text=f"Tipo de objeto: {tipo_data}", tags=("info",)
                )

                # Timestamp de actualización
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                detalle.insert(
                    "", "end", text=f"Última consulta: {timestamp}", tags=("info",)
                )
                detalle.insert("", "end", text="", tags=("spacer",))

                # Mostrar estructura completa del objeto
                node_estructura = detalle.insert(
                    "", "end", text="📂 Estructura Completa", tags=("section",)
                )

                # Si es un diccionario, mostrar sus claves y valores
                if isinstance(data, dict):
                    detalle.insert(
                        "",
                        "end",
                        text=f"Total de claves: {len(data)}",
                        tags=("summary",),
                    )
                    detalle.insert("", "end", text="", tags=("spacer",))

                    for subkey, subvalue in data.items():
                        if isinstance(subvalue, dict):
                            # Crear nodo expandible para diccionarios anidados
                            subnode = detalle.insert(
                                node_estructura,
                                "end",
                                text=f"🔹 {subkey}",
                                tags=("subkey",),
                            )
                            for k, v in subvalue.items():
                                detalle.insert(
                                    subnode, "end", text=f"  {k}: {v}", tags=("value",)
                                )
                        elif isinstance(subvalue, (list, tuple)):
                            # Mostrar listas/tuplas
                            subnode = detalle.insert(
                                node_estructura,
                                "end",
                                text=f"🔹 {subkey} (lista con {len(subvalue)} elementos)",
                                tags=("subkey",),
                            )
                            for idx, item in enumerate(
                                subvalue[:10]
                            ):  # Mostrar solo primeros 10
                                detalle.insert(
                                    subnode,
                                    "end",
                                    text=f"  [{idx}]: {item}",
                                    tags=("value",),
                                )
                            if len(subvalue) > 10:
                                detalle.insert(
                                    subnode,
                                    "end",
                                    text=f"  ... y {len(subvalue) - 10} más",
                                    tags=("value",),
                                )
                        elif isinstance(subvalue, pd.DataFrame):
                            # Mostrar info de DataFrames
                            df_info = f"DataFrame: {subvalue.shape[0]} filas × {subvalue.shape[1]} columnas"
                            subnode = detalle.insert(
                                node_estructura,
                                "end",
                                text=f"🔹 {subkey}",
                                tags=("subkey",),
                            )
                            detalle.insert(
                                subnode, "end", text=f"  {df_info}", tags=("value",)
                            )
                            detalle.insert(
                                subnode,
                                "end",
                                text=f"  Columnas: {list(subvalue.columns)}",
                                tags=("value",),
                            )
                        else:
                            # Valores simples
                            detalle.insert(
                                node_estructura,
                                "end",
                                text=f"🔹 {subkey}: {subvalue}",
                                tags=("value",),
                            )

                # Si es DataFrame directamente
                elif isinstance(data, pd.DataFrame):
                    detalle.insert(
                        "", "end", text="📋 Resumen del DataFrame", tags=("section",)
                    )
                    detalle.insert(
                        "", "end", text=f"Filas: {data.shape[0]}", tags=("summary",)
                    )
                    detalle.insert(
                        "", "end", text=f"Columnas: {data.shape[1]}", tags=("summary",)
                    )
                    detalle.insert(
                        "",
                        "end",
                        text=f"Columnas: {list(data.columns)}",
                        tags=("summary",),
                    )

                    # Mostrar primeras filas
                    detalle.insert("", "end", text="", tags=("spacer",))
                    detalle.insert(
                        "", "end", text="📊 Primeras 5 filas:", tags=("section",)
                    )
                    df_string = data.head().to_string()
                    for line in df_string.split("\n"):
                        detalle.insert("", "end", text=line, tags=("data",))

                # Si es otro tipo de objeto
                else:
                    detalle.insert(
                        node_estructura, "end", text=str(data)[:500], tags=("value",)
                    )

                # Expandir nodo principal
                detalle.item(node_estructura, open=True)

            except Exception as e:
                detalle.insert(
                    "", "end", text=f"❌ Error al mostrar detalle: {e}", tags=("error",)
                )
                print(f"[display_buysell_detail({key})]: {e}")

        def on_double_click(event):
            """Evento de doble click en la lista"""
            selected = lista.selection()
            if selected:
                key = lista.item(selected[0], "text")
                display_buysell_detail(key)

        def update_buysell_list():
            """Actualiza la lista de manager_buysell cada 30 segundos"""
            try:
                # Verificar si debemos continuar ejecutando
                if not self.is_running:
                    return

                # Limpiar lista
                for item in lista.get_children():
                    lista.delete(item)

                # Insertar keys de manager_buysell
                if DataHub.manager_buysell:
                    for key in sorted(DataHub.manager_buysell.keys()):
                        lista.insert("", "end", text=key, tags=("item",))
                else:
                    lista.insert(
                        "", "end", text="(Vacío - esperando datos)", tags=("empty",)
                    )

                # Programar siguiente actualización y registrar el after_id
                after_id = self.system.after(30000, update_buysell_list)
                self.after_ids.append(after_id)

            except Exception as e:
                print(f"[update_buysell_list()]: {e}")

        try:
            # Crear TreeViews para lista y detalle
            lista = ttk.Treeview(self.buysell, style="TFrame")
            detalle = ttk.Treeview(self.buysell, style="TFrame")

            # Configurar headers
            lista.heading("#0", text="Manager BuySell")
            detalle.heading("#0", text="Información Detallada")

            # Configurar anchos
            lista.column("#0", width=180, minwidth=150)

            # Pack widgets
            lista.pack(side=tk.LEFT, fill=tk.BOTH, pady=5, padx=(5, 2))
            detalle.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5, padx=(2, 5))

            # Configurar colores y estilos
            detalle.tag_configure(
                "header", foreground="cyan", font=("TkDefaultFont", 10, "bold")
            )
            detalle.tag_configure(
                "section", foreground="yellow", font=("TkDefaultFont", 9, "bold")
            )
            detalle.tag_configure("info", foreground="lightgreen")
            detalle.tag_configure("summary", foreground="orange")
            detalle.tag_configure("subkey", foreground="lightblue")
            detalle.tag_configure("value", foreground="white")
            detalle.tag_configure("data", foreground="lightgray", font=("Courier", 8))
            detalle.tag_configure("error", foreground="red")
            detalle.tag_configure("warning", foreground="orange")
            lista.tag_configure("item", foreground="lightgreen")
            lista.tag_configure("empty", foreground="gray")

            # Bind evento doble click
            lista.bind("<Double-Button-1>", on_double_click)

            # Scrollbars para detalle
            hsb = ttk.Scrollbar(detalle, orient=tk.HORIZONTAL, command=detalle.xview)
            detalle.configure(xscroll=hsb.set)
            hsb.pack(side=tk.BOTTOM, fill=tk.X)

            # Iniciar actualización de lista
            update_buysell_list()

            # Mostrar mensaje inicial en detalle
            detalle.insert(
                "",
                "end",
                text="👈 Haz doble click en un item de la izquierda",
                tags=("info",),
            )
            detalle.insert(
                "", "end", text="para ver su información detallada", tags=("info",)
            )
        except Exception as e:
            print(f"manager_buysell_system(): {e}")

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

        # toma series de datos desde DataHub - OPTIMIZADO
        def update(frame):
            try:
                # Verificar que los datos existen y tienen CpuLock
                if not hasattr(DataHub, "CpuLock") or DataHub.CpuLock is None:
                    return line_cpu, line_mem

                # Verificar que hay datos
                if not DataHub.DCpu or not DataHub.DMem:
                    return line_cpu, line_mem

                with DataHub.CpuLock:
                    x = list(range(len(DataHub.DCpu)))
                    line_cpu.set_data(x, DataHub.DCpu)
                    line_mem.set_data(x, DataHub.DMem)

                    # Actualizar límites solo si cambió el tamaño
                    max_x = max(
                        len(x), DataHub.max_points if DataHub.max_points > 0 else 60
                    )
                    self.ax.set_xlim(0, max_x)

                return line_cpu, line_mem

            except Exception as e:
                # Silenciar errores para no interrumpir la animación
                return line_cpu, line_mem

        # OPTIMIZACIÓN: Intervalo más largo para reducir consumo de CPU
        # Cambiado de interval * 3000 (3 segundos) a 10 segundos
        interval_optimizado = 15000  # 10 segundos (antes era ~3 segundos)

        ani = animation.FuncAnimation(
            self.fg,
            update,
            interval=interval_optimizado,  # Actualiza cada 10 segundos
            blit=True,
            cache_frame_data=False,
            save_count=0,  # No guardar frames en caché (ahorro de memoria)
        )

        # Guardar referencia para evitar que se recolecte por garbage collector
        self.monitor_animation = ani

        self.rv.draw()


if __name__ == "__main__":
    app = DashMain()
    app.run()
