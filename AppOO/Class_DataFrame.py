from Modulos_Mysql import PlanInversion, MarketScreen, IPerformance
from Modulos_Utilitarios import (
    is_none,
    vehiculo_parm,
    currency,
    numero_fib,
    retrocesos_fib,
    nivel_fib,
    porcentaje,
    convierte_ticket_crypto,
    meses_list,
    is_null,
    calcular_atr,
    read_json_tmp,
    write_json_tmp,
)
from Modulos_python import (
    csv,
    datetime,
    yf,
    pd,
    np,
    mpatches,
    ticker,
    plt,
    filedialog,
    PolarAxes,
    FixedLocator,
    DictFormatter,
    MaxNLocator,
    floating_axes,
    UserAgent,
    requests,
    math,
    Performance,
    ta,
    os,
    mpf,
    RSIIndicator,
    mdates,
    timedelta,
    time,
    wraps,
    logging,
    TTLCache,
    HTTPError,
    textwrap,
    traceback,
    tk,
    Figure,
    FigureCanvasTkAgg,
)
from Class_ApiBinnace import BinanceClient

_logger = logging.getLogger("DataFrame")

import yfinance as yf  # import diferido — evita ciclo con módulos que importan Class_DataFrame
from cachetools import TTLCache
from functools import wraps
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError


# establece cache para yfinance --------------------------------------------------------------------------------
# ============================================================
# 🧩 Clase de manejo de caché para DataFrames
# ============================================================
class DataFrameCache:
    def __init__(self, maxsize=200, ttl=3600):
        """
        maxsize: cantidad máxima de elementos en caché
        ttl: tiempo de vida (en segundos)
        """
        self.cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.GetCounter = 0

        # Asigna Nombre Logging
        self.logger = logging.getLogger("DataFrameCache")
        self.logger.warning("✅ Cache DataFrame inicializado correctamente.")

    def get(self, key):
        self.GetCounter += 1
        return self.cache.get(key)

    def set(self, key, value):
        self.cache[key] = value

    def keys(self):
        return list(self.cache.keys())

    def clear(self):
        self.cache.clear()

    def has(self, key):
        return key in self.cache

    def remove(self, key):
        if key in self.cache:
            del self.cache[key]


# ============================================================
# 🧠 Decorador para aplicar DataFrameCache a funciones
# ============================================================
def use_dataframe_cache(df_cache):
    """
    Decorador que usa cache para funciones que retornan DataFrames.
    Permite desactivar el cache usando use_cache=False.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            try:
                use_cache = kwargs.pop("use_cache", True)
                key = (func.__name__, args, tuple(sorted(kwargs.items())))

                # uso datos cacheados
                if use_cache and df_cache.has(key):
                    return df_cache.get(key)

                result = func(*args, **kwargs)

                if use_cache:
                    df_cache.set(key, result)
            except Exception as e:
                df_cache.logger.warning(textwrap.dedent(f"""
                        ===============================================
                        {func.__name__}():
                        🟡 [CACHE MISS] - descargando datos frescos...
                        ===============================================
                        args : {args}
                        keys : {key[2]}
                        error: {e}
                        """))

            return result

        return wrapper

    return decorator


# ============================================================
# 📈 Instancia global del cache
# ============================================================
CacheHut = DataFrameCache(maxsize=200, ttl=1800)


# resumen datos fundamentales de activo ------------------------------------------------------------------------------------------
class InfoYfinance:
    def __init__(self, symbol, activo):
        self.info_list = [
            "lastFiscalYearEnd",
            "shortName",
            "lastPrice",
            "previous_close",
            "open",
            "marketCap",
            "country",
            "ipoyear",
            "volume",
            "sector",
            "industry",
            "dividendRate",
            "dividendYield",
            "exDividendDate",
            "payoutRatio",
            "fiveYearAvgDividendYield",
            "trailingAnnualDividendRate",
            "trailingAnnualDividendYield",
            "trazaDividends",
            "lastDividendValue",
            "beta",
            "trailingPE",
            "forwardPE",
            "pegRatio",
            "averageVolume",
            "fiftyTwoWeekLow",
            "fiftyTwoWeekHigh",
            "fiftyDayAverage",
            "twoHundredDayAverage",
            "currency",
            "priceToBook",
            "trailingEps",
            "forwardEps",
            "targetHighPrice",
            "targetLowPrice",
            "targetMeanPrice",
            "totalDebt",
            "returnOnAssets",
            "returnOnEquity",
            "earningsGrowth",
            "revenueGrowth",
            "freeCashflow",
            "grossMargins",
            "ebitdaMargins",
            "operatingMargins",
            "financialCurrency",
            "trailingPegRatio",
            "firstTradeDateEpochUtc",
            "website",
        ]
        self.info = self.get_info_yf(symbol, activo)

    def get_info_yf(self, symbol, activo) -> dict:
        get_info = {}
        try:
            if symbol is not None:
                # recorre los activos necesarios de market
                if activo is not None:
                    for i, keys in enumerate(self.info_list):
                        if keys in activo:
                            # asegura escribir  formato de fechas
                            if keys in (
                                "lastFiscalYearEnd",
                                "exDividendDate",
                                "firstTradeDateEpochUtc",
                            ):
                                get_info.update({keys: datetime.fromtimestamp(activo[keys])})
                            else:
                                if activo[keys] is not None:
                                    get_info.update({keys: activo[keys]})

                        elif "lastFiscalYearEnd" not in activo:
                            if "fundInceptionDate" in activo:
                                get_info.update(
                                    {"lastFiscalYearEnd": datetime.fromtimestamp(activo["fundInceptionDate"])}
                                )
                            else:
                                get_info.update({"lastFiscalYearEnd": datetime.now().date()})

                    # asegura que el registro tenga lastFiscalYearEnd
                    if "lastFiscalYearEnd" not in get_info and "exDividendDate" in activo:
                        get_info.update({"lastFiscalYearEnd": datetime.fromtimestamp(activo["exDividendDate"])})

                    # asegura que el registro tenga exDividendDate
                    if "exDividendDate" not in activo:
                        get_info.update({"exDividendDate": datetime.now().date()})

                    if "previous_close" in activo:
                        price = activo["previous_close"]
                    elif "open" in activo:
                        price = activo["open"]
                    elif "bid" in activo:
                        price = activo["bid"]

                    # asegura que se informe 'dividendRate'
                    if "dividendYield" in get_info and "dividendRate" not in get_info:
                        rate = price * get_info["dividendYield"] / 100
                        get_info.update({"dividendRate": rate})

                    elif "dividendYield" in get_info and "dividendRate" in get_info:
                        if get_info["dividendRate"] > 0:
                            rate = price * get_info["dividendYield"] / 100
                            get_info.update({"dividendRate": rate})

                    # asegura nombre de la empresa
                    if "shortName" not in get_info and "longName" in activo:
                        get_info.update({"shortName": activo["longName"]})
                    elif "shortName" not in get_info and "longName" not in activo:
                        if "longBusinessSummary" in activo:
                            get_info.update({"shortName": activo["longBusinessSummary"][0:30]})

                return get_info
        except EncodingWarning as e:
            print("[get_info_yf()]: {}".format(e))


# =================================================================
# Símbolos que fallaron get_info() por timeout — se omiten por 30 min
_info_timeout_cache = TTLCache(maxsize=200, ttl=1800)


# 📊 Función principal get_yfinance: encapsula llamados a yfinance
# =================================================================
@use_dataframe_cache(CacheHut)
def get_yfinance(ticket=None, vehiculo="Stock", period="5y", interval="1d", desde=None, hasta=None):
    """
    @param ticket: id de activo
    @param vehiculo: tipo de activo Crypto, stock
    @param period: intervalo de tiempo para la solicitud de datos historic
    @param interval: intervalo de tiempo para los datos históricos
    @param desde: fecha de inicio de intervalo para la solicitud de datos historic
    @param hasta: fecha, fin de intervalo para la solicitud de datos historic
    @return: retorna structura yf.Ticker y/o Dataframe()
    """

    # para obtener get_info() de manera segura
    def safe_get_info(objeto, key):
        # Si el símbolo ya falló antes, omitir sin log ni llamada de red
        if key in _info_timeout_cache:
            return {}
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(objeto.get_info)
                info = future.result(timeout=5)
            return info if info else {}
        except FutureTimeoutError:
            _info_timeout_cache[key] = True
            CacheHut.logger.warning(f"safe_get_info({key}) :: timeout — bloqueado 30 min")
            return {}
        except Exception as e:
            CacheHut.logger.error(f"safe_get_info({key}) :: {e}")
            return {}

    activo, pdatos = {}, pd.DataFrame()

    try:
        # unifica ticket Crypto al dominio yfinance
        # symbol = convierte_ticket_crypto(ticket)

        # esta opción no retorna en pdatos la columna "Close", pero entrega Dividends y Splits
        if vehiculo == "Stock":
            dat = yf.Ticker(ticket)

            activo = safe_get_info(dat, ticket)
            pdatos = dat.history(period=period)

            return activo, pdatos

        # exclusivo para el mundo Crypto
        elif vehiculo == "Crypto":
            dat = yf.Ticker(convierte_ticket_crypto(ticket))

            activo = safe_get_info(dat, convierte_ticket_crypto(ticket))
            pdatos = get_klines_info(symbol=ticket, period=period, desde=desde, hasta=hasta)
            return activo, pdatos

        # exclusivo para FCI Argentina, obtiene data desde Diaria_CNV
        elif vehiculo in ["BBVA.ARS", "SANT.ARS"]:
            Otr = PlanInversion()
            pdatos = Otr.get_yf_CNV(symbol=ticket, start=desde, end=hasta)

            # Obtener metadatos del fondo desde BD (otros_activos)
            activo_bd, found = Otr.select_otros_activos(symbol=ticket)
            if found and activo_bd:
                activo = {
                    "shortName": activo_bd[0].get("descripcion", ticket),
                    "symbol": ticket,
                    "country": "Argentina",
                    "region": "AS",
                    "sector": "Fondo Inversión",
                    "industry": "Mutual Fund",
                    "currency": activo_bd[0].get("base_asset", "ARS"),
                    "quoteType": "MUTUALFUND",
                    "marketCap": None,
                    "dividendYield": 0,
                    "fiftyTwoWeekLow": pdatos["Low"].min() if not pdatos.empty else None,
                    "fiftyTwoWeekHigh": pdatos["High"].max() if not pdatos.empty else None,
                }
            else:
                activo = {}

            return activo, pdatos

        # esta opción para obtener solo info()
        elif vehiculo == "info()":
            dat = yf.Ticker(ticket)

            activo = safe_get_info(dat, ticket)
            return activo

        # esta opción para obtener solo ticker()
        elif vehiculo == "Dividends":

            activo = yf.Ticker(ticket)
            dividends = activo.dividends
            pdatos = yf.download(ticket, start=desde, end=hasta, auto_adjust=True, progress=False)

            # extraer el primer nivel de las columnas sacando infor Ticker
            pdatos.columns = pdatos.columns.get_level_values(0)

            # elimina zona horaria si la tiene (algunos tickers la traen, otros no)
            if dividends.index.tz is not None:
                dividends = dividends.tz_localize(None)

            # Filtrar solo los días donde hubo dividendos
            dividends = dividends.reindex(pdatos.index)
            pdatos["Dividends"] = dividends

            # estoy siguinedo para sacar warnings de pandas
            pdatos["Dividends"] = pdatos["Dividends"].fillna(0).infer_objects(copy=False).astype(float)
            return activo, pdatos

        else:
            # obtiene dataframe desde download yfinance
            if "USDT" not in ticket:
                # download sin fecha desde y hasta
                if is_none(desde) and is_none(hasta):

                    pdatos = yf.download(ticket, period=period, auto_adjust=True, progress=False)

                    # extraer el primer nivel de las columnas sacando infor Ticker
                    pdatos.columns = pdatos.columns.get_level_values(0)
                    activo = {}

                # download con fecha desde y hasta
                if not is_none(desde) and not is_none(hasta):

                    pdatos = yf.download(ticket, start=str(desde), auto_adjust=True, progress=False)

                    # extraer el primer nivel de las columnas sacando infor Ticker
                    pdatos.columns = pdatos.columns.get_level_values(0)
                    activo = {}

                return activo, pdatos

            # obtiene dataframe desde download BINANCE
            elif "USDT" in ticket:
                pdatos = get_klines_info(symbol=ticket, period=period, desde=desde, hasta=hasta)
                activo = {}
                return activo, pdatos
    except (Exception, EncodingWarning) as e:
        CacheHut.logger.error(f"[get_yfinance({ticket}, {vehiculo})]: {e}")
        time.sleep(3)
        return {}, pd.DataFrame()


# captura precios historic de binance
def get_klines_info(symbol=None, period="5y", interval="1d", desde=None, hasta=None):

    # construye intervalos de 1000 dias
    def intervalos_klines(ifecha, ffecha, limit=1000):

        intervalos = []
        cantidad, actual = (ffecha - ifecha), ifecha

        # para dividir en intervalos de 1000 dias
        if cantidad.days > limit:
            while actual < ffecha:
                siguiente = actual + timedelta(days=limit)
                if siguiente >= ffecha:
                    intervalos.append((int(actual.timestamp() * 1000), int(ffecha.timestamp() * 1000)))
                elif siguiente < ffecha:
                    intervalos.append(
                        (
                            int(actual.timestamp() * 1000),
                            int(siguiente.timestamp() * 1000),
                        )
                    )
                actual = siguiente

        # cuando intervalos es menor a 1000 dias
        elif cantidad.days < limit:
            x_desde = ifecha if isinstance(ifecha, datetime) else datetime.combine(ifecha, datetime.min.time())
            x_hasta = ffecha if isinstance(ffecha, datetime) else datetime.combine(ffecha, datetime.max.time())
            intervalos.append((int(x_desde.timestamp() * 1000), int(x_hasta.timestamp() * 1000)))

        return intervalos

    try:
        bi = BinanceClient().spot

        # controla inicio y fin
        if (desde is not None) and (hasta is not None):
            # Normalizar a datetime: acepta str, date o datetime
            def _to_datetime(val, end_of_day=False):
                if isinstance(val, str):
                    val = datetime.fromisoformat(val)
                if not isinstance(val, datetime):
                    # es date → combinar con medianoche o fin de día
                    t = datetime.max.time() if end_of_day else datetime.min.time()
                    return datetime.combine(val, t)
                return val

            i_fecha = _to_datetime(desde, end_of_day=False)
            f_fecha = _to_datetime(hasta, end_of_day=True)
        else:
            f_fecha = datetime.now()
            i_fecha = f_fecha - timedelta(days=1800)

        rangos = intervalos_klines(i_fecha, f_fecha)
        datos = None
        for i, (start, end) in enumerate(rangos, 1):

            start_date = datetime.fromtimestamp(int(start / 1000))
            end_date = datetime.fromtimestamp(end / 1000)

            # Obtener datos históricos de velas
            klines = bi.klines(
                symbol=symbol,
                interval=interval,
                startTime=start,
                endTime=end,
                limit=1000,
            )

            """
            columns = ['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume',
                       'Close_time', 'quote_asset_volume', 'number_of_trades',
                       'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore']
            """
            # Convertir a DataFrame
            df = pd.DataFrame(
                [
                    [
                        datetime.fromtimestamp(k[0] / 1000),
                        float(k[1]),  # Open
                        float(k[2]),  # High
                        float(k[3]),  # Low
                        float(k[4]),  # Close
                        float(k[5]),  # Volume
                    ]
                    for k in klines
                ],
                columns=["Date", "Open", "High", "Low", "Close", "Volume"],
            )
            # df.set_index("Date", inplace=True)
            df.dropna()

            # Localizar la zona horaria a UTC primero si es naive, luego convertir a America/New_York
            if not df.empty:
                if df["Date"].dt.tz is None:
                    df["Date"] = df["Date"].dt.tz_localize("UTC").dt.tz_convert("America/New_York")
                else:
                    df["Date"] = df["Date"].dt.tz_convert("America/New_York")

            # realiza append de los dataframe obtenidos
            if datos is None:
                datos = df
            else:
                if not df.empty:
                    datos = pd.concat([datos, df], ignore_index=True)

        datos.set_index("Date", inplace=True)
        # print(f"df {symbol} -- {datos}")
        return datos

    except (Exception, AttributeError, Exception) as e:
        _logger.error(f"get_klines_info({symbol}): {e}")
        return pd.DataFrame()


def get_ultimo_dia_mercado(market="Stock"):
    # Descarga los datos históricos del índice
    if market == "Stock":
        activo, datos = get_yfinance(ticket="^GSPC", period="7d", vehiculo="download")
    elif market == "Crypto":
        activo, datos = get_yfinance(ticket="BTC-USD", period="7d", vehiculo="download")
    elif market == "BBVA.ARS":
        activo, datos = get_yfinance(ticket="^MERV", period="7d", vehiculo="download")

    # Obtén el último día hábil como datetime.date
    if not datos.empty:
        hoy = datetime.now().date()
        datos_inverted = datos.iloc[::-1]
        for index, row in datos_inverted.iterrows():
            idx_date = index.date() if hasattr(index, "date") else index
            if idx_date < hoy:
                return idx_date
        return hoy
    else:
        return None


# método para cargar archivos
def cagar_archivo(account=None, titulo=None, tipo="csv"):
    """
    @param account: id de cuenta de inversión
    @param titulo:  titulo de ventada para selección de archivo
    @param tipo: tipo de archivo CSV, TXT, XLS
    @return: interfaz  para seleccionar tipo de archivo
    """
    try:
        ruta = filedialog.askopenfilename(title=titulo, filetypes=(("Archivos " + tipo.upper(), "*." + tipo),))
        extracto, ilog = {}, False
        if ruta:
            if ruta.endswith("." + tipo):
                extracto, ilog = get_extractos_csv(account, ruta)
        #
        # valida que CSv es 'Activity Statement'
        if not ilog:
            return {}, ilog
        else:
            return extracto, ilog
    except Exception as error:
        print(f"[cagar_archivo()] Error: {error}")
        return {}, None


# carga Csv a tabla de extractos
def get_extractos_csv(account=None, ruta=None):
    """
    @param account: id de cuenta de inversión
    @param ruta:  ruta donde se encuentra los archivos
    @return:  retorna dict() con atributos de del extracto."""
    try:
        extracto, ilog = {}, False
        with open(ruta, newline="", encoding="utf-8") as csvfile:

            spamreader = csv.reader(csvfile, delimiter=",")
            # spamreader = csv.reader(csvfile)
            depositos, retiros = 0.0, 0.0

            # for i, row in enumerate(spamreader):
            for row in spamreader:
                if ("Statement" in row) and ("Data" in row):
                    if "Period" in row:
                        f_inicio, f_fin = row[-1].split(" - ")
                        f_fin = f_fin.strip()

                        f_obj = datetime.strptime(f_fin, "%B %d, %Y")
                        fecha = f_obj.strftime("%Y-%m-%d")
                        extracto.update({"extracto": datetime.strptime(fecha, "%Y-%m-%d")})

                    if ("Title" in row) and ("Activity Statement" in row):
                        ilog = True

                elif ("Cash Report" in row) and ("Data" in row) and ("Commissions" in row):
                    ix = (
                        "Cash Report",
                        "Header",
                        "Currency Summary",
                        "Currency",
                        "Total",
                        "Securities",
                        "Futures",
                        "Paxos",
                    )
                    extracto.update({"comisiones": abs(float(row[ix.index("Securities")]))})

                elif ("Dividends" in row) and ("Data" in row) and ("Total" in row):
                    ix = (
                        "Dividends",
                        "Header",
                        "Currency",
                        "Account",
                        "Date",
                        "Description",
                        "Amount",
                    )
                    extracto.update({"dividendos": row[ix.index("Amount")]})

                elif ("Withholding Tax" in row) and ("Data" in row) and ("Total" in row):
                    ix = (
                        "Withholding Tax",
                        "Header",
                        "Currency",
                        "Account",
                        "Date",
                        "Description",
                        "Amount",
                        "Code",
                    )
                    extracto.update({"tax": abs(float(row[ix.index("Amount")]))})

                elif ("Fees" in row) and ("Data" in row) and ("Total" in row):
                    ix = (
                        "Fees",
                        "Header",
                        "Subtitle",
                        "Currency",
                        "Account",
                        "Date",
                        "Description",
                        "Amount",
                    )
                    extracto.update({"fee": abs(float(row[ix.index("Amount")]))})

                elif ("Deposits & Withdrawals" in row) and ("Data" in row) and ("USD" in row):
                    ix = (
                        "Deposits & Withdrawals",
                        "Header",
                        "Currency",
                        "Account",
                        "Date",
                        "Description",
                        "Amount",
                    )

                    if "Electronic Fund Transfer" in row[ix.index("Description")]:
                        depositos += float(row[ix.index("Amount")])
                    if "Disbursement" in row[ix.index("Description")]:
                        retiros += float(row[ix.index("Amount")])

                elif ("Interest" in row) and ("Data" in row) and ("USD" in row):
                    ix = (
                        "Interest",
                        "Header",
                        "Currency",
                        "Account",
                        "Date",
                        "Description",
                        "Amount",
                    )

                    extracto.update({"imargen": 0})
                    if "Debit" in row[ix.index("Description")]:
                        extracto.update({"imargen": abs(float(row[ix.index("Amount")]))})

                    extracto.update({"idevengo": 0})
                    if "Managed Securities" in row[ix.index("Description")]:
                        extracto.update({"idevengo": row[ix.index("Amount")]})

                elif ("Open Positions" in row) and ("Total" in row) and ("Stocks" in row) and ("USD" in row):
                    ix = (
                        "Open Positions",
                        "Header",
                        "DataDiscriminator",
                        "Asset Category",
                        "Currency",
                        "Symbol",
                        "Quantity",
                        "Mult",
                        "Cost Price",
                        "Cost Basis",
                        "Close Price",
                        "Value",
                        "Unrealized P/L",
                        "Code",
                    )
                    extracto.update({"costobase": row[ix.index("Cost Basis")]})
                    extracto.update({"navcierre": row[ix.index("Value")]})
                    ilog = True

                elif (
                    ("Realized & Unrealized Performance Summary" in row)
                    and ("Data" in row)
                    and ("Total (All Assets)" in row)
                ):

                    ix = (
                        "Realized & Unrealized Performance Summary",
                        "Data",
                        "Total",
                        "",
                        "Cost Adj.",
                        "Realized S/T Profit",
                        "Realized S/T Loss",
                        "Realized L/T Profit",
                        "Realized L/T Loss",
                        "Realized Total",
                        "Unrealized S/T Profit",
                        "Unrealized S/T Loss",
                        "Unrealized L/T Profit",
                        "Unrealized L/T Loss",
                        "Unrealized Total",
                        "Total",
                        "Code",
                    )

                    extracto.update(
                        {
                            "crecimiento": float(row[ix.index("Realized S/T Profit")])
                            + float(row[ix.index("Realized L/T Profit")])
                        }
                    )
                    extracto.update(
                        {
                            "perdidas": abs(float(row[ix.index("Realized S/T Loss")]))
                            + abs(float(row[ix.index("Realized L/T Loss")]))
                        }
                    )
            # por eof() actualiza
            extracto.update({"depositos": depositos})
            extracto.update({"retiros": retiros})

            return extracto, ilog
    except Exception as error:
        print("[Error::  get_extractos_csv()]: {}".format(error))
        return {}, None


def get_index_performa(vehiculo=None, date=None):
    """
    @param vehiculo: tipo de inversión stock, Crypto
    @param date:  fecha de inicio para cálculo de performa
    @return:  entrega DATAFRAME, desempeño de índice a partir de fecha de inicio. Cálculo logarithmic o arithmetic
    """

    hoy = datetime.now().date()
    f_inicio = date - timedelta(days=5)
    symbol, rtn_index, cum_index, index_ref = vehiculo_parm(vehiculo=vehiculo)
    performa = pd.DataFrame()

    activo, datos = get_yfinance(ticket=symbol, vehiculo="download", desde=f_inicio, hasta=hoy)

    performa[rtn_index] = datos["Close"].pct_change()
    performa[cum_index] = (1 + performa[rtn_index]).cumprod() - 1

    return performa.iloc[-1][rtn_index], rtn_index, cum_index, index_ref


# gráfica de symbol con sus indicadores y Fibonacci
def chart_symbol(fg=None, datos=None, keys=None):
    def operaciones_book(p_tipo="C", frame=None, df=None):

        signal = list()
        setix = df.index
        xmin = float(frame["preciotrans"].min())
        xmax = float(frame["preciotrans"].max())

        for date, values in frame.iterrows():

            if (date.strftime("%Y-%m-%d") in setix) and (values["codigo"] == p_tipo):
                signal.append(float(values["preciotrans"]) * 0.99)
            else:
                signal.append(np.nan)

        return signal, xmin, xmax

    def m_emaplot(p_tipo):

        z_sell, z_buy = {}, {}
        vmin = pdatos["Low"].min()
        ema09, ema21 = pdatos["EMA009"].iloc[-1], pdatos["EMA021"].iloc[-1]

        ndatos = numero_fib(n=pdatos.shape[0])
        minimax = pdatos[["High", "Low"]].tail(ndatos)
        xmax = minimax["High"].max()
        f_desde = minimax.loc[minimax["High"] == xmax].index[0]
        xmin = minimax["Low"].loc[f_desde.strftime("%Y-%m-%d") :].min()
        xmax = minimax["High"].max()

        (
            x_long,
            x_alcista,
            x_bajista,
            zone_fib0,
            zone_fib1,
            zone_fib2,
            zone_fib3,
            zone_fib4,
            zone_fib5,
        ) = retrocesos_fib(
            low=xmin,
            high=xmax.max(),
            ema09=ema09,
            ema21=ema21,
            datos=pdatos,
            desde=f_desde,
        )

        rsi_indicator = RSIIndicator(close=pclose, window=13)
        sh = rsi_indicator.rsi()
        ln = sh.rolling(window=55).mean()

        fup = dict(
            y1=sh.values,
            y2=ln.values,
            where=(sh > ln),
            color="green",
            alpha=0.3,
            interpolate=True,
        )
        fdn = dict(
            y1=sh.values,
            y2=ln.values,
            where=(sh < ln),
            color="red",
            alpha=0.3,
            interpolate=True,
        )
        lim = dict(y1=30, y2=70, alpha=0.2, color="white")

        f_above = dict(
            y1=pdatos["EMA009"].values,
            y2=pdatos["EMA021"].values,
            alpha=0.4,
            color="blue",
            interpolate=True,
            where=(pdatos["EMA009"] > pdatos["EMA021"].values),
        )
        f_below = dict(
            y1=pdatos["EMA009"].values,
            y2=pdatos["EMA021"].values,
            alpha=0.4,
            color="orange",
            interpolate=True,
            where=(pdatos["EMA009"] < pdatos["EMA021"].values),
        )

        l_above = dict(
            y1=vmin,
            y2=pdatos["Close"].values,
            alpha=0.4,
            color="blue",
            interpolate=True,
            where=(vmin > pdatos["Close"].values),
        )
        l_below = dict(
            y1=vmin,
            y2=pdatos["Close"].values,
            alpha=0.4,
            color="red",
            interpolate=True,
            where=(vmin < pdatos["Close"].values),
        )
        if keys["position"]:
            buy_signal, x1, x2 = operaciones_book(p_tipo="O", frame=keys["booktrading"], df=pclose)
            z_buy = dict(y1=x1, y2=x2, color="Olive", alpha=0.3)
            z_sell = dict(y1=x2, y2=vmax, color="DarkCyan", alpha=0.2)
            if p_tipo != "line":
                ema = [
                    mpf.make_addplot(pdatos["EMA009"], color="orange", ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos["EMA021"], color="blue", ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos["EMA055"], color="cyan", ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos["EMA144"], color="purple", ax=ax, alpha=0.6),
                    mpf.make_addplot(
                        pdatos["EMA009"],
                        fill_between=[f_above, f_below],
                        ax=ax,
                        alpha=0.6,
                    ),
                    mpf.make_addplot(pdatos["EMA021"], fill_between=z_buy, ax=ax, alpha=0.6),
                    mpf.make_addplot(
                        pdatos["EMA009"],
                        color="Olive",
                        fill_between=z_buy,
                        ax=ae,
                        alpha=0.1,
                    ),
                    mpf.make_addplot(
                        pdatos["EMA009"],
                        color="blue",
                        fill_between=z_sell,
                        ax=ae,
                        alpha=0.1,
                    ),
                    mpf.make_addplot(pdatos["ivolume"], type="bar", ax=av, alpha=0.6),
                    mpf.make_addplot(sh, color="green", ax=av, type="line", alpha=0.8),
                    mpf.make_addplot(ln, color="red", ax=av, type="line", alpha=0.8),
                    mpf.make_addplot(ln, color="green", ax=av, fill_between=[fup, fdn]),
                    mpf.make_addplot(ln, color="green", ax=av, fill_between=lim),
                ]
                # Agrega zonas Fibonacci solo si está activo
                if keys.get("fibonacci", False):
                    ema.extend(
                        [
                            mpf.make_addplot(
                                pdatos["EMA009"], color="green", fill_between=zone_fib0, ax=ax, alpha=0.01
                            ),
                            mpf.make_addplot(
                                pdatos["EMA009"], color="green", fill_between=zone_fib1, ax=ax, alpha=0.01
                            ),
                            mpf.make_addplot(
                                pdatos["EMA009"], color="green", fill_between=zone_fib2, ax=ax, alpha=0.01
                            ),
                            mpf.make_addplot(
                                pdatos["EMA009"], color="green", fill_between=zone_fib3, ax=ax, alpha=0.01
                            ),
                            mpf.make_addplot(
                                pdatos["EMA009"], color="green", fill_between=zone_fib4, ax=ax, alpha=0.01
                            ),
                            mpf.make_addplot(
                                pdatos["EMA009"], color="green", fill_between=zone_fib5, ax=ax, alpha=0.01
                            ),
                        ]
                    )
            else:
                ema = [
                    mpf.make_addplot(
                        pdatos["Close"],
                        fill_between=[l_above, l_below],
                        ax=ax,
                        alpha=0.6,
                    ),
                    mpf.make_addplot(
                        pdatos["EMA009"],
                        color="Olive",
                        fill_between=z_buy,
                        ax=ae,
                        alpha=0.1,
                    ),
                    mpf.make_addplot(
                        pdatos["EMA009"],
                        color="blue",
                        fill_between=z_sell,
                        ax=ae,
                        alpha=0.1,
                    ),
                    mpf.make_addplot(pdatos["ivolume"], type="bar", ax=av, alpha=0.6),
                    mpf.make_addplot(sh, color="green", ax=av, type="line", alpha=0.8),
                    mpf.make_addplot(ln, color="red", ax=av, type="line", alpha=0.8),
                    mpf.make_addplot(ln, color="green", ax=av, fill_between=[fup, fdn]),
                    mpf.make_addplot(ln, color="green", ax=av, fill_between=lim),
                ]
        else:
            if p_tipo != "line":
                ema = [
                    mpf.make_addplot(pdatos["EMA009"], color="orange", ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos["EMA021"], color="blue", ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos["EMA055"], color="cyan", ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos["EMA144"], color="purple", ax=ax, alpha=0.6),
                    mpf.make_addplot(
                        pdatos["EMA009"],
                        fill_between=[f_above, f_below],
                        ax=ax,
                        alpha=0.6,
                    ),
                    mpf.make_addplot(pdatos["ivolume"], type="bar", ax=av, alpha=0.6),
                    mpf.make_addplot(sh, color="green", ax=av, type="line", alpha=0.8),
                    mpf.make_addplot(ln, color="red", ax=av, type="line", alpha=0.8),
                    mpf.make_addplot(ln, color="green", ax=av, fill_between=[fup, fdn]),
                    mpf.make_addplot(ln, color="green", ax=av, fill_between=lim),
                ]
                # Agrega zonas Fibonacci solo si está activo
                if keys.get("fibonacci", False):
                    ema.extend(
                        [
                            mpf.make_addplot(
                                pdatos["EMA009"], color="green", fill_between=zone_fib0, ax=ax, alpha=0.01
                            ),
                            mpf.make_addplot(
                                pdatos["EMA009"], color="green", fill_between=zone_fib1, ax=ax, alpha=0.01
                            ),
                            mpf.make_addplot(
                                pdatos["EMA009"], color="green", fill_between=zone_fib2, ax=ax, alpha=0.01
                            ),
                            mpf.make_addplot(
                                pdatos["EMA009"], color="green", fill_between=zone_fib3, ax=ax, alpha=0.01
                            ),
                            mpf.make_addplot(
                                pdatos["EMA009"], color="green", fill_between=zone_fib4, ax=ax, alpha=0.01
                            ),
                            mpf.make_addplot(
                                pdatos["EMA009"], color="green", fill_between=zone_fib5, ax=ax, alpha=0.01
                            ),
                        ]
                    )
            else:
                ema = [
                    mpf.make_addplot(
                        pdatos["Close"],
                        fill_between=[l_above, l_below],
                        ax=ax,
                        alpha=0.6,
                    ),
                    mpf.make_addplot(pdatos["ivolume"], type="bar", ax=av, alpha=0.6),
                    mpf.make_addplot(sh, color="green", ax=av, type="line", alpha=0.8),
                    mpf.make_addplot(ln, color="red", ax=av, type="line", alpha=0.8),
                    mpf.make_addplot(ln, color="green", ax=av, fill_between=[fup, fdn]),
                    mpf.make_addplot(ln, color="green", ax=av, fill_between=lim),
                ]

        return ema, x_alcista, x_bajista, x_long, f_desde, z_buy, z_sell

    def add_plot(p_tipo) -> list:
        nonlocal ax, ae
        z_buy, z_sell = {}, {}  # inicializa para evitar error de scope

        def view_position():
            ix = pdatos.index[-1]
            l_ix = len(pdatos.index)

            ae.text(
                0,
                keys["mkPrice"],
                currency(keys["mkPrice"]),
                fontsize=5,
                ha="left",
                color=keys["pcolor"],
            )
            ae.plot(l_ix, keys["mkPrice"], marker=">", color=keys["pcolor"])

            y = float(keys["avgCost"]) * 1.1
            ax.axhline(keys["avgCost"], linewidth=0.6, ls="--", color="yellow")
            ax.text(
                0,
                y,
                "base: " + currency(keys["avgCost"]),
                fontsize=5,
                ha="left",
                color="yellow",
            )
            ae.plot(l_ix, keys["avgCost"], marker=">", color="yellow")

            if keys["position"] and z_buy.get("y2"):
                ae.text(
                    0.5,
                    z_buy["y2"],
                    "Zone Sell",
                    transform=ae.transAxes,
                    fontsize=10,
                    color="gray",
                    alpha=0.5,
                    va="bottom",
                    rotation=90,
                )

        x_emaplot, x_emaline, vmin = [], [], pdatos["Low"].min()
        x_long, x_alcista, x_bajista, f_desde = None, {}, {}, None  # valores por defecto

        mc = mpf.make_marketcolors(
            base_mpf_style="charles",
            up="green",
            down="red",
            volume={"up": "blue", "down": "orange"},
        )
        sty = mpf.make_mpf_style(
            base_mpl_style="dark_background",
            marketcolors=mc,
            y_on_right=False,
            edgecolor="grey",
        )

        if p_tipo != "line":
            x_emaplot, x_alcista, x_bajista, x_long, f_desde, _z_buy, _z_sell = m_emaplot(p_tipo)
            z_buy.update(_z_buy)
            z_sell.update(_z_sell)
            mpf.plot(
                pdatos,
                type=tipo,
                style=sty,
                ax=ax,
                addplot=x_emaplot,
                datetime_format="%b-%Y",
                scale_width_adjustment=dict(ohlc=1.5, lines=0.45, volume=0.8),
            )

            # draw() de texto fibonacci (solo si está activo)
            if keys.get("fibonacci", False):
                fdesde = pdatos.index.get_loc(f_desde)
                l_ix = len(pdatos.index)
                ndesde = fdesde + int((l_ix - fdesde) / 2)
                ax = nivel_fib(ax, ndesde, x_alcista, x_bajista, x_long)

        if p_tipo == "line":
            mpf.plot(
                pdatos,
                type=tipo,
                style=sty,
                ax=ax,
                addplot=x_emaline,
                datetime_format="%b-%Y",
                scale_width_adjustment=dict(ohlc=1.5, lines=0.45, volume=0.8),
            )

        # draw() de proyeccción de precios forward
        if keys["position"]:
            view_position()

        return (
            sty,
            x_emaplot,
            x_emaline,
            x_long,
            f_desde,
            x_alcista,
            x_bajista,
            z_sell,
            z_buy,
        )

    try:
        # limpia y define partes del gráfico
        fg.clear()
        gs = fg.add_gridspec(
            2,
            2,
            width_ratios=(6, 1),
            height_ratios=(5, 1),
            left=0.1,
            right=0.92,
            bottom=0.11,
            top=0.9,
            wspace=0.05,
            hspace=0.05,
        )
        ax = fg.add_subplot(gs[0, 0])
        av = fg.add_subplot(gs[1, 0], sharex=ax)
        ae = fg.add_subplot(gs[0, 1])

        ax.set_aspect("auto")
        av.set_aspect("auto")
        ae.set_aspect("auto")

        ax.set_facecolor(keys["gcolor"])
        av.set_facecolor(keys["gcolor"])
        ae.set_facecolor(keys["gcolor"])

        periodo = keys["periodo"]
        tipo = keys["tipo"]

        # prepara Dataframe() de entrada - resample OHLCV
        # Elimina columnas duplicadas si existen (toma la primera)
        datos = datos.loc[:, ~datos.columns.duplicated()]

        # Resample cada columna por separado para evitar problemas de compatibilidad
        resampled = datos.resample(periodo)
        pdatos = pd.DataFrame()
        pdatos["Open"] = resampled["Open"].apply(lambda x: x.iloc[0] if len(x) > 0 else None)
        pdatos["High"] = resampled["High"].max()
        pdatos["Low"] = resampled["Low"].min()
        pdatos["Close"] = resampled["Close"].apply(lambda x: x.iloc[-1] if len(x) > 0 else None)
        pdatos["Volume"] = resampled["Volume"].sum()
        pdatos = pdatos.dropna()

        # Validar que hay datos suficientes para graficar
        if pdatos.empty or len(pdatos) < 10:
            _logger.warning(f"chart_symbol(): datos insuficientes {len(pdatos)} filas (mínimo 10)")
            return None

        pclose = pdatos["Close"]
        vmax: object = pdatos["High"].max()
        pdatos["EMA144"] = ta.trend.ema_indicator(pclose, window=144)
        pdatos["EMA055"] = ta.trend.ema_indicator(pclose, window=55)
        pdatos["EMA021"] = ta.trend.ema_indicator(pclose, window=21)
        pdatos["EMA009"] = ta.trend.ema_indicator(pclose, window=9)
        pdatos["ivolume"] = (
            100 * (pdatos["Volume"] - pdatos["Volume"].min()) / (pdatos["Volume"].max() - pdatos["Volume"].min())
        )

        icolor = ["orange", "blue", "cyan", "purple"]
        ilabel = ["EMA(09)", "EMA(21)", "EMA(55)", "EMA(144)"]
        st, emaplot, emaline, long, desde, t_alcista, t_bajista, zone_sell, zone_buy = add_plot(tipo)

        # setup de ejes de coordenadas
        ax.spines[["left", "top", "right", "bottom"]].set_visible(False)
        ax.xaxis.set_visible(True)
        ax.yaxis.set_visible(True)
        ax.grid(True, color="gray", linewidth=0.3)
        ax.set_ylabel("Precio($)", fontsize="x-small", color=keys["tcolor"])
        plt.setp(ax.get_xticklabels(), ha="right", rotation=30, fontsize=5)
        plt.setp(ax.get_yticklabels(), ha="right", fontsize=6, color=keys["tcolor"])
        plt.rcParams.update({"axes.labelsize": 6, "xtick.labelsize": 6, "ytick.labelsize": 6})

        # indicadores de gráfico
        av.spines[["left", "top", "right"]].set_visible(False)
        av.spines["bottom"].set_color(keys["ecolor"])
        av.tick_params(axis="x", colors=keys["ecolor"])
        av.xaxis.set_visible(True)
        av.set_ylabel("RSI", fontsize="x-small", color=keys["tcolor"])
        plt.setp(
            av.get_xticklabels(),
            ha="right",
            rotation=30,
            fontsize=5,
            color=keys["ecolor"],
        )
        plt.setp(av.get_yticklabels(), ha="right", fontsize=6, color=keys["ecolor"])

        # setup de eje de proyeccción
        ae.spines[["left", "top", "bottom"]].set_visible(False)
        ae.spines["right"].set_color(keys["ecolor"])
        ae.set_ylabel("Forward ($)", fontsize="x-small", color=keys["tcolor"])
        ae.tick_params(axis="y", colors=keys["ecolor"])
        ae.yaxis.set_label_position("right")
        ae.yaxis.tick_right()
        ae.set_ylim(ax.get_ylim())
        ae.xaxis.set_visible(False)
        ae.yaxis.set_visible(True)
        plt.setp(ae.get_xticklabels(), ha="right", fontsize=5, color=keys["ecolor"])
        plt.setp(ae.get_yticklabels(), ha="left", fontsize=6, color=keys["ecolor"])

        # prepara titulo y leyenda del grafico
        titulo = keys["ticket"] + ":: " + keys["name"] + " - (" + periodo + ")"
        patch = list()
        for i in range(len(ilabel)):
            patch.append(mpatches.Patch(color=icolor[i], label=ilabel[i]))

        fg.legend(handles=patch, loc="outside lower right", fontsize=6)
        fg.suptitle(titulo, color=keys["tcolor"], fontsize="medium")

        return fg
    except Exception as e:
        print("[chart_symbol()]: {}".format(e))
        traceback.print_exc()


# gráfico indicador de miedo
def setup_fear_greed(fg: object, parm=None):
    # With custom locator and formatter.Note that the extreme values are swapped.
    def xy_color(score=None):
        colors = "red" if score > 60 else "green"
        angle = math.radians(((100 - score) / 100) * 180)
        x, y = math.cos(angle), math.sin(angle)
        return x, y, colors

    def fear_vix(fear=None):
        def _last_cached():
            cached = read_json_tmp("fear_vix.json")
            wfear = cached.get("fear", fear if not is_none(fear) else 50)
            vix = cached.get("vix", 50)
            return wfear, vix

        try:
            hoy = datetime.now().date()
            BASE_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/"
            START_DATE = hoy.strftime("%Y-%m-%d")
            ua = UserAgent()

            headers = {
                "User-Agent": ua.random,
            }

            r = requests.get(BASE_URL + START_DATE, headers=headers, timeout=10)
            if not r.ok or not r.text.strip():
                _logger.error(f"fear_vix(): API no disponible — HTTP {r.status_code}, usando último valor guardado")
                return _last_cached()

            data = r.json()
            wfear = data["fear_and_greed"]["score"] if is_none(fear) else fear
            ind_wix = data["market_volatility_vix"]["score"]
            write_json_tmp("fear_vix.json", {"fear": wfear, "vix": ind_wix, "date": str(hoy)})
            return wfear, ind_wix
        except (requests.exceptions.RequestException, ValueError, KeyError) as e:
            _logger.error(f"fear_vix(): {e} — usando último valor guardado")
            return _last_cached()

    def char_plot(ax=None, x=None, y=None, score=None, color=None, titulo=None):
        face = (
            cchart["plot41"] if (score > 45) and (score < 60) else cchart["plot11"] if score < 45 else cchart["plot31"]
        )
        acolor = cchart["plot11"] if face == cchart["plot41"] else cchart["plot41"]
        ax.set_facecolor(face)

        ax.arrow(
            0,
            0,
            x,
            y,
            head_width=0.2,
            head_length=1.0,
            fc=acolor,
            ec=cchart["asx"],
            alpha=0.5,
        )

        ax.text(
            0,
            -0.15,
            titulo,
            ha="center",
            va="center",
            fontsize=9,
            color=cchart["texto"],
        )

        ax.text(
            0,
            0.30,
            "{:.0f}".format(score),
            ha="center",
            va="center",
            fontsize=16,
            color=acolor,
        )

        ax.text(
            0.15,
            0.25,
            ix[0],
            transform=ax.transAxes,
            fontsize=6,
            color=cchart["asx"],
            alpha=0.7,
            ha="center",
            va="center",
            rotation=66,
        )
        ax.text(
            0.27,
            0.60,
            ix[1],
            transform=ax.transAxes,
            fontsize=6,
            color=cchart["asx"],
            alpha=0.7,
            ha="center",
            va="center",
            rotation=40,
        )
        ax.text(
            0.50,
            0.75,
            ix[2],
            transform=ax.transAxes,
            fontsize=6,
            color=cchart["asx"],
            alpha=0.7,
            ha="center",
            va="center",
            rotation=0,
        )
        ax.text(
            0.72,
            0.60,
            ix[3],
            transform=ax.transAxes,
            fontsize=6,
            color=cchart["asx"],
            alpha=0.7,
            ha="center",
            va="center",
            rotation=-40,
        )
        ax.text(
            0.85,
            0.23,
            ix[4],
            transform=ax.transAxes,
            fontsize=6,
            color=cchart["asx"],
            alpha=0.7,
            ha="center",
            va="center",
            rotation=-66,
        )

    try:
        # Crear el gráfico
        fg.clear()
        tr = PolarAxes.PolarTransform()
        ix = ["MIEDO\nEXTREMO", "MIEDO", "NEUTRO", "AVARICIA", "AVARICIA\nEXTREMA"]

        pi = np.pi
        angle_ticks = [
            (0.00, r"$0$"),
            (0.20 * pi, r"$\frac{1}{5}\pi$"),
            (0.40 * pi, r"$\frac{2}{5}\pi$"),
            (0.60 * pi, r"$\frac{3}{5}\pi$"),
            (0.80 * pi, r"$\frac{4}{5}\pi$"),
        ]

        # Define el grid_locator y tick_formatter para los ticks de ángulo
        grid_loc01 = FixedLocator([v for v, s in angle_ticks])
        tick_for01 = DictFormatter(dict(angle_ticks))
        cchart = parm["cchart"]

        grid_loc02 = MaxNLocator(1)
        grid_help01 = floating_axes.GridHelperCurveLinear(
            tr,
            extremes=(pi, 0.00, 2, 1),
            grid_locator1=grid_loc01,
            grid_locator2=grid_loc02,
            tick_formatter1=tick_for01,
            tick_formatter2=None,
        )

        # Crear los subplots: ax arriba, ay abajo
        fg.suptitle(parm["titulo"], color=cchart["titulo"], fontsize="medium")
        # Ajusta el tamaño relativo de los subplots para ocupar más área
        # gs = fg.add_gridspec(2, 1, height_ratios=[1, 1], left=0.05, right=0.95, top=0.95, bottom=0.05, hspace=0.15)
        gs = fg.add_gridspec(2, 1)
        ax = fg.add_subplot(gs[0], axes_class=floating_axes.FloatingAxes, grid_helper=grid_help01)
        ay = fg.add_subplot(gs[1], axes_class=floating_axes.FloatingAxes, grid_helper=grid_help01)
        ax.grid()
        ay.grid()

        # Aumenta el área ocupada por el gráfico
        ax.set_box_aspect(1 / 2)  # Cambia de 0.4 a 1.0 para ocupar más área
        ay.set_box_aspect(1 / 2)  # Cambia de 0.4 a 1.0 para ocupar más área

        fear, vix = fear_vix()
        xf, yf, color = xy_color(fear)
        char_plot(ax=ax, x=xf, y=yf, score=fear, color=color, titulo="Feeling")

        xv, yv, color = xy_color(vix)
        char_plot(ax=ay, x=xv, y=yv, score=vix, color=color, titulo="Volatility")

        # Cambiar el color de los ticks y etiquetas en los ejes con FixedLocator
        for axis in ["left", "right", "bottom", "top"]:
            ax.axis[axis].major_ticks.set_color(cchart["fondo"])
            ax.axis[axis].major_ticklabels.set_color(cchart["fondo"])
            ay.axis[axis].major_ticks.set_color(cchart["fondo"])
            ay.axis[axis].major_ticklabels.set_color(cchart["fondo"])

        return
    except Exception as error:
        print("[setup_fear_greed()]: {}".format(error))


# gráfica Diversificación vs tipo de activo
def grupo_activos(fg: object, parm=None, strategy=None):

    cchart = parm["cchart"]
    fg.clear()
    ax = fg.add_subplot()
    ax.set_facecolor(cchart["fondo"])

    data, ValueMarket = {}, 0

    # Construcción de dict() para gráfico
    for keys, activos in strategy.items():
        cbase, vmark = 0.0, 0.0
        for activo in activos:
            cbase += activo["costobase"]
            vmark += activo["costobase"] + activo["unrealizedpnl"]

        data.update({keys: (cbase, vmark)})

    keys = list(data.keys())
    x = np.arange(len(keys))

    cbase = np.array([data[k][0] for k in keys])
    vmark = np.array([data[k][1] for k in keys])
    mean = np.mean(vmark)
    ValueMarket = np.sum(vmark)

    p_legend, colores = [], [cchart["plot9"], cchart["plot31"]]

    # Gráfico de área estilo grupo_dividendo
    ax.fill_between(x, cbase, color=colores[0], alpha=0.99, label="Capital")
    ax.fill_between(x, vmark, color=colores[1], alpha=0.99, label="Valor Market")

    # Configurar legend
    p_legend.append(mpatches.Patch(color=colores[0], label="Capital"))
    p_legend.append(mpatches.Patch(color=colores[1], label="Valor Market"))
    fg.legend(loc=parm["legend"], handles=p_legend, fontsize=6)
    fg.suptitle(parm["titulo"], fontsize="medium", color=cchart["titulo"])

    # Configurar eje X
    ax.set_xticks(x)
    ax.set_xticklabels(keys, rotation=0, ha="center")
    ax.set(xlim=[x[0], x[-1]])
    xlabels = ax.get_xticklabels()
    plt.setp(xlabels, ha="center", fontsize=6, color=cchart["asx"], rotation=0)

    ax.spines[["top", "bottom", "right"]].set_visible(False)
    ax.spines["left"].set_color(cchart["asy"])
    ax.grid(True, color=cchart["texto"], linewidth=0.1)

    # Configurar eje Y
    ylabels = ax.get_yticklabels()
    plt.setp(ylabels, ha="right", fontsize=6, color=cchart["texto"])
    ax.set_ylabel("Valor en (USD)", fontsize=6, color=cchart["asx"])
    ax.yaxis.set_major_formatter(currency)
    ax.tick_params(axis="y", colors=cchart["asx"])

    # Línea de media
    ax.axhline(mean, linewidth=0.6, ls="--", color=cchart["texto"])
    smean = f" μ = {mean:.0f}$"
    ax.text(
        int(len(x) / 2),
        mean * 1.2,
        smean,
        fontsize=6,
        ha="center",
        color=cchart["texto"],
    )

    # Construir summary con formato compatible para rebalanceo
    total_inversion = sum(data[categoria][0] for categoria in keys)
    summary = {
        "Name": keys,
        "Inversion": [data[categoria][0] for categoria in keys],
        "Peso": [data[categoria][0] / total_inversion if total_inversion > 0 else 0 for categoria in keys],
    }

    return {
        "data": data,
        "summary": summary,
        "activos": keys,  # mantener para compatibilidad
        "media": mean,
        "total_valor_market": ValueMarket,
    }


# Gráfica Diversificación vs. region
def grupo_region(fg: object, strategy=None, parm=None):

    def get_region_portafolio(strategy):

        d_country, NoCountry, ValueMarket = (
            {},
            0.0,
            0.0,
        )

        # obtiene Valor Market total
        for keys, activos in strategy.items():
            for activo in activos:
                ValueMarket += float(activo["costobase"]) + activo["unrealizedpnl"]

        # calcula total por country
        for keys, activos in strategy.items():

            for activo in activos:

                # normalzia key_sec
                key_sec = activo["country"]
                if is_null(key_sec) or is_none(key_sec):
                    key_sec = "NotContry"

                elif key_sec == "US":
                    key_sec = "United States"

                elif key_sec == "Digital":
                    key_sec = "Crypto"

                # acumula por key_sec
                if key_sec not in list(d_country.keys()):
                    d_country[key_sec] = {
                        "Capital": float(activo["costobase"]),
                        "Valor Market": float(activo["costobase"]) + activo["unrealizedpnl"],
                    }

                elif key_sec in list(d_country.keys()):
                    d_country[key_sec]["Capital"] += float(activo["costobase"])
                    d_country[key_sec]["Valor Market"] += float(activo["costobase"]) + activo["unrealizedpnl"]
            # agerga peso de cada pais
            d_country[key_sec]["Peso"] = d_country[key_sec]["Valor Market"] / ValueMarket

        return d_country, ValueMarket

    cchart = parm["cchart"]
    fg.clear()
    ax = fg.add_subplot()
    ax.set_facecolor(cchart["fondo"])
    ax.set_box_aspect(parm["aspect"])

    data, Valuemarket = get_region_portafolio(strategy)

    keys = list(data.keys())
    x = np.arange(len(keys))

    cbase = np.array([data[i]["Capital"] for i in keys])
    vmark = np.array([data[i]["Valor Market"] for i in keys])
    mean = np.mean(vmark)

    p_legend = []
    ax.plot(x, cbase, color=cchart["plot9"])
    ax.plot(x, vmark, color=cchart["plot2"])

    # Rellenar cuando value > base (ganancia)
    ax.fill_between(x, cbase, vmark, where=vmark >= cbase, interpolate=True, color=cchart["plot2"])
    ax.fill_between(x, vmark, 0, where=vmark >= 0, interpolate=True, color=cchart["plot2"])

    # Rellenar cuando value < base (pérdida)
    ax.fill_between(x, cbase, vmark, where=vmark <= cbase, interpolate=True, color=cchart["plot9"])

    p_legend.append(mpatches.Patch(color=cchart["plot9"], label="Capital"))
    p_legend.append(mpatches.Patch(color=cchart["plot2"], label="Valor Market"))

    ax.spines[["top", "bottom", "left", "right"]].set_visible(False)
    ax.grid(True, color=cchart["texto"], linewidth=0.1)
    ax.spines.bottom.set_color(cchart["asx"])
    ax.spines.left.set_color(cchart["asx"])
    ax.spines.bottom.set_visible(True)
    ax.spines.right.set_visible(True)
    ax.yaxis.tick_right()

    xlabels = ax.get_xticklabels()
    ylabels = ax.get_yticklabels()
    plt.setp(xlabels, ha="right", fontsize=6, color=cchart["asx"], rotation=25)
    plt.setp(ylabels, ha="left", fontsize=6, color=cchart["texto"])

    ax.set_ylabel("Valor en (USD)", fontsize=7, color=cchart["texto"])
    fg.legend(loc=parm["legend"], handles=p_legend, fontsize=6)
    fg.suptitle(parm["titulo"], fontsize="medium", color=cchart["titulo"])

    ax.axhline(mean, linewidth=0.6, ls="--", color=cchart["texto"])
    media = f" μ = {mean:.0f}$"

    ax.text(x[5], mean * 1.2, media, fontsize=6, ha="center", color=cchart["texto"])

    def abreviar_pais(nombre):
        partes = nombre.split()
        if len(partes) == 1:
            return nombre[:3]
        return "".join(p[0] for p in partes)

    keys_abrev = [abreviar_pais(k) for k in keys]
    ax.set_xticks(x, keys_abrev)
    ax.yaxis.set_major_formatter(currency)
    ax.tick_params(axis="y", colors=cchart["asx"])

    # Construir summary con formato compatible para rebalanceo
    total_inversion = sum(data[country]["Capital"] for country in keys)
    summary = {
        "Name": keys,
        "Inversion": [data[country]["Capital"] for country in keys],
        "Peso": [data[country]["Capital"] / total_inversion if total_inversion > 0 else 0 for country in keys],
    }

    return {
        "data": data,
        "summary": summary,
        "country": keys,  # mantener para compatibilidad
        "media": mean,
        "total_valor_market": Valuemarket,
    }


# permite trazar el desempeño ultimos 6 meses de las inversiones globales
def Agente_income_Manager(fg: object, parm=None):
    def get_datos(periodo=None):
        Performa = IPerformance()
        PInversion = PlanInversion()

        dias = int(periodo) * 30 if periodo else 180
        hoy = datetime.now()
        hasta = datetime.now() - timedelta(days=dias)

        extracto = PInversion.select_extracto(extract="sum*")
        diaria, ix = Performa.select_diaria_performance(accion="hasta", date=hasta.date(), symbol="all")

        clave, gain, dividends = [], [], []
        clave.append(hoy.strftime("%B-%y"))
        gain.append(0)
        dividends.append(0)

        # acumula Gain y Dividends mes actual
        for read in diaria:
            if read[ix.index("Date")].strftime("%B-%y") == clave[-1]:
                gain[-1] += read[ix.index("gyp_dia")]
                dividends[-1] += read[ix.index("dividends")]
            else:
                break

        # anteriores 6 meses
        for read in extracto:
            if read["extracto"] > hasta.date():
                clave.append(read["extracto"].strftime("%B-%y"))
                gain.append(read["crecimiento"])
                dividends.append(read["dividendos"])
            else:
                break

        struct = {"Dividends": dividends, "Cap + Div": gain}
        datos = pd.DataFrame(struct, index=clave)
        return datos, clave, struct

    def char_performance(fg: object, pdatos=None, dlabl=None):

        fg.clear()
        ax = fg.add_subplot()
        cchart = dlabl["cchart"]
        ax.set_facecolor(cchart["fondo"])
        ax.set_box_aspect(dlabl["aspect"])

        mean = pdatos["Cap + Div"].mean() + pdatos["Dividends"].mean()
        mdiv = pdatos["Dividends"].mean()
        s_mean = f" μ = {mean:.0f}$"
        s_mdiv = f" μ Div = {mdiv:.0f}$"

        # plot performance
        n_axis = len(pdatos.index)
        xlabel = np.arange(n_axis)
        p_legend = []

        stack = ax.stackplot(xlabel, struct.values(), labels=struct.keys())
        stack_colors = [poly.get_facecolor()[0] for poly in stack]
        p_legend.append(mpatches.Patch(color=stack_colors[1], label="Cap + Div"))
        p_legend.append(mpatches.Patch(color=stack_colors[0], label="Dividends"))

        titulo = dlabl["titulo"] + " - " + dlabl["periodo"] + "m"
        fg.legend(loc=dlabl["legend"], handles=p_legend, fontsize=6)
        fg.suptitle(titulo, fontsize="medium", color=cchart["titulo"])
        # fg.tight_layout()

        # set eje X
        xlabels = ax.get_xticklabels()
        plt.setp(xlabels, ha="right", fontsize=6, color=cchart["asx"], rotation=30)
        ax.set_xlabel("", fontsize="x-small", color=cchart["asx"])

        ax.spines[["top", "bottom", "right"]].set_visible(False)
        ax.spines["left"].set_color(cchart["asy"])

        ax.set_xticks(xlabel, clave)
        if dlabl["periodo"] == 3:
            xsti = [xlabel[0], xlabel[1], xlabel[-1]]
        elif dlabl["periodo"] in (6, 12):
            xsti = [xlabel[0], xlabel[1], xlabel[2], xlabel[-1]]
        else:
            xsti = [xlabel[0], xlabel[2], xlabel[-1]]

        ax.set_xticks(xsti)
        ax.set(xlim=[xlabel[0], xlabel[-1]])
        ax.grid(True, color=cchart["texto"], linewidth=0.1)

        # set 1er eje Y
        ylabels = ax.get_yticklabels()
        plt.setp(ylabels, ha="right", fontsize=6, color=cchart["texto"])
        ax.set_ylabel("USD Dolar", fontsize=6, color=cchart["asx"])
        ax.yaxis.set_major_formatter(currency)

        ax.tick_params(axis="y", colors=cchart["asx"])
        ax.axhline(mean, linewidth=0.6, ls="--", color=cchart["texto"])
        ax.text(
            int(n_axis / 2),
            mean * 1.2,
            s_mean,
            fontsize=6,
            va="center",
            color=cchart["texto"],
        )

        ax.axhline(mdiv, linewidth=0.6, ls="--", color=cchart["plot9"])
        ax.text(
            int(n_axis / 2),
            mdiv * 0.80,
            s_mdiv,
            fontsize=6,
            va="center",
            color=cchart["plot9"],
        )

    datos, clave, struct = get_datos(periodo=parm["periodo"])
    char_performance(fg=fg, pdatos=datos, dlabl=parm)


# Gráfica Diversificación vs. performance sector
def grupo_sector(fig: object, positions=None, parm=None):

    def get_sector_portafolio(p_positions):
        xsector = sectores()

        # valida positions antes de graficar
        if p_positions is None:
            p_positions = PInversion.select_inversion(tipoin="Stock", ticket="all")

        d_sector, total, ValueMarket = {}, 0, 0
        for pkeys in p_positions:
            key_sec = pkeys["sector"]
            total += pkeys["costobase"]
            ValueMarket += pkeys["costobase"] + pkeys["unrealizedpnl"]

            # por defecto los activos no encontrados entra en "Consumer Cyclical"
            if not sectores(busca=key_sec):
                value = sectores(symbol=pkeys["ticket"])
            else:
                value = xsector[key_sec]

            if value not in list(d_sector.keys()):
                d_sector[value] = float(pkeys["costobase"])
            else:
                d_sector[value] += float(pkeys["costobase"])

        name = list(d_sector.keys())
        inversion = list(d_sector.values())
        s_sector = {
            "Name": name,
            "Inversion": inversion,
            "Peso": [x / total for x in inversion],
        }

        return s_sector, ValueMarket

    def char_performance_sector(fg: object, pdatos=None, dlabl=None, asset=None):

        fg.clear()
        ax = fg.add_subplot()
        av = ax.twinx()
        cchart = dlabl["cchart"]
        ax.set_facecolor(cchart["fondo"])
        # ax.set_box_aspect(dlabl['aspect'])

        vs = "Perf Quart"
        x = np.arange(len(pdatos["Name"]))
        width = 0.60  # the width of the bars
        multiplier = 1
        cbar = ("green", "red", "orange")
        xmax = max(pdatos["Perf Year"].max(), pdatos[vs].max())
        xmin = min(pdatos["Perf Year"].min(), pdatos[vs].min())
        p_legend = []

        # plot performance sector
        for keys, measurement in datos.items():
            offset = width * multiplier
            if keys == "Perf Year":
                ax.bar(x + offset, measurement, width, color=cchart["plot6"], alpha=0.30)
                p_legend.append(mpatches.Patch(color=cchart["plot6"], label=keys))

            if keys == "Perf Quart":
                ax.bar(
                    x + offset,
                    measurement,
                    width * 0.45,
                    color=cchart["plot4"],
                    alpha=0.85,
                )
                p_legend.append(mpatches.Patch(color=cchart["plot4"], label=keys))

        p_legend.append(mpatches.Patch(color=cchart["texto"], label="mean weight"))
        fg.legend(loc=dlabl["legend"], handles=p_legend, fontsize=6)
        fg.suptitle(dlabl["titulo"], fontsize="medium", color=cchart["titulo"])

        # set eje X
        xlabels = ax.get_xticklabels()
        plt.setp(xlabels, ha="right", fontsize=6, color=cchart["asx"], rotation=25)
        ax.set_xlabel("", fontsize="x-small", color=cchart["asx"])

        ax.spines[["top", "bottom", "right"]].set_visible(False)
        ax.spines["left"].set_color(cchart["asy"])

        ax.set_xticks(x + width, pdatos["Name"])
        ax.grid(True, color=cchart["texto"], linewidth=0.1)
        ax.set_ylim([xmin, xmax])

        # set 1er eje Y
        ylabels = ax.get_yticklabels()
        plt.setp(ylabels, ha="right", fontsize=6, color=cchart["texto"])
        ax.set_ylabel("Rendimiento sector", fontsize=6, color=cchart["asx"])

        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:2.0%}"))
        ax.tick_params(axis="y", colors=cchart["asx"])

        #  construcción de 2.º eje, para mostrar costos
        av.plot(x + width, pdatos["Peso"], color=cchart["asx"], linewidth=0.7, ls="--")

        mean = pdatos["Peso"].mean()
        media = f" μ = {mean:.1%}"
        av.axhline(mean, linewidth=0.6, ls="--", color=cchart["texto"])
        av.text(x[6], mean * 1.2, media, fontsize=6, ha="center", color=cchart["texto"])

        tlabels = av.get_yticklabels()
        plt.setp(tlabels, ha="left", fontsize=6, color=cchart["texto"])
        av.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:2.0%}"))
        av.set_ylabel("% Distribución Inversión", color=cchart["texto"], fontsize=6)

        av.set_ylim([xmin, xmax])
        av.tick_params(axis="y", colors=cchart["texto"])
        av.spines[["top", "bottom", "left"]].set_visible(False)
        av.spines["right"].set_color(cchart["texto"])

    def rendimiento_bonos(symbol="TLT"):

        # Fechas de referencia
        hoy = pd.Timestamp.today().normalize()
        hace_3m = hoy - pd.DateOffset(months=3)
        hace_1a = hoy - pd.DateOffset(years=1)

        # Descargar datos desde hace 1 año hasta hoy
        etf, pdatos = get_yfinance(ticket=symbol, vehiculo="Dividends", desde=hace_1a, hasta=hoy)

        # Asegurarse de tener cierre ajustado
        hist = pdatos[pdatos["Close"].notna()]

        # Cierre más cercano a las fechas
        actual = hist["Close"].iloc[-1]
        volume = hist["Volume"].iloc[-1]
        cierre_3m = hist.loc[hist.index >= hace_3m, "Close"].iloc[0]
        cierre_1a = hist["Close"].iloc[0]

        # Calcular variaciones
        rend_3m = (actual - cierre_3m) / cierre_3m
        rend_1a = (actual - cierre_1a) / cierre_1a

        # define fila de bonos
        renta = {
            "Name": "Treasury +20years",
            "Perf Week": 0.0,
            "Perf Month": 0.0,
            "Perf Quart": rend_3m,
            "Perf Half": 0.0,
            "Perf Year": rend_1a,
            "Perf YTD": 0.0,
            "Recom": 0.0,
            "Avg Volume": 0.0,
            "Rel Volume": volume,
            "Change": 0.0,
            "Volume": 0.0,
        }

        return renta

    try:
        PInversion = PlanInversion()
        fg_performance = Performance()
        sector = fg_performance.screener_view(group="Sector")

        d_positions, ValueMarket = get_sector_portafolio(positions)
        p_sector = pd.DataFrame(d_positions)

        # agrega información de bonos a los sectores
        bonos = rendimiento_bonos()
        sector = pd.concat([pd.DataFrame([bonos]), sector], ignore_index=True)

        datos = pd.merge(sector, p_sector, on="Name", how="left")
        datos.fillna(0, inplace=True)

        parm.update(
            {
                "BTC": "BTC++index",
                "++ index": "++ Token's",
                "legend": "outside upper right",
            }
        )
        char_performance_sector(fig, pdatos=datos, dlabl=parm)

        return {
            "data": datos,
            "summary": d_positions,
            "media": datos["Peso"].mean(),
            "total_valor_market": ValueMarket,
        }
    except HTTPError as e:
        if "403" in str(e):
            _logger.error(f"grupo_sector(): FINVIZ 403 Forbidden: {e}")
        elif "404" in str(e):
            _logger.error("grupo_sector(): FINVIZ 404 — revisar librería")
        else:
            _logger.error(f"grupo_sector(): FINVIZ HTTP error: {e}")
    except Exception as e_general:
        _logger.error(f"grupo_sector(): {e_general}")


def sectores(busca=None, symbol=None):
    xsector = {
        "Consumer Defensive": "Consumer Defensive",
        "Communication Services": "Communication Services",
        "Industrials": "Industrials",
        "Consumer Cyclical": "Consumer Cyclical",
        "Technology": "Technology",
        "Energy": "Energy",
        "Financial Services": "Financial",
        "Healthcare": "Healthcare",
        "Basic Materials": "Basic Materials",
        "Real Estate": "Real Estate",
        "Utilities": "Utilities",
        "Treasury +20years": "Treasury +20years",
    }

    # retorna diccionario de sectores
    if busca is None and symbol is None:
        return xsector

    # valida buscar en sectores
    elif busca is not None and symbol is None:
        found = True if busca in list(xsector.keys()) else False
        return found

    # asigna defecto para el sector
    elif busca is None and symbol is not None:
        if symbol == "TLT":
            value = xsector["Treasury +20years"]
        else:
            value = xsector["Consumer Cyclical"]

        return value


# lista dividendos mensuales
def get_dividends(account=None, vehiculo=None):
    try:
        dividendos, cobrados, meses = (
            [0] * 12,
            [0] * 12,
            meses_list(mask="%B", orden="desc", mes="actual"),
        )
        Market = MarketScreen()
        PInversion = PlanInversion()

        hoy = datetime.now()
        desde = datetime.now() - timedelta(days=365)

        positions = PInversion.select_inversion(tipoin=vehiculo, ticket="all")
        extracto = PInversion.select_extracto(extract="sum*")
        ValueMarket = 0

        # construye proyección de dividends
        for position in positions:
            symbol = convierte_ticket_crypto(position["ticket"])
            ValueMarket += position["costobase"] + position["unrealizedpnl"]

            market, ix = Market.select(account=account, symbol=symbol)
            if market:

                last = market[0][ix.index("lastDividendValue")]
                div = market[0][ix.index("dividendRate")]

                string = market[0][ix.index("monthDividendsPay")]
                a_meses = meses if string is None or string == "" else string.split(",")

                # calcula la cantidad de pagos - filtrar cadenas vacías
                distribuir = [s.strip() for s in a_meses if s.strip()]
                rata = (div / len(distribuir)) if (div is not None and len(distribuir) > 0) else (last or 0)

                # asume pago de dividends son iguales
                for i, mes in enumerate(distribuir):
                    if mes in meses:  # Validar que el mes existe en la lista
                        dividendos[meses.index(mes)] += rata * position["position"]

        # construye dividends cobrados en 11 meses
        for read in extracto:
            if read["extracto"] > desde.date():
                mes = read["extracto"].strftime("%B")
                cobrados[meses.index(mes)] += read["dividendos"]
            else:
                break
        # deja en cero el mas recenete hasta que cierre el extracto
        cobrados[0] = 0

        d_dividends = {
            "dividendos": dividendos,
            "cobrados": cobrados,
        }

        datos = pd.DataFrame(d_dividends, index=meses)
        return datos, d_dividends, ValueMarket
    except Exception as error:
        print("get_dividends(): {}".format(error))
        return None, None, 0


# Gráfica Diversificación vs. pago dividendos
def grupo_dividendo(fg: object, parm=None):
    try:
        datos, struct, ValueMarket = get_dividends(account=parm["account"], vehiculo=parm["vehiculo"])
        p_legend = []
        if datos is not None and not datos.empty:
            fg.clear()
            ax = fg.add_subplot()
            cchart = parm["cchart"]
            ax.set_facecolor(cchart["fondo"])

            # plot performance
            meses = datos.index
            x = np.arange(len(meses))
            p_legend, colores = [], [cchart["plot5"], cchart["plot31"]]

            # Graficar 'dividendos' con transparencia
            ax.fill_between(x, datos["dividendos"], color=colores[0], alpha=0.99, label="Dividendos")
            ax.fill_between(x, datos["cobrados"], color=colores[1], alpha=0.99, label="Cobrados")

            # Configurar de la legend
            p_legend.append(mpatches.Patch(color=colores[0], label="Dividendos"))
            p_legend.append(mpatches.Patch(color=colores[1], label="Div. Cobrados"))
            fg.legend(loc=parm["legend"], handles=p_legend, fontsize=6)
            fg.suptitle(parm["titulo"], fontsize="medium", color=cchart["titulo"])

            # Configurar el eje X con los nombres de los meses y rotación para una mejor lectura
            ax.set_xticks(x)
            ax.set_xticklabels(meses, rotation=45, ha="right")
            ax.set(xlim=[x[0], x[-1]])
            xlabels = ax.get_xticklabels()
            plt.setp(xlabels, ha="right", fontsize=6, color=cchart["asx"], rotation=25)
            ax.set_xlabel("", fontsize="x-small", color=cchart["asx"])

            ax.spines[["top", "bottom", "right"]].set_visible(False)
            ax.spines["left"].set_color(cchart["asy"])
            ax.grid(True, color=cchart["texto"], linewidth=0.1)

            # set 1er eje Y
            ylabels = ax.get_yticklabels()
            plt.setp(ylabels, ha="right", fontsize=6, color=cchart["texto"])
            ax.set_ylabel("Dolar U$", fontsize=6, color=cchart["asx"])

            ax.yaxis.set_major_formatter(currency)
            ax.tick_params(axis="y", colors=cchart["asx"])

            # escribe linea de media
            mean = datos["cobrados"].mean()
            ax.axhline(mean, linewidth=0.6, ls="--", color=cchart["texto"])
            media = f" μ = {mean:.0f}$"
            ax.text(x[6], mean * 1.2, media, fontsize=6, ha="center", color=cchart["texto"])

            return {
                "datos": datos,
                "struct": struct,
                "media": mean,
                "total_valor_market": ValueMarket,
            }
    except Exception as error:
        print("grupo_dividendo(): {}".format(error))


# gráfica performance de dividendos
def chart_rendimiento_dividendos(fg=None, datos=None, dlabl=None, cchart=None, asset=None):
    try:
        fg.clear()
        ax = fg.add_subplot()
        av = ax.twinx()

        ax.set_aspect("auto")
        av.set_aspect("auto")

        p_legend, p_zonas = [], []
        p_legend.append(mpatches.Patch(color=cchart["plot4"], label=dlabl["symbol"], alpha=0.4))

        p_zonas.append(mpatches.Patch(color=cchart["plot3"], label=dlabl["sell"]))
        p_zonas.append(mpatches.Patch(color=cchart["plot1"], label=dlabl["buy"]))
        p_zonas.append(mpatches.Patch(color=cchart["plot5"], label=dlabl["symbol"], alpha=0.4))

        fg.legend(handles=p_zonas, loc=dlabl["legend"], fontsize=6)
        fg.suptitle(
            "Precio vs Rendimiento Dividendo ",
            fontsize="medium",
            color=cchart["titulo"],
        )
        activo = asset["ticket"] + ": " + asset["name"]

        forward = asset["forward"]
        d_index = datos.index

        describe = datos.describe()

        column = "Close"
        p_min = datos[column].min()
        ax.plot(d_index, datos[column], alpha=0.23, color=cchart["plot4"], lw=2)

        ax.fill_between(d_index, p_min, datos[column], alpha=0.7, color=cchart["plot5"])
        ax.set_title(activo)

        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(True, color=cchart["axsx"], linewidth=0.3)
        ax.set_ylabel("Precio promedio ($)", fontsize=6, color=cchart["texto"])

        ax.set_facecolor(cchart["fondo_fig"])
        plt.setp(
            ax.get_xticklabels(),
            ha="right",
            fontsize=6,
            color=cchart["axsy"],
            rotation=30,
        )
        plt.setp(ax.get_yticklabels(), ha="right", fontsize=6, color=cchart["axsy"])

        ax.spines.left.set_visible(True)
        ax.spines["left"].set_color(cchart["texto"])
        ax.tick_params(axis="x", colors=cchart["axsy"])
        ax.tick_params(axis="y", colors=cchart["texto"])
        ax.set(ylim=(describe["Close"]["min"] * 0.90, describe["Close"]["max"] * 1.1))
        ax.yaxis.set_major_formatter(currency)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))

        # construcción de 2.º eje, para mostrar % rendimiento de capital + dividendos
        off = 0.001
        y = describe["Rendimiento"]["mean"] + describe["Rendimiento"]["std"]
        x = describe["Rendimiento"]["mean"] - describe["Rendimiento"]["std"]
        m = describe["Rendimiento"]["mean"]
        av.scatter(d_index, datos["Rendimiento"], marker="o", color=cchart["2eje"])
        av.fill_between(
            d_index,
            datos["Rendimiento"].values,
            m,
            where=(m < datos["Rendimiento"]),
            facecolor=cchart["plot1"],
            alpha=0.4,
            interpolate=True,
        )
        av.fill_between(
            d_index,
            datos["Rendimiento"].values,
            m,
            where=(m > datos["Rendimiento"]),
            facecolor=cchart["plot3"],
            alpha=0.4,
            interpolate=True,
        )

        lbl_idx = d_index[min(2, len(d_index) - 1)]
        av.axhline(y, linewidth=0.6, ls="--", color=cchart["plot1"])
        av.text(
            lbl_idx,
            y + off,
            "{:>+4.1%} Infravalorado el activo".format(y),
            fontsize=6,
            color=cchart["texto"],
        )
        av.axhline(m, linewidth=0.6, ls="--", color=cchart["texto"])
        av.axhline(x, linewidth=0.6, ls="--", color=cchart["plot3"])
        av.text(
            lbl_idx,
            x - off,
            "{:>+4.1%} Sobrevalorado el activo".format(x),
            fontsize=6,
            color=cchart["texto"],
        )
        av.text(
            d_index[-1],
            forward,
            "{:>+4.1%} forward".format(forward),
            fontsize=6,
            ha="right",
            color=cchart["texto"],
        )

        av.set_ylabel("Rendimiento Dividendo", fontsize=6, color=cchart["2eje"])
        av.tick_params(axis="y", labelcolor=cchart["2eje"])
        av.yaxis.set_major_formatter(porcentaje)

        # calcula limites del eje rendimiento, considera el max entre forward, limites infravalorado y sobrevalorado
        l_max = max(describe["Rendimiento"]["max"], y)
        l_min = min(describe["Rendimiento"]["min"], x)
        av.set(ylim=(l_min * 0.95, l_max * 1.05))

        tlabels = av.get_yticklabels()
        plt.setp(tlabels, ha="left", fontsize=6, color=cchart["2eje"])
        av.tick_params(axis="y", colors=cchart["2eje"])
        av.spines["right"].set_color(cchart["2eje"])
        av.spines.right.set_visible(True)
    except Exception as error:
        print("[chart_rendimiento_dividendos()]: {}".format(error))


# gráfica beneficios y costes de operación
def chart_margen_neto(fg=None, df=None, parm=None):
    """
    @param fg: lienzo donde se graficará cava
    @param df: Dataframe con información de extractos
    @param parm: parametros del gráfico: título y demás
    @return: grafica sobre lienzo margen neto es decir ingresos y costos.
    """

    fg.clear()
    ax = fg.add_subplot()
    av = ax.twinx()
    cchart = parm["cchart"]
    titulo = parm["titulo"]
    InicioInversior = parm["InicioInversior"]

    ax.set_facecolor(cchart["fondo"])
    ax.set_box_aspect(0.30)

    # define columna index
    df["año"] = df.index.year

    columnas = ["año", "ingresos", "costos", "margenNT"]
    resum = pd.DataFrame()
    resum[columnas] = df[columnas]

    # Omitir el año 0 en el cálculo y visualización
    resum = resum[resum["año"] != InicioInversior.year]

    lyear = list(resum["año"])
    x = np.arange(len(lyear))
    width = 0.30

    p_legend = []
    # Alinear ambos gráficos en x=0
    offset_ingresos = 0
    offset_costos = width

    # Barras de ingresos y costos
    ax.bar(
        x + offset_ingresos,
        resum["ingresos"],
        width,
        color=cchart["plot1"],
        alpha=0.8,
        label="ingresos",
    )
    ax.bar(
        x + offset_costos,
        resum["costos"],
        width,
        color=cchart["plot2"],
        alpha=0.9,
        label="costos",
    )

    p_legend.append(mpatches.Patch(color=cchart["plot1"], label="ingresos"))
    p_legend.append(mpatches.Patch(color=cchart["plot2"], label="costos"))
    p_legend.append(mpatches.Patch(color=cchart["plot0"], label="Margen Neto"))

    ax.spines[["top", "bottom", "right"]].set_visible(False)
    ax.grid(True, color=cchart["texto"], linewidth=0.1)

    fg.legend(loc="outside upper left", handles=p_legend, fontsize=5)
    fg.suptitle(titulo, fontsize="smaller", color=cchart["titulo"])

    xlabels = ax.get_xticklabels()
    ylabels = ax.get_yticklabels()
    plt.setp(xlabels, ha="right", fontsize=6, color=cchart["axsx"], rotation=30)
    plt.setp(ylabels, ha="right", fontsize=6, color=cchart["axsy"])
    ax.set_ylabel("Ingresos / Costos ($)", fontsize=6, color=cchart["asy"])
    ax.set_xlabel("", fontsize=6, color=cchart["asx"])

    # Centrar las etiquetas entre las barras
    ax.set_xticks(x + width / 2, lyear)
    ax.yaxis.set_major_formatter(currency)
    ax.tick_params(axis="x", colors=cchart["asx"])
    ax.tick_params(axis="y", colors=cchart["asx"])

    # 2do eje: margen neto (puede ser negativo)
    av.plot(
        x + width / 2,
        resum["margenNT"],
        color=cchart["plot0"],
        linewidth=0.6,
        ls="--",
        alpha=0.9,
        marker="o",
    )
    offset = 0.02 * (resum["margenNT"].max() - resum["margenNT"].min() or 1)
    for i in x:
        av.text(
            x[i] + width / 2,
            (
                resum["margenNT"].iloc[i] + offset
                if resum["margenNT"].iloc[i] >= 0
                else resum["margenNT"].iloc[i] - offset
            ),
            "{:>+4.1%}".format(resum["margenNT"].iloc[i]),
            fontsize=5,
            va="center",
            color="cyan",
        )

    tlabels = av.get_yticklabels()
    plt.setp(tlabels, ha="left", fontsize=6, color=cchart["plot0"])
    av.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:2.0%}"))
    av.set_ylabel("Margen Neto", color=cchart["plot0"], fontsize=6)

    # Limites simétricos para mostrar negativos y positivos
    # Sanitize values to avoid NaN or Inf in yabs
    max_val = resum["margenNT"].max()
    min_val = resum["margenNT"].min()
    max_val = np.nan_to_num(max_val, nan=0.0, posinf=0.0, neginf=0.0)
    min_val = np.nan_to_num(min_val, nan=0.0, posinf=0.0, neginf=0.0)
    # yabs = max(abs(max_val), abs(min_val), 0.1)

    # av.set(ylim=(-yabs * 1.20, yabs * 1.20))
    av.tick_params(axis="y", colors=cchart["plot0"])

    av.spines[["top", "bottom", "left"]].set_visible(False)
    av.spines["right"].set_color(cchart["plot0"])


# grafica performan traza plan
def chart_trazaplan(fg=None, traza=None, cchart=None):
    """
    @param fg: figura cava sobre la se hará el plot
    @param traza:  dict de unload trazaplan
    @param cchart:
    @return:  Chat de capital invertido vs plan trazado."""

    fg.clear()
    ax = fg.add_subplot()
    av = ax.twinx()
    ax.set_box_aspect(0.30)
    ax.set_facecolor(cchart["fondo"])
    titulo = "Plan (Trazado/Alcanzado) vs Rendimiento Total"

    if traza:

        meta, tinv, tvis, efec, tdiv = [], [], [], [], []
        for key in traza:
            if key["costobase"] != 0:
                meta.append(key["extracto"].year)
                efec.append(key["efectividad"])
                tinv.append(float(key["tinversion"]))
                tvis.append(key["vision"])
                tdiv.append(key["trendimiento"])

        # imax = float(imax) * 1.05
        ddato = {"Alcanzado": tinv, "Rendimiento": tdiv}

        x = np.arange(len(meta))
        width, multiplier, i, offset = 0.30, 1, 1, 0
        p_legend = []

        ax.plot(
            x + offset,
            tvis,
            linestyle=":",
            linewidth=1,
            color=cchart["plot8"],
            alpha=0.90,
        )
        p_legend.append(mpatches.Patch(color=cchart["plot8"], label="Plan Trazado"))

        for i in x[1:]:
            xcol = "cyan" if efec[i] > 0 else "red"
            ax.text(
                x[i] - offset,
                tinv[i] + offset,
                "{:>+4.1%}".format(efec[i]),
                fontsize=5,
                va="center",
                color=xcol,
            )

        ax.spines[["top", "bottom", "right"]].set_visible(False)
        ax.grid(True, color=cchart["texto"], linewidth=0.1)
        ax.set_ylabel("Capital Invertido($)", fontsize=6, color=cchart["asx"])
        ax.set_xticks(x + width, meta, fontsize=6)

        plt.setp(
            ax.get_xticklabels(),
            ha="right",
            fontsize=6,
            color=cchart["asy"],
            rotation=30,
        )
        plt.setp(ax.get_yticklabels(), ha="right", fontsize=6, color=cchart["asy"])

        ax.spines.left.set_visible(True)
        ax.spines["left"].set_color(cchart["asy"])
        ax.tick_params(axis="x", colors=cchart["asy"])
        ax.tick_params(axis="y", colors=cchart["asy"])
        ax.yaxis.set_major_formatter(currency)

        #  construcción de 2.º eje, para mostrar % rendimiento de capital + dividendos
        for keys, measurement in ddato.items():
            offset = width * multiplier
            if keys == "Alcanzado":
                ax.bar(x + offset, measurement, width, color=cchart["plot5"], alpha=0.7)
                p_legend.append(mpatches.Patch(color=cchart["plot5"], label=keys))

            if keys == "Rendimiento":
                av.bar(x + offset, measurement, width / 2, color=cchart["2eje"], alpha=0.9)
                p_legend.append(mpatches.Patch(color=cchart["2eje"], label=keys))

        fg.legend(loc="outside upper right", handles=p_legend, fontsize=5)
        fg.suptitle(titulo, fontsize="smaller", color=cchart["titulo"])

        av.spines[["top", "bottom", "left"]].set_visible(False)
        av.set_ylabel("Total (Cap + Div)", fontsize=6, color=cchart["2eje"])
        av.tick_params(axis="y", labelcolor=cchart["2eje"])
        av.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:2.0%}"))

        tlabels = av.get_yticklabels()
        av.set_ylim([0, 0.2])
        plt.setp(tlabels, ha="left", fontsize=6, color=cchart["2eje"])
        av.tick_params(axis="y", colors=cchart["2eje"])
        av.spines["right"].set_color(cchart["2eje"])
        av.spines.right.set_visible(True)


# ============================================================
# Gráfico de estrategia compartido (usable desde cualquier módulo)
# ============================================================
def show_strategy_chart(
    parent, symbol, vehiculo="Crypto", targets=None, chart_windows=None, Xposition=None, show_pm=False
):
    """Abre ventana de gráfico de estrategia para cualquier activo.

    Args:
        parent:        Tk root/Toplevel (para crear Toplevel y after())
        symbol:        símbolo del activo (ej: "AAPL", "BTCUSDT")
        vehiculo:      "Crypto" | "Stock"
        targets:       dict opcional con: entry, sl, objetivo (float)
        chart_windows: dict externo para rastrear ventanas abiertas (evitar duplicados)
    """
    if chart_windows is None:
        chart_windows = {}

    # Evitar ventana duplicada para el mismo símbolo
    existing = chart_windows.get(symbol)
    if existing:
        try:
            if existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                return
        except Exception:
            pass
        chart_windows.pop(symbol, None)

    bg_color = "#16213e"
    _timer_id = [None]
    targets = targets or {}

    # Periodos disponibles: btn_label → {period, high_label, n_tail}
    _PERIODS = {
        "1y": {"period": "1y", "high_label": "Máx 52 sem", "n_tail": 60},
        "6m": {"period": "6mo", "high_label": "Máx 26 sem", "n_tail": 50},
        "3m": {"period": "3mo", "high_label": "Máx 13 sem", "n_tail": 42},
        "1m": {"period": "1mo", "high_label": "Máx 1 mes", "n_tail": 21},
        "1s": {"period": "1mo", "high_label": "Máx 1 sem", "n_tail": 21, "n_high": 7},
    }
    _current_period = ["5d"]  # yfinance period code activo
    _btn_refs = {}  # {btn_label: Button widget}

    # ----- Helpers de datos -----
    def _get_data():
        try:
            result = get_yfinance(ticket=symbol, vehiculo=vehiculo, period=_current_period[0], interval="1d")
            if result:
                _, df = result
                if df is not None and not df.empty and len(df) >= 14:
                    return df
        except Exception:
            pass
        return None

    def _get_price(df):
        import Class_customer  # import diferido — evita ciclo: Class_DataFrame→Class_customer→Modulos_Comunes→Class_DataFrame

        info = Class_customer.DataHub.info.get(symbol, {})
        ws = info.get("websocket", {})
        p = ws.get("last") or ws.get("close") or ws.get("price")
        if p:
            try:
                return float(p)
            except Exception:
                pass
        if df is not None and not df.empty:
            return float(df["Close"].iloc[-1])
        return 0.0

    def _get_period_cfg():
        """Retorna cfg del periodo activo."""
        for cfg in _PERIODS.values():
            if cfg["period"] == _current_period[0]:
                return cfg
        return _PERIODS["1m"]

    # ----- Dibujo -----
    def _draw_chart(win_ref, fig_ref, canvas_ref):
        fig_ref.clear()
        ax = fig_ref.add_subplot(111)
        ax.set_facecolor(bg_color)

        label = symbol.replace("USDT", "") if vehiculo == "Crypto" else symbol
        wm_size = min(72, max(20, int(200 / max(len(label), 1))))
        ax.text(
            0.5,
            0.5,
            label,
            transform=ax.transAxes,
            fontsize=wm_size,
            fontweight="bold",
            color="white",
            alpha=0.04,
            ha="center",
            va="center",
            zorder=0,
            clip_on=True,
        )

        df = _get_data()
        price_now = _get_price(df)

        if df is None or len(df) < 14 or price_now <= 0:
            ax.text(
                0.5,
                0.5,
                "Sin datos disponibles",
                transform=ax.transAxes,
                color="gray",
                ha="center",
                va="center",
                fontsize=12,
            )
            canvas_ref.draw_idle()
            return

        cfg = _get_period_cfg()
        high_label = cfg["high_label"]
        n_tail = cfg["n_tail"]
        n_high = cfg.get("n_high", n_tail)  # barras para calcular el máximo del periodo

        atr = calcular_atr(df)
        atr = atr if atr and atr > 0 else price_now * 0.02

        entry = targets.get("entry")
        ref_price = entry if entry and entry > 0 else price_now
        sl_price = targets.get("sl") or (ref_price - atr * 1.5)
        objetivo_price = targets.get("objetivo") or (ref_price + atr * 2.0)

        # Histórico (n_tail velas del periodo seleccionado)
        df_vis = df.tail(n_tail)
        hist = df_vis["Close"].values.astype(float)
        n_hist = len(hist)

        # Máximo del periodo: usa n_high barras (puede ser menor que n_tail, ej. 1s = 7 días)
        period_high = float(df.tail(n_high)["High"].max())
        period_high_pct = ((period_high / price_now) - 1) * 100 if price_now > 0 else 0

        # Ocultar Max cuando está a ≤5% del objetivo (se solapan visualmente)
        _diff_obj_high = abs((objetivo_price - period_high) / period_high) * 100 if period_high > 0 else 0
        show_period_high = _diff_obj_high > 5.0

        x_hist = np.arange(n_hist)
        ax.plot(x_hist, hist, color="#00d4ff", linewidth=1.5)

        # Proyecciones (20 barras)
        n_proj = 20
        x_proj = np.arange(n_hist - 1, n_hist + n_proj)
        x_total = n_hist + n_proj

        y_obj = np.linspace(price_now, objetivo_price, len(x_proj))
        y_sl = np.linspace(price_now, sl_price, len(x_proj))
        y_ref = np.full_like(x_proj, ref_price, dtype=float)

        ax.fill_between(x_proj, y_ref, y_obj, alpha=0.12, color="#00ff88")
        ax.fill_between(x_proj, y_sl, y_ref, alpha=0.15, color="#ff4444")
        ax.plot(x_proj, y_obj, color="#00ff88", linewidth=1.0, linestyle="--")
        ax.plot(x_proj, y_sl, color="#ff4444", linewidth=1.0, linestyle="--")
        if show_period_high:
            y_phigh = np.linspace(price_now, period_high, len(x_proj))
            ax.fill_between(x_proj, y_obj, y_phigh, alpha=0.07, color="#ff9900")
            ax.plot(x_proj, y_phigh, color="#ff9900", linewidth=1.2, linestyle="--")

        ax.axhline(y=objetivo_price, color="#00ff88", linewidth=0.9, linestyle=":", alpha=0.4)
        ax.axhline(y=sl_price, color="#ff4444", linewidth=0.9, linestyle=":", alpha=0.4)
        ax.axhline(y=price_now, color="#00d4ff", linewidth=0.8, linestyle="-", alpha=0.3)
        ax.axvline(x=n_hist - 1, color="gray", linewidth=0.8, linestyle="--", alpha=0.4)

        # Línea del máximo del periodo (solo si no se solapa con objetivo)
        if show_period_high:
            ax.axhline(y=period_high, color="#ff9900", linewidth=0.9, linestyle=":", alpha=0.4)

        # Línea de entrada (si hay posición)
        if entry and entry > 0:
            ax.axhline(y=entry, color="#ffff00", linewidth=1, linestyle="-", alpha=0.4)
            ax.annotate(f"  Entrada {entry:.4f}", xy=(0, entry), fontsize=7, color="#ffff00", va="bottom")
            pnl_pct_pos = ((price_now / entry) - 1) * 100
            pnl_color = "#00ff88" if pnl_pct_pos >= 0 else "#ff4444"
            ax.annotate(
                f"PnL: {pnl_pct_pos:+.2f}%",
                xy=(n_hist - 2, price_now),
                fontsize=8,
                color=pnl_color,
                fontweight="bold",
                va="bottom",
                ha="right",
            )

        # Anotaciones derecha
        x_label = x_total - 1
        obj_pct = ((objetivo_price / ref_price) - 1) * 100 if ref_price > 0 else 0
        sl_pct_val = ((sl_price / ref_price) - 1) * 100 if ref_price > 0 else 0

        if show_period_high:
            ax.annotate(
                f"  {high_label}  {period_high:.4f}  (+{period_high_pct:.1f}%)",
                xy=(x_label, period_high),
                fontsize=8,
                color="#ff9900",
                fontweight="bold",
                va="center",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#ff9900", alpha=0.2),
            )
        ax.annotate(
            f"  Objetivo +{obj_pct:.1f}%  {objetivo_price:.4f}",
            xy=(x_label, objetivo_price),
            fontsize=8,
            color="#00ff88",
            fontweight="bold",
            va="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#00ff88", alpha=0.2),
        )
        ax.annotate(
            f"  \u25c4 Actual  {price_now:.4f}",
            xy=(x_label, price_now),
            fontsize=8,
            color="#00d4ff",
            fontweight="bold",
            va="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#00d4ff", alpha=0.15),
        )
        ax.annotate(
            f"  Ref.SL {sl_pct_val:.1f}%  {sl_price:.4f}",
            xy=(x_label, sl_price),
            fontsize=8,
            color="#ff4444",
            fontweight="bold",
            va="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#ff4444", alpha=0.2),
        )

        # Anotación derecha precio medio — solo desde window_estrategia y entre SL y máximo u objetivo
        upper_ref = max(period_high, objetivo_price)
        if show_pm and entry and entry > 0 and sl_price <= entry <= upper_ref:
            pm_pct = ((price_now / entry) - 1) * 100
            pm_color = "#00ff88" if pm_pct >= 0 else "#ff4444"
            ax.annotate(
                f"  PM  {entry:.4f}  ({pm_pct:+.1f}%)",
                xy=(x_label, entry),
                fontsize=8,
                color="#ffff00",
                fontweight="bold",
                va="center",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffff00", alpha=0.2),
            )

        # Etiquetas de zona — desplazadas al 88% del ylim para separar de la leyenda
        ylim = ax.get_ylim()
        y_zona = ylim[0] + (ylim[1] - ylim[0]) * 0.88
        ax.text(
            n_hist * 0.4,
            y_zona,
            "HISTORIAL",
            fontsize=9,
            color="white",
            ha="center",
            alpha=0.75,
            va="top",
            fontweight="bold",
        )
        ax.text(
            n_hist + n_proj * 0.4,
            y_zona,
            "PREVISION",
            fontsize=9,
            color="white",
            ha="center",
            alpha=0.75,
            va="top",
            fontweight="bold",
        )

        # Título informativo — 3 líneas encima del gráfico
        rr = abs(obj_pct / sl_pct_val) if sl_pct_val != 0 else 0
        line1 = f"{symbol}  |  {vehiculo}  —  Actual: {price_now:.4f}"
        line2 = f"Obj: +{obj_pct:.1f}%   SL: {sl_pct_val:.1f}%   R/R: 1:{rr:.1f}"
        line3 = f"{high_label}: {period_high:.4f}  (+{period_high_pct:.1f}%)" if show_period_high else ""
        title_text = f"{line1}\n{line2}\n{line3}" if show_period_high else f"{line1}\n{line2}"
        ax.set_title(
            title_text,
            loc="left",
            fontsize=7.5,
            color="black",
            fontfamily="monospace",
            pad=4,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.92, pad=3),
        )

        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(colors="gray", labelsize=7)
        for spine in ax.spines.values():
            spine.set_color("#2a3a5e")
        ax.set_xlim(-1, x_total + 2)
        ax.yaxis.set_major_formatter(lambda x, _: f"{x:.4f}")

        # Eje X con fechas reales
        try:
            dates = df_vis.index
            p = _current_period[0]
            fmt = "%b '%y" if p == "1y" else ("%d %b" if p in ("6mo", "3mo") else "%d/%m")

            # Hasta 6 ticks espaciados uniformemente en la zona histórica
            n_ticks = min(6, n_hist)
            tick_pos = np.linspace(0, n_hist - 1, n_ticks, dtype=int)
            tick_lbl = [dates[pos].strftime(fmt) if pos < len(dates) else "" for pos in tick_pos]

            ax.set_xticks(list(tick_pos))
            ax.set_xticklabels(tick_lbl, fontsize=7, color="gray", rotation=30, ha="right")

            # Fecha estimada fin proyección
            proj_end = dates[-1] + pd.Timedelta(days=n_proj)
            ax.text(
                x_total - 1,
                -0.06,
                f"~{proj_end.strftime(fmt)}",
                transform=ax.get_xaxis_transform(),
                fontsize=7,
                color="gray",
                ha="center",
                va="top",
            )
        except Exception:
            ax.set_xticklabels([])

        fig_ref.tight_layout(pad=0.5)
        fig_ref.subplots_adjust(top=0.83, bottom=0.12)

        # Línea separadora entre leyenda (título) y área del gráfico
        ax.plot([0, 1], [1, 1], transform=ax.transAxes, color="#445577", linewidth=0.8, alpha=0.7, clip_on=False)

        canvas_ref.draw_idle()

    def _auto_refresh(win_ref, fig_ref, canvas_ref):
        if win_ref.winfo_exists():
            _draw_chart(win_ref, fig_ref, canvas_ref)
            _timer_id[0] = win_ref.after(5000, _auto_refresh, win_ref, fig_ref, canvas_ref)

    def _on_close(win_ref):
        if _timer_id[0]:
            win_ref.after_cancel(_timer_id[0])
        chart_windows.pop(symbol, None)
        win_ref.destroy()

    def _set_period(p_code, btn_lbl, win_ref, fig_ref, canvas_ref):
        if _timer_id[0]:
            win_ref.after_cancel(_timer_id[0])
        _current_period[0] = p_code
        for lbl, btn in _btn_refs.items():
            if lbl == btn_lbl:
                btn.configure(bg="#00d4ff", fg="#16213e")
            else:
                btn.configure(bg="#1a2a4a", fg="#888888")
        _draw_chart(win_ref, fig_ref, canvas_ref)
        _timer_id[0] = win_ref.after(5000, _auto_refresh, win_ref, fig_ref, canvas_ref)

    # ----- Crear ventana -----
    try:
        x = parent.winfo_rootx() + parent.winfo_width() - 150 if Xposition is None else Xposition
        y = parent.winfo_rooty() + 200
    except Exception:
        x, y = 200, 150

    win = tk.Toplevel(parent)
    win.title(f"Estrategia - {symbol}")
    win.geometry(f"750x560+{x}+{y}")
    win.configure(bg=bg_color)
    win.resizable(False, False)
    chart_windows[symbol] = win

    # Toolbar de selección de periodo (alineado a la derecha)
    toolbar = tk.Frame(win, bg=bg_color, pady=0)
    toolbar.pack(side=tk.TOP, fill=tk.X)
    btn_frame = tk.Frame(toolbar, bg=bg_color)
    btn_frame.pack(side=tk.RIGHT, padx=8)
    tk.Label(btn_frame, text="Intervalo:", bg=bg_color, fg="#888888", font=("Arial", 8)).pack(side=tk.LEFT, padx=(0, 4))
    for btn_lbl, cfg in _PERIODS.items():
        is_active = cfg["period"] == _current_period[0]
        btn = tk.Button(
            btn_frame,
            text=btn_lbl,
            width=4,
            font=("Arial", 8, "bold"),
            bg="#00d4ff" if is_active else "#1a2a4a",
            fg="#16213e" if is_active else "#888888",
            relief=tk.FLAT,
            cursor="hand2",
        )
        _btn_refs[btn_lbl] = btn
        btn.pack(side=tk.LEFT, padx=2)

    fig = Figure(figsize=(7.5, 5.4), dpi=100, facecolor=bg_color)
    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Asignar commands una vez que win/fig/canvas existen
    for btn_lbl, btn in _btn_refs.items():
        p_code = _PERIODS[btn_lbl]["period"]
        btn.configure(command=lambda pc=p_code, bl=btn_lbl: _set_period(pc, bl, win, fig, canvas))

    _draw_chart(win, fig, canvas)
    _timer_id[0] = win.after(5000, _auto_refresh, win, fig, canvas)
    win.protocol("WM_DELETE_WINDOW", lambda: _on_close(win))
