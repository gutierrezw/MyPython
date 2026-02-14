"""
Class_BotCryptoUI.py - Bot de Trading Crypto Spot (UI + Lógica)

Módulo unificado que contiene:
- TradingBotSpot: Bot lógico por símbolo (estrategia + indicadores)
- OrderManager: Gestión de órdenes y ejecución
- BotManager: Coordinador de múltiples bots
- BotCryptoUI: Panel principal para pestaña BotCrypto
- WidgetBotSymbol: Widget individual por símbolo

Uso:
    from Class_BotCryptoUI import BotCryptoUI
    bot_ui = BotCryptoUI(parent_frame, colors, repositorio)
    bot_ui.inicializar()
"""

from Modulos_python import (
    tk,
    ttk,
    threading,
    traceback,
    time,
    json,
    pd,
    datetime,
    Figure,
    FigureCanvasTkAgg,
    logging,
    multiprocessing,
)
from Modulos_Mysql import BDsystem, RepositorioOportunidadesBuySell
from Modulos_Utilitarios import calcular_indicadores_df
from Class_ApiBinnace import BinanceClient, BinanceStreamClient
from Class_customer import DataHub, MyMessageBox
import webview


def _webview_process(title, url, width, height):
    """Función top-level para multiprocessing (pywebview requiere main thread)"""
    webview.create_window(title, url=url, width=width, height=height)
    webview.start()


# =============================================================================
# BOT LÓGICO: TradingBotSpot
# =============================================================================
class TradingBotSpot:
    """
    Bot lógico para trading Spot en Binance.
    Evalúa un único símbolo y decide acciones.
    """

    # =========================
    # INIT
    # =========================
    def __init__(self, symbol: str, interval: str, strategy_config: dict, risk_config: dict, state_repo, order_manager):
        self.symbol = symbol
        self.interval = interval

        self.strategy_cfg = strategy_config
        self.risk_cfg = risk_config

        self.state_repo = state_repo
        self.order_manager = order_manager
        self.logger = logging.getLogger("BotCryptoUI")

        # ----- Estado interno -----
        self.state = {
            "position": "NONE",  # NONE | LONG
            "entry_price": None,
            "position_qty": 0.0,
            "remaining_qty": 0.0,
            "stop_loss": None,
            "tp1_done": False,
            "tp2_done": False,
            # Trailing stop (se activa después de TP1)
            "trailing_active": False,
            "trail_high": None,
            "trailing_stop": None,
        }

        # ----- Datos de mercado -----
        self.df = None
        self.last_candle_ts = None

    # =========================
    # INTERFAZ PUBLICA
    # =========================
    def on_market_data(self, candle: dict) -> None:
        """
        Recibe vela cerrada (WS o scheduler).
        """
        self._update_dataframe(candle)

    def _evaluate_buy_conditions(self):
        rsi = self.df["rsi"].iloc[-1]
        macd = self.df["macd"].iloc[-1]
        macd_signal = self.df["macd_signal"].iloc[-1]
        ema_fast = self.df["ema_fast"].iloc[-1]
        ema_slow = self.df["ema_slow"].iloc[-1]
        price = self.df["Close"].iloc[-1]

        conditions = {
            "trend_ok": {
                "value": macd > macd_signal and ema_fast > ema_slow,
                "detail": f"MA {macd:.6f} > {macd_signal:.6f} " f"& EMf {ema_fast:.6f} > EMs {ema_slow:.6f}",
            },
            "rsi_ok": {
                "value": rsi < self.strategy_cfg["rsi_sell"],
                "detail": f"RSI {rsi:.2f} < {self.strategy_cfg['rsi_sell']}",
            },
            "price_ok": {"value": price > ema_fast, "detail": f"Price {price:.6f} > EMAf {ema_fast:.6f}"},
        }

        return conditions

    def evaluate(self) -> str:
        """
        Decide acción a tomar.
        Retorna: BUY | TP1 | TP2 | EXIT | HOLD
        """
        # Siempre evaluar condiciones para que la UI las muestre
        conditions = self._evaluate_buy_conditions() if self.df is not None and len(self.df) >= 50 else {}

        if not self._is_in_position():
            if self._should_buy():
                return "BUY", conditions
            return "HOLD", conditions

        # Ya en posición
        price = self._last_price()

        if not self.state["tp1_done"] and self._should_take_tp1(price):
            return "TP1", conditions

        # Post-TP1: actualizar trailing y verificar exit
        if self.state["tp1_done"]:
            self._update_trailing(price)
            if self._should_trail_exit(price):
                return "TRAIL_EXIT", conditions

        if self._should_exit(price):
            return "EXIT", conditions

        return "HOLD", conditions

    def on_order_update(self, execution_report: dict) -> None:
        """
        Actualización REAL de orden desde WebSocket.
        """
        self._update_state_on_fill(execution_report)
        self._persist_state()

    def restore_state(self) -> None:
        """
        Reconstruye estado desde storage al iniciar.
        """
        if self.state_repo:
            saved = self.state_repo.load_state(self.symbol)
            if saved:
                self.state.update(saved)

    def get_public_state(self) -> dict:
        """
        Estado resumido para UI / logs.
        """
        return {
            "symbol": self.symbol,
            "position": self.state["position"],
            "entry_price": self.state["entry_price"],
            "remaining_qty": self.state["remaining_qty"],
            "tp1_done": self.state["tp1_done"],
            "tp2_done": self.state["tp2_done"],
            "stop_loss": self.state["stop_loss"],
            "trailing_active": self.state["trailing_active"],
            "trail_high": self.state["trail_high"],
            "trailing_stop": self.state["trailing_stop"],
        }

    def get_indicators(self) -> dict:
        """
        Retorna indicadores técnicos para la UI.
        """
        if self.df is None or len(self.df) < 2:
            return {}

        try:
            return {
                "rsi": float(self.df["rsi"].iloc[-1]) if "rsi" in self.df.columns else None,
                "macd": float(self.df["macd"].iloc[-1]) if "macd" in self.df.columns else None,
                "macd_signal": float(self.df["macd_signal"].iloc[-1]) if "macd_signal" in self.df.columns else None,
                "ema_fast": float(self.df["ema_fast"].iloc[-1]) if "ema_fast" in self.df.columns else None,
                "ema_slow": float(self.df["ema_slow"].iloc[-1]) if "ema_slow" in self.df.columns else None,
                "last_price": self._last_price(),
            }
        except Exception:
            return {}

    # =========================
    # ESTRATEGIA (PRIVADO)   gwi001
    # =========================
    def _should_buy(self) -> bool:
        """RSI
        ┌───────────────────┐
        │ <35  | 35–65 | >65│
        └───────────────────┘
            │       │      ✖
            │       │
        trend_ok   trend_ok
        price_ok   price_ok
            │       │
        BUY     BUY"""

        if self.df is None or len(self.df) < 50:
            return False

        rsi = self.df["rsi"].iloc[-1]
        macd = self.df["macd"].iloc[-1]
        macd_signal = self.df["macd_signal"].iloc[-1]
        ema_fast = self.df["ema_fast"].iloc[-1]
        ema_slow = self.df["ema_slow"].iloc[-1]
        price = self.df["Close"].iloc[-1]

        # Confirmación de tendencia o giro alcista
        trend_ok = macd > macd_signal and ema_fast > ema_slow

        # Zona operable (evita sobrecompra)
        rsi_ok = rsi < self.strategy_cfg["rsi_sell"]

        # El precio confirma movimiento a favor
        price_ok = price > ema_fast

        ok = trend_ok and rsi_ok and price_ok

        return ok

    def _should_exit(self, price: float) -> bool:
        # Stop loss
        if self.state["stop_loss"] is None:
            return False

        if price <= self.state["stop_loss"]:
            return True

        rsi = self.df["rsi"].iloc[-1]
        return rsi > self.strategy_cfg["rsi_sell"]

    # =========================
    # TAKE PROFIT (PRIVADO)
    # =========================
    def _should_take_tp1(self, price: float) -> bool:
        if self.state["entry_price"] is None:
            return False

        target = self.state["entry_price"] * (1 + self.risk_cfg["tp1_pct"])
        return price >= target

    def _calc_atr14(self) -> float:
        """ATR simplificado: promedio del rango (High-Low) de las últimas 14 velas"""
        if self.df is None or len(self.df) < 14:
            return 0.0
        return (self.df["High"] - self.df["Low"]).tail(14).mean()

    def _update_trailing(self, price: float) -> None:
        """Actualiza trail_high y trailing_stop. Solo sube, nunca baja."""
        if not self.state["trailing_active"]:
            return
        if self.state["trail_high"] is None:
            return
        if price > self.state["trail_high"]:
            self.state["trail_high"] = price
            atr = self._calc_atr14()
            trail_mult = self.risk_cfg.get("trail_mult", 1.5)
            new_stop = price - (trail_mult * atr)
            # Solo sube
            if self.state["trailing_stop"] is None or new_stop > self.state["trailing_stop"]:
                self.state["trailing_stop"] = new_stop
                self.logger.info(
                    f"{self.symbol}: TRAIL actualizado | high={price:.6f} stop={new_stop:.6f} ATR={atr:.6f}"
                )

    def _should_trail_exit(self, price: float) -> bool:
        """Retorna True si el precio cae al trailing stop después de TP1"""
        if not self.state["trailing_active"]:
            return False
        if self.state["trailing_stop"] is None:
            return False
        return price <= self.state["trailing_stop"]

    # =========================
    # RIESGO (PRIVADO)
    # =========================
    def _calc_position_size(self, price: float, capital_usdt: float) -> float:
        risk_amount = capital_usdt * self.risk_cfg["risk_per_trade"]
        return risk_amount / price

    def _calc_stop_loss(self, price: float) -> float:
        return price * (1 - self.risk_cfg["stop_loss_pct"])

    # =========================
    # ESTADO (PRIVADO)
    # =========================
    def _update_state_on_fill(self, msg: dict) -> None:
        status = msg["X"]
        side = msg["S"]
        filled_qty = float(msg["l"])
        price = float(msg["L"])

        if status not in ("PARTIALLY_FILLED", "FILLED"):
            return

        if side == "BUY":
            self.state["position"] = "LONG"
            self.state["entry_price"] = price
            self.state["position_qty"] += filled_qty
            self.state["remaining_qty"] += filled_qty
            self.state["stop_loss"] = self._calc_stop_loss(price)

        elif side == "SELL":
            self.state["remaining_qty"] -= filled_qty

            if self.state["remaining_qty"] <= 0:
                self._reset_position_state()

    def _reset_position_state(self):
        self.state = {
            "position": "NONE",
            "entry_price": None,
            "position_qty": 0.0,
            "remaining_qty": 0.0,
            "stop_loss": None,
            "tp1_done": False,
            "tp2_done": False,
            "trailing_active": False,
            "trail_high": None,
            "trailing_stop": None,
        }

    def _persist_state(self):
        if self.state_repo:
            self.state_repo.save_state(self.symbol, self.state)

    def _is_in_position(self) -> bool:

        # Detectar dust: si el valor actual de la posición es menor a $5, limpiar estado
        qty = self.state.get("remaining_qty", 0) or 0
        price = self._last_price() if self.df is not None else (self.state.get("entry_price", 0) or 0)
        if qty > 0 and price > 0 and (price * qty) < 5.0:
            logging.getLogger("BotCryptoUI").warning(
                f"{self.symbol}: Dust detectado (${price * qty:.2f}), limpiando posición"
            )
            self.state["position"] = "NONE"
            self.state["entry_price"] = None
            self.state["remaining_qty"] = 0.0
            self.state["tp1_done"] = False
            self.state["tp2_done"] = False
            self.state["trailing_active"] = False
            self.state["trail_high"] = None
            self.state["trailing_stop"] = None
            self._persist_state()
            return False

        return self.state["position"] == "LONG"

    # =========================
    # MARKET DATA (PRIVADO)
    # =========================
    def _update_dataframe(self, candle: dict):
        """
        Actualiza DF con nueva vela cerrada y recalcula indicadores.
        """
        if self.df is None:
            return

        new_row = pd.DataFrame(
            [
                {
                    "Open": candle["open"],
                    "High": candle["high"],
                    "Low": candle["low"],
                    "Close": candle["close"],
                    "Volume": candle["volume"],
                }
            ]
        )

        self.df = pd.concat([self.df, new_row], ignore_index=True)

        # Mantener máximo 500 velas
        if len(self.df) > 500:
            self.df = self.df.tail(500).reset_index(drop=True)

        self.calcular_indicadores()

    def calcular_indicadores(self):
        """
        Calcula RSI, MACD, EMA rápida/lenta sobre el DataFrame.
        Usa calcular_indicadores_df() de Modulos_Utilitarios (función unificada).
        """
        if self.df is None or len(self.df) < 30:
            return

        calcular_indicadores_df(self.df)

    def calcular_scoring(self) -> dict:
        """
        Calcula score técnico de -7 a +7 para priorización de activos.
        Componentes: RSI (-1 a +2), MACD (-2 a +2), EMA (-2 a +2), Volatilidad (-1 a +1).
        """
        resultado = {
            "score_total": 0,
            "score_rsi": 0,
            "score_macd": 0,
            "score_ema": 0,
            "score_vol": 0,
            "prioridad": "BLOQUEADO",
            "permitir_compra": False,
        }

        if self.df is None or len(self.df) < 30 or "rsi" not in self.df.columns:
            return resultado

        try:
            rsi = self.df["rsi"].iloc[-1]
            rsi_prev = self.df["rsi"].iloc[-2]
            macd = self.df["macd"].iloc[-1]
            macd_signal = self.df["macd_signal"].iloc[-1]
            macd_prev = self.df["macd"].iloc[-2]
            macd_signal_prev = self.df["macd_signal"].iloc[-2]
            ema_fast = self.df["ema_fast"].iloc[-1]
            ema_slow = self.df["ema_slow"].iloc[-1]
            price = self.df["Close"].iloc[-1]

            # --- RSI (-1 a +2) ---
            score_rsi = 0
            if rsi_prev < 30 and rsi >= 30:
                score_rsi = 2  # cruzando 30 hacia arriba
            elif rsi > 50 and rsi < 70:
                score_rsi = 1  # zona alcista sana
            elif rsi >= 70:
                score_rsi = -1  # sobrecompra

            # --- MACD (-2 a +2) ---
            score_macd = 0
            if macd_prev <= macd_signal_prev and macd > macd_signal:
                score_macd = 2  # cruce alcista
            elif macd > macd_signal:
                score_macd = 1  # MACD sobre signal
            elif macd_prev >= macd_signal_prev and macd < macd_signal:
                score_macd = -2  # cruce bajista
            elif macd < macd_signal:
                score_macd = -1  # MACD bajo signal

            # --- EMA (-2 a +2) ---
            score_ema = 0
            if price > ema_slow:
                score_ema += 2  # precio sobre EMA lenta
            elif price < ema_slow:
                score_ema = -2  # precio bajo EMA lenta
            if ema_fast > ema_slow:
                score_ema = min(score_ema + 1, 2)  # EMA rápida sobre lenta

            # --- Volatilidad ATR (-1 a +1) ---
            score_vol = 0
            if "High" in self.df.columns and "Low" in self.df.columns:
                atr = (self.df["High"] - self.df["Low"]).tail(14).mean()
                atr_pct = (atr / price) * 100 if price > 0 else 0
                if 0.5 <= atr_pct <= 3.0:
                    score_vol = 1  # volatilidad saludable
                elif atr_pct > 5.0:
                    score_vol = -1  # volatilidad extrema

            total = score_rsi + score_macd + score_ema + score_vol

            # Clasificación
            if total >= 5:
                prioridad = "Alta"
            elif total >= 3:
                prioridad = "Media"
            elif total >= 1:
                prioridad = "Revisión"
            else:
                prioridad = "Bloqueado"

            resultado = {
                "score_total": total,
                "score_rsi": score_rsi,
                "score_macd": score_macd,
                "score_ema": score_ema,
                "score_vol": score_vol,
                "prioridad": prioridad,
                "permitir_compra": total >= 3,
                "indicadores": {
                    "rsi": round(rsi, 2),
                    "macd": round(macd, 8),
                    "macd_signal": round(macd_signal, 8),
                    "ema_fast": round(ema_fast, 6),
                    "ema_slow": round(ema_slow, 6),
                    "price": round(price, 6),
                },
            }
        except Exception as e:
            self.logger.error(f"calcular_scoring({self.symbol}): {e}")

        return resultado

    def _last_price(self) -> float:
        return self.df["Close"].iloc[-1]


# =============================================================================
# GESTOR DE ÓRDENES: OrderManager
# =============================================================================
class OrderManager:
    """
    Gestiona órdenes Spot:
    - registra órdenes enviadas por REST
    - procesa executionReport vía WebSocket
    - enruta eventos al bot correcto
    """

    def __init__(self):
        # orderId -> metadata
        self.orders = {}

        # symbol -> TradingBotSpot
        self.bots = {}

    # =========================
    # REGISTRO
    # =========================
    def register_bot(self, symbol: str, bot):
        """
        Registra un bot por símbolo.
        """
        self.bots[symbol] = bot

    def register_order(self, symbol: str, order_id: int, intent: str):
        """
        Registra una orden enviada por REST.
        """
        self.orders[order_id] = {"symbol": symbol, "intent": intent}

    # =========================
    # WEBSOCKET HANDLER
    # =========================
    def on_execution_report(self, msg: dict):
        """
        Entrada única desde WebSocket user data stream.
        """
        if msg.get("e") != "executionReport":
            return

        order_id = msg["i"]
        symbol = msg["s"]

        # Orden no registrada (re-sync o manual)
        if order_id not in self.orders:
            self._handle_unknown_order(msg)
            return

        intent = self.orders[order_id]["intent"]
        bot = self.bots.get(symbol)

        if not bot:
            return

        # Enriquecemos el mensaje con intent
        msg["intent"] = intent

        # Notificamos al bot
        bot.on_order_update(msg)

        # Limpieza si terminó
        if msg["X"] in ("FILLED", "CANCELED", "REJECTED", "EXPIRED"):
            self.orders.pop(order_id, None)

    # =========================
    # MANEJO DE ERRORES
    # =========================
    def _handle_unknown_order(self, msg: dict):
        """
        Orden no registrada (ej: restart).
        """
        pass


# =============================================================================
# GESTOR DE CAPITAL: CapitalManager
# =============================================================================
class CapitalManager:
    """
    Gestiona capital disponible para el bot.
    Rastrea capital total, reservado y disponible.
    """

    def __init__(self, capital_total: float):
        self.capital_total = capital_total
        self.capital_reservado = 0.0
        self.logger = logging.getLogger("BotCryptoUI")

    def get_available_capital(self) -> float:
        return self.capital_total - self.capital_reservado

    def reserve(self, amount: float):
        self.capital_reservado += amount
        self.logger.info(f"Capital reservado: {amount:.2f} | disponible: {self.get_available_capital():.2f}")

    def release(self, amount: float):
        self.capital_reservado = max(0.0, self.capital_reservado - amount)
        self.logger.info(f"Capital liberado: {amount:.2f} | disponible: {self.get_available_capital():.2f}")


# =============================================================================
# COORDINADOR: BotManager
# =============================================================================
class BotManager:
    """
    Coordina múltiples TradingBotSpot.
    Ejecuta órdenes Spot vía REST según decisiones de los bots.
    """

    def __init__(
        self,
        spot_client,
        order_manager,
        capital_manager,
        env="TESTNET",
        on_trade_complete=None,
        on_trade_booktrading=None,
    ):
        self.spot_client = spot_client
        self.order_manager = order_manager
        self.capital_manager = capital_manager
        self.env = env
        self.on_trade_complete = on_trade_complete  # Callback cuando se cierra posición
        self.on_trade_booktrading = on_trade_booktrading  # Callback para registrar en booktrading
        self.logger = logging.getLogger("BotCryptoUI")

        # symbol -> TradingBotSpot
        self.bots = {}

        # symbol -> {minQty, stepSize} (cache exchange_info)
        self.lot_sizes = {}

    # =========================
    # REGISTRO
    # =========================
    def register_bot(self, bot):
        """
        Registra un bot y lo vincula al OrderManager.
        Carga LOT_SIZE del símbolo para formatear cantidades.
        """
        self.bots[bot.symbol] = bot
        self.order_manager.register_bot(bot.symbol, bot)
        self._load_lot_size(bot.symbol)

    def unregister_bot(self, symbol):
        """Elimina un bot del manager"""
        self.bots.pop(symbol, None)
        self.lot_sizes.pop(symbol, None)
        if self.order_manager:
            self.order_manager.bots.pop(symbol, None)

    def _load_lot_size(self, symbol):
        """Carga minQty y stepSize desde exchange_info."""
        try:
            info = self.spot_client.get_exchange_info(symbol=symbol)
            if info and symbol in info:
                self.lot_sizes[symbol] = info[symbol]
                self.logger.info(f"LOT_SIZE {symbol}: {info[symbol]}")
        except Exception as e:
            self.logger.warning(f"No se pudo cargar LOT_SIZE para {symbol}: {e}")

    def _format_qty(self, symbol, qty):
        """Ajusta cantidad según stepSize y minQty del símbolo."""
        lot = self.lot_sizes.get(symbol)
        if not lot:
            return round(qty, 6)

        step_size = lot["stepSize"]
        min_qty = lot["minQty"]

        # Redondear al stepSize más cercano hacia abajo
        if step_size > 0:
            qty = qty - (qty % step_size)

        # Determinar decimales desde stepSize
        step_str = f"{step_size:.10f}".rstrip("0")
        decimals = len(step_str.split(".")[-1]) if "." in step_str else 0
        qty = round(qty, decimals)

        if qty < min_qty:
            self.logger.warning(f"{symbol}: qty={qty} < minQty={min_qty}, orden cancelada")
            return 0.0

        return qty

    def _check_notional(self, symbol: str, qty: float, price: float) -> bool:
        """Verifica que el nocional (qty * price) supere el mínimo de Binance."""
        lot = self.lot_sizes.get(symbol, {})
        min_notional = lot.get("minNotional", 5.0)  # Default 5 USDT
        notional = qty * price

        if notional < min_notional:
            self.logger.warning(
                f"{symbol}: notional={notional:.2f} < minNotional={min_notional:.2f} USDT, orden cancelada"
            )
            return False
        return True

    # =========================
    # EJECUCION ORDENES
    # =========================
    def execute_action(self, bot, action):
        """Ejecuta la acción decidida por el bot."""
        if action == "BUY":
            self._execute_buy(bot)
        elif action == "TP1":
            self._execute_partial_sell(bot, intent="TP1")
        elif action == "TRAIL_EXIT":
            self._execute_exit(bot, reason="TRAIL")
        elif action == "EXIT":
            self._execute_exit(bot)

    def _execute_buy(self, bot):
        price = bot._last_price()
        capital = self.capital_manager.get_available_capital()

        if capital <= 0:
            self.logger.warning(f"{bot.symbol}: Sin capital disponible")
            return

        qty_original = bot._calc_position_size(price, capital)
        qty = self._format_qty(bot.symbol, qty_original)

        self.logger.warning(
            f"{bot.symbol}: BUY eval | price={price:.6f} capital={capital:.2f} "
            f"qty_orig={qty_original:.8f} qty_fmt={qty:.8f} lot_sizes={self.lot_sizes.get(bot.symbol, 'NO')}"
        )

        if qty <= 0:
            self.logger.warning(f"{bot.symbol}: qty=0 después de format, orden cancelada")
            return

        # Piso adaptativo: ajustar qty si nocional < mínimo (máx 2x riesgo)
        lot = self.lot_sizes.get(bot.symbol, {})
        min_notional = lot.get("minNotional", 5.0)
        notional = qty * price

        if notional < min_notional:
            qty_min = min_notional / price
            qty_adjusted = self._format_qty(bot.symbol, qty_min * 1.01)  # +1% margen

            # Limitar riesgo: 3x en TESTNET, 2.5x en PRODUCTION
            max_risk_factor = 3.0 if self.env == "TESTNET" else 2.5
            if qty_adjusted > qty_original * max_risk_factor:
                self.logger.warning(
                    f"{bot.symbol}: notional={notional:.2f} < {min_notional:.2f}, "
                    f"ajuste supera {max_risk_factor}x riesgo (env={self.env}), orden cancelada"
                )
                return

            self.logger.info(
                f"{bot.symbol}: PISO ADAPTATIVO qty={qty:.6f} → {qty_adjusted:.6f} "
                f"(notional {notional:.2f} → {qty_adjusted * price:.2f} USDT)"
            )
            qty = qty_adjusted

        self.logger.info(f"{bot.symbol}: BUY qty={qty} price={price:.4f} capital={capital:.2f}")

        order = self.spot_client.get_new_order(
            symbol=bot.symbol,
            side="BUY",
            type="MARKET",
            quantity=qty,
        )

        if not order:
            self.logger.error(f"{bot.symbol}: Orden BUY fallida")
            return

        order_id = order["orderId"]
        self.order_manager.register_order(symbol=bot.symbol, order_id=order_id, intent="ENTRY")
        self.capital_manager.reserve(qty * price)

        # ⚠️ CRÍTICO: Actualizar estado del bot después de BUY exitoso
        bot.state["position"] = "LONG"
        bot.state["entry_price"] = price
        bot.state["position_qty"] = qty
        bot.state["remaining_qty"] = qty
        bot.state["stop_loss"] = price * (1 - bot.risk_cfg["stop_loss_pct"])
        bot.state["tp1_done"] = False
        bot.state["tp2_done"] = False

        self.logger.warning(
            f"✅ {bot.symbol}: POSICIÓN ABIERTA @ {price:.6f} | qty={qty} | SL={bot.state['stop_loss']:.6f}"
        )

        # Almacenar BUY en booktrading
        if self.on_trade_booktrading:
            self.on_trade_booktrading(bot.symbol, order=order)

    def _execute_partial_sell(self, bot, intent: str = "TP1"):
        """Venta parcial TP1 (33%). El cierre total se hace via _execute_exit (trailing o SL)."""
        qty = bot.state["position_qty"] * bot.risk_cfg["tp1_size"]

        qty = self._format_qty(bot.symbol, qty)

        if qty <= 0:
            return

        price = bot._last_price()

        # Validar nocional mínimo de Binance
        if not self._check_notional(bot.symbol, qty, price):
            return

        self.logger.info(f"{bot.symbol}: {intent} SELL qty={qty}")

        order = self.spot_client.get_new_order(
            symbol=bot.symbol,
            side="SELL",
            type="MARKET",
            quantity=qty,
        )

        if not order:
            self.logger.error(f"{bot.symbol}: Orden {intent} fallida")
            return

        order_id = order["orderId"]
        self.order_manager.register_order(symbol=bot.symbol, order_id=order_id, intent=intent)

        if intent == "TP1":
            bot.state["tp1_done"] = True
            bot.state["remaining_qty"] -= qty
            # Activar trailing stop después de TP1
            bot.state["trailing_active"] = True
            bot.state["trail_high"] = price
            atr = bot._calc_atr14()
            trail_mult = bot.risk_cfg.get("trail_mult", 1.5)
            bot.state["trailing_stop"] = price - (trail_mult * atr)
            self.logger.warning(
                f"{bot.symbol}: TRAILING activado | high={price:.6f} stop={bot.state['trailing_stop']:.6f} "
                f"ATR={atr:.6f} mult={trail_mult}"
            )

        self.capital_manager.release(qty * price)

        self.logger.warning(
            f"✅ {bot.symbol}: {intent} EJECUTADO | vendido={qty} | remaining={bot.state['remaining_qty']:.6f}"
        )

        # Almacenar TP1/TP2 en booktrading
        if self.on_trade_booktrading:
            self.on_trade_booktrading(bot.symbol, order=order)

    def _get_real_balance(self, symbol):
        """Obtiene el balance real disponible del activo en Binance"""
        try:
            asset = symbol.replace("USDT", "")
            account = self.spot_client.account_spot()
            if account and "balances" in account:
                for b in account["balances"]:
                    if b["asset"] == asset:
                        return float(b["free"])
        except Exception as e:
            self.logger.error(f"{symbol}: Error obteniendo balance real: {e}")
        return 0.0

    def _convert_dust_to_bnb(self, symbols):
        """Convierte dust de uno o más activos a BNB en una sola llamada (límite: 1 por hora)"""
        try:
            if isinstance(symbols, str):
                symbols = [symbols]
            assets = [s.replace("USDT", "") for s in symbols]
            result = self.spot_client.transfer_dust(asset=assets)
            transferred = result.get("totalTransfered", 0)
            self.logger.warning(f"Dust convertido a BNB | assets={assets} | {transferred} BNB")
            return True
        except Exception as e:
            self.logger.warning(f"No se pudo convertir dust a BNB ({assets}): {e}")
            return False

    def _execute_exit(self, bot, reason="SL"):
        # Usar balance real de Binance en vez del estado interno
        real_qty = self._get_real_balance(bot.symbol)
        qty = self._format_qty(bot.symbol, real_qty)

        if qty <= 0:
            self.logger.warning(f"{bot.symbol}: EXIT sin balance disponible (real={real_qty}), limpiando estado")
            bot.state.update(
                {
                    "position": "NONE",
                    "entry_price": None,
                    "remaining_qty": 0.0,
                    "trailing_active": False,
                    "trail_high": None,
                    "trailing_stop": None,
                }
            )
            return

        price = bot._last_price()
        notional = qty * price
        lot = self.lot_sizes.get(bot.symbol, {})
        min_notional = lot.get("minNotional", 5.0)

        # Si el valor es menor al mínimo de Binance, es dust - convertir a BNB y limpiar
        if notional < min_notional:
            self.logger.warning(f"{bot.symbol}: EXIT dust (${notional:.2f} < ${min_notional:.2f}), convirtiendo a BNB")
            self._convert_dust_to_bnb(bot.symbol)
            bot.state.update(
                {
                    "position": "NONE",
                    "entry_price": None,
                    "remaining_qty": 0.0,
                    "trailing_active": False,
                    "trail_high": None,
                    "trailing_stop": None,
                }
            )
            return

        self.logger.warning(f"{bot.symbol}: EXIT ({reason}) SELL qty={qty} | notional=${notional:.2f} | price={price}")

        order = self.spot_client.get_new_order(
            symbol=bot.symbol,
            side="SELL",
            type="MARKET",
            quantity=qty,
        )

        if not order:
            self.logger.error(f"{bot.symbol}: Orden EXIT fallida (qty={qty}, real={real_qty}), limpiando estado")
            bot.state.update(
                {
                    "position": "NONE",
                    "entry_price": None,
                    "remaining_qty": 0.0,
                    "trailing_active": False,
                    "trail_high": None,
                    "trailing_stop": None,
                }
            )
            return

        order_id = order["orderId"]
        self.order_manager.register_order(symbol=bot.symbol, order_id=order_id, intent="EXIT")
        self.capital_manager.release(qty * price)

        # Resetear estado del bot después de EXIT exitoso
        bot.state["position"] = "NONE"
        bot.state["entry_price"] = None
        bot.state["position_qty"] = 0.0
        bot.state["remaining_qty"] = 0.0
        bot.state["stop_loss"] = None
        bot.state["tp1_done"] = False
        bot.state["tp2_done"] = False
        bot.state["trailing_active"] = False
        bot.state["trail_high"] = None
        bot.state["trailing_stop"] = None

        self.logger.warning(f"✅ {bot.symbol}: POSICIÓN CERRADA ({reason}) @ {price:.6f} | qty={qty}")

        # Almacenar EXIT en booktrading
        if self.on_trade_booktrading:
            self.on_trade_booktrading(bot.symbol, order=order)

        # Notificar trade completado (contador)
        if self.on_trade_complete:
            self.on_trade_complete(bot.symbol)


# =============================================================================
# UI PRINCIPAL: BotCryptoUI
# =============================================================================
class BotCryptoUI:
    """
    UI principal para la pestaña BotCrypto.
    Muestra grid de widgets (3 por fila) con información de cada símbolo.
    """

    # Configuración
    ACCOUNT = "B0000002"
    COLUMNS = 3
    WIDGET_WIDTH = 300
    WIDGET_HEIGHT = 290

    # Factores de ajuste por temporalidad (base = 5m)
    INTERVAL_FACTORS = {
        "1m": {"tp1": 0.015, "sl": 0.01, "trail_mult": 1.0},
        "3m": {"tp1": 0.02, "sl": 0.015, "trail_mult": 1.0},
        "5m": {"tp1": 0.03, "sl": 0.02, "trail_mult": 1.2},
        "15m": {"tp1": 0.04, "sl": 0.025, "trail_mult": 1.5},
        "30m": {"tp1": 0.05, "sl": 0.03, "trail_mult": 1.5},
        "1h": {"tp1": 0.06, "sl": 0.035, "trail_mult": 2.0},
        "4h": {"tp1": 0.08, "sl": 0.05, "trail_mult": 2.5},
        "1d": {"tp1": 0.10, "sl": 0.06, "trail_mult": 3.0},
    }

    def __init__(self, parent, colors, repositorio):
        """
        Args:
            parent: Frame padre (win6 del notebook)
            colors: Diccionario de colores de la app
            repositorio: RepositorioOportunidadesBuySell
        """
        self.colors = colors
        self.repositorio = repositorio
        self.logger = logging.getLogger("BotCryptoUI")

        # Frame principales
        self.parent = parent
        self.right = ttk.Frame(
            parent, padding=(3, 6, 1, 1), style="C.TFrame", height=600
        )  # bot   antes (3,5,1,1) gwi001
        self.left = ttk.Frame(parent, padding=(3, 6, 1, 1), style="B.TFrame")  # control grafico
        self.left.pack(side=tk.LEFT)
        self.right.pack(fill=tk.BOTH, expand=True)

        # Estado
        self.widgets = {}  # symbol -> WidgetBotSymbol
        self.bots = {}  # symbol -> TradingBotSpot
        self.running = False
        self.interval = "15m"

        # Config desde BD (incluye env)
        self.env = None
        self.config = self._cargar_config()

        # Managers
        self.order_manager = None
        self.bot_manager = None
        self.binance_client = None
        self.ws_client = None

        # Contadores WebSocket para process_system (DataHub)
        self.ws_msg_counter = 0
        self.ws_stream_itera = 0

        # UI refs
        self.canvas = None
        self.scrollable_frame = None
        self.lbl_status = None
        self.lbl_capital = None
        self.lbl_activos = None
        self.lbl_trades = None
        self.lbl_pnl = None
        self.combo_interval = None

        # Auto-refresh timer (5 segundos)
        self._refresh_timer_id = None
        self._refresh_interval = 5000  # ms
        self._closing = False  # Flag para cierre limpio

        # WebSocket reconnect
        self._ws_reconnect_timer = None
        self._ws_reconnect_delay = 5000  # ms inicial (5s)
        self._ws_reconnect_max = 60000  # ms máximo (60s)
        self._ws_reconnect_count = 0

        # WebSocket watchdog (detecta conexión muerta sin on_close)
        self._ws_watchdog_timer = None
        self._ws_last_msg_time = None
        self._ws_watchdog_interval = 30000  # Verificar cada 30s
        self._ws_watchdog_timeout = 120  # Si no hay mensaje en 120s, reconectar

        # TopLevel windows abiertas (para cerrar en detener())
        self._toplevel_windows = []
        self._dust_symbols = []

        # Contadores reales
        self.trades_count = 0  # Trades completados (ciclos BUY→SELL)
        self.total_pnl_usdt = 0.0  # PnL total en USDT

        # Repositorio para almacenar trades en BD
        self.repositorio = RepositorioOportunidadesBuySell()
        self.ultimo_trade_time = None  # Para control de duplicados

        # Scoring / Rotación
        self.scoring_tree = None  # Treeview del panel scoring
        self.all_activos = []  # Todos los activos del universo
        self.scoring_data = {}  # symbol -> dict scoring

    def _cargar_config(self):
        """
        Carga configuración del bot con valores por defecto.
        El ambiente (TESTNET/PRODUCTION) se lee de la columna 'environment' en sesion.

        Nota: userapi/userpass contienen credenciales API de Binance,
        NO configuración del bot. La config del bot usa defaults.
        """
        config = {
            "capital": 100.0,
            "risk_per_trade": 0.02,
            "tp1_pct": 0.03,
            "stop_loss_pct": 0.02,
            "tp1_size": 0.33,
            "trail_mult": 1.5,
            "rsi_buy": 35,
            "rsi_sell": 65,
            "env": "TESTNET",
            "max_active_bots": 3,
        }

        try:
            sesion = BDsystem.get_sesion_by_vehiculo("BotCrypto")

            # Ambiente desde columna environment
            if sesion:
                db_env = (sesion.get("environment") or "").strip().upper()
                if db_env in ("TESTNET", "PRODUCTION"):
                    config["env"] = db_env

                    self.logger.warning(f"✅ Ambiente '{db_env}', inicializado correctamente")
                    config = json.loads(sesion.get("private_key"))
                    self.env = sesion.get("environment", "TESTNET")
                    self.ACCOUNT = sesion.get("idcuenta")

                else:
                    self.logger.warning(f"Ambiente no válido en BD: '{db_env}', usando TESTNET")

        except Exception as e:
            self.logger.warning(f"Error leyendo sesion BotCrypto: {e}")

        # Auto-ajustar TP/SL según temporalidad (from_bd=True: respetar interval guardado)
        config = self._ajustar_config_por_intervalo(config, from_bd=True)

        return config

    def _ajustar_config_por_intervalo(self, config, from_bd=False):
        """Auto-ajusta TP1, SL y trail_mult según la temporalidad seleccionada"""
        # Solo leer interval de BD durante carga inicial, no al cambiar combo
        if from_bd:
            saved_interval = config.get("interval")
            if saved_interval and saved_interval in self.INTERVAL_FACTORS:
                self.interval = saved_interval

        interval = getattr(self, "interval", "15m")
        factors = self.INTERVAL_FACTORS.get(interval, self.INTERVAL_FACTORS["15m"])

        config["interval"] = interval
        config["tp1_pct"] = factors["tp1"]
        config["stop_loss_pct"] = factors["sl"]
        config["trail_mult"] = factors["trail_mult"]

        self.logger.warning(
            f"⚙️ Config ({interval}): "
            f"capital={config.get('capital')} | risk={config.get('risk_per_trade',0)*100:.0f}% | "
            f"TP1={factors['tp1']*100:.1f}% | Trail×={factors['trail_mult']} | SL={factors['sl']*100:.1f}% | "
            f"tp1_size={config.get('tp1_size')} | "
            f"RSI={config.get('rsi_buy')}/{config.get('rsi_sell')} | max_bots={config.get('max_active_bots', 3)}"
        )

        return config

    def inicializar(self):
        """Inicializa la UI completa"""
        try:
            self._crear_graficos()
            self._crear_panel_control()
            self._crear_canvas_scrollable()
            self._crear_panel_scoring()
            self._cargar_simbolos()
            self._inicializar_managers()
            self._iniciar_auto_refresh()

            # Auto-start: iniciar bots al cargar la app
            if self.all_activos:
                self._on_start_all()
        except Exception as e:
            self.logger.error(f"Error inicializando BotCryptoUI: {e}")
            traceback.print_exc()

    # =========================================
    # PANEL DE GRAFICOS gwi001
    # =========================================
    def _crear_graficos(self):
        """Crea el panel ladetral derecho controles graficos"""

        top = ttk.Frame(self.left, padding=(1, 1, 1, 1), style="C.TFrame")  # Imagen derecha superior
        bot = ttk.Frame(self.left, padding=(1, 1, 1, 1), style="C.TFrame")  # Imagen derecha superior
        cen = ttk.Frame(self.left, padding=(1, 1, 1, 1), style="C.TFrame")  # Imagen derecha superior
        top.pack(side=tk.TOP)
        bot.pack(side=tk.BOTTOM)
        cen.pack(side=tk.LEFT)

        fg0 = Figure(figsize=(2.9, 1.9), dpi=110, layout="tight")
        fg0.set_facecolor(self.colors["cgcolor"])
        cv0 = FigureCanvasTkAgg(fg0, master=top)
        cv0.draw()
        cv0.get_tk_widget().pack()

        fg1 = Figure(figsize=(2.9, 1.9), dpi=110, layout="tight")
        fg1.set_facecolor(self.colors["cgcolor"])
        cv1 = FigureCanvasTkAgg(fg1, master=cen)
        cv1.draw()
        cv1.get_tk_widget().pack()

        self._crear_panel_capital(bot)

    def _crear_panel_capital(self, parent):
        """Crea panel de resumen Capital & Riesgo en el espacio inferior izquierdo"""
        bg = self.colors["cgcolor"]
        fg = self.colors["fgcolor"]

        frame = tk.Frame(parent, bg=bg, width=319, height=250)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.pack_propagate(False)

        # Título
        tk.Label(frame, text="CAPITAL & RIESGO", bg=bg, fg=self.colors["bgcolor"], font=("Arial", 9, "bold")).pack(
            anchor="w", padx=5, pady=(4, 2)
        )

        sep = tk.Frame(frame, bg="gray30", height=1)
        sep.pack(fill=tk.X, padx=5)

        # Sección capital
        cap_frame = tk.Frame(frame, bg=bg)
        cap_frame.pack(fill=tk.X, padx=5, pady=2)

        self._cap_labels = {}
        for key, label in [
            ("capital", "Capital"),
            ("reservado", "Reservado"),
            ("disponible", "Disponible"),
            ("risk", "Risk/Trade"),
        ]:
            row = tk.Frame(cap_frame, bg=bg)
            row.pack(fill=tk.X)
            tk.Label(row, text=f"{label}:", bg=bg, fg="gray70", font=("Arial", 8), anchor="w", width=12).pack(
                side=tk.LEFT
            )
            lbl = tk.Label(row, text="--", bg=bg, fg=fg, font=("Arial", 8, "bold"), anchor="e", width=14)
            lbl.pack(side=tk.RIGHT)
            self._cap_labels[key] = lbl

        # Separador
        sep2 = tk.Frame(frame, bg="gray30", height=1)
        sep2.pack(fill=tk.X, padx=5, pady=2)

        # Footer fijo (PnL + Posiciones) - empacar ANTES del canvas para reservar espacio
        footer = tk.Frame(frame, bg=bg)
        footer.pack(side=tk.BOTTOM, fill=tk.X)

        # Posiciones con scroll - ocupa espacio restante
        self._pos_canvas = tk.Canvas(frame, bg=bg, highlightthickness=0)
        pos_scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=self._pos_canvas.yview)
        self._pos_frame = tk.Frame(self._pos_canvas, bg=bg)

        self._pos_frame.bind(
            "<Configure>", lambda e: self._pos_canvas.configure(scrollregion=self._pos_canvas.bbox("all"))
        )
        self._pos_canvas.create_window((0, 0), window=self._pos_frame, anchor="nw", tags="pos_window")
        self._pos_canvas.configure(yscrollcommand=pos_scrollbar.set)

        # Mousewheel scroll
        def _on_mousewheel(event):
            self._pos_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self._pos_canvas.bind("<MouseWheel>", _on_mousewheel)
        self._pos_frame.bind("<MouseWheel>", _on_mousewheel)
        self._on_pos_mousewheel = _on_mousewheel  # Guardar ref para bindear hijos dinámicos

        pos_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._pos_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self._pos_labels = {}

        sep3 = tk.Frame(footer, bg="gray30", height=1)
        sep3.pack(fill=tk.X, padx=5, pady=2)

        # PnL Total
        pnl_row = tk.Frame(footer, bg=bg)
        pnl_row.pack(fill=tk.X, padx=5)
        tk.Label(pnl_row, text="PnL Total:", bg=bg, fg="gray70", font=("Arial", 8), anchor="w", width=12).pack(
            side=tk.LEFT
        )
        self._lbl_pnl_total = tk.Label(
            pnl_row, text="$0.00", bg=bg, fg="lime", font=("Arial", 8, "bold"), anchor="e", width=14
        )
        self._lbl_pnl_total.pack(side=tk.RIGHT)

        # Posiciones activas / total
        # count_row = tk.Frame(footer, bg=bg)
        # count_row.pack(fill=tk.X, padx=5)
        # tk.Label(count_row, text="Posiciones:", bg=bg, fg="gray70", font=("Arial", 8), anchor="w", width=12).pack(
        #    side=tk.LEFT
        # )
        # self._lbl_pos_count = tk.Label(
        #    count_row, text="0/0", bg=bg, fg=fg, font=("Arial", 8, "bold"), anchor="e", width=14
        # )
        # self._lbl_pos_count.pack(side=tk.RIGHT)

        # Pérdida por SL individual
        sl_row = tk.Frame(footer, bg=bg)
        sl_row.pack(fill=tk.X, padx=5)
        tk.Label(sl_row, text="SL/Trade:", bg=bg, fg="gray70", font=("Arial", 8), anchor="w", width=12).pack(
            side=tk.LEFT
        )
        self._lbl_sl_trade = tk.Label(
            sl_row, text="--", bg=bg, fg="orange", font=("Arial", 8, "bold"), anchor="e", width=14
        )
        self._lbl_sl_trade.pack(side=tk.RIGHT)

        # Pérdida máxima
        max_row = tk.Frame(footer, bg=bg)
        max_row.pack(fill=tk.X, padx=5)
        tk.Label(max_row, text="Max Loss:", bg=bg, fg="gray70", font=("Arial", 8), anchor="w", width=12).pack(
            side=tk.LEFT
        )
        self._lbl_max_loss = tk.Label(
            max_row, text="--", bg=bg, fg="red", font=("Arial", 8, "bold"), anchor="e", width=14
        )
        self._lbl_max_loss.pack(side=tk.RIGHT)

    def _actualizar_panel_capital(self):
        """Actualiza el panel de capital con datos en tiempo real"""
        try:
            if not hasattr(self, "_cap_labels"):
                return

            bg = self.colors["cgcolor"]
            fg = self.colors["fgcolor"]

            # Capital
            capital = self.config.get("capital", 0)
            reservado = self.capital_manager.capital_reservado if self.capital_manager else 0
            disponible = self.capital_manager.get_available_capital() if self.capital_manager else 0
            risk_pct = self.config.get("risk_per_trade", 0.02) * 100

            self._cap_labels["capital"].config(text=f"${capital:.2f}")
            self._cap_labels["reservado"].config(text=f"${reservado:.2f}")
            self._cap_labels["disponible"].config(text=f"${disponible:.2f}", fg="lime" if disponible > 0 else "red")
            self._cap_labels["risk"].config(text=f"{risk_pct:.0f}%")

            # Limpiar posiciones previas
            for w in self._pos_frame.winfo_children():
                w.destroy()

            # Posiciones por símbolo
            total_pnl = 0.0
            activas = 0

            for symbol, bot in self.bots.items():
                state = bot.get_public_state()
                position = state.get("position", "NONE")
                row = tk.Frame(self._pos_frame, bg=bg)
                row.pack(fill=tk.X)
                row.bind("<MouseWheel>", self._on_pos_mousewheel)

                sym_short = symbol.replace("USDT", "")

                if position == "LONG":
                    activas += 1
                    entry = state.get("entry_price", 0) or 0
                    qty = state.get("remaining_qty", 0) or 0
                    price = bot._last_price() if bot.df is not None and len(bot.df) > 0 else entry
                    notional = qty * entry
                    pnl_usdt = (price - entry) * qty if entry > 0 else 0
                    pnl_pct = ((price / entry) - 1) * 100 if entry > 0 else 0
                    total_pnl += pnl_usdt
                    color = "lime" if pnl_usdt >= 0 else "red"

                    tk.Label(
                        row,
                        text=f"{sym_short:<5}",
                        bg=bg,
                        fg="white",
                        font=("Arial", 8, "bold"),
                        width=5,
                        anchor="w",
                    ).pack(side=tk.LEFT)
                    tk.Label(
                        row, text=f"${notional:>6.1f}", bg=bg, fg="gray70", font=("Arial", 8), width=7, anchor="e"
                    ).pack(side=tk.LEFT)
                    tk.Label(
                        row,
                        text=f"{pnl_pct:>+5.1f}% ${pnl_usdt:>+6.2f}",
                        bg=bg,
                        fg=color,
                        font=("Arial", 8, "bold"),
                        anchor="e",
                    ).pack(side=tk.RIGHT)
                else:
                    tk.Label(
                        row, text=f"{sym_short:<5}", bg=bg, fg="gray50", font=("Arial", 8), width=5, anchor="w"
                    ).pack(side=tk.LEFT)
                    tk.Label(row, text="waiting", bg=bg, fg="gray50", font=("Arial", 8), anchor="e").pack(side=tk.RIGHT)

            # Bindear mousewheel a todos los labels hijos del canvas
            for child in self._pos_frame.winfo_children():
                child.bind("<MouseWheel>", self._on_pos_mousewheel)
                for subchild in child.winfo_children():
                    subchild.bind("<MouseWheel>", self._on_pos_mousewheel)

            # Ajustar ancho del frame interno al canvas
            self._pos_canvas.itemconfig("pos_window", width=self._pos_canvas.winfo_width())

            # PnL Total
            pnl_color = "lime" if total_pnl >= 0 else "red"
            self._lbl_pnl_total.config(text=f"${total_pnl:>+.2f}", fg=pnl_color)

            # Contador posiciones
            total = len(self.bots)
            self._cap_labels["reservado"].config(text=f"{activas} de {total} -  ${reservado:.2f}")

            # self._lbl_pos_count.config(text=f"{activas}/{total}")

            # Pérdida por SL: position_size × stop_loss_pct
            risk_pct_dec = self.config.get("risk_per_trade", 0.02)
            sl_pct = self.config.get("stop_loss_pct", 0.02)
            pos_size = capital * risk_pct_dec
            sl_loss = pos_size * sl_pct
            self._lbl_sl_trade.config(text=f"-${sl_loss:.2f}")

            # Pérdida máxima: SL × cantidad de bots activos (o total si todos entran)
            max_loss = sl_loss * total
            max_loss_pct = (max_loss / capital * 100) if capital > 0 else 0
            self._lbl_max_loss.config(text=f"-${max_loss:.2f} ({max_loss_pct:.1f}%)")
        except Exception as e:
            self.logger.error(f"_actualizar_panel_capital(): {e}")

    # =========================================
    # PANEL DE CONTROL
    # =========================================
    def _crear_panel_control(self):
        """Crea el panel superior con controles globales"""

        panel = tk.Frame(self.right, bg=self.colors["cgcolor"], height=80)
        panel.pack(fill=tk.X, padx=5, pady=5)
        panel.pack_propagate(False)

        # Fila 1: Botones y Status
        row1 = tk.Frame(panel, bg=self.colors["cgcolor"])
        row1.pack(fill=tk.X, pady=2)

        # Botón START
        btn_start = tk.Button(
            row1,
            text="START",
            bg="green",
            fg="white",
            font=("Arial", 10, "bold"),
            width=10,
            command=self._on_start_all,
        )
        btn_start.pack(side=tk.LEFT, padx=5)

        # Botón STOP
        btn_stop = tk.Button(
            row1,
            text="STOP",
            bg="red",
            fg="white",
            font=("Arial", 10, "bold"),
            width=10,
            command=self._on_stop_all,
        )
        btn_stop.pack(side=tk.LEFT, padx=5)

        # Botón Refresh config
        btn_refresh = tk.Button(
            row1,
            text="REFRESH",
            bg="#607D8B",
            fg="white",
            font=("Arial", 10, "bold"),
            width=10,
            command=self._on_refresh_config,
        )
        btn_refresh.pack(side=tk.LEFT, padx=5)

        # Status
        tk.Label(row1, text="Status:", bg=self.colors["cgcolor"], fg="white").pack(side=tk.LEFT, padx=(20, 5))
        self.lbl_status = tk.Label(
            row1,
            text="● STOPPED",
            bg=self.colors["cgcolor"],
            fg="gray",
            font=("Arial", 10, "bold"),
        )
        self.lbl_status.pack(side=tk.LEFT)

        # Capital (configurado)
        tk.Label(row1, text="Capital:", bg=self.colors["cgcolor"], fg="white").pack(side=tk.LEFT, padx=(30, 5))
        self.lbl_capital = tk.Label(
            row1,
            text=f"{self.config.get('capital', 0):.2f} USDT",
            bg=self.colors["cgcolor"],
            fg="cyan",
            font=("Arial", 10, "bold"),
        )
        self.lbl_capital.pack(side=tk.LEFT)

        # Saldo real (Binance)
        tk.Label(row1, text="Saldo:", bg=self.colors["cgcolor"], fg="white").pack(side=tk.LEFT, padx=(20, 5))
        self.lbl_saldo = tk.Label(
            row1,
            text="-- USDT",
            bg=self.colors["cgcolor"],
            fg="yellow",
            font=("Arial", 10, "bold"),
        )
        self.lbl_saldo.pack(side=tk.LEFT)

        # Fila 2: Intervalo y métricas
        row2 = tk.Frame(panel, bg=self.colors["cgcolor"])
        row2.pack(fill=tk.X, pady=2)

        # Selector de ambiente
        tk.Label(row2, text="Env:", bg=self.colors["cgcolor"], fg="white").pack(side=tk.LEFT, padx=5)
        self.combo_env = ttk.Combobox(row2, values=["TESTNET", "PRODUCTION"], width=12, state="disable")
        self.combo_env.set(self.env)
        self.combo_env.pack(side=tk.LEFT, padx=5)
        self.combo_env.bind("<<ComboboxSelected>>", self._on_env_change)

        # Selector de intervalo
        tk.Label(row2, text="Intervalo:", bg=self.colors["cgcolor"], fg="white").pack(side=tk.LEFT, padx=(10, 5))
        self.combo_interval = ttk.Combobox(row2, values=["1m", "5m", "15m", "30m", "1h"], width=5, state="readonly")
        self.combo_interval.set(self.interval)  # Usa intervalo de BD o default 15m
        self.combo_interval.pack(side=tk.LEFT, padx=5)
        self.combo_interval.bind("<<ComboboxSelected>>", self._on_interval_change)

        # Activos
        tk.Label(row2, text="Activos:", bg=self.colors["cgcolor"], fg="white").pack(side=tk.LEFT, padx=(20, 5))
        self.lbl_activos = tk.Label(row2, text="0", bg=self.colors["cgcolor"], fg="yellow")
        self.lbl_activos.pack(side=tk.LEFT)

        # Trades
        tk.Label(row2, text="Trades:", bg=self.colors["cgcolor"], fg="white").pack(side=tk.LEFT, padx=(20, 5))
        self.lbl_trades = tk.Label(row2, text="0", bg=self.colors["cgcolor"], fg="yellow")
        self.lbl_trades.pack(side=tk.LEFT)

        # PnL
        tk.Label(row2, text="PnL:", bg=self.colors["cgcolor"], fg="white").pack(side=tk.LEFT, padx=(20, 5))
        self.lbl_pnl = tk.Label(row2, text="0.00%", bg=self.colors["cgcolor"], fg="white")
        self.lbl_pnl.pack(side=tk.LEFT)

        # Botón para ver posiciones activas
        btn_activas = tk.Button(
            row2,
            text="Activas",
            command=self._abrir_posiciones_activas,
            bg="#ff1e1e",
            fg="white",
            width=10,
            font=("Arial", 9),
        )
        btn_activas.pack(side=tk.RIGHT, padx=5)

    # =========================================
    # PANEL DE SCORING (primer cubo del canvas)
    # =========================================
    def _crear_panel_scoring(self):
        """Widget de scoring con mismo estilo cubo que los trading widgets, posición 0 del grid"""
        self._scoring_frame = tk.Frame(
            self.scrollable_frame,
            bg=self.colors["cgcolor"],
            width=self.WIDGET_WIDTH,
            height=self.WIDGET_HEIGHT,
            highlightbackground="gray",
            highlightthickness=1,
        )
        self._scoring_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nw")
        self._scoring_frame.pack_propagate(False)

        # Header — mismo estilo que WidgetBotSymbol
        header = tk.Frame(self._scoring_frame, bg=self.colors["cgcolor"])
        header.pack(fill=tk.X, padx=3, pady=(3, 0))
        tk.Label(
            header,
            text="SCORING",
            bg=self.colors["cgcolor"],
            fg=self.colors["bgcolor"],
            font=("Arial", 10, "bold"),
        ).pack(side=tk.LEFT)
        max_bots = self.config.get("max_active_bots", 3)
        self._lbl_max_bots = tk.Label(
            header,
            text=f"Max: {max_bots}",
            bg=self.colors["cgcolor"],
            fg="yellow",
            font=("Arial", 8),
        )
        self._lbl_max_bots.pack(side=tk.RIGHT)

        # Botón agregar símbolo al universo
        btn_add = tk.Button(
            header,
            text="+",
            bg="blue",
            fg="white",
            font=("Arial", 8, "bold"),
            width=3,
            command=self._on_add_symbol,
        )
        btn_add.pack(side=tk.RIGHT, padx=3)

        # Treeview — 4 columnas compactas
        columns = ("symbol", "score", "prioridad", "estado")
        self.scoring_tree = ttk.Treeview(
            self._scoring_frame,
            columns=columns,
            show="headings",
            height=6,
            style="B.Treeview",
        )
        col_w = (self.WIDGET_WIDTH - 10) // 4
        hdrs = {
            "symbol": ("Activo", col_w + 10),
            "score": ("Score", col_w - 10),
            "prioridad": ("Prior.", col_w),
            "estado": ("Estado", col_w),
        }
        for col, (txt, w) in hdrs.items():
            self.scoring_tree.heading(col, text=txt)
            anchor = "center" if col != "symbol" else "w"
            self.scoring_tree.column(col, width=w, minwidth=w, anchor=anchor)

        self.scoring_tree.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Tags de color por prioridad
        self.scoring_tree.tag_configure("Alta", foreground="lime")
        self.scoring_tree.tag_configure("Media", foreground="yellow")
        self.scoring_tree.tag_configure("Revisión", foreground="white")
        self.scoring_tree.tag_configure("Bloqueado", foreground="red")

    # =========================================
    # CANVAS SCROLLABLE
    # =========================================
    def _crear_canvas_scrollable(self):
        """Crea el canvas con scroll para los widgets de símbolos"""
        # Container
        container = tk.Frame(self.right, bg=self.colors["bgcolor"])
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Canvas
        self.canvas = tk.Canvas(container, bg=self.colors["bgcolor"], highlightthickness=0)

        # Scrollbar
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)

        # Frame scrollable dentro del canvas
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors["bgcolor"])

        # Configurar scroll region cuando cambie el tamaño
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        # Crear ventana en el canvas
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Mousewheel
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Pack
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # =========================================
    # CARGAR SÍMBOLOS
    # =========================================
    def _cargar_simbolos(self):
        """Carga TODOS los símbolos desde otros_activos.
        Los widgets de trading se crean en _on_start_all según scoring."""
        try:
            activos, found = self.repositorio.select_otros_activos(account=self.ACCOUNT, symbol="all")

            if not found or not activos:
                self.logger.info(f"No hay símbolos para cuenta {self.ACCOUNT}")
                self._mostrar_mensaje_vacio()
                return

            # Guardar todos los activos para scoring/rotación
            self.all_activos = [a for a in activos if a.get("symbol")]

            # Actualizar contador
            self.lbl_activos.config(text=str(len(self.all_activos)))

        except Exception as e:
            self.logger.error(f"Error cargando símbolos: {e}")
            traceback.print_exc()

    def _mostrar_mensaje_vacio(self):
        """Muestra mensaje cuando no hay símbolos"""
        lbl = tk.Label(
            self.scrollable_frame,
            text=f"No hay símbolos configurados para la cuenta {self.ACCOUNT}\n\n"
            "Use el botón '+ Agregar' para agregar símbolos",
            bg=self.colors["bgcolor"],
            fg="gray",
            font=("Arial", 12),
        )
        lbl.grid(row=0, column=0, columnspan=3, pady=50)

    def _crear_widget_simbolo(self, symbol, activo, row, col):
        """Crea un WidgetBotSymbol para el símbolo"""
        widget = WidgetBotSymbol(
            parent=self.scrollable_frame,
            symbol=symbol,
            activo=activo,
            colors=self.colors,
            config=self.config,
            on_start=lambda s=symbol: self._on_start_symbol(s),
            on_stop=lambda s=symbol: self._on_stop_symbol(s),
            on_chart=lambda s=symbol: self._on_show_chart(s),
            on_test_buy=lambda s=symbol: self._on_test_buy(s),
            on_delete=lambda s=symbol: self._on_delete_symbol(s),
            on_sell_all=lambda s=symbol: self._on_sell_all(s),
            env=self.env,
            widget_width=self.WIDGET_WIDTH,
            widget_height=self.WIDGET_HEIGHT,
        )
        widget.crear_ui()
        widget.frame.grid(row=row, column=col, padx=5, pady=5, sticky="nw")
        self.widgets[symbol] = widget

    # =========================================
    # MANAGERS
    # =========================================
    def _inicializar_managers(self):
        """Inicializa BinanceClient, OrderManager, CapitalManager y BotManager."""
        try:
            # Binance client: usar self.env que ya se leyó de sesion.environment
            self.binance_client = BinanceClient(vehiculo="BotCrypto", env=self.env)
            self.spot_client = self.binance_client.spot

            # Verificar consistencia de env
            if self.env != self.binance_client.env:
                self.logger.warning(f"⚠️ env mismatch: UI={self.env}, Client={self.binance_client.env}")

            # Order Manager
            self.order_manager = OrderManager()

            # Capital Manager
            capital = self.config.get("capital", 100.0)
            self.capital_manager = CapitalManager(capital_total=capital)

            # Bot Manager (coordina ejecución de órdenes)
            self.bot_manager = BotManager(
                spot_client=self.spot_client,
                order_manager=self.order_manager,
                capital_manager=self.capital_manager,
                env=self.env,
                on_trade_complete=self._on_trade_complete,
                on_trade_booktrading=self._almacenar_trades_booktrading,
            )

            self.logger.info(
                f"Managers inicializados: env={self.env}, capital={capital}, base_url={self.binance_client.urls['base_url']}"
            )

            # Mostrar saldo inicial de Binance
            self._actualizar_saldo()

            # Telegram: cargar credenciales para notificaciones
        except Exception as e:
            self.logger.error(f"Error inicializando managers: {e}")

    def _publicar_estado_botcrypto(self):
        """Publica estado de posiciones activas en DataHub para Telegram"""
        resumen = []
        for symbol, bot in self.bots.items():
            state = bot.get_public_state()
            indicators = bot.get_indicators()
            price = indicators.get("last_price", 0)
            entry = state.get("entry_price") or 0
            qty = state.get("remaining_qty", 0)
            position = state.get("position", "NONE")

            pnl_pct = ((price - entry) / entry) * 100 if entry > 0 and price > 0 else 0
            pnl_usdt = (price - entry) * qty if entry > 0 else 0

            resumen.append(
                {
                    "symbol": symbol,
                    "position": position,
                    "entry": entry,
                    "price": price,
                    "qty": qty,
                    "pnl_pct": pnl_pct,
                    "pnl_usdt": pnl_usdt,
                }
            )

        DataHub.telegram_botcrypto = {
            "env": self.env,
            "running": self.running,
            "trades": self.trades_count,
            "posiciones": resumen,
        }

    def _on_trade_complete(self, symbol):
        """Callback cuando se completa un trade (posición cerrada)"""
        self.trades_count += 1
        self.logger.warning(f"Trade #{self.trades_count} completado: {symbol}")
        if self.lbl_trades:
            self.lbl_trades.config(text=str(self.trades_count))

    def _almacenar_trades_booktrading(self, symbol, order=None):
        """
        Almacena trade en booktrading usando la respuesta directa de la orden.
        order: respuesta de get_new_order() con fills, side, symbol, transactTime.
        """
        try:
            if not order or "fills" not in order:
                self.logger.warning(f"_almacenar_trades_booktrading({symbol}): orden sin fills, ignorando")
                return

            side = order.get("side", "BUY")
            order_id = str(order.get("orderId", ""))
            transact_time = order.get("transactTime", int(datetime.now().timestamp() * 1000))

            for i, fill in enumerate(order["fills"]):
                try:
                    qty = float(fill.get("qty", 0))
                    price = float(fill.get("price", 0))
                    commission = float(fill.get("commission", 0))
                    quoteqty = qty * price

                    # BUY = positivo, SELL = negativo (igual que trader_binance)
                    cantidad = qty if side == "BUY" else -qty

                    registro = {
                        "categoria": "BotCrypto",
                        "divisa": "USD",
                        "cuenta": self.ACCOUNT,
                        "cantidad": cantidad,
                        "producto": quoteqty,
                        "idtrans": f"{order_id}_{i}" if len(order["fills"]) > 1 else order_id,
                        "preciotrans": price,
                        "preciocierre": price,
                        "tarifacomision": commission * price,
                        "mtmgp": 0.00,
                        "fechahora": datetime.fromtimestamp(transact_time / 1000),
                    }

                    self.repositorio.insert_bottraderBook(values=registro, symbol=symbol, object="bottrader")
                    self.logger.warning(f"Booktrading: {symbol} | {side} | qty={cantidad} | price={price:.4f}")

                except Exception as e:
                    self.logger.error(f"Error procesando fill {symbol}: {e}")

        except Exception as e:
            self.logger.error(f"_almacenar_trades_booktrading error: {e}")

    # =========================================
    # WEBSOCKET
    # =========================================
    def _iniciar_websocket(self):
        """Inicia WebSocket para recibir klines"""
        try:
            symbols = list(self.widgets.keys())
            if not symbols:
                return

            def on_message(_, msg):
                self._on_ws_message(msg)

            self.ws_client = BinanceStreamClient(
                env=self.env,
                assets=symbols,
                mensaje_callback=on_message,
                on_close_callback=self._on_ws_close,
            )

            # Registrar en DataHub para monitoreo en process_system
            self.ws_stream_itera += 1
            self.ws_msg_counter = 0
            stream = "run_websocket_stream(BotCrypto)"
            socket = "WebsocketStream_OnMessage(BotCrypto)"

            # Registrar thread y widget solo la primera vez
            if self.ws_stream_itera == 1:
                DataHub.procesos.append({"thread": {stream: self.ws_stream_itera}})
                DataHub.procesos.append({"widget": {socket: 0}})
            else:
                DataHub.update_self_procesos(proces="thread", tarea=stream, itera=self.ws_stream_itera)

            self.logger.warning(
                f"✅ WebSocket inicializado correctamente | env={self.env} | symbols={len(symbols)} | itera={self.ws_stream_itera}"
            )

            # Suscribir a klines del intervalo seleccionado
            self.ws_client.subscribe_klines(interval=self.interval)

            # Iniciar watchdog para detectar conexiones muertas
            self._ws_last_msg_time = time.time()
            if self._ws_watchdog_timer:
                self.parent.after_cancel(self._ws_watchdog_timer)
            self._ws_watchdog_timer = self.parent.after(self._ws_watchdog_interval, self._ws_watchdog)
        except Exception as e:
            self.logger.error(f"Error iniciando WebSocket: {e}")

    def _detener_websocket(self):
        """Detiene el WebSocket"""
        try:
            # Cancelar watchdog y reconnect pendientes
            if self._ws_watchdog_timer:
                self.parent.after_cancel(self._ws_watchdog_timer)
                self._ws_watchdog_timer = None
            if self._ws_reconnect_timer:
                self.parent.after_cancel(self._ws_reconnect_timer)
                self._ws_reconnect_timer = None
            if self.ws_client:
                self.ws_client._on_close_callback = None  # Evitar reconnect al detener manualmente
                self.ws_client.stop()
                self.ws_client = None
        except Exception as e:
            self.logger.error(f"Error deteniendo WebSocket: {e}")

    def _ws_watchdog(self):
        """Verifica periódicamente si el WebSocket sigue vivo (detecta conexión muerta sin on_close)"""
        if self._closing or not self.running:
            return

        if self._ws_last_msg_time:
            elapsed = time.time() - self._ws_last_msg_time
            if elapsed > self._ws_watchdog_timeout:
                self.logger.warning(f"Watchdog: sin mensajes WS en {elapsed:.0f}s, forzando reconexión")
                self._on_ws_close("watchdog_timeout")
                return

        self._ws_watchdog_timer = self.parent.after(self._ws_watchdog_interval, self._ws_watchdog)

    def _on_ws_close(self, reason):
        """Callback cuando el WebSocket se desconecta - programa auto-reconnect"""
        if self._closing or not self.running:
            return

        self._ws_reconnect_count += 1
        delay = min(self._ws_reconnect_delay * self._ws_reconnect_count, self._ws_reconnect_max)

        self.logger.warning(
            f"🔄 WebSocket desconectado (intento #{self._ws_reconnect_count}). "
            f"Reconectando en {delay // 1000}s... | reason={reason}"
        )

        # Actualizar status en UI
        self.parent.after(0, lambda: self.lbl_status.config(text="● RECONNECTING", fg="orange"))

        # Programar reconexión en main thread
        self._ws_reconnect_timer = self.parent.after(delay, self._ws_reconnect)

    def _ws_reconnect(self):
        """Intenta reconectar el WebSocket"""
        if self._closing or not self.running:
            return

        try:
            # Cerrar viejo cliente antes de crear uno nuevo
            if self.ws_client:
                self.ws_client._on_close_callback = None  # Evitar loop de reconnect
                try:
                    self.ws_client.stop()
                except Exception:
                    pass
                self.ws_client = None

            self._iniciar_websocket()
            self._ws_reconnect_count = 0  # Reset contador en éxito
            self.lbl_status.config(text="● RUNNING", fg="lime")
            self.logger.warning("✅ WebSocket reconectado exitosamente")
        except Exception as e:
            self.logger.error(f"Error en reconexión WebSocket: {e}")
            # Reintentar con backoff
            self._on_ws_close(str(e))

    def _on_ws_message(self, msg):
        """Procesa mensaje del WebSocket (corre en thread WS, delega UI al main thread)"""
        try:
            if self._closing:
                return

            # Contabilizar iteradas para process_system y watchdog
            self.ws_msg_counter += 1
            self._ws_last_msg_time = time.time()
            DataHub.update_self_procesos(
                proces="widget",
                tarea="WebsocketStream_OnMessage(BotCrypto)",
                itera=self.ws_msg_counter,
            )

            data = json.loads(msg)
            if isinstance(data, dict) and data.get("e") == "kline":
                kline = data["k"]
                symbol = kline["s"]
                is_closed = kline["x"]

                # Delegar actualizaciones de UI al main thread via .after()
                if symbol in self.widgets:
                    price = float(kline["c"])
                    self.parent.after(0, self.widgets[symbol].update_price, price)

                # Si vela cerrada y bot activo, evaluar
                if is_closed and symbol in self.bots:
                    candle = {
                        "open": float(kline["o"]),
                        "high": float(kline["h"]),
                        "low": float(kline["l"]),
                        "close": float(kline["c"]),
                        "volume": float(kline["v"]),
                        "timestamp": kline["t"],
                    }
                    self.parent.after(0, self._evaluar_bot, symbol, candle)

        except Exception as e:
            if not self._closing:
                self.logger.error(f"Error procesando WS message: {e}")

    def _evaluar_bot(self, symbol, candle):
        """Evalúa el bot para un símbolo"""  # gwi001
        try:
            bot = self.bots.get(symbol)
            if not bot:
                return

            bot.on_market_data(candle)
            action, conditions = bot.evaluate()

            # Actualizar widget con estado
            state = bot.get_public_state()
            indicators = bot.get_indicators()
            self.widgets[symbol].update_state(state, indicators, conditions)

            # Ejecutar orden via bot_manager (en background para no bloquear UI)
            if action != "HOLD" and self.bot_manager:
                self.logger.info(f"{symbol}: Acción {action}")

                def _exec_action(b=bot, a=action, s=symbol, c=conditions):
                    try:
                        self.bot_manager.execute_action(b, a)
                    except Exception as ex:
                        self.logger.error(f"{s}: Error ejecutando {a}: {ex}")

                    # Actualizar widget post-ejecución en main thread
                    def _post_update():
                        try:
                            w = self.widgets.get(s)
                            if w:
                                st = b.get_public_state()
                                ind = b.get_indicators()
                                w.update_state(st, ind, c)
                                self._actualizar_panel_capital()
                        except Exception:
                            pass

                    self.parent.after(0, _post_update)

                threading.Thread(target=_exec_action, daemon=True).start()

            # Publicar estado en DataHub para consulta desde Telegram
            self._publicar_estado_botcrypto()

            # Actualizar panel capital
            self._actualizar_panel_capital()

            # Recalcular scoring y evaluar rotación en cada cierre de vela
            self._evaluar_rotacion_post_vela(symbol)

        except Exception as e:
            self.logger.error(f"_evaluar_bot(): Error evaluando bot {symbol}: {e}")

    def _evaluar_rotacion_post_vela(self, symbol):
        """Recalcula scoring de bots activos. Lanza recálculo de observación en background.
        Si hay bot NONE, la rotación se ejecuta DESPUÉS de que observación esté fresco."""
        try:
            # Recalcular scoring de bots activos (rápido, sin REST)
            for sym, bot in list(self.bots.items()):
                scoring = bot.calcular_scoring()
                self.scoring_data[sym] = scoring
                self._persistir_scoring(sym, scoring)

            # ¿Hay algún bot en NONE? → rotación posible
            bot = self.bots.get(symbol)
            necesita_rotacion = False
            if bot:
                state = bot.get_public_state()
                necesita_rotacion = state.get("position") == "NONE"

            # Recalcular observación en background → rotar al terminar
            def _recalcular_y_rotar():
                self._recalcular_scoring_observacion_sync()
                if necesita_rotacion:
                    self.parent.after(0, self._rotar_activos)
                self.parent.after(0, self._actualizar_panel_scoring)

            threading.Thread(target=_recalcular_y_rotar, daemon=True).start()

        except Exception as e:
            self.logger.error(f"_evaluar_rotacion_post_vela({symbol}): {e}")

    def _recalcular_scoring_observacion_sync(self):
        """Recalcula scoring para activos en observación (no activos). Síncrono."""
        try:
            activos_activos = set(self.bots.keys())
            strategy_config = {
                "rsi_buy": self.config.get("rsi_buy", 35),
                "rsi_sell": self.config.get("rsi_sell", 65),
            }
            risk_config = {
                "risk_per_trade": self.config.get("risk_per_trade", 0.02),
                "tp1_pct": self.config.get("tp1_pct", 0.03),
                "stop_loss_pct": self.config.get("stop_loss_pct", 0.02),
                "tp1_size": self.config.get("tp1_size", 0.33),
                "trail_mult": self.config.get("trail_mult", 1.5),
            }
            for activo in self.all_activos:
                symbol = activo.get("symbol")
                if not symbol or symbol in activos_activos:
                    continue
                try:
                    tmp_bot = TradingBotSpot(
                        symbol=symbol,
                        interval=self.interval,
                        strategy_config=strategy_config,
                        risk_config=risk_config,
                        state_repo=None,
                        order_manager=None,
                    )
                    self._cargar_historico(tmp_bot, symbol, limit=500)
                    tmp_bot.calcular_indicadores()
                    scoring = tmp_bot.calcular_scoring()
                    self.scoring_data[symbol] = scoring
                    self._persistir_scoring(symbol, scoring)
                except Exception as e:
                    self.logger.error(f"Scoring observación {symbol}: {e}")

        except Exception as e:
            self.logger.error(f"_recalcular_scoring_observacion_sync(): {e}")

    def _rotar_activos(self):
        """Rota activos: bots en NONE con bajo score salen, mejores candidatos entran.
        NUNCA cierra posiciones LONG activas."""
        try:
            # Encontrar bots en NONE (candidatos a salir)
            bots_none = []
            for sym, bot in list(self.bots.items()):
                state = bot.get_public_state()
                if state.get("position") == "NONE":
                    score = self.scoring_data.get(sym, {}).get("score_total", 0)
                    bots_none.append((sym, score))

            if not bots_none:
                return

            # Encontrar activos en observación con mejor score
            activos_en_panel = set(self.bots.keys())
            candidatos = []
            for sym, scoring in self.scoring_data.items():
                if sym not in activos_en_panel:
                    candidatos.append((sym, scoring.get("score_total", -99)))

            if not candidatos:
                return

            # Ordenar: bots NONE por score ascendente, candidatos por score descendente
            bots_none.sort(key=lambda x: x[1])
            candidatos.sort(key=lambda x: x[1], reverse=True)

            # Rotar: si el mejor candidato supera al peor bot NONE
            activos_map = {a["symbol"]: a for a in self.all_activos}
            rotaciones = []  # (none_sym, mejor_sym)
            for none_sym, none_score in bots_none:
                if not candidatos:
                    break
                mejor_sym, mejor_score = candidatos[0]
                if mejor_score > none_score:
                    self.logger.warning(f"ROTACIÓN: {none_sym}(score={none_score}) → {mejor_sym}(score={mejor_score})")
                    # Sacar bot NONE (UI)
                    del self.bots[none_sym]
                    if none_sym in self.widgets:
                        self.widgets[none_sym].frame.destroy()
                        del self.widgets[none_sym]
                    if self.bot_manager:
                        self.bot_manager.unregister_bot(none_sym)

                    # Crear widget vacío (UI)
                    activo = activos_map.get(mejor_sym, {})
                    grid_idx = len(self.widgets) + 1
                    row = grid_idx // self.COLUMNS
                    col = grid_idx % self.COLUMNS
                    self._crear_widget_simbolo(mejor_sym, activo, row, col)
                    rotaciones.append(mejor_sym)
                    candidatos.pop(0)

            # Crear bots en background (REST: historico + posición + lot_size)
            if rotaciones:

                def _crear_bots_bg():
                    for sym in rotaciones:
                        try:
                            self._crear_bot(sym)
                        except Exception as ex:
                            self.logger.error(f"Rotación _crear_bot({sym}): {ex}")

                    def _post_rotacion():
                        for sym in rotaciones:
                            w = self.widgets.get(sym)
                            if w:
                                w.set_running(True)
                        self._detener_websocket()
                        self.parent.after(500, self._iniciar_websocket)

                    self.parent.after(0, _post_rotacion)

                threading.Thread(target=_crear_bots_bg, daemon=True).start()

        except Exception as e:
            self.logger.error(f"_rotar_activos(): {e}")

    def _actualizar_panel_scoring(self):
        """Actualiza el treeview de scoring con datos actuales"""
        if not self.scoring_tree:
            return
        try:
            self.scoring_tree.delete(*self.scoring_tree.get_children())

            # Ordenar por score descendente
            ranked = sorted(
                self.scoring_data.items(),
                key=lambda x: x[1].get("score_total", -99),
                reverse=True,
            )

            activos_activos = set(self.bots.keys())
            for sym, scoring in ranked:
                # Solo mostrar activos en observación (no los que tienen bot activo)
                if sym in activos_activos:
                    continue

                score = scoring.get("score_total", 0)
                prioridad = scoring.get("prioridad", "BLOQUEADO")

                self.scoring_tree.insert(
                    "",
                    "end",
                    values=(sym, score, prioridad, "OBSERV."),
                    tags=(prioridad,),
                )
        except Exception as e:
            self.logger.error(f"_actualizar_panel_scoring(): {e}")

    def _persistir_scoring(self, symbol, scoring):
        """Guarda scoring + indicadores en campo indicadores de otros_activos"""
        try:
            from datetime import datetime

            data = {
                "scoring": {
                    "total": scoring.get("score_total", 0),
                    "rsi": scoring.get("score_rsi", 0),
                    "macd": scoring.get("score_macd", 0),
                    "ema": scoring.get("score_ema", 0),
                    "vol": scoring.get("score_vol", 0),
                },
                "prioridad": scoring.get("prioridad", "BLOQUEADO"),
                "indicadores": scoring.get("indicadores", {}),
                "timestamp": datetime.now().isoformat(),
            }
            self.repositorio.update_otros_activos_indicadores(symbol, self.ACCOUNT, data)
        except Exception as e:
            self.logger.error(f"_persistir_scoring({symbol}): {e}")

    # =========================================
    # EVENT HANDLERS
    # =========================================
    def _on_start_all(self):
        """Inicia bots priorizados por scoring (máx max_active_bots).
        Todo el trabajo pesado (REST API) va en background thread."""
        if self.running:
            return

        self.running = True
        self.lbl_status.config(text="● CALCULANDO...", fg="yellow")
        self.interval = self.combo_interval.get()

        def _trabajo_pesado():
            """Background: scoring + creación de bots (REST API calls)"""
            try:
                max_bots = self.config.get("max_active_bots", 3)

                # 1. Calcular scoring universo
                self._calcular_scoring_universo()

                # 2. Ordenar por score
                ranked = sorted(
                    self.scoring_data.items(),
                    key=lambda x: x[1].get("score_total", -99),
                    reverse=True,
                )

                # 3. Preparar bots para Top N (carga históricos en background)
                top_symbols = []
                strategy_config = {
                    "rsi_buy": self.config.get("rsi_buy", 35),
                    "rsi_sell": self.config.get("rsi_sell", 65),
                }
                risk_config = {
                    "risk_per_trade": self.config.get("risk_per_trade", 0.02),
                    "tp1_pct": self.config.get("tp1_pct", 0.03),
                    "stop_loss_pct": self.config.get("stop_loss_pct", 0.02),
                    "tp1_size": self.config.get("tp1_size", 0.33),
                    "trail_mult": self.config.get("trail_mult", 1.5),
                }

                for symbol, _scoring in ranked:
                    if len(top_symbols) >= max_bots:
                        break
                    top_symbols.append(symbol)

                # Pre-crear bots + todo REST en background
                pre_bots = {}
                for symbol in top_symbols:
                    try:
                        bot = TradingBotSpot(
                            symbol=symbol,
                            interval=self.interval,
                            strategy_config=strategy_config,
                            risk_config=risk_config,
                            state_repo=None,
                            order_manager=self.order_manager,
                        )
                        self._cargar_historico(bot, symbol, limit=500)

                        # Registrar en BotManager (carga lot_sizes via REST)
                        if self.bot_manager:
                            self.bot_manager.register_bot(bot)

                        # Cargar posición existente (REST)
                        self._cargar_posicion_existente(bot, symbol)

                        pre_bots[symbol] = bot
                        self.logger.info(f"{symbol}: Bot listo | df={len(bot.df) if bot.df is not None else 0}")
                    except Exception as e:
                        self.logger.error(f"{symbol}: Error preparando bot: {e}")

                # Delegar solo UI al main thread
                self.parent.after(0, lambda: self._fase_ui_bots(pre_bots))

            except Exception as e:
                self.logger.error(f"_trabajo_pesado: {e}")
                traceback.print_exc()

        threading.Thread(target=_trabajo_pesado, daemon=True).start()

    def _fase_ui_bots(self, pre_bots):
        """Main thread: solo operaciones UI (widgets, scoring, WS). Sin REST."""
        try:
            activos_map = {a["symbol"]: a for a in self.all_activos}
            active_count = 0

            for symbol, bot in pre_bots.items():
                # Crear widget (UI pura)
                activo = activos_map.get(symbol, {})
                grid_idx = active_count + 1
                row = grid_idx // self.COLUMNS
                col = grid_idx % self.COLUMNS
                self._crear_widget_simbolo(symbol, activo, row, col)

                # Asignar bot
                self.bots[symbol] = bot
                self.widgets[symbol].set_running(True)

                # Evaluación inicial + ejecución
                if bot.df is not None and len(bot.df) >= 50:
                    action, conditions = bot.evaluate()
                    state = bot.get_public_state()
                    indicators = bot.get_indicators()
                    self.widgets[symbol].update_state(state, indicators, conditions)
                    self.logger.warning(f"{symbol}: Eval → {action} | position={state.get('position')}")

                    if action != "HOLD" and self.bot_manager:
                        self.logger.warning(f">>> {symbol}: EJECUTANDO {action}")

                        def _exec_init(b=bot, a=action, s=symbol, c=conditions):
                            try:
                                self.bot_manager.execute_action(b, a)
                            except Exception as ex:
                                self.logger.error(f"{s}: Error init {a}: {ex}")

                            def _upd():
                                w = self.widgets.get(s)
                                if w:
                                    w.update_state(b.get_public_state(), b.get_indicators(), c)

                            self.parent.after(0, _upd)

                        threading.Thread(target=_exec_init, daemon=True).start()

                active_count += 1

            # Scoring panel
            self._actualizar_panel_scoring()

            # WebSocket
            self._iniciar_websocket()

            self.lbl_status.config(text="● RUNNING", fg="lime")
            self.logger.warning(f"BotCrypto LISTO | bots={len(self.bots)} | scoring={len(self.scoring_data)}")

        except Exception as e:
            self.logger.error(f"_fase_ui_bots: {e}")
            traceback.print_exc()

    def _calcular_scoring_universo(self):
        """Calcula scoring para todos los activos del universo usando bots temporales"""
        self.scoring_data = {}
        strategy_config = {
            "rsi_buy": self.config.get("rsi_buy", 35),
            "rsi_sell": self.config.get("rsi_sell", 65),
        }
        risk_config = {
            "risk_per_trade": self.config.get("risk_per_trade", 0.02),
            "tp1_pct": self.config.get("tp1_pct", 0.03),
            "stop_loss_pct": self.config.get("stop_loss_pct", 0.02),
            "tp1_size": self.config.get("tp1_size", 0.33),
            "trail_mult": self.config.get("trail_mult", 1.5),
        }

        for activo in self.all_activos:
            symbol = activo.get("symbol")
            if not symbol:
                continue
            try:
                # Bot temporal solo para calcular scoring
                tmp_bot = TradingBotSpot(
                    symbol=symbol,
                    interval=self.interval,
                    strategy_config=strategy_config,
                    risk_config=risk_config,
                    state_repo=None,
                    order_manager=None,
                )
                self._cargar_historico(tmp_bot, symbol, limit=500)
                tmp_bot.calcular_indicadores()
                scoring = tmp_bot.calcular_scoring()
                self.scoring_data[symbol] = scoring
            except Exception as e:
                self.logger.error(f"Scoring {symbol}: {e}")
                self.scoring_data[symbol] = {
                    "score_total": -99,
                    "prioridad": "BLOQUEADO",
                    "score_rsi": 0,
                    "score_macd": 0,
                    "score_ema": 0,
                    "score_vol": 0,
                }

    def _on_stop_all(self):
        """Detiene todos los bots"""
        if not self.running:
            return

        self.running = False
        self.lbl_status.config(text="● STOPPED", fg="gray")

        # Detener WebSocket
        self._detener_websocket()

        # Limpiar bots
        self.bots.clear()

        # Destruir widgets de trading
        for widget in self.widgets.values():
            widget.set_running(False)
            widget.frame.destroy()
        self.widgets.clear()

    def _on_start_symbol(self, symbol):
        """Inicia bot para un símbolo específico (REST en background)"""
        if symbol not in self.bots:

            def _bg():
                try:
                    self._crear_bot(symbol)
                except Exception as e:
                    self.logger.error(f"_on_start_symbol({symbol}): {e}")
                    return

                def _ui():
                    w = self.widgets.get(symbol)
                    if w:
                        w.set_running(True)
                    self.logger.warning(f"▶ {symbol}: Bot INICIADO | env={self.env}")

                self.parent.after(0, _ui)

            threading.Thread(target=_bg, daemon=True).start()

    def _on_stop_symbol(self, symbol):
        """Detiene bot para un símbolo específico"""
        if symbol in self.bots:
            del self.bots[symbol]
            self.widgets[symbol].set_running(False)
            self.logger.warning(f"■ {symbol}: Bot DETENIDO")

    def _on_show_chart(self, symbol):
        """Abre gráfico TradingView en ventana pywebview (no bloquea main thread)"""
        interval_map = {
            "1m": "1",
            "3m": "3",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "2h": "120",
            "4h": "240",
            "1d": "D",
            "1w": "W",
            "1M": "M",
        }
        tv_interval = interval_map.get(self.interval, "15")
        tv_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}&interval={tv_interval}"
        title = f"{symbol} - {self.interval}"

        p = multiprocessing.Process(
            target=_webview_process,
            args=(title, tv_url, 1050, 720),
            daemon=True,
        )
        p.start()

    def _on_sell_all(self, symbol):
        """Vende todo el balance de un símbolo específico (REST en background)"""

        def _bg():
            try:
                asset = symbol.replace("USDT", "")
                account = self.spot_client.account_spot()

                if not account or "balances" not in account:
                    self.logger.error(f"No se pudo obtener cuenta de Binance")
                    return

                balance = 0.0
                for b in account["balances"]:
                    if b["asset"] == asset:
                        balance = float(b["free"])
                        break

                if balance <= 0:
                    self.logger.warning(f"{symbol}: Sin balance de {asset} para vender")
                    return

                lot_info = self.bot_manager.lot_sizes.get(symbol, {})
                step_size = lot_info.get("stepSize", 1.0)
                min_qty = lot_info.get("minQty", 1.0)

                if step_size > 0:
                    decimals = len(str(step_size).split(".")[-1].rstrip("0")) if "." in str(step_size) else 0
                    qty = float(int(balance / step_size) * step_size)
                    qty = round(qty, decimals)
                else:
                    qty = balance

                if qty < min_qty:
                    self.logger.warning(f"{symbol}: qty={qty} < minQty={min_qty}")
                    return

                self.logger.warning(f"🔴 {symbol}: SELL ALL qty={qty} {asset}")

                order = self.spot_client.get_new_order(
                    symbol=symbol,
                    side="SELL",
                    type="MARKET",
                    quantity=qty,
                )

                if order:
                    self.logger.warning(f"✅ {symbol}: VENDIDO {qty} {asset} | orderId={order.get('orderId')}")
                    self.parent.after(0, self._actualizar_saldo)
                else:
                    self.logger.error(f"{symbol}: Orden SELL ALL fallida")

            except Exception as e:
                self.logger.error(f"_on_sell_all({symbol}): {e}")
                traceback.print_exc()

        threading.Thread(target=_bg, daemon=True).start()

    def _on_delete_symbol(self, symbol):
        """Detiene bot y quita widget. El símbolo permanece en otros_activos (dominio de rotación)."""
        respuesta = MyMessageBox(self.right).askquestion(
            "Quitar símbolo",
            f"¿Quitar {symbol} del panel activo?\n\nEl bot se detendrá. El símbolo seguirá en observación para rotación.",
        )
        if respuesta != "yes":
            return

        try:
            # 1. Detener bot
            if symbol in self.bots:
                del self.bots[symbol]
                self.logger.info(f"{symbol}: Bot detenido")

            # 2. Eliminar de BotManager
            if self.bot_manager:
                self.bot_manager.unregister_bot(symbol)

            # 3. Destruir widget
            if symbol in self.widgets:
                self.widgets[symbol].frame.destroy()
                del self.widgets[symbol]

            # 4. Actualizar scoring — el símbolo pasa a OBSERV.
            self._actualizar_panel_scoring()

            # 5. Reorganizar grid
            self._reorganizar_grid()

            self.logger.info(f"{symbol}: Quitado del panel → pasa a observación")

        except Exception as e:
            self.logger.error(f"Error quitando {symbol}: {e}")

    def _reorganizar_grid(self):
        """Reorganiza los widgets en el grid después de eliminar uno"""
        symbols = list(self.widgets.keys())
        for idx, symbol in enumerate(symbols):
            grid_idx = idx + 1  # +1: scoring ocupa posición 0
            row = grid_idx // self.COLUMNS
            col = grid_idx % self.COLUMNS
            self.widgets[symbol].frame.grid(row=row, column=col, padx=5, pady=5, sticky="nw")

    def _on_test_buy(self, symbol):
        """Ejecuta orden de prueba en TESTNET (REST en background)."""
        if self.env != "TESTNET":
            self.logger.warning("TEST BUY solo disponible en TESTNET")
            return
        if not self.bot_manager:
            self.logger.error("BotManager no inicializado")
            return

        def _bg():
            try:
                lot = self.bot_manager.lot_sizes.get(symbol)
                if not lot:
                    self.bot_manager._load_lot_size(symbol)
                    lot = self.bot_manager.lot_sizes.get(symbol)

                min_qty = lot["minQty"] if lot else 0.001
                self.logger.info(f"TEST BUY {symbol}: qty={min_qty} (minQty)")

                order = self.spot_client.get_new_order(
                    symbol=symbol,
                    side="BUY",
                    type="MARKET",
                    quantity=min_qty,
                )

                def _ui():
                    widget = self.widgets.get(symbol)
                    if order and widget:
                        widget.lbl_estado.config(text=f"TEST OK #{order['orderId']}", fg="lime")
                    elif widget:
                        widget.lbl_estado.config(text="TEST FALLIDO", fg="red")

                self.parent.after(0, _ui)

            except Exception as e:
                self.logger.error(f"TEST BUY error {symbol}: {e}")

                def _ui_err():
                    widget = self.widgets.get(symbol)
                    if widget:
                        widget.lbl_estado.config(text=f"ERROR", fg="red")

                self.parent.after(0, _ui_err)

        threading.Thread(target=_bg, daemon=True).start()

    def _obtener_saldo_usdt(self):
        """Obtiene el saldo libre de USDT desde Binance"""
        try:
            if not self.spot_client:
                return None
            account = self.spot_client.account_spot()
            if account and "balances" in account:
                for balance in account["balances"]:
                    if balance["asset"] == "USDT":
                        return float(balance["free"])
            return None
        except Exception as e:
            self.logger.error(f"Error obteniendo saldo USDT: {e}")
            return None

    def _actualizar_saldo(self):
        """Actualiza el label de saldo con el balance real de Binance (en background)"""

        def _fetch():
            saldo = self._obtener_saldo_usdt()

            def _update_ui():
                if saldo is not None:
                    self.lbl_saldo.config(text=f"{saldo:.2f} USDT")
                else:
                    self.lbl_saldo.config(text="-- USDT")

            self.parent.after(0, _update_ui)

        threading.Thread(target=_fetch, daemon=True).start()

    # =========================================
    # POSICIONES ACTIVAS gwi001
    # =========================================
    def _abrir_posiciones_activas(self):
        """Muestra posiciones activas (LONG) con opción de cerrar individualmente"""
        # Evitar abrir más de una vez
        if hasattr(self, "_win_posiciones") and self._win_posiciones and self._win_posiciones.winfo_exists():
            self._win_posiciones.lift()
            return

        win = tk.Toplevel(self.parent)
        self._win_posiciones = win
        win.title("Posiciones Activas")
        win.config(bg=self.colors["bgcolor"])
        win.resizable(False, False)
        self._toplevel_windows.append(win)
        win.protocol("WM_DELETE_WINDOW", lambda w=win: self._cerrar_toplevel(w))
        try:
            x = self.right.winfo_rootx() + self.right.winfo_width() - 40
            y = self.right.winfo_rooty() + 200
        except Exception:
            x, y = 200, 150
        win.geometry(f"650x320+{x}+{y}")

        # Título
        tk.Label(
            win,
            text="Posiciones Activas",
            bg=self.colors["bgcolor"],
            fg="yellow",
            font=("Arial", 11, "bold"),
        ).pack(pady=10)

        columns = ("symbol", "qty", "entry", "current", "pnl_pct", "pnl_usdt")

        # Frame negro que cubre el área detrás del Treeview
        tree_frame = ttk.Frame(win, style="B.TFrame", padding=(1, 1))
        tree_frame.pack(expand=True, fill="both", padx=10, pady=5)

        # selectmode="extended" permite selección múltiple con Ctrl+click o Shift+click
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8, selectmode="extended")

        # Configurar columnas
        tree.heading("symbol", text="Symbol")
        tree.heading("qty", text="Qty")
        tree.heading("entry", text="Entry")
        tree.heading("current", text="Current")
        tree.heading("pnl_pct", text="Pnl %")
        tree.heading("pnl_usdt", text="Pnl Usdt")

        tree.column("symbol", anchor="center", width=90)
        tree.column("qty", anchor="center", width=80)
        tree.column("entry", anchor="center", width=95)
        tree.column("current", anchor="center", width=95)
        tree.column("pnl_pct", anchor="center", width=75)
        tree.column("pnl_usdt", anchor="center", width=75)

        tree.pack(expand=True, fill="both")

        # Frame para botones
        btn_frame = tk.Frame(win, bg=self.colors["bgcolor"])
        btn_frame.pack(pady=10, expand=True)

        tk.Button(
            btn_frame,
            text="Close",
            bg="gray",
            fg="white",
            font=("Arial", 9),
            width=10,
            command=lambda: self._cerrar_posicion_seleccionada(tree),
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame,
            text="Close All",
            bg="gray",
            fg="white",
            font=("Arial", 9),
            width=10,
            command=lambda: self._cerrar_todas_posiciones(tree),
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame,
            text="Cancel",
            bg="gray",
            fg="white",
            font=("Arial", 9),
            width=10,
            command=lambda w=win: self._cerrar_toplevel(w),
        ).pack(side=tk.LEFT, padx=5)

        # Cargar posiciones iniciales
        self._cargar_posiciones_activas(tree)

        # Auto-refresh cada 5 segundos
        def auto_refresh():
            if self._closing:
                return
            if win.winfo_exists():
                self._cargar_posiciones_activas(tree)
                win.after(5000, auto_refresh)

        win.after(5000, auto_refresh)

    def _cargar_posiciones_activas(self, tree):
        """Carga posiciones activas desde Binance y el estado de los bots"""
        tree.delete(*tree.get_children())

        try:
            # Obtener balances reales de Binance
            account = self.spot_client.account_spot()
            if not account or "balances" not in account:
                return

            balances = {}
            for b in account["balances"]:
                free = float(b["free"])
                if free > 0.001 and b["asset"] not in ["USDT", "BNB"]:
                    balances[b["asset"]] = free

            # Para cada símbolo con balance, mostrar info
            for asset, qty in balances.items():
                symbol = f"{asset}USDT"

                # Obtener precio actual
                try:
                    ticker = self.spot_client.ticker_price(symbol=symbol)
                    current_price = float(ticker["price"]) if ticker else 0
                except:
                    current_price = 0

                # Obtener precio de entrada del bot si existe
                entry_price = 0
                if symbol in self.bots:
                    bot = self.bots[symbol]
                    entry_price = bot.state.get("entry_price") or 0

                # Si no hay entry, usar precio actual como fallback
                if entry_price == 0:
                    entry_price = current_price

                # Calcular PnL
                if entry_price > 0 and current_price > 0:
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    pnl_usdt = (current_price - entry_price) * qty
                else:
                    pnl_pct = 0
                    pnl_usdt = 0

                # Insertar en tree
                tree.insert(
                    "",
                    "end",
                    values=(
                        symbol,
                        f"{qty:.4f}",
                        f"{entry_price:.6f}",
                        f"{current_price:.6f}",
                        f"{pnl_pct:+.2f}%",
                        f"{pnl_usdt:+.4f}",
                    ),
                )

        except Exception as e:
            self.logger.error(f"Error cargando posiciones: {e}")

    def _cerrar_posicion_seleccionada(self, tree):
        """Cierra (vende) las posiciones seleccionadas (permite múltiples con Ctrl+click)"""
        selected = tree.selection()
        if not selected:
            MyMessageBox(self.parent).showinfo("Atención", "Seleccione una o más posiciones")
            return

        # Obtener símbolos seleccionados
        symbols_to_close = []
        for item in selected:
            values = tree.item(item, "values")
            symbols_to_close.append({"symbol": values[0], "qty": float(values[1])})

        # Confirmar
        msg = f"¿Cerrar {len(symbols_to_close)} posición(es)?\n\n"
        for s in symbols_to_close:
            msg += f"• {s['symbol']}: {s['qty']:.4f}\n"
        msg += "\nSe venderán a precio de mercado."

        respuesta = MyMessageBox(self.parent).askquestion("Cerrar Posiciones", msg)
        if respuesta != "yes":
            return

        cerradas = 0
        errores = 0

        for pos in symbols_to_close:
            symbol = pos["symbol"]
            qty = pos["qty"]

            try:
                lot_info = self.bot_manager.lot_sizes.get(symbol, {})
                step_size = lot_info.get("stepSize", 0.00001)
                qty_formatted = float(int(qty / step_size) * step_size)

                self.logger.warning(f"🔴 {symbol}: CERRANDO POSICIÓN | qty={qty_formatted}")

                order = self.spot_client.get_new_order(
                    symbol=symbol,
                    side="SELL",
                    type="MARKET",
                    quantity=qty_formatted,
                )

                if order:
                    self.logger.warning(f"✅ {symbol}: POSICIÓN CERRADA | orderId={order.get('orderId')}")
                    cerradas += 1

                    if symbol in self.bots:
                        bot = self.bots[symbol]
                        bot.state["position"] = "NONE"
                        bot.state["entry_price"] = None
                        bot.state["remaining_qty"] = 0.0
                else:
                    errores += 1

            except Exception as e:
                self.logger.error(f"Error cerrando {symbol}: {e}")
                errores += 1

        # Actualizar UI
        self._cargar_posiciones_activas(tree)
        self._actualizar_saldo()

        MyMessageBox(self.parent).showinfo("Resultado", f"Posiciones cerradas: {cerradas}\nErrores: {errores}")

    def _cerrar_todas_posiciones(self, tree):
        """Cierra todas las posiciones activas - BOTÓN DE EMERGENCIA"""
        items = tree.get_children()
        if not items:
            MyMessageBox(self.parent).showinfo("Info", "No hay posiciones activas")
            return

        respuesta = MyMessageBox(self.parent).askquestion(
            "⚠️ CERRAR TODAS",
            f"¿Cerrar TODAS las posiciones ({len(items)})?\n\n"
            "Esto venderá TODO a precio de mercado.\n"
            "Usar en caso de emergencia.",
        )
        if respuesta != "yes":
            return

        cerradas = 0
        errores = 0

        for item in items:
            values = tree.item(item, "values")
            symbol = values[0]
            qty = float(values[1])

            try:
                lot_info = self.bot_manager.lot_sizes.get(symbol, {})
                step_size = lot_info.get("stepSize", 0.00001)
                qty_formatted = float(int(qty / step_size) * step_size)

                order = self.spot_client.get_new_order(
                    symbol=symbol,
                    side="SELL",
                    type="MARKET",
                    quantity=qty_formatted,
                )

                if order:
                    self.logger.warning(f"✅ {symbol}: POSICIÓN CERRADA")
                    cerradas += 1
                    if symbol in self.bots:
                        self.bots[symbol].state["position"] = "NONE"
                        self.bots[symbol].state["remaining_qty"] = 0.0
                        self.trades_count += 1

            except Exception as e:
                self.logger.error(f"Error cerrando {symbol}: {e}")
                errores += 1

        # Actualizar UI
        if self.lbl_trades:
            self.lbl_trades.config(text=str(self.trades_count))
        self._cargar_posiciones_activas(tree)
        self._actualizar_saldo()

        MyMessageBox(self.parent).showinfo("Resultado", f"Posiciones cerradas: {cerradas}\nErrores: {errores}")

    # =========================================
    # AUTO-REFRESH (cada 5 segundos)
    # =========================================
    def _iniciar_auto_refresh(self):
        """Inicia el timer de auto-refresh"""
        self._auto_refresh()

    def _auto_refresh(self):
        """Actualiza saldo de Binance automáticamente cada 5 segundos"""
        if self._closing:
            return
        try:
            if self.spot_client:
                self._actualizar_saldo()
                self._actualizar_stats_panel()
        except Exception as e:
            self.logger.debug(f"Auto-refresh error: {e}")
        finally:
            if not self._closing:
                self._refresh_timer_id = self.right.after(self._refresh_interval, self._auto_refresh)

    def _actualizar_stats_panel(self):
        """Actualiza Trades y PnL del panel con datos reales de los bots"""
        try:
            total_pnl_pct = 0.0
            activos_en_posicion = 0

            for symbol, bot in self.bots.items():
                entry = bot.state.get("entry_price")
                qty = bot.state.get("remaining_qty", 0)

                if entry and qty > 0:
                    activos_en_posicion += 1
                    current_price = bot._last_price()
                    if current_price and entry > 0:
                        pnl_pct = ((current_price - entry) / entry) * 100
                        total_pnl_pct += pnl_pct

            # Actualizar labels
            if self.lbl_trades:
                self.lbl_trades.config(text=str(self.trades_count))

            if self.lbl_pnl:
                if activos_en_posicion > 0:
                    avg_pnl = total_pnl_pct / activos_en_posicion
                    color = "lime" if avg_pnl >= 0 else "red"
                    self.lbl_pnl.config(text=f"{avg_pnl:+.2f}%", fg=color)
                else:
                    self.lbl_pnl.config(text="0.00%", fg="white")

        except Exception as e:
            self.logger.debug(f"_actualizar_stats_panel error: {e}")

    def _detener_auto_refresh(self):
        """Detiene el timer de auto-refresh"""
        if self._refresh_timer_id:
            self.right.after_cancel(self._refresh_timer_id)
            self._refresh_timer_id = None

    def _cerrar_toplevel(self, win):
        """Cierra una TopLevel y la remueve del registro"""
        try:
            if win in self._toplevel_windows:
                self._toplevel_windows.remove(win)
            win.destroy()
        except Exception:
            pass

    def detener(self):
        """Cierre limpio: marca flag, destruye TopLevels, detiene WS, cancela timers"""
        self._closing = True

        # Destruir TopLevel abiertas (chart, posiciones) para cancelar sus after()
        for win in list(self._toplevel_windows):
            try:
                win.destroy()
            except Exception:
                pass
        self._toplevel_windows.clear()

        if self._ws_reconnect_timer:
            self.parent.after_cancel(self._ws_reconnect_timer)
            self._ws_reconnect_timer = None
        self._detener_auto_refresh()
        self._detener_websocket()

    def _on_refresh_config(self):
        """Recarga la configuración desde la BD y actualiza la UI"""
        try:
            old_capital = self.config.get("capital", 0)
            self.config = self._cargar_config()
            new_capital = self.config.get("capital", 0)

            # Actualizar label de capital
            self.lbl_capital.config(text=f"{new_capital:.2f} USDT")

            # Actualizar CapitalManager si existe
            if self.capital_manager:
                self.capital_manager.capital_total = new_capital
                self.logger.info(f"CapitalManager actualizado: {new_capital:.2f} USDT")

            # Actualizar combo de ambiente si cambió
            if self.env:
                self.combo_env.set(self.env)

            # Actualizar saldo desde Binance
            self._actualizar_saldo()

            self.logger.warning(
                f"🔄 Config recargada: capital {old_capital:.2f} → {new_capital:.2f} USDT | env={self.env}"
            )

        except Exception as e:
            self.logger.error(f"Error recargando config: {e}")

    def _on_env_change(self, event):
        """Cambia el ambiente (TESTNET / PRODUCTION) y persiste en BD"""
        new_env = self.combo_env.get()
        if new_env != self.env:
            if self.running:
                self._on_stop_all()
            self.env = new_env

            # Persistir en BD (sesion.environment)
            BDsystem.update_sesion_environment(vehiculo="BotCrypto", environment=new_env)

            # Reinicializar managers con nuevo ambiente
            self._inicializar_managers()

            # Toggle botón TEST en todos los widgets
            for widget in self.widgets.values():
                widget.set_env(new_env)

            self.logger.info(f"Ambiente cambiado a {new_env}")

    def _on_interval_change(self, event):
        """Cambia el intervalo de velas y auto-ajusta TP/SL"""
        new_interval = self.combo_interval.get()
        if new_interval != self.interval:
            self.interval = new_interval

            # Auto-ajustar TP/SL según nueva temporalidad
            self.config = self._ajustar_config_por_intervalo(self.config)

            # Guardar config ajustada en BD (sesion.private_key)
            BDsystem.update_sesion_config(vehiculo="BotCrypto", config=self.config)
            self.logger.warning(f"💾 Config guardada en BD (interval={new_interval})")

            # Actualizar risk_config en los bots existentes
            factors = self.INTERVAL_FACTORS.get(new_interval, self.INTERVAL_FACTORS["15m"])
            for symbol, bot in self.bots.items():
                bot.risk_cfg["tp1_pct"] = factors["tp1"]
                bot.risk_cfg["stop_loss_pct"] = factors["sl"]
                bot.risk_cfg["trail_mult"] = factors["trail_mult"]

                # Recalcular SL si tiene posición
                if bot.state.get("entry_price"):
                    bot.state["stop_loss"] = bot.state["entry_price"] * (1 - factors["sl"])

                self.logger.info(f"⚙️ {symbol}: Config actualizada a {new_interval}")

            if self.running:
                # Recargar históricos y reiniciar WebSocket en background
                def _reload():
                    for sym, bot in self.bots.items():
                        bot.interval = new_interval
                        self._cargar_historico(bot, sym, limit=500)
                    self.parent.after(0, self._detener_websocket)
                    self.parent.after(500, self._iniciar_websocket)

                threading.Thread(target=_reload, daemon=True).start()

    def _on_add_symbol(self):
        """Abre diálogo para agregar nuevo símbolo al BotCrypto"""  # gwi001

        def eexit():
            dialog.destroy()

        def agregar():
            symbol = entry.get().strip().upper()
            if not symbol:
                lbl_status.config(text="Ingrese un símbolo", fg="red")
                return

            if not symbol.endswith("USDT"):
                symbol += "USDT"

            # Verificar si ya existe
            existing_syms = {a.get("symbol") for a in self.all_activos}
            if symbol in existing_syms or symbol in self.widgets:
                lbl_status.config(text=f"{symbol} ya existe", fg="red")
                return

            lbl_status.config(text=f"Validando {symbol} en Binance...", fg="yellow")
            dialog.update()

            # Validar que exista en Binance
            try:
                if self.binance_client is None:
                    lbl_status.config(text="Binance no inicializado. Intente de nuevo.", fg="red")
                    return

                info = self.spot_client.get_exchange_info(symbol=symbol)
                if not info:
                    lbl_status.config(text=f"{symbol} no encontrado en Binance", fg="red")
                    return
            except Exception as e:
                lbl_status.config(text=f"Error validando: {e}", fg="red")
                return

            # Insertar en BD
            lbl_status.config(text=f"Insertando {symbol}...", fg="yellow")
            dialog.update()

            try:
                xlis, found = self.repositorio.insert_otros_activos(
                    symbol=symbol,
                    cuenta=self.ACCOUNT,
                )
            except Exception as e:
                lbl_status.config(text=f"Error BD: {e}", fg="red")
                return

            # Agregar al universo y refrescar scoring
            try:
                activos, act_found = self.repositorio.select_otros_activos(
                    symbol="all",
                    account=self.ACCOUNT,
                )
                activo = None
                if act_found and activos:
                    for a in activos:
                        if a.get("symbol") == symbol:
                            activo = a
                            break

                if activo:
                    self.all_activos.append(activo)
                    self.lbl_activos.config(text=str(len(self.all_activos)))

                    # Calcular scoring del nuevo símbolo en background
                    def _scoring_nuevo():
                        try:
                            strategy_config = {
                                "rsi_buy": self.config.get("rsi_buy", 35),
                                "rsi_sell": self.config.get("rsi_sell", 65),
                            }
                            risk_config = {
                                k: self.config.get(k, v)
                                for k, v in {
                                    "risk_per_trade": 0.02,
                                    "tp1_pct": 0.03,
                                    "stop_loss_pct": 0.02,
                                    "tp1_size": 0.33,
                                    "trail_mult": 1.5,
                                }.items()
                            }
                            tmp_bot = TradingBotSpot(
                                symbol=symbol,
                                interval=self.interval,
                                strategy_config=strategy_config,
                                risk_config=risk_config,
                                state_repo=None,
                                order_manager=None,
                            )
                            self._cargar_historico(tmp_bot, symbol, limit=500)
                            tmp_bot.calcular_indicadores()
                            scoring = tmp_bot.calcular_scoring()
                            self.scoring_data[symbol] = scoring
                            self._persistir_scoring(symbol, scoring)
                        except Exception as e:
                            self.logger.error(f"Scoring nuevo {symbol}: {e}")
                        self.parent.after(0, self._actualizar_panel_scoring)

                    threading.Thread(target=_scoring_nuevo, daemon=True).start()

                    self.logger.warning(f"Símbolo {symbol} agregado al universo | activos={len(self.all_activos)}")
                    dialog.destroy()
                else:
                    lbl_status.config(text="Error: símbolo no encontrado en BD", fg="red")

            except Exception as e:
                lbl_status.config(text=f"Error: {e}", fg="red")
                traceback.print_exc()

        dialog = tk.Toplevel(self.right)
        dialog.title("Agregar Símbolo")
        try:
            x = self.right.winfo_rootx() + self.right.winfo_width() - 100
            y = self.right.winfo_rooty() + 200
        except Exception:
            x, y = 200, 150
        dialog.geometry(f"250x160+{x}+{y}")
        dialog.resizable(False, False)
        dialog.config(bg=self.colors["bgcolor"])
        dialog.transient(self.right)
        dialog.grab_set()

        tk.Label(
            dialog,
            text="Símbolo (ej: BTCUSDT):",
            bg=self.colors["bgcolor"],
            fg="white",
            font=("Arial", 10),
        ).pack(pady=(12, 4))

        entry = tk.Entry(dialog, font=("Arial", 11), width=18, justify="center")
        entry.pack(pady=4)
        entry.focus_set()

        lbl_status = tk.Label(
            dialog,
            text="",
            bg=self.colors["bgcolor"],
            fg="yellow",
            font=("Arial", 9),
        )
        lbl_status.pack(pady=2)

        btn_frame = tk.Frame(dialog, bg=self.colors["bgcolor"])
        btn_frame.pack(pady=6)
        tk.Button(
            btn_frame,
            text="Agregar",
            command=agregar,
            font=("Arial", 9),
            width=9,
        ).pack(side=tk.LEFT, padx=8)
        tk.Button(
            btn_frame,
            text="Cancel",
            command=eexit,
            font=("Arial", 9),
            width=9,
        ).pack(side=tk.LEFT, padx=8)

        entry.bind("<Return>", lambda e: agregar())
        dialog.bind("<Escape>", lambda e: eexit())

    def _crear_bot(self, symbol):
        """Crea un TradingBotSpot para el símbolo"""
        try:
            strategy_config = {
                "rsi_buy": self.config.get("rsi_buy", 35),
                "rsi_sell": self.config.get("rsi_sell", 65),
            }
            risk_config = {
                "risk_per_trade": self.config.get("risk_per_trade", 0.02),
                "tp1_pct": self.config.get("tp1_pct", 0.03),
                "stop_loss_pct": self.config.get("stop_loss_pct", 0.02),
                "tp1_size": self.config.get("tp1_size", 0.33),
                "trail_mult": self.config.get("trail_mult", 1.5),
            }

            # valida symbol
            if symbol in self.bots:
                return

            # =============================
            # 1. Crear bot lógico
            # =============================
            bot = TradingBotSpot(
                symbol=symbol,
                interval=self.interval,
                strategy_config=strategy_config,
                risk_config=risk_config,
                state_repo=None,  # TODO: Implementar persistencia
                order_manager=self.order_manager,
            )

            # Cargar datos históricos (usa el cliente del ambiente correcto)
            self._cargar_historico(bot, symbol, limit=500)

            self.bots[symbol] = bot

            # Registrar en BotManager para ejecución de órdenes
            if self.bot_manager:
                self.bot_manager.register_bot(bot)

            # =============================
            # 2. Cargar posición existente desde Binance
            # =============================
            self._cargar_posicion_existente(bot, symbol)

        except Exception as e:
            self.logger.error(f"Error creando bot para {symbol}: {e}")

    def _cargar_historico(self, bot, symbol, limit=500):
        """
        Carga datos históricos para el bot usando el cliente correcto (TESTNET/PRODUCTION).

        Args:
            bot: TradingBotSpot instance
            symbol: Par de trading (ej: ADAUSDT)
            limit: Cantidad de velas a cargar (default: 500)
        """
        try:
            if not self.spot_client:
                self.logger.error(f"_cargar_historico: spot_client no inicializado")
                return

            # Usar el cliente Spot que respeta el ambiente (TESTNET/PRODUCTION)
            klines = self.spot_client.klines(symbol=symbol, interval=self.interval, limit=limit)

            if not klines:
                self.logger.warning(f"_cargar_historico: No hay datos para {symbol}")
                return

            # Convertir a DataFrame
            from datetime import datetime

            df = pd.DataFrame(
                [
                    {
                        "Date": datetime.fromtimestamp(k[0] / 1000),
                        "Open": float(k[1]),
                        "High": float(k[2]),
                        "Low": float(k[3]),
                        "Close": float(k[4]),
                        "Volume": float(k[5]),
                    }
                    for k in klines
                ]
            )

            if df is not None and not df.empty:
                bot.df = df
                bot.calcular_indicadores()
                self.logger.info(f"_cargar_historico: {symbol} cargado OK | {len(df)} velas | env={self.env}")

        except Exception as e:
            self.logger.error(f"Error cargando histórico {symbol}: {e}")

    def _cargar_posicion_existente(self, bot, symbol):
        """
        Carga posición existente desde Binance al iniciar el bot.
        Si hay balance del activo, calcula el precio de entrada promedio
        desde el historial de trades y configura el estado del bot.
        """
        try:
            # 1. Obtener balance del activo
            asset = symbol.replace("USDT", "")
            account = self.spot_client.account_spot()

            if not account or "balances" not in account:
                return

            balance = 0.0
            for b in account["balances"]:
                if b["asset"] == asset:
                    balance = float(b["free"]) + float(b.get("locked", 0))
                    break

            if balance <= 0:
                self.logger.info(f"{symbol}: Sin posición existente")
                return

            # Verificar si es dust (balance × precio < minNotional)
            price = bot._last_price() if bot.df is not None else 0
            if price <= 0:
                # Intentar obtener precio del ticker
                try:
                    ticker = self.spot_client.ticker_price(symbol)
                    price = float(ticker.get("price", 0))
                except Exception:
                    pass

            lot = self.bot_manager.lot_sizes.get(symbol, {}) if self.bot_manager else {}
            min_notional = lot.get("minNotional", 5.0)

            if price > 0 and (balance * price) < min_notional:
                self.logger.warning(
                    f"{symbol}: Dust detectado al cargar (${balance * price:.2f} < ${min_notional:.2f})"
                )
                self._dust_symbols.append(symbol)
                return

            # 2. Obtener trades recientes para calcular precio de entrada
            now = int(time.time() * 1000)
            day_ago = now - (24 * 60 * 60 * 1000)

            trades = self.spot_client.get_my_trades(symbol, limit=50, startTime=day_ago, endTime=now)

            if not trades:
                self.logger.warning(f"{symbol}: Balance={balance} pero sin trades recientes, usando precio actual")
                entry_price = bot._last_price() if bot.df is not None else 0
            else:
                # Calcular precio promedio ponderado de compras
                total_qty = 0.0
                total_cost = 0.0
                for t in trades:
                    if t["isBuyer"]:
                        qty = float(t["qty"])
                        cost = float(t["quoteQty"])
                        total_qty += qty
                        total_cost += cost

                entry_price = total_cost / total_qty if total_qty > 0 else 0

            if entry_price <= 0:
                self.logger.warning(f"{symbol}: No se pudo calcular precio de entrada")
                return

            # 3. Configurar estado del bot con posición existente
            bot.state["position"] = "LONG"
            bot.state["entry_price"] = entry_price
            bot.state["position_qty"] = balance
            bot.state["remaining_qty"] = balance
            bot.state["stop_loss"] = entry_price * (1 - bot.risk_cfg["stop_loss_pct"])
            bot.state["tp1_done"] = False
            bot.state["tp2_done"] = False
            bot.state["trailing_active"] = False
            bot.state["trail_high"] = None
            bot.state["trailing_stop"] = None

            # Reservar capital de la posición existente
            notional = balance * entry_price
            if self.capital_manager:
                self.capital_manager.reserve(notional)

            self.logger.warning(
                f"📥 {symbol}: POSICIÓN CARGADA | qty={balance:.4f} | entry={entry_price:.6f} | "
                f"SL={bot.state['stop_loss']:.6f} | reservado=${notional:.2f}"
            )

            # Incrementar contador de trades activos
            self.trades_count += 1
            if self.lbl_trades:
                self.lbl_trades.config(text=str(self.trades_count))

        except Exception as e:
            self.logger.error(f"Error cargando posición existente {symbol}: {e}")


# =============================================================================
# WIDGET POR SÍMBOLO: WidgetBotSymbol
# =============================================================================
class WidgetBotSymbol:
    """
    Widget individual para mostrar información de un símbolo.
    Incluye precio, indicadores, estado y controles.
    """

    def __init__(
        self,
        parent,
        symbol,
        activo,
        colors,
        config,
        on_start,
        on_stop,
        on_chart,
        on_test_buy=None,
        on_delete=None,
        on_sell_all=None,
        env="TESTNET",
        widget_width=280,
        widget_height=220,
    ):
        self.parent = parent
        self.symbol = symbol
        self.activo = activo
        self.colors = colors
        self.config = config
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_chart = on_chart
        self.on_test_buy = on_test_buy
        self.on_delete = on_delete
        self.on_sell_all = on_sell_all
        self.env = env
        self.widget_width = widget_width
        self.widget_height = widget_height

        self.frame = None
        self.running = False

        # Labels para actualizar
        self.lbl_price = None
        self.lbl_rsi = None
        self.lbl_macd = None
        self.lbl_estado = None
        self.lbl_entry = None
        self.lbl_tp = None
        self.lbl_pnl = None
        self.lbl_status_indicator = None
        self.lbl_trendok = None
        self.lbl_rsiok = None
        self.lbl_priceok = None
        self.btn_test_buy = None

    def crear_ui(self):
        """Crea la UI del widget"""
        # Frame principal con borde
        self.frame = tk.Frame(
            self.parent,
            bg=self.colors["cgcolor"],
            width=self.widget_width,
            height=self.widget_height,
            relief=tk.RIDGE,
            borderwidth=2,
        )
        self.frame.pack_propagate(False)

        # Header con símbolo
        header = tk.Frame(self.frame, bg="#2a4a5a")
        header.pack(fill=tk.X)

        # Botón X para eliminar (primero para que quede a la derecha)
        if self.on_delete:
            btn_delete = tk.Button(
                header,
                text="X",
                bg="#c62828",
                fg="white",
                font=("Arial", 8, "bold"),
                width=2,
                relief=tk.FLAT,
                command=self.on_delete,
            )
            btn_delete.pack(side=tk.RIGHT, padx=2, pady=2)

        # Indicador de status
        self.lbl_status_indicator = tk.Label(header, text="●", bg="#2a4a5a", fg="gray", font=("Arial", 12))
        self.lbl_status_indicator.pack(side=tk.LEFT, padx=5)

        tk.Label(
            header,
            text=self.symbol,
            bg="#2a4a5a",
            fg="white",
            font=("Arial", 11, "bold"),
        ).pack(side=tk.LEFT, pady=5)

        # Precio
        self.lbl_price = tk.Label(
            header,
            text="--",
            bg="#2a4a5a",
            fg="cyan",
            font=("Arial", 11, "bold"),
        )
        self.lbl_price.pack(side=tk.RIGHT, padx=10)

        # Contenido
        content = tk.Frame(self.frame, bg=self.colors["cgcolor"])
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Indicadores
        row = 0
        self._crear_label_row(content, "RSI:", "lbl_rsi", row)
        row += 1
        self._crear_label_row(content, "MACD:", "lbl_macd", row)
        row += 1
        self._crear_label_row(content, "Estado:", "lbl_estado", row)
        row += 1
        self._crear_label_row(content, "Entry:", "lbl_entry", row)
        row += 1
        self._crear_label_row(content, "TP:", "lbl_tp", row)
        row += 1
        self._crear_label_row(content, "PnL:", "lbl_pnl", row)

        # ─────────────────────────────────────────────────────────────
        # Línea separadora: Condiciones de compra GWI001
        # ─────────────────────────────────────────────────────────────
        row += 1
        separator = tk.Frame(content, bg="gray", height=1)
        separator.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)

        row += 1
        self._crear_label_row(content, "Trend:", "lbl_trendok", row, font_size=7)
        row += 1
        self._crear_label_row(content, "RSI:", "lbl_rsiok", row, font_size=7)
        row += 1
        self._crear_label_row(content, "Price:", "lbl_priceok", row, font_size=7)

        # Botones
        btn_frame = tk.Frame(self.frame, bg=self.colors["cgcolor"])
        btn_frame.pack(fill=tk.X, pady=5, padx=5)

        tk.Button(
            btn_frame,
            text="▶",
            bg="green",
            fg="white",
            width=3,
            command=self.on_start,
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            btn_frame,
            text="⏸️",
            bg="red",
            fg="white",
            width=3,
            command=self.on_stop,
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            btn_frame,
            text="📈",
            bg="blue",
            fg="white",
            width=3,
            command=self.on_chart,
        ).pack(side=tk.LEFT, padx=2)

        # SELL ALL - vender todo el balance del activo
        self.btn_sell_all = tk.Button(
            btn_frame,
            text="SELL",
            bg="#E91E63",
            fg="white",
            width=5,
            font=("Arial", 8, "bold"),
            command=self.on_sell_all if self.on_sell_all else lambda: None,
        )
        self.btn_sell_all.pack(side=tk.RIGHT, padx=2)

    def _crear_label_row(self, parent, label_text, attr_name, row, font_size=9):
        """Crea una fila con label y valor"""
        tk.Label(
            parent,
            text=label_text,
            bg=self.colors["cgcolor"],
            fg="gray",
            font=("Arial", font_size),
            anchor="w",
            width=8,
        ).grid(row=row, column=0, sticky="w")

        lbl_value = tk.Label(
            parent,
            text="--",
            bg=self.colors["cgcolor"],
            fg="white",
            font=("Arial", font_size),
            anchor="w",
        )
        lbl_value.grid(row=row, column=1, sticky="w")
        setattr(self, attr_name, lbl_value)

    def update_price(self, price):
        """Actualiza el precio"""
        self.lbl_price.config(text=f"{price:.4f}")

    def update_state(self, state, indicators, conditions):
        """Actualiza el estado y los indicadores"""
        # RSI
        rsi = indicators.get("rsi")
        if rsi:
            arrow = "▲" if rsi < 35 else "▼" if rsi > 65 else ""
            color = "lime" if rsi < 35 else "red" if rsi > 65 else "white"
            self.lbl_rsi.config(text=f"{rsi:.1f} {arrow}", fg=color)

        # MACD
        macd = indicators.get("macd")
        macd_signal = indicators.get("macd_signal")
        if macd is not None and macd_signal is not None:
            arrow = "▲" if macd > macd_signal else "▼"
            color = "lime" if macd > macd_signal else "red"
            self.lbl_macd.config(text=arrow, fg=color)

        # Estado
        position = state.get("position", "NONE")
        color = "lime" if position == "LONG" else "white"
        self.lbl_estado.config(text=position, fg=color)

        # Entry + importe de colocación
        entry = state.get("entry_price")
        qty = state.get("remaining_qty", 0)
        if entry and qty > 0:
            importe = entry * qty
            self.lbl_entry.config(text=f"{entry:.4f}  :: (${importe:.2f})")
        else:
            self.lbl_entry.config(text=f"{entry:.4f}" if entry else "--")

        # TP + Trailing
        tp1 = "✓" if state.get("tp1_done") else "○"
        if state.get("trailing_active"):
            trail_stop = state.get("trailing_stop")
            trail_txt = f"TRAIL:{trail_stop:.4f}" if trail_stop else "TRAIL:--"
            self.lbl_tp.config(text=f"TP1:{tp1} | {trail_txt}", fg="cyan")
        else:
            self.lbl_tp.config(text=f"TP1:{tp1}", fg="white")

        # PnL + cantidad del lote
        if entry and qty > 0:
            last = indicators.get("last_price", entry)
            pnl_pct = ((last - entry) / entry) * 100
            color = "lime" if pnl_pct > 0 else "red"
            self.lbl_pnl.config(text=f"{pnl_pct:+.2f}%  :: (qty:{qty})", fg=color)
        else:
            self.lbl_pnl.config(text="--", fg="white")

        # ─────────────────────────────────────────────────────────────
        # Condiciones de compra (siempre visibles)
        # ─────────────────────────────────────────────────────────────
        if conditions:
            # Trend: MACD > Signal AND EMA_fast > EMA_slow
            trend_ok = conditions.get("trend_ok", {})
            trend_val = trend_ok.get("value", False)
            trend_detail = trend_ok.get("detail", "--")
            trend_icon = "✓" if trend_val else "✗"
            trend_color = "lime" if trend_val else "red"
            self.lbl_trendok.config(text=f"{trend_icon} {trend_detail}", fg=trend_color)

            # RSI: RSI < rsi_sell (zona operable, evita sobrecompra)
            rsi_ok = conditions.get("rsi_ok", {})
            rsi_val = rsi_ok.get("value", False)
            rsi_detail = rsi_ok.get("detail", "--")
            rsi_icon = "✓" if rsi_val else "✗"
            rsi_color = "lime" if rsi_val else "red"
            self.lbl_rsiok.config(text=f"{rsi_icon} {rsi_detail}", fg=rsi_color)

            # Price: Precio > EMA_fast (confirma movimiento a favor)
            price_ok = conditions.get("price_ok", {})
            price_val = price_ok.get("value", False)
            price_detail = price_ok.get("detail", "--")
            price_icon = "✓" if price_val else "✗"
            price_color = "lime" if price_val else "red"
            self.lbl_priceok.config(text=f"{price_icon} {price_detail}", fg=price_color)

    def set_running(self, running):
        """Actualiza el indicador de running"""
        self.running = running
        color = "lime" if running else "gray"
        self.lbl_status_indicator.config(fg=color)

    def set_env(self, env):
        """Activa/desactiva botón TEST según ambiente"""
        self.env = env
        if self.btn_test_buy:
            self.btn_test_buy.config(state=tk.NORMAL if env == "TESTNET" else tk.DISABLED)
