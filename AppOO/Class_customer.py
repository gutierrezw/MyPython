from Modulos_python import (
    tk,
    ttk,
    datetime,
    threading,
    Figure,
    FigureCanvasTkAgg,
    Image,
    ImageTk,
    io,
    websocket,
    ssl,
    time,
    json,
    timedelta,
    yf,
    pd,
    np,
    plt,
    math,
    colormaps,
    mdates,
    mpatches,
    dtime,
    schedule,
    os,
    subprocess,
    csv,
    ast,
    json,
    date,
    logging,
    Future,
    textwrap,
    traceback,
    webbrowser,
    pyautogui,
)
from Modulos_Utilitarios import (
    display_red_green,
    sort_positions,
    convierte_ticket_crypto,
    is_magnitud,
    currency,
    porcentaje,
    vehiculo_parm,
    buscar_ticker,
    format_financiero,
    E,
    W,
    get_indicadores,
    calculate_decimal_places,
    calcular_atr,
    define_FileCache,
    read_json_tmp,
    write_json_tmp,
)
from Modulos_Comunes import (
    diaria_book_performance,
    performa_asset,
    proceso_update_performance,
)
from Class_DataFrame import (
    get_ultimo_dia_mercado,
    get_yfinance,
    chart_symbol,
    chart_rendimiento_dividendos,
    CacheHut,
    show_strategy_chart,
)
from Modulos_Mysql import (
    PlanInversion,
    EstrategiaInversion,
    RepositorioOportunidadesBuySell,
    MarketScreen,
    BDsystem,
)
from Class_Analisis import AnalisisFCI, AnalisisCrypto, AnalisisStock
from AppValuations.rebalance_engine import RebalanceEngine
from Class_ApiIBrks import IB
from Class_ApiBinnace import BinanceClient, BinanceStreamClient, BinanceWSApiClient


# class Manager para procesa ordenes remotas
class OrderManagerSync:
    def __init__(self):
        self.inbox = []  # lista de tuplas (orden, future)

        # Asigna Nombre Logging
        self.logger = logging.getLogger("IBroks_Client")

    def _normalize_order(self, trama):
        """Garantiza que el pedido sea un dict válido."""
        if isinstance(trama, dict):
            return trama
        if isinstance(trama, str):
            try:
                return json.loads(trama)  # si viene en JSON válido
            except json.JSONDecodeError:
                return ast.literal_eval(trama)  # si viene como string de dict
        raise TypeError(f"Formato de pedido no soportado: {type(trama)}")

    def _request(self, trama_in):
        """
        Cliente envía orden y espera respuesta.
        Retorna la respuesta procesada.
        """
        future = Future()
        trama = self._normalize_order(trama_in)

        self.inbox.append((trama, future))

        # log de entrada a inbox
        self.logger.warning(
            textwrap.dedent(
                f"""
                  =================================
                  class OrderManagerSync._request(): 
                  =================================  
                  inbox.append: {trama}
                  """
            )
        )
        return future.result()  # bloquea hasta que el procesador complete

    def get_next_order(self):
        """Procesador toma siguiente orden y su future"""
        if self.inbox:
            trama, future = self.inbox.pop(0)
            trama_out = self._normalize_order(trama)
            return trama_out, future

        return tuple((None, None))

    def _complete(self, future, resp):
        """Procesador completa la orden y desbloquea al cliente"""

        future.set_result(resp)

        # log de respuesta al inbox
        self.logger.warning(
            textwrap.dedent(
                f"""
                ===================================
                OrderManagerSync.request(complete): 
                ===================================  
                inbox.append: {resp}
                """
            )
        )


# clase para contener datos compartidos en la aplicacion
class DataHub:
    """
    Clase global para variables de entorno y configuración del sistema.

    Las variables configurables se cargan desde la base de datos (sesión DataHub).
    Estructura organizada en 4 grupos:
    1. Colores (bgcolor, cgcolor, cchart)
    2. Monitor CPU/Memoria (display, max_points, interval, CpuLock)
    3. Parámetros de Trading (MinProfit, Toleranciasell, MaxRoi, InicioInversior, ib_gateway_host, ib_gateway_port)
    4. Estructuras runtime (no configurables - se inicializan en código)
    """

    # ========================================================================================================
    # GRUPO 1: CONFIGURACIÓN DE COLORES (Cargable desde DB)
    # ========================================================================================================
    session_data = BDsystem.get_sesion_by_vehiculo(vehiculo="DataHub")
    envs_config = json.loads(session_data["userapi"].decode("utf-8"))
    bgcolor = envs_config["bgcolor"]
    cgcolor = envs_config["cgcolor"]
    cchart = envs_config["cchart"]
    cchart["tab20"] = colormaps.get_cmap("tab20")
    colors = {
        "bgcolor": bgcolor,
        "cgcolor": cgcolor,
        "fgcolor": "white",
        "dw": 1290,
        "dh": 700,
        "df": 1297,
        "max_dw": None,
        "max_dh": None,
        "cchart": cchart,
    }

    # ========================================================================================================
    # GRUPO 2: MONITOREO DE CPU Y MEMORIA (Cargable desde DB)
    # ========================================================================================================
    DCpu = []
    DMem = []
    display = envs_config["display"] or None
    max_points = envs_config["max_points"] or 40
    interval = envs_config["interval"] or 1
    CpuLock = envs_config["CpuLock"] or None

    # ========================================================================================================
    # GRUPO 3: PARÁMETROS DE TRADING (Cargable desde DB)
    # ========================================================================================================
    # Sell
    MinProfit = envs_config["MinProfit"] or 50
    Toleranciasell = envs_config["Toleranciasell"] or 0.10
    MaxRoi = envs_config["MaxRoi"] or 0.09

    # Buy
    MinGananciaPrecio = envs_config.get("MinGananciaPrecio") or 0.05  # 5% mínimo de ganancia precio
    MinScoreBuy = envs_config.get("MinScoreBuy") or 0.5  # Score mínimo para Buy

    InicioInversior = envs_config["InicioInversior"]
    ib_gateway_host = envs_config["ib_gateway_host"]
    ib_gateway_port = envs_config["ib_gateway_port"]

    # ========================================================================================================
    # GRUPO 4: ESTRUCTURAS RUNTIME (NO configurables - se inicializan en código)
    # ========================================================================================================

    # Sesiones y managers
    SessionYfinance = None
    QremoteOrder = {"Stock": OrderManagerSync(), "Crypto": OrderManagerSync()}
    manager_events = {}
    manager_after = {}
    manager_buysell = {}
    manager_sesion = {}
    manager_GyP = {"BotCrypto": {"Value": 0, "Inversion": 0, "dGyP": 0, "Debit": 0, "Margen": 0}}
    rebalanceo = {}
    telegram_botcrypto = {}
    procesos = []
    logger = {}
    orders = {}
    info = {
        "TimeDataHub": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Set para modelos IA
    JsonMSell = [
        "roi",
        "Nro_lotes",
        "cantidad_sell",
        "price_market",
        "costo_acumulado",
        "costo_base",
        "position",
        "Disponible",
        "Pos_AvgCost",
        "Pos_Position",
        "Pos_CostBase",
        "recomendado",
        "comentarios",
        "indicadores",
    ]
    ColumnCsvSell = [
        "Symbol",
        "account",
        "vehiculo",
        "Opcion",
        "Profit",
        "NroLotes",
        "CantidadSell",
        "PriceMarket",
        "Fecha",
        "CostoCum",
        "%Roi",
        "CostoBase",
        "Position",
        "Disponible",
        "PosAvgCost",
        "PosPosition",
        "PosCostobase",
        "Datostecnicos",
        "Recomendado",
        "Comentarios",
    ]

    ColumnCsvBuy = [
        "Symbol",
        "account",
        "vehiculo",
        "tipo",  # buy o dividends
        "score",
        "monto_sugerido",
        "pinvertir",
        "ganancia_precio",
        "ganancia_inversion",
        "cantidad_buy",
        "last",
        "avgcost",
        "cantidad_post",
        "avgcost_post",
        "retorno_post",
        "objetivo",
        "dividend_yield",
        "ex_dividend_date",
        "pre_dividendos",
        "post_dividendos",
        "pre_costobase",
        "post_costobase",
        "Datostecnicos",
        "Fecha",
        "Recomendado",
        "Comentarios",
    ]
    SellCsvJsonDcolumnas = {
        "Symbol": "symbol",
        "Opcion": "opcion",
        "Profit": "profit",
        "%Roi": "roi",
        "NroLotes": "Nro_lotes",
        "CantidadSell": "cantidad_sell",
        "pricemarket": "price_market",
        "CostoCum": "costo_acumulado",
        "CostoBase": "costo_base",
        "Position": "position",
        "Disponible": "Disponible",
        "PosAvgCost": "Pos_AvgCost",
        "PosPosition": "Pos_Position",
        "PosCostobase": "Pos_CostBase",
        "Recomendado": "recomendado",
        "Comentarios": "comentarios",
        "Datostecnicos": "datos_tecnicos",
    }

    BuyCsvJsonDcolumnas = {
        "Symbol": "symbol",
        "account": "account",
        "vehiculo": "vehiculo",
        "tipo": "tipo",
        "score": "score",
        "monto_sugerido": "monto_sugerido",
        "ganancia_precio": "ganancia_precio",
        "ganancia_inversion": "ganancia_inversion",
        "cantidad_buy": "cantidad_buy",
        "last": "last",
        "avgcost": "avgcost",
        "cantidad_post": "cantidad_post",
        "avgcost_post": "avgcost_post",
        "retorno_post": "retorno_post",
        "objetivo": "objetivo",
        "dividend_yield": "dividend_yield",
        "ex_dividend_date": "ex_dividend_date",
        "pre_dividendos": "pre_dividendos",
        "post_dividendos": "post_dividendos",
        "pre_costobase": "pre_costobase",
        "post_costobase": "post_costobase",
        "Datostecnicos": "datos_tecnicos",
        "Recomendado": "recomendado",
        "Comentarios": "comentarios",
    }
    max_mensajes = 5
    min_tiempo = 300  # segundos entre mensajes Sell (5 min)
    min_tiempo_buy = 300  # segundos entre mensajes Buy (5 min)

    # Fechas y procesos batch
    now = datetime.now()
    mrk_anterior = get_ultimo_dia_mercado(market="Stock")
    dia_anterior = get_ultimo_dia_mercado(market="Crypto")
    mrv_anterior = get_ultimo_dia_mercado(market="BBVA.ARS")
    mrv_safeday = mrv_anterior - timedelta(days=2)  # BBVA.ARS cierra un dia después

    wait_3m = now + timedelta(minutes=3)
    last_process = {
        "Stock": {"diaria_book_performance": mrk_anterior, "wait": wait_3m},
        "Crypto": {"diaria_book_performance": dia_anterior, "wait": wait_3m},
        "BBVA.ARS": {"diaria_book_performance": mrv_safeday, "wait": wait_3m},
        "BotCrypto": {"diaria_book_performance": mrv_safeday, "wait": wait_3m},
        "graph_performace_portafolio": False,
        "dividends_en_market_stock": now,
    }
    ultimoTraderCrypto = None

    # Locks para sincronización de procesos
    lockCsvAi = threading.Lock()
    lockInfo = threading.Lock()
    SupervisedThread = []

    # Accesos MySql
    RepositorioOportunidades = RepositorioOportunidadesBuySell()

    # ========================================================================================================
    # MÉTODOS DE INICIALIZACIÓN
    # ========================================================================================================

    @staticmethod
    def load_from_database():
        """
        Carga las variables de entorno desde la sesión DataHub en la base de datos.

        Grupos cargados:
        1. Colores (bgcolor, cgcolor, cchart)
        2. Monitor CPU/Memoria (display, max_points, interval, CpuLock)
        3. Parámetros de Trading (MinProfit, Toleranciasell, MaxRoi, InicioInversior, ib_gateway_host, ib_gateway_port)

        Returns:
            bool: True si cargó exitosamente, False si hubo error
        """
        try:
            # Obtener sesión DataHub
            datahub_session = BDsystem.get_sesion_by_vehiculo(vehiculo="DataHub")

            if not datahub_session or not datahub_session.get("userapi"):
                print("[DataHub.load_from_database] ADVERTENCIA: No se encontró configuración en DataHub")
                return False

            # Decodificar JSON desde BLOB
            envs_config = json.loads(datahub_session["userapi"].decode("utf-8"))

            # ====== GRUPO 1: COLORES ======
            if "bgcolor" in envs_config:
                DataHub.bgcolor = envs_config["bgcolor"]
                DataHub.colors["bgcolor"] = envs_config["bgcolor"]

            if "cgcolor" in envs_config:
                DataHub.cgcolor = envs_config["cgcolor"]
                DataHub.colors["cgcolor"] = envs_config["cgcolor"]

            if "cchart" in envs_config:
                DataHub.cchart.update(envs_config["cchart"])
                # Actualizar fondo con bgcolor
                DataHub.cchart["fondo"] = DataHub.bgcolor
                DataHub.cchart["fondo_fig"] = DataHub.cgcolor
                DataHub.colors["cchart"] = DataHub.cchart

            # ====== GRUPO 2: MONITOR CPU/MEMORIA ======
            if "display" in envs_config:
                DataHub.display = envs_config["display"]

            if "max_points" in envs_config:
                DataHub.max_points = envs_config["max_points"]

            if "interval" in envs_config:
                DataHub.interval = envs_config["interval"]

            if "CpuLock" in envs_config:
                DataHub.CpuLock = envs_config["CpuLock"]

            # ====== GRUPO 3: PARÁMETROS DE TRADING ======
            if "MinProfit" in envs_config:
                DataHub.MinProfit = float(envs_config["MinProfit"])

            if "Toleranciasell" in envs_config:
                DataHub.Toleranciasell = float(envs_config["Toleranciasell"])

            if "MaxRoi" in envs_config:
                DataHub.MaxRoi = float(envs_config["MaxRoi"])

            # Buy parameters
            if "MinGananciaPrecio" in envs_config:
                DataHub.MinGananciaPrecio = float(envs_config["MinGananciaPrecio"])

            if "MinScoreBuy" in envs_config:
                DataHub.MinScoreBuy = float(envs_config["MinScoreBuy"])

            if "InicioInversior" in envs_config:
                # Convertir string a date
                inicio_str = envs_config["InicioInversior"]
                if isinstance(inicio_str, str):
                    DataHub.InicioInversior = datetime.strptime(inicio_str, "%Y-%m-%d").date()

            if "ib_gateway_host" in envs_config:
                DataHub.ib_gateway_host = envs_config["ib_gateway_host"]

            if "ib_gateway_port" in envs_config:
                DataHub.ib_gateway_port = envs_config["ib_gateway_port"]

            return True

        except Exception as e:
            print(f"[DataHub.load_from_database] ERROR: {e}")
            traceback.print_exc()
            return False

    # actualiza contador self.procesos
    def update_self_procesos(proces=None, tarea=None, itera=0):
        # actualiza self.procesos
        if itera > 0:
            for i, rows in enumerate(DataHub.procesos):
                if proces in rows:
                    for task, subgrupo in rows[proces].items():

                        # caso: {'running': {'schedule_WebsocketBinanceStream': 304}}
                        if tarea == task:
                            DataHub.procesos[i][proces][tarea] = itera
                            break
                        else:
                            # caso: {'widget': {'Crypto_Dashmain': {'update_widget': 0}}}]
                            if isinstance(subgrupo, dict):
                                if tarea in subgrupo.keys():
                                    DataHub.procesos[i][proces][task][tarea] = itera
                                    break

        # retorna itera
        elif itera == 0:
            for i, rows in enumerate(DataHub.procesos):
                if proces in rows:
                    for task, subgrupo in rows[proces].items():
                        if tarea == task:
                            return DataHub.procesos[i][proces][tarea]
                        else:
                            # caso: {'widget': {'Crypto_Dashmain': {'update_widget': 0}}}]
                            if isinstance(subgrupo, dict):
                                if tarea in subgrupo.keys():
                                    return DataHub.procesos[i][proces][task][tarea]

            # caso de not found()
            return 0

    # write CSV: Oportunity sell
    def csv_OptionSales_write() -> None:
        """Genera CSV con oportunidades de venta para modelo IA."""
        try:
            path = define_FileCache(name="csv_datosIA_sell.csv")
            sells = DataHub.get_info_symbols_gain()

            with DataHub.lockCsvAi:
                with open(path, mode="w", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)
                    writer.writerow(DataHub.ColumnCsvSell)

                    for item in sells:
                        # Filtra profit por debajo del umbral
                        if item["profit"] < DataHub.MinProfit:
                            continue

                        ventas = DataHub.maximiza_sell_lotes(
                            account=item["account"],
                            symbol=item["symbol"],
                            last=item["last"],
                            c_sell=item["cantidad lotes"],
                            position=item["position"],
                            costobase=item["costobase"],
                        )

                        profit_anterior = None
                        for opcion, venta in ventas.items():
                            # Evita duplicados con mismo profit
                            if venta["profit"] == profit_anterior:
                                continue
                            profit_anterior = venta["profit"]

                            datos_tec = json.dumps(item.get("datos_tecnicos", {}))
                            writer.writerow(
                                [
                                    item["symbol"],
                                    item["account"],
                                    item["vehiculo"],
                                    opcion,
                                    venta["profit"],
                                    venta["lotes"],
                                    venta["cantidad sell"],
                                    item["last"],
                                    datetime.now().date(),
                                    venta["costo lote"],
                                    venta["roi"],
                                    item["costobase"],
                                    item["position"],
                                    item["disponible"],
                                    venta["pos avgCost"],
                                    venta["pos position"],
                                    venta["pos costobase"],
                                    datos_tec,
                                    0,  # Recomendado
                                    "SinNota",  # Comentarios
                                ]
                            )
        except Exception as e:
            print(f"csv_OptionSales_write(): {e}")

    # write CSV: Oportunity buy
    def csv_OptionBuy_write() -> None:
        """Genera CSV con oportunidades de compra para modelo IA."""
        try:
            path = define_FileCache(name="csv_datosIA_buy.csv")

            with DataHub.lockCsvAi:
                with open(path, mode="w", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)
                    writer.writerow(DataHub.ColumnCsvBuy)

                    # Obtener rebalanceo disponible
                    if not hasattr(DataHub, "rebalanceo") or not DataHub.rebalanceo:
                        return

                    with DataHub.lockInfo:
                        info_tmp = DataHub.info.copy()

                    for vehiculo, datos in DataHub.rebalanceo.items():
                        # Stock usa asignaciones, otros usan ranking
                        candidatos = datos.get("asignaciones", []) if vehiculo == "Stock" else datos.get("ranking", [])

                        for item in candidatos:
                            symbol = item.get("symbol")
                            if not symbol:
                                continue

                            # Obtener datos del símbolo desde info
                            info_symbol = info_tmp.get(symbol, {})
                            account = info_symbol.get("account", "")

                            # Buscar datos de buy o dividends
                            buy_data = info_symbol.get("buy") or info_symbol.get("dividends")
                            if not buy_data:
                                continue

                            # Determinar tipo (buy o dividends)
                            tipo = "dividends" if "dividends" in info_symbol else "buy"

                            score = item.get("score", 0)
                            monto_sugerido = item.get("monto_sugerido", 0)
                            if monto_sugerido == 0:
                                monto_sugerido = item.get("impacto", {}).get("gap_valor_total", 0)
                            pinvertir = item.get("pinvertir", 0)

                            # Filtrar sin score o monto
                            if score <= 0 or monto_sugerido <= 0:
                                continue

                            datos_tec = json.dumps(info_symbol.get("datos_tecnicos", {}))

                            writer.writerow(
                                [
                                    symbol,
                                    account,
                                    vehiculo,
                                    tipo,
                                    score,
                                    monto_sugerido,
                                    pinvertir,
                                    buy_data.get("ganancia precio", 0),
                                    buy_data.get("ganancia inversión", 0),
                                    buy_data.get("cantidad buy", 0),
                                    buy_data.get("last", 0),
                                    buy_data.get("avgcost", 0),
                                    buy_data.get("cantidad post", 0),
                                    buy_data.get("avgCost post", 0),
                                    buy_data.get("retorno post", 0),
                                    buy_data.get("objetivo", 0),
                                    buy_data.get("dividendYield", 0),
                                    buy_data.get("exDividendDate", ""),
                                    buy_data.get("pre dividendos", 0),
                                    buy_data.get("post dividendos", 0),
                                    buy_data.get("pre costobase", 0),
                                    buy_data.get("post costobase", 0),
                                    datos_tec,
                                    datetime.now().date(),
                                    0,  # Recomendado
                                    "SinNota",  # Comentarios
                                ]
                            )
        except Exception as e:
            print(f"csv_OptionBuy_write(): {e}")

    # recorre DataHub.info() para mostrar lo disponible para la sell
    def get_info_symbols_gain():
        try:
            a_sell, symbols = [], []
            # recupera profit que este desde DataHub.info[*]['sell']
            with DataHub.lockInfo:
                info_tmp = DataHub.info.copy()

            for keys, value in info_tmp.items():
                if "account" in value:
                    account = value["account"]
                    vehiculo = value["vehiculo"]
                elif "account" not in value:
                    continue

                if "sell" in value:
                    if "profit" in value["sell"]:
                        datos_tecnicos = {}
                        if "datos_tecnicos" in value:
                            datos_tecnicos = value["datos_tecnicos"]

                        a_sell.append(
                            {
                                "symbol": keys,
                                "account": account,
                                "vehiculo": vehiculo,
                                "profit": value["sell"]["profit"],
                                "cantidad lotes": value["sell"]["cantidad lotes"],
                                "cantidad sell": value["sell"]["cantidad sell"],
                                "costoCum": value["sell"]["costoCum"],
                                "roi": value["sell"]["roi"],
                                "last": value["sell"]["last"],
                                "position": value["sell"]["position"],
                                "costobase": value["sell"]["costobase"],
                                "disponible": value["sell"]["disponible"],
                                "divisa": value["sell"]["divisa"],
                                "factor": value["sell"]["factor"],
                                "datos_tecnicos": datos_tecnicos,
                            }
                        )

            # ordena lista de lotes ganadores y asigna acum=0  e insert symbols padres
            s_sell = sorted(a_sell, key=lambda x: x["profit"], reverse=True)

            return s_sell
        except Exception as e:
            print("[get_info_symbols_gain()]: {}".format(e))

    # recorre booktrading() para mostrar lotes  del symbol
    def get_lotesGainLost(opcion=None, account=None, symbol=None, divisa="USD", last=0):
        def lotesGain(book=None, ix=None, last=0):
            try:
                l_gain = []
                # enumera book, hace primera lectura e inicializa variables
                pbook, gain = enumerate(book), []
                eof_pbook, recd = next(pbook, (None, None))

                while eof_pbook is not None:

                    x_stock, x_costo, lotes = 0.0, 0.0, 0
                    factor, divisa = 0.0, "USD"
                    pkey = str(recd[ix.index("preciotrans")])
                    fkey = recd[ix.index("fechahora")].strftime("%Y-%m-%d")
                    key = f"{pkey}{fkey}"

                    while (eof_pbook is not None) and (key == f"{pkey}{fkey}"):

                        factor = recd[ix.index("factor_cambio")]
                        divisa = recd[ix.index("divisa")]

                        prec = recd[ix.index("preciotrans")]
                        cant = recd[ix.index("cantidad")]
                        cost = prec * cant + recd[ix.index("tarifacomision")]
                        fechahora = recd[ix.index("fechahora")]

                        x_costo += cost
                        x_stock += cant

                        eof_pbook, recd = next(pbook, (None, None))
                        if eof_pbook is not None:
                            pkey = str(recd[ix.index("preciotrans")])
                            fkey = recd[ix.index("fechahora")].strftime("%Y-%m-%d")

                    gyp = last * x_stock - x_costo
                    if gyp > 0:
                        lotes += 1
                        roi = (gyp / x_costo) if x_costo > 0 else 0
                        gain.append(
                            {
                                "symbol": symbol,
                                "last": last,
                                "fechahora": fechahora.date(),
                                "precio": prec,
                                "cantidad": x_stock,
                                "roi": roi,
                                "gyp": gyp,
                                "costo lote": x_costo,
                                "Nro.Lote": lotes,
                                "divisa": divisa,
                                "factar_cambio": factor,
                            }
                        )

                # ordena DESC lista de lotes ganadores y asigna acum=0
                l_gain = sorted(gain, key=lambda x: x["Nro.Lote"], reverse=False)
                return l_gain
            except Exception as e:
                print(f"lotesGain: {e}")
                traceback.print_exc()

        def lotesGainLost(book=None, ix=None, last=0):
            try:
                pbook = enumerate(book)
                eof_pbook, recd = next(pbook, (None, None))

                a_gain, a_lost, c_gain, c_lost, p_gain, p_lost = [], [], 0.0, 0.0, 0.0, 0.0
                x_profit, lote_profit, lotes_lost, x_cantidad = 0.0, 0.0, 0.0, 0.0

                while eof_pbook is not None:

                    prec, x_stock, x_costo = 0.0, 0.0, 0.0
                    factor, divisa = 0.0, "USD"

                    pkey = str(recd[ix.index("preciotrans")])
                    fkey = recd[ix.index("fechahora")].strftime("%Y-%m-%d")
                    key = f"{pkey}{fkey}"

                    while (eof_pbook is not None) and (key == f"{pkey}{fkey}"):

                        factor = recd[ix.index("factor_cambio")]
                        divisa = recd[ix.index("divisa")]

                        prec = recd[ix.index("preciotrans")]
                        cant = recd[ix.index("cantidad")]
                        cost = prec * cant + recd[ix.index("tarifacomision")]
                        fechahora = recd[ix.index("fechahora")]

                        x_costo += cost
                        x_stock += cant

                        eof_pbook, recd = next(pbook, (None, None))
                        if eof_pbook is not None:
                            pkey = str(recd[ix.index("preciotrans")])
                            fkey = recd[ix.index("fechahora")].strftime("%Y-%m-%d")

                    gyp = (last - prec) * x_stock

                    # acumula lotes con ganancias
                    if gyp >= 0:
                        x_profit += gyp
                        lote_profit += 1
                        x_cantidad += x_stock

                        c_gain += x_costo
                        p_gain += gyp
                        roi = (p_gain / c_gain) if c_gain > 0 else 0

                        a_gain.append(
                            {
                                "precio": prec,
                                "costo": x_costo,
                                "cantidad": x_stock,
                                "gyp": gyp,
                                "roi": roi,
                                "fecha": fechahora.date(),
                                "Nro.Lote": lote_profit,
                                "divisa": divisa,
                                "factar_cambio": factor,
                            }
                        )

                    # acumula lotes con perdidas
                    elif gyp < 0:
                        c_lost += prec * cant
                        p_lost += gyp
                        lotes_lost += 1
                        roi = (p_lost / c_lost) if c_lost > 0 else 0
                        a_lost.append(
                            {
                                "precio": prec,
                                "costo": x_costo,
                                "cantidad": x_stock,
                                "gyp": gyp,
                                "roi": roi,
                                "fecha": fechahora.date(),
                                "Nro.Lote": lotes_lost,
                                "divisa": divisa,
                                "factar_cambio": factor,
                            }
                        )

                # eof_pbbok()
                ResumLotes = {
                    "book": (book, ix),
                    "last": last,
                    "profit": x_profit,
                    "gain lotes": lote_profit,
                    "total lotes": lote_profit + lotes_lost,
                    "cantidad": x_cantidad,
                }
                return ResumLotes, a_gain, a_lost
            except Exception as e:
                print(f"lotesGainLost: {e}")
                traceback.print_exc()

        try:
            book, ix = DataHub.RepositorioOportunidades.select_booktrading(
                accion="select*", account=account, idivisa=divisa, symbol=symbol
            )
            # Elimina registros con 'codigo' == 'C' del book
            book = [row for row in book if row[ix.index("codigo")] != "C"]

            if book:
                if opcion == "gain":
                    return lotesGain(book, ix, last)
                elif opcion == "ambos":
                    return lotesGainLost(book, ix, last)
        except Exception as e:
            print(f"get_lotesGainLost: {e}")
            traceback.print_exc()

    # optimiza venta de lotes para la gain de capital
    def maximiza_sell_lotes(account=None, symbol=None, last=None, c_sell=None, position=None, costobase=None):
        try:
            pre_sell = {
                " 25%": {
                    "cantidad sell": 0.0,
                    "profit": 0.0,
                    "lotes": 0,
                    "costo lote": 0.0,
                    "roi": 0.0,
                    "pos avgCost": 0.0,
                    "pos position": 0.0,
                    "pos costobase": 0.0,
                },
                " 33%": {
                    "cantidad sell": 0.0,
                    "profit": 0.0,
                    "lotes": 0,
                    "costo lote": 0.0,
                    "roi": 0.0,
                    "pos avgCost": 0.0,
                    "pos position": 0.0,
                    "pos costobase": 0.0,
                },
                "100%": {
                    "cantidad sell": 0.0,
                    "profit": 0.0,
                    "lotes": 0,
                    "costo lote": 0.0,
                    "roi": 0.0,
                    "pos avgCost": 0.0,
                    "pos position": 0.0,
                    "pos costobase": 0.0,
                },
            }

            # lista de lotes ganadores y last
            list_gain = DataHub.get_lotesGainLost(opcion="gain", account=account, symbol=symbol, last=last)
            if list_gain:
                ebook, lotes_gain, pos_sell = (enumerate(list_gain), len(list_gain), {})
                eof_book, read = next(ebook, (None, None))

                while eof_book is not None:
                    key, stock, costo, gain = read["fechahora"], 0.0, 0.0, 0.0

                    last = read["last"]
                    cant = read["cantidad"]
                    cost = read["costo lote"]

                    gain += last * cant - cost
                    costo += cost
                    stock += cant

                    cant_acum = pre_sell[" 25%"]["cantidad sell"] + cant
                    cant_lote = pre_sell[" 25%"]["lotes"] + 1
                    p_sell = (cant_lote / c_sell) if c_sell > 0 else 0
                    if p_sell <= 0.25:
                        gain_acum = pre_sell[" 25%"]["profit"] + gain
                        cost_acum = pre_sell[" 25%"]["costo lote"] + costo
                        new_position = position - cant_acum
                        new_costobase = costobase - cost_acum
                        new_avgCost = new_costobase / new_position if new_position > 0 else 0
                        roi = (gain_acum / cost_acum) if cost_acum > 0 else 0
                        pre_sell[" 25%"] = {
                            "cantidad sell": cant_acum,
                            "profit": gain_acum,
                            "lotes": cant_lote,
                            "costo lote": cost_acum,
                            "roi": roi,
                            "pos avgCost": new_avgCost,
                            "pos position": new_position,
                            "pos costobase": new_costobase,
                        }

                    cant_acum = pre_sell[" 33%"]["cantidad sell"] + cant
                    cant_lote = pre_sell[" 33%"]["lotes"] + 1
                    p_sell = (cant_lote / c_sell) if c_sell > 0 else 0
                    if p_sell <= 0.336:
                        cant_acum = pre_sell[" 33%"]["cantidad sell"] + stock
                        gain_acum = pre_sell[" 33%"]["profit"] + gain
                        cost_acum = pre_sell[" 33%"]["costo lote"] + costo
                        new_position = position - cant_acum
                        new_costobase = costobase - cost_acum
                        new_avgCost = new_costobase / new_position if new_position > 0 else 0
                        roi = (gain_acum / cost_acum) if cost_acum > 0 else 0

                        pre_sell[" 33%"] = {
                            "cantidad sell": cant_acum,
                            "profit": gain_acum,
                            "lotes": cant_lote,
                            "costo lote": cost_acum,
                            "roi": roi,
                            "pos avgCost": new_avgCost,
                            "pos position": new_position,
                            "pos costobase": new_costobase,
                        }

                    cant_acum = pre_sell["100%"]["cantidad sell"] + stock
                    cant_lote = pre_sell["100%"]["lotes"] + 1
                    p_sell = (cant_lote / c_sell) if c_sell > 0 else 0
                    if p_sell <= 1.0:
                        cant_acum = pre_sell["100%"]["cantidad sell"] + stock
                        gain_acum = pre_sell["100%"]["profit"] + gain
                        cost_acum = pre_sell["100%"]["costo lote"] + costo
                        new_position = position - cant_acum
                        new_costobase = costobase - cost_acum
                        new_avgCost = new_costobase / new_position if new_position > 0 else 0
                        roi = (gain_acum / cost_acum) if cost_acum > 0 else 0

                        pre_sell["100%"] = {
                            "cantidad sell": cant_acum,
                            "profit": gain_acum,
                            "lotes": cant_lote,
                            "costo lote": cost_acum,
                            "roi": roi,
                            "pos avgCost": new_avgCost,
                            "pos position": new_position,
                            "pos costobase": new_costobase,
                        }

                    eof_book, read = next(ebook, (None, None))

            return pre_sell
        except Exception as e:
            print(f"maximiza_sell_lotes(): {e}")

    # ========================================================================================================
    # PRESERVATION: Lógica de vehículo para el Agente de Preservación de Ganancias
    # ========================================================================================================
    @staticmethod
    def preservation_get_price(symbol, positio):
        """Obtiene precio actual del símbolo (websocket → fallback mrkprice)."""
        info_symbol = DataHub.info.get(symbol, {})
        ws = info_symbol.get("websocket", {})
        return ws.get("last") or positio.get("mrkprice", 0)

    @staticmethod
    def preservation_get_atr(symbol, vehiculo="Stock"):
        """Calcula ATR desde CacheHut con fallback a yfinance. Retorna (atr, error_msg)."""

        # Intentar desde CacheHut primero
        info_symbol = DataHub.info.get(symbol, {})
        datos_fn = info_symbol.get("datos")
        datos = datos_fn() if datos_fn else None

        # Fallback: cargar desde yfinance si CacheHut está vacío
        if datos is None or datos.empty or len(datos) < 14:
            try:
                ticket = convierte_ticket_crypto(symbol) if vehiculo == "Crypto" else symbol
                result = get_yfinance(ticket=ticket, vehiculo=vehiculo, period="6mo", interval="1d")
                if result:
                    _, datos = result
            except Exception:
                pass

        if datos is None or datos.empty or len(datos) < 14:
            n = 0 if datos is None else len(datos)
            return None, f"datos insuficientes ({n} rows, CacheHut + yfinance)"
        return calcular_atr(datos), None

    @staticmethod
    def preservation_calc_qty(account, vehiculo, symbol, last, base_limit):
        """Calcula qty a proteger, respetando lotSize en Crypto."""

        def cantidad_lote():
            """Calcula qty a proteger desde booktranding."""
            value, qty_raw = 0.0, 0
            book = DataHub.get_lotesGainLost(opcion="gain", account=account, symbol=symbol, last=last)
            for keys in book:
                if value + keys.get("gyp", 0) > base_limit:
                    break

                value += keys.get("gyp", 0)
                qty_raw += keys.get("cantidad", 0)

            return qty_raw

        qty_raw = cantidad_lote()
        if vehiculo == "Crypto":
            info_symbol = DataHub.info.get(symbol, {})
            lot_info = info_symbol.get("lotSize", {})
            step_size = lot_info.get("stepSize", 0.00001)
            decimals = calculate_decimal_places(step_size)
            return round(qty_raw - (qty_raw % step_size), decimals)
        else:
            return qty_raw

    @staticmethod
    def preservation_build_trama(vehiculo, account, symbol, conid, stop_price, max_price, qty):
        """Construye la trama de orden STOP según el vehículo (IB o Binance)."""

        hash_id = DataHub.RepositorioOportunidades.generar_hash_id(
            account=account, symbol=symbol, option=vehiculo, tipo="STP", subtipo="LMT", recomendado="PRESERVATION_STOP"
        )
        if vehiculo == "Stock":
            return {
                "account": account,
                "vehiculo": "Stock",
                "symbol": symbol,
                "pedido": {
                    "orders": [
                        {
                            "conid": int(conid),
                            "orderType": "STP LMT",
                            "auxPrice": round(stop_price, 2),
                            "price": round(max_price, 2),
                            "side": "SELL",
                            "tif": "GTC",
                            "quantity": qty,
                        }
                    ]
                },
                "hash_id_Op": hash_id,
            }

        if vehiculo == "Crypto":
            return {
                "account": account,
                "vehiculo": "Crypto",
                "symbol": symbol,
                "pedido": {
                    "symbol": symbol,
                    "side": "SELL",
                    "type": "STOP_LOSS_LIMIT",
                    "price": round(stop_price, 2),
                    "stopPrice": round(stop_price, 2),
                    "quantity": qty,
                    "timeInForce": "GTC",
                },
                "hash_id_Op": hash_id,
            }

    @staticmethod
    def preservation_send_order(vehiculo, trama):
        """Envía orden STOP via QremoteOrder. Retorna response."""
        return DataHub.QremoteOrder[vehiculo]._request(trama)

    @staticmethod
    def preservation_cancel_order(vehiculo, account, order_id, symbol):
        """Cancela una orden PRESERVATION_STOP existente."""
        trama = {
            "account": account,
            "vehiculo": vehiculo,
            "symbol": symbol,
            "pedido": {"action": "cancel", "order_id": order_id},
            "hash_id_Op": "PRESERVATION_STOP",
        }
        return DataHub.QremoteOrder[vehiculo]._request(trama)

    @staticmethod
    def preservation_extract_order_id(response):
        """Extrae order_id de la respuesta tras colocar una orden."""
        try:
            if isinstance(response, dict):
                return response.get("order_id") or response.get("id")
            if isinstance(response, (list, tuple)) and response:
                first = response[0] if isinstance(response[0], dict) else response
                return first.get("order_id") or first.get("id")
        except Exception:
            pass
        return None


#  clase para colocar ordenes desde cualquier punto de la aplicacion
class MyOrders:
    def __init__(self, account, vehiculo, simulation=False):
        self.account = account
        self.vehiculo = vehiculo
        self.simulation = simulation

        # clientes de vehiculos
        self.BClient = BinanceClient().spot
        self.IClient = IB()

        # variables de TRADER
        self.entry_qty = None
        self.entry_prc = None
        self.entry_tip = None
        self.entry_id = None
        self.entry_tim = None
        self.entry_opt = None
        self.entry_conid = None
        self.SwichSumitOrder = False

        # Asigna Nombre Logging
        self.logger = logging.getLogger("ClassMyOrders")

    # colocación de la orden desde cuaquier punto
    def put_completa_orden(
        self,
        account=None,
        vehiculo=None,
        symbol=None,
        pedido=None,
        submit={},
        hash_id_Op=None,
        remote=False,
    ):
        # place order Stock
        def place_OrderStock(account, pedido):
            try:
                response, enviada, values = {}, {}, {}

                # Rectifica types de los parametros
                for keys in pedido["orders"]:
                    if "conid" in keys:
                        keys["conid"] = int(keys["conid"])
                    if "price" in keys:
                        keys["price"] = float(keys["price"])
                    if "quantity" in keys:
                        keys["quantity"] = float(keys["quantity"])
                orden = {"orders": [keys]}

                self.logger.warning(f"place_OrderStock: account={account} | symbol={symbol} | order={orden}")

                response = self.IClient.place_order(account_id=account, order=orden)

                if not response:
                    self.logger.error(
                        f"place_OrderStock: IB Gateway sin respuesta | account={account} | symbol={symbol}"
                    )
                    return {}, {}, {}

                self.SwichSumitOrder = True
                orden = pedido["orders"][0]
                resp = response[0] if isinstance(response, list) and response else response
                status, enviada, ClientOrderid = "Inactive", {}, " "
                stampSubmit = None

                self.logger.warning(
                    f"place_OrderStock: place_order OK | id={resp.get('id')} | response={response} | symbol={symbol}"
                )

                # Confirma orden en IB cuando no es simulación
                if not self.simulation and resp.get("id"):
                    RespEnviada = self.IClient.orderconfirm(replyid=resp["id"])

                    if RespEnviada:
                        tempJson = json.loads(RespEnviada)
                        enviada = tempJson[0] if isinstance(tempJson, list) else tempJson
                        if "order_status" in enviada:
                            status = enviada.get("order_status")
                            ClientOrderid = enviada.get("order_id")
                            stampSubmit = datetime.now()
                        self.logger.warning(f"place_OrderStock: confirm OK | status={status} | orderId={ClientOrderid}")
                    else:
                        self.logger.error(f"place_OrderStock: orderconfirm sin respuesta | replyid={resp.get('id')}")

                # Salva información de la orden — normalizar response a lista de dicts
                if isinstance(response, dict):
                    response = [response]
                elif not isinstance(response, list):
                    self.logger.error(f"place_OrderStock: response inesperado type={type(response)} | {response}")
                    return {}, {}, {}
                for items in response:
                    if not isinstance(items, dict):
                        self.logger.error(f"place_OrderStock: item no es dict: {items}")
                        continue
                    values.update(
                        {
                            "account": account,
                            "vehiculo": vehiculo,
                            "id_order": items["id"],
                            "conid": orden["conid"],
                            "orderType": orden["orderType"],
                            "price": orden["price"],
                            "side": orden["side"],
                            "tif": orden["tif"],
                            "status": status,
                            "quantity": orden["quantity"],
                            "clientOrderId": ClientOrderid,
                            "stampPlace": datetime.now(),
                            "stampSubmit": stampSubmit,
                            "hash_id_oportunidad": hash_id_Op,
                        }
                    )
                    self.RepositorioOportunidades.insert_order_trader(values=values, symbol=symbol)

                self.logger.warning(
                    f"place_OrderStock: COMPLETE | symbol={symbol} | status={status} | values={bool(values)}"
                )
                return response, enviada, values
            except Exception as e:
                self.logger.error(f"place_OrderStock({symbol}): {e}")
                traceback.print_exc()
                return {}, {}, {}

        # place order Crypto
        def place_OrderCrypto(pedido):
            try:
                response, enviada, values = {}, {}, {}

                response = self.BClient.get_new_order(
                    symbol=pedido["symbol"],
                    side=pedido["side"],
                    type=pedido["type"],
                    price=pedido["price"],
                    quantity=pedido["quantity"],
                    timeInForce=pedido["timeInForce"],
                )
                if response:
                    self.SwichSumitOrder = True
                    if "transactTime" in response.keys():
                        stamp = response["transactTime"] / 1000
                        values = {
                            "account": account,
                            "vehiculo": vehiculo,
                            "id_order": response["orderId"],
                            "conid": pedido["conid"],
                            "orderType": response["type"],
                            "price": response["price"],
                            "side": response["side"],
                            "tif": response["timeInForce"],
                            "status": response["status"],
                            "quantity": response["origQty"],
                            "clientOrderId": response["clientOrderId"],
                            "stampPlace": datetime.fromtimestamp(stamp),
                            "stampSubmit": datetime.fromtimestamp(stamp),
                            "hash_id_oportunidad": hash_id_Op,
                        }
                        self.RepositorioOportunidades.insert_order_trader(values=values, symbol=symbol)

                return response, enviada, values
            except Exception as e:
                self.logger.error(f"place_OrderCrypto({symbol}): {e}")
                traceback.print_exc()
                return {}, {}, {}

        try:
            if vehiculo == "Stock":
                response, enviada, values = place_OrderStock(account, pedido)

            elif vehiculo == "Crypto":
                response, enviada, values = place_OrderCrypto(pedido)
            else:
                response, enviada, values = {}, {}, {}

            # Traza de orden: WARNING si es remota o falló, DEBUG si local ok
            log_level = "warning" if remote or not values else "debug"
            getattr(self.logger, log_level)(
                textwrap.dedent(
                    f"""
                        ====================================
                        put_completa_orden({self.vehiculo}):
                        ====================================
                        Remote_order  : {remote}
                        Simutale_order: {self.simulation}
                        Order.........: {pedido}
                        API_response  : {response}
                        API_confirm   : {enviada}
                        Response      : {values}
                        """
                )
            )

            # Si es orden BUY exitosa, verifica si es activo nuevo para agregarlo al panel
            if values and values.get("side") == "BUY":
                found, _ = buscar_ticker(self.positions, symbol)
                if not found:
                    # Activo nuevo: agregar al panel WidgetVehiculo
                    precio = float(values.get("price", 0))
                    cantidad = float(values.get("quantity", 0))
                    costo = precio * cantidad
                    conid = values.get("conid")
                    self.agregar_nuevo_activo(symbol, conid, precio, cantidad, costo)

            return values
        except Exception as e:
            self.logger.error(f"put_completa_orden({symbol}): {e}")
            traceback.print_exc()
            return {}

    # ejecuta order trader
    def submit_orden(self, symbol, orden, option):
        def eexit():
            rnb.destroy()

        def ventana(cambio=None):

            # Asegura que las dimensiones sean correctas
            rnb.update_idletasks()

            # Calcular posición x y y para centrar la ventana
            rnb.resizable(False, False)
            rnb.attributes("-toolwindow", 1)
            rnb.config(bg=self.colors["cgcolor"])
            rnb.title(title)
            rnb.focus()
            rnb.grab_set()
            rnb.protocol("WM_DELETE_WINDOW", eexit)

            color = "blue" if option == "BUY" else "red"
            win0 = tk.Frame(rnb, bg=color, width=200)
            win1 = tk.Frame(rnb, bg=self.colors["cgcolor"], width=200)
            win2 = tk.Frame(rnb, bg=self.colors["cgcolor"], width=200)
            win3 = tk.Frame(rnb, bg=self.colors["fgcolor"], width=200)
            wi30 = tk.Frame(win3, bg=self.colors["fgcolor"], width=200)

            win3.pack(side=tk.BOTTOM, fill=tk.X)
            wi30.pack(side=tk.RIGHT)

            win0.pack(side=tk.TOP, fill=tk.X, pady=10)
            win1.pack(side=tk.LEFT, padx=10)
            win2.pack(side=tk.LEFT, padx=10)

            message = "{} : ({}, {})".format(option.upper(), cambio, symbol)
            bt1 = tk.Label(
                win0,
                text=f"{message}",
                font=("Arial", 12),
                bg=color,
                fg="white",
                height=3,
            )
            bt1.pack(side=tk.LEFT, padx=10)

            return (
                win1,
                win2,
                wi30,
            )

        # simulación antes y después de implicado por la 'place order'
        def display(win=None, submit=None, attribute=None, locate=None):

            if locate == "vertical":
                for fields, value in submit[attribute].items():

                    label_keys = tk.Label(
                        win,
                        text=f"{fields}:",
                        font=("Arial", 8),
                        bg="black",
                        fg="white",
                    )
                    label_value = tk.Label(win, text=f"{value}", font=("Arial", 8), bg="black", fg="white")

                    i = list(submit[attribute].keys()).index(fields)
                    label_keys.grid(row=i, column=0, padx=5, pady=5, sticky=W)
                    label_value.grid(row=i, column=1, padx=5, pady=5, sticky=W)

            if locate == "horizontal":
                for j, fields in enumerate(attribute):

                    label_keys = tk.Label(
                        win,
                        text=f"{fields}:",
                        font=("Arial", 8),
                        bg="black",
                        fg="white",
                    )
                    label_keys.grid(row=0, column=j + 1, padx=5, pady=5, sticky=W)

                    for k, keys in enumerate(submit[fields]):

                        value = submit[fields][keys]
                        label_field = tk.Label(
                            win,
                            text=f"{keys}",
                            font=("Arial", 8),
                            bg="black",
                            fg="white",
                        )
                        label_value = tk.Label(
                            win,
                            text=f"{value}",
                            font=("Arial", 8),
                            bg="black",
                            fg="white",
                        )

                        label_field.grid(row=k + 1, column=0, sticky=W)
                        label_value.grid(row=k + 1, column=j + 1, sticky=E)

        def completa_orden(symbol, pedido, submit):

            response = self.put_completa_orden(self.account, self.vehiculo, symbol, pedido, submit)
            eexit()

        def submit_stock():
            try:
                submit = self.IClient.place_order_scenario(account_id=self.account, order=orden)
                if submit:

                    win1, win2, win3 = ventana(cambio=submit["position"]["change"])

                    # pack() columna cantidad(win1)
                    display(win=win1, submit=submit, attribute="amount", locate="vertical")

                    # pack() position cantidad(win2)
                    a_list = ["equity", "initial", "maintenance", "position"]
                    display(win=win2, submit=submit, attribute=a_list, locate="horizontal")

                    bt3 = tk.Button(
                        win3,
                        text="CONFIRM",
                        width=8,
                        bg="gray",
                        fg="white",
                        command=lambda: completa_orden(symbol, orden, submit),
                    )

                    bt4 = tk.Button(
                        win3,
                        text="Cancel",
                        width=8,
                        bg="gray",
                        fg="white",
                        command=lambda: eexit(),
                    )

                    bt3.grid(row=0, column=0, sticky=W, padx=3, pady=10)
                    bt4.grid(row=0, column=1, sticky=W, padx=3, pady=10)
            except Exception as e:
                print(f"submit_stock(): {e}")

        def submit_crypto():
            try:
                # construye datos de simulación
                s_cambio = "{:>8.4f} {} {} {:>8.4f}".format(
                    orden["quantity"],
                    symbol.replace("USDT", ""),
                    orden["type"],
                    orden["price"],
                )

                producto = orden["price"] * orden["quantity"]
                comision = 0.0
                s_comision = "{:>8.2f} USDT".format(comision)
                s_total = "{:>8.2f} USDT".format(producto + comision)
                amount = "{:>8.2f} USDT ({},Coin)".format(producto, orden["quantity"])

                submit = {
                    "amount": {
                        "amount": amount,
                        "comisión": s_comision,
                        "total": s_total,
                    }
                }
                submit.update({"equity": {"amount": 0, "comisión": 0, "total": 0}})
                submit.update({"initial": {"amount": 1, "comisión": 1, "total": 1}})
                submit.update({"maintenance": {"amount": 2, "comisión": 2, "total": 2}})
                submit.update({"position": {"amount": 2, "comisión": 2, "total": 2}})
                win1, win2, win3 = ventana(cambio=s_cambio)

                # pack() columna cantidad(win1)
                display(win=win1, submit=submit, attribute="amount", locate="vertical")

                # pack() position cantidad(win2)
                a_list = ["equity", "initial", "maintenance", "position"]
                display(win=win2, submit=submit, attribute=a_list, locate="horizontal")

                bt3 = tk.Button(
                    win3,
                    text="CONFIRM",
                    width=8,
                    bg="gray",
                    fg="white",
                    command=lambda: completa_orden(symbol, orden, submit),
                )

                bt4 = tk.Button(
                    win3,
                    text="Cancel",
                    width=8,
                    bg="gray",
                    fg="white",
                    command=lambda: eexit(),
                )

                bt3.grid(row=0, column=0, sticky=W, padx=3, pady=10)
                bt4.grid(row=0, column=1, sticky=W, padx=3, pady=10)
            except Exception as e:
                print("[submit_crypto()]: {}".format(e))

        try:
            rnb = tk.Toplevel()
            title = "Submit Order : "
            dimension = "%dx%d+%d+%d" % (530, 250, 450, 450)
            rnb.geometry(dimension)

            if self.simulation:
                if self.vehiculo == "Stock":
                    submit_stock()

                    # if order sent
                    if self.SwichSumitOrder:
                        eexit()

                elif self.vehiculo == "Crypto":
                    submit_crypto()

                    # if order sent
                    if self.SwichSumitOrder:
                        eexit()

            # Not simulate and exit windows
            elif not self.simulation:
                completa_orden(symbol, orden, submit={})
        except Exception as e:
            print(f"submit_orden({self.vehiculo}): {e}")

    # parámetros para quantity, typeOrder y TimeInForce
    @staticmethod
    def params_order(vehiculo=None, elementos=None):
        if vehiculo == "Stock":
            qtys = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 100, 150, 200, 300]
            items = ["LMT", "MKT", "STP", "TRAIL", "REL", "RPI", "MOC", "LOC"]
            tif = ["DAY", "GTC"]

        elif vehiculo == "Crypto":
            qtys = [50, 100, 200, 300, 400, 500, 1000, 2000, 3000, 5000, 10000]
            items = [
                "LIMIT",
                "MARKET",
                "STOP_LOSS",
                "STOP_LOSS_LIMIT",
                "TAKE_PROFIT",
                "TAKE_PROFIT_LIMIT",
            ]
            tif = ["DAY", "GTC"]

        # condiciona elementos para return
        if elementos is None:
            return qtys[:], items[:], tif[:]
        elif not elementos:
            return qtys[elementos], items[elementos], tif[elementos]

    # Da structura ORders y verificacs cantidades disponible
    def format_orden(self, vehiculo, symbol, idd, tip, prc, opt, tim, qty):

        if vehiculo == "Stock":
            cantidad = self.stock_free_operar(symbol=symbol)
            orden = {
                "orders": [
                    {
                        "conid": idd,
                        "orderType": tip,
                        "price": round(prc, 2),
                        "side": opt,
                        "tif": tim,
                        "quantity": qty,
                        "outsideRTH": True,
                    }
                ]
            }

        elif vehiculo == "Crypto":
            cantidad = self.crypto_wallet_free(symbol=symbol, SetLotSize=True)

            # valida cantidad en spot y rescata de earn si es necesario
            if cantidad < qty and tip in ("Sell", "SELL"):
                rescata = round(qty - cantidad, 1)
                ticket = symbol.replace("USDT", "001")
                self.crypto_earn_rescate(symbol=ticket, amount=rescata)

            orden = {
                "conid": idd,
                "symbol": symbol,
                "type": tip,
                "price": prc,
                "side": opt,
                "timeInForce": "GTC",
                "quantity": qty,
                "disponibilidad": cantidad,
            }

        return orden

    # panel de buy & sell -------------------------------------------------------------------------------------------
    def WindowsBuySell_trader(self, rnb=None, option=None, parm=None):
        # controla salida de window_estrategia()
        def eexit():
            self.orderActivas = None
            rnb.destroy()

        # Cierra la entrada de texto y asigna el valor seleccionado tipo
        def on_select_tip(event):
            try:
                selected_item = lbx.get(lbx.curselection())
                self.entry_tip.set(selected_item)
                lbx.grid_forget()
            except (Exception, ValueError) as e:
                print("on_select_tip({}): {}".format(self.vehiculo, e))

        # Cierra la entrada de texto y asigna el valor seleccionado Qty
        def on_select_qty(event):
            selected_item = lbq.get(lbx.curselection())
            self.entry_qty.set(selected_item)
            lbq.grid_forget()

        # Muestra el Listbox tipo de orden.
        def on_click_tip(event):
            try:
                lbx.grid(row=2, column=2, pady=1)
            except (Exception, ValueError) as e:
                print("on_click_tip({}): {}".format(self.vehiculo, e))

        # Muestra el Listbox cuando se hace clic en el Entry.
        def on_click_qty(event):
            lbx.grid(row=2, column=2, pady=1)

        # valida que este disponible en Spot la cantidad de
        def valida_wallet_spot():
            try:
                cantidad, t_qty = self.crypto_wallet_free(symbol=symbol, SetLotSize=True), float(qty)

                # valida cantidad en spot y rescata de earn si es necesario
                if cantidad < t_qty:
                    amount = t_qty - cantidad
                    ticket = symbol.replace("USDT", "001")
                    self.crypto_earn_rescate(symbol=ticket, amount=amount)

                    cantidad = self.crypto_wallet_free(symbol=symbol, SetLotSize=True)
                    if cantidad < t_qty:
                        message = "No es posible rescatar {} su disponibilidad es de {:>,.5f}".format(
                            self.symbol, cantidad
                        )
                        self.messagebox.showinfo(title="Alerta", message=message)
            except (Exception, ValueError) as e:
                print("valida_wallet_spot({}): {}".format(self.vehiculo, e))

        def pre_orden(x_option):
            nonlocal qty
            try:
                win3.grid_forget()

                qty = self.entry_qty.get()
                if float(qty) > 0.0:

                    # antes de ceder el control verifica y carga wallet spot
                    if (self.vehiculo == "Crypto") and (x_option == "SELL"):
                        valida_wallet_spot()

                    self.valida_orden_vehiculo(option=x_option)

                    # if sumit ORder Exit
                    if self.SwichSumitOrder:
                        eexit()

                else:
                    self.messagebox.showinfo(
                        title="Submit" + x_option,
                        message="No es posible vender, si no ingresa una cantidad mayor a '0'",
                    )
            except (Exception, ValueError) as e:
                print("pre_orden({}): {}".format(self.vehiculo, e))

        # calcula cantidad en función de estrategia y cash disponible
        def cantidad_ordenada(x_symbol, x_option, precio):
            nonlocal cash
            try:
                cantidad = 0.0
                if option == "BUY":
                    cash = float(self.resumen[" Cash       :"])
                    if 0 < cash < self.invertir:
                        cantidad = cash / precio
                    else:
                        cantidad = self.invertir / precio
                    cantidad = round(cantidad, 1)
                    return cantidad

                if option == "SELL":
                    if self.vehiculo == "Crypto":
                        cantidad = self.crypto_wallet_free(symbol=symbol)
                        return cantidad

                    if self.vehiculo == "Stock":
                        cantidad = self.stock_free_operar(symbol=symbol)
                        return cantidad
            except (Exception, ValueError) as e:
                print("cantidad_ordenada({}): {}".format(self.vehiculo, e))

        def cash_redeem():
            try:
                self.crypto_earn_rescate(symbol="USDT001", amount=20)
            except (Exception, ValueError) as e:
                print("cash_redeem({}): {}".format(self.vehiculo, e))

        def update_windows():
            try:
                self.ventanas_activas()

                # actualiza cada 0.5" segundos
                self.orderActivas.after(500, update_windows)
            except (Exception, ValueError) as e:
                print("update_windows({}): {}".format(self.vehiculo, e))

        def on_swicth_sumit(estado):
            if estado:
                self.simulation = True
            else:
                self.simulation = False

        try:
            self.SwichSumitOrder = False
            desc = "Buy/Sell" if option is None else option
            color = "blue" if option == "BUY" else "red"
            symbol = parm["ticket"]

            win1 = tk.Frame(rnb, bg=color, width=200)  # información previa
            win2 = tk.Frame(rnb, bg=color, width=200)  # linea de parameter
            win3 = tk.Frame(rnb, bg=self.cgcolor, width=200)  # submit
            win1.pack(fill=tk.X)
            win2.pack(fill=tk.X)
            win3.pack(fill=tk.X, pady=1)
            win1.grid_rowconfigure(0, weight=1)

            # QTY y position en la misma columna ---------------------------------------------
            list_qty, items, tif = self.params_order(self.vehiculo)
            qty = cantidad_ordenada(symbol, option, parm["mkPrice"])

            self.entry_qty = tk.StringVar(value=str(qty))
            bt2 = tk.Label(win1, text="QTY", bg="gray", fg="white")
            bt3 = tk.Entry(win1, width=17, textvariable=self.entry_qty)
            # bt3.bind("<Button-1>", on_click_qty)

            lbq = tk.Listbox(win1, width=4, height=3)
            for item in list_qty:
                lbq.insert(tk.END, item)
            # lbx.bind("<<ListboxSelect>>", on_select_qty)

            position = "Position :{:>10.5f}".format(parm["stock"])
            available = "Disponible :{:>10.5f}".format(0)
            cash = "Cash : " + self.resumen[" Cash       :"]
            pt0 = tk.Button(
                win1,
                text=position,
                wraplength=150,
                justify="left",
                bg="gray",
                fg="white",
            )

            self.available = tk.Button(
                win1,
                text=available,
                wraplength=150,
                justify="left",
                bg="green",
                fg="white",
            )

            pt1 = tk.Button(
                win1,
                text=cash,
                wraplength=150,
                justify="left",
                bg="green",
                fg="white",
                command=lambda: cash_redeem(),
            )

            pt0.grid(row=0, column=1, sticky=W, padx=0, pady=10)
            self.available.grid(row=0, column=2, sticky=W, padx=0, pady=10)
            pt1.grid(row=0, column=5, sticky=W, padx=0, pady=10)

            bt2.grid(row=2, column=0, sticky=W, padx=20, pady=20)
            bt3.grid(row=2, column=1, padx=0)

            # BID, ASK y precio de trader --------------------------------------------------
            def calcular_precio_medio():
                """Calcula precio medio entre bid y ask y lo pone en entry_prc"""
                try:
                    bid_text = self.bid.cget("text").replace("Bid", "").strip()
                    ask_text = self.ask.cget("text").replace("Ask", "").strip()
                    bid_val = float(bid_text) if bid_text else 0
                    ask_val = float(ask_text) if ask_text else 0
                    if bid_val > 0 and ask_val > 0:
                        medio = (bid_val + ask_val) / 2
                        # Redondea a 2 decimales para cumplir PRICE_FILTER de Binance
                        self.entry_prc.set(f"{medio:.2f}")
                except Exception:
                    pass

            bid = "Bid {:>10.6f}".format(0)
            self.bid = tk.Button(win1, text=bid, width=15, bg="gray", fg="white")
            ask = "Ask {:>10.6f}".format(0)
            self.ask = tk.Button(win1, text=ask, width=15, bg="gray", fg="white")

            # Botón para calcular precio medio
            btn_medio = tk.Button(win1, text="↔", width=2, bg="cyan", fg="black", command=calcular_precio_medio)

            # Entry de tipo de Orden ---------------------------------------------------------------------------------------------
            s_tip = items[0]
            self.entry_tip = tk.StringVar(value=s_tip)
            self.entry_prc = tk.StringVar(value=str(parm["mkPrice"]))

            bt4 = tk.Entry(win1, width=5, textvariable=self.entry_tip)
            bt5 = tk.Entry(win1, width=15, textvariable=self.entry_prc)
            bt4.bind("<Button-1>", on_click_tip)

            lbx = tk.Listbox(win1, width=18, height=3)
            for item in items:
                lbx.insert(tk.END, item)
            lbx.bind("<<ListboxSelect>>", on_select_tip)

            self.bid.grid(row=1, column=2, sticky=E)
            btn_medio.grid(row=1, column=3, padx=2)
            self.ask.grid(row=1, column=4, sticky=W)

            bt4.grid(row=2, column=2, sticky=E)
            bt5.grid(row=2, column=3, columnspan=2, sticky=W)

            # timeInForce --------------------------------------------------------------------------------------------------------
            bt6 = tk.Label(win1, text=tif[0], bg="gray", fg="white")

            # botones de submit / cancel -----------------------------------------------------------------------------------------
            bt7 = ToggleSwitch(win3, command=on_swicth_sumit)
            simula = ttk.Label(win3, text=f"Simula {option}:", font=("Arial", 9))

            ct1 = tk.Button(
                win3,
                text="SUBMIT",
                width=8,
                bg="gray",
                fg="white",
                command=lambda: pre_orden(option),
            )

            ct2 = tk.Button(
                win3,
                text="Cancel",
                width=8,
                bg="gray",
                fg="white",
                command=lambda: eexit(),
            )

            bt6.grid(row=2, column=5, padx=20)

            simula.pack(side=tk.LEFT, padx=5)
            bt7.pack(side=tk.LEFT, padx=1)
            ct2.pack(side=tk.RIGHT, padx=5, pady=10)
            ct1.pack(side=tk.RIGHT)

            self.entry_opt = option
            self.entry_tim = "DAY"
            self.entry_id = parm["conid"]

            # ciclo para mantener actualizada la windows
            update_windows()
        except (TypeError, Exception, ValueError) as e:
            print(f"WindowsBuySell_trader({self.vehiculo}): {e}")
            traceback.print_exc()

    # verificar parameters order vehiculo ---------------------------------------------------------------------------
    def valida_orden_vehiculo(self, option=None):
        try:
            qty = float(self.entry_qty.get())
            prc = float(self.entry_prc.get())
            tip = self.entry_tip.get()

            idd = int(self.entry_id)
            opt = self.entry_opt
            tim = self.entry_tim

            if (qty > 0) and (prc > 0):

                # controla order para Stock y Crypto
                orden = self.format_orden(self.vehiculo, self.symbol, idd, tip, prc, opt, tim, qty)
                self.submit_orden(self.symbol, orden, option)
        except Exception as e:
            print(f"valida_orden_vehiculo({self.vehiculo})]: {e}")

    # obtiene puntualmente la cantidad free de un symbol
    def stock_free_operar(self, symbol=None):
        try:
            cantidad = 0.0
            if "sell" in self.info[symbol].keys():

                sell = self.info[symbol]["sell"]
                cantidad = sell["disponible"]

            return cantidad
        except Exception as e:
            pass


# Superclase para unificar atributos de los activos
class TickerInfo(MyOrders):
    def __init__(self, account, vehiculo):
        MyOrders.__init__(self, account=account, vehiculo=vehiculo)  # Inicializa los atributos de MyOrders

        self.summary = {}
        self.resumen = {}
        self.activos = []
        self.assets = {}
        self.currency = {}
        self.positions = []
        self.conid_inicio = {}

        self.WStreams = None
        self.WsClient = None

        # comparte lista de procesos Datahub
        self.cchart = DataHub.cchart
        self.procesos = DataHub.procesos
        self.orders = DataHub.orders
        self.info = DataHub.info

        self.schOportunidades = 0
        self.schOperativo_itera = 0
        self.schDiario_itera = 0
        self.schTrader_itera = 0
        self.schRemoteOrder_itera = 0

        # Accesos MySql ----------------------------------------------------------------------------------------------
        self.PlanInversion = PlanInversion()
        self.RepositorioOportunidades = RepositorioOportunidadesBuySell()

        # información de sesión y orden de cartera
        self.sesion = self.PlanInversion.get_sesion_by_vehiculo(self.vehiculo)
        self.orden = json.loads(self.sesion["orcartera"])

    # desde tabla inicia la estructura positions
    def carga_inversion_en_positions(self) -> list:
        try:
            self.positions = []

            cartera = self.PlanInversion.select_inversion(tipoin=self.vehiculo, ticket="all")
            positions = sort_positions(cartera, self.orden)

            for position in positions:

                # filtra posiciones mayores a 5 $USD y cantidad > 0
                if position["costobase"] > 5 and position["position"] > 0:
                    self.add_position(
                        position["ticket"],
                        position["useraccount"],
                        position["estrategia"],
                        position["empresa"],
                        position["peso"],
                        position["mrkprice"],
                        position["costobase"],
                        position["position"],
                        position["unrealizedpnl"],
                        position["dividendo"],
                        position["dividendYield"],
                        position["exDividendDate"],
                        position["conid"],
                        position["objetivo"],
                        position["deuda"],
                        position["retorno"],
                        position["fealta"],
                        position["febaja"],
                        position["iactiva"],
                        position["tipoinv"],
                        position["sector"],
                        position["open"],
                        position["mktvalue"],
                        position["dgyp"],
                        position["factor_cambio"],
                        position["nivelIA"],
                        position["region"],
                        position["country"],
                        position["divisa"],
                        position["sectype"],
                    )
        except Exception as e:
            print("[carga_inversion_en_positions()]: {}".format(e))

    # construye y adiciona las posiciones del vehiculo
    def add_position(
        self,
        ticket,
        useraccount,
        estrategia,
        empresa,
        peso,
        mrkprice,
        costobase,
        position,
        unrealizedpnl,
        dividendo,
        dividendyield,
        exdividend,
        conid,
        objetivo,
        deuda,
        retorno,
        fealta,
        febaja,
        iactiva,
        tipoinv,
        sector,
        i_open,
        mktvalue,
        dgyp,
        tasa_cambio,
        nivelIA,
        region,
        country,
        divisa,
        sectype,
    ):
        try:
            position = {
                "ticket": ticket,
                "conid": conid,
                "useraccount": useraccount,
                "estrategia": estrategia,
                "empresa": empresa,
                "peso": float(peso),
                "mrkprice": float(mrkprice),
                "open": float(i_open),
                "costobase": float(costobase),
                "position": float(position),
                "unrealizedpnl": float(unrealizedpnl),
                "dividendo": float(dividendo),
                "dividendYield": float(dividendyield),
                "exDividendDate": exdividend,
                "objetivo": float(objetivo),
                "deuda": float(deuda),
                "retorno": float(retorno),
                "fealta": fealta,
                "febaja": febaja,
                "iactiva": iactiva,
                "tipoinv": tipoinv,
                "sector": sector,
                "dgyp": dgyp,
                "mktvalue": mktvalue,
                "factor_cambio": tasa_cambio,
                "nivelIA": nivelIA,
                "region": region,
                "country": country,
                "divisa": divisa,
                "sectype": sectype,
            }
            self.positions.append(position)
        except Exception as e:
            print("[add_position()]: {}".format(e))

    # datos yfinance y otros para los activos de portafolio compartido entre clases
    def ts_yfinance_symbol(self, symbol, vehiculo=None):
        def get_datos(symbol, vehiculo=None, datos=None):
            try:

                indicadores, info_lotsize = {}, {}
                if not datos.empty:
                    indicadores = get_indicadores(symbol=symbol, datos=datos)

                if vehiculo == "Crypto":
                    response = self.BClient.get_exchange_info(symbol=symbol)
                    if response:
                        info_lotsize = response.get(symbol, {})
            except Exception as e:
                print("[ts_yfinance_symbol.get_datos()]: {}".format(e), symbol)

            return indicadores, info_lotsize

        try:
            result = get_yfinance(ticket=symbol, vehiculo=vehiculo)
            if result is None:
                return {}, pd.DataFrame(), False

            (activos, datos) = result

            # Crear clave de cache
            key_cache = (symbol, vehiculo)

            # recupera ts para el symbol si existe y not None [activos, datos, update]
            if symbol in self.info.keys():
                if "activos" in self.info[symbol]:
                    if self.info[symbol]["activos"] is not None:
                        activos = self.info[symbol].get("activos", {})
                        lotSize = self.info[symbol].get("lotSize", {})
                        # datos = self.info[symbol].get("datos", pd.DataFrame())
                        update = self.info[symbol]["update"]
                else:

                    # si no tiene activos, datos o update, lo reconstruye
                    indicadores, lotSize = get_datos(symbol=symbol, vehiculo=vehiculo, datos=datos)

                    update = False
                    with DataHub.lockInfo:
                        self.info.update(
                            {
                                symbol: {
                                    "activos": activos,  # almacena yf.Ticker.info()
                                    "datos": lambda: CacheHut.get(key_cache),
                                    "lotSize": lotSize,  # almacena minQty y stepSize
                                    "datos_tecnicos": indicadores,  # almacena datos técnicos
                                    "update": update,
                                }
                            }
                        )  # True: si contiene dividends

                return activos, datos, update

            # crea ts para el symbol si no existe o es None [activos, datos, update]
            elif symbol not in self.info.keys():

                # reconstruye datos del symbol
                indicadores, lotSize = get_datos(symbol=symbol, vehiculo=vehiculo, datos=datos)

                update = False
                with DataHub.lockInfo:
                    self.info.update(
                        {
                            symbol: {
                                "activos": activos,  # almacena yf.Ticker.info()
                                "datos": lambda: CacheHut.get(key_cache),
                                "lotSize": lotSize,  # almacena minQty y stepSize
                                "datos_tecnicos": indicadores,  # almacena datos técnicos
                                "update": update,
                            }
                        }
                    )  # True: si contiene dividends update = False

                return activos, datos, update
        except Exception as e:
            print("[ts_yfinance_symbol()]: {}".format(e), symbol)
            return {}, pd.DataFrame(), False

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

    # define estrategia por dividendos
    def rendimiento_dividends(self, fg=None, activo=None, datos=None, symbol=None, plot="no", period="5y"):
        """
        Calcula el rendimiento histórico de dividendos y genera estrategia de inversión.

        Este método analiza el historial de dividendos de un activo, calcula rendimientos
        anuales (dividendo/precio), y determina si es momento de compra, venta o mantener
        basándose en la comparación del rendimiento forward vs. rendimiento promedio histórico.

        Args:
            fg: Figure object de matplotlib para graficar (opcional)
            activo: Objeto yf.Ticker o dict con información del activo (opcional).
                   Si es None, se obtiene automáticamente usando ts_yfinance_symbol()
            datos: DataFrame con datos históricos del activo incluyendo columna 'Dividends' (opcional).
                   Si es None, se obtiene automáticamente
            symbol (str): Símbolo del activo a analizar (ej: "AAPL", "O", "PFE"). Requerido.
            plot (str): "yes" para generar gráfico de rendimientos, "no" para omitir. Default: "no"
            period (str): Período histórico para análisis (no utilizado actualmente). Default: "5y"

        Returns:
            tuple: (y_datos, value, meses) donde:
                - y_datos (pd.DataFrame): DataFrame con datos anuales conteniendo:
                    * 'Close': Precio promedio anual
                    * 'Dividends': Suma de dividendos pagados en el año
                    * 'Rendimiento': Rendimiento anual (Dividends/Close)
                - value (str): Estrategia de inversión:
                    * "I" = Inversión/Compra (forward yield > promedio histórico)
                    * "S" = Sell/Venta (forward yield < promedio histórico)
                    * "N" = Neutral (forward yield = promedio histórico)
                    * "E" = Error (sin datos válidos)
                - meses (list): Lista con nombres de meses en que se pagan dividendos
                                (ej: ["March", "June", "September", "December"])

        Raises:
            ValueError: Si el símbolo no contiene información de dividendos en datos['Dividends']
            Exception: Errores generales capturados y mostrados con print

        Lógica del método:
            1. Obtiene información del activo desde yfinance si no se provee
            2. Extrae trailingAnnualDividendRate (TTM), dividendRate y shortName
            3. VALIDACIÓN: Si trailingAnnualDividendRate = 0 → OMITIR (no paga dividendos)
            4. Filtra datos históricos para obtener solo pagos de dividendos (Dividends != 0)
            5. Identifica meses de pago analizando el año anterior
            6. Calcula rendimiento mensual: Dividends / Close (PAGOS REALES del extracto)
            7. Agrupa datos por año (resample YE) para obtener:
               - Precio promedio anual
               - Suma de dividendos anuales (HISTÓRICO - NO se modifica)
               - Rendimiento anual total
            8. Calcula rendimiento forward usando trailingAnnualDividendRate y precio actual
               (ESTIMADO basado en TTM de últimos 12 meses)
            9. Compara forward yield vs. promedio histórico para generar señal de trading
            10. Opcionalmente genera gráfico mostrando zonas de compra/venta

        Notas importantes:
            - ALINEADO con validaciones de DashMainV9_ia.py
            - Usa trailingAnnualDividendRate (TTM) para rendimiento forward (NO dividendRate)
            - Solo procesa activos con trailingAnnualDividendRate > 0 (omite activos sin dividendos)
            - Lo PAGADO viene del historial (extracto) y NO se modifica
            - Lo ESTIMADO (forward yield) se calcula: trailingAnnualDividendRate / precio_actual
            - Los datos se agrupan por año fiscal (YE = Year End)
            - El método asume que datos contiene columnas: 'Close' y 'Dividends'
            - Si no hay dividendos en el año anterior, intenta usar exDividendDate

        Ejemplo de uso:
            >>> customer = Class_customer(...)
            >>> y_datos, strategy, payment_months = customer.rendimiento_dividends(
            ...     symbol="O",  # Realty Income Corp
            ...     plot="yes"
            ... )
            >>> print(f"Estrategia: {strategy}")
            >>> print(f"Meses de pago: {payment_months}")
            >>> print(y_datos.tail())
        """
        try:
            y_datos, value, meses = pd.DataFrame(), "E", []
            if not (symbol is None):
                if activo is None:
                    (activo, datos, ind_update) = self.ts_yfinance_symbol(symbol=symbol, vehiculo=self.vehiculo)

                if isinstance(activo, yf.Ticker):
                    empresa = activo.info["shortName"]
                    # ALINEACIÓN: Usar trailingAnnualDividendRate (TTM) en lugar de dividendRate
                    # trailingAnnualDividendRate = suma de dividendos pagados en últimos 12 meses
                    trailing_annual = (
                        activo.info["trailingAnnualDividendRate"] if "trailingAnnualDividendRate" in activo.info else 0
                    )
                    dividend_rate = activo.info["dividendRate"] if "dividendRate" in activo.info else 0
                else:
                    # pasa por aca cuando carga los activos en ts_yfinance_symbol()
                    empresa = activo["shortName"] if "shortName" in activo else symbol
                    trailing_annual = (
                        activo["trailingAnnualDividendRate"] if "trailingAnnualDividendRate" in activo else 0
                    )
                    dividend_rate = activo["dividendRate"] if "dividendRate" in activo else 0

                # ============================================================================
                # VALIDACIÓN: No listar símbolos que no reportan dividendos
                # Si trailingAnnualDividendRate = 0 → el activo NO paga dividendos → SKIP
                # ============================================================================
                if trailing_annual == 0:
                    return pd.DataFrame(), "X", []  # Retornar vacío

                if "Dividends" not in datos:
                    raise ValueError("El symbol (" + symbol + ") No se construyo info() 'Dividends'")

                elif "Dividends" in datos:
                    m_div = datos[datos["Dividends"] != 0]
                    m_index = m_div.index

                    # entrega meses de pago de dividends
                    year = pd.Timestamp.now().year - 1
                    anual = m_div[m_div.index.year == year]
                    meses = list(anual.index.strftime("%B"))
                    if not meses:
                        if "exDividendDate" in activo:
                            exdiv = datetime.fromtimestamp(activo["exDividendDate"])
                            meses = [exdiv.strftime("%B")]

                    if not m_div.empty:

                        # llamado necesario para obtener close['Close']
                        pd.options.mode.copy_on_write = True
                        x_none, pdatos = get_yfinance(ticket=symbol, vehiculo="hist")

                        # datos.insert(datos.shape[1], 'Close', 0)
                        datos.index = datos.index.tz_localize(None)
                        d_index = datos.index

                        # filtra los meses de pago de dividendos y calcula su rendimiento
                        m_datos = datos[datos["Dividends"] != 0]
                        m_datos["Rendimiento"] = m_datos["Dividends"] / m_datos["Close"]
                        m_index = m_datos.index

                        # replantea el dividendo anual y su rendimiento
                        y_datos = pd.DataFrame(columns=["Close", "Dividends", "Rendimiento"])
                        y_datos["Close"] = m_datos["Close"].resample("YE").mean()
                        y_datos["Dividends"] = m_datos["Dividends"].resample("YE").sum()
                        y_datos["Rendimiento"] = m_datos["Rendimiento"].resample("YE").sum()

                        y_index = y_datos.index
                        if len(d_index) > 0:
                            # ============================================================================
                            # ALINEACIÓN: Recalcular rendimiento estimado (forward) usando TTM
                            # - Lo PAGADO viene del extracto (historial) → NO cambia
                            # - Lo ESTIMADO se calcula con trailingAnnualDividendRate (últimos 12 meses)
                            # - Solo se recalcula si trailingAnnualDividendRate > 0 (ya validado arriba)
                            # ============================================================================

                            # Calcular rendimiento forward usando TTM (trailing annual)
                            # TTM refleja lo que REALMENTE pagó en últimos 12 meses
                            current_price = datos.loc[d_index[-1], "Close"]

                            # Rendimiento forward = TTM dividendos / precio actual
                            # Esto da el rendimiento anualizado basado en pagos reales recientes
                            forward_yield_calculated = trailing_annual / current_price

                            # Actualizar último año (año en curso) con rendimiento forward
                            y_datos.loc[y_index[-1], "Rendimiento"] = forward_yield_calculated
                            y_datos.loc[y_index[-1], "Close"] = current_price

                            # NOTA: También podríamos actualizar el dividendo proyectado del año actual
                            # pero mantenemos solo el histórico. El forward solo sirve para comparar yields.
                            # y_datos.loc[y_index[-1], "Dividends"] = trailing_annual  # Opcional

                            forward_yield = forward_yield_calculated

                            # se maneja el plot del gráfico
                            if plot == "yes":
                                dlabl = {
                                    "symbol": symbol,
                                    "buy": "Zona buy",
                                    "sell": "Zona sell",
                                    "legend": "outside upper left",
                                }
                                asset = {
                                    "ticket": symbol,
                                    "forward": forward_yield,
                                    "name": empresa,
                                    "aspect": 0.25,
                                }
                                chart_rendimiento_dividendos(
                                    fg=fg,
                                    datos=y_datos,
                                    dlabl=dlabl,
                                    asset=asset,
                                    cchart=self.cchart,
                                )

                            m = y_datos.describe()["Rendimiento"]["mean"]
                            i = y_datos[y_datos["Rendimiento"] > m]["Rendimiento"].mean()
                            s = y_datos[y_datos["Rendimiento"] < m]["Rendimiento"].mean()

                            dforward = y_datos.loc[y_index[-1], "Rendimiento"]
                            value = ("I" if dforward > m else "S" if dforward < m else "N",)

                return y_datos, value, meses
        except Exception as e:
            print("[rendimiento_dividends()]: {}".format(e))

    def crypto_wallet_free(self, symbol=None, wallet="spot", SetLotSize=False):
        """
        Objetive: obtiene los asset desde la api account_spot y get_Account_margint.
        return:
        1: where symbol != 'all' & SetLotSize = False retrun cantidad free
        2: where symbol != 'all' & SetLotSize = True retrun lotSize
        3: Where symbol == 'all' return dict {symbol, {free, locked,borrowed}}
        """
        try:
            cantidad, SWallet = 0.0, {}
            response = self.BClient.account_spot()
            if response:
                if symbol != "all":
                    ticket = symbol.replace("USDT", "")
                    ticket = "LD" + ticket if wallet == "earn" else ticket

                    for keys in response["balances"]:
                        if float(keys["free"]) > 0 and keys["asset"] == ticket:

                            # si Sell busca lotSize
                            if SetLotSize:
                                if "lotSize" in self.info[symbol]["lotSize"]:
                                    stepSize = self.info[symbol]["lotSize"]["stepSize"]
                                    Exp = calculate_decimal_places(stepSize)
                                    cantidad = math.trunc(float(keys["free"] * 10**Exp)) / (10**Exp)
                                else:
                                    cantidad = float(keys["free"])
                            break
                    return cantidad

                # retorna dict asset account spot
                elif symbol == "all":
                    for keys in response["balances"]:
                        if "USDT" == keys["asset"]:
                            SWallet.update(
                                {
                                    keys["asset"]: {
                                        "free": float(keys["free"]),
                                        "locked": float(keys["locked"]),
                                        "borrowed": 0.0,
                                    }
                                }
                            )

                        elif float(keys["free"]) > 0 or float(keys["locked"]) > 0:
                            SWallet.update(
                                {
                                    keys["asset"]: {
                                        "free": float(keys["free"]),
                                        "locked": float(keys["locked"]),
                                        "borrowed": 0.0,
                                    }
                                }
                            )

                    # update dict asset account margin
                    margin = self.BClient.get_account_margin()
                    if margin:
                        for keys in margin["userAssets"]:

                            symbol = keys["asset"]
                            borrowed = float(keys["borrowed"])
                            locked = float(keys["locked"])
                            free = float(keys["free"])

                            if borrowed != 0.0 or free != 0.0 or locked != 0.0:
                                if symbol == "USDT":
                                    borrowed += SWallet[symbol].get("borrewed", 0)
                                    locked += SWallet[symbol].get("locked", 0)
                                    free += SWallet[symbol].get("free", 0)

                                    SWallet[symbol] = {
                                        "free": free,
                                        "locked": locked,
                                        "borrowed": borrowed,
                                    }

                                # cuadno no exista agrega el asset
                                elif symbol not in SWallet:
                                    asset = "MC" + symbol
                                    SWallet.update(
                                        {
                                            asset: {
                                                "free": free,
                                                "locked": locked,
                                                "borrowed": borrowed,
                                            }
                                        }
                                    )

                    return SWallet
        except Exception as e:
            print("[crypto_wallet_free()]: {}")

    # rescata de wallet EARN la cantidad indicada
    def crypto_earn_rescate(self, symbol=None, amount=0):
        try:
            response = self.BClient.get_redeem_flexible_product(productId=symbol, amount=amount, recvWindow=5000)
            if response:
                if "success" in response.keys():
                    if not response["success"]:
                        ticket = "LD" + symbol.replace("001", "")
                        disponible = self.crypto_wallert_free(self, Symbol=ticket, wallet="earn")
                        message = "La disponibilidad para rescatar {} en earn es de {:>,.5f}".format(ticket, disponible)

                        self.messagebox.showinfo(title="Alerta", message=message)
            return
        except Exception as e:
            print(f"crypto_earn_rescate(): {e}")

    # lista los activos del vehículo, si es Stock devuelve los keys de assets
    def list_activos_vehiculo(self):
        l_activos = []

        if self.vehiculo == "Stock":
            l_activos = [keys["symbol"] for keys in self.assets.values()]

        if self.vehiculo == "Crypto":
            l_activos = self.activos

        return l_activos

    # envía ordenes remotas desde DataHub QremoteOrder
    def schedule_order_remote(self):
        try:

            # contabiliza ejecución del schedule
            task = f"schedule_order_remote({self.vehiculo})"
            if self.schRemoteOrder_itera == 0:
                # print(f"{task} :: {datetime.now()}")
                self.procesos.append({"running": {task: 0}})

            self.schRemoteOrder_itera += 1
            DataHub.update_self_procesos(proces="running", tarea=task, itera=self.schRemoteOrder_itera)

            # si hay ordenes en QremoteOrder las procesa
            trama, future = DataHub.QremoteOrder[self.vehiculo].get_next_order()
            if trama is not None:

                # extrae datos de la trama Dashbot
                pedido = trama.get("pedido")
                vehiculo = trama.get("vehiculo")
                symbol = trama.get("symbol")
                account = trama.get("account")
                hash_id = trama.get("hash_id_Op")

                if vehiculo == "Stock":

                    response = self.put_completa_orden(
                        account=account,
                        vehiculo=vehiculo,
                        symbol=symbol,
                        pedido=pedido,
                        hash_id_Op=hash_id,
                        remote=True,
                    )

                    # arma respuesta compuesta para el bot
                    resp = {
                        "values": response,
                        "status": response.get("status", "No Submit"),
                    }

                    # libera recursos y entrega response
                    DataHub.QremoteOrder[self.vehiculo]._complete(future, resp)

                elif vehiculo == "Crypto":
                    response = self.put_completa_orden(
                        account=account,
                        vehiculo=vehiculo,
                        symbol=symbol,
                        pedido=pedido,
                        hash_id_Op=hash_id,
                        remote=True,
                    )
                    resp = {
                        "values": response,
                        "status": response.get("status", "No Submit"),
                    }

                    # libera recursos y entrega response
                    DataHub.QremoteOrder[self.vehiculo]._complete(future, resp)
        except Exception as e:
            self.logger.error(f"schedule_order_remote({self.vehiculo}): {e}")
            traceback.print_exc()

    # trades del vehículo y procede con update booktrading e inversión
    def schedule_diario(self):
        try:
            _FILE = "agents_schedule.json"
            _KEY = f"diaria_{self.vehiculo}"
            ultimo_cierre = get_ultimo_dia_mercado(market=self.vehiculo)
            if ultimo_cierre is None:
                return
            last_processed = read_json_tmp(_FILE).get(_KEY)
            if last_processed:
                last_processed = datetime.strptime(last_processed, "%Y-%m-%d").date()

            if ultimo_cierre == last_processed:
                return

            t_wait, update = DataHub.last_process[self.vehiculo], False
            update = diaria_book_performance(account=self.account, vehiculo=self.vehiculo, proces=t_wait)

            if update:
                data = read_json_tmp(_FILE)
                data[_KEY] = ultimo_cierre.strftime("%Y-%m-%d")
                write_json_tmp(_FILE, data)
                DataHub.last_process["graph_performace_portafolio"] = False
                proceso_update_performance(account=self.account, vehiculo=self.vehiculo)

            # contabiliza ejecución del schedule
            task = f"schedule_diario({self.vehiculo})"

            if self.schDiario_itera == 0:
                # print(f"{task} :: {datetime.now()}")
                self.procesos.append({"running": {task: 0}})

            self.schDiario_itera += 1
            DataHub.update_self_procesos(proces="running", tarea=task, itera=self.schDiario_itera)
        except Exception as e:
            print("[schedule_diario()]: {}".format(e))

    # programa las actualizaciones de API's cada minuto
    def schedule_operativo(self):
        try:
            # revisa y update inversiones vehículos
            self.conector_api_vehiclo()

            # obtiene lista de activos
            activos = self.list_activos_vehiculo()

            # update de dividends en tabla market aplica solo para Stock
            wait = DataHub.last_process["dividends_en_market_stock"]
            if wait < datetime.now():

                # Versión con yfinance (para comparar con IB)
                self.dividends_en_market_stock(activos)
                DataHub.last_process["dividends_en_market_stock"] = datetime.now() + timedelta(minutes=5)

            # contabiliza ejecución del schedule
            task = f"schedule_operativo({self.vehiculo})"

            if self.schOperativo_itera == 0:
                # print(f"{task} :: {datetime.now()}")
                self.procesos.append({"running": {task: 0}})

            self.schOperativo_itera += 1
            DataHub.update_self_procesos(proces="running", tarea=task, itera=self.schOperativo_itera)

            # revisa update trader vehículos
            # self.trader_api_vehiculo()
        except Exception as e:
            print("[schedule_operativo()]: {}".format(e))

        # programa las actualizaciones de API's cada minuto

    def schedule_trader(self):
        try:
            # revisa update trader vehículos
            self.trader_api_vehiculo()

            # contabiliza ejecución del schedule
            task = f"schedule_trader({self.vehiculo})"

            if self.schTrader_itera == 0:
                # print(f"{task} :: {datetime.now()}")
                self.procesos.append({"running": {task: 0}})

            self.schTrader_itera += 1
            DataHub.update_self_procesos(proces="running", tarea=task, itera=self.schTrader_itera)
        except Exception as e:
            print("[schedule_operativo()]: {}".format(e))

    # recorre booktrading o positions para ubicar que vender o que comprar
    def schedule_oportunidades(self):
        try:
            self.oportunidades_sell()

            # Ejecutar motor de rebalanceo
            self.ejecutar_rebalanceo()

            self.oportunidades_buy()

            # exporta oportunidades al agente IA
            DataHub.csv_OptionSales_write()
            DataHub.csv_OptionBuy_write()

            # contabiliza ejecución del schedule
            task = f"schedule_oportunidades({self.vehiculo})"

            if self.schOportunidades == 0:
                # print(f"{task} :: {datetime.now()}")
                self.procesos.append({"running": {task: 0}})

            self.schOportunidades += 1
            DataHub.update_self_procesos(proces="running", tarea=task, itera=self.schOportunidades)
        except schedule.ScheduleError as e:
            print("[schedule_oportunidades()]: {}".format(e))

    def ejecutar_rebalanceo(self):
        """
        Ejecuta el motor de rebalanceo y almacena resultados en DataHub.
        Genera ranking de activos priorizados y asignaciones de presupuesto.

        Solo se ejecuta si manager_buysell ya está poblado por graficos_main().
        """
        try:
            # Validar que manager_buysell esté disponible
            if not hasattr(DataHub, "manager_buysell") or not DataHub.manager_buysell:
                return

            # Validar que las dimensiones tengan datos antes de ejecutar
            dimensiones_requeridas = ["dividends", "sector", "activos", "region"]
            dimensiones_validas = []

            for dim in dimensiones_requeridas:
                data = DataHub.manager_buysell.get(dim)
                if data and isinstance(data, dict):
                    # Verificar que tenga la estructura mínima necesaria
                    # Usar 'in' en lugar de boolean OR para evitar ambiguedad con DataFrames
                    if "data" in data or "total_valor_market" in data:
                        dimensiones_validas.append(dim)

            # Si no hay ninguna dimensión válida, no ejecutar
            if not dimensiones_validas:
                return

            # Inicializar motor pasando el vehículo de esta instancia
            engine = RebalanceEngine(DataHub, vehiculo=self.vehiculo)

            # Ejecutar ranking
            ranking = engine.rank()

            # Generar asignaciones de presupuesto
            asignaciones = engine.budget_allocator(min_ticket=100.0)

            # Almacenar resultados en DataHub para visualización
            if not hasattr(DataHub, "rebalanceo"):
                DataHub.rebalanceo = {}

            # Verificar si hay cambios respecto a la ejecución anterior
            datos_previos = DataHub.rebalanceo.get(self.vehiculo)
            hay_cambios = True

            if datos_previos:
                # Comparar si hay cambios significativos
                gaps_previos = datos_previos.get("gaps", {})
                asignaciones_previas = datos_previos.get("asignaciones", [])

                # Considerar que hay cambio si gaps o número de asignaciones cambió
                if gaps_previos == engine.gaps and len(asignaciones_previas) == len(asignaciones):
                    hay_cambios = False

            if hay_cambios:
                DataHub.rebalanceo[self.vehiculo] = {
                    "timestamp": datetime.now(),
                    "vehiculo": self.vehiculo,
                    "gaps": engine.gaps,
                    "normalized_gaps": engine.normalized_gaps,
                    "dimension_priority": engine.dimension_priority,
                    "ranking": ranking[:10],  # Top 10
                    "asignaciones": asignaciones,
                    "total_sugerido": sum(a["monto_sugerido"] for a in asignaciones),
                }

        except Exception as e:
            print(f"[ejecutar_rebalanceo()]: {e}")
            traceback.print_exc()

    # invoca price websocket y suscribe symbols
    def schedule_WebsocketBinanceStream(self, limit=90, log=True):
        if self.WStreams:
            self.WStreams.stop()

        self.WStreams = BinanceStreamClient(
            env="PRODUCTION",
            assets=self.activos,
            mensaje_callback=self.on_message_binance_websocket,
        )
        if log and (self.WStreams.counter == 1):
            self.logger.warning(f"schedule_WebsocketBinanceStream:: symbols({len(self.activos)}),{datetime.now()}")

        self.WStreams.websocket_loop(limit=limit, log=False)

    # invoca allOrders websocket
    def schedule_WebsocketBinanceApiClient(self, limit=90, log=True):
        if self.WsClient:
            self.WsClient.stop()

        self.WsClient = BinanceWSApiClient(
            env="PRODUCTION",
            vehiculo="Crypto",
            mensaje_callback=self.on_message_binance_websocket,
        )
        if log and (self.WsClient.counter == 1):
            self.logger.warning(f"schedule_WebsocketBinanceApiClient:: symbols({len(self.activos)}),{datetime.now()}")

        self.WsClient.my_allOrders(assets=self.activos, limit=10, sleep=1)
        self.WsClient.counter = 1

    # =========================================================================================
    # Bloque para manejar Sell y Bull de activos
    # =========================================================================================
    def ts_oportunidades_symbol(self, symbol, datos=None):
        """almacena en ts_yfinance_symbol information de buy y sell"""
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
        except Exception as e:
            print("[ts_oportunidades_symbol()]: {}".format(e))

    def _get_estrategia_descripcion(self, codigo_estrategia):
        """Convierte código de estrategia (P01, P02, P03, C01, etc.) a su descripción para el rebalanceo."""
        if not codigo_estrategia:
            return None

        # Obtener mapeo código→descripción si no está cacheado
        if not hasattr(self, "_estrategia_map") or not self._estrategia_map:
            self._estrategia_map = {}
            # Cargar estrategias de todos los vehículos relevantes
            for vehiculo in ["Balance", "Crypto"]:
                result = EstrategiaInversion().select(accion="vehiculo", ivehiculo=vehiculo)
                if result:
                    for row in result:
                        codigo = row.get("estrategia")
                        descripcion = row.get("descripcion")
                        if codigo and descripcion:
                            self._estrategia_map[codigo] = descripcion

        # Retornar descripción si existe, sino el código original
        return self._estrategia_map.get(codigo_estrategia, codigo_estrategia)

    # recorre positions para actualizar oportunidades Sell general"""
    def oportunidades_sell(self):
        def obtiene_lotes(symbol=None, divisa="USD"):
            nonlocal datos
            try:

                profit, costCum, lotes, sell, datos = 0.0, 0.0, 0.0, 0.0, {}

                last = position["mrkprice"]
                l_gain = DataHub.get_lotesGainLost(
                    opcion="gain", account=self.account, symbol=symbol, divisa=divisa, last=last
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
                            "divisa": position["divisa"],
                            "factor": position["factor_cambio"],
                        }
                    }
                return datos
            except Exception as error:
                print("[obtiene_lotes()]: {}".format(error))

        try:
            for position in self.positions:
                symbol = position["ticket"]
                datos = obtiene_lotes(symbol=symbol, divisa=position["divisa"])

                # actualiza metadata del activo para el rebalanceo
                if symbol in self.info:
                    self.info[symbol]["sector"] = position.get("sector")
                    self.info[symbol]["region"] = position.get("region")
                    self.info[symbol]["costobase"] = position.get("costobase", 0)
                    # Convertir código de estrategia a descripción para que coincida con grupo_activos()
                    self.info[symbol]["asset_type"] = self._get_estrategia_descripcion(position.get("estrategia"))

                # actualiza en diccionario self.info()
                (d_buy, d_sell) = self.ts_oportunidades_symbol(symbol, datos)
        except Exception as e:
            print("[oportunidades_sell()]: {}".format(e))

    # recorre positions para actualizar oportunidades buy general"""
    def oportunidades_buy(self):
        try:
            invertir = self.sesion["Pinvertir"]
            for position in self.positions:
                symbol = position["ticket"]

                if (position["mrkprice"] > 0.000001) and (invertir > 0) and (position["position"] > 0):
                    stock = int(invertir / position["mrkprice"])
                    stockNew = stock + position["position"]
                    avgCost = position["costobase"] / position["position"]

                    # Solo usar dividendo si dividendYield > 0 (activo paga dividendos actualmente)
                    if position["dividendYield"] > 0 and position["dividendo"] > 0:
                        dividendo = position["dividendo"] / position["position"]
                    else:
                        dividendo = 0
                    gypInicial = (position["objetivo"] - avgCost + dividendo) * position["position"]
                    precioNew = (position["costobase"] + stock * position["mrkprice"] + 0.4) / stockNew

                    gypPrecio = (precioNew - avgCost) / avgCost if avgCost > 0 else 0
                    gypProyect = (position["objetivo"] - precioNew + dividendo) * stockNew
                    gainInversion = (gypProyect - gypInicial) / invertir

                    # ajusta calculo de la tasa nominal
                    if self.vehiculo == "Stock":
                        tasa_nominal = position["dividendYield"] / 100
                    else:
                        tasa_nominal = position["dividendo"] / position["costobase"]

                    ex_dividends = (
                        position["exDividendDate"].strftime("%d-%b'%y") if position["exDividendDate"] else "N/A"
                    )

                    datos = {}
                    if (gypPrecio < self.sesion["gypPrecio"]) and (gainInversion < self.sesion["gainInversion"]):
                        # Clasificar como "dividends" solo si dividendYield > 0
                        BuyDividends = "buy" if position["dividendYield"] <= 0 else "dividends"
                        datos = {
                            BuyDividends: {
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
                                "exDividendDate": ex_dividends,
                                "pre dividendos": position["dividendo"] if position["dividendYield"] > 0 else 0,
                                "post dividendos": dividendo * stockNew,
                                "pre costobase": position["costobase"],
                                "post costobase": precioNew * stockNew,
                            }
                        }

                    # actualiza metadata del activo para el rebalanceo
                    if symbol in self.info:
                        self.info[symbol]["sector"] = position.get("sector")
                        self.info[symbol]["region"] = position.get("region")
                        self.info[symbol]["costobase"] = position.get("costobase", 0)
                        # Convertir código de estrategia a descripción para que coincida con grupo_activos()
                        self.info[symbol]["asset_type"] = self._get_estrategia_descripcion(position.get("estrategia"))

                    # actualiza en diccionario self.info()
                    (d_buy, d_dividend) = self.ts_oportunidades_symbol(symbol, datos)
        except Exception as e:
            print("[oportunidades_buy()]: {}".format(e))


# class para visualizar del vehiculo
class WidgetVehiculo(TickerInfo):
    def __init__(self, master, account, vehiculo):
        TickerInfo.__init__(self, account=account, vehiculo=vehiculo)  # Inicializa los atributos de TickerInfo
        self.master = master

        self.index = {
            "Ticket": "ticket",
            "dGyP": "dgyp",
            "Posición": "position",
            "mktPrice": "mrkprice",
            "AvgCost": "deuda",
            "costo_base": "costobase",
            "ValueMkt": "unrealizedpnl",
            "GyP": "unrealizedpnl",
            "%ROI": "retorno",
            "Objetivo": "objetivo",
            "Dividendos": "dividendo",
        }
        self.heading = list(self.index.keys())
        self.ncolumns = len(self.heading)
        self.height = 17
        self.colors = DataHub.colors

        # enlace con DatosVehiculo
        self.cg = 120

        # widgets de OrderActivas
        self.orderActivas = None
        self.bid = None
        self.ask = None
        self.available = None

        win0 = ttk.Frame(master, padding=(0, 5, 0, 0), style="C.TFrame")  # header
        win0.pack_propagate(False)

        win2 = ttk.Frame(master, width=980, height=400, padding=(0, 0, 0, 0))  # positions detalle
        win3 = ttk.Frame(master, padding=(0, 0, 0, 0))  # graficos verticales
        win4 = ttk.Frame(master, padding=(0, 0, 0, 0))  # graficos inferiores

        win0.grid(row=0, column=0)
        win2.grid(row=1, column=0)
        win3.grid(row=0, column=1, rowspan=3, pady=2)
        win4.grid(row=3, column=0, columnspan=2, pady=2)

        wi00 = ttk.Frame(win0, padding=(1, 1, 1, 1), style="C.TFrame")
        wi01 = ttk.Frame(win0, padding=(1, 1, 1, 1), style="C.TFrame")
        wi00.pack_propagate(False)
        wi01.pack_propagate(False)

        wi30 = ttk.Frame(win3, padding=(1, 3, 1, 2), style="C.TFrame")  # Imagen derecha superior
        wi31 = ttk.Frame(win3, padding=(1, 1, 1, 1), style="C.TFrame")  # Imagen derecha inferior
        wi40 = ttk.Frame(win4, padding=(1, 1, 1, 1), style="C.TFrame")  # imagen inferior izquierda
        wi41 = ttk.Frame(win4, padding=(1, 1, 1, 1), style="B.TFrame")  # Oportunidades inferior derecha

        wi00.grid(row=0, column=0)
        wi01.grid(row=0, column=1)
        wi30.pack(side=tk.TOP)
        wi31.pack(side=tk.BOTTOM)
        wi40.pack(side=tk.LEFT)
        wi41.pack(side=tk.RIGHT)

        # define columna header del panel ---------------------------------------------------------------------------
        self.set_header_panel()
        self.panel_label = []
        dgyp = self.resumen[" dgyp       :"]
        gbg = display_red_green(dgyp)
        for i, (key, value) in enumerate(self.resumen.items()):
            if i == 0:  # escribe dGyP
                t_dgyp = f"dGyP: {int(value):>6d}"
                self.panel_label.append(ttk.Label(wi00, text=t_dgyp, style=gbg, font=("Courier", 24, "bold")))

            if i > 0:
                self.panel_label.append(ttk.Label(wi01, text=key, style="C.TLabel", font=("Courier", 9)))
                self.panel_label.append(
                    tk.Label(
                        wi01,
                        text=value,
                        bg=self.colors["bgcolor"],
                        fg="black",
                        font=("Courier", 9),
                    )
                )

        self.panel_label[0].grid(column=0, row=0)
        self.panel_label[1].grid(column=0, row=0)
        self.panel_label[2].grid(column=1, row=0)
        self.panel_label[3].grid(column=2, row=0)
        self.panel_label[4].grid(column=3, row=0)
        self.panel_label[5].grid(column=4, row=0)
        self.panel_label[6].grid(column=5, row=0)
        self.panel_label[7].grid(column=6, row=0)
        self.panel_label[8].grid(column=7, row=0)

        self.panel_label[9].grid(column=0, row=1)
        self.panel_label[10].grid(column=1, row=1)
        self.panel_label[11].grid(column=2, row=1)
        self.panel_label[12].grid(column=3, row=1)
        self.panel_label[13].grid(column=4, row=1)
        self.panel_label[14].grid(column=5, row=1)
        self.panel_label[15].grid(column=6, row=1)
        self.panel_label[16].grid(column=7, row=1)

        # define lienzos para imagen de widget
        frame = [wi30, wi31, wi40]
        self.graph = []
        for i, win in enumerate(frame):
            if i in (0, 1):
                fg = Figure(figsize=(2.9, 1.96), dpi=110, layout="tight")
                fg.set_facecolor(self.colors["cgcolor"])
                cv = FigureCanvasTkAgg(fg, master=win)
                self.graph.append((cv, fg))
                self.graph[-1][0].draw()
                self.graph[-1][0].get_tk_widget().pack()

            if i in (2, 2):
                fg = Figure(figsize=(7.8, 2.3), dpi=110, layout="tight")
                fg.set_facecolor(self.colors["cgcolor"])
                cv = FigureCanvasTkAgg(fg, master=win)

                self.graph.append((cv, fg))
                self.graph[-1][0].draw()
                self.graph[-1][0].get_tk_widget().pack()

                # command=lambda: chart_setup('W', gtipo, 'p'))
                bt1 = tk.Button(
                    win,
                    text="1m",
                    width=2,
                    bg=self.colors["cgcolor"],
                    fg=self.colors["bgcolor"],
                    relief=tk.FLAT,
                    command=lambda: self.setup_graph_performace("1M"),
                )
                bt2 = tk.Button(
                    win,
                    text="3m",
                    width=2,
                    bg=self.colors["cgcolor"],
                    fg=self.colors["bgcolor"],
                    relief=tk.FLAT,
                    command=lambda: self.setup_graph_performace("3M"),
                )
                bt3 = tk.Button(
                    win,
                    text="6m",
                    width=2,
                    bg=self.colors["cgcolor"],
                    fg=self.colors["bgcolor"],
                    relief=tk.FLAT,
                    command=lambda: self.setup_graph_performace("6M"),
                )
                bt4 = tk.Button(
                    win,
                    text="1y",
                    width=2,
                    bg=self.colors["cgcolor"],
                    fg=self.colors["bgcolor"],
                    relief=tk.FLAT,
                    command=lambda: self.setup_graph_performace("1Y"),
                )
                bt5 = tk.Button(
                    win,
                    text="5y",
                    width=2,
                    bg=self.colors["cgcolor"],
                    fg=self.colors["bgcolor"],
                    relief=tk.FLAT,
                    command=lambda: self.setup_graph_performace("5Y"),
                )
                bt1.place(y=15, x=725)
                bt2.place(y=15, x=750)
                bt3.place(y=15, x=775)
                bt4.place(y=15, x=800)
                bt5.place(y=15, x=825)

        # información de sesión
        self.sesion = self.PlanInversion.get_sesion_by_vehiculo(self.vehiculo)

        # área de oportunidades y entrenamiento
        self.invertir = self.sesion["Pinvertir"]
        self.precio = 0.1
        self.texto = [
            "$ {:>11.0f},_en_ganancias_por_ ventas_de_{:>6.0f}_lotes_fiscales",
            "Sobre_{:>3.0f}_activos,_para_acumular_al_invertir_${}",
            "Agregar_{:>5.0f},_nuevos_activos_invertiendo_${}",
        ]

        # obtiene posible ganancia y lotes implicados
        self.op0 = tk.Label(
            wi41,
            text="Oportunidad de Operar",
            font=("Arial", 13),
            bg=self.colors["cgcolor"],
            fg="cyan",
        )
        self.op1 = tk.Button(
            wi41,
            text=self.texto[0].format(0, 0),
            width=24,
            bg="blue",
            fg="white",
            wraplength=170,
            justify="left",
            command=lambda: self.oportunidad_gain_capital(),
        )
        self.op2 = tk.Button(
            wi41,
            text=self.texto[1].format(30, 300),
            width=24,
            bg="OrangeRed",
            fg="white",
            wraplength=170,
            justify="left",
            command=lambda: self.oportunidad_mejorar_buyDividends(),
        )
        self.op3 = tk.Button(
            wi41,
            text=self.texto[2].format(0, 300),
            width=24,
            bg="orange",
            fg="white",
            wraplength=170,
            justify="left",
        )

        self.op1.grid(row=1, column=0, padx=15, pady=7)
        self.op2.grid(row=2, column=0, padx=15, pady=7)
        self.op3.grid(row=1, column=1, padx=15, pady=7)
        self.op0.grid(row=0, column=0, pady=0, columnspan=3)

        # Opción de compra de símbolo nuevo (solo si id_transaccion está activo) ---------------------------------------
        btn_state = tk.NORMAL if self.sesion.get("id_transaccion", False) else tk.DISABLED
        entry_state = tk.NORMAL if self.sesion.get("id_transaccion", False) else tk.DISABLED

        frame_buy_new = tk.Frame(wi41, bg=self.colors["bgcolor"], width=175, height=40)
        frame_buy_new.grid(row=2, column=1, padx=15, pady=7)
        frame_buy_new.pack_propagate(False)

        self.entry_new_symbol = tk.Entry(frame_buy_new, width=14, state=entry_state, font=("Arial", 8))
        self.entry_new_symbol.pack(side=tk.LEFT, padx=5, pady=10)

        self.btn_buy_new = tk.Button(
            frame_buy_new,
            text="BUY",
            width=8,
            bg="blue",
            fg="white",
            state=btn_state,
            command=lambda: self.comprar_simbolo_nuevo(),
        )
        self.btn_buy_new.pack(side=tk.LEFT, padx=5)

        # Botón de Análisis por vehículo ------------------------------------------------------------------------------
        self.btn_analisis = tk.Button(
            wi41,
            text=f"ANÁLISIS de rendimiento: {self.vehiculo}",
            width=24,
            bg="purple",
            fg="white",
            wraplength=170,
            justify="left",
            font=("Arial", 9, "bold"),
            command=lambda: self.abrir_analisis_vehiculo(),
        )
        self.btn_analisis.grid(row=3, column=0, padx=15, pady=7)

        # crear treeview ----------------------------------------------------------------------------------------------
        top = tk.Frame(win2)
        bott = tk.Frame(win2)
        right = tk.Frame(win2)
        right.pack(side=tk.RIGHT, fill=tk.Y, expand=True)
        top.pack(side=tk.TOP, expand=True)
        bott.pack(side=tk.BOTTOM, expand=True)

        self.m_heard = self.create_treeviews(master=top, height=1, show="headings")
        self.m_tree = self.create_treeviews(master=bott, height=self.height, show="tree")

        self.positions = []
        self.select_activo = None

        # posiciona las columnas y método yview de cada Treeview, sincronice
        for i, tree in enumerate(self.m_tree):
            self.m_heard[i].pack(side=tk.LEFT)
            tree.pack(side=tk.LEFT)

            # controla movimiento de fuera de scroll
            if i == 0:
                self.m_heard[0].config()
                self.m_tree[0].bind("<MouseWheel>", self.on_mouse_wheel)

            # bloquea sensibilidad de mouse sobre el resto de las columnas
            elif i > 0:
                self.m_tree[i].bind("<MouseWheel>", self.disable_mousewheel)

        # Vincular los eventos de selección para mas detalle
        self.m_tree[0].bind("<<TreeviewSelect>>", self.on_treeview_select)

        # Vincula el evento a todas las columnas
        for tree in self.m_tree:
            tree.bind("<MouseWheel>", self.on_mouse_wheel)
            tree.bind("<Shift-MouseWheel>", self.on_mouse_wheel)

        # variable de window_estrategia() -----------------------------------------------------------------------------
        self.rns = None
        self.rnb = None
        self.symbol = None
        self.Ddatos = None
        self.bgcolor = DataHub.colors["bgcolor"]
        self.fgcolor = DataHub.colors["fgcolor"]
        self.cgcolor = DataHub.colors["cgcolor"]
        self.df = DataHub.colors["df"]
        self.max_dw = DataHub.colors["max_dw"]
        self.gchar = {
            "ticket": self.symbol,
            "gcolor": "black",
            "tcolor": "DarkCyan",
            "pcolor": "green",
            "ecolor": "white",
            "booktrading": pd.DataFrame(),
            "position": False,
            "objetivo": 0.0,
            "avgCost": 0.0,
            "account": 0,
            "mkPrice": 0.0,
            "periodo": "W",
            "secType": "Stock",
            "name": "buscar nombre",
            "tipo": "candle",
            "date": datetime.now(),
        }

        # Accesos MySql ----------------------------------------------------------------------------------------------
        self.Market = MarketScreen()
        self.RepositorioOportunidades = RepositorioOportunidadesBuySell()

    # crea las columnas de treeview multiple
    def create_treeviews(self, master=None, height=None, show=None):
        try:

            # construye columnas para mostrar positions
            treeviews = []
            for i, column in enumerate(self.heading):

                # construye cada columna del panel
                tree = ttk.Treeview(master, show=show, height=height, style="TFrame")
                tree["columns"] = (column,)
                titulo = column.replace("_", "")

                tree.heading("#0")
                tree.column("#0", width=0, minwidth=1)
                tree.heading(
                    column,
                    text=titulo,
                    anchor=tk.CENTER,
                    command=lambda c=column: self.on_heading_click(c),
                )

                # mayor amplitud para Ticket
                width = 90 if column == "Ticket" else 82
                tree.column(column, width=width, minwidth=width, anchor=tk.W)

                # controla el color de cada celda
                tree.tag_configure("even", background="black", foreground="white")
                tree.tag_configure("even_green", foreground="White", background="dark green")
                tree.tag_configure("even_red", foreground="White", background="firebrick4")
                tree.tag_configure("odd", background="Silver", foreground="black")
                tree.tag_configure("odd_green", foreground="black", background="green2")
                tree.tag_configure("odd_red", foreground="black", background="red3")

                treeviews.append(tree)

            return treeviews
        except Exception as e:
            print("[create_treeviews()]: {}".format(e))

    # Sincronizar el scroll vertical entre los dos Treeviews
    def on_sync_vertical_scroll(self, *args):
        for tree in self.m_tree:
            tree.yview(*args)

    def on_treeview_select(self, event):
        try:
            source_tree = event.widget
            item = source_tree.selection()

            # selecciona activos para más detalle en windows
            self.select_activo = self.m_tree[0].item(item, "values")
            if not (self.select_activo is None):
                symbol = self.select_activo[0].strip()

                # antes de invocar válida que este construida la self.ts_yfinance_symbol
                if symbol in self.info.keys():
                    self.symbol = symbol
                    self._on_symbol_menu(symbol, event)
                else:
                    print("[aun no ha cargado self.info()]:", symbol)
        except Exception as e:
            print("[on_treeview_select()]: {}".format(e))

    def _on_symbol_menu(self, symbol, event):
        """Muestra menú con opciones para el símbolo seleccionado."""
        menu = tk.Toplevel(self.master)
        menu.overrideredirect(True)  # sin borde de ventana
        menu.attributes("-topmost", True)

        bg = self.bgcolor
        fg = "#ffffff"
        btn_cfg = dict(
            bg=self.bgcolor,
            fg=fg,
            font=("Arial", 10),
            relief="flat",
            activebackground="#2a5298",
            activeforeground=fg,
            cursor="hand2",
            anchor="w",
            width=15,
            pady=2,
        )

        tk.Label(
            menu, text=f"  {symbol}", bg=self.bgcolor, fg=self.cgcolor, font=("Arial", 10, "bold"), anchor="w"
        ).pack(fill=tk.X)

        tk.Button(menu, text="Análisis", command=lambda: (menu.destroy(), self.window_estrategia()), **btn_cfg).pack(
            fill=tk.X, padx=1, pady=(0, 1)
        )

        tk.Button(
            menu, text="TradingView", command=lambda: (menu.destroy(), self._abrir_tradingview(symbol)), **btn_cfg
        ).pack(fill=tk.X, padx=1, pady=(0, 1))

        tk.Button(
            menu, text="Strategy", command=lambda: (menu.destroy(), self._abrir_grafico_estrategia(symbol)), **btn_cfg
        ).pack(fill=tk.X, padx=1, pady=(0, 1))

        # Posicionar junto al cursorcls
        x, y = pyautogui.position()
        x += event.x + 5
        y += event.y
        menu.geometry(f"+{x}+{y}")

        # Cerrar al perder foco
        menu.bind("<FocusOut>", lambda e: menu.destroy())
        menu.focus_set()

    def _abrir_tradingview(self, symbol):
        """Genera HTML con widget TradingView para el símbolo y lo abre en el browser."""
        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{symbol} - TradingView</title>
  <style>
    body {{ margin: 0; padding: 0; background: #131722; }}
    #tv_chart {{ width: 100vw; height: 100vh; }}
  </style>
</head>
<body>
  <div class="tradingview-widget-container" style="height:100vh; width:100vw;">
    <div id="tradingview_full" style="height:100%; width:100%;"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script type="text/javascript">
    new TradingView.widget({{
      "autosize": true,
      "symbol": "{symbol}",
      "interval": "D",
      "timezone": "Etc/UTC",
      "theme": "dark",
      "style": "1",
      "locale": "es",
      "toolbar_bg": "#131722",
      "enable_publishing": false,
      "hide_side_toolbar": false,
      "allow_symbol_change": true,
      "withdateranges": true,
      "save_image": true,
      "details": true,
      "studies": [
        "PUB;kPuoGBGx",
        "PUB;1aKxXAmg",
        "PUB;rMj56XfN"
      ],
      "container_id": "tradingview_full"
    }});
    </script>
  </div>
</body>
</html>"""
        tmp_dir = os.path.join(os.path.dirname(__file__), "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        html_path = os.path.join(tmp_dir, f"tv_{symbol}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open(f"file:///{html_path.replace(os.sep, '/')}")

    def _abrir_grafico_estrategia(self, symbol, Xposition=None):
        """Abre el gráfico de estrategia compartido para el símbolo seleccionado."""
        if not hasattr(self, "_chart_windows_estrategia"):
            self._chart_windows_estrategia = {}

        # Extraer targets desde DataHub si están disponibles
        targets = {}
        info = DataHub.info.get(symbol, {})
        ws = info.get("websocket", {})
        avgcost = ws.get("avgCost") or ws.get("avgcost")
        objetivo = ws.get("objetivo")
        if avgcost:
            try:
                targets["entry"] = float(avgcost)
            except Exception:
                pass
        if objetivo:
            try:
                targets["objetivo"] = float(objetivo)
            except Exception:
                pass

        show_strategy_chart(
            parent=self.master,
            symbol=symbol,
            vehiculo=self.vehiculo,
            targets=targets or None,
            chart_windows=self._chart_windows_estrategia,
            Xposition=Xposition,
            show_pm=True,
        )

    # Función para obtener columnas self.m_tree sincronizadamente
    def on_heading_click(self, column):
        try:
            tmp = []
            antes = self.orden[0]
            if column in antes.keys():
                como = "DES" if self.orden[1] == "ASC" else "ASC"
            else:
                como = "DES"

            field = self.index[column]

            tmp.append({column: field})
            tmp.append(como)
            self.orden = tmp.copy()

        except Exception as e:
            print("[on_heading_click()]: {}".format(e))

    # Función para ordenar por columnas self.m_tree sincronizadamente
    def on_sort_treeview(self, orden) -> list:
        try:

            positions = sort_positions(self.positions, orden)
            for index, position in enumerate(positions):
                data = self.struct_datos(position)
                for idx, tree in enumerate(self.m_tree):
                    items_id = self.m_tree[idx].get_children()
                    if index >= len(items_id):
                        continue

                    sty = self.create_styles(index, idx, data, "rows")
                    data_string = self.display_format(tipo="rows", data=data)
                    tree.item(items_id[index], values=(data_string[idx],), tags=(sty,))

            return positions
        except Exception as e:
            print("[on_sort_treeview()]: {}".format(e))
            traceback.print_exc()
            return []

    @staticmethod
    # Función para bloquear el scroll del mouse**
    def disable_mousewheel(event):
        return "break"  # Evita que el evento pase al Treeview

    # Conectar los eventos de movimiento del mouse
    def on_mouse_wheel(self, event):
        try:
            if event.state & 0x0001:  # Detecta si Shift está presionado (para scroll horizontal)
                for tree in self.m_tree:
                    tree.xview_scroll(-1 * (event.delta // 120), "units")
            else:  # Scroll vertical
                for tree in self.m_tree:
                    tree.yview_scroll(-1 * (event.delta // 120), "units")
            return "break"  # Evita que el evento se propague a otros widgets

        except Exception as e:
            print("[on_mouse_wheel()]: {}".format(e))

    # set valores del panel
    def set_header_panel(
        self,
        Dgyp=0,
        Nav=0,
        Unpyl=0,
        Unprofit=0,
        Per=0,
        Debit=0,
        Dividends=0,
        Margen=0,
        Cash=0,
        Sesion=None,
    ):
        try:
            # 1ra fila
            self.resumen[" dgyp       :"] = Dgyp
            self.resumen[" Valor liq. :"] = "{:>11.2f}".format(float(Nav))
            self.resumen[" Debit      :"] = "{:>11.2f}".format(float(Debit))
            self.resumen[" UnProfit   :"] = "{:>11.2f}".format(float(Unprofit))
            self.resumen[" UnPyl      :"] = "{:>11.2f}".format(float(Unpyl))

            # 2da fila
            self.resumen[" Dividendos :"] = "{:>11.2f}".format(float(Dividends))
            self.resumen[" % Margen   :"] = "{:>11.2f}".format(float(Margen))
            self.resumen[" Cash       :"] = "{:>11.2f}".format(float(Cash))
            if Sesion is None:
                self.resumen[" Prc/profit :"] = "{:>11.2f}".format(float(Per))
            else:
                if " Prc/profit :" in self.resumen.keys():
                    self.resumen.pop(" Prc/profit :")
                self.resumen[" Conexión   :"] = Sesion

            return
        except Exception as e:
            print("[set_header_panel()]: {}".format(e))

    # escribe información en cabecera del panel
    def header_panel(self):
        try:
            # rescribe resumen en panel - parte superior
            if self.resumen:
                dgyp = self.resumen[" dgyp       :"] if " dgyp       :" in self.resumen else 0
                gbg = display_red_green(dgyp)
                for i, (key, value) in enumerate(self.resumen.items()):
                    if i == 0:
                        t_dgyp = f"dGyP: {int(value):>6d}"
                        self.panel_label[i].config(text=t_dgyp, style=gbg, font=("Courier", 24, "bold"))

                    if i > 0:
                        # display linea superior header
                        k = 2 * i - 1
                        if i < 5:
                            self.panel_label[k].config(text=key, font=("Courier", 9))
                            self.panel_label[k + 1].config(text=value, font=("Courier", 9))

                        # display linea inferior header
                        if i > 4:
                            if " Conexión   :" != key:
                                self.panel_label[k].config(text=key, font=("Courier", 9))
                                self.panel_label[k + 1].config(text=value, font=("Courier", 9))
                            elif " Conexión   :" == key:
                                cox = display_red_green(0)
                                self.panel_label[k].config(text=key, font=("Courier", 9))
                                self.panel_label[k + 1].config(text=value, fg="yellow", font=("Courier", 9))

            # rescribe valores de oportunidades sell
            message = []
            (total, cantidad) = self.total_gain("sell")
            message.append(self.texto[0].format(total, cantidad).strip())

            estado: str = "normal" if cantidad > 0 else "disabled"
            self.op1.config(text=message[0].replace("_", " "), state=estado)

            # rescribe valores de oportunidades buy/dividends
            (total, cantidad) = self.total_gain("buy/dividends")
            message.append(self.texto[1].format(cantidad, self.invertir).strip())

            estado = "normal" if cantidad > 0 else "disabled"
            self.op2.config(text=message[1].replace("_", " "), state=estado)

            # rescribe valores de oportunidades buy
            (total, cantidad) = self.total_gain("buy")
            message.append(self.texto[2].format(cantidad, self.invertir).strip())

            estado = "normal" if cantidad > 0 else "disabled"
            self.op3.config(text=message[2].replace("_", " "), state=estado)

        except Exception as e:
            print("[header_panel()]: {}".format(e))

    # totaliza y coloca información del header
    def header_total_positions(self, positions) -> list:
        try:
            # totaliza sobre positions y deja en datos
            dgyp, costobase, mktvalue, gyp, debit, dividendos, roi, unprofit = (
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            )
            if positions:
                for position in positions:
                    unprofit += position["unrealizedpnl"] if position["unrealizedpnl"] > 0 else 0
                    dividendos += position["dividendo"]
                    costobase += position["costobase"]
                    # es reemplazado ya que es necesario tener value offline
                    mktvalue += position["mktvalue"]
                    if mktvalue == 0.0:
                        mktvalue += position["position"] * position["mrkprice"]
                    debit += position["deuda"]
                    dgyp += position["dgyp"]
                    gyp += position["unrealizedpnl"]
                    roi = (gyp / costobase) if costobase > 0 else 0

            # --------0------1----2---3----4-----------5--------6----7----8---9----0
            datos = [
                " ",
                dgyp,
                " ",
                " ",
                " ",
                costobase,
                mktvalue,
                gyp,
                roi,
                " ",
                dividendos,
            ]

            # construye header del panel en función del vehiculo
            if self.vehiculo == "Crypto":
                # comparte totalización de gyp diarias
                per = costobase / unprofit if unprofit > 0 else 0
                margen = costobase / (costobase - debit)
                cash = float(self.resumen.get(" Cash       :", 0))

                # escribir en resumen para impactar los graficos vehículo
                self.set_header_panel(
                    Dgyp=dgyp,
                    Nav=mktvalue,
                    Unpyl=gyp,
                    Unprofit=unprofit,
                    Per=per,
                    Debit=debit,
                    Dividends=dividendos,
                    Margen=margen,
                    Cash=cash,
                )

            if self.vehiculo == "Stock":
                if self.summary:
                    base = "BASE"
                    # comparte totalización de gyp diarias
                    dividendos = self.summary[base]["dividends"]
                    mktvalue = self.summary[base]["netliquidationvalue"]
                    debit = self.summary[base]["cashbalance"] if self.summary[base]["cashbalance"] < 0 else 0
                    cash = self.summary[base]["cashbalance"]
                    gyp = self.summary[base]["unrealizedpnl"]

                    per = costobase / unprofit if unprofit > 0 else 0
                    margen = costobase / (costobase + debit)

                    # escribir en resumen para impactar los graficos vehículo
                    self.set_header_panel(
                        Dgyp=dgyp,
                        Nav=mktvalue,
                        Unpyl=gyp,
                        Unprofit=unprofit,
                        Per=per,
                        Debit=debit,
                        Dividends=dividendos,
                        Margen=margen,
                        Cash=cash,
                    )

            return datos
        except Exception as e:
            print("[header_total_positions({})]: {}".format(self.vehiculo, e))

    @staticmethod
    def display_format(tipo="rows", data=None) -> list:
        try:
            datos = []
            if tipo == "total":
                datos = [
                    " ",
                    " ",
                    " ",
                    " ",
                    " ",
                    "{:>10.2f}".format(data[5]),
                    "{:>11.2f}".format(data[6]),
                    "{:>11.2f}".format(data[7]),
                    "{:>+11.2%}".format(data[8]),
                    " ",
                    "{:>10.2f}".format(data[10]),
                ]
            if tipo == "rows":
                datos = [
                    "{:>11}".format(data[0]),
                    "{:>10.0f}".format(data[1]),
                    "{:>11.4f}".format(data[2]),
                    "{:>11.4f}".format(data[3]),
                    "{:>11.4f}".format(data[4]),
                    "{:>10.2f}".format(data[5]),
                    "{:>11.2f}".format(data[6]),
                    "{:>11.2f}".format(data[7]),
                    "{:>+11.2%}".format(data[8]),
                    "{:>10.4f}".format(data[9]),
                    "{:>10.2f}".format(data[10]),
                ]
            return datos
        except Exception as e:
            print("[display_format()]: {}".format(e))

    # colorea lineas a display en positions
    def create_styles(self, i, idx, row, para):
        try:
            style = None
            # row totales
            if para == "total":
                if i == 0:
                    style = "even"
                    if self.heading[idx] in ("GyP", "%ROI"):
                        style = "even_green" if row[idx] >= 0 else "even_red"

            # rows detalles
            if para == "rows":
                # rows (even)
                if i % 2 == 0:
                    style = "even"
                    if self.heading[idx] in ("dGyP", "GyP", "%ROI"):
                        style = "even_green" if row[idx] >= 0 else "even_red"

                # rows (odd)
                if i % 2 != 0:
                    style = "odd"
                    if self.heading[idx] in ("dGyP", "GyP", "%ROI"):
                        style = "odd_green" if row[idx] >= 0 else "odd_red"

            return style
        except Exception as e:
            print("[create_styles()]: {}".format(e))

    @staticmethod
    # coloca los datos a ser mostrados en la liena del panel
    def struct_datos(position):
        try:
            data = [
                position["ticket"],
                position["dgyp"],
                position["position"],
                position["mrkprice"],
                (position["costobase"] / position["position"] if position["position"] > 0 else 0),
                position["costobase"],
                position["mrkprice"] * position["position"],
                position["unrealizedpnl"],
                position["retorno"],
                position["objetivo"],
                position["dividendo"],
            ]

            return data
        except Exception as e:
            print("[struct_datos()]: {}".format(e))

    # inicia información positions
    def inicio_widget_treeview(self, cartera):
        try:
            if cartera:
                # totaliza cartera y mueve totales a cada columna treeview row=0
                total, i = self.header_total_positions(cartera), 0
                for idx, tree in enumerate(self.m_heard):
                    sty = self.create_styles(0, idx, total, "total")
                    data_string = self.display_format(tipo="total", data=total)
                    tree.insert(
                        parent="",
                        index=0,
                        iid=0,
                        text="",
                        values=(data_string[idx],),
                        tags=(sty,),
                    )

                # recorre cartera y mueve detalle a cada columna treeview row > 0
                for i, position in enumerate(cartera):
                    data = self.struct_datos(position)
                    for idx, tree in enumerate(self.m_tree):
                        sty = self.create_styles(i, idx, data, "rows")
                        data_string = self.display_format(tipo="rows", data=data)
                        # tree.insert(parent="", index=tk.END, iid=i,  text='', values=(data_string[idx],), tags=(sty,))
                        tree.insert(
                            parent="",
                            index=i,
                            text="",
                            values=(data_string[idx],),
                            tags=(sty,),
                        )

        except Exception as e:
            print("[inicio_widget_treeview()]: {}".format(e))
            traceback.print_exc()

    def agregar_nuevo_activo(self, symbol, conid, precio, cantidad, costo):
        """Agrega un nuevo activo comprado al panel de posiciones.
        Solo agrega si el símbolo ya existe en inversiones (aparición orgánica)."""
        try:
            # Verificar si existe en inversiones - SOLO agregar si existe
            existe = self.PlanInversion.select_inversion(tipoin=self.vehiculo, ticket=symbol)
            if not existe:
                # No existe en inversiones aún, no agregar al panel
                return

            # Si existe en inversiones, continuar agregando al panel
            position = {
                "ticket": symbol,
                "conid": conid,
                "useraccount": self.account,
                "estrategia": "",
                "empresa": symbol,
                "peso": 0.0,
                "mrkprice": precio,
                "open": precio,
                "costobase": costo,
                "position": cantidad,
                "unrealizedpnl": 0.0,
                "dividendo": 0.0,
                "dividendYield": 0.0,
                "exDividendDate": None,
                "objetivo": 0.0,
                "deuda": precio,
                "retorno": 0.0,
                "fealta": None,
                "febaja": None,
                "iactiva": "Y",
                "tipoinv": self.vehiculo,
                "sector": "",
                "dgyp": 0,
                "mktvalue": costo,
                "factor_cambio": 1.0,
                "nivelIA": 0,
                "region": "",
                "country": "",
                "divisa": "USD",
            }

            # Agrega a self.positions
            self.positions.append(position)

            # Inserta en treeview
            i = len(self.positions) - 1
            data = self.struct_datos(position)
            for idx, tree in enumerate(self.m_tree):
                sty = self.create_styles(i, idx, data, "rows")
                data_string = self.display_format(tipo="rows", data=data)
                tree.insert(
                    parent="",
                    index=tk.END,
                    text="",
                    values=(data_string[idx],),
                    tags=(sty,),
                )

            # Actualiza totales
            total = self.header_total_positions(self.positions)
            for idx, tree in enumerate(self.m_heard):
                sty = self.create_styles(0, idx, total, "total")
                data_string = self.display_format(tipo="total", data=total)
                tree.item(0, values=(data_string[idx],), tags=(sty,))

            # Agrega a self.info para websocket
            self.info[symbol] = {"position": position}

            # Actualizar lista de símbolos para websocket y suscribir
            if self.vehiculo == "Crypto":
                if symbol not in self.activos:
                    self.activos.append(symbol)
            elif self.vehiculo == "Stock":
                if hasattr(self, "idsymbol") and conid and str(conid) not in self.idsymbol:
                    self.idsymbol.append(str(conid))
                    # Suscribir símbolo nuevo al websocket activo
                    try:
                        if hasattr(self, "ws") and self.ws and self.ws.sock and self.ws.sock.connected:
                            self.ws.send(
                                "smd+"
                                + str(conid)
                                + '+{"fields": ["31","55","70","71","76","82","84","86","7051","7292","7295","7296","7281","7286","7287","7288","7671","7672"]}'
                            )
                            print(f"[agregar_nuevo_activo()]: suscripto {symbol} (conid={conid})")
                        else:
                            print(f"[agregar_nuevo_activo()]: websocket no disponible para suscribir {symbol}")
                    except Exception as ws_err:
                        print(f"[agregar_nuevo_activo()]: error suscribiendo {symbol}: {ws_err}")

        except Exception as e:
            print(f"[agregar_nuevo_activo()]: {e}")

    # mantiene actualizada información positions en self_treeview (panel)
    def update_widget_treeview(self, symbol=None, position=None):
        def update_items_dash():
            try:
                # totaliza cartera y mueve totales a cada columna treeview row=0
                total = self.header_total_positions(self.positions)
                for idx, tree in enumerate(self.m_heard):
                    sty = self.create_styles(0, idx, total, "total")
                    data_string = self.display_format(tipo="total", data=total)
                    tree.item(0, values=(data_string[idx],), tags=(sty,))

                data = self.struct_datos(position)
                for idx, tree in enumerate(self.m_tree):
                    sty = self.create_styles(i, idx, data, "rows")
                    data_string = self.display_format(tipo="rows", data=data)
                    tree.item(child, values=(data_string[idx],), tags=(sty,))
            except Exception as e:
                print("[update_items_dash()]: {}".format(e))

        try:
            i = 0
            # recorre treeview[0] para ubicar el symbol y actualizar
            for child in self.m_tree[0].get_children():
                item = self.m_tree[0].item(child)
                ticket = item["values"][0].strip()
                if ticket == symbol:
                    update_items_dash()
                    break
                i += 1
        except Exception as e:
            print("[update_widget_treeview()]: {}".format(e))

    def update_panelVehiculo(self, orden=None):
        try:
            positions = self.on_sort_treeview(orden=orden)
            for position in positions:
                symbol = position["ticket"]
                self.update_widget_treeview(symbol=symbol, position=position)
        except Exception as e:
            print("[update_panelVehiculo()]: {}".format(e))
            traceback.print_exc()

    # obtiene lotes fiscales
    def get_lotes_fiscales(self, account=None, symbol=None, divisa="USD", last=None):
        try:
            elimina = [
                "id",
                "sec",
                "categoria",
                "divisa",
                "cuenta",
                "simbolo",
                "idtrans",
                "cantidad",
                "preciocierre",
                "producto",
                "tarifacomision",
                "basico",
                "gprealizadas",
                "mtmgp",
                "stock",
                "activa",
                "split",
            ]

            ResumLotes, a_gain, a_lost = DataHub.get_lotesGainLost(
                opcion="ambos", account=account, symbol=symbol, divisa=divisa, last=last
            )
            (book, ix) = ResumLotes["book"]

            if book:
                # revisar que hago con el frame
                frame_book = pd.DataFrame(book, columns=ix)
                frame_book = frame_book.drop(elimina, axis=1)
                frame_book["fechahora"] = frame_book["fechahora"].dt.date
                frame_book = frame_book.set_index("fechahora")
                self.gchar["booktrading"] = frame_book.copy()

            return ResumLotes, a_gain, a_lost
        except Exception as e:
            print(f"get_lotes_fiscales(): {e}")
            traceback.print_exc()
            # Retornar valores por defecto para evitar TypeError al desempaquetar
            return {"book": ([], [])}, 0, 0

    # despliega ventanas de estrategia y analisis de activo
    def window_estrategia(self, analisis=True):
        # controla salida de window_estrategia()
        def eexit():
            if not (self.rns is None):
                self.rns.destroy()

            # cerrar ventana de show_strategy_chart si está abierta
            if hasattr(self, "_chart_windows_estrategia"):
                for win in list(self._chart_windows_estrategia.values()):
                    try:
                        if win.winfo_exists():
                            win.destroy()
                    except Exception:
                        pass
                self._chart_windows_estrategia.clear()

            self.rnb.destroy()

        # ventana inferior para el activo
        def window_analisis():
            try:
                # define windows de analysis
                self.rns = tk.Toplevel()

                x_title = "Análisis " + self.symbol
                x_dimension = "%dx%d+%d+%d" % (self.max_dw - 13, 220, 0, 775)
                self.rns.geometry(x_dimension)
                self.rns.resizable(False, False)
                self.rns.attributes("-toolwindow", 1)
                self.rns.title(x_title)
                self.rns.config(bg=self.bgcolor)

                scr1 = ttk.Frame(self.rns, padding=(1, 1, 1, 1), style="C.TFrame")
                scr2 = ttk.Frame(self.rns, padding=(1, 1, 1, 1), style="C.TFrame")
                scr3 = ttk.Frame(self.rns, padding=(1, 1, 1, 1), style="C.TFrame")
                scr1.pack(side=tk.LEFT)
                scr2.pack(side=tk.LEFT)
                scr3.pack(side=tk.LEFT)

                fg1 = Figure(figsize=(5.78, 2.0), dpi=110, layout="tight")
                fg2 = Figure(figsize=(5.78, 2.0), dpi=110, layout="tight")
                fg3 = Figure(figsize=(5.78, 2.0), dpi=110, layout="tight")
                cv1 = FigureCanvasTkAgg(fg1, master=scr1)
                cv2 = FigureCanvasTkAgg(fg2, master=scr2)
                cv3 = FigureCanvasTkAgg(fg3, master=scr3)

                fg1.set_facecolor(self.cgcolor)
                fg2.set_facecolor(self.cgcolor)
                fg3.set_facecolor(self.cgcolor)

                cv1.draw()
                cv2.draw()
                cv3.draw()
                cv1.get_tk_widget().pack()
                cv2.get_tk_widget().pack()
                cv3.get_tk_widget().pack()

                # Gráfica performance de dividendo
                (market, iy) = self.Market.select(account=self.account, symbol=self.symbol)
                if market:
                    if market[0][iy.index("categoriaActivo")] in ("I", "N", "S", "X"):
                        # ubica información de yfinance.Ticker, para mostrar gráfico de dividends
                        (activo, datos, update) = self.ts_yfinance_symbol(symbol=self.symbol, vehiculo=self.vehiculo)
                        self.rendimiento_dividends(
                            fg=fg2,
                            activo=activo,
                            datos=datos,
                            symbol=self.symbol,
                            plot="yes",
                        )
                        cv2.draw()

                # Gráfica performance acumulado para el symbol
                ddatos = performa_asset(
                    account=self.account,
                    vehiculo=self.vehiculo,
                    tipo="activo",
                    asset=self.symbol,
                )

                (ticket, rtn_index, cum_index, index_ref) = vehiculo_parm(vehiculo=self.vehiculo)
                parm = {
                    "BTC": index_ref,
                    "++ index": "++ " + self.symbol,
                    "Value": "Value Market",
                    "Costo": "Cost basic",
                    "legend": "outside upper left",
                    "aspect": 0.21,
                    "titulo": "Performance (acumulativo) " + self.symbol,
                }
                self.graph_performace_portafolio(fg=fg3, data=ddatos, parm=parm)
                cv3.draw()
            except Exception as e:
                print("[window_analisis()]: {}".format(e))

        # encapsula llamado chart_symbol() gwi0001
        def chart_setup(periodo, tipo, accion, toggle_fib=False):
            try:
                # toggle fibonacci si se solicita
                if toggle_fib:
                    self.gchar["fibonacci"] = not self.gchar.get("fibonacci", False)

                # busca datos yf.download si activo tiene dividendos (stock)
                if self.vehiculo == "Stock":
                    vehiculo = "hist"
                elif self.vehiculo == "Crypto":
                    vehiculo = "download"
                else:
                    vehiculo = self.vehiculo

                (activo, pdatos, update) = self.ts_yfinance_symbol(symbol=self.symbol, vehiculo=vehiculo)
                self.gchar["periodo"] = periodo if accion == "p" else self.gchar["periodo"]
                self.gchar["tipo"] = tipo if accion == "t" else self.gchar["tipo"]

                chart_symbol(fg=fg, datos=pdatos, keys=self.gchar)
                cv.draw()
            except Exception as e:
                print("[chart_setup()]: {}".format(e))
                traceback.print_exc()

        # lista lotes fiscales (compras y book)
        def list_fiscales(lote=None, a_gain=[], a_lost=[], last=None):
            # actualiza totales de gain y lost
            def update_totales_lotes():
                try:
                    for parent in tree.get_children():
                        x_cant, x_roi, acum, cost = 0.0, 0.0, 0.0, 0.0

                        # Recorrer los hijos del padre
                        for child in tree.get_children(parent):
                            x_cant += float(tree.item(child, "values")[2])  # cantidades por lote
                            acum = float(tree.item(child, "values")[4])  # gyp por lote
                            cost = float(tree.item(child, "values")[5])  # costobase por lote

                        # Actualizar el valor del padre
                        # x_roi = (acum / self.gchar['costobase']) if self.gchar['costobase'] > 0 else 0
                        x_roi = (acum / cost) if cost > 0 else 0

                        tree.item(
                            parent,
                            values=(
                                "",
                                "",
                                "",
                                "{:>10.5f}".format(x_cant),
                                "{:>10.2f}$".format(acum),
                                "{:>10.2f}$".format(cost),
                                "{:>+10.2%}".format(x_roi),
                                "",
                            ),
                        )
                except Exception as er:
                    print("[update_totales_lotes()]: {}".format(er))

            # Función para sincronizar el desplazamiento horizontal de ambos Treeview
            def on_sync_treeview_scroll(*args):
                heard.xview(*args)
                tree.xview(*args)

            # muestra el arbol con last  y los lotes gain y lost
            def treeview_lotes() -> ttk.Treeview:
                try:
                    rns = ttk.Frame(lote, padding=(1, 1, 1, 1), style="C.TFrame")  # heard
                    rnb = ttk.Frame(lote, padding=(1, 1, 1, 1), style="C.TFrame")  # tree
                    scr = ttk.Frame(lote, padding=(1, 1, 1, 1), style="C.TFrame")  # scroll
                    rns.pack(side=tk.TOP, fill=tk.X, expand=True)
                    rnb.pack(side=tk.TOP, fill=tk.X, expand=True)
                    scr.pack(side=tk.TOP, fill=tk.X, expand=True)

                    heading = [
                        "Date",
                        "Price. Trader.",
                        "Cant. Trader",
                        "Cum Trader",
                        "Cum. UnP&L",
                        "Cum. CostB",
                        "Cum Total",
                        "%ROI",
                        "UnP&L",
                    ]

                    fields = [
                        "fec",
                        "prc",
                        "cant",
                        "acum",
                        "gyp",
                        "cost",
                        "total",
                        "bene",
                        "GPa",
                    ]
                    x_heard = ttk.Treeview(rns, columns=fields, height=1, style="TFrame")
                    x_heard.tag_configure("blue", background="blue", foreground="white")

                    x_heard.column("#0", width=55, minwidth=55)
                    x_heard.heading("#0", text="Lote")
                    x_heard.pack(side=tk.RIGHT, anchor=tk.E)

                    x_tree = ttk.Treeview(rnb, columns=fields, height=6, style="TFrame", show="tree")
                    for j, key in enumerate(fields):
                        x_heard.column(key, width=93, minwidth=93, anchor="e")
                        x_heard.heading(key, text=heading[j])

                        x_tree.column(key, width=93, minwidth=93, anchor="e")
                        x_tree.heading(key, text=heading[j])

                    x_tree.tag_configure("green", background="green", foreground="white")
                    x_tree.tag_configure("red", background="red", foreground="white")
                    x_tree.column("#0", width=55, minwidth=55)
                    x_tree.pack(side=tk.RIGHT, anchor=tk.E)

                    hscroll = ttk.Scrollbar(scr, orient="horizontal", command=on_sync_treeview_scroll)
                    x_heard.config(xscrollcommand=hscroll.set)
                    x_tree.config(xscrollcommand=hscroll.set)
                    hscroll.pack(side=tk.BOTTOM, fill=tk.X)

                    return x_tree, x_heard
                except Exception as er:
                    print("[treeview_lotes()]: {}".format(er))

            try:
                # define arbol para mostrar lotes
                tree, heard = treeview_lotes()

                # por bof() agrega last price del symbol (base cálculo de los lotes)
                cum_total = self.gchar["unrealizedpnl"] + self.gchar["costobase"]
                bof = heard.insert(
                    "",
                    "0",
                    text="last",
                    values=(
                        "",
                        "{:>10.5f}$".format(self.gchar["mkPrice"]),
                        "",
                        "{:>+10.5f}".format(self.gchar["stock"]),
                        "{:>10.2f}$".format(self.gchar["unrealizedpnl"]),
                        "{:>10.2f}$".format(self.gchar["costobase"]),
                        "{:>10.2f}$".format(cum_total),
                        "{:>+10.2%}".format(self.gchar["retorno"]),
                        "",
                    ),
                    tags=("blue",),
                )
                lost = tree.insert(
                    "",
                    "end",
                    text="lost",
                    values=(
                        "",
                        "",
                        "",
                        "{:>10.5f}".format(0),
                        "{:>10.2f}".format(0),
                        "{:>10.2f}".format(0),
                        "{:>10.2f}".format(0),
                        "{:>+10.2%}".format(0),
                        "",
                    ),
                )
                gain = tree.insert(
                    "",
                    "end",
                    text="gain",
                    values=(
                        "",
                        "",
                        "",
                        "{:>10.5f}".format(0),
                        "{:>10.2f}".format(0),
                        "{:>10.2f}".format(0),
                        "{:>10.2f}".format(0),
                        "{:>+10.2%}".format(0),
                        "",
                    ),
                )

                # ordena lista de lotes ganadores y asigna acum=0
                s_gain = sorted(a_gain, key=lambda x: x["precio"], reverse=False)
                p_acum, c_acum, costo = 0.0, 0.0, 0.0

                for i, value in enumerate(s_gain):
                    p_acum += value["gyp"]
                    c_acum += value["cantidad"]
                    costo += value["costo"]
                    roi = (p_acum / costo) if costo > 0 else 0
                    total = p_acum + costo

                    items = tree.insert(
                        gain,
                        "end",
                        text=str(i + 1),
                        values=(
                            "{}".format(value["fecha"]),
                            "{:>10.5f}".format(value["precio"]),
                            "{:>+10.5f}".format(value["cantidad"]),
                            "{:>+10.5f}".format(c_acum),
                            "{:>10.2f}".format(p_acum),
                            "{:>10.2f}".format(costo),
                            "{:>10.2f}".format(total),
                            "{:>+10.2%}".format(roi),
                            "{:>10.2f}".format(value["gyp"]),
                        ),
                        tags=("green",),
                    )

                # ordena lista de lotes perdedores y asigna acum=0
                s_lost = sorted(a_lost, key=lambda x: x["precio"], reverse=False)
                p_acum, c_acum, costo = 0.0, 0.0, 0.0

                for i, value in enumerate(s_lost):
                    p_acum += value["gyp"]
                    c_acum += value["cantidad"]
                    costo += value["costo"]
                    roi = (p_acum / costo) if costo > 0 else 0
                    total = p_acum + costo

                    items = tree.insert(
                        lost,
                        "end",
                        text=str(i + 1),
                        values=(
                            "{}".format(value["fecha"]),
                            "{:>10.5f}".format(value["precio"]),
                            "{:>+10.5f}".format(value["cantidad"]),
                            "{:>+10.5f}".format(c_acum),
                            "{:>10.2f}".format(p_acum),
                            "{:>10.2f}".format(costo),
                            "{:>10.2f}".format(total),
                            "{:>+10.2%}".format(roi),
                            "{:>10.2f}".format(value["gyp"]),
                        ),
                        tags=("red",),
                    )

                update_totales_lotes()
            except Exception as e:
                print("[list_fiscales()]: {}".format(e))

        try:
            # define windows de estrategia
            self.rnb = tk.Toplevel()
            title = "Grafico " + self.symbol
            dimension = "%dx%d+%d+%d" % (607, 665, self.df - 0, 65)
            self.rnb.geometry(dimension)
            self.rnb.resizable(False, False)
            self.rnb.attributes("-toolwindow", 1)
            self.rnb.config(bg=self.bgcolor)
            self.rnb.title(title)
            self.rnb.focus()
            self.rnb.grab_set()
            self.rnb.protocol("WM_DELETE_WINDOW", eexit)

            win1 = ttk.Frame(self.rnb, padding=(1, 1, 1, 1), style="C.TFrame")  # gráfica activo
            win2 = ttk.Frame(self.rnb, padding=(1, 1, 1, 1), style="C.TFrame")  # botones gráfico y widget
            win3 = ttk.Frame(self.rnb, padding=(1, 1, 1, 1), style="W.TFrame")  # ventana de lotes
            win1.pack(fill=tk.X)
            win2.pack(fill=tk.X)
            win3.pack(fill=tk.X)

            win20 = tk.Frame(win2, bg=self.bgcolor)
            win21 = tk.Frame(win2, bg=self.bgcolor)
            win20.pack(side=tk.LEFT)
            win21.pack(side=tk.RIGHT)

            bt1 = tk.Button(
                win21,
                text="1w",
                width=2,
                bg=self.bgcolor,
                fg=self.cgcolor,
                relief=tk.FLAT,
                command=lambda: chart_setup("W", gtipo, "p"),
            )
            bt2 = tk.Button(
                win21,
                text="1m",
                width=2,
                bg=self.bgcolor,
                fg=self.cgcolor,
                relief=tk.FLAT,
                command=lambda: chart_setup("ME", gtipo, "p"),
            )
            bt3 = tk.Button(
                win21,
                text="3m",
                width=2,
                bg=self.bgcolor,
                fg=self.cgcolor,
                relief=tk.FLAT,
                command=lambda: chart_setup("QE", gtipo, "p"),
            )
            bt4 = tk.Button(
                win21,
                text="1y",
                width=2,
                bg=self.bgcolor,
                fg=self.cgcolor,
                relief=tk.FLAT,
                command=lambda: chart_setup("YE", gtipo, "p"),
            )
            bt5 = tk.Button(
                win21,
                text="6m",
                width=2,
                bg=self.bgcolor,
                fg=self.cgcolor,
                relief=tk.FLAT,
                command=lambda: chart_setup("2QE", gtipo, "p"),
            )

            # inicia variables
            gtipo, gperiodo, position = "candle", "W", None
            AGain, ALost = [], []
            self.gchar["fibonacci"] = False

            # obtiene position para symbol y sus lotes fiscales
            if self.positions:
                found, position = buscar_ticker(self.positions, self.symbol)
                if position:
                    self.gchar["unrealizedpnl"] = position["unrealizedpnl"]
                    self.gchar["fibonacci"] = False
                    self.gchar["costobase"] = position["costobase"]
                    self.gchar["position"] = True
                    self.gchar["objetivo"] = position["objetivo"]
                    self.gchar["retorno"] = position["retorno"]
                    self.gchar["avgCost"] = position["costobase"] / position["position"]
                    self.gchar["account"] = position["useraccount"]
                    self.gchar["mkPrice"] = position["mrkprice"]
                    self.gchar["divisa"] = position["divisa"]
                    self.gchar["ticket"] = position["ticket"]
                    self.gchar["stock"] = position["position"]
                    self.gchar["conid"] = position["conid"]
                    self.gchar["name"] = position["empresa"]

                    # recupera información de lotes fiscales
                    (ResumLotes, AGain, ALost) = self.get_lotes_fiscales(
                        account=self.gchar["account"],
                        symbol=self.gchar["ticket"],
                        divisa=self.gchar["divisa"],
                        last=self.gchar["mkPrice"],
                    )

                    book, ix = ResumLotes.get("book")

            # bottom de buy y sell (habilitados solo si id_transaccion está activo)
            btn_state = tk.NORMAL if self.sesion.get("id_transaccion", False) else tk.DISABLED
            ft1 = tk.Button(
                win20,
                text="BUY",
                width=8,
                bg="blue",
                fg="white",
                state=btn_state,
                command=lambda: self.trader_lotes_fiscales(option="BUY", parm=self.gchar),
            )
            ft2 = tk.Button(
                win20,
                text="SELL",
                width=8,
                bg="red",
                fg="white",
                state=btn_state,
                command=lambda: self.trader_lotes_fiscales(option="SELL", parm=self.gchar),
            )
            ft3 = tk.Button(
                win20,
                text="Cancel",
                width=8,
                bg="gray",
                fg="white",
                command=lambda: eexit(),
            )

            # bottom de gráfica fibonacci ---------------------------------------------------------------------------
            imagen_tk = BDsystem.select_image(idd=104, size=(16, 16))
            gt0 = tk.Button(
                win21,
                image=imagen_tk,
                bg=self.bgcolor,
                relief=tk.FLAT,
                command=lambda: chart_setup(self.gchar["periodo"], self.gchar["tipo"], "t", toggle_fib=True),
            )
            gt0.imagen = imagen_tk

            # bottom de gráfica de velas ---------------------------------------------------------------------------
            imagen_tk = BDsystem.select_image(idd=100, size=(16, 16))
            gt1 = tk.Button(
                win21,
                image=imagen_tk,
                bg=self.bgcolor,
                relief=tk.FLAT,
                command=lambda: chart_setup(self.gchar["periodo"], "candle", "t"),
            )
            gt1.imagen = imagen_tk

            # bottom de gráfica de linea
            imagen_tk = BDsystem.select_image(idd=101, size=(16, 16))
            gt2 = tk.Button(
                win21,
                image=imagen_tk,
                bg=self.bgcolor,
                relief=tk.FLAT,
                command=lambda: chart_setup(self.gchar["periodo"], "line", "t"),
            )
            gt2.imagen = imagen_tk

            # botón gráfico de estrategia
            imagen_tk = BDsystem.select_image(idd=105, size=(16, 16))
            gt3 = tk.Button(
                win21,
                image=imagen_tk,
                bg=self.bgcolor,
                relief=tk.FLAT,
                command=lambda: self._abrir_grafico_estrategia(self.symbol, Xposition=530),
            )
            gt3.imagen = imagen_tk

            ft3.pack(side=tk.RIGHT, anchor=tk.W, padx=3)
            ft2.pack(side=tk.RIGHT, anchor=tk.W, padx=3)
            ft1.pack(side=tk.RIGHT, anchor=tk.W, padx=3)

            gt1.pack(side=tk.RIGHT, anchor=tk.E, padx=1)
            gt2.pack(side=tk.RIGHT, anchor=tk.E)
            gt0.pack(side=tk.RIGHT, anchor=tk.E)
            gt3.pack(side=tk.RIGHT, anchor=tk.E, padx=(4, 1))

            bt1.pack(side=tk.RIGHT, anchor=tk.E)  # 1w  → derecha
            bt2.pack(side=tk.RIGHT, anchor=tk.E)  # 1m
            bt3.pack(side=tk.RIGHT, anchor=tk.E)  # 3m
            bt5.pack(side=tk.RIGHT, anchor=tk.E)  # 6m
            bt4.pack(side=tk.RIGHT, anchor=tk.E)  # 1y  → izquierda

            # lienzo para grafico de activo
            fg = Figure(figsize=(5.9, 4.0), dpi=110)
            fg.set_facecolor(self.cgcolor)
            cv = FigureCanvasTkAgg(fg, master=win1)
            cv.draw()
            cv.get_tk_widget().pack()

            # obtiene pdatos(sin close ['Close'] del symbol y grafica
            chart_setup(self.gchar["periodo"], self.gchar["tipo"], accion="p")

            # muestra resumen de lotes
            if AGain or ALost:
                list_fiscales(lote=win3, a_gain=AGain, a_lost=ALost, last=self.gchar["ticket"])

            # más graficos de analisis cuando se parte del portafolio
            if analisis:
                window_analisis()
        except Exception as e:
            print(f"[window_estrategia()]: {e}")
            traceback.print_exc()

    # módulo principal para realizar BUY/SELL
    def trader_lotes_fiscales(self, option=None, parm=None):
        def eexit():
            self.orderActivas.destroy()

        self.orderActivas = tk.Toplevel()
        title = option + " : " + self.symbol

        # (ancho, largo  position:  x, y) % (620, 180, self.df - 10, 775)
        dimension = "%dx%d+%d+%d" % (620, 180, self.df - 630, 565)
        self.orderActivas.geometry(dimension)
        self.orderActivas.overrideredirect(False)
        self.orderActivas.resizable(False, False)
        self.orderActivas.attributes("-toolwindow", 1)
        self.orderActivas.config(bg=self.cgcolor)
        self.orderActivas.title(title)
        self.orderActivas.focus()
        self.orderActivas.grab_set()

        # primer nivel para trader
        self.WindowsBuySell_trader(rnb=self.orderActivas, option=option, parm=self.gchar)

    def ventanas_activas(self):
        symbol, ws, sell = self.gchar["ticket"], {}, {}

        if symbol is not None:
            # Verifica si el símbolo existe en self.info
            if symbol in self.info:
                ws = self.info[symbol].get("websocket", {})
                sell = self.info[symbol].get("sell", {})

            if ws:
                bid = ws["bid"]
                ask = ws["ask"]
                s_bid = "Bid {:>10.6f}".format(bid)
                self.bid.config(text=s_bid)

                s_ask = "Ask {:>10.6f}".format(ask)
                self.ask.config(text=s_ask)
            else:
                # Símbolo nuevo sin websocket - obtiene precio directo
                if self.vehiculo == "Crypto":
                    try:
                        resp = self.BClient.ticker_price(symbol=symbol)
                        if resp and "price" in resp:
                            precio = float(resp["price"])
                            s_bid = "Bid {:>10.6f}".format(precio)
                            s_ask = "Ask {:>10.6f}".format(precio)
                            self.bid.config(text=s_bid)
                            self.ask.config(text=s_ask)
                    except Exception:
                        pass

            if sell:
                disponible = sell["disponible"]
                s_available = "Disponible :{:>10.5f}".format(disponible)
                self.available.config(text=s_available)

    # totaliza las oportunidades de gain capital
    def total_gain(self, tipo):
        total, cantidad = 0, 0
        try:
            for key, value in self.info.items():

                # recupera profit que este  self.info[*]['sell']
                if "sell" in value and tipo == "sell":
                    if "profit" in value["sell"]:

                        # recupera tasa de cambio para divisa distinta a USD
                        importe = value["sell"]["profit"] / value["sell"]["factor"]
                        if importe > DataHub.MinProfit:
                            total += importe
                            cantidad += value["sell"]["cantidad lotes"]

                # recupera proyección de ganancias que este self.info[*]['buy/dividends']
                elif tipo == "buy/dividends":
                    if "buy" in value:
                        if "ganancia precio" in value["buy"]:
                            if value["buy"]["ganancia precio"] != 0:
                                cantidad += 1
                    elif "dividends" in value:
                        if "ganancia precio" in value["dividends"]:
                            if value["dividends"]["ganancia precio"] != 0:
                                cantidad += 1

            return total, cantidad
        except Exception as e:
            print("[total_gain()]: {}".format(e))

    # Abre ventana de análisis según el vehículo
    def abrir_analisis_vehiculo(self):
        """Abre ventana de análisis usando la clase correspondiente al vehículo"""
        try:
            # Seleccionar clase de análisis según vehículo
            if self.vehiculo == "BBVA.ARS":
                analisis = AnalisisFCI(
                    master=self.master,
                    info=self.info,
                    repositorio=self.PlanInversion,
                    colors=self.colors,
                    vehiculo=self.vehiculo,
                )
            elif self.vehiculo == "Crypto":
                analisis = AnalisisCrypto(
                    master=self.master,
                    info=self.info,
                    repositorio=self.PlanInversion,
                    colors=self.colors,
                    vehiculo=self.vehiculo,
                    positions=self.positions,
                )
            else:  # Stock y otros
                analisis = AnalisisStock(
                    master=self.master,
                    info=self.info,
                    repositorio=self.PlanInversion,
                    colors=self.colors,
                    vehiculo=self.vehiculo,
                )

            analisis.mostrar_ventana()

        except Exception as e:
            print(f"[abrir_analisis_vehiculo]: {e}")
            traceback.print_exc()

    # TopWindow() para ts_oportunidades_symbol y sus posibles ventas de lotes fiscales
    def oportunidad_gain_capital(self):
        # controla salida de window_estrategia()
        def eexit():
            ons.destroy()

        # control para mantener lista de procesos actualizados
        def delete_items():
            for padre_id in tree.get_children():
                for item_id in tree.get_children(padre_id):
                    tree.delete(item_id)

                tree.delete(padre_id)
            return tree

        def update_windows():
            # ordena lista de lotes ganadores y asigna acum=0 e insert symbols padres
            s_sell, acum = DataHub.get_info_symbols_gain(), 0.0

            delete_items()

            # inserta registros en treeview
            for i, value in enumerate(s_sell):
                if (value["profit"] / value["factor"]) < DataHub.MinProfit:
                    continue

                # acumula para los profit > DataHub.MinProfit
                acum += value["profit"] / value["factor"]
                importe = format_financiero(width=10, importe=value["profit"], divisa=value["divisa"])

                activo = tree.insert(
                    "",
                    "end",
                    text=value["symbol"],
                    values=(
                        importe,
                        "{:>10.0f}".format(acum),
                        "{:>10.0f}".format(value["cantidad lotes"]),
                        "{:>10.5f}".format(value["last"]),
                        "{:>10.5f}".format(value["cantidad sell"]),
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ),
                    tags=("symbol",),
                )

                # detalla lotes ganadores --
                ventas = DataHub.maximiza_sell_lotes(
                    account=self.account,
                    symbol=value["symbol"],
                    last=value["last"],
                    c_sell=value["cantidad lotes"],
                    position=value["position"],
                    costobase=value["costobase"],
                )
                anterior = None
                for keys, sell in ventas.items():
                    if sell["profit"] != anterior:
                        items = tree.insert(
                            activo,
                            "end",
                            text="",
                            values=(
                                "",
                                "",
                                "",
                                "",
                                "",
                                "{:>10}".format(keys),
                                "{:>10.0f}".format(sell["profit"]),
                                "{:>10.0f}".format(sell["lotes"]),
                                "{:>10.5f}".format(sell["cantidad sell"]),
                                "{:>10.1%}".format(sell["roi"]),
                                "{:>10.6f}".format(sell["pos avgCost"]),
                                "{:>10.5f}".format(sell["pos position"]),
                                "{:>10.2f}".format(sell["pos costobase"]),
                            ),
                            tags=("sell",),
                        )
                    anterior = sell["profit"]

                # muestra las opciones para el activo
                tree.item(activo, open=True)

            ons.after(1000, update_windows)

        # selecciona  symbol a sell
        def seleccionar_item(event):
            try:
                selected_item = tree.focus()
                parent = tree.parent(selected_item)
                symbol = tree.item(parent, "text")
                self.symbol = symbol.strip()
                self.window_estrategia(analisis=False)
            except Exception as e:
                print("seleccionar_item(): {}".format(e))

        try:
            ons = tk.Toplevel()
            title = "Grain Capital"
            dimension = "%dx%d+%d+%d" % (1270, 220, 0, 775)
            ons.geometry(dimension)
            ons.resizable(False, False)
            ons.attributes("-toolwindow", 1)
            ons.focus()
            ons.title(title)
            ons.config(bg=self.bgcolor)
            ons.protocol("WM_DELETE_WINDOW", eexit)

            win1 = ttk.Frame(ons, padding=(1, 1, 1, 1), style="C.TFrame")
            win2 = ttk.Frame(ons, padding=(1, 1, 1, 1), style="C.TFrame")
            win1.pack(side=tk.LEFT)
            win2.pack(side=tk.LEFT)

            # coloca acciones sobre ventana ------------------------------------------------------------------------
            ct1 = tk.Button(
                win2,
                text="Cancel",
                width=8,
                bg="gray",
                fg="white",
                command=lambda: eexit(),
            )

            ct1.pack(side=tk.BOTTOM, padx=20, pady=40)

            # define treeview cant, bene
            fields = [
                "gyp",
                "acum",
                "lote",
                "prc",
                "stock",
                "lotes",
                "sell",
                "bene",
                "cant",
                "roi",
                "pos_avg",
                "pos_position",
                "pos_costobase",
            ]
            heard = [
                "Maxima Gain",
                "Gain Acum.",
                "Lotes Sell",
                "Last Sell",
                "Stock Sell",
                "Opción",
                "Profit",
                "Lotes",
                "Cant.Trader",
                "%ROI",
                "post AvgCost",
                "post Position",
                "post Costbase",
            ]
            tree = ttk.Treeview(win1, columns=fields, height=9, style="TFrame")
            tree.tag_configure("symbol", background=self.cgcolor, foreground="white")
            tree.tag_configure("sell", background=self.cgcolor, foreground="cyan")
            tree.bind("<Double-1>", seleccionar_item)

            tree.column("#0", width=90, minwidth=90)
            tree.heading("#0", text="Symbol")
            for j, key in enumerate(fields):
                ancho = 89 if key == "gyp" else 82
                tree.column(key, width=ancho, minwidth=ancho, anchor="e")
                tree.heading(key, text=heard[j])

            tree.pack(fill=tk.X, anchor=tk.E)

            update_windows()
        except Exception as e:
            print("[oportunidad_gain_capital()]: {}".format(e))

    # TopWindow() para ts_oportunidades_symbol y sus posibles compra de lotes fiscales
    def oportunidad_mejorar_buyDividends(self):
        # controla salida de window_estrategia()
        def eexit():
            ons.destroy()

        # selecciona  symbol a sell
        def seleccionar_item(event):
            try:
                selected_item = tree.focus()
                parent = tree.parent(selected_item)
                symbol = tree.item(parent, "text")
                self.symbol = symbol.strip()
                self.window_estrategia(analisis=False)
            except Exception as e:
                print("seleccionar_item(): {}".format(e))

        # recorre self.info() para mostrar lo disponible para la compra
        def update_windows():

            tree.delete_row()

            # inserta registros en treeview
            Newheight = 0
            for key, value in self.info.items():
                tipo = "dividends" if "dividends" in value else "buy"
                if tipo in value:
                    if "ganancia precio" in value[tipo]:
                        row = [
                            key,
                            "{:>10.3%}".format(value[tipo]["ganancia precio"]),
                            "{:>10.5f}".format(value[tipo]["last"]),
                            "{:>10.2f}".format(value[tipo]["avgcost"]),
                            "{:>10.5f}".format(value[tipo]["objetivo"]),
                            "{:>10.5f}".format(value[tipo]["cantidad buy"]),
                            "{:>10}".format(value[tipo]["exDividendDate"]),
                            "{:>10.3%}".format(value[tipo]["dividendYield"]),
                            "{:>10.2f}".format(value[tipo]["pre dividendos"]),
                            "{:>10.2f}".format(value[tipo]["post dividendos"]),
                            "{:>10.2f}".format(value[tipo]["pre costobase"]),
                            "{:>10.2f}".format(value[tipo]["post costobase"]),
                        ]
                        Newheight += 1

                        # inserta registros en treeview
                        tree.insert_row(values=row)

                # ajusta altura del treeview
                tree.config(height=9 if Newheight >= 9 else Newheight)

            ons.after(1000, update_windows)

        try:
            ons = tk.Toplevel()
            title = "Acumular Stock/Dividendos"
            dimension = "%dx%d+%d+%d" % (1270, 220, 0, 775)
            ons.geometry(dimension)
            ons.resizable(False, False)
            ons.attributes("-toolwindow", 1)
            ons.focus()
            ons.title(title)
            ons.config(bg=self.bgcolor)
            ons.protocol("WM_DELETE_WINDOW", eexit)

            win1 = ttk.Frame(ons, padding=(1, 1, 1, 1), style="C.TFrame")
            win2 = ttk.Frame(ons, padding=(1, 1, 1, 1), style="C.TFrame")
            win1.pack(side=tk.LEFT)
            win2.pack(side=tk.LEFT)

            # coloca acciones sobre ventana ------------------------------------------------------------------------
            ct1 = tk.Button(
                win2,
                text="Cancel",
                width=8,
                bg="gray",
                fg="white",
                command=lambda: eexit(),
            )

            ct1.pack(side=tk.TOP, padx=30, pady=10)

            # Definir las columnas, columnas fijas y alineaciones
            alignments = {
                "Symbol": {"width": 80, "anchor": "w"},
                "Gain_Precio": {"width": 80, "anchor": "e"},
                "Last_Price": {"width": 90, "anchor": "e"},
                "AvgCost": {"width": 80, "anchor": "e"},
                "Objetivo": {"width": 90, "anchor": "e"},
                "Stock_Buy": {"width": 90, "anchor": "e"},
                "ExDividends": {"width": 80, "anchor": "e"},
                "Tasa_Nominal": {"width": 80, "anchor": "e"},
                "Pre_Dividendos": {"width": 90, "anchor": "e"},
                "Post_Dividendos": {"width": 100, "anchor": "e"},
                "Pre_Costobase": {"width": 90, "anchor": "e"},
                "Post_Costobase": {"width": 100, "anchor": "e"},
            }
            columns = list(alignments.keys())
            fixed_columns = columns[0:1]

            # Crear instancia de la clase con columnas fijas, scroll y alineación
            tree = CustomTreeview(
                master=win1,
                columns=columns,
                fixed_columns=fixed_columns,
                sort_columns=True,
                fixed_row=False,
                show_vscroll=False,
                show_hscroll=False,
                height=9,
                column_alignments=alignments,
                style="TFrame",
            )
            update_windows()

        except Exception as e:
            print(f"[oportunidad_mejorar_buyDividends()]: {e} {traceback.print_exc()}")

    def setup_graph_performace(self, tipo=None):

        periodos = {
            "1M": pd.DateOffset(months=1),
            "3M": pd.DateOffset(months=3),
            "6M": pd.DateOffset(months=6),
            "1Y": pd.DateOffset(years=1),
            "5Y": pd.DateOffset(years=5),
        }
        hoy = pd.Timestamp.today()

        symbol, rtn_index, cum_index, index_ref = vehiculo_parm(vehiculo=self.vehiculo)
        parm = {
            "BTC": index_ref,
            "++ index": "++ Portafolio",
            "Value": "Value Market",
            "Costo": "Cost basic",
            "legend": "outside upper left",
            "aspect": 0.21,
            "periodo": tipo,
            "titulo": f"Performance {self.vehiculo}: (in {tipo})",
        }

        # ajusta a tempralidad seleccionada
        if self.Ddatos is None or self.Ddatos.empty or not isinstance(self.Ddatos.index, pd.DatetimeIndex):
            return
        df_plot = self.Ddatos[self.Ddatos.index >= hoy - periodos[tipo]]
        self.graph_performace_portafolio(fg=self.graph[2][1], data=df_plot, parm=parm)
        self.graph[2][0].draw()

    # titulo ROI vehiculo -------------------------------------------------------------------------------------------
    def graph_ROI_vehiculo(self, data, parm):
        try:
            # Extrae valores clave
            inversión = float(data.get("Inversión", 0.0))
            unpnl = float(data.get("UnP&l", 0.0))
            unprofit = float(data.get("UnProfit", unpnl))
            cash = float(data.get("Cash", 0.0))

            # Preparar etiquetas y valores (excluimos UnProfit de las barras porque lo pintaremos como línea)
            labels = []
            values = []
            colors = []

            # Mantener consistencia con orden anterior: Inversión, UnProfit/UnP&l, Cash/UnProfit auxiliar
            # Añadimos Inversión como barra principal
            labels.append("Inversión")
            values.append(inversión)
            colors.append(self.cchart.get("plot5", "navy"))

            # Añadimos UnP&l como barra (si existe y distinto de Inversión) — será opcional visualmente
            if "UnP&l" in data:
                labels.append("UnP&l")
                values.append(unpnl)
                colors.append(self.cchart.get("plot1", "green"))

            # Añadimos Cash como barra
            labels.append("Cash")
            values.append(cash)
            colors.append(self.cchart.get("plot3", "orange"))

            # Configuración del gráfico
            self.graph[0][1].clear()
            self.graph[0][1].suptitle(parm.get("titulo", ""), color=self.cchart["titulo"], fontsize="medium")
            ax = self.graph[0][1].add_subplot()
            # ax.set_box_aspect(parm.get("aspect", 0.8))
            ax.set_facecolor(self.cchart["fondo_fig"])

            # posiciones y dibujo de barras horizontales
            y_pos = np.arange(len(labels))
            bars = ax.barh(y_pos, values, color=colors, height=0.6, alpha=0.9)

            # Etiquetas en eje Y
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, color=self.cchart["texto"], fontsize=7)

            # Dibuja una línea vertical para representar UnProfit (solicitud: UnProfit como línea)
            # Si UnProfit está definido, marcarlo con línea y etiqueta
            if not math.isclose(unprofit, 0.0, rel_tol=1e-12) or ("UnProfit" in data):
                ax.axvline(
                    unprofit,
                    color=self.cchart.get("axsx", "green"),
                    linestyle="--",
                    linewidth=1,
                )
                # añadir etiqueta de valor cerca de la línea (arriba a la derecha)
                x_text = unprofit
                y_text = len(labels) - 0.5
                ax.text(
                    x_text,
                    y_text,
                    " UnProfit: {:,.2f}".format(unprofit),
                    fontsize=7,
                    color=self.cchart.get("plot1", "green"),
                    va="bottom",
                    ha="left",
                    backgroundcolor=self.cchart["fondo_fig"],
                )

            # Formato de eje x y ajustes visuales
            ax.xaxis.set_major_formatter(currency)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_visible(False)
            ax.spines["top"].set_visible(False)
            ax.spines["bottom"].set_color(self.cchart["axsx"])
            ax.tick_params(axis="x", colors=self.cchart["axsx"], labelsize=6)
            ax.tick_params(axis="y", colors=self.cchart["texto"], labelsize=6)
            ax.set_xlabel(" ", fontsize=7, color=self.cchart["texto"])

            # Mostrar porcentaje relativo a Inversión encima de cada barra (si inversión > 0)
            if inversión > 0:
                for i, b in enumerate(bars):
                    width = b.get_width()
                    pct = width / inversión
                    ax.text(
                        width + (inversión * 0.01),
                        b.get_y() + b.get_height() / 2,
                        "{:> 4.1%}".format(pct),
                        fontsize=6,
                        va="center",
                        color=self.cchart["texto"],
                    )

            # ajusta ticks razonables
            xmin = min(0, min(values + [unprofit]) if values else 0)
            xmax = max(values + [unprofit]) if values else 1
            rng = xmax - xmin if (xmax - xmin) != 0 else 1
            # construir ticks de forma robusta
            ticks = np.linspace(xmin, xmax, num=4)
            ax.set_xlim([xmin - 0.05 * rng, xmax + 0.05 * rng])
            ax.set_xticks(ticks)

        except Exception as e:
            print(f"graph_ROI_vehiculo()]: {e}")

    # activos ganadores y perdedores
    def graph_gain_loss(self, data, parm):
        try:
            self.graph[1][1].clear()
            self.graph[1][1].suptitle(parm["titulo"], color=self.cchart["titulo"], fontsize="medium")
            ax = self.graph[1][1].add_subplot()
            ax.set_facecolor(self.cchart["fondo_fig"])

            # --- 1. Preparar los Datos (igual que antes) ---
            df_rendimiento = pd.DataFrame(data, columns=["Symbol", "Rendimiento"])
            df_rendimiento["Rendimiento_Pct"] = df_rendimiento["Rendimiento"] * 100

            ganadores = df_rendimiento[df_rendimiento["Rendimiento"] >= 0].nlargest(5, "Rendimiento_Pct")

            # Bear market: si no hay activos positivos, toma los 5 de menor pérdida
            if ganadores.empty:
                ganadores = df_rendimiento.nlargest(5, "Rendimiento_Pct")

            excluir_simbolos = set(ganadores["Symbol"])
            perdedores = df_rendimiento[
                (df_rendimiento["Rendimiento"] < 0) & (~df_rendimiento["Symbol"].isin(excluir_simbolos))
            ].nsmallest(5, "Rendimiento_Pct")

            # Combinar y ordenar para el gráfico único
            df_combinado = pd.concat(
                [
                    ganadores.sort_values(by="Rendimiento_Pct", ascending=False),
                    perdedores.sort_values(by="Rendimiento_Pct", ascending=True),
                ]
            )

            # Asignar colores basados en si es ganancia o pérdida
            colores = ["mediumseagreen" if r >= 0 else "tomato" for r in df_combinado["Rendimiento_Pct"]]

            ax.bar(df_combinado["Symbol"], df_combinado["Rendimiento_Pct"], color=colores)

            xlabels = ax.get_xticklabels()
            ylabels = ax.get_yticklabels()
            plt.setp(xlabels, ha="right", fontsize=6, color=self.cchart["asx"], rotation=30)
            plt.setp(ylabels, ha="right", fontsize=6, color=self.cchart["texto"])
            ax.set_xlabel("", fontsize="x-small", color=self.cchart["texto"])
            ax.set_ylabel("Rendimiento (%)", fontsize=7, color=self.cchart["texto"])

            ax.grid(axis="y", linestyle="--", alpha=0.7)
            ax.axhline(0, color=self.cchart["texto"], linewidth=0.8)  # Línea en 0%

            ax.set_xlabel("", fontsize="x-small", color=self.cchart["texto"])
            ax.tick_params(axis="x", colors=self.cchart["texto"])
            ax.tick_params(axis="y", colors=self.cchart["texto"])

            # Ajustar los límites del eje Y si es necesario para dar más espacio
            ax.set_ylim(
                df_combinado["Rendimiento_Pct"].min() * 1.2,
                df_combinado["Rendimiento_Pct"].max() * 1.2,
            )
            # self.graph[1][1].tight_layout()

        except Exception as e:
            print("[graphgraph_gain_loss()]: {}".format(e))

    # titulo Performance (acumulativo)
    def graph_performace_portafolio(self, fg=None, data=None, parm=None):
        """
        Grafica performance acumulado (eje izquierdo) y valor/costo (eje derecho).
        Entrada:
          - fg: matplotlib.figure.Figure
          - data: pd.DataFrame con las series a plotear
          - parm: dict con mapeo de etiquetas -> nombre de columna en `data`
                   keys típicas: 'BTC', '++ index', 'Value', 'Costo', 'legend', 'aspect', 'titulo'
        """
        try:
            # seguridad: datos mínimos
            if fg is None or data is None or data.empty or parm is None:
                if fg is not None:
                    fg.clear()
                return

            # limpiar figura y crear ejes
            fg.clear()
            title = parm.get("titulo", "")
            fg.suptitle(title, color=self.cchart["titulo"], fontsize="medium")
            ax = fg.add_subplot()
            ax.set_facecolor(self.cchart["fondo_fig"])

            # eje secundario (dólares / valores)
            av = ax.twinx()

            # aspecto opcional (defensivo)
            aspect = parm.get("aspect")

            # seleccionar series a graficar en orden predecible:
            # tomar valores de parm que sean strings y existan en data.columns
            series_cols = [v for k, v in parm.items() if isinstance(v, str) and v in data.columns]
            # esperamos al menos dos series para el eje izquierdo (performance comparativa)
            left_series = series_cols[:2] if len(series_cols) >= 2 else (series_cols + [None, None])[:2]

            # plot eje izquierdo (performance comparativa)
            if left_series[0]:
                ax.plot(
                    data.index,
                    data[left_series[0]],
                    color=self.cchart["plot5"],
                    linewidth=1.3,
                )
            if left_series[1]:
                ax.plot(
                    data.index,
                    data[left_series[1]],
                    color=self.cchart["plot2"],
                    linewidth=1.3,
                )

            # formateo eje X
            Xformatter = "%b-%y" if parm.get("periodo") in ("6M", "1Y", "5Y") else "%d-%b"
            ax.xaxis.set_major_formatter(mdates.DateFormatter(Xformatter))

            xlabels = ax.get_xticklabels()
            plt.setp(xlabels, ha="right", rotation=20, fontsize=6)
            ax.tick_params(axis="x", colors=self.cchart["plot5"])

            # estilos de spines y grilla
            ax.spines["bottom"].set_color(self.cchart["plot5"])
            ax.spines["left"].set_color(self.cchart["plot5"])
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.grid(True, color=self.cchart["axsx"], linewidth=0.3, axis="y", alpha=0.9)

            # eje Y izquierdo: porcentajes
            ax.set_ylabel("Performance", fontsize="x-small", color=self.cchart["axsy"])
            ax.yaxis.set_major_formatter(porcentaje)
            ylabels = ax.get_yticklabels()
            plt.setp(ylabels, ha="right", fontsize=6)
            ax.tick_params(axis="y", colors=self.cchart["plot5"])

            # eje derecho: Value / Costo (si existen)
            value_col = parm.get("Value") if parm.get("Value") in data.columns else None
            costo_col = parm.get("Costo") if parm.get("Costo") in data.columns else None

            # si no están mediante parm, intentar detectar en series_cols
            if value_col is None and "value" in data.columns:
                value_col = "value"
            if costo_col is None and "costo_base" in data.columns:
                costo_col = "costo_base"

            # Dibujar como barras: costo_col como barra de fondo, value_col como barra interior
            if value_col or costo_col:
                # calcular width en días (para índices datetime) de forma robusta
                try:
                    if isinstance(data.index, pd.DatetimeIndex) and len(data.index) > 1:
                        diffs = data.index.to_series().diff().dropna()
                        if not diffs.empty:
                            # ancho en días (mediana)
                            width_days = diffs.median().total_seconds() / 86400.0
                        else:
                            width_days = 0.8
                    else:
                        # índice no-datetime o único punto: usar ancho por defecto
                        width_days = 0.8
                except Exception:
                    width_days = 0.8

                # ancho para barras costo (fondo) y para value (interior)
                width_costo = width_days * 0.9
                width_value = width_days * 0.5

                # Si sólo existe costo_col -> dibujar barras de costo
                if costo_col and not value_col:
                    av.bar(
                        data.index,
                        data[costo_col],
                        width=width_costo,
                        color=self.cchart["plot31"],
                        alpha=0.35,
                        align="center",
                        edgecolor="none",
                    )

                    # Marca costo en el eje y
                    l_ix = len(data.index)
                    ycos = data[costo_col].iloc[-1] if costo_col else None
                    av.plot(l_ix, ycos, marker=">", color=self.cchart["plot3"])

                # Si existe value_col y no costo_col -> dibujar barras de value
                elif value_col and not costo_col:
                    av.bar(
                        data.index,
                        data[value_col],
                        width=width_value,
                        color=self.cchart["plot1"],
                        alpha=0.9,
                        align="center",
                        edgecolor="none",
                    )

                    # Marca value en el eje y
                    yval = data[value_col].iloc[-1] if value_col else None
                    av.plot(l_ix, yval, marker=">", color=self.cchart["plot8"])

                # Si existen ambas -> dibujar costo como fondo y value encima
                elif value_col and costo_col:
                    av.bar(
                        data.index,
                        data[costo_col],
                        width=width_costo,
                        color=self.cchart["plot31"],
                        alpha=0.35,
                        align="center",
                        edgecolor="none",
                        label=costo_col,
                    )
                    av.bar(
                        data.index,
                        data[value_col],
                        width=width_value,
                        color=self.cchart["plot1"],
                        alpha=0.9,
                        align="center",
                        edgecolor="none",
                        label=value_col,
                    )

                    # Marca costo en el eje y
                    l_ix = data.index[-1]
                    ycos = data[costo_col].iloc[-1] if costo_col else None
                    yval = data[value_col].iloc[-1] if value_col else None
                    av.plot(l_ix, yval, marker=">", color=self.cchart["plot9"])
                    av.plot(l_ix, ycos, marker=">", color=self.cchart["plot31"])

                    if yval is not None and ycos is not None:
                        pmedio = max(ycos, yval) - abs(yval - ycos) / 2
                        performa = (yval - ycos) / ycos if ycos != 0 else 0.0
                        # ycolor =  self.cchart["plot8"] if performa > 0 else self.cchart["plot31"]
                        ycolor = self.cchart["texto"]
                        av.annotate(
                            f"{performa:>3.1%}",
                            xy=(l_ix, pmedio),
                            xytext=(l_ix, pmedio),  # desplaza 5% arriba
                            fontsize=5,
                            color=ycolor,
                            ha="left",
                        )

                    # Opcional: si se quiere sombrear diferencias (cuando costo > value)
                    try:
                        mask = data[costo_col].notna() & data[value_col].notna()
                        if mask.any():
                            av.fill_between(
                                data.index[mask],
                                data[costo_col][mask],
                                data[value_col][mask],
                                where=(data[costo_col][mask] > data[value_col][mask]),
                                facecolor=self.cchart["plot3"],
                                alpha=0.12,
                                interpolate=True,
                            )
                    except Exception:
                        pass

            # formateo eje derecho
            av.set_ylabel("Dolar US", fontsize="x-small", color=self.cchart["plot1"])
            av.yaxis.set_major_formatter(currency)
            tlabels = av.get_yticklabels()
            plt.setp(tlabels, ha="left", fontsize=6, color=self.cchart["plot1"])
            av.tick_params(axis="y", colors=self.cchart["plot1"])
            av.spines["right"].set_color(self.cchart["plot1"])
            av.spines["right"].set_visible(True)
            av.axhline(0, linewidth=0.6, ls="--", color=self.cchart["plot1"])

            # línea 0 en eje izquierdo para referencia
            ax.axhline(0, linewidth=0.6, ls="--", color=self.cchart["texto"])

            # leyenda: construimos patches según las series dibujadas
            patches = []
            if left_series[0]:
                patches.append(mpatches.Patch(color=self.cchart["plot5"], label=left_series[0]))
            if left_series[1]:
                patches.append(mpatches.Patch(color=self.cchart["plot2"], label=left_series[1]))
            if value_col:
                patches.append(mpatches.Patch(color=self.cchart["plot1"], label="Values Market", alpha=0.45))
            if costo_col:
                patches.append(mpatches.Patch(color=self.cchart["plot3"], label="Cost Base", alpha=0.35))

            legend_loc = parm.get("legend", "upper left")
            if patches:
                fg.legend(handles=patches, loc=legend_loc, fontsize=5)

            # ajustar límites Y de forma robusta (si es necesario)
            try:
                left_vals = []
                for s in left_series:
                    if s and s in data.columns:
                        left_vals.append(data[s].dropna().values)
                if left_vals:
                    all_left = np.concatenate(left_vals)
                    ymin, ymax = np.nanmin(all_left), np.nanmax(all_left)
                    if ymin != ymax:
                        rng = ymax - ymin
                        ax.set_ylim(ymin - 0.05 * rng, ymax + 0.05 * rng)
            except Exception:
                pass
        except Exception as e:
            print(f"graph_performace_portafolio(): {e}")

    # (thread): coordinador de actualización de graficos
    def run_graficos(self):
        # estructura datos de positions
        def datos_grafico():
            wvals, wlabe, wrati = [], [], []
            wdebi, wprof, GainLoss = [], [], []
            tcos, tpro, tunr, cash = 0, 0, 0, 0
            ocos, opro, ounr, odeu, opes = 0, 0, 0, 0, 0

            i = 0
            orden = [{"GyP": "unrealizedpnl"}, "DES"]
            cartera = sort_positions(self.positions, orden)

            for i, key in enumerate(cartera):
                pobj = 0 if key["unrealizedpnl"] < 0 else key["unrealizedpnl"]
                tcos += key["costobase"]
                tunr += key["unrealizedpnl"]
                tpro += pobj

                rend = key["unrealizedpnl"] / key["costobase"] if key["costobase"] > 10 else 0
                if rend > -0.8:
                    GainLoss.append(
                        {
                            "Symbol": key["ticket"],
                            "Rendimiento": key["unrealizedpnl"] / key["costobase"],
                        }
                    )

                if i < 4:
                    wvals.append([key["costobase"], pobj])
                    wrati.append(key["unrealizedpnl"])
                    wprof.append(0 if key["unrealizedpnl"] < 0 else key["unrealizedpnl"])
                    wdebi.append(key["deuda"])
                    ticket = convierte_ticket_crypto(key["ticket"])[0:10]
                    wlabe.append(ticket)
                else:
                    ocos += key["costobase"]
                    ounr += key["unrealizedpnl"]
                    odeu += key["deuda"]
                    opes += key["peso"]
                # i += 1

            if i > 4:
                wrati.append(ounr)
                wdebi.append(odeu)
                wlabe.append("Otros")

            if self.vehiculo in ("Stock", "BBVA.ARS"):
                if self.resumen:
                    cash = float(self.resumen[" Cash       :"])
                pdatos = {
                    "Inversión": tcos,
                    "UnProfit": tpro,
                    "UnP&l": tunr,
                    "Cash": cash,
                }

            elif self.vehiculo == "Crypto":
                pdatos = {
                    "Inversión": tcos,
                    "UnProfit": tpro,
                    "UnP&l": tunr,
                    "Cash": -sum(wdebi),
                }

            # Obtiene Dataframe de performance
            ddatos = performa_asset(account=self.account, vehiculo=self.vehiculo, tipo=self.vehiculo)
            return pdatos, ddatos, GainLoss

        try:
            (Pdatos, self.Ddatos, GainLoss) = datos_grafico()

            parm = {"titulo": "ROI " + self.vehiculo, "aspect": 0.80}
            self.graph_ROI_vehiculo(Pdatos, parm)
            self.graph[0][0].draw()

            # reemplazar o mejorar Gráfico por 5 mejores y peores desempeño
            parm = {"titulo": "Top 5 - Gain/Loss " + self.vehiculo, "aspect": 0.40}
            self.graph_gain_loss(data=GainLoss, parm=parm)
            self.graph[1][0].draw()

            # ajusta gráfico performance portafolio i setea a 1
            self.setup_graph_performace(tipo="1Y")

        except Exception as e:
            print(f"[run_gráficos()]: {e}")

    def comprar_simbolo_nuevo(self):
        """Abre ventana de compra para un símbolo que no está en la cartera"""
        symbol = self.entry_new_symbol.get().strip().upper()

        if not symbol:
            MyMessageBox(self.master).showinfo(
                title="Buy - New symbol", message="Debe ingresar el símbolo que desea comprar"
            )
            return

        precio = 0.0
        conid = None

        try:

            # obtiene conid desde tabla otros_activos
            if self.vehiculo == "Crypto":
                response = self.BClient.ticker_price(symbol=symbol)
                if response and "price" in response:
                    precio = float(response["price"])
                    crypto, found = self.RepositorioOportunidades.select_otros_activos(
                        accout=self.account, symbol=symbol
                    )
                    conid = crypto[0]["idcrypto"] if found else None

                else:
                    MyMessageBox(self.master).showinfo(
                        title="Buy - New symbol",
                        message=f"Símbolo {symbol} no encontrado en los activos {self.vehiculo}",
                    )
                    return

            # Busca en Interactive Brokers (Stock)
            elif self.vehiculo == "Stock":
                response = self.IClient._get_symbol(symbol=symbol, secType="STK")
                if not response:
                    MyMessageBox(self.master).showinfo(
                        title="Buy - New symbol",
                        message=f"Símbolo {symbol} no encontrado en los activos {self.vehiculo}",
                    )
                    return

                conid = response.get("conid")

                # Campo "31" puede no estar disponible si el websocket aún no suscribió el símbolo
                market_data = response.get("market_data") or {}
                precio_str = market_data.get("31")
                if precio_str:
                    precio = float(precio_str)
                else:
                    # Fallback: obtener precio desde yfinance
                    result = get_yfinance(ticket=symbol, vehiculo="Stock")
                    if result:
                        activos, _ = result
                        precio = float(activos.get("previous_close") or activos.get("open") or 0)
                    if not precio:
                        MyMessageBox(self.master).showinfo(
                            title="Buy - New symbol",
                            message=f"Símbolo {symbol}: websocket no suscripto aún. Reintenta en unos segundos.",
                        )
                        return
        except Exception as e:
            MyMessageBox(self.master).showinfo(title="Buy - New symbol", message=f"Error: {symbol} no válido")
            traceback.print_exc()
            return

        # Configura el símbolo para la compra
        if conid:
            self.symbol = symbol
            self.gchar["ticket"] = symbol
            self.gchar["position"] = False
            self.gchar["objetivo"] = 0.0
            self.gchar["avgCost"] = 0.0
            self.gchar["mkPrice"] = precio
            self.gchar["stock"] = 0.0
            self.gchar["conid"] = conid

            # Abre ventana de trading para el nuevo símbolo
            self.trader_lotes_fiscales(option="BUY", parm=self.gchar)

        # inicializa variable de entrada
        self.entry_new_symbol.delete(0, tk.END)


# =================================================================================================
#  Helper
#
# =================================================================================================
# Class para el manejo de treeview
class CustomTreeview:
    def __init__(
        self,
        master,
        columns,
        fixed_columns=None,
        fixed_row=False,
        show_vscroll=True,
        show_hscroll=True,
        sort_columns=False,
        height=10,
        column_alignments=None,
        show_headings=True,
        style=None,
    ):
        """
        Constructor para crear un Treeview personalizado.

        Args:
            parent: El widget padre (como un Frame o la ventana principal).
            columns: Lista de nombres de columnas.
            fixed_columns: Lista de columnas que serán fijas (opcional).
            fixed_row: Índice de la fila que será fija (opcional).
            show_vscroll: Booleano, muestra o no la barra de scroll vertical.
            show_hscroll: Booleano, muestra o no la barra de scroll horizontal.
            height: Altura del Treeview (número de filas visibles).
            column_alignments: Diccionario para alinear columnas, ej: {'Nombre': 'center', 'Edad': 'right'}.
        """
        self.parent = master
        self.columns = columns
        self.fixed_columns = fixed_columns or []
        self.sort_columns = sort_columns
        self.fixed_row = fixed_row
        self.show_vscroll = show_vscroll
        self.show_hscroll = show_hscroll
        self.height = height
        self.column_alignments = column_alignments or {}
        self.arbol = {}
        self.style = style or ttk.Style()
        show_fixed_row = "headings" if not self.fixed_row else "tree"

        # Crear los frames
        self.master = tk.Frame(self.parent)
        self.heard = tk.Frame(self.parent)
        self.right = tk.Frame(self.parent)
        self.right.pack(side=tk.RIGHT, fill=tk.Y, expand=True)
        self.heard.pack(side=tk.TOP, fill=tk.X)
        self.master.pack(side=tk.BOTTOM, fill=tk.X)
        if show_headings:
            self.heard_fixed, self.heard_scroll = self.create_treeview(
                master=self.heard, show="headings", height=1, style=self.style
            )

        self.tree_fixed, self.tree_scroll = self.create_treeview(
            master=self.master, show="headings", height=self.height, style=self.style
        )

        # set movimientos del mouse.
        self.tree_fixed.bind("<MouseWheel>", self.on_mouse_wheel)
        self.tree_scroll.bind("<MouseWheel>", self.disable_mousewheel)
        self.tree_scroll.bind("<Motion>", self.disable_mousewheel)
        self.tree_fixed.bind("<Motion>", self.disable_mousewheel)

        # set selección de items
        self.tree_fixed.bind("<<TreeviewSelect>>", self.sync_fixed_selection)

        # Sincronizar el scroll vertical si se habilita
        if self.show_vscroll:
            self.vscroll = ttk.Scrollbar(self.right, orient="vertical", command=self.on_sync_vtreeview_scroll)
            self.vscroll.pack(side=tk.RIGHT, fill=tk.Y)
            self.tree_fixed.config(yscrollcommand=self.vscroll.set)
            self.tree_scroll.config(yscrollcommand=self.vscroll.set)

        # Sincronizar el scroll horizontal si se habilita
        if self.show_hscroll:
            if not self.fixed_row:
                self.hscroll = ttk.Scrollbar(self.master, orient="horizontal", command=self.tree_scroll.xview)
                self.hscroll.pack(side=tk.BOTTOM, fill=tk.X)
                self.tree_scroll.config(xscrollcommand=self.hscroll.set)

            if self.fixed_row:
                self.hscroll = ttk.Scrollbar(
                    self.master,
                    orient="horizontal",
                    command=self.on_sync_htreeview_scroll,
                )
                self.hscroll.pack(side=tk.BOTTOM, fill=tk.X)
                self.tree_scroll.config(xscrollcommand=self.hscroll.set)
                self.heard_scroll.config(xscrollcommand=self.hscroll.set)

        # Configurar los treeviews header
        if self.fixed_row:
            self.heard_fixed.pack(side=tk.LEFT)
            self.heard_scroll.pack(side=tk.RIGHT, expand=True)
            self.tree_fixed.pack(side=tk.LEFT)
            self.tree_scroll.pack(side=tk.RIGHT, expand=True)

        # Configurar los treeviews clasico
        if not self.fixed_row:
            self.tree_fixed.pack(side=tk.LEFT)
            self.tree_scroll.pack(side=tk.RIGHT, fill=tk.X)

        # Configurar los heading treeviews para el detalle
        if (show_fixed_row == "tree") or (not show_headings):
            self.config(show="tree")
            self.tree_fixed.configure(show="tree")
            self.tree_scroll.configure(show="tree")

    # creación de treeview, con o sin fixed row
    def create_treeview(self, master=None, show=None, height=None, style=None):
        def ordenar_columnas(col_tree, col, reverse):
            def sort_key(val):
                v = (val or "").strip()
                if v.endswith("%"):
                    try:
                        return (0, float(v[:-1]))
                    except ValueError:
                        pass
                try:
                    return (0, float(v))
                except (ValueError, TypeError):
                    return (1, v.lower())

            data = [(col_tree.set(k, col), k) for k in col_tree.get_children("")]
            data.sort(key=lambda x: sort_key(x[0]), reverse=reverse)

            # Reorganizar los valores de cada Treeview sincronizadamente
            for index, (val, k) in enumerate(data):
                col_tree.move(k, "", index)

                # Mover el mismo índice en las otras columnas
                trees = [self.tree_fixed, self.tree_scroll]
                for tree in trees:
                    if tree != col_tree:
                        tree.move(k, "", index)

            # Alternar entre ascendente y descendente
            col_tree.heading(col, command=lambda: ordenar_columnas(col_tree, col, not reverse))

        if not self.fixed_columns:
            return

        # construye parte fixed
        tree_fixed = ttk.Treeview(master, columns=self.fixed_columns, show=show, height=height)
        tree_fixed.heading("#0")
        tree_fixed.column("#0", width=0, minwidth=1)

        for col in self.fixed_columns:

            # activa ordainment por columna
            if self.sort_columns:
                tree_fixed.heading(
                    col,
                    text=col,
                    command=lambda _col=col, _tree=tree_fixed: ordenar_columnas(_tree, _col, False),
                )
            else:
                tree_fixed.heading(col, text=col)

            anchor = self.column_alignments[col]["anchor"] if col in self.column_alignments.keys() else "center"
            width = self.column_alignments[col]["width"] if col in self.column_alignments.keys() else "60"

            tree_fixed.column(col, width=width, anchor=anchor)

        # construye parte scrollable
        scrollable_columns = [col for col in self.columns if col not in self.fixed_columns]
        tree_scroll = ttk.Treeview(master, columns=scrollable_columns, show=show, height=height)
        tree_scroll.heading("#0")
        tree_scroll.column("#0", width=0, minwidth=1)

        for col in scrollable_columns:
            if show != "tree":
                anchor = self.column_alignments[col]["anchor"] if col in self.column_alignments.keys() else "center"
                width = self.column_alignments[col]["width"] if col in self.column_alignments.keys() else "60"

                # activa ordainment por columna
                if self.sort_columns:
                    tree_scroll.heading(
                        col,
                        text=col,
                        command=lambda _col=col, _tree=tree_scroll: ordenar_columnas(_tree, _col, False),
                    )
                else:
                    tree_scroll.heading(col, text=col)

                tree_scroll.column(col, width=width, anchor=anchor)

        return tree_fixed, tree_scroll

    # Scroll cuando se usa la rueda del ratón
    def on_mouse_wheel(self, event):
        self.tree_fixed.yview_scroll(-1 * (event.delta // 120), "units")
        self.tree_scroll.yview_scroll(-1 * (event.delta // 120), "units")
        return "break"  # Evita que el evento se propague a otros widgets

    @staticmethod
    # Función para bloquear el scroll del mouse**
    def disable_mousewheel(event):
        return "break"  # Evita que el evento pase al Treeview

    # Sincronizar el scroll vertical entre los dos Treeviews.
    def on_sync_vtreeview_scroll(self, *args):
        self.tree_fixed.yview(*args)
        self.tree_scroll.yview(*args)

    # Función para sincronizar el desplazamiento horizontal de ambos Treeview
    def on_sync_htreeview_scroll(self, *args):
        self.heard_scroll.xview(*args)
        self.tree_scroll.xview(*args)

    # Función para sincronizar la selección
    def sync_fixed_selection(self, event):
        selected_item = self.tree_fixed.selection()
        self.tree_scroll.selection_set(selected_item)

    def insert_row(self, padre=None, texto=None, values=None, summary=None):
        """Método para insertar una fila en los Treeviews.
        Values: para detalle y
        summary: para línea de totales"""
        if self.fixed_columns:
            if values is not None:
                fixed_values = values[: len(self.fixed_columns)]
                scrollable_values = values[len(self.fixed_columns) :]

                # treeview simple
                if texto is None and padre is None:
                    self.tree_fixed.insert("", "end", values=fixed_values)
                    self.tree_scroll.insert("", "end", values=scrollable_values)

                else:
                    # treeview tipo arbol
                    if padre is None:
                        fixed = self.tree_fixed.insert("", "end", text=texto, values=fixed_values)
                        scroll = self.tree_scroll.insert("", "end", values=scrollable_values)
                        self.arbol.update({texto: {"fixed": fixed, "scroll": scroll}})

                        self.tree_fixed.item(fixed, open=True)
                        self.tree_scroll.item(scroll, open=True)
                    else:
                        fixed = self.arbol[padre]["fixed"]
                        scroll = self.arbol[padre]["scroll"]

                        items = self.tree_fixed.insert(fixed, "end", values=fixed_values)
                        posts = self.tree_scroll.insert(scroll, "end", values=scrollable_values)

        if self.fixed_row:
            if summary is not None:

                left_values = summary[: len(self.fixed_columns)]
                right_values = summary[len(self.fixed_columns) :]

                self.heard_fixed.insert("", "end", values=left_values)
                self.heard_scroll.insert("", "end", values=right_values)

    def delete_row(self):

        for item_id in self.tree_fixed.get_children():
            self.tree_fixed.delete(item_id)

        for item_id in self.tree_scroll.get_children():
            self.tree_scroll.delete(item_id)

    def config(self, show=None, height=None):
        if show is not None:
            self.tree_fixed.configure(show=show)
            self.tree_scroll.configure(show=show)

        if height is not None:
            self.tree_fixed.configure(height=height)
            self.tree_scroll.configure(height=height)


# class para el manejo de datos de mercado
class MyWebsocket:
    def __init__(self, url, logger, vehiculo, assets, idsymbol, *args, **kwargs):
        # super().__init__(url, *args, **kwargs)
        self.logger = logger
        self.vehiculo = vehiculo
        self.url = url
        self.assets = assets
        self.idsymbol = idsymbol
        self.counter = 0
        self.procesos = DataHub.procesos
        self.limit = 10
        self.ws = None

        def on_message(ws, message):
            self.my_message(message)

        def on_error(ws, e):
            pass

        def on_open(ws):
            print("WebSocket connection opened({}):".format(self.vehiculo))

            # recibe órdenes activas de stock
            subscribe_to_idsymbol()
            subscribe_get_order()

        def force_close(ws):
            # self.ws.close()
            pass

        def on_close(ws):
            print("WebSocket connection closed():", self.vehiculo)

        def subscribe_get_order():
            time.sleep(3)
            payload = {
                "type": "request",
                "topic": "sor",  # Suscribirse a Smart Order Routing (órdenes)
            }
            self.ws.send("sor+{}")
            # self.ws.send(json.dumps(payload))

        # inicia symbol en websocket
        def subscribe_to_idsymbol():
            try:
                time.sleep(3)
                if self.idsymbol:
                    for conid in self.idsymbol:
                        self.ws.send(
                            "smd+"
                            + conid
                            + '+{"fields": ["31","55","70","71","76","82","84","86","7051","7292","7295","7296","7281","7286","7287","7288","7671","7672"]}'
                        )

                    print("subscribe_stocks({})".format(len(self.idsymbol)))

                else:
                    raise ValueError("La lista  self.idsymbol está vacía. No se puede continuar.")

            except Exception as e:
                print("[subscribe_stock()]: {}".format(e))

        def update_subscribe(new_idsymbol):
            try:
                with self.lock:
                    unsubscribe_params = [f"{crypto.lower()}@miniTicker" for crypto in self.idsymbol]
                    self.ws.send(
                        json.dumps(
                            {
                                "method": "UNSUBSCRIBE",
                                "params": unsubscribe_params,
                                "id": 2,
                            }
                        )
                    )
                    print("Unsubscribed from idsymbol:", self.idsymbol)
                    self.idsymbol = new_idsymbol
                    self.subscribe_to_idsymbol()

            except Exception as e:
                print("[MyWebsocket.update_subscribe_{}()]: {}".format(self.vehiculo, e))
                time.sleep(5)

        self.ws = websocket.WebSocketApp(
            url=self.url,
            on_open=on_open,
            on_error=on_error,
            on_close=on_close,
            on_message=on_message,
        )

    # (thread): para ejecutar websocket
    def my_message(self, message):
        message = self.message_json

    def websocket_loop(self, limit=10):
        try:
            if self.ws:
                self.ws.close()

            sslopt = {"cert_reqs": ssl.CERT_NONE}
            self.limit = limit
            self.ws.run_forever(sslopt=sslopt, ping_interval=60, ping_timeout=10)

        except Exception as e:
            print("[MyWebsocket.run_({})]: {}".format(self.vehiculo, e))


# Class para el manejo de mensajes
class MyMessageBox(tk.Toplevel):
    def __init__(self, parent=None, bg="skyblue", fg="black", font=("Arial", 10)):
        """Constructor para crear un cuadro de mensaje personalizado.
        Args:
        - title (str): Título de la ventana.
        - message (str): Mensaje que se mostrará.
        - bg (str): Color de fondo.
        - fg (str): Color del texto.
        - font (tuple): Fuente del texto.
        """
        parent = get_root(parent)
        super().__init__(parent)
        self.withdraw()  # Ocultar hasta que se llame showinfo/askquestion

        # Crear la ventana modal
        self.bg = bg
        self.fg = fg
        self.font = font
        self.attributes("-toolwindow", 1)
        self.configure(bg=bg)

        ancho_pantalla = self.winfo_screenwidth()
        alto_pantalla = self.winfo_screenheight()

        # Obtener dimensiones de la ventana
        ancho_ventana = 400
        alto_ventana = 150

        # Calcular posición para centrar
        x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        y = (alto_pantalla // 2) - (alto_ventana // 2)

        self.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")
        self.left = tk.Frame(self, bg=self.bg)
        self.right = tk.Frame(self, bg=self.bg)
        self.bottom = ttk.Frame(self, padding=(3, 3, 15, 3), style="W.TFrame")

        self.bottom.pack(side=tk.BOTTOM, fill=tk.X)
        self.left.pack(side=tk.LEFT, fill=tk.Y)
        self.right.pack(side=tk.LEFT, fill=tk.Y)

        self.Bdsystem = BDsystem()

    # Etiqueta para el mensaje informativo
    def showinfo(self, title, message):
        self.deiconify()  # Mostrar la ventana ahora que tiene contenido

        # agrega icono de mensaje ----------------------------------------------------------------------------------
        imagen0, xlis = BDsystem.select_objeto(codigo=18)
        imagen = Image.open(io.BytesIO(imagen0))
        imagen = imagen.resize((48, 48), Image.ADAPTIVE)
        imagen_tk = ImageTk.PhotoImage(imagen)
        button = tk.Button(self.left, image=imagen_tk, bg=self.bg, relief=tk.FLAT)
        button.imagen = imagen_tk

        message_label = tk.Label(
            self.right,
            text=message,
            justify="center",
            wraplength=300,
            bg=self.bg,
            fg=self.fg,
            font=self.font,
        )
        message_label.pack(fill=tk.X, pady=20, expand=True)

        # Botón de cierre
        close_button = tk.Button(
            self.bottom,
            text="Aceptar",
            width=8,
            bg="grey",
            fg="black",
            font=self.font,
            command=self.destroy,
        )
        close_button.pack(side=tk.RIGHT, pady=10)
        button.pack(padx=10, pady=10)

        # Hacer que sea una ventana modal
        self.title(title)
        self.transient()  # Evitar que se minimice por separado
        self.grab_set()  # Bloquear interacción con la ventana principal
        self.wait_window()  # Esperar hasta que se cierre

    def askquestion(self, title, message):
        self.deiconify()  # Mostrar la ventana ahora que tiene contenido

        def respuesta(accion):
            nonlocal ask
            ask = accion
            self.destroy()

        ask = "no"

        # agrega icono de mensaje ----------------------------------------------------------------------------------
        imagen0, xlis = BDsystem.select_objeto(codigo=19)
        imagen = Image.open(io.BytesIO(imagen0))
        imagen = imagen.resize((48, 48), Image.ADAPTIVE)
        imagen_tk = ImageTk.PhotoImage(imagen)
        button = tk.Button(self.left, image=imagen_tk, bg=self.bg, relief=tk.FLAT)
        button.imagen = imagen_tk

        message_label = tk.Label(
            self.right,
            text=message,
            justify="center",
            bg=self.bg,
            fg=self.fg,
            font=self.font,
        )
        message_label.pack(fill=tk.X, pady=20, expand=True)

        # Botón Yes
        yes = tk.Button(
            self.bottom,
            text="Si",
            width=8,
            bg="grey",
            fg="black",
            font=self.font,
            command=lambda: respuesta("yes"),
        )
        # Botón Nos
        no = tk.Button(
            self.bottom,
            text="No",
            width=8,
            bg="grey",
            fg="black",
            font=self.font,
            command=lambda: respuesta("no"),
        )

        no.pack(side=tk.RIGHT, padx=3, pady=10)
        yes.pack(side=tk.RIGHT, padx=3, pady=10)
        button.pack(padx=10, pady=10)

        # Hacer que sea una ventana modal
        self.title(title)
        self.transient()  # Evitar que se minimice por separado
        self.grab_set()  # Bloquear interacción con la ventana principal
        self.wait_window()  # Esperar hasta que se cierre

        return ask

    # Asignar un alias al método
    showwarning = showinfo
    showerror = showinfo


# Class para el manejo de Switch
class ToggleSwitch(ttk.Checkbutton):
    def __init__(self, master=None, on_text="ON", off_text="OFF", command=None, **kwargs):
        # Utiliza un estilo personalizado para el widget
        # style = ttk.Style()

        self.on_text = on_text
        self.off_text = off_text

        # Variable para el estado del botón
        self.var = tk.StringVar(value=self.on_text)

        super().__init__(
            master,
            text=self.off_text,
            variable=self.var,
            onvalue=self.on_text,
            offvalue=self.off_text,
            style="T.TCheckbutton",
            command=self.toggle_state,
            **kwargs,
        )

        # Guarda el comando del usuario para ejecutarlo después
        self.user_command = command
        self.toggle_state()

    def toggle_state(self):
        # Cambia el texto del botón al hacer clic
        if self.var.get() == self.on_text:
            self["text"] = self.on_text
            self["style"] = "T.TCheckbutton"
        else:
            self["text"] = self.off_text
            self["style"] = "T.TCheckbutton"

        # Ejecuta el comando del usuario si existe
        if self.user_command:
            self.user_command(self.var.get() == self.on_text)


# controla barra de progreso
class ProgressBar(tk.Frame):
    """
    Widget de Tkinter que muestra una barra de progreso financiera visual.

    Parámetros:
        master: Widget padre
        partida: Valor inicial
        avance: Valor actual alcanzado
        proyeccion: Valor objetivo
        width: Ancho del canvas en píxeles (default: 400)
        height: Alto de la barra en píxeles (default: 40)
        bg_color: Color de fondo
        progress_color: Color de la barra de progreso
        border_color: Color del borde
    """

    def __init__(
        self,
        master=None,
        label="",
        partida=0,
        avance=0,
        proyeccion=100,
        width=400,
        height=40,
        bg_color="#2C3E50",
        fg_color="#FFFFFF",
        progress_color="#27AE60",
        border_color="#ECF0F1",
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self.label_text = label
        self.label_cavas = None
        self.partida = partida
        self.avance = avance
        self.proyeccion = proyeccion
        self.width = width
        self.height = height
        self.bg_cavas = "#2C3E50"
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.progress_color = progress_color
        self.border_color = border_color

        self._create_widgets()
        self.update_values(partida, avance, proyeccion)

    def _create_widgets(self):
        """Crea los widgets internos del componente"""

        # Obtener color de fondo del padre
        try:
            parent_bg = self.master.cget("bg")
        except:
            parent_bg = self.bg_color

        # Frame principal contenedor alineado a la izquierda
        main_container = tk.Frame(self, bg=parent_bg)
        main_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, anchor=tk.W)

        # Label en la parte superior
        if self.label_text:
            self.label_cavas = tk.Label(
                main_container,
                text=self.label_text,
                font=("Segoe UI", 9),
                bg=self.bg_color,
                fg="#121414",
                anchor=tk.W,
            )
            self.label_cavas.pack(side=tk.TOP, anchor=tk.W, padx=1, pady=(0, 2))

        # Canvas para la barra de progreso
        canvas_container = tk.Frame(main_container, bg=self.bg_cavas, bd=0)
        canvas_container.pack(side=tk.TOP, anchor=tk.W, padx=5, pady=(0, 5))

        self.canvas = tk.Canvas(
            canvas_container,
            width=self.width,
            height=self.height,
            bg=self.bg_cavas,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(padx=2, pady=1)

        # Frame para labels inferiores (partida y proyección)
        info_frame = tk.Frame(main_container, bg=self.bg_color)
        info_frame.pack(side=tk.TOP, fill=tk.X, anchor=tk.W, padx=5, pady=(0, 0))

        # Labels para mostrar valores con mejor tipografía
        self.label_partida = tk.Label(
            info_frame,
            text="0",
            font=("Segoe UI", 8),
            bg=self.bg_color,
            fg=self.fg_color,
            anchor=tk.W,
        )
        self.label_partida.pack(side=tk.LEFT)

        self.label_proyeccion = tk.Label(
            info_frame,
            text="0",
            font=("Segoe UI", 8),
            bg=self.bg_color,
            fg=self.fg_color,
            anchor=tk.E,
        )
        self.label_proyeccion.pack(side=tk.RIGHT)

    def update_values(self, partida, avance, proyeccion):
        """
        Actualiza los valores de la barra de progreso.

        Args:
            partida: Valor inicial (puede ser negativo)
            avance: Valor actual alcanzado (puede ser negativo)
            proyeccion: Valor objetivo
        """
        # Permitir valores negativos
        self.partida = partida
        self.avance = avance
        self.proyeccion = proyeccion if proyeccion != 0 else 1

        self._draw_progress_bar()
        self._update_labels()

    def _draw_progress_bar(self):
        """Dibuja la barra de progreso en el canvas con diseño moderno"""
        # Limpiar canvas
        self.canvas.delete("all")

        # Calcular rango total (para manejar valores negativos)
        min_val = min(self.partida, 0, self.avance)
        max_val = max(self.proyeccion, self.partida, self.avance)
        total_range = max_val - min_val if max_val != min_val else 1

        # Calcular posiciones normalizadas (0 a 1)
        zero_position = (0 - min_val) / total_range if total_range > 0 else 0
        avance_position = (self.avance - min_val) / total_range if total_range > 0 else 0

        # Convertir a píxeles
        zero_pixel = int(self.width * zero_position)
        avance_pixel = int(self.width * avance_position)

        # Radio para bordes redondeados
        radius = min(8, self.height // 4)

        # Dibujar fondo de la barra con bordes redondeados
        self._draw_rounded_rect(0, 0, self.width, self.height, radius, fill=self.bg_cavas)

        # Calcular ancho de la barra (desde 0 hasta avance)
        if self.avance >= 0:
            # Valor positivo: dibuja desde zero_pixel hacia la derecha
            progress_start = zero_pixel
            progress_end = avance_pixel
        else:
            # Valor negativo: dibuja desde avance_pixel hasta zero_pixel
            progress_start = avance_pixel
            progress_end = zero_pixel

        progress_width = abs(progress_end - progress_start)

        # Dibujar línea de cero si hay valores negativos
        if min_val < 0:
            self.canvas.create_line(
                zero_pixel,
                0,
                zero_pixel,
                self.height,
                fill="#95A5A6",
                width=2,
                dash=(3, 3),
            )

        # Dibujar progreso con bordes redondeados
        if progress_width > 5:
            # Color dinámico según si es positivo o negativo
            if self.avance >= 0:
                # Valores positivos en verde
                if self.proyeccion > 0:
                    percent = self.avance / self.proyeccion
                    if percent >= 1.0:
                        color = "#27AE60"  # Verde completo
                    elif percent >= 0.75:
                        color = "#2ECC71"  # Verde claro
                    elif percent >= 0.5:
                        color = "#F39C12"  # Naranja
                    else:
                        color = "#E67E22"  # Naranja oscuro
                else:
                    color = "#27AE60"
            else:
                # Valores negativos en rojo
                color = "#E74C3C"  # Rojo

            # Barra de progreso principal
            self._draw_rounded_rect(progress_start, 0, progress_end, self.height, radius, fill=color)

            # Efecto de brillo en la parte superior
            self._draw_rounded_rect(
                progress_start,
                0,
                progress_end,
                self.height // 3,
                radius,
                fill=self._lighten_color(color, 60),
            )

            # Sombra interna en la parte inferior
            self.canvas.create_rectangle(
                progress_start,
                self.height * 0.7,
                progress_end,
                self.height,
                fill=self._darken_color(color),
                outline="",
            )

        # Dibujar marcador de inicio (partida) si es diferente de cero
        if self.partida != 0:
            partida_position = (self.partida - min_val) / total_range if total_range > 0 else 0
            partida_pos = int(partida_position * self.width)
            # Línea del marcador
            self.canvas.create_line(partida_pos, 3, partida_pos, self.height - 3, fill="#E74C3C", width=3)
            # Círculo superior
            self.canvas.create_oval(
                partida_pos - 4,
                -2,
                partida_pos + 4,
                6,
                fill="#E74C3C",
                outline="#C0392B",
                width=1,
            )

        # Dibujar marcador de objetivo (proyección)
        proyeccion_position = (self.proyeccion - min_val) / total_range if total_range > 0 else 1
        proyeccion_pos = int(proyeccion_position * self.width)
        arrow_size = min(12, self.height // 3)
        self.canvas.create_polygon(
            proyeccion_pos - arrow_size,
            self.height // 2 - arrow_size,
            proyeccion_pos - arrow_size,
            self.height // 2 + arrow_size,
            proyeccion_pos - 2,
            self.height // 2,
            fill="#3498DB",
            outline="#2980B9",
            width=2,
        )

        # Texto del valor actual en el centro con sombra
        avance_text = self._format_amount(self.avance)
        percent_text = f"{avance_text}"

        # Determinar posición del texto (en el centro de la barra de progreso)
        text_x = (progress_start + progress_end) // 2 if progress_width > 20 else self.width // 2

        # Sombra del texto
        self.canvas.create_text(
            text_x + 1,
            self.height // 2 + 1,
            text=percent_text,
            font=("Segoe UI", 8, "bold"),
            fill="#000000",
            anchor=tk.CENTER,
        )

        # Texto principal
        text_color = "white" if progress_width > 20 else "#ECF0F1"
        self.canvas.create_text(
            text_x,
            self.height // 2,
            text=percent_text,
            font=("Segoe UI", 8, "bold"),
            fill=text_color,
            anchor=tk.CENTER,
        )

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Dibuja un rectángulo con bordes redondeados"""
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _darken_color(self, color):
        """Oscurece un color hexadecimal"""
        color = color.lstrip("#")
        r, g, b = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))

        r = max(0, r - 30)
        g = max(0, g - 30)
        b = max(0, b - 30)

        return f"#{r:02x}{g:02x}{b:02x}"

    def _update_labels(self):
        """Actualiza los textos de los labels"""
        percent = (self.avance / self.proyeccion * 100) if self.proyeccion > 0 else 0

        # Determinar color según progreso
        if percent >= 100:
            color = "#27AE60"  # Verde
        elif percent >= 75:
            color = "#F39C12"  # Naranja
        elif percent >= 50:
            color = "#E67E22"  # Naranja oscuro
        else:
            color = "#E74C3C"  # Rojo

        self.label_partida.config(text=f"{self._format_amount(self.partida)}")

        # self.label_avance.config(
        #    text=f"Avance: ${self._format_amount(self.avance)} ({percent:.1f}%)", fg=color
        # )

        self.label_proyeccion.config(text=f"{self._format_amount(self.proyeccion)}")

    def _lighten_color(self, color, amount=40):
        """Aclara un color hexadecimal para efecto de brillo"""
        # Convertir hex a RGB
        color = color.lstrip("#")
        r, g, b = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))

        # Aclarar (aumentar hacia 255)
        r = min(255, r + amount)
        g = min(255, g + amount)
        b = min(255, b + amount)

        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _clamp(value, min_value, max_value):
        """Limita un valor entre un mínimo y un máximo"""
        return max(min_value, min(value, max_value))

    @staticmethod
    def _format_amount(amount):
        """Formatea un número como cantidad con separadores de miles (maneja negativos)"""
        abs_amount = abs(amount)
        sign = "-" if amount < 0 else ""

        if abs_amount >= 1_000_000:
            return f"{sign}{abs_amount / 1_000_000:.1f}M"
        elif abs_amount >= 1_000:
            return f"{sign}{abs_amount / 1_000:.1f}K"
        else:
            return f"{sign}{abs_amount:,.0f}"


# Muestra el tipo de widget y su referencia
def get_root(parent):
    for widget in parent.winfo_children():
        return widget


if __name__ == "__main__":
    # master = tk.Tk()
    messageBox = MyMessageBox()
    # messageBox.showinfo(title="------ Sell", message="Solo tiene disponible "+ str(0) + " USDT")
    resp = messageBox.askquestion(title="------ Sell", message="Solo tiene disponible " + str(0) + " USDT")
    print(resp)
    # master.mainloop()
