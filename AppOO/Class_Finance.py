from Modulos_python import (
    tk,
    ttk,
    calendar,
    os,
    re,
    shutil,
    hashlib,
    time,
    datetime,
    date,
    timedelta,
    timezone,
    Decimal,
    InvalidOperation,
    logging,
    pdfplumber,
    connect,
    Error,
    Figure,
    FigureCanvasTkAgg,
    ticker,
)
from Modulos_Mysql import BDsystem, FinanceScreen
from Class_ApiBinnace import BinanceClient

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


def _fmt_amount(v, currency: str) -> str:
    """Formatea monto según divisa: ARS=$ , USD=U$ , cualquier otra=número plano."""
    try:
        val = float(v)
        if currency == "ARS":
            return f"$ {val:,.0f}".replace(",", ".")
        if currency == "USD":
            return f"U$ {val:,.2f}"
        return f"{val:,.2f}"  # VES u otras: número sin símbolo
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
            padx=4,
            pady=2,
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
    """Tarjeta con título, valor grande y dos líneas de subtexto."""

    def __init__(self, parent, title="", value_color=None):
        super().__init__(parent, bg=_CARD_BG, bd=0, highlightthickness=1, highlightbackground=_NEUTRAL)
        self._vcolor = value_color or _ACCENT

        tk.Label(self, text=title, font=_FONT_TITLE, bg=_CARD_BG, fg=_NEUTRAL).pack(anchor="w", padx=10, pady=(8, 0))
        self._val_lbl = tk.Label(self, text="—", font=_FONT_VALUE, bg=_CARD_BG, fg=self._vcolor)
        self._val_lbl.pack(anchor="w", padx=10)
        self._sub_lbl = tk.Label(self, text="", font=_FONT_SUB, bg=_CARD_BG, fg=_NEUTRAL)
        self._sub_lbl.pack(anchor="w", padx=10, pady=(0, 2))
        self._sub2_lbl = tk.Label(self, text="", font=_FONT_SUB, bg=_CARD_BG, fg=_NEUTRAL)
        self._sub2_lbl.pack(anchor="w", padx=10, pady=(0, 8))

    def update_value(self, value, sub="", sub2="", color=None):
        self._val_lbl.config(text=value, fg=color or self._vcolor)
        self._sub_lbl.config(text=sub)
        self._sub2_lbl.config(text=sub2)


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

    def __init__(self, parent, bgcolor, on_category_edit, on_date_edit=None):
        super().__init__(parent, bg=bgcolor)
        self._on_category_edit = on_category_edit  # callback(txn_id, iid, row)
        self._on_date_edit = on_date_edit  # callback(txn_id, iid, row)
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
        for r in self._all_rows:
            if r.get("_iid") != iid:
                continue
            if col == "#1" and self._on_date_edit:  # Fecha
                self._on_date_edit(r["txn_id"], iid, r)
            elif col == "#4":  # Categoría
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

    def update_row_date(self, iid: str, new_date: str):
        """Actualiza la fecha visible de una fila ya insertada."""
        vals = list(self.tree.item(iid, "values"))
        vals[0] = new_date
        self.tree.item(iid, values=vals)
        for r in self._all_rows:
            if r.get("_iid") == iid:
                r["date"] = new_date
                break

    def _render(self):
        self.tree.delete(*self.tree.get_children())
        rows = self._all_rows
        if self._cat_filter:
            rows = [r for r in rows if r.get("category") == self._cat_filter]
        for r in rows:
            monto = _fmt_amount(r["amount"], r.get("currency", "ARS"))
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

    @property
    def category_filter(self) -> str | None:
        return self._cat_filter


# ─────────────────────────────────────────────────────────────────────────────
# Widget: semáforo de cobertura por cuenta
# ─────────────────────────────────────────────────────────────────────────────


class _CoverageTable(tk.Frame):
    """
    Una fila por cuenta activa: último movimiento cargado, días de atraso y próximo cierre en las tarjetas.
    Verde al día, naranja por vencer, rojo atrasada, gris sin datos.
    """

    COLS = ("Cuenta", "Último mov.", "Atraso", "Próximo cierre")
    WIDTHS = (260, 120, 90, 130)

    def __init__(self, parent, bgcolor):
        super().__init__(parent, bg=bgcolor)
        self._build()

    def _build(self):
        vsb = ttk.Scrollbar(self, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(self, columns=self.COLS, show="headings", height=10, yscrollcommand=vsb.set)
        vsb.config(command=self.tree.yview)

        for col, w in zip(self.COLS, self.WIDTHS):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor=tk.E if col == "Atraso" else tk.W, stretch=False)

        self.tree.tag_configure("ok", foreground=_POSITIVE)
        self.tree.tag_configure("aviso", foreground=_GOLD)
        self.tree.tag_configure("atraso", foreground=_NEGATIVE)
        self.tree.tag_configure("sin_datos", foreground=_NEUTRAL)
        self.tree.pack(fill=tk.BOTH, expand=True)

    def load(self, rows: list[dict]):
        """Carga el estado de cada cuenta; rows viene de FinanceScreen.get_coverage()."""
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            dias = r.get("days")
            self.tree.insert(
                "",
                tk.END,
                values=(
                    r.get("account", ""),
                    r.get("last_date") or "nunca",
                    f"{dias} d" if dias is not None else "—",
                    r.get("next_closing") or "—",
                ),
                tags=(r.get("status", "ok"),),
            )


class _CommitmentsTable(tk.Frame):
    """
    Cuotas de planes vigentes que todavía no llegaron en ningún resumen, en bloques por mes.
    Cada mes abre con su total: ese es el número que hay que tener reservado para pagar el resumen completo.
    Las filas de tarjeta se destacan — son las que el banco cuotifica solo si el resumen no se paga entero.
    """

    COLS = ("Mes", "Cuenta", "Concepto", "Cuota", "Monto", "USD")
    WIDTHS = (70, 190, 250, 60, 120, 80)

    def __init__(self, parent, bgcolor):
        super().__init__(parent, bg=bgcolor)
        self.totals: dict[str, float] = {}
        self._build()

    def _build(self):
        vsb = ttk.Scrollbar(self, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(self, columns=self.COLS, show="headings", height=10, yscrollcommand=vsb.set)
        vsb.config(command=self.tree.yview)

        for col, w in zip(self.COLS, self.WIDTHS):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor=tk.E if col in ("Cuota", "Monto", "USD") else tk.W, stretch=False)

        self.tree.tag_configure("total", foreground=_GOLD)
        self.tree.tag_configure("credit", foreground=_WHITE)
        self.tree.tag_configure("debit", foreground=_NEUTRAL)
        self.tree.pack(fill=tk.BOTH, expand=True)

    def load(self, rows: list[dict]):
        """Carga las cuotas proyectadas; rows viene de FinanceScreen.get_installments_pending()."""
        self.tree.delete(*self.tree.get_children())
        self.totals = {}
        for r in rows:
            self.totals[r["period"]] = self.totals.get(r["period"], 0) + r.get("usdt", 0)

        for period in sorted(self.totals):
            grupo = [r for r in rows if r["period"] == period]
            self.tree.insert(
                "",
                tk.END,
                values=(period, f"{len(grupo)} cuotas", "TOTAL COMPROMETIDO", "", "", f"{self.totals[period]:,.0f}"),
                tags=("total",),
            )
            for r in sorted(grupo, key=lambda x: -x.get("usdt", 0)):
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        "",
                        r.get("account", ""),
                        r.get("description", "")[:60],
                        r.get("installment", ""),
                        f"{r.get('amount', 0):,.0f} {r.get('currency', '')}",
                        f"{r.get('usdt', 0):,.0f}",
                    ),
                    tags=("credit" if r.get("type") == "credit" else "debit",),
                )


# ─────────────────────────────────────────────────────────────────────────────
# Widget: barra de gastos por categoría (clickeable para filtrar)
# ─────────────────────────────────────────────────────────────────────────────


class _CategoryBar(tk.Frame):
    """
    Lista scrollable de categorías con barra proporcional y monto.
    Clic en una fila → llama on_select(cat_name).
    Clic en fila activa → deselecciona (on_select(None)).
    """

    _ROW_H = 18  # altura estimada por fila en px
    _MAX_H = 280  # altura máxima visible del panel

    def __init__(self, parent, bgcolor, on_select, bar_color=None):
        super().__init__(parent, bg=bgcolor)
        self.bgcolor = bgcolor
        self._on_select = on_select
        self._bar_color = bar_color or _ACCENT
        self._active_cat: str | None = None
        self._rows: list[tuple] = []

        # canvas scrollable
        self._canvas = tk.Canvas(self, bg=bgcolor, highlightthickness=0, width=380)
        self._vsb = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vsb.set)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._inner = tk.Frame(self._canvas, bg=bgcolor)
        self._canvas_window = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<MouseWheel>", self._on_mousewheel)

    def _on_inner_configure(self, _event=None):
        total_h = self._inner.winfo_reqheight()
        visible_h = min(total_h, self._MAX_H)
        self._canvas.configure(scrollregion=self._canvas.bbox("all"), height=visible_h)
        self._vsb.pack(side=tk.RIGHT, fill=tk.Y) if total_h > self._MAX_H else self._vsb.pack_forget()

    def _on_canvas_resize(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def load(self, data: list[dict], income_total: float = 0):
        """data = [{"name": str, "total": float, "pct": float}, ...]
        income_total: si > 0 muestra columna %ing a la derecha del monto.
        """
        for w in self._inner.winfo_children():
            w.destroy()
        self._rows.clear()
        self._active_cat = None

        max_pct = max((abs(d["pct"]) for d in data), default=1) or 1
        bar_w = 80
        show_pct_ing = income_total > 0

        for d in data:
            name = d["name"]
            display = name if len(name) <= 20 else name[:19] + "…"
            row_frame = tk.Frame(self._inner, bg=self.bgcolor, cursor="hand2")
            row_frame.pack(fill=tk.X, pady=1)

            name_lbl = tk.Label(
                row_frame,
                text=display,
                font=_FONT_LABEL,
                bg=self.bgcolor,
                fg="white",
                width=20,
                anchor="w",
                cursor="hand2",
            )
            name_lbl.pack(side=tk.LEFT)

            filled = max(int(bar_w * abs(d["pct"]) / max_pct), 2)
            canvas = tk.Canvas(row_frame, width=bar_w, height=14, bg=self.bgcolor, highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=4)
            canvas.create_rectangle(0, 2, filled, 12, fill=self._bar_color, outline="", tags="bar")

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

            pct_lbl = None
            if show_pct_ing:
                pct_val = d["total"] / income_total * 100
                pct_lbl = tk.Label(
                    row_frame,
                    text=f"{pct_val:.1f}%",
                    font=_FONT_LABEL,
                    bg=self.bgcolor,
                    fg=_NEUTRAL,
                    width=6,
                    anchor="e",
                    cursor="hand2",
                )
                pct_lbl.pack(side=tk.LEFT, padx=(2, 0))

            self._rows.append((row_frame, name_lbl, canvas, amt_lbl, name, pct_lbl))

            bind_targets = [row_frame, name_lbl, canvas, amt_lbl]
            if pct_lbl:
                bind_targets.append(pct_lbl)
            for widget in bind_targets:
                widget.bind("<Button-1>", lambda _e, n=name: self._click(n))
                widget.bind("<MouseWheel>", self._on_mousewheel)

    def _click(self, cat_name: str):
        if self._active_cat == cat_name:
            self._active_cat = None
            self._on_select(None)
        else:
            self._active_cat = cat_name
            self._on_select(cat_name)
        self._highlight()

    def _highlight(self):
        for row_frame, name_lbl, canvas, amt_lbl, name, pct_lbl in self._rows:
            if name == self._active_cat:
                row_frame.config(bg=_BLACK)
                name_lbl.config(bg=_BLACK, fg=_WHITE)
                canvas.config(bg=_BLACK)
                amt_lbl.config(bg=_BLACK)
                if pct_lbl:
                    pct_lbl.config(bg=_BLACK)
            else:
                row_frame.config(bg=self.bgcolor)
                name_lbl.config(bg=self.bgcolor, fg="white")
                canvas.config(bg=self.bgcolor)
                amt_lbl.config(bg=self.bgcolor)
                if pct_lbl:
                    pct_lbl.config(bg=self.bgcolor)

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
        self._cat_map = {name: cid for cid, name, *_ in categories}
        cat_names = [name for _, name, *_ in categories]

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


class _DateEditPopup(tk.Toplevel):
    """
    Ventana flotante para corregir la fecha de una transacción.
    Útil para ajustar el desfase BBVA (fecha acreditación vs fecha operación).
    on_save(txn_id, iid, new_date_str)  new_date_str en formato YYYY-MM-DD
    """

    def __init__(self, parent, txn_row: dict, on_save):
        super().__init__(parent)
        self.title("Corregir fecha")
        self.resizable(False, False)
        self.configure(bg=_CARD_BG)
        self.grab_set()

        self._txn_row = txn_row
        self._on_save = on_save

        tk.Label(self, text="Transacción:", font=_FONT_LABEL, bg=_CARD_BG, fg=_NEUTRAL).pack(
            anchor="w", padx=14, pady=(12, 0)
        )
        tk.Label(self, text=txn_row.get("description", "")[:60], font=_FONT_HEADER, bg=_CARD_BG, fg=_WHITE).pack(
            anchor="w", padx=14, pady=(0, 8)
        )

        tk.Frame(self, bg=_NEUTRAL, height=1).pack(fill=tk.X, padx=14, pady=(0, 8))

        tk.Label(self, text="Fecha actual:", font=_FONT_LABEL, bg=_CARD_BG, fg=_NEUTRAL).pack(anchor="w", padx=14)
        tk.Label(self, text=str(txn_row.get("date", "")), font=_FONT_HEADER, bg=_CARD_BG, fg=_GOLD).pack(
            anchor="w", padx=14, pady=(0, 10)
        )

        tk.Label(self, text="Nueva fecha (YYYY-MM-DD):", font=_FONT_LABEL, bg=_CARD_BG, fg=_NEUTRAL).pack(
            anchor="w", padx=14
        )
        self._var_date = tk.StringVar(value=str(txn_row.get("date", "")))
        tk.Entry(
            self,
            textvariable=self._var_date,
            font=_FONT_HEADER,
            bg="#0D0D1A",
            fg=_WHITE,
            insertbackground=_WHITE,
            relief=tk.FLAT,
            width=16,
        ).pack(padx=14, pady=(4, 12))

        self._lbl_error = tk.Label(self, text="", font=_FONT_SUB, bg=_CARD_BG, fg=_NEGATIVE)
        self._lbl_error.pack(anchor="w", padx=14)

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

    def _center(self, parent):
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - self.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{px}+{py}")

    def _save(self):
        date_str = self._var_date.get().strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            self._lbl_error.config(text="Formato inválido — usa YYYY-MM-DD")
            return
        self._on_save(self._txn_row["txn_id"], self._txn_row.get("_iid"), date_str)
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Panel principal
# ─────────────────────────────────────────────────────────────────────────────


class _CategoryManagerPopup(tk.Toplevel):
    """
    Popup para agregar o eliminar categorías de fin_categories.
    Muestra lista con botón – por fila y campo + para agregar nueva.
    """

    _TYPES = ["expense", "income", "transfer"]

    def __init__(self, parent, categories: list[tuple], db: "FinanceScreen", on_change):
        super().__init__(parent)
        self.title("Administrar categorías")
        self.resizable(False, True)
        self.configure(bg=_CARD_BG)
        self.grab_set()
        self._db = db
        self._on_change = on_change
        self._categories = list(categories)

        # ── lista existente con scrollbar ─────────────────────────────────
        tk.Label(self, text="Categorías existentes", font=_FONT_HEADER, bg=_CARD_BG, fg=_ACCENT).pack(
            anchor="w", padx=14, pady=(12, 4)
        )

        list_container = tk.Frame(self, bg=_CARD_BG)
        list_container.pack(fill=tk.BOTH, expand=True, padx=14)

        scrollbar = tk.Scrollbar(list_container, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        canvas = tk.Canvas(list_container, bg=_CARD_BG, highlightthickness=0, yscrollcommand=scrollbar.set, height=300)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=canvas.yview)

        self._list_frame = tk.Frame(canvas, bg=_CARD_BG)
        canvas.create_window((0, 0), window=self._list_frame, anchor="nw")

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        self._list_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<MouseWheel>", _on_mousewheel)
        self._list_frame.bind("<MouseWheel>", _on_mousewheel)

        self._render_list()

        tk.Frame(self, bg=_NEUTRAL, height=1).pack(fill=tk.X, padx=14, pady=10)

        # ── agregar nueva ──────────────────────────────────────────────────
        tk.Label(self, text="Nueva categoría", font=_FONT_HEADER, bg=_CARD_BG, fg=_ACCENT).pack(
            anchor="w", padx=14, pady=(0, 4)
        )

        add_row = tk.Frame(self, bg=_CARD_BG)
        add_row.pack(fill=tk.X, padx=14, pady=(0, 6))

        self._var_name = tk.StringVar()
        tk.Entry(
            add_row,
            textvariable=self._var_name,
            font=_FONT_LABEL,
            bg="#2A2A3E",
            fg=_WHITE,
            insertbackground=_WHITE,
            relief=tk.FLAT,
            width=22,
        ).pack(side=tk.LEFT, ipady=4, padx=(0, 6))

        self._var_type = tk.StringVar(value="expense")
        ttk.Combobox(add_row, textvariable=self._var_type, values=self._TYPES, state="readonly", width=10).pack(
            side=tk.LEFT, padx=(0, 6)
        )

        tk.Button(
            add_row,
            text="+",
            font=_FONT_HEADER,
            bg=_POSITIVE,
            fg=_WHITE,
            relief=tk.FLAT,
            padx=10,
            cursor="hand2",
            command=self._add,
        ).pack(side=tk.LEFT)

        self._lbl_msg = tk.Label(self, text="", font=_FONT_SUB, bg=_CARD_BG, fg=_NEUTRAL)
        self._lbl_msg.pack(padx=14, pady=(0, 10))

    def _render_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()
        for cat_id, name, cat_type in sorted(self._categories, key=lambda x: x[1]):
            row = tk.Frame(self._list_frame, bg=_CARD_BG)
            row.pack(fill=tk.X, pady=1)
            type_color = {"income": _POSITIVE, "expense": _NEGATIVE, "transfer": _GOLD}.get(cat_type, _NEUTRAL)
            tk.Label(row, text=f"[{cat_type}]", font=_FONT_SUB, bg=_CARD_BG, fg=type_color, width=10, anchor="w").pack(
                side=tk.LEFT
            )
            tk.Label(row, text=name, font=_FONT_LABEL, bg=_CARD_BG, fg=_WHITE, anchor="w", width=26).pack(side=tk.LEFT)
            tk.Button(
                row,
                text="−",
                font=_FONT_LABEL,
                bg=_NEGATIVE,
                fg=_WHITE,
                relief=tk.FLAT,
                padx=6,
                cursor="hand2",
                command=lambda cid=cat_id, cname=name: self._delete(cid, cname),
            ).pack(side=tk.RIGHT)

    def _add(self):
        name = self._var_name.get().strip()
        cat_type = self._var_type.get()
        ok, msg = self._db.add_category(name, cat_type)
        if ok:
            cats = self._db.get_categories()
            self._categories = list(cats)
            self._render_list()
            self._var_name.set("")
            self._on_change()
        self._lbl_msg.config(text=msg, fg=_POSITIVE if ok else _NEGATIVE)

    def _delete(self, cat_id: int, name: str):
        ok, msg = self._db.delete_category(cat_id)
        if ok:
            self._categories = [(cid, n, ct) for cid, n, ct in self._categories if cid != cat_id]
            self._render_list()
            self._on_change()
        self._lbl_msg.config(text=msg, fg=_POSITIVE if ok else _NEGATIVE)


class _EvolucionChart(tk.Frame):
    """Gráfico de evolución anual: Ingresos / Gastos / Invertido (12 meses)."""

    def __init__(self, parent, bgcolor):
        super().__init__(parent, bg=bgcolor)
        self._fig = Figure(figsize=(4.2, 3.2), dpi=80, facecolor=_BLACK)
        self._fig.subplots_adjust(left=0.13, right=0.97, top=0.88, bottom=0.10)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def load(self, rows: list[dict]):
        ax = self._ax
        ax.clear()
        ax.set_facecolor("#111111")
        ax.set_title("Evolución anual  (U$)", fontsize=8, color=_WHITE, pad=4, loc="left")
        ax.spines[:].set_color("#333333")
        ax.tick_params(colors=_NEUTRAL, labelsize=7)

        if not rows:
            ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", color=_NEUTRAL, transform=ax.transAxes, fontsize=8)
            self._canvas.draw()
            return

        xs = list(range(len(rows)))
        labels = [r["label"] for r in rows]
        ingresos = [r["ingresos"] for r in rows]
        gastos = [r["gastos"] for r in rows]
        invertido = [r["invertido"] for r in rows]

        ax.plot(xs, ingresos, color=_POSITIVE, marker="o", markersize=3, linewidth=1.5, label="Ingresos")
        ax.plot(xs, gastos, color=_NEGATIVE, marker="o", markersize=3, linewidth=1.5, label="Gastos")
        ax.plot(xs, invertido, color=_GOLD, marker="o", markersize=3, linewidth=1.2, linestyle="--", label="Invertido")

        for i, r in enumerate(rows):
            if r["en_curso"]:
                ax.axvspan(i - 0.4, i + 0.4, alpha=0.35, color=_NEUTRAL, hatch="///", fill=False)
                ax.text(
                    i,
                    0.97,
                    "en curso",
                    transform=ax.get_xaxis_transform(),
                    ha="center",
                    va="top",
                    color=_NEUTRAL,
                    fontsize=6,
                )
            elif r["gastos"] > r["ingresos"]:
                ax.axvspan(i - 0.4, i + 0.4, alpha=0.12, color=_NEGATIVE)

        ax.set_xticks(xs)
        ax.set_xticklabels(labels, fontsize=7, color=_WHITE)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.legend(
            fontsize=6,
            facecolor="#111111",
            labelcolor=_WHITE,
            framealpha=0.4,
            loc="upper left",
            handlelength=1.2,
            borderpad=0.4,
            labelspacing=0.3,
        )
        self._canvas.draw()


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
        self._sel_month, self._sel_year = self._db.get_last_loaded_period()

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

        # ── chips de banco/cuenta — canvas scrollable horizontal con flechas ──
        chip_row = tk.Frame(self, bg=self.bgcolor)
        chip_row.pack(fill=tk.X, padx=10, pady=(2, 4))

        def _scroll_left():
            chip_canvas.xview_scroll(-3, "units")

        def _scroll_right():
            chip_canvas.xview_scroll(3, "units")

        tk.Button(
            chip_row,
            text="◀",
            font=("Segoe UI", 7),
            bg=self.bgcolor,
            fg=_NEUTRAL,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=_scroll_left,
        ).pack(side=tk.LEFT)

        chip_canvas = tk.Canvas(chip_row, bg=self.bgcolor, height=26, highlightthickness=0)
        chip_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(
            chip_row,
            text="▶",
            font=("Segoe UI", 7),
            bg=self.bgcolor,
            fg=_NEUTRAL,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=_scroll_right,
        ).pack(side=tk.LEFT)

        self._chip_frame = tk.Frame(chip_canvas, bg=self.bgcolor)
        chip_canvas.create_window((0, 0), window=self._chip_frame, anchor="nw")

        def _on_chips_resize(e):
            chip_canvas.configure(scrollregion=chip_canvas.bbox("all"))

        def _on_chip_scroll(e):
            chip_canvas.xview_scroll(int(-1 * (e.delta / 120)), "units")

        self._chip_frame.bind("<Configure>", _on_chips_resize)
        chip_canvas.bind("<MouseWheel>", _on_chip_scroll)
        self._chip_frame.bind("<MouseWheel>", _on_chip_scroll)

        # ── separador ────────────────────────────────────────────────────────
        tk.Frame(self, bg=_NEUTRAL, height=1).pack(fill=tk.X, padx=10, pady=2)

        # ── fila KPI ─────────────────────────────────────────────────────────
        kpi_row = tk.Frame(self, bg=self.bgcolor)
        kpi_row.pack(fill=tk.X, padx=10, pady=6)

        self._kpi_income = _KpiCard(kpi_row, "Ingresos", value_color=_POSITIVE)
        self._kpi_expense = _KpiCard(kpi_row, "Gastos", value_color=_NEGATIVE)
        self._kpi_invest = _KpiCard(kpi_row, "Invertido", value_color=_GOLD)
        self._kpi_balance = _KpiCard(kpi_row, "Balance")

        for card in (self._kpi_income, self._kpi_expense, self._kpi_invest, self._kpi_balance):
            card.pack(side=tk.LEFT, padx=6, ipadx=8, ipady=4, fill=tk.X, expand=True)

        # ── separador ────────────────────────────────────────────────────────
        tk.Frame(self, bg=_NEUTRAL, height=1).pack(fill=tk.X, padx=10, pady=2)

        # ── body ─────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=self.bgcolor)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        # panel izquierdo — categorías + gráficos
        left = tk.Frame(body, bg=self.bgcolor)
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))

        cat_hdr = tk.Frame(left, bg=self.bgcolor)
        cat_hdr.pack(fill=tk.X, pady=(0, 4))
        tk.Button(
            cat_hdr,
            text="+",
            font=_FONT_CHIP,
            bg=_POSITIVE,
            fg=_WHITE,
            relief=tk.FLAT,
            padx=6,
            pady=1,
            cursor="hand2",
            command=self._open_category_manager,
        ).pack(side=tk.RIGHT, padx=(4, 0))
        tk.Button(
            cat_hdr,
            text="−",
            font=_FONT_CHIP,
            bg=_NEGATIVE,
            fg=_WHITE,
            relief=tk.FLAT,
            padx=6,
            pady=1,
            cursor="hand2",
            command=self._open_category_manager,
        ).pack(side=tk.RIGHT)

        style = ttk.Style()
        style.configure("Cat.TNotebook", background=self.bgcolor, borderwidth=0)
        style.configure("Cat.TNotebook.Tab", background="#1A1A2E", foreground=_NEUTRAL, font=_FONT_CHIP, padding=(8, 3))
        style.map("Cat.TNotebook.Tab", background=[("selected", "#2A2A3E")], foreground=[("selected", _WHITE)])

        cat_wrap = tk.Frame(left, bg=self.bgcolor, height=280)
        cat_wrap.pack(fill=tk.X)
        cat_wrap.pack_propagate(False)

        cat_nb = ttk.Notebook(cat_wrap, style="Cat.TNotebook")
        cat_nb.pack(fill=tk.BOTH, expand=True)

        self._cat_nb = cat_nb

        tab_expense = tk.Frame(cat_nb, bg=self.bgcolor)
        tab_income = tk.Frame(cat_nb, bg=self.bgcolor)
        tab_invest = tk.Frame(cat_nb, bg=self.bgcolor)
        tab_transfer = tk.Frame(cat_nb, bg=self.bgcolor)
        cat_nb.add(tab_expense, text="Gastos")
        cat_nb.add(tab_income, text="Ingresos")
        cat_nb.add(tab_invest, text="Inversiones")
        cat_nb.add(tab_transfer, text="Transferencias")

        self._cat_bar = _CategoryBar(tab_expense, self.bgcolor, on_select=self._on_category_select, bar_color=_NEGATIVE)
        self._cat_bar.pack(fill=tk.BOTH, expand=True, pady=4)

        self._cat_bar_income = _CategoryBar(
            tab_income, self.bgcolor, on_select=self._on_category_select, bar_color=_POSITIVE
        )
        self._cat_bar_income.pack(fill=tk.BOTH, expand=True, pady=4)

        self._cat_bar_invest = _CategoryBar(
            tab_invest, self.bgcolor, on_select=self._on_category_select, bar_color=_GOLD
        )
        self._cat_bar_invest.pack(fill=tk.BOTH, expand=True, pady=4)

        self._cat_bar_transfer = _CategoryBar(
            tab_transfer, self.bgcolor, on_select=self._on_category_select, bar_color=_NEUTRAL
        )
        self._cat_bar_transfer.pack(fill=tk.BOTH, expand=True, pady=4)

        tk.Frame(left, bg=_NEUTRAL, height=1).pack(fill=tk.X, pady=4)

        self._evol_chart = _EvolucionChart(left, self.bgcolor)
        self._evol_chart.pack(fill=tk.BOTH, expand=True)

        tk.Frame(body, bg=_NEUTRAL, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        # panel derecho — transacciones
        right = tk.Frame(body, bg=self.bgcolor)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        hdr = tk.Frame(right, bg=self.bgcolor)
        hdr.pack(fill=tk.X)

        # El panel de detalle tiene tres vistas: las transacciones del período, la cobertura de carga y lo
        # comprometido hacia adelante. Ninguna de las dos últimas es una categoría ni depende del período o de los
        # chips —la cobertura mira el estado de carga y el comprometido mira el futuro—, por eso no viven en el
        # notebook de la izquierda.
        self._lbl_txn_section = _SectionLabel(hdr, "Últimas transacciones", cursor="hand2")
        self._lbl_txn_section.pack(side=tk.LEFT, pady=(0, 6))
        self._lbl_txn_section.bind("<Button-1>", lambda _e: self._show_transactions())

        self._lbl_cover_section = _SectionLabel(hdr, "Cobertura", cursor="hand2")
        self._lbl_cover_section.pack(side=tk.LEFT, padx=(6, 0), pady=(0, 6))
        self._lbl_cover_section.bind("<Button-1>", lambda _e: self._show_coverage())

        self._lbl_commit_section = _SectionLabel(hdr, "Comprometido", cursor="hand2")
        self._lbl_commit_section.pack(side=tk.LEFT, padx=(6, 0), pady=(0, 6))
        self._lbl_commit_section.bind("<Button-1>", lambda _e: self._show_commitments())

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

        self._txn_table = _TxnTable(
            right,
            self.bgcolor,
            on_category_edit=self._on_category_edit,
            on_date_edit=self._on_date_edit,
        )
        self._cover_table = _CoverageTable(right, self.bgcolor)
        self._commit_table = _CommitmentsTable(right, self.bgcolor)

        self._detail = "txn"  # txn | cover | commit — qué vista ocupa el panel derecho
        self._cover_pending = 0
        self._show_transactions()

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

            for _label, acct_id, bname, aname, short_name in accts:
                short = short_name or aname.replace(bname, "").strip(" -—")
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

    def _open_category_manager(self):
        """Abre popup de administración de categorías (+/-)."""
        _CategoryManagerPopup(
            self,
            self._categories,
            db=self._db,
            on_change=self._reload_categories,
        )

    def _reload_categories(self):
        """Recarga categorías desde BD y refresca la barra."""
        self._categories = self._db.get_categories()
        date_from, date_to = self._period()
        account_ids = self._selected_account_ids()
        self._cat_bar.load(self._db.get_categories_expense(date_from, date_to, account_ids))
        self._cat_bar_income.load(self._db.get_categories_income(date_from, date_to, account_ids))
        self._cat_bar_invest.load(self._db.get_categories_investment(date_from, date_to, account_ids))
        self._cat_bar_transfer.load(self._db.get_categories_transfer(date_from, date_to, account_ids))

    def _on_category_select(self, cat_name: str | None):
        self._show_transactions()
        self._txn_table.set_category_filter(cat_name)
        if cat_name:
            self._lbl_txn_section.config(text=f"  {cat_name}  ")
            self._btn_clear_cat.pack(side=tk.LEFT, padx=(6, 0), pady=(0, 6))
        else:
            self._clear_category_filter()
        self._update_status()

    def _clear_category_filter(self):
        self._txn_table.set_category_filter(None)
        for bar in (self._cat_bar, self._cat_bar_income, self._cat_bar_invest, self._cat_bar_transfer):
            bar.clear_filter()
        self._lbl_txn_section.config(text="  Últimas transacciones  ")
        self._btn_clear_cat.pack_forget()
        self._update_status()

    def _mark_section(self, activa):
        """Enciende la etiqueta de la vista activa y apaga las otras. Cobertura conserva su rojo si hay pendientes."""
        for lbl in (self._lbl_txn_section, self._lbl_cover_section, self._lbl_commit_section):
            if lbl is activa:
                lbl.config(bg=_BLACK, fg=_WHITE)
            elif lbl is self._lbl_cover_section:
                lbl.config(bg="#2A2A3E", fg=_NEGATIVE if self._cover_pending else _NEUTRAL)
            else:
                lbl.config(bg="#2A2A3E", fg=_NEUTRAL)

    def _show_transactions(self):
        """Vuelve al detalle del período. El filtro de categoría se restaura si estaba puesto."""
        self._detail = "txn"
        self._cover_table.pack_forget()
        self._commit_table.pack_forget()
        self._txn_table.pack(fill=tk.BOTH, expand=True)
        self._mark_section(self._lbl_txn_section)
        if self._txn_table.category_filter:
            self._btn_clear_cat.pack(side=tk.LEFT, padx=(6, 0), pady=(0, 6))
        self._update_status()

    def _show_coverage(self):
        """La cobertura ocupa el panel de detalle: estado de carga por cuenta, sin filtro de categoría."""
        self._detail = "cover"
        self._txn_table.pack_forget()
        self._commit_table.pack_forget()
        self._btn_clear_cat.pack_forget()
        self._cover_table.pack(fill=tk.BOTH, expand=True)
        self._mark_section(self._lbl_cover_section)
        self._update_status()

    def _show_commitments(self):
        """Lo comprometido hacia adelante ocupa el panel: cuotas que todavía no llegaron, por mes."""
        self._detail = "commit"
        self._txn_table.pack_forget()
        self._cover_table.pack_forget()
        self._btn_clear_cat.pack_forget()
        self._commit_table.pack(fill=tk.BOTH, expand=True)
        self._mark_section(self._lbl_commit_section)
        self._update_status()

    def _update_status(self):
        if self._detail == "cover":
            total = len(self._cover_table.tree.get_children())
            pend = self._cover_pending
            texto = f"{total} cuentas — {pend} esperando extracto" if pend else f"{total} cuentas — todas al día"
            self._lbl_status.config(text=texto, fg=_NEGATIVE if pend else _POSITIVE)
            return
        if self._detail == "commit":
            totals = self._commit_table.totals
            if not totals:
                self._lbl_status.config(text="sin cuotas pendientes", fg=_POSITIVE)
                return
            prox = min(totals)
            self._lbl_status.config(
                text=f"{prox}: {_fmt_usdt(totals[prox])} comprometidos — {len(totals)} meses por delante", fg=_GOLD
            )
            return
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

    # ── lógica edición de fecha ───────────────────────────────────────────────

    def _on_date_edit(self, txn_id: int, iid: str, txn_row: dict):
        """Abre popup para corregir la fecha de txn_id."""
        _DateEditPopup(self, txn_row, on_save=self._save_date)

    def _save_date(self, txn_id: int, iid: str, new_date: str):
        """Persiste el cambio de fecha en la BD y actualiza la fila visible."""
        ok = self._db.update_txn_date(txn_id, new_date)
        if ok and iid:
            self._txn_table.update_row_date(iid, new_date)
            self._update_status()

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
                bal_color = _POSITIVE if balance >= 0 else _NEGATIVE
                pct_gastos = (kpi["gastos"] / kpi["ingresos"] * 100) if kpi["ingresos"] else 0
                pct_ahorro = (balance / kpi["ingresos"] * 100) if kpi["ingresos"] else 0

                self._kpi_income.update_value(
                    _fmt_usdt(kpi["ingresos"]),
                    sub=f"ARS {kpi['ingresos_ars']:,.0f}".replace(",", ".") if kpi["ingresos_ars"] else "",
                )
                self._kpi_expense.update_value(
                    _fmt_usdt(kpi["gastos"]),
                    sub=f"ARS {kpi['gastos_ars']:,.0f}".replace(",", ".") if kpi["gastos_ars"] else "",
                    sub2=f"{pct_gastos:.1f}% de ingresos",
                )
                self._kpi_invest.update_value(
                    _fmt_usdt(kpi["invertido"]),
                    sub=f"ARS {kpi['invertido_ars']:,.0f}".replace(",", ".") if kpi["invertido_ars"] else "",
                    sub2=f"Suscr. {_fmt_usdt(kpi['suscripto'])} · Resc. {_fmt_usdt(kpi['rescatado'])}",
                )
                self._kpi_balance.update_value(
                    _fmt_usdt(balance), sub=f"Ahorro {pct_ahorro:.1f}% de ingresos", color=bal_color
                )
            else:
                for card in (self._kpi_income, self._kpi_expense, self._kpi_invest, self._kpi_balance):
                    card.update_value("—", sub="Sin datos")

            # reset filtro de categoría al refrescar
            self._clear_category_filter()

            income_total = kpi.get("ingresos", 0) if kpi else 0
            self._cat_bar.load(
                self._db.get_categories_expense(date_from, date_to, account_ids), income_total=income_total
            )
            self._cat_bar_income.load(self._db.get_categories_income(date_from, date_to, account_ids))
            self._cat_bar_invest.load(self._db.get_categories_investment(date_from, date_to, account_ids))
            self._cat_bar_transfer.load(self._db.get_categories_transfer(date_from, date_to, account_ids))

            self._evol_chart.load(self._db.get_monthly_evolution(12, account_ids))

            # la cobertura no depende del período ni de los chips: es el estado de carga de todas las cuentas
            cobertura = self._db.get_coverage()
            self._cover_table.load(cobertura)
            self._cover_pending = sum(1 for c in cobertura if c["status"] in ("atraso", "sin_datos"))
            self._lbl_cover_section.config(
                text=f"  Cobertura ({self._cover_pending})  " if self._cover_pending else "  Cobertura  "
            )
            if self._detail != "cover":
                self._lbl_cover_section.config(fg=_NEGATIVE if self._cover_pending else _NEUTRAL)

            # lo comprometido tampoco depende del período: son las cuotas que caen de acá en adelante
            self._commit_table.load(self._db.get_installments_pending(6, account_ids))

            txns = self._db.get_transactions(date_from, date_to, account_ids)
            self._txn_table.load(txns)
            self._update_status()

        except Exception as e:
            _logger.error(f"FinancePanel.refresh: {e}")
            self._lbl_status.config(text=f"Error: {e}", fg=_NEGATIVE)

    def inicializar(self):
        """Llamado desde DashMain tras instanciar — carga cuentas, categorías, chips y refresca."""
        self._accounts = self._db.get_accounts()
        self._categories = self._db.get_categories()
        self._build_chips()
        self.refresh()


# ─────────────────────────────────────────────────────────────────────────────
# Parsers de extractos bancarios — dominio Finance
# ─────────────────────────────────────────────────────────────────────────────


EXTRACTOS_DIR = os.path.join(
    os.environ.get("APPOO_TMP") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp"), "extractos"
)
PROCESADOS_DIR = os.path.join(EXTRACTOS_DIR, "procesados")
DESCONOCIDOS_DIR = os.path.join(EXTRACTOS_DIR, "desconocidos")

# Reglas de detección automática de banco/adaptador por contenido del PDF.
# Orden importa — primera coincidencia gana.
# (keyword_en_pdf, adapter_key, account_ref)  account_ref=None → multi-sección

DETECTION_RULES = [
    ("CITIBANK, N. A.", "citibank_us", None),
    ("1067995586", "santander_tc_resumen", "TC-0925"),
    ("1068053384", "santander_tc_resumen", "TC-9541"),
    ("Santander", "santander", None),
    ("0720175888000037071990", "santander", None),
    ("196-009369/5", "bbva_ahorro", "196-009369/5"),
    ("196-004699/4", "bbva_cuenta", "196-004699/4"),
    ("1269461197", "bbva_tc", "TC-1269461197"),
    ("1175839390", "bbva_tc", "TC-1175839390"),
    ("0102****9412", "bdv_ves", "BDV-9412"),
    ("01340474784741030611", "banesco_ves", "BANESCO-0611"),
    ("Historial de órdenes C2C", "binance_c2c", "BINANCE-USDT"),
]

MESES_ES = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "set": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}

RE_IMPORTE_AR = re.compile(r"^\$?-?\d{1,3}(?:\.\d{3})*,\d{2}$")
RE_MES_CUOTA = re.compile(r"^([^\W\d_]+)(?:/(\d{2}))?$")
RE_ANIO = re.compile(r"^\d{4}$")
# cuota de un plan de financiación dentro de la descripción: 'VISA PLAN V 2-06 (TNA 79,00)'. La cuota no lleva cero
# adelante, así una fecha '07-12' no pasa por cuota
RE_CUOTA_PLAN = re.compile(r"(?<![\d/.-])([1-9]\d?)-(\d{2})(?![\d/.-])")

# un cierre a más de 10 días del último movimiento del resumen es el del mes siguiente, no el de este: medido sobre
# los 36 resúmenes con cuotas, los que traen su ciclo caen entre 0 y 5 días y el siguiente salta a 28
CIERRE_MAX_DIAS = 10

_INSERT_TXN_SQL = """
    INSERT IGNORE INTO fin_transactions
        (date, type, amount, currency, amount_usdt, category_id, account_id,
         description, raw_description, raw_description_detail,
         comprobante, import_id, classified_by,
         installment_current, installment_total)
    VALUES
        (%(date)s, %(type)s, %(amount)s, %(currency)s, %(amount_usdt)s,
         %(category_id)s, %(account_id)s, %(description)s, %(raw_description)s,
         %(raw_description_detail)s, %(comprobante)s, %(import_id)s,
         %(classified_by)s, %(installment_current)s, %(installment_total)s)
"""

_NEAR_DUP_SQL = """
    SELECT id FROM fin_transactions
    WHERE account_id = %s AND date = %s AND raw_description = %s
      AND currency = %s AND ABS(amount - %s) < 2.0
      AND (installment_current <=> %s)
    LIMIT 1
"""


def _is_near_duplicate(cursor, txn: dict) -> bool:
    """True si ya existe una transacción con mismo cuenta/fecha/descripción, monto ±$2
    y mismo número de cuota (NULL-safe). Evita falsos positivos con cuotas distintas."""
    cursor.execute(
        _NEAR_DUP_SQL,
        (
            txn["account_id"],
            txn["date"],
            txn["raw_description"],
            txn.get("currency", "ARS"),
            txn["amount"],
            txn.get("installment_current"),
        ),
    )
    return cursor.fetchone() is not None


def _dedup_raw_descriptions(txns: list[dict]) -> list[dict]:
    """Numera raw_description cuando el mismo (account_id, date, amount, raw_description)
    aparece más de una vez en el batch. Ej: dos 'Pago de tarjeta de credito' $150k el mismo día
    quedan como '...' y '... (2)' para que el unique index no rechace el segundo."""
    seen: dict[tuple, int] = {}
    for txn in txns:
        key = (txn["account_id"], txn["date"], txn["amount"], txn["raw_description"])
        count = seen.get(key, 0) + 1
        seen[key] = count
        if count > 1:
            txn["raw_description"] = f"{txn['raw_description']} ({count})"
    return txns


def _get_tasa_cursor(currency: str, txn_date, cursor) -> float | None:
    """Tasa fiat→USDT más cercana a txn_date usando cursor existente."""
    if currency == "USD":
        return 1.0
    categoria = {"ARS": "ARS", "VES": "VES"}.get(currency)
    if not categoria:
        return None
    cursor.execute(
        "SELECT preciotrans FROM booktrading "
        "WHERE categoria=%s AND simbolo='USDT' AND preciotrans > 0 "
        "ORDER BY ABS(TIMESTAMPDIFF(SECOND, fechahora, %s)) LIMIT 1",
        (categoria, txn_date),
    )
    row = cursor.fetchone()
    return float(row[0]) if row else None


def _calc_usdt(amount: Decimal, currency: str, txn_date, cursor) -> Decimal | None:
    """Calcula amount_usdt usando la tasa más cercana a txn_date."""
    tasa = _get_tasa_cursor(currency, txn_date, cursor)
    if tasa is None or tasa == 0:
        return None
    if currency == "USD":
        return amount
    return (amount / Decimal(str(tasa))).quantize(Decimal("0.00000001"))


def parse_amount_us(text: str) -> Decimal | None:
    """Convierte número formato US '1,234.56' → Decimal('1234.56')."""
    if not text:
        return None
    text = text.strip().replace(" ", "").replace(",", "")
    if not text or text in ("-", "—"):
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_amount_ar(text: str) -> Decimal | None:
    """Convierte número formato argentino '1.234,56' → Decimal('1234.56')."""
    if not text:
        return None
    text = text.strip().replace(" ", "")
    if not text or text in ("-", "—"):
        return None
    text = text.replace(".", "").replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def parse_date_bbva_tc(text: str) -> date | None:
    """BBVA tarjetas: 'DD-Mon-YY'  ej: '15-Mar-25' → date(2025, 3, 15)"""
    text = text.strip()
    m = re.match(r"(\d{1,2})-([A-Za-z]{3})-(\d{2})$", text)
    if m:
        day, mes, yy = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        month = MESES_ES.get(mes)
        if month:
            return date(2000 + yy, month, day)
    return None


def parse_plan_installment(desc: str) -> tuple[int | None, int | None]:
    """Cuota de un plan de financiación ('CUOTIFICACION 3-06 (TNA 79,00)' → (3, 6)). BBVA y Santander la escriben
    así, pegada a la descripción y fuera de su formato de cuota: sin reconocerla el plan entero caía en el mes del
    alta en vez de repartirse en los resúmenes que lo cobran."""
    m = RE_CUOTA_PLAN.search(desc)
    if m and int(m.group(1)) <= int(m.group(2)):
        return int(m.group(1)), int(m.group(2))
    return None, None


def parse_installments_due(lines: list[list[dict]], max_gap: float = 25.0) -> list[tuple[date, Decimal]]:
    """Cuotas a vencer de un resumen de tarjeta: fila de meses ('Agosto 2026' o 'SETIEMBRE/26') y el importe
    de cada mes debajo, a la misma x."""
    for idx, line in enumerate(lines):
        months = []
        for pos, w in enumerate(line):
            m = RE_MES_CUOTA.match(w["text"])
            month = MESES_ES.get(m.group(1)[:3].lower()) if m else None
            if not month:
                continue
            if m.group(2):
                months.append((w, date(2000 + int(m.group(2)), month, 1)))
            elif pos + 1 < len(line) and RE_ANIO.match(line[pos + 1]["text"]):
                months.append((w, date(int(line[pos + 1]["text"]), month, 1)))
        if len(months) < 3:
            continue
        top = months[0][0]["top"]
        due = {}
        for below in lines[idx + 1 :]:
            for w in below:
                if 0 < w["top"] - top <= max_gap and RE_IMPORTE_AR.match(w["text"]):
                    nearest = min(months, key=lambda mw: abs(mw[0]["x0"] - w["x0"]))[1]
                    due.setdefault(nearest, parse_amount_ar(w["text"].replace("$", "")))
        return sorted(due.items())
    return []


def _save_card_cycle(cursor, account_id: int, import_id: int, cycle: dict | None) -> int:
    """Graba cierre, vencimiento y cuotas a vencer. Un ciclo ya cargado no se pisa. Devuelve las filas insertadas."""
    if not cycle:
        return 0
    cursor.execute(
        "INSERT IGNORE INTO fin_card_cycles "
        "(account_id,import_id,closing_date,due_date,next_closing_date,next_due_date) VALUES (%s,%s,%s,%s,%s,%s)",
        (account_id, import_id, cycle["closing"], cycle["due"], cycle.get("next_closing"), cycle.get("next_due")),
    )
    if cursor.rowcount != 1:
        _logger.info(f"  Ciclo con cierre {cycle['closing']} ya cargado — omitido")
        return 0
    cycle_id = cursor.lastrowid
    for month, amount in cycle["installments"]:
        cursor.execute(
            "INSERT INTO fin_card_installments_due (cycle_id,month,amount) VALUES (%s,%s,%s)",
            (cycle_id, month, amount),
        )
    _logger.info(f"  Ciclo con cierre {cycle['closing']}: {len(cycle['installments'])} meses de cuotas a vencer")
    return 1 + len(cycle["installments"])


def _set_billing_dates(cursor, import_id: int, closing: date | None = None) -> int:
    """Sella en las cuotas de este resumen el cierre que las cobra: la cuota se paga en el resumen donde aparece,
    no en el mes de la compra, así que sin esto un plan entero cae en un solo mes. Sin ciclo parseado busca el cierre
    real de la cuenta (lo trae el resumen de tarjeta, que es otro PDF) y si no lo hay cae al último movimiento del
    resumen entero — no de la sección: las 5 secciones de un PDF de Santander son 5 imports con el mismo file_hash y
    una sección con pocas filas termina semanas antes del cierre."""
    if closing is None:
        cursor.execute(
            "SELECT MAX(t.date) FROM fin_transactions t JOIN fin_statement_imports i ON i.id = t.import_id "
            "WHERE i.file_hash = (SELECT file_hash FROM fin_statement_imports WHERE id = %s)",
            (import_id,),
        )
        row = cursor.fetchone()
        closing = row[0] if row else None
        if closing is not None:
            cursor.execute(
                "SELECT MIN(cy.closing_date) FROM fin_card_cycles cy "
                "JOIN fin_statement_imports i ON i.account_id = cy.account_id "
                "WHERE i.id = %s AND cy.closing_date BETWEEN %s AND %s + INTERVAL %s DAY",
                (import_id, closing, closing, CIERRE_MAX_DIAS),
            )
            row = cursor.fetchone()
            if row and row[0]:
                closing = row[0]
    if closing is None:
        return 0
    cursor.execute(
        "UPDATE fin_transactions SET billing_date = %s WHERE import_id = %s AND installment_current IS NOT NULL",
        (closing, import_id),
    )
    if cursor.rowcount:
        _logger.info(f"  {cursor.rowcount} cuotas del resumen quedan cobradas el {closing}")
    return cursor.rowcount


def apply_rules(desc: str, cursor=None, detail: str = "") -> tuple[int | None, str | None]:
    """Busca la primera regla activa coincidente para desc (y opcionalmente detail).
    Devuelve (category_id, 'rule') o (None, None)."""
    if cursor is None:
        return None, None
    cursor.execute(
        "SELECT id, pattern, match_type, category_id " "FROM fin_import_rules WHERE is_active=1 ORDER BY priority, id"
    )
    rules = cursor.fetchall()
    combined = (desc + " " + detail).strip() if detail else desc
    desc_upper = combined.upper()
    for rule_id, pattern, match_type, cat_id in rules:
        p = pattern.upper()
        matched = False
        if match_type == "exact":
            matched = desc_upper == p
        elif match_type == "contains":
            matched = p in desc_upper
        elif match_type == "startswith":
            matched = desc_upper.startswith(p)
        elif match_type == "regex":
            matched = bool(re.search(pattern, desc, re.IGNORECASE))
        if matched:
            cursor.execute(
                "UPDATE fin_import_rules SET hit_count=hit_count+1, last_hit_at=NOW() WHERE id=%s",
                (rule_id,),
            )
            return cat_id, "rule"
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Adaptador BBVA AR — Tarjetas de crédito (Mastercard / Visa)
# ─────────────────────────────────────────────────────────────────────────────


class BbvaArTarjeta:
    """
    Parsea el PDF de resumen de tarjeta BBVA Argentina (Visa / Mastercard).

    Columnas por X:
        x < 110          → FECHA (DD-Mon-YY)
        110 ≤ x < 370    → DESCRIPCIÓN
        370 ≤ x < 450    → NRO. CUPÓN
        450 ≤ x < 530    → PESOS
        x ≥ 530          → DÓLARES
    """

    SECTION_NAME = "bbva_tc"
    RE_CUOTA = re.compile(r"\bC\.?(\d{1,2})/(\d{1,2})\b", re.IGNORECASE)
    RE_DATE = re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{2}$")

    X_DESC_MIN = 110
    X_CUPON_MIN = 370
    X_PESOS_MIN = 450
    X_DOLARES_MIN = 530

    SKIP_MARKERS = {
        "SALDO ANTERIOR",
        "SALDO ACTUAL",
        "TOTAL CONSUMOS",
        "INTERESES FINANCIACION",
        "DB IVA",
        "PAGO MÍNIMO",
        "TOTAL CONSUMOS DE",
    }
    CYCLE_LABELS = {
        ("CIERRE", "ACTUAL"): "closing",
        ("VENCIMIENTO", "ACTUAL"): "due",
        ("CIERRE", "ANTERIOR"): "prev_closing",
        ("PRÓXIMO", "CIERRE"): "next_closing",
        ("PRÓXIMO", "VENCIMIENTO"): "next_due",
    }

    def __init__(self, pdf_path: str, account_ref: str, dry_run: bool = False):
        self.pdf_path = pdf_path
        self.account_ref = account_ref.strip()
        self.dry_run = dry_run
        self.file_hash = sha256_file(pdf_path)

    def _parse_cuota(self, desc: str) -> tuple[int | None, int | None, str]:
        m = self.RE_CUOTA.search(desc)
        if m:
            cur, tot = int(m.group(1)), int(m.group(2))
            return cur, tot, self.RE_CUOTA.sub("", desc).strip()
        # la cuota del plan queda en la descripción: es lo único que distingue sus filas en la tabla
        cur, tot = parse_plan_installment(desc)
        return cur, tot, desc

    def _is_date(self, text: str) -> bool:
        return bool(self.RE_DATE.match(text.strip()))

    def _words_to_lines(self, words: list[dict], y_tol: float = 3.0) -> list[list[dict]]:
        if not words:
            return []
        lines, current = [], [words[0]]
        for w in words[1:]:
            if abs(w["top"] - current[0]["top"]) <= y_tol:
                current.append(w)
            else:
                lines.append(sorted(current, key=lambda x: x["x0"]))
                current = [w]
        lines.append(sorted(current, key=lambda x: x["x0"]))
        return lines

    def _classify_word(self, w: dict) -> str:
        x = w["x0"]
        if x < self.X_DESC_MIN:
            return "fecha"
        if x < self.X_CUPON_MIN:
            return "desc"
        if x < self.X_PESOS_MIN:
            return "cupon"
        if x < self.X_DOLARES_MIN:
            return "pesos"
        return "dolares"

    def _extract_rows(self) -> list[dict]:
        rows = []
        in_detail = False
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                words = [w for w in page.extract_words(x_tolerance=3, y_tolerance=3) if w["x0"] < 570]
                lines = self._words_to_lines(words)
                for line in lines:
                    text = " ".join(w["text"] for w in line)
                    if "FECHA" in text and "DESCRIPCIÓN" in text:
                        in_detail = True
                        continue
                    if in_detail and any(mk in text.upper() for mk in self.SKIP_MARKERS):
                        in_detail = False
                        continue
                    if not in_detail:
                        continue
                    cols = {"fecha": [], "desc": [], "cupon": [], "pesos": [], "dolares": []}
                    for w in line:
                        cols[self._classify_word(w)].append(w["text"])
                    fecha_str = " ".join(cols["fecha"]).strip()
                    if not self._is_date(fecha_str):
                        continue
                    rows.append(
                        {
                            "fecha_str": fecha_str,
                            "date": parse_date_bbva_tc(fecha_str),
                            "raw_description": " ".join(cols["desc"]).strip(),
                            "comprobante": " ".join(cols["cupon"]).strip() or None,
                            "pesos": " ".join(cols["pesos"]).strip(),
                            "dolares": " ".join(cols["dolares"]).strip(),
                        }
                    )
        return rows

    def _extract_cycle(self) -> dict | None:
        with pdfplumber.open(self.pdf_path) as pdf:
            words = [w for w in pdf.pages[0].extract_words(x_tolerance=3, y_tolerance=3) if w["x0"] < 570]
        lines = self._words_to_lines(words)
        cycle = {}
        for line in lines:
            for first, second in zip(line, line[1:]):
                key = self.CYCLE_LABELS.get((first["text"], second["text"]))
                if not key:
                    continue
                # la fecha va debajo de la etiqueta, alineada a su primera palabra
                fechas = [
                    w["text"]
                    for w in words
                    if 0 < w["top"] - first["top"] <= 20
                    and abs(w["x0"] - first["x0"]) <= 5
                    and self._is_date(w["text"])
                ]
                if fechas:
                    cycle[key] = parse_date_bbva_tc(fechas[0])
        if not cycle.get("closing") or not cycle.get("due"):
            return None
        cycle["installments"] = parse_installments_due(lines)
        return cycle

    def _build_transactions(self, rows: list[dict], account_id: int, import_id: int, cursor) -> list[dict]:
        txns = []
        for r in rows:
            if not r.get("date"):
                _logger.warning(f"  Fecha inválida: {r.get('fecha_str')} — omitida")
                continue
            raw_desc = r["raw_description"].strip()
            inst_cur, inst_tot, desc_clean = self._parse_cuota(raw_desc)
            amount_pesos = parse_amount_ar(r.get("pesos", ""))
            amount_dolares = parse_amount_ar(r.get("dolares", ""))
            if amount_dolares is not None and amount_dolares != 0:
                amount, currency = amount_dolares, "USD"
            elif amount_pesos is not None:
                amount, currency = amount_pesos, "ARS"
            else:
                _logger.warning(f"  Sin monto: {raw_desc[:60]} — omitida")
                continue
            txn_type = "income" if amount < 0 else "expense"
            cat_id, classified_by = apply_rules(raw_desc, cursor)
            txns.append(
                {
                    "date": r["date"],
                    "type": txn_type,
                    "amount": abs(amount),
                    "currency": currency,
                    "amount_usdt": _calc_usdt(abs(amount), currency, r["date"], cursor),
                    "category_id": cat_id,
                    "account_id": account_id,
                    "description": desc_clean,
                    "raw_description": raw_desc,
                    "raw_description_detail": None,
                    "comprobante": r.get("comprobante"),
                    "import_id": import_id,
                    "classified_by": classified_by,
                    "installment_current": inst_cur,
                    "installment_total": inst_tot,
                }
            )
        return txns

    def preview(self) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        raw_rows = self._extract_rows()
        stats["rows_found"] = len(raw_rows)
        _logger.info(f"  Filas encontradas: {len(raw_rows)}")
        for r in raw_rows:
            if not r.get("date"):
                stats["errors"] += 1
                continue
            inst_cur, inst_tot, desc_clean = self._parse_cuota(r["raw_description"])
            amount_pesos = parse_amount_ar(r.get("pesos", ""))
            amount_dolares = parse_amount_ar(r.get("dolares", ""))
            amount = amount_dolares if (amount_dolares is not None and amount_dolares != 0) else amount_pesos
            currency = "USD" if (amount_dolares is not None and amount_dolares != 0) else "ARS"
            if amount is None:
                stats["errors"] += 1
                continue
            txn_type = "income" if amount < 0 else "expense"
            _logger.info(
                f"  {r['date']} | {txn_type:8s} | {currency} {abs(amount):>12.2f} | "
                f"cuota={inst_cur}/{inst_tot} | {desc_clean[:55]}"
            )
            stats["inserted"] += 1
        return stats

    def load(self, conn) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, bank_id FROM fin_accounts WHERE account_ref=%s AND is_active=1",
            (self.account_ref,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Cuenta no encontrada: account_ref='{self.account_ref}'")
        account_id, bank_id = row
        raw_rows = self._extract_rows()
        stats["rows_found"] = len(raw_rows)
        if not raw_rows:
            cursor.close()
            return stats
        cycle = self._extract_cycle()
        cursor.execute(
            "SELECT id, status FROM fin_statement_imports WHERE file_hash=%s AND section=%s",
            (self.file_hash, self.SECTION_NAME),
        )
        imported = cursor.fetchone()
        if imported:
            _logger.warning("  PDF ya importado — omitido")
            # el ciclo sí se graba: los resúmenes cargados antes de existir fin_card_cycles se recuperan re-soltándolos
            _save_card_cycle(cursor, account_id, imported[0], cycle)
            _set_billing_dates(cursor, imported[0], cycle.get("closing") if cycle else None)
            conn.commit()
            cursor.close()
            return stats
        cursor.execute(
            "INSERT INTO fin_statement_imports (account_id,bank_id,filename,file_hash,section,status) "
            "VALUES (%s,%s,%s,%s,%s,'pending')",
            (account_id, bank_id, os.path.basename(self.pdf_path), self.file_hash, self.SECTION_NAME),
        )
        conn.commit()
        import_id = cursor.lastrowid
        txns = _dedup_raw_descriptions(self._build_transactions(raw_rows, account_id, import_id, cursor))
        for txn in txns:
            try:
                if _is_near_duplicate(cursor, txn):
                    stats["skipped"] += 1
                else:
                    cursor.execute(_INSERT_TXN_SQL, txn)
                    stats["inserted" if cursor.rowcount == 1 else "skipped"] += 1
            except Error as e:
                _logger.error(f"  Error: {e} — {txn.get('raw_description','')[:60]}")
                stats["errors"] += 1
        _save_card_cycle(cursor, account_id, import_id, cycle)
        _set_billing_dates(cursor, import_id, cycle.get("closing") if cycle else None)
        cursor.execute(
            "UPDATE fin_statement_imports SET status='processed',row_count=%s,processed_count=%s,skipped_count=%s,"
            "period_from=(SELECT MIN(date) FROM fin_transactions WHERE import_id=%s),"
            "period_to=(SELECT MAX(date) FROM fin_transactions WHERE import_id=%s) WHERE id=%s",
            (stats["rows_found"], stats["inserted"], stats["skipped"], import_id, import_id, import_id),
        )
        conn.commit()
        cursor.close()
        return stats


# ─────────────────────────────────────────────────────────────────────────────
# Adaptador BBVA AR — Cuenta Corriente ARS
# ─────────────────────────────────────────────────────────────────────────────


class BbvaArCuenta:
    """
    Parsea el PDF de resumen de cuenta corriente BBVA Argentina.

    Columnas por X (calibradas del PDF real):
        x < 97           → FECHA  (DD/MM — año inferido del PDF)
        97  ≤ x < 134    → ORIGEN
        134 ≤ x < 400    → CONCEPTO
        400 ≤ x < 474    → DÉBITO
        474 ≤ x < 515    → CRÉDITO
        x ≥ 515          → SALDO (ignorado)
    """

    SECTION_NAME = "bbva_cuenta"
    RE_DATE = re.compile(r"^\d{2}/\d{2}$")
    RE_INLINE_AMOUNT = re.compile(r"\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$")
    # Código interno BBVA: 11XXXXXXXX20260128DIGITAL → fecha cierre YYYYMMDD
    RE_BBVA_CLOSE = re.compile(r"1\d{8}(20\d{2})(\d{2})\d{2}DIGITAL")

    X_ORIGEN_MIN = 97
    X_CONCEPTO_MIN = 134
    X_DEBITO_MIN = 370
    X_CREDITO_MIN = 474
    X_SALDO_MIN = 515

    SKIP_MARKERS = {
        "SALDO ANTERIOR",
        "TOTALES DEL",
        "TOTAL DÉBITOS",
        "TOTAL CRÉDITOS",
        "Página",
    }

    def __init__(self, pdf_path: str, account_ref: str, dry_run: bool = False):
        self.pdf_path = pdf_path
        self.account_ref = account_ref.strip()
        self.dry_run = dry_run
        self.file_hash = sha256_file(pdf_path)
        self._end_year: int = datetime.now().year
        self._end_month: int = datetime.now().month

    def _infer_period(self, words: list[dict]):
        """Extrae año y mes de cierre del código interno BBVA o primer año encontrado."""
        for w in words:
            m = self.RE_BBVA_CLOSE.search(w["text"])
            if m:
                self._end_year = int(m.group(1))
                self._end_month = int(m.group(2))
                return
        # fallback: primer año mencionado
        for w in words:
            m = re.search(r"\b(20\d{2})\b", w["text"])
            if m:
                self._end_year = int(m.group(1))
                return

    def _is_date(self, text: str) -> bool:
        return bool(self.RE_DATE.match(text.strip()))

    def _parse_date(self, fecha_str: str) -> date | None:
        m = re.match(r"(\d{2})/(\d{2})$", fecha_str.strip())
        if not m:
            return None
        day, month = int(m.group(1)), int(m.group(2))
        # Fechas cuyo mes supera el mes de cierre → pertenecen al año anterior
        year = self._end_year if month <= self._end_month else self._end_year - 1
        try:
            return date(year, month, day)
        except ValueError:
            return None

    def _words_to_lines(self, words: list[dict], y_tol: float = 3.0) -> list[list[dict]]:
        if not words:
            return []
        lines, current = [], [words[0]]
        for w in words[1:]:
            if abs(w["top"] - current[0]["top"]) <= y_tol:
                current.append(w)
            else:
                lines.append(sorted(current, key=lambda x: x["x0"]))
                current = [w]
        lines.append(sorted(current, key=lambda x: x["x0"]))
        return lines

    def _classify_word(self, w: dict) -> str:
        x = w["x0"]
        if x < self.X_ORIGEN_MIN:
            return "fecha"
        if x < self.X_CONCEPTO_MIN:
            return "origen"
        if x < self.X_DEBITO_MIN:
            return "concepto"
        if x < self.X_CREDITO_MIN:
            return "debito"
        if x < self.X_SALDO_MIN:
            return "credito"
        return "saldo"

    def _extract_rows(self) -> list[dict]:
        rows = []
        in_detail = False
        with pdfplumber.open(self.pdf_path) as pdf:
            all_words = []
            for page in pdf.pages:
                all_words.extend(page.extract_words(x_tolerance=3, y_tolerance=3))
            self._infer_period(all_words)
            _logger.info(f"  BBVA CA — período cierre: {self._end_month}/{self._end_year}")
            for page in pdf.pages:
                words = [w for w in page.extract_words(x_tolerance=3, y_tolerance=3) if w["x0"] < 570]
                lines = self._words_to_lines(words)
                for line in lines:
                    line_text = " ".join(w["text"] for w in line)
                    upper = line_text.upper()
                    if "FECHA" in upper and "CONCEPTO" in upper and "DÉBITO" in upper:
                        in_detail = True
                        continue
                    if not in_detail:
                        continue
                    if any(mk.upper() in upper for mk in self.SKIP_MARKERS):
                        continue
                    cols = {"fecha": [], "origen": [], "concepto": [], "debito": [], "credito": [], "saldo": []}
                    for w in line:
                        cols[self._classify_word(w)].append(w["text"])
                    fecha_str = " ".join(cols["fecha"]).strip()
                    if not self._is_date(fecha_str):
                        continue
                    concepto = " ".join(cols["concepto"]).strip()
                    if not concepto:
                        continue
                    rows.append(
                        {
                            "fecha_str": fecha_str,
                            "origen": " ".join(cols["origen"]).strip() or None,
                            "concepto": concepto,
                            "debito": " ".join(cols["debito"]).strip(),
                            "credito": " ".join(cols["credito"]).strip(),
                        }
                    )
        return rows

    def _resolve_amount(self, r: dict) -> tuple[Decimal | None, str]:
        """Resuelve monto y tipo desde columnas DÉBITO/CRÉDITO o fallback inline.

        BBVA CA: negativo en col DÉBITO = dinero que SALE (expense/transfer)
                 positivo en col DÉBITO = dinero que ENTRA (income/transfer)
        """
        debito = parse_amount_ar(r.get("debito", ""))
        credito = parse_amount_ar(r.get("credito", ""))
        concepto = r["concepto"].strip()
        if debito is not None and debito != 0:
            # negativo = sale dinero (expense), positivo = entra dinero (income)
            return abs(debito), "expense" if debito < 0 else "income", concepto
        if credito is not None and credito != 0:
            return abs(credito), "income", concepto
        m_inline = self.RE_INLINE_AMOUNT.search(concepto)
        if m_inline:
            inline_val = parse_amount_ar(m_inline.group(1))
            if inline_val is not None:
                concepto_clean = concepto[: m_inline.start()].strip()
                txn_type = "expense" if inline_val > 0 else "income"
                return abs(inline_val), txn_type, concepto_clean
        return None, None, concepto

    def _build_transactions(self, rows: list[dict], account_id: int, import_id: int, cursor) -> list[dict]:
        txns = []
        for r in rows:
            txn_date = self._parse_date(r["fecha_str"])
            if not txn_date:
                _logger.warning(f"  Fecha inválida: {r['fecha_str']} — omitida")
                continue
            amount, txn_type, concepto = self._resolve_amount(r)
            if amount is None:
                _logger.warning(f"  Sin monto: {r['concepto'][:60]} — omitida")
                continue
            cat_id, classified_by = apply_rules(concepto, cursor)
            txns.append(
                {
                    "date": txn_date,
                    "type": txn_type,
                    "amount": amount,
                    "currency": "ARS",
                    "amount_usdt": _calc_usdt(amount, "ARS", txn_date, cursor),
                    "category_id": cat_id,
                    "account_id": account_id,
                    "description": f"{concepto} — {r['origen']}" if r.get("origen") else concepto,
                    "raw_description": concepto,
                    "raw_description_detail": r.get("origen"),
                    "comprobante": None,
                    "import_id": import_id,
                    "classified_by": classified_by,
                    "installment_current": None,
                    "installment_total": None,
                }
            )
        return txns

    def preview(self) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        raw_rows = self._extract_rows()
        stats["rows_found"] = len(raw_rows)
        _logger.info(f"  Filas encontradas: {len(raw_rows)}")
        for r in raw_rows:
            txn_date = self._parse_date(r["fecha_str"])
            if not txn_date:
                stats["errors"] += 1
                continue
            amount, txn_type, concepto = self._resolve_amount(r)
            if amount is None:
                _logger.warning(f"  Sin monto: {r['concepto'][:60]} — omitida")
                stats["errors"] += 1
                continue
            _logger.info(
                f"  {txn_date} | {txn_type:8s} | ARS {amount:>12.2f} | "
                f"orig={r.get('origen') or '-':>4s} | {concepto[:50]}"
            )
            stats["inserted"] += 1
        return stats

    def load(self, conn) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, bank_id FROM fin_accounts WHERE account_ref=%s AND is_active=1",
            (self.account_ref,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Cuenta no encontrada: account_ref='{self.account_ref}'")
        account_id, bank_id = row
        raw_rows = self._extract_rows()
        stats["rows_found"] = len(raw_rows)
        if not raw_rows:
            cursor.close()
            return stats
        cursor.execute(
            "SELECT id FROM fin_statement_imports WHERE file_hash=%s AND section=%s",
            (self.file_hash, self.SECTION_NAME),
        )
        if cursor.fetchone():
            _logger.warning("  PDF ya importado — omitido")
            cursor.close()
            return stats
        cursor.execute(
            "INSERT INTO fin_statement_imports (account_id,bank_id,filename,file_hash,section,status) "
            "VALUES (%s,%s,%s,%s,%s,'pending')",
            (account_id, bank_id, os.path.basename(self.pdf_path), self.file_hash, self.SECTION_NAME),
        )
        conn.commit()
        import_id = cursor.lastrowid
        txns = _dedup_raw_descriptions(self._build_transactions(raw_rows, account_id, import_id, cursor))
        for txn in txns:
            try:
                if _is_near_duplicate(cursor, txn):
                    stats["skipped"] += 1
                else:
                    cursor.execute(_INSERT_TXN_SQL, txn)
                    stats["inserted" if cursor.rowcount == 1 else "skipped"] += 1
            except Error as e:
                _logger.error(f"  Error: {e} — {txn.get('raw_description','')[:60]}")
                stats["errors"] += 1
        cursor.execute(
            "UPDATE fin_statement_imports SET status='processed',row_count=%s,processed_count=%s,skipped_count=%s,"
            "period_from=(SELECT MIN(date) FROM fin_transactions WHERE import_id=%s),"
            "period_to=(SELECT MAX(date) FROM fin_transactions WHERE import_id=%s) WHERE id=%s",
            (stats["rows_found"], stats["inserted"], stats["skipped"], import_id, import_id, import_id),
        )
        conn.commit()
        cursor.close()
        return stats


# ─────────────────────────────────────────────────────────────────────────────
# Adaptador BBVA AR — Caja de Ahorros ARS
# ─────────────────────────────────────────────────────────────────────────────


class BbvaArAhorro(BbvaArCuenta):
    """Layout idéntico a BbvaArCuenta. account_ref típico: '196-009369/5'"""

    SECTION_NAME = "bbva_ahorro"


# ─────────────────────────────────────────────────────────────────────────────
# Adaptador Santander AR — PDF unificado (cuenta + TC Visa + TC AmEx + débito)
# ─────────────────────────────────────────────────────────────────────────────


class SantanderAr:
    """
    Parsea el PDF mensual unificado de Santander Argentina.
    State machine detecta secciones por encabezados.

    Secciones → account_ref:
        cuenta_ars → 175-370719/9
        cuenta_usd → 175-370719/9-USD
        visa       → TC-0925
        amex       → TC-9541
        debito     → TD-2861
    """

    ACCOUNT_REF_MAP = {
        "cuenta_ars": "175-370719/9",
        "cuenta_usd": "175-370719/9-USD",
        "visa": "TC-0925",
        "amex": "TC-9541",
        "debito": "TD-2861",
    }
    SECTION_NAME_MAP = {
        "cuenta_ars": "santander_cuenta_ars",
        "cuenta_usd": "santander_cuenta_usd",
        "visa": "santander_visa",
        "amex": "santander_amex",
        "debito": "santander_debito",
    }

    RE_DATE_DDMMYY = re.compile(r"^\d{2}/\d{2}/\d{2}$")
    RE_CUOTA_SAN = re.compile(r"^(\d{1,2})\s+de\s+(\d{1,2})$", re.IGNORECASE)

    def __init__(self, pdf_path: str, dry_run: bool = False):
        self.pdf_path = pdf_path
        self.dry_run = dry_run
        self.file_hash = sha256_file(pdf_path)
        self._year: int = datetime.now().year

    def _words_to_lines(self, words: list[dict], y_tol: float = 4.0) -> list[list[dict]]:
        if not words:
            return []
        lines, current = [], [words[0]]
        for w in words[1:]:
            if abs(w["top"] - current[0]["top"]) <= y_tol:
                current.append(w)
            else:
                lines.append(sorted(current, key=lambda x: x["x0"]))
                current = [w]
        lines.append(sorted(current, key=lambda x: x["x0"]))
        return lines

    def _is_date(self, text: str) -> bool:
        return bool(self.RE_DATE_DDMMYY.match(text.strip()))

    def _parse_date(self, text: str) -> date | None:
        m = re.match(r"(\d{2})/(\d{2})/(\d{2})$", text.strip())
        if not m:
            return None
        try:
            return date(2000 + int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None

    def _parse_signed_tokens(self, tokens: list[str]) -> Decimal | None:
        joined = " ".join(tokens).strip()
        negative = joined.startswith("-")
        cleaned = re.sub(r"[-]?[\$]|U\$S|U\$\s*S", "", joined).strip()
        value = parse_amount_ar(cleaned)
        if value is None:
            return None
        return -value if negative else value

    def _classify_cuenta(self, w: dict) -> str:
        x = w["x0"]
        if x < 65:
            return "fecha"
        if x < 115:
            return "comprobante"
        if x < 340:
            return "concepto"
        if x < 416:
            return "monto_ca"
        if x < 524:
            return "monto_cc"
        return "saldo"

    def _classify_tc(self, w: dict) -> str:
        x = w["x0"]
        if x < 80:
            return "fecha"
        if x < 140:
            return "comprobante"
        if x < 345:
            return "descripcion"
        if x < 415:
            return "cuota"
        if x < 500:
            return "pesos"
        return "dolares"

    def _classify_tc_pagos(self, w: dict) -> str:
        """Sección 'Pago anterior y devoluciones' — sin columna comprobante."""
        x = w["x0"]
        if x < 65:
            return "fecha"
        if x < 410:
            return "descripcion"
        if x < 500:
            return "pesos"
        return "dolares"

    def _classify_debito(self, w: dict) -> str:
        x = w["x0"]
        if x < 60:
            return "fecha"
        if x < 144:
            return "comprobante"
        if x < 480:
            return "descripcion"
        return "importe"

    def _extract_all(self) -> dict[str, list[dict]]:
        result: dict[str, list[dict]] = {k: [] for k in self.ACCOUNT_REF_MAP}
        state = "none"
        prev_state = "none"
        product_ctx = "none"
        pending_san = False
        last_fecha_str = ""

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                words = [w for w in page.extract_words(x_tolerance=3, y_tolerance=3) if w["x0"] < 600]
                lines = self._words_to_lines(words)
                for line in lines:
                    text = " ".join(w["text"] for w in line)
                    upper = text.upper()

                    if pending_san:
                        pending_san = False
                        if "VISA" in upper:
                            product_ctx = "visa"
                            state = "none"
                            continue
                        if "AMERICAN EXPRESS" in upper:
                            product_ctx = "amex"
                            state = "none"
                            continue

                    if upper.strip() == "TARJETA SANTANDER":
                        pending_san = True
                        state = "none"
                        continue
                    if "TARJETA DE D" in upper and "BITO" in upper and len(line) <= 4:
                        product_ctx = "debito"
                        state = "none"
                        continue
                    if "CAJA DE AHORRO EN PESOS" in upper and "CUENTA CORRIENTE EN PESOS" in upper:
                        state = "cuenta_ars"
                        product_ctx = "cuenta"
                        continue
                    if "CAJA DE AHORRO EN" in upper and "LARES" in upper and product_ctx == "cuenta":
                        state = "cuenta_usd"
                        continue
                    if state in ("cuenta_ars", "cuenta_usd") and (
                        "SALDO TOTAL" in upper or "DETALLE IMPOSITIVO" in upper
                    ):
                        state = "none"
                        continue
                    if product_ctx in ("visa", "amex") and "PAGO ANTERIOR" in upper:
                        state = "tc_pagos"
                        continue
                    if "CONSUMOS DEL MES" in upper and product_ctx in ("visa", "amex"):
                        state = product_ctx
                        continue
                    if product_ctx in ("visa", "amex") and upper.startswith("IMPUESTOS"):
                        state = "tc_impuestos"
                        continue
                    if state in ("visa", "amex", "tc_impuestos") and (
                        upper.startswith("CONSUMOS TOTALES")
                        or (upper.startswith("TOTAL CONSUMOS") and "DE " not in upper[:30])
                        or upper.startswith("TOTAL A PAGAR")
                    ):
                        state = "none"
                        continue
                    if state in ("visa", "amex") and "DESCRIPCI" in upper and "CUOTA" in upper:
                        continue
                    if state == "tc_pagos" and "CONSUMOS DEL MES" in upper:
                        state = product_ctx
                        last_fecha_str = ""
                        continue
                    if product_ctx == "debito" and "ESTABLECIMIENTO" in upper and "IMPORTE" in upper:
                        state = "debito"
                        continue
                    if product_ctx == "debito" and "SERVICIO" in upper and "MEDIO DE PAGO" in upper:
                        state = "debito_pagos"
                        continue
                    if state == "debito" and upper.startswith("MONTO TOTAL"):
                        state = "none"
                        continue
                    if state == "debito_pagos" and upper.startswith("PAGOS TOTALES"):
                        state = "none"
                        continue

                    if state != prev_state:
                        last_fecha_str = ""
                        prev_state = state

                    if state == "cuenta_ars":
                        last_fecha_str = self._process_cuenta_line(line, result["cuenta_ars"], last_fecha_str)
                    elif state == "cuenta_usd":
                        last_fecha_str = self._process_cuenta_usd_line(line, result["cuenta_usd"], last_fecha_str)
                    elif state in ("visa", "amex"):
                        last_fecha_str = self._process_tc_line(line, result[state], last_fecha_str)
                    elif state in ("tc_pagos", "tc_impuestos"):
                        last_fecha_str = self._process_tc_line(
                            line, result[product_ctx], last_fecha_str, classifier=self._classify_tc_pagos
                        )
                    # debito omitido — sus transacciones ya están en cuenta_ars (duplicado)

        return result

    def _process_cuenta_line(self, line: list[dict], rows: list[dict], last_fecha_str: str = "") -> str:
        cols = {k: [] for k in ("fecha", "comprobante", "concepto", "monto_ca", "monto_cc", "saldo")}
        for w in line:
            cols[self._classify_cuenta(w)].append(w["text"])
        fecha_str = " ".join(cols["fecha"]).strip()
        if not self._is_date(fecha_str):
            fecha_str = last_fecha_str
        if not fecha_str:
            return last_fecha_str
        concepto = " ".join(cols["concepto"]).strip()
        if any(s in concepto.upper() for s in ("SALDO INICIAL", "SALDO ANTERIOR")):
            return fecha_str
        monto_tokens = cols["monto_ca"] or cols["monto_cc"]
        amount = self._parse_signed_tokens(monto_tokens)
        if amount is None:
            # línea sin monto: es detalle de la transacción anterior. Vale solo la primera: si el movimiento
            # cierra la hoja, las que siguen son el pie legal y pisaban la contraparte
            if concepto and rows and "detail" not in rows[-1]:
                rows[-1]["detail"] = concepto
            return fecha_str
        rows.append(
            {
                "fecha_str": fecha_str,
                "date": self._parse_date(fecha_str),
                "comprobante": " ".join(cols["comprobante"]).strip() or None,
                "concepto": concepto,
                "amount": abs(amount),
                "type": "expense" if amount < 0 else "income",
                "currency": "ARS",
            }
        )
        return fecha_str

    def _process_cuenta_usd_line(self, line: list[dict], rows: list[dict], last_fecha_str: str = "") -> str:
        cols = {k: [] for k in ("fecha", "comprobante", "concepto", "monto_ca", "monto_cc", "saldo")}
        for w in line:
            cols[self._classify_cuenta(w)].append(w["text"])
        fecha_str = " ".join(cols["fecha"]).strip()
        if not self._is_date(fecha_str):
            fecha_str = last_fecha_str
        if not fecha_str:
            return last_fecha_str
        concepto = " ".join(cols["concepto"]).strip()
        if any(s in concepto.upper() for s in ("SALDO INICIAL", "SALDO ANTERIOR")):
            return fecha_str
        monto_tokens = cols["monto_ca"] or cols["monto_cc"]
        amount = self._parse_signed_tokens(monto_tokens)
        if amount is None:
            # línea sin monto: es detalle de la transacción anterior. Vale solo la primera: si el movimiento
            # cierra la hoja, las que siguen son el pie legal y pisaban la contraparte
            if concepto and rows and "detail" not in rows[-1]:
                rows[-1]["detail"] = concepto
            return fecha_str
        rows.append(
            {
                "fecha_str": fecha_str,
                "date": self._parse_date(fecha_str),
                "comprobante": " ".join(cols["comprobante"]).strip() or None,
                "concepto": concepto,
                "amount": abs(amount),
                "type": "expense" if amount < 0 else "income",
                "currency": "USD",
            }
        )
        return fecha_str

    def _process_tc_line(self, line: list[dict], rows: list[dict], last_fecha_str: str = "", classifier=None) -> str:
        cols = {k: [] for k in ("fecha", "comprobante", "descripcion", "cuota", "pesos", "dolares")}
        classify = classifier or self._classify_tc
        for w in line:
            cols[classify(w)].append(w["text"])
        fecha_str = " ".join(cols["fecha"]).strip()
        if not self._is_date(fecha_str):
            fecha_str = last_fecha_str
        if not fecha_str:
            return last_fecha_str
        desc = " ".join(cols["descripcion"]).strip()
        if not desc:
            return fecha_str
        desc_upper = desc.upper()
        # Cr.rg 5617 se carga: devuelve la percepción Db.rg 5617 que ahora entra por la sección Impuestos
        if (
            any(s in desc_upper for s in ("SALDO ANTERIOR", "TRANSFERENCIA DEUDA"))
            or ("CR." in desc_upper and "CR.RG" not in desc_upper)
            or desc_upper == "TOTAL"
        ):
            return fecha_str
        if cols["pesos"]:
            amount = self._parse_signed_tokens(cols["pesos"])
            currency = "ARS"
        elif cols["dolares"]:
            amount = self._parse_signed_tokens(cols["dolares"])
            currency = "USD"
        else:
            # línea sin monto: es detalle de la transacción anterior
            if desc and rows:
                rows[-1]["detail"] = desc
            return fecha_str
        if amount is None:
            return fecha_str
        cuota_text = " ".join(cols["cuota"]).strip()
        inst_cur, inst_tot = parse_plan_installment(desc)
        m = self.RE_CUOTA_SAN.match(cuota_text)
        if m:
            inst_cur, inst_tot = int(m.group(1)), int(m.group(2))
        rows.append(
            {
                "fecha_str": fecha_str,
                "date": self._parse_date(fecha_str),
                "comprobante": " ".join(cols["comprobante"]).strip() or None,
                "concepto": desc,
                "amount": abs(amount),
                "type": "expense" if amount >= 0 else "income",
                "currency": currency,
                "installment_current": inst_cur,
                "installment_total": inst_tot,
            }
        )
        return fecha_str

    def _process_debito_line(self, line: list[dict], rows: list[dict], expense: bool, last_fecha_str: str = "") -> str:
        cols = {k: [] for k in ("fecha", "comprobante", "descripcion", "importe")}
        for w in line:
            cols[self._classify_debito(w)].append(w["text"])
        fecha_str = " ".join(cols["fecha"]).strip()
        if not self._is_date(fecha_str):
            fecha_str = last_fecha_str
        if not fecha_str:
            return last_fecha_str
        desc = " ".join(cols["descripcion"]).strip()
        if not desc:
            return fecha_str
        amount = self._parse_signed_tokens(cols["importe"])
        if amount is None:
            return fecha_str
        rows.append(
            {
                "fecha_str": fecha_str,
                "date": self._parse_date(fecha_str),
                "comprobante": " ".join(cols["comprobante"]).strip() or None,
                "concepto": desc,
                "amount": abs(amount),
                "type": "expense" if expense else "income",
                "currency": "ARS",
                "installment_current": None,
                "installment_total": None,
            }
        )
        return fecha_str

    def _build_transactions(self, rows, account_id, import_id, section_key, cursor) -> list[dict]:
        txns = []
        for r in rows:
            if not r.get("date"):
                _logger.warning(f"  [{section_key}] Fecha inválida: {r.get('fecha_str')} — omitida")
                continue
            currency = r.get("currency", "ARS")
            detail = r.get("detail", "")
            cat_id, classified_by = apply_rules(r["concepto"], cursor, detail=detail)
            txns.append(
                {
                    "date": r["date"],
                    "type": r["type"],
                    "amount": r["amount"],
                    "currency": currency,
                    "amount_usdt": _calc_usdt(r["amount"], currency, r["date"], cursor),
                    "category_id": cat_id,
                    "account_id": account_id,
                    "description": f"{r['concepto']} — {detail}" if detail else r["concepto"],
                    "raw_description": r["concepto"],
                    "raw_description_detail": detail or None,
                    "comprobante": r.get("comprobante"),
                    "import_id": import_id,
                    "classified_by": classified_by,
                    "installment_current": r.get("installment_current"),
                    "installment_total": r.get("installment_total"),
                }
            )
        return txns

    def preview(self) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        all_rows = self._extract_all()
        for section_key, rows in all_rows.items():
            if not rows:
                continue
            _logger.info(f"\n  ── {section_key} ({self.ACCOUNT_REF_MAP[section_key]}) — {len(rows)} filas ──")
            stats["rows_found"] += len(rows)
            for r in rows:
                if not r.get("date"):
                    stats["errors"] += 1
                    continue
                inst = f" [{r['installment_current']}/{r['installment_total']}]" if r.get("installment_current") else ""
                _logger.info(
                    f"  {r['date']} | {r['type']:8s} | {r.get('currency','ARS')} "
                    f"{r['amount']:>12.2f}{inst} | {r['concepto'][:50]}"
                )
                stats["inserted"] += 1
        return stats

    def load(self, conn) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        cursor = conn.cursor()
        account_ids: dict[str, int] = {}
        bank_ids: dict[str, int] = {}
        for section_key, acct_ref in self.ACCOUNT_REF_MAP.items():
            cursor.execute("SELECT id, bank_id FROM fin_accounts WHERE account_ref=%s AND is_active=1", (acct_ref,))
            row = cursor.fetchone()
            if row:
                account_ids[section_key] = row[0]
                bank_ids[section_key] = row[1]
            else:
                _logger.warning(f"  Cuenta no encontrada: {acct_ref} ({section_key}) — omitida")

        all_rows = self._extract_all()
        stats["rows_found"] = sum(len(rows) for section_key, rows in all_rows.items() if section_key in account_ids)
        if not stats["rows_found"]:
            cursor.close()
            return stats
        import_ids: dict[str, int] = {}
        filename = os.path.basename(self.pdf_path)
        for section_key, section_name in self.SECTION_NAME_MAP.items():
            if section_key not in account_ids:
                continue
            cursor.execute(
                "SELECT id FROM fin_statement_imports WHERE file_hash=%s AND section=%s",
                (self.file_hash, section_name),
            )
            if cursor.fetchone():
                _logger.warning(f"  [{section_key}] Ya importado — omitido")
                import_ids[section_key] = -1
                continue
            cursor.execute(
                "INSERT INTO fin_statement_imports (account_id,bank_id,filename,file_hash,section,status) "
                "VALUES (%s,%s,%s,%s,%s,'pending')",
                (account_ids[section_key], bank_ids[section_key], filename, self.file_hash, section_name),
            )
            conn.commit()
            import_ids[section_key] = cursor.lastrowid

        for section_key, rows in all_rows.items():
            if import_ids.get(section_key) == -1:
                continue
            if section_key not in account_ids or section_key not in import_ids:
                continue
            import_id = import_ids[section_key]
            txns = _dedup_raw_descriptions(
                self._build_transactions(rows, account_ids[section_key], import_id, section_key, cursor)
            )
            inserted_sec = 0
            for txn in txns:
                try:
                    if _is_near_duplicate(cursor, txn):
                        stats["skipped"] += 1
                    else:
                        cursor.execute(_INSERT_TXN_SQL, txn)
                        if cursor.rowcount == 1:
                            stats["inserted"] += 1
                            inserted_sec += 1
                        else:
                            stats["skipped"] += 1
                except Error as e:
                    _logger.error(f"  Error: {e} — {txn.get('raw_description','')[:60]}")
                    stats["errors"] += 1
            cursor.execute(
                "UPDATE fin_statement_imports SET status='processed',row_count=%s,processed_count=%s,"
                "period_from=(SELECT MIN(date) FROM fin_transactions WHERE import_id=%s),"
                "period_to=(SELECT MAX(date) FROM fin_transactions WHERE import_id=%s) WHERE id=%s",
                (len(rows), inserted_sec, import_id, import_id, import_id),
            )
            conn.commit()
            _logger.info(f"  [{section_key}] {len(rows)} filas → {inserted_sec} insertadas")

        # el sellado va fuera del bucle y sobre todas las secciones del PDF: el cierre que cobra las cuotas es del
        # resumen entero, y así alcanza también a las secciones que ya estaban cargadas y el bucle se saltea
        cursor.execute("SELECT id FROM fin_statement_imports WHERE file_hash = %s", (self.file_hash,))
        for (sec_id,) in cursor.fetchall():
            _set_billing_dates(cursor, sec_id)
        conn.commit()
        cursor.close()
        return stats


# ─────────────────────────────────────────────────────────────────────────────
# Adaptador Santander AR — Resumen de tarjeta (ciclo y cuotas a vencer)
# ─────────────────────────────────────────────────────────────────────────────


class SantanderArTarjetaResumen:
    """
    PDF de resumen de tarjeta Santander (Visa / American Express). Los movimientos entran por el extracto de
    cuenta (SantanderAr); de este PDF se lee solo la hoja 1:
        línea con 6 fechas dd/mm/yy → cierre y vencimiento anterior, actual y próximo
        "Próximas cuotas a vencer"  → meses con su importe debajo
    """

    SECTION_NAME = "santander_tc_resumen"
    _words_to_lines = SantanderAr._words_to_lines

    def __init__(self, pdf_path: str, account_ref: str):
        self.pdf_path = pdf_path
        self.account_ref = account_ref.strip()
        self.file_hash = sha256_file(pdf_path)

    def load(self, conn) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, bank_id FROM fin_accounts WHERE account_ref=%s AND is_active=1",
            (self.account_ref,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Cuenta no encontrada: account_ref='{self.account_ref}'")
        account_id, bank_id = row
        cycle = self._extract_cycle()
        if not cycle:
            cursor.close()
            return stats
        stats["rows_found"] = 1 + len(cycle["installments"])
        cursor.execute(
            "SELECT id FROM fin_statement_imports WHERE file_hash=%s AND section=%s",
            (self.file_hash, self.SECTION_NAME),
        )
        if cursor.fetchone():
            _logger.warning("  PDF ya importado — omitido")
            cursor.close()
            return stats
        cursor.execute(
            "INSERT INTO fin_statement_imports (account_id,bank_id,filename,file_hash,section,status) "
            "VALUES (%s,%s,%s,%s,%s,'pending')",
            (account_id, bank_id, os.path.basename(self.pdf_path), self.file_hash, self.SECTION_NAME),
        )
        conn.commit()
        import_id = cursor.lastrowid
        stats["inserted"] = _save_card_cycle(cursor, account_id, import_id, cycle)
        stats["skipped"] = stats["rows_found"] - stats["inserted"]
        cursor.execute(
            "UPDATE fin_statement_imports SET status='processed',row_count=%s,processed_count=%s,skipped_count=%s,"
            "period_from=%s,period_to=%s WHERE id=%s",
            (
                stats["rows_found"],
                stats["inserted"],
                stats["skipped"],
                cycle["prev_closing"],
                cycle["closing"],
                import_id,
            ),
        )
        if stats["inserted"]:
            # el cierre real recién quedó en fin_card_cycles: los resúmenes de esta tarjeta que ya se cargaron con el
            # último movimiento como aproximación se corrigen solos, sin volver a soltar el PDF
            cursor.execute(
                "SELECT DISTINCT i.id FROM fin_statement_imports i JOIN fin_transactions t ON t.import_id = i.id "
                "WHERE i.account_id = %s AND t.installment_current IS NOT NULL",
                (account_id,),
            )
            for (sec_id,) in cursor.fetchall():
                _set_billing_dates(cursor, sec_id)
        conn.commit()
        cursor.close()
        return stats

    def _extract_cycle(self) -> dict | None:
        with pdfplumber.open(self.pdf_path) as pdf:
            lines = self._words_to_lines(pdf.pages[0].extract_words(x_tolerance=3, y_tolerance=3))
        for line in lines:
            fechas = [w["text"] for w in line if SantanderAr.RE_DATE_DDMMYY.match(w["text"])]
            if len(fechas) != 6:
                continue
            d = [datetime.strptime(f, "%d/%m/%y").date() for f in fechas]
            return {
                "prev_closing": d[0],
                "closing": d[2],
                "due": d[3],
                "next_closing": d[4],
                "next_due": d[5],
                "installments": parse_installments_due(lines),
            }
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Adaptador Citibank US — Checking + Savings (estado de cuenta mensual)
# ─────────────────────────────────────────────────────────────────────────────


class CitibankUs:
    """
    Parsea el PDF mensual de Citibank USA (Regular Checking + Savings Plus).

    Secciones detectadas por encabezado:
        CHECKING ACTIVITY  → account_ref CITI-9135153751
        SAVINGS ACTIVITY   → account_ref CITI-9137165365

    Columnas por X (layout fijo Citi):
        x < 90       → fecha  (MM/DD)
        90 ≤ x < 390 → descripción
        390 ≤ x < 480 → amount_subtracted (débito)
        480 ≤ x < 560 → amount_added (crédito)
        x ≥ 560      → balance (ignorado)

    Fecha: MM/DD — año inferido del header "Statement Period Dec 15 - Jan 12, 2026"
    """

    ACCOUNT_REF_MAP = {
        "checking": "CITI-9135153751",
        "savings": "CITI-9137165365",
    }
    SECTION_NAME_MAP = {
        "checking": "citi_checking",
        "savings": "citi_savings",
    }

    RE_DATE = re.compile(r"^\d{2}/\d{2}$")
    RE_STMT_PERIOD = re.compile(r"(\w+)\s+\d+\s*-\s*(\w+)\s+\d+,\s*(20\d{2})", re.IGNORECASE)

    MESES_EN = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    SKIP_DESC = {"Total Subtracted/Added", "Beginning Balance", "Ending Balance"}

    def __init__(self, pdf_path: str, dry_run: bool = False):
        self.pdf_path = pdf_path
        self.dry_run = dry_run
        self.file_hash = sha256_file(pdf_path)
        self._end_year: int = datetime.now().year
        self._end_month: int = datetime.now().month

    def _infer_period(self, text: str):
        """Extrae año y mes de cierre del statement period. Ej: 'Dec 15 - Jan 12, 2026' → end_month=1, end_year=2026."""
        m = self.RE_STMT_PERIOD.search(text)
        if m:
            self._end_month = self.MESES_EN.get(m.group(2).lower()[:3], self._end_month)
            self._end_year = int(m.group(3))

    def _is_date(self, text: str) -> bool:
        return bool(self.RE_DATE.match(text.strip()))

    def _parse_date(self, fecha_str: str) -> date | None:
        m = re.match(r"(\d{2})/(\d{2})$", fecha_str.strip())
        if not m:
            return None
        month, day = int(m.group(1)), int(m.group(2))
        # Transacciones cuyo mes es mayor al mes de cierre → pertenecen al año anterior
        year = self._end_year if month <= self._end_month else self._end_year - 1
        try:
            return date(year, month, day)
        except ValueError:
            return None

    def _words_to_lines(self, words: list[dict], y_tol: float = 3.0) -> list[list[dict]]:
        if not words:
            return []
        lines, current = [], [words[0]]
        for w in words[1:]:
            if abs(w["top"] - current[0]["top"]) <= y_tol:
                current.append(w)
            else:
                lines.append(sorted(current, key=lambda x: x["x0"]))
                current = [w]
        lines.append(sorted(current, key=lambda x: x["x0"]))
        return lines

    def _classify_word(self, w: dict) -> str:
        x = w["x0"]
        if x < 75:
            return "fecha"
        if x < 355:
            return "desc"
        if x < 450:
            return "subtracted"
        if x < 530:
            return "added"
        return "balance"

    def _extract_all(self) -> dict[str, list[dict]]:
        result = {"checking": [], "savings": []}
        state = "none"

        with pdfplumber.open(self.pdf_path) as pdf:
            full_text = " ".join(
                w["text"] for page in pdf.pages[:2] for w in page.extract_words(x_tolerance=3, y_tolerance=3)
            )
            self._infer_period(full_text)
            _logger.info(f"  Citi — período cierre: {self._end_month}/{self._end_year}")

            for page in pdf.pages:
                words = [w for w in page.extract_words(x_tolerance=3, y_tolerance=3) if w["x0"] < 600]
                lines = self._words_to_lines(words)
                pending_row: dict | None = None  # fila abierta esperando continuación desc

                for line in lines:
                    text = " ".join(w["text"] for w in line)
                    upper = text.upper()

                    if "CHECKING ACTIVITY" in upper:
                        state = "checking"
                        pending_row = None
                        continue
                    if "SAVINGS ACTIVITY" in upper:
                        state = "savings"
                        pending_row = None
                        continue
                    if state == "none":
                        continue
                    if any(s.upper() in upper for s in self.SKIP_DESC):
                        if pending_row:
                            result[state].append(pending_row)
                            pending_row = None
                        continue
                    if "ALL TRANSACTION TIMES" in upper or "APY AND INTEREST" in upper:
                        pending_row = None
                        continue

                    cols = {"fecha": [], "desc": [], "subtracted": [], "added": [], "balance": []}
                    for w in line:
                        cols[self._classify_word(w)].append(w["text"])

                    fecha_str = " ".join(cols["fecha"]).strip()
                    desc = " ".join(cols["desc"]).strip()

                    if not self._is_date(fecha_str):
                        # línea de continuación de descripción (sin fecha, sin montos)
                        if pending_row and desc and not cols["subtracted"] and not cols["added"]:
                            pending_row["concepto"] += " " + desc
                        else:
                            pending_row = None
                        continue

                    # nueva fila con fecha
                    if pending_row:
                        result[state].append(pending_row)
                    pending_row = None

                    if not desc:
                        continue

                    subtracted = parse_amount_us(" ".join(cols["subtracted"]))
                    added = parse_amount_us(" ".join(cols["added"]))

                    if added is not None and added != 0:
                        amount, txn_type = added, "income"
                    elif subtracted is not None and subtracted != 0:
                        amount, txn_type = subtracted, "expense"
                    else:
                        continue

                    pending_row = {
                        "fecha_str": fecha_str,
                        "date": self._parse_date(fecha_str),
                        "concepto": desc,
                        "amount": abs(amount),
                        "type": txn_type,
                        "currency": "USD",
                    }

                if pending_row:
                    result[state].append(pending_row)
                    pending_row = None

        return result

    def _build_transactions(self, rows, account_id, import_id, section_key, cursor) -> list[dict]:
        txns = []
        for r in rows:
            if not r.get("date"):
                _logger.warning(f"  [{section_key}] Fecha inválida: {r.get('fecha_str')} — omitida")
                continue
            cat_id, classified_by = apply_rules(r["concepto"], cursor)
            txns.append(
                {
                    "date": r["date"],
                    "type": r["type"],
                    "amount": r["amount"],
                    "currency": "USD",
                    "amount_usdt": r["amount"],  # USD = USDT directo
                    "category_id": cat_id,
                    "account_id": account_id,
                    "description": r["concepto"],
                    "raw_description": r["concepto"],
                    "raw_description_detail": None,
                    "comprobante": None,
                    "import_id": import_id,
                    "classified_by": classified_by,
                    "installment_current": None,
                    "installment_total": None,
                }
            )
        return txns

    def preview(self) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        all_rows = self._extract_all()
        for section_key, rows in all_rows.items():
            if not rows:
                continue
            _logger.info(f"\n  ── {section_key} ({self.ACCOUNT_REF_MAP[section_key]}) — {len(rows)} filas ──")
            stats["rows_found"] += len(rows)
            for r in rows:
                if not r.get("date"):
                    stats["errors"] += 1
                    continue
                _logger.info(f"  {r['date']} | {r['type']:8s} | USD {r['amount']:>10.2f} | {r['concepto'][:60]}")
                stats["inserted"] += 1
        return stats

    def load(self, conn) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        cursor = conn.cursor()
        account_ids: dict[str, int] = {}
        bank_ids: dict[str, int] = {}
        for section_key, acct_ref in self.ACCOUNT_REF_MAP.items():
            cursor.execute("SELECT id, bank_id FROM fin_accounts WHERE account_ref=%s AND is_active=1", (acct_ref,))
            row = cursor.fetchone()
            if row:
                account_ids[section_key] = row[0]
                bank_ids[section_key] = row[1]
            else:
                _logger.warning(f"  Cuenta no encontrada: {acct_ref} ({section_key}) — omitida")

        all_rows = self._extract_all()
        stats["rows_found"] = sum(len(rows) for section_key, rows in all_rows.items() if section_key in account_ids)
        if not stats["rows_found"]:
            cursor.close()
            return stats
        import_ids: dict[str, int] = {}
        filename = os.path.basename(self.pdf_path)
        for section_key, section_name in self.SECTION_NAME_MAP.items():
            if section_key not in account_ids:
                continue
            cursor.execute(
                "SELECT id FROM fin_statement_imports WHERE file_hash=%s AND section=%s",
                (self.file_hash, section_name),
            )
            if cursor.fetchone():
                _logger.warning(f"  [{section_key}] Ya importado — omitido")
                import_ids[section_key] = -1
                continue
            cursor.execute(
                "INSERT INTO fin_statement_imports (account_id,bank_id,filename,file_hash,section,status) "
                "VALUES (%s,%s,%s,%s,%s,'pending')",
                (account_ids[section_key], bank_ids[section_key], filename, self.file_hash, section_name),
            )
            conn.commit()
            import_ids[section_key] = cursor.lastrowid

        for section_key, rows in all_rows.items():
            if import_ids.get(section_key) == -1:
                continue
            if section_key not in account_ids or section_key not in import_ids:
                continue
            import_id = import_ids[section_key]
            txns = _dedup_raw_descriptions(
                self._build_transactions(rows, account_ids[section_key], import_id, section_key, cursor)
            )
            inserted_sec = 0
            for txn in txns:
                try:
                    if _is_near_duplicate(cursor, txn):
                        stats["skipped"] += 1
                    else:
                        cursor.execute(_INSERT_TXN_SQL, txn)
                        if cursor.rowcount == 1:
                            stats["inserted"] += 1
                            inserted_sec += 1
                        else:
                            stats["skipped"] += 1
                except Error as e:
                    _logger.error(f"  Error: {e} — {txn.get('raw_description','')[:60]}")
                    stats["errors"] += 1
            cursor.execute(
                "UPDATE fin_statement_imports SET status='processed',row_count=%s,processed_count=%s,"
                "period_from=(SELECT MIN(date) FROM fin_transactions WHERE import_id=%s),"
                "period_to=(SELECT MAX(date) FROM fin_transactions WHERE import_id=%s) WHERE id=%s",
                (len(rows), inserted_sec, import_id, import_id, import_id),
            )
            conn.commit()
            _logger.info(f"  [{section_key}] {len(rows)} filas → {inserted_sec} insertadas")

        cursor.close()
        return stats


# ─────────────────────────────────────────────────────────────────────────────
# Parser: Banco de Venezuela (BDV) — moneda nacional (VES)
# ─────────────────────────────────────────────────────────────────────────────


class BdvVes:
    """
    Parser para extractos del Banco de Venezuela — cuenta en bolívares (VES).

    Columnas posicionales del PDF:
      x < 80        → Referencia
      80 ≤ x < 316  → Descripción
      316 ≤ x < 368 → Fecha  (DD/MM/YYYY)
      368 ≤ x < 414 → Mov    (SI / NC / ND)
      414 ≤ x < 475 → Débito
      475 ≤ x < 540 → Crédito
      x ≥ 540       → Saldo

    NC = ingreso, ND = egreso, SI = saldo inicial (se omite).
    """

    SECTION_NAME = "bdv_cc"

    _X_REF = 80
    _X_DESC = 316
    _X_FECHA = 368
    _X_MOV = 414
    _X_DEB = 475
    _X_CRED = 540
    _DATE_FMT = "%d/%m/%Y"

    def __init__(self, pdf_path: str, account_ref: str, dry_run: bool = False):
        self._pdf_path = pdf_path
        self._account_ref = account_ref
        self._dry_run = dry_run

    def _parse_amount(self, s: str) -> Decimal:
        """Convierte '8.142,30' o '-7.932,08' → Decimal (formato VES: punto=miles, coma=decimal)."""
        s = s.strip().lstrip("-").replace(".", "").replace(",", ".")
        try:
            return Decimal(s)
        except InvalidOperation:
            return Decimal("0")

    def _parse_rows(self) -> list[dict]:
        rows = []
        with pdfplumber.open(self._pdf_path) as pdf:
            for page in pdf.pages:
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                row_map: dict[int, list] = {}
                for w in words:
                    key = round(w["top"] / 3) * 3
                    row_map.setdefault(key, []).append(w)
                for top_key in sorted(row_map.keys()):
                    ws = sorted(row_map[top_key], key=lambda w: w["x0"])
                    ref_p, desc_p, fecha_p, mov_p, deb_p, cred_p = [], [], [], [], [], []
                    for w in ws:
                        x, t = w["x0"], w["text"]
                        if x < self._X_REF:
                            ref_p.append(t)
                        elif x < self._X_DESC:
                            desc_p.append(t)
                        elif x < self._X_FECHA:
                            fecha_p.append(t)
                        elif x < self._X_MOV:
                            mov_p.append(t)
                        elif x < self._X_DEB:
                            deb_p.append(t)
                        elif x < self._X_CRED:
                            cred_p.append(t)
                    fecha_str = " ".join(fecha_p).strip()
                    mov = " ".join(mov_p).strip()
                    if not re.match(r"\d{2}/\d{2}/\d{4}", fecha_str):
                        continue
                    if mov not in ("SI", "NC", "ND"):
                        continue
                    if mov == "SI":
                        continue
                    try:
                        txn_date = datetime.strptime(fecha_str, self._DATE_FMT).date()
                    except ValueError:
                        continue
                    desc = " ".join(desc_p).strip()
                    ref = " ".join(ref_p).strip()
                    if mov == "NC":
                        txn_type = "income"
                        amount = self._parse_amount(" ".join(cred_p).strip())
                    else:
                        txn_type = "expense"
                        amount = self._parse_amount(" ".join(deb_p).strip())
                    if amount == 0:
                        continue
                    rows.append(
                        {"date": txn_date, "type": txn_type, "amount": amount, "description": desc, "comprobante": ref}
                    )
        return rows

    def _get_account_ids(self, cursor) -> tuple[int, int] | None:
        cursor.execute(
            "SELECT id, bank_id FROM fin_accounts WHERE account_ref = %s AND is_active = 1",
            (self._account_ref,),
        )
        return cursor.fetchone()

    def _file_hash(self) -> str:
        h = hashlib.sha256()
        with open(self._pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _get_monthly_rates(self, cursor) -> dict:
        """Tasa promedio ponderada VES/USDT por mes desde booktrading (categoria='VES')."""
        cursor.execute("""SELECT DATE_FORMAT(fechahora,'%Y-%m'),
                      SUM(ABS(producto)) / SUM(ABS(cantidad))
               FROM booktrading WHERE simbolo='USDT' AND categoria='VES'
               GROUP BY DATE_FORMAT(fechahora,'%Y-%m')""")
        return {row[0]: Decimal(str(row[1])) for row in cursor.fetchall()}

    def _build_transactions(self, rows: list[dict], account_id: int, import_id: int, cursor) -> list[dict]:
        rates = self._get_monthly_rates(cursor)
        txns = []
        for r in rows:
            mes = r["date"].strftime("%Y-%m")
            tasa = rates.get(mes)
            amount_usdt = round(r["amount"] / tasa, 6) if tasa else None
            # NC (income) = ingreso desde Binance P2P — prefijo para distinguir de ND salidas
            is_income = r["type"] == "income"
            description = ("BINANCE P2P - " + r["description"]) if is_income else r["description"]
            cat_id, classified_by = apply_rules(description, cursor)
            txns.append(
                {
                    "date": r["date"],
                    "type": r["type"],
                    "amount": r["amount"],
                    "currency": "VES",
                    "amount_usdt": amount_usdt,
                    "category_id": cat_id,
                    "account_id": account_id,
                    "description": description,
                    "raw_description": r["description"],
                    "raw_description_detail": None,
                    "comprobante": r["comprobante"],
                    "import_id": import_id,
                    "classified_by": classified_by or "unclassified",
                    "installment_current": None,
                    "installment_total": None,
                }
            )
        return txns

    def preview(self) -> dict:
        rows = self._parse_rows()
        for r in rows:
            print(f"  {r['date']}  {r['type']:<8}  {r['amount']:>12}  {r['description']}")
        return {"rows_found": len(rows), "inserted": 0, "skipped": len(rows), "errors": 0}

    def load(self, conn) -> dict:
        stats = {"rows_found": 0, "inserted": 0, "skipped": 0, "errors": 0}
        cursor = conn.cursor()
        row = self._get_account_ids(cursor)
        if not row:
            raise ValueError(
                f"Cuenta no encontrada (account_ref={self._account_ref!r}) — creala en fin_accounts primero"
            )
        account_id, bank_id = row
        raw_rows = self._parse_rows()
        stats["rows_found"] = len(raw_rows)
        if not raw_rows:
            cursor.close()
            return stats
        file_hash = self._file_hash()
        cursor.execute(
            "SELECT id FROM fin_statement_imports WHERE file_hash = %s AND section = %s",
            (file_hash, self.SECTION_NAME),
        )
        if cursor.fetchone():
            _logger.info("  Archivo ya importado (hash duplicado) — omitido")
            cursor.close()
            return stats
        cursor.execute(
            "INSERT INTO fin_statement_imports (account_id, bank_id, filename, file_hash, section, status) "
            "VALUES (%s,%s,%s,%s,%s,'pending')",
            (account_id, bank_id, os.path.basename(self._pdf_path), file_hash, self.SECTION_NAME),
        )
        import_id = cursor.lastrowid
        txns = _dedup_raw_descriptions(self._build_transactions(raw_rows, account_id, import_id, cursor))
        for txn in txns:
            try:
                if _is_near_duplicate(cursor, txn):
                    stats["skipped"] += 1
                    continue
                cursor.execute(_INSERT_TXN_SQL, txn)
                if cursor.rowcount:
                    stats["inserted"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as e:
                _logger.error(f"  {type(self).__name__} insert error: {e}")
                stats["errors"] += 1
        cursor.execute(
            "UPDATE fin_statement_imports SET status='processed',row_count=%s,processed_count=%s,"
            "period_from=(SELECT MIN(date) FROM fin_transactions WHERE import_id=%s),"
            "period_to=(SELECT MAX(date) FROM fin_transactions WHERE import_id=%s) WHERE id=%s",
            (stats["rows_found"], stats["inserted"], import_id, import_id, import_id),
        )
        conn.commit()
        cursor.close()
        return stats


# ─────────────────────────────────────────────────────────────────────────────
# Parser: Banesco — moneda nacional (VES)
# ─────────────────────────────────────────────────────────────────────────────


class BanescoVes(BdvVes):
    """
    Parser para extractos de Banesco — cuenta corriente en bolívares (VES).

    La hoja 1 es apaisada y trae a la izquierda el titular y el RESUMEN; las hojas de continuación no, así que
    el detalle queda corrido ~388 pt. Las columnas no se fijan en x absoluta: se miden desde la palabra "DIA"
    de la cabecera del detalle (la que está en la línea de "CARGOS"), y la hoja se recorta ahí para que las
    líneas del resumen no se mezclen con las filas.

    Columnas relativas a x("DIA"):
      x0 < 13         → Día
      13 ≤ x0 < 56    → Referencia
      resto sin monto → Concepto
      x1 < 230        → Cargos  (montos alineados a la derecha → se clasifican por x1)
      230 ≤ x1 < 300  → Abonos
      x1 ≥ 300        → Saldo   (se omite)

    La fila solo trae el día: mes y año salen de "Período: MM-YYYY" de la hoja 1.
    Carga, tasa VES/USDT y reglas se heredan de BdvVes.
    """

    SECTION_NAME = "banesco_cc"

    _RE_MONTO = re.compile(r"-?[\d.]+,\d{2}")
    _DX_REF = 13
    _DX_CONCEPTO = 56
    _DX1_CARGO = 230
    _DX1_ABONO = 300

    def _parse_rows(self) -> list[dict]:
        def x_encabezado(page):
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            tops_cargos = [w["top"] for w in words if w["text"] == "CARGOS"]
            for w in words:
                if w["text"] == "DIA" and any(abs(w["top"] - t) < 2 for t in tops_cargos):
                    return w["x0"]
            return None

        rows = []
        with pdfplumber.open(self._pdf_path) as pdf:
            m = re.search(r"Per[ií]odo:\s*(\d{2})-(\d{4})", pdf.pages[0].extract_text() or "")
            if not m:
                return rows
            month, year = int(m.group(1)), int(m.group(2))
            for page in pdf.pages:
                x_dia = x_encabezado(page)
                if x_dia is None:
                    continue
                detalle = page.crop((x_dia - 5, 0, page.width, page.height))
                row_map: dict[int, list] = {}
                for w in detalle.extract_words(x_tolerance=3, y_tolerance=3):
                    row_map.setdefault(round(w["top"] / 3) * 3, []).append(w)
                for top_key in sorted(row_map):
                    dia_p, ref_p, concepto_p, cargo_p, abono_p = [], [], [], [], []
                    for w in sorted(row_map[top_key], key=lambda w: w["x0"]):
                        dx, t = w["x0"] - x_dia, w["text"]
                        if dx < self._DX_REF:
                            dia_p.append(t)
                        elif dx < self._DX_CONCEPTO:
                            ref_p.append(t)
                        elif not self._RE_MONTO.fullmatch(t):
                            concepto_p.append(t)
                        elif w["x1"] - x_dia < self._DX1_CARGO:
                            cargo_p.append(t)
                        elif w["x1"] - x_dia < self._DX1_ABONO:
                            abono_p.append(t)
                    dia = " ".join(dia_p)
                    if not re.fullmatch(r"\d{1,2}", dia) or not ref_p:
                        continue
                    try:
                        txn_date = date(year, month, int(dia))
                    except ValueError:
                        continue
                    cargo = self._parse_amount(" ".join(cargo_p)) if cargo_p else Decimal("0")
                    abono = self._parse_amount(" ".join(abono_p)) if abono_p else Decimal("0")
                    if cargo:
                        txn_type, amount = "expense", cargo
                    elif abono:
                        txn_type, amount = "income", abono
                    else:
                        continue
                    rows.append(
                        {
                            "date": txn_date,
                            "type": txn_type,
                            "amount": amount,
                            "description": " ".join(concepto_p),
                            "comprobante": " ".join(ref_p),
                        }
                    )
        return rows


# ─────────────────────────────────────────────────────────────────────────────
# Adaptador Binance C2C — historial de órdenes P2P
# ─────────────────────────────────────────────────────────────────────────────

_RE_C2C_ROW = re.compile(
    r"(\d{18,20})\s+"
    r"(Buy|Sell)\s+USDT\s+"
    r"([A-Z]{3})\s+"
    r"([\d.]+)\s+"
    r"([\d.]+)\s+"
    r"([\d.]+)\s+"
    r"([\d.]+)\s+"
    r"(.+?)\s+Completed\s+"
    # Binance pasó de "26-03-28" a "2026-03-28": el siglo opcional deja "hora" siempre en yy-mm-dd
    r"(?:\d{2})?(\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"
)


class BinanceC2c:
    """
    Parsea el historial de órdenes C2C de Binance (PDF) y carga en fin_transactions.
    Representa la cuenta USDT de Binance como cuenta financiera:
      Buy  USDT ARS → income  (USDT entra) — contrapartida de Compra USDT en BBVA
      Sell USDT VES → expense (USDT sale)  — contrapartida de BINANCE P2P en BDV
      Sell USDT USD → expense (USDT sale)  — contrapartida de ingreso en Citi
    """

    SECTION_NAME = "binance_c2c"

    def __init__(self, pdf_path: str, account_ref: str, dry_run: bool = False):
        self.pdf_path = pdf_path
        self.account_ref = account_ref.strip()
        self.dry_run = dry_run
        self.file_hash = sha256_file(pdf_path)

    def _parse_rows(self) -> list[dict]:
        rows = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                for line in text.splitlines():
                    m = _RE_C2C_ROW.search(line)
                    if not m:
                        continue
                    order_id, tipo, fiat, precio_total, precio, cantidad, fee, contraparte, hora = m.groups()
                    rows.append(
                        {
                            "order_id": order_id,
                            "tipo": tipo,
                            "fiat": fiat,
                            "precio_total": float(precio_total),
                            "precio": float(precio),
                            "cantidad": float(cantidad),
                            "fee": float(fee),
                            "contraparte": contraparte.strip(),
                            "hora": hora.strip(),
                        }
                    )
        return rows

    def _build_transactions(self, rows: list[dict], account_id: int, import_id: int, cursor) -> list[dict]:
        txns = []
        for r in rows:
            try:
                fecha = datetime.strptime(r["hora"], "%y-%m-%d %H:%M:%S").date()
            except ValueError:
                _logger.warning(f"  [BinanceC2c] Fecha inválida: {r['hora']} — omitida")
                continue
            fiat = r["fiat"]
            if r["tipo"] == "Buy":
                usdt_amount = round(r["cantidad"] - r["fee"], 8)
                txn_type = "income"
            else:
                usdt_amount = round(r["cantidad"] + r["fee"], 8)
                txn_type = "expense"
            raw_desc = f"C2C {r['tipo'].upper()} {fiat}"
            description = f"C2C {r['tipo']} USDT/{fiat} — {r['contraparte']}"
            cat_id, classified_by = apply_rules(raw_desc, cursor)
            txns.append(
                {
                    "date": fecha,
                    "type": txn_type,
                    "amount": Decimal(str(usdt_amount)),
                    "currency": "USDT",
                    "amount_usdt": Decimal(str(usdt_amount)),
                    "category_id": cat_id,
                    "account_id": account_id,
                    "description": description,
                    "raw_description": raw_desc,
                    "raw_description_detail": f"@{r['precio']} {fiat}/{r['precio_total']:.0f}",
                    "comprobante": r["order_id"],
                    "import_id": import_id,
                    "classified_by": classified_by,
                    "installment_current": None,
                    "installment_total": None,
                }
            )
        return txns

    def preview(self) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        rows = self._parse_rows()
        stats["rows_found"] = len(rows)
        for r in rows:
            try:
                fecha = datetime.strptime(r["hora"], "%y-%m-%d %H:%M:%S").date()
            except ValueError:
                stats["errors"] += 1
                continue
            fiat = r["fiat"]
            fee = r["fee"]
            usdt = round(r["cantidad"] - fee if r["tipo"] == "Buy" else r["cantidad"] + fee, 8)
            _logger.info(
                f"  {fecha} | {r['tipo']:4s} USDT/{fiat} | {usdt:>9.4f} USDT | "
                f"@{r['precio']:,.2f} | {r['contraparte'][:30]}"
            )
            stats["inserted"] += 1
        return stats

    def load(self, conn) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, bank_id FROM fin_accounts WHERE account_ref=%s AND is_active=1",
            (self.account_ref,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Cuenta no encontrada: account_ref='{self.account_ref}'")
        account_id, bank_id = row
        raw_rows = self._parse_rows()
        stats["rows_found"] = len(raw_rows)
        if not raw_rows:
            cursor.close()
            return stats
        cursor.execute(
            "SELECT id FROM fin_statement_imports WHERE file_hash=%s AND section=%s",
            (self.file_hash, self.SECTION_NAME),
        )
        if cursor.fetchone():
            _logger.warning("  PDF ya importado — omitido")
            cursor.close()
            return stats
        cursor.execute(
            "INSERT INTO fin_statement_imports (account_id,bank_id,filename,file_hash,section,status) "
            "VALUES (%s,%s,%s,%s,%s,'pending')",
            (account_id, bank_id, os.path.basename(self.pdf_path), self.file_hash, self.SECTION_NAME),
        )
        conn.commit()
        import_id = cursor.lastrowid
        txns = _dedup_raw_descriptions(self._build_transactions(raw_rows, account_id, import_id, cursor))
        for txn in txns:
            try:
                cursor.execute(
                    "SELECT id FROM fin_transactions WHERE comprobante=%s AND account_id=%s",
                    (txn["comprobante"], account_id),
                )
                if cursor.fetchone():
                    stats["skipped"] += 1
                    continue
                cursor.execute(_INSERT_TXN_SQL, txn)
                stats["inserted"] += 1
            except Exception as e:
                _logger.error(f"  [BinanceC2c] Error txn {txn.get('comprobante')}: {e}")
                stats["errors"] += 1
        conn.commit()
        cursor.execute(
            "UPDATE fin_statement_imports SET status='processed',row_count=%s,processed_count=%s,skipped_count=%s "
            "WHERE id=%s",
            (stats["rows_found"], stats["inserted"], stats["skipped"], import_id),
        )
        conn.commit()
        cursor.close()
        months = {(t["date"].year, t["date"].month) for t in txns}
        for year, month in months:
            FinanceScreen().sync_binance_investment(year, month)
        return stats


# ─────────────────────────────────────────────────────────────────────────────
# Carga por API de Binance — compartida por C2C y Pay
# ─────────────────────────────────────────────────────────────────────────────


def _filtrar_nuevas(cursor, account_id: int, rows: list[dict], id_field: str) -> list[dict]:
    """Filas cuyo comprobante todavía no está en la cuenta. Va antes de clasificar: apply_rules suma hit_count."""
    if not rows:
        return []
    ids = [str(r[id_field]) for r in rows]
    marcas = ",".join(["%s"] * len(ids))
    cursor.execute(
        f"SELECT comprobante FROM fin_transactions WHERE account_id=%s AND comprobante IN ({marcas})",
        (account_id, *ids),
    )
    existentes = {c for (c,) in cursor.fetchall()}
    return [r for r in rows if str(r[id_field]) not in existentes]


def _load_api_rows(conn, adapter, account_ref: str, rows: list[dict], id_field: str, filename: str) -> dict:
    """
    Carga filas traídas por API. A diferencia de un PDF, la misma ventana se vuelve a consultar todos los días:
    el import se registra solo si hay comprobantes nuevos, con el hash de esos comprobantes (no hay archivo).
    Si una corrida anterior registró el import y cortó antes de insertar, el mismo hash lo reutiliza.
    """
    stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": len(rows)}
    cursor = conn.cursor()
    cursor.execute("SELECT id, bank_id FROM fin_accounts WHERE account_ref=%s AND is_active=1", (account_ref,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        raise ValueError(f"Cuenta no encontrada: account_ref='{account_ref}'")
    account_id, bank_id = row
    nuevas = _filtrar_nuevas(cursor, account_id, rows, id_field)
    stats["skipped"] = len(rows) - len(nuevas)
    if not nuevas:
        cursor.close()
        return stats
    file_hash = hashlib.sha256(",".join(sorted(str(r[id_field]) for r in nuevas)).encode()).hexdigest()
    cursor.execute(
        "SELECT id FROM fin_statement_imports WHERE file_hash=%s AND section=%s", (file_hash, adapter.SECTION_NAME)
    )
    previo = cursor.fetchone()
    if previo:
        import_id = previo[0]
    else:
        cursor.execute(
            "INSERT INTO fin_statement_imports (account_id,bank_id,filename,file_hash,section,status) "
            "VALUES (%s,%s,%s,%s,%s,'pending')",
            (account_id, bank_id, filename, file_hash, adapter.SECTION_NAME),
        )
        conn.commit()
        import_id = cursor.lastrowid
    txns = _dedup_raw_descriptions(adapter._build_transactions(nuevas, account_id, import_id, cursor))
    for txn in txns:
        try:
            cursor.execute(_INSERT_TXN_SQL, txn)
            if cursor.rowcount:
                stats["inserted"] += 1
            else:
                # INSERT IGNORE: el índice único (cuenta/fecha/importe/descripción) la descartó sin error
                _logger.warning(f"  [{adapter.SECTION_NAME}] Descartada por índice único: {txn['comprobante']}")
                stats["errors"] += 1
        except Exception as e:
            _logger.error(f"  [{adapter.SECTION_NAME}] Error txn {txn.get('comprobante')}: {e}")
            stats["errors"] += 1
    conn.commit()
    cursor.execute(
        "UPDATE fin_statement_imports SET status='processed',row_count=%s,processed_count=%s,skipped_count=%s "
        "WHERE id=%s",
        (stats["rows_found"], stats["inserted"], stats["skipped"], import_id),
    )
    conn.commit()
    cursor.close()
    for year, month in {(t["date"].year, t["date"].month) for t in txns}:
        FinanceScreen().sync_binance_investment(year, month)
    return stats


class BinanceC2cApi(BinanceC2c):
    """
    Las mismas órdenes C2C del PDF, traídas de la API. orderNumber es el comprobante del PDF, así que las dos
    fuentes se deduplican entre sí; hereda _build_transactions para que ambas carguen igual.

    Uso:
        adapter = BinanceC2cApi(date_from=date(2026,9,1), date_to=date(2026,9,13))
        stats = adapter.load(conn)
    """

    ACCOUNT_REF = "BINANCE-USDT"

    def __init__(self, date_from: date, date_to: date, dry_run: bool = False):
        self.account_ref = self.ACCOUNT_REF
        self.date_from = date_from
        self.date_to = date_to
        self.dry_run = dry_run
        self._client = BinanceClient(vehiculo="Crypto")

    def load(self, conn) -> dict:
        filename = f"API {self.date_from}_{self.date_to}"
        return _load_api_rows(conn, self, self.ACCOUNT_REF, self._parse_rows(), "order_id", filename)

    def _parse_rows(self) -> list[dict]:
        start_ms = int(datetime.combine(self.date_from, datetime.min.time()).timestamp() * 1000)
        end_ms = int(datetime.combine(self.date_to, datetime.max.time()).timestamp() * 1000)
        return [
            {
                "order_id": str(o["orderNumber"]),
                "tipo": o["tradeType"].capitalize(),
                "fiat": o["fiat"],
                "precio_total": float(o["totalPrice"]),
                "precio": float(o["unitPrice"]),
                "cantidad": float(o["amount"]),
                "fee": float(o["takerCommission"]),
                "contraparte": (o.get("counterPartNickName") or "").strip(),
                # hora local, como la trae el PDF
                "hora": datetime.fromtimestamp(o["createTime"] / 1000).strftime("%y-%m-%d %H:%M:%S"),
            }
            for o in self._client.fetch_c2c_orders(start_ms, end_ms)
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Adaptador Binance Pay — remesas vía Binance Pay API
# ─────────────────────────────────────────────────────────────────────────────


class BinancePay:
    """
    Carga transacciones salientes de Binance Pay (remesas) en fin_transactions.
    Fuente: API /sapi/v1/pay/transactions via BinanceClient.fetch_pay_transactions().
    Solo procesa pagos negativos (USDT que sale de la cuenta).
    Dedup por comprobante = transactionId.

    Uso (sin PDF, recibe rango de fechas):
        adapter = BinancePay(date_from=date(2026,1,1), date_to=date(2026,3,31))
        stats = adapter.load(conn)
    """

    SECTION_NAME = "binance_pay"
    ACCOUNT_REF = "BINANCE-USDT"

    def __init__(self, date_from: date, date_to: date, dry_run: bool = False):
        self.date_from = date_from
        self.date_to = date_to
        self.dry_run = dry_run
        self._client = BinanceClient(vehiculo="Crypto")

    def _fetch_raw(self) -> list[dict]:
        start_ms = int(datetime.combine(self.date_from, datetime.min.time()).timestamp() * 1000)
        end_ms = int(datetime.combine(self.date_to, datetime.max.time()).timestamp() * 1000)
        return self._client.fetch_pay_transactions(start_ms, end_ms)

    def _build_transactions(self, raw: list[dict], account_id: int, import_id: int, cursor) -> list[dict]:
        txns = []
        for item in raw:
            try:
                amount = float(item.get("amount", "0"))
            except (ValueError, TypeError):
                continue
            if amount >= 0:
                continue  # solo salidas
            usdt_amount = abs(amount)
            ts = item.get("transactionTime", 0)
            fecha = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date()
            transaction_id = item.get("transactionId", "")
            recv = item.get("receiverInfo") or {}
            email = recv.get("email", "")
            phone = recv.get("phoneNumber", "")
            contraparte = email or phone or recv.get("name", "?")
            raw_desc = f"BINANCE PAY {contraparte}"
            description = f"Binance Pay → {contraparte}"
            cat_id, classified_by = apply_rules(raw_desc, cursor)
            txns.append(
                {
                    "date": fecha,
                    "type": "expense",
                    "amount": Decimal(str(round(usdt_amount, 8))),
                    "currency": "USDT",
                    "amount_usdt": Decimal(str(round(usdt_amount, 8))),
                    "category_id": cat_id,
                    "account_id": account_id,
                    "description": description,
                    "raw_description": raw_desc,
                    "raw_description_detail": "",
                    "comprobante": transaction_id,
                    "import_id": import_id,
                    "classified_by": classified_by,
                    "installment_current": None,
                    "installment_total": None,
                }
            )
        return txns

    def preview(self) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        raw = self._fetch_raw()
        outgoing = [r for r in raw if float(r.get("amount", "0")) < 0]
        stats["rows_found"] = len(outgoing)
        for item in outgoing:
            ts = item.get("transactionTime", 0)
            fecha = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date()
            usdt = abs(float(item.get("amount", "0")))
            recv = item.get("receiverInfo") or {}
            contraparte = recv.get("email") or recv.get("phoneNumber") or recv.get("name", "?")
            _logger.info(f"  {fecha} | PAY {usdt:>8.4f} USDT → {contraparte}")
            stats["inserted"] += 1
        return stats

    def load(self, conn) -> dict:
        outgoing = [r for r in self._fetch_raw() if float(r.get("amount", "0")) < 0]
        filename = f"{self.date_from}_{self.date_to}"
        return _load_api_rows(conn, self, self.ACCOUNT_REF, outgoing, "transactionId", filename)


# ─────────────────────────────────────────────────────────────────────────────
# Mapa de adaptadores
# ─────────────────────────────────────────────────────────────────────────────

ADAPTER_MAP = {
    "bbva_tc": BbvaArTarjeta,
    "bbva_cuenta": BbvaArCuenta,
    "bbva_ahorro": BbvaArAhorro,
    "santander": SantanderAr,
    "santander_tc_resumen": SantanderArTarjetaResumen,
    "citibank_us": CitibankUs,
    "bdv_ves": BdvVes,
    "banesco_ves": BanescoVes,
    "binance_c2c": BinanceC2c,
}


# ─────────────────────────────────────────────────────────────────────────────
# Lógica de escaneo automático de carpeta
# ─────────────────────────────────────────────────────────────────────────────


def detect_adapter(pdf_path: str) -> tuple[str, str | None] | None:
    """Detecta adaptador y account_ref por contenido del PDF. Devuelve (key, ref) o None."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            words = []
            for page in pdf.pages[:2]:
                words.extend(w["text"] for w in page.extract_words(x_tolerance=3, y_tolerance=3))
                if len(words) >= 200:
                    break
            text = " ".join(words[:200])
    except Exception as e:
        _logger.error(f"  Error leyendo PDF: {e}")
        return None
    for keyword, adapter_key, account_ref in DETECTION_RULES:
        if keyword in text:
            return adapter_key, account_ref
    return None


def process_pdf(pdf_path: str) -> bool:
    """Detecta banco, carga en BD y devuelve True si OK (incluyendo ya-importado); False si no extrajo filas."""
    filename = os.path.basename(pdf_path)
    _logger.info(f"── Procesando: {filename}")
    detected = detect_adapter(pdf_path)
    if not detected:
        _logger.warning(f"  Banco no reconocido: {filename}")
        return False
    adapter_key, account_ref = detected
    _logger.info(f"  Detectado: {adapter_key}  ref={account_ref or 'multi-sección'}")
    AdapterClass = ADAPTER_MAP.get(adapter_key)
    if not AdapterClass:
        _logger.error(f"  Adaptador '{adapter_key}' no encontrado")
        return False
    try:
        _multi_section = AdapterClass in (SantanderAr, CitibankUs)
        adapter = (
            AdapterClass(pdf_path=pdf_path)
            if _multi_section
            else AdapterClass(pdf_path=pdf_path, account_ref=account_ref)
        )
        conn = connect(**BDsystem.DB_CONFIG)
        stats = adapter.load(conn)
        conn.close()
        _logger.info(
            f"  {stats['rows_found']} filas | {stats['inserted']} ins | "
            f"{stats['skipped']} skip | {stats['errors']} err"
        )
        if not stats["rows_found"]:
            _logger.warning(f"  Reconocido pero sin filas extraídas → desconocidos: {filename}")
            return False
        return True
    except Error as e:
        _logger.error(f"  Error BD: {e}")
        return False
    except Exception as e:
        _logger.error(f"  Error: {e}")
        return False


def scan_extractos() -> str:
    """Escanea EXTRACTOS_DIR, procesa PDFs y los elimina.
    - Reconocidos (importados o duplicado interno): se eliminan.
    - No reconocidos o sin filas extraídas: se mueven a desconocidos/ para revisión.
    La validación de duplicados es interna vía SHA-256 en BD.
    """
    if not os.path.isdir(EXTRACTOS_DIR):
        return f"Carpeta no encontrada: {EXTRACTOS_DIR}"
    pdfs = sorted(
        os.path.join(EXTRACTOS_DIR, f)
        for f in os.listdir(EXTRACTOS_DIR)
        if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(EXTRACTOS_DIR, f))
    )
    if not pdfs:
        return "Sin PDFs pendientes"
    ok_count = 0
    fail_count = 0
    for pdf_path in pdfs:
        ok = process_pdf(pdf_path)
        if ok:
            os.remove(pdf_path)
            ok_count += 1
        else:
            os.makedirs(DESCONOCIDOS_DIR, exist_ok=True)
            dest_file = os.path.join(DESCONOCIDOS_DIR, os.path.basename(pdf_path))
            if os.path.exists(dest_file):
                base, ext = os.path.splitext(os.path.basename(pdf_path))
                dest_file = os.path.join(DESCONOCIDOS_DIR, f"{base}_{int(time.time())}{ext}")
            shutil.move(pdf_path, dest_file)
            fail_count += 1
    return f"Procesados: {ok_count} eliminados, {fail_count} a desconocidos de {len(pdfs)} PDFs"


def _binance_api_desde(conn, section: str, hoy: date) -> date:
    """3 días antes del último movimiento cargado de la sección; 90 días atrás si todavía no hay ninguno.
    La fila sintética BINANCE-INV no tiene import_id: el JOIN la deja afuera y no adelanta la ventana."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT MAX(t.date) FROM fin_transactions t JOIN fin_statement_imports i ON i.id = t.import_id "
        "WHERE i.section = %s",
        (section,),
    )
    ultima = cursor.fetchone()[0]
    cursor.close()
    return ultima - timedelta(days=3) if ultima else hoy - timedelta(days=90)


def sync_binance_api() -> str:
    """
    Carga C2C y Pay de Binance por API, sin descargar el PDF de C2C.
    Cada fuente arranca 3 días antes de su último movimiento (cubre cortes y el desfase UTC/hora local);
    lo ya cargado lo descarta el comprobante. Una fuente que falla no frena a la otra.
    """
    hoy = date.today()
    resultados = []
    conn = connect(**BDsystem.DB_CONFIG)
    try:
        for adapter_cls in (BinanceC2cApi, BinancePay):
            try:
                desde = _binance_api_desde(conn, adapter_cls.SECTION_NAME, hoy)
                stats = adapter_cls(date_from=desde, date_to=hoy).load(conn)
                resultados.append(
                    f"{adapter_cls.SECTION_NAME} desde {desde}: {stats['inserted']} nuevas, "
                    f"{stats['skipped']} ya cargadas, {stats['errors']} err"
                )
            except Exception as e:
                conn.rollback()
                _logger.error(f"  sync_binance_api {adapter_cls.SECTION_NAME}: {e}")
                resultados.append(f"{adapter_cls.SECTION_NAME}: ERROR {e}")
    finally:
        conn.close()
    return " | ".join(resultados)
