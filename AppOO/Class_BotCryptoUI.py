"""
Class_BotCryptoUI.py - UI para Bot de Trading Crypto Spot

Arquitectura:
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
)
from Modulos_Mysql import BDsystem
from Class_tradingBot import TradingBotSpot, BotManager, OrderManager
from API_vehiculos import BB, SpotWebsocketStreamClient
from Class_DataFrame import get_klines_info
import logging


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

        # Managers
        self.order_manager = None
        self.bot_manager = None
        self.ws_client = None

        # Config desde BD
        self.config = self._cargar_config()

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
        """Carga configuración desde tabla sesion vehiculo=BotCrypto"""
        try:
            sesion = BDsystem.get_sesion_by_vehiculo("BotCrypto")
            if sesion and sesion.get("userapi"):
                config = json.loads(sesion["userapi"].decode("utf-8"))
                return config
        except Exception as e:
            self.logger.warning(f"Config BotCrypto no encontrada: {e}")

        # Config por defecto
        return {
            "capital": 1000.0,
            "risk_per_trade": 0.02,
            "tp1_pct": 0.03,
            "tp2_pct": 0.06,
            "stop_loss_pct": 0.02,
            "tp1_size": 0.33,
            "tp2_size": 0.33,
            "rsi_buy": 35,
            "rsi_sell": 65,
        }

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
            text="▶ START",
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
            text="⏹ STOP",
            bg="red",
            fg="white",
            font=("Arial", 10, "bold"),
            width=10,
            command=self._on_stop_all,
        )
        btn_stop.pack(side=tk.LEFT, padx=5)

        # Status
        tk.Label(row1, text="Status:", bg=self.colors["cgcolor"], fg="white").pack(
            side=tk.LEFT, padx=(20, 5)
        )
        self.lbl_status = tk.Label(
            row1,
            text="● STOPPED",
            bg=self.colors["cgcolor"],
            fg="gray",
            font=("Arial", 10, "bold"),
        )
        self.lbl_status.pack(side=tk.LEFT)

        # Capital
        tk.Label(row1, text="Capital:", bg=self.colors["cgcolor"], fg="white").pack(
            side=tk.LEFT, padx=(30, 5)
        )
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

        # Selector de intervalo
        tk.Label(row2, text="Intervalo:", bg=self.colors["cgcolor"], fg="white").pack(
            side=tk.LEFT, padx=5
        )
        self.combo_interval = ttk.Combobox(
            row2, values=["1m", "5m", "15m", "1h"], width=5, state="readonly"
        )
        self.combo_interval.set("5m")
        self.combo_interval.pack(side=tk.LEFT, padx=5)
        self.combo_interval.bind("<<ComboboxSelected>>", self._on_interval_change)

        # Activos
        tk.Label(row2, text="Activos:", bg=self.colors["cgcolor"], fg="white").pack(
            side=tk.LEFT, padx=(20, 5)
        )
        self.lbl_activos = tk.Label(
            row2, text="0", bg=self.colors["cgcolor"], fg="yellow"
        )
        self.lbl_activos.pack(side=tk.LEFT)

        # Trades
        tk.Label(row2, text="Trades:", bg=self.colors["cgcolor"], fg="white").pack(
            side=tk.LEFT, padx=(20, 5)
        )
        self.lbl_trades = tk.Label(
            row2, text="0", bg=self.colors["cgcolor"], fg="yellow"
        )
        self.lbl_trades.pack(side=tk.LEFT)

        # PnL
        tk.Label(row2, text="PnL:", bg=self.colors["cgcolor"], fg="white").pack(
            side=tk.LEFT, padx=(20, 5)
        )
        self.lbl_pnl = tk.Label(
            row2, text="0.00%", bg=self.colors["cgcolor"], fg="white"
        )
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
        self.canvas = tk.Canvas(
            container, bg=self.colors["bgcolor"], highlightthickness=0
        )

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
            activos, found = self.repositorio.select_otros_activos(
                symbol="all", account=self.ACCOUNT
            )

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
        )
        widget.crear_ui()
        widget.frame.grid(row=row, column=col, padx=5, pady=5, sticky="nw")
        self.widgets[symbol] = widget

    # =========================================
    # MANAGERS
    # =========================================
    def _inicializar_managers(self):
        """Inicializa OrderManager y BotManager"""
        try:
            # Binance client
            bb = BB()
            self.spot_client = bb.spot

            # Order Manager
            self.order_manager = OrderManager()

            # Bot Manager (placeholder - se conectará al iniciar)
            # self.bot_manager = BotManager(...)

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

            # Crear streams para cada símbolo
            streams = [f"{s.lower()}@kline_{self.interval}" for s in symbols]

            def on_message(_, msg):
                self._on_ws_message(msg)

            def on_error(_, error):
                self.logger.error(f"WebSocket error: {error}")

            def on_close(_):
                self.logger.info("WebSocket cerrado")

            def on_open(_):
                self.logger.info("WebSocket conectado")

            self.ws_client = SpotWebsocketStreamClient(
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open,
            )

            # Suscribir a los streams
            for stream in streams:
                self.ws_client.subscribe(stream)

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
            if isinstance(msg, dict) and msg.get("e") == "kline":
                kline = msg["k"]
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
            indicators = bot.get_indicators() if hasattr(bot, "get_indicators") else {}
            self.widgets[symbol].update_state(state, indicators)

            # Ejecutar acción si hay
            if action != "HOLD":
                self.logger.info(f"{symbol}: Acción {action}")
                # TODO: Ejecutar orden via bot_manager

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
        """Abre diálogo para agregar nuevo símbolo"""
        # TODO: Implementar diálogo
        self.logger.info("Agregar símbolo")

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

        except Exception as e:
            self.logger.error(f"Error creando bot para {symbol}: {e}")

    def _cargar_historico(self, bot, symbol):
        """Carga datos históricos para el bot"""
        try:
            # Obtener klines históricos
            df = get_klines_info(symbol=symbol, period="30d", interval=self.interval)
            if df is not None and not df.empty:
                bot.df = df
                # TODO: Calcular indicadores
        except Exception as e:
            self.logger.error(f"Error cargando histórico {symbol}: {e}")


class WidgetBotSymbol:
    """
    Widget individual para mostrar información de un símbolo.
    Incluye precio, indicadores, estado y controles.
    """

    def __init__(self, parent, symbol, activo, colors, config, on_start, on_stop, on_chart):
        self.parent = parent
        self.symbol = symbol
        self.activo = activo
        self.colors = colors
        self.config = config
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_chart = on_chart

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
        self.lbl_status_indicator = tk.Label(
            header, text="●", bg="#2a4a5a", fg="gray", font=("Arial", 12)
        )
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
