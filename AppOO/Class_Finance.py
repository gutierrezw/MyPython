import calendar

from Modulos_python import (
    tk,
    ttk,
    datetime,
    logging,
)
from Modulos_Mysql import FinanceScreen

_logger = logging.getLogger("Finance")


# ─────────────────────────────────────────────────────────────────────────────
# Constantes de UI
# ─────────────────────────────────────────────────────────────────────────────

_ACCENT = "#00BCD4"
_POSITIVE = "#26A69A"
_NEGATIVE = "#EF5350"
_NEUTRAL = "#78909C"
_GOLD = "#FFA726"
_CARD_BG = "#1A1A2E"

_FONT_TITLE = ("Segoe UI", 10, "bold")
_FONT_VALUE = ("Segoe UI", 18, "bold")
_FONT_SUB = ("Segoe UI", 8)
_FONT_LABEL = ("Segoe UI", 9)
_FONT_HEADER = ("Segoe UI", 9, "bold")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de formato
# ─────────────────────────────────────────────────────────────────────────────


def _fmt_ars(v) -> str:
    try:
        return f"$ {float(v):,.0f}".replace(",", ".")
    except Exception:
        return "—"


def _fmt_usdt(v) -> str:
    try:
        return f"U$ {float(v):,.2f}"
    except Exception:
        return "—"


# ─────────────────────────────────────────────────────────────────────────────
# Widget: tarjeta KPI
# ─────────────────────────────────────────────────────────────────────────────


class _KpiCard(tk.Frame):
    """Tarjeta con título, valor grande y subtexto."""

    def __init__(self, parent, title="", value_color=None):
        super().__init__(parent, bg=_CARD_BG, bd=0, highlightthickness=1, highlightbackground=_NEUTRAL)
        self._vcolor = value_color or _ACCENT

        tk.Label(self, text=title, font=_FONT_TITLE, bg=_CARD_BG, fg=_NEUTRAL).pack(anchor="w", padx=10, pady=(8, 0))
        self._val_lbl = tk.Label(self, text="—", font=_FONT_VALUE, bg=_CARD_BG, fg=self._vcolor)
        self._val_lbl.pack(anchor="w", padx=10)
        self._sub_lbl = tk.Label(self, text="", font=_FONT_SUB, bg=_CARD_BG, fg=_NEUTRAL)
        self._sub_lbl.pack(anchor="w", padx=10, pady=(0, 8))

    def update_value(self, value, sub="", color=None):
        self._val_lbl.config(text=value, fg=color or self._vcolor)
        self._sub_lbl.config(text=sub)


# ─────────────────────────────────────────────────────────────────────────────
# Widget: tabla de transacciones
# ─────────────────────────────────────────────────────────────────────────────


class _TxnTable(tk.Frame):
    """Treeview de transacciones con scrollbar."""

    COLS = ("Fecha", "Cuenta", "Descripción", "Categoría", "Moneda", "Monto")
    WIDTHS = (80, 140, 240, 130, 60, 100)

    def __init__(self, parent, bgcolor):
        super().__init__(parent, bg=bgcolor)
        self._build()

    def _build(self):
        tree_frame = tk.Frame(self, bg=self.cget("bg"))
        tree_frame.pack(fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(tree_frame, columns=self.COLS, show="headings", height=14, yscrollcommand=vsb.set)
        vsb.config(command=self.tree.yview)

        for col, w in zip(self.COLS, self.WIDTHS):
            anchor = tk.E if col == "Monto" else tk.W
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor=anchor, stretch=False)

        self.tree.tag_configure("expense", foreground=_NEGATIVE)
        self.tree.tag_configure("income", foreground=_POSITIVE)
        self.tree.tag_configure("transfer", foreground=_NEUTRAL)
        self.tree.pack(fill=tk.BOTH, expand=True)

    def load(self, rows: list[dict]):
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            monto = _fmt_ars(r["amount"]) if r.get("currency") == "ARS" else _fmt_usdt(r["amount"])
            self.tree.insert(
                "",
                tk.END,
                values=(
                    r.get("date", ""),
                    r.get("account", ""),
                    r.get("description", ""),
                    r.get("category", "Sin categoría"),
                    r.get("currency", ""),
                    monto,
                ),
                tags=(r.get("type", "expense"),),
            )


# ─────────────────────────────────────────────────────────────────────────────
# Widget: barra de gastos por categoría
# ─────────────────────────────────────────────────────────────────────────────


class _CategoryBar(tk.Frame):
    """Lista de categorías con barra proporcional y monto."""

    def __init__(self, parent, bgcolor):
        super().__init__(parent, bg=bgcolor)
        self.bgcolor = bgcolor

    def load(self, data: list[dict]):
        """data = [{"name": str, "total": float, "pct": float}, ...]"""
        for w in self.winfo_children():
            w.destroy()

        max_pct = max((d["pct"] for d in data), default=1) or 1
        bar_w = 180

        for d in data[:12]:
            row = tk.Frame(self, bg=self.bgcolor)
            row.pack(fill=tk.X, pady=1)

            tk.Label(row, text=d["name"], font=_FONT_LABEL, bg=self.bgcolor, fg="white", width=20, anchor="w").pack(
                side=tk.LEFT
            )

            filled = max(int(bar_w * d["pct"] / max_pct), 2)
            canvas = tk.Canvas(row, width=bar_w, height=14, bg=self.bgcolor, highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=4)
            canvas.create_rectangle(0, 2, filled, 12, fill=_ACCENT, outline="")

            tk.Label(
                row, text=_fmt_ars(d["total"]), font=_FONT_LABEL, bg=self.bgcolor, fg=_GOLD, width=14, anchor="e"
            ).pack(side=tk.LEFT)


# ─────────────────────────────────────────────────────────────────────────────
# Panel principal
# ─────────────────────────────────────────────────────────────────────────────


class FinancePanel(tk.Frame):
    """
    Tab Finance — resumen de finanzas personales.

    Layout:
      ┌─ toolbar: título + selectores mes/año/cuenta + ↻ ──────┐
      ├─ kpi_row: [Ingresos] [Gastos] [Balance] [≈ USDT] ──────┤
      ├─ body ──────────────────────────────────────────────────┤
      │   left: gastos por categoría   right: últimas txns      │
      └─────────────────────────────────────────────────────────┘
    """

    _MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    def __init__(self, master=None, colores=None):
        bg = colores["bgcolor"] if colores else "#0D0D1A"
        super().__init__(master, bg=bg)
        self.bgcolor = bg
        self._db = FinanceScreen()
        self._sel_month = datetime.now().month
        self._sel_year = datetime.now().year

        self._build()

    # ── construcción ──────────────────────────────────────────────────────────

    def _build(self):
        # toolbar
        tb = tk.Frame(self, bg=self.bgcolor)
        tb.pack(fill=tk.X, padx=10, pady=(8, 4))

        tk.Label(tb, text="Finanzas Personales", font=("Segoe UI", 13, "bold"), bg=self.bgcolor, fg=_ACCENT).pack(
            side=tk.LEFT
        )

        ctrl = tk.Frame(tb, bg=self.bgcolor)
        ctrl.pack(side=tk.RIGHT)

        tk.Label(ctrl, text="Mes:", font=_FONT_LABEL, bg=self.bgcolor, fg=_NEUTRAL).pack(side=tk.LEFT, padx=(0, 2))
        self._cb_month = ttk.Combobox(ctrl, values=self._MONTHS, state="readonly", width=5, style="TCombobox")
        self._cb_month.current(self._sel_month - 1)
        self._cb_month.pack(side=tk.LEFT)
        self._cb_month.bind("<<ComboboxSelected>>", self._on_filter_change)

        tk.Label(ctrl, text="Año:", font=_FONT_LABEL, bg=self.bgcolor, fg=_NEUTRAL).pack(side=tk.LEFT, padx=(8, 2))
        years = [str(y) for y in range(datetime.now().year, datetime.now().year - 4, -1)]
        self._cb_year = ttk.Combobox(ctrl, values=years, state="readonly", width=6, style="TCombobox")
        self._cb_year.current(0)
        self._cb_year.pack(side=tk.LEFT)
        self._cb_year.bind("<<ComboboxSelected>>", self._on_filter_change)

        tk.Label(ctrl, text="Cuenta:", font=_FONT_LABEL, bg=self.bgcolor, fg=_NEUTRAL).pack(side=tk.LEFT, padx=(8, 2))
        self._cb_account = ttk.Combobox(ctrl, values=["Todas"], state="readonly", width=22, style="TCombobox")
        self._cb_account.current(0)
        self._cb_account.pack(side=tk.LEFT)
        self._cb_account.bind("<<ComboboxSelected>>", self._on_filter_change)

        tk.Button(
            ctrl,
            text="↻",
            font=("Segoe UI", 12, "bold"),
            bg=self.bgcolor,
            fg=_ACCENT,
            relief=tk.FLAT,
            activebackground=self.bgcolor,
            cursor="hand2",
            command=self.refresh,
        ).pack(side=tk.LEFT, padx=(8, 0))

        # separador
        tk.Frame(self, bg=_NEUTRAL, height=1).pack(fill=tk.X, padx=10, pady=2)

        # fila KPI
        kpi_row = tk.Frame(self, bg=self.bgcolor)
        kpi_row.pack(fill=tk.X, padx=10, pady=6)

        self._kpi_income = _KpiCard(kpi_row, "Ingresos", value_color=_POSITIVE)
        self._kpi_expense = _KpiCard(kpi_row, "Gastos", value_color=_NEGATIVE)
        self._kpi_balance = _KpiCard(kpi_row, "Balance")
        self._kpi_usdt = _KpiCard(kpi_row, "≈ USDT", value_color=_GOLD)

        for card in (self._kpi_income, self._kpi_expense, self._kpi_balance, self._kpi_usdt):
            card.pack(side=tk.LEFT, padx=6, ipadx=8, ipady=4, fill=tk.X, expand=True)

        # separador
        tk.Frame(self, bg=_NEUTRAL, height=1).pack(fill=tk.X, padx=10, pady=2)

        # body
        body = tk.Frame(self, bg=self.bgcolor)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        left = tk.Frame(body, bg=self.bgcolor)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        tk.Label(left, text="Gastos por categoría", font=_FONT_HEADER, bg=self.bgcolor, fg=_ACCENT).pack(
            anchor="w", pady=(0, 4)
        )
        self._cat_bar = _CategoryBar(left, self.bgcolor)
        self._cat_bar.pack(fill=tk.BOTH, expand=True)

        tk.Frame(body, bg=_NEUTRAL, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        right = tk.Frame(body, bg=self.bgcolor)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        hdr = tk.Frame(right, bg=self.bgcolor)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="Últimas transacciones", font=_FONT_HEADER, bg=self.bgcolor, fg=_ACCENT).pack(
            side=tk.LEFT, pady=(0, 4)
        )
        self._lbl_status = tk.Label(hdr, text="", font=_FONT_SUB, bg=self.bgcolor, fg=_NEUTRAL)
        self._lbl_status.pack(side=tk.RIGHT)

        self._txn_table = _TxnTable(right, self.bgcolor)
        self._txn_table.pack(fill=tk.BOTH, expand=True)

    # ── helpers privados ──────────────────────────────────────────────────────

    def _period(self) -> tuple[str, str]:
        y = self._sel_year
        m = self._sel_month
        last = calendar.monthrange(y, m)[1]
        return f"{y}-{m:02d}-01", f"{y}-{m:02d}-{last:02d}"

    def _account_id(self) -> int | None:
        label = self._cb_account.get()
        if label == "Todas":
            return None
        return self._db.get_account_id(label)

    # ── eventos ───────────────────────────────────────────────────────────────

    def _on_filter_change(self, _event=None):
        self._sel_month = self._MONTHS.index(self._cb_month.get()) + 1
        self._sel_year = int(self._cb_year.get())
        self.refresh()

    # ── público ───────────────────────────────────────────────────────────────

    def refresh(self):
        try:
            date_from, date_to = self._period()
            account_id = self._account_id()

            # KPIs
            kpi = self._db.get_kpis(date_from, date_to, account_id)
            if kpi:
                balance = kpi["ingresos"] - kpi["gastos"]
                balance_usdt = kpi["ing_usdt"] - kpi["gas_usdt"]
                bal_color = _POSITIVE if balance >= 0 else _NEGATIVE

                self._kpi_income.update_value(_fmt_ars(kpi["ingresos"]), sub=f"≈ {_fmt_usdt(kpi['ing_usdt'])}")
                self._kpi_expense.update_value(_fmt_ars(kpi["gastos"]), sub=f"≈ {_fmt_usdt(kpi['gas_usdt'])}")
                self._kpi_balance.update_value(_fmt_ars(balance), sub=f"≈ {_fmt_usdt(balance_usdt)}", color=bal_color)
                self._kpi_usdt.update_value(_fmt_usdt(balance_usdt), sub=f"{kpi['total_txns']} transacciones")
            else:
                for card in (self._kpi_income, self._kpi_expense, self._kpi_balance, self._kpi_usdt):
                    card.update_value("—", sub="Sin datos")

            # Categorías
            self._cat_bar.load(self._db.get_categories_expense(date_from, date_to, account_id))

            # Transacciones
            txns = self._db.get_transactions(date_from, date_to, account_id)
            self._txn_table.load(txns)
            self._lbl_status.config(text=f"{len(txns)} registros — {date_from} → {date_to}", fg=_NEUTRAL)

        except Exception as e:
            _logger.error(f"FinancePanel.refresh: {e}")
            self._lbl_status.config(text=f"Error: {e}", fg=_NEGATIVE)

    def inicializar(self):
        """Llamado desde DashMain tras instanciar — carga cuentas y primer refresh."""
        accounts = self._db.get_accounts()
        labels = ["Todas"] + [r[0] for r in accounts]
        self._cb_account["values"] = labels
        self.refresh()
