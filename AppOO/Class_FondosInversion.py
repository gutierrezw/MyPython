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
    timedelta,
    traceback,
    logging,
)

_logger = logging.getLogger("FondosInversion")
from Modulos_Mysql import RepositorioOportunidadesBuySell, DiariaCNV, IPerformance
from Class_customer import WidgetVehiculo, TickerInfo, DataHub
from Modulos_Utilitarios import delete_file, buscar_ticker, define_FileCache, is_numeric
from Modulos_Comunes import diaria_book_performance, proceso_update_performance
from download_cnv_selenium import descargar_cnv_hoy

_SUPERFONDO_CAFCI = frozenset({689, 1346, 1325, 1565, 5334})

_CNV_NAMES_LIST = [
    "fondo",
    "Moneda",
    "Region",
    "Horizonte",
    "Fecha",
    "V_actual",
    "V_anterior",
    "variation",
    "Reexp_Pesos",
    "var_30d",
    "var_60d",
    "var_90d",
    "cuota_p_actual",
    "cuota_p_anterior",
    "Patrimonio_actual",
    "Patrimonio_anterior",
    "Market_Share",
    "Soc_Depositaria",
    "Codigo_CNV",
    "Calificación",
    "Código_CAFCI",
    "Código_SocGte",
    "Código_SocDep",
    "Sociedad_Gerente",
    "Cód_Clasificación",
    "Código_Moneda",
    "Cód_Región",
    "Cód_Horizonte",
    "Indice_MM",
    "Comision_Ingreso",
    "Hon_Adm.SG",
    "Hon_AdmSD",
    "Gastos_Gestion",
    "Comision_Rescate",
    "Com_Transf",
    "Hon_Éxito",
    "Moneda_Fondo",
    "Plazo_Liq",
    "Decreto_596",
    "F_CAFCI_padre",
    "F CNV_padre",
    "Tipo_escisión",
    "Repatriación",
    "Mín_Inversión",
    "RegLey_27.743",
    "Tipo_dinero",
    "Calificado",
]


def _parse_cnv_row_fn(keys) -> tuple:
    """Parsea una fila itertuples del Excel CNV → (values_dict, codCAFCI)."""
    fecha = datetime.strptime(str(keys.Fecha), "%d/%m/%y")
    values = {
        "fecha": fecha.date(),
        "fondo": str(keys.fondo),
        "moneda": keys.Moneda,
        "region": keys.Region,
        "horizonte": keys.Horizonte,
        "valorActual": keys.V_actual,
        "valorAnterior": keys.V_anterior,
        "variacion": keys.variation,
        "valorPesos": keys.Reexp_Pesos,
        "variacion30dias": keys.var_30d,
        "variacion60dias": keys.var_60d,
        "variacion90dias": keys.var_90d,
        "patrimonioActual": keys.Patrimonio_actual,
        "patrimonioAnterior": keys.Patrimonio_anterior,
        "marketShare": keys.Market_Share,
        "sociedadDepositaria": keys.Soc_Depositaria,
        "codigoCNV": keys.Codigo_CNV,
        "codSociedadDep": keys.Código_SocDep,
        "monedaFondo": keys.Código_Moneda,
    }
    return values, keys.Código_CAFCI


def sync_cnv_superfondos(df) -> int:
    """Inserta en diaria_cnv las filas de Superfondos por codCAFCI/nombre, sin gate de otros_activos.
    Retorna cantidad de filas insertadas."""
    cnv_db = DiariaCNV()
    insertados = 0
    for keys in df.itertuples():
        try:
            cafci = keys.Código_CAFCI
            if cafci not in _SUPERFONDO_CAFCI or not keys.V_actual or keys.Fecha == 0:
                continue
            values, symbol = _parse_cnv_row_fn(keys)
            cnv_db.insert_CNV(values=values, symbol=symbol)
            insertados += 1
        except Exception:
            continue
    return insertados


def sync_fci_browser(account_bbva: str = None) -> list:
    """Descarga extractos FCI de BBVA y Santander y los procesa en booktrading.
    Función standalone para uso desde agentes (sin UI).
    """
    from Class_BrowserFCI import BrowserFCI  # import diferido — evita ciclo con Modulos_Mysql

    repo = RepositorioOportunidadesBuySell()
    cnv = DiariaCNV()

    ses_bbva = cnv.get_sesion_by_vehiculo("BBVA.ARS")
    acc_bbva = account_bbva or ses_bbva["idcuenta"]

    path = (os.environ.get("APPOO_TMP") or os.path.join(os.getcwd(), "tmp")).rstrip("\\/") + os.sep
    os.makedirs(path, exist_ok=True)

    last, _ = repo.select_booktrading(accion="last", account=acc_bbva, idivisa="ARS")
    desde = last[0]["fechahora"].date() if last else date.today() - timedelta(days=90)

    browser = BrowserFCI()
    procesados = []
    if browser.download_bbva(desde=desde, destino=path, prefijo="BBVA_Comprobante_"):
        procesados.append("BBVA")
    if browser.download_santander(desde=desde, destino=path, prefijo="movimientos-de-superfondos-"):
        procesados.append("SANT")

    return procesados


class ArsFondosInversion(tk.Frame):
    def __init__(self, parent=None, master=None, colores=None):
        super().__init__(parent)
        self.root = master
        self.colors = colores
        self.bgcolor = self.colors["bgcolor"]
        self.cgcolor = self.colors["cgcolor"]

        self.path = os.environ.get("APPOO_TMP") or os.path.join(os.getcwd(), "tmp")
        self.path = self.path.rstrip("\\/") + os.sep
        os.makedirs(self.path, exist_ok=True)

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

        self.sesion = self.ClassCNV.get_sesion_by_vehiculo("BBVA.ARS")
        self.account_bbva = self.sesion["idcuenta"]
        self.orden = json.loads(self.sesion["orcartera"])
        self.vehiculo = "BBVA.ARS"

        self.sesion = self.ClassCNV.get_sesion_by_vehiculo("SANT.ARS")
        self.account_sant = self.sesion["idcuenta"]
        self.accounTitulo = self.sesion["xstrategy"]
        self.currency = {}
        self.counter = 1

        self.account_fci = [self.account_bbva, self.account_sant]
        self.get_tasa_cambio_USDT(fiat="ARS")

        # carga y actualiza panel treeview ------------------------------------------------------------------------
        self.ars = WidgetVehiculo(master=self.root, account="BBVA0001", vehiculo=self.vehiculo)
        self.cus = TickerInfo(account="BBVA0001", vehiculo=self.vehiculo)

        self.ars.carga_inversion_en_positions()
        self.update_FCI_en_positions()
        self.update_panel_fci()

        self.ars.inicio_widget_treeview(self.ars.positions)
        self.ars.run_graficos()

        self.run_loads()
        self.widgets_FCI()

    # Construye extractos de FCI
    def widgets_FCI(self):
        try:
            self.ars.update_panelVehiculo(orden=self.ars.orden)
        except Exception as e:
            _logger.error(f"widgets_FCI: {e}")
        finally:
            self.root.after(5000, lambda: self.widgets_FCI())

    def update_panel_fci(self):
        def change_a_ARS():
            nav, unpyl, dgyp, unprofit, costo, fecha = 0.0, 0.0, 0.0, 0.0, 0.0, None
            dgyp_usd = 0.0

            # obtiene tasa de cambio USDT-ARS
            hoy = datetime.now()
            tasa_cambio = self.get_tasa_cambio_USDT(fiat="ARS", date=hoy.date())
            _logger.warning(f"change_a_ARS: tasa_cambio={tasa_cambio}, positions={len(self.ars.positions)}")

            self.cus.positions = self.ars.positions
            for keys in self.ars.positions:

                # rechaza position < 0 o menor a 5 Usd
                if keys["costobase"] <= 5 or keys["position"] <= 0:
                    continue

                fc = keys.get("factor_cambio", 0)
                _logger.warning(f"change_a_ARS: {keys.get('ticket')} fc={fc} mrkprice_pre={keys.get('mrkprice'):.6f}")
                dgyp_usd += keys["dgyp"] * keys["position"]
                keys["mrkprice"] = keys["mrkprice"] * fc
                keys["mktvalue"] = keys["mrkprice"] * keys["position"]
                keys["costobase"] = keys["costobase"] * fc
                keys["unrealizedpnl"] = keys["unrealizedpnl"] * fc
                keys["open"] = keys["open"] * fc
                keys["dgyp"] = keys["dgyp"] * fc
                ex = keys.get("exDividendDate")
                fecha = ex.strftime("%d-%b-%Y") if hasattr(ex, "strftime") else str(ex)

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

                # actualiza DataHub.info()
                activo, datos, ind_update = self.cus.ts_yfinance_symbol(symbol=symbol, vehiculo=self.vehiculo)
                self.cus.update_precio_DataHubInfo(symbol=symbol, conid=conid, precio=d_precio)

            per = costo / unprofit if unprofit > 0 else 0
            _logger.warning(f"change_a_ARS: completado — nav={nav:.2f} ARS, unpyl={unpyl:.2f} ARS")
            DataHub.manager_GyP["Ars"]["dGyP"] = dgyp_usd
            self.ars.set_header_panel(
                Dgyp=dgyp,
                Nav=nav,
                Unpyl=unpyl,
                Unprofit=unprofit,
                Per=per,
                Sesion=fecha,
            )

        # convierte a pesos y muestra positions
        try:
            change_a_ARS()
        except Exception as _e:
            _logger.error(f"update_panel_fci/change_a_ARS: {_e}", exc_info=True)

        # ejecuta servicios de Trading
        self.cus.oportunidades_buy()
        self.cus.oportunidades_sell()
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
            archivos = [f for f in ruta.iterdir() if f.is_file() and f.name.startswith(prefijo)]

        if sufijo is not None:
            archivos = [f for f in ruta.iterdir() if f.is_file() and f.name.endswith(sufijo)]

        if not archivos:
            return None

        # Selecciona el archivo con la fecha de modificación más reciente
        archivo_reciente = max(archivos, key=lambda f: f.stat().st_mtime)
        return archivo_reciente

    # carga desde Excel rendimiento CNV
    def load_EXCEL_TBdiaria_CNV_(self):
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

            diaria_CNV = self.obtener_archivo_mas_reciente(p_path=self.path, sufijo=self.aliasExcel.get("CNV"))
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
                            # valida existencia del fondo — primero por CAFCI, fallback por nombre
                            activo, found = self.RepositorioOportunidades.select_otros_activos(
                                idSymbol=keys.Código_CAFCI
                            )
                            if not found:
                                activo, found = self.RepositorioOportunidades.select_otros_activos(
                                    descripcion=keys.fondo
                                )
                                if found and activo and activo[0].get("idcrypto") != keys.Código_CAFCI:
                                    cuenta_upd = activo[0].get("cuenta")
                                    self.RepositorioOportunidades.update_otros_activos(
                                        account=cuenta_upd,
                                        symbol=keys.fondo,
                                        values={"idcrypto": keys.Código_CAFCI},
                                    )
                                    activo[0]["idcrypto"] = keys.Código_CAFCI
                            if not found:
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

                            self.ClassCNV.insert_CNV(values=values, symbol=symbol)
                        except ValueError:
                            continue

                    # Almacena archivo CNV que no estan en otros_activos
                    # file_CNV = define_FileCache("CNV_FCI_missing_activos.json")

                sync_cnv_superfondos(df)
                delete_file(ruta=diaria_CNV, display=False)
        except Exception as e:
            print("load_EXCEL_TBdiaria_CNV_(): {}".format(e))

    def _parse_cnv_row(self, keys):
        """Extrae el dict de valores para insert_CNV a partir de una fila del Excel CNV."""
        fecha = datetime.strptime(keys.Fecha, "%d/%m/%y")
        values = {
            "fecha": fecha.date(),
            "fondo": keys.fondo,
            "moneda": keys.Moneda,
            "region": keys.Region,
            "horizonte": keys.Horizonte,
            "valorActual": keys.V_actual,
            "valorAnterior": keys.V_anterior,
            "variacion": keys.variation,
            "valorPesos": keys.Reexp_Pesos,
            "variacion30dias": keys.var_30d,
            "variacion60dias": keys.var_60d,
            "variacion90dias": keys.var_90d,
            "patrimonioActual": keys.Patrimonio_actual,
            "patrimonioAnterior": keys.Patrimonio_anterior,
            "marketShare": keys.Market_Share,
            "sociedadDepositaria": keys.Soc_Depositaria,
            "codigoCNV": keys.Codigo_CNV,
            "codSociedadDep": keys.Código_SocDep,
            "monedaFondo": keys.Código_Moneda,
        }
        return values, keys.Código_CAFCI

    def backfill_historico_cnv(self, codCAFCI, meses=6):
        """Descarga histórico de 6 meses de diaria_cnv para un nuevo fondo.
        Se ejecuta en thread separado — no bloquea la UI."""

        def _run():
            try:
                from download_cnv_selenium import (
                    obtener_documentos,
                )  # import diferido — evita ciclo con módulo de descarga

                names_list = [
                    "fondo",
                    "Moneda",
                    "Region",
                    "Horizonte",
                    "Fecha",
                    "V_actual",
                    "V_anterior",
                    "variation",
                    "Reexp_Pesos",
                    "var_30d",
                    "var_60d",
                    "var_90d",
                    "cuota_p_actual",
                    "cuota_p_anterior",
                    "Patrimonio_actual",
                    "Patrimonio_anterior",
                    "Market_Share",
                    "Soc_Depositaria",
                    "Codigo_CNV",
                    "Calificación",
                    "Código_CAFCI",
                    "Código_SocGte",
                    "Código_SocDep",
                    "Sociedad_Gerente",
                    "Cód_Clasificación",
                    "Código_Moneda",
                    "Cód_Región",
                    "Cód_Horizonte",
                    "Indice_MM",
                    "Comision_Ingreso",
                    "Hon_Adm.SG",
                    "Hon_AdmSD",
                    "Gastos_Gestion",
                    "Comision_Rescate",
                    "Com_Transf",
                    "Hon_Éxito",
                    "Moneda_Fondo",
                    "Plazo_Liq",
                    "Decreto_596",
                    "F_CAFCI_padre",
                    "F CNV_padre",
                    "Tipo_escisión",
                    "Repatriación",
                    "Mín_Inversión",
                    "RegLey_27.743",
                    "Tipo_dinero",
                    "Calificado",
                ]
                desde = (datetime.now() - timedelta(days=meses * 30)).date()
                docs = obtener_documentos()
                docs = [d for d in docs if d["fecha_dt"].date() >= desde]
                docs.sort(key=lambda x: x["fecha_dt"])

                insertados = 0
                for doc in docs:
                    fecha_doc = doc["fecha_dt"].date()
                    existente = self.ClassCNV.last_insert_CNV(symbol=codCAFCI, date=str(fecha_doc))
                    if existente != "0001-01-01":
                        continue

                    fecha_str = doc["fecha_dt"].strftime("%d-%m-%Y")
                    from download_cnv_selenium import descargar_cnv_hoy  # import diferido

                    resultado = descargar_cnv_hoy(fecha_str)
                    if not resultado["success"] or not resultado.get("archivo"):
                        continue

                    try:
                        df = pd.read_excel(resultado["archivo"], skiprows=11, header=None, names=names_list)
                        df.fillna(0, inplace=True)
                        fila = df[df["Código_CAFCI"] == codCAFCI]
                        if not fila.empty:
                            keys = next(fila.itertuples())
                            values, symbol = self._parse_cnv_row(keys)
                            self.ClassCNV.insert_CNV(values=values, symbol=symbol)
                            insertados += 1
                    except Exception as e:
                        _logger.error(f"backfill_historico_cnv parse {fecha_str}: {e}")
                    finally:
                        delete_file(ruta=Path(resultado["archivo"]), display=False)

                _logger.warning(f"backfill_historico_cnv({codCAFCI}): {insertados} dias insertados")
            except Exception as e:
                _logger.error(f"backfill_historico_cnv({codCAFCI}): {e}")

        threading.Thread(target=_run, daemon=True).start()

    # define position en moneda base USD
    def struct_positions_fci(self, account=None, ticket=None, positions=None, last=None):
        try:
            p = {}

            # obtiene costo promedio
            activo, found = self.RepositorioOportunidades.select_otros_activos(account=account, symbol=ticket)

            # obtiene precio de mercado — fallback a preciocierre de booktrading si no está en CNV
            conid = activo[0]["idcrypto"]
            cnv, ix, cnv_found = self.ClassCNV.select_CNV(symbol=conid)
            fc_booktrading = last[0]["factor_cambio"]
            factor = fc_booktrading if fc_booktrading > 0 else (self.get_tasa_cambio_USDT(fiat="ARS", date=datetime.now().date()) or 1)

            if cnv_found:
                fecha_cnv = cnv[ix.index("fecha")]
                valor_actual = cnv[ix.index("valorActual")] / 1000 / factor
                valor_anterior = cnv[ix.index("valorAnterior")] / 1000 / factor
            else:
                fecha_cnv = (
                    last[0]["fechahora"].date() if hasattr(last[0]["fechahora"], "date") else last[0]["fechahora"]
                )
                precio_cierre = last[0].get("preciocierre") or 0
                valor_actual = precio_cierre / factor if precio_cierre else 0
                valor_anterior = valor_actual

            # obtiene valor anterior de la posición
            found, position = buscar_ticker(positions, ticket)

            p["exDividendDate"] = fecha_cnv
            p["factor_cambio"] = factor
            p["dividendYield"] = 0
            p["estrategia"] = "P05"
            p["dividendo"] = 0
            p["costobase"] = (activo[0]["avgcost"] * last[0]["stock"] / factor) if factor > 0 else 0
            p["objetivo"] = 0
            p["position"] = last[0]["stock"]
            p["mrkprice"] = valor_actual

            p["mktvalue"] = p["mrkprice"] * last[0]["stock"]
            p["retorno"] = (p["mktvalue"] - p["costobase"]) / p["costobase"] if p["costobase"] > 0 else 0
            p["empresa"] = activo[0]["descripcion"]
            p["nivelIA"] = "02"
            p["country"] = "Argentina"
            p["sectype"] = "FCI"
            p["region"] = "AS"
            p["divisa"] = (activo[0].get("base_asset") or "ARS")[:3]

            p["sector"] = "Fondo Inversión"
            p["ticket"] = ticket
            p["deuda"] = 0
            p["conid"] = str(activo[0]["idcrypto"])
            p["peso"] = 0
            p["open"] = valor_anterior

            p["unrealizedpnl"] = p["mktvalue"] - p["costobase"]
            p["dgyp"] = p["mrkprice"] - p["open"]

            return p
        except Exception as e:
            _logger.error("struct_positions_fci(): {}".format(e))

    # update self.ars.positions
    def update_FCI_en_positions(self):
        try:
            in_positions = self.RepositorioOportunidades.select_inversion(tipoin=self.vehiculo, ticket="all")
            iupdate = False

            for account in self.account_fci:
                positions = []
                activo, found = self.RepositorioOportunidades.select_otros_activos(account=account, symbol="all")

                for keys in activo:
                    symbol = keys["symbol"]
                    last_trader, ix = self.RepositorioOportunidades.select_booktrading(
                        accion="last",
                        account=account,
                        idivisa="ARS",
                        symbol=symbol,
                    )

                    # valida que position sea mayor que el umbral
                    if last_trader and abs(last_trader[0]["stock"]) > 0.01:
                        datos = self.struct_positions_fci(
                            account=account, ticket=symbol, positions=in_positions, last=last_trader
                        )
                        if datos is not None:
                            positions.append(datos)

                # actualiza tabla de inversiones con última información de la API
                if positions:
                    self.RepositorioOportunidades.update_inversion(
                        account=account, vehiculo=self.vehiculo, positions=positions
                    )
                    iupdate = True

            # re-escribe self.position en moneda base para que se muestre en widget
            out_positions = self.RepositorioOportunidades.select_inversion(tipoin=self.vehiculo, ticket="all")
            self.ars.positions = [
                p for p in copy.deepcopy(out_positions) if p.get("costobase", 0) > 5 and p.get("position", 0) > 0
            ]
        except Exception as e:
            print("update_FCI_en_positions(): {}".format(e))
            traceback.print_exc()

    def sync_extracto_browser(self) -> list:
        from Class_BrowserFCI import BrowserFCI  # import diferido — evita ciclo con Modulos_Mysql

        browser = BrowserFCI()

        last, _ = self.RepositorioOportunidades.select_booktrading(
            accion="last", account=self.account_bbva, idivisa="ARS"
        )
        desde = last[0]["fechahora"].date() if last else date.today() - timedelta(days=90)

        procesados = []
        if browser.download_bbva(desde=desde, destino=self.path, prefijo=self.aliasExcel["BBVA"]):
            self.load_positions_FCI()
            procesados.append("BBVA")

        if browser.download_santander(desde=desde, destino=self.path, prefijo=self.aliasExcel["SANT"]):
            self.load_positions_FCI()
            procesados.append("SANT")

        return procesados

    # carga en booktrading operaciones de FCI
    def load_positions_FCI(self):
        def insert_values_in_booktrading(trader):
            _PRIORIDAD = {"Rescate": 1, "Transferencia": 2, "Inversión": 3}
            try:
                asc_trader = sorted(
                    trader,
                    key=lambda x: (
                        x["cuenta"],
                        x["symbol"],
                        x["fechahora"],
                        _PRIORIDAD.get(x.get("tipomov", "Inversión"), 3),
                    ),
                )

                ebook = enumerate(asc_trader)
                eof_book, values = next(ebook, (None, None))
                keySymbol = None
                hoy = datetime.now().date()

                while eof_book is not None:

                    symbol = values["symbol"]

                    # Fix 1: ignorar ops del día de descarga — precio aún no ajustado por el banco
                    if values["fechahora"].date() >= hoy:
                        eof_book, values = next(ebook, (None, None))
                        continue

                    if keySymbol != symbol:
                        last_trader, ix = self.RepositorioOportunidades.select_booktrading(
                            accion="last",
                            account=values["cuenta"],
                            idivisa="ARS",
                            symbol=symbol,
                        )
                        last_date = last_trader[0]["fechahora"] if last_trader else datetime(2000, 1, 1)
                        keySymbol = symbol

                    idtrans = str(values.get("idtrans", ""))
                    # Fix 2: si idtrans ya existe actualizar precio ajustado, no duplicar
                    existing, _ = self.RepositorioOportunidades.select_booktrading(
                        accion="valida",
                        account=values["cuenta"],
                        idivisa="ARS",
                        symbol=symbol,
                        idtrans=idtrans,
                    )
                    if existing:
                        self.RepositorioOportunidades.update_preciotrans_fci(
                            account=values["cuenta"],
                            idivisa="ARS",
                            symbol=symbol,
                            idtrans=idtrans,
                            preciotrans=values["preciotrans"],
                            cantidad=values["cantidad"],
                            producto=values.get("producto", 0),
                        )
                    elif last_date < values["fechahora"]:
                        values.pop("symbol")
                        values.pop("tipomov", None)
                        self.RepositorioOportunidades.insert_booktrading(values, symbol=symbol)

                    eof_book, values = next(ebook, (None, None))

                # elimina archivo procesado
                delete_file(ruta=self.archivo, display=True)
            except Exception as e:
                _logger.error(f"[insert_values_in_booktrading()]: {e}")

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
                        if rows["Tipo"] == "Suscripción":
                            codigo = "O"
                            tipomov = "Inversión"
                        elif rows["Tipo"] == "Rescate":
                            codigo = "C"
                            tipomov = "Rescate"
                        else:
                            continue
                        if self.string_float(s=rows.get("Cantidad (VN)", 0)) <= 0:
                            continue
                        if self.string_float(s=rows.get("Precio", 0)) <= 0:
                            continue
                        activo, found = self.RepositorioOportunidades.select_otros_activos(
                            account=self.account_bbva, symbol=rows["Descripción de Especie"]
                        )
                        if not found:
                            precio = self.string_float(s=rows["Precio"])
                            fecha_mv = datetime.strptime(rows["Fecha"], "%d/%m/%Y").date()
                            cafci, cafci_found = self.ClassCNV.select_CNV_by_precio(precio=precio, fecha=fecha_mv)
                            if cafci_found:
                                activo, found = self.RepositorioOportunidades.insert_otros_activos(
                                    symbol=rows["Descripción de Especie"],
                                    cuenta=self.account_bbva,
                                    avgcost_override=precio if precio > 0 else 1,
                                    base_asset="ARS",
                                    idcrypto_override=cafci,
                                    descripcion=rows["Descripción de Especie"],
                                )
                                if found:
                                    self.backfill_historico_cnv(cafci)
                        if found:
                            cantidad = self.string_float(s=rows["Cantidad (VN)"]) * (1 if codigo == "O" else -1)
                            fecha = datetime.strptime(rows["Fecha"], "%d/%m/%Y")
                            tasa_cambio = self.get_tasa_cambio_USDT(fiat="ARS", date=fecha.date())

                            values.update({"categoria": self.vehiculo})
                            values.update({"divisa": "ARS"})
                            values.update({"cuenta": self.account_bbva})
                            values.update({"fechahora": fecha})
                            values.update({"idtrans": rows["Operación"]})
                            values.update({"cantidad": cantidad})
                            values.update({"preciotrans": self.string_float(s=rows["Precio"])})
                            values.update({"preciocierre": self.string_float(s=rows["Precio"])})
                            values.update({"producto": self.string_float(s=rows["Monto Neto"])})
                            values.update({"tarifacomision": 0.0})
                            values.update({"gprealizadas": 0.0})
                            values.update({"mtmgp": 0.0})
                            values.update({"codigo": codigo})
                            values.update({"factor_cambio": tasa_cambio})
                            values.update({"symbol": activo[0]["symbol"]})
                            values.update({"tipomov": tipomov})
                            trader.append(values)

                # insert booktradin
                insert_values_in_booktrading(trader)
            except Exception as e:
                _logger.error(f"[fci_BBVA()]: {e}")

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

                df = pd.read_excel(self.archivo, skiprows=2, header=0, names=list(columns.values()))
                cond1 = df[columns["F"]] == "Inversión"
                cond2 = df[columns["F"]] == "Rescate"
                cond3 = df[columns["F"]] == "Transferencia - origen"
                cond4 = df[columns["F"]] == "Transferencia - destino"
                df_santa = df[cond1 | cond2 | cond3 | cond4]

                santa = df_santa.to_dict(orient="records")
                santa_ord = sorted(
                    [r for r in santa if not pd.isna(r.get("Fecha_liquidación"))],
                    key=lambda x: x["Fecha_liquidación"],
                )
                _logger.warning(f"fci_santander: archivo={self.archivo}, filas_mov={len(santa_ord)}")

                trader = []
                for i, rows in enumerate(santa_ord):

                    # acepta solo Cuenta Títulos  inicada en sesison
                    if rows["Cuenta Títulos"] != self.accounTitulo:
                        continue

                    values = {}
                    ValorCuotaParte = self.string_float(s=rows["Valor_cuotaparte"], tipo="$.,")
                    CuotaParte = self.string_float(s=rows["Cantidad_cuotapartes"], tipo=".,")
                    if ValorCuotaParte > 0 and CuotaParte > 0:

                        # Evalua tipos de movimientos espardos
                        if rows["Movimiento"] == "Inversión":
                            codigo = "O"
                            tipomov = "Inversión"
                        elif rows["Movimiento"] == "Rescate":
                            codigo = "C"
                            tipomov = "Rescate"
                        elif rows["Movimiento"] == "Transferencia - origen":
                            codigo = "C"
                            tipomov = "Transferencia"
                        elif rows["Movimiento"] == "Transferencia - destino":
                            codigo = "O"
                            tipomov = "Transferencia"
                        else:
                            continue

                        activo, found = self.RepositorioOportunidades.select_otros_activos(
                            account=self.account_sant, symbol=rows["Fondo"]
                        )
                        if not found:
                            _fl = rows["Fecha_liquidación"]
                            fecha_mv = (_fl.date() if hasattr(_fl, "date") else datetime.strptime(str(_fl), "%d/%m/%Y").date())
                            cafci, cafci_found = self.ClassCNV.select_CNV_by_precio(
                                precio=ValorCuotaParte, fecha=fecha_mv
                            )
                            if cafci_found:
                                activo, found = self.RepositorioOportunidades.insert_otros_activos(
                                    symbol=rows["Fondo"],
                                    cuenta=self.account_sant,
                                    avgcost_override=ValorCuotaParte,
                                    base_asset="ARS",
                                    idcrypto_override=cafci,
                                    descripcion=rows["Fondo"],
                                )
                                if found:
                                    self.backfill_historico_cnv(cafci)

                        if found:
                            cantidad = CuotaParte * (1 if codigo == "O" else -1)
                            _fl = rows["Fecha_liquidación"]
                            fecha = (_fl if hasattr(_fl, "date") else datetime.strptime(str(_fl), "%d/%m/%Y"))
                            tasa_cambio = self.get_tasa_cambio_USDT(fiat="ARS", date=fecha.date())
                            producto = ValorCuotaParte * CuotaParte
                            values.update({"categoria": self.vehiculo})
                            values.update({"divisa": "ARS"})
                            values.update({"cuenta": self.account_sant})
                            values.update({"fechahora": fecha})
                            comprobante = rows.get("N°_comprobante")
                            if pd.isna(comprobante):
                                continue
                            values.update({"idtrans": str(int(comprobante))})
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
                            values.update({"tipomov": tipomov})
                            trader.append(values)

                # valida e inserta booktrading
                insert_values_in_booktrading(trader)
            except Exception as e:
                _logger.error(f"[fci_santander()]: {e}")

        account = None
        try:
            # carga información BBVA
            self.archivo = self.obtener_archivo_mas_reciente(p_path=self.path, prefijo=self.aliasExcel.get("BBVA"))
            if self.archivo is not None:
                fci_BBVA()
                account = self.account_bbva
        except Exception as e:
            _logger.error(f"load_positions_FCI(BBVA): {e}")

        try:
            # carga información santander
            self.archivo = self.obtener_archivo_mas_reciente(p_path=self.path, prefijo=self.aliasExcel.get("SANT"))
            if self.archivo is not None:
                fci_santander()
                account = account or self.account_sant
        except Exception as e:
            _logger.error(f"load_positions_FCI(SANT): {e}")

        return account

    # carga de booktrading los movimientos USDT
    def get_tasa_cambio_USDT(self, fiat="ARS", date=None):
        try:
            if date is None:
                book, ix = self.RepositorioOportunidades.select_booktrading(
                    accion="tasa_cambio",
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

                    # toma tasa mas reciente anterior a la fecha dada
                    elif values[ix.index("fechahora")].date() <= date:

                        tasa = values[ix.index("preciotrans")]
                        break

                    else:
                        anterior = values[ix.index("preciotrans")]

                return tasa if tasa > 0 else anterior
        except Exception as e:
            print("get_tasa_cambio_USDT(): {}".format(e))

    # valida si llego nueva interfaz para cargar
    def chequea_new_loadFile(self):
        existe = False

        # carga ultima tasa USDT
        self.get_tasa_cambio_USDT(fiat="ARS")

        bbva = self.obtener_archivo_mas_reciente(p_path=self.path, prefijo=self.aliasExcel.get("BBVA"))
        if bbva is not None:
            existe = True

        # santa = self.obtener_archivo_mas_reciente(p_path=self.path, prefijo='últimos movimientos Superfondos')
        santa = self.obtener_archivo_mas_reciente(p_path=self.path, prefijo=self.aliasExcel.get("SANT"))

        if santa is not None:
            existe = True

        diaria = self.obtener_archivo_mas_reciente(p_path=self.path, sufijo=self.aliasExcel.get("CNV"))
        if diaria is not None:
            # laod diaria, actualiza panel y no forza actualzaición de peformance
            self.load_EXCEL_TBdiaria_CNV_()

            # encadena update_FCI_en_positions + panel en una sola callback (evita race con widgets_FCI)
            def _refresh_cnv():
                self.update_FCI_en_positions()
                self.update_panel_fci()
                self.ars.update_panelVehiculo(orden=self.ars.orden)

            self.root.after(0, _refresh_cnv)
            existe = False

        return existe

    def schedule_diaria_performace(self, account):

        update = False
        if account:
            # solo procesar cuando CNV ya publicó precios de ayer — valida fecha en diaria_cnv
            ayer = (datetime.now() - timedelta(days=1)).date()
            ultima_cnv = self.ClassCNV.last_insert_CNV()
            if ultima_cnv == "0001-01-01" or datetime.strptime(ultima_cnv, "%Y-%m-%d").date() < ayer:
                _logger.debug(
                    f"schedule_diaria_performace({account}): CNV gate bloqueado — ultima_cnv={ultima_cnv} ayer={ayer}"
                )
                return update

            t_wait, update = DataHub.last_process[self.vehiculo], False
            update = diaria_book_performance(account=account, vehiculo=self.vehiculo, proces=t_wait)

            if update:
                proceso_update_performance(account=account, vehiculo=self.vehiculo)

        return update

    def _purgar_diaria_si_nueva_operacion(self, account):
        try:
            Performa = IPerformance()
            sql, ix = Performa.select_diaria_performance(account=account)
            if not sql:
                return
            ultima_diaria = max(row[ix.index("Date")] for row in sql)

            book, bix = self.RepositorioOportunidades.select_booktrading(accion="diaria_app", account=account)
            if not book:
                return
            ops_nuevas = [r for r in book if r[bix.index("fechahora")].date() > ultima_diaria]
            if not ops_nuevas:
                return

            desde = min(r[bix.index("fechahora")].date() for r in ops_nuevas)
            result = Performa.purgar_desde(account=account, vehiculo=self.vehiculo, desde=desde)
            DataHub.last_process[self.vehiculo]["diaria_book_performance"] = None
            _logger.warning(f"_purgar_diaria ({account}): purga desde {desde} → {result}")
        except Exception as e:
            _logger.error(f"_purgar_diaria_si_nueva_operacion({account}): {e}")

    # descarga EXCEl de la WEB
    def downdload_CNV_diaria(self):
        try:

            last_process = self.ClassCNV.last_insert_CNV()
            prox_process = datetime.strptime(last_process, "%Y-%m-%d")
            prox_process = prox_process + timedelta(days=1)

            # descarga planilla diaria CNV
            if prox_process.date() < datetime.now().date():
                descargar_cnv_hoy(fecha_str=prox_process.strftime("%Y-%m-%d"))
        except Exception as e:
            _logger.error(f"downdload_CNV_diaria(): {e}")

    # vericica cada 90 segundos si hay nueva interfaz para cargar
    def run_loads(self):
        def run_schedule(task=None):
            while True:

                # descarga de la web planilla diaria CNV
                self.downdload_CNV_diaria()

                # valida si hay nueva interfaz
                if self.chequea_new_loadFile():

                    # encadena update_FCI_en_positions + panel en una sola callback (evita race con widgets_FCI)
                    account = self.load_positions_FCI()

                    def _refresh_fci():
                        self.update_FCI_en_positions()
                        self.update_panel_fci()
                        self.ars.update_panelVehiculo(orden=self.ars.orden)

                    self.root.after(0, _refresh_fci)

                    # si hay operaciones nuevas después de la última diaria → purga para regenerar limpio
                    # se itera account_fci completo porque BBVA y SANT son cuentas independientes
                    if account:
                        for _acc in self.account_fci:
                            if _acc:
                                self._purgar_diaria_si_nueva_operacion(_acc)

                # actualiza diaria y performance siempre — independiente de carga de archivo
                # (gprealizadas de ventas se capturan aunque no haya extracto nuevo ese día)
                ran = False
                for _acc in self.account_fci:
                    ran = self.schedule_diaria_performace(_acc) or ran
                if ran:
                    DataHub.last_process[self.vehiculo]["diaria_book_performance"] = (
                        datetime.now() + timedelta(days=1)
                    ).date()
                    DataHub.last_process["graph_performace_portafolio"] = False

                self.counter += 1
                DataHub.update_self_procesos(proces="thread", tarea=task, itera=self.counter)
                threading.Event().wait(90)

        try:
            task_name = f"schedule_FondoInversion(ARS)"
            DataHub.procesos.append({"thread": {task_name: self.counter}})
            DataHub.manager_events.register_thread(
                name=task_name,
                target=run_schedule,
                task=task_name,
            )
        except Exception as e:
            print(f"run_loads(ARS): {e}")
            traceback.print_exc()


def app():
    root = tk.Tk()
    bgcolor = DataHub.bgcolor
    cgcolor = DataHub.cgcolor
    cchart = DataHub.cchart
    colors = DataHub.colorsk0
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
    style.configure("TFrame", font=("Courier", 8), foreground="white", background="black")
    dpn = ttk.Frame(root, style="TFrame", width=colors["df"], height=700)
    dpn.pack()

    frame_strat = ArsFondosInversion(master=dpn, colores=colors)
    frame_strat.pack()
    frame_strat.mainloop()


if __name__ == "__main__":
    app()
