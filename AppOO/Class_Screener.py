from Modulos_Mysql import MarketScreen, BDsystem
from Modulos_Utilitarios import style_app, is_null, is_none, mask_numero
from Class_customer import CustomTreeview
from Modulos_python import (
    tk,
    ttk,
    W,
    S,
    N,
    E,
    VERTICAL,
    HORIZONTAL,
    io,
    ImageTk,
    Image,
    messagebox,
    datetime,
    timezone,
    time,
    requests,
    UserAgent,
    ThreadPoolExecutor,
)


def _yahoo_session():
    """Obtiene cookie + crumb para autenticar requests a Yahoo Finance.
    Usa headers de navegador real para evitar 401/429. Reintenta hasta 3 veces."""
    ua = UserAgent().random
    session = requests.Session()
    session.headers.update({
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    })
    crumb = ""
    for attempt in range(3):
        try:
            session.get("https://finance.yahoo.com/", timeout=10)
            time.sleep(1)
            r = session.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=10)
            if r.ok and r.text.strip():
                crumb = r.text.strip()
                break
            print(f"  [yahoo_session] intento {attempt + 1}: crumb vacío (HTTP {r.status_code})")
            time.sleep(2)
        except Exception as e:
            print(f"  [yahoo_session] intento {attempt + 1} error: {e}")
            time.sleep(2)
    # Actualizar Accept a JSON para las llamadas API
    session.headers.update({"Accept": "application/json"})
    if not crumb:
        print("  [yahoo_session] WARN: crumb no obtenido — las requests pueden devolver 401")
    return session, crumb


class Screener(tk.Frame):
    def __init__(self, master=None, account=None, colors=None):
        super().__init__(master)
        self.root = ttk.Frame(master, padding=(1, 1, 1, 1), style="B.TFrame")
        self.account = account
        self.colors = colors
        self.config(bg="black")
        self.s_country = None
        self.s_sector = None
        self.s_tipo = "Dividends"
        self.s_beta = None
        self.s_market = None
        self.s_entry = None
        self.s_encartera = False
        self.tree = None
        self.panel = None
        self.options = None
        self.wi20 = None
        self.root.pack(side=tk.LEFT)
        self.market = None
        self.counter = 0
        self.ix = []
        self.ctree = []  # poblado en widgets_screener vía _COL_DEFS
        self.ctree_widget = None  # instancia CustomTreeview

        # Accesos MySql ----------------------------------------------------------------------------------------------
        self.ScMarket = MarketScreen()

        self.start()

    # Start Screener
    def start(self):
        # carga de datos e insert treeview
        self.market, self.ix = self.ScMarket.select(
            account=self.account,
            tipo=self.s_tipo,
            country=self.s_country,
            sector=self.s_sector,
            name=self.s_entry,
            symbol=self.s_entry,
        )

        self.widgets_screener()
        self.update_screener()

    def widgets_screener(self):

        def item_selected(event):
            for selected_item in self.ctree_widget.tree_fixed.selection():
                item = self.ctree_widget.tree_fixed.item(selected_item)
                record = item["values"]
                if not is_none(record[0]):
                    ticket = record[0].strip()
                    name = record[1]
                    # evaluar_fila(vehiculo='Stock', empresa=name, ticket=ticket)

        def sort_treeview(tree, col, reverse):
            xlis = [(tree.set(k, col), k) for k in tree.get_children("")]
            xlis.sort(reverse=reverse)

            # Reordenar los elementos en el treeview
            for index, (val, k) in enumerate(xlis):
                tree.move(k, "", index)

            tree.heading(
                col, text=col, command=lambda: sort_treeview(tree, col, not reverse)
            )
            i = 0
            for item in tree.get_children():
                xtag = "even" if i % 2 == 0 else "odd"
                tree.item(item, tags=(xtag,))
                i += 1

        def get_select(*args):
            self.s_tipo = tipo.get()
            self.s_beta = beta.get()
            self.s_entry = entry.get()
            self.s_market = mkt_c.get()
            self.s_encartera = encartera_var.get()

            self.s_beta = self.s_beta if not is_null(self.s_beta) else None
            self.s_entry = self.s_entry if not is_null(self.s_entry) else None
            self.s_market = self.s_market if not is_null(self.s_market) else None

        def update_window(tipo):

            if tipo == "reset":
                self.s_country = None
                self.s_sector = None
                self.s_tipo = "Dividends"
                self.s_beta = None
                self.s_market = None
                self.s_entry = None
                self.s_encartera = False
                encartera_var.set(False)

            self.after(1, self.update_screener)

        def country_select(event):
            try:
                seleccion = event.widget.curselection()
                if seleccion:
                    indice = seleccion[0]
                    self.s_country = event.widget.get(indice)
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def sector_select(event):
            try:
                seleccion = event.widget.curselection()
                if seleccion:
                    indice = seleccion[0]
                    self.s_sector = event.widget.get(indice)
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def filtra_x_beta(s_beta):
            pass  # no-op — pendiente de implementar con ctree_widget

        try:

            self.win = ttk.Frame(self.root, padding=(5, 5, 5, 5), style="B.TFrame")
            self.panel = ttk.Frame(self.win, padding=(5, 5, 5, 5), style="B.TFrame")
            self.options = ttk.Frame(self.win, padding=(5, 5, 5, 5), style="C.TFrame")
            self.win.pack(fill=tk.BOTH)
            self.options.pack(
                side=tk.RIGHT, fill=tk.Y
            )  # options PRIMERO → se reserva espacio derecho
            self.panel.pack(
                side=tk.LEFT, fill=tk.BOTH, expand=True
            )  # panel llena lo restante

            # --- CustomTreeview con columnas fijas ---
            _FIXED = ["symbol", "shortName", "categoriaActivo", "encartera"]
            _COL_DEFS = [
                # (db_field, header, width, anchor)
                ("symbol", "Symbol", 70, "w"),
                ("shortName", "Name", 200, "w"),
                ("categoriaActivo", "Status", 45, "center"),
                ("encartera", "Cart", 35, "center"),
                ("country", "Country", 100, "w"),
                ("sector", "Sector", 120, "w"),
                ("industry", "Industry", 160, "w"),
                ("currency", "Cur", 35, "center"),
                ("lastPrice", "Last", 70, "e"),
                ("previousClose", "Prev", 70, "e"),
                ("open", "Open", 70, "e"),
                ("fiftyTwoWeekHigh", "52W H", 70, "e"),
                ("fiftyTwoWeekLow", "52W L", 70, "e"),
                ("fiftyDayAverage", "50D Avg", 70, "e"),
                ("twoHundredDayAverage", "200D Avg", 70, "e"),
                ("ema20", "EMA20", 70, "e"),
                ("ema50", "EMA50", 70, "e"),
                ("ema100", "EMA100", 70, "e"),
                ("ema200", "EMA200", 70, "e"),
                ("marketCap", "Mkt Cap", 85, "e"),
                ("volume", "Volume", 80, "e"),
                ("averageVolume", "Avg Vol", 80, "e"),
                ("beta", "Beta", 55, "e"),
                ("trailingPE", "P/E", 60, "e"),
                ("forwardPE", "Fwd P/E", 65, "e"),
                ("priceToBook", "P/B", 55, "e"),
                ("pegRatio", "PEG", 55, "e"),
                ("trailingPegRatio", "T-PEG", 55, "e"),
                ("trailingEps", "EPS", 60, "e"),
                ("forwardEps", "Fwd EPS", 65, "e"),
                ("dividendRate", "Div $", 65, "e"),
                ("dividendYield", "Div %", 65, "e"),
                ("exDividendDate", "ExDiv", 75, "w"),
                ("payoutRatio", "Payout", 65, "e"),
                ("fiveYearAvgDividendYield", "5Y Yield", 65, "e"),
                ("trailingAnnualDividendRate", "Ann Div $", 70, "e"),
                ("trailingAnnualDividendYield", "Ann Div %", 70, "e"),
                ("lastDividendValue", "Last Div", 65, "e"),
                ("nextDividend", "Next Div", 65, "e"),
                ("ttmDividends", "TTM Div", 65, "e"),
                ("targetHighPrice", "Tgt High", 70, "e"),
                ("targetLowPrice", "Tgt Low", 70, "e"),
                ("targetMeanPrice", "Tgt Mean", 70, "e"),
                ("returnOnEquity", "ROE", 60, "e"),
                ("returnOnAssets", "ROA", 60, "e"),
                ("earningsGrowth", "E Growth", 70, "e"),
                ("revenueGrowth", "R Growth", 70, "e"),
                ("freeCashflow", "Free CF", 80, "e"),
                ("grossMargins", "Gross M", 65, "e"),
                ("ebitdaMargins", "EBITDA M", 70, "e"),
                ("operatingMargins", "Op M", 60, "e"),
                ("totalDebt", "Total Debt", 85, "e"),
                ("lastFiscalYearEnd", "FY End", 75, "w"),
                ("firstTradeDateEpochUtc", "IPO", 75, "w"),
                ("financialCurrency", "Fin Cur", 55, "center"),
                ("website", "Website", 200, "w"),
            ]
            self.ctree = [c[0] for c in _COL_DEFS]
            col_align = {
                col_id: {"anchor": anc, "width": w} for col_id, _, w, anc in _COL_DEFS
            }

            # Prevenir que self.panel se expanda por las columnas del treeview (3500px+)
            self.panel.pack_propagate(False)

            # Frame contenedor en grid dentro de self.panel
            tree_frame = ttk.Frame(self.panel, style="B.TFrame")
            tree_frame.grid(
                column=0, row=6, columnspan=3, rowspan=4, sticky=(N, S, E, W)
            )
            self.panel.columnconfigure(
                0, weight=1
            )  # tree_frame llena el ancho del panel

            self.ctree_widget = CustomTreeview(
                master=tree_frame,
                columns=self.ctree,
                fixed_columns=_FIXED,
                show_vscroll=True,
                show_hscroll=True,
                sort_columns=True,
                height=27,
                column_alignments=col_align,
                show_headings=True,
            )

            # Sobrescribir heading text y anchor (CustomTreeview pone text=col_id por defecto)
            # También fijar stretch=NO para que el scrollbar horizontal funcione
            for col_id, col_text, col_width, col_anchor in _COL_DEFS:
                _t = (
                    self.ctree_widget.tree_fixed
                    if col_id in _FIXED
                    else self.ctree_widget.tree_scroll
                )
                _t.heading(col_id, text=col_text, anchor=col_anchor)
                _t.column(
                    col_id,
                    width=col_width,
                    minwidth=max(30, col_width // 2),
                    stretch=tk.NO,
                )

            self.ctree_widget.tree_fixed.bind("<<TreeviewSelect>>", item_selected)

            # set position of all above objects by pack panel
            imagen_tk = BDsystem.select_image(idd=200, size=(32, 32))

            entry = ttk.Entry(
                self.panel,
                width=58,
                justify="left",
                font=("Arial", 22),
                style="C.TButton",
            )
            search = tk.Button(
                self.panel,
                image=imagen_tk,
                bg=self.colors["bgcolor"],
                relief=tk.FLAT,
                command=lambda: self.update_screener,
            )
            search.imagen = imagen_tk
            entry.grid(column=1, row=0, columnspan=3, pady=5)
            search.grid(column=0, row=0, sticky=E, pady=5)
            entry.bind("<KeyRelease>", get_select)

            self.insert_treeview()

            # Windows 2 (right)
            self.wi20 = ttk.Frame(self.options, padding=(5, 5, 5, 5), style="C.TFrame")
            self.wi20.grid(column=0, row=20, padx=0, pady=10, sticky=(N, S, E, W))
            apply = tk.Button(
                self.wi20,
                text="Apply",
                width=6,
                bg="gray",
                fg="white",
                command=lambda: update_window("apply"),
            )
            reset = tk.Button(
                self.wi20,
                text="Reset",
                width=6,
                bg="gray",
                fg="white",
                command=lambda: update_window("reset"),
            )

            # filtro tipo de activo rnb1
            tipo = tk.StringVar()
            tipo.set(self.s_tipo)
            tipo.trace("w", get_select)
            encartera_var = tk.BooleanVar()
            encartera_var.set(self.s_encartera)
            encartera_var.trace("w", get_select)
            tp1 = ttk.Label(self.options, text="TIPO DE ACTIVO ::", style="C.TLabel")
            tp2 = ttk.Radiobutton(
                self.options,
                text="Stock Dividends",
                variable=tipo,
                value="Dividends",
                style="C.TRadiobutton",
            )
            tp3 = ttk.Radiobutton(
                self.options,
                text="Stock Trend",
                variable=tipo,
                value="Trend",
                style="C.TRadiobutton",
            )
            tp4 = ttk.Radiobutton(
                self.options,
                text="ETF's Funds",
                variable=tipo,
                value="ETF",
                style="C.TRadiobutton",
            )
            tp5 = ttk.Checkbutton(
                self.options,
                text="En Cartera",
                variable=encartera_var,
                style="C.TRadiobutton",
            )

            tp1.grid(column=0, row=0, sticky=W, pady=1)
            tp2.grid(column=0, row=1, sticky=W, padx=10)
            tp3.grid(column=0, row=2, sticky=W, padx=10)
            tp4.grid(column=0, row=3, sticky=W, padx=10)
            tp5.grid(column=0, row=4, sticky=W, padx=10)

            # filtro Beta de activo rnb2
            beta = tk.StringVar()
            beta.set(self.s_beta)
            beta.trace("w", get_select)
            bt1 = ttk.Label(self.options, text="BETA ::", style="C.TLabel")
            bt2 = ttk.Radiobutton(
                self.options,
                text="Low (<0.5)",
                variable=beta,
                value="Low",
                style="C.TRadiobutton",
            )
            bt3 = ttk.Radiobutton(
                self.options,
                text="Medium (0.5-1.5)",
                variable=beta,
                value="Medium",
                style="C.TRadiobutton",
            )
            bt4 = ttk.Radiobutton(
                self.options,
                text="High (>1.5)",
                variable=beta,
                value="High",
                style="C.TRadiobutton",
            )

            bt1.grid(column=0, row=5, sticky=W, pady=10)
            bt2.grid(column=0, row=6, sticky=W, padx=10)
            bt3.grid(column=0, row=7, sticky=W, padx=10)
            bt4.grid(column=0, row=8, sticky=W, padx=10)

            # filtro Market CAP de activo rnb3
            mkt_c = tk.StringVar()
            mkt_c.set(self.s_market)
            mkt_c.trace("w", get_select)
            mt1 = ttk.Label(self.options, text="MARKET CAP ::", style="C.TLabel")
            mt2 = ttk.Radiobutton(
                self.options,
                text="Mega (>$200B)",
                variable=mkt_c,
                value="Mega",
                style="C.TRadiobutton",
            )
            mt3 = ttk.Radiobutton(
                self.options,
                text="Large ($10B-$200B)",
                variable=mkt_c,
                value="Large",
                style="C.TRadiobutton",
            )
            mt4 = ttk.Radiobutton(
                self.options,
                text="Medium ($2B-$10B)",
                variable=mkt_c,
                value="Medium",
                style="C.TRadiobutton",
            )
            mt5 = ttk.Radiobutton(
                self.options,
                text="Small ($300M-$2B)",
                variable=mkt_c,
                value="Small",
                style="C.TRadiobutton",
            )
            mt6 = ttk.Radiobutton(
                self.options,
                text="Micro ($50M-$300M)",
                variable=mkt_c,
                value="Micro",
                style="C.TRadiobutton",
            )
            mt7 = ttk.Radiobutton(
                self.options,
                text="Nano (<$50M)",
                variable=mkt_c,
                value="Nano",
                style="C.TRadiobutton",
            )

            mt1.grid(column=0, row=9, sticky=W, pady=10)
            mt2.grid(column=0, row=10, sticky=W, padx=10)
            mt3.grid(column=0, row=11, sticky=W, padx=10)
            mt4.grid(column=0, row=12, sticky=W, padx=10)
            mt5.grid(column=0, row=13, sticky=W, padx=10)
            mt6.grid(column=0, row=14, sticky=W, padx=10)
            mt7.grid(column=0, row=15, sticky=W, padx=10)

            # filtro sector rnb4
            st1 = ttk.Label(self.options, text="SECTOR ::", style="C.TLabel")
            sector = tk.Listbox(self.options, width=24, height=5)
            sector.bind("<<ListboxSelect>>", sector_select)
            s_scroll = ttk.Scrollbar(
                self.options, orient=tk.VERTICAL, command=sector.yview
            )
            sector.config(yscrollcommand=s_scroll.set)
            st1.grid(column=0, row=16, sticky=W, pady=10)
            sector.grid(column=0, row=17, sticky=W, padx=10)
            s_scroll.grid(column=1, row=17, sticky=(W, N + S))

            d_sector, d_country = self.sector_country()
            sector.insert(tk.END, "None")
            for keys in d_sector:
                sector.insert(tk.END, keys)

            # filtro country rnb5
            ct1 = ttk.Label(self.options, text="COUNTRY ::", style="C.TLabel")
            country = tk.Listbox(self.options, width=24, height=5)
            country.bind("<<ListboxSelect>>", country_select)
            c_scroll = ttk.Scrollbar(
                self.options, orient=tk.VERTICAL, command=country.yview
            )
            country.config(yscrollcommand=c_scroll.set)

            country.insert(tk.END, "None")
            for keys in d_country:
                country.insert(tk.END, keys)

            ct1.grid(column=0, row=18, sticky=W, pady=10)
            country.grid(column=0, row=19, sticky=W, padx=10)
            c_scroll.grid(column=1, row=19, sticky=(W, N + S))

            apply.grid(column=0, row=20, sticky=E, padx=20, pady=20)
            reset.grid(column=1, row=20, sticky=E, columnspa=2, pady=20)
        except EncodingWarning as e:
            print("widgets_screener(): {}".format(e))

    def update_screener(self):

        self.filtra_seleccion()

        d_sector, d_country = self.sector_country()

        self.after(9000000, self.update_screener)

    def sector_country(self) -> list:
        s_datos, c_datos = list(), list()
        for keys in self.market:
            if not is_null(keys[self.ix.index("sector")]):
                if keys[self.ix.index("sector")] not in s_datos:
                    s_datos.append(keys[self.ix.index("sector")])

            if not is_none(keys[self.ix.index("country")]):
                if keys[self.ix.index("country")] not in c_datos:
                    c_datos.append(keys[self.ix.index("country")])

        return s_datos, c_datos

    # carga datos en treeview()
    def insert_treeview(self):
        self.counter = 0
        ix = self.ix

        def _g(key):
            try:
                v = keys[ix.index(key)]
                return v if not is_none(v) else None
            except (ValueError, IndexError):
                return None

        def _price(v):
            return f"{v:.2f}" if v is not None else ""

        def _pct(v):
            return f"{v:.2%}" if v is not None else ""

        def _big(v):
            return mask_numero(v or 0) if v is not None else ""

        def _date(v):
            try:
                return f"{v:%y-%b-%d}" if v else ""
            except:
                return str(v) if v else ""

        for keys in self.market:
            self.ctree_widget.insert_row(
                values=(
                    _g("symbol") or "",
                    _g("shortName") or "",
                    _g("categoriaActivo") or "",
                    _g("encartera") or "",
                    _g("country") or "",
                    _g("sector") or "",
                    _g("industry") or "",
                    _g("currency") or "",
                    _price(_g("lastPrice")),
                    _price(_g("previousClose")),
                    _price(_g("open")),
                    _price(_g("fiftyTwoWeekHigh")),
                    _price(_g("fiftyTwoWeekLow")),
                    _price(_g("fiftyDayAverage")),
                    _price(_g("twoHundredDayAverage")),
                    _price(_g("ema20")),
                    _price(_g("ema50")),
                    _price(_g("ema100")),
                    _price(_g("ema200")),
                    _big(_g("marketCap")),
                    _big(_g("volume")),
                    _big(_g("averageVolume")),
                    _price(_g("beta")),
                    _price(_g("trailingPE")),
                    _price(_g("forwardPE")),
                    _price(_g("priceToBook")),
                    _price(_g("pegRatio")),
                    _price(_g("trailingPegRatio")),
                    _price(_g("trailingEps")),
                    _price(_g("forwardEps")),
                    _price(_g("dividendRate")),
                    _pct(_g("dividendYield")),
                    _date(_g("exDividendDate")),
                    _pct(_g("payoutRatio")),
                    _price(_g("fiveYearAvgDividendYield")),
                    _price(_g("trailingAnnualDividendRate")),
                    _pct(_g("trailingAnnualDividendYield")),
                    _price(_g("lastDividendValue")),
                    _price(_g("nextDividend")),
                    _price(_g("ttmDividends")),
                    _price(_g("targetHighPrice")),
                    _price(_g("targetLowPrice")),
                    _price(_g("targetMeanPrice")),
                    _pct(_g("returnOnEquity")),
                    _pct(_g("returnOnAssets")),
                    _pct(_g("earningsGrowth")),
                    _pct(_g("revenueGrowth")),
                    _big(_g("freeCashflow")),
                    _pct(_g("grossMargins")),
                    _pct(_g("ebitdaMargins")),
                    _pct(_g("operatingMargins")),
                    _big(_g("totalDebt")),
                    _date(_g("lastFiscalYearEnd")),
                    _date(_g("firstTradeDateEpochUtc")),
                    _g("financialCurrency") or "",
                    _g("website") or "",
                )
            )
            self.counter += 1

    # elimina datos de treeview()
    def delete_items_treeview(self):
        self.ctree_widget.delete_row()

    # controla que se muestren los datos seleccionados en el screener
    def filtra_seleccion(self):

        (self.market, self.ix) = self.ScMarket.select(
            account=self.account,
            tipo=self.s_tipo,
            country=self.s_country,
            sector=self.s_sector,
            name=self.s_entry,
            symbol=self.s_entry,
        )

        if self.s_encartera:
            ec_idx = self.ix.index("encartera")
            self.market = [row for row in self.market if row[ec_idx] == "Y"]

        self.delete_items_treeview()
        self.insert_treeview()

        if not is_none(self.s_beta):
            pass

        if not is_none(self.s_market):
            pass


def sync_market(account):
    """
    Sincroniza la tabla market en 3 fases:
      Phase 1 — NASDAQ : descubre símbolos nuevos de dividendos (INSERT mínimo)
      Phase 2 — Yahoo Quote      : actualiza precio/mercado para todos (batch 250, paralelo)
      Phase 3 — Yahoo Fundamentals: actualiza sector/dividendos/financieros (paralelo)
    Los campos de datos los provee Yahoo; NASDAQ solo sirve para descubrimiento.
    """
    _QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
    _FUND_URL = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{}"
    _FUND_MODULES = "summaryDetail,defaultKeyStatistics,financialData,assetProfile"
    _session, _crumb = _yahoo_session()

    # ── helpers comunes ──────────────────────────────────────────────────────
    def _chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    def _safe_float(val):
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    def _safe_date(val):
        if val is None:
            return None
        try:
            if isinstance(val, (int, float)):
                return datetime.fromtimestamp(val, tz=timezone.utc).date()
            return str(val)[:10]
        except Exception:
            return None

    # ── Phase 1: NASDAQ discovery ────────────────────────────────────────────
    def _nasdaq_fetch():
        ua = UserAgent()
        headers = {"User-Agent": ua.random, "Accept": "application/json"}
        base_url = (
            "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=5000"
        )
        rows, offset = [], 0
        while True:
            resp = requests.get(
                f"{base_url}&offset={offset}", headers=headers, timeout=30
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            # La API puede devolver rows en data.table.rows o directamente en data.rows
            table = data.get("table") or data
            page = table.get("rows") or []
            rows.extend(page)
            total = int(data.get("totalrecords") or 0)
            offset += len(page)
            if not page or offset >= total:
                break
        return rows

    def _is_dividend_candidate(row):
        sector = row.get("sector", "") or ""
        industry = row.get("industry", "") or ""
        name = row.get("name", "") or ""
        return sector == "Real Estate" or "REIT" in industry or "Trust" in name

    # ── Phase 2: Yahoo Quote ─────────────────────────────────────────────────
    def _fetch_quote_batch(symbols):
        time.sleep(1.0)  # 1 s entre batches para respetar rate limit de Yahoo
        try:
            resp = _session.get(
                _QUOTE_URL,
                params={"symbols": ",".join(symbols), "crumb": _crumb},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("quoteResponse", {}).get("result", [])
        except Exception:
            return []

    def _map_quote(s):
        campos = [
            "shortName",
            "lastPrice",
            "previousClose",
            "open",
            "volume",
            "marketCap",
            "currency",
            "averageVolume",
            "fiftyTwoWeekHigh",
            "fiftyTwoWeekLow",
            "fiftyDayAverage",
            "twoHundredDayAverage",
            "trailingPE",
            "forwardPE",
            "trailingEps",
            "beta",
        ]
        valores = [
            str(s.get("shortName") or "")[:60],
            _safe_float(s.get("regularMarketPrice")),
            _safe_float(s.get("regularMarketPreviousClose")),
            _safe_float(s.get("regularMarketOpen")),
            _safe_float(s.get("regularMarketVolume")),
            _safe_float(s.get("marketCap")),
            str(s.get("currency") or "")[:6],
            _safe_float(s.get("averageDailyVolume3Month")),
            _safe_float(s.get("fiftyTwoWeekHigh")),
            _safe_float(s.get("fiftyTwoWeekLow")),
            _safe_float(s.get("fiftyDayAverage")),
            _safe_float(s.get("twoHundredDayAverage")),
            _safe_float(s.get("trailingPE")),
            _safe_float(s.get("forwardPE")),
            _safe_float(s.get("epsTrailingTwelveMonths")),
            _safe_float(s.get("beta")),
        ]
        return campos, valores

    # ── Phase 3: Yahoo Fundamentals ──────────────────────────────────────────
    def _fetch_fundamentals(symbol):
        time.sleep(0.5)  # 0.5 s entre requests para respetar rate limit de Yahoo
        try:
            resp = _session.get(
                _FUND_URL.format(symbol),
                params={"modules": _FUND_MODULES, "crumb": _crumb},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json().get("quoteSummary", {}).get("result", [{}])[0]
            sd = data.get("summaryDetail", {})
            ks = data.get("defaultKeyStatistics", {})
            fd = data.get("financialData", {})
            ap = data.get("assetProfile", {})

            campos = [
                "sector",
                "industry",
                "country",
                "dividendRate",
                "dividendYield",
                "exDividendDate",
                "payoutRatio",
                "fiveYearAvgDividendYield",
                "trailingAnnualDividendRate",
                "trailingAnnualDividendYield",
                "pegRatio",
                "priceToBook",
                "forwardEps",
                "trailingPegRatio",
                "lastFiscalYearEnd",
                "firstTradeDateEpochUtc",
                "targetHighPrice",
                "targetLowPrice",
                "targetMeanPrice",
                "returnOnAssets",
                "returnOnEquity",
                "earningsGrowth",
                "revenueGrowth",
                "freeCashflow",
                "grossMargins",
                "ebitdaMargins",
                "operatingMargins",
                "financialCurrency",
                "website",
            ]
            valores = [
                str(ap.get("sector") or "")[:50],
                str(ap.get("industry") or "")[:80],
                str(ap.get("country") or "")[:50],
                _safe_float(sd.get("dividendRate", {}).get("raw")),
                _safe_float(sd.get("dividendYield", {}).get("raw")),
                _safe_date(sd.get("exDividendDate", {}).get("raw")),
                _safe_float(sd.get("payoutRatio", {}).get("raw")),
                _safe_float(sd.get("fiveYearAvgDividendYield", {}).get("raw")),
                _safe_float(sd.get("trailingAnnualDividendRate", {}).get("raw")),
                _safe_float(sd.get("trailingAnnualDividendYield", {}).get("raw")),
                _safe_float(ks.get("pegRatio", {}).get("raw")),
                _safe_float(ks.get("priceToBook", {}).get("raw")),
                _safe_float(ks.get("forwardEps", {}).get("raw")),
                _safe_float(ks.get("trailingPegRatio", {}).get("raw")),
                _safe_date(ks.get("lastFiscalYearEnd", {}).get("raw")),
                _safe_date(ks.get("firstTradeDateEpochUtc", {}).get("raw")),
                _safe_float(fd.get("targetHighPrice", {}).get("raw")),
                _safe_float(fd.get("targetLowPrice", {}).get("raw")),
                _safe_float(fd.get("targetMeanPrice", {}).get("raw")),
                _safe_float(fd.get("returnOnAssets", {}).get("raw")),
                _safe_float(fd.get("returnOnEquity", {}).get("raw")),
                _safe_float(fd.get("earningsGrowth", {}).get("raw")),
                _safe_float(fd.get("revenueGrowth", {}).get("raw")),
                _safe_float(fd.get("freeCashflow", {}).get("raw")),
                _safe_float(fd.get("grossMargins", {}).get("raw")),
                _safe_float(fd.get("ebitdaMargins", {}).get("raw")),
                _safe_float(fd.get("operatingMargins", {}).get("raw")),
                str(fd.get("financialCurrency") or "")[:6],
                str(ap.get("website") or "")[:200],
            ]
            return campos, valores
        except Exception:
            return [], []

    # ── Ejecución ────────────────────────────────────────────────────────────
    market = MarketScreen()
    existing = market.load_symbols(account=account)

    # Phase 1: NASDAQ — solo INSERT símbolos nuevos (Yahoo proveerá los datos)
    rows = _nasdaq_fetch()
    insertados, omitidos = 0, 0
    for row in rows:
        if not _is_dividend_candidate(row):
            continue
        symbol = (row.get("symbol", "") or "").strip()
        if not symbol:
            continue
        if symbol not in existing:
            market.insert(
                upd=["account", "tipo"], val=[account, "Dividends"], symbol=symbol
            )
            existing[symbol] = "N"  # disponible para fases 2 y 3
            insertados += 1
        elif existing[symbol] in ("I", "S", "X"):
            omitidos += 1

    # Phase 2: Yahoo Quote — todos los símbolos, batches de 250
    all_symbols = list(existing.keys())
    quote_ok = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        for page in ex.map(_fetch_quote_batch, list(_chunks(all_symbols, 250))):
            for s in page:
                symbol = s.get("symbol", "").strip()
                if not symbol or existing.get(symbol) in ("I", "S", "X"):
                    continue
                campos, valores = _map_quote(s)
                market.update(upd=campos, val=valores, symbol=symbol)
                quote_ok += 1

    # Phase 3: Yahoo Fundamentals — símbolos activos, paralelo
    active_symbols = [s for s, cat in existing.items() if cat not in ("I", "S", "X")]
    fund_ok = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(_fetch_fundamentals, sym): sym for sym in active_symbols}
        for future, symbol in futures.items():
            campos, valores = future.result()
            if campos:
                market.update(upd=campos, val=valores, symbol=symbol)
                fund_ok += 1

    return {
        "descargados": len(rows),
        "insertados": insertados,
        "omitidos": omitidos,
        "quote_actualizados": quote_ok,
        "fund_actualizados": fund_ok,
    }


def cleanup_market(account):
    """
    Valida y completa todos los símbolos de la tabla market contra Yahoo Finance.
    - Actualiza campos de quote (precio, mercado) para símbolos devueltos por Yahoo.
    - Elimina símbolos NO devueltos por Yahoo, SALVO los que están en cartera (encartera='Y').
    - Completa campos vacíos (country, shortName) con datos de Yahoo Fundamentals.
    - Batches que fallan (429 u otro error) se omiten sin eliminar nada.
    """
    _QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
    _FUND_URL = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{}"
    _FUND_MODULES = "summaryDetail,defaultKeyStatistics,financialData,assetProfile"
    def _chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    def _safe_float(val):
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    def _safe_date(val):
        if val is None:
            return None
        try:
            if isinstance(val, (int, float)):
                return datetime.fromtimestamp(val, tz=timezone.utc).date()
            return str(val)[:10]
        except Exception:
            return None

    _session, _crumb = _yahoo_session()

    def _map_quote(s):
        campos = [
            "shortName", "lastPrice", "previousClose", "open", "volume",
            "marketCap", "currency", "averageVolume", "fiftyTwoWeekHigh",
            "fiftyTwoWeekLow", "fiftyDayAverage", "twoHundredDayAverage",
            "trailingPE", "forwardPE", "trailingEps", "beta",
        ]
        valores = [
            str(s.get("shortName") or "")[:60],
            _safe_float(s.get("regularMarketPrice")),
            _safe_float(s.get("regularMarketPreviousClose")),
            _safe_float(s.get("regularMarketOpen")),
            _safe_float(s.get("regularMarketVolume")),
            _safe_float(s.get("marketCap")),
            str(s.get("currency") or "")[:6],
            _safe_float(s.get("averageDailyVolume3Month")),
            _safe_float(s.get("fiftyTwoWeekHigh")),
            _safe_float(s.get("fiftyTwoWeekLow")),
            _safe_float(s.get("fiftyDayAverage")),
            _safe_float(s.get("twoHundredDayAverage")),
            _safe_float(s.get("trailingPE")),
            _safe_float(s.get("forwardPE")),
            _safe_float(s.get("epsTrailingTwelveMonths")),
            _safe_float(s.get("beta")),
        ]
        return campos, valores

    def _fetch_fundamentals(symbol):
        time.sleep(0.5)
        try:
            resp = _session.get(
                _FUND_URL.format(symbol),
                params={"modules": _FUND_MODULES, "crumb": _crumb},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json().get("quoteSummary", {}).get("result", [{}])[0]
            sd = data.get("summaryDetail", {})
            ks = data.get("defaultKeyStatistics", {})
            fd = data.get("financialData", {})
            ap = data.get("assetProfile", {})
            campos = [
                "sector", "industry", "country", "dividendRate", "dividendYield",
                "exDividendDate", "payoutRatio", "fiveYearAvgDividendYield",
                "trailingAnnualDividendRate", "trailingAnnualDividendYield",
                "pegRatio", "priceToBook", "forwardEps", "trailingPegRatio",
                "lastFiscalYearEnd", "firstTradeDateEpochUtc", "targetHighPrice",
                "targetLowPrice", "targetMeanPrice", "returnOnAssets", "returnOnEquity",
                "earningsGrowth", "revenueGrowth", "freeCashflow", "grossMargins",
                "ebitdaMargins", "operatingMargins", "financialCurrency", "website",
            ]
            valores = [
                str(ap.get("sector") or "")[:50],
                str(ap.get("industry") or "")[:80],
                str(ap.get("country") or "")[:50],
                _safe_float(sd.get("dividendRate", {}).get("raw")),
                _safe_float(sd.get("dividendYield", {}).get("raw")),
                _safe_date(sd.get("exDividendDate", {}).get("raw")),
                _safe_float(sd.get("payoutRatio", {}).get("raw")),
                _safe_float(sd.get("fiveYearAvgDividendYield", {}).get("raw")),
                _safe_float(sd.get("trailingAnnualDividendRate", {}).get("raw")),
                _safe_float(sd.get("trailingAnnualDividendYield", {}).get("raw")),
                _safe_float(ks.get("pegRatio", {}).get("raw")),
                _safe_float(ks.get("priceToBook", {}).get("raw")),
                _safe_float(ks.get("forwardEps", {}).get("raw")),
                _safe_float(ks.get("trailingPegRatio", {}).get("raw")),
                _safe_date(ks.get("lastFiscalYearEnd", {}).get("raw")),
                _safe_date(ks.get("firstTradeDateEpochUtc", {}).get("raw")),
                _safe_float(fd.get("targetHighPrice", {}).get("raw")),
                _safe_float(fd.get("targetLowPrice", {}).get("raw")),
                _safe_float(fd.get("targetMeanPrice", {}).get("raw")),
                _safe_float(fd.get("returnOnAssets", {}).get("raw")),
                _safe_float(fd.get("returnOnEquity", {}).get("raw")),
                _safe_float(fd.get("earningsGrowth", {}).get("raw")),
                _safe_float(fd.get("revenueGrowth", {}).get("raw")),
                _safe_float(fd.get("freeCashflow", {}).get("raw")),
                _safe_float(fd.get("grossMargins", {}).get("raw")),
                _safe_float(fd.get("ebitdaMargins", {}).get("raw")),
                _safe_float(fd.get("operatingMargins", {}).get("raw")),
                str(fd.get("financialCurrency") or "")[:6],
                str(ap.get("website") or "")[:200],
            ]
            return campos, valores
        except Exception:
            return [], []

    market = MarketScreen()
    rows, ix = market.select(account=account, tipo="Dividends") or ([], [])
    existing = {}
    for row in (rows or []):
        d = dict(zip(ix, row))
        existing[d["symbol"]] = {
            "categoriaActivo": d.get("categoriaActivo"),
            "encartera": d.get("encartera"),
            "shortName": d.get("shortName"),
            "country": d.get("country"),
        }
    all_symbols = list(existing.keys())

    # ── Phase 1: Quote — actualizar precios y detectar no encontrados ─────────
    not_found = []
    batches_ok = 0
    quote_ok = 0

    for batch in _chunks(all_symbols, 250):
        time.sleep(1.0)
        try:
            resp = _session.get(
                _QUOTE_URL,
                params={"symbols": ",".join(batch), "crumb": _crumb},
                timeout=15,
            )
            if not resp.ok:
                print(f"  batch skip HTTP {resp.status_code} — no se procesan {len(batch)} símbolos")
                continue
            result = resp.json().get("quoteResponse", {}).get("result", [])
            returned = {s["symbol"] for s in result}
            batches_ok += 1
            # Actualizar todos los devueltos (incluye encartera sin dividendos)
            for s in result:
                sym = s.get("symbol", "").strip()
                if not sym:
                    continue
                campos, valores = _map_quote(s)
                market.update(upd=campos, val=valores, symbol=sym)
                quote_ok += 1
            # Detectar no encontrados en este batch
            for sym in batch:
                if sym not in returned:
                    not_found.append(sym)
        except Exception as e:
            print(f"  batch skip (error: {e}) — no se procesan {len(batch)} símbolos")
            continue

    # ── Phase 2: Eliminar no encontrados, salvo los que están en cartera ──────
    eliminados = 0
    salvados = 0
    for sym in not_found:
        info = existing.get(sym, {})
        if info.get("encartera") == "Y":
            salvados += 1
            print(f"  en cartera — no eliminado: {sym}")
        else:
            market.delete(symbol=sym, account=account)
            eliminados += 1
            print(f"  eliminado: {sym}")

    # ── Phase 3: Fundamentals — completar campos vacíos ───────────────────────
    needs_fund = [
        sym for sym, info in existing.items()
        if not (info.get("country") or "").strip() or not (info.get("shortName") or "").strip()
    ]
    fund_ok = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(_fetch_fundamentals, sym): sym for sym in needs_fund}
        for future, symbol in futures.items():
            campos, valores = future.result()
            if campos:
                market.update(upd=campos, val=valores, symbol=symbol)
                fund_ok += 1

    return {
        "total": len(all_symbols),
        "batches_ok": batches_ok,
        "quote_actualizados": quote_ok,
        "eliminados": eliminados,
        "en_cartera_salvados": salvados,
        "fund_completados": fund_ok,
    }


if __name__ == "__main__":
    print("Iniciando cleanup_market ...")
    result = cleanup_market(account="U4214563")
    print(f"  total símbolos      : {result['total']}")
    print(f"  batches exitosos    : {result['batches_ok']}")
    print(f"  quote actualizados  : {result['quote_actualizados']}")
    print(f"  eliminados          : {result['eliminados']}")
    print(f"  en cartera salvados : {result['en_cartera_salvados']}")
    print(f"  fund completados    : {result['fund_completados']}")
    print("cleanup_market completado.")
