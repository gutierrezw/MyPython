from Modulos_python import (
    urllib,
    requests,
    json,
    time,
    webbrowser,
    threading,
    traceback,
    datetime,
    textwrap,
    Dict,
    List,
    logging,
)
from Modulos_Mysql import BDsystem
from Class_Ibrks import IBClient


# --- Interactive Brokers -----------------------------------------------------------------------------------------
class IB(IBClient):
    # Mercados tal como IB los escribe en el paréntesis de companyHeader. La búsqueda de símbolos no trae currency,
    # así que ese paréntesis es el único dato del mercado. Los OTC van en un nivel aparte: en BIL, BHP en VALUE
    # sale antes que el ETF en ARCA
    MERCADOS_US = ("NYSE", "NASDAQ", "AMEX", "ARCA", "BATS", "IEX")
    MERCADOS_US_OTC = ("PINK", "VALUE")

    def __init__(
        self,
        username: str = None,
        account: str = None,
        client_gateway_path: str = None,
        is_server_running: bool = True,
    ) -> None:
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

        sesion = BDsystem.get_sesion_by_vehiculo("Stock")
        IBClient.__init__(
            self, username=sesion["iduser"], account=sesion["idcuenta"], is_server_running=is_server_running
        )

        # Sobreescribe puerto (IBClient usa 5000, IB usa 5501)
        self.ib_gateway_host = r"https://localhost"
        self.ib_gateway_port = r"5501"
        self.ib_gateway_path = self.ib_gateway_host + ":" + self.ib_gateway_port
        self.login_gateway_path = self.ib_gateway_path + "/sso/Login?forwardTo=22&RL=1&ip2loc=on"

        self.task = "IBKR-Tickle(On)"
        self.logger = logging.getLogger("IBroks_Client")
        self._network_error_logged = False  # guard: loguea NETWORK EXCEPTION solo una vez por período de caída
        self._browser_opened = False  # guard: abre browser IB solo una vez hasta autenticación exitosa

    # valida conexión al localHost
    def is_localhost(self):
        try:
            ilog, url = False, self.ib_gateway_path
            # response = requests.get(url, verify=True)

            auth = self.is_authenticated(True)
            if not auth:
                print("is_localhost(Stock): gateway inalcanzable (sin respuesta)")
                return ilog
            if "authenticated" in auth:
                if auth["authenticated"] and auth["connected"]:
                    ilog = True
                    self._browser_opened = False
                else:
                    if not self._browser_opened:
                        webbrowser.open(self.login_gateway_path)
                        self._browser_opened = True
                    time.sleep(20)
            else:
                print(f"is_localhost(Stock): Error usuario no authenticated")
                if not self._browser_opened:
                    webbrowser.open(self.login_gateway_path)
                    self._browser_opened = True

            return ilog
        except Exception as error:
            print(
                f"is_localhost(Stock): ",
                f"No se pudo conectar al Portal Cliente. Asegúrate de que está en ejecución. {error}",
            )

    def create_session(self, set_server=True) -> bool:
        """Override no-interactivo: avisa en log pero nunca llama input() desde un thread daemon."""
        try:
            auth_response = self.is_authenticated()
            if auth_response and auth_response.get("authenticated"):
                self.authenticated = self._set_server()
                return self.authenticated
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.logger.warning(textwrap.dedent(f"""
                ============================================================
                ⚠️  IB GATEWAY — RE-AUTENTICACIÓN REQUERIDA  [{ts}]
                ============================================================
                PASO 1: Abrí el navegador en: {self.login_gateway_path}
                PASO 2: Ingresá con tu usuario y contraseña de IBKR.
                PASO 3: Cuando veas "Client login succeeds", la app reconecta sola.
                ============================================================"""))
            return False
        except Exception as e:
            self.logger.error(f"create_session(): {e}")
            return False

    # valida connection de IB()
    def ib_is_connet(self) -> bool:
        connect = False
        if self._is_server_running:
            if self.is_authenticated("connected") and self.is_authenticated("authenticated"):
                connect = True
        return connect

    # ===========================================================
    # asegura conecction antes de cualquier requests
    # ===========================================================
    def ensure_connection(self) -> None:
        """
        Garantiza que el Gateway esté vivo y la sesión autenticada.
        Lanza RuntimeError si no es recuperable.
        """

        try:
            status = self.is_authenticated(check=True)
        except Exception as exc:
            raise RuntimeError("Gateway no responde") from exc

        if not status:
            raise RuntimeError("Respuesta inválida del gateway")

        if not status.get("authenticated", False):
            logging.warning("Sesión no autenticada, intentando reautenticar")

            self.validate()
            reauth = self.reauthenticate()

            status = self.is_authenticated(check=True)
            if not status.get("authenticated", False):
                raise RuntimeError(
                    f"Sesión IBKR no autenticada. Requiere login web en {self.ib_gateway_host}:{self.ib_gateway_port}"
                )

    # ===========================================================
    # Keep-alive (background)
    # ===========================================================
    def tickle(self) -> Dict:
        """Keeps the session open.

        If the gateway has not received any requests for several minutes an open session will
        automatically timeout. The tickle endpoint pings the server to prevent the
        session from ending.
        """
        # define request components
        endpoint = r"tickle"
        req_type = "POST"
        content = self._make_request(endpoint=endpoint, req_type=req_type)

        return content

    def _tickle_loop(self, interval: int, datahub=None) -> None:
        """
        Loop interno para mantener viva la sesión IBKR.
        Detecta desconexión y reconecta automáticamente cuando el usuario
        vuelve a autenticarse en el Gateway (sin reiniciar la app).
        """
        counter = 1
        was_disconnected = False
        reconnect_interval = 30

        while True:
            try:
                resp = self.tickle()
                auth_status = resp.get("iserver", {}).get("authStatus", {})
                auth = auth_status.get("authenticated", False)
                connected = auth_status.get("connected", False)

                self.logger.debug(f"Tickle: auth={auth} connected={connected} iter={counter}")
                if datahub:
                    datahub.update_self_procesos(proces="thread", tarea=self.task, itera=counter)
                counter += 1

                # sesión SSO viva pero brokerage desconectado — IB lo recupera solo, no intervenir
                if auth and not connected:
                    self.logger.warning("⚠️ IB connected=False — esperando recuperación automática")

                if auth:
                    if was_disconnected:
                        logging.warning("🔄 IB reconectando... recreando sesión")
                        success = self.create_session()
                        if success:
                            logging.warning("✅ IB reconexión exitosa — sesión restaurada")
                            was_disconnected = False
                            if self._on_reconnect:
                                try:
                                    self._on_reconnect()
                                except Exception as e:
                                    logging.error(f"on_reconnect callback error: {e}")
                        else:
                            logging.warning("⚠️ IB auth OK pero create_session falló, reintentando...")
                    self.authenticated = True
                else:
                    if not was_disconnected:
                        logging.warning(f"⚠️ IB sesión perdida — esperando re-autenticación del Gateway")
                    was_disconnected = True
                    self.authenticated = False
                    time.sleep(reconnect_interval)
                    continue
            except Exception as e:
                if not was_disconnected:
                    logging.error(f"Tickle falló: {e} — Gateway posiblemente caído")
                was_disconnected = True
                self.authenticated = False
                time.sleep(reconnect_interval)
                continue
            time.sleep(interval)

    def start_tickle(self, interval: int = 30, datahub=None, on_reconnect=None) -> None:
        """
        Inicia el loop de tickle en background.

        Args:
            interval: Segundos entre cada tickle (default: 30)
            datahub: DataHub para registrar proceso
            on_reconnect: Callback ejecutado al reconectar tras pérdida de sesión
        """
        self._on_reconnect = on_reconnect
        try:
            if hasattr(self, "_tickle_thread"):
                return

            if datahub:
                datahub.procesos.append({"thread": {self.task: 0}})

            self._tickle_thread = threading.Thread(
                target=self._tickle_loop,
                args=(interval, datahub),
                daemon=True,
                name=self.task,
            )
            self._tickle_thread.start()
            logging.warning("✅ Tickle inicializado correctamente")
        except Exception as e:
            logging.error(f"start_tickle(): {e}")

    def stop_tickle(self):
        self._tickle_stop.set()

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

            content = self._make_request(endpoint=endpoint, req_type=req_type, headers="none")
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
        return urllib.parse.unquote(urllib.parse.urljoin(self.ib_gateway_path, self.api_version) + r"api/" + endpoint)

    def get_listings(self, symbol: str, secType: str = "STK") -> List[Dict]:
        """
        Listados de IB cuyo ticker es exactamente symbol, con los mercados de EE.UU. primero.

        La búsqueda de IB es difusa y el mismo ticker lo usan empresas distintas en otras bolsas: ENB devuelve
        Enbridge en TSE antes que en NYSE, y BIL devuelve BHP antes que el ETF. Tomar el primer resultado
        compraba en Toronto en CAD.

        Returns:
            [{"conid", "symbol", "exchange", "companyHeader"}] — vacío si no hay un listado con ese ticker exacto
        """

        def mercado(header):
            # "ENBRIDGE INC (NYSE)" → "NYSE"
            return header.rsplit("(", 1)[1].rstrip(") ") if "(" in header else ""

        def prioridad(listing):
            if listing["exchange"] in self.MERCADOS_US:
                return 0
            return 1 if listing["exchange"] in self.MERCADOS_US_OTC else 2

        try:
            content = self._get_conid(symbol=symbol, secType=secType)
            if not isinstance(content, list):
                return []

            listings = [
                {
                    "conid": str(c["conid"]),
                    "symbol": c.get("symbol"),
                    "exchange": mercado(c.get("companyHeader") or ""),
                    "companyHeader": c.get("companyHeader") or "",
                }
                for c in content
                if c.get("conid")
                and c.get("secType") == secType
                and str(c.get("symbol", "")).upper() == symbol.upper()
            ]
            # sorted es estable: dentro de cada nivel se conserva el orden de IB
            return sorted(listings, key=prioridad)
        except Exception as e:
            self.logger.exception(f"get_listings(): Error buscando listados de {symbol}: {e}")
            return []

    def _get_conid(self, symbol: str, secType="STK") -> int:
        """
        Obtiene el conid (Contract ID) y otros datos dado un ticker/symbol.

        NAME: symbol
        DESC: Ticker del instrumento (ej: AAPL, MSFT)
        TYPE: String
        """
        try:
            # define request components
            endpoint = r"/iserver/secdef/search"
            req_type = "GET"

            params = {"symbol": symbol, "name": False, "secType": secType}

            content = self._make_request(endpoint=endpoint, req_type=req_type, params=params)

            return content
        except Exception as e:
            self.logger.exception(f"_get_conid(): Error obteniendo conid para {symbol} {e}")

    @staticmethod
    def _prepare_arguments_list(parameter_list: List[str]) -> str:
        """Prepares the arguments for the request.

        Some endpoints can take multiple values for a parameter, this
        method takes that list and creates a valid string that can be
        used in an API request. The list can have either one index or
        multiple indexes.

        Arguments:r
        ----
        parameter_list {List} -- A list of paramater values assigned to an argument.

        Usage:
        ----
            >>> SessionObject._prepare_arguments_list(parameter_list=['MSFT','SQ'])

        Returns:
        ----
        {str} -- The joined list.

        """

        # validate it's a list.
        if type(parameter_list) is list:
            # specify the delimiter and join the list.
            delimiter = ","
            parameter_list = delimiter.join(parameter_list)

        return parameter_list

    def _get_marketData(self, conids: List[str], since: str, fields: List[str]) -> Dict:
        """
        Get Market Data for the given conid(s). The end-point will return by
        default bid, ask, last, change, change pct, close, listing exchange.
        See response fields for a list of available fields that can be request
        via fields argument. The endpoint /iserver/accounts should be called
        prior to /iserver/marketdata/snapshot. To receive all available fields
        the /snapshot endpoint will need to be called several times.

        NAME: conid
        DESC: The list of contract IDs you wish to pull current quotes for.
        TYPE: List<String>

        NAME: since
        DESC: Time period since which updates are required.
              Uses epoch time with milliseconds.
        TYPE: String

        NAME: fields
        DESC: List of fields you wish to retrieve for each quote.
        TYPE: List<String>
        """

        # define request components
        endpoint = "iserver/marketdata/snapshot"
        req_type = "GET"

        # join the two list arguments so they are both a single string.
        conids_joined = self._prepare_arguments_list(parameter_list=conids)

        if fields is not None:
            fields_joined = ",".join(str(n) for n in fields)
        else:
            fields_joined = ""

        # define the parameters
        if since is None:
            params = {"conids": conids_joined, "fields": fields_joined}
        else:
            params = {"conids": conids_joined, "since": since, "fields": fields_joined}

        content = self._make_request(endpoint=endpoint, req_type=req_type, params=params)

        return content

    def _get_symbol(self, symbol: str, secType: str = "STK", fields: List[str] = None, conid: str = None) -> Dict:
        """
        Obtiene información de mercado para un symbol dado.
        Primero obtiene el conid y luego consulta marketData.

        NAME: symbol
        DESC: Ticker del instrumento (ej: AAPL, MSFT)
        TYPE: String

        NAME: secType
        DESC: Tipo de seguridad (STK, OPT, FUT, etc.)
        TYPE: String

        NAME: fields
        DESC: Lista de campos a obtener del market data
        TYPE: List<String>

        NAME: conid
        DESC: Listado ya elegido por el llamador. Sin él se toma el primero de get_listings()
        TYPE: String

        Returns:
            Dict con información del symbol incluyendo market data
        """
        try:
            # 1. Obtener conid desde el symbol. La preferencia anterior filtraba por currency == "USD", campo que la
            # búsqueda de IB no devuelve: nunca coincidía y quedaba el primer STK de cualquier bolsa
            if not conid:
                listings = self.get_listings(symbol=symbol, secType=secType)
                if not listings:
                    self.logger.warning(f"_get_symbol(): No hay un listado con el ticker exacto {symbol}")
                    return None

                conid = listings[0]["conid"]
                self.logger.warning(
                    f"_get_symbol(): {symbol} → conid={conid} exchange={listings[0]['exchange']} "
                    f"listados={len(listings)}"
                )
            conid = [str(conid)]

            # 2. Obtener market data usando el conid
            FIELD_MAP = {
                "last": "31",
                "change": "82",
                "bid": "84",
                "ask": "86",
                "open": "7295",
                "close": "7296",
                "high": "70",
                "low": "71",
            }

            fields = list(FIELD_MAP.values())
            market_data = self._get_marketData(conids=conid, since=None, fields=fields)

            if not market_data or len(market_data) == 0:
                self.logger.warning(f"_get_symbol(): No se obtuvo marketData para {symbol} (conid: {conid})")
                return {"symbol": symbol, "conid": conid[0], "market_data": None}

            # 3. Combinar información
            result = {
                "symbol": symbol,
                "conid": conid[0],
                "market_data": market_data[0] if isinstance(market_data, list) else market_data,
            }

            return result

        except Exception as e:
            self.logger.exception(f"_get_symbol(): Error obteniendo datos para {symbol}: {e}")
            return None

    # gwi001
    def _make_request(
        self,
        endpoint: str,
        req_type: str,
        headers: str = "json",
        params: dict = None,
        data: dict = None,
        json: dict = None,
        _retry_accounts: bool = True,
    ) -> Dict:
        """
        Handles a request to the client API (GET, POST, DELETE, PUT).
        """

        url = self._build_url(endpoint=endpoint)
        headers = self._headers(mode=headers)

        # self.ensure_connection()

        try:
            # Log de la petición
            self.logger.info(f"_make_request(): {req_type} {url} | params={params} | json={json}")

            # Selección del método
            if req_type == "POST":
                response = requests.post(url=url, headers=headers, params=params, json=json, verify=False)
            elif req_type == "GET":
                response = requests.get(url=url, headers=headers, params=params, json=json, verify=False)
            elif req_type == "DELETE":
                response = requests.delete(url=url, headers=headers, params=params, json=json, verify=False)
            elif req_type == "PUT":
                response = requests.put(url=url, headers=headers, params=params, json=json, verify=False)
            else:
                self.logger.error(f"_make_request(): ❌ Tipo de request inválido {req_type}")
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

                    self._network_error_logged = False  # reset: Gateway volvió a responder
                    self.logger.debug(textwrap.dedent(f"""
                            ================
                            _make_request(): SUCCESS
                            ================
                            URL: {response.url}
                            Code: {status_code}
                            """))
                    return data
                except ValueError:
                    self.logger.error(
                        f"_make_request(): ❌ No se pudo parsear JSON. Respuesta cruda: {response.text[:200]}"
                    )
                    return {"raw_text": response.text}
            else:
                # sesión perdió el contexto de cuenta (típico tras reset nocturno del Gateway):
                # re-primea con iserver/accounts y reintenta una única vez
                if status_code == 500 and _retry_accounts and "query /accounts first" in response.text:
                    self.logger.warning("_make_request(): sesión sin contexto de cuenta, re-primeando iserver/accounts")
                    self._make_request(endpoint="iserver/accounts", req_type="GET", _retry_accounts=False)
                    return self._make_request(
                        endpoint=endpoint,
                        req_type=req_type,
                        headers="json",
                        params=params,
                        data=data,
                        json=json,
                        _retry_accounts=False,
                    )

                # Error HTTP
                self.logger.error(textwrap.dedent(f"""
                        ================
                        _make_request(): HTTP ERROR
                        ================
                        URL    : {response.url}
                        Code   : {status_code}
                        params : {params}
                        json   : {json}
                        Body   : {response.text[:500]}
                        headers: {headers}
                        """))
                return {}

        except requests.exceptions.RequestException as e:
            if not self._network_error_logged:
                self.logger.error(textwrap.dedent(f"""
                    ================
                    _make_request(): NETWORK EXCEPTION
                    ================
                    URL: {url}
                    Type: {req_type}
                    Error: {e}
                    """))
                self._network_error_logged = True
            else:
                self.logger.debug(f"_make_request(): NETWORK EXCEPTION (suprimido) | {url}")
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

        endpoint = r"iserver/account/trades?days={}&accountId={}".format(days, account_id)
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
            endpoint = r"iserver/account/orders"
            req_type = "GET"
            content = self._make_request(endpoint=endpoint, req_type=req_type)
            return content
        except Exception as e:
            print("[get_live_orders()]: {}".format(e))

    def get_preservation_stops(self):
        """Retorna las órdenes STP LMT SELL GTC activas — usadas por Agente_ManagerPreservation
        para reconstruir preservation_state al arrancar.
        Retorna lista de dicts: {symbol, order_id, stop_price, status}."""
        try:
            response = self.get_live_orders()
            if not response:
                return []
            result = []
            for o in response.get("orders", []):
                order_type = (o.get("orderType") or "").upper()
                side = (o.get("side") or o.get("orderDesc") or "").upper()
                tif = (o.get("timeInForce") or "").upper()
                status = o.get("status", "")
                if (
                    order_type in ("STP", "STP LMT")
                    and "SELL" in side
                    and tif == "GTC"
                    and status in ("Submitted", "PreSubmitted")
                ):
                    result.append(
                        {
                            "symbol": o.get("ticker", ""),
                            "order_id": o.get("orderId"),
                            "stop_price": o.get("auxPrice"),
                            "status": status,
                        }
                    )
            return result
        except Exception as e:
            print(f"[get_preservation_stops()]: {e}")
            return []

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

            content = self._make_request(endpoint=endpoint, req_type=req_type, json=order)
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
        content = self._make_request(endpoint=endpoint, req_type=req_type, json=json_body)
        # gwi001 json = json_body

        return content

    def orderconfirm(self, replyid: str) -> str:
        """
        Confirma una orden que requiere respuesta.

        Args:
            replyid: ID del reply a confirmar

        Returns:
            JSON string con la respuesta
        """
        base_url = f"{self.ib_gateway_host}:{self.ib_gateway_port}/v1/api/"
        endpoint = r"iserver/reply/{}".format(replyid)
        reply_url = "".join([base_url, endpoint])
        json_body = {"confirmed": True}

        try:
            order_req = requests.post(url=reply_url, verify=False, json=json_body)
            if not order_req.text or not order_req.text.strip():
                self.logger.warning(f"orderconfirm(): IB body vacío → confirmado | replyid={replyid}")
                return json.dumps([{"order_status": "Submitted", "order_id": ""}])
            try:
                return json.dumps(order_req.json(), indent=2)
            except Exception:
                # IB devolvió texto no-JSON (ej: HTML) → tratar como confirmación OK
                self.logger.warning(f"orderconfirm(): IB respuesta no-JSON → confirmado | replyid={replyid} | text={order_req.text[:80]}")
                return json.dumps([{"order_status": "Submitted", "order_id": ""}])
        except Exception as e:
            self.logger.error(f"orderconfirm(): {e}")
            return json.dumps({"error": str(e)})

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
        base_url = f"{self.ib_gateway_host}:{self.ib_gateway_port}/v1/api/"
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

    def modify_order(self, account_id: str, customer_order_id: str, order: dict) -> Dict:
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
