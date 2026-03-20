from Modulos_Mysql import MarketScreen, BDsystem
from Modulos_Utilitarios import style_app, is_null, is_none, mask_numero, define_FileCache
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
    re,
    requests,
    UserAgent,
    ThreadPoolExecutor,
    logging,
    yf,
    math,
    pd,
    EmptyDataError,
)

_logger = logging.getLogger("Screener")

def _yahoo_session():
    """Obtiene cookie + crumb para autenticar requests a Yahoo Finance.
    Nuevo flujo: fc.yahoo.com primero (cambia de autenticación Yahoo ~2024).
    Fallback a finance.yahoo.com. Alterna query1/query2 para el crumb."""
    _INIT_URLS = [
        "https://fc.yahoo.com",
        "https://finance.yahoo.com/",
    ]
    _CRUMB_URLS = [
        "https://query1.finance.yahoo.com/v1/test/getcrumb",
        "https://query2.finance.yahoo.com/v1/test/getcrumb",
    ]
    ua = UserAgent().random
    session = requests.Session()
    session.headers.update({
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    crumb = ""
    _BACKOFF = [0, 30, 90]  # segundos de espera antes de cada intento
    for attempt in range(3):
        try:
            if _BACKOFF[attempt]:
                _logger.warning(f"[yahoo_session] backoff {_BACKOFF[attempt]}s antes de intento {attempt + 1}")
                time.sleep(_BACKOFF[attempt])
            # Obtener cookies — probar fc.yahoo.com primero (nuevo flujo)
            for init_url in _INIT_URLS:
                try:
                    session.get(init_url, timeout=10)
                    break
                except Exception:
                    continue
            time.sleep(3)
            session.headers.update({"Referer": "https://finance.yahoo.com/"})
            # Intentar obtener crumb alternando entre query1 y query2
            got_429 = False
            for crumb_url in _CRUMB_URLS:
                try:
                    r = session.get(crumb_url, timeout=10)
                    if r.ok and r.text.strip():
                        crumb = r.text.strip()
                        break
                    if r.status_code == 429:
                        got_429 = True
                    _logger.warning(f"[yahoo_session] intento {attempt + 1} ({crumb_url[-7:]}): HTTP {r.status_code}")
                except Exception as e:
                    _logger.warning(f"[yahoo_session] intento {attempt + 1}: {e}")
            if crumb:
                break
            if got_429 and attempt < 2:
                _logger.warning(f"[yahoo_session] 429 detectado — esperando {_BACKOFF[attempt + 1]}s")
        except Exception as e:
            _logger.warning(f"[yahoo_session] intento {attempt + 1} error: {e}")
    session.headers.update({"Accept": "application/json"})
    if not crumb:
        _logger.error("[yahoo_session] crumb no obtenido — las requests pueden devolver 401")
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
                ("inst_score", "Inst Score", 75, "e"),
                ("inst_ownership_pct", "Inst %", 65, "e"),
                ("fh_count", "13F Funds", 65, "e"),
                ("fh_total_value", "13F Value", 90, "e"),
                ("inst_top_holder", "Top Holder", 160, "w"),
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

            # Los tk.Frame internos de CustomTreeview no heredan ttk styles — forzar bg negro
            self.ctree_widget.master.configure(bg="black")
            self.ctree_widget.heard.configure(bg="black")
            self.ctree_widget.right.configure(bg="black")

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

            btn_frame = ttk.Frame(self.panel, style="B.TFrame")
            btn_frame.grid(column=0, row=10, columnspan=3, sticky=W, padx=8, pady=(6, 4))

            ttk.Button(
                btn_frame,
                text="Inst. Intro",
                style="C.TButton",
                command=self._show_institucionales_cartera,
            ).pack(side=tk.LEFT, padx=(0, 6))

            ttk.Button(
                btn_frame,
                text="Inst. Out",
                style="C.TButton",
                state=tk.DISABLED,
            ).pack(side=tk.LEFT)
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
                    _price(_g("inst_score")),
                    _pct(_g("inst_ownership_pct")),
                    str(_g("fh_count")) if _g("fh_count") else "",
                    _big(_g("fh_total_value")),
                    _g("inst_top_holder") or "",
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

    def _show_institucionales_cartera(self):
        _TAG_ORDER = {"CUADRUPLE": 0, "TRIPLE": 1, "ALINEADO": 2, "DIVERGE": 3, "ALERTA": 4, "NEUTRO": 5}

        def _senal_inst(inst_score, fh_buy_ratio, fh_count):
            score = inst_score or 0.0
            buy_r = fh_buy_ratio or 0.0
            count = fh_count or 0
            if score >= 0.4 and buy_r >= 0.5 and count >= 20:
                return "ACOMPAÑAR"
            elif score >= 0.25 or count >= 10:
                return "MANTENER"
            else:
                return "REVISAR"

        def _read_csv_signals(filename):
            try:
                path = define_FileCache(name=f"{filename}.CSV")
                df = pd.read_csv(path, header=0, sep=",", encoding="utf-8", index_col=False)
                df.columns = df.columns.str.strip()
                return set(df["Symbol"].dropna().str.strip().tolist()) if "Symbol" in df.columns else set()
            except (EmptyDataError, FileNotFoundError):
                return set()
            except Exception:
                return set()

        def _senal_analyst(rec):
            mapa = {
                "strong_buy":  "▲▲ FUERTE",
                "buy":         "▲ COMPRAR",
                "hold":        "→ MANTENER",
                "sell":        "▼ VENDER",
                "strong_sell": "▼▼ FUERTE",
            }
            return mapa.get((rec or "").lower().replace(" ", "_"), "")

        def _alineacion(senal_inst, en_buy, en_sell, rec, categ):
            bullish_analyst = rec in ("strong_buy", "buy")
            bearish_analyst = rec in ("sell", "strong_sell")
            bullish_inst    = senal_inst == "ACOMPAÑAR"
            bearish_inst    = senal_inst == "REVISAR"
            bullish_div     = categ == "I"
            bearish_div     = categ == "S"
            has_div         = categ not in ("X", None, "")

            # 4 fuentes alineadas (solo cuando div aplica)
            if has_div and bullish_inst and en_buy and bullish_analyst and bullish_div:
                return "★ CUÁDRUPLE BUY"
            if has_div and bearish_inst and en_sell and bearish_analyst and bearish_div:
                return "★ CUÁDRUPLE SELL"
            # 3 fuentes — inst + analyst + modelo
            if bullish_inst and en_buy and bullish_analyst:
                return "✓✓ TRIPLE BUY"
            if bearish_inst and en_sell and bearish_analyst:
                return "✓✓ TRIPLE SELL"
            # 3 fuentes — inst + modelo + div
            if has_div and bullish_inst and en_buy and bullish_div:
                return "✓✓ TRIPLE BUY"
            if has_div and bearish_inst and en_sell and bearish_div:
                return "✓✓ TRIPLE SELL"
            # 3 fuentes — inst + analyst + div
            if has_div and bullish_inst and bullish_analyst and bullish_div:
                return "✓✓ TRIPLE BUY"
            if has_div and bearish_inst and bearish_analyst and bearish_div:
                return "✓✓ TRIPLE SELL"
            # 2 fuentes — inst + modelo
            if bullish_inst and en_buy:
                return "✓ INST+MOD BUY"
            if bearish_inst and en_sell:
                return "✓ INST+MOD SELL"
            # 2 fuentes — inst + analista
            if bullish_inst and bullish_analyst:
                return "✓ INST+ANA BUY"
            if bearish_inst and bearish_analyst:
                return "✓ INST+ANA SELL"
            # 2 fuentes — inst + div
            if has_div and bullish_inst and bullish_div:
                return "✓ INST+DIV BUY"
            if has_div and bearish_inst and bearish_div:
                return "✓ INST+DIV SELL"
            # Divergencias
            if bullish_inst and en_sell:
                return "⚠ DIVERGE"
            if bearish_inst and en_buy:
                return "⚠ ALERTA"
            return "— NEUTRO"

        cartera = self.ScMarket.load_cartera_inst(self.account)
        fh_stats = self.ScMarket.load_fund_holdings_stats()
        syms_buy = _read_csv_signals("csv_datosIA_buy")
        syms_sell = _read_csv_signals("csv_datosIA_sell")

        # Construir filas y ordenar por prioridad de alineación
        filas = []
        for row in cartera:
            if (row.get("categoriaActivo") or "") == "X":
                continue
            sym = row["symbol"]
            stats = fh_stats.get(sym, {})
            fh_buy_ratio  = stats.get("fh_buy_ratio", 0.0)
            fh_sell_ratio = stats.get("fh_sell_ratio", 0.0)
            rec    = (row.get("analyst_rec") or "").lower().replace(" ", "_")
            categ  = row.get("categoriaActivo") or ""
            senal_inst = _senal_inst(row.get("inst_score"), fh_buy_ratio, row.get("fh_count"))
            senal_ana  = _senal_analyst(rec)
            n_ana      = str(row["analyst_count"]) if row.get("analyst_count") else ""
            en_buy     = sym in syms_buy
            en_sell    = sym in syms_sell
            modelo     = "▲ COMPRAR" if en_buy else ("▼ VENDER" if en_sell else "—")
            alineacion = _alineacion(senal_inst, en_buy, en_sell, rec, categ)
            inst_val   = min(row["inst_ownership_pct"], 1.0) if row.get("inst_ownership_pct") else None
            inst_pct   = f"{inst_val:.1%}" if inst_val else ""
            buy_r_str  = f"{fh_buy_ratio:.0%}" if fh_buy_ratio else ""
            sell_r_str = f"{fh_sell_ratio:.0%}" if fh_sell_ratio else ""
            n_inst     = str(stats["fh_count"]) if stats.get("fh_count") else ""
            nombre     = (row.get("shortName") or "")[:28]

            if "CUÁDRUPLE" in alineacion:
                tag = "CUADRUPLE"
            elif "TRIPLE" in alineacion:
                tag = "TRIPLE"
            elif "✓" in alineacion:
                tag = "ALINEADO"
            elif "DIVERGE" in alineacion:
                tag = "DIVERGE"
            elif "ALERTA" in alineacion:
                tag = "ALERTA"
            else:
                tag = "NEUTRO"

            filas.append({
                "values": (sym, categ, nombre, inst_pct, n_inst, buy_r_str, sell_r_str, senal_inst, senal_ana, n_ana, modelo, alineacion),
                "tag": tag,
                "categ": categ,
            })

        filas.sort(key=lambda r: _TAG_ORDER.get(r["tag"], 99))

        # Contadores por categoría de alineación
        contadores = {}
        for f in filas:
            contadores[f["tag"]] = contadores.get(f["tag"], 0) + 1

        win = tk.Toplevel(self)
        win.title("Inst + Analistas vs Modelo — En Cartera")
        win.configure(bg="black")
        offset_x = max(0, self.winfo_rootx() + self.winfo_width() // 2)
        offset_y = max(0, self.winfo_rooty() + 60)
        win.geometry(f"1200x580+{offset_x}+{offset_y}")

        hdr = tk.Label(
            win,
            text=f"Inst + Analistas vs Modelo — Cartera ({len(filas)} activos)",
            bg="black", fg="cyan", font=("Arial", 11, "bold"),
        )
        hdr.pack(pady=(8, 4))

        cols    = ("symbol", "div",    "nombre", "inst_pct", "n_inst",  "buy_ratio", "sell_ratio", "senal_inst", "analista",  "n_ana", "modelo",   "alineacion")
        headers = ("Symbol", "Div",    "Nombre", "Inst %",   "# Inst",  "13F Buy%",  "13F Sell%",  "Inst Señal", "Analistas", "N",     "Modelo",   "Alineación")
        widths  = (65,        38,       170,       65,          55,        70,           70,           100,          105,          40,      80,          150)
        anchors = ("w",       "center", "w",       "e",         "e",       "e",          "e",          "w",          "w",          "e",     "center",    "w")

        frame = tk.Frame(win, bg="black")
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        vsb = ttk.Scrollbar(frame, orient=VERTICAL)
        tree = ttk.Treeview(frame, columns=cols, show="headings", yscrollcommand=vsb.set, height=20)
        vsb.config(command=tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for col_id, hdr_text, w, anc in zip(cols, headers, widths, anchors):
            tree.heading(col_id, text=hdr_text)
            tree.column(col_id, width=w, minwidth=40, stretch=tk.NO, anchor=anc)

        tree.tag_configure("CUADRUPLE", foreground="#FFD700")
        tree.tag_configure("TRIPLE",    foreground="#00FF88")
        tree.tag_configure("ALINEADO",  foreground="cyan")
        tree.tag_configure("DIVERGE",   foreground="#FF6060")
        tree.tag_configure("ALERTA",    foreground="#FFA500")
        tree.tag_configure("NEUTRO",    foreground="#888888")

        for f in filas:
            tree.insert("", tk.END, values=f["values"], tags=(f["tag"],))

        # Barra resumen
        resumen_frame = tk.Frame(win, bg="#111111")
        resumen_frame.pack(fill=tk.X, padx=8, pady=(2, 6))
        etiquetas = [
            ("CUADRUPLE", "★ CUÁD",  "#FFD700"),
            ("TRIPLE",    "✓✓ TRIPLE", "#00FF88"),
            ("ALINEADO",  "✓ ALIN",  "cyan"),
            ("DIVERGE",   "⚠ DIV",   "#FF6060"),
            ("ALERTA",    "⚠ ALERT", "#FFA500"),
            ("NEUTRO",    "— NEUT",  "#888888"),
        ]
        for key, label, color in etiquetas:
            n = contadores.get(key, 0)
            tk.Label(
                resumen_frame, text=f"{label}: {n}",
                bg="#111111", fg=color, font=("Arial", 9),
            ).pack(side=tk.LEFT, padx=10, pady=2)

        ttk.Button(resumen_frame, text="Ver Modelo", style="C.TButton", state=tk.DISABLED).pack(side=tk.RIGHT, padx=(0, 8))

def sync_market(account):
    """
    Sincroniza la tabla market en 2 fases:
      Phase 1 — NASDAQ : descubre símbolos nuevos de dividendos (INSERT mínimo)
      Phase 2 — yfinance: actualiza precio, mercado y fundamentales por símbolo (paralelo)
    Reemplaza HTTP directo + crumb por yf.Ticker().info — más robusto ante cambios de Yahoo.
    """

    def _safe_float(val):
        try:
            f = float(val) if val is not None else None
            return None if f is not None and (math.isnan(f) or math.isinf(f)) else f
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
        base_url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=5000"
        rows, offset = [], 0
        while True:
            resp = requests.get(f"{base_url}&offset={offset}", headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json().get("data", {})
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

    # ── Phase 2: yfinance por símbolo ────────────────────────────────────────
    def _fetch_symbol_data(symbol):
        time.sleep(0.3)
        try:
            info = yf.Ticker(symbol.replace("^", "-")).info
            if not info:
                return symbol, [], []
            campos = [
                "shortName", "lastPrice", "previousClose", "open", "volume",
                "marketCap", "currency", "averageVolume", "fiftyTwoWeekHigh",
                "fiftyTwoWeekLow", "fiftyDayAverage", "twoHundredDayAverage",
                "trailingPE", "forwardPE", "trailingEps", "beta",
                "sector", "industry", "country",
                "dividendRate", "dividendYield", "exDividendDate", "payoutRatio",
                "fiveYearAvgDividendYield", "trailingAnnualDividendRate",
                "trailingAnnualDividendYield", "pegRatio", "priceToBook",
                "forwardEps", "trailingPegRatio", "lastFiscalYearEnd",
                "firstTradeDateEpochUtc", "targetHighPrice", "targetLowPrice",
                "targetMeanPrice", "returnOnAssets", "returnOnEquity",
                "earningsGrowth", "revenueGrowth", "freeCashflow",
                "grossMargins", "ebitdaMargins", "operatingMargins",
                "financialCurrency", "website",
            ]
            valores = [
                str(info.get("shortName") or "")[:60],
                _safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
                _safe_float(info.get("previousClose")),
                _safe_float(info.get("open")),
                _safe_float(info.get("volume")),
                _safe_float(info.get("marketCap")),
                str(info.get("currency") or "")[:6],
                _safe_float(info.get("averageVolume")),
                _safe_float(info.get("fiftyTwoWeekHigh")),
                _safe_float(info.get("fiftyTwoWeekLow")),
                _safe_float(info.get("fiftyDayAverage")),
                _safe_float(info.get("twoHundredDayAverage")),
                _safe_float(info.get("trailingPE")),
                _safe_float(info.get("forwardPE")),
                _safe_float(info.get("trailingEps")),
                _safe_float(info.get("beta")),
                str(info.get("sector") or "")[:50],
                str(info.get("industry") or "")[:80],
                str(info.get("country") or "")[:50],
                _safe_float(info.get("dividendRate")),
                _safe_float(info.get("dividendYield")),
                _safe_date(info.get("exDividendDate")),
                _safe_float(info.get("payoutRatio")),
                _safe_float(info.get("fiveYearAvgDividendYield")),
                _safe_float(info.get("trailingAnnualDividendRate")),
                _safe_float(info.get("trailingAnnualDividendYield")),
                _safe_float(info.get("pegRatio")),
                _safe_float(info.get("priceToBook")),
                _safe_float(info.get("forwardEps")),
                _safe_float(info.get("trailingPegRatio")),
                _safe_date(info.get("lastFiscalYearEnd")),
                _safe_date(info.get("firstTradeDateEpochUtc")),
                _safe_float(info.get("targetHighPrice")),
                _safe_float(info.get("targetLowPrice")),
                _safe_float(info.get("targetMeanPrice")),
                _safe_float(info.get("returnOnAssets")),
                _safe_float(info.get("returnOnEquity")),
                _safe_float(info.get("earningsGrowth")),
                _safe_float(info.get("revenueGrowth")),
                _safe_float(info.get("freeCashflow")),
                _safe_float(info.get("grossMargins")),
                _safe_float(info.get("ebitdaMargins")),
                _safe_float(info.get("operatingMargins")),
                str(info.get("financialCurrency") or "")[:6],
                str(info.get("website") or "")[:200],
            ]
            return symbol, campos, valores
        except Exception:
            return symbol, [], []

    # ── Ejecución ────────────────────────────────────────────────────────────
    market = MarketScreen()
    existing = market.load_symbols(account=account)

    # Phase 1: NASDAQ — solo INSERT símbolos nuevos
    rows = _nasdaq_fetch()
    insertados, omitidos = 0, 0
    for row in rows:
        if not _is_dividend_candidate(row):
            continue
        symbol = (row.get("symbol", "") or "").strip()
        if not symbol:
            continue
        # Filtrar preferreds, warrants, rights, units (símbolo con guión: ABR-D, AHT-F, etc.)
        if "-" in symbol:
            continue
        if symbol not in existing:
            market.insert(upd=["account", "tipo"], val=[account, "Dividends"], symbol=symbol)
            existing[symbol] = "N"
            insertados += 1
        elif existing[symbol] in ("I", "S", "X"):
            omitidos += 1

    # Phase 2: yfinance — todos los símbolos activos, paralelo
    active_symbols = [s for s, cat in existing.items() if cat not in ("I", "S", "X")]
    data_ok = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(_fetch_symbol_data, sym): sym for sym in active_symbols}
        for future in futures:
            symbol, campos, valores = future.result()
            if campos:
                market.update(upd=campos, val=valores, symbol=symbol)
                data_ok += 1

    return {
        "descargados": len(rows),
        "insertados": insertados,
        "omitidos": omitidos,
        "actualizados": data_ok,
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
            f = float(val) if val is not None else None
            return None if f is not None and (math.isnan(f) or math.isinf(f)) else f
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
                "analyst_rec", "analyst_mean", "analyst_count",
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
                str(fd.get("recommendationKey") or "")[:20] or None,
                _safe_float(fd.get("recommendationMean", {}).get("raw")),
                int(fd["numberOfAnalystOpinions"]["raw"]) if fd.get("numberOfAnalystOpinions", {}).get("raw") else None,
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
        }
    all_symbols = list(existing.keys())

    # ── Phase 0: Eliminar preferreds/warrants/rights ya existentes ────────────
    preferreds_eliminados = 0
    for sym in list(all_symbols):
        if "-" in sym and existing[sym].get("encartera") != "Y":
            market.delete(symbol=sym, account=account)
            existing.pop(sym)
            all_symbols.remove(sym)
            preferreds_eliminados += 1
            _logger.warning(f"cleanup_market: preferred eliminado {sym}")

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
                if not _safe_float(s.get("regularMarketPrice")) and existing.get(sym, {}).get("encartera") != "Y":
                    not_found.append(sym)
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

    # ── Phase 2: Eliminar no encontrados (preserva encartera='Y' → los maneja audit_portfolio)
    eliminados = 0
    en_cartera_salvados = 0
    for sym in not_found:
        if existing.get(sym, {}).get("encartera") == "Y":
            en_cartera_salvados += 1
            continue
        market.delete(symbol=sym, account=account)
        eliminados += 1
        _logger.warning(f"cleanup_market: eliminado {sym}")

    # ── Phase 3: Fundamentals — cualquier campo fundamental ausente ──────────────
    needs_fund = market.load_symbols_needing_fundamentals(account)
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
        "en_cartera_salvados": en_cartera_salvados,
        "preferreds_eliminados": preferreds_eliminados,
        "fund_completados": fund_ok,
    }


def _resolve_cusip_from_edgar(symbol, short_name):
    """
    Busca el CUSIP de un símbolo en los propios filings 10-K/20-F de la compañía en EDGAR.
    Estrategia 1: buscar por ticker/nombre via entity search → descargar header .hdr.sgml.
    Estrategia 2: descargar primeros 64KB del documento principal y buscar patrón CUSIP.
    Retorna el CUSIP (str 9 chars) o None si no lo encuentra.
    """
    _HEADERS  = {"User-Agent": "AppOO research@appoo.com"}
    _SEARCH   = "https://efts.sec.gov/LATEST/search-index"
    _CUSIP_RE = re.compile(r"CUSIP[:\s#]*([A-Z0-9]{9})", re.I)

    queries = [symbol]
    if short_name and short_name.upper() != symbol.upper():
        queries.append(short_name)

    for query in queries:
        try:
            r = requests.get(
                _SEARCH,
                params={"entity": query, "forms": "10-K,20-F",
                        "dateRange": "custom", "startdt": "2022-01-01"},
                headers=_HEADERS,
                timeout=15,
            )
            hits = r.json().get("hits", {}).get("hits", [])

            for hit in hits[:4]:
                src   = hit.get("_source", {})
                ciks  = src.get("ciks", [])
                hit_id = hit.get("_id", "")
                if not ciks or ":" not in hit_id:
                    continue
                accn, xmlfile = hit_id.split(":", 1)
                cik       = int(ciks[0])
                acc_clean = accn.replace("-", "")

                # Intentar primero el header SGML (archivo pequeño, ~2-10KB)
                hdr_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{accn}.hdr.sgml"
                r2 = requests.get(hdr_url, headers=_HEADERS, timeout=10)
                if r2.ok:
                    m = _CUSIP_RE.search(r2.text)
                    if m:
                        return m.group(1).upper()

                # Fallback: primeros 64KB del documento principal (cover page del 10-K)
                doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{xmlfile}"
                r3 = requests.get(doc_url, headers=_HEADERS, stream=True, timeout=20)
                if r3.ok:
                    raw = b""
                    for chunk in r3.iter_content(8192):
                        raw += chunk
                        if len(raw) >= 65536:
                            break
                    r3.close()
                    m = _CUSIP_RE.search(raw.decode("utf-8", errors="ignore"))
                    if m:
                        return m.group(1).upper()

                time.sleep(0.4)

        except Exception as e:
            _logger.warning(f"_resolve_cusip_from_edgar({symbol}, q={query!r}): {e}")

    return None


def audit_portfolio(account):
    """
    Audita activos en cartera (encartera='Y') contra Yahoo Finance y EDGAR.
    - Delistado (sin datos Yahoo): delisted=1 en booktrading + delete en market.
    - Nombre cambió: actualiza shortName en market.
    - Sin precio (datos parciales): solo log, sin acción.
    - CUSIP faltante: resuelve via EDGAR 13F y actualiza market.
    Retorna dict con contadores.
    """
    market   = MarketScreen()
    cartera  = market.load_cartera_symbols(account)

    _ETF_TYPES    = {"ETF", "MUTUALFUND", "TRUST", "INDEX", "MONEYMARKET"}
    delistados    = 0
    nombres_upd   = 0
    sin_precio    = 0
    cusips_upd    = 0
    etfs_upd      = 0
    errores       = 0

    for row in cartera:
        sym       = row["symbol"]
        nombre_db = (row.get("shortName") or "")

        try:
            info      = yf.Ticker(sym).info
            qt        = (info.get("quoteType") or "").upper()
            nombre_yf = (info.get("shortName") or info.get("longName") or "").strip()
            precio_yf = info.get("regularMarketPrice") or info.get("previousClose")

            # ETF/fondo → forzar categoriaActivo='X' (sin estudio de dividendo individual)
            if qt in _ETF_TYPES and row.get("categoriaActivo") != "X":
                market.update(upd=["categoriaActivo"], val=["X"], symbol=sym, account=account)
                etfs_upd += 1
                _logger.warning(f"audit_portfolio: ETF detectado {sym} qt={qt} → categoriaActivo=X")

            if not qt or qt == "NONE":
                # Sin datos Yahoo → delistado: eliminar de market + marcar booktrading
                market.mark_booktrading_delisted(sym, account)
                market.delete(sym, account)
                delistados += 1
                _logger.warning(f"audit_portfolio: delistado {sym} — eliminado market + booktrading marcado")

            elif not precio_yf:
                sin_precio += 1
                _logger.warning(f"audit_portfolio: sin precio {sym}  qt={qt}")

            elif nombre_yf and nombre_db and nombre_yf[:25] != nombre_db[:25]:
                market.update(upd=["shortName"], val=[nombre_yf], symbol=sym, account=account)
                nombres_upd += 1
                _logger.warning(f"audit_portfolio: nombre actualizado {sym}  '{nombre_db}' → '{nombre_yf}'")

            # CUSIP faltante → resolver via EDGAR
            if not row.get("cusip"):
                cusip = _resolve_cusip_from_edgar(sym, nombre_yf or nombre_db)
                if cusip:
                    market.update_market_cusip(sym, account, cusip)
                    cusips_upd += 1
                    _logger.warning(f"audit_portfolio: cusip resuelto {sym} → {cusip}")

        except Exception as e:
            errores += 1
            _logger.error(f"audit_portfolio({sym}): {e}")

        time.sleep(1.5)

    return {
        "total":       len(cartera),
        "delistados":  delistados,
        "nombres_upd": nombres_upd,
        "cusips_upd":  cusips_upd,
        "etfs_upd":    etfs_upd,
        "sin_precio":  sin_precio,
        "errores":     errores,
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
