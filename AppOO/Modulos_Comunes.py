from Class_DataFrame import get_yfinance
from Modulos_Mysql import BDsystem, IPerformance, RepositorioOportunidadesBuySell
from Modulos_Utilitarios import (
    vehiculo_parm,
    convierte_ticket_crypto,
    convierte_ticket_stock,
    define_FileCache,
    read_json_tmp,
)
from Modulos_python import datetime, date, pd, timedelta, os, csv, traceback, logging, time

_logger = logging.getLogger("ClassMyOrders")


# construye e inserta diaria para los assets del vehiculo
def diaria_book_performance(account=None, vehiculo=None, proces=None):
    try:
        RepositorioOportunidades = RepositorioOportunidadesBuySell()
        update, ahora, book, ix = False, datetime.now(), [], []

        # print(
        #    f"diaria_book_performance() {vehiculo} {proces['diaria_book_performance'].date()} < {ahora.date()}"
        # )
        dbp = proces["diaria_book_performance"]
        if dbp is None:
            dbp_date = ahora.date() - timedelta(days=1)
        else:
            dbp_date = dbp if isinstance(dbp, date) else dbp.date()
        if dbp_date < ahora.date():

            # itera para recorrer booktrading  e insertar performance dia(s) anteriores
            book, ix = RepositorioOportunidades.select_booktrading(accion="diaria_app", account=account, idivisa="USD")
            path = detalle_book(account=account, vehiculo=vehiculo, book=book, ix=ix, option="app")

            # Leer CSV e inserta después de ultima diaria
            if path is None:
                return update
            diaria, iy = read_csv_insert_diaria(path=path, insert=True)
            update = True

        return update
    except Exception as error:
        _logger.error(f"diaria_book_performance({vehiculo}): {error}")


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

        # FCI (BBVA.ARS): usa performa_inversion consolidada — recalcula retorno desde value/costo_base sumados
        if tipo == "BBVA.ARS":
            sql, iy = Performa.select_performa_inversion(account=None, vehiculo=vehiculo)
            if sql and iy:
                df = pd.DataFrame(sql, columns=iy)
                df["fechaclose"] = pd.to_datetime(df["fechaclose"])
                df.set_index("fechaclose", inplace=True)
                df.sort_index(inplace=True)
                for col in ["p_referencia", "value", "costo_base", "gyp_dia", "dividends"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                # Replica crea_dataframe_diaria: ratio portfolio consolidado → retorno diario → acumulado
                df["performa"] = (df["value"] + df["dividends"] + df["gyp_dia"]) / df["costo_base"]
                df["CumPort"] = (1 + df["performa"].pct_change()).cumprod() - 1
                df[cum_index] = (1 + df["p_referencia"]).cumprod() - 1
                datos = df[["CumPort"] + [c for c in ("value", "costo_base") if c in df.columns] + [cum_index]].copy()
                datos[index_ref] = datos[cum_index]
                datos["++ Portafolio"] = datos["CumPort"]

        # Stock / Crypto: recalcula desde diaria_performance
        elif tipo in ("Stock", "Crypto"):
            if account is None:
                try:
                    ses = BDsystem.get_sesion_by_vehiculo(vehiculo=vehiculo)
                    if ses and ses.get("idcuenta"):
                        account = ses["idcuenta"]
                except Exception:
                    pass

            diaria_all, ix = [], []
            sql, iy = Performa.select_diaria_performance(account=account)
            if sql:
                diaria_all.extend(sql)
                ix = iy

            if diaria_all and ix:
                pdatos = crea_dataframe_diaria(diaria=diaria_all, ix=ix)
                if pdatos is not None and not pdatos.empty:
                    raiz = pdatos["performa"].iloc[0]
                    pdatos["CumPort"] = (pdatos["performa"] / raiz) - 1

                    first_date = pdatos.index[0]
                    result = crea_dataframe_index(vehiculo=vehiculo, desde=first_date)
                    if result is not None:
                        indice, _, _ = result
                        pdatos.index = pd.to_datetime(pdatos.index)
                        indice.index = pd.to_datetime(indice.index)
                        cols_pdatos = ["CumPort"] + [c for c in ("value", "costo_base") if c in pdatos.columns]
                        datos = (
                            pdatos[cols_pdatos]
                            .join(indice[[cum_index]], how="inner")
                            .dropna(subset=["CumPort", cum_index])
                        )
                        datos[index_ref] = datos[cum_index]
                        datos["++ Portafolio"] = datos["CumPort"]

        # obtiene DataFrame para un activo individual desde diaria_performance
        if tipo == "activo":
            sql, iy = Performa.select_diaria_performance(account=account, symbol=asset)
            if sql:
                pdatos = pd.DataFrame(sql, columns=iy)
                drop_cols = ["id", "account", "cantidad", "gyp_dia", "comisiones", "symbol"]
                pdatos.drop(columns=[c for c in drop_cols if c in pdatos.columns], inplace=True)
                pdatos["Date"] = pd.to_datetime(pdatos["Date"])
                pdatos.set_index("Date", inplace=True)

                first_date = str(pdatos.index.min().date())
                result = crea_dataframe_index(vehiculo=vehiculo, desde=first_date)
                if result is not None:
                    indice, _, _ = result
                    indice.index = pd.to_datetime(indice.index)
                    datos = pdatos.join(indice[[rtn_index, cum_index]], how="inner")
                    datos[index_ref] = datos[cum_index]
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
        try:
            nonlocal ebook, idatos, row, eof_book, read, a_read, writer

            skey = a_read[ix.index("simbolo")]
            stock = float(a_read[ix.index("stock")])

            # controla factor de cambio en divisa
            factor = float(a_read[ix.index("factor_cambio")])

            basic = float(a_read[ix.index("basico")] / factor)
            close = float(row["Close"] / factor)

            value = close * stock
            div = row["Dividends"] / factor * stock if "Dividends" in row else 0

            GyP = gyp / factor
            fee = fee / factor

            value = value
            costo = basic * stock
            nr_gyp, perf = 0.0, 0.0

            # escribe porque hay stock o reportar gyp
            if (costo >= 0) or (GyP != 0):

                if costo > 0:
                    nr_gyp = value - costo
                    perf = nr_gyp / costo

                if (costo <= 0) and (GyP != 0):
                    costo = 0.0
                    stock = float(abs(a_read[ix.index("cantidad")]))
                    x_cost = basic * stock
                    perf = (GyP / x_cost) if x_cost > 0 else 0.0

                writer.writerow(
                    [
                        account,
                        eof_datos.date(),
                        skey,
                        close,
                        value,
                        stock,
                        costo,
                        perf,
                        GyP,
                        nr_gyp,
                        fee,
                        div,
                        factor,
                    ]
                )
        except Exception as error:
            print(f"write_csv({vehiculo})]: {error}")

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
        path = define_FileCache(name=f"{prefijo}{vehiculo}.csv")

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
                    "factor_cambio",
                ]
            )

            ebook = enumerate(book)
            eof_book, read = next(ebook, (None, None))

            # procesa hasta el dia anterior
            hasta = datetime.now() - timedelta(days=1)
            f_hasta = hasta.date()

            # por cada symbol itera sobre su historia desde f_hasta, siempre que datos no este vacio
            while eof_book is not None:

                # por cada symbol itera sobre su historia desde f_hasta, siempre que datos no este vacio
                activo, a_read, datos = None, [], pd.DataFrame()
                bkey = read[ix.index("simbolo")]
                f_desde = read[ix.index("fechahora")].date()
                sym_hasta = f_hasta

                # delisted sin fecha_deliste → saltar completo
                # delisted con fecha_deliste → procesar hasta esa fecha (aporta hasta cierre)
                if "delisted" in ix and read[ix.index("delisted")] == 1:
                    fd = read[ix.index("fecha_deliste")] if "fecha_deliste" in ix else None
                    if fd is not None:
                        sym_hasta = fd
                        # compra posterior al deliste → zero-row a partir de f_desde
                        if f_desde > sym_hasta:
                            last_read = read
                            while eof_book is not None and read[ix.index("simbolo")] == bkey:
                                last_read = read
                                eof_book, read = next(ebook, (None, None))
                            try:
                                stock_d = float(last_read[ix.index("stock")])
                                basico_d = float(last_read[ix.index("basico")]) / float(
                                    last_read[ix.index("factor_cambio")]
                                )
                                if stock_d > 0:
                                    costo_d = basico_d * stock_d
                                    writer.writerow(
                                        [
                                            account,
                                            f_desde,
                                            bkey,
                                            0.0,
                                            0.0,
                                            stock_d,
                                            costo_d,
                                            -1.0,
                                            0.0,
                                            -costo_d,
                                            0.0,
                                            0.0,
                                            1.0,
                                        ]
                                    )
                            except Exception:
                                pass
                            continue
                    else:
                        while eof_book is not None and read[ix.index("simbolo")] == bkey:
                            eof_book, read = next(ebook, (None, None))
                        continue

                divisa = read[ix.index("divisa")] if "divisa" in ix else "USD"
                yf_ticket = convierte_ticket_stock(bkey, divisa)

                # cuarentena: símbolo con datos corruptos recurrentes — saltear hasta que expire (24h)
                _quarantine = read_json_tmp("cache_health").get("quarantine", {})
                _q_ts = _quarantine.get(bkey, 0)
                if _q_ts and (time.time() - _q_ts) < 86400:
                    while eof_book is not None and read[ix.index("simbolo")] == bkey:
                        eof_book, read = next(ebook, (None, None))
                    continue

                # cuando Stock hace Ticker para bajar los dividends
                if read[ix.index("categoria")] == "Stock":
                    activo, datos = get_yfinance(ticket=yf_ticket, vehiculo="Dividends", desde=f_desde, hasta=sym_hasta)

                elif read[ix.index("categoria")] == "BBVA.ARS":
                    activo, datos = get_yfinance(ticket=yf_ticket, vehiculo="BBVA.ARS", desde=f_desde, hasta=sym_hasta)

                else:
                    activo, datos = get_yfinance(ticket=yf_ticket, vehiculo="download", desde=f_desde, hasta=sym_hasta)

                if datos is None or datos.empty:
                    last_read = read
                    while eof_book is not None and read[ix.index("simbolo")] == bkey:
                        last_read = read
                        eof_book, read = next(ebook, (None, None))
                    # delisted con fecha_deliste pero sin datos yfinance → registrar pérdida total
                    if sym_hasta != f_hasta:
                        try:
                            stock_d = float(last_read[ix.index("stock")])
                            basico_d = float(last_read[ix.index("basico")]) / float(
                                last_read[ix.index("factor_cambio")]
                            )
                            if stock_d > 0:
                                costo_d = basico_d * stock_d
                                writer.writerow(
                                    [
                                        account,
                                        sym_hasta,
                                        bkey,
                                        0.0,
                                        0.0,
                                        stock_d,
                                        costo_d,
                                        -1.0,
                                        0.0,
                                        -costo_d,
                                        0.0,
                                        0.0,
                                        1.0,
                                    ]
                                )
                        except Exception:
                            pass
                else:

                    # en caso hay datos yfinance
                    idatos = datos.iterrows()
                    eof_datos, row = next(idatos, (None, None))
                    while (eof_datos is not None) and (eof_book is not None) and (read[ix.index("simbolo")] == bkey):

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
                    if (a_read[ix.index("simbolo")] == bkey) and (a_read[ix.index("stock")] > 0):
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
        last_update, ix = Performa.select_performa_inversion(account=account, vehiculo=vehiculo, accion="last")
        if last_update:

            # obtiene a partir last fecha de performa, registros diarias pendientes
            f_desde = last_update[ix.index("fechaclose")]
            f_inicio = f_desde - timedelta(days=1)
            diaria, iy = Performa.select_diaria_performance(account=account, date=f_inicio, accion="desde")

            datos = pd.DataFrame(diaria, columns=iy)

            columns_to_clean = [
                "AdjClose",
                "value",
                "gyp_dia",
                "nr_gyp",
                "costo_base",
                "dividends",
            ]
            datos[columns_to_clean] = datos[columns_to_clean].apply(pd.to_numeric, errors="coerce").fillna(0)
            datos["Date"] = pd.to_datetime(datos["Date"])

            # Calcular valor del portafolio por día
            datos["value Portafolio"] = datos["value"] + datos["dividends"] + datos["gyp_dia"]

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
            pdatos.index = pdatos.index.date

            # Normalizar para crear índice
            pdatos["performa"] = pdatos["value Portafolio"] / pdatos["costo_base"]

            # inserta tabla performance
            if not pdatos.empty:

                # calcula performance de procesamiento de la diaria
                pdatos["retorno"] = pdatos["performa"].pct_change()
                pdatos["CumPort"] = (1 + pdatos["retorno"]).cumprod() - 1

                # busca desempeño del índice asociado al vehículo
                df_indice, index_ref, rtn_index = crea_dataframe_index(vehiculo=vehiculo, desde=f_inicio)
                df_previo = pd.merge(df_indice, pdatos, left_index=True, right_index=True, how="inner")

                # deja en df_update las filas Date > f_desde
                f_limite = f_desde.date() if hasattr(f_desde, "date") else f_desde
                df_update = df_previo[df_previo.index > f_limite]

                # saltar fechas con cobertura de símbolos < 80% vs día anterior (diaria incompleta)
                n_simbolos = datos.groupby("Date")["symbol"].nunique()
                n_simbolos.index = pd.to_datetime(n_simbolos.index).date
                n_ayer = n_simbolos.shift(1)
                fechas_incompletas = set(n_simbolos[(n_simbolos < n_ayer * 0.8)].index)
                if fechas_incompletas:
                    omitidas = df_update.index.isin(fechas_incompletas)
                    print(
                        f"[actualiza_performa_inversion] fechas omitidas por cobertura < 80%: "
                        f"{sorted(fechas_incompletas)}"
                    )
                    df_update = df_update[~omitidas]

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
        activo, datos = get_yfinance(ticket=symbol, vehiculo="donwload", desde=desde, hasta=hoy)

        if datos is None or datos.empty or "Close" not in datos.columns:
            return None

        # asegura tomar solo la primera columna si hay varias
        if isinstance(datos["Close"], pd.DataFrame):
            datos["Close"] = datos["Close"].iloc[:, 0]

        # elimina zona horaria, convierte a date object para consistencia con crea_dataframe_diaria
        datos.reset_index(inplace=True)

        datos["Date"] = pd.to_datetime(datos["Date"])
        if datos["Date"].dt.tz is not None:
            datos["Date"] = datos["Date"].dt.tz_convert(None)
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
        datos[columns_to_clean] = datos[columns_to_clean].apply(pd.to_numeric, errors="coerce").fillna(0)

        # estandariza formato Date y lo define como index
        datos["Date"] = pd.to_datetime(datos["Date"])
        datos["Date"] = datos["Date"].dt.date
        datos.set_index("Date", inplace=True)

        # Calcular valor del portafolio por día
        datos["value Portafolio"] = datos["value"] + datos["dividends"] + datos["gyp_dia"]

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
def crea_dataframe_performa_Index(account=None, vehiculo=None, display=True, diaria=None, iy=None):
    try:
        # define index a partir 1er dia de la diaria
        f_desde = diaria[0][iy.index("Date")]
        indice, index_ref, rtn_index = crea_dataframe_index(vehiculo=vehiculo, desde=f_desde)

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
            print(" - Indice referencia: {}, Registros {}".format(index_ref, indice.shape[0]))
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
        Performa = IPerformance()
        last_update, ix = Performa.select_performa_inversion(account=account, vehiculo=vehiculo, accion="last")

        if last_update:
            hasta = last_update[ix.index("fechaclose")]
            desde = hasta - timedelta(days=60)
            diaria, iy = Performa.select_diaria_performance(account=account, date=desde, accion="desde")
        else:
            # primera vez: performa_inversion vacía — carga desde el inicio de diaria_performance
            hasta = None
            diaria, iy = Performa.select_diaria_performance(account=account)

        if diaria:
            df_performa = crea_dataframe_performa_Index(
                account=account,
                vehiculo=vehiculo,
                display=False,
                diaria=diaria,
                iy=iy,
            )

            symbol, rtn_index, cum_index, index_ref = vehiculo_parm(vehiculo=vehiculo)

            for date, rows in df_performa.iterrows():
                if hasta is None or date > hasta:
                    values = {
                        "idcuenta": account,
                        "vehiculo": vehiculo,
                        "fechaclose": date,
                        "referencia": index_ref,
                        "p_referencia": float(rows[rtn_index]),
                        "p_vehiculo": float(rows["retorno"]),
                        "gyp_dia": float(rows["gyp_dia"]),
                        "nr_gyp": float(rows["nr_gyp"]),
                        "value": float(rows["value"]),
                        "costo_base": float(rows["costo_base"]),
                        "dividends": float(rows["dividends"]),
                    }
                    Performa.insert_performa_inversion(values)
    except Exception as e:
        print(f"proceso_update_performance({vehiculo}): error: {e}")
