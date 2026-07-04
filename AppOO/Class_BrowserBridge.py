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
    requests,
)
from Modulos_Utilitarios import calculate_decimal_places

_logger = logging.getLogger("TradingView")

# Puerto interno para callbacks de órdenes desde Node (solo localhost)
_CALLBACK_PORT = 5051

# URL del server-api Node (puede ser localhost o Cloudflare tunnel)
_NODE_URL = "http://localhost:8050"

_EXCHANGE_PREFIX = {
    "Crypto": "BINANCE:",
    "Stock": "",
    "FCI": "",
}

_tv_current = {"symbol": ""}   # copia local para abrir_tradingview sin depender de Node
_callback_server = None        # mini-server 5051 para callbacks de órdenes

_order_callback = None         # fn(symbol, vehiculo, account, opt, qty, price, conid, razon)
_switch_callback = None        # fn(symbol)
_symbols_fn = None             # fn() → list[str]
_info_fn = None                # fn() → DataHub.info
_balance_fn = None             # fn() → float USDT libre


def _is_tv_active() -> bool:
    """Consulta a Node si el panel TV (Tampermonkey) ha pingeado alguna vez."""
    try:
        resp = requests.get(f"{_NODE_URL}/tv/ping-status", timeout=1)
        return resp.json().get("ever", False)
    except Exception:
        return False


def _push(type_, payload, symbol=None):
    """Envía un update al server-api Node. Silencioso si Node no está disponible."""
    try:
        body = {"type": type_, "payload": payload}
        if symbol:
            body["symbol"] = symbol
        data = json.dumps(body, default=str)
        requests.post(
            f"{_NODE_URL}/internal/update",
            data=data,
            headers={"Content-Type": "application/json"},
            timeout=2,
        )
    except Exception:
        pass


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


def _tv_symbol(symbol, vehiculo):
    prefix = _EXCHANGE_PREFIX.get(vehiculo, "")
    return f"{prefix}{symbol}"


class _CallbackHandler(BaseHTTPRequestHandler):
    """Mini-server en 5051 — solo recibe callbacks de Node para /order y /switch."""

    def log_message(self, format, *args):
        _logger.debug(f"TVCallback: {format % args}")

    def _send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionAbortedError, BrokenPipeError):
            pass

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        if parsed.path == "/order":
            try:
                if not _order_callback:
                    self._send_json({"ok": False, "error": "order callback not registered"}, 503)
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
                    self._send_json({"ok": False, "error": "symbol, qty/importe y price requeridos"}, 400)
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
                self._send_json({"ok": True, "status": response.get("status", ""), "detail": response})
            except Exception as e:
                _logger.error(f"CallbackHandler /order: {e}")
                self._send_json({"ok": False, "error": str(e)}, 500)

        elif parsed.path == "/switch":
            try:
                symbol = body.get("symbol", "").upper()
                if not symbol:
                    self._send_json({"ok": False, "error": "symbol requerido"}, 400)
                    return
                if not _switch_callback:
                    self._send_json({"ok": False, "error": "switch callback no registrado"}, 503)
                    return
                _switch_callback(symbol)
                self._send_json({"ok": True})
            except Exception as e:
                _logger.error(f"CallbackHandler /switch: {e}")
                self._send_json({"ok": False, "error": str(e)}, 500)

        else:
            self._send_json({"error": "not found"}, 404)


def start_tv_server():
    """Inicia el mini-server de callbacks en 5051. Llamar una vez al arrancar la app."""
    global _callback_server
    try:
        _callback_server = HTTPServer(("localhost", _CALLBACK_PORT), _CallbackHandler)
        t = threading.Thread(target=_callback_server.serve_forever, name="TVCallback", daemon=True)
        t.start()
        _logger.warning(f"TradingView callback server iniciado en puerto {_CALLBACK_PORT}")
    except OSError as e:
        _logger.warning(f"TradingView callback server no pudo iniciar (puerto {_CALLBACK_PORT} en uso?): {e}")
    except Exception as e:
        _logger.error(f"start_tv_server(): {e}")


def stop_tv_server():
    global _callback_server
    if _callback_server:
        try:
            _callback_server.shutdown()
            _callback_server.server_close()
        except Exception:
            pass
        _callback_server = None
        _logger.warning("TradingView callback server detenido")


def is_tv_server_running() -> bool:
    return _callback_server is not None


def restart_tv_server():
    stop_tv_server()
    start_tv_server()


def set_order_callback(fn):
    global _order_callback
    _order_callback = fn


def set_switch_callback(fn):
    global _switch_callback
    _switch_callback = fn


def set_symbols_fn(fn):
    global _symbols_fn
    _symbols_fn = fn


def set_info_fn(fn):
    global _info_fn
    _info_fn = fn


def set_balance_fn(fn):
    global _balance_fn
    _balance_fn = fn


def set_claude_contexto(data):
    _push("contexto", data)


def update_tv_price(symbol, last):
    if symbol and last:
        _push("price", {"last": float(last)}, symbol=symbol)


def start_price_sync(datahub_info_fn):
    """Loop que sincroniza el precio del símbolo activo a Node cada 2s."""
    def _loop():
        while True:
            try:
                sym = _tv_current.get("symbol", "")
                if sym:
                    info = datahub_info_fn().get(sym, {})
                    last = info.get("websocket", {}).get("last") or info.get("mrkprice")
                    if last:
                        update_tv_price(sym, last)
            except Exception:
                pass
            time.sleep(2)

    threading.Thread(target=_loop, args=(), name="TVPriceSync", daemon=True).start()


def abrir_tradingview(symbol, vehiculo="Stock", posicion=None, lotes=None):
    """Pushea datos a Node y abre TradingView en el browser si Tampermonkey no está activo."""
    try:
        posicion = posicion or {}
        lotes = lotes or []

        _push("position", {"posicion": posicion, "lotes": lotes, "vehiculo": vehiculo}, symbol=symbol)
        _push("current", {"symbol": symbol})
        _tv_current["symbol"] = symbol

        # sincroniza lista de símbolos
        if _symbols_fn:
            try:
                _push("symbols", {"symbols": sorted(_symbols_fn())})
            except Exception:
                pass

        # sincroniza balance USDT si disponible
        if _balance_fn:
            try:
                _push("balance", {"usdt_free": float(_balance_fn())})
            except Exception:
                pass

        tv_symbol = _tv_symbol(symbol, vehiculo)
        tv_activo = _is_tv_active()
        if not tv_activo:
            webbrowser.open(f"https://www.tradingview.com/chart/?symbol={tv_symbol}")
        _logger.warning(f"TradingView {'navegado por Tampermonkey' if tv_activo else 'abierto'}: {symbol} ({vehiculo})")
    except Exception as e:
        _logger.error(f"abrir_tradingview({symbol}): {e}")
