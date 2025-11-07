from Modulos_python import (
    os,
    pd,
    Path,
    tk,
    ttk,
    datetime,
    json,
    copy,
    itemgetter,
    threading,
    datetime,
)
from Modulos_Mysql import RepositorioOportunidadesBuySell, DiariaCNV
from Class_customer import WidgetVehiculo, DataHub
from Modulos_Utilitarios import delete_file, buscar_ticker, define_FileCache
from Modulos_Utilitarios import is_numeric


class ArsFondosInversion(tk.Frame):
    def __init__(self, parent=None, master=None, colores=None):
        super().__init__(parent)
        self.root = master
        self.colors = colores
        self.bgcolor = self.colors["bgcolor"]
        self.cgcolor = self.colors["cgcolor"]

        self.path = os.getcwd()
        self.path += "\\tmp\\"

        self.CNVDiaria = None
        self.archivo = None
        self.account_fiat = "ARS-0001"
        self.aliasExcel = {
            "BBVA": "BBVA_Comprobante_",
            "SANT": "movimientos-de-superfondos-",
            "CNV": "_Planilla_Diaria_A..xlsx",
        }
        # Accesos MySql ----------------------------------------------------------------------------------------------
        self.RepositorioOportunidades = RepositorioOportunidadesBuySell()
        self.ClassCNV = DiariaCNV()

        self.sesion = self.ClassCNV.select_sesion(
            datetime.now(), accion="select", vehiculo="BBVA.ARS"
        )
        self.account_bbva = self.sesion["idcuenta"]
        self.orden = json.loads(self.sesion["orcartera"])
        self.vehiculo = "BBVA.ARS"

        self.sesion = self.ClassCNV.select_sesion(
            datetime.now(), accion="select", vehiculo="SANT.ARS"
        )
        self.account_sant = self.sesion["idcuenta"]
        self.currency = {}
        self.counter = 1

        self.account_fci = [self.account_bbva, self.account_sant]
        self.get_tasa_cambio_USDT(fiat="ARS")

        # carga y actualiza panel treeview ------------------------------------------------------------------------
        self.ars = WidgetVehiculo(
            master=self.root, account="BBVA0001", vehiculo=self.vehiculo
        )

        self.ars.carga_inversion_en_positions()
        self.update_panel_fci()

        self.ars.inicio_widget_treeview(self.ars.positions)
        self.ars.run_graficos()

        self.run_loads()
        self.widgets_FCI()

    # Construye extractos de FCI
    def widgets_FCI(self):
        try:

            # update widget ARS
            self.ars.update_panelVehiculo(orden=self.ars.orden)

            self.root.after(5000, lambda: self.widgets_FCI())
        except (EncodingWarning, Exception) as e:
            print("widgets_extractos(): {}".format(e))

    def update_panel_fci(self):
        def change_a_ARS():
            nav, unpyl, dgyp, unprofit, costo, fecha = 0.0, 0.0, 0.0, 0.0, 0.0, None
            for keys in self.ars.positions:
                keys["mrkprice"] = keys["mrkprice"] * keys["factor_cambio"]
                keys["mktvalue"] = keys["mrkprice"] * keys["position"]
                keys["costobase"] = keys["costobase"] * keys["factor_cambio"]
                keys["unrealizedpnl"] = keys["unrealizedpnl"] * keys["factor_cambio"]
                keys["dgyp"] = keys["dgyp"] * keys["factor_cambio"]
                fecha = keys["exDividendDate"].strftime("%d-%b-%Y")

                nav += keys["mktvalue"]
                unpyl += keys["unrealizedpnl"]
                costo += keys["costobase"]
                dgyp += keys["dgyp"]
                unprofit += keys["unrealizedpnl"] if keys["unrealizedpnl"] > 0 else 0

                symbol = keys["ticket"]
                conid = keys["conid"]
                Stimestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                d_precio = {
                    symbol: {
                        "last": keys["mrkprice"],
                        "open": keys["open"],
                        "ask": keys["mrkprice"],
                        "bid": keys["mrkprice"],
                        "high": keys["mrkprice"],
                        "low": keys["mrkprice"],
                        "timestamp": Stimestamp,
                    }
                }

                # agrega precio update a info() -- revisar como agrego esto
                # self.update_precio_DataHubInfo(
                #    symbol=symbol, conid=conid, precio=d_precio
                # )


            per = costo / unprofit if unprofit > 0 else 0
            self.ars.set_header_panel(
                Dgyp=dgyp,
                Nav=nav,
                Unpyl=unpyl,
                Unprofit=unprofit,
                Per=per,
                Sesion=fecha,
            )

        # convierte a pesos y muestra positions
        change_a_ARS()
        self.ars.header_panel()

    # manipula campos numeric para convertir a float
    @staticmethod
    def string_float(s=None, tipo=".,"):
        fl = 0.0
        if tipo == ".,":
            if not is_numeric(s):
                st = s.replace(".", "")
                fl = float(st.replace(",", "."))

        elif tipo == "$.,":
            if not is_numeric(s):
                st = s.replace("$", "")
                st = st.replace(".", "")
                fl = float(st.replace(",", "."))

        return fl

    # encuentra archivos FCI y planilla diaria de CNV - Argentina
    @staticmethod
    def obtener_archivo_mas_reciente(p_path=None, prefijo=None, sufijo=None):
        ruta = Path(p_path)
        archivos = []
        if prefijo is not None:
            archivos = [
                f for f in ruta.iterdir() if f.is_file() and f.name.startswith(prefijo)
            ]

        if sufijo is not None:
            archivos = [
                f for f in ruta.iterdir() if f.is_file() and f.name.endswith(sufijo)
            ]

        if not archivos:
            return None

        # Selecciona el archivo con la fecha de modificación más reciente
        archivo_reciente = max(archivos, key=lambda f: f.stat().st_mtime)
        return archivo_reciente

    # carga desde Excel rendimiento CNV
    def load_diaria_CNV(self):
        try:
            columns = {
                "A": "fondo",
                "B": "Moneda",
                "C": "Region",
                "D": "Horizonte",
                "E": "Fecha",
                "F": "V_actual",
                "G": "V_anterior",
                "H": "variation",
                "I": "Reexp_Pesos",
                "J": "var_30d",
                "K": "var_60d",
                "L": "var_90d",
                "M": "cuota_p_actual",
                "N": "cuota_p_anterior",
                "O": "Patrimonio_actual",
                "P": "Patrimonio_anterior",
                "Q": "Market_Share",
                "R": "Soc_Depositaria",
                "S": "Codigo_CNV",
                "T": "Calificación",
                "U": "Código_CAFCI",
                "V": "Código_SocGte",
                "W": "Código_SocDep",
                "X": "Sociedad_Gerente",
                "Y": "Cód_Clasificación",
                "Z": "Código_Moneda",
                "AA": "Cód_Región",
                "AB": "Cód_Horizonte",
                "AC": "Indice_MM",
                "AD": "Comision_Ingreso",
                "AE": "Hon_Adm.SG",
                "AF": "Hon_AdmSD",
                "AG": "Gastos_Gestion",
                "AH": "Comision_Rescate",
                "AI": "Com_Transf",
                "AJ": "Hon_Éxito",
                "AK": "Moneda_Fondo",
                "AL": "Plazo_Liq",
                "AM": "Decreto_596",
                "AN": "F_CAFCI_padre",
                "AO": "F CNV_padre",
                "AP": "Tipo_escisión",
                "AQ": "Repatriación",
                "AR": "Mín_Inversión",
                "AS": "RegLey_27.743",
                "AT": "Tipo_dinero",
                "AU": "Calificado",
            }

            diaria_CNV = self.obtener_archivo_mas_reciente(
                p_path=self.path, sufijo=self.aliasExcel.get("CNV")
            )
            if diaria_CNV is not None:
                # convierte Excel CNV en Dataframe standard / selection entidades de inversión
                try:
                    names_list = list(columns.values())
                    self.CNVDiaria = []
                    df = pd.read_excel(
                        diaria_CNV,
                        skiprows=11,
                        header=None,  # Indicamos que no hay encabezado en el archivo
                        names=names_list,
                    )  # Usamos tus nombres de columna
                    df.fillna(0, inplace=True)
                    # df.set_index("fondo", inplace=True)

                    cond1 = df[columns["R"]] == "BBVA Argentina S.A."
                    cond2 = df[columns["R"]] == "Banco Santander Argentina S.A."
                    cond3 = df[columns["G"]] > 0
                    cond4 = df[columns["E"]] != 0
                    df_fci = df[(cond1 | cond2) & cond3 & cond4]
                except (ValueError, FileNotFoundError, KeyError, Exception) as e:
                    df_fci = pd.DataFrame()

                if not df_fci.empty:
                    for keys in df_fci.itertuples():
                        try:
                            # valida existencia del fondo en cartera
                            activo, found = self.RepositorioOportunidades.select_otros_activos(idSymbol=keys.Código_CAFCI)
                            if not found :
                               self.CNVDiaria.append({"idcrypto": keys.Código_CAFCI,
                                                      "descripcion": keys.fondo,
                                                      "base_asset": "ARS",
                                                      "quote_asset": "USD"
                                                      })
                               continue

                            values = {}
                            symbol = keys.Código_CAFCI
                            fecha = datetime.strptime(keys.Fecha, "%d/%m/%y")
                       
                            values.update({"fecha": fecha.date()})
                            values.update({"fondo": keys.fondo})
                            values.update({"moneda": keys.Moneda})
                            values.update({"region": keys.Region})
                            values.update({"horizonte": keys.Horizonte})
                            values.update({"valorActual": keys.V_actual})
                            values.update({"valorAnterior": keys.V_anterior})
                            values.update({"variacion": keys.variation})
                            values.update({"valorPesos": keys.Reexp_Pesos})
                            values.update({"variacion30dias": keys.var_30d})
                            values.update({"variacion60dias": keys.var_60d})
                            values.update({"variacion90dias": keys.var_90d})
                            values.update({"patrimonioActual": keys.Patrimonio_actual})
                            values.update({"patrimonioAnterior": keys.Patrimonio_anterior})
                            values.update({"marketShare": keys.Market_Share})
                            values.update({"sociedadDepositaria": keys.Soc_Depositaria})
                            values.update({"codigoCNV": keys.Codigo_CNV})
                            values.update({"codSociedadDep": keys.Código_SocDep})
                            values.update({"monedaFondo": keys.Código_Moneda})

                            self.ClassCNV.insert(values=values, symbol=symbol)
                        except ValueError:
                            continue

                    # Almacena archivo CNV que no estan en otros_activos
                    # file_CNV = define_FileCache("CNV_FCI_missing_activos.json")


                delete_file(ruta=diaria_CNV, display=False)
        except (EncodingWarning, Exception) as e:
            print("load_diaria_CNV(): {}".format(e))

    # carga en booktrading operaciones de FCI
    def load_positions_FCI(self):
        def fci_BBVA():
            try:
                columns = {
                    "A": "Especie",
                    "B": "Descripción de Especie",
                    "C": "Fecha",
                    "D": "Tipo",
                    "E": "Cantidad (VN)",
                    "F": "precio",
                    "H": "Importe Ajuste",
                    "I": "Monto Neto",
                    "J": "Moneda",
                    "k": "Estado",
                    "L": "Operación",
                }

                df_bbva = pd.read_excel(self.archivo, engine="xlrd", skiprows=2)
                bbva = df_bbva.to_dict(orient="records")
                bbva_ord = sorted(bbva, key=lambda x: (x["Especie"], x["Fecha"]))

                trader = []
                for i, rows in enumerate(bbva_ord):

                    if rows["Moneda"] == "$":
                        values = {}
                        codigo = "O" if rows["Tipo"] == "Suscripción" else "C"
                        activo, found = (
                            self.RepositorioOportunidades.select_otros_activos(
                                symbol=rows["Descripción de Especie"]
                            )
                        )
                        if found:
                            cantidad = self.string_float(s=rows["Cantidad (VN)"]) * (
                                1 if codigo == "O" else -1
                            )
                            fecha = datetime.strptime(rows["Fecha"], "%d/%m/%Y")
                            tasa_cambio = self.get_tasa_cambio_USDT(
                                fiat="ARS", date=fecha.date()
                            )

                            values.update({"categoria": self.vehiculo})
                            values.update({"divisa": "ARS"})
                            values.update({"cuenta": self.account_bbva})
                            values.update({"fechahora": fecha})
                            values.update({"idtrans": rows["Operación"]})
                            values.update({"cantidad": cantidad})
                            values.update(
                                {"preciotrans": self.string_float(s=rows["Precio"])}
                            )
                            values.update(
                                {"preciocierre": self.string_float(s=rows["Precio"])}
                            )
                            values.update(
                                {"producto": self.string_float(s=rows["Monto Neto"])}
                            )
                            values.update({"tarifacomision": 0.0})
                            values.update({"gprealizadas": 0.0})
                            values.update({"mtmgp": 0.0})
                            values.update({"codigo": codigo})
                            values.update({"factor_cambio": tasa_cambio})
                            values.update({"symbol": activo[0]["symbol"]})
                            trader.append(values)

                # valida e inserta booktrading
                asc_trader = sorted(
                    trader,
                    key=itemgetter(
                        "cuenta",
                        "symbol",
                        "fechahora",
                    ),
                )
                for i, values in enumerate(asc_trader):

                    symbol = values["symbol"]
                    last_trader, ix = self.RepositorioOportunidades.select_booktrading(
                        accion="last",
                        account=self.account_bbva,
                        idivisa="ARS",
                        symbol=symbol,
                    )
                    last_date = (
                        last_trader[0]["fechahora"]
                        if last_trader
                        else datetime(2000, 1, 1)
                    )

                    if last_date < values["fechahora"]:
                        values.pop("symbol")
                        self.RepositorioOportunidades.insert_booktrading(
                            values, symbol=symbol
                        )

                # elimina archivo procesado
                delete_file(ruta=self.archivo, display=True)
            except (EncodingWarning, Exception) as error:
                print("[fci_BBVA()]: {}".format(error))

        def fci_santander():
            try:
                columns = {
                    "A": "Cuenta Títulos",
                    "B": "Fondo",
                    "C": "Fecha de solicitud",
                    "D": "Fecha_liquidación",
                    "E": "N°_comprobante",
                    "F": "Movimiento",
                    "H": "Cantidad_cuotapartes",
                    "I": "Valor_cuotaparte",
                    "J": "Importe",
                }

                df = pd.read_excel(
                    self.archivo, skiprows=2, header=0, names=list(columns.values())
                )
                cond1 = df[columns["F"]] == "Inversión"
                cond2 = df[columns["F"]] == "Rescate"
                df_santa = df[cond1 | cond2]

                santa = df_santa.to_dict(orient="records")
                santa_ord = sorted(santa, key=lambda x: x["Fecha_liquidación"])

                trader = []
                for i, rows in enumerate(santa_ord):

                    values = {}
                    ValorCuotaParte = self.string_float(
                        s=rows["Valor_cuotaparte"], tipo="$.,"
                    )
                    CuotaParte = self.string_float(
                        s=rows["Cantidad_cuotapartes"], tipo=".,"
                    )
                    if ValorCuotaParte > 0:
                        codigo = "O" if rows["Movimiento"] == "Inversión" else "C"
                        activo, found = (
                            self.RepositorioOportunidades.select_otros_activos(
                                symbol=rows["Fondo"]
                            )
                        )

                        if not found:
                            activo, found = (
                                self.RepositorioOportunidades.insert_otros_activos(
                                    symbol=rows["Fondo"]
                                )
                            )
                        if found:
                            cantidad = CuotaParte * (1 if codigo == "O" else -1)
                            fecha = datetime.strptime(
                                rows["Fecha_liquidación"], "%d/%m/%Y"
                            )
                            tasa_cambio = self.get_tasa_cambio_USDT(
                                fiat="ARS", date=fecha.date()
                            )
                            producto = ValorCuotaParte * CuotaParte
                            values.update({"categoria": self.vehiculo})
                            values.update({"divisa": "ARS"})
                            values.update({"cuenta": self.account_sant})
                            values.update({"fechahora": fecha})
                            values.update({"idtrans": str(int(rows["N°_comprobante"]))})
                            values.update({"cantidad": cantidad})
                            values.update({"preciotrans": ValorCuotaParte})
                            values.update({"preciocierre": ValorCuotaParte})
                            values.update({"producto": producto})
                            values.update({"tarifacomision": 0.0})
                            values.update({"gprealizadas": 0.0})
                            values.update({"mtmgp": 0.0})
                            values.update({"codigo": codigo})
                            values.update({"factor_cambio": tasa_cambio})
                            values.update({"symbol": activo[0]["symbol"]})
                            trader.append(values)

                # valida e inserta booktrading
                asc_trader = sorted(
                    trader,
                    key=itemgetter(
                        "cuenta",
                        "symbol",
                        "fechahora",
                    ),
                )
                for i, values in enumerate(asc_trader):
                    symbol = values["symbol"]
                    last_trader, ix = self.RepositorioOportunidades.select_booktrading(
                        accion="last",
                        account=self.account_sant,
                        idivisa="ARS",
                        symbol=symbol,
                    )
                    last_date = (
                        last_trader[0]["fechahora"]
                        if last_trader
                        else datetime(2000, 1, 1)
                    )

                    if last_date < values["fechahora"]:
                        values.pop("symbol")
                        self.RepositorioOportunidades.insert_booktrading(
                            values, symbol=symbol
                        )

                # elimina archivo procesado
                delete_file(ruta=self.archivo, display=False)
            except (EncodingWarning, Exception) as error:
                print("[fci_santander()]: {}".format(error))

        # define position en moneda base USD
        def struct_positions_fci(ticket, positions, last):
            try:
                p = {}

                # obtiene costo promedio
                activo, found = self.RepositorioOportunidades.select_otros_activos(
                    symbol=ticket
                )

                # obtiene precio de mercado
                conid = activo[0]["idcrypto"]
                cnv, ix, found = self.ClassCNV.select(symbol=conid)

                # obtiene valor anterior de la posición
                found, position = buscar_ticker(positions, ticket)

                p["exDividendDate"] = cnv[ix.index("fecha")]
                p["factor_cambio"] = last[0]["factor_cambio"]
                p["dividendYield"] = 0
                p["estrategia"] = "P05"
                p["dividendo"] = 0
                p["costobase"] = (
                    (activo[0]["avgcost"] * last[0]["stock"] / last[0]["factor_cambio"])
                    if last[0]["factor_cambio"] > 0
                    else 0
                )
                p["objetivo"] = 0
                p["position"] = last[0]["stock"]
                p["mrkprice"] = (
                    (cnv[ix.index("valorActual")] / 1000 / last[0]["factor_cambio"])
                    if last[0]["factor_cambio"] > 0
                    else 0
                )

                p["mktvalue"] = p["mrkprice"] * last[0]["stock"]
                p["retorno"] = (
                    (p["mktvalue"] - p["costobase"]) / p["costobase"]
                    if p["costobase"] > 0
                    else 0
                )
                p["empresa"] = activo[0]["descripcion"]
                p["nivelIA"] = "02"
                p["country"] = "Argentina"
                p["region"] = "AS"
                p["divisa"] = activo[0]["base_asset"]

                p["sector"] = "Fondo Inversión"
                p["ticket"] = ticket
                p["deuda"] = 0
                p["conid"] = str(activo[0]["idcrypto"])
                p["peso"] = 0
                p["open"] = (
                    (cnv[ix.index("valorAnterior")] / 1000 / last[0]["factor_cambio"])
                    if last[0]["factor_cambio"] > 0
                    else 0
                )

                p["unrealizedpnl"] = p["mktvalue"] - p["costobase"]
                p["dgyp"] = p["mrkprice"] - p["open"]

                return p
            except (EncodingWarning, Exception) as error:
                print("struct_positions_fci(): {}".format(error))

        def update_FCI_en_positions():
            try:
                in_positions = self.RepositorioOportunidades.select_inversion(
                    tipoin=self.vehiculo, ticket="all"
                )
                iupdate = False

                for account in self.account_fci:
                    positions = []
                    activo, found = self.RepositorioOportunidades.select_otros_activos(
                        symbol="all", account=account
                    )

                    for keys in activo:
                        symbol = keys["symbol"]
                        last_trader, ix = (
                            self.RepositorioOportunidades.select_booktrading(
                                accion="last",
                                account=account,
                                idivisa="ARS",
                                symbol=symbol,
                            )
                        )

                        # valida que position sea mayor que el umbral
                        if abs(last_trader[0]["stock"]) > 0.01:
                            datos = struct_positions_fci(
                                symbol, in_positions, last_trader
                            )
                            positions.append(datos)

                    # actualiza tabla de inversiones con última información de la API
                    if positions:
                        self.RepositorioOportunidades.update_inversion(
                            account=account, vehiculo=self.vehiculo, positions=positions
                        )
                        iupdate = True

                # re-escribe self.position en moneda base para que se muestre en widget
                out_positions = self.RepositorioOportunidades.select_inversion(
                    tipoin=self.vehiculo, ticket="all"
                )
                self.ars.positions = copy.deepcopy(out_positions)

            except (EncodingWarning, Exception) as error:
                print("update_FCI_en_positions(): {}".format(error))

        try:
            # carga información BBVA
            self.archivo = self.obtener_archivo_mas_reciente(
                p_path=self.path, prefijo=self.aliasExcel.get("BBVA")
            )
            if self.archivo is not None:
                fci_BBVA()

            # carga información santander
            self.archivo = self.obtener_archivo_mas_reciente(
                p_path=self.path, prefijo=self.aliasExcel.get("SANT")
            )
            if self.archivo is not None:
                fci_santander()

            update_FCI_en_positions()
        except (EncodingWarning, Exception) as e:
            print("load_positions_FCI(): {}".format(e))

    # carga de booktrading los movimientos USDT
    def get_tasa_cambio_USDT(self, fiat="ARS", date=None):
        try:
            if date is None:
                book, ix = self.RepositorioOportunidades.select_booktrading(
                    accion="select*",
                    account=self.account_fiat,
                    idivisa="USD",
                    symbol="USDT",
                )

                # extrae máximo 360 registros de con fechahora descendente
                self.currency = {"heard": ix, "trader": book[0:360]}
                return 0.0

            elif date is not None:

                tasa, anterior, ix = 0.0, 0.0, self.currency["heard"]
                # recorre lista y entrega tasa, o promedio si no ubica para la fecha dada
                for i, values in enumerate(self.currency["trader"]):

                    if values[ix.index("fechahora")].date() > date:
                        if anterior > 0:
                            tasa = (values[ix.index("preciotrans")] + anterior) / 2
                        else:
                            tasa = values[ix.index("preciotrans")]

                        break

                    elif values[ix.index("fechahora")].date() == date:

                        tasa = values[ix.index("preciotrans")]
                        break

                    else:
                        anterior = values[ix.index("preciotrans")]

                return tasa if tasa > 0 else anterior
        except (EncodingWarning, Exception) as e:
            print("get_tasa_cambio_USDT(): {}".format(e))

    # valida si llego nueva interfaz para cargar
    def chequea_new_loadFile(self):
        existe = False

        # carga ultima tasa USDT
        self.get_tasa_cambio_USDT(fiat="ARS")

        bbva = self.obtener_archivo_mas_reciente(
            p_path=self.path, prefijo=self.aliasExcel.get("BBVA")
        )
        if bbva is not None:
            existe = True

        # santa = self.obtener_archivo_mas_reciente(p_path=self.path, prefijo='últimos movimientos Superfondos')
        santa = self.obtener_archivo_mas_reciente(
            p_path=self.path, prefijo=self.aliasExcel.get("SANT")
        )

        if santa is not None:
            existe = True

        diaria = self.obtener_archivo_mas_reciente(
            p_path=self.path, sufijo=self.aliasExcel.get("CNV")
        )
        if diaria is not None:
            existe = True

        return existe

    # vericica cada 90 segundos si hay nueva interfaz para cargar
    def run_loads(self):
        def run_schedule(task=None):
            while True:
                # valida si hay nueva interfaz
                if self.chequea_new_loadFile():
                    self.load_diaria_CNV()
                    self.load_positions_FCI()

                    self.update_panel_fci()

                self.counter += 1
                DataHub.update_self_procesos(
                    proces="thread", tarea=task, itera=self.counter
                )
                threading.Event().wait(90)

        try:
            task_name = f"schedule_FondoInversion(ARS)"
            DataHub.procesos.append({"thread": {task_name: self.counter}})
            DataHub.manager_events.register_thread(
                name=task_name,
                target=run_schedule,
                task=task_name,
            )
        except (EncodingWarning, Exception) as e:
            print(f"run_loads(ARS): {e}")


def app():
    root = tk.Tk()
    bgcolor = DataHub.bgcolor
    cgcolor = DataHub.cgcolor
    cchart = DataHub.cchart
    colors = DataHub.colors
    dw = DataHub.colors.get("dw")
    dh = DataHub.colors.get("dh")
    df = DataHub.colors.get("df")
    max_dw = root.winfo_screenwidth()
    max_dh = root.winfo_screenheight()

    # actualiza dimensiones de la pantalla
    DataHub.colors["max_dw"] = root.winfo_screenwidth()
    DataHub.colors["max_dh"] = root.winfo_screenheight()

    dimension = "%dx%d+0+0" % (colors["dw"], colors["dh"])
    root.geometry(dimension)
    root.config(bg=colors["bgcolor"])
    style = ttk.Style(root)
    style.configure(
        "TFrame", font=("Courier", 8), foreground="white", background="black"
    )
    dpn = ttk.Frame(root, style="TFrame", width=colors["df"], height=700)
    dpn.pack()

    frame_strat = ArsFondosInversion(master=dpn, colores=colors)
    frame_strat.pack()
    frame_strat.mainloop()


if __name__ == "__main__":
    app()
