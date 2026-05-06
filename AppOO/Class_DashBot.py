# Class_DasBot.py
"""
┌─────────────────────┐       ┌──────────────────────┐        ┌──────────────────────┐
│ Dashmain            │ ----> | cvs_forChatbot(Write)|        | Agente_ManagerSell() |
│ (analiza, detecta)  │       │schedule_oportunidades|  ||    | readCSV(file)        |
└─────────────────────┘       └──────────────────────┘        └─────────┬────────────┘
          ┌─────────────────────────────────────────────────────────────┘
          ▼
┌─────────────────────┐
│ Bot Interno         │
│ (usa API Telegram)  │
└─────────┬───────────┘
          │ HTTP Request (API)
          ▼
┌─────────────────────┐
│ Telegram Server     │
│ (procesa   mensaje) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Tu Teléfono         │
│ (notificación)      │
└─────────────────────┘
"""

from Modulos_python import (
    asyncio,
    Bot,
    tk,
    sys,
    scrolledtext,
    pd,
    EmptyDataError,
    time,
    os,
    yf,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQueryHandler,
    ApplicationBuilder,
    CommandHandler,
    BadRequest,
    filters,
    MessageHandler,
    logging,
    json,
    asyncio,
    textwrap,
    datetime,
    timedelta,
    Path,
    wraps,
    signal,
    traceback,
    requests,
    threading,
)

sys.path.insert(0, "..")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "AppValuations"))
from Modulos_Mysql import (
    RepositorioOportunidadesBuySell,
    BDsystem,
    PlanInversion,
    MarketScreen,
    EstrategiaInversion,
    IPerformance,
)
from Class_Finance import scan_extractos
from Class_Screener import sync_market, audit_portfolio, refresh_consenso_tags
from Class_InstitucionalScore import (
    sync_institutional,
    sync_edgar_funds,
    sync_13f_scores,
)
from edgar_13f import sync_fund_filings, sync_13f_holdings
from valuation_edgar_downloader import BASE_DIR, download_filing
from valuation_xbrl_api import get_zip_files
from Class_customer import DataHub, TickerInfo
from Class_BrowserBridge import set_claude_contexto
from Class_ApiBinnace import BinanceClient
from Class_ServiciosCrypto import ServiciosCrypto
from Class_IA_modelos import ModeloOportunidadesSell, ModeloOportunidadesBuy
from Modulos_Utilitarios import define_FileCache, read_json_tmp, write_json_tmp


# Admistrador de Agentes IA
class ClassAgenteIA:
    def __init__(self):

        # Obiene valores de session Stock
        self.vehiculo = "Stock"
        self.positions = []
        self.NotFound = []
        self.PlanInversion = PlanInversion()
        self.sesion = self.PlanInversion.get_sesion_by_vehiculo(self.vehiculo)
        self.account = self.sesion["idcuenta"]
        self.Performa = IPerformance()

        # variables Modelo sell
        modelo = BDsystem.get_modelo_ia(modelo="modelo_sellv01")
        modelo_config = json.loads(modelo["paramts"].decode("utf-8"))
        self.Sellumbral = modelo_config.get("umbral_sell", 0.50)
        self.SellumbralObserv = modelo_config.get("umbral_observacion", 0.35)

        # variables Modelo buy
        modelo = BDsystem.get_modelo_ia(modelo="modelo_buyv01")
        modelo_config = json.loads(modelo["paramts"].decode("utf-8"))
        self.Buyumbral = modelo_config.get("umbral_sell", 0.50)
        self.BuyumbralObserv = modelo_config.get("umbral_observacion", 0.35)

        # Asigna Nombre Logging
        self.logger = logging.getLogger("ClassAgenteIA")

        # Estado del agente de preservación
        self.preservation_state = {}  # {symbol: {max_price, stop_actual, last_check}}
        self.preservation_config = {}  # {vehiculo: sub-dict "preservation"} — extraído de _params_cache
        self.preservation_last_run = {}  # {vehiculo: datetime} — última evaluación por vehículo
        self._params_cache = {}  # {vehiculo: full parsed parameters dict} — compartido entre agentes

    # decorador para limitar ejecuciones
    def wait_rate(intervalo_segundos: int, persist: bool = False):
        """
        Fábrica de Decoradores: Restringe la ejecución de la función
        a un máximo de una vez por el intervalo de tiempo especificado.

        Args:
            intervalo_segundos (int): Tiempo mínimo de espera entre llamadas (en segundos).
            persist (bool): Si True, persiste last_run en tmp/agents_schedule.json
                            para sobrevivir reinicios. Usar para intervalos > 12h.
        """
        _FILE = "agents_schedule.json"

        def decorator(func):
            func.last_run = 0

            @wraps(func)
            def wrapper(*args, **kwargs):
                tiempo_actual = time.time()
                if func.last_run == 0 and persist:
                    func.last_run = read_json_tmp(_FILE).get(func.__name__, 0)
                tiempo_transcurrido = tiempo_actual - func.last_run

                if tiempo_transcurrido < intervalo_segundos:
                    tiempo_restante = intervalo_segundos - tiempo_transcurrido
                    logging.getLogger("ClassAgenteIA").debug(
                        f"wait_rate: '{func.__name__}' bloqueado — faltan {int(tiempo_restante)}s"
                    )
                    wrapper._overdue = False
                    return None
                else:
                    # True si lleva más de 1.5x el intervalo sin ejecutar (reinicios frecuentes)
                    wrapper._overdue = tiempo_transcurrido > intervalo_segundos * 1.5
                    resultado = func(*args, **kwargs)
                    func.last_run = tiempo_actual
                    if persist:
                        data = read_json_tmp(_FILE)
                        data[func.__name__] = tiempo_actual
                        write_json_tmp(_FILE, data)
                    wrapper._overdue = False
                    return resultado

            return wrapper

        return decorator

    _BUY_TAGS = {"UNANIME", "CONSENSO", "TENDENCIA"}
    _SELL_TAGS = {"ALERTA", "SALIDA"}

    def _consenso_info(self, symbol):
        rows, ix = MarketScreen().select(account=self.account, symbol=symbol)
        if not rows or not ix:
            return None, None
        try:
            tag = rows[0][ix.index("consenso_tag")]
            suma = rows[0][ix.index("consenso_suma")]
            return tag, suma
        except (ValueError, IndexError):
            return None, None

    def _consenso_tag(self, symbol):
        tag, _ = self._consenso_info(symbol)
        return tag

    # Controla si el mensaje debe enviarse a Telegram según reglas:
    def Agente_message_Manager_sell(self, row):
        """
        reglas:
        - mejora de ROI
        - tiempo mínimo desde último envío (DataHub.min_tiempo)
        - máximo de mensajes por ciclo (DataHub.max_mensajes).
        """
        symbol = row["Symbol"]
        roi = row["%Roi"]
        ahora = datetime.now()

        # Regla 1: mejora ROI
        if symbol in self.ultimo_envio:
            if roi <= self.ultimo_envio[symbol]["roi"]:
                return False  # no hay mejora

            # Regla 2: tiempo mínimo desde último mensaje
            delta = (ahora - self.ultimo_envio[symbol]["time"]).total_seconds()
            if delta < DataHub.min_tiempo:
                return False

        # Regla 3: máximo de mensajes por ciclo
        # if len(self.sell_enviados) >= DataHub.max_mensajes:
        #    return False

        # Gate Consenso: SELL solo pasa si los fundamentos institucionales confirman salida
        tag = self._consenso_tag(symbol)
        if tag and tag not in self._SELL_TAGS:
            return False

        # si pasó todas las reglas → actualiza registro
        self.ultimo_envio[symbol] = {"roi": roi, "time": ahora}
        return True

    # Controla si el mensaje Buy debe enviarse a Telegram según reglas:
    def Agente_message_Manager_Buy(self, row):
        """
        Reglas para Buy:
        - mejora de score (mayor score = mejor oportunidad)
        - tiempo mínimo desde último envío (DataHub.min_tiempo_buy)
        """
        symbol = row.get("Symbol", "")
        score = row.get("score", 0)
        ahora = datetime.now()

        # Gate Consenso: BUY solo pasa si los fundamentos institucionales (sin voto Mod) apoyan
        tag = self._consenso_tag(symbol)
        if tag and tag not in self._BUY_TAGS:
            return False

        # Regla 1: mejora de score
        if symbol in self.ultimo_envio_buy:
            if score <= self.ultimo_envio_buy[symbol]["score"]:
                return False  # no hay mejora

            # Regla 2: tiempo mínimo desde último mensaje
            delta = (ahora - self.ultimo_envio_buy[symbol]["time"]).total_seconds()
            if delta < DataHub.min_tiempo_buy:
                return False

        # si pasó todas las reglas → actualiza registro
        self.ultimo_envio_buy[symbol] = {"score": score, "time": ahora}
        return True

    def Agente_message_Manager_Top10(self, tipo="sell"):
        """
        Controla si el TOP 10 debe enviarse a Telegram según reglas:
        - Cambio en el ranking (nuevo símbolo en top 3, o cambio de posición significativo)
        - Tiempo mínimo desde último envío (self.min_tiempo_top10)
        Retorna: (debe_enviar: bool, ranking_actual: list)
        """
        ahora = datetime.now()

        if tipo == "sell":
            top10 = self.get_top_sell()
            ultimo = self.ultimo_top10_sell
        else:
            top10 = self.get_top_buy()
            ultimo = self.ultimo_top10_buy

        if not top10:
            return False, []

        # Extraer símbolos del ranking actual
        ranking_actual = [row.get("Symbol", "") for row in top10]

        # Primera vez: siempre enviar
        if not ultimo["ranking"] or ultimo["time"] is None:
            return True, ranking_actual

        # Regla 1: Cambio en TOP 3 (los más importantes)
        top3_anterior = ultimo["ranking"][:3]
        top3_actual = ranking_actual[:3]
        cambio_top3 = top3_anterior != top3_actual

        # Regla 2: Nuevo símbolo entró al TOP 10
        nuevo_en_top10 = any(s not in ultimo["ranking"] for s in ranking_actual)

        # Regla 3: Tiempo mínimo transcurrido
        delta = (ahora - ultimo["time"]).total_seconds()
        tiempo_cumplido = delta >= self.min_tiempo_top10

        # Enviar si hay cambio significativo Y pasó tiempo mínimo
        if (cambio_top3 or nuevo_en_top10) and tiempo_cumplido:
            return True, ranking_actual

        return False, ranking_actual

    # agente para las recomendaciones de ventas ---------------------------------------------------------------------------------
    async def Agente_ManagerSell(self):
        try:
            df_sell = self.readCSV_sell(file="csv_datosIA_sell")

            if df_sell.empty:
                return

            await self.evaluar_oportunidades_sell_con_IA(
                df_sell=df_sell,
                umbral_venta=self.Sellumbral,
                umbral_observacion=self.SellumbralObserv,
            )
        except Exception as e:
            self.logger.error(f"Agente_ManagerSell(): {e}")

    # agente para las recomendaciones de compras
    async def Agente_ManagerBuy(self):
        try:
            df_buy = self.readCSV_buy(file="csv_datosIA_buy")

            if df_buy.empty:
                return

            await self.evaluar_oportunidades_buy_con_IA(
                df_buy=df_buy,
                umbral_compra=self.Buyumbral,
                umbral_observacion=self.BuyumbralObserv,
            )
        except Exception as e:
            self.logger.error(f"Agente_ManagerBuy(): {e}")

    # agente para enviar TOP 10 cuando cambia el ranking
    async def Agente_ManagerTop10(self):
        """
        Monitorea cambios en el TOP 10 y envía actualizaciones a Telegram
        cuando la opción Top10 está seleccionada.
        Envía 5 Sell + 5 Buy para entrenamiento efectivo.
        """
        try:
            # Solo procesar si la opción Top10 está activa
            if self.MostrarOpcionMenu_enTelegram != "Top10":
                return

            # Verificar y enviar TOP 5 Sell + TOP 5 Buy si hay cambios
            await self.send_top10_telegram(forzar=False)

        except Exception as e:
            self.logger.error(f"Agente_ManagerTop10(): {e}")

    # agente paras las descargas de filings cada 3600 seg
    @wait_rate(3600)
    def Agente_downloads_filings_EDGAR(self):
        try:
            # desacrga la estructura positions
            self.positions = self.PlanInversion.select_inversion(tipoin=self.vehiculo, ticket="all")

            counter = 1
            for positio in self.positions:
                ticker = positio.get("ticket")
                sectype = positio.get("sectype")

                # skip not found
                if ticker in self.NotFound:
                    continue

                # skip is not STK
                if sectype not in ("STK", "EQUITY"):
                    continue

                # valida filings en directorio
                ticker_dir = Path(BASE_DIR) / f"{positio.get("ticket")}_EDGAR_Files"
                files = get_zip_files(ticker_dir=ticker_dir)
                if files:
                    continue

                # procede con la descarga de EDGAR
                counter += 1
                found = download_filing(ticker=ticker)
                if not found:
                    self.NotFound.append(ticker)
                    self.logger.warning(textwrap.dedent(f"""
                            ==============================================================================================
                            Agente_downloads_filings_EDGAR(): 
                            = 
                            🚨 FILINGS DENEGADO. Posible deslistado del ticker: {ticker}
                            ==============================================================================================

                            """))

                elif found:
                    # controla que no haga mas de 2 downloads en EDGAR
                    if counter > 2:
                        return None
        except Exception as e:
            print(f"Angente_downloads_filings_EDGAR(): {e}")

    # agente Market Screener — descubre símbolos + enriquece con Yahoo, una vez al día
    @wait_rate(86400, persist=True)
    def Agente_MarketScreener(self):
        try:
            result = sync_market(account=self.account)
            self.logger.warning(
                f"MarketScreener: descargados={result['descargados']} insertados={result['insertados']} "
                f"omitidos={result['omitidos']} actualizados={result['actualizados']}"
            )
        except Exception as e:
            self.logger.error(f"Agente_MarketScreener(): {e}")

    # agente Institutional Score — enriquece Market con ownership institucional, una vez al día
    @wait_rate(86400, persist=True)
    def Agente_InstitucionalScore(self):
        try:
            result = sync_institutional(account=self.account)
            self.logger.warning(
                f"InstitucionalScore: procesados={result['symbols_processed']} actualizados={result['updated']}"
            )
        except Exception as e:
            self.logger.error(f"Agente_InstitucionalScore(): {e}")

    # agente Consenso Cache — materializa consenso_tag/suma (sin voto Mod) en market cada 5 min
    @wait_rate(300, persist=True)
    def Agente_ConsensoCache(self):
        try:
            result = refresh_consenso_tags(account=self.account)
            self.logger.warning(f"ConsensoCache: actualizados={result['actualizados']}/{result['total']}")
        except Exception as e:
            self.logger.error(f"Agente_ConsensoCache(): {e}")

    # agente Edgar Funds — carga todos los filers 13F-HR de EDGAR en tabla funds, una vez por mes
    @wait_rate(2592000, persist=True)
    def Agente_EdgarFunds(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_EdgarFunds._overdue:
            return
        try:
            result = sync_edgar_funds()
            self.logger.warning(f"EdgarFunds: total={result['total']} insertados={result['inserted']}")
        except Exception as e:
            self.logger.error(f"Agente_EdgarFunds(): {e}")

    # agente Fund Filings — descarga XMLs 13F-HR para top 50 fondos, una vez por semana
    @wait_rate(604800, persist=True)
    def Agente_FundFilings(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_FundFilings._overdue:
            return
        try:
            result = sync_fund_filings()
            self.logger.warning(
                f"FundFilings: fondos={result['funds']} descargados={result['downloaded']} "
                f"skipped={result['skipped']} fallidos={result['failed']}"
            )
        except Exception as e:
            self.logger.error(f"Agente_FundFilings(): {e}")

    # agente 13F Scores — recalcula inst_score con señales 13F, una vez al día
    @wait_rate(86400, persist=True)
    def Agente_13FScores(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_13FScores._overdue:
            return
        try:
            result = sync_13f_scores(account=self.account)
            self.logger.warning(
                f"13FScores: símbolos={result['symbols']} actualizados={result['updated']} skipped={result['skipped']}"
            )
        except Exception as e:
            self.logger.error(f"Agente_13FScores(): {e}")

    # agente 13F Holdings — parsea XMLs descargados y pobla fund_holdings, una vez al día
    @wait_rate(86400, persist=True)
    def Agente_13FHoldings(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_13FHoldings._overdue:
            return
        try:
            result = sync_13f_holdings(account=self.account)
            self.logger.warning(
                f"13FHoldings: archivos={result['xml_files']} "
                f"holdings={result['inserted_holdings']} opciones={result['inserted_options']}"
            )
            deleted = MarketScreen().cleanup_fund_holdings_nulls()
            self.logger.warning(f"13FHoldings cleanup: eliminadas={deleted} filas NULL")
        except Exception as e:
            self.logger.error(f"Agente_13FHoldings(): {e}")

    # agente auditoría cartera — detecta delistados/renombrados, mensual
    @wait_rate(2592000, persist=True)
    def Agente_AuditPortfolio(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_AuditPortfolio._overdue:
            return
        try:
            result = audit_portfolio(account=self.account)
            self.logger.warning(
                f"AuditPortfolio: total={result['total']} delistados={result['delistados']} "
                f"nombres_upd={result['nombres_upd']} cusips_upd={result['cusips_upd']} "
                f"etfs_upd={result['etfs_upd']} sin_precio={result['sin_precio']} errores={result['errores']}"
            )
        except Exception as e:
            self.logger.error(f"Agente_AuditPortfolio(): {e}")

    def _consultar_claude(self, mensaje_usuario, contexto=""):
        """Llamada general a Claude API para el chatbot. Retorna respuesta en texto."""
        sesion_claude = BDsystem.get_sesion_by_vehiculo("ClaudeAPI")
        api_key = sesion_claude["userapi"].decode("utf-8")

        sistema = (
            "Sos un asistente de inversión integrado en una app de trading. "
            "Respondé en español, de forma concisa y directa. "
            "Tenés acceso al estado actual de la cartera del usuario."
        )
        if contexto:
            sistema += f"\n\nContexto actual:\n{contexto}"

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 512,
                "system": sistema,
                "messages": [{"role": "user", "content": mensaje_usuario}],
            },
            timeout=30,
        )
        if not resp.ok:
            raise RuntimeError(f"{resp.status_code} — {resp.json()}")
        return resp.json()["content"][0]["text"].strip()

    def _clasificar_etf_claude(self, yf_info, opciones):
        """Llama Claude Haiku para clasificar un ETF en una estrategia del sistema. Retorna código (P01..P05) o None."""
        sesion_claude = BDsystem.get_sesion_by_vehiculo("ClaudeAPI")
        api_key = sesion_claude["userapi"].decode("utf-8")
        if not api_key:
            self.logger.error("_clasificar_etf_claude: userapi no configurada en sesion ClaudeAPI")
            return None

        opciones_str = " | ".join(f"{o['descripcion']}({o['estrategia']})" for o in opciones)
        nombre = yf_info.get("longName") or yf_info.get("shortName", "")
        descripcion = (yf_info.get("longBusinessSummary") or "N/A")[:400]
        categoria = yf_info.get("category") or "N/A"

        prompt = (
            f"Clasificá este activo financiero en exactamente una de estas categorías:\n"
            f"{opciones_str}\n\n"
            f"Nombre: {nombre}\n"
            f"Descripción: {descripcion}\n"
            f"Categoría Morningstar: {categoria}\n\n"
            f"Respondé solo el código de estrategia (ej: P01). Sin explicación."
        )

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15,
        )
        resp.raise_for_status()
        codigo = resp.json()["content"][0]["text"].strip()
        codigos_validos = {o["estrategia"] for o in opciones}
        return codigo if codigo in codigos_validos else None

    # agente clasificador ETF — corre semanalmente, asigna estrategia Balance (P01-P05)
    # a ETFs detectados en market (categoriaActivo='X') usando DataHub + Claude Haiku.
    # Write-once: no reclasifica ETFs que ya tienen estrategia Balance asignada.
    @wait_rate(604800, persist=True)
    def Agente_ClasificadorETF(self):
        try:
            estrategia_svc = EstrategiaInversion()
            opciones = estrategia_svc.select(accion="vehiculo", ivehiculo="Balance")
            etfs = estrategia_svc.get_etfs_pendientes(self.account)
            clasificados, sin_info = 0, 0
            for etf in etfs:
                symbol = etf["symbol"]
                yf_info = DataHub.info.get(symbol, {}).get("activos", {})
                if not yf_info:
                    sin_info += 1
                    continue
                codigo = self._clasificar_etf_claude(yf_info, opciones)
                if codigo:
                    estrategia_svc.update_estrategia_etf(symbol, self.account, codigo)
                    clasificados += 1
            self.logger.warning(
                f"Agente_ClasificadorETF: pendientes={len(etfs)} clasificados={clasificados} sin_info={sin_info}"
            )
        except Exception as e:
            self.logger.error(f"Agente_ClasificadorETF(): {e}")

    # Agente LTV — mantiene el LTV en ~28% para evitar liquidaciones de colateral en Binance.
    # Corre cada 5 min. Si el precio del colateral baja (LTV sube) → agrega colateral automáticamente.
    # Si el precio sube (LTV baja) → retira colateral sobrante hacia Earn.
    # Complementa loan_distribute (distribución inicial manual desde AnalisisCrypto).
    # Parámetros: bloque "ltv" en el JSON de sesión Crypto (target, umbral_alto, umbral_bajo, umbral_critico).
    # Doc completa: Doc/ltv_agent.md
    @wait_rate(300, persist=True)
    def Agente_LtvControl(self):
        try:
            params = self._load_params("Crypto")
            lconfig = (params or {}).get("ltv", {})

            svc = ServiciosCrypto()
            analisis = svc.ltv_check_and_adjust(lconfig)
            if not analisis:
                self.logger.warning("Agente_LtvControl: sin préstamos activos")
                return

            # Siempre sincronizar DataHub — independiente de si hay lconfig o no
            total_col = sum(i["collateral_usd"] for i in analisis)
            total_deuda = sum(i["loan_usd"] for i in analisis)

            # capital_neto = earn balance de activos en garantía - deuda
            # misma base que _seccion_deuda en AnalisisCrypto (earn_spot_balances)
            try:
                earn_balances = svc.earn_spot_balances()
                earn_map = {b["asset"]: b.get("usdt_value", 0.0) for b in earn_balances}
                col_assets = {i["collateralCoin"] for i in analisis}
                capital_earn_col = sum(earn_map.get(a, 0.0) for a in col_assets)
            except Exception as e_earn:
                self.logger.error(f"LtvControl earn_spot_balances: {e_earn}")
                capital_earn_col = 0.0
            capital_neto = (capital_earn_col if capital_earn_col > 0 else total_col) - total_deuda

            DataHub.manager_GyP["Crypto"]["Colateral"] = total_col
            DataHub.manager_GyP["Crypto"]["CapitalNeto"] = capital_neto
            DataHub.manager_GyP["Crypto"]["Debit"] = total_deuda
            DataHub.manager_GyP["Crypto"]["Leverage"] = total_col / max(capital_neto, 1.0)
            beta_actual = DataHub.manager_GyP["Crypto"].get("BetaPortfolio", 1.5)
            mrg_actual = total_deuda / max(capital_neto, 1.0) * beta_actual
            self.logger.warning(
                f"LtvControl DataHub: col={total_col:.2f} earn_col={capital_earn_col:.2f} "
                f"deuda={total_deuda:.2f} neto={capital_neto:.2f} beta={beta_actual:.3f} → mrg={mrg_actual:.2%}"
            )

            # Ajuste LTV — solo si hay config explícita
            if not lconfig:
                return
            for item in analisis:
                gap = item["ltv_actual"] - lconfig.get("target", 0.50)
                gap_str = f"+{gap:.2%}" if gap >= 0 else f"{gap:.2%}"
                if item["ajuste_direction"] and item["ajuste_coin"] > 0:
                    resp = svc._spot.get_flexible_adjust_ltv(
                        loanCoin=item["loanCoin"],
                        collateralCoin=item["collateralCoin"],
                        adjustType=item["ajuste_direction"],
                        amount=item["ajuste_coin"],
                    )
                    ajuste_str = (
                        f"{item['ajuste_direction']} {item['ajuste_coin']:.4f} {item['collateralCoin']} → {resp}"
                    )
                else:
                    ajuste_str = "sin ajuste"
                self.logger.warning(
                    f"LTV [{item['collateralCoin']}] {item['ltv_actual']:.2%} gap={gap_str} "
                    f"{item['estado']} | col={item['collateral_amount']:.4f} (~{item['collateral_usd']:.2f}) "
                    f"deuda={item['loan_usd']:.2f} | {ajuste_str}"
                )

        except Exception as e:
            self.logger.error(f"Agente_LtvControl(): {e}")

    # agente beta portfolio Stock — actualiza BetaPortfolio cada hora desde DB + posiciones vivas
    @wait_rate(3600, persist=True)
    def Agente_StockBeta(self):
        try:
            positions = [p for p in DataHub.manager_positions.get("Stock", []) if float(p.get("mktvalue", 0)) > 0]
            if not positions:
                return
            result = MarketScreen().select_all(account=self.account)
            if not result:
                return
            rows, ix = result
            if not rows or not ix:
                return
            beta_map = {dict(zip(ix, row))["symbol"]: dict(zip(ix, row)).get("beta") for row in rows}
            total_val, beta_sum = 0.0, 0.0
            for p in positions:
                val = float(p.get("mktvalue", 0))
                beta_raw = beta_map.get(p.get("ticket", ""))
                try:
                    beta = float(beta_raw) if beta_raw is not None else 1.0
                except (TypeError, ValueError):
                    beta = 1.0
                beta_sum += val * beta
                total_val += val
            beta_port = round(max(beta_sum / total_val, 0.1), 3) if total_val > 0 else 1.0
            DataHub.manager_GyP["Stock"]["BetaPortfolio"] = beta_port
            self.logger.warning(f"StockBeta: β={beta_port:.3f}  ({len(positions)} posiciones)")
        except Exception as e:
            self.logger.error(f"Agente_StockBeta(): {e}")

    # agente beta portfolio Crypto — descarga histórico yfinance y calcula beta vs BTC cada 6h
    @wait_rate(21600)
    def Agente_CryptoBeta(self):
        try:
            positions = [p for p in DataHub.manager_positions.get("Crypto", []) if float(p.get("position", 0)) > 0]
            if not positions:
                return
            orig_names = [p["ticket"] for p in positions]
            yf_names = [s[:-4] + "-USD" if s.endswith("USDT") else s for s in orig_names]
            name_map = dict(zip(yf_names, orig_names))
            raw = yf.download(yf_names, period="6mo", auto_adjust=True, progress=False)
            if raw.empty:
                return
            close = (
                raw[["Close"]].rename(columns={"Close": orig_names[0]})
                if len(yf_names) == 1
                else raw["Close"].rename(columns=name_map)
            )
            returns = close.pct_change().dropna()
            if returns.empty or len(returns) < 10:
                return
            btc_col = next((c for c in returns.columns if "BTC" in c.upper()), None)
            market_ret = returns[btc_col] if btc_col else returns.mean(axis=1)
            market_var = market_ret.var()
            if market_var == 0:
                return
            beta_map = {col: returns[col].cov(market_ret) / market_var for col in returns.columns}
            total_val = sum(float(p.get("mktvalue", 0)) for p in positions)
            if total_val <= 0:
                return
            beta_port = sum(
                (float(p.get("mktvalue", 0)) / total_val) * beta_map.get(p["ticket"], 1.5) for p in positions
            )
            DataHub.manager_GyP["Crypto"]["BetaPortfolio"] = round(max(beta_port, 0.1), 3)
            self.logger.warning(
                f"CryptoBeta: β={DataHub.manager_GyP['Crypto']['BetaPortfolio']:.3f}  ({len(positions)} posiciones)"
            )
        except Exception as e:
            self.logger.error(f"Agente_CryptoBeta(): {e}")

    # agente extractos bancarios — escanea tmp/extractos/ y carga PDFs nuevos cada hora
    @wait_rate(3600, persist=True)
    def Agente_ExtractosWatcher(self):
        try:
            result = scan_extractos()
            self.logger.warning(f"Agente_ExtractosWatcher: {result}")
        except Exception as e:
            self.logger.error(f"Agente_ExtractosWatcher(): {e}")

    # agente splits — detecta y aplica splits de yfinance a booktrading diariamente
    @wait_rate(86400, persist=True)
    def Agente_SplitsControl(self):
        try:
            result = self.RepositorioOportunidades.sync_splits(account=self.account)
            self.logger.warning(
                f"Agente_SplitsControl: nuevos={result['nuevos']} aplicados={result['aplicados']} residuos={result['residuos']}"
            )
        except Exception as e:
            self.logger.error(f"Agente_SplitsControl(): {e}")

    # agente validador de performa — detecta precios yfinance corruptos y purga para regeneración
    @wait_rate(3600, persist=True)
    def Agente_PerformaValidator(self):
        try:
            result = self.Performa.validate_performa(account=self.account, vehiculo=self.vehiculo)
            if result["purgados"]:
                detalle = ", ".join(f"{a['symbol']} {a['fecha']} ratio={a['ratio']:.2f}x" for a in result["anomalias"])
                self.logger.warning(f"Agente_PerformaValidator: anomalías purgadas — {detalle}")
        except Exception as e:
            self.logger.error(f"Agente_PerformaValidator(): {e}")

    # agente defensivo: protege ganancias con órdenes STOP dinámicas
    async def Agente_ManagerPreservation(self):
        """
        Agente de Preservación de Ganancias (Stock + Crypto).
        Protege ganancias acumuladas mediante órdenes STOP dinámicas.
        No optimiza ventas, no predice mercado, solo protege.
        """
        for vehiculo in ("Stock", "Crypto"):
            try:
                # valida conexion del vehiculo antes
                if DataHub.manager_sesion.get(vehiculo):
                    self._preservation_run_vehiculo(vehiculo)
                else:
                    self.logger.warning(f"Agente_ManagerPreservation({vehiculo}): sesion no activa → SKIP")
            except Exception as e:
                self.logger.error(f"Agente_ManagerPreservation({vehiculo}): {e}")

    def _load_params(self, vehiculo):
        """
        Carga y cachea el JSON completo de parameters para el vehiculo.
        Fuente única — evita duplicar parseo entre agentes (preservation, ltv, etc.).
        Retorna dict o None si no hay parameters en sesion.
        """
        if vehiculo not in self._params_cache:
            sesion = self.PlanInversion.get_sesion_by_vehiculo(vehiculo)
            params_raw = sesion.get("parameters")
            if not params_raw:
                self._params_cache[vehiculo] = None
            else:
                self._params_cache[vehiculo] = json.loads(
                    params_raw.decode("utf-8") if isinstance(params_raw, bytes) else params_raw
                )
        return self._params_cache.get(vehiculo)

    def _preservation_get_config(self, vehiculo):
        """
        Carga config desde BD una sola vez por vehículo (cache en self.preservation_config).
        En cada ciclo solo verifica si pasó el intervalo — sin tocar BD.
        Retorna (pconfig, intervalo_min, ejecutar) donde ejecutar=True cuando toca revisión.
        """
        # 1. Carga config una sola vez al arranque del vehículo
        if vehiculo not in self.preservation_config:
            params = self._load_params(vehiculo)
            if not params:
                self.logger.warning(f"Preservation({vehiculo}): sin parameters en sesion → SKIP")
                self.preservation_config[vehiculo] = None
                return None, 0, False
            pconfig = params.get("preservation")
            if not pconfig:
                self.logger.warning(f"Preservation({vehiculo}): sin bloque 'preservation' en parameters → SKIP")
                self.preservation_config[vehiculo] = None
                return None, 0, False
            self.preservation_config[vehiculo] = pconfig
            roi_minimo = pconfig.get("roi_minimo", 0.10)
            proteccion_base = pconfig.get("proteccion_base", 0.50)
            self.logger.warning(
                f"Preservation({vehiculo}): config cargada | roi_min={roi_minimo} | prot={proteccion_base}"
            )

        pconfig = self.preservation_config.get(vehiculo)
        if not pconfig:
            return None, 0, False

        revisiones_dia = pconfig.get("revisiones_dia", 2)
        intervalo_min = 86400 / revisiones_dia
        # TODO TEST: intervalo reducido para pruebas, restaurar en producción
        intervalo_min = 600  # 10 minutos para testing

        # 2. Verificar intervalo por vehículo — único acceso a BD solo cuando toca
        last_run = self.preservation_last_run.get(vehiculo)
        if last_run is None:
            # Primera ejecución: inicializa reloj pero no evalúa todavía
            self.preservation_last_run[vehiculo] = datetime.now()
            return pconfig, intervalo_min, False

        elapsed = (datetime.now() - last_run).total_seconds()
        if elapsed < intervalo_min:
            return pconfig, intervalo_min, False

        # Toca revisión: actualiza reloj y autoriza evaluación
        self.preservation_last_run[vehiculo] = datetime.now()
        roi_minimo = pconfig.get("roi_minimo", 0.10)
        proteccion_base = pconfig.get("proteccion_base", 0.50)
        self.logger.warning(
            f"Preservation({vehiculo}): REVISIÓN | roi_min={roi_minimo} | prot={proteccion_base} | elapsed={elapsed:.0f}s"
        )
        return pconfig, intervalo_min, True

    def _preservation_run_vehiculo(self, vehiculo):
        """Orquesta la preservación para un vehículo. Lógica de vehículo en DataHub."""

        pconfig, intervalo_min, time_revision = self._preservation_get_config(vehiculo)
        if not time_revision:
            return

        roi_minimo = pconfig.get("roi_minimo", 0.10)
        proteccion_base = pconfig.get("proteccion_base", 0.50)
        correccion_pct = pconfig.get("correccion_pct", 0.08)
        atr_mult = pconfig.get("atr_mult", 2.0)

        # 1. Cargar posiciones activas
        positions = self.PlanInversion.select_inversion(tipoin=vehiculo, ticket="all")
        self.logger.warning(f"Preservation({vehiculo}): {len(positions)} posiciones cargadas")

        for positio in positions:
            symbol = positio.get("ticket")
            costobase = positio.get("costobase", 0)
            unrealizedpnl = positio.get("unrealizedpnl", 0)
            position_qty = positio.get("position", 0)
            conid = positio.get("conid")
            account = positio.get("useraccount")
            base_limit = unrealizedpnl * proteccion_base

            if costobase <= 0 or position_qty <= 0:
                continue

            # 2. Verificar ROI >= roi_minimo
            roi = unrealizedpnl / costobase
            if roi < roi_minimo:
                continue

            self.logger.warning(f"Preservation({vehiculo}/{symbol}): ROI={roi:.1%} ≥ {roi_minimo:.0%} → evaluando")

            # estado previo del símbolo
            state = self.preservation_state.get(symbol, {})

            # 4. Obtener precio actual (DataHub)
            last = DataHub.preservation_get_price(symbol, positio)
            if not last or last <= 0:
                self.logger.warning(f"Preservation({vehiculo}/{symbol}): sin precio → SKIP")
                continue

            # 5. Calcular ATR (DataHub)
            atr, atr_error = DataHub.preservation_get_atr(symbol, vehiculo)
            if atr is None:
                self.logger.warning(f"Preservation({vehiculo}/{symbol}): {atr_error} → SKIP")
                continue

            # 6. Actualizar max_price
            max_price_prev = state.get("max_price", last)
            max_price = max(max_price_prev, last)

            # 7. Calcular stop
            stop_distance = max(correccion_pct * max_price, atr_mult * atr)
            stop_calculado = max_price - stop_distance

            # 8. Regla de oro: nunca bajar el stop
            stop_anterior = state.get("stop_actual", 0)
            stop_final = max(stop_anterior, stop_calculado)

            # 9. Cantidad a proteger (DataHub — respeta lotSize en Crypto)
            qty = DataHub.preservation_calc_qty(self.account, vehiculo, symbol, last, base_limit)
            if qty <= 0:
                continue

            # 10. Construir trama de orden STOP (DataHub)
            trama = DataHub.preservation_build_trama(vehiculo, account, symbol, conid, stop_final, max_price, 10)

            order_id_prev = state.get("order_id")

            # Activa Order STOP para el symbol
            if stop_final > stop_anterior and symbol == "PBR":

                self.logger.warning(
                    f"Preservation({vehiculo}/{symbol}): base_limit {base_limit}, Order: {trama},  Previo: {order_id_prev}"
                )
                if order_id_prev:
                    DataHub.preservation_cancel_order(vehiculo, account, order_id_prev, symbol)

                response = DataHub.preservation_send_order(vehiculo, trama)
                order_id = DataHub.preservation_extract_order_id(response)

                order_id = order_id_prev

                accion = "NUEVA" if not order_id_prev else "MODIFICADA (cancel+new)"
                self.logger.warning(
                    f"Preservation({vehiculo}/{symbol}): "
                    f"ROI={roi:.1%} | last={last:.2f} | max={max_price:.2f} | "
                    f"ATR={atr:.2f} | stop_prev={stop_anterior:.2f} → stop_new={stop_final:.2f} | "
                    f"qty={qty} | {accion} [DRY-RUN]"
                )
            else:
                order_id = order_id_prev
                self.logger.warning(
                    f"Preservation({vehiculo}/{symbol}): "
                    f"ROI={roi:.1%} | last={last:.2f} | max={max_price:.2f} | "
                    f"stop={stop_final:.2f} (sin cambio)"
                )

            # 11. Persistir estado
            self.preservation_state[symbol] = {
                "max_price": max_price,
                "stop_actual": stop_final,
                "last_check": datetime.now(),
                "order_id": order_id,
                "vehiculo": vehiculo,
                "trama": trama,
            }


# Admistrador de mensajeria Telegram
class Telegram:
    def __init__(self):
        self.MostrarOpcionMenu_enTelegram = "menu"
        self.SentMessage = []
        self.DeleteMessageHash = []
        self.simulation = True

        # Control de frecuencia para TOP 10
        self.ultimo_top10_sell = {"ranking": [], "time": None}
        self.ultimo_top10_buy = {"ranking": [], "time": None}
        self.min_tiempo_top10 = 120  # segundos mínimo entre actualizaciones TOP 10

        # Token / ID que te da BotFather - personal (número)
        sesion = BDsystem.get_sesion_by_vehiculo("Chatbot")
        self.TOKEN = sesion["userapi"].decode("utf-8")
        self.CHAT_ID = int(sesion["iduser"])

        # 🔑 Definición de usuarios autorizados (Lista de Integers)
        self.userAuth = [self.CHAT_ID, 7726175446]

    # método para capturar cualquier mensaje de texto
    async def handle_segurity_message(self, update, context):

        chat_id = update.effective_chat.id
        nombre_usuario = update.effective_chat.first_name

        if chat_id not in self.userAuth:
            # 🛑 Acción de Seguridad: Loguea el ID del nuevo usuario
            self.logger.warning(textwrap.dedent(f"""
                  ==============================================================================================
                  handle_segurity_message(): 
                  = 
                  🚨 ACCESO DENEGADO. Nuevo chat_id para autorizar: {chat_id} | Nombre: {nombre_usuario}
                  ==============================================================================================

                  """))

            await update.message.reply_text(
                f"❌ Acceso Denegado. Por favor, contacta al administrador. ID de Chat asignado: `{chat_id}`",
                parse_mode="Markdown",
            )
            return

        # Si el usuario está en la lista:
        if update.message.text == "/start":
            await self.send_Telegram(f"¡Bienvenido de nuevo, {nombre_usuario}!")
            await self.handle_menu()
        else:
            # Opcional: Reenvía el mensaje al chat interno (si quieres que el asistente responda)
            self._agregar_mensaje(f"👤 Telegram: {update.message.text}")
            # ... tu lógica de respuesta aquí ...

    # Método para enviar menú principal
    async def handle_menu(self, update=None, context=None):

        # 🔑 Si el update existe, envía solo al usuario que hizo la solicitud
        CHAT_ID = [update.effective_chat.id] if update else None

        # elimina del chat los mensajes anteriores
        if CHAT_ID:
            await self.clear_bot_chat(CHAT_ID)

            botones = [
                [
                    InlineKeyboardButton("⬇️⬆️ Top(10)", callback_data="menu_top"),
                    InlineKeyboardButton("⬇️ Sell", callback_data="menu_sell"),
                    InlineKeyboardButton("⬆️ Buy", callback_data="menu_buy"),
                ],
                [
                    InlineKeyboardButton("🎯 Performan", callback_data="performan"),
                    InlineKeyboardButton("🟢🔴 Orders", callback_data="OrdersExec"),
                    InlineKeyboardButton("🤖 BotTrader", callback_data="botrtrader"),
                ],
            ]
            menu_markup = InlineKeyboardMarkup(botones)

            await self.send_Telegram(
                texto="☰ Selecciona la categoría de mensajes que quieres recibir:",
                reply_markup=menu_markup,
            )

    # Aquí podrías iniciar/parar Telegram ------------------------------------------------------------------------
    async def toggle_telegram(self):
        def polling_callbackTelegram():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Construir app en el MISMO loop que hará polling
                self.telegram_app = ApplicationBuilder().token(self.TOKEN).build()

                self.telegram_app.add_handler(CommandHandler("menu", self.handle_menu))
                self.telegram_app.add_handler(CommandHandler("start", self.handle_segurity_message))
                self.telegram_app.add_handler(
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_segurity_message)
                )
                self.telegram_app.add_handler(CallbackQueryHandler(self.handle_callback))

                # Captura errores de red dentro del loop de polling (ConnectError, NetworkError, etc.)
                async def _telegram_error_handler(update, context):
                    self.logger.warning(f"Telegram network error (ignorado): {context.error}")

                self.telegram_app.add_error_handler(_telegram_error_handler)

                # Enviar mensaje de bienvenida antes de polling
                async def _send_welcome():
                    await self.telegram_app.initialize()
                    self.bot = self.telegram_app.bot
                    await self.send_Telegram(f"🏁 Bot interno iniciado session: {datetime.now()}")
                    await self.handle_menu()
                    await self.telegram_app.shutdown()

                loop.run_until_complete(_send_welcome())

                # run_polling en el mismo loop donde se creó la app
                loop.run_until_complete(
                    self.telegram_app.run_polling(
                        allowed_updates=["message", "callback_query"],
                        drop_pending_updates=True,
                    )
                )
            except Exception as e:
                self.logger.error(f"polling_callbackTelegram() error: {e}")
            finally:
                try:
                    loop.close()
                except:
                    pass

        try:
            if not self.estadoTelegram:
                self.estadoTelegram = True

                task_name = f"polling_callbackTelegram(On)"
                DataHub.procesos.append({"thread": {task_name: 1}})
                DataHub.manager_events.register_thread(
                    name=task_name,
                    target=polling_callbackTelegram,
                )

                self.logger.warning(f"Start: (toggle_telegram(On))")
        except Exception as e:
            self.logger.error(f"toggle_telegram(): {e}")
            traceback.print_exc()

    def _activar_telegram(self):
        self.exec_modulo_async(self.toggle_telegram())

    # envio de mensaje a Telegram
    async def send_Telegram(self, texto, hash_id=None, reply_markup=None):
        try:
            async with Bot(token=self.TOKEN) as bot:
                for CHAT_ID in self.userAuth:
                    if reply_markup is not None:
                        sent_message = await bot.send_message(
                            chat_id=CHAT_ID,
                            text=texto,
                            reply_markup=reply_markup,
                            parse_mode="Markdown",
                        )
                        await self._save_message(sent_message, CHAT_ID)
                        return

                    # si hash_id no es proporcionado, envía mensaje simple
                    elif hash_id is None:
                        sent_message = await bot.send_message(chat_id=CHAT_ID, text=texto, parse_mode="Markdown")
                        await self._save_message(sent_message, CHAT_ID)
                        return

                    # si hash_id es proporcionado, crea botones de aprobación/rechazo
                    elif hash_id is not None:
                        botones = [
                            [
                                InlineKeyboardButton("✅ Aprobar", callback_data=f"aprobar|{hash_id}"),
                                InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar|{hash_id}"),
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(botones)
                        sent_message = await bot.send_message(
                            chat_id=CHAT_ID,
                            text=texto,
                            reply_markup=reply_markup,
                            parse_mode="Markdown",
                        )
                        await self._save_message(sent_message, CHAT_ID, hash_id=hash_id)
                        return
        except Exception as e:
            self.logger.warning(f"send_Telegram(): {e}")

    def put_order(self, symbol, vehiculo, account, opt, qty, price, conid=None, hash_id=None, razon="Orden ejecutada"):
        try:
            Ticker = TickerInfo(account=account, vehiculo=vehiculo)
            _, tip, tim = Ticker.params_order(vehiculo=vehiculo, elementos=0)
            order = Ticker.format_orden(vehiculo, symbol, conid, tip, price, opt, tim, qty)
            trama = {
                "account": account,
                "vehiculo": vehiculo,
                "symbol": symbol,
                "pedido": order,
                "hash_id_Op": hash_id,
            }
            response = DataHub.QremoteOrder[vehiculo]._request(trama)
            if hash_id and response.get("status") in ("Submitted", "PreSubmitted", "FILLED"):
                self.RepositorioOportunidades.marcar_oportunidad(
                    hash_id, recomendado=1, estado="ejecutada", razon=razon
                )
            return response, symbol
        except Exception as e:
            self.logger.error(f"put_order(): {e}\n{traceback.format_exc()}")
            return {}, None

    def put_order_stockTelegram(self, op, ix):
        detalle = json.loads(op[ix.index("json_detalle")])
        last = op[ix.index("mrkprice")] or 0.0
        tipo_op = op[ix.index("tipo")]
        opt = "SELL" if tipo_op == "sell" else "BUY"
        qty = detalle.get("cantidad_sell", 0) if tipo_op == "sell" else detalle.get("cantidad_buy", 0)
        price_op = detalle.get("price_market") or 0.0
        prc = price_op if price_op > last else last
        return self.put_order(
            symbol=op[ix.index("symbol")],
            vehiculo=op[ix.index("vehiculo")],
            account=op[ix.index("account")],
            opt=opt,
            qty=qty,
            price=prc,
            conid=op[ix.index("conid")],
            hash_id=op[ix.index("hash_id")],
        )

    def put_order_cryptoTelegram(self, op, ix):
        detalle = json.loads(op[ix.index("json_detalle")])
        symbol = op[ix.index("symbol")]
        last = op[ix.index("mrkprice")] or 0.0
        tipo_op = op[ix.index("tipo")]
        opt = "SELL" if tipo_op == "sell" else "BUY"
        qty = detalle.get("cantidad_sell", 0) if tipo_op == "sell" else detalle.get("cantidad_buy", 0)
        price_op = detalle.get("price_market") or 0.0
        prc = price_op if price_op > last else last
        crypto, found = self.RepositorioOportunidades.select_otros_activos(symbol=symbol)
        conid = crypto[0]["idcrypto"] if found else None
        return self.put_order(
            symbol=symbol,
            vehiculo=op[ix.index("vehiculo")],
            account=op[ix.index("account")],
            opt=opt,
            qty=qty,
            price=prc,
            conid=conid,
            hash_id=op[ix.index("hash_id")],
        )

    # enlace con TickerInfo() para colocar orders
    def put_order_aprovate_telegram(self, hash_id):
        try:
            oportunidad, ix = self.RepositorioOportunidades.obtener_id_por_hash(hash_id=hash_id)
            if not oportunidad:
                return {}, None, None

            if oportunidad[ix.index("estado")] == "ejecutada":
                return {"status": "ya_ejecutada"}, oportunidad[ix.index("simbolo")], oportunidad[ix.index("vehiculo")]

            vehiculo = oportunidad[ix.index("vehiculo")]
            razon = "Aprobada desde Telegram"
            razon += "." if oportunidad[ix.index("origen")] == "system" else " (IA)"

            if vehiculo == "Stock":
                values, symbol = self.put_order_stockTelegram(oportunidad, ix)
            elif vehiculo == "Crypto":
                values, symbol = self.put_order_cryptoTelegram(oportunidad, ix)
            else:
                return {}, None, None

            if values.get("status") in ("Submitted", "PreSubmitted", "FILLED"):
                self.RepositorioOportunidades.marcar_oportunidad(
                    hash_id, recomendado=1, estado="ejecutada", razon=razon
                )

            return values, symbol, vehiculo
        except Exception as e:
            self.logger.error(f"put_order_aprovate_telegram(): {e}\n{traceback.format_exc()}")
            return {}, None, None

    # Maneja los callbacks de los botones de aprobación/rechazo
    async def handle_callback(self, update, context):
        try:

            # opciones de menu seleccionado
            query = update.callback_query
            await query.answer()

            accion, *args = query.data.split("|")

            # solicita put Order & wait response de ManagerOrderQueue
            if accion == "aprobar":
                await query.edit_message_reply_markup(reply_markup=None)
                response, symbol, vehiculo = self.put_order_aprovate_telegram(hash_id=args[0])

                if response.get("status") == "ya_ejecutada":
                    await query.edit_message_text(f"⚠️ {symbol}: orden ya ejecutada anteriormente.")
                elif response and response.get("status"):
                    status = response.get("status", "Pendiente")
                    price = response.get("price", 0)
                    message = f"✅ Oportunidad procesada: {status}\n"
                    message += f"Symbol {symbol}: @price {round(price, 4) if price else 0}"
                    await query.edit_message_text(message)
                else:
                    broker = "IB Gateway" if vehiculo == "Stock" else "Binance API"
                    message = f"⚠️ Sin servicio de broker.\n"
                    message += f"Symbol: {symbol or 'N/A'}\nVerifique conexión {broker}."
                    await query.edit_message_text(message)

            elif accion == "rechazar":
                self.RepositorioOportunidades.marcar_oportunidad(
                    args[0],
                    recomendado=-1,
                    estado="rechazada",
                    razon="Rechazada desde Telegram.",
                )
                await query.edit_message_text("❌ Oportunidad rechazada.")

            # Aquí podrías activar solo mensajes de venta
            elif accion == "menu_sell":
                await query.edit_message_text(
                    "⬇️🔴 Has seleccionado *Oportunidades de Ventas*.",
                    parse_mode="Markdown",
                )
                self.MostrarOpcionMenu_enTelegram = "Sell"

            elif accion == "menu_buy":
                await query.edit_message_text(
                    "⬆️🟢 Has seleccionado *Oportunidades de Compra*.",
                    parse_mode="Markdown",
                )
                self.MostrarOpcionMenu_enTelegram = "Buy"

            elif accion == "menu_top":
                self.MostrarOpcionMenu_enTelegram = "Top10"
                await query.edit_message_text(
                    "📊 Has seleccionado *TOP 10 Oportunidades* (5 Sell + 5 Buy).\nRecibirás las mejores para entrenar.",
                    parse_mode="Markdown",
                )
                # Enviar TOP 5 Sell + TOP 5 Buy para entrenamiento
                await self.send_top10_telegram(forzar=True)

            elif accion == "menu_reconnect":
                await query.edit_message_text("⚙️ Ajustes: próximamente más opciones.", parse_mode="Markdown")

            elif accion == "performan":
                await query.edit_message_text("🎯 Perfonance: Ganancias y Perdidas.", parse_mode="Markdown")

            elif accion == "OrdersExec":
                self.MostrarOpcionMenu_enTelegram = "ListOrder"

                # se pasa el chat que solicitó la lista (opcional)
                await self.list_orders_exec(chat_id=update.effective_chat.id)

            elif accion == "botrtrader":
                await self.list_positions_BotCrypto(chat_id=update.effective_chat.id)

        except Exception as e:
            self.logger.error(f"handle_callback(): {e}\n{traceback.format_exc()}")

    # delete message puntual
    async def _delete_message_hash(self, message):

        FileMessage = define_FileCache(name="telegram_message_ids.json")
        async with Bot(token=self.TOKEN) as bot:
            with open(FileMessage, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        # Solo borra del chat el mensajes anterior
                        if (
                            data.get("chat_id") == message.get("chat_id")
                            and data.get("hash_id") == message.get("hash_id")
                            and data.get("message_id") != message.get("message_id")
                        ):
                            await bot.delete_message(
                                chat_id=data.get("chat_id"),
                                message_id=data.get("message_id"),
                            )
                    except (json.JSONDecodeError, BadRequest):
                        continue

    # Path to JSON file for storing message IDs
    async def _save_message(self, sent_message, CHAT_ID, hash_id=None):
        try:
            if sent_message is None:
                return

            # Obtiene el message_id del mensaje enviado
            message_id = sent_message.message_id
            FileMessage = define_FileCache(name="telegram_message_ids.json")
            self.DeleteMessageHash = []

            # Guarda el chat_id y el message_id en el archivo JSON
            with open(FileMessage, "a") as f:

                # option para mensajes comunes
                if hash_id is None:
                    json.dump({"chat_id": int(CHAT_ID), "message_id": message_id}, f)
                    f.write("\n")

                # option para borrar oportunidad que se ha mejorado
                if hash_id is not None:

                    # salmacena hash:id y message_id que se preservan
                    message = {
                        "chat_id": int(CHAT_ID),
                        "message_id": message_id,
                        "hash_id": hash_id,
                    }
                    json.dump(message, f)
                    f.write("\n")

            # elimina mensaje previo
            if hash_id is not None:
                await self._delete_message_hash(message)
        except Exception as e:
            print(f"_save_message(): {e}")

    # Scrach message
    async def clear_bot_chat(self, CHAT_ID):
        try:
            # Lee los IDs de los mensajes desde el archivo
            self.SentMessage = []
            FileMessage = define_FileCache(name="telegram_message_ids.json")
            with open(FileMessage, "r") as f:
                for line in f:
                    try:
                        # Solo borra los mensajes de todos los usuarios
                        data = json.loads(line)

                        if data.get("chat_id") not in CHAT_ID:
                            self.SentMessage.append(data)

                        elif data.get("chat_id") in CHAT_ID:
                            await self.bot.delete_message(
                                chat_id=data.get("chat_id"),
                                message_id=data.get("message_id"),
                            )
                    except (json.JSONDecodeError, BadRequest):
                        continue

            # eof(): limpiar el archivo de IDs
            open(FileMessage, "w").close()

            # Guarda el chat_id y el message_id en el archivo JSON
            for data in self.SentMessage:

                with open(FileMessage, "a") as f:
                    json.dump(data, f)
                    f.write("\n")
        except (FileNotFoundError, Exception) as e:
            print(f"clear_bot_chat(): {e}")


# Main ChatBot
class Chatbot(tk.Toplevel, ClassAgenteIA, Telegram):
    def __init__(self, master=None, on_minimizar=None):
        super().__init__(master)
        ClassAgenteIA.__init__(self)
        Telegram.__init__(self)

        # colores
        self.bgcolor = "#1e1e2e"
        self.usercolor = "#cba6f7"
        self.botcolor = "#cdd6f4"
        self.fgcolor = "#cdd6f4"

        self.title("🤖 Asistente de Inversión")
        self.geometry("600x780+1200+100")
        self.configure(bg=self.bgcolor)
        self.resizable(True, True)
        self.attributes("-topmost", True)

        self.ultimo_envio = {}
        self.ultimo_envio_buy = {}
        self.logger = logging.getLogger("ClassChatbot")
        self.on_minimizar = on_minimizar

        # Accesos MySql
        self.RepositorioOportunidades = RepositorioOportunidadesBuySell()
        self.IAsell = ModeloOportunidadesSell()
        self.IAbuy = ModeloOportunidadesBuy()
        self.modelo_name = self.IAsell.modelo_name
        self.modelo_name_buy = self.IAbuy.modelo_name

        self.bot = None
        self.MessageTelegram = None
        self.counter = 0
        self.sell_enviados = {}
        self.buy_enviados = {}

        # ── BARRA ICONOS (top) ───────────────────────────────────────────────
        barra = tk.Frame(self, bg="#181825", height=40)
        barra.pack(fill=tk.X, side=tk.TOP)
        barra.pack_propagate(False)

        Imagen_tk = BDsystem.select_image(idd=333, size=(26, 26))
        self.BNews = tk.Button(
            barra,
            image=Imagen_tk,
            bg="#181825",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.ver_noticias,
        )
        self.BNews.imagen = Imagen_tk
        self.BNews.pack(side=tk.LEFT, padx=(10, 4), pady=6)

        Imagen_tk = BDsystem.select_image(idd=334, size=(26, 26))
        self.IA = tk.Button(barra, image=Imagen_tk, bg="#181825", relief=tk.FLAT)
        self.IA.imagen = Imagen_tk
        self.IA.pack(side=tk.LEFT, padx=4, pady=6)

        # referencia para compatibilidad con código existente
        self.iconos = barra
        self.chat = self

        # ── AREA CHAT ───────────────────────────────────────────────────────
        self.area_mensaje = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            bg="#181825",
            fg=self.fgcolor,
            font=("Segoe UI", 11),
            relief=tk.FLAT,
            padx=16,
            pady=12,
            selectbackground="#45475a",
        )
        self.area_mensaje.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 0))

        self.area_mensaje.tag_configure("usuario", foreground=self.usercolor, font=("Segoe UI", 11, "bold"))
        self.area_mensaje.tag_configure("asistente", foreground=self.botcolor, font=("Segoe UI", 11))
        self.area_mensaje.tag_configure("thinking", foreground="#6c7086", font=("Segoe UI", 11, "italic"))

        self.area_mensaje.insert(tk.END, "🤖  ¿En qué puedo ayudarte?\n\n", "asistente")
        self.area_mensaje.configure(state="disabled")

        # ── INPUT ───────────────────────────────────────────────────────────
        footer = tk.Frame(self, bg=self.bgcolor)
        footer.pack(fill=tk.X, padx=10, pady=10)

        self.entrada = tk.Entry(
            footer,
            font=("Segoe UI", 11),
            bg="#313244",
            fg="white",
            insertbackground="white",
            relief=tk.FLAT,
        )
        self.entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 8))
        self.entrada.bind("<Return>", self._enviar)

        tk.Button(
            footer,
            text="▶",
            bg="#cba6f7",
            fg="#1e1e2e",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            command=self._enviar,
            padx=10,
        ).pack(side=tk.LEFT)

        self.protocol("WM_DELETE_WINDOW", self._al_perder_foco)

        # variables de trabajo
        self.estadoTelegram = False
        self.estadoOportunidades = True
        self.telegram_app = None
        self.threadCall = None
        self.activaIA = True

        modelo = BDsystem.get_modelo_ia(modelo="modelo_sellv01")
        modelo_config = json.loads(modelo["paramts"].decode("utf-8"))
        self.umbral = modelo_config.get("umbral_sell", 0.50)
        self.umbralObserv = modelo_config.get("umbral_observacion", 0.35)

        self._activar_telegram()

    def _enviar(self, event=None):
        texto = self.entrada.get().strip()
        if not texto:
            return
        self._agregar_mensaje(f"👤  {texto}", tag="usuario")
        self._agregar_mensaje("⏳  Analizando...", tag="thinking")
        self.entrada.delete(0, tk.END)
        self.entrada.config(state="disabled")

        def _worker():
            try:
                contexto = self._build_contexto()
                respuesta = self._consultar_claude(texto, contexto)
            except Exception as e:
                respuesta = f"Error al consultar Claude: {e}"
            self.after(0, lambda: self._reemplazar_ultimo(f"🤖  {respuesta}", tag="asistente"))
            self.after(0, lambda: self.entrada.config(state="normal"))

        threading.Thread(target=_worker, daemon=True).start()

    def _agregar_mensaje(self, mensaje, tag="asistente"):
        self.area_mensaje.configure(state="normal")
        self.area_mensaje.insert(tk.END, mensaje + "\n\n", tag)
        self.area_mensaje.configure(state="disabled")
        self.area_mensaje.yview(tk.END)

    def _reemplazar_ultimo(self, nuevo, tag="asistente"):
        self.area_mensaje.configure(state="normal")
        self.area_mensaje.delete("end-3l linestart", "end-1l lineend+1c")
        self.area_mensaje.insert(tk.END, nuevo + "\n\n", tag)
        self.area_mensaje.configure(state="disabled")
        self.area_mensaje.yview(tk.END)

    def _build_contexto(self):
        posiciones = []
        for symbol, data in DataHub.info.copy().items():
            if not isinstance(data, dict):
                continue
            activos = data.get("activos", {})
            if not activos or not isinstance(activos, dict):
                continue
            precio = activos.get("currentPrice") or activos.get("regularMarketPrice", 0)
            nombre = activos.get("shortName", symbol)
            posiciones.append({"symbol": symbol, "nombre": nombre, "precio": precio})
        set_claude_contexto({"posiciones": posiciones[:20]})
        if not posiciones:
            return ""
        lineas = [f"{p['symbol']} ({p['nombre']}): ${p['precio']:.2f}" for p in posiciones[:20]]
        return "Posiciones en cartera:\n" + "\n".join(lineas)

    def ver_noticias(self):
        mensaje = "📰 Últimas noticias relacionadas con tu cartera..."
        self.enviar_mensaje(mensaje)

    def ver_consejos(self):
        mensaje = "💡 Consejo de hoy: Rebalancear tu cartera puede mejorar tu rendimiento."
        self.enviar_mensaje(mensaje)

        # muestra botón flotante

    def _al_perder_foco(self, event=None):
        self.withdraw()
        if self.on_minimizar:
            self.on_minimizar()

        # start agentes IA -------------------------------------------------------------------------------------------

    # read CSV : Oportunity
    @staticmethod
    def readCSV_sell(file=None, filtrar=True):
        try:
            vacio = pd.DataFrame()
            path = define_FileCache(name=f"{file}.CSV")

            # look read CSV sell
            with DataHub.lockCsvAi:
                df = pd.read_csv(path, header=0, sep=",", encoding="utf-8", index_col=False)
            if df.empty:
                return vacio

            df.columns = df.columns.str.strip()
            df.reset_index(drop=True, inplace=True)

            # Verificar que existen las columnas necesarias
            if "Opcion" in df.columns:
                df["Opcion"] = df["Opcion"].astype(str).str.strip()

            df = df.dropna(how="all", axis=1)

            # Si no queremos filtrar, devolver todo (para monitor)
            if not filtrar:
                return df

            # Filtrar recomendaciones válidas
            if "%Roi" in df.columns and "Profit" in df.columns:
                df_recom = df[(df["%Roi"] >= DataHub.MaxRoi) & (df["Profit"] >= DataHub.MinProfit)]
                return df_recom if not df_recom.empty else df
            return df
        except (EmptyDataError, FileNotFoundError):
            return vacio
        except Exception as e:
            print(f"readCSV_sell(): {e}")
            return vacio

    # read CSV : Oportunity Buy
    @staticmethod
    def readCSV_buy(file=None, filtrar=True):
        try:
            vacio = pd.DataFrame()
            path = define_FileCache(name=f"{file}.CSV")

            # look read CSV buy
            with DataHub.lockCsvAi:
                df = pd.read_csv(path, header=0, sep=",", encoding="utf-8", index_col=False)
            if df.empty:
                return vacio

            df.columns = df.columns.str.strip()
            df.reset_index(drop=True, inplace=True)

            # Verificar que existen las columnas necesarias
            if "vehiculo" in df.columns:
                df["vehiculo"] = df["vehiculo"].astype(str).str.strip()

            df = df.dropna(how="all", axis=1)

            # Si no queremos filtrar, devolver todo (para monitor)
            if not filtrar:
                return df

            # Filtrar recomendaciones válidas para buy
            # ganancia_precio >= MinGananciaPrecio (ej: 5%) y score >= MinScoreBuy (ej: 0.5)
            if "score" in df.columns and "ganancia_precio" in df.columns:
                df_recom = df[
                    (df["ganancia_precio"] >= DataHub.MinGananciaPrecio) & (df["score"] >= DataHub.MinScoreBuy)
                ]
                return df_recom if not df_recom.empty else df
            return df
        except (EmptyDataError, FileNotFoundError):
            return vacio
        except Exception as e:
            print(f"readCSV_buy(): {e}")
            return vacio

    # Aquí podrías iniciar/parar oportunidades chat---------------------------------------------------------------
    def toggle_oportunidades(self):
        try:
            # activa y desactiva mensajería Telegram
            if self.estadoOportunidades:
                self.estadoOportunidades = False
                print(f"Start: (toggle_oportunidades(Off))")

            if not self.estadoOportunidades:
                self.estadoOportunidades = True
                print(f"Start: (toggle_oportunidades(On))")
        except Exception as e:
            print(f"toggle_oportunidades(): {e}")

    # esto sí lanza la coroutine correctamente
    @staticmethod
    def exec_modulo_async(modulo):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(modulo)
            else:
                loop.run_until_complete(modulo)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(modulo)

    # Consultar y enviar por Telegram un resumen de órdenes ejecutadas.
    async def list_positions_BotCrypto(self, chat_id=None, limit=25):
        """
        Consultar y enviar por Telegram un resumen de posiciones activas BotCrypto.
        """
        try:
            info = DataHub.telegram_botcrypto
            if not info:
                await self.send_Telegram("ℹ️ BotCrypto no ha publicado datos aún.", None)
                return

            env = info.get("env", "?")
            trades = info.get("trades", 0)
            posiciones = info.get("posiciones", [])
            activas = [p for p in posiciones if p["position"] == "LONG"]
            waiting = [p for p in posiciones if p["position"] == "NONE"]

            if not activas:
                message = f"🤖 *BotTrader* ({env}) | Trades: {trades}\n"
                message += "ℹ️ Sin posiciones abiertas\n"
                if waiting:
                    message += f"\n⏳ *Esperando señal:* {', '.join(p['symbol'] for p in waiting)}"
                await self.send_Telegram(message, None)
                return

            lines = []
            total_pnl = 0.0
            for p in activas[:limit]:
                emoji = "🟢" if p["pnl_pct"] >= 0 else "🔴"
                lines.append(
                    f"{emoji}{p['symbol']:<8} {p['price']:>9.4f} "
                    f"{p['qty']:>8.2f} {p['pnl_pct']:>+6.2f}% ${p['pnl_usdt']:>+7.2f}"
                )
                total_pnl += p.get("pnl_usdt", 0)

            message = f"🤖 *BotTrader* ({env}) | Trades: {trades}\n"
            message += f"```\n"
            message += f"{'symbol':<9} {'price':>9} {'qty':>8} {'pnl%':>7} {'pnl$':>8}\n"
            message += f"{'-' * 54}\n"
            message += "\n".join(lines)
            message += f"\n{'-' * 54}\n"
            message += f"{'Total PnL':>37} ${total_pnl:>+7.2f}"
            message += "```"

            if waiting:
                message += f"\n⏳ *Esperando señal:* {', '.join(p['symbol'] for p in waiting)}"

            await self.send_Telegram(message, None)
        except Exception as e:
            self.logger.error(f"list_positions_BotCrypto(): {e}")

    # Consultar y enviar por Telegram un resumen de órdenes ejecutadas.
    async def list_orders_exec(self, chat_id=None, limit=25):
        """
        Consultar y enviar por Telegram un resumen de órdenes ejecutadas.
        Ajusta la consulta según la fuente real (BD, RepositorioOportunidades, MyOrders, QremoteOrder, etc.).
        """
        try:
            lista, ix = self.RepositorioOportunidades.select_order_trader(account="all")
            orders = []
            for i, trader in enumerate(lista):
                timestamp = trader[ix.index("stampPlace")]

                orders.append(
                    {
                        "timestamp": timestamp.strftime("%d-%b,%H%M%S"),
                        "symbol": trader[ix.index("symbol")],
                        "side": trader[ix.index("side")],
                        "quantity": trader[ix.index("quantity")],
                        "price": trader[ix.index("price")],
                        "status": trader[ix.index("status")][0:9],
                    }
                )

            # Si no hay órdenes, informar
            if not orders:
                await self.send_Telegram("ℹ️ No hay órdenes ejecutadas recientes.", None)
                return

            # Formatea la lista (ejemplo genérico)
            lines = []

            for o in orders[:limit]:
                if isinstance(o, dict):
                    lines.append(
                        f"{o.get('timestamp'):>14} {o.get('symbol'):>7} "
                        f"{o.get('side'):<4} {o.get('quantity'):>7} {o.get('price'):>7} {o.get('status'):>9}"
                    )

            message = f"🟢🔴 *Trader recent (-7 days):*\n"
            message += f"```\n"
            message += f"{'timestamp':<12} {'symbol':>7} {'side':>4} {'quantity':>7} {'price':>5} {'status':>7}\n"
            message += f"{'-' * 52}\n"
            message += "\n".join(lines)
            message += "```"

            await self.send_Telegram(message, None)
        except Exception as e:
            print(f"list_orders_exec(): {e}")

    async def send_top10_telegram(self, forzar=False):
        """
        Envía las TOP oportunidades (5 Sell + 5 Buy) a Telegram para entrenamiento.
        Envía cada oportunidad individual con botones de aprobar/rechazar.
        - forzar=True: envía siempre (usado al seleccionar menú)
        - forzar=False: solo envía si hay cambios significativos en el ranking
        """
        try:
            # Verificar si debe enviar (control de frecuencia)
            if not forzar:
                debe_enviar_sell, ranking_sell = self.Agente_message_Manager_Top10("sell")
                debe_enviar_buy, ranking_buy = self.Agente_message_Manager_Top10("buy")

                if not debe_enviar_sell and not debe_enviar_buy:
                    return

            # Obtener TOP 5 de cada tipo
            top_sell = self.get_top_sell(top=5)
            top_buy = self.get_top_buy(top=5)

            # Enviar oportunidades de SELL individualmente
            for row in top_sell:
                hash_id = self.RepositorioOportunidades.generar_hash_id(
                    row.get("account"),
                    row.get("Symbol"),
                    row.get("Opcion"),
                    row.get("Fecha"),
                    "sell",
                    "gain",
                    row.get("Recomendado"),
                )
                # Enviar con origen "top10" para identificar que viene del ranking
                await self.opportunity_handler_message_sell(hash_id=hash_id, row=row, origen="top10")

            # Enviar oportunidades de BUY individualmente
            for row in top_buy:
                hash_id = self.RepositorioOportunidades.generar_hash_id(
                    row.get("account"),
                    row.get("Symbol"),
                    row.get("vehiculo"),
                    row.get("Fecha"),
                    "buy",
                    "rebalanceo",
                    row.get("Recomendado"),
                )
                # Enviar con origen "top10" para identificar que viene del ranking
                await self.opportunity_handler_message_buy(hash_id=hash_id, row=row, origen="top10")

            # Actualizar registro de último envío
            self.ultimo_top10_sell = {
                "ranking": [r.get("Symbol", "") for r in top_sell],
                "time": datetime.now(),
            }
            self.ultimo_top10_buy = {
                "ranking": [r.get("Symbol", "") for r in top_buy],
                "time": datetime.now(),
            }

        except Exception as e:
            print(f"send_top10_telegram(): {e}")

    # Inicio del chatbot
    def run(self):
        def _log_schedule_status():
            """Loguea tabla de estado de agentes al arrancar agentesIA."""
            _AGENTES = {
                "Agente_MarketScreener": 86400,
                "Agente_InstitucionalScore": 86400,
                "Agente_ConsensoCache": 300,
                "Agente_EdgarFunds": 2592000,
                "Agente_FundFilings": 604800,
                "Agente_13FHoldings": 86400,
                "Agente_13FScores": 86400,
                "Agente_AuditPortfolio": 2592000,
                "Agente_LtvControl": 300,
                "Agente_StockBeta": 3600,
                "Agente_ExtractosWatcher": 3600,
                "Agente_ClasificadorETF": 604800,
                "Agente_SplitsControl": 86400,
            }

            def _fmt_intervalo(seg):
                if seg >= 86400:
                    return f"{seg // 86400}d"
                if seg >= 3600:
                    return f"{seg // 3600}h"
                return f"{seg // 60}m"

            sched = read_json_tmp("agents_schedule.json")
            ahora = time.time()
            sep = "─" * 100
            header = f"{'Agente':<28} {'Intervalo':<10} {'Último run':<22} {'Próximo run':<22} {'Estado'}"
            lineas = ["\nAgentesIA — schedule al arrancar:", sep, header, sep]
            ok, pendiente, vencido = 0, 0, 0

            for nombre, intervalo in _AGENTES.items():
                ts = sched.get(nombre, 0)
                if not ts:
                    estado = "⚠  NUNCA"
                    ultimo_str, proximo_str = "nunca", "al arrancar"
                    pendiente += 1
                else:
                    ultimo_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                    proximo_str = datetime.fromtimestamp(ts + intervalo).strftime("%Y-%m-%d %H:%M")
                    transcurrido = ahora - ts
                    if transcurrido >= intervalo * 1.5:
                        estado = "🔴 VENCIDO"
                        vencido += 1
                    elif transcurrido >= intervalo:
                        estado = "🟡 PENDIENTE"
                        pendiente += 1
                    else:
                        estado = "🟢 OK"
                        ok += 1
                lineas.append(
                    f"{nombre:<28} {_fmt_intervalo(intervalo):<10} {ultimo_str:<22} {proximo_str:<22} {estado}"
                )

            lineas.append(sep)
            lineas.append(f"Resumen: 🟢 OK={ok}  🟡 Pendiente={pendiente}  🔴 Vencido={vencido}")
            self.logger.critical("\n".join(lineas))

        def agentesIA():
            try:
                _log_schedule_status()
                while True:
                    # Agente for Sell
                    self.exec_modulo_async(self.Agente_ManagerSell())

                    # Agente for Buy
                    self.exec_modulo_async(self.Agente_ManagerBuy())

                    # Agente for Top 10 (monitorea cambios en ranking)
                    self.exec_modulo_async(self.Agente_ManagerTop10())

                    # Agente for Donloads filings
                    self.Agente_downloads_filings_EDGAR()

                    # Agente LTV Control — monitorea ratio deuda/colateral Binance (DRY RUN)
                    self.Agente_LtvControl()

                    # Agente Beta Portfolio Stock — actualiza BetaPortfolio cada hora
                    self.Agente_StockBeta()

                    # Agente Extractos Watcher — escanea tmp/extractos/ y carga PDFs bancarios
                    self.Agente_ExtractosWatcher()

                    # Agente Beta Portfolio Crypto — descarga yfinance y calcula beta vs BTC cada 6h
                    self.Agente_CryptoBeta()

                    # Agente Splits — detecta y aplica splits a booktrading diariamente
                    self.Agente_SplitsControl()

                    # Agente PerformaValidator — detecta precios yfinance corruptos y purga para regeneración
                    self.Agente_PerformaValidator()

                    # Agente for Preservation (defensivo estructural)  -- No activar esta en prueba
                    # self.exec_modulo_async(self.Agente_ManagerPreservation())

                    time.sleep(15)
                    self.counter += 1

                    DataHub.update_self_procesos(proces="thread", tarea=task_name, itera=self.counter)
            except Exception as e:
                print(f"agentesIA(): {e}")

        try:
            task_name = f"run_agentesIA(all)"
            DataHub.procesos.append({"thread": {task_name: 1}})
            DataHub.manager_events.register_thread(
                name=task_name,
                target=agentesIA,
            )

            DataHub.manager_events.register_thread(
                name="Agente_MarketScreener", target=self.Agente_MarketScreener, loop_sleep=300
            )
            DataHub.manager_events.register_thread(
                name="Agente_InstitucionalScore", target=self.Agente_InstitucionalScore, loop_sleep=300
            )
            DataHub.manager_events.register_thread(
                name="Agente_ConsensoCache", target=self.Agente_ConsensoCache, loop_sleep=300
            )
            DataHub.manager_events.register_thread(
                name="Agente_EdgarFunds", target=self.Agente_EdgarFunds, loop_sleep=300
            )
            DataHub.manager_events.register_thread(
                name="Agente_FundFilings", target=self.Agente_FundFilings, loop_sleep=300
            )
            DataHub.manager_events.register_thread(
                name="Agente_13FHoldings",
                target=self.Agente_13FHoldings,
                loop_sleep=300,
            )
            DataHub.manager_events.register_thread(
                name="Agente_13FScores", target=self.Agente_13FScores, loop_sleep=300
            )
            DataHub.manager_events.register_thread(
                name="Agente_AuditPortfolio",
                target=self.Agente_AuditPortfolio,
                loop_sleep=300,
            )
            DataHub.manager_events.register_thread(
                name="Agente_ClasificadorETF",
                target=self.Agente_ClasificadorETF,
                loop_sleep=300,
            )
        except Exception as error:
            print(f"agentesIA(): {error}")

    # ============================================================================
    # soporte para gestion de sell
    #
    # ============================================================================
    def message_format_sell(self, row, modo=None):
        try:

            mensaje = []
            symbol = row["Symbol"]
            option = row["Opcion"]
            price = f"{row['PriceMarket']:>12.4f}".strip()

            if modo == "system":
                mensaje = f"🔴 *System Sell: ${symbol} ({option};  @price: {price})*\n"
                mensaje += "```\n"

            elif modo == "top10":
                roi = (row.get("%Roi", 0) or 0) * 100
                mensaje = f"🔴📊 *TOP Sell: ${symbol} ({option};  @price: {price})*\n"
                mensaje += f"*ROI: {roi:.2f}%*\n"
                mensaje += "```\n"

            elif modo == "ia":
                confianza = row["confianza"]
                mensaje = f"🔴 *IA Sell: ${symbol} ({option};  @price: {price})*\n"
                mensaje += "```\n"

            mensaje += f"{'Métrica':<15} {'Valor':>12}\n"
            mensaje += f"{'-' * 37}\n"
            mensaje += f"{'Profit'         :<15} {row['Profit']:>12.2f}\n"
            mensaje += f"{'ROI (%)'        :<15} {row['%Roi'] * 100:>12.2f}\n"
            mensaje += f"{'for sell'       :<15} {row['CantidadSell']:>12.1f} de {row['Disponible']:>12.1f}\n"
            mensaje += f"{'CostoAcum'      :<15} {row['CostoCum']:>12.2f}\n"
            mensaje += f"{'Prec. posVenta' :<15} {row['PosAvgCost']:>12.4f}\n"
            mensaje += f"{'Pos. posVenta'  :<15} {row['PosPosition']:>12.4f}\n"
            mensaje += f"{'CostoB posVenta':<15} {row['PosCostobase']:>12.2f}\n"
            mensaje += f"{'Valoracion'         :<18} {""}\n"

            if modo == "ia":
                mensaje += f"{'-' * 37}\n"
                mensaje += f"{'Confianza IA'   :<15} {confianza:>12.1%}\n"

            tag, suma = self._consenso_info(symbol)
            if tag:
                mensaje += f"{'-' * 37}\n"
                mensaje += f"{'Consenso':<15} {tag:>12} ({suma:+d}/6)\n"

            mensaje += "```"

            return mensaje
        except Exception as e:
            print(f"message_format_sell(): {e}")

    async def opportunity_handler_message_sell(self, hash_id, row, origen="system"):
        try:
            # Para top10: siempre enviar (son los mejores para entrenar)
            # Para otros: filtrar mensajes repetidos o sin mejora
            if origen != "top10" and not self.Agente_message_Manager_sell(row):
                return

            # Marcar como enviado y da formato al mensaje
            self.sell_enviados.update({hash_id: row})
            message = self.message_format_sell(row, modo=origen)

            # send a Telegram si esta activo
            if self.estadoTelegram:
                await self.send_Telegram(message, hash_id)

            # send al chat si esta activo
            if self.estadoOportunidades:
                self._agregar_mensaje(message)
        except Exception as e:
            print(f"opportunity_handler_message_sell(): {e}")

    # maneja las oportunidades hash_id e insert de oportunidades en función del origen
    async def oportunity_handler_sell(self, row, origen="system"):
        try:
            insert = False
            hash_id = self.RepositorioOportunidades.generar_hash_id(
                row.get("account"),
                row.get("Symbol"),
                row.get("Opcion"),
                row.get("Fecha"),
                "sell",
                "gain",
                row.get("Recomendado"),
            )

            # válida los mensajes ya enviados o que no tenga el tope Minimo de Profit
            if hash_id in self.sell_enviados.keys():

                # update RepositorioOportunidadescon nuevos Sell
                insert = self.RepositorioOportunidades.actualizar_oportunidad(
                    hash_id=hash_id,
                    estado="pendiente",
                    origen=self.modelo_name,
                    row=row,
                )

                insert = True

            # inserta Oportunidad de venta
            elif hash_id not in self.sell_enviados.keys():

                # Verifica  y actuliza hash_id y fecha de oportinidad si existe
                existe = self.RepositorioOportunidades.actualizar_oportunidad(
                    hash_id=None,
                    estado="pendiente",
                    origen=self.modelo_name,
                    tipo="sell",
                    subtipo="gain",
                    row=row,
                )
                # en casos de existir, elimina hash_id anterior
                if existe:
                    self.sell_enviados.pop(hash_id, None)

                # en casos de no existente, inserta nueva oportunidad
                if not existe:
                    Worigen = origen if origen == "system" else self.modelo_name
                    insert = self.RepositorioOportunidades.insertar_sell(
                        row=row,
                        tipo="sell",
                        subtipo="gain",
                        origen=Worigen,
                        tolerancia_roi=DataHub.Toleranciasell,
                    )
                # marca hash_id como enviada
                self.sell_enviados.update({hash_id: row})

            # si insert es True, significa que se insertó correctamente
            if insert:
                # Verifica que este TRUE mostrar las ventas
                if self.MostrarOpcionMenu_enTelegram == "Sell":
                    await self.opportunity_handler_message_sell(hash_id=hash_id, row=row, origen=origen)
        except Exception as e:
            print(f"opportunity_handler(): {e}")

    # Obtener oportunidades desde modelo IA
    async def evaluar_oportunidades_sell_con_IA(self, df_sell=None, umbral_venta=0.65, umbral_observacion=0.35):
        """
        Sistema de dos umbrales:
        - confianza >= umbral_venta (0.65): Enviar a Telegram para vender
        - umbral_observacion <= confianza < umbral_venta (0.35-0.65): En observación
        - confianza < umbral_observacion (0.35): Ignorar
        """

        def filtrar_por_confianza(df_merged, umbral_min, umbral_max=None, estado=None):
            """Filtra oportunidades por rango de confianza usando merge de pandas."""
            if umbral_max is None:
                # Solo umbral mínimo (aprobadas)
                df_filtrado = df_merged[df_merged["confianza"] >= umbral_min].copy()
                df_filtrado["Comentarios"] = df_filtrado["confianza"].apply(
                    lambda c: f"Oportunity sent by Sell IA Model, confianza {c:.2f}"
                )
            else:
                # Rango de umbrales (observación)
                df_filtrado = df_merged[
                    (df_merged["confianza"] >= umbral_min) & (df_merged["confianza"] < umbral_max)
                ].copy()
                if estado:
                    df_filtrado["estado_ia"] = estado
            return df_filtrado

        try:
            # Cargar modelo
            self.IAsell.load_modelo(self.modelo_name)

            # Sin modelo: enviar todas las oportunidades para etiquetar y ganar experiencia
            if self.IAsell.modelo is None:
                self.logger.info("evaluar_oportunidades_sell_con_IA(): Sin modelo, enviando para etiquetado")
                for _, row in df_sell.iterrows():
                    await self.oportunity_handler_sell(row=row, origen="system")
                return

            # Generar hash_id para cada fila
            df_sell["hash_id"] = df_sell.apply(
                lambda row: self.RepositorioOportunidades.generar_hash_id(
                    row.get("account"),
                    row.get("Symbol"),
                    row.get("Opcion"),
                    row.get("Fecha"),
                    "sell",
                    "gain",
                    row.get("Recomendado"),
                ),
                axis=1,
            )

            # Renombrar columnas para compatibilidad
            df_in = df_sell.copy()
            df_in = df_in.rename(columns=DataHub.SellCsvJsonDcolumnas)

            # Aplicar predicción IA
            df = self.IAsell.aplanar_datos_tecnicos(df_in)
            if df is None or df.empty:
                self.logger.warning("evaluar_oportunidades_sell_con_IA(): df aplanado vacío")
                return

            resultado = self.IAsell.predecir_modelo(df)
            if resultado is None or resultado.empty:
                self.logger.warning("evaluar_oportunidades_sell_con_IA(): resultado predicción vacío")
                return

            # Merge por hash_id (O(n) en vez de O(n²))
            df_merged = df_sell.merge(
                resultado[["hash_id", "confianza", "clasificacion"]],
                on="hash_id",
                how="inner",
            )

            # 1. Aprobadas para venta (confianza >= umbral_venta)
            aprobadas = filtrar_por_confianza(df_merged, umbral_min=umbral_venta)

            # 2. En observación (umbral_observacion <= confianza < umbral_venta)
            # observacion = filtrar_por_confianza(
            #     df_merged, umbral_min=umbral_observacion, umbral_max=umbral_venta, estado="observacion"
            # )

            # Procesar aprobadas
            for _, row in aprobadas.iterrows():
                await self.oportunity_handler_sell(row=row, origen="ia")
        except Exception as e:
            self.logger.error(f"evaluar_oportunidades_sell_con_IA(): {e}")
            traceback.print_exc()

            # Filtrar por confianza mínima
            # aprobadas = resultado[resultado["confianza"] >= umbral].copy()

    def get_top_sell(self, top=5) -> list:
        """
        Obtiene las TOP 10 oportunidades de venta ordenadas por ROI.
        Criterio: Mayor ROI indica mejor momento para vender.
        Retorna lista de diccionarios con las mejores oportunidades.
        """
        try:
            if not self.sell_enviados:
                return []

            # Convertir a lista y ordenar por ROI descendente
            oportunidades = list(self.sell_enviados.values())

            # Ordenar por %Roi (mayor primero)
            oportunidades_ordenadas = sorted(
                oportunidades,
                key=lambda x: (x.get("%Roi", 0) or 0, x.get("Profit", 0) or 0),
                reverse=True,
            )

            return oportunidades_ordenadas[:top]
        except Exception as e:
            print(f"get_top_sell(): {e}")
            return []

    # ============================================================================
    # soporte para gestion de buy
    #
    # ============================================================================
    def message_format_buy(self, row, modo=None):
        try:
            symbol = row.get("Symbol", "")
            vehiculo = row.get("vehiculo", "")
            last = row.get("last", 0)

            if modo == "system":
                mensaje = f"🟢 *System Buy: ${symbol} ({vehiculo};  @price: {last:.4f})*\n"
                mensaje += "```\n"
            elif modo == "top10":
                score = row.get("score", 0) or 0
                gap = (row.get("ganancia_precio", 0) or 0) * 100
                mensaje = f"🟢📊 *TOP Buy: ${symbol} ({vehiculo};  @price: {last:.4f})*\n"
                mensaje += f"*Score: {score:.1f} | Gap: {gap:.2f}%*\n"
                mensaje += "```\n"
            elif modo == "ia":
                confianza = row.get("confianza", 0)
                mensaje = f"🟢 *IA Buy: ${symbol} ({vehiculo};  @price: {last:.4f})*\n"
                mensaje += "```\n"

            mensaje += f"{'Métrica':<18} {'Valor':>12}\n"
            mensaje += f"{'-' * 37}\n"
            mensaje += f"{'Ganancia Precio'  :<18} {row.get('ganancia_precio', 0):>12.2%}\n"
            mensaje += f"{'Ganancia Inv.'    :<18} {row.get('ganancia_inversion', 0):>12.2f}\n"
            mensaje += f"{'Dividend Yield'   :<18} {row.get('dividend_yield', 0):>12.2%}\n"
            mensaje += f"{'Monto Invertir'   :<18} {row.get('pinvertir', 0):>12.2f}\n"
            mensaje += f"{'Cantidad Buy'     :<18} {row.get('cantidad_buy', 0):>12.1f}\n"
            mensaje += f"{'Prec. preBuy'     :<18} {row.get('avgcost', 0):>12.4f}\n"
            mensaje += f"{'Prec. posBuy'     :<18} {row.get('avgcost_post', 0):>12.4f}\n"
            mensaje += f"{'Objetivo'         :<18} {row.get('objetivo', 0):>12.4f}\n"
            mensaje += f"{'Valoracion'       :<18} {""}\n"

            if modo == "ia":
                mensaje += f"{'-' * 37}\n"
                mensaje += f"{'Confianza IA'     :<18} {confianza:>12.1%}\n"

            tag, suma = self._consenso_info(symbol)
            if tag:
                mensaje += f"{'-' * 37}\n"
                mensaje += f"{'Consenso':<18} {tag:>12} ({suma:+d}/6)\n"

            mensaje += "```"
            return mensaje
        except Exception as e:
            self.logger.error(f"message_format_buy(): {e}")

    async def opportunity_handler_message_buy(self, hash_id, row, origen="system"):
        try:
            # Para top10: siempre enviar (son los mejores para entrenar)
            # Para otros: verificar control de frecuencia y mejora de score
            if origen != "top10" and not self.Agente_message_Manager_Buy(row):
                return

            # Marcar como enviado y da formato al mensaje
            self.buy_enviados.update({hash_id: row})
            message = self.message_format_buy(row, modo=origen)

            # Send a Telegram si esta activo
            if self.estadoTelegram:
                await self.send_Telegram(message, hash_id)

            # Send al chat si esta activo
            if self.estadoOportunidades:
                self._agregar_mensaje(message)
        except Exception as e:
            self.logger.error(f"opportunity_handler_message_buy(): {e}")

    # Handler para oportunidades de compra
    async def oportunity_handler_buy(self, row, origen="system"):
        try:
            insert = False
            hash_id = self.RepositorioOportunidades.generar_hash_id(
                row.get("account"),
                row.get("Symbol"),
                row.get("vehiculo"),
                row.get("Fecha"),
                "buy",
                "rebalanceo",
                row.get("Recomendado"),
            )

            # Válida los mensajes ya enviados
            if hash_id in self.buy_enviados.keys():
                # Update RepositorioOportunidades con nuevos Buy
                insert = self.RepositorioOportunidades.actualizar_oportunidad_buy(
                    hash_id=hash_id,
                    estado="pendiente",
                    origen=self.modelo_name_buy,
                    row=row,
                )
                insert = True

            # Inserta Oportunidad de compra
            elif hash_id not in self.buy_enviados.keys():
                # Verifica y actualiza hash_id y fecha de oportunidad si existe
                existe = self.RepositorioOportunidades.actualizar_oportunidad_buy(
                    hash_id=None,
                    estado="pendiente",
                    origen=self.modelo_name_buy,
                    tipo="buy",
                    subtipo="rebalanceo",
                    row=row,
                )
                # En caso de existir, elimina hash_id anterior
                if existe:
                    self.buy_enviados.pop(hash_id, None)

                # En caso de no existente, inserta nueva oportunidad
                if not existe:
                    Worigen = origen if origen == "system" else self.modelo_name_buy
                    insert = self.RepositorioOportunidades.insertar_buy(
                        row=row,
                        tipo="buy",
                        subtipo="rebalanceo",
                        origen=Worigen,
                    )
                # Marca hash_id como enviada
                self.buy_enviados.update({hash_id: row})

            # Si insert es True, significa que se insertó correctamente
            if insert:
                # Verifica que esté TRUE mostrar las compras
                if self.MostrarOpcionMenu_enTelegram == "Buy":
                    await self.opportunity_handler_message_buy(hash_id=hash_id, row=row, origen=origen)
        except Exception as e:
            self.logger.error(f"oportunity_handler_buy(): {e}")

    # Obtener oportunidades de compra desde modelo IA
    async def evaluar_oportunidades_buy_con_IA(self, df_buy=None, umbral_compra=0.65, umbral_observacion=0.35):
        """
        Sistema de dos umbrales para Buy:
        - confianza >= umbral_compra (0.65): Enviar a Telegram para comprar
        - umbral_observacion <= confianza < umbral_compra: En observación
        - confianza < umbral_observacion: Ignorar
        """

        def filtrar_por_confianza(df_merged, umbral_min, umbral_max=None, estado=None):
            """Filtra oportunidades por rango de confianza usando merge de pandas."""
            if umbral_max is None:
                df_filtrado = df_merged[df_merged["confianza"] >= umbral_min].copy()
                df_filtrado["Comentarios"] = df_filtrado["confianza"].apply(
                    lambda c: f"Oportunity sent by Buy IA Model, confianza {c:.2f}"
                )
            else:
                df_filtrado = df_merged[
                    (df_merged["confianza"] >= umbral_min) & (df_merged["confianza"] < umbral_max)
                ].copy()
                if estado:
                    df_filtrado["estado_ia"] = estado
            return df_filtrado

        try:
            # Cargar modelo
            self.IAbuy.load_modelo(self.modelo_name_buy)

            # Sin modelo: enviar todas las oportunidades para etiquetar y ganar experiencia
            if self.IAbuy.modelo is None:
                self.logger.info("evaluar_oportunidades_buy_con_IA(): Sin modelo, enviando para etiquetado")
                for _, row in df_buy.iterrows():
                    await self.oportunity_handler_buy(row=row, origen="system")
                return

            # Generar hash_id para cada fila
            df_buy["hash_id"] = df_buy.apply(
                lambda row: self.RepositorioOportunidades.generar_hash_id(
                    row.get("account"),
                    row.get("Symbol"),
                    row.get("vehiculo"),
                    row.get("Fecha"),
                    "buy",
                    "rebalanceo",
                    row.get("Recomendado"),
                ),
                axis=1,
            )

            # Renombrar columnas para compatibilidad
            df_in = df_buy.copy()
            df_in = df_in.rename(columns=DataHub.BuyCsvJsonDcolumnas)

            # Aplicar predicción IA
            df = self.IAbuy.aplanar_datos_tecnicos(df_in)
            if df is None or df.empty:
                self.logger.warning("evaluar_oportunidades_buy_con_IA(): df aplanado vacío")
                return

            resultado = self.IAbuy.predecir_modelo(df)
            if resultado is None or resultado.empty:
                self.logger.warning("evaluar_oportunidades_buy_con_IA(): resultado predicción vacío")
                return

            # Merge por hash_id
            df_merged = df_buy.merge(
                resultado[["hash_id", "confianza", "clasificacion"]],
                on="hash_id",
                how="inner",
            )

            # Aprobadas para compra (confianza >= umbral_compra)
            aprobadas = filtrar_por_confianza(df_merged, umbral_min=umbral_compra)

            # Procesar aprobadas
            for _, row in aprobadas.iterrows():
                await self.oportunity_handler_buy(row=row, origen="ia")
        except Exception as e:
            self.logger.error(f"evaluar_oportunidades_buy_con_IA(): {e}")
            traceback.print_exc()

    # obtenen muestra para entrenamiento del modelo de sell
    def obtener_dataframe_entrenamiento_IA(self, tipo="sell", return_stats=False):
        """
        Extrae las oportunidades con decisión tomada y devuelve un DataFrame
        con todos los campos necesarios para entrenamiento IA.

        Criterio de filtrado:
        - Solo oportunidades con recomendado = 1 (aprobada) o -1 (rechazada)
        - Excluye automáticamente pendientes (recomendado = 0 o NULL)
        - Independiente del estado (ejecutada, rechazada, no repetir, etc.)
        - El campo 'recomendado' es el indicador definitivo de decisión humana

        Args:
            tipo: Tipo de oportunidad ("sell" o "buy")
            return_stats: Si True, retorna (df, errores_parseo)

        Returns:
            DataFrame con datos de entrenamiento, o (DataFrame, dict) si return_stats=True
        """
        try:
            # Obtener todas las oportunidades del tipo (sin filtro de estado)
            # Filtraremos solo por recomendado in [1, -1] que es el indicador real de decisión
            oportunidades, ix = self.RepositorioOportunidades.obtener_por_tipo(tipo=tipo)

            registros = []
            errores_parseo = {
                "sin_decision": 0,
                "json_invalido": 0,
                "detalle_no_dict": 0,
                "indicadores_no_dict": 0,
                "otros": 0,
            }

            for op in oportunidades:
                try:
                    # Filtro único: verificar decisión tomada (recomendado = 1 o -1)
                    # Esto excluye automáticamente pendientes (recomendado = 0 o NULL)
                    if op[ix.index("recomendado")] not in [1, -1]:
                        errores_parseo["sin_decision"] += 1
                        continue

                    # Parsear json_detalle (maneja doble/triple codificación)
                    json_detalle_raw = op[ix.index("json_detalle")]
                    try:
                        if isinstance(json_detalle_raw, str):
                            detalle = json.loads(json_detalle_raw)
                            if isinstance(detalle, str):
                                detalle = json.loads(detalle)
                        else:
                            detalle = json_detalle_raw
                    except json.JSONDecodeError:
                        errores_parseo["json_invalido"] += 1
                        continue

                    if not isinstance(detalle, dict):
                        errores_parseo["detalle_no_dict"] += 1
                        continue

                    # Parsear indicadores (puede ser string con triple codificación)
                    indicadores_raw = detalle.get("indicadores", {})
                    if isinstance(indicadores_raw, str):
                        try:
                            indicadores = json.loads(indicadores_raw)
                        except json.JSONDecodeError:
                            errores_parseo["indicadores_no_dict"] += 1
                            continue
                    else:
                        indicadores = indicadores_raw

                    if not isinstance(indicadores, dict):
                        errores_parseo["indicadores_no_dict"] += 1
                        continue

                    # Extraer datos de indicadores diarios (preferencia)
                    indicadores_diaria = (
                        indicadores.get("diaria", {}) if isinstance(indicadores.get("diaria"), dict) else {}
                    )

                    # Extraer EMAs largos y cortos
                    emas_largos = (
                        indicadores_diaria.get("ema(20,50,100,200)", {})
                        if isinstance(indicadores_diaria.get("ema(20,50,100,200)"), dict)
                        else {}
                    )
                    emas_cortos = (
                        indicadores_diaria.get("ema(09,21,055,144)", {})
                        if isinstance(indicadores_diaria.get("ema(09,21,055,144)"), dict)
                        else {}
                    )
                    fibo = (
                        indicadores_diaria.get("retroceso_fibonacci", {})
                        if isinstance(indicadores_diaria.get("retroceso_fibonacci"), dict)
                        else {}
                    )

                    # Nombres con sufijo _d para compatibilidad con cargar_datos() en Class_IA_modelos
                    fila = {
                        "symbol": op[ix.index("symbol")],
                        "recomendado": op[ix.index("recomendado")],
                        "profit": detalle.get("profit"),
                        "roi": detalle.get("roi"),
                        # Indicadores diarios con sufijo _d
                        "rsi_d": indicadores_diaria.get("rsi"),
                        "macd_d": indicadores_diaria.get("macd"),
                        "Close_d": indicadores_diaria.get("precio_calculo"),
                        "EMA020_d": emas_largos.get("EMA020"),
                        "EMA050_d": emas_largos.get("EMA050"),
                        "EMA100_d": emas_largos.get("EMA100"),
                        "EMA200_d": emas_largos.get("EMA200"),
                        "EMA009_d": emas_cortos.get("EMA009"),
                        "EMA021_d": emas_cortos.get("EMA021"),
                        "EMA055_d": emas_cortos.get("EMA055"),
                        "EMA144_d": emas_cortos.get("EMA144"),
                        "fibo_longico_d": fibo.get("longico"),
                        # NOTA: fibo_alcista y fibo_bajista son dicts con niveles (23.6%, 38.2%, etc.)
                        # Por ahora los omitimos para evitar error "float() argument must be a string or real number, not 'dict'"
                    }
                    registros.append(fila)

                except Exception as e:
                    errores_parseo["otros"] += 1
                    continue

            df = pd.DataFrame(registros)

            if return_stats:
                return df, errores_parseo
            return df
        except Exception as e:
            print(f"obtener_dataframe_entrenamiento_IA(): {e}")
            if return_stats:
                return pd.DataFrame(), {"error_general": str(e)}
            return pd.DataFrame()

    def get_top_buy(self, top=5) -> list:
        """
        Obtiene las TOP 10 oportunidades de compra ordenadas por score y ganancia_precio.
        Criterio: Mayor score indica mejor oportunidad de rebalanceo.
                  Mayor ganancia_precio indica mejor precio respecto al objetivo.
        Retorna lista de diccionarios con las mejores oportunidades.
        """
        try:
            if not self.buy_enviados:
                return []

            # Convertir a lista y ordenar por score + ganancia_precio
            oportunidades = list(self.buy_enviados.values())

            # Ordenar por score (mayor primero), luego por ganancia_precio
            oportunidades_ordenadas = sorted(
                oportunidades,
                key=lambda x: (
                    x.get("score", 0) or 0,
                    x.get("ganancia_precio", 0) or 0,
                ),
                reverse=True,
            )

            return oportunidades_ordenadas[:top]
        except Exception as e:
            print(f"get_top_buy(): {e}")
            return []


# Inicio chatbot ----------------------------------------------------------------------------------------------------------------
class BotonFlotante(tk.Toplevel):
    def __init__(self, master=None, on_click=None):
        super().__init__(master)
        self.bgcolor = "DarkCyan"
        self.geometry("80x80+1830+945")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.70)
        self.configure(bg=self.bgcolor)

        self.on_click = on_click

        # chatbot y/o asistente ---------------------------------------------------------------------------------------
        Imagen_tk = BDsystem.select_image(idd=330, size=(84, 84))

        boton = tk.Button(
            self,
            image=Imagen_tk,
            bg=self.bgcolor,
            fg="blue",
            font=("Segoe UI", 43),
            bd=0,
            relief="flat",
            activebackground="#555",
            command=self.activar_chatbot,
        )
        boton.image = Imagen_tk
        boton.pack(fill=tk.BOTH, expand=True)

    def activar_chatbot(self):
        self.withdraw()
        if self.on_click:
            self.on_click()


# 🎯 Integración ---------------------------------------------------------------------------------------------------------------
def AsistenteChatbot(root=None):
    def mostrar_asistente():
        bot.deiconify()

    def mostrar_boton():
        boton_flotante.deiconify()

    try:
        bot = Chatbot(master=root, on_minimizar=mostrar_boton)
        boton_flotante = BotonFlotante(root, on_click=mostrar_asistente)
        bot.run()

        # oculta chat al inicio. Solo se activa desde el boton flotante
        bot._al_perder_foco()

    except Exception as error:
        print(f"AsistenteChatbot(): {error}")


def app():
    master = tk.Tk()
    master.withdraw()
    AsistenteChatbot(root=master)
    master.mainloop()


if __name__ == "__main__":
    app()
