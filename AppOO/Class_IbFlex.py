import io
import logging
import time

from Modulos_python import ET, pd, requests

_logger = logging.getLogger("IbFlex")


_BASE_URL = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService"
_SEND_URL = _BASE_URL + "/SendRequest"
_GET_URL  = _BASE_URL + "/GetStatement"

# Mapeo atributos XML → nombres internos (snake_case)
_XML_ATTR = {
    "accountId":        "account_id",
    "currency":         "currency",
    "symbol":           "symbol",
    "description":      "description",
    "conid":            "conid",
    "dateTime":         "datetime",
    "tradeDate":        "trade_date",
    "quantity":         "quantity",
    "tradePrice":       "price",
    "tradeMoney":       "trade_money",
    "proceeds":         "proceeds",
    "taxes":            "taxes",
    "ibCommission":     "commission",
    "closePrice":       "close_price",
    "costBasis":        "cost_basis",
    "mtmPnl":           "mtm_pnl",
    "fifoPnlRealized":  "realized_pnl",
    "capitalGainsPnl":  "capital_gains_pnl",
    "fxPnl":            "fx_pnl",
    "fxRateToBase":     "fx_rate",
    "buySell":          "buy_sell",
    "transactionID":    "idtrans",
    "transactionType":  "transaction_type",
    "brokerageOrderID": "order_id",
    "orderReference":   "order_reference",
}


class Class_IbFlex:
    """
    Descarga reportes Flex de IB via Web Service (2 pasos) en formato XML.

    Paso 1 — SendRequest: solicita el reporte → devuelve referenceCode
    Paso 2 — GetStatement: descarga el XML usando referenceCode

    Uso:
        flex = Class_IbFlex(token="...", query_id="...")
        df   = flex.download()                      # DataFrame normalizado
        flex.save_raw("tmp/flex.xml")               # guarda el XML crudo
    """

    def __init__(self, token: str, query_id: str):
        self.token    = str(token).strip()
        self.query_id = str(query_id).strip()

    # ------------------------------------------------------------------
    # Descarga HTTP
    # ------------------------------------------------------------------

    _HEADERS = {"User-Agent": "Python/3"}

    def _send_request(self) -> tuple:
        """Paso 1: solicita el reporte. Retorna (referenceCode, get_url)."""
        resp = requests.get(
            _SEND_URL,
            params={"t": self.token, "q": self.query_id, "v": "3"},
            headers=self._HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.text.strip()
        _logger.debug(f"SendRequest respuesta: {text[:400]}")
        if "<Status>Success</Status>" not in text:
            raise RuntimeError(f"IB Flex SendRequest error: {text[:300]}")
        ref_start = text.find("<ReferenceCode>") + len("<ReferenceCode>")
        ref_end   = text.find("</ReferenceCode>")
        if ref_start < len("<ReferenceCode>") or ref_end < 0:
            raise RuntimeError(f"No ReferenceCode en respuesta: {text[:300]}")
        ref = text[ref_start:ref_end].strip()
        url_start = text.find("<Url>") + len("<Url>")
        url_end   = text.find("</Url>")
        get_url   = text[url_start:url_end].strip() if url_start > len("<Url>") and url_end > 0 else _GET_URL
        _logger.debug(f"ReferenceCode={ref}  GetURL={get_url}")
        return ref, get_url

    def _get_statement(self, reference_code: str, get_url: str,
                       retries: int = 8, delay: int = 10) -> str:
        """Paso 2: descarga el reporte. Requiere token + reference code + User-Agent."""
        time.sleep(delay)
        for attempt in range(1, retries + 1):
            resp = requests.get(
                get_url,
                params={"t": self.token, "q": reference_code, "v": "3"},
                headers=self._HEADERS,
                timeout=60,
            )
            resp.raise_for_status()
            text = resp.text.strip()
            # 1020 = token/código expirado — no tiene sentido reintentar
            if "<ErrorCode>1020</ErrorCode>" in text:
                _logger.error("IB Flex token vencido (1020) — renovar en IB Portal → Reports → Flex Queries → Settings")
                raise RuntimeError(f"IB Flex 1020 — token vencido: {text[:300]}")
            # 1019 = reporte aún procesando — reintentar
            if "<ErrorCode>1019</ErrorCode>" in text:
                _logger.debug(f"intento {attempt}/{retries} — reporte procesando, reintentando...")
                if attempt < retries:
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"IB Flex: reporte no disponible tras {retries} intentos")
            if "<ErrorCode>" in text:
                raise RuntimeError(f"IB Flex GetStatement error: {text[:300]}")
            return text
        raise RuntimeError("IB Flex: no se pudo obtener el reporte")

    def download_raw(self) -> str:
        """Descarga el reporte Flex crudo. Usa la URL que IB devuelve en SendRequest."""
        ref, get_url = self._send_request()
        return self._get_statement(ref, get_url)

    # ------------------------------------------------------------------
    # Parsing XML
    # ------------------------------------------------------------------

    def _parse_xml(self, raw: str) -> pd.DataFrame:
        """
        Parsea el XML de IB Flex y retorna DataFrame normalizado.
        Extrae todos los elementos <Trade> dentro de <Trades>.
        """
        root = ET.fromstring(raw)
        rows = []
        for trade in root.iter("Trade"):
            row = {internal: trade.get(xml_attr, "")
                   for xml_attr, internal in _XML_ATTR.items()}
            rows.append(row)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df["quantity"]   = pd.to_numeric(df["quantity"],   errors="coerce")
        df["price"]      = pd.to_numeric(df["price"],      errors="coerce")
        df["commission"] = pd.to_numeric(df["commission"], errors="coerce").fillna(0).abs()
        df["datetime"]   = pd.to_datetime(df["datetime"],  format="%Y%m%d;%H%M%S", errors="coerce")
        df["idtrans"]    = df["idtrans"].astype(str).str.strip()
        df["buy_sell"]   = df["buy_sell"].str.upper()
        return df[df["quantity"].notna() & (df["quantity"] != 0)].copy()

    def _parse_csv(self, raw: str) -> pd.DataFrame:
        """Parsea respuesta CSV del Flex API (mismo formato que descarga manual)."""
        df = pd.read_csv(io.StringIO(raw), dtype=str)
        _RENAME = {
            "CurrencyPrimary": "currency",
            "Symbol":          "symbol",
            "DateTime":        "datetime",
            "Quantity":        "quantity",
            "TradePrice":      "price",
            "IBCommission":    "commission",
            "FifoPnlRealized": "realized_pl",
            "TransactionID":   "idtrans",
        }
        df.rename(columns=_RENAME, inplace=True)
        df["quantity"]   = pd.to_numeric(df["quantity"],   errors="coerce")
        df["price"]      = pd.to_numeric(df["price"],      errors="coerce")
        df["commission"] = pd.to_numeric(df.get("commission", 0), errors="coerce").fillna(0).abs()
        df["datetime"]   = pd.to_datetime(df["datetime"], format="%Y%m%d;%H%M%S", errors="coerce")
        df["idtrans"]    = df["idtrans"].astype(str).str.strip()
        return df[df["quantity"].notna() & (df["quantity"] != 0)].copy()

    def _parse_response(self, raw: str) -> pd.DataFrame:
        """Auto-detecta XML o CSV y parsea correctamente."""
        if raw.lstrip().startswith("<"):
            return self._parse_xml(raw)
        return self._parse_csv(raw)

    def download(self) -> pd.DataFrame:
        """
        Descarga el reporte Flex y retorna DataFrame normalizado.
        Auto-detecta XML o CSV según la configuración del query en IB.
        Columnas clave: symbol, currency, datetime, quantity, price, commission, idtrans
        """
        return self._parse_response(self.download_raw())

    def parse_file(self, path: str) -> pd.DataFrame:
        """Parsea un archivo local XML o CSV (auto-detectado)."""
        with open(path, encoding="utf-8-sig") as f:
            raw = f.read()
        return self._parse_response(raw)

    def import_from_file(self, db, account_id: str, path: str) -> dict:
        """Importa trades desde un archivo local (CSV o XML) a ib_flex_trades."""
        with open(path, encoding="utf-8-sig") as f:
            raw = f.read()
        return self.import_to_db(db, account_id, raw=raw)

    def save_raw(self, path: str, raw: str = None):
        """Guarda el XML crudo en disco. Si raw no se pasa, descarga primero."""
        if raw is None:
            raw = self.download_raw()
        with open(path, "w", encoding="utf-8") as f:
            f.write(raw)

    # ------------------------------------------------------------------
    # Importación a DB
    # ------------------------------------------------------------------

    def _rows_for_db(self, raw: str):
        """
        Retorna lista de dicts normalizados para INSERT en ib_flex_trades.
        Maneja tanto CSV (columnas PascalCase) como XML (atributos camelCase → snake_case).
        """
        is_xml = raw.lstrip().startswith("<")
        if is_xml:
            rows = []
            for trade in ET.fromstring(raw).iter("Trade"):
                rows.append({internal: trade.get(attr, "")
                              for attr, internal in _XML_ATTR.items()})
            return rows
        # CSV — leer con nombres originales
        df = pd.read_csv(io.StringIO(raw), dtype=str).fillna("")
        result = []
        for _, r in df.iterrows():
            qty = _dec(r.get("Quantity"))
            if qty is None or qty == 0:
                continue
            result.append({
                "idtrans":          r.get("TransactionID", "").strip(),
                "symbol":           r.get("Symbol", "").strip(),
                "currency":         r.get("CurrencyPrimary", "").strip(),
                "conid":            r.get("Conid", "").strip(),
                "description":      r.get("Description", "").strip(),
                "datetime":         r.get("DateTime", "").strip(),
                "trade_date":       r.get("TradeDate", "").strip(),
                "quantity":         r.get("Quantity", "").strip(),
                "price":            r.get("TradePrice", "").strip(),
                "trade_money":      r.get("TradeMoney", "").strip(),
                "proceeds":         r.get("Proceeds", "").strip(),
                "taxes":            r.get("Taxes", "").strip(),
                "commission":       r.get("IBCommission", "").strip(),
                "close_price":      r.get("ClosePrice", "").strip(),
                "cost_basis":       r.get("CostBasis", "").strip(),
                "mtm_pnl":         r.get("MtmPnl", "").strip(),
                "realized_pnl":    r.get("FifoPnlRealized", "").strip(),
                "capital_gains_pnl": r.get("CapitalGainsPnl", "").strip(),
                "fx_pnl":          r.get("FxPnl", "").strip(),
                "fx_rate":         r.get("FXRateToBase", "").strip(),
                "buy_sell":        r.get("Buy/Sell", "BUY").strip().upper(),
                "transaction_type": r.get("TransactionType", "").strip(),
                "order_id":        r.get("BrokerageOrderID", "").strip(),
                "order_reference": r.get("OrderReference", "").strip(),
            })
        return result

    def import_to_db(self, db, account_id: str, raw: str = None) -> dict:
        """
        Descarga (o usa raw ya descargado) e importa todos los trades a ib_flex_trades.
        Usa INSERT IGNORE en transaction_id → idempotente (reejecutar es seguro).

        db         : RepositorioOportunidadesBuySell
        account_id : ej. 'U4214563'
        raw        : contenido ya descargado/leído (opcional — evita segunda descarga)
        Retorna dict con {total, inserted, skipped}.
        """
        if raw is None:
            raw = self.download_raw()
        rows = self._rows_for_db(raw)

        total = inserted = skipped = 0
        conn = db._conectar(tabla="insert.ib_flex_trades")
        cursor = None
        try:
            cursor = conn.cursor()
            for r in rows:
                total += 1
                try:
                    cursor.execute(
                        """INSERT IGNORE INTO ib_flex_trades
                           (transaction_id, account_id, symbol, currency, conid, description,
                            trade_datetime, trade_date, quantity, price, trade_money, proceeds,
                            taxes, commission, close_price, cost_basis, mtm_pnl, realized_pnl,
                            capital_gains_pnl, fx_pnl, fx_rate, buy_sell, transaction_type,
                            order_id, order_reference)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            _int(r.get("idtrans")),
                            account_id,
                            r.get("symbol", "").strip(),
                            r.get("currency", "").strip(),
                            _int(r.get("conid")),
                            r.get("description", "").strip() or None,
                            _dt(r.get("datetime")),
                            _date(r.get("trade_date")),
                            _dec(r.get("quantity")),
                            _dec(r.get("price")),
                            _dec(r.get("trade_money")),
                            _dec(r.get("proceeds")),
                            _dec(r.get("taxes"), 0),
                            abs(_dec(r.get("commission"), 0)),
                            _dec(r.get("close_price")),
                            _dec(r.get("cost_basis")),
                            _dec(r.get("mtm_pnl")),
                            _dec(r.get("realized_pnl")),
                            _dec(r.get("capital_gains_pnl")),
                            _dec(r.get("fx_pnl")),
                            _dec(r.get("fx_rate")),
                            r.get("buy_sell", "BUY").strip().upper(),
                            r.get("transaction_type", "").strip() or None,
                            r.get("order_id", "").strip() or None,
                            r.get("order_reference", "").strip() or None,
                        ),
                    )
                    if cursor.rowcount:
                        inserted += 1
                    else:
                        skipped += 1
                except Exception as e:
                    skipped += 1
                    print(f"[IbFlex import] fila {total} ({r.get('symbol')}) error: {e}")
            conn.commit()
        finally:
            if cursor:
                cursor.close()
            conn.close()
        return {"total": total, "inserted": inserted, "skipped": skipped}


# ------------------------------------------------------------------
# Helpers de conversión
# ------------------------------------------------------------------

def _dec(val, default=None):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

def _int(val, default=None):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default

def _dt(val):
    try:
        return pd.to_datetime(str(val), format="%Y%m%d;%H%M%S").to_pydatetime()
    except Exception:
        return None

def _date(val):
    try:
        v = str(val).strip()
        return f"{v[:4]}-{v[4:6]}-{v[6:8]}"
    except Exception:
        return None
