from Modulos_Mysql import MarketScreen, BDsystem
from Modulos_Utilitarios import (
    style_app,
    is_null,
    is_none,
    mask_numero,
    define_FileCache,
    documentar_estructura,
)
from Class_customer import CustomTreeview
from ConvergIA.ThemeMapper import load_sentiment, load_analysis, voto_tech_alignment
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
    threading,
    logging,
    yf,
    math,
    pd,
    EmptyDataError,
    webbrowser,
)

_logger = logging.getLogger("Screener")


def _build_net_percentiles(cartera_rows):
    nets = sorted(
        [
            float(r.get("fh_buy_ratio") or 0.0) - float(r.get("fh_sell_ratio") or 0.0)
            for r in cartera_rows
            if r.get("fh_count")
        ]
    )
    if len(nets) < 3:
        return 0.2, 0.5
    n = len(nets)
    return nets[n // 3], nets[(2 * n) // 3]


def _build_flujo_percentiles(cartera_rows):
    vals = sorted(
        [
            max(
                -1.0,
                min(1.0, ((r.get("new_entrants") or 0) - (r.get("full_exits") or 0)) / max(r.get("fh_count") or 1, 1)),
            )
            for r in cartera_rows
            if r.get("fh_count")
        ]
    )
    if len(vals) < 3:
        return -0.1, 0.1
    n = len(vals)
    return vals[n // 3], vals[(2 * n) // 3]


def voto_net_relativo(buy_r, sell_r, p33, p67, fh_count=None):
    if not fh_count:
        return 0
    net = (buy_r or 0.0) - (sell_r or 0.0)
    if net >= p67:
        return 1
    if net >= p33:
        return 0
    return -1


def voto_options(call_shares, put_shares):
    total = (call_shares or 0) + (put_shares or 0)
    if total == 0:
        return 0
    ratio = (call_shares or 0) / total
    if ratio >= 0.6:
        return 1
    if ratio >= 0.4:
        return 0
    return -1


def voto_analistas(rec):
    r = (rec or "").lower().replace(" ", "_")
    if r in ("strong_buy", "buy"):
        return 1
    if r in ("sell", "strong_sell"):
        return -1
    if r == "hold":
        return 0
    return 0


def voto_valuacion(categ):
    if categ == "I":
        return 1
    if categ == "S":
        return -1
    if categ == "N":
        return 0
    return 0


def voto_cobertura(fh_count):
    c = fh_count or 0
    if c >= 20:
        return 1
    if c >= 5:
        return 0
    return -1


def voto_flujo(new_ent, exits, fh_count, p33, p67):
    if not fh_count:
        return 0
    fn = max(-1.0, min(1.0, ((new_ent or 0) - (exits or 0)) / fh_count))
    if fn >= p67:
        return 1
    if fn >= p33:
        return 0
    return -1


def senal_consenso(votos_activos, suma):
    n = len(votos_activos)
    if n == 0:
        return "S/D", 0, 0
    pct = suma / n
    if suma == n:
        etiqueta = "UNANIME"
    elif pct >= 0.6:
        etiqueta = "CONSENSO"
    elif pct >= 0.2:
        etiqueta = "TENDENCIA"
    elif pct > -0.2:
        etiqueta = "NEUTRO"
    elif pct > -0.6:
        etiqueta = "ALERTA"
    else:
        etiqueta = "SALIDA"
    return etiqueta, suma, n


_ETF_TYPES = {"ETF", "MUTUALFUND", "TRUST", "INDEX", "MONEYMARKET"}


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
    session.headers.update(
        {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    )
    crumb = ""
    _BACKOFF = [0, 5, 15]  # segundos de espera antes de cada intento
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
        self._inst_win = None
        self._cand_win = None
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

            tree.heading(col, text=col, command=lambda: sort_treeview(tree, col, not reverse))
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
            self.options.pack(side=tk.RIGHT, fill=tk.Y)  # options PRIMERO → se reserva espacio derecho
            self.panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # panel llena lo restante

            # --- CustomTreeview con columnas fijas ---
            _FIXED = ["symbol", "shortName", "categoriaActivo", "encartera"]
            _COL_DEFS = [
                # (db_field, header, width, anchor)
                ("symbol", "Symbol", 70, "w"),
                ("shortName", "Name", 200, "w"),
                ("categoriaActivo", "Status", 45, "center"),
                ("encartera", "Cart", 35, "center"),
                ("lastPrice", "Last", 70, "e"),
                ("rotacion", "Rotación", 80, "center"),
                ("inst_score", "Inst Score", 75, "e"),
                ("inst_ownership_pct", "Inst %", 65, "e"),
                ("fh_count", "13F Inst", 65, "e"),
                ("fh_buy_ratio", "13F Buy%", 65, "e"),
                ("fh_sell_ratio", "13F Sell%", 65, "e"),
                ("fh_call_shares", "CALL", 70, "e"),
                ("fh_put_shares", "PUT", 70, "e"),
                ("delta_call_shares", "ΔCall", 75, "e"),
                ("delta_put_shares", "ΔPut", 75, "e"),
                ("new_entrants", "+Nuevos", 60, "e"),
                ("full_exits", "-Salidas", 65, "e"),
                ("fh_total_value", "13F Value", 90, "e"),
                ("volume", "Volume", 80, "e"),
                ("averageVolume", "Avg Vol", 80, "e"),
                ("country", "Country", 100, "w"),
                ("sector", "Sector", 120, "w"),
                ("industry", "Industry", 160, "w"),
                ("currency", "Cur", 35, "center"),
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
                ("inst_top_holder", "Top Holder", 160, "w"),
                ("totalDebt", "Total Debt", 85, "e"),
                ("lastFiscalYearEnd", "FY End", 75, "w"),
                ("firstTradeDateEpochUtc", "IPO", 75, "w"),
                ("financialCurrency", "Fin Cur", 55, "center"),
                ("website", "Website", 200, "w"),
            ]
            self.ctree = [c[0] for c in _COL_DEFS]
            col_align = {col_id: {"anchor": anc, "width": w} for col_id, _, w, anc in _COL_DEFS}

            # Prevenir que self.panel se expanda por las columnas del treeview (3500px+)
            self.panel.pack_propagate(False)

            # Frame contenedor en grid dentro de self.panel
            tree_frame = ttk.Frame(self.panel, style="B.TFrame")
            tree_frame.grid(column=0, row=6, columnspan=3, rowspan=4, sticky=(N, S, E, W))
            self.panel.columnconfigure(0, weight=1)  # tree_frame llena el ancho del panel

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
                _t = self.ctree_widget.tree_fixed if col_id in _FIXED else self.ctree_widget.tree_scroll
                _t.heading(col_id, text=col_text, anchor=col_anchor)
                _t.column(
                    col_id,
                    width=col_width,
                    minwidth=max(30, col_width // 2),
                    stretch=tk.NO,
                )

            self.ctree_widget.tree_fixed.bind("<<TreeviewSelect>>", item_selected)

            def _open_website(event):
                tree = event.widget
                col = tree.identify_column(event.x)
                col_id = tree.column(col, "id") if col else ""
                if col_id != "website":
                    return
                sel = tree.selection()
                if not sel:
                    return
                iid = sel[0]
                fixed_vals = self.ctree_widget.tree_fixed.item(iid, "values")
                if not fixed_vals:
                    return
                symbol = fixed_vals[0]
                url = next(
                    (
                        row[self.ix.index("website")]
                        for row in self.market
                        if row[self.ix.index("symbol")] == symbol and self.ix.count("website")
                    ),
                    None,
                )
                if url and str(url).startswith("http"):
                    webbrowser.open(str(url))

            self.ctree_widget.tree_scroll.bind("<Double-1>", _open_website)

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
            tp5 = ttk.Checkbutton(
                self.options,
                text="En Cartera",
                variable=encartera_var,
                style="C.TRadiobutton",
            )

            tp1.grid(column=0, row=0, sticky=W, pady=1)
            tp2.grid(column=0, row=1, sticky=W, padx=10)
            tp3.grid(column=0, row=2, sticky=W, padx=10)
            tp5.grid(column=0, row=3, sticky=W, padx=10)

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
            s_scroll = ttk.Scrollbar(self.options, orient=tk.VERTICAL, command=sector.yview)
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
            c_scroll = ttk.Scrollbar(self.options, orient=tk.VERTICAL, command=country.yview)
            country.config(yscrollcommand=c_scroll.set)

            country.insert(tk.END, "None")
            for keys in d_country:
                country.insert(tk.END, keys)

            ct1.grid(column=0, row=18, sticky=W, pady=10)
            country.grid(column=0, row=19, sticky=W, padx=10)
            c_scroll.grid(column=1, row=19, sticky=(W, N + S))

            apply.grid(column=0, row=20, sticky=E, padx=20, pady=20)
            reset.grid(column=1, row=20, sticky=E, columnspa=2, pady=20)

            btn_line = ttk.Frame(self.panel, style="B.TFrame")
            btn_line.grid(column=0, row=10, columnspan=3, sticky=tk.EW, padx=8, pady=(6, 4))

            btn_frame = tk.Frame(btn_line, bg="black")
            health_frame = tk.Frame(btn_line, bg="black")
            btn_frame.pack(side=tk.LEFT)
            health_frame.pack(side=tk.RIGHT, padx=10)

            ttk.Button(
                btn_frame,
                text="Consenso",
                width=10,
                command=self._show_institucionales_cartera,
            ).pack(side=tk.LEFT, padx=(0, 6), pady=5)

            ttk.Button(
                btn_frame,
                text="Inst. Out",
                width=10,
                state=tk.DISABLED,
            ).pack(side=tk.LEFT, padx=(0, 6), pady=5)

            ttk.Button(
                btn_frame,
                text="Modelo",
                width=10,
                command=lambda: documentar_estructura("Screener", self, self.colors),
            ).pack(side=tk.LEFT, padx=(0, 6), pady=5)

            ttk.Button(
                btn_frame,
                text="Candidatos",
                width=10,
                command=self._show_youtube_candidatos,
            ).pack(side=tk.LEFT, padx=(0, 6), pady=5)

            # Status bar — health check pipeline 13F (derecha)
            self._health_labels = {}
            for key, texto in (
                ("pendientes", "📋 pendientes"),
                ("por_renovar", "🔄 por renovar"),
                ("inconsistencias", "⚠ inconsistencias"),
            ):
                lbl = tk.Label(
                    health_frame,
                    text=f"— {texto}",
                    bg="black",
                    fg="#555555",
                    font=("Arial", 8),
                )
                lbl.pack(side=tk.RIGHT, padx=6)
                self._health_labels[key] = lbl

            self.after(200, self._refresh_screener_health)
        except Exception as e:
            _logger.error("widgets_screener(): {}".format(e))

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
            return f"{v:.1%}" if v is not None else ""

        def _shares_m(v):
            return f"{float(v) / 1_000_000:.1f}M" if v and float(v) > 0 else ""

        def _delta_m(v):
            if v is None:
                return ""
            f = float(v) / 1_000_000
            return f"{f:+.1f}M" if f != 0 else ""

        def _big(v):
            return mask_numero(v or 0) if v is not None else ""

        def _date(v):
            try:
                return f"{v:%y-%b-%d}" if v else ""
            except:
                return str(v) if v else ""

        def _rotacion(row_keys):
            float_sh = row_keys[ix.index("floatShares")] if "floatShares" in ix else None
            if not float_sh and "sharesOutstanding" in ix:
                float_sh = row_keys[ix.index("sharesOutstanding")]
            vol = row_keys[ix.index("volume")] if "volume" in ix else None
            try:
                float_sh = float(float_sh)
                vol = float(vol)
            except (TypeError, ValueError):
                return ""
            if not float_sh or not vol:
                return ""
            ratio = vol / float_sh
            if ratio >= 3.0:
                return "⚡ EXTREMA"
            if ratio >= 1.0:
                return "↑↑ ALTA"
            if ratio >= 0.3:
                return "↑ MEDIA"
            return "— BAJA"

        for keys in self.market:
            self.ctree_widget.insert_row(
                values=(
                    # fijas
                    _g("symbol") or "",
                    _g("shortName") or "",
                    _g("categoriaActivo") or "",
                    _g("encartera") or "",
                    # scrollables — orden igual a _COL_DEFS
                    _price(_g("lastPrice")),
                    _rotacion(keys),
                    _price(_g("inst_score")),
                    _pct(min(_g("inst_ownership_pct"), 1.0) if _g("inst_ownership_pct") else None),
                    str(_g("fh_count")) if _g("fh_count") else "",
                    _pct(_g("fh_buy_ratio")),
                    _pct(_g("fh_sell_ratio")),
                    _shares_m(_g("fh_call_shares")),
                    _shares_m(_g("fh_put_shares")),
                    _delta_m(_g("delta_call_shares")),
                    _delta_m(_g("delta_put_shares")),
                    str(_g("new_entrants")) if _g("new_entrants") else "",
                    str(_g("full_exits")) if _g("full_exits") else "",
                    _big(_g("fh_total_value")),
                    _big(_g("volume")),
                    _big(_g("averageVolume")),
                    _g("country") or "",
                    _g("sector") or "",
                    _g("industry") or "",
                    _g("currency") or "",
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

        self.market, self.ix = self.ScMarket.select(
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

    def _refresh_screener_health(self):
        def _color_count(n, warn=10):
            if n == 0:
                return "#00FF88", "0"
            return ("#FFA500" if n < warn else "#FF6060"), str(n)

        def _fetch():
            try:
                h = self.ScMarket.load_screener_health(self.account)
                inconsistencias = h["fh_sin_symbol"] + h["market_sin_cusip"]
                self.after(0, lambda: _apply(h, inconsistencias))
            except Exception as e:
                _logger.warning(f"_refresh_screener_health: {e}")

        def _apply(h, inconsistencias):
            c, v = _color_count(h["pendientes"])
            self._health_labels["pendientes"].config(text=f"📋 {v} pendientes", fg=c)
            c, v = _color_count(h["por_renovar"], warn=50)
            self._health_labels["por_renovar"].config(text=f"🔄 {v} por renovar", fg=c)
            c, v = _color_count(inconsistencias)
            self._health_labels["inconsistencias"].config(text=f"⚠ {v} inconsistencias", fg=c)

        threading.Thread(target=_fetch, daemon=True).start()

    def _show_youtube_candidatos(self):
        if self._cand_win is not None and self._cand_win.winfo_exists():
            self._cand_win.lift()
            return

        win = tk.Toplevel(self)
        win.title("Candidatos YouTube")
        win.configure(bg="black")
        win.geometry("1150x460")
        self._cand_win = win

        _COLS = (
            "Symbol",
            "Empresa",
            "Veces",
            "Conf",
            "Mkt Cap",
            "Sector",
            "Canales",
            "Desde",
            "En Market",
            "Cartera",
        )
        _WIDTHS = (70, 150, 75, 50, 70, 130, 150, 85, 70, 55)

        frame = tk.Frame(win, bg="black")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 4))

        tree = ttk.Treeview(frame, columns=_COLS, show="headings", selectmode="browse")
        for col, w in zip(_COLS, _WIDTHS):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor=tk.CENTER)
        tree.column("Symbol", anchor=tk.E)
        tree.column("Empresa", anchor=tk.W)
        tree.column("Sector", anchor=tk.W)
        tree.column("Canales", anchor=tk.W)
        tree.tag_configure("en_market", foreground="#888888")
        tree.tag_configure("en_cartera", foreground="#00cc88")

        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.LEFT, fill=tk.Y)

        btn_frame = tk.Frame(win, bg="black")
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

        status_lbl = tk.Label(btn_frame, text="", bg="black", fg="#aaaaaa", font=("Courier", 9))
        status_lbl.pack(side=tk.RIGHT, padx=8)

        def _refresh():
            for row in tree.get_children():
                tree.delete(row)
            rows = MarketScreen().load_youtube_candidatos("pending")
            for r in rows:
                mc = r.get("market_cap") or 0
                mc_str = f"${mc/1e9:.1f}B" if mc >= 1e9 else f"${mc/1e6:.0f}M"
                en_market = bool(r.get("en_market"))
                en_cartera = r.get("en_cartera") == "Y"
                tag = "en_cartera" if en_cartera else ("en_market" if en_market else "")
                tree.insert(
                    "",
                    tk.END,
                    iid=r["symbol"],
                    values=(
                        r["symbol"],
                        r.get("company_name") or "",
                        r["apariciones"],
                        f"{r['confidence']:.2f}",
                        mc_str,
                        r.get("sector") or "",
                        r.get("canales") or "",
                        str(r.get("primera_vez") or "")[:10],
                        "Si" if en_market else "No",
                        "Si" if en_cartera else "No",
                    ),
                    tags=(tag,) if tag else (),
                )
            status_lbl.config(text=f"{len(rows)} pendientes")

        def _comprar():
            sel = tree.selection()
            if not sel:
                return
            symbol = sel[0]
            vals = tree.item(symbol, "values")
            if vals[6] == "Si":
                status_lbl.config(text=f"{symbol} ya está en market", fg="#888888")
                return
            try:
                db = MarketScreen()
                db.insert(
                    upd=["symbol", "encartera", "categoriaActivo"],
                    val=[symbol, "N", "T"],
                    symbol=symbol,
                )
                db.set_youtube_candidato_status(symbol, "approved")
                status_lbl.config(
                    text=f"{symbol} agregado a market (T) — Consenso lo tomará en el próximo ciclo", fg="#00cc88"
                )
                tree.delete(symbol)
            except Exception as e:
                status_lbl.config(text=f"Error: {e}", fg="red")

        def _rechazar():
            sel = tree.selection()
            if not sel:
                return
            symbol = sel[0]
            MarketScreen().set_youtube_candidato_status(symbol, "rejected")
            tree.delete(symbol)
            status_lbl.config(text=f"{symbol} rechazado", fg="#888888")

        ttk.Button(btn_frame, text="Comprar", width=10, command=_comprar).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Rechazar", width=10, command=_rechazar).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Refresh", width=10, command=_refresh).pack(side=tk.LEFT, padx=(0, 6))

        _refresh()

    def _show_institucionales_cartera(self):
        if self._inst_win is not None and self._inst_win.winfo_exists():
            self._inst_win.lift()
            return

        _TAG_ORDER = {
            "UNANIME": 0,
            "CONSENSO": 1,
            "TENDENCIA": 2,
            "NEUTRO": 3,
            "ALERTA": 4,
            "SALIDA": 5,
        }

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

        def _float_ratio(row):
            float_shares = row.get("floatShares") or 0
            vol = row.get("volume") or 0
            if float_shares <= 0 or vol <= 0:
                return None
            return vol / float_shares

        def _senal_float(ratio):
            if ratio is None:
                return ""
            if ratio >= 3.0:
                return "⚡ EXTREMA"
            if ratio >= 1.0:
                return "↑↑ ALTA"
            if ratio >= 0.3:
                return "↑ MEDIA"
            return "— BAJA"

        def _senal_analyst(rec):
            mapa = {
                "strong_buy": "▲▲ FUERTE",
                "buy": "▲ COMPRAR",
                "hold": "→ MANTENER",
                "sell": "▼ VENDER",
                "strong_sell": "▼▼ FUERTE",
            }
            return mapa.get((rec or "").lower().replace(" ", "_"), "")

        _TAG_DISPLAY = {
            "UNANIME": "★ UNÁNIME",
            "CONSENSO": "▲ CONSENSO",
            "TENDENCIA": "↗ TENDENCIA",
            "NEUTRO": "→ NEUTRO",
            "ALERTA": "↘ ALERTA",
            "SALIDA": "▼ SALIDA",
            "S/D": "— S/D",
        }

        def senal_consenso_display(votos_activos, suma):
            tag, s, n = senal_consenso(votos_activos, suma)
            return _TAG_DISPLAY.get(tag, tag), s, n

        cartera = self.ScMarket.load_cartera_inst(self.account)
        syms_buy = _read_csv_signals("csv_datosIA_buy")
        syms_sell = _read_csv_signals("csv_datosIA_sell")

        p33_net, p67_net = _build_net_percentiles(cartera)
        p33_flujo, p67_flujo = _build_flujo_percentiles(cartera)

        # Construir filas y ordenar por prioridad de consenso
        sentiment = load_sentiment(self.account)
        analysis = load_analysis(self.account)
        filas = []
        for row in cartera:
            sym = row["symbol"]
            fh_buy_ratio = float(row.get("fh_buy_ratio") or 0.0)
            fh_sell_ratio = float(row.get("fh_sell_ratio") or 0.0)
            rec = (row.get("analyst_rec") or "").lower().replace(" ", "_")
            categ = row.get("categoriaActivo") or ""
            senal_inst = _senal_inst(row.get("inst_score"), fh_buy_ratio, row.get("fh_count"))
            _senal = _senal_analyst(rec)
            _n_ana = str(row["analyst_count"]) if row.get("analyst_count") else ""
            senal_ana = f"{_senal:<10}  {_n_ana:>3}" if _senal and _n_ana else _senal
            en_buy = sym in syms_buy
            en_sell = sym in syms_sell
            modelo = "▲ COMPRAR" if en_buy else ("▼ VENDER" if en_sell else "—")
            ratio = _float_ratio(row)
            float_str = _senal_float(ratio)
            inst_val = min(row["inst_ownership_pct"], 1.0) if row.get("inst_ownership_pct") else None
            inst_pct = f"{inst_val:.1%}" if inst_val else ""
            buy_r_str = f"{fh_buy_ratio:.1%}" if fh_buy_ratio else ""
            sell_r_str = f"{fh_sell_ratio:.1%}" if fh_sell_ratio else ""
            n_inst = str(row["fh_count"]) if row.get("fh_count") else ""
            nombre = (row.get("shortName") or "")[:35]

            votos = {
                "Net": voto_net_relativo(fh_buy_ratio, fh_sell_ratio, p33_net, p67_net, row.get("fh_count")),
                "Opt": voto_options(row.get("fh_call_shares"), row.get("fh_put_shares")),
                "Flujo": voto_flujo(
                    row.get("new_entrants"), row.get("full_exits"), row.get("fh_count"), p33_flujo, p67_flujo
                ),
                "Ana": voto_analistas(rec),
                "Mod": (1 if en_buy else (-1 if en_sell else 0)),
                "Val": voto_valuacion(categ),
                "Cob": voto_cobertura(row.get("fh_count")),
                "Sent": voto_tech_alignment(sym, sentiment, analysis),
            }
            activos = {k: v for k, v in votos.items() if k != "Mod" and v is not None}
            suma = sum(activos.values())
            tag, _suma, _n = senal_consenso(list(activos.values()), suma)
            _etiq = _TAG_DISPLAY.get(tag, tag)
            consenso = f"{_etiq:<12}  {_suma:+d}/{_n}" if _n else _etiq

            _call_sh = row.get("fh_call_shares") or 0
            _put_sh = row.get("fh_put_shares") or 0
            calls_str = f"{float(_call_sh) / 1_000_000:.1f}M" if _call_sh else ""
            puts_str = f"{float(_put_sh) / 1_000_000:.1f}M" if _put_sh else ""
            _d_call = row.get("delta_call_shares")
            _d_put = row.get("delta_put_shares")
            d_call_str = f"{float(_d_call) / 1_000_000:+.1f}M" if _d_call is not None and _d_call != 0 else ""
            d_put_str = f"{float(_d_put) / 1_000_000:+.1f}M" if _d_put is not None and _d_put != 0 else ""
            new_ent_str = str(row["new_entrants"]) if row.get("new_entrants") else ""
            full_ex_str = str(row["full_exits"]) if row.get("full_exits") else ""
            _fh_c = row.get("fh_count") or 0
            _fn = (
                max(-1.0, min(1.0, ((row.get("new_entrants") or 0) - (row.get("full_exits") or 0)) / max(_fh_c, 1)))
                if _fh_c
                else None
            )
            flujo_str = f"{_fn:+.2f}" if _fn is not None else ""
            _sent = votos.get("Sent", 0)
            sent_str = f"{_sent:+d}" if _sent != 0 else "0"
            filas.append(
                {
                    "values": (
                        sym,
                        categ,
                        nombre,
                        f"{float(row['lastPrice']):.2f}" if row.get("lastPrice") else "",
                        inst_pct,
                        n_inst,
                        buy_r_str,
                        sell_r_str,
                        calls_str,
                        puts_str,
                        d_call_str,
                        d_put_str,
                        new_ent_str,
                        full_ex_str,
                        flujo_str,
                        float_str,
                        senal_inst,
                        senal_ana,
                        modelo,
                        sent_str,
                        consenso,
                        row.get("website") or "",
                    ),
                    "tag": tag,
                    "categ": categ,
                }
            )

        filas.sort(key=lambda r: _TAG_ORDER.get(r["tag"], 99))

        # Contadores por categoría de alineación
        contadores = {}
        for f in filas:
            contadores[f["tag"]] = contadores.get(f["tag"], 0) + 1

        win = tk.Toplevel(self)
        self._inst_win = win
        win.protocol(
            "WM_DELETE_WINDOW",
            lambda: (win.destroy(), setattr(self, "_inst_win", None)),
        )
        win.title("Señales de Consenso — En Cartera")
        win.configure(bg="black")
        win.geometry(f"1200x530+{650}+{400}")

        hdr = tk.Label(
            win,
            text=f"Señales de Consenso — Cartera ({len(filas)} activos)",
            bg="black",
            fg="cyan",
            font=("Arial", 11, "bold"),
        )
        hdr.pack(pady=(8, 4))

        _FIXED_COLS = ("Symbol", "Div", "Nombre", "Last", "Inst %", "13F Inst")
        _COL_DEFS = (
            ("Symbol", 65, "w"),
            ("Div", 38, "center"),
            ("Nombre", 200, "w"),
            ("Last", 65, "e"),
            ("Inst %", 65, "e"),
            ("13F Inst", 55, "e"),
            ("13F Buy%", 70, "e"),
            ("13F Sell%", 70, "e"),
            ("CALL", 60, "e"),
            ("PUT", 60, "e"),
            ("ΔCall", 70, "e"),
            ("ΔPut", 70, "e"),
            ("+Nuevos", 60, "e"),
            ("-Salidas", 65, "e"),
            ("Flujo", 55, "center"),
            ("Rotación", 80, "center"),
            ("Inst Señal", 100, "w"),
            ("Analistas", 140, "w"),
            ("IA Signal", 90, "center"),
            ("Sent", 45, "center"),
            ("Consenso", 160, "w"),
            ("Website", 200, "w"),
        )
        all_cols = tuple(d[0] for d in _COL_DEFS)
        col_align = {d[0]: {"anchor": d[2], "width": d[1]} for d in _COL_DEFS}

        frame = tk.Frame(win, bg="black")
        frame.pack(fill=tk.X, padx=8, pady=4)

        ct = CustomTreeview(
            master=frame,
            columns=all_cols,
            fixed_columns=_FIXED_COLS,
            sort_columns=True,
            height=20,
            column_alignments=col_align,
        )
        ct.master.config(bg="black")
        ct.heard.config(bg="black")
        ct.right.config(bg="black")

        for tag, color in (
            ("UNANIME", "#FFD700"),
            ("CONSENSO", "#00FF88"),
            ("TENDENCIA", "cyan"),
            ("NEUTRO", "#888888"),
            ("ALERTA", "#FFA500"),
            ("SALIDA", "#FF6060"),
        ):
            ct.tree_fixed.tag_configure(tag, foreground=color)
            ct.tree_scroll.tag_configure(tag, foreground=color)

        n_fixed = len(_FIXED_COLS)
        for f in filas:
            ct.tree_fixed.insert("", tk.END, values=f["values"][:n_fixed], tags=(f["tag"],))
            ct.tree_scroll.insert("", tk.END, values=f["values"][n_fixed:], tags=(f["tag"],))

        def _open_website_consenso(event):
            tree = event.widget
            col = tree.identify_column(event.x)
            col_id = tree.column(col, "id") if col else ""
            if col_id != "Website":
                return
            sel = tree.selection()
            if not sel:
                return
            iid = sel[0]
            scroll_vals = ct.tree_scroll.item(iid, "values")
            scroll_cols = [d[0] for d in _COL_DEFS if d[0] not in _FIXED_COLS]
            idx = scroll_cols.index("Website") if "Website" in scroll_cols else -1
            if idx >= 0 and idx < len(scroll_vals):
                url = scroll_vals[idx]
                if url and str(url).startswith("http"):
                    webbrowser.open(str(url))

        ct.tree_scroll.bind("<Double-1>", _open_website_consenso)

        # Barra resumen
        resumen_frame = tk.Frame(win, bg="#111111")
        resumen_frame.pack(fill=tk.X, padx=8, pady=(2, 6))
        etiquetas = [
            ("UNANIME", "★ UNÁNIME", "#FFD700"),
            ("CONSENSO", "▲ CONSENSO", "#00FF88"),
            ("TENDENCIA", "↗ TENDENCIA", "cyan"),
            ("NEUTRO", "→ NEUTRO", "#888888"),
            ("ALERTA", "↘ ALERTA", "#FFA500"),
            ("SALIDA", "▼ SALIDA", "#FF6060"),
        ]
        for key, label, color in etiquetas:
            n = contadores.get(key, 0)
            tk.Label(
                resumen_frame,
                text=f"{label}: {n}",
                bg="#111111",
                fg=color,
                font=("Arial", 9),
            ).pack(side=tk.LEFT, padx=10, pady=2)


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
    active_symbols = [s for s, cat in existing.items() if cat not in ("X",)]
    data_ok = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(_fetch_symbol_data, sym): sym for sym in active_symbols}
        for future in futures:
            symbol, campos, valores = future.result()
            if campos:
                market.update(upd=campos, val=valores, symbol=symbol)
                data_ok += 1

    sector_ok = market.sync_sector_to_inversion(account)

    return {
        "descargados": len(rows),
        "insertados": insertados,
        "omitidos": omitidos,
        "actualizados": data_ok,
        "sector_sync": sector_ok,
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
            yield lst[i : i + n]

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
    if not _crumb:
        _logger.error("cleanup_market: Yahoo no disponible (429/sin crumb) — abortando")
        return {
            "total": 0,
            "batches_ok": 0,
            "quote_actualizados": 0,
            "eliminados": 0,
            "preferreds_eliminados": 0,
            "fund_completados": 0,
        }

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
                "analyst_rec",
                "analyst_mean",
                "analyst_count",
                "sharesOutstanding",
                "floatShares",
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
                (
                    int(fd["numberOfAnalystOpinions"]["raw"])
                    if fd.get("numberOfAnalystOpinions", {}).get("raw")
                    else None
                ),
                (int(ks["sharesOutstanding"]["raw"]) if ks.get("sharesOutstanding", {}).get("raw") else None),
                (int(ks["floatShares"]["raw"]) if ks.get("floatShares", {}).get("raw") else None),
            ]
            return campos, valores
        except Exception:
            return [], []

    market = MarketScreen()
    rows, ix = market.select(account=account, tipo="Dividends") or ([], [])
    existing = {}
    for row in rows or []:
        d = dict(zip(ix, row))
        existing[d["symbol"]] = {
            "categoriaActivo": d.get("categoriaActivo"),
            "encartera": d.get("encartera"),
        }
    all_symbols = list(existing.keys())

    # ── Phase 0: Eliminar preferreds/warrants/rights ya existentes ────────────
    preferreds_eliminados = 0
    for sym in list(all_symbols):
        if ("-" in sym or "^" in sym) and existing[sym].get("encartera") != "Y":
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
                _logger.warning(
                    f"cleanup_market batch skip HTTP {resp.status_code} — no se procesan {len(batch)} símbolos"
                )
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
                qt = (s.get("quoteType") or "").upper()
                if qt in _ETF_TYPES and existing.get(sym, {}).get("categoriaActivo") == "N":
                    campos = list(campos) + ["categoriaActivo"]
                    valores = list(valores) + ["X"]
                market.update(upd=campos, val=valores, symbol=sym)
                quote_ok += 1
            # Detectar no encontrados en este batch
            for sym in batch:
                if sym not in returned:
                    not_found.append(sym)
        except Exception as e:
            _logger.warning(f"cleanup_market batch skip ({e}) — no se procesan {len(batch)} símbolos")
            continue

    # ── Phase 2: Eliminar no encontrados — deslistados salen siempre, cartera o no
    eliminados = 0
    for sym in not_found:
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
    _HEADERS = {"User-Agent": "AppOO research@appoo.com"}
    _SEARCH = "https://efts.sec.gov/LATEST/search-index"
    _CUSIP_RE = re.compile(r"CUSIP[:\s#]*([A-Z0-9]{9})", re.I)

    queries = [symbol]
    if short_name and short_name.upper() != symbol.upper():
        queries.append(short_name)

    for query in queries:
        try:
            r = requests.get(
                _SEARCH,
                params={
                    "entity": query,
                    "forms": "10-K,20-F",
                    "dateRange": "custom",
                    "startdt": "2022-01-01",
                },
                headers=_HEADERS,
                timeout=15,
            )
            hits = r.json().get("hits", {}).get("hits", [])

            for hit in hits[:4]:
                src = hit.get("_source", {})
                ciks = src.get("ciks", [])
                hit_id = hit.get("_id", "")
                if not ciks or ":" not in hit_id:
                    continue
                accn, xmlfile = hit_id.split(":", 1)
                cik = int(ciks[0])
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
    market = MarketScreen()
    cartera = market.load_cartera_symbols(account)

    delistados = 0
    nombres_upd = 0
    sin_precio = 0
    cusips_upd = 0
    etfs_upd = 0
    errores = 0

    for row in cartera:
        sym = row["symbol"]
        nombre_db = row.get("shortName") or ""

        try:
            info = yf.Ticker(sym).info
            qt = (info.get("quoteType") or "").upper()
            nombre_yf = (info.get("shortName") or info.get("longName") or "").strip()
            precio_yf = info.get("regularMarketPrice") or info.get("previousClose")

            # ETF/fondo → eliminar de market, solo acciones
            if qt in _ETF_TYPES:
                market.delete(sym, account)
                etfs_upd += 1
                _logger.warning(f"audit_portfolio: ETF eliminado {sym} qt={qt}")
                continue

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
        "total": len(cartera),
        "delistados": delistados,
        "nombres_upd": nombres_upd,
        "cusips_upd": cusips_upd,
        "etfs_upd": etfs_upd,
        "sin_precio": sin_precio,
        "errores": errores,
    }


def _load_csv_signals():
    def _read(filename):
        try:
            path = define_FileCache(name=f"{filename}.CSV")
            df = pd.read_csv(path, header=0, sep=",", encoding="utf-8", index_col=False)
            df.columns = df.columns.str.strip()
            return set(df["Symbol"].dropna().str.strip().tolist()) if "Symbol" in df.columns else set()
        except (EmptyDataError, FileNotFoundError):
            return set()
        except Exception:
            return set()

    return _read("csv_datosIA_buy"), _read("csv_datosIA_sell")


def refresh_consenso_tags(account):
    """Recalcula consenso_tag y consenso_suma (7 votos) para todos los símbolos
    en cartera y los persiste en market. Llamado por Agente_ConsensoCache cada 5 min."""
    mkt = MarketScreen()
    cartera = mkt.load_cartera_inst(account)
    if not cartera:
        return {"actualizados": 0, "total": 0}

    p33_net, p67_net = _build_net_percentiles(cartera)
    p33_flujo, p67_flujo = _build_flujo_percentiles(cartera)
    syms_buy, syms_sell = _load_csv_signals()

    actualizados = 0
    for row in cartera:
        sym = row["symbol"]
        fh_buy_ratio = float(row.get("fh_buy_ratio") or 0.0)
        fh_sell_ratio = float(row.get("fh_sell_ratio") or 0.0)
        rec = (row.get("analyst_rec") or "").lower().replace(" ", "_")
        categ = row.get("categoriaActivo") or ""

        votos = {
            "Net": voto_net_relativo(fh_buy_ratio, fh_sell_ratio, p33_net, p67_net, row.get("fh_count")),
            "Opt": voto_options(row.get("fh_call_shares"), row.get("fh_put_shares")),
            "Flujo": voto_flujo(
                row.get("new_entrants"), row.get("full_exits"), row.get("fh_count"), p33_flujo, p67_flujo
            ),
            "Ana": voto_analistas(rec),
            "Mod": (1 if sym in syms_buy else (-1 if sym in syms_sell else 0)),
            "Val": voto_valuacion(categ),
            "Cob": voto_cobertura(row.get("fh_count")),
        }
        activos = {k: v for k, v in votos.items() if k != "Mod" and v is not None}
        suma = sum(activos.values())
        tag, _, _ = senal_consenso(list(activos.values()), suma)

        mkt.update(upd=["consenso_tag", "consenso_suma"], val=[tag, int(suma)], symbol=sym, account=account)
        actualizados += 1

    return {"actualizados": actualizados, "total": len(cartera)}


if __name__ == "__main__":
    print("Iniciando cleanup_market ...")
    result = cleanup_market(account="U4214563")
    print(f"  total símbolos      : {result['total']}")
    print(f"  batches exitosos    : {result['batches_ok']}")
    print(f"  quote actualizados  : {result['quote_actualizados']}")
    print(f"  eliminados          : {result['eliminados']}")
    print(f"  fund completados    : {result['fund_completados']}")
    print("cleanup_market completado.")
