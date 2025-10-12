from Class_DataFrame import get_yfinance
from Modulos_Mysql import IPerformance, RepositorioOportunidadesBuySell
from Modulos_Utilitarios import vehiculo_parm, convierte_ticket_crypto
from Modulos_python import datetime, pd, timedelta, os, csv


# construye e inserta diaria para los assets del vehiculo
def diaria_book_performance(account=None, vehiculo=None, proces=None):
    try:
        RepositorioOportunidades = RepositorioOportunidadesBuySell()
        update, ahora, book, ix = False, datetime.now(), [], []

        # print(f'diaria_book_performance() {vehiculo} {proces['diaria_book_performance'].date()} < {ahora.date()}')
        if proces["diaria_book_performance"].date() < ahora.date():

            # itera para recorrer booktrading  e insertar performance dia(s) anteriores
            book, ix = RepositorioOportunidades.select_booktrading(
                accion="diaria_app", account=account, idivisa="USD"
            )
            path = detalle_book(
                account=account, vehiculo=vehiculo, book=book, ix=ix, option="app"
            )

            # Leer CSV e inserta después de ultima diaria
            diaria, iy = read_csv_insert_diaria(path=path, insert=True)
            update = True

        return update
    except Exception as error:
        print("[diaria_book_performance({})]: {}".format(vehiculo, error))


# organiza como la solicitud de datos para armar de performance del vehículo
def performa_asset(account=None, vehiculo=None, tipo=None, asset=None):
    """
    @param account: identifica cuentaid
    @param vehiculo: identifica tipo cálculo para el activo (Crypto, Stock.)
    @param tipo: identifica tipo de acción portafolio o activo individual
    @param asset: list() de symbol's
    @return: Dataframe historica del performa para el tipo de activo."""

    datos = pd.DataFrame()
    Performa = IPerformance()
    try:
        symbol, rtn_index, cum_index, index_ref = vehiculo_parm(vehiculo=vehiculo)
        columnas = [
            "Date",
            "p_referencia",
            "p_vehiculo",
            "nr_gyp",
            "value",
            "costo_base",
        ]
        sql = Performa.select_performa_inversion(account=account, vehiculo=vehiculo)
        d_datos = {
            columnas: columna for columnas, columna in zip(columnas, zip(*sql[0]))
        }

        # obtiene DataFrame para portafolios
        # if tipo in ('Stock', 'Crypto', 'BBVA.ARS'):
        if tipo in ("Stock", "Crypto"):
            if sql:
                datos = pd.DataFrame(d_datos, index=d_datos["Date"])
                datos[index_ref] = (1 + datos["p_referencia"]).cumprod()
                datos["++ index"] = (1 + datos["p_vehiculo"]).cumprod()

        # obtiene DataFrame para un activo que esté en la tabla diaria
        if tipo == "activo":
            wperf = pd.DataFrame(d_datos, index=d_datos["Date"])
            cols = ["nr_gyp", "value", "p_vehiculo", "costo_base"]
            wperf = wperf.drop(cols, axis=1)

            (diaria, iy) = Performa.select_diaria_performance(
                account=account, symbol=asset
            )

            pdatos = pd.DataFrame(diaria, columns=iy)
            cols = ["id", "account", "cantidad", "gyp_dia", "comisiones", "symbol"]
            pdatos = pdatos.drop(cols, axis=1)

            datos = pd.merge(pdatos, wperf, on="Date", how="inner")
            datos.set_index("Date", inplace=True)
            datos[index_ref] = (1 + datos["p_referencia"]).cumprod() - 1
            datos["retorno"] = datos["AdjClose"].pct_change()
            datos["++ index"] = (1 + datos["retorno"]).cumprod()

        return datos

    except Exception as error:
        print("[performa_asset({})]: {}".format(vehiculo, error))


# carga de datos diarios desde CSV e inserta en la tabla diaria_performance
def read_csv_insert_diaria(path=None, insert=None):

    Performa = IPerformance()
    with open(path, mode="r", newline="") as file:
        reader = csv.reader(file)
        ix = next(reader)

        bkey, diaria, ebook = None, [], enumerate(reader)
        eof_book, read = next(ebook, (None, None))

        while eof_book is not None:
            if bkey != read[ix.index("symbol")]:
                bkey = read[ix.index("symbol")]
                last, iy = Performa.select_diaria_performance(
                    accion="last", account=read[ix.index("account")], symbol=bkey
                )

                # asegura tenga last actualización diaria
                if last:
                    last_date = last[iy.index("Date")]
                    s_date = last_date.strftime("%Y-%m-%d")
                else:
                    # para el caso que no exista diaria, manipula s_date
                    date = datetime.strptime(read[ix.index("Date")], "%Y-%m-%d").date()
                    last_date = date - timedelta(days=1)
                    s_date = last_date.strftime("%Y-%m-%d")

            if read[ix.index("Date")] > s_date:
                values = {}
                for i, campo in enumerate(ix):
                    if campo != "symbol":
                        values.update({campo: read[ix.index(campo)]})

                diaria.append(read)
                if insert:
                    Performa.insert_diaria_performance(values=values, symbol=bkey)

            eof_book, read = next(ebook, (None, None))
    return diaria, ix


# explota booktrading para la construcción de la tabla diaria_performance
def detalle_book(account=None, vehiculo=None, book=None, ix=None, option="inicio"):

    def write_csv(gyp, fee):
        nonlocal ebook, idatos, row, eof_book, read, a_read

        skey = a_read[ix.index("simbolo")]
        stock = float(a_read[ix.index("stock")])
        basic = float(a_read[ix.index("basico")])

        value = row["Close"] * stock
        div = row["Dividends"] * stock if "Dividends" in row else 0
        costo = basic * stock
        nr_gyp = 0.0

        # escribe porque hay stock o reportar gyp
        if (costo >= 0) or (gyp != 0):

            if costo > 0:
                nr_gyp = value - costo
                perf = nr_gyp / costo

            if (costo <= 0) and (gyp != 0):
                costo = 0.0
                stock = float(abs(a_read[ix.index("cantidad")]))
                x_cost = basic * stock
                perf = (gyp / x_cost) if x_cost > 0 else 0.0

            writer.writerow(
                [
                    account,
                    eof_datos.date(),
                    skey,
                    row["Close"],
                    value,
                    stock,
                    costo,
                    perf,
                    gyp,
                    nr_gyp,
                    fee,
                    div,
                ]
            )

    def acumula_igual_date():
        nonlocal ebook, idatos, row, eof_book, read, a_read

        gyp, basic, stock, fee = 0.0, 0.0, 0.0, 0.0
        while (
            (eof_datos is not None)
            and (eof_book is not None)
            and (read[ix.index("simbolo")] == bkey)
            and (eof_datos.date() == read[ix.index("fechahora")].date())
        ):
            gyp += float(read[ix.index("gprealizadas")])
            fee += float(read[ix.index("tarifacomision")])
            a_read = read
            eof_book, read = next(ebook, (None, None))
        #
        write_csv(gyp, fee)
        return a_read

    def escribir_fecha():
        nonlocal ebook, idatos, eof_datos, row, eof_book, read, a_read

        gyp, fee = 0.0, 0.0
        #
        if a_read:
            write_csv(gyp, fee)

    def completa_diaria():
        nonlocal ebook, idatos, eof_datos, row, eof_book, read, a_read

        gyp, fee = 0.0, 0.0
        while eof_datos is not None:
            write_csv(gyp, fee)
            eof_datos, row = next(idatos, (None, None))

    try:
        eof_datos, a_read = [], []
        eof_book, read = [], []

        prefijo = "csv_datos_" if option == "inicio" else "csv_app_"
        path = os.getcwd()
        path += "\\tmp\\" + prefijo + vehiculo + ".csv"
        with open(path, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "account",
                    "Date",
                    "symbol",
                    "AdjClose",
                    "value",
                    "cantidad",
                    "costo_base",
                    "performa",
                    "gyp_dia",
                    "nr_gyp",
                    "comisiones",
                    "dividends",
                ]
            )

            ebook = enumerate(book)
            eof_book, read = next(ebook, (None, None))

            # procesa hasta el dia anterior
            hasta = datetime.now() - timedelta(days=1)
            f_hasta = hasta.date()

            while eof_book is not None:

                # por cada symbol itera sobre su historia desde f_hasta, siempre que datos no este vacio
                activo, a_read, datos = None, [], pd.DataFrame()
                bkey = read[ix.index("simbolo")]
                f_desde = read[ix.index("fechahora")].date()

                # cuando Stock hace Ticker para bajar los dividends
                if read[ix.index("categoria")] == "Stock":
                    activo, datos = get_yfinance(
                        ticket=bkey, vehiculo="Dividends", desde=f_desde, hasta=f_hasta
                    )
                else:
                    activo, datos = get_yfinance(
                        ticket=bkey, vehiculo="download", desde=f_desde, hasta=f_hasta
                    )

                if datos.empty:
                    eof_book, read = next(ebook, (None, None))
                else:

                    # en caso hay datos yfinance
                    idatos = datos.iterrows()
                    eof_datos, row = next(idatos, (None, None))
                    while (
                        (eof_datos is not None)
                        and (eof_book is not None)
                        and (read[ix.index("simbolo")] == bkey)
                    ):

                        if eof_datos.date() == read[ix.index("fechahora")].date():
                            a_read = acumula_igual_date()
                            eof_datos, row = next(idatos, (None, None))
                        else:
                            if eof_datos.date() < read[ix.index("fechahora")].date():
                                escribir_fecha()
                                eof_datos, row = next(idatos, (None, None))
                            else:
                                a_read = read
                                eof_book, read = next(ebook, (None, None))

                    # por fin simbolo completar diaria para el bkey anterior, si stock > 0
                    if (a_read[ix.index("simbolo")] == bkey) and (
                        a_read[ix.index("stock")] > 0
                    ):
                        completa_diaria()

        return path
    except Exception as error:
        print("detalle_book({})]: {}".format(vehiculo, error))


# inserta en performa_inversiones desempeño del índice y los activos de la cartera
def actualiza_performa_inversion(account=None, vehiculo=None):

    def inserta_index_performa(dataframe=None, index=None, performa=None, insert=True):
        for date, rows in dataframe.iterrows():
            values = dict()
            values.update({"idcuenta": account})
            values.update({"vehiculo": vehiculo})
            values.update({"fechaclose": date})
            values.update({"referencia": index})
            values.update({"p_referencia": rows[performa]})
            values.update({"p_vehiculo": rows["retorno"]})
            values.update({"gyp_dia": rows["gyp_dia"]})
            values.update({"nr_gyp": rows["nr_gyp"]})
            values.update({"value": rows["value"]})
            values.update({"costo_base": rows["costo_base"]})
            values.update({"dividends": rows["dividends"]})

            if insert:
                Performa.insert_performa_inversion(values)

    try:
        Performa = IPerformance()
        (last_update, ix) = Performa.select_performa_inversion(
            account=account, vehiculo=vehiculo, accion="last"
        )
        if last_update:

            # obtiene a partir last fecha de performa, registros diarias pendientes
            f_desde = last_update[ix.index("fechaclose")]
            f_inicio = f_desde - timedelta(days=1)
            diaria, iy = Performa.select_diaria_performance(
                account=account, date=f_inicio, accion="desde"
            )

            datos = pd.DataFrame(diaria, columns=iy)

            columns_to_clean = [
                "AdjClose",
                "value",
                "gyp_dia",
                "nr_gyp",
                "costo_base",
                "dividends",
            ]
            datos[columns_to_clean] = (
                datos[columns_to_clean].apply(pd.to_numeric, errors="coerce").fillna(0)
            )
            datos["Date"] = pd.to_datetime(datos["Date"])

            # Calcular valor del portafolio por día
            datos["value Portafolio"] = (
                datos["value"] + datos["dividends"] + datos["gyp_dia"]
            )

            # agrupa y suma
            columnas = [
                "value",
                "nr_gyp",
                "gyp_dia",
                "costo_base",
                "dividends",
                "value Portafolio",
            ]
            pdatos = datos.groupby("Date")[columnas].sum()

            # Normalizar para crear índice
            pdatos["performa"] = pdatos["value Portafolio"] / pdatos["costo_base"]

            # inserta tabla performance
            if not pdatos.empty:

                # calcula performance de procesamiento de la diaria
                pdatos["retorno"] = pdatos["performa"].pct_change()
                pdatos["CumPort"] = (1 + pdatos["retorno"]).cumprod() - 1

                # busca desempeño del índice asociado al vehículo
                (df_indice, index_ref, rtn_index) = crea_dataframe_index(
                    vehiculo=vehiculo, desde=f_inicio
                )
                df_previo = pd.merge(df_indice, pdatos, on="Date", how="inner")

                # deja en df_update las filas Date > f_desde
                f_limite = pd.to_datetime(f_desde)
                df_update = df_previo[df_previo.index > f_limite]

                inserta_index_performa(
                    dataframe=df_update,
                    index=index_ref,
                    performa=rtn_index,
                    insert=True,
                )

    except Exception as error:
        print("[actualiza_performa_inversion({})]: {}".format(vehiculo, error))


# Modulo para crear performance del indice asociado al vehiculo
def crea_dataframe_index(vehiculo=None, desde=None):
    try:
        hoy = (datetime.now() - timedelta(days=1)).date()
        symbol, rtn_index, cum_index, index_ref = vehiculo_parm(vehiculo=vehiculo)

        indice = pd.DataFrame()
        # symbol = convierte_ticket_crypto(symbol)
        activo, datos = get_yfinance(
            ticket=symbol, vehiculo="donwload", desde=desde, hasta=hoy
        )

        # asegura tomar solo la primera columna si hay varias
        if isinstance(datos["Close"], pd.DataFrame):
            datos["Close"] = datos["Close"].iloc[:, 0]

        # limina zona horaria para aparear con la Df diaria
        datos.reset_index(inplace=True)

        datos["Date"] = pd.to_datetime(datos["Date"])
        datos["Date"] = datos["Date"].dt.date
        datos.set_index("Date", inplace=True)

        # calcula la variación porcentual entre dos precios sucesivos
        indice[rtn_index] = datos["Close"].pct_change()
        indice[cum_index] = (1 + indice[rtn_index]).cumprod() - 1

        return indice, index_ref, rtn_index
    except Exception as error:
        print(f"[crea_dataframe_index({vehiculo})]: {error}")


# modulo para crear dataframe de tabla
def crea_dataframe_diaria(diaria=None, ix=None):
    try:
        datos = pd.DataFrame(diaria, columns=ix)

        columns_to_clean = [
            "AdjClose",
            "value",
            "gyp_dia",
            "nr_gyp",
            "costo_base",
            "dividends",
        ]
        datos[columns_to_clean] = (
            datos[columns_to_clean].apply(pd.to_numeric, errors="coerce").fillna(0)
        )

        # estandariza formato Date y lo define como index
        datos["Date"] = pd.to_datetime(datos["Date"])
        datos["Date"] = datos["Date"].dt.date
        datos.set_index("Date", inplace=True)

        # Calcular valor del portafolio por día
        datos["value Portafolio"] = (
            datos["value"] + datos["dividends"] + datos["gyp_dia"]
        )

        # agrupa y suma
        columnas = [
            "value",
            "nr_gyp",
            "gyp_dia",
            "costo_base",
            "dividends",
            "value Portafolio",
        ]
        pdatos = datos.groupby("Date")[columnas].sum()

        pdatos["performa"] = pdatos["value Portafolio"] / pdatos["costo_base"]

        return pdatos
    except Exception as error:
        print("[Error:: procesar_df_book()]: {}".format(error))
        return pd.Dataframe()


# módulo para crear performance del vehiculo a partir de la diaria
def crea_dataframe_performa_Index(
    account=None, vehiculo=None, display=True, diaria=None, iy=None
):
    try:
        # define index a partir 1er dia de la diaria
        f_desde = diaria[0][iy.index("Date")]
        indice, index_ref, rtn_index = crea_dataframe_index(
            vehiculo=vehiculo, desde=f_desde
        )

        # evalua calculo del retorno
        pdatos = crea_dataframe_diaria(diaria=diaria, ix=iy)

        if not pdatos.empty:
            pdatos["retorno"] = pdatos["performa"].pct_change()
            pdatos["CumPort"] = (1 + pdatos["retorno"]).cumprod() - 1

            c_pdatos = pd.merge(indice, pdatos, on="Date", how="inner")
            c_pdatos.fillna(0, inplace=True)

        if display:
            hoy = datetime.now().date()
            print("=" * 100)
            print(" - Procesado desde: {} hasta {}".format(f_desde, hoy))
            print(" ")
            print(
                " - Indice referencia: {}, Registros {}".format(
                    index_ref, indice.shape[0]
                )
            )
            print(
                " - Inicio insert.performance()::",
                account,
                "Registros Booktrading de",
                vehiculo,
            )
            print(" - Registros diaria=", len(diaria))
            print("=" * 100)

            print(
                "===================================================================================================="
            )
            print("dataframe=pdatos, base=", account)
            print(
                "===================================================================================================="
            )
            print(
                pdatos[
                    [
                        "value",
                        "nr_gyp",
                        "gyp_dia",
                        "costo_base",
                        "dividends",
                        "value Portafolio",
                    ]
                ]
            )

        return c_pdatos

    except (Exception, ValueError, EncodingWarning) as e:
        print(f"crea_dataframe_performa_Index({vehiculo}): error: {e}")


# orquesta la construcción del performance a partir de la diaria
def proceso_update_performance(account=None, vehiculo=None):
    try:
        # obtienen última actualización y retrocede 60 días en la diaria
        Performa = IPerformance()
        (last_update, ix) = Performa.select_performa_inversion(
            account=account, vehiculo=vehiculo, accion="last"
        )
        if last_update:

            hasta = last_update[ix.index("fechaclose")]
            desde = hasta - timedelta(days=60)

            diaria, iy = Performa.select_diaria_performance(
                account=account, date=desde, accion="desde"
            )

            if diaria:
                df_performa = crea_dataframe_performa_Index(
                    account=account,
                    vehiculo=vehiculo,
                    display=False,
                    diaria=diaria,
                    iy=iy,
                )

                symbol, rtn_index, cum_index, index_ref = vehiculo_parm(
                    vehiculo=vehiculo
                )

                # recorre Dataframe para insertar las filas mayores a la fecha desde
                for date, rows in df_performa.iterrows():
                    values = {}

                    if date > hasta:
                        values.update({"idcuenta": account})
                        values.update({"vehiculo": vehiculo})
                        values.update({"idcuenta": account})
                        values.update({"vehiculo": vehiculo})
                        values.update({"fechaclose": date})
                        values.update({"referencia": index_ref})
                        values.update({"p_referencia": float(rows[rtn_index])})
                        values.update({"p_vehiculo": float(rows["retorno"])})
                        values.update({"gyp_dia": float(rows["gyp_dia"])})
                        values.update({"nr_gyp": float(rows["nr_gyp"])})
                        values.update({"value": float(rows["value"])})
                        values.update({"costo_base": float(rows["costo_base"])})
                        values.update({"dividends": float(rows["dividends"])})

                        # Inserta fila en la tabla de performance
                        Performa.insert_performa_inversion(values)
    except Exception as e:
        print(f"proceso_update_performance({vehiculo}): error: {e}")
