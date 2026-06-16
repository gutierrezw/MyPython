from Modulos_python import (
    schedule,
    datetime,
    logging,
    os,
    ssl,
    time,
    sys,
    urllib3,
    warnings,
    psutil,
    datetime,
    threading,
    traceback,
    textwrap,
)
from Modulos_Utilitarios import AGENTES_SCHEDULE, delete_file, read_json_tmp, write_json_tmp
from logging.handlers import RotatingFileHandler


# Clase principal para eventos thread & schedule
class ManagerEvents:
    def __init__(self, logger, GlobalHub=None):
        self.threads = {}
        self.jobs = {}
        self.running_flags = {}
        self.thread_params = {}  # Nuevo: guarda parámetros de cada thread
        self.job_params = {}  # Nuevo: guarda parámetros de cada job
        self.DataHub = GlobalHub

        # Asigna Nombre Logging
        self.logger = logging.getLogger(logger)
        self.logger.info("✅ ManagerEvents inicializado correctamente.")

    # ---------------- Threads ----------------
    def register_thread(self, name, target, *args, loop_sleep=0, **kwargs):
        if name in self.threads and self.threads[name].is_alive():
            self.logger.warning(f"🔄 Thread {name} ya estaba activo.")
            return

        # cada thread tiene un flag propio de running
        self.running_flags[name] = True
        self.thread_params[name] = (target, args, kwargs)  # Guarda parámetros

        task_name = name
        counter = 0
        self.DataHub.procesos.append({"thread": {task_name: counter}})

        def wrapper():
            nonlocal counter
            while self.running_flags[name]:
                try:
                    if not AGENTES_SCHEDULE.get(name, {}).get("active", True):
                        if loop_sleep > 0:
                            time.sleep(loop_sleep)
                        continue
                    target(*args, **kwargs)
                    counter += 1
                    self.DataHub.update_self_procesos(proces="thread", tarea=task_name, itera=counter)
                    if loop_sleep > 0:
                        time.sleep(loop_sleep)
                except Exception as e:
                    self.logger.error(f"❌ Error en thread {name}: {e}")
                    break

        t = threading.Thread(target=wrapper, name=name, daemon=True)
        t.start()

        print(f"Start:({task_name})")
        self.threads[name] = t
        self.logger.warning(f"✅ Thread {name} iniciado.")

    def stop_thread(self, name):
        if name in self.threads:
            self.running_flags[name] = False
            self.logger.warning(f"🛑 Stop solicitado para thread {name}.")
        else:
            self.logger.warning(f"⚠️ Thread {name} no registrado.")

    # ---------------- Jobs ----------------
    def register_job(self, name, interval_sec, func, *args, run_now=False, **kwargs):
        job = schedule.every(interval_sec).seconds.do(func, *args, **kwargs).tag(name)
        if run_now:
            job.next_run = schedule.datetime.datetime.now()
        self.job_params[name] = (interval_sec, func, args, kwargs)  # Guarda parámetros

        print(f"{name}")
        self.logger.warning(f"✅ Job {name} registrado cada {interval_sec}s.")

    def stop_job(self, name):
        schedule.clear(name)
        if name in self.job_params:
            del self.job_params[name]
        self.logger.warning(f"🛑 Job {name} cancelado.")

    # ---------------- Scheduler ----------------
    def run_scheduler(self):
        """Se corre en un hilo separado"""

        try:

            def loopSchedule(counter=0):
                while True:
                    schedule.run_pending()
                    time.sleep(1)

                    # actualiza iteración de proceso
                    counter += 1
                    self.DataHub.update_self_procesos(proces="thread", tarea=task_name, itera=counter)

            task_name = f"schedule_pending(all)"
            counter = 0
            self.DataHub.procesos.append({"thread": {task_name: counter}})

            t = threading.Thread(target=loopSchedule, name=task_name, args=(counter,), daemon=True)
            t.start()

            print("Start:({})".format(task_name))
            self.logger.info("✅ Scheduler iniciado.")
        except Exception as e:
            self.logger.error(f"❌ Error al iniciar scheduler: {e}")

    # ---------------- Monitor & Rearmado ----------------
    def monitor_and_restart(self, check_interval=10):
        """
        Monitorea el estado de threads y jobs, y rearma si detecta caída.
        """

        def monitor_loop():
            while True:
                # Verifica threads
                for name, thread in list(self.threads.items()):
                    if not thread.is_alive() and self.running_flags.get(name, False):
                        self.logger.warning(f"🔄 Thread {name} caído. Rearmando...")
                        target, args, kwargs = self.thread_params.get(name, (None, (), {}))
                        if target:
                            self.register_thread(name, target, *args, **kwargs)

                # Verifica jobs (schedules)
                for name, job in list(self.jobs.items()):
                    if job not in schedule.jobs:
                        self.logger.warning(f"🔄 Job {name} caído. Rearmando...")
                        params = self.job_params.get(name)
                        if params:
                            interval_sec, func, args, kwargs = params
                            self.register_job(name, interval_sec, func, *args, **kwargs)

                time.sleep(check_interval)

        t = threading.Thread(target=monitor_loop, name="MonitorRestart", daemon=True)
        t.start()
        self.logger.info("✅ Monitor de threads/jobs iniciado.")

    def stop_all(self):
        for name in list(self.threads.keys()):
            self.stop_thread(name)
        for name in list(self.jobs.keys()):
            self.stop_job(name)

        self.logger.warning("🛑 Todos los threads y jobs detenidos.")

    def restart_all(self):
        for name, thread in list(self.threads.items()):
            if not thread.is_alive():
                target, args, kwargs = self.thread_params.get(name, (None, (), {}))
                if target:
                    self.register_thread(name, target, *args, **kwargs)
        for name, job in list(self.jobs.items()):
            if job not in schedule.jobs:
                params = self.job_params.get(name)
                if params:
                    interval_sec, func, args, kwargs = params
                    self.register_job(name, interval_sec, func, *args, **kwargs)
        self.logger.warning("🔄 Todos los threads y jobs rearmados.")


# Clase principal para eventos after de tkinter
class MangerAfterEvents:
    def __init__(self, AppRoot, logger):
        self.root = AppRoot
        self.after_jobs = {}
        self.app_running = True

        # Asigna Nombre Logging
        self.logger = logging.getLogger(logger)
        self.logger.info("✅ ManagerEvents inicializado correctamente.")

    # ---------------- After -----------------
    def _safe(self, delay_ms, callback, name=None):
        """Programa un after() y lo registra para poder cancelarlo luego."""
        if not self.app_running:
            return None

        if name is None:
            name = f"job_{len(self.after_jobs)}"

        try:
            job_id = self.root.after(delay_ms, lambda: self._run_callback(name, callback))
            self.after_jobs[name] = job_id
            return job_id
        except Exception as e:
            print(f"[after_safe] error creando after(): {e}")
            return None

    def _run_callback(self, name, callback):
        """Ejecuta el callback y lo limpia de la lista si corresponde."""
        if name in self.after_jobs:
            del self.after_jobs[name]
        if self.app_running:
            try:
                callback()
            except Exception as e:
                print(f"[after_safe] error en callback {name}: {e}")

    def _cancel_all(self):
        """Cancela todas las tareas pendientes."""
        self.app_running = False
        for name, job_id in list(self.after_jobs.items()):
            try:
                self.root.after_cancel(job_id)
            except Exception:
                pass
        self.after_jobs.clear()


class Debugging:
    def __init__(
        self,
        log_file="dashmain_",
        max_bytes=10_000_000,
        backup_count=5,
        DisplayConsole=False,
        GlobalHub=None,
    ):
        """
        Inicializa el sistema de logging y manejo de excepciones globales.
        """
        self.log_file = log_file
        self.DisplayConsole = DisplayConsole
        self.loggerName = None
        self.logger = {}
        self.spath = None
        self.DataHub = GlobalHub

        # Variables gráfico consumo CPU y MEMORIA
        self.interval = 1
        self.cpu_data = []
        self.mem_data = []
        self.max_points = 40
        self.display = True
        self.lock = threading.Lock()

        # logging.basicConfig
        self.logger.update({"root": logging.getLogger()})
        self.logger["root"].setLevel(logging.WARNING)
        self.handled_CacheLogger_name()

        # Formato de logs
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(threadName)s - %(message)s")

        # Handler para archivo rotativo
        file_handler = RotatingFileHandler(
            filename=self.loggerName,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        self.logger["root"].addHandler(file_handler)

        # Handler para consola
        if self.DisplayConsole:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger["root"].addHandler(console_handler)

        # Manejo global de excepciones no controladas
        sys.excepthook = self.handle_exception_general
        threading.excepthook = self.handle_exception_threading

        # Suprimir warnings molestos de librerías externas
        warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")
        warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
        warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
        warnings.filterwarnings("ignore", category=FutureWarning)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.logger["root"].warning("✅ Debugging inicializado correctamente.")

        # manager logging
        self.logger.update({"yfinance": logging.getLogger("yfinance")})
        self.logger["yfinance"].setLevel(logging.CRITICAL)

        # manager logging
        self.logger.update({"IBroks_Client": logging.getLogger("IBroks_Client")})
        self.logger["IBroks_Client"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"requests_cache": logging.getLogger("requests_cache")})
        self.logger["requests_cache"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"matplotlib.font_manager": logging.getLogger("matplotlib.font_manager")})
        self.logger["matplotlib.font_manager"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"PIL.PngImagePlugin": logging.getLogger("PIL.PngImagePlugin")})
        self.logger["PIL.PngImagePlugin"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"peewee": logging.getLogger("peewee")})
        self.logger["peewee"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"urllib3.connectionpool": logging.getLogger("urllib3.connectionpool")})
        self.logger["urllib3.connectionpool"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"schedule": logging.getLogger("schedule")})
        self.logger["schedule"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update(
            {"binance.websocket.websocket_client": logging.getLogger("binance.websocket.websocket_client")}
        )
        self.logger["binance.websocket.websocket_client"].setLevel(logging.ERROR)

        # manager logging
        self.logger.update({"binance.api": logging.getLogger("binance.api")})
        self.logger["binance.api"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"ClassChatbot": logging.getLogger("ClassChatbot")})
        self.logger["ClassChatbot"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"ClassMoodeloIA": logging.getLogger("ClassMoodeloIA")})
        self.logger["ClassMoodeloIA"].setLevel(logging.WARNING)

        # manager logging sklearn (captura warnings de cross-validation, etc.)
        logging.captureWarnings(True)
        self.logger.update({"py.warnings": logging.getLogger("py.warnings")})
        self.logger["py.warnings"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"ClassMyOrders": logging.getLogger("ClassMyOrders")})
        self.logger["ClassMyOrders"].setLevel(logging.DEBUG)

        # manager logging
        self.logger.update({"DataFrameCache": logging.getLogger("DataFrameCache")})
        self.logger["DataFrameCache"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"DataFrame": logging.getLogger("DataFrame")})
        self.logger["DataFrame"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"FondosInversion": logging.getLogger("FondosInversion")})
        self.logger["FondosInversion"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"BrowserFCI": logging.getLogger("BrowserFCI")})
        self.logger["BrowserFCI"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"Screener": logging.getLogger("Screener")})
        self.logger["Screener"].setLevel(logging.WARNING)
        self.logger.update({"TradingView": logging.getLogger("TradingView")})
        self.logger["TradingView"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"InstitucionalScore": logging.getLogger("InstitucionalScore")})
        self.logger["InstitucionalScore"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"Mysql": logging.getLogger("Mysql")})
        self.logger["Mysql"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"ClassAgenteIA": logging.getLogger("ClassAgenteIA")})
        self.logger["ClassAgenteIA"].setLevel(logging.WARNING)

        # manager logging BotCrypto (Class_vehiculo.py)
        self.logger.update({"BinanceClient": logging.getLogger("BinanceClient")})
        self.logger["BinanceClient"].setLevel(logging.WARNING)

        self.logger.update({"BinanceSpot": logging.getLogger("BinanceSpot")})
        self.logger["BinanceSpot"].setLevel(logging.WARNING)

        self.logger.update({"BotCryptoUI": logging.getLogger("BotCryptoUI")})
        self.logger["BotCryptoUI"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"Analisis": logging.getLogger("Analisis")})
        self.logger["Analisis"].setLevel(logging.WARNING)
        self.logger.update({"Sentimiento": logging.getLogger("Sentimiento")})
        self.logger["Sentimiento"].setLevel(logging.WARNING)
        self.logger.update({"ApiTracker": logging.getLogger("ApiTracker")})
        self.logger["ApiTracker"].setLevel(logging.WARNING)
        self.logger.update({"YouTubeScanner": logging.getLogger("YouTubeScanner")})
        self.logger["YouTubeScanner"].setLevel(logging.WARNING)

        # manager logging AgentManager domain loggers
        self.logger.update({"Agente.Stock": logging.getLogger("Agente.Stock")})
        self.logger["Agente.Stock"].setLevel(logging.WARNING)
        self.logger.update({"Agente.Crypto": logging.getLogger("Agente.Crypto")})
        self.logger["Agente.Crypto"].setLevel(logging.WARNING)
        self.logger.update({"Agente.IA": logging.getLogger("Agente.IA")})
        self.logger["Agente.IA"].setLevel(logging.WARNING)
        self.logger.update({"Agente.Infra": logging.getLogger("Agente.Infra")})
        self.logger["Agente.Infra"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"GainsCapture": logging.getLogger("GainsCapture")})
        self.logger["GainsCapture"].setLevel(logging.WARNING)
        self.logger.update({"BrowserFCI": logging.getLogger("BrowserFCI")})
        self.logger["BrowserFCI"].setLevel(logging.WARNING)
        self.logger.update({"ClaudeIA": logging.getLogger("ClaudeIA")})
        self.logger["ClaudeIA"].setLevel(logging.WARNING)

        # manager logging
        self.logger.update({"Sentimiento": logging.getLogger("Sentimiento")})
        self.logger["Sentimiento"].setLevel(logging.WARNING)

        # restaurar niveles guardados por el usuario desde el panel Debugging
        self._apply_saved_levels()
        self._apply_saved_agents()

    def _apply_saved_agents(self):
        """Carga agents_config.json y aplica estado active/inactive sobre AGENTES_SCHEDULE."""
        saved = read_json_tmp("agents_config")
        for name, active in saved.items():
            if name in AGENTES_SCHEDULE:
                AGENTES_SCHEDULE[name]["active"] = bool(active)

    def _apply_saved_levels(self):
        """Carga logger_levels.json y aplica los niveles guardados sobre los defaults."""
        saved = read_json_tmp("logger_levels")
        for key, lvl_name in saved.items():
            if key in self.logger:
                level = getattr(logging, lvl_name, None)
                if level is not None:
                    self.logger[key].setLevel(level)

    def handled_CacheLogger_name(self):
        """
        Captura manejo de cache y filename para logger
        alterna entre días pares e impares para creación de archivo log
        """
        now = datetime.now()
        today = int(now.strftime("%d"))

        if today % 2 == 0:
            log_create = self.log_file + "log_old"
            log_delete = self.log_file + "log_even"
        else:
            log_create = self.log_file + "log_even"
            log_delete = self.log_file + "log_old"

        tmp_env = os.environ.get("APPOO_TMP")
        if tmp_env:
            # APPOO_TMP = .../deploy/tmp → logs = .../deploy/logs
            lpath = os.path.normpath(os.path.join(tmp_env, "..", "logs"))
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            lpath = os.path.join(script_dir, "logs")
        os.makedirs(lpath, exist_ok=True)
        self.loggerName = os.path.join(lpath, log_create)
        self.spath = os.environ.get("APPOO_TMP") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp")
        delete_rpath = os.path.join(lpath, log_delete)

        # Elimina log anterior
        delete_file(ruta=delete_rpath, display=False)

        # Elimina logs de gateway
        delete_file(ruta=lpath, patron="gw.*", display=False)

    # Define Handle Exception ---------------------------------------------------------------------------------------------------
    def handle_exception_general(self, exc_type, exc_value, exc_traceback):
        """
        Captura excepciones no controladas y las envía al logger.
        """
        # if issubclass(exc_type, KeyboardInterrupt):
        #    sys.__excepthook__(exc_type, exc_value, exc_traceback)
        #    return

        self.logger["root"].critical(
            textwrap.dedent(
                """
                  ==================================
                  handle_exception_general():
                  -- 
                  ¡Oops! Se ha producido una excepción no manejada
                  ================================== 
                  exc_type     : {type}
                  exc_value    : {value}
                  exc_traceback: {traceback}
                  """.format(
                    type=exc_type,
                    value=exc_value,
                    traceback=traceback.print_tb(exc_traceback),
                )
            )
        )

    def handle_exception_threading(self, args):
        """
        Función personalizada para manejar excepciones en hilos.

        Args:
            args: Un objeto threading.ExceptHookArgs que contiene información
                sobre la excepción.
        """
        self.logger["root"].critical(
            textwrap.dedent(
                """
                  ==================================
                  handle_ehandle_exception_threading():
                  -- 
                  ¡Oops! Se ha producido una excepción no manejada
                  ================================== 
                  exc_type     : {type}
                  exc_value    : {value}
                  exec_thread  : {thread}  
                  """.format(
                    type=args.exc_type.__name__,
                    value=args.exc_value,
                    thread=args.thread.name,
                )
            )
        )

    def show_config(self):
        print("🔍 Configuración actual del logger:")
        # print("Nivel global:", logging.getLevelName(self.logger.level))
        for logg, handler in self.logger.items():
            print(f" - {logg}::nivel {logging.getLevelName(handler.level)}")

    def monitor_system(self, interval=1, task_name="SystemMonitor"):
        """
        Monitorea uso de CPU y memoria en un hilo separado.
        """
        # añade a lista de procesos
        counter = 0
        self.DataHub.procesos.append({"thread": {task_name: counter}})

        last_log = time.time()
        while True:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            with self.lock:
                self.cpu_data.append(cpu)
                self.mem_data.append(mem)

                # loguear cada 10 segundos
                if time.time() - last_log >= 10:
                    self.logger["root"].info(f"📊 CPU: {cpu:.1f}% | RAM: {mem:.1f}%")
                    last_log = time.time()

                # elimina simpre el ultimoa
                if len(self.cpu_data) > self.max_points:
                    self.cpu_data.pop(0)
                    self.mem_data.pop(0)

                time.sleep(interval)

                # actualiza iteración de proceso
                counter += 1
                self.DataHub.update_self_procesos(proces="thread", tarea=task_name, itera=counter)
