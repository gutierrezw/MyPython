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
_BLACK = "#000000"
_WHITE = "#FFFFFF"

_FONT_TITLE = ("Segoe UI", 10, "bold")
_FONT_VALUE = ("Segoe UI", 18, "bold")
_FONT_SUB = ("Segoe UI", 8)
_FONT_LABEL = ("Segoe UI", 9)
_FONT_HEADER = ("Segoe UI", 9, "bold")
_FONT_CHIP = ("Segoe UI", 8, "bold")


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
# Widget: etiqueta de sección con fondo negro
# ─────────────────────────────────────────────────────────────────────────────


class _SectionLabel(tk.Label):
    """Encabezado de sección con fondo negro y texto blanco — fácil lectura."""

    def __init__(self, parent, text, **kw):
        super().__init__(
            parent,
            text=f"  {text}  ",
            font=_FONT_HEADER,
            bg=_BLACK,
            fg=_WHITE,
            padx=4,
            pady=2,
            **kw,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Widget: chip de filtro (toggle)
# ─────────────────────────────────────────────────────────────────────────────


class _Chip(tk.Label):
    """
    Etiqueta clickeable que alterna entre activo/inactivo.
    Activo  → bg negro, fg blanco, borde _ACCENT
    Inactivo → bg gris oscuro, fg _NEUTRAL
    """

    _BG_ON = _BLACK
    _FG_ON = _WHITE
    _BG_OFF = "#1E1E2E"
    _FG_OFF = _NEUTRAL

    def __init__(self, parent, text, on_toggle, bgcolor):
        self._bgcolor = bgcolor
        super().__init__(
            parent,
            text=text,
            font=_FONT_CHIP,
            bg=self._BG_OFF,
            fg=self._FG_OFF,
            padx=7,
            pady=3,
            bd=1,
            relief=tk.SOLID,
            cursor="hand2",
        )
        self._active = False
        self._on_toggle = on_toggle
        self.bind("<Button-1>", self._click)
        self._refresh()

    def _click(self, _e=None):
        self._active = not self._active
        self._refresh()
        self._on_toggle(self)

    def _refresh(self):
        if self._active:
            self.config(
                bg=self._BG_ON,
                fg=self._FG_ON,
                highlightthickness=1,
                highlightbackground=_ACCENT,
                highlightcolor=_ACCENT,
            )
        else:
            self.config(bg=self._BG_OFF, fg=self._FG_OFF, highlightthickness=0)

    def set_active(self, value: bool):
        if self._active != value:
            self._active = value
            self._refresh()

    @property
    def active(self) -> bool:
        return self._active


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
# Widget: tabla de transacciones con filtro de categoría y editor inline
# ─────────────────────────────────────────────────────────────────────────────


class _TxnTable(tk.Frame):
    """
    Treeview de transacciones.
    - Clic en encabezado "Categoría" → limpiar filtro de categoría
    - Doble-clic en fila → popup para cambiar categoría
    """

    COLS = ("Fecha", "Cuenta", "Descripción", "Categoría", "Moneda", "Monto")
    WIDTHS = (80, 150, 320, 140, 60, 110)

    def __init__(self, parent, bgcolor, on_category_edit):
        super().__init__(parent, bg=bgcolor)
        self._on_category_edit = on_category_edit  # callback(txn_id, iid)
        self._all_rows: list[dict] = []
        self._cat_filter: str | None = None  # nombre de categoría activo
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

        self.tree.bind("<Double-1>", self._on_double_click)

    def _on_double_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        col = self.tree.identify_column(event.x)
        # col "#4" = Categoría (índice 1-based)
        if col != "#4":
            return
        # buscar fila original por iid
        for r in self._all_rows:
            if r.get("_iid") == iid:
                self._on_category_edit(r["txn_id"], iid, r)
                return

    def load(self, rows: list[dict]):
        """Carga todas las filas; aplica filtro de categoría si hay uno activo."""
        self._all_rows = rows
        self._render()

    def set_category_filter(self, cat_name: str | None):
        """Filtra la tabla por categoría. None = sin filtro."""
        self._cat_filter = cat_name
        self._render()

    def update_row_category(self, iid: str, new_cat_name: str):
        """Actualiza el texto de categoría de una fila ya insertada."""
        vals = list(self.tree.item(iid, "values"))
        vals[3] = new_cat_name
        self.tree.item(iid, values=vals)
        # también en _all_rows
        for r in self._all_rows:
            if r.get("_iid") == iid:
                r["category"] = new_cat_name
                break
        # re-aplicar filtro si hay uno activo
        if self._cat_filter and self._cat_filter != new_cat_name:
            self.tree.detach(iid)

    def _render(self):
        self.tree.delete(*self.tree.get_children())
        rows = self._all_rows
        if self._cat_filter:
            rows = [r for r in rows if r.get("category") == self._cat_filter]
        for r in rows:
            monto = _fmt_ars(r["amount"]) if r.get("currency") == "ARS" else _fmt_usdt(r["amount"])
            iid = self.tree.insert(
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
            r["_iid"] = iid

    @property
    def visible_count(self) -> int:
        return len(self.tree.get_children())


# ─────────────────────────────────────────────────────────────────────────────
# Widget: barra de gastos por categoría (clickeable para filtrar)
# ─────────────────────────────────────────────────────────────────────────────


class _CategoryBar(tk.Frame):
    """
    Lista de categorías con barra proporcional y monto.
    Clic en una fila → llama on_select(cat_name).
    Clic en fila activa → deselecciona (on_select(None)).
    """

    def __init__(self, parent, bgcolor, on_select):
        super().__init__(parent, bg=bgcolor)
        self.bgcolor = bgcolor
        self._on_select = on_select
        self._active_cat: str | None = None
        self._rows: list[tuple] = []  # (frame, name_label, canvas, amount_label)

    def load(self, data: list[dict]):
        """data = [{"name": str, "total": float, "pct": float}, ...]"""
        for w in self.winfo_children():
            w.destroy()
        self._rows.clear()
        self._active_cat = None

        max_pct = max((d["pct"] for d in data), default=1) or 1
        bar_w = 120

        for d in data[:12]:
            name = d["name"]
            row_frame = tk.Frame(self, bg=self.bgcolor, cursor="hand2")
            row_frame.pack(fill=tk.X, pady=1)

            name_lbl = tk.Label(
                row_frame,
                text=name,
                font=_FONT_LABEL,
                bg=self.bgcolor,
                fg="white",
                width=16,
                anchor="w",
                cursor="hand2",
            )
            name_lbl.pack(side=tk.LEFT)

            filled = max(int(bar_w * d["pct"] / max_pct), 2)
            canvas = tk.Canvas(row_frame, width=bar_w, height=14, bg=self.bgcolor, highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=4)
            canvas.create_rectangle(0, 2, filled, 12, fill=_ACCENT, outline="", tags="bar")

            amt_lbl = tk.Label(
                row_frame,
                text=_fmt_ars(d["total"]),
                font=_FONT_LABEL,
                bg=self.bgcolor,
                fg=_GOLD,
                width=12,
                anchor="e",
                cursor="hand2",
            )
            amt_lbl.pack(side=tk.LEFT)

            self._rows.append((row_frame, name_lbl, canvas, amt_lbl, name))

            # bind clic en todos los widgets de la fila
            for widget in (row_frame, name_lbl, canvas, amt_lbl):
                widget.bind("<Button-1>", lambda _e, n=name: self._click(n))

    def _click(self, cat_name: str):
        if self._active_cat == cat_name:
            # deseleccionar
            self._active_cat = None
            self._on_select(None)
        else:
            self._active_cat = cat_name
            self._on_select(cat_name)
        self._highlight()

    def _highlight(self):
        for row_frame, name_lbl, canvas, amt_lbl, name in self._rows:
            if name == self._active_cat:
                row_frame.config(bg=_BLACK)
                name_lbl.config(bg=_BLACK, fg=_WHITE)
                canvas.config(bg=_BLACK)
                amt_lbl.config(bg=_BLACK)
            else:
                row_frame.config(bg=self.bgcolor)
                name_lbl.config(bg=self.bgcolor, fg="white")
                canvas.config(bg=self.bgcolor)
                amt_lbl.config(bg=self.bgcolor)

    def clear_filter(self):
        self._active_cat = None
        self._highlight()


# ─────────────────────────────────────────────────────────────────────────────
# Popup: editar categoría de una transacción
# ─────────────────────────────────────────────────────────────────────────────


class _CategoryEditPopup(tk.Toplevel):
    """
    Ventana flotante para cambiar la categoría de una transacción.

    Además de actualizar la transacción, permite guardar el patrón como
    regla automática en fin_import_rules (tipo contains/startswith/exact).

    on_save(txn_id, iid, cat_id, cat_name, pattern, match_type)
      pattern=None → no guardar regla.
    """

    _MATCH_TYPES = ["contains", "startswith", "exact", "regex"]

    def __init__(self, parent, txn_row: dict, categories: list[tuple], on_save, db_preview):
        super().__init__(parent)
        self.title("Editar categoría")
        self.resizable(False, False)
        self.configure(bg=_CARD_BG)
        self.grab_set()

        self._txn_row = txn_row
        self._on_save = on_save
        self._db_preview = db_preview  # callable(pattern, match_type) → int
        self._cat_map = {name: cid for cid, name in categories}
        cat_names = [name for _, name in categories]

        raw_desc = txn_row.get("description", "")

        # ── descripción de la transacción ──────────────────────────────────
        tk.Label(self, text="Transacción:", font=_FONT_LABEL, bg=_CARD_BG, fg=_NEUTRAL).pack(
            anchor="w", padx=14, pady=(12, 0)
        )
        tk.Label(self, text=raw_desc[:70], font=_FONT_HEADER, bg=_CARD_BG, fg=_WHITE).pack(
            anchor="w", padx=14, pady=(0, 8)
        )

        # ── selector de categoría ──────────────────────────────────────────
        tk.Label(self, text="Categoría:", font=_FONT_LABEL, bg=_CARD_BG, fg=_NEUTRAL).pack(anchor="w", padx=14)
        self._cb_cat = ttk.Combobox(self, values=cat_names, state="normal", width=34)
        cur_cat = txn_row.get("category", "")
        if cur_cat in cat_names:
            self._cb_cat.set(cur_cat)
        self._cb_cat.pack(padx=14, pady=(4, 10))
        self._cb_cat.focus_set()

        # ── separador ──────────────────────────────────────────────────────
        tk.Frame(self, bg=_NEUTRAL, height=1).pack(fill=tk.X, padx=14, pady=(0, 8))

        # ── sección de regla automática ────────────────────────────────────
        rule_hdr = tk.Frame(self, bg=_CARD_BG)
        rule_hdr.pack(fill=tk.X, padx=14)

        self._var_guardar_regla = tk.BooleanVar(value=True)
        tk.Checkbutton(
            rule_hdr,
            text="Guardar como regla automática",
            variable=self._var_guardar_regla,
            font=_FONT_LABEL,
            bg=_CARD_BG,
            fg=_WHITE,
            activebackground=_CARD_BG,
            activeforeground=_ACCENT,
            selectcolor=_BLACK,
            cursor="hand2",
            command=self._toggle_rule_section,
        ).pack(side=tk.LEFT)

        self._rule_frame = tk.Frame(self, bg=_CARD_BG)
        self._rule_frame.pack(fill=tk.X, padx=14, pady=(6, 0))

        tk.Label(self._rule_frame, text="Patrón:", font=_FONT_LABEL, bg=_CARD_BG, fg=_NEUTRAL).pack(anchor="w")
        self._var_pattern = tk.StringVar(value=raw_desc.strip())
        tk.Entry(
            self._rule_frame,
            textvariable=self._var_pattern,
            font=_FONT_LABEL,
            bg="#0D0D1A",
            fg=_WHITE,
            insertbackground=_WHITE,
            relief=tk.FLAT,
            width=36,
        ).pack(fill=tk.X, pady=(2, 6))

        match_row = tk.Frame(self._rule_frame, bg=_CARD_BG)
        match_row.pack(fill=tk.X)
        tk.Label(match_row, text="Tipo:", font=_FONT_LABEL, bg=_CARD_BG, fg=_NEUTRAL).pack(side=tk.LEFT, padx=(0, 4))
        self._cb_match = ttk.Combobox(match_row, values=self._MATCH_TYPES, state="readonly", width=14)
        self._cb_match.set("contains")
        self._cb_match.pack(side=tk.LEFT)

        # preview: cuántas transacciones sin categoría coincidirán
        self._lbl_preview = tk.Label(self._rule_frame, text="", font=_FONT_SUB, bg=_CARD_BG, fg=_GOLD)
        self._lbl_preview.pack(anchor="w", pady=(6, 0))

        # actualizar preview al cambiar patrón o tipo
        self._var_pattern.trace_add("write", lambda *_: self._refresh_preview())
        self._cb_match.bind("<<ComboboxSelected>>", lambda _e: self._refresh_preview())
        self._refresh_preview()

        # ── botones ────────────────────────────────────────────────────────
        btn_row = tk.Frame(self, bg=_CARD_BG)
        btn_row.pack(fill=tk.X, padx=14, pady=14)

        tk.Button(
            btn_row,
            text="Guardar",
            font=_FONT_LABEL,
            bg=_ACCENT,
            fg=_BLACK,
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._save,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_row,
            text="Cancelar",
            font=_FONT_LABEL,
            bg="#2A2A3E",
            fg=_NEUTRAL,
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.destroy,
        ).pack(side=tk.LEFT)

        self.bind("<Return>", lambda _e: self._save())
        self.bind("<Escape>", lambda _e: self.destroy())
        self._center(parent)

    def _toggle_rule_section(self):
        if self._var_guardar_regla.get():
            self._rule_frame.pack(fill=tk.X, padx=14, pady=(6, 0))
        else:
            self._rule_frame.pack_forget()
        self.update_idletasks()

    def _refresh_preview(self):
        """Muestra cuántas txns sin categoría coincidirían con el patrón actual."""
        pattern = self._var_pattern.get().strip()
        match_type = self._cb_match.get()
        if not pattern or not match_type:
            self._lbl_preview.config(text="")
            return
        try:
            count = self._db_preview(pattern, match_type)
            if count > 0:
                self._lbl_preview.config(
                    text=f"↳ clasificará {count} transacción{'es' if count > 1 else ''} sin categoría",
                    fg=_GOLD,
                )
            else:
                self._lbl_preview.config(text="↳ ninguna transacción sin categoría coincide", fg=_NEUTRAL)
        except Exception:
            self._lbl_preview.config(text="")

    def _center(self, parent):
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - self.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{px}+{py}")

    def _save(self):
        name = self._cb_cat.get().strip()
        if not name:
            return
        cat_id = self._cat_map.get(name)

        pattern = None
        match_type = None
        if self._var_guardar_regla.get():
            pattern = self._var_pattern.get().strip()
            match_type = self._cb_match.get()
            if not pattern:
                pattern = None

        self._on_save(self._txn_row["txn_id"], self._txn_row.get("_iid"), cat_id, name, pattern, match_type)
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Panel principal
# ─────────────────────────────────────────────────────────────────────────────


class FinancePanel(tk.Frame):
    """
    Tab Finance — resumen de finanzas personales.

    Layout:
      ┌─ toolbar: título + selectores mes/año + ↻ ──────────────┐
      ├─ chip_row: [Todas] [Banco...] [Cuenta...] ──────────────┤
      ├─ kpi_row: [Ingresos] [Gastos] [Balance] [≈ USDT] ───────┤
      ├─ body ───────────────────────────────────────────────────┤
      │   left: gastos por categoría   right: últimas txns       │
      └──────────────────────────────────────────────────────────┘

    Filtros:
      - Banco / Cuenta: chips en chip_row
      - Categoría: clic en barra izquierda → filtra tabla derecha
      - Editar categoría: doble-clic en columna "Categoría" de la tabla
    """

    _MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    def __init__(self, master=None, colores=None):
        bg = colores["bgcolor"] if colores else "#0D0D1A"
        super().__init__(master, bg=bg)
        self.bgcolor = bg
        self._db = FinanceScreen()
        self._sel_month = datetime.now().month
        self._sel_year = datetime.now().year

        self._accounts: list[tuple] = []
        self._categories: list[tuple] = []  # [(id, name), ...]

        self._bank_chips: dict[str, _Chip] = {}
        self._account_chips: dict[int, _Chip] = {}
        self._chip_todas: _Chip | None = None

        self._build()

    # ── construcción ──────────────────────────────────────────────────────────

    def _build(self):
        # ── toolbar ──────────────────────────────────────────────────────────
        tb = tk.Frame(self, bg=self.bgcolor)
        tb.pack(fill=tk.X, padx=10, pady=(8, 4))

        tk.Label(tb, text="Finanzas Personales", font=("Segoe UI", 13, "bold"), bg=self.bgcolor, fg=_ACCENT).pack(
            side=tk.LEFT
        )

        ctrl = tk.Frame(tb, bg=self.bgcolor)
        ctrl.pack(side=tk.RIGHT)

        tk.Label(ctrl, text="Mes:", font=_FONT_LABEL, bg=_BLACK, fg=_WHITE, padx=4, pady=2).pack(
            side=tk.LEFT, padx=(0, 2)
        )
        self._cb_month = ttk.Combobox(ctrl, values=self._MONTHS, state="readonly", width=5)
        self._cb_month.current(self._sel_month - 1)
        self._cb_month.pack(side=tk.LEFT)
        self._cb_month.bind("<<ComboboxSelected>>", self._on_filter_change)

        tk.Label(ctrl, text="Año:", font=_FONT_LABEL, bg=_BLACK, fg=_WHITE, padx=4, pady=2).pack(
            side=tk.LEFT, padx=(8, 2)
        )
        years = [str(y) for y in range(datetime.now().year, datetime.now().year - 4, -1)]
        self._cb_year = ttk.Combobox(ctrl, values=years, state="readonly", width=6)
        self._cb_year.current(0)
        self._cb_year.pack(side=tk.LEFT)
        self._cb_year.bind("<<ComboboxSelected>>", self._on_filter_change)

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

        # ── chips de banco/cuenta (se pueblan en inicializar) ─────────────────
        self._chip_frame = tk.Frame(self, bg=self.bgcolor)
        self._chip_frame.pack(fill=tk.X, padx=10, pady=(2, 4))

        # ── separador ────────────────────────────────────────────────────────
        tk.Frame(self, bg=_NEUTRAL, height=1).pack(fill=tk.X, padx=10, pady=2)

        # ── fila KPI ─────────────────────────────────────────────────────────
        kpi_row = tk.Frame(self, bg=self.bgcolor)
        kpi_row.pack(fill=tk.X, padx=10, pady=6)

        self._kpi_income = _KpiCard(kpi_row, "Ingresos", value_color=_POSITIVE)
        self._kpi_expense = _KpiCard(kpi_row, "Gastos", value_color=_NEGATIVE)
        self._kpi_balance = _KpiCard(kpi_row, "Balance")
        self._kpi_usdt = _KpiCard(kpi_row, "≈ USDT", value_color=_GOLD)

        for card in (self._kpi_income, self._kpi_expense, self._kpi_balance, self._kpi_usdt):
            card.pack(side=tk.LEFT, padx=6, ipadx=8, ipady=4, fill=tk.X, expand=True)

        # ── separador ────────────────────────────────────────────────────────
        tk.Frame(self, bg=_NEUTRAL, height=1).pack(fill=tk.X, padx=10, pady=2)

        # ── body ─────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=self.bgcolor)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        # panel izquierdo — categorías
        left = tk.Frame(body, bg=self.bgcolor)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        _SectionLabel(left, "Gastos por categoría").pack(anchor="w", pady=(0, 6))
        self._cat_bar = _CategoryBar(left, self.bgcolor, on_select=self._on_category_select)
        self._cat_bar.pack(fill=tk.BOTH, expand=True)

        tk.Frame(body, bg=_NEUTRAL, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        # panel derecho — transacciones
        right = tk.Frame(body, bg=self.bgcolor)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        hdr = tk.Frame(right, bg=self.bgcolor)
        hdr.pack(fill=tk.X)

        self._lbl_txn_section = _SectionLabel(hdr, "Últimas transacciones")
        self._lbl_txn_section.pack(side=tk.LEFT, pady=(0, 6))

        # botón limpiar filtro de categoría (visible solo cuando hay filtro activo)
        self._btn_clear_cat = tk.Button(
            hdr,
            text="✕ categoría",
            font=_FONT_SUB,
            bg="#2A2A3E",
            fg=_NEUTRAL,
            relief=tk.FLAT,
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._clear_category_filter,
        )

        self._lbl_status = tk.Label(hdr, text="", font=_FONT_SUB, bg=_BLACK, fg=_WHITE, padx=6, pady=2)
        self._lbl_status.pack(side=tk.RIGHT)

        self._txn_table = _TxnTable(right, self.bgcolor, on_category_edit=self._on_category_edit)
        self._txn_table.pack(fill=tk.BOTH, expand=True)

    def _build_chips(self):
        """Puebla la fila de chips con 'Todas', chips de banco y chips de cuenta."""
        for w in self._chip_frame.winfo_children():
            w.destroy()
        self._bank_chips.clear()
        self._account_chips.clear()

        self._chip_todas = _Chip(self._chip_frame, "Todas", self._on_chip_todas, self.bgcolor)
        self._chip_todas.pack(side=tk.LEFT, padx=(0, 6))
        self._chip_todas.set_active(True)

        tk.Frame(self._chip_frame, bg=_NEUTRAL, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        banks: dict[str, list[tuple]] = {}
        for row in self._accounts:
            banks.setdefault(row[2], []).append(row)

        for bank_name, accts in banks.items():
            bc = _Chip(self._chip_frame, bank_name, self._on_chip_bank, self.bgcolor)
            bc.pack(side=tk.LEFT, padx=2)
            self._bank_chips[bank_name] = bc

            for _label, acct_id, bname, aname in accts:
                short = aname.replace(bname, "").strip(" -—")
                ac = _Chip(self._chip_frame, short, self._on_chip_account, self.bgcolor)
                ac._bank = bank_name  # type: ignore[attr-defined]
                ac._acct_id = acct_id  # type: ignore[attr-defined]
                ac.pack(side=tk.LEFT, padx=2)
                self._account_chips[acct_id] = ac

            tk.Frame(self._chip_frame, bg=_NEUTRAL, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=6)

    # ── lógica chips banco/cuenta ─────────────────────────────────────────────

    def _deactivate_all_chips(self):
        if self._chip_todas:
            self._chip_todas.set_active(False)
        for c in self._bank_chips.values():
            c.set_active(False)
        for c in self._account_chips.values():
            c.set_active(False)

    def _on_chip_todas(self, chip: _Chip):
        self._deactivate_all_chips()
        chip.set_active(True)
        self.refresh()

    def _on_chip_bank(self, chip: _Chip):
        bank_name = chip.cget("text").strip()
        if chip.active:
            self._chip_todas.set_active(False)
            for c in self._bank_chips.values():
                if c is not chip:
                    c.set_active(False)
            for c in self._account_chips.values():
                c.set_active(c._bank == bank_name)  # type: ignore[attr-defined]
        else:
            if not any(c.active for c in self._account_chips.values()):
                self._chip_todas.set_active(True)
        self.refresh()

    def _on_chip_account(self, chip: _Chip):
        self._chip_todas.set_active(False)
        bank_name = chip._bank  # type: ignore[attr-defined]
        bank_accts = [c for c in self._account_chips.values() if c._bank == bank_name]  # type: ignore[attr-defined]
        bank_chip = self._bank_chips.get(bank_name)
        if bank_chip:
            bank_chip.set_active(all(c.active for c in bank_accts))
        if not any(c.active for c in self._account_chips.values()):
            self._chip_todas.set_active(True)
        self.refresh()

    def _selected_account_ids(self) -> list[int] | None:
        if self._chip_todas and self._chip_todas.active:
            return None
        selected = [aid for aid, c in self._account_chips.items() if c.active]
        return selected if selected else None

    # ── lógica filtro categoría ───────────────────────────────────────────────

    def _on_category_select(self, cat_name: str | None):
        self._txn_table.set_category_filter(cat_name)
        if cat_name:
            self._lbl_txn_section.config(text=f"  {cat_name}  ")
            self._btn_clear_cat.pack(side=tk.LEFT, padx=(6, 0), pady=(0, 6))
        else:
            self._clear_category_filter()
        self._update_status()

    def _clear_category_filter(self):
        self._txn_table.set_category_filter(None)
        self._cat_bar.clear_filter()
        self._lbl_txn_section.config(text="  Últimas transacciones  ")
        self._btn_clear_cat.pack_forget()
        self._update_status()

    def _update_status(self):
        count = self._txn_table.visible_count
        df, dt = self._period()
        self._lbl_status.config(text=f"{count} registros — {df} → {dt}", fg=_WHITE)

    # ── lógica edición de categoría ───────────────────────────────────────────

    def _on_category_edit(self, txn_id: int, iid: str, txn_row: dict):
        """Abre popup para editar la categoría de txn_id."""
        _CategoryEditPopup(
            self,
            txn_row,
            self._categories,
            on_save=self._save_category,
            db_preview=self._db.save_rule_count_retro,
        )

    def _save_category(
        self,
        txn_id: int,
        iid: str,
        cat_id: int | None,
        cat_name: str,
        pattern: str | None,
        match_type: str | None,
    ):
        """Persiste el cambio de categoría y, opcionalmente, guarda la regla."""
        ok = self._db.update_txn_category(txn_id, cat_id)
        if ok and iid:
            self._txn_table.update_row_category(iid, cat_name)
            self._update_status()

        if pattern and match_type and cat_id is not None:
            saved = self._db.save_rule(pattern, match_type, cat_id)
            if saved:
                _logger.warning(f"Regla guardada: [{match_type}] '{pattern}' → {cat_name}")
            else:
                _logger.warning(f"Regla ya existente o error: [{match_type}] '{pattern}'")

    # ── helpers privados ──────────────────────────────────────────────────────

    def _period(self) -> tuple[str, str]:
        y = self._sel_year
        m = self._sel_month
        last = calendar.monthrange(y, m)[1]
        return f"{y}-{m:02d}-01", f"{y}-{m:02d}-{last:02d}"

    def _on_filter_change(self, _event=None):
        self._sel_month = self._MONTHS.index(self._cb_month.get()) + 1
        self._sel_year = int(self._cb_year.get())
        self.refresh()

    # ── público ───────────────────────────────────────────────────────────────

    def refresh(self):
        try:
            date_from, date_to = self._period()
            account_ids = self._selected_account_ids()

            kpi = self._db.get_kpis(date_from, date_to, account_ids)
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

            # reset filtro de categoría al refrescar
            self._clear_category_filter()

            self._cat_bar.load(self._db.get_categories_expense(date_from, date_to, account_ids))

            txns = self._db.get_transactions(date_from, date_to, account_ids)
            self._txn_table.load(txns)
            self._lbl_status.config(text=f"{len(txns)} registros — {date_from} → {date_to}", fg=_WHITE)

        except Exception as e:
            _logger.error(f"FinancePanel.refresh: {e}")
            self._lbl_status.config(text=f"Error: {e}", fg=_NEGATIVE)

    def inicializar(self):
        """Llamado desde DashMain tras instanciar — carga cuentas, categorías, chips y refresca."""
        self._accounts = self._db.get_accounts()
        self._categories = self._db.get_categories()
        self._build_chips()
        self.refresh()
