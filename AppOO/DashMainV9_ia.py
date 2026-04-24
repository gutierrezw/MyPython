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
from Class_ApiIBrks import IB
from Class_ApiBinnace import BinanceClient
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
    sys,
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
from Class_IA_modelos import ModeloOportunidadesSell
from Class_SystemStatus import system_status
from Class_BotCryptoUI import BotCryptoUI
from Class_BrowserBridge import start_tv_server, stop_tv_server, start_price_sync
from Class_Finance import FinancePanel


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
        self.Estrategia = EstrategiaInversion()

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
            run_now=True,
        )
        DataHub.manager_events.register_job(
            name=RemoteOrder,
            interval_sec=1,
            func=self.schedule_order_remote,
        )

        if vehiculo == "Stock":
            DataHub.manager_events.register_job(
                name=f"ib_offline_sync({vehiculo})",
                interval_sec=300,
                func=self.schedule_ib_offline_sync,
            )

    def schedule_ib_offline_sync(self):
        try:
            if not self.IClient.authenticated:
                result = self.ib_offline_sync()
                self.logger.warning(f"IBFallback yfinance: {result}")
                if " Conexión   :" in self.resumen:
                    self.resumen[" Conexión   :"] = "IB OFFLINE (yf)"
        except Exception as e:
            self.logger.error(f"schedule_ib_offline_sync(): {e}")

    def on_message_binance_websocket(self, _, message):
        # captura de evento de precio
        def procesa_stream_crypto(x_message):
            try:
                symbol, conid, d_precio = None, None, {}
                if "e" in x_message.keys():

                    symbol = x_message["s"]
                    timestamp = x_message["E"] / 1000  # Convertir a segundos
                    Stimestamp = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
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
                        account=self.account, symbol=symbol
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
                        struct["unrealizedpnl"] = struct["mktvalue"] - struct["costobase"]
                        struct["retorno"] = (
                            struct["unrealizedpnl"] / struct["costobase"] if struct["costobase"] > 0 else 0
                        )

                        # actualiza estructura positions y luego treeview para el symbol en cuestión
                        ix = self.update_symbol_en_positions(struct)

                        # agrega precio update a info()
                        self.update_precio_DataHubInfo(symbol=symbol, conid=conid, precio=d_precio)

                    self.WStreams.counter += 1
                    socket = "WebsocketBinanceStream_OnMessage(Crypto)"
                    DataHub.update_self_procesos(proces="widget", tarea=socket, itera=self.WStreams.counter)

            except Exception as e:
                print("procesa_stream_crypto(): {}".format(e))

        # ubica y almacenar en lista de órdenes: trasladado a get_orders_binance()
        def procesa_orders_crypto(x_message):
            try:
                if "result" in x_message:
                    response, orders = x_message["result"], []
                    if response:
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

                # contabiliza cada iteración
                self.WsClient.counter += 1
                DataHub.update_self_procesos(
                    proces="running",
                    tarea="schedule_WebsocketBinanceApiClient(Crypto)",
                    itera=self.WsClient.counter,
                )
            except Exception as e:
                print("procesa_orders_crypto(): {}".format(e))

        def procesa_execution_report_crypto(msg):
            """Actualiza order_trade y self.orders cuando llega un executionReport de Binance."""
            try:
                order_id = str(msg["i"])
                symbol = msg["s"]
                status = msg["X"]
                side = msg["S"]
                qty = float(msg.get("q", 0))
                cum_qty = float(msg.get("z", 0))
                timestamp = datetime.fromtimestamp(msg["T"] / 1000.0)

                values = {"status": status, "stampSubmit": timestamp}
                self.RepositorioOportunidades.update_order_trader(
                    account=self.account,
                    values=values,
                    symbol=symbol,
                    orderid=order_id,
                )

                for orden in self.orders.get("Crypto", []):
                    if str(orden.get("id_order")) == order_id:
                        orden["status"] = status
                        break

                self.logger.warning(
                    f"executionReport(Crypto): symbol={symbol} orderId={order_id} "
                    f"status={status} side={side} qty={qty} cumFilled={cum_qty}"
                )
            except Exception as e:
                print(f"[procesa_execution_report_crypto()]: {e}")

        try:
            data = json.loads(message)

            # captura de evento de precio
            if "e" in data.keys():
                if data["e"] == "24hrTicker":
                    procesa_stream_crypto(data)
                elif data["e"] == "executionReport":
                    procesa_execution_report_crypto(data)

            # captura otros eventos id Client: trasladado a get_orders_binance()
            # elif 'id' in data.keys():
            #         if data["id"] == "allOrders_5494febb":
            #            procesa_orders_crypto(data)
        except json.JSONDecodeError or Exception as error:
            print("[on_message_binance_websocket()]: {}".format(error))
            time.sleep(1)

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
                    struct["retorno"] = (struct["unrealizedpnl"] / costo) if costo > 0 else 0

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
                            self.conid_inicio[conid][field_name] = float(value.rstrip("%"))
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
                    update_field(x_conid, internal_name, FIELD_MAP[field], convert_to_float=False)

                # Procesar campos numéricos
                for field in NUMERIC_FIELDS:
                    internal_name = DIVIDEND_FIELD_MAPPING.get(field, field)
                    update_field(x_conid, internal_name, FIELD_MAP[field], convert_to_float=True)

                # Procesar timestamp
                timestamp = x_message["_updated"] / 1000  # Convertir a segundos
                timestamp_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

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
                    self.update_precio_DataHubInfo(symbol=symbol, conid=conid, precio=n_precio)
                    procesa_stock(d_precio=n_precio[symbol])

                    # cuenta las iteraciones websocket stock
                    self.WsStock.counter += 1

                    socket = f"WebsocketStream_OnMessage({self.vehiculo})"
                    DataHub.update_self_procesos(proces="widget", tarea=socket, itera=self.WsStock.counter)

            elif data["topic"] == "sor":
                # Smart Order Routing IB: args = lista de 1 dict con orderId/ticker/status
                try:
                    raw = data.get("args", [])
                    args = raw[0] if isinstance(raw, list) and raw else {}
                    order_id = str(args.get("orderId", ""))
                    status = args.get("status", "")
                    # ticker solo llega en el primer mensaje completo;
                    # en updates parciales lo buscamos en self.orders
                    symbol = args.get("ticker", "")
                    if not symbol:
                        for orden in self.orders.get("Stock", []):
                            if str(orden.get("id_order")) == order_id:
                                symbol = orden.get("symbol", "")
                                break
                    if order_id and status:
                        values = {"status": status}
                        threading.Thread(
                            target=self.RepositorioOportunidades.update_order_trader,
                            kwargs={
                                "account": self.account,
                                "values": values,
                                "symbol": symbol,
                                "orderid": order_id,
                            },
                            daemon=True,
                        ).start()
                        for orden in self.orders.get("Stock", []):
                            if str(orden.get("id_order")) == order_id:
                                orden["status"] = status
                                break
                        self.logger.warning(f"sor(Stock): symbol={symbol} orderId={order_id} status={status}")
                except Exception as e:
                    print(f"[on_message_IBrks_websocket(sor)]: {e}")

            elif not data["topic"].startswith("prefijo"):
                # print(f"data=={data}")
                pass
        except Exception as error:
            print("[on_message_IBrks_websocket({})]: {}".format(self.vehiculo, error))

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
                position["gypp"] = struct["position"] * struct["objetivo"] - struct["costobase"]
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
        except Exception as e:
            print("[update_symbol_en_positions({})]: {}".format(self.vehiculo, e))

    def update_peso_position(self):
        try:
            inversion = sum(position["costobase"] for position in self.positions)
            return inversion
        except Exception as e:
            print("[update_peso_position({})]: {}".format(self.vehiculo, e))

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
        except Exception as e:
            print("[update_positions({})]: {}".format(self.vehiculo, e))

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
                                w_trade = self.BClient.get_my_trades(ticket, limit=20, startTime=stime, endTime=etime)
                                if w_trade:
                                    for i in range(len(w_trade)):
                                        try:
                                            registro = dict()
                                            if w_trade[i]:

                                                registro.update({"categoria": self.vehiculo})
                                                registro.update({"divisa": "USD"})
                                                registro.update({"cuenta": self.account})

                                                qty = float(w_trade[i].get("qty", 0.0))
                                                qty = qty if w_trade[i]["isBuyer"] else -1 * qty
                                                quoteqty = float(w_trade[i].get("quoteQty", 0.0))
                                                registro.update({"cantidad": qty})
                                                registro.update({"producto": quoteqty})

                                                price = float(w_trade[i].get("price", 0.0))
                                                registro.update({"idtrans": str(w_trade[i].get("id"))})
                                                registro.update({"preciotrans": price})
                                                registro.update({"preciocierre": price})

                                                comision = (
                                                    float(w_trade[i].get("commission", 0.0)) * registro["preciotrans"]
                                                )
                                                registro.update({"tarifacomision": comision})
                                                registro.update({"mtmgp": 0.00})

                                                fechahora = datetime.fromtimestamp(w_trade[i].get("time", 0) / 1000)
                                                registro.update({"fechahora": fechahora})

                                                # valida existencia del trader
                                                found_hashId = self.RepositorioOportunidades.get_hash_booktrading(
                                                    accion="valida",
                                                    values=registro,
                                                    symbol=ticket,
                                                )

                                                if not found_hashId:

                                                    # Agrega indicadores técnicos al registro
                                                    temp = DataHub.info[ticket].get("datos_tecnicos", {})
                                                    indicadores = (
                                                        json.dumps(temp, default=str)
                                                        if isinstance(temp, dict)
                                                        else temp
                                                    )
                                                    registro.update({"indicadores": indicadores})

                                                    self.RepositorioOportunidades.insert_booktrading(
                                                        values=registro, symbol=ticket
                                                    )
                                        except (ValueError, Exception) as error:
                                            print(f"Error en w_trade {i} - {w_trade[i]}: {error}")
                            # espera para no saturar la API
                            time.sleep(0.8)

                    # Almacena ultima fecha en session que exploro API get_my_trades()
                    if efecha > DataHub.ultimoTraderCrypto:
                        DataHub.ultimoTraderCrypto = hoy + timedelta(days=-1)
            except Exception as error:
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
            except Exception as e:
                print(f"get_orders_binance(): {e}")

        # cargas ultimas compras de USDT
        def trade_USDT_diario():
            # ARS: compra USDT con ARS (BUY). VES: vende USDT por bolívares (SELL).
            fiat_config = {"ARS": "BUY", "VES": "SELL"}

            def get_trader_insert_fiat(trama=None, fiat=None, trade_type=None):
                try:
                    symbol, trader = "USDT", []
                    for keys, values in trama.items():
                        if keys == "data":
                            for i, rows in enumerate(values):

                                date = datetime.fromtimestamp(rows["createTime"] / 1000)
                                if (
                                    (rows["tradeType"] == trade_type)
                                    and (rows["orderStatus"] == "COMPLETED")
                                    and (rows["fiat"] == fiat)
                                ):
                                    values = {}

                                    values.update({"categoria": rows["fiat"]})
                                    values.update({"divisa": "USD"})
                                    values.update({"cuenta": rows["fiat"] + "-0001"})
                                    values.update({"fechahora": date})
                                    values.update({"idtrans": rows["advNo"]})
                                    values.update({"cantidad": float(rows["takerAmount"])})
                                    values.update({"preciotrans": float(rows["unitPrice"])})
                                    values.update({"preciocierre": float(rows["unitPrice"])})
                                    values.update({"producto": float(rows["totalPrice"])})
                                    values.update({"tarifacomision": 0.0})
                                    values.update({"gprealizadas": 0.0})
                                    values.update({"mtmgp": 0.0})
                                    values.update({"codigo": "O"})
                                    trader.append(values)

                    # orden ascendente por fecha
                    asc_trader = sorted(trader, key=lambda x: x["fechahora"], reverse=False)

                    # valida los trader antes de insert booktrading
                    for i, registro in enumerate(asc_trader):
                        found_hashId = self.RepositorioOportunidades.get_hash_booktrading(
                            accion="valida", values=registro, symbol=symbol
                        )

                        if not found_hashId:
                            self.RepositorioOportunidades.insert_booktrading(values=registro, symbol=symbol)

                    return asc_trader
                except Exception as error:
                    print(f"get_trader_insert_fiat(): {error}")

            try:
                hasta = datetime.today()
                desde = hasta - timedelta(days=60)
                start_time = int(desde.timestamp() * 1000)
                end_time = int(hasta.timestamp() * 1000)

                for fiat, trade_type in fiat_config.items():
                    response = self.BClient.get_c2c_trade_history(
                        tradeType=trade_type,
                        startTimestamp=start_time,
                        endTimestamp=end_time,
                        fiat=fiat,
                    )
                    if response:
                        get_trader_insert_fiat(trama=response, fiat=fiat, trade_type=trade_type)
            except Exception as e:
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
                trader, ix = self.RepositorioOportunidades.select_order_trader(account=self.account, symbol=symbol)

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
            def ubica_confirm(orden=None, conid=None, orderid=None, account=None, vehiculo=None):
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
                            and (is_null(keys[ix.index("clientOrderId")]) or is_vacio(keys[ix.index("clientOrderId")]))
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
                                if int(keys[ix.index("clientOrderId")]) == orden["orderId"]:
                                    return (
                                        True,
                                        orden["orderId"],
                                        keys[ix.index("id_order")],
                                    )
                    return False, clientOrderId, id_order
                except Exception as e:
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
            except Exception as e:
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
                        values.update({"divisa": keys.get("currency", "USD")})
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
                        found_hashId = self.RepositorioOportunidades.get_hash_booktrading(
                            accion="valida", values=registro, symbol=simbolo
                        )

                        # inserta trade en booktrading
                        if not found_hashId:

                            # Agrega indicadores técnicos al registro
                            temp = DataHub.info[simbolo].get("datos_tecnicos", {})
                            indicadores = json.dumps(temp, default=str) if isinstance(temp, dict) else temp
                            registro.update({"indicadores": indicadores})

                            self.RepositorioOportunidades.insert_booktrading(values=registro, symbol=simbolo)
            except Exception as e:
                self.logger.error(f"trader_iteractive(): {e}")

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

                        crypto, found = self.RepositorioOportunidades.select_otros_activos(
                            account=self.account, symbol=asset
                        )
                        found, self_position = buscar_ticker(self.positions, asset)

                        # obtiene información de dividendos
                        yf_activo, datos, ind_update = self.ts_yfinance_symbol(symbol=asset, vehiculo=self.vehiculo)

                        keys_asset = values["position"]
                        position["mrkprice"] = self_position["mrkprice"]
                        position["dgyp"] = self_position["dgyp"]
                        position["open"] = self_position["open"]

                        position["position"] = keys_asset["borrowed"] + keys_asset["netAsset"]
                        position["objetivo"] = crypto[0]["objetivo"]
                        position["empresa"] = crypto[0]["descripcion"]
                        position["costobase"] = crypto[0]["avgcost"] * position["position"]
                        position["dividendo"] = keys_asset["rewards"] * position["mrkprice"]
                        position["mktvalue"] = position["mrkprice"] * position["position"]

                        position["unrealizedpnl"] = position["mktvalue"] - position["costobase"]

                        if position["costobase"] > 0:
                            position["retorno"] = position["unrealizedpnl"] / position["costobase"]
                        else:
                            position["retorno"] = 0
                        position["deuda"] = keys_asset["debit USDT"]

                        # rescribe el peso de la position
                        position["peso"] = position["costobase"] / self.update_peso_position()

                        position["sectype"] = yf_activo.get("quoteType")
                        position["region"], position["country"] = "Crypto", "Crypto"
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
                            crypto, found = self.RepositorioOportunidades.select_otros_activos(symbol=asset)
                            if not found:
                                crypto, found = self.RepositorioOportunidades.insert_otros_activos(symbol=asset)

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

                            p["position"] = keys_asset["borrowed"] + keys_asset["netAsset"]
                            p["objetivo"] = crypto[0]["objetivo"]
                            p["mrkprice"] = crypto[0]["avgcost"]
                            p["costobase"] = crypto[0]["avgcost"] * p["position"]
                            p["dividendo"] = keys_asset["rewards"] * p["mrkprice"]
                            p["mktvalue"] = p["mrkprice"] * p["position"]

                            p["unrealizedpnl"] = p["mktvalue"] - p["costobase"]
                            p["retorno"] = p["unrealizedpnl"] / p["costobase"] if p["costobase"] > 0 else 0
                            p["deuda"] = keys_asset["debit USDT"]
                            p["open"] = 0.0
                            p["dgyp"] = 0.0

                            # rescribe el peso de la position
                            p["peso"] = p["costobase"] / self.update_peso_position()

                            p["region"], p["country"] = "Crypto", "Crypto"

                            x_positions.append(p)

                            eof_abook, (asset, values) = next(abook, (None, None))
                        else:
                            eof_pbook, position = next(pbook, (None, None))

                return x_positions
            except Exception as e:
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
            except Exception as e:
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
                            symbol = keys["asset"] + "USDT" if keys["asset"] != "USDT" else keys["asset"]

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
                        assets[keys]["position"]["debit USDT"] = float(field["totalDebt"])

        # actualiza tablas y variables globales
        def update_entorno_e_inversion():
            positions = self.RepositorioOportunidades.select_inversion(tipoin=self.vehiculo, ticket="all")

            self.assets, self.activos = {}, []
            for keys, value in assets.items():
                if "position" in value.keys():
                    self.assets.update({keys: value})
                    self.activos.append(keys)

            # si hay position en assets e in_position != [] actualiza la tabla inversion
            if positions and self.assets:
                out_positions = update_inversion_crypto(api=self.assets, in_positions=positions)

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
        except Exception as e:
            print("[api_vehiculo_binance()]: {}".format(e))

    # declara las api de Interactive Brockers
    def api_vehiculo_iteractive(self):
        # obtiene las diferentes divisas que maneja el portafolio
        def currency_account(ledger):

            for moneda, value in ledger.items():
                self.currency.update({moneda: value["exchangerate"]})

        # p_cartera instancia API vs p_positions tabla inversión
        def update_inversion_stock(p_cartera, p_positions):
            def get_dividends_yfinance():

                exDividendDate, dividendo = "9999-12-31", 0.0
                dividendYield = yf_activo.get("dividendYield", 0)
                price = yf_activo.get("previousClose", 0)

                if yf_activo.get("quoteType") in ("STK", "EQUITY"):

                    # si ha pagado dividndo en los ultimos 12 meses
                    if yf_activo.get("trailingAnnualDividendRate", 0) > 0:
                        dividendo = price * dividendYield / 100

                        # ultima instaancia -- para obtener el dividendo
                        if "dividendRate" in yf_activo:
                            dividendo = yf_activo["dividendRate"]

                if yf_activo.get("quoteType") == "ETF":
                    dividendo = price * dividendYield / 100

                if "exDividendDate" in yf_activo:
                    exDividendDate = datetime.fromtimestamp(yf_activo["exDividendDate"])

                return dividendo, dividendYield, exDividendDate

            try:
                # acumular en local para evitar race condition con schedule_operativo
                x_activos, x_positions = [], []
                _dbg_tickets = {pos["ticket"] for pos in self.positions}
                for key in p_cartera:

                    symbol = key["contractDesc"]

                    # descarta symbolos migrados (split)
                    if symbol.endswith(".OLD"):
                        continue

                    # encuentra factor de conversión para las positions que no están USD
                    p = {}
                    factor = self.currency[key["currency"]]
                    symbol = key["contractDesc"]

                    # obtiene información de dividendos
                    yf_activo, datos, ind_update = self.ts_yfinance_symbol(symbol=symbol, vehiculo=self.vehiculo)

                    objetivo, x_open, price, empresa = 0.0, 0.0, 0.0, ""
                    sector = key["sector"] if "sector" in key else "buscar"

                    price = key["mktPrice"]

                    # captura el dividendo del activo
                    dividendo, dividendYield, exDividendDate = get_dividends_yfinance()

                    x_open = yf_activo.get("open", 0) * factor

                    # fija precio objetivo
                    objetivo = yf_activo.get("targetMeanPrice", 0)
                    if objetivo == 0:
                        objetivo = yf_activo.get("targetHighPrice", 0)
                    if objetivo == 0:
                        objetivo = yf_activo.get("targetLowPrice", 0)
                    if objetivo == 0:
                        objetivo = yf_activo.get("fiftyTwoWeekHigh", 0)

                    # sector: yfinance es fuente de verdad; si no trae dato, preservar el de BD
                    sector = yf_activo.get("sector", "")
                    if is_vacio(sector) or is_null(sector):
                        existing = next((pos["sector"] for pos in p_positions if pos["ticket"] == symbol), "")
                        sector = existing if existing and not is_vacio(existing) and not is_null(existing) else ""

                    empresa = yf_activo.get("longName", "revisar ------")

                    p["sectype"] = yf_activo.get("quoteType")
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
                    p["retorno"] = (key["mktValue"] - p["costobase"]) / p["costobase"] if p["costobase"] > 0 else 0
                    p["sector"] = sector
                    p["ticket"] = symbol
                    p["deuda"] = 0
                    p["conid"] = str(key["conid"])
                    p["open"] = x_open
                    p["factor_cambio"] = factor
                    p["divisa"] = key.get("currency", "USD")
                    p["dgyp"] = (p["mrkprice"] - p["open"] if p["open"] > 0 else 0) * p["position"]
                    p["peso"] = 0

                    # obtiene la positions anterior, la estrategia y otros valores
                    for position in p_positions:
                        if position["ticket"] == p["ticket"]:
                            p["estrategia"] = position["estrategia"]
                            p["objetivo"] = position["objetivo"] if p["objetivo"] == 0 else p["objetivo"]

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
                    # solo suscribir símbolos activos — self.positions ya filtra position>0 y costobase>5
                    if symbol in _dbg_tickets:
                        x_activos.append(p["conid"])
                    x_positions.append(p)
                # asignación atómica al final — evita corrupción por race condition con schedule_operativo
                self.activos = x_activos
                return x_positions
            except Exception as e:
                print("update_inversion_stock(): {}".format(e))

        try:
            response = self.IClient.portfolio_account_ledger(account_id=self.account)
            if response:
                # almacena las currency para aplicar conversión a las posiciones
                currency_account(response)
                self.summary = response

                # obtiene positions a partir de API
                cartera = self.IClient.portfolio_account_positions(account_id=self.account, page_id=0)
                in_positions = self.RepositorioOportunidades.select_inversion(tipoin=self.vehiculo, ticket="all")

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
        except Exception as error:
            print(f"conector_api_vehiclo({self.vehiculo}): {error}")
            time.sleep(5)

    """ actualiza stock en tabla market -- estrategia de dividendos para el portfolio"""

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

    """ Helper: calcula meses de pago desde ex-dividend date"""

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

    def _validate_dividend_data_freshness(self, symbol, activo, dividends_history, display_log=False):
        """
        Valida que los datos de dividendos estén actualizados.

        PROBLEMA DETECTADO: yfinance a veces retiene datos obsoletos de activos
        que dejaron de pagar dividendos.

        Validaciones aplicadas:
        1. Si tiene dividendRate > 0 → debe tener historial de pagos
        2. Si último pago fue hace >18 meses → datos obsoletos
        3. Si tiene trailingAnnualDividendRate > 0 → debe tener al menos 1 pago en últimos 12 meses

        Args:
            activo (dict): Información del activo desde yf.Ticker.info
            dividends_history (pd.Series): Historial de dividendos

        Returns:
            tuple: (is_valid, warning_message)
                - is_valid (bool): True si los datos parecen actualizados
                - warning_message (str): Mensaje de advertencia si hay problemas
        """
        try:
            # Extraer campos clave
            dividend_rate = activo.get("dividendRate", 0)
            trailing_annual = activo.get("trailingAnnualDividendRate", 0)
            ex_dividend_date = activo.get("exDividendDate")

            # ============================================================================
            # VALIDACIÓN 1: Si tiene dividendRate pero sin historial → sospechoso
            # ============================================================================
            if dividend_rate > 0 and len(dividends_history) == 0:
                return (
                    False,
                    "⚠️ {symbol}: Tiene dividendRate pero sin historial de pagos. Verificar manualmente.",
                )

            # ============================================================================
            # VALIDACIÓN 2: Si tiene historial, verificar último pago (no más de 18 meses)
            # ============================================================================
            if dividend_rate > 0 and len(dividends_history) > 0:
                # Verificar último pago
                last_payment_date = dividends_history.index[-1]

                # Normalizar timezone
                if last_payment_date.tz is not None:
                    last_payment_date = last_payment_date.tz_localize(None)

                # Si el último pago fue hace más de 18 meses, datos probablemente obsoletos
                cutoff_18_months = pd.Timestamp.now() - pd.DateOffset(months=18)
                cutoff_18_months = cutoff_18_months.tz_localize(None)

                if last_payment_date < cutoff_18_months:
                    warning = f"⚠️  {symbol}: Último pago hace más de 18 meses ({last_payment_date.strftime('%Y-%m-%d')}). Datos posiblemente obsoletos."
                    return False, warning

            # ============================================================================
            # VALIDACIÓN 3: Si tiene trailingAnnualDividendRate > 0 → debe haber pagado
            #               al menos 1 dividendo en los últimos 12 meses (TTM)
            # CRÍTICO: Esta es la validación clave que sugirió el usuario
            # ============================================================================
            if trailing_annual > 0:
                if len(dividends_history) == 0:
                    return (
                        False,
                        f"⚠️ {symbol}: Tiene trailingAnnualDividendRate=${trailing_annual:.2f} pero sin historial. Datos inconsistentes.",
                    )

                # Calcular fecha de corte (últimos 12 meses - TTM)
                cutoff_12_months = pd.Timestamp.now() - pd.DateOffset(months=12)
                cutoff_12_months = cutoff_12_months.tz_localize(None)

                # Normalizar índice de dividendos
                dividends_index = dividends_history.index
                if dividends_index.tz is not None:
                    dividends_index = dividends_index.tz_localize(None)

                # Filtrar pagos de los últimos 12 meses
                recent_payments = [
                    (
                        date,
                        dividends_history.loc[dividends_history.index == date].iloc[0],
                    )
                    for date in dividends_history.index
                    if date.tz_localize(None) > cutoff_12_months
                ]

                if len(recent_payments) == 0:
                    # Tiene trailingAnnualDividendRate pero NO hay pagos en últimos 12 meses
                    # Esto es una INCONSISTENCIA CRÍTICA
                    last_payment = dividends_history.index[-1]
                    if last_payment.tz is not None:
                        last_payment = last_payment.tz_localize(None)

                    warning = (
                        f"⚠️  {symbol}: Tiene trailingAnnualDividendRate=${trailing_annual:.2f} pero SIN pagos en últimos 12 meses. "
                        f"Último pago: {last_payment.strftime('%Y-%m-%d')}. Datos OBSOLETOS."
                    )
                    return False, warning

                # VALIDACIÓN ADICIONAL: Verificar que TTM reportado coincida con suma real
                total_ttm_calculated = sum(amount for _, amount in recent_payments)
                difference = abs(trailing_annual - total_ttm_calculated)

                # Si la diferencia es mayor al 20%, advertir (puede ser cambio reciente)
                if difference > (trailing_annual * 0.20) and display_log:
                    warning = (
                        f"⚠️  {symbol}: trailingAnnualDividendRate reportado (${trailing_annual:.2f}) difiere "
                        f"{difference:.2f} del calculado (${total_ttm_calculated:.2f}). "
                        f"Posible cambio reciente o datos desactualizados."
                    )
                    # No marcar como inválido, solo advertir
                    # return False, warning  # Comentado: permitir continuar

                    print(f"[VALIDACIÓN TTM] {warning}")

            # Si pasó todas las validaciones
            return True, ""
        except Exception as e:
            print(f"[_validate_dividend_data_freshness()]: {e}")
            traceback.print_exc()
            return True, ""  # En caso de error, asumir válido para no bloquear

    def _extract_dividend_payment_months(self, dividends_history):
        """
        Extrae meses de pago de dividendos desde el historial real (últimos 12 meses).

        Basado en test_yfinance_dividends_fields.py - Método mejorado que:
        - Analiza pagos de los últimos 12 meses (no solo año anterior)
        - Maneja correctamente zonas horarias
        - Detecta frecuencia de pago (mensual, trimestral, semestral, anual)
        - Retorna nombres de meses en inglés para consistencia

        Args:
            dividends_history (pd.Series): Serie de pandas con historial de dividendos
                                          (index: fechas, values: montos)

        Returns:
            tuple: (meses_pago, frecuencia, total_ttm)
                - meses_pago (list): Lista de nombres de meses (ej: ["March", "June", "September", "December"])
                - frecuencia (int): Número de pagos por año detectados
                - total_ttm (float): Total pagado en últimos 12 meses (Trailing Twelve Months)
        """
        try:
            if len(dividends_history) == 0:
                return [], 0, 0.0

            # Calcular fecha de corte (últimos 12 meses)
            cutoff_date = pd.Timestamp.now() - pd.DateOffset(months=12)
            cutoff_date = cutoff_date.tz_localize(None)

            # Normalizar índice de dividendos (quitar zona horaria si existe)
            dividends_index = dividends_history.index
            if dividends_index.tz is not None:
                dividends_index = dividends_index.tz_localize(None)

            # Filtrar dividendos de los últimos 12 meses
            recent_dividends = [
                (date, dividends_history.loc[dividends_history.index == date].iloc[0])
                for date in dividends_history.index
                if date.tz_localize(None) > cutoff_date
            ]

            if not recent_dividends:
                return [], 0, 0.0

            # Calcular total TTM
            total_ttm = sum(amount for _, amount in recent_dividends)

            # Detectar frecuencia (número de pagos/año)
            frecuencia = len(recent_dividends)

            # Extraer meses únicos de pago
            months_paid = [date.month for date, _ in recent_dividends]
            unique_months = sorted(set(months_paid))

            # Convertir números de mes a nombres en inglés
            month_names = [datetime(2000, m, 1).strftime("%B") for m in unique_months]

            return month_names, frecuencia, total_ttm

        except Exception as e:
            print(f"[_extract_dividend_payment_months()]: {e}")
            return [], 0, 0.0

    def dividends_en_market_stock(self, activos):
        def update_tabla_market(x_symbol, campo, value):
            try:
                found, iy = self.Market.select(account=self.account, symbol=x_symbol)
                if not found:
                    self.Market.insert(upd=campo, val=value, symbol=x_symbol)
                else:
                    self.Market.update(upd=campo, val=value, symbol=x_symbol)
            except Exception as error:
                self.logger.error("update_tabla_market({}): {}".format(x_symbol, error))

        def construct_info_dividends(x_symbol, activo, pdatos):
            try:
                campos = {}
                ddatos, x_categoria, x_meses = self.rendimiento_dividends(activo=activo, datos=pdatos, symbol=x_symbol)
                if not ddatos.empty:
                    campos.update({"categoriaActivo": x_categoria[0]})
                    campos.update({"trazaDividends": ddatos.to_json(orient="split")})
                else:
                    qt = (activo.get("quoteType") or "").upper()
                    campos.update({"categoriaActivo": "X" if qt in _ETF_TYPES else "N"})
                campos.update({"trailingAnnualDividendRate": activo.get("trailingAnnualDividendRate", 0)})
                campos.update({"dividendYield": activo.get("dividendYield", 0)})
                timestamp = activo.get("exDividendDate")
                exdivi = "9999-12-31"
                if timestamp is not None:
                    exdivi = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                campos.update({"exDividendDate": exdivi})
                campos.update({"previousClose": activo.get("previousClose", 0)})
                return campos, x_categoria[0], x_meses
            except Exception as error:
                self.logger.error("construct_info_dividends({}): {}".format(x_symbol, error), exc_info=True)

        _ETF_TYPES = {"ETF", "MUTUALFUND", "TRUST", "INDEX", "MONEYMARKET"}

        try:
            if self.vehiculo != "Stock":
                return
            for symbol in activos:
                ticket = convierte_ticket_crypto(symbol)
                yf_activo, datos, ind_update = self.ts_yfinance_symbol(symbol=ticket, vehiculo=self.vehiculo)
                qt = (yf_activo.get("quoteType") or "").upper()
                if qt in _ETF_TYPES:
                    continue  # ETF/fondo — no insertar en market
                if not ind_update and ("dividendYield" in yf_activo) and ("Dividends" in datos):
                    self._validate_dividend_data_freshness(symbol, yf_activo, datos["Dividends"])
                    fields, categoria, meses = construct_info_dividends(ticket, yf_activo, datos)
                    columnas, values = [], []
                    for keys, info in fields.items():
                        info = info if not isinstance(info, str) or info not in ("Infinity", "nan", "NaN") else 0
                        columnas.append(keys)
                        values.append(info)
                    columnas.append("monthDividendsPay")
                    values.append(", ".join(meses))
                    columnas.append("lastPrice")
                    values.append(yf_activo.get("currentPrice", 0))
                    columnas.append("encartera")
                    values.append("Y")
                    update_tabla_market(symbol, columnas, values)
                    if symbol in self.info.keys():
                        self.info[symbol]["update"] = True
                elif not ind_update:
                    # Sin datos de dividendo — garantizar registro en market con encartera='Y'
                    cat = "X" if qt in _ETF_TYPES else "N"
                    update_tabla_market(symbol, ["encartera", "categoriaActivo", "account"], ["Y", cat, self.account])
        except Exception as e:
            self.logger.error("dividends_en_market_stock(): {}".format(e))

    def run(self):
        def run_cryptos():
            # planifica y ejecuta una vez actualización de precios Cryptos
            def websocket_stream(limit, task):
                nonlocal iteraStream
                while True:
                    try:
                        DataHub.update_self_procesos(proces="thread", tarea=task, itera=iteraStream)
                        self.schedule_WebsocketBinanceStream(limit=limit)
                        iteraStream += 1
                    except Exception as e:
                        self.logger.error(f"websocket_stream(): {e}")
                        time.sleep(30)

            def websocket_client(limit, task):
                nonlocal iteraClient
                while True:
                    try:
                        DataHub.update_self_procesos(proces="thread", tarea=task, itera=iteraClient)
                        self.schedule_WebsocketBinanceApiClient(limit=limit)
                        iteraClient += 1
                    except Exception as e:
                        self.logger.error(f"websocket_client(): {e}")
                        time.sleep(30)

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
            except Exception as e:
                print(f"run_cryptos(): {e}")

        def run_stock():
            # invoca websocket y suscribe symbols
            def websocket_stream(limit, task):
                nonlocal iteraStream
                _log = logging.getLogger("IBroks_Client")

                def _watchdog():
                    # Cierra el WS si el counter no avanzó en 5 minutos — fuerza re-suscripción
                    TIMEOUT = 300
                    while True:
                        time.sleep(60)
                        if self.WsStock is None:
                            continue
                        prev = self.WsStock.counter
                        time.sleep(TIMEOUT - 60)
                        if self.WsStock is not None and self.WsStock.counter == prev:
                            _log.warning("websocket_stream(Stock): watchdog — sin datos 5 min, reconectando")
                            try:
                                self.WsStock.ws.close()
                            except Exception:
                                pass

                threading.Thread(target=_watchdog, name="WsStock_Watchdog", daemon=True).start()

                try:
                    url = f"wss://localhost:{DataHub.ib_gateway_port}/v1/api/ws"
                    while True:

                        if iteraStream > 1:
                            _log.error(f"websocket_stream(Stock): reconectando (iter={iteraStream})")

                        if not self.activos:
                            _log.warning("websocket_stream(Stock): self.activos vacío al reconectar")

                        self.WsStock = MyWebsocket(
                            url=url,
                            logger=False,
                            vehiculo=self.vehiculo,
                            assets=self.assets,
                            idsymbol=self.activos,
                        )

                        iteraStream += 1
                        self.WsStock.my_message = self.on_message_IBrks_websocket
                        DataHub.update_self_procesos(proces="thread", tarea=task, itera=iteraStream)
                        self.WsStock.websocket_loop(limit=limit)
                        _log.error(
                            f"websocket_stream(Stock): websocket_loop() terminó, esperando 30s antes de reconectar"
                        )
                        time.sleep(30)

                except Exception as e:
                    _log.error(f"websocket_stream(Stock): excepción fatal — {e}")

            try:
                self.ib_connection = self.IClient.create_session()

                if self.IClient.ib_is_connet():
                    # invoca API y actualiza inversiones
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

                    socket = f"WebsocketStream_OnMessage({self.vehiculo})"
                    self.procesos.append({"widget": {socket: 0}})

                else:
                    logging.getLogger("IBroks_Client").warning("run_stock(): No hay conexión con IBKR")
            except Exception as error:
                logging.getLogger("IBroks_Client").error(f"run_stock(): {error}")

        try:
            # instancia para vehiculo Crypto
            if self.vehiculo == "Crypto":
                run_cryptos()

            # instancia para vehiculo Stock
            if self.vehiculo == "Stock":
                run_stock()
        except Exception as e:
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

        # Control de instancia única para ventana de configuración
        self.setup_window = None

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

        self.nb = ttk.Notebook(self.root_note, style="C.TNotebook", width=self.dw, height=self.dh)
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
        self.win9 = ttk.Frame(self.nb, style="C.TFrame", width=self.dw, height=self.dh)

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
        self.win9.pack(fill=tk.BOTH, expand=True)

        self.nb.add(self.win1, text="Crypto         ")
        self.nb.add(self.win0, text="Stock          ")
        self.nb.add(self.win4, text="Ars            ")
        self.nb.add(self.win6, text="BotCrypto      ")
        self.nb.add(self.win7, text="Ves            ", state="disabled")
        self.nb.add(self.win8, text="Crowfonding    ", state="disabled")
        self.nb.add(self.win2, text="Screener       ")
        self.nb.add(self.win3, text="Gestión        ")
        self.nb.add(self.win9, text="Finance        ")
        self.nb.add(self.win5, text="System         ")

        # frames de Gráficos y figuras principales
        pn0 = ttk.Frame(self.root, padding=(1, 1, 1, 1), style="C.TFrame")
        pn1 = tk.Frame(self.root, bg="white", border=2)  # frame desemenño ultimos 6 meses
        pn2 = tk.Frame(self.root, bg="white", border=2)  # frame Fear and Greed
        pn3 = tk.Frame(self.root, bg="white", border=2)  # frame Diversificacion por dividendos
        pn4 = tk.Frame(self.root, bg="white", border=2)  # frame Diversificacion por sector
        pn5 = tk.Frame(self.root, bg="white", border=2)  # frame Diversificacion por tipo de activo
        pn6 = tk.Frame(self.root, bg="white", border=2)  # frame Diversificacion por region

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
        leftBotPn0 = ttk.Frame(botPn0, style="C.TFrame")
        rightBotPn0 = ttk.Frame(botPn0, style="C.TFrame")
        gypBottom = ttk.Frame(leftBotPn0, style="C.TFrame")
        InvBottom = ttk.Frame(leftBotPn0, style="C.TFrame")
        DebtBottom = ttk.Frame(rightBotPn0, style="C.TFrame")

        topPn0.pack(side=tk.TOP)
        botPn0.pack(side=tk.BOTTOM)
        lineLeft.pack(side=tk.LEFT, fill=tk.X)
        lineRight.pack(side=tk.RIGHT, fill=tk.X)
        leftBotPn0.pack(side=tk.LEFT)
        rightBotPn0.pack(side=tk.LEFT)
        gypBottom.pack(side=tk.TOP)
        InvBottom.pack(side=tk.BOTTOM)
        DebtBottom.pack(side=tk.TOP)

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
            command=lambda: self.setup_config(),
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
            label="Total dGyP (USD)",
            avance=0,
            proyeccion=1_000,
            width=130,
            height=10,
            bg_color=self.colors["bgcolor"],
        )
        self.InvProgress = ProgressBar(
            InvBottom,
            label="Total Inversión (USD)",
            avance=0,
            proyeccion=1_000_000,
            width=130,
            height=10,
            bg_color=self.colors["bgcolor"],
        )
        self.DebtProgress = ProgressBar(
            DebtBottom,
            label="Deuda Total (USD)",
            avance=0,
            proyeccion=1_000,
            width=130,
            height=10,
            bg_color=self.colors["bgcolor"],
        )
        self.GypProgress.pack(side=tk.LEFT, pady=5)
        self.InvProgress.pack(side=tk.LEFT, pady=5)
        self.DebtProgress.pack(side=tk.LEFT, pady=5)

        # áreas y figuras de gráficos principales --------------------------------------------------------------------
        self.rg0 = Figure(figsize=(2.77, 2.4), dpi=110, layout="tight")  # firgura de rendimiento ultimos 6 meses
        self.rg1 = Figure(figsize=(2.77, 2.4), dpi=110)  # figura de Fear and Greed
        self.rg2 = Figure(figsize=(5.55, 2.4), dpi=110, layout="tight")  # figura de Diversificación por dividendos
        self.rg3 = Figure(figsize=(5.75, 2.9), dpi=110, layout="tight")  # figura de Diversificación por sector
        self.rg4 = Figure(figsize=(5.75, 2.9), dpi=110, layout="tight")  # figura de Diversificación por tipo de activo
        self.rg5 = Figure(figsize=(5.75, 2.9), dpi=110, layout="tight")  # figura de Diversificación por region

        self.rv0 = FigureCanvasTkAgg(self.rg0, master=pn1)  # canvas de rendimiento ultimos 6 meses
        self.rv1 = FigureCanvasTkAgg(self.rg1, master=pn2)  # canvas de Fear and Greed
        self.rv2 = FigureCanvasTkAgg(self.rg2, master=pn3)  # canvas de Diversificación por dividendos
        self.rv3 = FigureCanvasTkAgg(self.rg3, master=pn4)  # canvas de Diversificación por sector
        self.rv4 = FigureCanvasTkAgg(self.rg4, master=pn5)  # canvas de Diversificación por tipo de activo
        self.rv5 = FigureCanvasTkAgg(self.rg5, master=pn6)  # canvas de Diversificación por region

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

        bt4 = tk.Button(
            pn1,
            text="3y",
            width=2,
            bg=self.bgcolor,
            fg=self.cgcolor,
            relief=tk.FLAT,
            command=lambda: self.setup_graph_income("36"),
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
        gt6 = tk.Button(
            pn6,
            image=imagen_tk,
            bg=self.colors["bgcolor"],
            relief=tk.FLAT,
            command=lambda: self.detalle_graph("Region"),
        )

        gt3.imagen = imagen_tk
        gt4.imagen = imagen_tk
        gt5.imagen = imagen_tk
        gt6.imagen = imagen_tk

        bt1.place(y=20, x=10)
        bt2.place(y=20, x=30)
        bt3.place(y=20, x=50)
        bt4.place(y=20, x=70)
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

    def on_tab_changed(self, event):
        """cambia estilo notebook ----------------------------------------------------------------------------------------"""

        selected = event.widget.index("current")
        for i in range(self.root_note.index("end")):
            if i == selected:
                self.root_note.tab(i, style="Custom.TNotebook.Tab")
            else:
                self.root_note.tab(i, style="TNotebook.Tab")  # estilo por defecto

    def start_crypto(self, account=None, vehiculo=None):
        """contendor para iniciar widget cryptos"""

        def update_pane_crypto():
            nav, unpyl, dgyp, unprofit, costo = 0.0, 0.0, 0.0, 0.0, 0.0
            for keys in self.crypto.positions:
                nav += keys["mktvalue"]
                unpyl += keys["unrealizedpnl"]
                costo += keys["costobase"]
                dgyp += keys["dgyp"]
                unprofit += keys["unrealizedpnl"] if keys["unrealizedpnl"] > 0 else 0

            per = costo / unprofit if unprofit > 0 else 0

            self.crypto.set_header_panel(Dgyp=dgyp, Nav=nav, Unpyl=unpyl, Unprofit=unprofit, Per=per)
            self.crypto.header_panel()

        try:
            cb = BinanceClient().spot
            self.crypto = WidgetVehiculo(master=self.win1, account=account, vehiculo=vehiculo)

            if cb.check_binance_connection():
                DataHub.manager_sesion.update({"Crypto": True})
                self.crypto_ts = DatosVehivulo(account=account, vehiculo=vehiculo)
                self.crypto_ts.run()

                self.procesos.append({"widget": {"update_widget(Crypto)": self.it_crypto}})

                # información para widgetCrypto
                self.crypto.positions = self.crypto_ts.positions
                self.crypto.resumen = self.crypto_ts.resumen

                self.crypto.inicio_widget_treeview(self.crypto.positions)
                self.crypto.run_graficos()
                self.update_widget(vehiculo=vehiculo)

            # para widget offline
            elif not cb.check_binance_connection():
                DataHub.manager_sesion.update({"Crypto": True})
                self.crypto.carga_inversion_en_positions()
                update_pane_crypto()

                self.crypto.inicio_widget_treeview(self.crypto.positions)
                self.crypto.run_graficos()
        except Exception as e:
            print(f"start_cryptos({e})")

    def start_stock(self, account=None, vehiculo=None):
        """contendor para iniciar widget de stock"""

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

        def _ib_on_reconnect():
            """Callback: IB Gateway reconectó tras pérdida de sesión."""
            _log = logging.getLogger("IBroks_Client")
            try:
                if hasattr(self, "stock_ts") and self.stock_ts:
                    # Ya existía conexión previa — refrescar datos
                    self.stock_ts.ib_connection = self.stock_ts.IClient.create_session()
                    self.stock_ts.carga_inversion_en_positions()
                    self.stock_ts.conector_api_vehiclo()
                    self.stock.positions = self.stock_ts.positions
                    self.stock.resumen = self.stock_ts.resumen
                    _log.warning("✅ IB reconnect: posiciones y datos actualizados")
                else:
                    # Arrancó Offline — crear DatosVehivulo y levantar todo
                    self.stock_ts = DatosVehivulo(account=account, vehiculo=vehiculo)
                    self.stock_ts.run()

                    self.procesos.append({"widget": {"update_widget(Stock)": self.it_stock}})
                    self.stock.positions = self.stock_ts.positions
                    self.stock.resumen = self.stock_ts.resumen

                    # UI updates deben correr en el hilo principal de Tkinter
                    def _refresh_treeview():
                        for tree in self.stock.m_heard + self.stock.m_tree:
                            tree.delete(*tree.get_children())
                        self.stock.inicio_widget_treeview(self.stock.positions)

                    self.root.after(0, _refresh_treeview)
                    self.root.after(100, lambda: self.stock.run_graficos())
                    self.root.after(200, lambda: self.update_widget(vehiculo=vehiculo))
                    _log.warning("✅ IB reconnect: DatosVehivulo creado + WebSocket + posiciones levantados")

                # en ambos casos (refresh o arranque diferido) la sesión ya está activa
                DataHub.manager_sesion.update({"Stock": True})
            except Exception as e:
                _log.error(f"_ib_on_reconnect error: {e}")

        try:
            ib = IB()
            self.stock = WidgetVehiculo(master=self.win0, account=account, vehiculo=vehiculo)

            connected = False
            try:
                connected = ib.is_localhost()
                DataHub.manager_sesion.update({"Stock": False})

            except Exception:
                logging.getLogger("IBroks_Client").warning("⚠️ IB Gateway no disponible — modo Offline")

            if connected:
                DataHub.manager_sesion.update({"Stock": True})
                self.stock_ts = DatosVehivulo(account=account, vehiculo=vehiculo)
                self.stock_ts.run()

                self.procesos.append({"widget": {"update_widget(Stock)": self.it_stock}})

                # información para widgetCrypto
                self.stock.positions = self.stock_ts.positions
                self.stock.resumen = self.stock_ts.resumen

                self.stock.inicio_widget_treeview(self.stock.positions)
                self.stock.run_graficos()
                self.update_widget(vehiculo=vehiculo)

            # para widget offline
            else:
                self.stock_ts = DatosVehivulo(account=account, vehiculo=vehiculo)
                self.stock_ts.carga_inversion_en_positions()
                self.stock.positions = self.stock_ts.positions
                self.stock.resumen = self.stock_ts.resumen
                update_pane_stock()

                self.procesos.append({"widget": {"update_widget(Stock)": self.it_stock}})
                self.stock.inicio_widget_treeview(self.stock.positions)
                self.stock.run_graficos()
                self.update_widget(vehiculo=vehiculo)

            # Tickle siempre corre — detecta reconexión aunque arranque offline
            ib.start_tickle(interval=30, datahub=DataHub, on_reconnect=_ib_on_reconnect)

        except Exception as e:
            logging.getLogger("IBroks_Client").error(f"start_stock(): {e}")

    def start_chatbot(self):
        """
        Inicializa el chatbot y su botón flotante.
        Luego inicializa el monitor de modelo IA.
        """
        self.chatbot = None  # Inicializar como None por defecto

        def mostrar_asistente():
            """Callback para mostrar el chatbot"""
            if hasattr(self, "chatbot") and self.chatbot:
                self.chatbot.deiconify()

        def mostrar_boton():
            """Callback para mostrar el botón flotante"""
            if hasattr(self, "boton_flotante") and self.boton_flotante:
                self.boton_flotante.deiconify()

        try:
            # Importar Chatbot y BotonFlotante
            from Class_DashBot import Chatbot, BotonFlotante

            # Crear instancias
            self.chatbot = Chatbot(master=self.root, on_minimizar=mostrar_boton)
            self.boton_flotante = BotonFlotante(self.root, on_click=mostrar_asistente)

            # Iniciar el chatbot
            self.chatbot.run()

            # Ocultar chat al inicio. Solo se activa desde el botón flotante
            self.chatbot._al_perder_foco()
        except Exception as e:
            self.chatbot = None

        # Inicializar monitores de modelos IA después de que chatbot esté disponible
        # Los monitores están en la clase system_status, pasamos el chatbot como parámetro
        try:
            if hasattr(self, "system") and self.chatbot is not None:
                self.system.sell_ia_monitor(chatbot=self.chatbot)
                self.system.buy_ia_monitor(chatbot=self.chatbot)
        except Exception:
            pass

    def update_widget(self, vehiculo=None):
        """update widget del crypto"""

        try:
            # Verificar si debemos continuar ejecutando
            if not self.is_running:
                return

            # información para widgetCrypto
            if vehiculo == "Crypto":
                self.it_crypto += 1
                self.crypto.header_panel()
                DataHub.update_self_procesos(proces="widget", tarea="update_widget(Crypto)", itera=self.it_crypto)

                self.crypto.update_panelVehiculo(orden=self.crypto.orden)

            # información para widgetStock
            if vehiculo == "Stock" and self.stock_ts is not None:

                self.it_stock += 1

                self.stock.summary = self.stock_ts.summary
                self.stock.positions = self.stock_ts.positions

                if not self.stock_ts.IClient.authenticated:
                    for position in self.stock.positions:
                        symbol = position.get("ticket")
                        ws = DataHub.info.get(symbol, {}).get("websocket", {})
                        last = ws.get("last")
                        if last:
                            qty = position.get("position", 0)
                            costo = position.get("costobase", 0)
                            xopen = position.get("open", 0)
                            position["mrkprice"] = last
                            position["mktvalue"] = last * qty
                            position["unrealizedpnl"] = last * qty - costo
                            position["retorno"] = (last * qty - costo) / costo if costo else 0
                            position["dgyp"] = (last - xopen) * qty if xopen > 0 else 0

                self.stock.header_panel()
                DataHub.update_self_procesos(proces="widget", tarea="update_widget(Stock)", itera=self.it_stock)

                self.stock.update_panelVehiculo(orden=self.stock.orden)
                # self.stock.schedule_order_remote()

        except Exception as e:
            print("update_widget({}}): {}".format(vehiculo, e))

        finally:
            # siempre reprogramar — nunca detener el loop por una excepción interna
            if self.is_running:
                after_id = self.root.after(500, lambda: self.update_widget(vehiculo=vehiculo))
                self.after_ids.append(after_id)

    def car_ordenes_activas(self):
        def eexit():
            rnb.destroy()

        # construye treeview con todas las orders
        def config_treeview_ordenes(tree, heard):
            def sort_children_by_col(col, reverse, btn):
                try:
                    for parent in tree.get_children(""):
                        children = tree.get_children(parent)
                        data = []
                        for k in children:
                            raw = tree.set(k, col)
                            try:
                                val = float(raw) if raw not in ("", None) else None
                            except (ValueError, TypeError):
                                val = raw or None
                            data.append((val, k))
                        data.sort(
                            key=lambda x: (x[0] is None, x[0] if isinstance(x[0], (int, float)) else str(x[0] or "")),
                            reverse=reverse,
                        )
                        for index, (_, k) in enumerate(data):
                            tree.move(k, parent, index)
                    arrow = " ▲" if not reverse else " ▼"
                    heard.heading(btn, text=btn + arrow, command=lambda: sort_children_by_col(col, not reverse, btn))
                except Exception as e:
                    print(f"sort_children_by_col({col}): {e}")

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
                    heard.heading(
                        key, text=cols[i], command=lambda _k=key, _i=i: sort_children_by_col(_k, False, cols[_i])
                    )

                tree.tag_configure("green", background="green", foreground="white")
                tree.tag_configure("red", background="red", foreground="white")
            except Exception as e:
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

            except Exception as e:
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
                    response = self.crypto_ts.BClient.get_cancel_order(symbol=symbol, orderId=orderId)
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

                    response = self.stock_ts.IClient.deleteorder(account_id=account, customer_order_id=orderId)

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

            except Exception as e:
                print("eliminar_orden(): {}".format(e))

        # refresca ordenes en treeview
        def update_treeview_ordenes():
            try:
                padres = tree.get_children()
                for padre in padres:
                    for hijo in tree.get_children(padre):
                        tree.delete(hijo)
                insert_ordenes_treeview(tree)
            except Exception as e:
                print("update_treeview_ordenes(): {}".format(e))

        # carga órdenes ejecutadas hoy en treeview
        # Stock: directo de IB API (frescos); Crypto: desde booktrading (bot escribe ahí al cerrar)
        def insert_ejecutadas_treeview():
            try:
                for padre in tree.get_children():
                    for hijo in tree.get_children(padre):
                        tree.delete(hijo)
                nro = 1
                today = datetime.now().date()

                # --- Stock: IB API ---
                trades_ib = self.stock_ts.IClient.trades(account_id=self.stock_ts.account, days=1) or []
                for t in trades_ib:
                    ts = int(t.get("trade_time_r", 0)) / 1000
                    fh = datetime.fromtimestamp(ts)
                    if fh.date() != today:
                        continue
                    simbolo = t.get("symbol", "")
                    side = "BUY" if t.get("side", "") == "B" else "SELL"
                    precio = t.get("price", "")
                    cant = t.get("size", "")
                    values = ["", "", simbolo, side, "", precio, cant, "", str(fh), "", "", "", ""]
                    tree.insert(Stock, "end", text="{:>3.0f}".format(nro), values=values)
                    nro += 1

                # --- Crypto: booktrading hoy ---
                rows, ix = self.RepositorioOportunidades.select_booktrading(accion="hoy")
                for row in rows:
                    cuenta = row[ix.index("cuenta")]
                    if cuenta == self.stock_ts.account:
                        continue
                    simbolo = row[ix.index("simbolo")]
                    raw_cod = row[ix.index("codigo")]
                    codigo = "BUY" if raw_cod == "O" else "SELL" if raw_cod == "C" else raw_cod
                    cant = row[ix.index("cantidad")]
                    basico = row[ix.index("basico")]
                    gp = row[ix.index("gprealizadas")]
                    fh = row[ix.index("fechahora")]
                    values = ["", "", simbolo, codigo, "", basico, cant, "", str(fh), "", "", gp, ""]
                    tree.insert(Crypto, "end", text="{:>3.0f}".format(nro), values=values)
                    nro += 1
            except Exception as e:
                print("insert_ejecutadas_treeview(): {}".format(e))

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
            except Exception as e:
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
            tree = ttk.Treeview(win2, columns=cols, height=18, style="TFrame", show="tree")

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
                text="Ejecutadas",
                width=10,
                bg="gray",
                fg="white",
                command=lambda: insert_ejecutadas_treeview(),
            )

            ct6 = tk.Button(
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
            ct5.pack(side=tk.LEFT, padx=5, pady=20)
            ct6.pack(side=tk.LEFT, padx=40, pady=20)

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
        except Exception as e:
            print("car_ordenes_activas(): {}".format(e))

    def detalle_graph(self, tipo=None):
        """despliega ventana con detalle para el gráfico"""

        # controla salida de window_estrategia()
        def eexit():
            rnb.destroy()

        # Ubica información de yfinance. Ticker, para mostrar gráfico de dividends
        def grafico_rendimiento_symbol(symbol=None, windows=None):
            try:

                # if symbol in self.stock_ts.info:
                activo, datos, update = self.crypto_ts.ts_yfinance_symbol(symbol=symbol, vehiculo="Stock")
                self.crypto_ts.rendimiento_dividends(fg=rg, activo=activo, datos=datos, symbol=symbol, plot="yes")
                rv.draw()

                # resultados del simbolo
                inicial = datos["Close"].iloc[0]
                final = datos["Close"].iloc[-1]
                growth = (final - inicial) / inicial
                analisis = {
                    "symbol": symbol,
                    "Precio": "{:>10.2f}".format(inicial) + " - " + "{:>10.2f}".format(final),
                    "Growth": "{:>10.2%}".format(growth),
                    "Dividend Yield": "{:>10.2%}".format(activo.get("dividendYield", 0)),
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
                    lbv = tk.Label(windows, text=str(value), bg=self.bgcolor, font=("Arial", 9))
                    lbv.grid(row=i + 1, column=1, padx=5, pady=1, sticky=W)
                    lbl.grid(row=i + 1, column=0, padx=5, pady=1, sticky=W)

            except Exception as e:
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

            elif tipo == "Activo":
                if str_float(values[4]) > 0.0:
                    symbol = values[1]
                    grafico_rendimiento_symbol(symbol=symbol, windows=windows)

                else:
                    symbol = values[1]
                    message = "symbol :" + symbol + " No informa pago de dividendos"
                    self.messagebox.showwarning("Advertencia", message)

            elif tipo == "Region":
                symbol = str(values[1]).strip()
                if symbol:
                    grafico_rendimiento_symbol(symbol=symbol, windows=windows)

        # selecciona y clasifica detalle por symbol y dividendos
        def detalle_dividendos(meses):
            book, date = {}, datetime.now().month
            positions = self.PlanInversion.select_inversion(tipoin="Stock", ticket="all")
            for position in positions:
                symbol = convierte_ticket_crypto(position["ticket"])
                market, ix = self.Market.select(account="U4214563", symbol=symbol)

                if market:
                    last = market[0][ix.index("lastDividendValue")] or 0
                    trallingAnual = market[0][ix.index("trailingAnnualDividendRate")] or 0

                    div = 0
                    if trallingAnual > 0:
                        div = market[0][ix.index("dividendRate")] or 0

                    string = market[0][ix.index("monthDividendsPay")]
                    fecha = market[0][ix.index("exDividendDate")]

                    exdiv = fecha.strftime("%d-%b") if fecha and fecha.month == date else " "
                    avgcost = position["costobase"] / position["position"]

                    dividends = [0] * 12
                    a_meses = meses if string is None or string == "" else string.split(",")

                    # calcula la cantidad de pagos - filtrar cadenas vacías
                    distribuir = [s.strip()[:3] for s in a_meses if s.strip()]
                    rata = (div / len(distribuir)) if (div and len(distribuir) > 0) else last

                    # asume pago de dividends son iguales
                    for i, mes in enumerate(distribuir):
                        if mes in meses:  # Validar que el mes existe en la lista
                            dividends[meses.index(mes)] = rata * position["position"]

                    # recalculo de rendimiento en función avgcost
                    rend = div / avgcost if avgcost > 0 else 0

                    # Agrega si ha pagado dividendno en año
                    if trallingAnual > 0:
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
            positions = self.PlanInversion.select_inversion(tipoin="Stock", ticket="all")
            orden = [{"Sector": "sector"}, "DES"]
            cartera = sort_positions(positions, orden)

            for position in cartera:
                symbol = convierte_ticket_crypto(position["ticket"])
                market, ix = self.Market.select(account="U4214563", symbol=symbol)

                exdiv, rend, dividends = "", 0.0, [0] * 12
                if market:
                    last = market[0][ix.index("lastDividendValue")] or 0
                    trallingAnual = market[0][ix.index("trailingAnnualDividendRate")] or 0

                    div = 0
                    if trallingAnual > 0:
                        div = market[0][ix.index("dividendRate")] or 0

                    string = market[0][ix.index("monthDividendsPay")]
                    fecha = market[0][ix.index("exDividendDate")]

                    exdiv = fecha.strftime("%d-%b") if fecha and fecha.month == date else " "
                    avgcost = position["costobase"] / position["position"]

                    # Solo calcular dividendos si ha pagado en el último año
                    if trallingAnual > 0:
                        a_meses = meses if string is None or string == "" else string.split(",")

                        # calcula la cantidad de pagos - filtrar cadenas vacías
                        distribuir = [s.strip()[:3] for s in a_meses if s.strip()]
                        rata = (div / len(distribuir)) if (div and len(distribuir) > 0) else last

                        # asume pago de dividends son iguales
                        for i, mes in enumerate(distribuir):
                            if mes in meses:  # Validar que el mes existe en la lista
                                dividends[meses.index(mes)] = rata * position["position"]

                        # recalculo de rendimiento en función avgcost
                        rend = div / avgcost if avgcost > 0 else 0
                    else:
                        # Activo no paga dividendos - valores en 0
                        dividends = [0] * 12
                        rend = 0.0
                        exdiv = ""

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
            positions = self.PlanInversion.select_inversion(tipoin="activo", ticket="all")

            orden = [{"Activo": "tipoActivo"}, "DES"]
            cartera = sort_positions(positions, orden)

            for position in cartera:
                symbol = convierte_ticket_crypto(position["ticket"])
                market, ix = self.Market.select(account="U4214563", symbol=symbol)

                exdiv, rend, dividends = "", 0.0, [0] * 12
                if market:
                    last = market[0][ix.index("lastDividendValue")]

                    div = 0
                    if (market[0][ix.index("trailingAnnualDividendRate")] or 0) > 0:
                        div = market[0][ix.index("dividendRate")] or 0

                    string = market[0][ix.index("monthDividendsPay")]
                    fecha = market[0][ix.index("exDividendDate")]
                    exdiv = fecha.strftime("%d-%b") if fecha and fecha.month == date else " "
                    avgcost = position["costobase"] / position["position"]

                    a_meses = meses if string is None or string == "" else string.split(",")

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
                        t_symbol[i] = "{:4.1f}".format(activo["dividends"][i]) if activo["dividends"][i] > 0 else ""
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
            except Exception as e:
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
                        t_symbol[i] = "{:4.1f}".format(activo["dividends"][i]) if activo["dividends"][i] > 0 else ""
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
            except Exception as e:
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
                        t_symbol[i] = "{:4.1f}".format(activo["dividends"][i]) if activo["dividends"][i] > 0 else ""
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
            except Exception as e:
                print("treeview_TipoActivo(): {}".format(e))

        def treeview_Region(option=None, windows=None):
            try:
                fixed_columns = [
                    "País",
                    "Symbol",
                    "Capital",
                    "Mkt Value",
                    "PnL",
                    "Retorno%",
                    "Peso%",
                    "Year $",
                    "%Yield",
                ]
                alignments = {
                    "País": {"width": 148, "anchor": "w"},
                    "Symbol": {"width": 100, "anchor": "w"},
                    "Capital": {"width": 90, "anchor": "e"},
                    "Mkt Value": {"width": 95, "anchor": "e"},
                    "PnL": {"width": 88, "anchor": "e"},
                    "Retorno%": {"width": 78, "anchor": "e"},
                    "Peso%": {"width": 68, "anchor": "e"},
                    "Year $": {"width": 80, "anchor": "e"},
                    "%Yield": {"width": 74, "anchor": "e"},
                }
                columns = list(alignments.keys())

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

                # Agrupar posiciones por país
                strategy = self.Estrategia.read()
                d_country = {}
                for activos in strategy.values():
                    for activo in activos:
                        country = activo.get("country") or "NotCountry"
                        if country == "US":
                            country = "United States"
                        elif country == "Digital":
                            country = "Crypto"
                        d_country.setdefault(country, []).append(activo)

                total_capital_global = sum(a["costobase"] for activos in d_country.values() for a in activos) or 1

                min_base, ticket = pow(10, 9), ""
                total_cap_sum, total_mkt_sum, total_pnl_sum, total_div_sum = 0.0, 0.0, 0.0, 0.0

                for country, activos in sorted(d_country.items()):
                    cap_pais = sum(a["costobase"] for a in activos)
                    mkt_pais = sum(a["costobase"] + a["unrealizedpnl"] for a in activos)
                    pnl_pais = mkt_pais - cap_pais
                    div_pais = sum(a.get("dividendo", 0) or 0 for a in activos)
                    retorno_pais = pnl_pais / cap_pais if cap_pais > 0 else 0
                    peso_pais = cap_pais / total_capital_global
                    yield_pais = div_pais / cap_pais if cap_pais > 0 else 0

                    tree.insert_row(
                        texto=country,
                        padre=None,
                        values=[
                            country,
                            "",
                            "{:,.0f}".format(cap_pais),
                            "{:,.0f}".format(mkt_pais),
                            "{:+,.0f}".format(pnl_pais),
                            "{:.2%}".format(retorno_pais),
                            "{:.1%}".format(peso_pais),
                            "{:,.1f}".format(div_pais),
                            "{:.2%}".format(yield_pais),
                        ],
                    )

                    for activo in sorted(activos, key=lambda a: a["symbol"]):
                        symbol = activo["symbol"]
                        cap = activo["costobase"]
                        mkt = activo["costobase"] + activo["unrealizedpnl"]
                        pnl = activo["unrealizedpnl"]
                        div = activo.get("dividendo", 0) or 0
                        retorno = pnl / cap if cap > 0 else 0
                        peso = cap / total_capital_global
                        yield_pct = div / cap if cap > 0 else 0

                        if cap < min_base:
                            min_base, ticket = cap, symbol

                        tree.insert_row(
                            texto=None,
                            padre=country,
                            values=[
                                "",
                                symbol,
                                "{:,.0f}".format(cap),
                                "{:,.0f}".format(mkt),
                                "{:+,.0f}".format(pnl),
                                "{:.2%}".format(retorno),
                                "{:.1%}".format(peso),
                                "{:,.1f}".format(div),
                                "{:.2%}".format(yield_pct),
                            ],
                        )
                        total_cap_sum += cap
                        total_mkt_sum += mkt
                        total_pnl_sum += pnl
                        total_div_sum += div

                retorno_total = total_pnl_sum / total_cap_sum if total_cap_sum > 0 else 0
                yield_total = total_div_sum / total_cap_sum if total_cap_sum > 0 else 0
                tree.insert_row(
                    summary=[
                        "",  # País  (vacío)
                        "",  # Symbol (vacío)
                        "{:,.0f}".format(total_cap_sum),  # Capital
                        "{:,.0f}".format(total_mkt_sum),  # Mkt Value
                        "{:+,.0f}".format(total_pnl_sum),  # PnL
                        "{:.2%}".format(retorno_total),  # Retorno%
                        "100%",  # Peso%
                        "{:,.1f}".format(total_div_sum),  # Year $
                        "{:.2%}".format(yield_total),  # %Yield
                    ]
                )

                grafico_rendimiento_symbol(symbol=ticket, windows=windows)
            except Exception as e:
                print("treeview_Region(): {}".format(e))

        try:
            # define titulo de la pantalla
            title = "Diversificación vs pago Dividendos"
            if tipo == "Sector":
                title = "Diversificación vs Performance Sector"
            elif tipo == "Activo":
                title = "Diversificación vs Tipo Activo"
            elif tipo == "Region":
                title = "Diversificación vs Región"

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

            frm1 = ttk.Frame(rnb, padding=(2, 10, 2, 2), style="C.TFrame", width=600, height=300)
            frm2 = ttk.Frame(rnb, padding=(2, 10, 2, 2), style="C.TFrame", width=600, height=200)

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

            # detalle para el tipo de graph region
            elif tipo == "Region":
                treeview_Region(option=tipo, windows=fr20)

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
        except Exception as e:
            print("detalle_graph(): {}".format(e))

    def setup_graph_income(self, tipo=None):
        """performace de  ultimos n meses"""

        parm = {
            "titulo": "Ingresos",
            "periodo": tipo,
            "cchart": self.cchart,
            "legend": "upper right",
            "aspect": 0.60,
        }
        Agente_income_Manager(fg=self.rg0, parm=parm)
        self.rv0.draw()

    def graficos_main(self):
        """graficos windows main"""

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
        DataHub.manager_buysell["activos"] = grupo_activos(fg=self.rg4, parm=parm, strategy=xestrategia)
        self.rv4.draw()

        # Diversificación vs. región
        parm = {
            "titulo": "Diversificación vs Región",
            "cchart": self.cchart,
            "legend": "outside upper right",
            "aspect": 0.30,
        }
        DataHub.manager_buysell["region"] = grupo_region(fg=self.rg5, strategy=xestrategia, parm=parm)
        self.rv5.draw()

        # mantiene actualizado los graficos cada 20m o 1200.000ms
        # Verificar si debemos continuar ejecutando
        if self.is_running:
            after_id = self.root.after(1200000, lambda: self.graficos_main())
            self.after_ids.append(after_id)
        # DataHub.manager_after._safe(1200000, self.graficos_main(), name="graficos_main")

    def setup_config(self):
        """
        Abre ventana de gestión de sesiones con operaciones CRUD.
        Crea ventana Toplevel posicionada para no solapar el notebook principal.
        Implementa patrón Singleton: solo permite una instancia de la ventana.
        """
        # Verificar si ya existe una ventana abierta
        if self.setup_window is not None and self.setup_window.winfo_exists():
            # Traer ventana existente al frente
            self.setup_window.lift()
            self.setup_window.focus_force()
            return

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
                    fesesion_str = session["fesesion"].strftime("%Y-%m-%d %H:%M") if session.get("fesesion") else ""
                    fiscalYear_str = session["fiscalYear"].strftime("%Y-%m-%d") if session.get("fiscalYear") else ""
                    fefund_str = session["fefund"].strftime("%Y-%m-%d") if session.get("fefund") else ""

                    # Mostrar estrella si es cuenta principal
                    idcuenta_principal_str = "⭐" if session.get("Idcuenta_principal", False) else ""

                    # Solo incluir campos visibles (sin id, orcartera, xstrategy, userapi, userpass, private_key, public_key)
                    row_values = [
                        session.get("vehiculo", ""),
                        fiscalYear_str,
                        idcuenta_principal_str,
                        session.get("iduser", ""),
                        session.get("idcuenta", ""),
                        fesesion_str,
                        session.get("Pinvertir", 0),
                        session.get("gypPrecio", 0.0),
                        session.get("gainInversion", 0.0),
                    ]

                    tree.insert_row(values=row_values)

            except Exception as e:
                print(f"[refresh_sessions()]: {e}")
                MyMessageBox(session_window).showerror("Error", f"Error al cargar sesiones: {str(e)}")

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
                        success = BDsystem.delete_sesion(session["id"], session["vehiculo"])

                        if success:
                            MyMessageBox(session_window).showinfo("Éxito", "Sesión eliminada correctamente")
                            refresh_sessions()
                        else:
                            MyMessageBox(session_window).showerror("Error", "No se pudo eliminar la sesión")
            except Exception as e:
                print(f"[on_delete_click()]: {e}")
                MyMessageBox(session_window).showerror("Error", f"Error al eliminar sesión: {str(e)}")

        def on_envs_click():
            """
            Maneja botón Envs para editar variables de entorno de la sesión DataHub.

            IMPORTANTE: Este botón NO depende de selección en el tree.
            Siempre edita la sesión con vehiculo='DataHub'.
            """
            nonlocal session_window
            try:
                # Obtener sesión DataHub directamente (sin depender de selección en tree)
                datahub_session = BDsystem.get_sesion_by_vehiculo(vehiculo="DataHub")

                if datahub_session:
                    # Abrir editor con la sesión DataHub
                    open_envs_editor(datahub_session)
                else:
                    # Si no existe sesión DataHub, mostrar error
                    MyMessageBox(session_window).showerror(
                        "Error",
                        "No se encontró la sesión 'DataHub' en la base de datos.\n"
                        "Por favor, cree una sesión con vehículo='DataHub' primero.",
                    )
            except Exception as e:
                print(f"[on_envs_click()]: {e}")
                traceback.print_exc()
                MyMessageBox(session_window).showerror(
                    "Error", f"Error al abrir editor de variables de entorno: {str(e)}"
                )

        def open_envs_editor(session_data):
            """
            Abre ventana para editar variables de entorno de la sesión DataHub.
            Carga configuración desde session.userapi (JSON) y la guarda actualizada.

            Args:
                session_data: dict con datos de la sesión
            """

            def save_envs():
                """Guarda variables de entorno en userapi y actualiza DataHub"""
                try:
                    # Construir estructura cchart desde el diccionario de entradas
                    cchart_data = {
                        "texto": cchart_entries["texto"].get().strip(),
                        "titulo": cchart_entries["titulo"].get().strip(),
                        "fondo": entry_bgcolor.get().strip(),
                        "fondo_fig": entry_cgcolor.get().strip(),
                        "asx": cchart_entries["asx"].get().strip(),
                        "asy": cchart_entries["asy"].get().strip(),
                        "axsy": cchart_entries["axsy"].get().strip(),
                        "axsx": cchart_entries["axsx"].get().strip(),
                        "2eje": cchart_entries["2eje"].get().strip(),
                        "plot0": cchart_entries["plot0"].get().strip(),
                        "plot1": cchart_entries["plot1"].get().strip(),
                        "plot11": cchart_entries["plot11"].get().strip(),
                        "plot2": cchart_entries["plot2"].get().strip(),
                        "plot21": cchart_entries["plot21"].get().strip(),
                        "plot3": cchart_entries["plot3"].get().strip(),
                        "plot31": cchart_entries["plot31"].get().strip(),
                        "plot4": cchart_entries["plot4"].get().strip(),
                        "plot41": cchart_entries["plot41"].get().strip(),
                        "plot5": cchart_entries["plot5"].get().strip(),
                        "plot6": cchart_entries["plot6"].get().strip(),
                        "plot7": cchart_entries["plot7"].get().strip(),
                        "plot8": cchart_entries["plot8"].get().strip(),
                        "plot9": cchart_entries["plot9"].get().strip(),
                    }

                    # Construir estructura completa de configuración
                    envs_config = {
                        "bgcolor": entry_bgcolor.get().strip(),
                        "cgcolor": entry_cgcolor.get().strip(),
                        "cchart": cchart_data,
                        "display": (entry_display.get().strip() if entry_display.get().strip() else None),
                        "max_points": (int(entry_max_points.get().strip()) if entry_max_points.get().strip() else 40),
                        "interval": (int(entry_interval.get().strip()) if entry_interval.get().strip() else 1),
                        "CpuLock": (entry_cpulock.get().strip() if entry_cpulock.get().strip() else None),
                        "MinProfit": (float(entry_minprofit.get().strip()) if entry_minprofit.get().strip() else 80.0),
                        "Toleranciasell": (
                            float(entry_toleranciasell.get().strip()) if entry_toleranciasell.get().strip() else 0.10
                        ),
                        "MaxRoi": (float(entry_maxroi.get().strip()) if entry_maxroi.get().strip() else 0.09),
                        "InicioInversior": entry_inicioinversior.get().strip(),
                        "ib_gateway_host": entry_ib_gateway_host.get().strip(),
                        "ib_gateway_port": entry_ib_gateway_port.get().strip(),
                        # Parámetros Modelo IA Sell
                        "ia_umbral_venta": (
                            float(entry_umbral_venta.get().strip()) if entry_umbral_venta.get().strip() else 0.65
                        ),
                        "ia_umbral_observacion": (
                            float(entry_umbral_observacion.get().strip())
                            if entry_umbral_observacion.get().strip()
                            else 0.35
                        ),
                        "ia_modelo_name": (
                            entry_modelo_name.get().strip() if entry_modelo_name.get().strip() else "modelo_sellv01"
                        ),
                    }

                    # Convertir a JSON
                    userapi_json = json.dumps(envs_config, indent=2).encode("utf-8")

                    # Preparar valores para actualización (solo userapi cambia)
                    update_values = {
                        "fesesion": session_data.get("fesesion"),
                        "iduser": session_data.get("iduser"),
                        "idcuenta": session_data.get("idcuenta"),
                        "orcartera": session_data.get("orcartera"),
                        "fiscalYear": session_data.get("fiscalYear"),
                        "fefund": session_data.get("fefund"),
                        "Pinvertir": session_data.get("Pinvertir"),
                        "xstrategy": session_data.get("xstrategy"),
                        "userapi": userapi_json,  # Actualizar solo userapi
                        "userpass": session_data.get("userpass"),
                        "private_key": session_data.get("private_key"),
                        "public_key": session_data.get("public_key"),
                        "port": session_data.get("port"),
                        "environment": session_data.get("environment"),
                    }

                    # Actualizar registro en BD
                    success = BDsystem.update_sesion(session_data["id"], session_data["vehiculo"], update_values)

                    if success:
                        # Actualizar DataHub si se editó la sesión "DataHub"
                        vehiculo_editado = session_data.get("vehiculo", "")

                        # Obtener sesión DataHub para actualizar variables globales
                        try:
                            datahub_session = BDsystem.get_sesion_by_vehiculo(vehiculo="DataHub")

                            # Si se editó la sesión DataHub o existe una sesión DataHub, actualizar
                            if datahub_session and (
                                vehiculo_editado == "DataHub" or datahub_session["id"] == session_data["id"]
                            ):
                                # Actualizar variables de DataHub en memoria
                                DataHub.bgcolor = envs_config["bgcolor"]
                                DataHub.cgcolor = envs_config["cgcolor"]
                                DataHub.cchart = envs_config["cchart"]
                                DataHub.display = envs_config["display"]
                                DataHub.max_points = envs_config["max_points"]
                                DataHub.interval = envs_config["interval"]
                                DataHub.CpuLock = envs_config["CpuLock"]
                                DataHub.MinProfit = envs_config["MinProfit"]
                                DataHub.Toleranciasell = envs_config["Toleranciasell"]
                                DataHub.MaxRoi = envs_config["MaxRoi"]

                                # InicioInversior requiere conversión a date
                                DataHub.InicioInversior = datetime.strptime(
                                    envs_config["InicioInversior"], "%Y-%m-%d"
                                ).date()
                                DataHub.ib_gateway_host = envs_config["ib_gateway_host"]
                                DataHub.ib_gateway_port = envs_config["ib_gateway_port"]

                                # Actualizar colors dict
                                DataHub.colors["bgcolor"] = envs_config["bgcolor"]
                                DataHub.colors["cgcolor"] = envs_config["cgcolor"]
                                DataHub.colors["cchart"] = envs_config["cchart"]
                        except Exception as e:
                            print(f"[save_envs - actualizar DataHub]: {e}")
                            # Continuar aunque falle la actualización de DataHub

                        MyMessageBox(envs_window).showinfo(
                            "Éxito",
                            "Variables de entorno actualizadas correctamente.\n"
                            "Algunos cambios pueden requerir reiniciar la aplicación.",
                        )
                        envs_window.destroy()
                    else:
                        MyMessageBox(envs_window).showerror("Error", "No se pudo actualizar la configuración")

                except ValueError as ve:
                    MyMessageBox(envs_window).showerror(
                        "Error de Validación",
                        f"Por favor verifique que los valores numéricos sean correctos:\n{str(ve)}",
                    )
                except Exception as e:
                    print(f"[save_envs()]: {e}")

                    traceback.print_exc()
                    MyMessageBox(envs_window).showerror("Error", f"Error al guardar configuración: {str(e)}")

            def eexit():
                """Cierra ventana de edición"""
                envs_window.destroy()

            # Crear ventana modal
            envs_window = tk.Toplevel(session_window)
            envs_window.title(f"Variables de Entorno - {session_data.get('vehiculo', 'N/A')}")

            # Posicionar a la derecha de la ventana de sesiones (igual que editor)
            session_x = session_window.winfo_x()
            session_y = session_window.winfo_y()
            session_width = session_window.winfo_width()
            envs_window.geometry(f"700x700+{session_x + session_width + 10}+{session_y}")

            envs_window.resizable(False, False)
            envs_window.config(bg=self.colors["bgcolor"])
            envs_window.transient(session_window)
            envs_window.grab_set()
            envs_window.focus()
            envs_window.protocol("WM_DELETE_WINDOW", eexit)

            # Cargar configuración desde userapi (de la sesión actual o DataHub)
            try:
                userapi_bytes = session_data.get("userapi")
                if userapi_bytes:
                    # La sesión actual tiene configuración
                    envs_config = json.loads(userapi_bytes.decode("utf-8"))
                else:
                    # Si no hay configuración, cargar desde sesión DataHub
                    datahub_session = BDsystem.get_sesion_by_vehiculo(vehiculo="DataHub")
                    if datahub_session and datahub_session.get("userapi"):
                        envs_config = json.loads(datahub_session["userapi"].decode("utf-8"))
                    else:
                        # Error: DataHub debe existir y tener configuración
                        MyMessageBox(session_window).showerror(
                            "Error de Configuración",
                            "No se encontró configuración de variables de entorno.\n\n"
                            "La sesión 'DataHub' debe existir en la base de datos\n"
                            "con el campo 'userapi' correctamente configurado.",
                        )
                        return
            except Exception as e:
                print(f"[open_envs_editor - carga config]: {e}")

                traceback.print_exc()
                envs_config = {}

            # Crear canvas scrollable (igual que editor de sesiones)
            canvas = tk.Canvas(envs_window, bg=self.colors["bgcolor"])
            scrollbar = ttk.Scrollbar(envs_window, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg=self.colors["bgcolor"])

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # Campos del formulario - REORGANIZADO: 1) Trading, 2) Monitor, 3) Colores
            row = 0

            # ========== GRUPO 1: PARÁMETROS DE TRADING ==========
            tk.Label(
                scrollable_frame,
                text="💰 Parámetros de Trading",
                bg=self.colors["bgcolor"],
                fg="yellow",
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
            row += 1

            # MinProfit
            tk.Label(
                scrollable_frame,
                text="Min Profit:",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_minprofit = tk.Entry(scrollable_frame, width=50)
            entry_minprofit.insert(0, str(envs_config.get("MinProfit", 80.0)))
            entry_minprofit.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # Toleranciasell
            tk.Label(
                scrollable_frame,
                text="Tolerancia Sell:",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_toleranciasell = tk.Entry(scrollable_frame, width=50)
            entry_toleranciasell.insert(0, str(envs_config.get("Toleranciasell", 0.10)))
            entry_toleranciasell.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # MaxRoi
            tk.Label(
                scrollable_frame,
                text="Max ROI:",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_maxroi = tk.Entry(scrollable_frame, width=50)
            entry_maxroi.insert(0, str(envs_config.get("MaxRoi", 0.09)))
            entry_maxroi.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # InicioInversior
            tk.Label(
                scrollable_frame,
                text="Inicio Inversión (YYYY-MM-DD):",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_inicioinversior = tk.Entry(scrollable_frame, width=50)
            entry_inicioinversior.insert(0, envs_config.get("InicioInversior", "2020-07-31"))
            entry_inicioinversior.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # ib_gateway_host
            tk.Label(
                scrollable_frame,
                text="IB Gateway Host:",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_ib_gateway_host = tk.Entry(scrollable_frame, width=50)
            entry_ib_gateway_host.insert(0, envs_config.get("ib_gateway_host", "https://localhost"))
            entry_ib_gateway_host.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # ib_gateway_port
            tk.Label(
                scrollable_frame,
                text="IB Gateway Port:",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_ib_gateway_port = tk.Entry(scrollable_frame, width=50)
            entry_ib_gateway_port.insert(0, envs_config.get("ib_gateway_port", "5501"))
            entry_ib_gateway_port.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # ========== GRUPO 1.5: MODELO IA SELL ==========
            tk.Label(
                scrollable_frame,
                text="🤖 Modelo IA Sell",
                bg=self.colors["bgcolor"],
                fg="yellow",
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))
            row += 1

            # umbral_venta (confianza >= 0.65 = enviar a telegram)
            tk.Label(
                scrollable_frame,
                text="Umbral Venta (conf >=):",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_umbral_venta = tk.Entry(scrollable_frame, width=50)
            entry_umbral_venta.insert(0, str(envs_config.get("ia_umbral_venta", 0.65)))
            entry_umbral_venta.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # umbral_observacion (0.35 <= conf < 0.65 = observación)
            tk.Label(
                scrollable_frame,
                text="Umbral Observación (conf >=):",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_umbral_observacion = tk.Entry(scrollable_frame, width=50)
            entry_umbral_observacion.insert(0, str(envs_config.get("ia_umbral_observacion", 0.35)))
            entry_umbral_observacion.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # modelo_name
            tk.Label(
                scrollable_frame,
                text="Nombre Modelo:",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_modelo_name = tk.Entry(scrollable_frame, width=50)
            entry_modelo_name.insert(0, envs_config.get("ia_modelo_name", "modelo_sellv01"))
            entry_modelo_name.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # ========== GRUPO 2: MONITOREO CPU/MEMORIA ==========
            tk.Label(
                scrollable_frame,
                text="💻 Monitoreo CPU/Memoria",
                bg=self.colors["bgcolor"],
                fg="yellow",
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))
            row += 1

            # display
            tk.Label(
                scrollable_frame,
                text="Display:",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_display = tk.Entry(scrollable_frame, width=50)
            entry_display.insert(0, envs_config.get("display", "") or "")
            entry_display.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # max_points
            tk.Label(
                scrollable_frame,
                text="Max Points:",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_max_points = tk.Entry(scrollable_frame, width=50)
            entry_max_points.insert(0, str(envs_config.get("max_points", 40)))
            entry_max_points.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # interval
            tk.Label(
                scrollable_frame,
                text="Interval:",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_interval = tk.Entry(scrollable_frame, width=50)
            entry_interval.insert(0, str(envs_config.get("interval", 1)))
            entry_interval.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # CpuLock
            tk.Label(
                scrollable_frame,
                text="CPU Lock:",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_cpulock = tk.Entry(scrollable_frame, width=50)
            entry_cpulock.insert(0, envs_config.get("CpuLock", "") or "")
            entry_cpulock.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # ========== GRUPO 3: COLORES ==========
            tk.Label(
                scrollable_frame,
                text="🎨 Colores",
                bg=self.colors["bgcolor"],
                fg="yellow",
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))
            row += 1

            # bgcolor
            tk.Label(
                scrollable_frame,
                text="Color de Fondo (bgcolor):",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_bgcolor = tk.Entry(scrollable_frame, width=50)
            entry_bgcolor.insert(0, envs_config.get("bgcolor", "DarkCyan"))
            entry_bgcolor.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # cgcolor
            tk.Label(
                scrollable_frame,
                text="Color de Gráficos (cgcolor):",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry_cgcolor = tk.Entry(scrollable_frame, width=50)
            entry_cgcolor.insert(0, envs_config.get("cgcolor", "black"))
            entry_cgcolor.grid(row=row, column=1, padx=10, pady=5)
            row += 1

            # Subsección: Colores de Gráficos (cchart)
            tk.Label(
                scrollable_frame,
                text="  📊 Paleta de Gráficos (cchart):",
                bg=self.colors["bgcolor"],
                fg="cyan",
                font=("Segoe UI", 9, "bold"),
                anchor="w",
            ).grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
            row += 1

            cchart = envs_config.get("cchart", {})
            cchart_fields = [
                ("texto", "Texto"),
                ("titulo", "Título"),
                ("asx", "Eje X"),
                ("asy", "Eje Y"),
                ("axsy", "Grid Y"),
                ("axsx", "Grid X"),
                ("2eje", "Segundo Eje"),
                ("plot0", "Plot 0"),
                ("plot1", "Plot 1"),
                ("plot11", "Plot 11"),
                ("plot2", "Plot 2"),
                ("plot21", "Plot 21"),
                ("plot3", "Plot 3"),
                ("plot31", "Plot 31"),
                ("plot4", "Plot 4"),
                ("plot41", "Plot 41"),
                ("plot5", "Plot 5"),
                ("plot6", "Plot 6"),
                ("plot7", "Plot 7"),
                ("plot8", "Plot 8"),
                ("plot9", "Plot 9"),
            ]

            # Diccionario para almacenar referencias a entradas cchart
            cchart_entries = {}
            for field_key, field_label in cchart_fields:
                tk.Label(
                    scrollable_frame,
                    text=f"    {field_label}:",
                    bg=self.colors["bgcolor"],
                    fg="white",
                    anchor="w",
                ).grid(row=row, column=0, sticky="w", padx=20, pady=2)

                entry = tk.Entry(scrollable_frame, width=50)
                entry.insert(0, cchart.get(field_key, "white"))
                entry.grid(row=row, column=1, padx=10, pady=2)

                # Guardar referencia en diccionario
                cchart_entries[field_key] = entry
                row += 1

            # Frame de botones (igual que editor de sesiones)
            btn_frame = tk.Frame(scrollable_frame, bg=self.colors["bgcolor"])
            btn_frame.grid(row=row, column=0, columnspan=2, pady=20)

            save_btn = tk.Button(btn_frame, text="Guardar", width=10, command=save_envs)
            save_btn.pack(side=tk.LEFT, padx=10)

            cancel_btn = tk.Button(btn_frame, text="Cancel", width=10, command=eexit)
            cancel_btn.pack(side=tk.LEFT, padx=10)

            # Empaquetar canvas y scrollbar
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

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
                        "Idcuenta_principal": var_idcuenta_principal.get(),
                        "id_transaccion": var_id_transaccion.get(),
                        "load_csv": var_load_csv.get(),
                        "fefund": entry_fefund.get().strip(),
                        "Pinvertir": entry_Pinvertir.get().strip(),
                        "gypPrecio": entry_gypPrecio.get().strip(),
                        "gainInversion": entry_gainInversion.get().strip(),
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
                        "environment": entry_environment.get().strip() if entry_environment else None,
                        "parameters": (
                            blob_parameters.get("1.0", tk.END).strip().encode("utf-8")
                            if blob_parameters.get("1.0", tk.END).strip()
                            else None
                        ),
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
                            # Intentar formato completo, si falla usar solo fecha con hora actual
                            try:
                                values["fesesion"] = datetime.strptime(values["fesesion"], "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                # Solo fecha: agregar hora actual
                                fecha = datetime.strptime(values["fesesion"], "%Y-%m-%d")
                                now = datetime.now()
                                values["fesesion"] = fecha.replace(hour=now.hour, minute=now.minute, second=now.second)
                        else:
                            values["fesesion"] = datetime.now()  # Default: fecha/hora actual

                        if values["fiscalYear"]:
                            values["fiscalYear"] = datetime.strptime(values["fiscalYear"], "%Y-%m-%d").date()
                        else:
                            values["fiscalYear"] = None

                        if values["fefund"]:
                            values["fefund"] = datetime.strptime(values["fefund"], "%Y-%m-%d").date()
                        else:
                            values["fefund"] = None
                    except ValueError as ve:
                        MyMessageBox(session_window).showerror(
                            "Error de Validación", f"Formato de fecha inválido: {ve}"
                        )
                        return

                    # Convertir Pinvertir a int
                    try:
                        values["Pinvertir"] = int(values["Pinvertir"]) if values["Pinvertir"] else 0
                    except ValueError:
                        MyMessageBox(session_window).showerror("Error de Validación", "Pinvertir debe ser un número")
                        return

                    # Convertir gypPrecio a float
                    try:
                        values["gypPrecio"] = float(values["gypPrecio"]) if values["gypPrecio"] else 0.0
                    except ValueError:
                        MyMessageBox(session_window).showerror(
                            "Error de Validación",
                            "Gyp Precio debe ser un número decimal",
                        )
                        return

                    # Convertir gainInversion a float
                    try:
                        values["gainInversion"] = float(values["gainInversion"]) if values["gainInversion"] else 0.0
                    except ValueError:
                        MyMessageBox(session_window).showerror(
                            "Error de Validación",
                            "Gain Inversión debe ser un número decimal",
                        )
                        return

                    # Convertir port a int
                    try:
                        values["port"] = int(values["port"]) if values["port"] else None
                    except ValueError:
                        MyMessageBox(session_window).showerror("Error de Validación", "Port debe ser un número entero")
                        return

                    # Validar rango de port
                    if values["port"] is not None and (values["port"] < 1 or values["port"] > 65535):
                        MyMessageBox(session_window).showerror("Error de Validación", "Port debe estar entre 1 y 65535")
                        return

                    # Guardar en BD
                    if edit_mode:
                        success = BDsystem.update_sesion(session_data["id"], session_data["vehiculo"], values)
                        msg = "Sesión actualizada correctamente" if success else "No se pudo actualizar la sesión"
                    else:
                        success = BDsystem.insert_sesion(values)
                        msg = "Sesión creada correctamente" if success else "No se pudo crear la sesión"

                    if success:
                        MyMessageBox(session_window).showinfo("Éxito", msg)
                        editor_window.destroy()
                        refresh_sessions()
                    else:
                        MyMessageBox(session_window).showerror("Error", msg)
                except Exception as e:
                    print(f"[save_session()]: {e}")
                    MyMessageBox(session_window).showerror("Error", f"Error al guardar sesión: {str(e)}")

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
                    MyMessageBox(session_window).showerror("Error", f"Error al importar archivo: {str(e)}")

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
            editor_window.geometry(f"700x700+{session_x + session_width + 10}+{session_y}")

            editor_window.resizable(False, False)
            editor_window.config(bg=self.colors["bgcolor"])
            editor_window.grab_set()
            editor_window.focus()

            # Crear canvas scrollable
            canvas = tk.Canvas(editor_window, bg=self.colors["bgcolor"])
            scrollbar = ttk.Scrollbar(editor_window, orient="vertical", command=canvas.yview)
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
                    "disabled" if edit_mode else "normal",
                ),
                ("fesesion", "Fecha Sesión (YYYY-MM-DD HH:MM:SS):", "normal"),
                ("iduser", "ID Usuario (char 10):", "normal"),
                ("idcuenta", "ID Cuenta (char 10):", "normal"),
                ("orcartera", "Orden Cartera (char 50):", "normal"),
                (
                    "fiscalYear",
                    "Año Fiscal (YYYY-MM-DD):",
                    "normal",
                ),
                (
                    "fefund",
                    "Fecha Fundación (YYYY-MM-DD):",
                    "disabled" if edit_mode else "normal",
                ),
                ("Pinvertir", "Monto a Invertir (int):", "normal"),
                ("gypPrecio", "Gyp Precio (float):", "normal"),
                ("gainInversion", "Gain Inversión (float):", "normal"),
                ("xstrategy", "Estrategia (char 60):", "normal"),
                ("port", "Puerto (int 1-65535):", "normal"),
                ("environment", "Environment (TESTNET|PRODUCTION):", "normal"),
            ]

            # Crear widgets de entrada
            entry_vehiculo = None
            entry_fesesion = None
            entry_iduser = None
            entry_idcuenta = None
            entry_orcartera = None
            entry_fiscalYear = None
            var_idcuenta_principal = None
            var_id_transaccion = None
            var_load_csv = None
            entry_fefund = None
            entry_Pinvertir = None
            entry_gypPrecio = None
            entry_gainInversion = None
            entry_xstrategy = None
            entry_port = None
            entry_environment = None

            for field_name, label_text, state in fields_config:
                label = tk.Label(
                    scrollable_frame,
                    text=label_text,
                    bg=self.colors["bgcolor"],
                    fg="white",
                    anchor="w",
                )
                label.grid(row=row, column=0, sticky="w", padx=10, pady=5)

                # Crear Entry siempre en estado normal para permitir inserción de valores
                entry = tk.Entry(scrollable_frame, width=50)
                entry.grid(row=row, column=1, padx=10, pady=5)

                # Poblar con datos existentes si está en modo edición
                if edit_mode and session_data:
                    value = session_data.get(field_name, "")
                    if value:
                        if field_name == "fesesion" and hasattr(value, "strftime"):
                            entry.insert(0, value.strftime("%Y-%m-%d %H:%M:%S"))
                        elif field_name in ["fiscalYear", "fefund"] and hasattr(value, "strftime"):
                            entry.insert(0, value.strftime("%Y-%m-%d"))
                        else:
                            entry.insert(0, str(value))

                # Aplicar estado disabled/readonly DESPUÉS de insertar valores
                if state == "disabled":
                    entry.config(state="disabled")
                elif state == "readonly":
                    entry.config(state="readonly")

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

                    # Agregar campo Idcuenta_principal (booleano) justo después de fiscalYear
                    row += 1
                    label_principal = tk.Label(
                        scrollable_frame,
                        text="⭐ Cuenta Principal:",
                        bg=self.colors["bgcolor"],
                        fg="white",
                        anchor="w",
                    )
                    label_principal.grid(row=row, column=0, sticky="w", padx=10, pady=5)

                    var_idcuenta_principal = tk.BooleanVar(value=False)
                    check_principal = tk.Checkbutton(
                        scrollable_frame,
                        variable=var_idcuenta_principal,
                        state="disabled",  # Siempre deshabilitado
                        bg=self.colors["bgcolor"],
                    )
                    check_principal.grid(row=row, column=1, sticky="w", padx=10, pady=5)

                    # Poblar con datos existentes si está en modo edición
                    if edit_mode and session_data:
                        is_principal = session_data.get("Idcuenta_principal", False)
                        var_idcuenta_principal.set(is_principal)

                    # Agregar campo id_transaccion (booleano) - indica si transacciona en línea
                    row += 1
                    label_transaccion = tk.Label(
                        scrollable_frame,
                        text="🔄 Transacción Online:",
                        bg=self.colors["bgcolor"],
                        fg="white",
                        anchor="w",
                    )
                    label_transaccion.grid(row=row, column=0, sticky="w", padx=10, pady=5)

                    var_id_transaccion = tk.BooleanVar(value=False)
                    check_transaccion = tk.Checkbutton(
                        scrollable_frame,
                        variable=var_id_transaccion,
                        state="normal",  # Editable
                        bg=self.colors["bgcolor"],
                    )
                    check_transaccion.grid(row=row, column=1, sticky="w", padx=10, pady=5)

                    # Poblar con datos existentes si está en modo edición
                    if edit_mode and session_data:
                        transaccion_value = session_data.get("id_transaccion", False)
                        var_id_transaccion.set(transaccion_value)

                    # Agregar campo load_csv (booleano editable) justo después de id_transaccion
                    row += 1
                    label_load_csv = tk.Label(
                        scrollable_frame,
                        text="Load CSV:",
                        bg=self.colors["bgcolor"],
                        fg="white",
                        anchor="w",
                    )
                    label_load_csv.grid(row=row, column=0, sticky="w", padx=10, pady=5)

                    var_load_csv = tk.BooleanVar(value=False)
                    check_load_csv = tk.Checkbutton(
                        scrollable_frame,
                        variable=var_load_csv,
                        state="normal",  # Editable
                        bg=self.colors["bgcolor"],
                    )
                    check_load_csv.grid(row=row, column=1, sticky="w", padx=10, pady=5)

                    # Poblar con datos existentes si está en modo edición
                    if edit_mode and session_data:
                        load_csv_value = session_data.get("load_csv", False)
                        var_load_csv.set(load_csv_value)

                elif field_name == "fefund":
                    entry_fefund = entry
                elif field_name == "Pinvertir":
                    entry_Pinvertir = entry
                elif field_name == "gypPrecio":
                    entry_gypPrecio = entry
                elif field_name == "gainInversion":
                    entry_gainInversion = entry
                elif field_name == "xstrategy":
                    entry_xstrategy = entry
                elif field_name == "port":
                    entry_port = entry
                elif field_name == "environment":
                    entry_environment = entry

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
            blob_parameters = None

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

            # Campo parameters (BLOB/JSON) — al final
            label_params = tk.Label(
                scrollable_frame,
                text="Parameters (JSON):",
                bg=self.colors["bgcolor"],
                fg="white",
                anchor="w",
            )
            label_params.grid(row=row, column=0, sticky="nw", padx=10, pady=5)

            blob_frame_params = tk.Frame(scrollable_frame, bg=self.colors["bgcolor"])
            blob_frame_params.grid(row=row, column=1, padx=20, pady=5, sticky="ew")

            blob_parameters = tk.Text(blob_frame_params, width=30, height=5)
            blob_parameters.pack(side=tk.LEFT)

            import_btn_params = tk.Button(
                blob_frame_params,
                text="Importar",
                command=lambda: import_blob_file(blob_parameters),
            )
            import_btn_params.pack(side=tk.LEFT, padx=5)

            if edit_mode and session_data:
                params_value = session_data.get("parameters")
                if params_value:
                    try:
                        if isinstance(params_value, bytes):
                            blob_parameters.insert("1.0", params_value.decode("utf-8"))
                        else:
                            blob_parameters.insert("1.0", str(params_value))
                    except Exception:
                        blob_parameters.insert("1.0", "[Datos binarios]")

            row += 1

            # Frame de botones
            btn_frame = tk.Frame(scrollable_frame, bg=self.colors["bgcolor"])
            btn_frame.grid(row=row, column=0, columnspan=2, pady=20)

            save_btn = tk.Button(btn_frame, text="Guardar", width=10, command=save_session)
            save_btn.pack(side=tk.LEFT, padx=10)

            cancel_btn = tk.Button(btn_frame, text="Cancel", width=10, command=cancel_edit)
            cancel_btn.pack(side=tk.LEFT, padx=10)

            # Empaquetar canvas y scrollbar
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def eexit():
            """Cierra la ventana y limpia la referencia"""
            session_window.destroy()
            self.setup_window = None

        # Crear ventana principal de gestión de sesiones
        try:
            # Ventana Toplevel
            session_window = tk.Toplevel(self.root)
            session_window.title("Setup - Inversionista")

            # Guardar referencia para control de instancia única
            self.setup_window = session_window

            # Asegurar limpieza al cerrar con la X de la ventana
            session_window.protocol("WM_DELETE_WINDOW", eexit)

            # Cargar datos desde BD
            sessions = BDsystem.select_all_sesion()
            height = max(2, len(sessions) + 1)

            # Posicionamiento (izquierda de la pantalla para dejar espacio al editor)
            window_width = 850
            window_height = min(550, 30 + height * 25)
            x_position = 300
            y_position = 110
            session_window.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
            session_window.config(bg=self.colors["bgcolor"])
            session_window.resizable(True, True)

            # Panel de control con botones
            control_frame = ttk.Frame(session_window, style="C.TFrame", padding=(10, 10))
            control_frame.pack(side=tk.BOTTOM, fill=tk.X)

            add_btn = tk.Button(control_frame, text="Agregar", width=10, command=on_add_click)
            add_btn.pack(side=tk.LEFT, padx=5)

            delete_btn = tk.Button(control_frame, text="Eliminar", width=10, command=on_delete_click)
            delete_btn.pack(side=tk.LEFT, padx=5)

            refresh_btn = tk.Button(control_frame, text="Refrescar", width=10, command=refresh_sessions)
            refresh_btn.pack(side=tk.LEFT, padx=5)

            envs_btn = tk.Button(control_frame, text="Envs", width=10, command=on_envs_click)
            envs_btn.pack(side=tk.LEFT, padx=5)

            cancel_btn = tk.Button(control_frame, text="Cancel", width=10, command=eexit)
            cancel_btn.pack(side=tk.LEFT, padx=5)

            # Frame para TreeView
            tree_frame = ttk.Frame(session_window, style="B.TFrame")
            tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Definición de columnas (sin id, orcartera, xstrategy, userapi, userpass, private_key, public_key)
            columns = [
                "vehiculo",
                "fiscalYear",
                "⭐",
                "iduser",
                "idcuenta",
                "fesesion",
                "Pinvertir",
                "gypPrecio",
                "gainInversion",
            ]

            fixed_columns = ["vehiculo", "fiscalYear", "⭐"]

            column_alignments = {
                "vehiculo": {"width": 80, "anchor": "w"},
                "fiscalYear": {"width": 80, "anchor": "w"},
                "⭐": {"width": 30, "anchor": "c"},
                "iduser": {"width": 80, "anchor": "w"},
                "idcuenta": {"width": 80, "anchor": "w"},
                "fesesion": {"width": 140, "anchor": "w"},
                "Pinvertir": {"width": 90, "anchor": "e"},
                "gypPrecio": {"width": 90, "anchor": "e"},
                "gainInversion": {"width": 100, "anchor": "e"},
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
                style="TFrame",
            )

            # Vincular eventos
            tree.tree_fixed.bind("<Double-1>", on_double_click)
            tree.tree_scroll.bind("<Double-1>", on_double_click)

            # Carga inicial
            refresh_sessions()
        except Exception as e:
            print(f"[setup()]: {e}")
            MyMessageBox(session_window).showerror("Error", f"Error al abrir gestor de sesiones: {str(e)}")

    def eexit(self):
        """Cierra la aplicación de forma ordenada"""

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
            plt.close("all")
        except:
            pass

        # Detener BotCrypto (flag _closing + WS + timers)
        try:
            if hasattr(self, "bot_crypto_ui") and self.bot_crypto_ui:
                self.bot_crypto_ui.detener()
        except:
            pass

        try:
            stop_tv_server()
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
        sys.exit(0)

    def get_limite_inversion(self):
        """toma limites de barraProgress"""
        traz = self.PlanInversion.select_trazaplan(idcuenta=self.sesion_stock["idcuenta"])
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
            limit_costoB, limit_gyp = self.get_limite_inversion()

            # add saldos botCrypto
            capital_botCrypto = DataHub.manager_GyP["BotCrypto"].get("Inversion", 0)
            Value_botCrypto = DataHub.manager_GyP["BotCrypto"].get("Value", 0)
            Gyp_botCrypto = capital_botCrypto - Value_botCrypto

            ganancias_dia = totales["total_ganancia_dia"] + Gyp_botCrypto
            costo_base = totales["total_costo_base"] + capital_botCrypto

            if ganancias_dia > 0:
                _inf = 0
            elif ganancias_dia <= 0:
                _inf = -1

            if abs(ganancias_dia) < limit_gyp:
                _mul = 1
            elif abs(ganancias_dia) > limit_gyp:
                _mul = round(abs(ganancias_dia / limit_gyp), 1)

            low_limit_gyp = (_inf * _mul) * limit_gyp
            high_limit_gyp = _mul * limit_gyp

            # deuda total Stock + Crypto vs límite máximo
            total_debit = DataHub.manager_GyP.get("Stock", {}).get("Debit", 0) + DataHub.manager_GyP.get(
                "Crypto", {}
            ).get("Debit", 0)
            total_debitmax = DataHub.manager_GyP.get("Stock", {}).get("DebitMax", 0) + DataHub.manager_GyP.get(
                "Crypto", {}
            ).get("DebitMax", 0)

            # update progressos
            self.GypProgress.update_values(low_limit_gyp, ganancias_dia, high_limit_gyp)
            self.InvProgress.update_values(0, costo_base, limit_costoB)
            self.DebtProgress.update_values(0, total_debit, total_debitmax if total_debitmax > 0 else 1)

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

    def run(self):
        """Inicia el dashboard"""

        # Cargar variables de entorno desde base de datos (sesión DataHub) ------------------------------------------
        DataHub.load_from_database()

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
        self.gestion = GestionInversion(parent=self.root, master=self.win3, colores=self.colors)
        self.gestion.pack()

        # define widget principales FCI-------------------------------------------------------------------
        self.sesion_FCI = self.PlanInversion.get_sesion_by_vehiculo("SANT.ARS")
        self.fci = ArsFondosInversion(parent=self.root, master=self.win4, colores=self.colors)
        self.fci.pack()

        # Inicializar UI del Bot Crypto ------------------------------------------------------------------
        self.bot_crypto_ui = BotCryptoUI(
            parent=self.win6,
            colors=self.colors,
            repositorio=self.RepositorioOportunidades,
        )
        self.bot_crypto_ui.inicializar()

        self.finance = FinancePanel(master=self.win9, colores=self.colors)
        self.finance.pack(fill=tk.BOTH, expand=True)
        self.finance.inicializar()

        self.system = system_status(master=self.win5, colores=self.colors)

        self.screener = Screener(master=self.win2, account=self.sesion_stock["idcuenta"], colors=self.colors)
        self.screener.pack()

        # Inicia servidor HTTP para datos TradingView (Tampermonkey) ------------------------------------
        start_tv_server()
        start_price_sync(lambda: DataHub.info)

        # Start ayudante y agentes del sistema------------------------------------------------------------
        self.start_chatbot()

        # Iniciar actualización de totales de inversionescls
        self.actualizar_totales_inversiones()

        self.root.mainloop()


if __name__ == "__main__":
    app = DashMain()
    app.run()
