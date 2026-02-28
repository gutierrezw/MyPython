"""
Class_vehiculo.py - Módulo Binance con soporte de ambientes (PRODUCTION / TESTNET)

Clases:
- BinanceSpot:         Cliente REST Spot (extiende binance.spot.Spot)
- BinanceClient:       Wrapper principal (resuelve sesión + keys + environment)
- BinanceStreamClient: WebSocket para streams de mercado (ticker, klines)
- BinanceWSApiClient:  WebSocket para API autenticada (orders, account)

Uso:
    from Class_vehiculo import BinanceClient, BinanceStreamClient

    # Testnet
    client = BinanceClient(env="TESTNET", vehiculo="BotCrypto")
    client.spot.get_new_order(symbol="BTCUSDT", side="BUY", type="MARKET", quantity=0.001)

    # Producción
    client = BinanceClient(env="PRODUCTION", vehiculo="Crypto")
"""

# binance SDK
from binance.spot import Spot
from binance.api import ClientError
from binance.websocket.spot.websocket_api import SpotWebsocketAPIClient
from binance.websocket.spot.websocket_stream import SpotWebsocketStreamClient

from Modulos_python import (
    functools,
    time,
    requests,
    serialization,
    b64encode,
    ssl,
    threading,
    textwrap,
    json,
    sys,
    urllib,
    webbrowser,
    datetime,
)
import pathlib
from Modulos_Mysql import BDsystem
import logging
from typing import Dict, List


# =============================================================================
# CONFIGURACIÓN DE AMBIENTES
# =============================================================================
BINANCE_ENV = {
    "PRODUCTION": {
        "base_url": "https://api.binance.com",
        "ws_stream": "wss://stream.binance.com:9443",
        "ws_api": "wss://ws-api.binance.com:9443/ws-api/v3",
    },
    "TESTNET": {
        "base_url": "https://testnet.binance.vision",
        "ws_stream": "wss://stream.testnet.binance.vision",
        "ws_api": "wss://ws-api.testnet.binance.vision/ws-api/v3",
    },
}


# =============================================================================
# DECORADOR DE EXCEPCIONES
# =============================================================================
def handle_binance_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger("BinanceSpot")
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error_code = getattr(e, "error_code", None)
            msg = getattr(e, "error_message", str(e))
            # -2011: sin órdenes que cancelar (orden ya ejecutada por Binance) → no es error real
            if error_code == -2011 or "-2011" in str(msg):
                logger.warning(f"cancel_all_orders {func.__name__}: sin órdenes abiertas (orden ya ejecutada) [{error_code}]")
            else:
                logger.error(
                    textwrap.dedent(
                        f"""
                      =======================================
                      handle_binance_exceptions(ClientError):
                      =======================================
                      Code   : {error_code}
                      status : {getattr(e, "status_error", None)}
                      message: {msg}
                      func   : {func.__name__}
                      args   : {args[1:]}
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
                  No hay conexión a internet.
                  ==============================================================
                  message: {e}
                  func   : {func.__name__}
                  """
                )
            )
        except Exception as e:
            msg = getattr(e, "error_message", str(e))
            # -2011 puede venir también como HTTPError genérico
            if "-2011" in str(msg) or "-2011" in str(e):
                logger.warning(f"{func.__name__}: sin órdenes abiertas (orden ya ejecutada por Binance) [-2011]")
            else:
                logger.error(
                    textwrap.dedent(
                        f"""
                      =============================
                      handle_binance_exceptions():
                      =============================
                      func   : {func.__name__}
                      Code   : {getattr(e, "error_code", None)}
                      status : {getattr(e, "status_error", None)}
                      message: {msg}
                      """
                    )
                )
        return None

    return wrapper


# =============================================================================
# CLIENTE REST SPOT: BinanceSpot
# =============================================================================
class BinanceSpot(Spot):
    """
    Cliente REST Spot mejorado.
    Recibe api_key, private_key y base_url como parámetros (no lee BD internamente).
    """

    def __init__(self, api_key, private_key, base_url, timeout=10):
        # Pasar private_key al SDK para que firme automáticamente con Ed25519
        super().__init__(api_key, base_url=base_url, timeout=timeout, private_key=private_key)
        self._base_url = base_url
        self.api_key = api_key
        self.private_key = private_key
        self.logger = logging.getLogger("BinanceSpot")
        # Debug: verificar que private_key se pasó correctamente
        self.logger.info(f"BinanceSpot init: private_key={'SET' if self.private_key else 'NONE'}, base_url={base_url}")

    # =========================
    # FIRMA DE MENSAJES
    # =========================
    def signature_spot_message(self, tipo="b64", REQUEST=None):

        def ed25519(a_key, p_key, p_params=None):
            p_params["timestamp"] = int(time.time() * 1000)
            payload = "&".join([f"{param}={value}" for param, value in p_params.items()])
            signature = b64encode(p_key.sign(payload.encode("utf-8")))
            p_params["signature"] = signature.decode("utf-8")
            return p_params

        try:
            private_key = serialization.load_pem_private_key(data=self.private_key, password=None)
            if tipo == "b64":
                return ed25519(self.api_key, private_key, p_params=REQUEST)
        except Exception as e:
            self.logger.error(f"signature_spot_message(): {e}")

    # =========================
    # CONECTIVIDAD
    # =========================
    def check_binance_connection(self):
        try:
            url_path = f"{self._base_url}/api/v3/ping"
            response = requests.get(url_path, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            self.logger.error(f"check_binance_connection(): {e}")
            return False

    # =========================
    # EXCHANGE INFO
    # =========================
    def get_exchange_info(self, symbol=None):
        try:
            response = self.exchange_info(symbol=symbol)
            if response:
                for s in response["symbols"]:
                    if s["symbol"] == symbol:
                        result = {symbol: {"minQty": 0.0, "stepSize": 0.0, "minNotional": 5.0}}
                        for filtro in s["filters"]:
                            if filtro["filterType"] == "LOT_SIZE":
                                result[symbol]["minQty"] = float(filtro["minQty"])
                                result[symbol]["stepSize"] = float(filtro["stepSize"])
                            elif filtro["filterType"] == "NOTIONAL":
                                result[symbol]["minNotional"] = float(filtro.get("minNotional", 5.0))
                            elif filtro["filterType"] == "PRICE_FILTER":
                                result[symbol]["tickSize"] = float(filtro["tickSize"])
                        return result
        except (ClientError, requests.exceptions.RequestException) as e:
            self.logger.error(f"get_exchange_info(): {e}")

    # =========================
    # ÓRDENES
    # =========================
    @handle_binance_exceptions
    def get_new_order(
        self, symbol=None, side=None, type=None, price=None, quantity=None, timeInForce=None, stopPrice=None
    ):

        params = {
            "symbol": symbol,
            "side": side,
            "type": type,
            "quantity": quantity,
            "timestamp": int(time.time() * 1000),
        }
        if price is not None:
            params["price"] = float(price)
        if stopPrice is not None:
            params["stopPrice"] = float(stopPrice)
        if timeInForce is not None:
            params["timeInForce"] = timeInForce

        self.logger.warning(f"API >> POST /api/v3/order | {params}")

        signed_query = self.signature_spot_message(REQUEST=params)
        headers = {"X-MBX-APIKEY": self.api_key}
        r = requests.post(self._base_url + "/api/v3/order", headers=headers, params=signed_query, timeout=5)

        self.logger.warning(f"API << {r.status_code} | {r.text[:500]}")

        r.raise_for_status()
        return r.json()

    @handle_binance_exceptions
    def get_cancel_order(self, symbol: str, orderId: int):
        params = {
            "symbol": symbol,
            "orderId": orderId,
            "timestamp": int(time.time() * 1000),
        }

        self.logger.warning(f"API >> DELETE /api/v3/order | {params}")

        signed_query = self.signature_spot_message(REQUEST=params)
        headers = {"X-MBX-APIKEY": self.api_key}
        r = requests.delete(self._base_url + "/api/v3/order", headers=headers, params=signed_query, timeout=5)

        self.logger.warning(f"API << {r.status_code} | {r.text[:500]}")

        r.raise_for_status()
        return r.json()

    @handle_binance_exceptions
    def cancel_all_orders(self, symbol):
        params = {
            "symbol": symbol,
            "timestamp": int(time.time() * 1000),
        }

        self.logger.warning(f"API >> DELETE /api/v3/openOrders | {params}")

        signed_query = self.signature_spot_message(REQUEST=params)
        headers = {"X-MBX-APIKEY": self.api_key}
        r = requests.delete(self._base_url + "/api/v3/openOrders", headers=headers, params=signed_query, timeout=5)

        self.logger.warning(f"API << {r.status_code} | {r.text[:500]}")

        r.raise_for_status()
        return r.json()

    @handle_binance_exceptions
    def get_my_trades(self, ticket: str, limit: int, startTime: int, endTime: int):
        return self.my_trades(ticket, limit=limit, startTime=startTime, endTime=endTime)

    @handle_binance_exceptions
    def Myget_open_orders(self):
        return self.get_open_orders()

    # =========================
    # CUENTA
    # =========================
    @handle_binance_exceptions
    def account_spot(self, **kwargs):
        try:
            url_path = "/api/v3/account"
            return self.sign_request("GET", url_path, {**kwargs})
        except (ClientError, requests.exceptions.RequestException) as e:
            self.logger.error(f"account_spot(): {e}")

    @handle_binance_exceptions
    def get_account_margin(self, **kwargs):
        try:
            return self.margin_account()
        except (ClientError, requests.exceptions.RequestException) as e:
            self.logger.error(f"get_account_margin(): {e}")

    # =========================
    # PRÉSTAMOS FLEXIBLES
    # =========================
    @handle_binance_exceptions
    def get_flexible_adjust_ltv(self, loanCoin="USDT", collateralCoin=None, adjustType="ADDITIONAL", amount=0.001):
        url_path = f"{self._base_url}/sapi/v2/loan/flexible/adjust/ltv"
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
            self.logger.error(f"get_flexible_adjust_ltv(): {e}")

    @handle_binance_exceptions
    def get_flexible_loan_repay(self, loanCoin="USDT", collateralCoin=None, amount=0.001):
        url_path = f"{self._base_url}/sapi/v2/loan/flexible/repay"
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
            self.logger.error(f"get_flexible_loan_repay(): {e}")

    @handle_binance_exceptions
    def get_flexible_loan_ongoing_orders(self, **kwargs):
        try:
            url_path = "/sapi/v2/loan/flexible/ongoing/orders"
            kwargs.setdefault("recvWindow", 8000)
            return self.sign_request("GET", url_path, {**kwargs})
        except (ClientError, requests.exceptions.RequestException) as e:
            self.logger.error(f"get_flexible_loan_ongoing_orders(): {e}")

    # =========================
    # C2C / EARN
    # =========================
    @handle_binance_exceptions
    def get_c2c_trade_history(self, tradeType=None, startTimestamp=None, endTimestamp=None, rows=100):
        return self.c2c_trade_history(
            tradeType=tradeType,
            startTimestamp=startTimestamp,
            endTimestamp=endTimestamp,
            rows=rows,
        )

    @handle_binance_exceptions
    def Myget_flexible_product_position(self, current=1, size=100, recvWindow=5000):
        return self.get_flexible_product_position(current=current, size=size, recvWindow=recvWindow)

    @handle_binance_exceptions
    def get_redeem_flexible_product(self, productId: str, amount: float, recvWindow=10000):
        return self.redeem_flexible_product(productId=productId, amount=amount, recvWindow=recvWindow)

    @handle_binance_exceptions
    def Myget_flexible_redemption_record(self, current=1, size=100):
        return self.get_flexible_redemption_record(current=current, size=size)


# =============================================================================
# WRAPPER PRINCIPAL: BinanceClient
# =============================================================================
class BinanceClient:
    """
    Wrapper principal para Binance.
    Resuelve sesión desde BD y crea BinanceSpot con el ambiente correcto.

    El ambiente se lee de sesion.environment (TESTNET | PRODUCTION).
    Si environment está vacío o no es válido, usa PRODUCTION por defecto.

    Uso:
        # Lee env desde BD automáticamente
        client = BinanceClient(vehiculo="BotCrypto")

        # Override manual del env (ignora BD)
        client = BinanceClient(vehiculo="BotCrypto", env="TESTNET")
    """

    VALID_ENVS = tuple(BINANCE_ENV.keys())

    def __init__(self, vehiculo="Crypto", env=None):
        self.logger = logging.getLogger("BinanceClient")
        self.vehiculo = vehiculo

        # Sesión desde BD
        self.sesion = BDsystem.get_sesion_by_vehiculo(vehiculo)

        # Ambiente: prioridad env param > sesion.environment > PRODUCTION
        if env and env in self.VALID_ENVS:
            self.env = env
        else:
            db_env = (self.sesion.get("environment") or "").strip().upper()
            self.env = db_env if db_env in self.VALID_ENVS else "PRODUCTION"

        self.urls = BINANCE_ENV[self.env]

        # Keys desde sesión
        self.API_KEY = self.sesion["userapi"].decode("utf-8")
        self.private_key = self.sesion["userpass"]

        # Cliente Spot
        self.spot = BinanceSpot(
            api_key=self.API_KEY,
            private_key=self.private_key,
            base_url=self.urls["base_url"],
        )

        self.logger.info(f"BinanceClient: vehiculo={vehiculo}, env={self.env}, base_url={self.urls['base_url']}")

    # =========================
    # FIRMA DE MENSAJES (WS)
    # =========================
    def signature_message(self, tipo="b64", REQUEST=None):

        def ed25519(a_key, p_key, p_params=None):
            p_params["timestamp"] = int(time.time() * 1000)
            p_params["apiKey"] = a_key
            payload = "&".join([f"{param}={value}" for param, value in sorted(p_params.items())])
            signature = b64encode(p_key.sign(payload.encode("utf-8")))
            p_params["signature"] = signature.decode("utf-8")
            return p_params

        try:
            private_key = serialization.load_pem_private_key(data=self.private_key, password=None)
            if tipo == "b64":
                return ed25519(self.API_KEY, private_key, p_params=REQUEST)
        except Exception as e:
            self.logger.error(f"signature_message(): {e}")


# =============================================================================
# WEBSOCKET STREAMS: BinanceStreamClient
# =============================================================================
class BinanceStreamClient(SpotWebsocketStreamClient):
    """
    WebSocket para streams de mercado (ticker, klines).
    Resuelve URL desde BINANCE_ENV.

    Uso:
        ws = BinanceStreamClient(env="TESTNET", assets=["BTCUSDT"], mensaje_callback=on_msg)
        ws.SUBSCRIBE()
    """

    def __init__(self, env="PRODUCTION", assets=None, mensaje_callback=None, on_close_callback=None):
        # Atributos ANTES de super().__init__ porque on_open se dispara dentro del constructor
        self.env = env
        self.assets = assets
        self.symbols = None
        self.counter = 0
        self.running = False
        self.logger = logging.getLogger("BinanceClient")
        self.thread_name = f"BinanceStream({env})"
        self._on_close_callback = on_close_callback
        self._sleep_event = threading.Event()

        urls = BINANCE_ENV[env]
        ws_url = urls["ws_stream"]
        self.logger.info(f"BinanceStreamClient init env={env} ws_stream={ws_url}")
        super().__init__(
            stream_url=ws_url,
            on_message=mensaje_callback,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
        )

    def _initialize_socket(self, *args, **kwargs):
        """Override para marcar el thread como daemon y no bloquear la salida de la app."""
        sm = super()._initialize_socket(*args, **kwargs)
        sm.daemon = True
        return sm

    def on_open(self, reason):
        self.running = True
        self.counter += 1
        self.logger.warning(f"BinanceStreamClient conectado ({self.env}) | counter={self.counter}")
        time.sleep(2)

    def on_close(self, reason):
        self.running = False
        self._sleep_event.set()  # Interrumpe websocket_loop para reconexión inmediata
        self.logger.warning(f"BinanceStreamClient cerrado ({self.env}): {reason}")
        if self._on_close_callback:
            self._on_close_callback(reason)

    def on_error(self, code, error):
        self.logger.error(f"BinanceStreamClient error ({self.env}): {code} - {error}")

    def SUBSCRIBE(self):
        try:
            self.symbols = [f"{activo.lower()}@ticker" for activo in self.assets]
            self.subscribe(stream=self.symbols, id="24hrTicker_bot")
        except (ssl.SSLEOFError, Exception) as e:
            self.logger.error(f"SUBSCRIBE() running:{self.running}: {e}")

    def subscribe_klines(self, interval="5m"):
        try:
            streams = [f"{activo.lower()}@kline_{interval}" for activo in self.assets]
            self.subscribe(stream=streams, id="klines_bot")
        except (ssl.SSLEOFError, Exception) as e:
            self.logger.error(f"subscribe_klines(): {e}")

    def websocket_loop(self, limit=None, log=True):
        try:
            self._sleep_event.clear()
            self.SUBSCRIBE()
            self._sleep_event.wait(timeout=limit)
            self.stop()

            if log:
                self.logger.info(f"BinanceStreamClient loop finalizado ({self.env})")

        except (ssl.SSLEOFError, Exception) as e:
            self.logger.error(f"websocket_loop(): {e}")
            raise


# =============================================================================
# WEBSOCKET API: BinanceWSApiClient
# =============================================================================
class BinanceWSApiClient(SpotWebsocketAPIClient):
    """
    WebSocket para API autenticada (orders, account status).
    Resuelve URL desde BINANCE_ENV.

    Uso:
        ws = BinanceWSApiClient(env="TESTNET", vehiculo="BotCrypto", mensaje_callback=on_msg)
        ws.login()
        ws.subscribe_execution_reports()
    """

    def __init__(self, env="PRODUCTION", vehiculo="Crypto", mensaje_callback=None):
        # Atributos ANTES de super().__init__ (on_error puede dispararse durante conexión)
        self.env = env
        self.bclient = BinanceClient(env=env, vehiculo=vehiculo)
        self.stop_threads = True
        self.thread = None
        self.counter = 0
        self.logger = logging.getLogger("BinanceClient")

        urls = BINANCE_ENV[env]
        super().__init__(
            stream_url=urls["ws_api"],
            on_message=mensaje_callback,
            on_error=self.on_error,
            on_close=self.on_close,
        )

    def _initialize_socket(self, *args, **kwargs):
        """Override para marcar el thread como daemon y no bloquear la salida de la app."""
        sm = super()._initialize_socket(*args, **kwargs)
        sm.daemon = True
        return sm

    @staticmethod
    def on_close(reason):
        pass

    def on_error(self, code, error):
        self.logger.error(f"BinanceWSApiClient error ({self.env}): {code} - {error}")

    def reconnect(self):
        try:
            self.logger.info(f"BinanceWSApiClient reconectando ({self.env})...")
            self.close_thread(sleep=5)
        except Exception as e:
            self.logger.error(f"BinanceWSApiClient reconnect error: {e}")

    def close_thread(self, sleep=1):
        if (self.thread is not None) and self.thread.is_alive():
            time.sleep(sleep)
            self.thread.join()

    # =========================
    # AUTENTICACIÓN
    # =========================
    def login(self):
        auth = {"apiKey": self.bclient.API_KEY, "timestamp": int(time.time() * 1000)}
        params = self.bclient.signature_message(REQUEST=auth)
        auth_request = {
            "id": "auth_request_bot",
            "method": "session.logon",
            "params": params,
        }
        self.send(auth_request)

    def subscribe_execution_reports(self):
        self.send(
            {
                "method": "subscribe",
                "params": ["executionReport"],
                "id": "execution_reports_bot",
            }
        )

    def account_status(self):
        account = {}
        params = self.bclient.signature_message(REQUEST=account)
        auth_account = {
            "id": "accountStatus_bot",
            "method": "account.status",
            "params": params,
        }
        self.send(auth_account)
        time.sleep(1)

    # =========================
    # ÓRDENES VÍA WEBSOCKET
    # =========================
    def my_Orders(self, symbol=None, idOrder=None):
        auth = {}
        params = self.bclient.signature_message(REQUEST=auth)
        auth_order = {
            "id": "Orders_bot",
            "method": "order.status",
            "params": {
                "symbol": symbol,
                "orderId": idOrder,
                "apiKey": self.bclient.API_KEY,
                "signature": params["signature"],
                "timestamp": int(time.time() * 1000),
            },
        }
        self.send(auth_order)

    def my_allOrders(self, assets=None, limit=1, dias=7, sleep=1):
        one_day_ms = 24 * 60 * 60 * 1000
        inicio = time.time()

        while time.time() - inicio < limit:
            ini_time = int(time.time() * 1000)
            l_timestamp = [ini_time - i * one_day_ms for i in range(dias)]
            l_timestamp.reverse()

            lSymbols = [f"{activo.upper()}" for activo in assets] if assets else []

            for i, start_time in enumerate(l_timestamp, 1):
                end_time = start_time + one_day_ms

                for symbol in lSymbols:
                    order = {
                        "symbol": symbol,
                        "startTime": start_time,
                        "endTime": end_time,
                        "limit": limit,
                    }
                    params = self.bclient.signature_message(REQUEST=order)
                    auth_order = {
                        "id": "allOrders_bot",
                        "method": "allOrders",
                        "params": params,
                    }
                    self.send(auth_order)
                    time.sleep(sleep)

            time.sleep(2.5)

    def my_traders(self, assets=None, limit=1):
        for symbol in assets:
            traders = {
                "id": "traders_bot",
                "method": "trades.historical",
                "params": {
                    "symbol": symbol.upper(),
                    "apiKey": self.bclient.API_KEY,
                    "fromId": 0,
                    "limit": limit,
                },
            }
            self.send(traders)
