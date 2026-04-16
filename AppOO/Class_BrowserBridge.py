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
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
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
        else:
            self._send_json({"error": "not found"}, 404)


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
            _tv_server.server_close()
        except Exception:
            pass
        _tv_server = None
        _logger.warning("TradingView server detenido")


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
