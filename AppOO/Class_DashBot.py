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
    DiariaCNV,
    IPerformance,
    PlanInversion,
    MarketScreen,
    IaTraceScreen,
)
from Class_customer import DataHub, TickerInfo
from Class_BrowserBridge import set_claude_contexto
from Class_IA_modelos import ModeloOportunidadesSell, ModeloOportunidadesBuy
from Modulos_Utilitarios import (
    define_FileCache,
    read_json_tmp,
    write_json_tmp,
    AGENTES_SCHEDULE,
    wait_rate,
    track_claude_usage,
    load_vehiculo_params,
)
from Class_AgentManager import AgentManager
from ConvergIA.Scanner_Sentimiento import scan_sentimiento
from ConvergIA.Interprete_Sentimiento import interpretar_sentimiento


# Admistrador de Agentes IA
class ClassAgenteIA:
    def __init__(self):

        # Obiene valores de session Stock
        self.vehiculo = "Stock"
        self.positions = []
        self.NotFound = []
        self.PlanInversion = PlanInversion()
        self.Market = MarketScreen()
        self.IaTrace = IaTraceScreen()
        self.sesion = self.PlanInversion.get_sesion_by_vehiculo(self.vehiculo)
        self.account = self.sesion["idcuenta"]
        _sesion_crypto = self.PlanInversion.get_sesion_by_vehiculo("Crypto")
        self.account_crypto = _sesion_crypto.get("idcuenta", "B0000001") if _sesion_crypto else "B0000001"

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
        self.preservation_config = {}  # {vehiculo: sub-dict "preservation"} — extraído de _params_cache
        self.preservation_last_run = {}  # {vehiculo: datetime} — última evaluación por vehículo
        self._params_cache = {}  # {vehiculo: full parsed parameters dict} — compartido entre agentes
        self._preservation_dry_run = False
        # Cargar estado persistido (sobrevive reinicios — stop_prev correcto sin depender de IB)
        _saved = read_json_tmp("preservation_state.json")
        self.preservation_state = {
            k: {
                **v,
                "last_check": (
                    datetime.fromisoformat(v["last_check"])
                    if isinstance(v.get("last_check"), str)
                    else v.get("last_check")
                ),
            }
            for k, v in _saved.items()
            if not k.startswith("_last_run_")
        }
        # Restaurar last_run por vehículo — evita re-ejecución al reabrir Chatbot
        for _veh in ("Stock", "Crypto"):
            _lr = _saved.get(f"_last_run_{_veh}")
            if _lr:
                try:
                    self.preservation_last_run[_veh] = datetime.fromisoformat(_lr)
                except Exception:
                    pass

        # Estado GainsCapture — escalonamiento de salida para activos volátiles (categoriaActivo='N')
        _gc_saved = read_json_tmp("gains_capture_state.json")
        self.gains_capture_state = {k: v for k, v in _gc_saved.items() if not k.startswith("_")}
        _gc_params = self._load_params("Stock") or {}
        DataHub.gains_capture_modo = _gc_params.get("gains_capture", {}).get("modo", "automatico")
        DataHub.modo_operacion = _gc_params.get("agente_ia", {}).get("modo", "OBSERVACION")

        # Logger dedicado a preservation — escribe a logs/preservation_diag.log
        self._preservation_logger = logging.getLogger("Preservation")
        if not self._preservation_logger.handlers:
            _tmp = os.environ.get("APPOO_TMP") or os.path.join(os.getcwd(), "tmp")
            _logs = os.path.normpath(os.path.join(_tmp, "..", "logs"))
            os.makedirs(_logs, exist_ok=True)
            _fh = logging.FileHandler(os.path.join(_logs, "preservation_diag.log"), encoding="utf-8")
            _fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self._preservation_logger.addHandler(_fh)
            self._preservation_logger.setLevel(logging.DEBUG)
            self._preservation_logger.propagate = False

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

        # Gate Consenso: solo aplica si el modelo IA no tiene confianza suficiente.
        # Si confianza >= umbral, el modelo ya evaluó los fundamentos → bypass.
        confianza = row.get("confianza") or 0
        if confianza < self.Sellumbral:
            tag = self._consenso_tag(symbol)
            if tag and tag not in self._SELL_TAGS and roi < DataHub.MaxRoi:
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
            df_sell = self.readCSV_sell(file="csv_datosIA_sell", filtrar=False)

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
            df_buy = self.readCSV_buy(file="csv_datosIA_buy", filtrar=False)

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

    def _call_claude(self, prompt: str, api_key: str, session_key: str, max_tokens: int = 500, timeout: int = 20):
        """POST a Claude API, retorna primer bloque JSON parseado o None."""
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": max_tokens,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=timeout,
            )
            if not resp.ok:
                self.logger.error(f"_call_claude({session_key}): HTTP {resp.status_code} — {resp.text[:200]}")
                return None
            usage = resp.json().get("usage", {})
            track_claude_usage(session_key, usage.get("input_tokens", 0), usage.get("output_tokens", 0))
            text = resp.json()["content"][0]["text"].strip()
            start, end = text.find("{"), text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception as e:
            self.logger.error(f"_call_claude({session_key}): {e}")
        return None

    def _consultar_claude(self, mensaje_usuario, contexto="", messages=None):
        """Llamada a Claude API. Si messages se provee, usa conversación multi-turno con historial."""
        sesion_claude = BDsystem.get_sesion_by_vehiculo("ClaudeAPIC")
        api_key = sesion_claude["userapi"].decode("utf-8")

        sistema = (
            "Sos un asistente de inversión integrado en una app de trading. "
            "Respondé en español, de forma concisa y directa. "
            "Tenés acceso al estado actual de la cartera del usuario."
        )
        if contexto:
            sistema += f"\n\nContexto actual:\n{contexto}"

        msgs = messages[-20:] if messages else [{"role": "user", "content": mensaje_usuario}]
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
                "messages": msgs,
            },
            timeout=30,
        )
        if not resp.ok:
            raise RuntimeError(f"{resp.status_code} — {resp.json()}")
        usage = resp.json().get("usage", {})
        track_claude_usage("ClaudeAPIC", usage.get("input_tokens", 0), usage.get("output_tokens", 0))
        return resp.json()["content"][0]["text"].strip()

    @wait_rate(300, persist=True)
    def Agente_SyncOrders(self):
        """Sincroniza order_trader con el estado real en IB (Stock) y Binance (Crypto) cada 5 min."""
        try:
            ib = DataHub.clients.get("Stock")
            if ib:
                n = self.RepositorioOportunidades.sync_orders_from_ib(ib, self.account)
                self.logger.warning(f"Agente_SyncOrders IB: {n} actualizadas")
        except Exception as e:
            self.logger.error(f"Agente_SyncOrders IB: {e}")
        try:
            bc = DataHub.clients.get("Crypto")
            if bc:
                n = self.RepositorioOportunidades.sync_orders_from_binance(bc, self.account_crypto)
                self.logger.warning(f"Agente_SyncOrders Binance: {n} actualizadas")
        except Exception as e:
            self.logger.error(f"Agente_SyncOrders Binance: {e}")

    @wait_rate(3600, persist=True)
    def Agente_OrderEodCleanup(self):
        """Cleanup periódico de order_trader: plazos fijos + validación API para NEW/Submitted 2-7d."""
        try:
            d_stock = self.RepositorioOportunidades.cleanup_order_trader_eod(self.account)
            d_crypto = self.RepositorioOportunidades.cleanup_order_trader_eod(self.account_crypto)
            ib = DataHub.clients.get("Stock")
            v_stock = self.RepositorioOportunidades.validate_stale_stock_orders(self.account, ib) if ib else 0
            bc = DataHub.clients.get("Crypto")
            v_crypto = self.RepositorioOportunidades.validate_stale_crypto_orders(self.account_crypto, bc) if bc else 0
            self.logger.warning(f"Agente_OrderEodCleanup: deleted={d_stock + d_crypto} validated={v_stock + v_crypto}")
        except Exception as e:
            self.logger.error(f"Agente_OrderEodCleanup(): {e}")

    async def _flush_system_alerts(self):
        """Envía alertas de sistema acumuladas en DataHub.system_alerts a Telegram."""
        while DataHub.system_alerts:
            msg = DataHub.system_alerts.pop(0)
            try:
                if msg.startswith("[FCI_BLOCKED]"):
                    texto = msg[len("[FCI_BLOCKED]") :]
                    markup = InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🔓 Liberar bloqueo FCI", callback_data="fci_reset_blocked")]]
                    )
                    await self.send_Telegram(texto, reply_markup=markup)
                else:
                    await self.send_Telegram(msg)
            except Exception as e:
                self.logger.error(f"_flush_system_alerts: {e}")

    # agente defensivo: protege ganancias con órdenes STOP dinámicas
    async def Agente_ManagerPreservation(self):
        """
        Agente de Preservación de Ganancias (Stock + Crypto).
        Protege ganancias acumuladas mediante órdenes STOP dinámicas.
        No optimiza ventas, no predice mercado, solo protege.
        """
        for vehiculo in ("Stock", "Crypto"):
            try:
                if DataHub.manager_sesion.get(vehiculo):
                    self._preservation_run_vehiculo(vehiculo)
                else:
                    self.logger.debug(f"Agente_ManagerPreservation({vehiculo}): sesion no activa → SKIP")
            except Exception as e:
                self.logger.error(f"Agente_ManagerPreservation({vehiculo}): {e}")

    # agente especulativo: captura ganancias en activos volátiles con ventas parciales por niveles ROI
    @wait_rate(3600, persist=True)
    async def Agente_GainsCapture(self):
        try:
            if DataHub.manager_sesion.get("Stock"):
                self._gains_capture_run()
            else:
                self.logger.debug("Agente_GainsCapture: sesion Stock no activa → SKIP")
        except Exception as e:
            self.logger.error(f"Agente_GainsCapture(): {e}")

    @wait_rate(28800, persist=True)
    def Agente_Sentimiento(self):
        try:
            ses = BDsystem.get_sesion_by_vehiculo("ClaudeAPIP")
            api_key = ses["userapi"].decode("utf-8") if ses else ""
            result = scan_sentimiento(account=self.account, api_key=api_key)
            self.logger.warning(
                f"Agente_Sentimiento [iter={self.counter}]: "
                f"simbolos={result['symbols']} noticias={result['with_news']} clasificados={result['classified']}"
            )
        except Exception as e:
            self.logger.error(f"Agente_Sentimiento(): {e}")

    @wait_rate(86400, persist=True)
    def Agente_InterpreteSentimiento(self):
        try:
            ses = BDsystem.get_sesion_by_vehiculo("ClaudeAPIP")
            api_key = ses["userapi"].decode("utf-8") if ses else ""
            result = interpretar_sentimiento(account=self.account, api_key=api_key)
            deleted = self.Market.cleanup_sentiment(months=5)
            self.logger.warning(
                f"Agente_InterpreteSentimiento [iter={self.counter}]: "
                f"{len(result)} patrones → {result} | depurados={deleted}"
            )
        except Exception as e:
            self.logger.error(f"Agente_InterpreteSentimiento(): {e}")

    @wait_rate(86400, persist=True)
    def Agente_ExtractoBBVA(self):
        try:
            from Class_BrowserFCI import BrowserFCI  # import diferido — evita ciclo con Modulos_Mysql

            browser = BrowserFCI()
            path = os.environ.get("APPOO_TMP") or os.path.join(os.getcwd(), "tmp")
            descargados = []
            if browser.download_bbva(desde=None, destino=path, prefijo="BBVA_Comprobante_"):
                descargados.append("BBVA")
            if browser.download_santander(desde=None, destino=path, prefijo="movimientos-de-superfondos-"):
                descargados.append("SANT")
            self.logger.warning(f"Agente_ExtractoBBVA: descargados={descargados}")
        except Exception as e:
            self.logger.error(f"Agente_ExtractoBBVA(): {e}")

    @wait_rate(86400, persist=True, desc="AgIA — análisis diario portfolio + candidatos (Fase 1: observación)", nivel=2)
    def Agente_ClaudeIA(self):
        try:
            params = self._load_params("Stock")
            if not params:
                return
            ia_config = params.get("agente_ia", {})
            if not ia_config.get("activo", False):
                self.logger.debug("Agente_ClaudeIA: inactivo en configuración → SKIP")
                return
            try:
                ses = BDsystem.get_sesion_by_vehiculo("ClaudeAPIP")
                api_key = ses["userapi"].decode("utf-8") if ses else ""
            except Exception as _e:
                self.logger.error(f"Agente_ClaudeIA: ClaudeAPIP no disponible → {_e}")
                return
            ctx = self._armar_contexto_ia(params)
            if (
                not ctx.get("portfolio")
                and not ctx.get("candidatos")
                and not ctx.get("oport_buy")
                and not ctx.get("oport_sell")
            ):
                self.logger.warning("Agente_ClaudeIA: sin posiciones ni oportunidades → SKIP (sin llamada API)")
                return
            decision = self._claude_ia_eval(ctx, ia_config, api_key)
            if decision:
                trace_id = self.IaTrace.insert_trace(
                    vehiculo="Stock",
                    simbolo=decision.get("simbolo", ""),
                    decision=decision.get("decision", "HOLD"),
                    monto=decision.get("monto", 0),
                    motivo=decision.get("motivo", ""),
                    gates_ok={},
                )
                self.logger.warning(
                    f"Agente_ClaudeIA [Fase1]: decision={decision.get('decision')} "
                    f"simbolo={decision.get('simbolo','—')} "
                    f"motivo={str(decision.get('motivo',''))[:80]} trace_id={trace_id}"
                )
                modo = DataHub.modo_operacion
                accion = decision.get("decision", "HOLD")
                if modo == "SUPERVISADO" and accion in ("BUY", "SELL") and trace_id:
                    self._propuesta_supervisado(decision, trace_id)
        except Exception as e:
            self.logger.error(f"Agente_ClaudeIA(): {e}")

    def _propuesta_supervisado(self, decision: dict, trace_id: int):
        simbolo = decision.get("simbolo", "—")
        accion = decision.get("decision", "—")
        monto = decision.get("monto", 0)
        motivo = str(decision.get("motivo", ""))[:500]
        emoji = "🟢" if accion == "BUY" else "🔴"
        texto = (
            f"{emoji} *Propuesta IA — {accion} {simbolo}*\n"
            f"Monto: ${monto:,.0f}\n\n"
            f"_{motivo}_\n\n"
            f"⚙ Modo: SUPERVISADO — esperando aprobación"
        )
        botones = [
            [
                InlineKeyboardButton("✅ Ejecutar", callback_data=f"ia_ejecutar|{trace_id}"),
                InlineKeyboardButton("⏸ Diferir", callback_data=f"ia_diferir|{trace_id}"),
            ]
        ]
        markup = InlineKeyboardMarkup(botones)
        self.exec_modulo_async(self.send_Telegram(texto, reply_markup=markup))

    def _armar_contexto_ia(self, params: dict) -> dict:
        ia_config = params.get("agente_ia", {})
        gc_config = params.get("gains_capture", {})
        pinvertir = float(ia_config.get("monto_por_trade", 170))
        min_ganancia = float(gc_config.get("min_ganancia", 100.0))

        positions = DataHub.manager_positions.get("Stock", [])
        portfolio = []
        for p in positions:
            if not p.get("ticket"):
                continue
            gain_usd = round(float(p.get("unrealizedpnl", 0) or 0), 2)
            portfolio.append(
                {
                    "symbol": p.get("ticket"),
                    "roi_pct": round(float(p.get("roi", 0) or 0) * 100, 2),
                    "valor_mkt": round(float(p.get("valuemkt", 0) or 0), 2),
                    "gain_usd": gain_usd,
                    "gains_candidate": gain_usd >= min_ganancia,
                    "consenso": p.get("consenso_tag", ""),
                    "dividends": round(float(p.get("dividends", 0) or 0), 2),
                }
            )
        candidatos = self.IaTrace.select_candidatos_ia(self.account, consenso_min=ia_config.get("gate_consenso_min", 4))
        for c in candidatos:
            last = float(c.get("lastPrice") or 0)
            c["monto_sugerido"] = max(pinvertir, last) if last > 0 else pinvertir

        rebalanceo = {}
        mb = getattr(DataHub, "manager_buysell", {})
        for dim in ("sector", "region", "activos"):
            dim_data = mb.get(dim, {})
            summary = dim_data.get("summary", {})
            names = summary.get("Name", [])
            pesos = summary.get("Peso", [])
            total = dim_data.get("total_valor_market", 0)
            if names and pesos and total > 0:
                n = len(names)
                objetivo = 1 / n if n > 0 else 0
                items = [
                    {"name": nm, "peso": round(ps, 3), "gap": round(objetivo - ps, 3)} for nm, ps in zip(names, pesos)
                ]
                rebalanceo[dim] = {"items": items, "total_usd": round(total, 0)}
        div_data = mb.get("dividends", {})
        div_summary = div_data.get("summary", {})
        if div_summary:
            rebalanceo["dividends"] = {"meses": div_summary, "total_usd": div_data.get("total_valor_market", 0)}

        rebalanceo_ranking = []
        rb_engine = getattr(DataHub, "rebalanceo", {}).get("Stock", {})
        for item in rb_engine.get("ranking", [])[:5]:
            rebalanceo_ranking.append(
                {
                    "symbol": item.get("symbol"),
                    "score": round(item.get("score", 0), 3),
                    "dimension": item.get("dimension", ""),
                    "monto": round(item.get("monto_sugerido", 0), 0),
                }
            )

        info = getattr(DataHub, "info", {})
        oport_buy = []
        oport_sell = []
        for sym, data in info.items():
            buy_key = "dividends" if "dividends" in data else ("buy" if "buy" in data else None)
            if buy_key:
                b = data[buy_key]
                oport_buy.append(
                    {
                        "symbol": sym,
                        "tipo": buy_key,
                        "gain_inversion": round(float(b.get("ganancia inversión", 0)), 3),
                        "qty": int(b.get("cantidad buy", 0)),
                        "yield": round(float(b.get("dividendYield", 0)) * 100, 2),
                        "avgcost_post": round(float(b.get("avgCost post", 0)), 2),
                    }
                )
            if "sell" in data:
                s = data["sell"]
                profit = float(s.get("profit", 0))
                if profit > 0:
                    oport_sell.append(
                        {
                            "symbol": sym,
                            "profit": round(profit, 2),
                            "roi": round(float(s.get("roi", 0)) * 100, 2),
                            "qty": round(float(s.get("cantidad sell", 0)), 4),
                            "lotes": int(s.get("cantidad lotes", 0)),
                        }
                    )

        oport_buy.sort(key=lambda x: x["gain_inversion"])
        oport_sell.sort(key=lambda x: -x["profit"])

        _FCI_ENTIDADES = {
            "BBVA0001": ("FBA", "Supergestion"),
            "SANT0001": ("Superfondo", "Supergestion"),
        }
        fci_rotacion = {}
        fci_sell_symbols = {s["symbol"] for s in oport_sell}
        cnv_db = DiariaCNV()
        for cuenta, prefijos in _FCI_ENTIDADES.items():
            if any(any(s.startswith(p) for p in prefijos) for s in fci_sell_symbols):
                candidato = cnv_db.select_fci_rf_candidato(cuenta)
                if candidato:
                    fci_rotacion[cuenta] = candidato

        return {
            "portfolio": portfolio,
            "candidatos": candidatos,
            "rebalanceo": rebalanceo,
            "rebalanceo_ranking": rebalanceo_ranking,
            "oport_buy": oport_buy[:8],
            "oport_sell": oport_sell[:5],
            "fci_rotacion": fci_rotacion,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "pinvertir": pinvertir,
            "min_ganancia": min_ganancia,
        }

    def _claude_ia_eval(self, ctx: dict, ia_config: dict, api_key: str) -> dict | None:
        def _portfolio_txt():
            rows = ctx.get("portfolio", [])
            if not rows:
                return "  (sin posiciones)"
            return "\n".join(
                f"  {p['symbol']}: ROI={p['roi_pct']:+.1f}% | mkt=${p['valor_mkt']:.0f} | "
                f"gain=${p['gain_usd']:.0f}"
                + (" [GAINS?]" if p.get("gains_candidate") else "")
                + f" | consenso={p['consenso']}"
                for p in rows
            )

        def _candidatos_txt():
            rows = ctx.get("candidatos", [])
            if not rows:
                return "  (sin candidatos con consenso suficiente)"
            return "\n".join(
                f"  {c['symbol']} ({(c.get('shortName') or '')[:20]}): "
                f"consenso_suma={c.get('consenso_suma')} "
                f"inst_score={c.get('inst_score') or '-'} "
                f"yield={c.get('dividendYield') or '-'} "
                f"monto_sugerido=${c.get('monto_sugerido', 0):.0f}"
                for c in rows
            )

        def _rebalanceo_txt():
            rb = ctx.get("rebalanceo", {})
            if not rb:
                return "  (sin datos — manager_buysell vacío)"
            dim_labels = {"sector": "Sectores", "region": "Regiones", "activos": "Tipos de activo"}
            lines = []
            for dim, label in dim_labels.items():
                data = rb.get(dim)
                if not data:
                    continue
                items = sorted(data.get("items", []), key=lambda x: -x["gap"])
                parts = " | ".join(
                    f"{it['name']}={it['peso']*100:.0f}%"
                    + ("▼" if it["gap"] > 0.03 else "▲" if it["gap"] < -0.03 else "✓")
                    for it in items[:6]
                )
                total = data.get("total_usd", 0)
                lines.append(f"  {label} (total ${total:.0f}): {parts}")
            div = rb.get("dividends", {})
            if div and div.get("total_usd", 0) > 0:
                lines.append(f"  Dividendos: ingreso total portafolio ${div['total_usd']:.0f}/año")
            return "\n".join(lines) if lines else "  (sin datos de dimensiones)"

        def _oport_buy_txt():
            rows = ctx.get("oport_buy", [])
            if not rows:
                return "  (ninguna)"
            return "\n".join(
                f"  {r['symbol']}: tipo={r['tipo']} qty={r['qty']} "
                f"yield={r['yield']:.1f}% gain_inv={r['gain_inversion']:+.3f} avgcost_post=${r['avgcost_post']:.2f}"
                for r in rows
            )

        def _oport_sell_txt():
            rows = ctx.get("oport_sell", [])
            if not rows:
                return "  (ninguna)"
            return "\n".join(
                f"  {r['symbol']}: profit=${r['profit']:.0f} ROI={r['roi']:+.1f}% qty={r['qty']} lotes={r['lotes']}"
                for r in rows
            )

        def _ranking_txt():
            rows = ctx.get("rebalanceo_ranking", [])
            if not rows:
                return "  (sin ranking — RebalanceEngine no ejecutó aún)"
            return "\n".join(
                f"  {r['symbol']}: score={r['score']} dim={r['dimension']} monto=${r['monto']:.0f}" for r in rows
            )

        def _fci_rotacion_txt():
            rotacion = ctx.get("fci_rotacion", {})
            if not rotacion:
                return ""
            lineas = ["Rotación FCI sugerida (si SELL sobre RV, rotar al RF más deprimido de la misma entidad):"]
            for cuenta, c in rotacion.items():
                entidad = "BBVA" if "BBVA" in cuenta else "Santander"
                v30 = c.get("variacion30dias", 0) or 0
                v90 = c.get("variacion90dias", 0) or 0
                lineas.append(f"  {entidad} → {c['fondo']} (rend30d: {v30:+.2f}% | rend90d: {v90:+.2f}%)")
            return "\n".join(lineas) + "\n\n"

        gains_symbols = [p["symbol"] for p in ctx.get("portfolio", []) if p.get("gains_candidate")]
        gains_txt = f"Posiciones con ganancia ≥${ctx.get('min_ganancia', 100):.0f} (candidatas a captura): " + (
            ", ".join(gains_symbols) if gains_symbols else "(ninguna)"
        )
        _plan = ia_config.get("plan", {})
        _meta_capital = _plan.get("meta_capital", "1.2M USD")
        _meta_año = _plan.get("meta_año", "2030")
        _ingreso_pct = _plan.get("ingreso_pasivo_pct", "≥3%")
        _mision_extra = _plan.get("mision", "En crisis → Hold o sumar posiciones, nunca vender por pánico.")
        prompt = (
            f"Sos el agente de inversión autónomo. Misión: acumular capital hacia {_meta_capital} en {_meta_año} "
            f"generando ingresos pasivos {_ingreso_pct}/año. Foco en dividendos, uso moderado de apalancamiento IB. "
            f"{_mision_extra}\n\n"
            f"Fecha: {ctx.get('fecha')}\n\n"
            f"Portfolio actual (Stock):\n{_portfolio_txt()}\n\n"
            f"{gains_txt}\n\n"
            f"Rebalanceo — diversificación actual (▼=subponderado, ▲=sobreponderado, ✓=equilibrado):\n"
            f"{_rebalanceo_txt()}\n\n"
            f"Ranking rebalanceo (top 5 por motor estructural):\n{_ranking_txt()}\n\n"
            f"Oportunidades BUY detectadas por el sistema:\n{_oport_buy_txt()}\n\n"
            f"Oportunidades SELL detectadas por el sistema:\n{_oport_sell_txt()}\n\n"
            f"Candidatos externos (consenso ≥ {ia_config.get('gate_consenso_min', 4)}):\n{_candidatos_txt()}\n\n"
            f"{_fci_rotacion_txt()}"
            f"Límites: monto_base=${ctx.get('pinvertir', 170):.0f} (se ajusta al precio del activo) | "
            f"leverage_max={ia_config.get('leverage_max', 1.8)}x | "
            f"inst_score_min={ia_config.get('gate_inst_score_min', 0.5)}\n\n"
            "Para BUY: cruzar oportunidades BUY del sistema con candidatos externos y ranking rebalanceo. "
            "Priorizar los que aparecen en más de una fuente y alineen con dimensiones subponderadas (▼). "
            "Para posiciones [GAINS?] o SELL del sistema: evaluá si el contexto justifica captura (SELL) u HOLD. "
            "Si el SELL es sobre un FCI de Renta Variable, en el motivo indicar hacia qué fondo de Renta Fija rotar.\n\n"
            "Producí UNA decisión con formato JSON exacto:\n"
            '{"decision": "BUY|SELL|HOLD|ALERTA", "simbolo": "TICKER_O_VACIO", '
            '"monto": 0, "motivo": "explicación en 2-3 oraciones completas: qué acción, por qué ahora, qué se espera lograr. Sin abreviaturas."}'
        )
        result = self._call_claude(prompt, api_key, "ClaudeAPIP", max_tokens=500, timeout=20)
        return result if result and "decision" in result else None

    def _gains_capture_run(self):
        _gc_logger = logging.getLogger("GainsCapture")

        params = self._load_params("Stock")
        if not params:
            return
        gc_config = params.get("gains_capture")
        if not gc_config:
            _gc_logger.debug("_gains_capture_run: gains_capture no configurado en sesion → SKIP")
            return

        min_roi = gc_config.get("min_roi", 0.20)
        min_ganancia = float(gc_config.get("min_ganancia", 100.0))

        _claude_key = None
        try:
            _ses = BDsystem.get_sesion_by_vehiculo("ClaudeAPIP")
            _claude_key = _ses["userapi"].decode("utf-8") if _ses else None
        except Exception as e:
            _gc_logger.error(f"GainsCapture: ClaudeAPIP no disponible → {e}")

        categories = self.Market.load_symbols(self.account)
        positions = self.PlanInversion.select_inversion(tipoin="Stock", ticket="all")
        conid_map = {p.get("ticket"): (p.get("conid"), p.get("useraccount")) for p in positions}
        symbols_gain = DataHub.get_info_symbols_gain()

        for sym_data in symbols_gain:
            symbol = sym_data.get("symbol")
            if categories.get(symbol) != "N":
                continue

            list_gain = sym_data.get("list_gain", [])
            if not list_gain:
                continue

            lotes_validos = []
            for lote in list_gain:
                last_l = lote.get("last", 0)
                cantidad = lote.get("cantidad", 0)
                costo_lote = lote.get("costo lote", 0)
                if costo_lote <= 0:
                    continue
                ganancia_lote = last_l * cantidad - costo_lote
                roi_lote = ganancia_lote / costo_lote
                if roi_lote >= min_roi and ganancia_lote >= min_ganancia:
                    lotes_validos.append({**lote, "ganancia": ganancia_lote, "roi": roi_lote})

            if not lotes_validos:
                continue

            mejor_lote = max(lotes_validos, key=lambda x: x["roi"])
            roi_ref = mejor_lote["roi"]
            ganancia_ref = mejor_lote["ganancia"]
            last = sym_data.get("last", 0)
            conid, account = conid_map.get(symbol, (None, None))

            state = self.gains_capture_state.get(symbol, {})
            estado = state.get("estado", "normal")

            if estado == "esperando_reset":
                self.gains_capture_state[symbol] = {**state, "estado": "normal"}
                write_json_tmp("gains_capture_state.json", self.gains_capture_state)
                _gc_logger.warning(f"GainsCapture({symbol}): reset completado → normal")
                estado = "normal"

            if estado == "pendiente_autorizacion":
                ts_raw = state.get("pendiente_ts")
                if ts_raw:
                    elapsed = (datetime.now() - datetime.fromisoformat(ts_raw)).total_seconds()
                    if elapsed > 1800:
                        self.gains_capture_state[symbol] = {**state, "estado": "normal", "pendiente": None}
                        write_json_tmp("gains_capture_state.json", self.gains_capture_state)
                        _gc_logger.warning(f"GainsCapture({symbol}): propuesta expirada (30 min) → cancelada")
                        estado = "normal"
                    else:
                        _gc_logger.debug(
                            f"GainsCapture({symbol}): pendiente_autorizacion → esperando ({elapsed/60:.0f}m)"
                        )
                        continue

            if estado == "escalon_pendiente":
                _gc_logger.debug(f"GainsCapture({symbol}): escalon_pendiente → esperando fill")
                continue

            datos_tecnicos = DataHub.info.get(symbol, {}).get("datos_tecnicos", {})
            claude_result = None
            if _claude_key:
                claude_result = self._gains_capture_claude_eval(
                    symbol, roi_ref, ganancia_ref, last, datos_tecnicos, _claude_key
                )

            if not claude_result or claude_result.get("accion") != "vender":
                razon = claude_result.get("razon", "") if claude_result else "sin evaluación"
                _gc_logger.warning(
                    f"GainsCapture({symbol}): roi={roi_ref:.1%} gain=${ganancia_ref:.0f} → ESPERAR — {razon}"
                )
                continue

            escenario_key = {" 25%": " 25%", "25%": " 25%", " 33%": " 33%", "33%": " 33%", "100%": "100%"}.get(
                claude_result.get("escenario", "25%"), " 25%"
            )
            ventas = DataHub.maximiza_sell_lotes(
                list_gain=list_gain,
                position=sym_data.get("position"),
                costobase=sym_data.get("costobase"),
            )
            sell_data = ventas.get(escenario_key, ventas.get(" 25%", {}))
            vender_qty = int(sell_data.get("cantidad sell", 0))
            if vender_qty <= 0:
                continue

            lmt_price = round(last * 0.995, 2)
            _det = {
                "tipo": "gains_capture",
                "roi_lote": roi_ref,
                "ganancia_lote": ganancia_ref,
                "escenario": escenario_key.strip(),
                "modo": DataHub.gains_capture_modo,
                "claude": claude_result,
                "orden": {"qty": vender_qty, "lmt_price": lmt_price},
            }

            if DataHub.gains_capture_modo == "autorizado":
                razon = claude_result.get("razon", "")
                msg = (
                    f"📈 *GainsCapture — {symbol}*\n"
                    f"ROI lote: {roi_ref:.1%} | Ganancia: ${ganancia_ref:.0f}\n"
                    f"Escenario: {escenario_key.strip()} | Vender {vender_qty} acc LMT ${lmt_price:.2f}\n"
                    f"{razon}\n"
                    f"/ok\\_{symbol}  |  /no\\_{symbol}"
                )
                DataHub.system_alerts.append(msg)
                self.gains_capture_state[symbol] = {
                    **state,
                    "estado": "pendiente_autorizacion",
                    "pendiente": {
                        "escenario": escenario_key.strip(),
                        "qty": vender_qty,
                        "lmt_price": lmt_price,
                        "conid": str(conid) if conid else None,
                        "account": account,
                        "det": _det,
                    },
                    "pendiente_ts": datetime.now().isoformat(),
                }
                write_json_tmp("gains_capture_state.json", self.gains_capture_state)
                _gc_logger.warning(f"GainsCapture({symbol}): propuesta enviada a Telegram (autorizado)")
                continue

            trama = DataHub.gains_capture_build_trama_sell("Stock", account, symbol, conid, lmt_price, vender_qty)
            try:
                response = DataHub.preservation_send_order("Stock", trama)
                order_id = DataHub.preservation_extract_order_id(response)
                self.gains_capture_state[symbol] = {
                    **state,
                    "estado": "escalon_pendiente",
                    "escalon_order_id": str(order_id) if order_id else None,
                    "last_check": datetime.now().isoformat(),
                }
                write_json_tmp("gains_capture_state.json", self.gains_capture_state)
                try:
                    self.RepositorioOportunidades.insert_preservation_order(
                        account,
                        "Stock",
                        symbol,
                        str(conid),
                        str(order_id),
                        lmt_price,
                        float(vender_qty),
                        json.dumps(_det),
                    )
                except Exception as _e:
                    _gc_logger.error(f"GainsCapture({symbol}): insert_preservation_order → {_e}")
                DataHub.system_alerts.append(
                    f"📈 GainsCapture {symbol}: vendiendo {vender_qty} acc LMT ${lmt_price:.2f} "
                    f"escenario={escenario_key.strip()} — order_id={order_id}"
                )
                _gc_logger.warning(
                    f"GainsCapture({symbol}): LMT SELL {vender_qty} acc @ {lmt_price:.2f} "
                    f"escenario={escenario_key.strip()} roi_lote={roi_ref:.1%} order_id={order_id}"
                )
            except Exception as e:
                _gc_logger.error(f"GainsCapture({symbol}): error enviando orden → {e}")

    def _gains_capture_claude_eval(
        self, symbol: str, roi_lote: float, ganancia_lote: float, last: float, datos_tecnicos: dict, api_key: str
    ) -> dict | None:
        d = datos_tecnicos.get("diaria", {})
        s = datos_tecnicos.get("semanal", {})
        rsi_d = d.get("rsi")
        rsi_w = s.get("rsi")
        macd_val = d.get("macd")
        macd_estado = "alcista" if macd_val and macd_val > 0 else ("bajista" if macd_val and macd_val < 0 else "neutro")
        ema50 = (d.get("ema(20,50,100,200)") or {}).get("EMA50")
        ema200 = (d.get("ema(20,50,100,200)") or {}).get("EMA200")
        ema50_rel = ("sobre" if last > ema50 else "bajo") if ema50 else "N/D"
        ema200_rel = ("sobre" if last > ema200 else "bajo") if ema200 else "N/D"

        def _f(v, fmt="{:.1f}", default="N/D"):
            return fmt.format(v) if v is not None else default

        prompt = (
            f"Eres un agente de captura de ganancias para un portfolio especulativo de acciones volátiles.\n"
            f"El activo {symbol} tiene un lote con ROI={roi_lote:.1%} y ganancia=${ganancia_lote:.0f}. Precio actual: ${last:.2f}.\n\n"
            f"Técnico:\n"
            f"- RSI diario: {_f(rsi_d)} | RSI semanal: {_f(rsi_w)} | MACD: {macd_estado}\n"
            f"- Precio vs EMA50: {ema50_rel} | vs EMA200: {ema200_rel}\n\n"
            f"Determiná si el precio está en un SPIKE/TECHO (vender) o en TENDENCIA ALCISTA sostenida (esperar).\n"
            f"Si vendés, elegí el escenario según convicción:\n"
            f"- '25%': momentum presente, asegurar algo conservador\n"
            f"- '33%': señales mixtas, venta moderada\n"
            f"- '100%': spike claro o sobrecompra extrema, salida total del lote\n\n"
            f'Respondé SOLO con JSON: {{"accion": "vender"|"esperar", "escenario": "25%"|"33%"|"100%", "razon": "max 120 chars"}}'
        )
        result = self._call_claude(prompt, api_key, "ClaudeAPIP", max_tokens=200, timeout=15)
        return result if result and "accion" in result else None

    def _load_params(self, vehiculo):
        return load_vehiculo_params(vehiculo, self._params_cache, self.PlanInversion)

    def _build_preservation_context(
        self, symbol, account, roi, last, sma_base, max_price, stop_calculado, stop_anterior, atr, base_limit
    ) -> dict:
        """Arma el dict de contexto completo para el prompt Claude de preservation."""
        ctx = self.Market.select_preservation_context(symbol, account)
        ctx.update(
            {
                "symbol": symbol,
                "roi": roi,
                "last": last,
                "sma_base": sma_base,
                "max_price": max_price,
                "stop_calculado": stop_calculado,
                "stop_anterior": stop_anterior,
                "atr": atr,
                "base_limit": base_limit,
            }
        )
        # indicadores técnicos en tiempo real desde DataHub (actualizado por TickerInfo)
        dt = DataHub.info.get(symbol, {}).get("datos_tecnicos", {})
        d = dt.get("diaria", {})
        s = dt.get("semanal", {})
        if d:
            ctx["rsi_d"] = round(d["rsi"], 1) if d.get("rsi") is not None else None
            macd_val = d.get("macd")
            if macd_val is not None:
                ctx["macd_estado"] = "alcista" if macd_val > 0 else ("bajista" if macd_val < 0 else "neutro")
            ema200 = (d.get("ema(20,50,100,200)") or {}).get("EMA200")
            precio = d.get("precio_calculo")
            if ema200 and precio:
                ctx["ema200_rel"] = "sobre" if precio > ema200 else "bajo"
            w13_min, w13_max = d.get("13_semanas_min"), d.get("13_semanas_max")
            if w13_min is not None and w13_max and w13_max > w13_min and precio:
                ctx["rango_13w_pct"] = round((precio - w13_min) / (w13_max - w13_min), 2)
        if s:
            ctx["rsi_w"] = round(s["rsi"], 1) if s.get("rsi") is not None else None
            precio_s = s.get("precio_calculo")
            w26_min, w26_max = s.get("26_semanas_min"), s.get("26_semanas_max")
            if w26_min is not None and w26_max and w26_max > w26_min and precio_s:
                ctx["rango_26w_pct"] = round((precio_s - w26_min) / (w26_max - w26_min), 2)
        return ctx

    def _claude_preservation_eval(self, ctx: dict, api_key: str) -> dict | None:
        """Llama a Claude Haiku para afinar el stop. Retorna dict o None si falla."""

        def _v(key, fmt=None, default="N/D"):
            val = ctx.get(key)
            if val is None:
                return default
            try:
                return fmt.format(val) if fmt else str(val)
            except Exception:
                return str(val)

        prompt = (
            f"Eres un agente de preservación de ganancias para un portfolio de inversión.\n"
            f"Las reglas fijas ya activaron la protección de esta posición (ROI >= 10%).\n"
            f"Tu tarea es ajustar el nivel del STOP para maximizar la protección según el contexto.\n\n"
            f"Posición: {ctx['symbol']}\n"
            f"- ROI actual: {_v('roi', '{:.1%}')} | Precio: ${_v('last', '{:.2f}')} | SMA20: ${_v('sma_base', '{:.2f}')} | Max reciente: ${_v('max_price', '{:.2f}')}\n"
            f"- Stop base (SMA20): ${_v('stop_calculado', '{:.2f}')} | Stop anterior: ${_v('stop_anterior', '{:.2f}')}\n"
            f"- ATR(14): ${_v('atr', '{:.2f}')}\n\n"
            f"Contexto fundamental:\n"
            f"- Consenso: {_v('consenso_tag')} ({_v('consenso_suma')} votos)\n"
            f"- Inst Score: {_v('inst_score')} | 13F Buy ratio: {_v('fh_buy_ratio', '{:.1%}')}\n"
            f"- Analistas: {_v('analyst_rec')} (mean={_v('analyst_mean', '{:.1f}')})\n"
            f"- Sentimiento: {_v('patron')} (score={_v('sentiment_score')})\n\n"
            f"Técnico:\n"
            f"- RSI diario: {_v('rsi_d')} | RSI semanal: {_v('rsi_w')} | MACD: {_v('macd_estado')}\n"
            f"- EMA200: precio {_v('ema200_rel')}\n"
            f"- Rango 13 semanas: {_v('rango_13w_pct', '{:.0%}')} | Rango 26 semanas: {_v('rango_26w_pct', '{:.0%}')}\n\n"
            f"Podés subir el stop (más protección) o mantener el base.\n"
            f"NUNCA sugerir un stop inferior al base calculado por reglas (${ctx['stop_calculado']:.2f}).\n"
            f'Respondé SOLO con JSON válido: {{"stop_sugerido": float, "razon": "str max 120 chars", "urgencia": "alta"|"media"|"baja"}}'
        )
        result = self._call_claude(prompt, api_key, "ClaudeAPIP", max_tokens=256, timeout=15)
        return result if result and "stop_sugerido" in result else None

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

        # 2. Verificar intervalo por vehículo — único acceso a BD solo cuando toca
        last_run = self.preservation_last_run.get(vehiculo)
        if last_run is not None:
            elapsed = (datetime.now() - last_run).total_seconds()
            if elapsed < intervalo_min:
                return pconfig, intervalo_min, False

        # Primera ejecución o toca revisión: autoriza evaluación
        now = datetime.now()
        self.preservation_last_run[vehiculo] = now
        # Persistir last_run en JSON para sobrevivir reinicios del Chatbot
        _state_snap = read_json_tmp("preservation_state.json")
        _state_snap[f"_last_run_{vehiculo}"] = now.isoformat()
        write_json_tmp("preservation_state.json", _state_snap)
        roi_minimo = pconfig.get("roi_minimo", 0.10)
        proteccion_base = pconfig.get("proteccion_base", 0.50)
        elapsed_log = (now - last_run).total_seconds() if last_run else 0
        self.logger.warning(
            f"Preservation({vehiculo}): REVISIÓN | roi_min={roi_minimo} | prot={proteccion_base} | elapsed={elapsed_log:.0f}s"
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

        _claude_key = None
        try:
            _ses = BDsystem.get_sesion_by_vehiculo("ClaudeAPIP")
            _claude_key = _ses["userapi"].decode("utf-8") if _ses else None
        except Exception as e:
            self.logger.error(f"Preservation({vehiculo}): ClaudeAPIP no disponible → {e}")

        # 1. Cargar posiciones activas
        positions = self.PlanInversion.select_inversion(tipoin=vehiculo, ticket="all")
        self.logger.warning(f"Preservation({vehiculo}): {len(positions)} posiciones cargadas")

        for positio in positions:
            symbol = positio.get("ticket")
            costobase = positio.get("costobase", 0)
            position_qty = positio.get("position", 0)
            conid = positio.get("conid")
            account = positio.get("useraccount")

            if costobase <= 0 or position_qty <= 0:
                continue

            # unrealizedpnl desde mktvalue (mrkprice×position) — más fresco que el campo guardado en DB
            mktvalue = positio.get("mktvalue") or 0
            unrealizedpnl = (mktvalue - costobase) if mktvalue else positio.get("unrealizedpnl", 0)

            # 2. Verificar ROI >= roi_minimo
            roi = unrealizedpnl / costobase
            if roi < roi_minimo:
                continue

            base_limit = unrealizedpnl * proteccion_base

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

            # 5b. SMA20 — base suavizada para stop (activos long-term encima de EMAs)
            sma_base, sma_error = DataHub.preservation_get_sma(symbol, vehiculo)
            if sma_base is None:
                sma_base = last
                self.logger.warning(
                    f"Preservation({vehiculo}/{symbol}): SMA20 no disponible ({sma_error}) → usando last={last:.2f}"
                )

            # 6. Actualizar max_price (solo para limit price de la orden STP LMT)
            max_price_prev = state.get("max_price", last)
            max_price = max(max_price_prev, last)

            # 7. Calcular stop desde SMA20 (no persigue picos intradiarios)
            stop_distance = max(correccion_pct * sma_base, atr_mult * atr)
            stop_calculado = sma_base - stop_distance

            # 8. Regla de oro: nunca bajar el stop
            stop_anterior = state.get("stop_actual", 0)
            stop_final = max(stop_anterior, stop_calculado)

            # 8b. Claude afina el stop (opcional — fallback a reglas si falla)
            ctx = {}
            claude_result = None
            if _claude_key:
                ctx = self._build_preservation_context(
                    symbol, account, roi, last, sma_base, max_price, stop_calculado, stop_anterior, atr, base_limit
                )
                claude_result = self._claude_preservation_eval(ctx, _claude_key)
                if claude_result:
                    stop_claude = claude_result.get("stop_sugerido", 0)
                    stop_final = max(stop_final, stop_claude)
                    self._preservation_logger.info(
                        f"[CLAUDE] {symbol}: stop_sugerido={stop_claude:.2f} "
                        f"urgencia={claude_result.get('urgencia')} razon={claude_result.get('razon')}"
                    )

            # 9. Cantidad a proteger (DataHub — respeta lotSize en Crypto)
            qty = DataHub.preservation_calc_qty(self.account, vehiculo, symbol, last, base_limit)
            if qty <= 0:
                continue

            # 10. Construir trama de orden STOP (DataHub)
            trama = DataHub.preservation_build_trama(vehiculo, account, symbol, conid, stop_final, max_price, qty)

            order_id_prev = state.get("order_id")

            is_live = not self._preservation_dry_run and vehiculo == "Stock"

            # Activa Order STOP para el symbol — también cuando no hay order_id (primera vez en live)
            if stop_final > stop_anterior or not order_id_prev:
                accion = "NUEVA" if not order_id_prev else "MODIFICADA (cancel+new)"
                msg = (
                    f"Preservation({vehiculo}/{symbol}): "
                    f"ROI={roi:.1%} | last={last:.2f} | sma20={sma_base:.2f} | max={max_price:.2f} | "
                    f"ATR={atr:.2f} | stop_prev={stop_anterior:.2f} → stop_new={stop_final:.2f} | "
                    f"qty={qty} | base_limit={base_limit:.2f} | trama={trama} | {accion}"
                )
                if not is_live:
                    order_id = order_id_prev
                    self._preservation_logger.info(f"[DRY-RUN] {msg}")
                    self.logger.warning(f"[DRY-RUN] {msg}")
                else:
                    if order_id_prev:
                        DataHub.preservation_cancel_order(vehiculo, account, order_id_prev, symbol)
                    response = DataHub.preservation_send_order(vehiculo, trama)
                    order_id = DataHub.preservation_extract_order_id(response)
                    self._preservation_logger.info(f"[ENVIADA] {msg} | order_id={order_id}")
                    self.logger.warning(f"[ENVIADA] {msg} | order_id={order_id}")
                    try:
                        _det = {
                            "tipo": "preservation_stop",
                            "decision": {
                                "roi": round(float(roi), 4),
                                "sma_base": round(float(sma_base), 4),
                                "max_price": round(float(max_price), 4),
                                "atr": round(float(atr), 4),
                                "stop_calculado_reglas": round(float(stop_calculado), 4),
                                "consenso_tag": ctx.get("consenso_tag") if claude_result else None,
                                "inst_score": ctx.get("inst_score") if claude_result else None,
                                "fh_buy_ratio": ctx.get("fh_buy_ratio") if claude_result else None,
                                "sentiment_patron": ctx.get("patron") if claude_result else None,
                                "rsi_d": ctx.get("rsi_d") if claude_result else None,
                                "macd_estado": ctx.get("macd_estado") if claude_result else None,
                                "base_limit": round(float(base_limit), 4),
                            },
                            "claude": claude_result,
                            "resultado": {
                                "stop_final": round(float(stop_final), 4),
                                "qty_protegida": int(qty),
                                "ganancia_protegida_usd": round(float(base_limit), 4),
                            },
                        }
                        self.RepositorioOportunidades.insert_preservation_order(
                            account,
                            vehiculo,
                            symbol,
                            str(conid),
                            str(order_id),
                            float(stop_final),
                            float(qty),
                            json.dumps(_det),
                        )
                    except Exception as _e:
                        self.logger.error(f"insert_preservation_order({symbol}): {_e}")
            else:
                order_id = order_id_prev
                msg = (
                    f"Preservation({vehiculo}/{symbol}): "
                    f"ROI={roi:.1%} | last={last:.2f} | sma20={sma_base:.2f} | "
                    f"stop={stop_final:.2f} (sin cambio)"
                )
                self._preservation_logger.info(msg)
                self.logger.warning(msg)

            # 11. Persistir estado en memoria y en JSON (sobrevive reinicios)
            # float() convierte np.float64 → JSON serializable; trama se reconstruye cada ciclo
            self.preservation_state[symbol] = {
                "max_price": float(max_price),
                "stop_actual": float(stop_final),
                "last_check": datetime.now().isoformat(),
                "order_id": order_id,
                "vehiculo": vehiculo,
            }
            write_json_tmp("preservation_state.json", self.preservation_state)


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
        CHAT_ID = [update.effective_chat.id] if update else self.userAuth

        await self.clear_bot_chat(CHAT_ID)

        n_alertas = len(DataHub.system_alerts)
        lbl_alertas = f"🚨 Alertas ({n_alertas})" if n_alertas else "🔕 Alertas"
        botones = [
            [
                InlineKeyboardButton("⬇️⬆️ Top(10)", callback_data="menu_top"),
                InlineKeyboardButton("⬇️ Sell", callback_data="menu_sell"),
                InlineKeyboardButton("⬆️ Buy", callback_data="menu_buy"),
            ],
            [
                InlineKeyboardButton("🎯 G/P Real", callback_data="performan"),
                InlineKeyboardButton("🟢🔴 Orders", callback_data="OrdersExec"),
                InlineKeyboardButton("🤖 BotTrader", callback_data="botrtrader"),
            ],
            [
                InlineKeyboardButton(lbl_alertas, callback_data="alertas"),
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
                self.telegram_app = ApplicationBuilder().token(self.TOKEN).connect_timeout(30).read_timeout(30).build()

                self.telegram_app.add_handler(CommandHandler("menu", self.handle_menu))
                self.telegram_app.add_handler(CommandHandler("start", self.handle_menu))
                self.telegram_app.add_handler(
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_segurity_message)
                )
                self.telegram_app.add_handler(CallbackQueryHandler(self.handle_callback))
                self.telegram_app.add_handler(MessageHandler(filters.Regex(r"^/ok_\w+$"), self.handle_gains_capture_ok))
                self.telegram_app.add_handler(MessageHandler(filters.Regex(r"^/no_\w+$"), self.handle_gains_capture_no))

                # Captura errores de red dentro del loop de polling (ConnectError, NetworkError, etc.)
                async def _telegram_error_handler(update, context):
                    self.logger.warning(f"Telegram network error (ignorado): {context.error}")

                self.telegram_app.add_error_handler(_telegram_error_handler)

                # Enviar mensaje de bienvenida antes de polling
                async def _send_welcome():
                    await self.telegram_app.initialize()
                    self.bot = self.telegram_app.bot
                    modo = DataHub.modo_operacion
                    _emoji_modo = {"OBSERVACION": "🔴", "SUPERVISADO": "🟡", "AUTONOMO": "🟢"}
                    await self.send_Telegram(
                        f"🏁 Bot iniciado — {datetime.now().strftime('%d/%m %H:%M')}\n"
                        f"{_emoji_modo.get(modo, '⚪')} Modo operación: *{modo}*"
                    )
                    await self.handle_menu()
                    await self.telegram_app.shutdown()

                loop.run_until_complete(_send_welcome())

                # run_polling en el mismo loop donde se creó la app
                loop.run_until_complete(
                    self.telegram_app.run_polling(
                        allowed_updates=["message", "callback_query"],
                        drop_pending_updates=True,
                        bootstrap_retries=-1,
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
        async def _send(bot, chat_id, text, markup):
            """Intenta con Markdown; si falla por parse error, reintenta sin parse_mode."""
            kwargs = {"chat_id": chat_id, "text": text}
            if markup is not None:
                kwargs["reply_markup"] = markup
            for mode in ("Markdown", None):
                try:
                    if mode:
                        kwargs["parse_mode"] = mode
                    else:
                        kwargs.pop("parse_mode", None)
                    msg = await bot.send_message(**kwargs)
                    return msg
                except BadRequest as e:
                    if mode and "parse" in str(e).lower():
                        continue
                    raise

        try:
            async with Bot(token=self.TOKEN) as bot:
                for CHAT_ID in self.userAuth:
                    if reply_markup is not None:
                        sent_message = await _send(bot, CHAT_ID, texto, reply_markup)
                        await self._save_message(sent_message, CHAT_ID)
                        return

                    elif hash_id is None:
                        sent_message = await _send(bot, CHAT_ID, texto, None)
                        await self._save_message(sent_message, CHAT_ID)
                        return

                    else:
                        botones = [
                            [
                                InlineKeyboardButton("✅ Aprobar", callback_data=f"aprobar|{hash_id}"),
                                InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar|{hash_id}"),
                            ]
                        ]
                        markup = InlineKeyboardMarkup(botones)
                        sent_message = await _send(bot, CHAT_ID, texto, markup)
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
                "intent": f"IA_{opt}",
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
                await self._flush_sell_actual()

            elif accion == "menu_buy":
                await query.edit_message_text(
                    "⬆️🟢 Has seleccionado *Oportunidades de Compra*.",
                    parse_mode="Markdown",
                )
                self.MostrarOpcionMenu_enTelegram = "Buy"
                await self._flush_buy_actual()

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
                await query.edit_message_text("🎯 Cargando performance…", parse_mode="Markdown")
                await self._send_performa()

            elif accion == "OrdersExec":
                self.MostrarOpcionMenu_enTelegram = "ListOrder"

                # se pasa el chat que solicitó la lista (opcional)
                await self.list_orders_exec(chat_id=update.effective_chat.id)

            elif accion == "botrtrader":
                await self.list_positions_BotCrypto(chat_id=update.effective_chat.id)

            elif accion == "alertas":
                alertas = DataHub.system_alerts[:]
                DataHub.system_alerts.clear()
                if not alertas:
                    await query.edit_message_text("🔕 Sin alertas pendientes.")
                else:
                    texto = "\n\n".join(alertas)
                    await query.edit_message_text(
                        f"🚨 *{len(alertas)} Alertas*\n\n{texto}",
                        parse_mode="Markdown",
                    )

            elif accion == "ia_ejecutar":
                trace_id = int(args[0])
                self.IaTrace.update_trace_estado(trace_id, estado="APROBADO")
                await query.edit_message_reply_markup(reply_markup=None)
                await query.edit_message_text(
                    f"✅ Propuesta IA aprobada (trace #{trace_id})\n_Ejecución manual por ahora — AUTONOMO pendiente._",
                    parse_mode="Markdown",
                )

            elif accion == "ia_diferir":
                trace_id = int(args[0])
                self.IaTrace.update_trace_estado(trace_id, estado="DIFERIDO")
                await query.edit_message_reply_markup(reply_markup=None)
                await query.edit_message_text(
                    f"⏸ Propuesta diferida (trace #{trace_id})",
                    parse_mode="Markdown",
                )

            elif accion == "fci_reset_blocked":
                from Class_BrowserFCI import BrowserFCI  # import diferido — evita ciclo

                BrowserFCI().reset_blocked()
                await query.edit_message_reply_markup(reply_markup=None)
                await query.edit_message_text("🔓 Bloqueo FCI liberado. El agente reintentará en el próximo ciclo.")

        except Exception as e:
            self.logger.error(f"handle_callback(): {e}\n{traceback.format_exc()}")

    async def handle_gains_capture_ok(self, update, context):
        """Handler /ok_SYMBOL — aprueba una propuesta GainsCapture pendiente."""
        try:
            text = update.message.text.strip()
            symbol = text.replace("/ok_", "").upper()
            state = self.gains_capture_state.get(symbol, {})
            if state.get("estado") != "pendiente_autorizacion":
                await update.message.reply_text(f"⚠️ {symbol}: sin propuesta GainsCapture pendiente.")
                return
            pendiente = state.get("pendiente", {})
            trama = DataHub.gains_capture_build_trama_sell(
                "Stock",
                pendiente["account"],
                symbol,
                pendiente["conid"],
                pendiente["lmt_price"],
                pendiente["qty"],
            )
            response = DataHub.preservation_send_order("Stock", trama)
            order_id = DataHub.preservation_extract_order_id(response)
            niveles_ejecutados = state.get("niveles_ejecutados", []) + [pendiente["nivel_roi"]]
            self.gains_capture_state[symbol] = {
                **state,
                "estado": "escalon_pendiente",
                "escalon_order_id": str(order_id) if order_id else None,
                "niveles_ejecutados": niveles_ejecutados,
                "pendiente": None,
                "last_check": datetime.now().isoformat(),
            }
            write_json_tmp("gains_capture_state.json", self.gains_capture_state)
            try:
                self.RepositorioOportunidades.insert_preservation_order(
                    pendiente["account"],
                    "Stock",
                    symbol,
                    pendiente["conid"],
                    str(order_id),
                    pendiente["lmt_price"],
                    float(pendiente["qty"]),
                    json.dumps(pendiente.get("det", {})),
                )
            except Exception as _e:
                self.logger.error(f"handle_gains_capture_ok({symbol}): insert → {_e}")
            await update.message.reply_text(
                f"✅ GainsCapture {symbol}: orden enviada — {pendiente['qty']} acc LMT ${pendiente['lmt_price']:.2f}"
            )
            logging.getLogger("GainsCapture").warning(
                f"GainsCapture({symbol}): aprobado por usuario → order_id={order_id}"
            )
        except Exception as e:
            self.logger.error(f"handle_gains_capture_ok(): {e}")

    async def handle_gains_capture_no(self, update, context):
        """Handler /no_SYMBOL — rechaza una propuesta GainsCapture pendiente."""
        try:
            text = update.message.text.strip()
            symbol = text.replace("/no_", "").upper()
            state = self.gains_capture_state.get(symbol, {})
            if state.get("estado") != "pendiente_autorizacion":
                await update.message.reply_text(f"⚠️ {symbol}: sin propuesta GainsCapture pendiente.")
                return
            self.gains_capture_state[symbol] = {**state, "estado": "normal", "pendiente": None}
            write_json_tmp("gains_capture_state.json", self.gains_capture_state)
            await update.message.reply_text(f"❌ GainsCapture {symbol}: propuesta cancelada.")
            logging.getLogger("GainsCapture").warning(f"GainsCapture({symbol}): rechazado por usuario")
        except Exception as e:
            self.logger.error(f"handle_gains_capture_no(): {e}")

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
        self.withdraw()
        ClassAgenteIA.__init__(self)
        Telegram.__init__(self)

        # colores
        self.bgcolor = "#1e1e2e"
        self.usercolor = "#cba6f7"
        self.botcolor = "#cdd6f4"
        self.fgcolor = "#cdd6f4"

        self.title("🤖 Asistente de Inversión")
        self.geometry("920x740+1000+100")
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

        # ── CONTENEDOR PRINCIPAL — dos columnas ──────────────────────────────
        main = tk.Frame(self, bg=self.bgcolor)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 0))

        # ── COLUMNA IZQUIERDA — teletipo decisiones autónomas ────────────────
        left = tk.Frame(main, bg="#0d0d1a", width=300)
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 4))
        left.pack_propagate(False)

        tk.Label(
            left,
            text="🤖 Decisiones Autónomas",
            bg="#0d0d1a",
            fg="#00BFFF",
            font=("Consolas", 8, "bold"),
            anchor="w",
        ).pack(fill=tk.X, padx=6, pady=(4, 2))

        self._feed_txt = tk.Text(
            left,
            bg="#0d0d1a",
            fg="#aaaaaa",
            font=("Consolas", 9),
            relief=tk.FLAT,
            wrap=tk.WORD,
            state="disabled",
            padx=6,
            pady=2,
        )
        self._feed_txt.tag_configure("BUY", foreground="#00FF66")
        self._feed_txt.tag_configure("SELL", foreground="#FF6B6B")
        self._feed_txt.tag_configure("HOLD", foreground="#AAAAAA")
        self._feed_txt.tag_configure("ALERTA", foreground="#FFB347")
        self._feed_txt.tag_configure("meta", foreground="#444466")
        self._feed_txt.pack(fill=tk.BOTH, expand=True)
        self._feed_rows = []
        self._feed_txt.bind("<Double-Button-1>", self._ia_feed_click)

        # separador vertical
        tk.Frame(main, bg="#2a2a3a", width=1).pack(side=tk.LEFT, fill=tk.Y)

        # ── COLUMNA DERECHA — chat ────────────────────────────────────────────
        right = tk.Frame(main, bg=self.bgcolor)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ── AREA CHAT ────────────────────────────────────────────────────────
        self.area_mensaje = scrolledtext.ScrolledText(
            right,
            wrap=tk.WORD,
            bg="#181825",
            fg=self.fgcolor,
            font=("Segoe UI", 11),
            relief=tk.FLAT,
            padx=16,
            pady=12,
            selectbackground="#45475a",
        )
        self.area_mensaje.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self.area_mensaje.tag_configure("usuario", foreground=self.usercolor, font=("Segoe UI", 11, "bold"))
        self.area_mensaje.tag_configure("asistente", foreground=self.botcolor, font=("Segoe UI", 11))
        self.area_mensaje.tag_configure("thinking", foreground="#6c7086", font=("Segoe UI", 11, "italic"))

        self._chat_messages = []
        self._chat_display = []
        _hist = read_json_tmp("chatbot_history.json")
        if _hist:
            self._chat_messages = _hist.get("messages", [])[-40:]
            self._chat_display = _hist.get("display", [])[-40:]
            self.area_mensaje.configure(state="normal")
            for _item in self._chat_display:
                self.area_mensaje.insert(tk.END, _item["text"] + "\n\n", _item["tag"])
        else:
            self.area_mensaje.insert(tk.END, "🤖  ¿En qué puedo ayudarte?\n\n", "asistente")
        self.area_mensaje.configure(state="disabled")
        self.area_mensaje.yview(tk.END)

        # ── INPUT ────────────────────────────────────────────────────────────
        footer = tk.Frame(right, bg=self.bgcolor)
        footer.pack(fill=tk.X, pady=(0, 4))

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
        self.after(400, self._ia_feed_refresh)

    def _ia_feed_refresh(self):
        try:
            ia_db = IaTraceScreen()
            rows = ia_db.select_trace(limit=20)
            self._feed_rows = rows
            self._feed_txt.configure(state="normal")
            self._feed_txt.delete("1.0", tk.END)
            if not rows:
                self._feed_txt.insert(tk.END, "  (sin decisiones aún)\n", "meta")
            for r in rows:
                ts = str(r.get("timestamp", ""))[:16]
                dec = r.get("decision", "HOLD")
                sym = r.get("simbolo", "") or ""
                monto = r.get("monto", 0) or 0
                motivo = r.get("motivo", "") or ""
                linea1 = f"[{dec}] {sym}  ${monto:.0f}  {ts}\n"
                linea2 = f"  {motivo[:80]}\n\n"
                tag = dec if dec in ("BUY", "SELL", "HOLD", "ALERTA") else "meta"
                self._feed_txt.insert(tk.END, linea1, tag)
                self._feed_txt.insert(tk.END, linea2, "meta")
            self._feed_txt.configure(state="disabled")
            self._feed_txt.yview(tk.END)
        except Exception as e:
            self.logger.error(f"_ia_feed_refresh: {e}")
        self.after(60_000, self._ia_feed_refresh)

    def _ia_feed_click(self, event):
        try:
            line_no = int(self._feed_txt.index(f"@{event.x},{event.y}").split(".")[0])
            idx = (line_no - 1) // 3
            if not self._feed_rows or idx < 0 or idx >= len(self._feed_rows):
                return
            r = self._feed_rows[idx]
            ts = str(r.get("timestamp", ""))[:19]
            dec = r.get("decision", "HOLD")
            sym = r.get("simbolo", "") or ""
            monto = float(r.get("monto", 0) or 0)
            motivo = r.get("motivo", "") or ""
            vehiculo = r.get("vehiculo", "") or ""
            estado = r.get("estado", "") or ""
            gates_raw = r.get("gates_ok") or {}
            if isinstance(gates_raw, (str, bytes)):
                try:
                    gates_raw = json.loads(gates_raw)
                except Exception:
                    gates_raw = {}

            mkt = self.Market.select_feed_context(sym, self.account) if sym else {}
            pos = self.Market.select_last_position(sym, self.account) if sym else {}

            last_price = float(mkt.get("lastPrice") or 0)
            short_name = mkt.get("shortName") or sym
            sector = mkt.get("sector") or "—"
            country = mkt.get("country") or "—"
            inst_score = mkt.get("inst_score")
            inst_pct = mkt.get("inst_ownership_pct")
            fh_count = mkt.get("fh_count")
            consenso_tag = mkt.get("consenso_tag") or "—"
            consenso_suma = mkt.get("consenso_suma")

            stock_qty = float(pos.get("stock") or 0)
            basico = float(pos.get("basico") or 0)
            valor_pos = stock_qty * last_price if last_price > 0 else 0
            roi_pct = ((last_price - basico) / basico * 100) if basico > 0 and last_price > 0 else None
            qty_sug = max(1, int(monto / last_price)) if last_price > 0 and monto > 0 and vehiculo == "Stock" else (
                (monto / last_price) if last_price > 0 and monto > 0 else 0
            )

            def _fmt(v, decimals=2, suffix=""):
                if v is None:
                    return "—"
                return f"{v:.{decimals}f}{suffix}"

            gates_lines = []
            for k, v in (gates_raw.items() if isinstance(gates_raw, dict) else []):
                gates_lines.append(f"  {'✓' if v else '✗'} {k}")
            gates_str = "\n".join(gates_lines) if gates_lines else "  —"

            sep = "─" * 48
            lineas = [
                f"{sep}",
                f"  [{dec}] {short_name} ({sym})   ${monto:,.0f}",
                f"  {ts}   Cuenta: {vehiculo}   Estado: {estado}",
                f"{sep}",
            ]

            if stock_qty > 0 or basico > 0:
                roi_str = f"  ROI: {roi_pct:+.1f}%" if roi_pct is not None else ""
                lineas += [
                    "💰 POSICIÓN ACTUAL",
                    f"  Precio actual:  ${last_price:,.2f}    Costo prom: ${basico:,.2f}",
                    f"  Tenencia:       {stock_qty:,.0f} acc   Valor: ${valor_pos:,.0f}{roi_str}",
                ]
            elif last_price > 0:
                lineas += [
                    "💰 PRECIO ACTUAL",
                    f"  ${last_price:,.2f}  (sin posición registrada)",
                ]
            lineas.append("")

            lineas += ["🎯 ACCIÓN SUGERIDA"]
            if dec == "BUY":
                qty_txt = f"~{qty_sug} acc @ ${last_price:,.2f}" if qty_sug > 0 else ""
                lineas.append(f"  COMPRAR  ${monto:,.0f}  {qty_txt}")
                if stock_qty == 0:
                    lineas.append("  ⚠️  Sin posición previa — evaluar capital disponible antes")
                else:
                    lineas.append("  ⚠️  Velar deuda: si no hay cash libre, vender posición débil primero")
            elif dec == "SELL":
                qty_txt = f"~{qty_sug} acc @ ${last_price:,.2f}" if qty_sug > 0 else ""
                pnl_str = f"  PnL est: ${(last_price - basico) * qty_sug:+,.0f}" if basico > 0 and qty_sug > 0 else ""
                lineas.append(f"  VENDER   ${monto:,.0f}  {qty_txt}{pnl_str}")
            else:
                lineas.append(f"  {dec}  ${monto:,.0f}")
            lineas.append("")

            if mkt:
                lineas += [
                    "📊 CONTEXTO MERCADO",
                    f"  Sector: {sector}   País: {country}",
                    f"  Consenso: {consenso_tag}" + (f" ({consenso_suma} votos)" if consenso_suma else ""),
                    f"  Inst Score: {_fmt(inst_score)}   13F Inst: {fh_count or '—'}   Inst %: {_fmt(inst_pct)}%",
                    "",
                ]

            if gates_raw:
                lineas += [
                    "🔍 GATES",
                    gates_str,
                    "",
                ]

            lineas += [
                "📝 RAZONAMIENTO",
                f"  {motivo}",
                sep,
            ]

            self._agregar_mensaje("\n".join(lineas), tag="asistente")
        except Exception as e:
            self.logger.error(f"_ia_feed_click: {e}")

    def _enviar(self, event=None):
        texto = self.entrada.get().strip()
        if not texto:
            return
        self._agregar_mensaje(f"👤  {texto}", tag="usuario")
        self._agregar_mensaje("⏳  Analizando...", tag="thinking")
        self.entrada.delete(0, tk.END)
        self.entrada.config(state="disabled")

        def _worker():
            respuesta = ""
            try:
                contexto = self._build_contexto()
                self._chat_messages.append({"role": "user", "content": texto})
                respuesta = self._consultar_claude(texto, contexto, messages=self._chat_messages)
                self._chat_messages.append({"role": "assistant", "content": respuesta})
                self._chat_display.append({"text": f"👤  {texto}", "tag": "usuario"})
                self._chat_display.append({"text": f"🤖  {respuesta}", "tag": "asistente"})
                write_json_tmp(
                    "chatbot_history.json",
                    {
                        "messages": self._chat_messages[-40:],
                        "display": self._chat_display[-40:],
                    },
                )
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
        if modulo is None:
            return
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
                        "timestamp": timestamp.strftime("%d-%b,%H:%M"),
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

            sep = "─" * 37
            lines = [f"{'Sym':<7} {'Side':<4} {'Qty':>8} {'@Precio':>15}", sep]
            for o in orders[:limit]:
                if not isinstance(o, dict):
                    continue
                sym = (o.get("symbol") or "")[:7]
                side = o.get("side") or ""
                qty = o.get("quantity") or 0
                price = f"@{o.get('price') or 0}"
                ts = o.get("timestamp") or ""
                status = (o.get("status") or "")[:8]
                lines.append(f"{sym:<7} {side:<4} {qty:>8} {price:>15}")
                lines.append(f"  {ts:<14} {status:>18}")
                lines.append(sep)

            message = f"🟢🔴 *Trader recent (-7 days):*\n"
            message += f"```\n"
            message += "\n".join(lines)
            message += "```"

            await self.send_Telegram(message, None)
        except Exception as e:
            print(f"list_orders_exec(): {e}")

    async def _send_performa(self):
        """Envía resumen de G/P y dividendos acumulados por vehículo."""
        try:
            performa = IPerformance()
            rows, ix = performa.select_resumen_por_vehiculo(account=None)
            if not rows:
                await self.send_Telegram("ℹ️ Sin datos de performance.", None)
                return
            sep = "─" * 37
            msg = "```\n"
            msg += f"{'Vehículo':<10} {'30d':>8} {'60d':>8} {'90d':>8}\n"
            msg += sep + "\n"
            tot30 = tot60 = tot90 = 0.0
            for row in rows:
                d = dict(zip(ix, row))
                veh = (d.get("vehiculo") or "")[:10]
                d30 = float(d.get("d30") or 0)
                d60 = float(d.get("d60") or 0)
                d90 = float(d.get("d90") or 0)
                tot30 += d30
                tot60 += d60
                tot90 += d90
                msg += f"{veh:<10} {d30:>+8,.0f} {d60:>+8,.0f} {d90:>+8,.0f}\n"
            msg += sep + "\n"
            msg += f"{'TOTAL':<10} {tot30:>+8,.0f} {tot60:>+8,.0f} {tot90:>+8,.0f}\n"
            msg += "```"
            await self.send_Telegram(f"🎯 *Performance Acumulada*\n{msg}", None)
        except Exception as e:
            self.logger.error(f"_send_performa(): {e}")

    async def _flush_sell_actual(self):
        """Envía las oportunidades de venta actuales al seleccionar el modo Sell."""
        try:
            df_sell = self.readCSV_sell(file="csv_datosIA_sell", filtrar=False)
            if df_sell is None or df_sell.empty:
                return
            await self.evaluar_oportunidades_sell_con_IA(
                df_sell=df_sell,
                umbral_venta=self.Sellumbral,
                umbral_observacion=self.SellumbralObserv,
            )
        except Exception as e:
            self.logger.error(f"_flush_sell_actual(): {e}")

    async def _flush_buy_actual(self):
        """Envía las oportunidades de compra actuales al seleccionar el modo Buy."""
        try:
            df_buy = self.readCSV_buy(file="csv_datosIA_buy", filtrar=False)
            if df_buy is None or df_buy.empty:
                return
            await self.evaluar_oportunidades_buy_con_IA(
                df_buy=df_buy,
                umbral_compra=self.Buyumbral,
                umbral_observacion=self.BuyumbralObserv,
            )
        except Exception as e:
            self.logger.error(f"_flush_buy_actual(): {e}")

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

            for nombre, cfg in AGENTES_SCHEDULE.items():
                intervalo = cfg["intervalo"]
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
                agent_mgr = AgentManager(self.account, self.vehiculo)
                while True:
                    self.exec_modulo_async(self.Agente_ManagerSell())
                    self.exec_modulo_async(self.Agente_ManagerBuy())
                    self.exec_modulo_async(self.Agente_ManagerTop10())
                    agent_mgr.run_loop()
                    self.exec_modulo_async(self.Agente_ManagerPreservation())
                    self.exec_modulo_async(self.Agente_GainsCapture())
                    self.Agente_Sentimiento()
                    self.Agente_InterpreteSentimiento()
                    self.Agente_ExtractoBBVA()
                    self.Agente_ClaudeIA()
                    self.Agente_SyncOrders()
                    self.Agente_OrderEodCleanup()
                    self.exec_modulo_async(self._flush_system_alerts())
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
            agent_mgr = AgentManager(self.account, self.vehiculo)
            agent_mgr.register_threads()
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

            mensaje += f"{'Métrica':<18} {'Valor':>12}\n"
            mensaje += f"{'-' * 37}\n"
            mensaje += f"{'Profit'          :<18} {row['Profit']:>12.2f}\n"
            mensaje += f"{'ROI (%)'         :<18} {row['%Roi'] * 100:>12.2f}\n"
            _cant = f"{row['CantidadSell']:.1f}/{row['Disponible']:.1f}"
            mensaje += f"{'Cant Sell'        :<18} {_cant:>12}\n"
            mensaje += f"{'CostoAcum'        :<18} {row['CostoCum']:>12.2f}\n"
            mensaje += f"{'Prec. posVenta'   :<18} {row['PosAvgCost']:>12.4f}\n"
            mensaje += f"{'Pos. posVenta'    :<18} {row['PosPosition']:>12.4f}\n"
            mensaje += f"{'CostoB posVenta'  :<18} {row['PosCostobase']:>12.2f}\n"
            mensaje += f"{'Valoracion'       :<18} {""}\n"

            confianza = row.get("confianza") if modo != "ia" else confianza
            if confianza is not None:
                mensaje += f"{'-' * 37}\n"
                mensaje += f"{'Confianza IA'     :<18} {confianza:>12.1%}\n"

            tag, suma = self._consenso_info(symbol)
            if tag:
                mensaje += f"{'-' * 37}\n"
                mensaje += f"{'Consenso'         :<18} {tag} ({suma:+d})\n"

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
                # en casos de existir, elimina hash_id anterior y notifica si el modo está activo
                if existe:
                    self.sell_enviados.pop(hash_id, None)
                    insert = True

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

            sent_features = MarketScreen().load_sentiment_features(self.account)
            df = self.IAsell.enriquecer_con_sentimiento(df, sent_features)

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
        def _tecnicos(row):
            raw = row.get("datos_tecnicos") or row.get("Datostecnicos")
            if not raw:
                return None, {}
            try:
                d = json.loads(raw) if isinstance(raw, str) else raw
                diaria = d.get("diaria", {})
                return diaria.get("rsi"), diaria.get("ema(20,50,100,200)", {})
            except Exception:
                return None, {}

        def _score_hibrido(o):
            confianza = o.get("confianza") or 0
            rsi, emas = _tecnicos(o)
            rsi_score = max(0.0, (rsi - 60) / 40) if rsi is not None else 0.0
            e20 = emas.get("EMA020") or 0
            e50 = emas.get("EMA050") or 0
            e100 = emas.get("EMA100") or 0
            if e20 > 0 and e50 > 0 and e100 > 0 and e20 > e50 > e100:
                tendencia = 1.0
            elif e20 > 0 and e50 > 0 and e20 > e50:
                tendencia = 0.5
            else:
                tendencia = 0.0
            return (confianza * 0.50) + (rsi_score * 0.30) + (tendencia * 0.20)

        def _es_candidato(o):
            if o.get("confianza") is not None:
                return _score_hibrido(o) >= 0.25
            return (o.get("%Roi") or 0) > DataHub.Toleranciasell

        try:
            if not self.sell_enviados:
                return []
            oportunidades = [o for o in self.sell_enviados.values() if _es_candidato(o)]
            if not oportunidades:
                return []
            return sorted(oportunidades, key=_score_hibrido, reverse=True)[:top]
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

            confianza = row.get("confianza") if modo != "ia" else confianza
            if confianza is not None:
                mensaje += f"{'-' * 37}\n"
                mensaje += f"{'Confianza IA'     :<18} {confianza:>12.1%}\n"

            tag, suma = self._consenso_info(symbol)
            if tag:
                mensaje += f"{'-' * 37}\n"
                mensaje += f"{'Consenso':<12} {tag} ({suma:+d})\n"

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
                # En caso de existir, elimina hash_id anterior y notifica si el modo está activo
                if existe:
                    self.buy_enviados.pop(hash_id, None)
                    insert = True

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

            sent_features = MarketScreen().load_sentiment_features(self.account)
            df = self.IAbuy.enriquecer_con_sentimiento(df, sent_features)

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
        def _tecnicos(row):
            raw = row.get("Datostecnicos")
            if not raw:
                return None, {}
            try:
                d = json.loads(raw) if isinstance(raw, str) else raw
                diaria = d.get("diaria", {})
                return diaria.get("rsi"), diaria.get("ema(20,50,100,200)", {})
            except Exception:
                return None, {}

        def _score_hibrido(o):
            confianza = o.get("confianza") or 0
            rsi, emas = _tecnicos(o)
            rsi_score = max(0.0, (60 - rsi) / 60) if rsi is not None else 0.0
            e20 = emas.get("EMA020") or 0
            e50 = emas.get("EMA050") or 0
            e100 = emas.get("EMA100") or 0
            if e20 > 0 and e50 > 0 and e100 > 0 and e20 > e50 > e100:
                tendencia = 1.0
            elif e20 > 0 and e50 > 0 and e20 > e50:
                tendencia = 0.5
            else:
                tendencia = 0.0
            return (confianza * 0.50) + (rsi_score * 0.30) + (tendencia * 0.20)

        def _es_candidato(o):
            if o.get("confianza") is not None:
                return _score_hibrido(o) >= 0.25
            return (
                (o.get("score") or 0) >= DataHub.MinScoreBuy
                and (o.get("ganancia_precio") or 0) >= DataHub.MinGananciaPrecio
            )

        try:
            if not self.buy_enviados:
                return []
            oportunidades = [o for o in self.buy_enviados.values() if _es_candidato(o)]
            if not oportunidades:
                return []
            return sorted(oportunidades, key=_score_hibrido, reverse=True)[:top]
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
