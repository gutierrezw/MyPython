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
    json,
    pd,
    RSIIndicator,
    EMAIndicator,
    MACD,
)
from Modulos_Mysql import BDsystem
from Class_vehiculo import BinanceClient, BinanceStreamClient
from Class_customer import DataHub
from Class_DataFrame import get_klines_info
import logging


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
        if self.state_repo:
            self.state_repo.save_state(self.symbol, self.state)

    def _is_in_position(self) -> bool:
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
        Usa la librería `ta` (ya disponible en el proyecto).
        """
        if self.df is None or len(self.df) < 30:
            return

        close = self.df["Close"]

        # RSI (14 períodos)
        self.df["rsi"] = RSIIndicator(close=close, window=14).rsi()

        # MACD (12, 26, 9)
        macd_obj = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
        self.df["macd"] = macd_obj.macd()
        self.df["macd_signal"] = macd_obj.macd_signal()
        self.df["macd_hist"] = macd_obj.macd_diff()

        # EMA rápida (9) y lenta (21)
        self.df["ema_fast"] = EMAIndicator(close=close, window=9).ema_indicator()
        self.df["ema_slow"] = EMAIndicator(close=close, window=21).ema_indicator()

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

    def __init__(self, spot_client, order_manager, capital_manager):
        self.spot_client = spot_client
        self.order_manager = order_manager
        self.capital_manager = capital_manager
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

    # =========================
    # EJECUCION ORDENES
    # =========================
    def execute_action(self, bot, action):
        """Ejecuta la acción decidida por el bot."""
        if action == "BUY":
            self._execute_buy(bot)
        elif action == "TP1":
            self._execute_partial_sell(bot, intent="TP1")
        elif action == "TP2":
            self._execute_partial_sell(bot, intent="TP2")
        elif action == "EXIT":
            self._execute_exit(bot)

    def _execute_buy(self, bot):
        price = bot._last_price()
        capital = self.capital_manager.get_available_capital()

        if capital <= 0:
            self.logger.warning(f"{bot.symbol}: Sin capital disponible")
            return

        qty = bot._calc_position_size(price, capital)
        qty = self._format_qty(bot.symbol, qty)

        if qty <= 0:
            return

        self.logger.info(f"{bot.symbol}: BUY qty={qty} price={price:.4f} capital={capital:.2f}")

        order = self.spot_client.get_new_order(
            symbol=bot.symbol, side="BUY", type="MARKET", quantity=qty,
        )

        if not order:
            self.logger.error(f"{bot.symbol}: Orden BUY fallida")
            return

        order_id = order["orderId"]
        self.order_manager.register_order(symbol=bot.symbol, order_id=order_id, intent="ENTRY")
        self.capital_manager.reserve(qty * price)

    def _execute_partial_sell(self, bot, intent: str):
        if intent == "TP1":
            qty = bot.state["position_qty"] * bot.risk_cfg["tp1_size"]
        elif intent == "TP2":
            qty = bot.state["position_qty"] * bot.risk_cfg["tp2_size"]
        else:
            return

        qty = self._format_qty(bot.symbol, qty)

        if qty <= 0:
            return

        self.logger.info(f"{bot.symbol}: {intent} SELL qty={qty}")

        order = self.spot_client.get_new_order(
            symbol=bot.symbol, side="SELL", type="MARKET", quantity=qty,
        )

        if not order:
            self.logger.error(f"{bot.symbol}: Orden {intent} fallida")
            return

        order_id = order["orderId"]
        self.order_manager.register_order(symbol=bot.symbol, order_id=order_id, intent=intent)

        if intent == "TP1":
            bot.state["tp1_done"] = True
        elif intent == "TP2":
            bot.state["tp2_done"] = True

        self.capital_manager.release(qty * bot._last_price())

    def _execute_exit(self, bot):
        qty = bot.state["remaining_qty"]

        if qty <= 0:
            return

        qty = self._format_qty(bot.symbol, qty)

        if qty <= 0:
            return

        self.logger.info(f"{bot.symbol}: EXIT SELL qty={qty}")

        order = self.spot_client.get_new_order(
            symbol=bot.symbol, side="SELL", type="MARKET", quantity=qty,
        )

        if not order:
            self.logger.error(f"{bot.symbol}: Orden EXIT fallida")
            return

        order_id = order["orderId"]
        self.order_manager.register_order(symbol=bot.symbol, order_id=order_id, intent="EXIT")
        self.capital_manager.release(qty * bot._last_price())


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
    WIDGET_WIDTH = 280
    WIDGET_HEIGHT = 220

    def __init__(self, parent, colors, repositorio):
        """
        Args:
            parent: Frame padre (win6 del notebook)
            colors: Diccionario de colores de la app
            repositorio: RepositorioOportunidadesBuySell
        """
        self.parent = parent
        self.colors = colors
        self.repositorio = repositorio
        self.logger = logging.getLogger("BotCryptoUI")

        # Estado
        self.widgets = {}  # symbol -> WidgetBotSymbol
        self.bots = {}  # symbol -> TradingBotSpot
        self.running = False
        self.interval = "5m"

        # Config desde BD (incluye env)
        self.config = self._cargar_config()
        self.env = self.config.get("env", "TESTNET")

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

    def _cargar_config(self):
        """
        Carga configuración desde tabla sesion vehiculo=BotCrypto.
        - userapi (JSON): capital, risk, tp, rsi, etc.
        - environment: ambiente (TESTNET | PRODUCTION)
        """
        config = {
            "capital": 100.0,
            "risk_per_trade": 0.02,
            "tp1_pct": 0.03,
            "tp2_pct": 0.06,
            "stop_loss_pct": 0.02,
            "tp1_size": 0.33,
            "tp2_size": 0.33,
            "rsi_buy": 35,
            "rsi_sell": 65,
            "env": "TESTNET",
        }

        try:
            sesion = BDsystem.get_sesion_by_vehiculo("BotCrypto")

            # Config JSON desde userapi
            if sesion and sesion.get("userapi"):
                user_config = json.loads(sesion["userapi"].decode("utf-8"))
                config.update(user_config)

            # Ambiente desde environment
            if sesion:
                db_env = (sesion.get("environment") or "").strip().upper()
                if db_env in ("TESTNET", "PRODUCTION"):
                    config["env"] = db_env

        except Exception as e:
            self.logger.warning(f"Config BotCrypto no encontrada: {e}")

        return config

    def inicializar(self):
        """Inicializa la UI completa"""
        try:
            self._crear_panel_control()
            self._crear_canvas_scrollable()
            self._cargar_simbolos()
            self._inicializar_managers()
        except Exception as e:
            self.logger.error(f"Error inicializando BotCryptoUI: {e}")
            traceback.print_exc()

    # =========================================
    # PANEL DE CONTROL
    # =========================================
    def _crear_panel_control(self):
        """Crea el panel superior con controles globales"""
        panel = tk.Frame(self.parent, bg=self.colors["cgcolor"], height=80)
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

        # Capital
        tk.Label(row1, text="Capital:", bg=self.colors["cgcolor"], fg="white").pack(side=tk.LEFT, padx=(30, 5))
        self.lbl_capital = tk.Label(
            row1,
            text=f"{self.config.get('capital', 0):.2f} USDT",
            bg=self.colors["cgcolor"],
            fg="cyan",
            font=("Arial", 10, "bold"),
        )
        self.lbl_capital.pack(side=tk.LEFT)

        # Fila 2: Intervalo y métricas
        row2 = tk.Frame(panel, bg=self.colors["cgcolor"])
        row2.pack(fill=tk.X, pady=2)

        # Selector de ambiente
        tk.Label(row2, text="Env:", bg=self.colors["cgcolor"], fg="white").pack(side=tk.LEFT, padx=5)
        self.combo_env = ttk.Combobox(row2, values=["TESTNET", "PRODUCTION"], width=12, state="readonly")
        self.combo_env.set(self.env)
        self.combo_env.pack(side=tk.LEFT, padx=5)
        self.combo_env.bind("<<ComboboxSelected>>", self._on_env_change)

        # Selector de intervalo
        tk.Label(row2, text="Intervalo:", bg=self.colors["cgcolor"], fg="white").pack(side=tk.LEFT, padx=(10, 5))
        self.combo_interval = ttk.Combobox(row2, values=["1m", "5m", "15m", "1h"], width=5, state="readonly")
        self.combo_interval.set("5m")
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

        # Botón agregar símbolo
        btn_add = tk.Button(
            row2,
            text="+ Agregar",
            bg="blue",
            fg="white",
            font=("Arial", 9),
            command=self._on_add_symbol,
        )
        btn_add.pack(side=tk.RIGHT, padx=10)

    # =========================================
    # CANVAS SCROLLABLE
    # =========================================
    def _crear_canvas_scrollable(self):
        """Crea el canvas con scroll para los widgets de símbolos"""
        # Container
        container = tk.Frame(self.parent, bg=self.colors["bgcolor"])
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
        """Carga símbolos desde otros_activos y crea widgets"""
        try:
            activos, found = self.repositorio.select_otros_activos(symbol="all", account=self.ACCOUNT)

            if not found or not activos:
                self.logger.info(f"No hay símbolos para cuenta {self.ACCOUNT}")
                self._mostrar_mensaje_vacio()
                return

            # Crear widgets en grid
            for idx, activo in enumerate(activos):
                symbol = activo.get("symbol")
                if symbol:
                    row = idx // self.COLUMNS
                    col = idx % self.COLUMNS
                    self._crear_widget_simbolo(symbol, activo, row, col)

            # Actualizar contador
            self.lbl_activos.config(text=str(len(activos)))

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
            env=self.env,
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
            # Binance client (lee env desde sesion.environment)
            self.binance_client = BinanceClient(vehiculo="BotCrypto")
            self.spot_client = self.binance_client.spot

            # Sincronizar env local con lo que resolvió BinanceClient
            self.env = self.binance_client.env

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
            )

            self.logger.info(f"Managers inicializados: env={self.env}, capital={capital}, base_url={self.binance_client.urls['base_url']}")

        except Exception as e:
            self.logger.error(f"Error inicializando managers: {e}")

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
                f"✅ [BotCryptoUI] WebSocket inicializado correctamente | env={self.env} | symbols={len(symbols)} | itera={self.ws_stream_itera}"
            )

            # Suscribir a klines del intervalo seleccionado
            self.ws_client.subscribe_klines(interval=self.interval)
        except Exception as e:
            self.logger.error(f"Error iniciando WebSocket: {e}")

    def _detener_websocket(self):
        """Detiene el WebSocket"""
        try:
            if self.ws_client:
                self.ws_client.stop()
                self.ws_client = None
        except Exception as e:
            self.logger.error(f"Error deteniendo WebSocket: {e}")

    def _on_ws_message(self, msg):
        """Procesa mensaje del WebSocket"""
        try:
            # Contabilizar iteradas para process_system
            self.ws_msg_counter += 1
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

                # Actualizar widget
                if symbol in self.widgets:
                    price = float(kline["c"])
                    self.widgets[symbol].update_price(price)

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
                    self._evaluar_bot(symbol, candle)

        except Exception as e:
            self.logger.error(f"Error procesando WS message: {e}")

    def _evaluar_bot(self, symbol, candle):
        """Evalúa el bot para un símbolo"""
        try:
            bot = self.bots.get(symbol)
            if not bot:
                return

            bot.on_market_data(candle)
            action = bot.evaluate()

            # Actualizar widget con estado
            state = bot.get_public_state()
            indicators = bot.get_indicators()
            self.widgets[symbol].update_state(state, indicators)

            # Ejecutar orden via bot_manager
            if action != "HOLD" and self.bot_manager:
                self.logger.info(f"{symbol}: Acción {action}")
                self.bot_manager.execute_action(bot, action)

        except Exception as e:
            self.logger.error(f"Error evaluando bot {symbol}: {e}")

    # =========================================
    # EVENT HANDLERS
    # =========================================
    def _on_start_all(self):
        """Inicia todos los bots"""
        if self.running:
            return

        self.running = True
        self.lbl_status.config(text="● RUNNING", fg="lime")
        self.interval = self.combo_interval.get()

        # Crear bots para cada símbolo
        for symbol, widget in self.widgets.items():
            self._crear_bot(symbol)
            widget.set_running(True)

        # Iniciar WebSocket
        self._iniciar_websocket()

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

        # Actualizar widgets
        for widget in self.widgets.values():
            widget.set_running(False)

    def _on_start_symbol(self, symbol):
        """Inicia bot para un símbolo específico"""
        if symbol not in self.bots:
            self._crear_bot(symbol)
            self.widgets[symbol].set_running(True)

    def _on_stop_symbol(self, symbol):
        """Detiene bot para un símbolo específico"""
        if symbol in self.bots:
            del self.bots[symbol]
            self.widgets[symbol].set_running(False)

    def _on_show_chart(self, symbol):
        """Muestra gráfico detallado del símbolo"""
        # TODO: Abrir ventana de análisis
        self.logger.info(f"Mostrar chart para {symbol}")

    def _on_test_buy(self, symbol):
        """Ejecuta orden de prueba en TESTNET. Compra mínima del símbolo."""
        if self.env != "TESTNET":
            self.logger.warning("TEST BUY solo disponible en TESTNET")
            return

        if not self.bot_manager:
            self.logger.error("BotManager no inicializado")
            return

        try:
            # Obtener LOT_SIZE para calcular cantidad mínima
            lot = self.bot_manager.lot_sizes.get(symbol)
            if not lot:
                # Cargar si no está en cache
                self.bot_manager._load_lot_size(symbol)
                lot = self.bot_manager.lot_sizes.get(symbol)

            min_qty = lot["minQty"] if lot else 0.001

            self.logger.info(f"TEST BUY {symbol}: qty={min_qty} (minQty)")

            order = self.spot_client.get_new_order(
                symbol=symbol, side="BUY", type="MARKET", quantity=min_qty,
            )

            if order:
                self.logger.warning(f"TEST BUY OK {symbol}: orderId={order['orderId']} status={order.get('status')}")

                # Actualizar widget para mostrar resultado
                widget = self.widgets.get(symbol)
                if widget:
                    widget.lbl_estado.config(text=f"TEST OK #{order['orderId']}", fg="lime")
            else:
                self.logger.error(f"TEST BUY FALLIDO {symbol}")
                widget = self.widgets.get(symbol)
                if widget:
                    widget.lbl_estado.config(text="TEST FALLIDO", fg="red")

        except Exception as e:
            self.logger.error(f"TEST BUY error {symbol}: {e}")
            widget = self.widgets.get(symbol)
            if widget:
                widget.lbl_estado.config(text=f"ERROR: {e}", fg="red")

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
        """Cambia el intervalo de velas"""
        new_interval = self.combo_interval.get()
        if new_interval != self.interval:
            self.interval = new_interval
            if self.running:
                # Reiniciar WebSocket con nuevo intervalo
                self._detener_websocket()
                self._iniciar_websocket()

    def _on_add_symbol(self):
        """Abre diálogo para agregar nuevo símbolo al BotCrypto"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Agregar Símbolo - BotCrypto")
        dialog.geometry("360x180")
        dialog.resizable(False, False)
        dialog.config(bg=self.colors["bgcolor"])
        dialog.transient(self.parent)
        dialog.grab_set()

        tk.Label(
            dialog,
            text="Símbolo (ej: BTCUSDT):",
            bg=self.colors["bgcolor"],
            fg="white",
            font=("Arial", 10),
        ).pack(pady=(15, 5))

        entry = tk.Entry(dialog, font=("Arial", 12), width=20, justify="center")
        entry.pack(pady=5)
        entry.focus_set()

        lbl_status = tk.Label(
            dialog,
            text="",
            bg=self.colors["bgcolor"],
            fg="yellow",
            font=("Arial", 9),
        )
        lbl_status.pack(pady=5)

        def agregar():
            symbol = entry.get().strip().upper()
            if not symbol:
                lbl_status.config(text="Ingrese un símbolo", fg="red")
                return

            if not symbol.endswith("USDT"):
                symbol += "USDT"

            # Verificar si ya existe en el grid
            if symbol in self.widgets:
                lbl_status.config(text=f"{symbol} ya existe en el panel", fg="red")
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

            # Cargar desde BD y crear widget
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
                    idx = len(self.widgets)
                    row = idx // self.COLUMNS
                    col = idx % self.COLUMNS

                    # Limpiar label "no hay símbolos" si existe
                    for child in self.scrollable_frame.winfo_children():
                        if isinstance(child, tk.Label):
                            child.destroy()

                    self._crear_widget_simbolo(symbol, activo, row, col)
                    self.lbl_activos.config(text=str(len(self.widgets)))
                    print(f"[BotCryptoUI] Símbolo {symbol} agregado OK | widgets={len(self.widgets)}")
                    dialog.destroy()
                else:
                    lbl_status.config(text="Error: símbolo no encontrado después de insertar", fg="red")

            except Exception as e:
                lbl_status.config(text=f"Error creando widget: {e}", fg="red")
                traceback.print_exc()

        btn = tk.Button(
            dialog,
            text="Agregar",
            command=agregar,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
            width=15,
        )
        btn.pack(pady=10)

        entry.bind("<Return>", lambda e: agregar())

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
                "tp2_pct": self.config.get("tp2_pct", 0.06),
                "stop_loss_pct": self.config.get("stop_loss_pct", 0.02),
                "tp1_size": self.config.get("tp1_size", 0.33),
                "tp2_size": self.config.get("tp2_size", 0.33),
            }

            bot = TradingBotSpot(
                symbol=symbol,
                interval=self.interval,
                strategy_config=strategy_config,
                risk_config=risk_config,
                state_repo=None,  # TODO: Implementar persistencia
                order_manager=self.order_manager,
            )

            # Cargar datos históricos
            self._cargar_historico(bot, symbol)

            self.bots[symbol] = bot

            # Registrar en BotManager para ejecución de órdenes
            if self.bot_manager:
                self.bot_manager.register_bot(bot)

        except Exception as e:
            self.logger.error(f"Error creando bot para {symbol}: {e}")

    def _cargar_historico(self, bot, symbol):
        """Carga datos históricos para el bot"""
        try:
            # Obtener klines históricos
            df = get_klines_info(symbol=symbol, period="30d", interval=self.interval)
            if df is not None and not df.empty:
                bot.df = df
                bot.calcular_indicadores()
        except Exception as e:
            self.logger.error(f"Error cargando histórico {symbol}: {e}")


# =============================================================================
# WIDGET POR SÍMBOLO: WidgetBotSymbol
# =============================================================================
class WidgetBotSymbol:
    """
    Widget individual para mostrar información de un símbolo.
    Incluye precio, indicadores, estado y controles.
    """

    def __init__(self, parent, symbol, activo, colors, config, on_start, on_stop, on_chart, on_test_buy=None, env="TESTNET"):
        self.parent = parent
        self.symbol = symbol
        self.activo = activo
        self.colors = colors
        self.config = config
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_chart = on_chart
        self.on_test_buy = on_test_buy
        self.env = env

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
        self.btn_test_buy = None

    def crear_ui(self):
        """Crea la UI del widget"""
        # Frame principal con borde
        self.frame = tk.Frame(
            self.parent,
            bg=self.colors["cgcolor"],
            width=280,
            height=220,
            relief=tk.RIDGE,
            borderwidth=2,
        )
        self.frame.pack_propagate(False)

        # Header con símbolo
        header = tk.Frame(self.frame, bg="#2a4a5a")
        header.pack(fill=tk.X)

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
            text="⏹",
            bg="red",
            fg="white",
            width=3,
            command=self.on_stop,
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            btn_frame,
            text="📊",
            bg="blue",
            fg="white",
            width=3,
            command=self.on_chart,
        ).pack(side=tk.LEFT, padx=2)

        # TEST BUY - solo activo en TESTNET
        self.btn_test_buy = tk.Button(
            btn_frame,
            text="TEST",
            bg="#FF9800",
            fg="white",
            width=5,
            font=("Arial", 8, "bold"),
            command=self.on_test_buy if self.on_test_buy else lambda: None,
            state=tk.NORMAL if self.env == "TESTNET" else tk.DISABLED,
        )
        self.btn_test_buy.pack(side=tk.RIGHT, padx=2)

    def _crear_label_row(self, parent, label_text, attr_name, row):
        """Crea una fila con label y valor"""
        tk.Label(
            parent,
            text=label_text,
            bg=self.colors["cgcolor"],
            fg="gray",
            font=("Arial", 9),
            anchor="w",
            width=8,
        ).grid(row=row, column=0, sticky="w")

        lbl_value = tk.Label(
            parent,
            text="--",
            bg=self.colors["cgcolor"],
            fg="white",
            font=("Arial", 9),
            anchor="w",
        )
        lbl_value.grid(row=row, column=1, sticky="w")
        setattr(self, attr_name, lbl_value)

    def update_price(self, price):
        """Actualiza el precio"""
        self.lbl_price.config(text=f"{price:.4f}")

    def update_state(self, state, indicators):
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

        # Entry
        entry = state.get("entry_price")
        self.lbl_entry.config(text=f"{entry:.4f}" if entry else "--")

        # TP
        tp1 = "✓" if state.get("tp1_done") else "○"
        tp2 = "✓" if state.get("tp2_done") else "○"
        self.lbl_tp.config(text=f"TP1:{tp1} TP2:{tp2}")

        # PnL
        if entry and state.get("remaining_qty", 0) > 0:
            last = indicators.get("last_price", entry)
            pnl_pct = ((last - entry) / entry) * 100
            color = "lime" if pnl_pct > 0 else "red"
            self.lbl_pnl.config(text=f"{pnl_pct:+.2f}%", fg=color)
        else:
            self.lbl_pnl.config(text="--", fg="white")

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
