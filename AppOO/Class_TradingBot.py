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

        # ----- Estado interno -----
        self.state = {
            "position": "NONE",  # NONE | LONG
            "entry_price": None,
            "position_qty": 0.0,
            "remaining_qty": 0.0,
            "stop_loss": None,
            "tp1_done": False,
            "tp2_done": False,
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

    def evaluate(self) -> str:
        """
        Decide acción a tomar.
        Retorna: BUY | TP1 | TP2 | EXIT | HOLD
        """
        if not self._is_in_position():
            if self._should_buy():
                return "BUY"
            return "HOLD"

        # Ya en posición
        price = self._last_price()

        if not self.state["tp1_done"] and self._should_take_tp1(price):
            return "TP1"

        if not self.state["tp2_done"] and self._should_take_tp2(price):
            return "TP2"

        if self._should_exit(price):
            return "EXIT"

        return "HOLD"

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
    # ESTRATEGIA (PRIVADO)
    # =========================
    def _should_buy(self) -> bool:
        if self.df is None or len(self.df) < 50:
            return False

        rsi = self.df["rsi"].iloc[-1]
        macd = self.df["macd"].iloc[-1]
        macd_signal = self.df["macd_signal"].iloc[-1]
        ema_fast = self.df["ema_fast"].iloc[-1]
        ema_slow = self.df["ema_slow"].iloc[-1]

        return rsi < self.strategy_cfg["rsi_buy"] and macd > macd_signal and ema_fast > ema_slow

    def _should_exit(self, price: float) -> bool:
        # Stop loss
        if price <= self.state["stop_loss"]:
            return True

        rsi = self.df["rsi"].iloc[-1]
        return rsi > self.strategy_cfg["rsi_sell"]

    # =========================
    # TAKE PROFIT (PRIVADO)
    # =========================
    def _should_take_tp1(self, price: float) -> bool:
        target = self.state["entry_price"] * (1 + self.risk_cfg["tp1_pct"])
        return price >= target

    def _should_take_tp2(self, price: float) -> bool:
        target = self.state["entry_price"] * (1 + self.risk_cfg["tp2_pct"])
        return price >= target

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
        }

    def _persist_state(self):
        self.state_repo.save_state(self.symbol, self.state)

    def _is_in_position(self) -> bool:
        return self.state["position"] == "LONG"

    # =========================
    # MARKET DATA (PRIVADO)
    # =========================
    def _update_dataframe(self, candle: dict):
        """
        Actualiza DF + indicadores.
        Asumimos candle cerrada.
        """
        # Acá reutilizás tu lógica previa de indicadores
        pass

    def _last_price(self) -> float:
        return self.df["close"].iloc[-1]


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
        # Estrategia simple:
        # - log
        # - ignorar
        # - o reconciliar vía REST
        pass


class BotManager:
    """
    Coordina múltiples TradingBotSpot.
    Ejecuta órdenes Spot vía REST según decisiones de los bots.
    """

    def __init__(self, spot_client, order_manager, capital_manager):
        self.spot_client = spot_client
        self.order_manager = order_manager
        self.capital_manager = capital_manager

        # symbol -> TradingBotSpot
        self.bots = {}

    # =========================
    # REGISTRO
    # =========================
    def register_bot(self, bot):
        """
        Registra un bot y lo vincula al OrderManager.
        """
        self.bots[bot.symbol] = bot
        self.order_manager.register_bot(bot.symbol, bot)

    # =========================
    # MARKET DATA
    # =========================
    def on_market_data(self, symbol: str, candle: dict):
        """
        Entrada desde WebSocket (vela cerrada).
        """
        bot = self.bots.get(symbol)
        if not bot:
            return

        bot.on_market_data(candle)
        self._evaluate_bot(bot)

    # =========================
    # EVALUACION
    # =========================
    def _evaluate_bot(self, bot):
        action = bot.evaluate()

        if action == "BUY":
            self._execute_buy(bot)

        elif action == "TP1":
            self._execute_partial_sell(bot, intent="TP1")

        elif action == "TP2":
            self._execute_partial_sell(bot, intent="TP2")

        elif action == "EXIT":
            self._execute_exit(bot)

    # =========================
    # EJECUCION ORDENES
    # =========================
    def _execute_buy(self, bot):
        price = bot._last_price()
        capital = self.capital_manager.get_available_capital()

        qty = bot._calc_position_size(price, capital)

        order = self.spot_client.new_order(symbol=bot.symbol, side="BUY", type="MARKET", quantity=qty)

        order_id = order["orderId"]

        self.order_manager.register_order(symbol=bot.symbol, order_id=order_id, intent="ENTRY")

    def _execute_partial_sell(self, bot, intent: str):
        if intent == "TP1":
            qty = bot.state["position_qty"] * bot.risk_cfg["tp1_size"]
            bot.state["tp1_done"] = True

        elif intent == "TP2":
            qty = bot.state["position_qty"] * bot.risk_cfg["tp2_size"]
            bot.state["tp2_done"] = True

        order = self.spot_client.new_order(symbol=bot.symbol, side="SELL", type="MARKET", quantity=qty)

        order_id = order["orderId"]

        self.order_manager.register_order(symbol=bot.symbol, order_id=order_id, intent=intent)

    def _execute_exit(self, bot):
        qty = bot.state["remaining_qty"]

        if qty <= 0:
            return

        order = self.spot_client.new_order(symbol=bot.symbol, side="SELL", type="MARKET", quantity=qty)

        order_id = order["orderId"]

        self.order_manager.register_order(symbol=bot.symbol, order_id=order_id, intent="EXIT")
