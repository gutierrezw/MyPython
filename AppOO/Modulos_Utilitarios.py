from Modulos_python import (
    datetime,
    timedelta,
    pd,
    ttk,
    os,
    E,
    W,
    N,
    S,
    date,
    relativedelta,
    Path,
    EMAIndicator,
    MACD,
    RSIIndicator,
    math,
)


def is_null(s):
    """Valida si el parametro contingent valor Null o espacios"""

    if s is None or (isinstance(s, str) and (s.isspace() or s == "")):
        rc = True
    else:
        rc = False
    return rc


def is_none(s) -> bool:
    """Valida si el parametro contingent valor None"""
    if s is None:
        rc = True
    else:
        rc = False
    return rc


def is_datetime(s):
    try:
        datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False


def is_numeric(s) -> bool:
    """Valida si es numerico  string"""
    try:
        if is_none(s):
            return False
        else:
            float(s)
            return True
    except ValueError:
        return False


def is_vacio(s) -> bool:
    """
    @param s: dict o list
    @return:  Valida si 's' es vacio
    """
    sset = True
    try:
        if type(s) is dict:
            if s == {}:
                sset = False
            else:
                if "Stock" in s or "Crypto" in s:
                    sset = False

        if type(s) is list:
            if s == []:
                sset = False

    except ValueError:
        return sset


# Calcula la cantidad de dígitos decimales a partir de un step_size.
def calculate_decimal_places(step_size):
    """
    Calcula la cantidad de dígitos decimales a partir de un step_size.
    Ej: 0.1 -> 1, 0.01 -> 2, 0.00001 -> 5
    """
    if step_size > 0:
        return int(round(-math.log10(step_size)))


def is_magnitud(x) -> int:
    """
    @param x: numero decimal
    @return: obtiene magnitud de numero
    """
    try:
        i = 0
        if is_numeric(x):
            n = int(x)
            for i in range(0, 100):
                if n % 10 == 0:
                    if int(n / 10) == 0:
                        return i - 1

                n = int(n / 10)

    except ValueError:
        return -1


def str_float(s):
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


# ordena estructura array[dict()] donde cada elemento es dict()
def sort_positions(struct, orden) -> list:
    i = 0
    dic = list(orden[0].values())
    keys = dic[0]
    como = orden[1]
    if como == "ASC":
        for i in range(len(struct) - 1):
            for j in range(i + 1, len(struct)):
                if struct[i][keys] > struct[j][keys]:
                    sortposition = struct[i]
                    struct[i] = struct[j]
                    struct[j] = sortposition
    else:
        for i in range(len(struct) - 1):
            for j in range(i + 1, len(struct)):
                if struct[i][keys] < struct[j][keys]:
                    sortposition = struct[i]
                    struct[i] = struct[j]
                    struct[j] = sortposition

    return struct


def valida_meses_consecutivos(inicio=None, fin=None):
    """
    @param inicio:  fecha inicial
    @param fin: fecha final
    @return: retorna TRUE si los meses son consecutivos entre inicio y fin."""

    s_fin, s_inicio = "", ""
    if isinstance(inicio, date):
        s_inicio = inicio.strftime("%Y-%m")
    elif isinstance(inicio, str):
        s_inicio = datetime.strptime(inicio, "%Y-%m")

    if isinstance(fin, datetime):
        s_fin = fin.strftime("%Y-%m")
    elif isinstance(fin, date):
        s_fin = fin.strftime("%Y-%m")

    f_inicio = datetime.strptime(s_inicio, "%Y-%m")
    f_fin = datetime.strptime(s_fin, "%Y-%m")
    diferencia = relativedelta(dt1=f_fin, dt2=f_inicio, months=1)

    return f_fin == f_inicio + diferencia

    def convertir(dato):
        num = 0
        if not dato.isalpha() and not isNumeric(dato):
            x = dato.replace("%", "")
            num = float(x) / 100
        else:
            num = 0.10
        return num

    valor = 0.00
    """
    @ valora ganancias del precio medio
    @ respecto al precio objetivo
    """
    if positions["Obje"] > 0:
        dprc: float = (positions["avgCost"] - positions["prcmd"]) / positions["avgCost"]
        keys = tabla["Gprc"]
        for i in keys:
            if convertir(i) >= dprc:
                valor += keys[i]
                break
            else:
                if convertir(i) == 1:
                    valor += keys[i]

        """
        @ valora delta de Gyp proyectado
        @ respecto a las Gyp  objetivo
        """
        if positions["GyPo"] > 0:
            keys = tabla["GGyp"]
            dpyg = (positions["GyPp"] - positions["GyPo"]) / invertir
            for i in keys:
                if convertir(i) >= dpyg:
                    valor += keys[i]
                    break
                else:
                    if convertir(i) == 1:
                        valor += keys[i]
        """
        @ valora peso del activo para que no
        @ exceda el 10% de la cartera
        """
        if peso > 0:
            keys = tabla["peso"]
            if peso <= 0.10:
                valor += keys["menorq"]
            else:
                valor += keys["mayorq"]

    return valor / 8


def buscar_ticker(positions, ticket) -> float:
    """
    @param positions: estructura de portafolio
    @param ticket:  activo a buscar en positions
    @return:  logic de encontrado o NO y la información encontrada
    """
    keys, found = False, {}
    if type(positions) is dict:
        keys = dict()
        for keys in positions:
            ix = "contractDesc" if "contractDesc" in keys else "ticket"
            if keys[ix] == ticket:
                found = True
                break

    if type(positions) is list:
        keys = dict()
        for keys in positions:
            ix = "contractDesc" if "contractDesc" in keys else "ticket"
            if keys[ix] == ticket:
                found = True
                break

    return found, keys


def convierte_ticket_crypto(s: str) -> str:
    conversion_yfinance = {"VRLA": "VRLAF", "POL-USD": "MATIC-USD"}
    ticket = s
    ticket = ticket.replace("USDT", "-USD")
    ticket = ticket.replace(" CRYPTO", "-USD")

    # conversion temporal para los symbol IBKR's no están yfinance
    ticket = (
        ticket if ticket not in conversion_yfinance else conversion_yfinance[ticket]
    )
    return ticket


def currency(y=None, pos=None):
    """The two arguments are the value and tick position"""
    x = y if y >= 0 else -y

    if x >= 1e6:
        s = "${:1.1f}M".format(y * 1e-6)
    else:
        if x < 1e3:
            if x > 1:
                s = "${:3.1f}".format(y)
            else:
                s = "${:3.3f}".format(y)
        else:
            s = "${:1.1f}K".format(y * 1e-3)

    return s


def porcentaje(y, pos=1):
    """The two arguments are the value porcentaje"""
    x = y if y >= 0 else -y

    if x >= 1e3:
        s = "{:4.0%}".format(y)
    else:
        if x < 1e2:
            s = "{:3.2%}".format(y)
        else:
            s = "{:2.1%}".format(y)

    return s


def display_red_green(campo=None, i=None) -> str:
    if not is_none(i):
        if i % 2 != 0:
            cbg = "Wr.TLabel" if campo < 0 else "Wg.TLabel"

        if i % 2 == 0:
            cbg = "Br.TLabel" if campo < 0 else "Bg.TLabel"

    if is_none(i):
        cbg = "Wr.TLabel" if campo < 0 else "Wg.TLabel"

    return cbg


def display_azul(campo, i) -> str:
    if campo < 0.10:
        iibg = "Cb.TLabel" if i == 5 else ("Cb.TLabel" if i % 2 == 0 else "Cw.TLabel")
    else:
        iibg = "Sy.TLabel" if i == 5 else ("Sy.TLabel" if i % 2 == 0 else "Cw.TLabel")

    return iibg


def vehiculo_parm(vehiculo=None):
    """
    @param vehiculo:
    @return:
    """
    if vehiculo in ("Crypto", "token"):
        symbol = "BTCUSDT"
        rtn_index = "Return BTC"
        cum_index = "Cum BTC"
        index_ref = "BTC++index"

    elif vehiculo == "Stock":
        symbol = "^GSPC"
        rtn_index = "Return SPX"
        cum_index = "Cum SPX"
        index_ref = "SPX++index"

    elif vehiculo == "BBVA.ARS":
        symbol = "^MERV"
        rtn_index = "Return MRV"
        cum_index = "Cum MRV"
        index_ref = "MRV++index"

    return symbol, rtn_index, cum_index, index_ref


# Función para calcular retorceso de fibonacci
def retrocesos_fib(low=None, high=None, ema09=None, ema21=None, datos=None, desde=None):
    """
    @param low:
    @param high:
    @param ema09: serie de media movil exponencial 9
    @param ema21: serie de media movil exponencial 21
    @param datos: serie de datos de precios
    @param desde: fecha desde la cual se calcularan los retrocesos
    @return:  sucesión fibonacci y tendencia alcista o bajista."""

    fib = [0, 0.236, 0.382, 0.50, 0.618, 0.786, 1.0, 1.272, 1.618, 2.0]
    t_alcista, t_bajista, long = {}, {}, True
    rango = high - low
    for ix, valor in enumerate(fib):
        key = "{:> 3.1%}".format(valor)
        t_alcista.update({key: float(low + valor * rango)})

        if high - valor * rango > 0:
            fib_ant = high - valor * rango
            t_bajista.update({key: float(fib_ant)})
        else:
            t_bajista.update({key: float(fib_ant)})

    if ema09 <= ema21:
        zone_fib0 = dict(
            y1=t_alcista[" 0.0%"],
            y2=t_alcista[" 23.6%"],
            color="red",
            alpha=0.2,
            interpolate=True,
            where=(datos["EMA009"].index > desde),
        )
        zone_fib1 = dict(
            y1=t_alcista[" 23.6%"],
            y2=t_alcista[" 38.2%"],
            color="green",
            alpha=0.2,
            interpolate=True,
            where=(datos["EMA009"].index > desde),
        )
        zone_fib2 = dict(
            y1=t_alcista[" 38.2%"],
            y2=t_alcista[" 61.8%"],
            color="lime",
            alpha=0.2,
            interpolate=True,
            where=(datos["EMA009"].index > desde),
        )
        zone_fib3 = dict(
            y1=t_alcista[" 61.8%"],
            y2=t_alcista[" 78.6%"],
            color="cyan",
            alpha=0.2,
            interpolate=True,
            where=(datos["EMA009"].index > desde),
        )
        zone_fib4 = dict(
            y1=t_alcista[" 78.6%"],
            y2=t_alcista[" 100.0%"],
            color="gray",
            alpha=0.2,
            interpolate=True,
            where=(datos["EMA009"].index > desde),
        )
        zone_fib5 = dict(
            y1=t_alcista[" 100.0%"],
            y2=t_alcista[" 127.2%"],
            color="blue",
            alpha=0.2,
            interpolate=True,
            where=(datos["EMA009"].index > desde),
        )
    else:
        long = False
        zone_fib0 = dict(
            y1=t_bajista[" 0.0%"],
            y2=t_bajista[" 23.6%"],
            color="red",
            alpha=0.2,
            interpolate=True,
            where=(datos["EMA009"].index > desde),
        )
        zone_fib1 = dict(
            y1=t_bajista[" 23.6%"],
            y2=t_bajista[" 38.2%"],
            color="green",
            alpha=0.2,
            interpolate=True,
            where=(datos["EMA009"].index > desde),
        )
        zone_fib2 = dict(
            y1=t_bajista[" 38.2%"],
            y2=t_bajista[" 61.8%"],
            color="lime",
            alpha=0.2,
            interpolate=True,
            where=(datos["EMA009"].index > desde),
        )
        zone_fib3 = dict(
            y1=t_bajista[" 61.8%"],
            y2=t_bajista[" 78.6%"],
            color="cyan",
            alpha=0.2,
            interpolate=True,
            where=(datos["EMA009"].index > desde),
        )
        zone_fib4 = dict(
            y1=t_bajista[" 78.6%"],
            y2=t_bajista[" 100.0%"],
            color="gray",
            alpha=0.2,
            interpolate=True,
            where=(datos["EMA009"].index > desde),
        )
        zone_fib5 = dict(
            y1=t_bajista[" 100.0%"],
            y2=t_bajista[" 127.2%"],
            color="blue",
            alpha=0.3,
            interpolate=True,
            where=(datos["EMA009"].index > desde),
        )

    return (
        long,
        t_alcista,
        t_bajista,
        zone_fib0,
        zone_fib1,
        zone_fib2,
        zone_fib3,
        zone_fib4,
        zone_fib5,
    )


def nivel_fib(ax, l_ix, t_alcista, t_bajista, long):
    if long:
        t_fib = t_alcista
    else:
        t_fib = t_bajista
    i = 0
    for key, valor in t_fib.items():
        if i != 0 and long:
            ax.text(l_ix, valor, key, fontsize=5, ha="center", color="white")

        if i != 6 and not long:
            ax.text(l_ix, valor, key, fontsize=5, ha="center", color="white")

        i += 1
    return ax


def numero_fib(n=None) -> int:
    """
    @param n:  numero de entrada
    @return: obtiene numero fibonacci inmediato inferior al input
    """
    fib = [0, 1, 2]
    for i in range(3, 15):
        fib.append(fib[i - 2] + fib[i - 1])
        if fib[i] > n:
            break
    return fib[i - 1]


# reemplaza nan por null -- esto es para escribitra de json
def limpiar_nan(obj):
    if isinstance(obj, dict):
        return {k: limpiar_nan(v) for k, v in obj.items()}
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    else:
        return obj


# Función para calcular indicadores técnicos
def get_indicadores(symbol=None, datos=None):
    """
    Calcula indicadores técnicos para el símbolo. Devuelve un diccionario
    con los indicadores del último punto de cada serie,
    para temporalidad diaria, semanal y mensual.
    """
    temporalidades = {"diaria": "D", "semanal": "W", "mensual": "ME"}
    MaximoMInimos = {
        "diaria": ("13_semanas_max", "13_semanas_min"),
        "semanal": ("26_semanas_max", "26_semanas_min"),
        "mensual": ("52_semanas_max", "52_semanas_min"),
    }

    df = datos.copy().dropna()
    if not df.empty:

        value = {"datos_tecnicos": {}}
        highs_lows = get_highs_lows(symbol=symbol, df=df)

        for nombre_temp, freq in temporalidades.items():
            try:
                # Resamplear según la temporalidad
                df_resampled = (
                    df.resample(freq)
                    .agg(
                        {
                            "Open": "first",
                            "High": "max",
                            "Low": "min",
                            "Close": "last",
                            "Volume": "sum",
                        }
                    )
                    .dropna()
                )

                if df_resampled.empty:
                    continue

                df_resampled["rsi"] = RSIIndicator(close=df_resampled["Close"]).rsi()
                df_resampled["EMA020"] = EMAIndicator(
                    close=df_resampled["Close"], window=20
                ).ema_indicator()
                df_resampled["EMA050"] = EMAIndicator(
                    close=df_resampled["Close"], window=50
                ).ema_indicator()
                df_resampled["EMA100"] = EMAIndicator(
                    close=df_resampled["Close"], window=100
                ).ema_indicator()
                df_resampled["EMA200"] = EMAIndicator(
                    close=df_resampled["Close"], window=200
                ).ema_indicator()
                df_resampled["EMA009"] = EMAIndicator(
                    close=df_resampled["Close"], window=9
                ).ema_indicator()
                df_resampled["EMA021"] = EMAIndicator(
                    close=df_resampled["Close"], window=21
                ).ema_indicator()
                df_resampled["EMA055"] = EMAIndicator(
                    close=df_resampled["Close"], window=55
                ).ema_indicator()
                df_resampled["EMA144"] = EMAIndicator(
                    close=df_resampled["Close"], window=144
                ).ema_indicator()
                df_resampled["macd"] = MACD(close=df_resampled["Close"]).macd()

                # Calcular máximos y mínimos y retroceso fibonacci
                ndatos = numero_fib(n=df_resampled.shape[0])
                minimax = df_resampled[["High", "Low"]].tail(ndatos)
                xmax = minimax["High"].max()
                f_desde = minimax.loc[minimax["High"] == xmax].index[0]
                xmin = minimax["Low"].loc[f_desde.strftime("%Y-%m-%d") :].min()
                xmax = minimax["High"].max()

                ema09, ema21 = (
                    df_resampled["EMA009"].iloc[-1],
                    df_resampled["EMA021"].iloc[-1],
                )
                x_long, x_alcista, x_bajista, *_ = retrocesos_fib(
                    low=xmin,
                    high=xmax.max(),
                    ema09=ema09,
                    ema21=ema21,
                    datos=df_resampled,
                    desde=f_desde,
                )

                ultima = df_resampled.iloc[-1]

                value["datos_tecnicos"][nombre_temp] = {
                    "rsi": float(round(ultima["rsi"], 7)),
                    "ema(20,50,100,200)": {
                        "EMA020": float(round(ultima["EMA020"], 7)),
                        "EMA050": float(round(ultima["EMA050"], 7)),
                        "EMA100": float(round(ultima["EMA100"], 7)),
                        "EMA200": float(round(ultima["EMA200"], 7)),
                    },
                    "ema(09,21,055,144)": {
                        "EMA009": float(round(ultima["EMA009"], 7)),
                        "EMA021": float(round(ultima["EMA021"], 7)),
                        "EMA055": float(round(ultima["EMA055"], 7)),
                        "EMA144": float(round(ultima["EMA144"], 7)),
                    },
                    "retroceso_fibonacci": {
                        "longico": x_long,
                        "tendencia alcista": x_alcista,
                        "tendencia_bajista": x_bajista,
                    },
                    "macd": float(round(ultima["macd"], 7)),
                    MaximoMInimos[nombre_temp][0]: highs_lows[
                        MaximoMInimos[nombre_temp][0]
                    ],  # Maximo
                    MaximoMInimos[nombre_temp][1]: highs_lows[
                        MaximoMInimos[nombre_temp][1]
                    ],  # Minimo
                    "precio_calculo": float(round(ultima["Close"], 7)),
                }
            except (EncodingWarning, Exception) as e:
                print(f"get_indicadores({symbol}, {nombre_temp}): {e}")
                continue

        return value["datos_tecnicos"]


# Calcula los máximos y mínimos de 52, 26 y 13 semanas para symbol
def get_highs_lows(symbol: str, df=None) -> dict:
    try:
        # Calcular los máximos y mínimos
        today = date.today()
        highs_lows = {}

        if df.empty:
            return highs_lows

        # Detectar si el índice tiene timezone (yfinance) o no (CNV/FCI)
        index_has_tz = df.index.tz is not None

        def make_timestamp(days_ago):
            """Crea timestamp compatible con el índice del DataFrame"""
            ts = pd.Timestamp(today - timedelta(days=days_ago))
            if index_has_tz:
                # Para datos con timezone (yfinance Stock/Crypto)
                ts = ts.tz_localize("UTC").tz_convert("America/New_York")
            return ts

        # 52 semanas (365 días)
        timestamp = make_timestamp(365)
        periodo_52_sem = df.loc[df.index >= timestamp]
        if not periodo_52_sem.empty:
            highs_lows["52_semanas_max"] = float(periodo_52_sem["High"].max())
            highs_lows["52_semanas_min"] = float(periodo_52_sem["Low"].min())

        # 26 semanas (182 días)
        timestamp = make_timestamp(182)
        periodo_26_sem = df.loc[df.index >= timestamp]
        if not periodo_26_sem.empty:
            highs_lows["26_semanas_max"] = float(periodo_26_sem["High"].max())
            highs_lows["26_semanas_min"] = float(periodo_26_sem["Low"].min())

        # 13 semanas (91 días)
        timestamp = make_timestamp(91)
        periodo_13_sem = df.loc[df.index >= timestamp]
        if not periodo_13_sem.empty:
            highs_lows["13_semanas_max"] = float(periodo_13_sem["High"].max())
            highs_lows["13_semanas_min"] = float(periodo_13_sem["Low"].min())

        return highs_lows

    except (EncodingWarning, Exception) as e:
        print(f"get_highs_lows({symbol}): {e}")


def style_app(main=None) -> object:
    """
    @param main:  windonw principal de la aplicación
    @return: configura colores y style de la aplicación
    """
    style = ttk.Style(main)

    # TFrame
    style.configure(
        "TFrame", font=("Courier", 8), foreground="white", background="black"
    )
    style.map(
        "TFrame",
        background=[("selected", "lightblue")],  # Fondo de selección
        foreground=[("selected", "black")],
    )  # Texto de selección

    style.configure(
        "B.TFrame", font=("Courier", 8), foreground="black", background="black"
    )
    style.configure(
        "C.TFrame", font=("Courier", 8), foreground="white", background="DarkCyan"
    )
    style.configure(
        "W.TFrame", font=("Courier", 8), foreground="black", background="white"
    )
    style.configure("R.TFrame", font=("Courier", 8), background="red")

    # Button
    style.configure("W.TButton", foreground="white")
    style.configure("B.TButton", foreground="black")
    style.configure("C.TButton", background="DarkCyan", foreground="black")

    # TNoteBook
    style.configure("TNotebook", background="DarkCyan", borderwidth=1)
    style.configure("TNotebook.Tab", background="DarkCyan", foreground="black")
    style.configure("I.TNotebook.Tab", 
                background="lightcoral",   # Color de fondo cuando NO está seleccionada
                foreground="white"         # Color del texto
    )

    style.configure(
        "Custom.TNotebook.Tab", background="lightblue", font=("Arial", 10, "bold")
    )

    # TLabel
    style.configure(
        "TLabel", font=("Courier", 8), foreground="white", background="black"
    )
    style.configure(
        "C.TLabel", font=("Courier", 8), foreground="white", background="DarkCyan"
    )
    style.configure(
        "Br.TLabel", font=("Courier", 8), foreground="black", background="red3"
    )
    style.configure(
        "Bg.TLabel", font=("Courier", 8), foreground="black", background="green2"
    )
    style.configure(
        "Wr.TLabel", font=("Courier", 8), foreground="White", background="firebrick4"
    )
    style.configure(
        "Wg.TLabel", font=("Courier", 8), foreground="White", background="dark green"
    )
    # (C.TScrollbar)
    style.configure(
        "C.TScrollbar",
        troughcolor="gray",
        background="DarkCyan",
        arrowcolor="black",
        relief="flat",
        gripcount=10,
    )

    # (Treeview)
    style.configure(
        "Treeview",
        background="Black",
        foreground="white",
        fieldbackground="black",
        font=("Courier", 8),
    )

    style.map(
        "Treeview",
        background=[("selected", "lightblue")],
        foreground=[("selected", "black")],
    )

    # B.Heading
    style.configure(
        "B.Heading", font=("Arial", 10, "bold"), background="blue", foreground="white"
    )

    # R.Heading
    style.configure(
        "R.Heading", font=("Arial", 10, "bold"), background="red", foreground="white"
    )
    # G.Heading
    style.configure(
        "G.Heading", font=("Arial", 10, "bold"), background="green", foreground="white"
    )

    # (TRadiobutton)
    style.configure(
        "C.TRadiobutton", background="DarkCyan", foreground="black", font=("Courier", 8)
    )

    # (TCheckbutton)
    # style.configure("T.TCheckbutton", font=("Helvetica", 10), foreground="gray")
    style.configure("T.TCheckbutton", foreground="gray")
    style.map(
        "T.TCheckbutton",
        background=[("selected", "green"), ("!selected", "red")],
        foreground=[("selected", "white"), ("!selected", "white")],
    )
    style.configure(
        "TScrollbar",
        background="gray",
        troughcolor="black",
        arrowcolor="blue",
        gripcount=5,
        width=5,
    )

    return style


def mask_numero(numero):
    if abs(numero) >= 1_000_000_000_000:
        return f"{numero / 1_000_000_000_000:.1f}T"
    elif abs(numero) >= 1_000_000_000:
        return f"{numero / 1_000_000_000:.1f}B"
    elif abs(numero) >= 1_000_000:
        return f"{numero / 1_000_000:.1f}M"
    elif abs(numero) >= 1_000:
        return f"{numero / 1_000:.1f}K"
    else:
        return str(numero)


def spaces(s):
    blancos = " " * s
    return blancos


# Crear una lista de fechas mensuales (al inicio de cada mes)
def meses_list(mask="B", orden="asc", mes="anterior"):
    try:
        f_desde = datetime.now()

        # calcula ultimo dia del mes anterior
        if mes == "anterior":
            dia = f_desde.day
            f_desde = f_desde - timedelta(days=dia)
            f_hasta = f_desde + timedelta(days=360)

        # calcula 1er dia del mes actual
        elif mes != "anterior":
            dia = f_desde.day - 1
            f_hasta = f_desde - timedelta(days=dia)
            f_desde = f_hasta - timedelta(days=360)

        temp = pd.date_range(start=f_desde, end=f_hasta, freq="MS")
        meses = temp.sort_values(ascending=True if orden == "asc" else False)
        l_meses = [Date.strftime(mask) for Date in meses]

        return l_meses
    except Exception as error:
        print("[meses_list()]: {}".format(error))


# Elimina archivos
def delete_file(ruta=None, patron=None, display=True):
    """Elimina varios archivos que coincidan con un patrón en un directorio."""

    s_archivo = None
    ruta_directorio = Path(ruta)

    # Elimina patron del directorio
    if patron is not None:
        for s_archivo in ruta_directorio.glob(patron):
            try:
                s_archivo.unlink()
            except Exception as e:
                if display:
                    print(f"delete_file(): {e}")

    else:
        try:
            s_archivo = Path(ruta)
            s_archivo.unlink()
        except Exception as e:
            if display:
                print(f"delete_file(): {e}")


# establece cache -- para yfinance
def define_FileCache(name=None):
    ipath = os.getcwd()
    if name is not None:
        cache = ipath + f"\\tmp\\{name}"
    elif name is None:
        temp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cache = ipath + "\\tmp\\cache_{temp}"
    return cache


if __name__ == "__main__":
    print("rutinas-----")
    print(is_magnitud(1000))
