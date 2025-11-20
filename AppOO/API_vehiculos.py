# iteractive Broker's
from Class_Ibrks import *
from clientportal import *

# binance API's
from binance.api import ClientError
from binance.spot import Spot

# binance Websocket
from binance.websocket.spot.websocket_api import SpotWebsocketAPIClient
from binance.websocket.spot.websocket_stream import SpotWebsocketStreamClient

# modulos propios DashMain
from Modulos_python import (
    sys,
    urllib,
    requests,
    json,
    functools,
    time,
    serialization,
    b64encode,
    webbrowser,
    ssl,
)
from Modulos_Mysql import BDsystem


# --- Binance Exchange ---------------------------------------------------------------------------------------------
class BB:
    def __init__(self, api_key=None, api_secret=None, idcuenta=None):

        # datos de session Crypto
        sesion = BDsystem.select_sesion("select", vehiculo="Crypto")

        # RSA Keys
        self.API_KEY = sesion["userapi"].decode("utf-8")
        self.private_key = sesion["userpass"]

        # self.private_key = sesion['userpass'].decode('utf-8')
        self.spot = MySpot(api_key=self.API_KEY, private_key=self.private_key)

    # firma de mensajes
    def signature_message(self, tipo="b64", REQUEST=None):

        # Set up the request parameters  y auth_request
        def ed25519(a_key, p_key, p_params=None):

            # Sign the request
            p_params["timestamp"] = int(time.time() * 1000)
            p_params["apiKey"] = a_key

            payload = "&".join(
                [f"{param}={value}" for param, value in sorted(p_params.items())]
            )
            signature = b64encode(p_key.sign(payload.encode("utf-8")))
            p_params["signature"] = signature.decode("utf-8")

            return p_params

        try:
            # -- WebSocket_v3_SP
            api_key = self.API_KEY
            private_key = serialization.load_pem_private_key(
                data=self.private_key, password=None
            )

            # Sign request
            if tipo == "b64":
                s_params = ed25519(api_key, private_key, p_params=REQUEST)
                return s_params

        except Exception as e:
            print("signature_message(): {}".format(e))

    try:
        pass
    except Exception as e:
        print("BB(): {}".format(e))


# Decorador para manejar excepciones en métodos de Binance API.
def handle_binance_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):

        logger = logging.getLogger("binance.api")
        try:
            # Ejecuta el método original
            return func(*args, **kwargs)
        except ClientError as e:
            logger.error(
                textwrap.dedent(
                    f"""
                  =======================================
                  handle_binance_exceptions(ClientError): 
                  =======================================  
                  Code   : {getattr(e, "error_code", None)}
                  status : {getattr(e, "status_error", None)}
                  message: {e, "error_message", str(e)}
                  func   : {func}
                  args   : {args}
                  kwargs : {kwargs}
                  """
                )
            )
        except ConnectionError as e:
            logger.error(
                textwrap.dedent(
                    f"""
                  ==============================================================
                  handle_binance_exceptions(ConnectionError): 
                  Requests: No hay conexión a internet. Reintentando en 5 seg...
                  ==============================================================  
                  message: {e}
                  func   : {func}
                  args   : {args}
                  kwargs : {kwargs}
                  """
                )
            )
        except Exception as e:
            logger.error(
                textwrap.dedent(
                    f"""
                  =============================
                  handle_binance_exceptions(): 
                  =============================  
                  func: {func}
                  args: {args}
                  kwargs: {kwargs}
                  Code   : {getattr(e, "error_code", None)}
                  status : {getattr(e, "status_error", None)}
                  message: {e, "error_message", str(e)}
                """
                )
            )

        return None  # Devuelve None si hay un error

    return wrapper


# superClass para Cliente Spot
class MySpot(Spot):
    def __init__(self, api_key=None, api_secret=None, **kwargs):
        if "base_url" not in kwargs:
            kwargs["base_url"] = "https://api.binance.com"
        super().__init__(
            api_key,
            api_secret,
            base_url="https://api.binance.com",
            timeout=10,
        )

        # obtienen ApiKey y ApiSecret de la sesión
        self.sesion = BDsystem.select_sesion("select", vehiculo="Crypto")
        self.API_KEY = self.sesion["userapi"].decode("utf-8")
        self.private_key = self.sesion["userpass"]

    # firma de mensajes class MySpot
    def signature_spot_message(self, tipo="b64", REQUEST=None):

        # Set up the request parameters  y auth_request
        def ed25519(a_key, p_key, p_params=None):

            # Sign the request
            p_params["timestamp"] = int(time.time() * 1000)
            # p_params['apiKey'] = a_key

            payload = "&".join(
                [f"{param}={value}" for param, value in p_params.items()]
            )
            signature = b64encode(p_key.sign(payload.encode("utf-8")))
            p_params["signature"] = signature.decode("utf-8")

            return p_params

        try:
            # -- WebSocket_v3_SP
            private_key = serialization.load_pem_private_key(
                data=self.private_key, password=None
            )

            # Sign request
            if tipo == "b64":
                s_params = ed25519(self.api_key, private_key, p_params=REQUEST)
                return s_params

        except Exception as e:
            print("signature_spot_message(): {}".format(e))

    @staticmethod
    def check_binance_connection():
        try:
            url_path = "https://api.binance.com/api/v3/ping"
            response = requests.get(url_path, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            print("check_binance_connection():".format(e))
            return False

    # ajuste del colateral como forma de pago flexible
    @handle_binance_exceptions
    def get_flexible_adjust_ltv(
        self,
        loanCoin="USDT",
        collateralCoin=None,
        adjustType="ADDITIONAL",
        amount=0.001,
    ):
        """
        Ajusta el LTV de un préstamo flexible en Binance.
        """
        url_path = "https://api.binance.com/sapi/v2/loan/flexible/adjust/ltv"

        xparams = {
            "loanCoin": loanCoin,
            "collateralCoin": collateralCoin,
            "direction": adjustType,
            "adjustmentAmount": amount,
            "timestamp": int(time.time() * 1000),
        }

        try:
            params = self.signature_spot_message(REQUEST=xparams)
            headers = {"X-MBX-APIKEY": self.api_key}
            response = requests.post(url_path, params=params, headers=headers)

            return response.json() if response else None
        except (ClientError, requests.exceptions.RequestException) as e:
            print("[get_flexible_adjust_ltv()]: {}".format(e))

    # repay de préstamo flexible
    @handle_binance_exceptions
    def get_flexible_loan_repay(
        self, loanCoin="USDT", collateralCoin=None, amount=0.001
    ):
        """
        Reembolsa un préstamo flexible en Binance.
        """
        url_path = "https://api.binance.com/sapi/v2/loan/flexible/repay"

        xparams = {
            "loanCoin": loanCoin,
            "collateralCoin": collateralCoin,
            "repayAmount": amount,
            "timestamp": int(time.time() * 1000),
        }

        try:
            params = self.signature_spot_message(REQUEST=xparams)
            headers = {"X-MBX-APIKEY": self.api_key}
            response = requests.post(url_path, params=params, headers=headers)

            return response.json() if response else None
        except (ClientError, requests.exceptions.RequestException) as e:
            print("[get_flexible_adjust_ltv()]: {}".format(e))

    # extracción de información del intercambio para los symbols
    def get_exchange_info(self, symbol=list):
        """Obtiene información del intercambio de Binance."""
        try:
            response = self.exchange_info(symbol=symbol)
            if response:
                for s in response["symbols"]:
                    if s["symbol"] == symbol:
                        for filtro in s["filters"]:
                            if filtro["filterType"] == "LOT_SIZE":
                                min_qty = float(filtro["minQty"])
                                step_size = float(filtro["stepSize"])
                                break
                return {symbol: {"minQty": min_qty, "stepSize": step_size}}
        except (ClientError, requests.exceptions.RequestException) as e:
            print("[get_exchange_info()]: {}".format(e))

    # from binance.spot._crypto_loan import flexible_loan_ongoing_orders
    @handle_binance_exceptions
    def get_flexible_loan_ongoing_orders(self, **kwargs):
        """Borrow - Get Flexible Loan Ongoing Orders (USER_DATA)

        Weight(IP): 300
        GET /sapi/v1/loan/flexible/ongoing/orders
        https://binance-docs.github.io/apidocs/spot/en/#borrow-get-flexible-loan-ongoing-orders-user_data

        Keyword Args:
            loanCoin (str, optional): Coin loaned
            collateralCoin (str, optional): Coin used as collateral
            current (int, optional): Current querying page. Start from 1. Default:1
            limit (int, optional): Default 500; max 1000.
            recvWindow (int, optional): The value cannot be greater than 60000."""
        try:
            url_path = "/sapi/v2/loan/flexible/ongoing/orders"
            kwargs.setdefault("recvWindow", 8000)
            return self.sign_request("GET", url_path, {**kwargs})

        except (ClientError, requests.exceptions.RequestException) as e:
            print("[get_flexible_loan_ongoing_orders()]: {}".format(e))

    @handle_binance_exceptions
    def get_c2c_trade_history(
        self, tradeType=None, startTimestamp=None, endTimestamp=None, rows=100
    ):
        response: any = self.c2c_trade_history(
            tradeType=tradeType,
            startTimestamp=startTimestamp,
            endTimestamp=endTimestamp,
            rows=rows,
        )
        return response

    @handle_binance_exceptions
    def Myget_flexible_product_position(self, current=1, size=100, recvWindow=5000):

        response = {}
        response = self.get_flexible_product_position(
            current=current, size=size, recvWindow=recvWindow
        )
        return response

    @handle_binance_exceptions
    def get_redeem_flexible_product(
        self, productId: str, amount: float, recvWindow=10000
    ):
        response = self.redeem_flexible_product(
            productId=productId, amount=amount, recvWindow=recvWindow
        )
        return response

    @handle_binance_exceptions
    def Myget_flexible_redemption_record(self, current=1, size=100):
        response = self.get_flexible_redemption_record(current=current, size=size)
        return response

    @handle_binance_exceptions
    def Myget_open_orders(self):
        response = self.get_open_orders()
        return response

    @handle_binance_exceptions
    def get_new_order(
        self,
        symbol=None,
        side=None,
        type=None,
        price=None,
        quantity=None,
        timeInForce=None,
    ):
        response = self.new_order(
            symbol=symbol,
            side=side,
            type=type,
            price=price,
            quantity=quantity,
            timeInForce=timeInForce,
        )
        return response

    @handle_binance_exceptions
    def get_cancel_order(self, symbol: str, orderId: int):
        response = self.cancel_order(symbol, orderId)
        return response

    @handle_binance_exceptions
    def get_my_trades(self, ticket: str, limit: int, startTime: int, endTime: int):
        response = self.my_trades(
            ticket, limit=limit, startTime=startTime, endTime=endTime
        )
        return response

    @handle_binance_exceptions
    def account_spot(self, **kwargs):
        """Account information request
        GET /api/v3/account
        """
        try:
            url_path = "/api/v3/account"
            return self.sign_request("GET", url_path, {**kwargs})

        except (ClientError, requests.exceptions.RequestException) as e:
            print(f"account_spot(): {e}")

    # Llama al método para obtener el resumen de la cuenta de margen
    @handle_binance_exceptions
    def get_account_margin(self, **kwargs):
        """
        Llama al método para obtener el resumen de la cuenta de margen."""
        try:
            response = self.margin_account()
            return response
        except (ClientError, requests.exceptions.Request) as e:
            print(f"get_account_margin(): {e}")


# superClass para Client Websocket Binance
class WebsocketBinanceApiClient(SpotWebsocketAPIClient):
    def __init__(self, assets=None, mensaje_callback=None, stream_url=None):
        super().__init__(
            stream_url=stream_url,
            on_message=mensaje_callback,
            on_error=self.on_error,
            on_close=self.on_close,
        )

        self.BClient = BB()
        self.stop_threads = True
        self.thread = None
        self.counter = 0

    @staticmethod
    def on_close(reason):
        # print(f"❌ Cerrado  WebsocketBinanceApiClient(): motivo: {reason}")
        pass

    @staticmethod
    def on_error(code, error):
        print(f"⚠️ Error en WebsocketBinanceApiClient(): {code} - {error}")

    def reconnect(self):
        try:
            print("♻️ Intentando reconectar WebsocketBinanceApiClient():.....")
            self.close_thread(sleep=5)

        except Exception as e:
            print(
                f"WebsocketBinanceApiClient():: Error: Reintentando conexión en 5 segundos...({e})"
            )
            # self.reconnect()

    # asegura cerrar el thread
    def close_thread(self, sleep=1):

        # esta activo espera
        if (self.thread is not None) and self.thread.is_alive():
            time.sleep(sleep)
            self.thread.join()

    # autenticación websocket
    def login(self):
        auth = {"apiKey": self.BClient.API_KEY, "timestamp": int(time.time() * 1000)}

        params = self.BClient.signature_message(REQUEST=auth)
        auth_request = {
            "id": "auth_request_5494febb",
            "method": "session.logon",
            "params": params,
        }
        self.send(auth_request)

    def subscribe_execution_reports(self):
        self.send(
            {
                "method": "subscribe",
                "params": ["executionReport"],
                "id": "execution_reports_5494febb",
            }
        )

    def account_status(self):

        account = {}

        params = self.BClient.signature_message(REQUEST=account)

        auth_account = {
            "id": "accountStatus_5494febb",
            "method": "account.status",
            "params": params,
        }
        print(auth_account)
        self.send(auth_account)

        time.sleep(1)

    # lista orders activas
    def my_Orders(self, symbol=None, idOrder=None):

        auth = {}

        params = self.BClient.signature_message(REQUEST=auth)

        auth_order = {
            "id": "Orders_5494febb",
            "method": "order.status",
            "params": {
                "symbol": symbol,
                "orderId": idOrder,
                "clientOrderId": "web_e24747a2484c4ded9eaf1f9e40199d7f",
                "apiKey": self.BClient.API_KEY,
                "signature": params["signature"],
                "timestamp": int(time.time() * 1000),
            },
        }
        self.send(auth_order)
        print(auth_order)

    # lista orders activas
    def my_allOrders(self, assets=None, limit=1, dias=7, sleep=1):
        # 24 horas en milisegundos
        one_day_ms = 24 * 60 * 60 * 1000

        inicio = time.time()
        while time.time() - inicio < limit:

            # construye ultimo (late) timestamp
            ini_time = int(time.time() * 1000)
            l_timestamp = [ini_time - i * one_day_ms for i in range(dias)]
            l_timestamp.reverse()

            lSymbols = [f"{activo.upper()}" for activo in assets] or []

            for i, start_time in enumerate(l_timestamp, 1):
                end_time = start_time + one_day_ms

                for symbol in lSymbols:
                    order = {
                        "symbol": symbol,
                        "startTime": start_time,
                        "endTime": end_time,
                        "limit": limit,
                    }

                    params = self.BClient.signature_message(REQUEST=order)

                    auth_order = {
                        "id": "allOrders_5494febb",
                        "method": "allOrders",
                        "params": params,
                    }
                    self.send(auth_order)
                    time.sleep(sleep)

            # espera para reanudar escucha del socket
            time.sleep(2.5)

    def my_traders(self, assets=None, limit=1, late=7, sleep=1):

        for symbol in assets:
            traders = {
                "id": "traders_5494febb",
                "method": "trades.historical",
                "params": {
                    "symbol": symbol.upper(),
                    "apiKey": self.BClient.API_KEY,
                    "fromId": 0,
                    "limit": limit,
                },
            }
            self.send(traders)


# superClass para Streams Binance
class WebsocketBinanceStreams(SpotWebsocketStreamClient):
    """
    WebsocketBinanceStreams is a subclass of SpotWebsocketStreamClient designed to manage Binance Spot WebSocket streams for ticker updates.
    Args:
        stream_url (str, optional): The URL of the WebSocket stream. Defaults to None.
        assets (list, optional): List of asset symbols to subscribe to. Defaults to None.
        mensaje_callback (callable, optional): Callback function to handle incoming messages. Defaults to None.
    Attributes:
        symbols (list): List of formatted symbol strings for Binance ticker streams.
        stop_threads (bool): Flag to control thread execution.
        thread (threading.Thread or None): Thread object for managing the WebSocket subscription.
        counter (int): Counter for internal use.
        reconnect (bool): Flag indicating if a reconnection is required.
    Methods:
        on_close(reason): Handles WebSocket closure events and sets the reconnect flag.
        on_error(code, error): Handles WebSocket errors, logs them, and sets the reconnect flag.
        SUBSCRIBE(): Subscribes to the specified Binance ticker streams.
        reconnect(): Attempts to reconnect the WebSocket stream, handling exceptions.
        websocket_loop(limit=None, log=True): Starts the WebSocket subscription in a separate thread and manages its lifecycle.
        close_thread(sleep=1): Ensures the WebSocket thread is properly closed, waiting for a specified duration.
    """

    def __init__(self, stream_url=None, assets=None, mensaje_callback=None):
        super().__init__(
            stream_url=stream_url,
            on_message=mensaje_callback,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
        )
        self.assets = assets
        self.symbols = None
        self.counter = 0
        self.running = False
        self.thread_name = "WebsocketBinanceStream(Crypto)"

    def on_open(self, reason):
        self.running = True
        time.sleep(2)

    def on_close(self, reason):
        self.running = False

    def on_error(self, code, error):
        # self.running = False
        # self.stop()
        print(f"WebsocketBinanceStreams(): {code} Error: {error}")

    # subscribe cryptos al websocket
    def SUBSCRIBE(self):
        try:
            # toma ultimo assets para suscribir
            self.symbols = [f"{activo.lower()}@ticker" for activo in self.assets]
            self.subscribe(stream=self.symbols, id="24hrTicker_5494febb")
        except (ssl.SSLEOFError, Exception) as e:
            print(f"SUBSCRIBE():: running:{self.running}:: {e}")
            # self.reconnect = False

    # loop de reconexión en websocket
    def websocket_loop(self, limit=None, log=True, reconnect=True):
        try:
            self.SUBSCRIBE()
            time.sleep(limit)
            self.stop()

            if log:
                print(f"WebsocketBinanceStreams():: activo: {self.thread.name}")

        except (ssl.SSLEOFError, Exception) as e:
            print(f"websocket_loop():: {e}")
            # self.running = False
            raise


# --- Iteractive Brokers -----------------------------------------------------------------------------------------
class IB(IBClient):
    def __init__(
        self,
        username: str = None,
        account: str = None,
        client_gateway_path: str = None,
        is_server_running: bool = True,
    ) -> None:
        IBClient.__init__(self, username, account, is_server_running)
        """Initialize a new instance of the IBClient Object.

        Usage:
        ----
            >>> ib_paper_session = IBClient(
                username='IB_PAPER_USERNAME',
                account='IB_PAPER_ACCOUNT'
                )
            >>> ib_paper_session
            >>> ib_regular_session = IBClient(
                username='IB_REGULAR_USERNAME',
                account='IB_REGULAR_ACCOUNT'
                )
            >>> ib_regular_session
            :rtype: object
        """

        sesion = BDsystem.select_sesion("select", vehiculo="Stock")
        self.account = sesion["idcuenta"]
        self.username = sesion["iduser"]
        self.client_portal_client = ClientPortal()

        self.api_version = "v1/"
        self._operating_system = sys.platform
        self.session_state_path: pathlib.Path = (
            pathlib.Path(__file__).parent.joinpath("server_session.json").resolve()
        )
        self.authenticated = False
        self._is_server_running = is_server_running

        # Define URL Components
        ib_gateway_host = r"https://localhost"
        ib_gateway_port = r"5000"
        self.ib_gateway_path = ib_gateway_host + ":" + ib_gateway_port
        self.backup_gateway_path = r"https://cdcdyn.interactivebrokers.com/portal.proxy"
        self.login_gateway_path = (
            self.ib_gateway_path + "/sso/Login?forwardTo=22&RL=1&ip2loc=on"
        )

        # Asigna Nombre Logging
        self.logger = logging.getLogger("IBroks_Client")

    # valida conexión al localHost
    def is_localhost(self):
        try:
            ilog, url = False, "https://localhost:5000"
            # response = requests.get(url, verify=True)

            auth = self.is_authenticated(True)
            if "authenticated" in auth:
                if auth["authenticated"] and auth["connected"]:
                    ilog = True
                else:
                    webbrowser.open("https://localhost:5000")
                    time.sleep(20)
            else:
                print(f"is_localhost(Stock): Error usuario no authenticated")
                webbrowser.open("https://localhost:5000")

            return ilog
        except Exception as error:
            print(
                f"is_localhost(Stock): ",
                f"No se pudo conectar al Portal Cliente. Asegúrate de que está en ejecución. {error}",
            )

    # valida connection de IB()
    def ib_is_connet(self) -> bool:
        connect = False
        if self._is_server_running:
            if self.is_authenticated("connected") and self.is_authenticated(
                "authenticated"
            ):
                connect = True
        return connect

    def create_session(self, set_server=True) -> bool:
        """Creates a new session.

        Creates a new session with Interactive Broker using the credentials
        passed through when the Robot was initalized.

        Usage:
        ----
            >>> ib_client = IBClient(
                username='IB_PAPER_username',
                password='IB_PAPER_PASSWORD',
                account='IB_PAPER_account',
            )
            >>> server_response = ib_client.create_session()
            >>> server_response
                True

        Returns:
        ----
        bool -- True if the session was created, False if wasn't created.
        """

        # first let's check if the server is running, if it's not then we can start up.
        if self.server_process is None and not self._is_server_running:

            # If it's None we need to connect first.
            if set_server:
                self.connect(start_server=True, check_user_input=True)
            else:
                self.connect(start_server=True, check_user_input=False)
                return True

            # then make sure the server is updated.
            if self._set_server():
                return True

        # Try and authenticate.
        auth_response = self.is_authenticated()

        # Log the initial Info.
        self.logger.info(
            textwrap.dedent(
                f"""
           =================
           Create Session:
           =================
           Auth Response: {auth_response}
           """
            )
        )

        # Finally make sure we are authenticated.   >daga2004
        # print('create_session:', auth_response)
        if auth_response:
            if (
                "authenticated" in auth_response.keys()
                and auth_response["authenticated"]
                and self._set_server()
            ):
                self.authenticated = True
                return True, auth_response
        else:
            # In this case don't connect, but prompt the user to log in again.
            self.connect(start_server=False)

            if self._set_server():
                self.authenticated = True
                return True, auth_response

    def is_authenticated(self, check: bool = False) -> Dict:
        """Checks if session is authenticated.

        Overview:
        ----
        Current Authentication status to the Brokerage system. Market Data and
        Trading is not possible if not authenticated, e.g. authenticated
        shows `False`.

        Returns:
        ----
        (dict): A dictionary with an authentication flag.
        """

        # define request components
        endpoint = "iserver/auth/status"
        try:
            if not check:
                req_type = "POST"
            else:
                req_type = "GET"

            content = self._make_request(
                endpoint=endpoint, req_type=req_type, headers="none"
            )
            content = content if content is not None else {}

            return content
        except Exception as error:
            print("[is_authenticated()]: {}".format(error))

    def _headers(self, mode: str = "json") -> Dict:
        """Builds the headers.

        Returns a dictionary of default HTTP headers for calls to Interactive
        Brokers API, in the headers we defined the Authorization and access
        token.

        Arguments:
        ----
        mode {str} -- Defines the content-type for the header's dictionary.
            default is 'json'. Possible values are ['json','form']

        Returns:
        ----
        Dict
        """
        version = self.api_version
        if mode == "json":
            headers = {"Content-Type": "application/json"}
        elif mode == "form":
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
        elif mode == "none":
            headers = None

        return headers

    def _build_url(self, endpoint: str) -> str:
        """Builds url for a request.

        Arguments:
        ----
        endpoint {str} -- The URL that needs conversion to a full endpoint URL.

        Returns:
        ----
        {srt} -- A full URL path.
        """
        return urllib.parse.unquote(
            urllib.parse.urljoin(self.ib_gateway_path, self.api_version)
            + r"portal/"
            + endpoint
        )

    # gwi001
    def _make_request(
        self,
        endpoint: str,
        req_type: str,
        headers: str = "json",
        params: dict = None,
        data: dict = None,
        json: dict = None,
    ) -> Dict:
        """
        Handles a request to the client API (GET, POST, DELETE, PUT).
        """

        url = self._build_url(endpoint=endpoint)
        headers = self._headers(mode=headers)

        try:
            # Log de la petición
            self.logger.info(
                f"_make_request(): {req_type} {url} | params={params} | json={json}"
            )

            # Selección del método
            if req_type == "POST":
                response = requests.post(
                    url=url, headers=headers, params=params, json=json, verify=False
                )
            elif req_type == "GET":
                response = requests.get(
                    url=url, headers=headers, params=params, json=json, verify=False
                )
            elif req_type == "DELETE":
                response = requests.delete(
                    url=url, headers=headers, params=params, json=json, verify=False
                )
            elif req_type == "PUT":
                response = requests.put(
                    url=url, headers=headers, params=params, json=json, verify=False
                )
            else:
                self.logger.error(
                    f"_make_request(): ❌ Tipo de request inválido {req_type}"
                )
                return {}

            # Procesar respuesta
            status_code = response.status_code
            content_type = response.headers.get("Content-Type", "")

            if response.ok:
                try:
                    if "application/json" in content_type:
                        data = response.json()
                    else:
                        data = {"raw_text": response.text}

                    self.logger.debug(
                        textwrap.dedent(
                            f"""
                            ================
                            _make_request(): SUCCESS
                            ================  
                            URL: {response.url}
                            Code: {status_code}
                            """
                        )
                    )
                    return data
                except ValueError:
                    self.logger.error(
                        f"_make_request(): ❌ No se pudo parsear JSON. Respuesta cruda: {response.text[:200]}"
                    )
                    return {"raw_text": response.text}
            else:
                # Error HTTP
                self.logger.error(
                    textwrap.dedent(
                        f"""
                        ================
                        _make_request(): HTTP ERROR
                        ================  
                        URL    : {response.url}
                        Code   : {status_code}
                        params : {params}
                        json   : {json}
                        Body   : {response.text[:500]}
                        headers: {headers}
                        """
                    )
                )
                return {}

        except requests.exceptions.RequestException as e:
            # Errores de red: timeouts, conexión caída, etc.
            self.logger.error(
                textwrap.dedent(
                    f"""
                    ================
                    _make_request(): NETWORK EXCEPTION
                    ================  
                    URL: {url}
                    Type: {req_type}
                    Error: {e}
                    """
                )
            )
            return {}
        except Exception as e:
            # Otros errores no controlados
            self.logger.exception(f"_make_request(): ❌ Excepción inesperada: {e}")
            return {}

    def portfolio_account_positions(self, account_id: str, page_id: int = 0) -> Dict:
        """
        Returns a list of positions for the given account. The endpoint supports paging,
        page's default size is 30 positions. /portfolio/accounts or /portfolio/subaccounts
        must be called prior to this endpoint.

        NAME: account_id
        DESC: The account ID you wish to return positions for.
        TYPE: String

        NAME: page_id
        DESC: The page you wish to return if there are more than 1. The
              default value is `0`.
        TYPE: String

        ADDITIONAL ARGUMENTS NEED TO BE ADDED!!!!!
        :rtype: object
        """

        # define request components
        endpoint = r"portfolio/{}/positions/{}".format(account_id, page_id)
        req_type = "GET"
        content = self._make_request(endpoint=endpoint, req_type=req_type)

        return content

    def portfolio_account_ledger(self, account_id: str) -> Dict:
        """
        Information regarding settled cash, cash balances, etc. in the account's
        base currency and any other cash balances hold in other currencies. /portfolio/accounts
        or /portfolio/subaccounts must be called prior to this endpoint. The list of supported
        currencies is available at https://www.interactivebrokers.com/en/index.php?f=3185.

        NAME: account_id
        DESC: The account ID you wish to return info for.
        TYPE: String
        """

        # define request components
        endpoint = r"portfolio/{}/ledger".format(account_id)
        req_type = "GET"
        content = self._make_request(endpoint=endpoint, req_type=req_type)

        return content

    def trades(self, account_id: str, days: int):
        """
        Returns a list of trades for the currently selected account for current day and
        six previous days.
        """

        endpoint = r"iserver/account/trades?days={}&accountId={}".format(
            days, account_id
        )
        req_type = "GET"
        content = self._make_request(endpoint=endpoint, req_type=req_type)

        return content

    def get_live_orders(self):
        """
        The end-point is meant to be used in polling mode, e.g. requesting every
        x seconds. The response will contain two objects, one is notification, the
        other is orders. Orders is the list of orders (cancelled, filled, submitted)
        with activity in the current day. Notifications contains information about
        execute orders as they happen, see status field."""

        try:
            # define request components
            endpoint = r"iserver/account/orders"
            req_type = "GET"
            content = self._make_request(endpoint=endpoint, req_type=req_type)

            return content
        except Exception as e:
            print("[get_live_orders()]: {}".format(e))

    def place_order(self, account_id: str, order: dict) -> Dict:
        """
        Please note here, sometimes this end-point alone can't make sure you submit the order
        successfully, you could receive some questions in the response, you have to answer
        them in order to submit the order successfully. You can use "/iserver/reply/{replyid}"
        end-point to answer questions.

        NAME: account_id
        DESC: The account ID you wish to place an order for.
        TYPE: String

        NAME: order
        DESC: Either an IBOrder object or a dictionary with the specified payload.
        TYPE: IBOrder or Dict
        """
        try:
            if type(order) is dict:
                order = order
            else:
                order = order.create_order()

            # define request components
            endpoint = r"iserver/account/{}/orders".format(account_id)
            req_type = "POST"

            content = self._make_request(
                endpoint=endpoint, req_type=req_type, json=order
            )
            return content
        except (Exception, requests.exceptions.RequestException) as e:
            print("[place_order()]: {}".format(e))
            return {}

    def place_orders(self, account_id: str, orders: List[Dict]) -> Dict:
        """
        An extension of the `place_order` endpoint but allows for a list of orders. Those orders may be
        either a list of dictionary objects or a list of IBOrder objects.

        NAME: account_id
        DESC: The account ID you wish to place an order for.
        TYPE: String

        NAME: orders
        DESC: Either a list of IBOrder objects or a list of dictionaries with the specified payload.
        TYPE: List<IBOrder Object> or List<Dictionary>
        """

        # EXTENDED THIS
        if type(orders) is list:
            orders = orders
        else:
            orders = orders

        # define request components
        endpoint = r"iserver/account/{}/orders".format(account_id)
        req_type = "POST"
        content = self._make_request(endpoint=endpoint, req_type=req_type, json=orders)

        return content

    def order_confirm(self, replyid=None):
        """
        An extension of the `place_confirm` endpoint but allows to confirm id orders.

        NAME: replyid
        DESC: The number ID to place an order.
        TYPE: String
        """
        endpoint = "iserver/reply/{}".format(replyid)
        print(endpoint)
        json_body = {"confirmed": True}
        req_type = "POST"
        content = self._make_request(
            endpoint=endpoint, req_type=req_type, json=json_body
        )
        # gwi001 json = json_body

        return content

    @staticmethod
    def orderconfirm(replyid=None):
        """
        provisional :: An extension of the `place_confirm` endpoint but allows to confirm id orders.

        NAME: replyid
        DESC: The number ID to place an order.
        TYPE: String
        """

        base_url = "https://localhost:5000/v1/api/"
        endpoint = r"iserver/reply/{}".format(replyid)
        reply_url = "".join([base_url, endpoint])
        json_body = {"confirmed": True}
        order_req = requests.post(url=reply_url, verify=False, json=json_body)
        content = json.dumps(order_req.json(), indent=2)

        return content

    @staticmethod
    def deleteorder(self, account_id=None, customer_order_id=None):
        """Provisional Deletes the order specified by the customer order ID.

        NAME: account_id
        DESC: The account ID you wish to place an order for.
        TYPE: String

        NAME: customer_order_id
        DESC: The customer order ID for the order you wish to DELETE.
        TYPE: String
        """

        # define request components
        base_url = "https://localhost:5000/v1/api/"
        endpoint = r"iserver/account/{}/order/{}".format(account_id, customer_order_id)
        req_type = "DELETE"
        reply_url = "".join([base_url, endpoint])
        order_req = requests.post(
            url=reply_url,
            verify=False,
        )
        content = json.dumps(order_req.json(), indent=2)

        return content

    def delete_order(self, account_id: str, customer_order_id: str) -> Dict:
        """Deletes the order specified by the customer order ID.

        NAME: account_id
        DESC: The account ID you wish to place an order for.
        TYPE: String

        NAME: customer_order_id
        DESC: The customer order ID for the order you wish to DELETE.
        TYPE: String
        """

        # define request components
        endpoint = r"iserver/account/{}/order/{}".format(account_id, customer_order_id)
        req_type = "DELETE"
        content = self._make_request(endpoint=endpoint, req_type=req_type)

        return content

    def place_order_scenario(self, account_id: str, order: dict) -> Dict:
        """
        This end-point allows you to preview order without actually submitting the
        order, and you can get commission information in the response.

        NAME: account_id
        DESC: The account ID you wish to place an order for.
        TYPE: String

        NAME: order
        DESC: Either an IBOrder object or a dictionary with the specified payload.
        TYPE: IBOrder or Dict
        """

        if type(order) is dict:
            order = order
        else:
            order = order.create_order()

        # define request components
        endpoint = r"iserver/account/{}/orders/whatif".format(account_id)
        req_type = "POST"
        content = self._make_request(endpoint=endpoint, req_type=req_type, json=order)

        return content

    def place_order_reply(self, reply_id: str = None, reply: str = None):
        """
        An extension of the `place_order` endpoint but allows for a list of orders. Those orders may be
        either a list of dictionary objects or a list of IBOrder objects.

        NAME: account_id
        DESC: The account ID you wish to place an order for.
        TYPE: String

        NAME: orders
        DESC: Either a list of IBOrder objects or a list of dictionaries with the specified payload.
        TYPE: List<IBOrder Object> or List<Dictionary>
        """

        # define request components
        endpoint = r"iserver/reply/{}".format(reply_id)
        req_type = "POST"
        reply = {"confirmed": reply}

        content = self._make_request(endpoint=endpoint, req_type=req_type, json=reply)

        return content

    def modify_order(
        self, account_id: str, customer_order_id: str, order: dict
    ) -> Dict:
        """
        Modifies an open order. The /iserver/accounts endpoint must first
        be called.

        NAME: account_id
        DESC: The account ID you wish to place an order for.
        TYPE: String

        NAME: customer_order_id
        DESC: The customer order ID for the order you wish to MODIFY.
        TYPE: String

        NAME: order
        DESC: Either an IBOrder object or a dictionary with the specified payload.
        TYPE: IBOrder or Dict
        """

        if type(order) is dict:
            order = order
        else:
            order = order.create_order()

        # define request components
        endpoint = r"iserver/account/{}/order/{}".format(account_id, customer_order_id)
        req_type = "POST"
        content = self._make_request(endpoint=endpoint, req_type=req_type, json=order)

        return content


if __name__ == "__main__":

    ib = IB()

    # grab the account data.
    print("portfolio_accounts()")
    account_data = ib.portfolio_accounts()
    print(account_data)
    print("--------------------------------------")
