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
    np,
    timedelta,
)
import os
from Modulos_Mysql import BDsystem, RepositorioOportunidadesBuySell, PlanInversion
from Modulos_Utilitarios import calcular_indicadores_df, define_FileCache
from Class_ApiBinnace import BinanceClient, BinanceStreamClient
from Class_customer import DataHub, MyMessageBox
from Modulos_Comunes import diaria_book_performance, proceso_update_performance


# =============================================================================
# PERSISTENCIA DE ESTADO: FileStateRepo
# =============================================================================
class FileStateRepo:
    """Persiste el estado del bot en archivos JSON por símbolo.
    Directorio: <cwd>/tmp/bot_states/<symbol>.json
    """

    def __init__(self):
        self._dir = define_FileCache("bot_states")
        os.makedirs(self._dir, exist_ok=True)

    def _path(self, symbol: str) -> str:
        return os.path.join(self._dir, f"{symbol}.json")

    def save_state(self, symbol: str, state: dict):
        try:
            with open(self._path(symbol), "w") as f:
                json.dump(state, f, default=str)
        except Exception as e:
            logging.getLogger(__name__).error(f"FileStateRepo.save_state({symbol}): {e}")

    def load_state(self, symbol: str) -> dict:
        path = self._path(symbol)
        if not os.path.exists(path):
            return {}
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            logging.getLogger(__name__).error(f"FileStateRepo.load_state({symbol}): {e}")
            return {}

    def delete_state(self, symbol: str):
        try:
            path = self._path(symbol)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


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
            # SL order en Binance (red de seguridad)
            "sl_order_id": None,
            # Cooldown: timestamp ISO del último trade cerrado
            "last_trade_time": None,
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
        regime = self._check_market_regime()

        conditions = {
            "regime_ok": {
                "value": regime == "BULL",
                "detail": regime,
            },
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

        # Post-TP1: evaluar TP2
        if self.state["tp1_done"] and not self.state["tp2_done"] and self._should_take_tp2(price):
            return "TP2", conditions

        # Post-TP2 (o TP1 si no hay TP2): trailing stop
        if self.state["tp2_done"] or (self.state["tp1_done"] and not self.risk_cfg.get("tp2_pct")):
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
            last_price = self._last_price()
            vol_rel = None
            if "Volume" in self.df.columns and len(self.df) >= 20:
                vol_mean = float(self.df["Volume"].tail(20).mean())
                vol_rel = round(float(self.df["Volume"].iloc[-1]) / vol_mean, 2) if vol_mean > 0 else None
            return {
                "rsi": float(self.df["rsi"].iloc[-1]) if "rsi" in self.df.columns else None,
                "macd": float(self.df["macd"].iloc[-1]) if "macd" in self.df.columns else None,
                "macd_signal": float(self.df["macd_signal"].iloc[-1]) if "macd_signal" in self.df.columns else None,
                "macd_hist": float(self.df["macd_hist"].iloc[-1]) if "macd_hist" in self.df.columns else None,
                "ema_fast": float(self.df["ema_fast"].iloc[-1]) if "ema_fast" in self.df.columns else None,
                "ema_slow": float(self.df["ema_slow"].iloc[-1]) if "ema_slow" in self.df.columns else None,
                "ema100": float(self.df["ema100"].iloc[-1]) if "ema100" in self.df.columns else None,
                "ema200": float(self.df["ema200"].iloc[-1]) if "ema200" in self.df.columns else None,
                "atr14": round(self._calc_atr14(), 6),
                "vol_rel": vol_rel,
                "regime": self._check_market_regime(),
                "last_price": last_price,
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

        # Gate estructural: solo operar LONG en régimen BULL
        if self._check_market_regime() != "BULL":
            return False

        # Cooldown: no re-entrar hasta que hayan pasado cooldown_hours desde el último trade
        last_trade_str = self.state.get("last_trade_time")
        if last_trade_str:
            try:
                last_trade_dt = datetime.fromisoformat(last_trade_str)
                cooldown_h = self.risk_cfg.get("cooldown_hours", 4)
                elapsed_h = (datetime.now() - last_trade_dt).total_seconds() / 3600
                if elapsed_h < cooldown_h:
                    return False
            except Exception:
                pass

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

    def _check_market_regime(self) -> str:
        """Clasifica régimen estructural basado en EMA100/EMA200.
        Retorna: 'BULL' | 'RANGE' | 'BEAR'
        """
        if self.df is None or "ema100" not in self.df.columns or "ema200" not in self.df.columns:
            return "RANGE"
        ema100 = self.df["ema100"].iloc[-1]
        ema200 = self.df["ema200"].iloc[-1]
        price = self.df["Close"].iloc[-1]
        if price > ema100 and ema100 > ema200:
            return "BULL"
        if price < ema100 and ema100 < ema200:
            return "BEAR"
        return "RANGE"

    def _should_exit(self, price: float) -> bool:
        # Solo salir por Stop Loss (RSI no fuerza exit, solo bloquea compras)
        if self.state["stop_loss"] is None:
            return False

        return price <= self.state["stop_loss"]

    # =========================
    # TAKE PROFIT (PRIVADO)
    # =========================
    def _should_take_tp1(self, price: float) -> bool:
        if self.state["entry_price"] is None:
            return False

        target = self.state["entry_price"] * (1 + self.risk_cfg["tp1_pct"])
        return price >= target

    def _should_take_tp2(self, price: float) -> bool:
        if self.state["entry_price"] is None:
            return False

        tp2_pct = self.risk_cfg.get("tp2_pct", 0)
        if not tp2_pct:
            return False
        target = self.state["entry_price"] * (1 + tp2_pct)
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
    def _calc_position_size(self, price: float, capital_per_bot: float) -> float:
        # capital_per_bot ya viene calculado como capital_total / max_bots
        risk_amount = capital_per_bot * self.risk_cfg["risk_per_trade"]
        sl_pct = self.risk_cfg.get("stop_loss_pct", 0.02)
        return risk_amount / (price * sl_pct)

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
            "sl_order_id": None,
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

    def calcular_scoring(self, contexto_superior=None, lateralidad=None, momentum=None) -> dict:
        """
        Calcula score técnico para priorización de activos.
        Score base: RSI (-1 a +2), MACD (-2 a +2), EMA (-2 a +2), Volatilidad (-1 a +1).
        Contexto superior: penalización -5 si TF superior no confirma tendencia.
        Lateralidad: penalización -3 si mercado lateral (3/4 métricas no cumplen).
        Momentum: penalización -2 si sobreextendido o RSI>75 en TF superior.
        """
        resultado = {
            "score_total": 0,
            "score_base": 0,
            "score_contexto": 0,
            "score_lateral": 0,
            "score_momentum": 0,
            "score_rsi": 0,
            "score_macd": 0,
            "score_ema": 0,
            "score_vol": 0,
            "prioridad": "BLOQUEADO",
            "permitir_compra": False,
            "contexto_ok": True,
            "contexto_detalle": {},
            "lateral_ok": True,
            "lateral_detalle": {},
            "momentum_ok": True,
            "momentum_fase": "indefinido",
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

            score_base = score_rsi + score_macd + score_ema + score_vol

            # --- Contexto Superior (penalización estructural) ---
            score_contexto = 0
            contexto_ok = True
            contexto_detalle = {}
            if contexto_superior is not None:
                contexto_ok = contexto_superior.get("contexto_ok", True)
                contexto_detalle = contexto_superior.get("detalle", {})
                if not contexto_ok:
                    score_contexto = -5

            # --- Filtro Anti-Lateralidad (penalización táctica) ---
            score_lateral = 0
            lateral_ok = True
            lateral_detalle = {}
            if lateralidad is not None:
                lateral_ok = lateralidad.get("ok", True)
                lateral_detalle = lateralidad.get("detalle", {})
                if not lateral_ok:
                    score_lateral = -3

            # --- Filtro Momentum Débil (sobreextensión / pérdida de fuerza) ---
            score_momentum = 0
            momentum_ok = True
            momentum_fase = "indefinido"
            if momentum is not None:
                momentum_ok = momentum.get("ok", True)
                momentum_fase = momentum.get("fase", "indefinido")
                if not momentum_ok:
                    score_momentum = -2

            total = score_base + score_contexto + score_lateral + score_momentum
            if not contexto_ok:
                total = min(total, 0)

            # Clasificación (prioridad del filtro más restrictivo primero)
            if not contexto_ok and score_base >= 1:
                prioridad = "Fuera Ctx"
            elif not lateral_ok and score_base >= 1:
                prioridad = "Lateral"
            elif not momentum_ok and score_base >= 1:
                prioridad = "MomDebil"
            elif total >= 5:
                prioridad = "Alta"
            elif total >= 3:
                prioridad = "Media"
            elif total >= 1:
                prioridad = "Revisión"
            else:
                prioridad = "Bloqueado"

            resultado = {
                "score_total": total,
                "score_base": score_base,
                "score_contexto": score_contexto,
                "score_lateral": score_lateral,
                "score_momentum": score_momentum,
                "score_rsi": score_rsi,
                "score_macd": score_macd,
                "score_ema": score_ema,
                "score_vol": score_vol,
                "prioridad": prioridad,
                "permitir_compra": total >= 3,
                "contexto_ok": contexto_ok,
                "contexto_detalle": contexto_detalle,
                "lateral_ok": lateral_ok,
                "lateral_detalle": lateral_detalle,
                "momentum_ok": momentum_ok,
                "momentum_fase": momentum_fase,
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
        config=None,
        env="TESTNET",
        on_trade_complete=None,
        on_trade_booktrading=None,
    ):
        self.spot_client = spot_client
        self.order_manager = order_manager
        self.capital_manager = capital_manager
        self.config = config or {}
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

    def _format_price(self, symbol, price):
        """Ajusta precio según tickSize del símbolo."""
        lot = self.lot_sizes.get(symbol)
        if not lot or "tickSize" not in lot:
            return round(price, 8)
        tick = lot["tickSize"]
        if tick > 0:
            price = price - (price % tick)
        tick_str = f"{tick:.10f}".rstrip("0")
        decimals = len(tick_str.split(".")[-1]) if "." in tick_str else 0
        return round(price, decimals)

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
    # STOP LOSS EN EXCHANGE
    # =========================
    def _place_sl_order(self, bot):
        """Coloca STOP_LOSS_LIMIT en Binance como red de seguridad."""
        try:
            sl_price = (
                bot.state.get("trailing_stop") if bot.state.get("trailing_active") else bot.state.get("stop_loss")
            )
            if not sl_price:
                return
            qty = bot.state["remaining_qty"]
            qty = self._format_qty(bot.symbol, qty)
            if qty <= 0:
                return
            sl_price = self._format_price(bot.symbol, sl_price)
            limit_price = self._format_price(bot.symbol, sl_price * 0.99)  # 1% slippage para flash crash

            order = self.spot_client.get_new_order(
                symbol=bot.symbol,
                side="SELL",
                type="STOP_LOSS_LIMIT",
                quantity=qty,
                stopPrice=sl_price,
                price=limit_price,
                timeInForce="GTC",
            )
            if order:
                bot.state["sl_order_id"] = order["orderId"]
                self.logger.warning(
                    f"SL ORDER {bot.symbol}: orderId={order['orderId']} "
                    f"stopPrice={sl_price} limitPrice={limit_price} qty={qty}"
                )
        except Exception as e:
            self.logger.error(f"_place_sl_order({bot.symbol}): {e}")

    def _cancel_sl_order(self, bot):
        """Cancela la orden STOP_LOSS_LIMIT en Binance (por ID o todas las abiertas)."""
        sl_id = bot.state.get("sl_order_id")
        if sl_id:
            try:
                self.spot_client.get_cancel_order(symbol=bot.symbol, orderId=sl_id)
                self.logger.warning(f"SL CANCELLED {bot.symbol}: orderId={sl_id}")
            except Exception as e:
                self.logger.warning(f"Ya estaba CANCELLED {bot.symbol}: orderId={sl_id}: Error: {e}")
        else:
            # Sin ID guardado (ej: posición cargada al reiniciar) → cancelar todas
            try:
                self.spot_client.cancel_all_orders(bot.symbol)
                self.logger.warning(f"SL CANCELLED {bot.symbol}: todas las órdenes abiertas")
            except Exception as e:
                self.logger.warning(f"Ya estaban CANCELLED {bot.symbol}: sin órdenes abiertas (OK): ERROR {e}")

        bot.state["sl_order_id"] = None

    # =========================
    # EJECUCION ORDENES
    # =========================
    def _log_orden(self, symbol, intent, order):
        """Log detallado de orden ejecutada: fills, precio real, comisiones."""
        try:
            order_id = order.get("orderId", "?")
            side = order.get("side", "?")
            status = order.get("status", "?")
            exec_qty = order.get("executedQty", "?")
            cummulative = order.get("cummulativeQuoteQty", "?")

            fills = order.get("fills", [])
            total_commission = 0.0
            avg_price = 0.0
            commission_asset = ""
            if fills:
                total_qty = sum(float(f.get("qty", 0)) for f in fills)
                total_cost = sum(float(f.get("qty", 0)) * float(f.get("price", 0)) for f in fills)
                total_commission = sum(float(f.get("commission", 0)) for f in fills)
                commission_asset = fills[0].get("commissionAsset", "")
                avg_price = total_cost / total_qty if total_qty > 0 else 0

            self.logger.warning(
                f"ORDER {symbol} [{intent}] | side={side} status={status} | "
                f"orderId={order_id} | qty={exec_qty} | total={cummulative} USDT | "
                f"avgPrice={avg_price:.6f} | commission={total_commission:.6f} {commission_asset}"
            )
        except Exception as e:
            self.logger.error(f"_log_orden({symbol}): {e}")

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
        max_bots = self.config.get("max_active_bots", 3)
        capital_total = self.config.get("capital", 0)
        capital_per_bot = capital_total / max_bots

        available = self.capital_manager.get_available_capital()
        if available < capital_per_bot * 0.5:
            self.logger.warning(
                f"{bot.symbol}: Capital insuficiente (disponible={available:.2f}, necesario~{capital_per_bot:.2f})"
            )
            return

        qty_original = bot._calc_position_size(price, capital_per_bot)
        qty = self._format_qty(bot.symbol, qty_original)

        self.logger.warning(
            f"{bot.symbol}: BUY eval | price={price:.6f} capital={capital_per_bot:.2f} "
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
            qty_adjusted = self._format_qty(bot.symbol, qty_min * 1.05)  # +5% margen para absorber redondeo

            # Verificar que tras redondeo siga arriba del mínimo
            if qty_adjusted * price < min_notional:
                step = lot.get("stepSize", 0.1)
                qty_adjusted += step
                qty_adjusted = self._format_qty(bot.symbol, qty_adjusted)

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

        self.logger.warning(
            f"API REQUEST {bot.symbol} | side=BUY type=MARKET qty={qty} "
            f"price~{price:.6f} notional~{qty * price:.2f} USDT | capital={capital_per_bot:.2f}"
        )

        order = self.spot_client.get_new_order(
            symbol=bot.symbol,
            side="BUY",
            type="MARKET",
            quantity=qty,
        )

        if not order:
            self.logger.error(f"{bot.symbol}: Orden BUY fallida")
            return

        self._log_orden(bot.symbol, "BUY", order)

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

        # Colocar STOP_LOSS_LIMIT en Binance como red de seguridad
        self._place_sl_order(bot)

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

        self.logger.warning(
            f"API REQUEST {bot.symbol} | side=SELL type=MARKET intent={intent} "
            f"qty={qty} price~{price:.6f} notional~{qty * price:.2f} USDT"
        )

        # cancela orden previa y update en exchange: cancelar SL viejo, colocar nuevo (qty reducida + trailing)
        self._cancel_sl_order(bot)

        order = self.spot_client.get_new_order(
            symbol=bot.symbol,
            side="SELL",
            type="MARKET",
            quantity=qty,
        )

        if not order:
            self.logger.error(f"{bot.symbol}: Orden {intent} fallida")
            return

        self._log_orden(bot.symbol, intent, order)

        order_id = order["orderId"]
        self.order_manager.register_order(symbol=bot.symbol, order_id=order_id, intent=intent)

        # actualizan qty remainning
        if intent == "TP1":
            bot.state["tp1_done"] = True
            bot.state["remaining_qty"] -= qty
            # Post-TP1: mover SL a breakeven para proteger ganancia
            bot.state["stop_loss"] = bot.state["entry_price"]
            # Trailing solo arranca aquí si no hay TP2 configurado
            if not bot.risk_cfg.get("tp2_pct"):
                atr = bot._calc_atr14()
                trail_mult = bot.risk_cfg.get("trail_mult", 1.5)
                bot.state["trailing_active"] = True
                bot.state["trail_high"] = price
                bot.state["trailing_stop"] = price - (trail_mult * atr)
                self.logger.warning(
                    f"{bot.symbol}: TRAILING activado post-TP1 | high={price:.6f} "
                    f"stop={bot.state['trailing_stop']:.6f} ATR={atr:.6f} mult={trail_mult}"
                )

        elif intent == "TP2":
            bot.state["tp2_done"] = True
            bot.state["remaining_qty"] -= qty
            # Post-TP2: activar trailing sobre el remanente
            atr = bot._calc_atr14()
            trail_mult = bot.risk_cfg.get("trail_mult", 1.5)
            bot.state["trailing_active"] = True
            bot.state["trail_high"] = price
            bot.state["trailing_stop"] = price - (trail_mult * atr)
            self.logger.warning(
                f"{bot.symbol}: TRAILING activado post-TP2 | high={price:.6f} "
                f"stop={bot.state['trailing_stop']:.6f} ATR={atr:.6f} mult={trail_mult}"
            )

        self.capital_manager.release(qty * price)

        # Actualizar SL en exchange: colocar nuevo (qty reducida + trailing)
        if bot.state["remaining_qty"] > 0:
            self._place_sl_order(bot)

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
        # Cancelar SL primero para liberar balance locked
        self._cancel_sl_order(bot)

        # Usar balance real de Binance (ahora free, ya no locked)
        real_qty = self._get_real_balance(bot.symbol)
        qty = self._format_qty(bot.symbol, real_qty)

        if qty <= 0:
            self.logger.warning(f"{bot.symbol}: EXIT sin balance (SL de Binance ya ejecutó), limpiando estado")
            # Guardar datos antes de resetear
            entry = bot.state.get("entry_price")
            exit_qty = bot.state.get("remaining_qty", 0) or bot.state.get("position_qty", 0)
            sl_order_id = bot.state.get("sl_order_id")

            bot.state.update(
                {
                    "position": "NONE",
                    "entry_price": None,
                    "remaining_qty": 0.0,
                    "trailing_active": False,
                    "trail_high": None,
                    "trailing_stop": None,
                    "sl_order_id": None,
                    "last_trade_time": datetime.now().isoformat(),
                }
            )
            bot.state_repo.delete_state(bot.symbol) if bot.state_repo else None

            # Buscar la orden real de SL en Binance y registrar en booktrading
            if self.on_trade_booktrading:
                real_order = None
                try:
                    if sl_order_id:
                        # Caso normal: tenemos el ID de la orden SL
                        real_order = self.spot_client.get_order(symbol=bot.symbol, orderId=sl_order_id)
                        if real_order and real_order.get("status") != "FILLED":
                            self.logger.warning(
                                f"{bot.symbol}: SL order {sl_order_id} no está FILLED: {real_order.get('status')}"
                            )
                            real_order = None
                    else:
                        # Fallback: sl_order_id desconocido (ej: restart sin estado) →
                        # buscar el último trade SELL ejecutado en Binance
                        now = int(time.time() * 1000)
                        trades = self.spot_client.get_my_trades(bot.symbol, limit=5, startTime=now - 3600000)
                        sell_trades = [t for t in (trades or []) if not t.get("isBuyer")]
                        if sell_trades:
                            last_sell = sorted(sell_trades, key=lambda t: t["time"], reverse=True)[0]
                            # Construir objeto orden compatible con on_trade_booktrading
                            real_order = {
                                "orderId": last_sell.get("orderId"),
                                "symbol": bot.symbol,
                                "side": "SELL",
                                "type": "STOP_LOSS_LIMIT",
                                "status": "FILLED",
                                "executedQty": last_sell.get("qty"),
                                "cummulativeQuoteQty": last_sell.get("quoteQty"),
                                "price": last_sell.get("price"),
                                "fills": [last_sell],
                                "transactTime": last_sell.get("time"),
                            }
                            self.logger.warning(
                                f"{bot.symbol}: sl_order_id desconocido → usando último SELL trade como fallback"
                            )
                        else:
                            self.logger.warning(
                                f"{bot.symbol}: No se encontró trade SELL reciente → booktrading no registrado"
                            )

                    if real_order:
                        self.on_trade_booktrading(bot.symbol, order=real_order)
                        self.logger.warning(
                            f"📝 {bot.symbol}: Booktrading registrado (SL Binance) | "
                            f"orderId={real_order.get('orderId')} | qty={real_order.get('executedQty')}"
                        )
                except Exception as e:
                    self.logger.error(f"{bot.symbol}: Error consultando SL order: {e}")

            if self.on_trade_complete:
                self.on_trade_complete(bot.symbol)

            if self.capital_manager and entry and exit_qty > 0:
                self.capital_manager.release(exit_qty * entry)

            return

        price = bot._last_price()
        notional = qty * price
        lot = self.lot_sizes.get(bot.symbol, {})
        min_notional = lot.get("minNotional", 5.0)

        # Si el valor es menor al mínimo de Binance, es dust - convertir a BNB y limpiar
        if notional < min_notional:
            self.logger.warning(f"{bot.symbol}: EXIT dust (${notional:.2f} < ${min_notional:.2f}), convirtiendo a BNB")
            entry_price = bot.state.get("entry_price")
            exit_qty = bot.state.get("remaining_qty", 0) or bot.state.get("position_qty", 0)
            self._convert_dust_to_bnb(bot.symbol)
            bot.state.update(
                {
                    "position": "NONE",
                    "entry_price": None,
                    "remaining_qty": 0.0,
                    "trailing_active": False,
                    "trail_high": None,
                    "trailing_stop": None,
                    "sl_order_id": None,
                    "last_trade_time": datetime.now().isoformat(),
                }
            )

            if self.on_trade_complete:
                self.on_trade_complete(bot.symbol)

            if self.capital_manager and entry_price and exit_qty > 0:
                self.capital_manager.release(exit_qty * entry_price)

            return

        self.logger.warning(
            f"API REQUEST {bot.symbol} | side=SELL type=MARKET intent=EXIT-{reason} "
            f"qty={qty} price~{price:.6f} notional~{notional:.2f} USDT"
        )

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
                    "sl_order_id": None,
                    "last_trade_time": datetime.now().isoformat(),
                }
            )
            return

        self._log_orden(bot.symbol, f"EXIT-{reason}", order)

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
        bot.state["sl_order_id"] = None
        bot.state["last_trade_time"] = datetime.now().isoformat()

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
    ACCOUNT = None
    VEHICULO = None
    COLUMNS = 3
    WIDGET_WIDTH = 300
    WIDGET_HEIGHT = 290

    # Factores de ajuste por temporalidad (base = 5m)
    INTERVAL_FACTORS = {
        "1m": {"tp1": 0.008, "sl": 0.005, "trail_mult": 1.0},
        "3m": {"tp1": 0.01, "sl": 0.008, "trail_mult": 1.0},
        "5m": {"tp1": 0.015, "sl": 0.01, "trail_mult": 1.2},
        "15m": {"tp1": 0.02, "sl": 0.015, "trail_mult": 1.5},
        "30m": {"tp1": 0.025, "sl": 0.02, "trail_mult": 1.5},
        "1h": {"tp1": 0.03, "sl": 0.025, "trail_mult": 1.5},
        "4h": {"tp1": 0.05, "sl": 0.035, "trail_mult": 2.0},
        "1d": {"tp1": 0.08, "sl": 0.05, "trail_mult": 2.5},
    }

    # Mapeo de timeframe operativo → timeframe superior (contexto estructural)
    SUPERIOR_INTERVALS = {
        "1m": "5m",
        "3m": "15m",
        "5m": "30m",
        "15m": "1h",
        "30m": "4h",
        "1h": "4h",
        "4h": "1d",
        "1d": None,
    }
    CONTEXTO_PENALIZACION = -5
    CONTEXTO_CACHE_TTL = 600  # segundos (10 min)

    # Filtro Anti-Lateralidad: umbrales por timeframe (ATR%, rango%, dist_ema%, vol_ratio)
    LATERAL_PENALIZACION = -3
    LATERAL_MIN_CONDICIONES = 4  # 3 de 4 para considerar mercado con tendencia
    LATERAL_UMBRALES = {
        "1m": {"atr_min": 0.008, "rango_min": 0.006, "dist_ema_min": 0.002, "vol_ratio_min": 1.1},
        "3m": {"atr_min": 0.009, "rango_min": 0.007, "dist_ema_min": 0.002, "vol_ratio_min": 1.1},
        "5m": {"atr_min": 0.010, "rango_min": 0.008, "dist_ema_min": 0.003, "vol_ratio_min": 1.2},
        "15m": {"atr_min": 0.012, "rango_min": 0.010, "dist_ema_min": 0.003, "vol_ratio_min": 1.2},
        "30m": {"atr_min": 0.013, "rango_min": 0.011, "dist_ema_min": 0.003, "vol_ratio_min": 1.2},
        "1h": {"atr_min": 0.015, "rango_min": 0.012, "dist_ema_min": 0.003, "vol_ratio_min": 1.2},
        "4h": {"atr_min": 0.020, "rango_min": 0.015, "dist_ema_min": 0.004, "vol_ratio_min": 1.3},
        "1d": {"atr_min": 0.025, "rango_min": 0.020, "dist_ema_min": 0.005, "vol_ratio_min": 1.3},
    }

    # Filtro Momentum Débil: penalización por sobreextensión o pérdida de fuerza en 4H
    MOMENTUM_PENALIZACION = -2

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
        self.right = ttk.Frame(parent, padding=(3, 6, 1, 1), style="C.TFrame", height=600)
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
        self.state_repo = FileStateRepo()

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

        # Scoring cycle (independiente del intervalo de velas)
        self._scoring_timer_id = None
        self._scoring_interval = 120000  # 2 minutos en ms

        # Cache de contexto superior por símbolo
        self._contexto_cache = {}  # {symbol: {"timestamp": float, "resultado": dict}}

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
            "cooldown_hours": 4,
        }

        try:
            sesion = BDsystem.get_sesion_by_vehiculo("BotCrypto")

            # Ambiente desde columna environment
            if sesion:
                db_env = (sesion.get("environment") or "").strip().upper()
                if db_env in ("TESTNET", "PRODUCTION"):
                    # Asignar env/cuenta ANTES de json.loads para que no queden en None si falla
                    self.env = db_env
                    self.ACCOUNT = sesion.get("idcuenta")
                    self.VEHICULO = sesion.get("vehiculo")
                    config["env"] = db_env

                    self.logger.warning(f"✅ Ambiente '{db_env}', inicializado correctamente")
                    try:
                        config = json.loads(sesion.get("private_key") or "{}")
                    except Exception as je:
                        self.logger.warning(f"⚠️ private_key JSON inválido, usando config default: {je}")

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
        # BD tiene prioridad; INTERVAL_FACTORS solo aplica como fallback
        config["tp1_pct"] = config.get("tp1_pct") or factors["tp1"]
        config["stop_loss_pct"] = config.get("stop_loss_pct") or factors["sl"]
        config["trail_mult"] = config.get("trail_mult") or factors["trail_mult"]

        self.logger.warning(
            f"⚙️ Config ({interval}): "
            f"capital={config.get('capital')} | risk={config.get('risk_per_trade',0)*100:.1f}% | "
            f"TP1={config['tp1_pct']*100:.1f}% | Trail×={config['trail_mult']} | SL={config['stop_loss_pct']*100:.1f}% | "
            f"tp1_size={config.get('tp1_size')} | "
            f"RSI={config.get('rsi_buy')}/{config.get('rsi_sell')} | max_bots={config.get('max_active_bots', 3)} | "
            f"cooldown={config.get('cooldown_hours', 4)}h"
        )

        return config

    def inicializar(self):
        """Inicializa la UI completa"""  # gwi001
        try:
            self._crear_graficos()
            self._crear_panel_control()
            self._crear_canvas_scrollable()
            self._crear_panel_scoring()
            self._cargar_simbolos()
            self._inicializar_managers()
            self._iniciar_auto_refresh()
            self._schedule_diaria_performace()

            # Auto-start: iniciar bots al cargar la app, siempre self.env != None
            if self.all_activos and self.env:
                self._on_start_all()
        except Exception as e:
            self.logger.error(f"Error inicializando BotCryptoUI: {e}")
            traceback.print_exc()

    # =========================================
    # CONSTRUYE DIARA y PERFORMACE vehiculo
    # =========================================
    def _get_insert_fallidos(self, desde=None, display_log=False):

        bnb_ticker = self.spot_client.ticker_price("BNBUSDT")
        PRICE_BNB = float(bnb_ticker.get("price", 0))
        CATEGORIA = "BotCrypto"
        DIVISA = "USD"
        book, ix = PlanInversion().select_otros_activos(account=self.ACCOUNT, symbol="all")

        for keys in book:
            symbol = keys["symbol"]
            efecha = desde
            hoy = datetime.now()
            sym_insertados = 0
            sym_existentes = 0

            while efecha <= hoy:
                sfecha = efecha
                efecha += timedelta(days=1)

                stime = int(sfecha.timestamp() * 1000)
                etime = int(efecha.timestamp() * 1000)

                if etime <= stime:
                    continue

                trades = self.spot_client.get_my_trades(symbol, limit=50, startTime=stime, endTime=etime)

                if not trades:
                    continue

                for trade in trades:
                    try:
                        qty = float(trade.get("qty", 0.0))
                        qty = qty if trade["isBuyer"] else -1 * qty
                        quoteqty = float(trade.get("quoteQty", 0.0))
                        price = float(trade.get("price", 0.0))
                        commission_raw = float(trade.get("commission", 0.0))
                        commission_asset = trade.get("commissionAsset", "")
                        commission = (
                            commission_raw * PRICE_BNB
                            if commission_asset == "BNB" and PRICE_BNB > 0
                            else commission_raw * price
                        )
                        fechahora = datetime.fromtimestamp(trade.get("time", 0) / 1000)

                        registro = {
                            "categoria": CATEGORIA,
                            "divisa": DIVISA,
                            "cuenta": self.ACCOUNT,
                            "cantidad": qty,
                            "producto": quoteqty,
                            "idtrans": str(trade.get("id")),
                            "preciotrans": price,
                            "preciocierre": price,
                            "tarifacomision": commission,
                            "mtmgp": 0.00,
                            "fechahora": fechahora,
                        }

                        # Validar si ya existe
                        found = self.repositorio.get_hash_booktrading(
                            accion="valida",
                            values=registro,
                            symbol=symbol,
                        )

                        if not found:
                            self.repositorio.insert_bottraderBook(values=registro, symbol=symbol, object="bottrader")
                            side = "BUY" if trade["isBuyer"] else "SELL"
                            if display_log:
                                print(
                                    f"  + {fechahora.strftime('%d-%b %H:%M')} | {side:4} | qty={abs(qty):>10.4f} | price={price:.6f} | ${quoteqty:.2f}"
                                )
                            sym_insertados += 1
                        else:
                            sym_existentes += 1

                    except Exception as e:
                        print(f"  ERROR: {e} | trade={trade}")

                # Espera para no saturar la API
                time.sleep(0.8)
            if display_log:
                print(f"  {symbol}: {sym_insertados} insertados, {sym_existentes} ya existían")

    def _schedule_diaria_performace(self):

        update = False
        if self.ACCOUNT:
            # for account BotCrypto
            t_wait, update = DataHub.last_process[self.VEHICULO], False

            self._get_insert_fallidos(desde=t_wait["diaria_book_performance"])
            update = diaria_book_performance(account=self.ACCOUNT, vehiculo=self.VEHICULO, proces=t_wait)

            # si actualizó tabla diaria, calcula proxima fecha de update
            if update:
                # agrega performance a la tabla
                proceso_update_performance(account=self.ACCOUNT, vehiculo=self.VEHICULO)

    # =========================================
    # PANEL DE GRAFICOS gwi001
    # =========================================
    def _crear_graficos(self):
        """Crea el panel lateral izquierdo con gráficos de performance y CAPITAL & RIESGO"""

        top = ttk.Frame(self.left, padding=(1, 1, 1, 1), style="C.TFrame")
        bot = ttk.Frame(self.left, padding=(1, 1, 1, 1), style="C.TFrame")
        cen = ttk.Frame(self.left, padding=(1, 1, 1, 1), style="C.TFrame")
        top.pack(side=tk.TOP)
        bot.pack(side=tk.BOTTOM)
        cen.pack(side=tk.LEFT)

        # Header fg0: título + botón refresh
        hdr0 = tk.Frame(top, bg=self.colors["cgcolor"])
        hdr0.pack(fill=tk.X)
        tk.Label(hdr0, text="PnL Diario", bg=self.colors["cgcolor"], fg="gray60", font=("Arial", 7)).pack(
            side=tk.LEFT, padx=4
        )
        tk.Button(
            hdr0,
            text="↺",
            bg=self.colors["cgcolor"],
            fg="gray60",
            font=("Arial", 7),
            relief="flat",
            bd=0,
            command=self._refresh_performance_charts,
        ).pack(side=tk.RIGHT, padx=2)

        self.fg0 = Figure(figsize=(2.9, 1.75), dpi=110, layout="tight")
        self.fg0.set_facecolor(self.colors["cgcolor"])
        self.cv0 = FigureCanvasTkAgg(self.fg0, master=top)
        self.cv0.draw()
        self.cv0.get_tk_widget().pack()

        # Header fg1: título
        hdr1 = tk.Frame(cen, bg=self.colors["cgcolor"])
        hdr1.pack(fill=tk.X)
        tk.Label(hdr1, text="PnL Acumulado", bg=self.colors["cgcolor"], fg="gray60", font=("Arial", 7)).pack(
            side=tk.LEFT, padx=4
        )

        self.fg1 = Figure(figsize=(2.9, 1.75), dpi=110, layout="constrained")
        self.fg1.set_facecolor(self.colors["cgcolor"])
        self.cv1 = FigureCanvasTkAgg(self.fg1, master=cen)
        self.cv1.draw()
        self.cv1.get_tk_widget().pack()

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

    # =========================================
    # GRAFICOS DE PERFORMANCE (fg0 / fg1)
    # =========================================
    def _refresh_performance_charts(self):
        """Lanza en thread la carga y dibujo de gráficos de performance."""
        threading.Thread(target=self._draw_performance_charts, daemon=True).start()

    def _perf_placeholder(self, msg):
        """Muestra mensaje de estado en fg0 y fg1 cuando no hay datos o hay error."""
        bg = self.colors["cgcolor"]

        def _do():
            for fig, cv in ((self.fg0, self.cv0), (self.fg1, self.cv1)):
                fig.clear()
                ax = fig.add_subplot(111)
                ax.set_facecolor(bg)
                fig.set_facecolor(bg)
                ax.text(0.5, 0.5, msg, transform=ax.transAxes, fontsize=8, color="0.5", ha="center", va="center")
                for sp in ax.spines.values():
                    sp.set_edgecolor("0.3")
                ax.set_xticks([])
                ax.set_yticks([])
                cv.draw()

        try:
            self.parent.after(0, _do)
        except RuntimeError:
            pass

    def _perf_render(self, daily, by_sym):
        """Dibuja fg0 (PnL diario barras) y fg1 (PnL acumulado). Corre en main thread."""
        bg = self.colors["cgcolor"]
        green = "#00ff88"
        red = "#ff4444"

        # ── fg0: PnL DIARIO ────────────────────────────────────────────────────
        self.fg0.clear()
        ax0 = self.fg0.add_subplot(111)
        ax0.set_facecolor(bg)
        self.fg0.set_facecolor(bg)

        fechas = daily["fecha"].dt.strftime("%d/%m").tolist()
        valores = daily["pnl"].tolist()
        colores = [green if v >= 0 else red for v in valores]
        n = min(30, len(fechas))

        ax0.bar(range(n), valores[-n:], color=colores[-n:], width=0.7, linewidth=0)
        ax0.axhline(0, color="0.5", linewidth=0.5)
        ax0.set_xticks(range(n))
        ax0.set_xticklabels(fechas[-n:], fontsize=5, rotation=60, color="0.6")
        ax0.tick_params(axis="y", labelsize=6, colors="0.6")
        ax0.spines[["top", "right"]].set_visible(False)
        ax0.grid(True, color="0.5", linewidth=0.1)

        total_wins = int(daily["wins"].sum())
        total_losses = int(daily["losses"].sum())
        total_trades = total_wins + total_losses
        wr = (total_wins / total_trades * 100) if total_trades else 0
        total_pnl = daily["pnl"].sum()
        pnl_color = green if total_pnl >= 0 else red

        ax0.text(
            0.02,
            0.97,
            f"${total_pnl:+.2f}  WR:{wr:.0f}%  T:{total_trades}",
            transform=ax0.transAxes,
            fontsize=6.5,
            color=pnl_color,
            va="top",
            ha="left",
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor=bg, alpha=0.7),
        )
        for sp in ax0.spines.values():
            sp.set_edgecolor("0.3")
        self.cv0.draw()

        # ── fg1: PnL ACUMULADO (izq) + RANKING símbolos (der) ─────────────────
        self.fg1.clear()
        self.fg1.set_facecolor(bg)

        gs = self.fg1.add_gridspec(1, 2, width_ratios=[3, 1], wspace=0.07)
        ax1 = self.fg1.add_subplot(gs[0])  # línea acumulada
        axr = self.fg1.add_subplot(gs[1])  # ranking

        # ── Línea acumulada ─────────────────────────────────────────────────────
        ax1.set_facecolor(bg)
        cum_vals = daily["cum_pnl"].tolist()
        x_vals = list(range(len(cum_vals)))
        color_line = green if cum_vals[-1] >= 0 else red

        cv = np.array(cum_vals)
        ax1.plot(x_vals, cv, color=color_line, linewidth=1.0)
        ax1.fill_between(x_vals, 0, cv, where=(cv >= 0), color=green, alpha=0.40, interpolate=True)
        ax1.fill_between(x_vals, 0, cv, where=(cv < 0), color=red, alpha=0.40, interpolate=True)
        ax1.axhline(0, color="0.5", linewidth=0.5)
        ax1.annotate(
            f"${cum_vals[-1]:+.2f}",
            xy=(len(cum_vals) - 1, cum_vals[-1]),
            fontsize=6,
            color=color_line,
            xytext=(-4, 4),
            textcoords="offset points",
            ha="right",
        )
        ax1.tick_params(axis="both", labelsize=6, colors="0.6")
        ax1.spines[["top", "right"]].set_visible(False)
        for sp in ax1.spines.values():
            sp.set_edgecolor("0.3")

        # ── Ranking símbolos ────────────────────────────────────────────────────
        axr.set_facecolor(bg)
        axr.set_xticks([])
        axr.set_yticks([])
        axr.spines[["top", "right"]].set_visible(False)
        for sp in axr.spines.values():
            sp.set_edgecolor("0.25")

        if not by_sym.empty:
            # ordenar: mejor arriba
            ranking = by_sym.sort_values("pnl", ascending=False).head(8)
            y_step = 1.0 / (len(ranking) + 1)
            for i, (_, srow) in enumerate(ranking.iterrows()):
                sym = str(srow["simbolo"]).replace("USDT", "")
                pnl = float(srow["pnl"])
                wins = int(srow["wins"])
                tot = int(srow["trades"])
                col = green if pnl >= 0 else red
                y = 1.0 - (i + 1) * y_step
                # barra de fondo proporcional al PnL absoluto
                max_pnl = float(by_sym["pnl"].abs().max()) or 1
                bar_w = abs(pnl) / max_pnl * 0.9
                axr.barh(y, bar_w, height=y_step * 0.7, color=col, alpha=0.18, left=0)
                axr.text(0.04, y, f"{sym}", transform=axr.transAxes, fontsize=6.5, color=col, va="center")
                axr.text(
                    0.96, y, f"${pnl:+.2f}", transform=axr.transAxes, fontsize=6, color=col, va="center", ha="right"
                )

        self.cv1.draw()

    def _draw_performance_charts(self):
        """Consulta booktrading y despacha el render al main thread. Corre en thread."""
        try:
            account = getattr(self, "ACCOUNT", None)
            if not account:
                self.logger.warning("_draw_performance_charts: ACCOUNT no disponible")
                self._perf_placeholder("ACCOUNT no disponible")
                return

            rows, cols = self.repositorio.select_botcrypto_performance(account=account, dias=90)
            self.logger.warning(f"_draw_performance_charts: account={account} rows={len(rows)}")

            if not rows:
                self._perf_placeholder(f"Sin trades (90 días)\ncuenta: {account}")
                return

            df = pd.DataFrame(rows, columns=cols)
            df["fecha"] = pd.to_datetime(df["fecha"])
            df["pnl_dia"] = df["pnl_dia"].astype(float)

            daily = (
                df.groupby("fecha")
                .agg(pnl=("pnl_dia", "sum"), trades=("trades", "sum"), wins=("wins", "sum"), losses=("losses", "sum"))
                .reset_index()
                .sort_values("fecha")
            )
            daily["cum_pnl"] = daily["pnl"].cumsum()

            by_sym = (
                df.groupby("simbolo")
                .agg(pnl=("pnl_dia", "sum"), trades=("trades", "sum"), wins=("wins", "sum"))
                .reset_index()
                .sort_values("pnl", ascending=True)
            )

            try:
                self.parent.after(0, self._perf_render, daily, by_sym)
            except RuntimeError:
                pass
        except Exception as e:
            self.logger.error(f"_draw_performance_charts: {e}", exc_info=True)
            self._perf_placeholder(f"Error: {e}")

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
            # Disponible = saldo real USDT de Binance (no teórico)
            saldo_real = getattr(self, "_saldo_real_usdt", None)
            disponible = (
                saldo_real
                if saldo_real is not None
                else (self.capital_manager.get_available_capital() if self.capital_manager else 0)
            )
            risk_pct = self.config.get("risk_per_trade", 0.02) * 100

            self._cap_labels["capital"].config(text=f"${capital:.2f}")
            self._cap_labels["reservado"].config(text=f"${reservado:.2f}")
            self._cap_labels["disponible"].config(text=f"${disponible:.2f}", fg="lime" if disponible > 0 else "red")
            self._cap_labels["risk"].config(text=f"{risk_pct:.1f}%")

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
                    # Precio live del WS, fallback al DataFrame
                    live_prices = getattr(self, "_live_prices", {})
                    price = live_prices.get(symbol) or (
                        bot._last_price() if bot.df is not None and len(bot.df) > 0 else entry
                    )
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
                        text=f"{pnl_pct:>+5.2f}% ${pnl_usdt:>+6.2f}",
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

            # Pérdida por SL = risk_amount por bot (capital / max_bots × risk_per_trade)
            risk_pct_dec = self.config.get("risk_per_trade", 0.02)
            max_bots = self.config.get("max_active_bots", 3)
            sl_loss = (capital / max_bots) * risk_pct_dec
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
        self.combo_env = ttk.Combobox(row2, values=["TESTNET", "PRODUCTION", "DISABLE"], width=13, state="disable")

        if self.env is not None:
            self.combo_env.set(self.env)
        else:
            # sin env -- no se puede dar START
            self.combo_env.set("DISABLE")
            btn_start.config(state="disable")
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

        # Max símbolos activos
        tk.Label(row2, text="Max:", bg=self.colors["cgcolor"], fg="white").pack(side=tk.LEFT, padx=(20, 2))
        max_bots = self.config.get("max_active_bots", 3)
        self._lbl_max_bots = tk.Label(
            row2,
            text=str(max_bots),
            bg=self.colors["cgcolor"],
            fg="yellow",
            font=("Arial", 10, "bold"),
        )
        self._lbl_max_bots.pack(side=tk.LEFT)

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

        # Última actualización
        self._lbl_scoring_iter = tk.Label(
            header,
            text="--:--:--",
            bg=self.colors["cgcolor"],
            fg="gray",
            font=("Arial", 8),
        )
        self._lbl_scoring_iter.pack(side=tk.RIGHT)

        # Botón eliminar símbolo del universo
        tk.Button(
            header,
            text="-",
            bg="#b71c1c",
            fg="white",
            font=("Arial", 8, "bold"),
            width=3,
            command=self._on_remove_symbol,
        ).pack(side=tk.RIGHT, padx=(0, 2))

        # Botón agregar símbolo al universo
        tk.Button(
            header,
            text="+",
            bg="blue",
            fg="white",
            font=("Arial", 8, "bold"),
            width=3,
            command=self._on_add_symbol,
        ).pack(side=tk.RIGHT, padx=3)

        # Treeview — 7 columnas compactas
        columns = ("symbol", "score", "prioridad", "ctx", "lat", "mom", "estado")
        self.scoring_tree = ttk.Treeview(
            self._scoring_frame,
            columns=columns,
            show="headings",
            height=6,
            style="TFrame",
        )
        col_w = (self.WIDGET_WIDTH - 10) // 7
        hdrs = {
            "symbol": ("Activo", col_w + 20),
            "score": ("Sc.", col_w - 8),
            "prioridad": ("Prior.", col_w),
            "ctx": ("Ctx", col_w - 10),
            "lat": ("Lat", col_w - 10),
            "mom": ("Mom", col_w - 10),
            "estado": ("Estado", col_w - 2),
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
        self.scoring_tree.tag_configure("Fuera Ctx", foreground="orange")
        self.scoring_tree.tag_configure("Lateral", foreground="#FF69B4")  # rosa/pink
        self.scoring_tree.tag_configure("MomDebil", foreground="#DDA0DD")  # plum/lila

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
                self.logger.warning(
                    f"⚠️ env mismatch: UI={self.env}, Client={self.binance_client.env}, No run _inicializar_managers(self)"
                )
                return

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
                config=self.config,
                env=self.env,
                on_trade_complete=self._on_trade_complete,
                on_trade_booktrading=self._almacenar_trades_booktrading,
            )

            self.logger.info(
                f"Managers inicializados: env={self.env}, capital={capital}, base_url={self.binance_client.urls['base_url']}"
            )

            # Mostrar saldo inicial de Binance
            self._actualizar_saldo()

            # Cargar gráficos de performance al iniciar (delay para que mainloop esté listo)
            self.parent.after(2000, self._refresh_performance_charts)

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
        """Callback cuando se completa un trade (posición cerrada).
        Puede ser llamado desde background thread, usa after() para UI."""
        self.trades_count += 1
        self.logger.warning(f"Trade #{self.trades_count} completado: {symbol}")

        def _ui_cleanup():
            try:
                if self.lbl_trades:
                    self.lbl_trades.config(text=str(self.trades_count))

                # Remover bot y widget del canvas
                if symbol in self.bots:
                    del self.bots[symbol]
                if self.bot_manager:
                    self.bot_manager.unregister_bot(symbol)
                if symbol in self.widgets:
                    self.widgets[symbol].frame.destroy()
                    del self.widgets[symbol]

                # Resetear indicadores en BD
                self._resetear_indicadores_bd(symbol)

                # Reorganizar grid y actualizar scoring
                self._reorganizar_grid()
                self._actualizar_panel_scoring()

                # Forzar ciclo de scoring inmediato para buscar reemplazo
                self._scoring_cycle()
            except Exception as e:
                self.logger.error(f"_on_trade_complete UI cleanup {symbol}: {e}")

        self.parent.after(0, _ui_cleanup)

    def _almacenar_trades_booktrading(self, symbol, order=None):
        """
        Almacena trade en booktrading usando la respuesta directa de la orden.
        order: respuesta de get_new_order() con fills, side, symbol, transactTime.
        """  # gwi001
        try:
            if not order or "fills" not in order:
                self.logger.warning(f"_almacenar_trades_booktrading({symbol}): orden sin fills, ignorando")
                return

            side = order.get("side", "BUY")
            order_id = str(order.get("orderId", ""))
            transact_time = order.get("transactTime", int(datetime.now().timestamp() * 1000))

            # Obtener precio BNB/USDT para convertir comisiones
            price_bnb = 0.0
            try:
                bnb_ticker = self.spot_client.ticker_price("BNBUSDT")
                price_bnb = float(bnb_ticker.get("price", 0))
            except Exception as e:
                self.logger.warning(f"No se pudo obtener precio BNB: {e}")

            for fill in order["fills"]:
                try:
                    qty = float(fill.get("qty", 0))
                    price = float(fill.get("price", 0))
                    commission = float(fill.get("commission", 0))
                    commission_asset = fill.get("commissionAsset", "")
                    quoteqty = qty * price
                    # Usar tradeId del fill (igual que Test_InsertBotTraderBook.py)
                    trade_id = str(fill.get("tradeId", order_id))

                    # BUY = positivo, SELL = negativo (igual que trader_binance)
                    cantidad = qty if side == "BUY" else -qty

                    # Comisión en USD: si viene en BNB usar precio BNB, si no usar precio del activo
                    if commission_asset == "BNB" and price_bnb > 0:
                        comision_usd = commission * price_bnb
                    else:
                        comision_usd = commission * price

                    # obtiene situación actual del estado de los indicadores + contexto operación
                    bot = self.bots.get(symbol)
                    indicadores = bot.get_indicators() if bot else {}
                    if bot and isinstance(indicadores, dict):
                        entry = bot.state.get("entry_price")
                        tp1_pct = bot.risk_cfg.get("tp1_pct", 0)
                        tp2_pct = bot.risk_cfg.get("tp2_pct", 0)
                        pnl_pct = round((price - entry) / entry * 100, 4) if entry and price else None
                        scoring = self.scoring_data.get(symbol, {})
                        indicadores.update(
                            {
                                "intent": order.get("type", side),
                                "entry_price": entry,
                                "sl_price": bot.state.get("stop_loss"),
                                "tp1_target": round(entry * (1 + tp1_pct), 6) if entry else None,
                                "tp2_target": round(entry * (1 + tp2_pct), 6) if entry and tp2_pct else None,
                                "pnl_pct": pnl_pct,
                                "tp1_done": bot.state.get("tp1_done"),
                                "tp2_done": bot.state.get("tp2_done"),
                                "trailing_active": bot.state.get("trailing_active"),
                                "score": scoring.get("score_total"),
                                "prioridad": scoring.get("prioridad"),
                                "interval": self.interval,
                            }
                        )

                    registro = {
                        "categoria": "BotCrypto",
                        "divisa": "USD",
                        "cuenta": self.ACCOUNT,
                        "cantidad": cantidad,
                        "producto": quoteqty,
                        "idtrans": trade_id,
                        "preciotrans": price,
                        "preciocierre": price,
                        "tarifacomision": comision_usd,
                        "mtmgp": 0.00,
                        "indicadores": (
                            json.dumps(indicadores, default=str) if isinstance(indicadores, dict) else indicadores
                        ),
                        "fechahora": datetime.fromtimestamp(transact_time / 1000),
                    }

                    # Anti-duplicado: validar si ya existe en BD
                    found = self.repositorio.get_hash_booktrading(
                        accion="valida",
                        values=registro,
                        symbol=symbol,
                    )
                    if found:
                        self.logger.warning(f"Booktrading: {symbol} | tradeId={trade_id} ya existe, ignorando")
                        continue

                    self.repositorio.insert_bottraderBook(values=registro, symbol=symbol, object="bottrader")
                    self.logger.warning(
                        f"Booktrading: {symbol} | {side} | qty={cantidad} | price={price:.4f} | tradeId={trade_id}"
                    )

                except Exception as e:
                    self.logger.error(f"Error procesando fill {symbol}: {e}")

        except Exception as e:
            self.logger.error(f"_almacenar_trades_booktrading error: {e}")

    # =========================================
    # WEBSOCKET
    # =========================================
    def _iniciar_websocket(self):
        """Inicia WebSocket para recibir klines de todo el universo de activos"""
        try:
            # Monitorear todos los símbolos: activos + observación
            symbols_set = set(self.bots.keys())
            for a in self.all_activos:
                s = a.get("symbol")
                if s:
                    symbols_set.add(s)
            symbols = list(symbols_set)
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
                price = float(kline["c"])
                # Guardar precio live para panel de capital
                if not hasattr(self, "_live_prices"):
                    self._live_prices = {}
                self._live_prices[symbol] = price
                if symbol in self.widgets:
                    self.parent.after(0, self.widgets[symbol].update_price, price)

                # Actualizar panel capital cada 30 ticks (~30s) para PnL en tiempo real
                if not hasattr(self, "_ws_tick_counter"):
                    self._ws_tick_counter = 0
                self._ws_tick_counter += 1
                if self._ws_tick_counter % 30 == 0:
                    self.parent.after(0, self._actualizar_panel_capital)

                # Monitoreo SL tick-a-tick para bots en LONG
                if symbol in self.bots:
                    bot = self.bots[symbol]
                    st = bot.state
                    if st.get("position") == "LONG":
                        trail_sl = st.get("trailing_stop")
                        sl = st.get("stop_loss")
                        effective_sl = trail_sl if st.get("trailing_active") and trail_sl else sl
                        if effective_sl and price <= effective_sl:
                            self.logger.warning(f"SL TICK {symbol}: price={price:.6f} <= sl={effective_sl:.6f}")
                            self.parent.after(0, self._ejecutar_sl_tick, symbol)

                if is_closed:
                    candle = {
                        "open": float(kline["o"]),
                        "high": float(kline["h"]),
                        "low": float(kline["l"]),
                        "close": float(kline["c"]),
                        "volume": float(kline["v"]),
                        "timestamp": kline["t"],
                    }
                    if symbol in self.bots:
                        # Bot activo: evaluar normalmente
                        self.parent.after(0, self._evaluar_bot, symbol, candle)
                    else:
                        # Símbolo en observación: recalcular scoring y buscar oportunidad
                        self.parent.after(0, self._evaluar_observacion, symbol)

        except Exception as e:
            if not self._closing:
                self.logger.error(f"Error procesando WS message: {e}")

    def _ejecutar_sl_tick(self, symbol):
        """Ejecuta EXIT inmediato por SL detectado tick-a-tick (main thread)."""
        bot = self.bots.get(symbol)
        if not bot or bot.state.get("position") != "LONG":
            return  # Ya salió o no existe

        self.logger.warning(f"SL TICK EXIT {symbol}: ejecutando salida inmediata")

        def _exit_bg(b=bot, s=symbol):
            try:
                self.bot_manager._execute_exit(b, reason="SL_TICK")
            except Exception as ex:
                self.logger.error(f"{s}: SL_TICK exit error: {ex}")

            def _post():
                w = self.widgets.get(s)
                if w:
                    w.update_state(b.get_public_state(), b.get_indicators(), {})
                self._actualizar_panel_capital()

            self.parent.after(0, _post)

        threading.Thread(target=_exit_bg, daemon=True).start()

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

            # Actualizar panel capital (scoring cycle también lo hace cada 2 min)
            self._actualizar_panel_capital()

        except Exception as e:
            self.logger.error(f"_evaluar_bot(): Error evaluando bot {symbol}: {e}")

    def _evaluar_observacion(self, symbol):
        """Evalúa un símbolo en observación cuando cierra vela.
        Solo actualiza scoring_data. La gestión de cubos la hace el scoring cycle."""
        if symbol in self.bots:
            return
        if not self.running:
            return

        def _bg():
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
                    "cooldown_hours": self.config.get("cooldown_hours", 4),
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
                contexto = self._evaluar_contexto_superior(symbol)
                lateral = self._evaluar_lateralidad(symbol, tmp_bot)
                mom = self._evaluar_momentum(symbol)
                scoring = tmp_bot.calcular_scoring(contexto_superior=contexto, lateralidad=lateral, momentum=mom)
                self.scoring_data[symbol] = scoring
                self._persistir_scoring(symbol, scoring)
                self.parent.after(0, self._actualizar_panel_scoring)
            except Exception as e:
                self.logger.error(f"_evaluar_observacion({symbol}): {e}")

        threading.Thread(target=_bg, daemon=True).start()

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
                "cooldown_hours": self.config.get("cooldown_hours", 4),
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
                    contexto = self._evaluar_contexto_superior(symbol)
                    lateral = self._evaluar_lateralidad(symbol, tmp_bot)
                    mom = self._evaluar_momentum(symbol)
                    scoring = tmp_bot.calcular_scoring(contexto_superior=contexto, lateralidad=lateral, momentum=mom)
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
                    self._resetear_indicadores_bd(none_sym)

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

                    # Evaluar inmediatamente los nuevos bots (aún en background)
                    for sym in rotaciones:
                        bot = self.bots.get(sym)
                        if bot and bot.df is not None and len(bot.df) >= 50:
                            try:
                                bot.calcular_indicadores()
                                action, conditions = bot.evaluate()
                                self.logger.warning(f"ROTACIÓN {sym}: Eval → {action}")
                                if action != "HOLD" and self.bot_manager:
                                    self.bot_manager.execute_action(bot, action)
                            except Exception as ex:
                                self.logger.error(f"Rotación eval {sym}: {ex}")

                    def _post_rotacion():
                        for sym in rotaciones:
                            w = self.widgets.get(sym)
                            bot = self.bots.get(sym)
                            if w and bot:
                                w.set_running(True)
                                if bot.df is not None and len(bot.df) >= 50:
                                    st = bot.get_public_state()
                                    ind = bot.get_indicators()
                                    _, conds = bot.evaluate()
                                    w.update_state(st, ind, conds)
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
                ctx_icon = "OK" if scoring.get("contexto_ok", True) else "NO"
                lat_icon = "OK" if scoring.get("lateral_ok", True) else "NO"
                mom_icon = "OK" if scoring.get("momentum_ok", True) else "NO"

                self.scoring_tree.insert(
                    "",
                    "end",
                    values=(sym, score, prioridad, ctx_icon, lat_icon, mom_icon, "OBSERV."),
                    tags=(prioridad,),
                )

            # Actualizar timestamp
            now = datetime.now().strftime("%H:%M:%S")
            self._lbl_scoring_iter.config(text=now, fg="cyan")

        except Exception as e:
            self.logger.error(f"_actualizar_panel_scoring(): {e}")

    def _persistir_scoring(self, symbol, scoring):
        """Guarda scoring + indicadores en campo indicadores de otros_activos"""
        try:
            from datetime import datetime

            # Recuperar contexto completo del cache para indicadores_ctx
            ctx_cached = self._contexto_cache.get(symbol, {}).get("resultado", {})

            data = {
                "scoring": {
                    "total": scoring.get("score_total", 0),
                    "base": scoring.get("score_base", 0),
                    "contexto": scoring.get("score_contexto", 0),
                    "lateral": scoring.get("score_lateral", 0),
                    "rsi": scoring.get("score_rsi", 0),
                    "macd": scoring.get("score_macd", 0),
                    "ema": scoring.get("score_ema", 0),
                    "vol": scoring.get("score_vol", 0),
                },
                "prioridad": scoring.get("prioridad", "BLOQUEADO"),
                "intervalo": self.interval,
                "indicadores": scoring.get("indicadores", {}),
                "contexto_superior": {
                    "ok": scoring.get("contexto_ok", True),
                    "timeframe": ctx_cached.get("timeframe", self.SUPERIOR_INTERVALS.get(self.interval)),
                    "condiciones": ctx_cached.get("condiciones_cumplidas", 0),
                    "detalle": scoring.get("contexto_detalle", {}),
                    "indicadores": ctx_cached.get("indicadores_ctx", {}),
                },
                "lateralidad": {
                    "ok": scoring.get("lateral_ok", True),
                    "detalle": scoring.get("lateral_detalle", {}),
                },
                "timestamp": datetime.now().isoformat(),
            }
            self.repositorio.update_otros_activos_indicadores(symbol, self.ACCOUNT, data)
        except Exception as e:
            self.logger.error(f"_persistir_scoring({symbol}): {e}")

    def _evaluar_contexto_superior(self, symbol):
        """Evalúa el contexto del timeframe superior para penalización estructural.
        Usa cache de 10 min para evitar API calls excesivos.
        Retorna dict con contexto_ok, condiciones_cumplidas, detalle."""
        superior_interval = self.SUPERIOR_INTERVALS.get(self.interval)

        # Sin TF superior (1d) → contexto OK por defecto
        if superior_interval is None:
            return {
                "contexto_ok": True,
                "condiciones_cumplidas": 4,
                "detalle": {
                    "ema20_gt_ema50": True,
                    "price_gt_ema20": True,
                    "macd_gt_0": True,
                    "rsi_gt_50": True,
                },
            }

        # Revisar cache
        now = time.time()
        cached = self._contexto_cache.get(symbol)
        if cached and (now - cached["timestamp"]) < self.CONTEXTO_CACHE_TTL:
            return cached["resultado"]

        try:
            if not self.spot_client:
                return {"contexto_ok": True, "condiciones_cumplidas": 4, "detalle": {}}

            klines = self.spot_client.klines(symbol=symbol, interval=superior_interval, limit=100)
            if not klines or len(klines) < 55:
                return {"contexto_ok": True, "condiciones_cumplidas": 4, "detalle": {}}

            df_htf = pd.DataFrame(
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

            # Indicadores con EMA20/EMA50 para contexto estructural
            calcular_indicadores_df(df_htf, ema_fast=20, ema_slow=50)

            last = df_htf.iloc[-1]
            prev = df_htf.iloc[-2] if len(df_htf) >= 2 else last

            # Valores numéricos del TF superior
            ctx_rsi = float(last["rsi"])
            ctx_macd = float(last["macd"])
            ctx_macd_signal = float(last["macd_signal"])
            ctx_ema20 = float(last["ema_fast"])
            ctx_ema50 = float(last["ema_slow"])
            ctx_price = float(last["Close"])

            # Variación porcentual de la última vela superior
            ctx_cambio_pct = (
                ((ctx_price - float(prev["Close"])) / float(prev["Close"])) * 100 if float(prev["Close"]) > 0 else 0
            )

            # Tendencia EMA: distancia porcentual EMA20 vs EMA50
            ctx_ema_gap_pct = ((ctx_ema20 - ctx_ema50) / ctx_ema50) * 100 if ctx_ema50 > 0 else 0

            # Evaluación de condiciones
            ema20_gt_ema50 = bool(ctx_ema20 > ctx_ema50)
            price_gt_ema20 = bool(ctx_price > ctx_ema20)
            macd_gt_0 = bool(ctx_macd > 0)
            rsi_gt_50 = bool(ctx_rsi > 50)

            condiciones = sum([ema20_gt_ema50, price_gt_ema20, macd_gt_0, rsi_gt_50])
            contexto_ok = condiciones >= 3

            resultado = {
                "contexto_ok": contexto_ok,
                "condiciones_cumplidas": condiciones,
                "timeframe": superior_interval,
                "detalle": {
                    "ema20_gt_ema50": ema20_gt_ema50,
                    "price_gt_ema20": price_gt_ema20,
                    "macd_gt_0": macd_gt_0,
                    "rsi_gt_50": rsi_gt_50,
                },
                "indicadores_ctx": {
                    "rsi": round(ctx_rsi, 2),
                    "macd": round(ctx_macd, 8),
                    "macd_signal": round(ctx_macd_signal, 8),
                    "ema20": round(ctx_ema20, 6),
                    "ema50": round(ctx_ema50, 6),
                    "price": round(ctx_price, 6),
                    "cambio_pct": round(ctx_cambio_pct, 3),
                    "ema_gap_pct": round(ctx_ema_gap_pct, 3),
                },
            }

            self._contexto_cache[symbol] = {"timestamp": now, "resultado": resultado}
            self.logger.info(
                f"CONTEXTO {symbol} [{superior_interval}]: {condiciones}/4 → {'OK' if contexto_ok else 'FUERA'}"
            )
            return resultado

        except Exception as e:
            self.logger.error(f"_evaluar_contexto_superior({symbol}): {e}")
            return {"contexto_ok": True, "condiciones_cumplidas": 4, "detalle": {}}

    def _evaluar_lateralidad(self, symbol, tmp_bot):
        """Evalúa si el mercado está lateral usando 4 métricas: ATR%, rango, dist_ema, volumen.
        Requiere 3/4 condiciones OK para considerar mercado con tendencia.
        Retorna dict con ok, condiciones_cumplidas, detalle, metricas."""
        try:
            df = tmp_bot.df
            if df is None or len(df) < 20:
                return {"ok": True, "condiciones_cumplidas": 4, "detalle": {}, "metricas": {}}

            umbrales = self.LATERAL_UMBRALES.get(self.interval, self.LATERAL_UMBRALES["1h"])

            price = df["Close"].iloc[-1]
            ema20 = df["ema_fast"].iloc[-1] if "ema_fast" in df.columns else None

            # ATR (Average True Range) - 14 periodos
            high = df["High"]
            low = df["Low"]
            close = df["Close"]
            tr = pd.concat(
                [
                    high - low,
                    (high - close.shift(1)).abs(),
                    (low - close.shift(1)).abs(),
                ],
                axis=1,
            ).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]
            atr_pct = atr / price if price > 0 else 0

            # Rango últimas 10 velas
            rango_10 = (high.iloc[-10:].max() - low.iloc[-10:].min()) / price if price > 0 else 0

            # Distancia a EMA20
            if ema20 and ema20 > 0:
                dist_ema = abs(price - ema20) / price
            else:
                dist_ema = 0

            # Volumen relativo (actual vs media 20)
            vol_actual = df["Volume"].iloc[-1]
            vol_media = df["Volume"].iloc[-20:].mean()
            vol_ratio = vol_actual / vol_media if vol_media > 0 else 0

            condiciones = {
                "atr_ok": atr_pct >= umbrales["atr_min"],
                "rango_ok": rango_10 >= umbrales["rango_min"],
                "dist_ema_ok": dist_ema >= umbrales["dist_ema_min"],
                "vol_ok": vol_ratio >= umbrales["vol_ratio_min"],
            }

            cumplidas = sum(condiciones.values())
            ok = cumplidas >= self.LATERAL_MIN_CONDICIONES

            metricas = {
                "atr_pct": round(atr_pct, 4),
                "rango_10": round(rango_10, 4),
                "dist_ema": round(dist_ema, 4),
                "vol_ratio": round(vol_ratio, 2),
            }

            self.logger.info(
                f"LATERAL {symbol}: {cumplidas}/4 → {'OK' if ok else 'LATERAL'} | "
                f"atr={metricas['atr_pct']} rango={metricas['rango_10']} "
                f"dist_ema={metricas['dist_ema']} vol={metricas['vol_ratio']}"
            )

            return {
                "ok": ok,
                "condiciones_cumplidas": cumplidas,
                "detalle": condiciones,
                "metricas": metricas,
            }

        except Exception as e:
            self.logger.error(f"_evaluar_lateralidad({symbol}): {e}")
            return {"ok": True, "condiciones_cumplidas": 4, "detalle": {}, "metricas": {}}

    def _clasificar_fase_contexto(self, indicadores_ctx):
        """Clasifica la fase del activo usando indicadores del TF superior (4H)."""
        rsi = indicadores_ctx.get("rsi", 50)
        macd = indicadores_ctx.get("macd", 0)
        macd_signal = indicadores_ctx.get("macd_signal", 0)
        ema20 = indicadores_ctx.get("ema20", 0)
        ema50 = indicadores_ctx.get("ema50", 0)

        ema_gap_pct = ((ema20 - ema50) / ema50) * 100 if ema50 > 0 else 0

        if ema20 > ema50 and macd > macd_signal and rsi < 70:
            fase = "impulso_sano"
        elif ema20 > ema50 and rsi >= 70:
            fase = "sobreextendido"
        elif ema20 > ema50 and macd < macd_signal:
            fase = "enfriamiento"
        elif ema20 < ema50:
            fase = "bajista"
        else:
            fase = "indefinido"

        return {"fase": fase, "ema_gap_pct": round(ema_gap_pct, 2), "rsi": rsi}

    def _filtro_momentum_debil(self, fase_data):
        """Detecta si el activo está sobreextendido o perdiendo fuerza."""
        fase = fase_data.get("fase", "indefinido")
        ema_gap_pct = fase_data.get("ema_gap_pct", 0)
        rsi = fase_data.get("rsi", 50)

        if fase == "sobreextendido" and ema_gap_pct > 2:
            return True
        if rsi > 75:
            return True
        return False

    def _evaluar_momentum(self, symbol):
        """Evalúa momentum usando los indicadores del TF superior ya cacheados.
        Retorna dict con ok, fase, debil, fase_data."""
        try:
            cached = self._contexto_cache.get(symbol, {}).get("resultado", {})
            indicadores_ctx = cached.get("indicadores_ctx", {})

            if not indicadores_ctx:
                return {"ok": True, "fase": "indefinido", "debil": False, "fase_data": {}}

            fase_data = self._clasificar_fase_contexto(indicadores_ctx)
            debil = self._filtro_momentum_debil(fase_data)

            self.logger.info(
                f"MOMENTUM {symbol}: fase={fase_data['fase']} ema_gap={fase_data['ema_gap_pct']}% "
                f"rsi={fase_data['rsi']:.1f} → {'DEBIL' if debil else 'OK'}"
            )

            return {
                "ok": not debil,
                "fase": fase_data["fase"],
                "debil": debil,
                "fase_data": fase_data,
            }

        except Exception as e:
            self.logger.error(f"_evaluar_momentum({symbol}): {e}")
            return {"ok": True, "fase": "indefinido", "debil": False, "fase_data": {}}

    def _resetear_indicadores_bd(self, symbol):
        """Limpia el campo indicadores en BD cuando un símbolo sale del panel activo"""
        try:
            data = {"scoring": {}, "prioridad": "OBSERV.", "indicadores": {}, "timestamp": datetime.now().isoformat()}
            self.repositorio.update_otros_activos_indicadores(symbol, self.ACCOUNT, data)
            if symbol in self.scoring_data:
                del self.scoring_data[symbol]
            self.logger.info(f"{symbol}: Indicadores reseteados en BD")
        except Exception as e:
            self.logger.error(f"_resetear_indicadores_bd({symbol}): {e}")

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
                    "cooldown_hours": self.config.get("cooldown_hours", 4),
                }

                # 3a. Detectar posiciones existentes en Binance (prioridad absoluta)
                symbols_con_posicion = self._detectar_posiciones_binance()
                self._symbols_con_posicion_binance = set(symbols_con_posicion)
                for sym in symbols_con_posicion:
                    if sym not in top_symbols:
                        top_symbols.append(sym)
                        self.logger.warning(f"📥 {sym}: Posición existente detectada → forzando cubo")

                for symbol, _scoring in ranked:
                    if len(top_symbols) >= max_bots:
                        break
                    if symbol in top_symbols:
                        continue
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
        """Main thread: solo operaciones UI (widgets, scoring, WS). Sin REST.
        Solo crea widgets para bots con posición LONG o señal BUY. Los NONE no entran al canvas."""
        try:
            activos_map = {a["symbol"]: a for a in self.all_activos}
            active_count = 0

            for symbol, bot in pre_bots.items():
                # Evaluar antes de decidir si entra al canvas
                action = "HOLD"
                conditions = {}
                has_position = bot.get_public_state().get("position") == "LONG"

                if bot.df is not None and len(bot.df) >= 50:
                    action, conditions = bot.evaluate()

                # Solo crear widget si tiene posición LONG, señal BUY, scoring Alta (>=5),
                # o posición real detectada en Binance
                score = self.scoring_data.get(symbol, {}).get("score_total", 0)
                tiene_posicion_binance = symbol in getattr(self, "_symbols_con_posicion_binance", set())
                if not has_position and not tiene_posicion_binance and action != "BUY" and score < 5:
                    self.logger.info(f"{symbol}: NONE sin BUY ni Alta → no entra al canvas (score={score})")
                    self._resetear_indicadores_bd(symbol)
                    continue

                # Crear widget (UI pura)
                activo = activos_map.get(symbol, {})
                grid_idx = active_count + 1
                row = grid_idx // self.COLUMNS
                col = grid_idx % self.COLUMNS
                self._crear_widget_simbolo(symbol, activo, row, col)

                # Asignar bot
                self.bots[symbol] = bot
                self.widgets[symbol].set_running(True)

                # Mostrar estado
                state = bot.get_public_state()
                indicators = bot.get_indicators()
                self.widgets[symbol].update_state(state, indicators, conditions)
                self.logger.warning(f"{symbol}: Eval → {action} | position={state.get('position')}")

                # Ejecutar acción si no es HOLD
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

            # WebSocket (incluye todos los símbolos del universo para detectar señales)
            self._iniciar_websocket()

            # Iniciar ciclo de scoring independiente (cada 2 min)
            self._iniciar_scoring_cycle()

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
            "cooldown_hours": self.config.get("cooldown_hours", 4),
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
                contexto = self._evaluar_contexto_superior(symbol)
                lateral = self._evaluar_lateralidad(symbol, tmp_bot)
                mom = self._evaluar_momentum(symbol)
                scoring = tmp_bot.calcular_scoring(contexto_superior=contexto, lateralidad=lateral, momentum=mom)
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

        # Detener WebSocket y scoring cycle
        self._detener_websocket()
        self._detener_scoring_cycle()

        # Resetear indicadores en BD para todos los bots activos
        for sym in list(self.bots.keys()):
            self._resetear_indicadores_bd(sym)

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

    def _cerrar_chart_window(self, symbol):
        """Cierra la ventana Strategy del símbolo si está abierta."""
        if not hasattr(self, "_chart_windows"):
            return
        win = self._chart_windows.pop(symbol, None)
        if win:
            try:
                if win.winfo_exists():
                    win.destroy()
            except tk.TclError:
                pass

    def _on_show_chart(self, symbol):
        """Abre ventana con gráfico de estrategia con auto-actualización"""  # gwi001

        # --- Funciones internas (al inicio, según pyproject.toml) ---
        bg_color = "#16213e"
        _timer_id = [None]

        def _draw_chart(win_ref, fig_ref, canvas_ref, bot_ref):
            """Dibuja/redibuja el gráfico con datos actuales"""
            fig_ref.clear()
            ax = fig_ref.add_subplot(111)
            ax.set_facecolor(bg_color)

            # Marca de agua: símbolo grande al fondo
            ax.text(
                0.5,
                0.5,
                symbol.replace("USDT", ""),
                transform=ax.transAxes,
                fontsize=72,
                fontweight="bold",
                color="white",
                alpha=0.04,
                ha="center",
                va="center",
                zorder=0,
            )

            state = bot_ref.state
            risk = bot_ref.risk_cfg
            entry = state.get("entry_price")
            sl_pct = risk.get("stop_loss_pct", 0.02)
            tp1_pct = risk.get("tp1_pct", 0.025)
            trail_mult = risk.get("trail_mult", 1.5)
            tp1_size = risk.get("tp1_size", 0.33)
            risk_per_trade = risk.get("risk_per_trade", 0.015)
            max_bots = self.config.get("max_active_bots", 3)
            capital_total = self.config.get("capital", 302)
            capital_per_bot = capital_total / max_bots

            df = bot_ref.df
            if df is None or len(df) < 14:
                return

            price_now = self._live_prices.get(symbol, float(df["Close"].iloc[-1]))
            atr = bot_ref._calc_atr14()

            if not entry or entry <= 0:
                entry = price_now

            qty = state.get("remaining_qty") or state.get("position_qty") or 0
            if qty <= 0:
                qty = (capital_per_bot * risk_per_trade) / (price_now * sl_pct)

            # Niveles clave — usar estado real del bot si está disponible
            tp1_done = state.get("tp1_done", False)
            trailing_active = state.get("trailing_active", False)
            trailing_stop = state.get("trailing_stop")
            state_sl = state.get("stop_loss")

            if trailing_active and trailing_stop:
                # Post-TP1 con trailing activo: SL efectivo = trailing_stop
                sl_price = trailing_stop
            elif state_sl and state_sl > 0:
                # SL movido por el bot (ej: breakeven post-TP1)
                sl_price = state_sl
            else:
                # Sin posición o antes del primer trade: usar config
                sl_price = entry * (1 - sl_pct)

            tp1_price = entry * (1 + tp1_pct)
            rally_price = entry * (1 + tp1_pct * 2.5)
            avg_trail_exit = entry * (1 + tp1_pct * 1.5)

            # Ganancias estimadas
            loss_sl = qty * (sl_price - entry)
            gain_tp1_partial = qty * tp1_size * (tp1_price - entry)
            qty_after_tp1 = qty * (1 - tp1_size)
            gain_trail = qty_after_tp1 * (avg_trail_exit - entry) + gain_tp1_partial
            gain_rally = qty_after_tp1 * (rally_price - entry) + gain_tp1_partial

            # --- Histórico (últimas 50 velas) ---
            hist = df["Close"].tail(50).values.astype(float)
            n_hist = len(hist)
            x_hist = np.arange(n_hist)
            ax.plot(x_hist, hist, color="#00d4ff", linewidth=1.5)

            # --- Proyecciones (20 barras) ---
            n_proj = 20
            x_proj = np.arange(n_hist - 1, n_hist + n_proj)
            x_total = n_hist + n_proj

            y_max = np.linspace(price_now, rally_price, len(x_proj))
            y_avg = np.linspace(price_now, avg_trail_exit, len(x_proj))
            y_tp1 = np.linspace(price_now, tp1_price, len(x_proj))
            y_min = np.linspace(price_now, sl_price, len(x_proj))

            # Zonas de color
            y_entry = np.full_like(x_proj, entry, dtype=float)
            ax.fill_between(x_proj, y_avg, y_max, alpha=0.15, color="#00ff88")
            ax.fill_between(x_proj, y_entry, y_avg, alpha=0.12, color="#ffaa00")
            ax.fill_between(x_proj, y_entry, y_tp1, alpha=0.12, color="#00ff88")
            ax.fill_between(x_proj, y_min, y_entry, alpha=0.15, color="#ff4444")

            # Líneas de proyección
            ax.plot(x_proj, y_max, color="#00ff88", linewidth=1.0, linestyle="--")
            ax.plot(x_proj, y_avg, color="#ffaa00", linewidth=1.0, linestyle="--")
            ax.plot(x_proj, y_tp1, color="#00ff88", linewidth=1.0, linestyle="--")
            ax.plot(x_proj, y_min, color="#ff4444", linewidth=1.0, linestyle="--")

            # Líneas horizontales
            ax.axhline(y=tp1_price, color="#00ff88", linewidth=0.9, linestyle=":", alpha=0.4)
            ax.axhline(y=sl_price, color="#ff4444", linewidth=0.9, linestyle=":", alpha=0.4)
            ax.axhline(y=price_now, color="#00d4ff", linewidth=0.8, linestyle="-", alpha=0.3)
            ax.axvline(x=n_hist - 1, color="gray", linewidth=0.8, linestyle="--", alpha=0.4)

            # Anotaciones derecha
            x_label = x_total - 1
            ax.annotate(
                f"  TP2 +{((rally_price/entry)-1)*100:.1f}%  ${gain_rally:+.2f}",
                xy=(x_label, rally_price),
                fontsize=8,
                color="#00ff88",
                fontweight="bold",
                va="center",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#00ff88", alpha=0.2),
            )
            ax.annotate(
                f"  Trail +{((avg_trail_exit/entry)-1)*100:.1f}%  ${gain_trail:+.2f}",
                xy=(x_label, avg_trail_exit),
                fontsize=8,
                color="#ffaa00",
                fontweight="bold",
                va="center",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffaa00", alpha=0.2),
            )
            ax.annotate(
                f"  TP1 +{((tp1_price/entry)-1)*100:.1f}%  ${gain_tp1_partial:+.2f}",
                xy=(x_label, tp1_price),
                fontsize=8,
                color="#00ff88",
                fontweight="bold",
                va="center",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffaa00", alpha=0.2),
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
                f"  SL -{sl_pct*100:.1f}%  ${loss_sl:+.2f}",
                xy=(x_label, sl_price),
                fontsize=8,
                color="#ff4444",
                fontweight="bold",
                va="center",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#ff4444", alpha=0.2),
            )

            # Etiquetas de zona
            ylim = ax.get_ylim()
            ax.text(n_hist * 0.4, ylim[1], "HISTORIAL", fontsize=8, color="gray", ha="center", alpha=0.5, va="top")
            ax.text(
                n_hist + n_proj * 0.4, ylim[1], "PROYECCION", fontsize=8, color="gray", ha="center", alpha=0.5, va="top"
            )

            # Entry (si en posición)
            if state.get("position") == "LONG":
                ax.axhline(y=entry, color="#ffff00", linewidth=1, linestyle="-", alpha=0.4)
                ax.annotate(f"  Entry {entry:.4f}", xy=(0, entry), fontsize=7, color="#ffff00", va="bottom")
                ax.annotate(f"  Sl {sl_price:.4f}", xy=(0, sl_price), fontsize=7, color="#ff4444", va="bottom")
                ax.annotate(f"  Tp {tp1_price:.4f}", xy=(0, tp1_price), fontsize=7, color="#00ff88", va="bottom")

                pnl_now = qty * (price_now - entry)
                pnl_pct = ((price_now / entry) - 1) * 100
                pnl_color = "#00ff88" if pnl_now >= 0 else "#ff4444"
                ax.annotate(
                    f"PnL: ${pnl_now:+.2f} ({pnl_pct:+.2f}%)",
                    xy=(n_hist - 2, price_now),
                    fontsize=8,
                    color=pnl_color,
                    fontweight="bold",
                    va="bottom",
                    ha="right",
                )

            # Info box
            rr = abs(gain_trail / loss_sl) if loss_sl != 0 else 0
            info = (
                f"{symbol} | {self.interval}\n"
                f"Capital/bot: ${capital_per_bot:.0f}\n"
                f"Qty: {qty:.2f} | Pos: ${qty*price_now:.2f}\n"
                f"TP1: {tp1_pct*100:.1f}% | SL: {sl_pct*100:.1f}% | Trail: {trail_mult}x\n"
                f"R/R: 1:{rr:.1f}"
            )
            ax.text(
                0.02,
                0.98,
                info,
                transform=ax.transAxes,
                fontsize=7.5,
                color="white",
                verticalalignment="top",
                fontfamily="monospace",
                bbox=dict(boxstyle="round,pad=0.4", facecolor=bg_color, edgecolor="gray", alpha=0.9),
            )

            # Estilo
            ax.spines[["top", "right"]].set_visible(False)
            ax.tick_params(colors="gray", labelsize=7)
            for spine in ax.spines.values():
                spine.set_color("#2a3a5e")
            ax.set_xlim(-1, x_total + 2)
            ax.yaxis.set_major_formatter(lambda x, _: f"{x:.4f}")
            ax.set_xticklabels([])

            fig_ref.tight_layout(pad=0.5)
            canvas_ref.draw_idle()

        def _auto_refresh(win_ref, fig_ref, canvas_ref, bot_ref):
            if win_ref.winfo_exists():
                _draw_chart(win_ref, fig_ref, canvas_ref, bot_ref)
                _timer_id[0] = win_ref.after(5000, _auto_refresh, win_ref, fig_ref, canvas_ref, bot_ref)

        def _on_close(win_ref):
            if _timer_id[0]:
                win_ref.after_cancel(_timer_id[0])
            self._chart_windows.pop(symbol, None)
            win_ref.destroy()

        # --- Código principal ---
        bot = self.bots.get(symbol)
        if not bot:
            return

        # Una sola ventana por símbolo
        if not hasattr(self, "_chart_windows"):
            self._chart_windows = {}
        existing = self._chart_windows.get(symbol)
        if existing:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return
            except tk.TclError:
                pass
            self._chart_windows.pop(symbol, None)

        # Ventana Toplevel
        win = tk.Toplevel(self.parent)
        win.title(f"Strategy - {symbol} ({self.interval})")
        try:
            x = self.parent.winfo_rootx() + self.parent.winfo_width() - 90
            y = self.parent.winfo_rooty() + 200
        except Exception:
            x, y = 200, 150

        win.geometry(f"700x450+{x}+{y}")
        win.configure(bg=bg_color)
        win.resizable(False, False)
        self._chart_windows[symbol] = win

        fig = Figure(figsize=(7.0, 4.5), dpi=100, facecolor=bg_color)
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Dibujo inicial + auto-refresh
        _draw_chart(win, fig, canvas, bot)
        _timer_id[0] = win.after(5000, _auto_refresh, win, fig, canvas, bot)
        win.protocol("WM_DELETE_WINDOW", lambda: _on_close(win))

    def _on_sell_all(self, symbol):
        """Vende todo el balance de un símbolo específico (REST en background).
        Cancela SL, vende, resetea estado del bot y libera capital."""
        self._cerrar_chart_window(symbol)

        def _bg():
            try:
                bot = self.bots.get(symbol)

                # 1. Cancelar orden SL en Binance antes de vender
                if bot:
                    self.bot_manager._cancel_sl_order(bot)

                asset = symbol.replace("USDT", "")

                # 2. Esperar a que Binance libere el locked (retry hasta 3 veces)
                balance = 0.0
                for attempt in range(3):
                    time.sleep(1.0)  # Esperar que Binance procese la cancelación
                    account = self.spot_client.account_spot()

                    if not account or "balances" not in account:
                        self.logger.error(f"No se pudo obtener cuenta de Binance")
                        return

                    for b in account["balances"]:
                        if b["asset"] == asset:
                            balance = float(b["free"])
                            locked = float(b.get("locked", 0))
                            self.logger.warning(f"{symbol}: intento {attempt+1} | free={balance} locked={locked}")
                            break

                    if balance > 0:
                        break

                if balance <= 0:
                    self.logger.warning(f"{symbol}: Sin balance FREE de {asset} para vender (puede seguir locked)")
                    if bot and bot.state.get("position") == "LONG":
                        self._reset_bot_state(bot, symbol)
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
                    price = float(order.get("fills", [{}])[0].get("price", 0)) if order.get("fills") else 0
                    notional = qty * price if price else 0
                    self.logger.warning(f"✅ {symbol}: VENDIDO {qty} {asset} | orderId={order.get('orderId')}")

                    # 3. Liberar capital reservado
                    if notional > 0:
                        self.capital_manager.release(notional)

                    # 4. Registrar en booktrading
                    if self.bot_manager.on_trade_booktrading:
                        self.bot_manager.on_trade_booktrading(symbol, order=order)

                    # 5. Resetear estado del bot
                    if bot:
                        self._reset_bot_state(bot, symbol)

                    self.parent.after(0, self._actualizar_saldo)
                    self.parent.after(0, self._actualizar_panel_capital)
                else:
                    self.logger.error(f"{symbol}: Orden SELL ALL fallida")

            except Exception as e:
                self.logger.error(f"_on_sell_all({symbol}): {e}")
                traceback.print_exc()

        threading.Thread(target=_bg, daemon=True).start()

    def _reset_bot_state(self, bot, symbol):
        """Resetea el estado del bot a NONE después de cerrar posición manualmente."""
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
        bot.state["sl_order_id"] = None
        bot.state["last_trade_time"] = datetime.now().isoformat()
        self.state_repo.delete_state(symbol)
        self.logger.warning(f"✅ {symbol}: Estado reseteado a NONE (cierre manual)")

        # Actualizar widget en main thread
        def _upd():
            w = self.widgets.get(symbol)
            if w:
                w.update_state(bot.get_public_state(), bot.get_indicators(), {})

        self.parent.after(0, _upd)

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

            # 3. Cerrar gráfico Strategy si está abierto
            self._cerrar_chart_window(symbol)

            # 4. Destruir widget
            if symbol in self.widgets:
                self.widgets[symbol].frame.destroy()
                del self.widgets[symbol]

            # 5. Resetear indicadores en BD
            self._resetear_indicadores_bd(symbol)

            # 6. Actualizar scoring — el símbolo pasa a OBSERV.
            self._actualizar_panel_scoring()

            # 6. Reorganizar grid
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
            self._saldo_real_usdt = saldo  # Guardar para panel de capital

            def _update_ui():
                if saldo is not None:
                    self.lbl_saldo.config(text=f"{saldo:.2f} USDT")
                else:
                    self.lbl_saldo.config(text="-- USDT")

            try:
                self.parent.after(0, _update_ui)
            except RuntimeError:
                pass

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
        tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", height=8, selectmode="extended", style="TFrame"
        )

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
                locked = float(b.get("locked", 0))
                total = free + locked
                if total > 0.001 and b["asset"] not in ["USDT", "BNB"]:
                    balances[b["asset"]] = total

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

            try:
                self.logger.warning(f"🔴 {symbol}: CERRANDO POSICIÓN desde Posiciones Activas")

                if symbol in self.bot_manager.bots:
                    # Ruta bot activo: cancela SL order primero, luego MARKET SELL
                    bot = self.bot_manager.bots[symbol]
                    self.bot_manager._execute_exit(bot, reason="MANUAL")
                    cerradas += 1
                else:
                    # Ruta posición huérfana (sin bot): cancelar órdenes abiertas y vender balance free+locked
                    self.spot_client.cancel_all_orders(symbol=symbol)
                    real_qty = self.bot_manager._get_real_balance(symbol)
                    qty_fmt = self.bot_manager._format_qty(symbol, real_qty)
                    if qty_fmt > 0:
                        order = self.spot_client.get_new_order(
                            symbol=symbol,
                            side="SELL",
                            type="MARKET",
                            quantity=qty_fmt,
                        )
                        if order:
                            self.logger.warning(f"✅ {symbol}: POSICIÓN HUÉRFANA CERRADA | orderId={order.get('orderId')}")
                            cerradas += 1
                        else:
                            errores += 1
                    else:
                        self.logger.warning(f"{symbol}: sin balance para vender")
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

            try:
                if symbol in self.bot_manager.bots:
                    # Ruta bot activo: cancela SL order primero, luego MARKET SELL
                    bot = self.bot_manager.bots[symbol]
                    self.bot_manager._execute_exit(bot, reason="MANUAL")
                    cerradas += 1
                else:
                    # Ruta posición huérfana: cancelar órdenes abiertas y vender
                    self.spot_client.cancel_all_orders(symbol=symbol)
                    real_qty = self.bot_manager._get_real_balance(symbol)
                    qty_fmt = self.bot_manager._format_qty(symbol, real_qty)
                    if qty_fmt > 0:
                        order = self.spot_client.get_new_order(
                            symbol=symbol,
                            side="SELL",
                            type="MARKET",
                            quantity=qty_fmt,
                        )
                        if order:
                            self.logger.warning(f"✅ {symbol}: POSICIÓN HUÉRFANA CERRADA | orderId={order.get('orderId')}")
                            cerradas += 1
                        else:
                            errores += 1
                    else:
                        errores += 1

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

    # =========================================
    # SCORING CYCLE (independiente del intervalo de velas)
    # =========================================
    def _iniciar_scoring_cycle(self):
        """Inicia el ciclo periódico de scoring (cada 2 min)"""
        self._scoring_cycle()

    def _detener_scoring_cycle(self):
        """Detiene el ciclo de scoring"""
        if self._scoring_timer_id:
            self.parent.after_cancel(self._scoring_timer_id)
            self._scoring_timer_id = None

    def _scoring_cycle(self):
        """Ciclo independiente: recalcula scoring de TODO el universo,
        gestiona cubos (entra Alta, sale no-Alta), actualiza panel.
        Corre cada 2 min sin importar el intervalo de velas."""
        if self._closing or not self.running:
            return

        def _bg():
            try:
                self.logger.info("SCORING CYCLE: Recalculando universo...")
                self._recalcular_scoring_observacion_sync()

                # Recalcular scoring de bots activos (con contexto superior + lateralidad)
                for sym, bot in list(self.bots.items()):
                    try:
                        contexto = self._evaluar_contexto_superior(sym)
                        lateral = self._evaluar_lateralidad(sym, bot)
                        mom = self._evaluar_momentum(sym)
                        scoring = bot.calcular_scoring(contexto_superior=contexto, lateralidad=lateral, momentum=mom)
                        self.scoring_data[sym] = scoring
                        self._persistir_scoring(sym, scoring)
                    except Exception:
                        pass

                # Gestionar cubos en main thread
                self.parent.after(0, self._gestionar_cubos)

            except Exception as e:
                self.logger.error(f"_scoring_cycle bg: {e}")
            finally:
                # Programar siguiente ciclo
                if not self._closing and self.running:
                    self.parent.after(0, self._programar_siguiente_scoring)

        threading.Thread(target=_bg, daemon=True).start()

    def _programar_siguiente_scoring(self):
        """Programa el siguiente ciclo de scoring"""
        if not self._closing and self.running:
            self._scoring_timer_id = self.parent.after(self._scoring_interval, self._scoring_cycle)

    def _gestionar_cubos(self):
        """Main thread: agrega/remueve cubos según scoring actual.
        - Score >= 5 (Alta) + hay espacio → entra al canvas
        - Score < 5 + NONE → sale del canvas
        """
        try:
            max_bots = self.config.get("max_active_bots", 3)

            # 1. Remover bots NONE con scoring < 5
            bots_removidos = []
            for sym, bot in list(self.bots.items()):
                if bot.get_public_state().get("position") != "NONE":
                    continue
                score = self.scoring_data.get(sym, {}).get("score_total", 0)
                if score < 5:
                    self.logger.warning(f"SCORING CYCLE: {sym} score={score} < 5 → removiendo")
                    bots_removidos.append(sym)
                    del self.bots[sym]
                    if self.bot_manager:
                        self.bot_manager.unregister_bot(sym)
                    if sym in self.widgets:
                        self.widgets[sym].frame.destroy()
                        del self.widgets[sym]
                    self._resetear_indicadores_bd(sym)

            # 2. Rotación: si cubos llenos, reemplazar NONE de menor score
            #    por candidato de mayor score (prioriza símbolos más prometedores)
            activos_en_panel = set(self.bots.keys())
            candidatos = []
            for sym, scoring in self.scoring_data.items():
                if sym not in activos_en_panel:
                    score = scoring.get("score_total", 0)
                    if score >= 5:
                        candidatos.append((sym, score))

            candidatos.sort(key=lambda x: x[1], reverse=True)

            # Set de símbolos pendientes de creación (evita race condition con threads)
            if not hasattr(self, "_pending_bots"):
                self._pending_bots = set()

            # Si cubos llenos y hay candidatos, rotar NONE de menor score
            if len(self.bots) + len(self._pending_bots) >= max_bots and candidatos:
                # Bots en NONE ordenados por score ascendente (peor primero)
                bots_none = []
                for sym, bot in list(self.bots.items()):
                    if bot.get_public_state().get("position") == "NONE":
                        score_actual = self.scoring_data.get(sym, {}).get("score_total", 0)
                        bots_none.append((sym, score_actual))
                bots_none.sort(key=lambda x: x[1])  # peor score primero

                for cand_sym, cand_score in candidatos:
                    if not bots_none:
                        break
                    peor_sym, peor_score = bots_none[0]
                    # Solo rotar si el candidato tiene mejor score
                    if cand_score > peor_score:
                        self.logger.warning(
                            f"ROTACIÓN: {peor_sym}(score={peor_score}, NONE) → " f"{cand_sym}(score={cand_score})"
                        )
                        # Remover el NONE de menor score
                        del self.bots[peor_sym]
                        if self.bot_manager:
                            self.bot_manager.unregister_bot(peor_sym)
                        if peor_sym in self.widgets:
                            self.widgets[peor_sym].frame.destroy()
                            del self.widgets[peor_sym]
                        self._resetear_indicadores_bd(peor_sym)
                        bots_removidos.append(peor_sym)
                        bots_none.pop(0)
                    else:
                        break  # candidatos están ordenados desc, si este no supera, ninguno lo hará

            for sym, score in candidatos:
                total_ocupados = len(self.bots) + len(self._pending_bots)
                if total_ocupados >= max_bots:
                    break
                if sym in self.bots or sym in self._pending_bots:
                    continue

                self.logger.warning(f"SCORING CYCLE: {sym} score={score} → creando bot")
                self._pending_bots.add(sym)

                # Crear bot en background
                def _crear_bg(s=sym):
                    try:
                        self._crear_bot(s)
                    except Exception as e:
                        self.logger.error(f"SCORING CYCLE _crear_bot({s}): {e}")
                    finally:
                        self._pending_bots.discard(s)

                    def _ui(s=s):
                        if s not in self.bots:
                            return
                        activos_map = {a["symbol"]: a for a in self.all_activos}
                        activo = activos_map.get(s, {})
                        grid_idx = len(self.widgets) + 1
                        row = grid_idx // self.COLUMNS
                        col = grid_idx % self.COLUMNS
                        self._crear_widget_simbolo(s, activo, row, col)
                        self.widgets[s].set_running(True)

                        bot = self.bots.get(s)
                        if bot and bot.df is not None and len(bot.df) >= 50:
                            action, conds = bot.evaluate()
                            self.widgets[s].update_state(bot.get_public_state(), bot.get_indicators(), conds)
                            if action == "BUY" and self.bot_manager:
                                self.logger.warning(f">>> {s}: BUY desde scoring cycle")

                                def _exec(b=bot):
                                    try:
                                        self.bot_manager.execute_action(b, "BUY")
                                    except Exception as ex:
                                        self.logger.error(f"{s}: BUY error: {ex}")

                                    def _upd():
                                        w = self.widgets.get(s)
                                        if w:
                                            w.update_state(b.get_public_state(), b.get_indicators(), {})

                                    self.parent.after(0, _upd)

                                threading.Thread(target=_exec, daemon=True).start()

                    self.parent.after(0, _ui)

                threading.Thread(target=_crear_bg, daemon=True).start()

            if bots_removidos:
                self._reorganizar_grid()

            # 3. Actualizar panel scoring y capital (alineados)
            self._actualizar_panel_scoring()
            self._actualizar_panel_capital()

        except Exception as e:
            self.logger.error(f"_gestionar_cubos(): {e}")

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
        self._detener_scoring_cycle()
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

            # Actualizar label Max bots
            new_max = self.config.get("max_active_bots", 3)
            self._lbl_max_bots.config(text=str(new_max))

            # Actualizar combo de ambiente si cambió
            if self.env:
                self.combo_env.set(self.env)

            # Actualizar saldo desde Binance
            self._actualizar_saldo()

            self.logger.warning(
                f"Config recargada: capital {old_capital:.2f} → {new_capital:.2f} | max_bots={new_max} | env={self.env}"
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
            # Bloquear si hay posiciones LONG activas
            tiene_posiciones = any(bot.get_public_state().get("position") == "LONG" for bot in self.bots.values())
            if tiene_posiciones:
                self.combo_interval.set(self.interval)  # Revertir combo
                self.logger.warning(f"Cambio de intervalo bloqueado: hay posiciones LONG activas")
                MyMessageBox(self.right).showwarning(
                    "Cambio bloqueado",
                    "No se puede cambiar la temporalidad con posiciones LONG activas.\nCierra las posiciones primero.",
                )
                return

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
                                    "cooldown_hours": 4,
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
                            contexto = self._evaluar_contexto_superior(symbol)
                            lateral = self._evaluar_lateralidad(symbol, tmp_bot)
                            mom = self._evaluar_momentum(symbol)
                            scoring = tmp_bot.calcular_scoring(
                                contexto_superior=contexto, lateralidad=lateral, momentum=mom
                            )
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

    def _on_remove_symbol(self):
        """Abre diálogo para eliminar un símbolo del universo BotCrypto."""
        simbolos = [a.get("symbol") for a in self.all_activos if a.get("symbol")]
        if not simbolos:
            return

        bg  = self.colors["bgcolor"]
        fg  = "white"

        dialog = tk.Toplevel(self.right)
        dialog.title("Eliminar Símbolo")
        try:
            x = self.right.winfo_rootx() + self.right.winfo_width() - 100
            y = self.right.winfo_rooty() + 200
        except Exception:
            x, y = 200, 150
        dialog.geometry(f"240x190+{x}+{y}")
        dialog.resizable(False, False)
        dialog.config(bg=bg)
        dialog.transient(self.right)
        dialog.grab_set()

        tk.Label(dialog, text="Seleccionar símbolo:", bg=bg, fg=fg,
                 font=("Arial", 10)).pack(pady=(12, 4))

        combo = ttk.Combobox(dialog, values=simbolos, state="readonly",
                             font=("Arial", 11), width=16, justify="center")
        combo.pack(pady=4)
        if simbolos:
            combo.current(0)

        lbl_status = tk.Label(dialog, text="", bg=bg, fg="yellow", font=("Arial", 9))
        lbl_status.pack(pady=2)

        def eliminar():
            symbol = combo.get().strip()
            if not symbol:
                return

            # Bloquear si tiene bot activo con posición abierta
            bot = self.bots.get(symbol)
            if bot and bot.state.get("position") == "LONG":
                lbl_status.config(text=f"{symbol} tiene posición abierta", fg="red")
                return

            lbl_status.config(text=f"Eliminando {symbol}...", fg="yellow")
            dialog.update()

            try:
                self.repositorio.delete_otros_activos(symbol=symbol, cuenta=self.ACCOUNT)
            except Exception as e:
                lbl_status.config(text=f"Error BD: {e}", fg="red")
                return

            # Limpiar en memoria
            self.all_activos  = [a for a in self.all_activos if a.get("symbol") != symbol]
            self.scoring_data.pop(symbol, None)

            # Si tiene cubo activo sin posición → cerrarlo
            if symbol in self.bots:
                self._on_stop_symbol(symbol)
            if symbol in self.widgets:
                self._cerrar_chart_window(symbol)
                self.widgets[symbol].frame.destroy()
                self.widgets.pop(symbol, None)

            self.lbl_activos.config(text=str(len(self.all_activos)))
            self._actualizar_panel_scoring()
            self.logger.warning(f"Símbolo {symbol} eliminado del universo")
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=bg)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text="Eliminar", command=eliminar,
                  bg="#b71c1c", fg="white", font=("Arial", 9), width=9).pack(side=tk.LEFT, padx=8)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy,
                  font=("Arial", 9), width=9).pack(side=tk.LEFT, padx=8)

        dialog.bind("<Escape>", lambda e: dialog.destroy())

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
                "cooldown_hours": self.config.get("cooldown_hours", 4),
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
                state_repo=self.state_repo,
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

    def _detectar_posiciones_binance(self):
        """Detecta símbolos con posiciones reales en Binance (balance > dust).
        Retorna lista de símbolos USDT que tienen balance significativo."""
        symbols_con_posicion = []
        try:
            account = self.spot_client.account_spot()
            if not account or "balances" not in account:
                return symbols_con_posicion

            # Set de símbolos del universo para filtrar
            universo = {a["symbol"] for a in self.all_activos}

            for b in account["balances"]:
                asset = b["asset"]
                if asset in ("USDT", "BNB"):
                    continue
                total = float(b.get("free", 0)) + float(b.get("locked", 0))
                if total <= 0:
                    continue

                symbol = f"{asset}USDT"
                if symbol not in universo:
                    continue

                # Verificar que no sea dust (> $1)
                try:
                    ticker = self.spot_client.ticker_price(symbol)
                    price = float(ticker.get("price", 0))
                    if price > 0 and total * price > 1.0:
                        symbols_con_posicion.append(symbol)
                except Exception:
                    pass

        except Exception as e:
            self.logger.error(f"_detectar_posiciones_binance: {e}")

        return symbols_con_posicion

    def _cargar_posicion_existente(self, bot, symbol):
        """
        Carga posición existente al iniciar el bot.
        Primero intenta restaurar desde estado persistido (FileStateRepo).
        Si no hay estado guardado, reconstruye desde Binance API.
        """
        try:
            # 0. Intentar restaurar estado persistido
            saved = self.state_repo.load_state(symbol)
            if saved and saved.get("position") == "LONG" and saved.get("entry_price"):
                bot.state.update(saved)
                notional = bot.state.get("remaining_qty", 0) * bot.state["entry_price"]
                if self.capital_manager and notional > 0:
                    self.capital_manager.reserve(notional)
                self.trades_count += 1
                if self.lbl_trades:
                    self.lbl_trades.config(text=str(self.trades_count))
                self.logger.warning(
                    f"📥 {symbol}: ESTADO RESTAURADO desde archivo | entry={bot.state['entry_price']:.6f} "
                    f"| qty={bot.state.get('remaining_qty'):.4f} | tp1={bot.state.get('tp1_done')} "
                    f"| trailing={bot.state.get('trailing_active')}"
                )
                return

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
                self.logger.warning(f"{symbol}: Balance={balance} pero sin trades recientes")
                entry_price = 0
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

            # Fallback: usar precio actual si no se pudo calcular entry
            if entry_price <= 0:
                entry_price = bot._last_price() if bot.df is not None and len(bot.df) > 0 else 0
            if entry_price <= 0:
                entry_price = price  # precio del ticker obtenido arriba
            if entry_price <= 0:
                self.logger.error(
                    f"{symbol}: Balance={balance} pero no se pudo obtener ningún precio → forzando con ticker"
                )
                try:
                    ticker = self.spot_client.ticker_price(symbol)
                    entry_price = float(ticker.get("price", 0))
                except Exception:
                    pass
            if entry_price <= 0:
                self.logger.error(f"{symbol}: IMPOSIBLE obtener precio, posición no cargada")
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
        self.lbl_regimeok = None
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
        self._crear_label_row(content, "Regime:", "lbl_regimeok", row, font_size=7)
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
            text="Strategy",
            bg="blue",
            fg="white",
            width=7,
            command=self.on_chart,
        ).pack(side=tk.RIGHT, padx=2)

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
        """Actualiza el precio y PnL en tiempo real (cada tick WS)"""
        try:
            if not self.lbl_price.winfo_exists():
                return
            self.lbl_price.config(text=f"{price:.4f}")
            # Actualizar PnL con precio live
            if hasattr(self, "_entry_price") and self._entry_price and hasattr(self, "_qty") and self._qty > 0:
                pnl_pct = ((price - self._entry_price) / self._entry_price) * 100
                color = "lime" if pnl_pct > 0 else "red" if pnl_pct < 0 else "white"
                if self.lbl_pnl.winfo_exists():
                    self.lbl_pnl.config(text=f"{pnl_pct:+.2f}%  :: (qty:{self._qty:.1f})", fg=color)
        except tk.TclError:
            pass

    def update_state(self, state, indicators, conditions):
        """Actualiza el estado y los indicadores"""
        # RSI con zona visual
        rsi = indicators.get("rsi")
        if rsi:
            if rsi < 35:
                arrow, color = "▲▲", "lime"  # Sobreventa (compra fuerte)
            elif rsi < 45:
                arrow, color = "▲", "#90EE90"  # Acercándose a compra
            elif rsi <= 55:
                arrow, color = "●", "yellow"  # Neutral
            elif rsi <= 65:
                arrow, color = "▼", "orange"  # Acercándose a venta
            else:
                arrow, color = "▼▼", "red"  # Sobrecompra (venta fuerte)
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
        tp2 = "✓" if state.get("tp2_done") else "○"
        if state.get("trailing_active"):
            trail_stop = state.get("trailing_stop")
            trail_txt = f"TRAIL:{trail_stop:.4f}" if trail_stop else "TRAIL:--"
            self.lbl_tp.config(text=f"TP1:{tp1} TP2:{tp2} | {trail_txt}", fg="cyan")
        else:
            self.lbl_tp.config(text=f"TP1:{tp1} TP2:{tp2}", fg="white")

        # PnL + cantidad del lote
        # Guardar para update_price en tiempo real
        self._entry_price = entry
        self._qty = qty
        if entry and qty > 0:
            last = indicators.get("last_price", entry)
            pnl_pct = ((last - entry) / entry) * 100
            color = "lime" if pnl_pct > 0 else "red"
            self.lbl_pnl.config(text=f"{pnl_pct:+.2f}%  :: (qty:{qty:.1f})", fg=color)
        else:
            self.lbl_pnl.config(text="--", fg="white")

        # ─────────────────────────────────────────────────────────────
        # Condiciones de compra (siempre visibles)
        # ─────────────────────────────────────────────────────────────
        if conditions:
            # Regime: Filtro estructural EMA100/EMA200
            regime_ok = conditions.get("regime_ok", {})
            regime_val = regime_ok.get("value", False)
            regime_detail = regime_ok.get("detail", "--")
            regime_color = {"BULL": "lime", "BEAR": "red", "RANGE": "orange"}.get(regime_detail, "gray")
            regime_icon = "✓" if regime_val else "✗"
            self.lbl_regimeok.config(text=f"{regime_icon} {regime_detail}", fg=regime_color)

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
