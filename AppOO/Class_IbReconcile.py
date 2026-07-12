from Modulos_python import ET, csv, pd


class Class_IbReconcile:
    """
    Parsea IB Activity Statement CSVs o Flex Query CSVs y reconcilia posiciones
    contra booktrading para detectar y corregir discrepancias de stock.

    Uso típico:
        rec = Class_IbReconcile(DataHub.db)
        df  = rec.reconcile("B0000001", "2025-01-01",
                             "path/2025.csv", "path/2026_flex.csv")
        rec.print_report(df)
        for sql in rec.fix_sqls(df):
            print(sql)
    """

    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _detect_format(self, path: str) -> str:
        """Detecta formato del archivo: 'xml', 'flex_csv' o 'activity'."""
        with open(path, encoding="utf-8-sig", newline="") as f:
            first = f.readline().lstrip()
        if first.startswith("<?xml") or first.startswith("<FlexQuery"):
            return "xml"
        if "ClientAccountID" in first or "CurrencyPrimary" in first:
            return "flex_csv"
        return "activity"

    def _parse_activity_statement(self, path: str) -> pd.DataFrame:
        """Parsea IB Activity Statement CSV (formato sección-based)."""
        _RENAME = {
            "Asset Category": "asset_category",
            "Currency": "currency",
            "Symbol": "symbol",
            "Date/Time": "datetime",
            "Quantity": "quantity",
            "T. Price": "price",
            "Comm/Fee": "commission",
            "Realized P/L": "realized_pl",
        }
        header = None
        rows = []
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 3 or row[0] != "Trades":
                    continue
                if row[1] == "Header" and row[2] == "DataDiscriminator":
                    header = row[2:]
                elif row[1] == "Data" and row[2] == "Trade" and header is not None:
                    rows.append(row[2:])

        if not rows or header is None:
            return pd.DataFrame()

        ncols = max(len(r) for r in rows)
        hdr = (header + ["_x"] * ncols)[:ncols]
        rows = [r + [""] * (ncols - len(r)) for r in rows]
        df = pd.DataFrame(rows, columns=hdr)
        df.rename(columns=_RENAME, inplace=True)
        df = df[df.get("asset_category", pd.Series()) == "Stocks"].copy()
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df["commission"] = pd.to_numeric(df.get("commission", 0), errors="coerce").fillna(0)
        df["datetime"] = pd.to_datetime(df["datetime"], format="%Y-%m-%d, %H:%M:%S", errors="coerce")
        df["idtrans"] = None
        return df

    def _parse_flex_csv(self, path: str) -> pd.DataFrame:
        """
        Parsea IB Flex Query CSV (formato plano con header en primera línea).
        DateTime: YYYYMMDD;HHmmss. Quantity negativa para SELL.
        Incluye TransactionID → idtrans (match exacto con booktrading).
        """
        _RENAME = {
            "CurrencyPrimary": "currency",
            "Symbol": "symbol",
            "DateTime": "datetime",
            "Quantity": "quantity",
            "TradePrice": "price",
            "IBCommission": "commission",
            "FifoPnlRealized": "realized_pl",
            "TransactionID": "idtrans",
        }
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
        df.rename(columns=_RENAME, inplace=True)
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df["commission"] = pd.to_numeric(df.get("commission", 0), errors="coerce").fillna(0).abs()
        df["datetime"] = pd.to_datetime(df["datetime"], format="%Y%m%d;%H%M%S", errors="coerce")
        df["idtrans"] = df["idtrans"].astype(str).str.strip()
        df = df[df["quantity"].notna() & (df["quantity"] != 0)].copy()
        return df

    def _parse_flex_xml(self, path: str) -> pd.DataFrame:
        """Parsea un archivo XML de IB Flex Query."""
        from Class_IbFlex import _XML_ATTR
        tree = ET.parse(path)
        rows = []
        for trade in tree.getroot().iter("Trade"):
            row = {internal: trade.get(xml_attr, "")
                   for xml_attr, internal in _XML_ATTR.items()}
            rows.append(row)
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df.rename(columns={"account_id": "_ib_account"}, inplace=True)
        df["quantity"]   = pd.to_numeric(df["quantity"],   errors="coerce")
        df["price"]      = pd.to_numeric(df["price"],      errors="coerce")
        df["commission"] = pd.to_numeric(df["commission"], errors="coerce").fillna(0).abs()
        df["datetime"]   = pd.to_datetime(df["datetime"],  format="%Y%m%d;%H%M%S", errors="coerce")
        df["idtrans"]    = df["idtrans"].astype(str).str.strip()
        return df[df["quantity"].notna() & (df["quantity"] != 0)].copy()

    def parse_trades(self, *csv_paths) -> pd.DataFrame:
        """
        Parsea uno o más archivos IB (XML Flex, CSV Flex o Activity Statement, auto-detectado).
        Retorna DataFrame normalizado con columnas:
            symbol, currency, datetime, quantity, price, commission, idtrans
        """
        frames = []
        for path in csv_paths:
            fmt = self._detect_format(path)
            if fmt == "xml":
                df = self._parse_flex_xml(path)
            elif fmt == "flex_csv":
                df = self._parse_flex_csv(path)
            else:
                df = self._parse_activity_statement(path)
            if not df.empty:
                frames.append(df)

        if not frames:
            return pd.DataFrame()

        cols = ["symbol", "currency", "datetime", "quantity", "price", "commission", "idtrans"]
        result = pd.concat(frames, ignore_index=True)
        for c in cols:
            if c not in result.columns:
                result[c] = None
        return result[cols].reset_index(drop=True)

    # ------------------------------------------------------------------
    # Reconciliación principal
    # ------------------------------------------------------------------

    def reconcile(self, account: str, period_start: str, *csv_paths,
                  exclude: set = None) -> pd.DataFrame:
        """
        Reconcilia posiciones IB vs booktrading para todos los símbolos del CSV.

        account      : cuenta de booktrading (ej: 'B0000001')
        period_start : fecha de inicio del primer CSV (ej: '2025-01-01')
                       — se usa para obtener el stock previo en booktrading
        csv_paths    : uno o más paths a IB Activity Statement CSV
        exclude      : set de símbolos a omitir (default: CORPORATE_ACTION_SYMBOLS)

        Retorna DataFrame con columnas:
            symbol, currency, bt_start, ib_net, expected, bt_current, bt_id, diff, status
        """
        if exclude is None:
            exclude = self.CORPORATE_ACTION_SYMBOLS
        df = self.parse_trades(*csv_paths)
        if df.empty:
            return pd.DataFrame()

        net = (
            df.groupby(["currency", "symbol"])["quantity"]
            .sum()
            .reset_index()
            .rename(columns={"quantity": "ib_net"})
        )

        results = []
        for _, row in net.iterrows():
            symbol = row["symbol"]
            if symbol in exclude:
                continue
            currency = row["currency"]
            ib_net = row["ib_net"]

            bt_start = self.db.get_bt_stock_before(account, symbol, currency, period_start)
            bt_id, bt_current = self.db.get_bt_latest_stock(account, symbol, currency)

            expected = round((bt_start or 0) + ib_net, 4)
            current = bt_current or 0
            diff = round(expected - current, 4)

            results.append({
                "symbol": symbol,
                "currency": currency,
                "bt_start": bt_start if bt_start is not None else 0,
                "ib_net": ib_net,
                "expected": expected,
                "bt_current": current,
                "bt_id": bt_id,
                "diff": diff,
                "status": "OK" if abs(diff) < 0.001 else f"DIFF {diff:+.0f}",
            })

        return pd.DataFrame(results).sort_values("diff", key=abs, ascending=False).reset_index(drop=True)

    # Símbolos excluidos del reconcile automático — 3 categorías:
    # 1. Splits: Agente_SplitsControl (yfinance) ya los aplica en booktrading.
    #    IB Flex Trades no registra la conversión del split (solo en Corporate Actions),
    #    por lo que el IB net siempre difiere del booktrading post-split.
    # 2. Ticker renames: viejo y nuevo son el mismo activo, diffs se cancelan entre sí.
    # 3. Sin registro en booktrading: delisted, quiebras o crypto fuera de scope.
    CORPORATE_ACTION_SYMBOLS = {
        # splits — booktrading correcto via Agente_SplitsControl, IB Flex incompleto
        "WKHS", "WKHS.NEW", "CTRM", "CHPT", "TLRY", "SNDL",
        # ticker renames (viejo → nuevo)
        "MPW", "MPT", "SKLZ", "FIRY", "NEP", "XIFR", "GOLD", "B",
        # delisted / quiebra / sin booktrading
        "GOEV", "GOEVQ", "CFRX", "SSUP", "BGFV", "SUP", "GHSI", "TORO",
        # crypto fuera de scope
        "MATIC.USD-PAXOS", "ETH.USD-PAXOS", "BTC.USD-PAXOS",
    }

    def reconcile_from_db(self, account: str, period_start: str,
                          period_end: str = None,
                          exclude: set = None) -> pd.DataFrame:
        """
        Igual que reconcile() pero lee los trades de ib_flex_trades en lugar de CSV.
        Requiere que la tabla esté poblada via Class_IbFlex.import_to_db().

        account      : cuenta booktrading (ej: 'B0000001')
        period_start : fecha inicio 'YYYY-MM-DD'
        period_end   : fecha fin  'YYYY-MM-DD' (opcional, por defecto hoy)
        exclude      : set de símbolos a omitir (default: CORPORATE_ACTION_SYMBOLS)
        """
        if exclude is None:
            exclude = self.CORPORATE_ACTION_SYMBOLS
        ib_account = self.db.get_sesion_ib_account(account) if hasattr(self.db, "get_sesion_ib_account") else "U4214563"
        net_rows = self.db.get_ib_trades_net(ib_account, period_start, period_end)
        if not net_rows:
            return pd.DataFrame()

        results = []
        for row in net_rows:
            symbol   = row["symbol"]
            if symbol in exclude:
                continue
            currency = row["currency"]
            ib_net   = float(row["ib_net"])

            bt_start          = self.db.get_bt_stock_before(account, symbol, currency, period_start)
            bt_id, bt_current = self.db.get_bt_latest_stock(account, symbol, currency)

            expected = round((bt_start or 0) + ib_net, 4)
            current  = bt_current or 0
            diff     = round(expected - current, 4)

            results.append({
                "symbol":     symbol,
                "currency":   currency,
                "bt_start":   bt_start if bt_start is not None else 0,
                "ib_net":     ib_net,
                "expected":   expected,
                "bt_current": current,
                "bt_id":      bt_id,
                "diff":       diff,
                "status":     "OK" if abs(diff) < 0.001 else f"DIFF {diff:+.0f}",
            })

        return pd.DataFrame(results).sort_values("diff", key=abs, ascending=False).reset_index(drop=True)

    # ------------------------------------------------------------------
    # Herramientas de corrección
    # ------------------------------------------------------------------

    def fix_sqls(self, df: pd.DataFrame) -> list:
        """
        Genera sentencias UPDATE para los registros con diff != 0.
        Revisar antes de ejecutar — el UPDATE solo corrige 'stock', no los lotes.
        """
        sqls = []
        for _, row in df[df["diff"].abs() > 0.001].iterrows():
            if row["bt_id"] is None:
                sqls.append(f"-- {row['symbol']}: sin registro activo en booktrading (bt_id es NULL)")
                continue
            sqls.append(
                f"UPDATE booktrading SET stock = {row['expected']:.4f} WHERE id = {row['bt_id']};"
                f"  -- {row['symbol']} diff={row['diff']:+.0f} ({row['bt_current']:.0f} → {row['expected']:.0f})"
            )
        return sqls

    def apply_fix(self, df: pd.DataFrame, db_write) -> dict:
        """
        Aplica los UPDATE directamente en DB para los registros con diff != 0.
        db_write: conexión MySQL (cursor con autocommit o conn.cursor())
        Retorna dict {symbol: resultado}.
        NO llamar sin confirmar fix_sqls() primero.
        """
        results = {}
        for _, row in df[df["diff"].abs() > 0.001].iterrows():
            symbol = row["symbol"]
            if row["bt_id"] is None:
                results[symbol] = "SKIP — bt_id NULL"
                continue
            try:
                db_write.execute(
                    "UPDATE booktrading SET stock = %s WHERE id = %s",
                    (row["expected"], row["bt_id"]),
                )
                results[symbol] = f"OK — stock={row['expected']:.4f} (id={row['bt_id']})"
            except Exception as e:
                results[symbol] = f"ERROR — {e}"
        return results

    # ------------------------------------------------------------------
    # Corrección
    # ------------------------------------------------------------------

    def find_missing_trades(self, account: str, symbol: str, divisa: str, df_csv: pd.DataFrame) -> pd.DataFrame:
        """
        Devuelve trades del CSV que NO están en booktrading.
        Si el CSV incluye idtrans (Flex format): match exacto por idtrans.
        Si no (Activity Statement): match fuzzy por fecha/qty/precio.
        """
        sym_trades = df_csv[df_csv["symbol"] == symbol].copy()
        missing = []
        has_idtrans = "idtrans" in sym_trades.columns and sym_trades["idtrans"].notna().any()
        for _, row in sym_trades.iterrows():
            idtrans = str(row.get("idtrans", "") or "").strip()
            if has_idtrans and idtrans and idtrans != "nan":
                found = self.db.exists_bt_trade_by_idtrans(account, symbol, divisa, idtrans)
            else:
                found = self.db.exists_bt_trade(account, symbol, divisa,
                                                row["datetime"], row["quantity"], row["price"])
            if not found:
                missing.append(row)
        return pd.DataFrame(missing)

    def fix_symbols(self, account: str, df_reconcile: pd.DataFrame,
                    df_csv: pd.DataFrame) -> list:
        """
        Para cada símbolo con diff != 0:
          1. Detecta si hay trades faltantes en booktrading.
          2. Si los hay: los inserta via raw_insert_bt_trade.
          3. Siempre recalcula la cadena de stock completa.

        Retorna lista de dicts con el resultado por símbolo.
        """
        results = []
        diffs = df_reconcile[df_reconcile["diff"].abs() > 0.001]

        for _, row in diffs.iterrows():
            symbol = row["symbol"]
            divisa = row["currency"]
            inserted = 0

            missing = self.find_missing_trades(account, symbol, divisa, df_csv)

            if not missing.empty:
                missing_sorted = missing.sort_values("datetime")
                for _, t in missing_sorted.iterrows():
                    comm = pd.to_numeric(t.get("commission", 0), errors="coerce") or 0.0
                    idtrans_val = str(t.get("idtrans", "") or "").strip()
                    idtrans_val = None if idtrans_val in ("", "nan", "None") else idtrans_val
                    ok = self.db.raw_insert_bt_trade(
                        account=account,
                        symbol=symbol,
                        divisa=divisa,
                        fechahora=t["datetime"],
                        cantidad=t["quantity"],
                        precio=t["price"],
                        commission=abs(comm),
                        idtrans=idtrans_val,
                    )
                    if ok:
                        inserted += 1

            updated = self.db.recalculate_stock_chain(account, symbol, divisa)

            _, new_stock = self.db.get_bt_latest_stock(account, symbol, divisa)
            results.append({
                "symbol": symbol,
                "currency": divisa,
                "diff_before": row["diff"],
                "inserted": inserted,
                "rows_updated": updated,
                "new_stock": new_stock,
                "expected": row["expected"],
                "ok": abs((new_stock or 0) - row["expected"]) < 0.001,
            })

        return results

    # ------------------------------------------------------------------
    # Reporte
    # ------------------------------------------------------------------

    def print_report(self, df: pd.DataFrame):
        """Imprime la tabla de reconciliación, diferencias primero."""
        if df.empty:
            print("[IbReconcile] Sin datos para reportar.")
            return
        diffs = df[df["diff"].abs() > 0.001]
        ok = df[df["diff"].abs() <= 0.001]
        print(f"\n{'─'*72}")
        print(f"  IB RECONCILE — {len(df)} símbolos | DIFF: {len(diffs)} | OK: {len(ok)}")
        print(f"{'─'*72}")
        cols = ["symbol", "currency", "bt_start", "ib_net", "expected", "bt_current", "diff", "status"]
        print(df[cols].to_string(index=False))
        print(f"{'─'*72}")
        if not diffs.empty:
            print("\nSQL de corrección:")
            for sql in self.fix_sqls(diffs):
                print(f"  {sql}")
        print()
