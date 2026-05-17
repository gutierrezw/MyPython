import math

from Modulos_python import (
    webbrowser,
    logging,
    threading,
    json,
    time,
    HTTPServer,
    BaseHTTPRequestHandler,
    urlparse,
    parse_qs,
)
from Modulos_Utilitarios import calculate_decimal_places

_logger = logging.getLogger("TradingView")
_TV_PORT = 5050

# Símbolo TradingView por vehículo: prefijo del exchange
_EXCHANGE_PREFIX = {
    "Crypto": "BINANCE:",
    "Stock": "",
    "FCI": "",
}

# Cache de datos por símbolo — leídos por Tampermonkey vía HTTP
_tv_data = {}  # {symbol: {"posicion": {...}, "lotes": [...], "vehiculo": "..."}}
_tv_prices = {}  # {symbol: {"last": float, "ts": float}} — precios live actualizados por la app
_tv_current = {"symbol": ""}  # último símbolo enviado desde la app
_tv_last_ping = {"t": 0.0, "ever": False}  # ever=True → Tampermonkey activo en esta sesión
_tv_server = None  # referencia para shutdown limpio
_tv_contexto = {}  # contexto de cartera para inyección en claude.ai
_order_callback = None  # fn(symbol, vehiculo, account, opt, qty, price, conid, razon) → (response, symbol)
_info_fn = None  # fn() → DataHub.info dict


def _calc_qty_from_importe(importe, price, vehiculo, symbol):
    if price <= 0:
        return 0.0
    if vehiculo == "Stock":
        return float(math.floor(importe / price))
    raw = importe / price
    try:
        step_size = _info_fn()[symbol]["lotSize"]["stepSize"]
        exp = calculate_decimal_places(step_size)
    except Exception:
        exp = 5
    return math.trunc(raw * 10**exp) / (10**exp)


_switch_callback = None  # fn(symbol) → None; carga datos del símbolo y llama abrir_tradingview()
_symbols_fn = None  # fn() → list[str]; retorna lista de símbolos en cartera (live)


def _tv_symbol(symbol, vehiculo):
    """Convierte símbolo interno al formato TradingView según vehículo."""
    prefix = _EXCHANGE_PREFIX.get(vehiculo, "")
    return f"{prefix}{symbol}"


class _TVRequestHandler(BaseHTTPRequestHandler):
    """Handler HTTP para el servidor local de datos TradingView."""

    def log_message(self, format, *args):
        _logger.debug(f"TVServer: {self.address_string()} {format % args}")

    def _send_json(self, data, status=200, origin="https://www.tradingview.com"):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "https://www.tradingview.com")
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if parsed.path == "/position":
            symbol = (params.get("symbol") or [""])[0].upper()
            self._send_json(_tv_data.get(symbol, {}))
        elif parsed.path == "/current":
            self._send_json(_tv_current)
        elif parsed.path == "/price":
            symbol = (params.get("symbol") or [""])[0].upper()
            self._send_json(_tv_prices.get(symbol, {}))
        elif parsed.path == "/ping":
            _tv_last_ping["t"] = time.time()
            _tv_last_ping["ever"] = True
            self._send_json({"ok": True})
        elif parsed.path == "/contexto":
            origin = self.headers.get("Origin", "https://claude.ai")
            self._send_json(_tv_contexto, origin=origin)
        elif parsed.path == "/symbols":
            symbols = sorted(_symbols_fn()) if _symbols_fn else sorted(_tv_data.keys())
            self._send_json({"symbols": symbols})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        origin = self.headers.get("Origin", "https://www.tradingview.com")
        if parsed.path == "/order":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                if not _order_callback:
                    _logger.error("do_POST /order: order callback not registered — chatbot no iniciado")
                    self._send_json({"ok": False, "error": "order callback not registered"}, 503, origin)
                    return
                symbol = body.get("symbol", "")
                vehiculo = body.get("vehiculo", "Stock")
                account = body.get("account", "")
                side = body.get("side", "BUY").upper()
                price = float(body.get("price", 0))
                conid = body.get("conid")
                importe = body.get("importe")
                qty = float(body.get("qty", 0))
                if importe is not None and price > 0:
                    qty = _calc_qty_from_importe(float(importe), price, vehiculo, symbol)
                if not symbol or qty <= 0 or price <= 0:
                    self._send_json({"ok": False, "error": "symbol, qty/importe y price requeridos"}, 400, origin)
                    return
                response, _ = _order_callback(
                    symbol=symbol,
                    vehiculo=vehiculo,
                    account=account,
                    opt=side,
                    qty=qty,
                    price=price,
                    conid=conid,
                    razon="Orden desde TradingView",
                )
                self._send_json({"ok": True, "status": response.get("status", ""), "detail": response}, origin=origin)
            except Exception as e:
                _logger.error(f"do_POST /order: {e}")
                self._send_json({"ok": False, "error": str(e)}, 500, origin)
        elif parsed.path == "/current":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                symbol = body.get("symbol", "").upper()
                if not symbol:
                    self._send_json({"ok": False, "error": "symbol requerido"}, 400, origin)
                    return
                if not _switch_callback:
                    self._send_json({"ok": False, "error": "switch callback no registrado"}, 503, origin)
                    return
                _switch_callback(symbol)
                self._send_json({"ok": True, **_tv_data.get(symbol, {})}, origin=origin)
            except Exception as e:
                _logger.error(f"do_POST /current: {e}")
                self._send_json({"ok": False, "error": str(e)}, 500, origin)
        else:
            self._send_json({"error": "not found"}, 404, origin)


def start_tv_server():
    """Inicia el servidor HTTP local en background. Llamar una vez al arrancar la app."""
    global _tv_server
    try:
        _tv_server = HTTPServer(("localhost", _TV_PORT), _TVRequestHandler)
        t = threading.Thread(target=_tv_server.serve_forever, name="TVServer", daemon=True)
        t.start()
        _logger.warning(f"TradingView server iniciado en puerto {_TV_PORT}")
    except OSError as e:
        _logger.warning(f"TradingView server no pudo iniciar (puerto {_TV_PORT} en uso?): {e}")
    except Exception as e:
        _logger.error(f"start_tv_server(): {e}")


def stop_tv_server():
    """Cierra el servidor HTTP sin bloquear el shutdown de la app."""
    global _tv_server
    if _tv_server:
        try:
            _tv_server.shutdown()
            _tv_server.server_close()
        except Exception:
            pass
        _tv_server = None
        _logger.warning("TradingView server detenido")


def set_order_callback(fn):
    """Registra el callable que ejecuta órdenes. Firma: fn(symbol, vehiculo, account, opt, qty, price, conid, razon)."""
    global _order_callback
    _order_callback = fn


def set_switch_callback(fn):
    """Registra el callable que carga datos de un símbolo y llama abrir_tradingview(). Firma: fn(symbol)."""
    global _switch_callback
    _switch_callback = fn


def set_symbols_fn(fn):
    """Registra la función que retorna la lista live de símbolos en cartera. Firma: fn() → list[str]."""
    global _symbols_fn
    _symbols_fn = fn


def set_info_fn(fn):
    """Registra fn() → DataHub.info para calcular qty desde importe en /order."""
    global _info_fn
    _info_fn = fn


def set_claude_contexto(data):
    """Actualiza el contexto de cartera servido en /contexto para inyección en claude.ai."""
    global _tv_contexto
    _tv_contexto = data


def update_tv_price(symbol, last):
    """Actualiza el precio live de un símbolo en el cache."""
    if symbol and last:
        _tv_prices[symbol] = {"last": float(last), "ts": time.time()}


def _price_sync_loop(get_info_fn):
    """Loop que sincroniza precios desde DataHub.info al cache _tv_prices cada 2s."""
    while True:
        try:
            sym = _tv_current.get("symbol", "")
            if sym:
                info = get_info_fn().get(sym, {})
                last = info.get("websocket", {}).get("last") or info.get("mrkprice")
                if last:
                    update_tv_price(sym, last)
        except Exception:
            pass
        time.sleep(2)


def start_price_sync(datahub_info_fn):
    """Inicia el loop de sincronización de precios. Llamar después de start_tv_server()."""
    t = threading.Thread(
        target=_price_sync_loop,
        args=(datahub_info_fn,),
        name="TVPriceSync",
        daemon=True,
    )
    t.start()


def abrir_tradingview(symbol, vehiculo="Stock", posicion=None, lotes=None):
    """
    Cachea los datos del símbolo y abre TradingView web en el browser.
    Tampermonkey lee los datos desde http://localhost:5050/position?symbol=X

    Args:
        symbol: símbolo del activo
        vehiculo: "Stock" | "Crypto" | "FCI"
        posicion: dict con avgcost, costo_base, position, last, objetivo, stop_loss
        lotes: lista de dicts de get_lotesGainLost
    """
    try:
        posicion = posicion or {}
        lotes = lotes or []
        _tv_data[symbol] = {"posicion": posicion, "lotes": lotes, "vehiculo": vehiculo}
        _tv_current["symbol"] = symbol
        tv_symbol = _tv_symbol(symbol, vehiculo)
        tv_activo = _tv_last_ping["ever"]
        if not tv_activo:
            webbrowser.open(f"https://www.tradingview.com/chart/?symbol={tv_symbol}")
        _logger.warning(f"TradingView {'navegado por Tampermonkey' if tv_activo else 'abierto'}: {symbol} ({vehiculo})")
    except Exception as e:
        _logger.error(f"abrir_tradingview({symbol}): {e}")
