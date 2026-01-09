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
)

sys.path.insert(0, "..")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "AppValuations"))
from Modulos_Mysql import RepositorioOportunidadesBuySell, BDsystem, PlanInversion
from valuation_edgar_downloader import BASE_DIR, download_filing
from valuation_xbrl_api import get_zip_files
from Class_customer import DataHub, TickerInfo
from Class_IA_modelos import ModeloOportunidadesSell
from Modulos_Utilitarios import define_FileCache


# Admistrador de Agentes IA
class ClassAgenteIA:
    def __init__(self):

        # Obiene valores de session Stock
        self.vehiculo = "Stock"
        self.positions = []
        self.NotFound = []
        self.PlanInversion = PlanInversion()
        self.sesion = self.PlanInversion.get_sesion_by_vehiculo(self.vehiculo)

        # Asigna Nombre Logging
        self.logger = logging.getLogger("ClassAgenteIA")

    # decorador para limitar ejecuciones
    def wait_rate(intervalo_segundos: int):
        """
        Fábrica de Decoradores: Restringe la ejecución de la función
        a un máximo de una vez por el intervalo de tiempo especificado.

        Args:
            intervalo_segundos (int): Tiempo mínimo de espera entre llamadas (en segundos).
        """

        def decorator(func):
            # 1. Almacenamos la hora de la última ejecución en el objeto de la función
            func.last_run = 0

            @wraps(func)
            def wrapper(*args, **kwargs):
                tiempo_actual = time.time()
                tiempo_transcurrido = tiempo_actual - func.last_run

                # 2. Usamos la variable 'intervalo_segundos' del ámbito externo
                if tiempo_transcurrido < intervalo_segundos:

                    tiempo_restante = intervalo_segundos - tiempo_transcurrido
                    td = timedelta(seconds=int(tiempo_restante))
                    return None

                else:
                    # El tiempo ha transcurrido, ejecutar la función
                    resultado = func(*args, **kwargs)

                    # 3. Actualizar el tiempo de la última ejecución
                    func.last_run = tiempo_actual
                    logger = logging.getLogger("ClassAgenteIA")
                    logger.warning(
                        textwrap.dedent(
                            f"""
                            ==============================================================================================
                            Agente_downloads_filings_EDGAR(): 
                            = 
                            🛑 BLOQUEADO: La función '{func.__name__}' está limitada a 1 llamada cada {intervalo_segundos}s.
                            ==============================================================================================

                            """
                        )
                    )
                    return resultado

            return wrapper

        return decorator

    # Controla si el mensaje debe enviarse a Telegram según reglas:
    def Agente_message_Manager(self, row):
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

        # si pasó todas las reglas → actualiza registro
        self.ultimo_envio[symbol] = {"roi": roi, "time": ahora}
        return True

    # agente para las recomendaciones de ventas ---------------------------------------------------------------------------------
    async def Agente_ManagerSell(self):
        try:

            # Generar un hash identificador para evitar duplicados
            df_sell = self.readCSV(file="csv_datosIA_sell")
            if not df_sell.empty:

                # oportinidades sin filtros presentadas por DataHub.info()
                if not self.activaIA:
                    await self.evaluar_oportunidades(df_sell)

                # oportunidades con fitros IA
                elif self.activaIA:
                    await self.evaluar_oportunidades_con_IA(df_sell, umbral=0.65)
        except (EncodingWarning, Exception) as e:
            print(f"Agente_ManagerSell(): {e}")

    # agente paras las descargas de filings cada 3600 seg
    @wait_rate(3600)
    def Agente_downloads_filings_EDGAR(self):
        try:
            # desacrga la estructura positions
            self.positions = self.PlanInversion.select_inversion(
                tipoin=self.vehiculo, ticket="all"
            )

            counter = 1
            for positio in self.positions:
                ticker = positio.get("ticket")

                # skip not found
                if ticker in self.NotFound:
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
                    self.logger.warning(
                        textwrap.dedent(
                            f"""
                            ==============================================================================================
                            Agente_downloads_filings_EDGAR(): 
                            = 
                            🚨 FILINGS DENEGADO. Posible deslistado del ticker: {ticker}
                            ==============================================================================================

                            """
                        )
                    )

                elif found:
                    # controla que no haga mas de 2 downloads en EDGAR
                    if counter > 2:
                        return None
        except Exception as e:
            print(f"Angente_downloads_filings_EDGAR(): {e}")


# Admistrador de mensajeria Telegram
class Telegram:
    def __init__(self):
        self.MostrarOpcionMenu_enTelegram = "menu"
        self.SentMessage = []
        self.DeleteMessageHash = []
        self.simulation = True

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
            self.logger.warning(
                textwrap.dedent(
                    f"""
                  ==============================================================================================
                  handle_segurity_message(): 
                  = 
                  🚨 ACCESO DENEGADO. Nuevo chat_id para autorizar: {chat_id} | Nombre: {nombre_usuario}
                  ==============================================================================================

                  """
                )
            )

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
                    InlineKeyboardButton("⬇️ Sell", callback_data="menu_sell"),
                    InlineKeyboardButton("⬆️ Buy", callback_data="menu_buy"),
                ],
                [
                    InlineKeyboardButton(
                        "🟢🔴 Resumen Orders", callback_data="OrdersExec"
                    ),
                    InlineKeyboardButton("🔄 Reconnect", callback_data="menu_reconnet"),
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
                # Usar run_polling que maneja todo el ciclo de vida
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                loop.run_until_complete(
                    self.telegram_app.run_polling(
                        allowed_updates=["message", "callback_query"],
                        drop_pending_updates=True,
                    )
                )
            except Exception as e:
                print(f"polling_callbackTelegram() error: {e}")
            finally:
                try:
                    loop.close()
                except:
                    pass

        try:
            # activa mensajería Telegram
            if not self.estadoTelegram:
                self.estadoTelegram = True

                # Build the async Application
                self.telegram_app = ApplicationBuilder().token(self.TOKEN).build()

                # 🔑 Registrar el manejador para /menu
                self.telegram_app.add_handler(CommandHandler("menu", self.handle_menu))

                # 🔑 Registrar el manejador para /start
                self.telegram_app.add_handler(
                    CommandHandler("start", self.handle_segurity_message)
                )

                # 🔑 Registrar el manejador para CUALQUIER texto (excluyendo comandos ya manejados)
                self.telegram_app.add_handler(
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.handle_segurity_message
                    )
                )

                # 🔑 Registrar el manejador para /respuestas
                self.telegram_app.add_handler(
                    CallbackQueryHandler(self.handle_callback)
                )

                # Inicializar bot solo para enviar mensajes iniciales
                await self.telegram_app.initialize()
                self.bot = self.telegram_app.bot

                # Send welcome message and previous opportunities
                await self.send_Telegram(
                    f"🏁 Bot interno iniciado session: {datetime.now()}"
                )
                await self.handle_menu()

                # Cerrar inicialización temporal para que run_polling lo maneje
                await self.telegram_app.shutdown()

                # inicia hilo para polling de mensajes
                task_name = f"polling_callbackTelegram(On)"
                DataHub.procesos.append({"thread": {task_name: 1}})
                DataHub.manager_events.register_thread(
                    name=task_name,
                    target=polling_callbackTelegram,
                )

                print(f"Start: (toggle_telegram(On))")
        except (EncodingWarning, Exception) as e:
            print(f"toggle_telegram(): {e}")

    def _activar_telegram(self):
        self.exec_modulo_async(self.toggle_telegram())

    # envio de mensaje a Telegram
    async def send_Telegram(self, texto, hash_id=None, reply_markup=None):
        try:
            # if para otros mensajes con reply_markup
            for CHAT_ID in self.userAuth:
                if reply_markup is not None:
                    sent_message = await self.bot.send_message(
                        chat_id=CHAT_ID,
                        text=texto,
                        reply_markup=reply_markup,
                        parse_mode="Markdown",
                    )
                    await self._save_message(sent_message, CHAT_ID)
                    return

                # si hash_id no es proporcionado, envía mensaje simple
                elif hash_id is None:
                    sent_message = await self.bot.send_message(
                        chat_id=CHAT_ID, text=texto, parse_mode="Markdown"
                    )
                    await self._save_message(sent_message, CHAT_ID)
                    return

                # si hash_id es proporcionado, crea botones de aprobación/rechazo
                elif hash_id is not None:
                    botones = [
                        [
                            InlineKeyboardButton(
                                "✅ Aprobar", callback_data=f"aprobar|{hash_id}"
                            ),
                            InlineKeyboardButton(
                                "❌ Rechazar", callback_data=f"rechazar|{hash_id}"
                            ),
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(botones)
                    sent_message = await self.bot.send_message(
                        chat_id=CHAT_ID,
                        text=texto,
                        reply_markup=reply_markup,
                        parse_mode="Markdown",
                    )
                    await self._save_message(sent_message, CHAT_ID, hash_id=hash_id)
                    return
        except Exception as e:
            print(f"send_Telegram(): Error: {e}")

    def put_order_stockTelegram(self, op, ix):
        try:
            # extrea información de la oportunidad
            detalle = json.loads(op[ix.index("json_detalle")])
            symbol = op[ix.index("symbol")]
            account = op[ix.index("account")]
            vehiculo = op[ix.index("vehiculo")]
            hash_id = op[ix.index("hash_id")]
            idd = op[ix.index("conid")]
            last = op[ix.index("mrkprice")]
            Stock = TickerInfo(account=account, vehiculo=vehiculo)

            # crea instancia de MyOrders para colocar orden
            qty, tip, tim = Stock.params_order(vehiculo=vehiculo, elementos=0)

            opt, qty = "SELL", detalle.get("cantidad_sell")
            PriceOportunidad = detalle.get("price_market")
            prc = PriceOportunidad if PriceOportunidad > last else last

            # crea la orden en formato diccionario
            order = Stock.format_orden(vehiculo, symbol, idd, tip, prc, opt, tim, qty)

            trama = {
                "account": account,
                "vehiculo": vehiculo,
                "symbol": symbol,
                "pedido": order,
                "hash_id_Op": hash_id,
            }

            # encola la orden para ser procesada por ManagerOrderQueue
            response = DataHub.QremoteOrder[vehiculo]._request(trama)
            return response, symbol
        except Exception as e:
            print(f"put_order_stockTelegram(): Error: {e}")

    # enlace con TickerInfo() para colocar orders
    def put_order_aprovate_telegram(self, hash_id):
        try:
            values, symbol = {}, None

            # recupera info() de Oportunidad sell
            oportunidad, ix = self.RepositorioOportunidades.obtener_id_por_hash(
                hash_id=hash_id
            )

            if not oportunidad:
                return {}, None

            elif oportunidad[ix.index("vehiculo")] == "Stock":
                values, symbol = self.put_order_stockTelegram(oportunidad, ix)

            elif oportunidad[ix.index("vehiculo")] == "Crypto":
                pass

            # marca oportunidad como aprobada si la orden fue aceptada
            if values.get("status") in ("Submitted", "PreSubmitted", "FILLED"):
                self.RepositorioOportunidades.marcar_oportunidad(
                    hash_id,
                    recomendado=1,
                    estado="ejecutada",
                    razon="Aprobada desde Telegram (IA)",
                )

            return values, symbol
        except Exception as e:
            print(f"put_order_aprovate_telegram(): Error: {e}")

    # Maneja los callbacks de los botones de aprobación/rechazo
    async def handle_callback(self, update, context):
        try:

            # opciones de menu seleccionado
            query = update.callback_query
            await query.answer()

            accion, *args = query.data.split("|")

            # solicita put Order & wait response de ManagerOrderQueue
            if accion == "aprobar":
                response, symbol = self.put_order_aprovate_telegram(hash_id=args[0])
                if response:
                    # message = f"✅ Oportunidad procesada :{response['status']}\n"
                    message = (
                        f"✅ Oportunidad procesada :{"pendinete response['status']"}\n"
                    )
                    message += f"Symbol {symbol}: @price {round(0, 4)}"
                if not response:
                    message = f"⚠️ Error al colocar la orden. {symbol}"

                await query.edit_message_text(message)

            elif accion == "rechazar":
                self.RepositorioOportunidades.marcar_oportunidad(
                    args[0],
                    recomendo=-1,
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

            elif accion == "menu_reconnect":
                await query.edit_message_text(
                    "⚙️ Ajustes: próximamente más opciones.", parse_mode="Markdown"
                )

            elif accion == "OrdersExec":
                self.MostrarOpcionMenu_enTelegram = "ListOrder"

                # se pasa el chat que solicitó la lista (opcional)
                await self.list_orders_exec(chat_id=update.effective_chat.id)

        except Exception as e:
            print(f"handle_callback(): Error: {e}")

    # delete message puntual
    async def _delete_message_hash(self, message):

        FileMessage = define_FileCache(name="telegram_message_ids.json")
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
                        await self.bot.delete_message(
                            chat_id=data.get("chat_id"),
                            message_id=data.get("message_id"),
                        )
                except (json.JSONDecodeError, BadRequest):
                    continue

    # Path to JSON file for storing message IDs
    async def _save_message(self, sent_message, CHAT_ID, hash_id=None):
        try:

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
        ClassAgenteIA.__init__(self)  # Inicializa los atributos de AgenteIA
        Telegram.__init__(self)  # Inicializa los atributos de Telegram

        self.bgcolor = "#252526"
        self.fgcolor = "white"
        self.title("Asistente de Inversión 💬")
        self.geometry("600x700+1325+320")
        self.configure(bg="#1e1e1e")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.90)  # transparencia
        self.overrideredirect(True)  # sin bordes ni título
        self.ultimo_envio = {}  # para controlar envíos repetidos

        # Asigna Nombre Logging
        self.logger = logging.getLogger("ClassChatbot")

        # Accesos MySql ----------------------------------------------------------------------------------------------
        self.RepositorioOportunidades = RepositorioOportunidadesBuySell()
        self.IAsell = ModeloOportunidadesSell()
        self.modelo_name = self.IAsell.modelo_name

        self.bot = None
        self.MessageTelegram = None
        self.counter = 0
        self.sell_enviados = {}

        self.iconos = tk.Frame(self, bg=self.bgcolor)
        self.chat = tk.Frame(self, bg=self.bgcolor)
        self.iconos.pack(side=tk.LEFT, expand=True)
        self.chat.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.bind("<FocusOut>", self._al_perder_foco)
        self.on_minimizar = on_minimizar

        # Activa/desactiva News--------------------------------------------------------------------------------------
        Imagen_tk = BDsystem.select_image(idd=333, size=(32, 32))
        self.BNews = tk.Button(
            self.iconos,
            image=Imagen_tk,
            bg=self.bgcolor,
            relief=tk.FLAT,
            command=self.ver_noticias,
        )
        self.BNews.imagen = Imagen_tk

        # Activa/desactiva IA---------------------------------------------------------------------------------------
        Imagen_tk = BDsystem.select_image(idd=334, size=(32, 32))
        self.IA = tk.Button(
            self.iconos, image=Imagen_tk, bg=self.bgcolor, relief=tk.FLAT
        )
        self.IA.imagen = Imagen_tk

        # define area de Chat ---------------------------------------------------------------------------------------
        self.area_mensaje = scrolledtext.ScrolledText(
            self.chat,
            wrap=tk.WORD,
            bg=self.bgcolor,
            fg=self.fgcolor,
            font=("Segoe UI", 10),
        )

        self.area_mensaje.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        self.area_mensaje.insert(tk.END, "🤖 Asistente: ¿En qué puedo ayudarte hoy?\n")
        self.area_mensaje.configure(state="disabled")

        self.entrada = tk.Entry(
            self.chat,
            font=("Segoe UI", 10),
            bg="#333",
            fg="white",
            insertbackground="white",
        )

        self.entrada.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.entrada.bind("<Return>", self._enviar)

        self.BNews.pack(side=tk.TOP)
        self.IA.pack(side=tk.TOP)

        # variables de trabajo
        self.estadoTelegram = False
        self.estadoOportunidades = True
        self.telegram_app = None
        self.threadCall = None
        self.activaIA = True

        # activa Telegram
        self._activar_telegram()

    def _enviar(self, event=None):
        texto = self.entrada.get().strip()
        if texto:
            self._agregar_mensaje(f"👤 Tú: {texto}")
            respuesta = self._procesar_mensaje(texto)
            self._agregar_mensaje(f"🤖 Asistente: {respuesta}")
            self.entrada.delete(0, tk.END)

    def _agregar_mensaje(self, mensaje):
        self.area_mensaje.configure(state="normal")
        self.area_mensaje.insert(tk.END, mensaje + "\n")
        self.area_mensaje.configure(state="disabled")
        self.area_mensaje.yview(tk.END)

    def _procesar_mensaje(self, texto):
        if "ADA" in texto.upper():
            return "📈 ADAUSDT está dando señal de entrada."
        return "Estoy analizando..."

    def ver_noticias(self):
        mensaje = "📰 Últimas noticias relacionadas con tu cartera..."
        self.enviar_mensaje(mensaje)

    def ver_consejos(self):
        mensaje = (
            "💡 Consejo de hoy: Rebalancear tu cartera puede mejorar tu rendimiento."
        )
        self.enviar_mensaje(mensaje)

        # muestra botón flotante

    def _al_perder_foco(self, event=None):
        self.withdraw()
        if self.on_minimizar:
            self.on_minimizar()

        # start agentes IA -------------------------------------------------------------------------------------------

    # read CSV : Oportunity
    @staticmethod
    def readCSV(file=None):
        try:
            vacio = pd.DataFrame()
            path = define_FileCache(name=f"{file}.CSV")

            # look read CSV sell
            with DataHub.lockCsvAi:
                df = pd.read_csv(
                    path, header=0, sep=",", encoding="utf-8", index_col=False
                )
            if df.empty:
                return vacio

            df.columns = df.columns.str.strip()
            df.reset_index(drop=True, inplace=True)
            df["Opcion"] = df["Opcion"].astype(str).str.strip()
            df = df.dropna(how="all", axis=1)

            # Filtrar recomendaciones válidas
            df_recom = df[
                (df["%Roi"] >= DataHub.MaxRoi) & (df["Profit"] >= DataHub.MinProfit)
            ]
            return df_recom if not df_recom.empty else vacio
        except (EmptyDataError, FileNotFoundError):
            # print(f"readCSV(): El archivo {path} está vacío.")
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
        except EncodingWarning as e:
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

    # Inicio del chatbot
    def run(self):
        def agentesIA():
            try:

                while True:
                    # Agente for Sell
                    self.exec_modulo_async(self.Agente_ManagerSell())

                    # Agente for Donloads filings
                    self.Agente_downloads_filings_EDGAR()

                    time.sleep(15)
                    self.counter += 1

                    DataHub.update_self_procesos(
                        proces="thread", tarea=task_name, itera=self.counter
                    )
            except EncodingWarning as e:
                print(f"agentesIA(): {e}")

        try:
            task_name = f"run_agentesIA(all)"
            DataHub.procesos.append({"thread": {task_name: 1}})
            DataHub.manager_events.register_thread(
                name=task_name,
                target=agentesIA,
            )
        except (Exception, EncodingWarning) as error:
            print(f"agentesIA(): {error}")

    # gestiona mensajes repetidos o sin mejora
    def message_format(self, row, modo=None):
        try:

            mensaje = []
            symbol = row["Symbol"]
            option = row["Opcion"]
            price = f"{row['PriceMarket']:>12.4f}".strip()

            if modo == "system":
                mensaje = f"🔴 *System Sell: ${symbol} ({option};  @price: {price})*\n"
                mensaje += "```\n"

            elif modo == "ia":
                confianza = row["confianza"]
                mensaje = f"🔴 *IA Sell: ${symbol} ({option};  @price: {price})*\n"
                mensaje += "```\n"

            mensaje += f"{'Métrica':<15} {'Valor':>12}\n"
            mensaje += f"{'-' * 45}\n"
            mensaje += f"{'Profit'         :<15} {row['Profit']:>12.2f}\n"
            mensaje += f"{'ROI (%)'        :<15} {row['%Roi'] * 100:>12.2f}\n"
            mensaje += f"{'for sell'       :<15} {row['CantidadSell']:>12.1f} de {row['Disponible']:>12.1f}\n"
            mensaje += f"{'CostoAcum'      :<15} {row['CostoCum']:>12.2f}\n"
            mensaje += f"{'Prec. posVenta' :<15} {row['PosAvgCost']:>12.4f}\n"
            mensaje += f"{'Pos. posVenta'  :<15} {row['PosPosition']:>12.4f}\n"
            mensaje += f"{'CostoB posVenta':<15} {row['PosCostobase']:>12.2f}\n"

            if modo == "ia":
                mensaje += f"{'-' * 45}\n"
                mensaje += f"{'Confianza IA'   :<15} {confianza:>12.1%}\n"

            mensaje += "```"

            return mensaje
        except (EncodingWarning, Exception) as e:
            print(f"message_format(): {e}")

    # controla el envío de mensajes de oportunidades
    async def opportunity_handler_message(self, hash_id, row, origen="system"):
        try:

            # filtra mensajes repetidos o sin mejora
            if not self.Agente_message_Manager(row):
                return

            # Marcar como enviado y da formato al mensaje
            self.sell_enviados.update({hash_id: row})
            message = self.message_format(row, modo=origen)

            # send a Telegram si esta activo
            if self.estadoTelegram:
                await self.send_Telegram(message, hash_id)

            # send al chat si esta activo
            if self.estadoOportunidades:
                self._agregar_mensaje(message)
        except (EncodingWarning, Exception) as e:
            print(f"opportunity_handler_message(): {e}")

    # maneja las oportunidades hash_id e insert de oportunidades en función del origen
    async def oportunity_handler(self, row, origen="system"):
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
                    await self.opportunity_handler_message(
                        hash_id=hash_id, row=row, origen=origen
                    )
        except (EncodingWarning, Exception) as e:
            print(f"opportunity_handler(): {e}")

    # Evalua oportunidades entrega por el sistema
    async def evaluar_oportunidades(self, df_sell):
        try:

            for _, row in df_sell.iterrows():
                await self.oportunity_handler(row=row, origen="system")

        except (EncodingWarning, Exception) as e:
            print(f"evaluar_oportunidades(): {e}")

    # Obtener oportunidades desde modelo IA
    async def evaluar_oportunidades_con_IA(self, df_sell, umbral=0.65):
        # selecciona de df_sell las fila  aprobadas
        def get_sell_aprobadas(df_en=None, df_ap=None, umbral=None):

            df_ou = pd.DataFrame()
            for _, row in df_en.iterrows():
                for _, apro in df_ap.iterrows():
                    if row["hash_id"] == apro["hash_id"]:

                        if apro["confianza"] >= umbral:
                            df_ou = pd.concat(
                                [df_ou, pd.DataFrame([row])], ignore_index=True
                            )
                            df_ou["Comentarios"] = (
                                f"Oportunity sent by Sell IA Model, confianza {apro['confianza']}"
                            )
                            df_ou["confianza"] = apro["confianza"]
                            break
            return df_ou

        try:
            # modelo para presentar Oportunidades
            self.IAsell.load_modelo(self.modelo_name)

            # agreca columna hash_id, para luego aparear
            df_sell.insert(0, "hash_id", " ")
            for _, row in df_sell.iterrows():
                hash_id = self.RepositorioOportunidades.generar_hash_id(
                    row.get("account"),
                    row.get("Symbol"),
                    row.get("Opcion"),
                    row.get("Fecha"),
                    "sell",
                    "gain",
                    row.get("Recomendado"),
                )
                row["hash_id"] = hash_id

            # Deja names columns como estan den tabla de oportunidades
            df_in = df_sell.copy()
            df_in = df_in.rename(columns=DataHub.SellCsvJsonDcolumnas)

            # Aplicar predicción IA
            df = self.IAsell.aplanar_datos_tecnicos(df_in)
            resultado = self.IAsell.predecir_modelo(df)

            # take the sales approved by the AI model.
            aprobadas = get_sell_aprobadas(
                df_en=df_sell, df_ap=resultado, umbral=umbral
            )

            # recorre aprobadas para actualzzar en Oportunidades
            for _, row in aprobadas.iterrows():
                await self.oportunity_handler(row=row, origen="ia")
        except (EncodingWarning, Exception) as e:
            print(f"evaluar_oportunidades_con_IA(): {e}")

            # Filtrar por confianza mínima
            # aprobadas = resultado[resultado["confianza"] >= umbral].copy()

    # obtenen muestra para entrenamiento del modelo de sell
    def obtener_dataframe_entrenamiento_IA(self):
        """
        Extrae las oportunidades con acción tomada (aprobada o rechazada)
        y devuelve un DataFrame con todos los campos necesarios para entrenamiento IA.
        """
        try:
            oportunidades, ix = self.RepositorioOportunidades.obtener_por_tipo(
                tipo="sell"
            )
            registros = []
            for op in oportunidades:

                # saltar pendientes  los no recomendados
                if op[ix.index("recomendado")] not in [1, -1]:
                    continue

                detalle = json.loads(op[ix.index("json_detalle")])
                indicadores = detalle.get("indicadores", {})

                fila = {
                    "symbol": op[ix.index("symbol")],
                    "recomendado": op[ix.index("recomendado")],
                    "profit": detalle.get("profit"),
                    "roi": detalle.get("roi"),
                    "rsi": indicadores.get("rsi"),
                    "macd": indicadores.get("macd"),
                    "Close": indicadores.get("precio_calculo"),
                    "EMA020": indicadores.get("ema(20,50,100,200)", {}).get("EMA020"),
                    "EMA050": indicadores.get("ema(20,50,100,200)", {}).get("EMA050"),
                    "EMA100": indicadores.get("ema(20,50,100,200)", {}).get("EMA100"),
                    "EMA200": indicadores.get("ema(20,50,100,200)", {}).get("EMA200"),
                    "EMA009": indicadores.get("ema(09,21,055,144)", {}).get("EMA009"),
                    "EMA021": indicadores.get("ema(09,21,055,144)", {}).get("EMA021"),
                    "EMA055": indicadores.get("ema(09,21,055,144)", {}).get("EMA055"),
                    "EMA144": indicadores.get("ema(09,21,055,144)", {}).get("EMA144"),
                    "fibo_longico": indicadores.get("retroceso_fibonacci", {}).get(
                        "longico"
                    ),
                    "fibo_alcista": indicadores.get("retroceso_fibonacci", {}).get(
                        "tendencia alcista"
                    ),
                    "fibo_bajista": indicadores.get("retroceso_fibonacci", {}).get(
                        "tendencia_bajista"
                    ),
                }
                registros.append(fila)

            df = pd.DataFrame(registros)
            return df
        except (EncodingWarning, Exception) as e:
            print(f"obtener_dataframe_entrenamiento_IA(): {e}")

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
                        "status": trader[ix.index("status")],
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
            message += f"{'timestamp':<14} {'symbol':>7} {'side':>5} {'quantity':>7} {'price':>7} {'status':>5}\n"
            message += f"{'-' * 55}\n"
            message += "\n".join(lines)
            message += "```"

            await self.send_Telegram(message, None)
        except Exception as e:
            print(f"list_orders_exec(): {e}")


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

    except (Exception, EncodingWarning) as error:
        print(f"AsistenteChatbot(): {error}")


def app():
    master = tk.Tk()
    master.withdraw()
    AsistenteChatbot(root=master)
    master.mainloop()


if __name__ == "__main__":
    app()
