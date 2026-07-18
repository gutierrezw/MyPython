"""
Class_Analisis.py - Módulo Unificado de Análisis por Vehículo

Arquitectura basada en herencia:
- AnalisisBase: Clase base con ventana estándar y helpers
- AnalisisFCI: Análisis específico para Fondos Comunes de Inversión
- AnalisisCrypto: Análisis específico para Criptomonedas
- AnalisisStock: Análisis específico para Acciones

Uso:
    from Class_Analisis import AnalisisFCI, AnalisisCrypto, AnalisisStock
    analisis = AnalisisFCI(master, info, repositorio, colors)
    analisis.mostrar_ventana()
"""

import json

from Modulos_python import (
    tk,
    ttk,
    datetime,
    pd,
    np,
    re,
    mpatches,
    mdates,
    traceback,
    logging,
)
from Modulos_Mysql import BDsystem, PlanInversion, RepositorioOportunidadesBuySell, MarketScreen
from Modulos_Comunes import performa_asset, detalle_book, read_csv_insert_diaria, proceso_update_performance
from Modulos_Utilitarios import vehiculo_parm, margin_risk_status
from Modulos_python import threading, time, yf
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

_logger = logging.getLogger("Analisis")


class AnalisisBase:
    """
    Clase base para análisis de vehículos de inversión.
    Provee ventana estándar con estilo DarkCyan y helpers para crear UI.
    """

    # Variable de clase para controlar ventana única
    _ventana_activa = None

    # Colores estilo Variables de Entorno
    BG_COLOR = "DarkCyan"
    CG_COLOR = "black"
    ENTRY_BG = "#244D03"  # LightGreen (más claro para mejor lectura)
    LABEL_FG = "yellow"
    VALUE_FG = "black"  # Negro para mejor lectura sobre fondo verde

    def __init__(self, master, info, repositorio, colors, vehiculo, summary=None, account=None, positions=None):
        self.master = master
        self.info = info
        self.repositorio = repositorio
        self.colors = colors
        self.vehiculo = vehiculo
        self.summary = summary or {}
        self.account = account
        self.positions = positions or []
        self.top = 3

        # DataFrames para análisis
        self.df_lotes = pd.DataFrame()

    def mostrar_ventana(self):
        """Muestra ventana de análisis con estilo DarkCyan"""

        def eexit():
            # Desvincular mousewheel antes de cerrar
            self.canvas.unbind_all("<MouseWheel>")
            self.analisis_window.destroy()
            AnalisisBase._ventana_activa = None

        try:
            # Cerrar ventana anterior si existe
            if AnalisisBase._ventana_activa is not None:
                try:
                    AnalisisBase._ventana_activa.destroy()
                except:
                    pass
                AnalisisBase._ventana_activa = None

            # Crear ventana
            self.analisis_window = tk.Toplevel(self.master)
            AnalisisBase._ventana_activa = self.analisis_window
            self.analisis_window.title(f"Analisis {self.vehiculo}")

            screen_width = self.analisis_window.winfo_screenwidth()
            window_width, window_height = 620, 750
            x_position = screen_width - window_width - 10
            self.analisis_window.geometry(f"{window_width}x{window_height}+{x_position}+200")

            self.analisis_window.resizable(False, False)
            self.analisis_window.config(bg=self.BG_COLOR)
            self.analisis_window.protocol("WM_DELETE_WINDOW", eexit)

            # Canvas con scroll
            self.canvas = tk.Canvas(self.analisis_window, bg=self.BG_COLOR, highlightthickness=0)
            scrollbar = ttk.Scrollbar(self.analisis_window, orient="vertical", command=self.canvas.yview)
            self.scrollable_frame = tk.Frame(self.canvas, bg=self.BG_COLOR)

            self.scrollable_frame.bind(
                "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            )
            self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
            self.canvas.configure(yscrollcommand=scrollbar.set)

            def on_mousewheel(event):
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

            self.canvas.bind_all("<MouseWheel>", on_mousewheel)
            self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Poblar contenido específico del vehículo
            self._poblar_contenido(self.scrollable_frame)

            # Botón cerrar al final
            tk.Button(
                self.scrollable_frame,
                text="Cancel",
                width=10,
                bg="gray",
                fg="white",
                command=eexit,
            ).grid(row=999, column=0, columnspan=2, pady=20)
        except Exception as e:
            _logger.error(f"[AnalisisBase.mostrar_ventana]: {e}")
            traceback.print_exc()

    def _poblar_contenido(self, frame):
        """
        Método abstracto: cada subclase debe implementar su contenido específico.

        Args:
            frame: Frame scrollable donde agregar widgets
        """
        raise NotImplementedError("Las subclases deben implementar _poblar_contenido()")

    def crear_seccion(self, parent, titulo, row):
        """
        Crea un título de sección con estilo.

        Args:
            parent: Frame padre
            titulo: Texto del título
            row: Fila donde ubicar

        Returns:
            int: Siguiente fila disponible
        """
        tk.Label(
            parent,
            text=f"  {titulo}",
            bg=self.BG_COLOR,
            fg=self.LABEL_FG,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=(15, 5))
        return row + 1

    def crear_campo(self, parent, label, valor, row, width=45, fg_valor=None, bg_valor=None):
        """
        Crea un campo label + entry readonly.

        Args:
            parent: Frame padre
            label: Texto del label
            valor: Valor a mostrar
            row: Fila donde ubicar
            width: Ancho del entry
            fg_valor: Color del texto del valor (opcional)

        Returns:
            int: Siguiente fila disponible
        """
        fg_valor = fg_valor or self.VALUE_FG
        bg_valor = bg_valor or self.BG_COLOR
        tk.Label(
            parent,
            text=label,
            bg=bg_valor,
            font=("Segoe UI", 9),
            anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=10, pady=3)

        entry = tk.Entry(parent, width=width, bg=self.ENTRY_BG, fg=fg_valor, font=("Segoe UI", 9), relief="flat")
        entry.insert(0, str(valor))
        entry.config(state="readonly")
        entry.grid(row=row, column=1, padx=10, pady=3, sticky="w")
        return row + 1

    @staticmethod
    def _sin_outliers(df, col):
        """Excluye outliers estadísticos por IQR×3 en la columna dada."""
        if df.empty or col not in df.columns or len(df) < 3:
            return df
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return df
        return df[(df[col] >= q1 - 3 * iqr) & (df[col] <= q3 + 3 * iqr)]

    def obtener_color_ganancia(self, valor):
        """Retorna color según ganancia/pérdida"""
        if valor > 0:
            return "green"
        elif valor < 0:
            return "red"
        return self.VALUE_FG

    def crear_grafico_vs_indice(self, parent, row):
        """
        Gráfico de líneas: rendimiento acumulado de la cartera vs índice de referencia.
        Recalcula desde diaria_performance (value + gyp_dia + dividends / costo_base por día)
        en lugar de usar performa_inversion precalculada.
        Combina todas las cuentas FCI del vehículo (BBVA + Santander).
        """
        try:
            symbol, rtn_index, cum_index, index_ref = vehiculo_parm(vehiculo=self.vehiculo)

            # Pipeline unificado: diaria_performance → normalización → merge índice
            df_plot = performa_asset(vehiculo=self.vehiculo, tipo=self.vehiculo)
            if df_plot is None or df_plot.empty or cum_index not in df_plot.columns:
                return row

            # Convertir a porcentaje (dataset completo)
            df_plot["cartera_pct"] = df_plot["CumPort"] * 100
            df_plot["indice_pct"] = df_plot[cum_index] * 100

            # --- Figura interactiva con botones de intervalo ---
            INTERVALOS = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "5y": 1825}

            fg = Figure(figsize=(5.4, 2.8), dpi=100)
            fg.patch.set_facecolor(self.CG_COLOR)
            fg.subplots_adjust(left=0.05, right=0.90, top=0.85, bottom=0.20)

            frame_g = tk.Frame(parent, bg=self.CG_COLOR)
            frame_g.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

            canvas = FigureCanvasTkAgg(fg, master=frame_g)
            canvas.get_tk_widget().pack(fill="x", expand=True)

            sin_benchmark = self.vehiculo == "BBVA.ARS"

            def _draw(dias):
                """Filtra df_plot al período y redibuja."""
                fecha_desde = df_plot.index.max() - pd.Timedelta(days=dias)
                df = df_plot[df_plot.index >= fecha_desde].copy()
                if df.empty:
                    return

                df["cartera_pct"] = (df["CumPort"] - df["CumPort"].iloc[0]) * 100
                last_c = float(df["cartera_pct"].iloc[-1])

                fg.clear()
                ax = fg.add_subplot(111)
                ax.set_facecolor(self.CG_COLOR)

                dates = df.index
                cart = df["cartera_pct"].values

                if sin_benchmark:
                    c_line = "#2ecc71" if last_c >= 0 else "#e74c3c"
                    ax.fill_between(dates, cart, 0, where=(cart >= 0), alpha=0.15, color="#2ecc71", interpolate=True)
                    ax.fill_between(dates, cart, 0, where=(cart < 0), alpha=0.15, color="#e74c3c", interpolate=True)
                    ax.plot(dates, cart, color=c_line, linewidth=1.2)
                    p_legend = [mpatches.Patch(label=f"Cartera ({last_c:+.1f}%)", color=c_line)]
                    titulo = f"Performance {self.vehiculo}"
                else:
                    df["indice_pct"] = (df[cum_index] - df[cum_index].iloc[0]) * 100
                    last_i = float(df["indice_pct"].iloc[-1])
                    alpha = last_c - last_i
                    c_alpha = "#2ecc71" if alpha >= 0 else "#e74c3c"
                    indx = df["indice_pct"].values
                    ax.fill_between(dates, cart, indx, where=(cart >= indx), alpha=0.18, color="#2ecc71", interpolate=True)
                    ax.fill_between(dates, cart, indx, where=(cart < indx), alpha=0.18, color="#e74c3c", interpolate=True)
                    ax.plot(dates, cart, color="#27ae60", linewidth=1.2)
                    ax.plot(dates, indx, color="#3498db", linewidth=1.2, linestyle="--")
                    ax.annotate(
                        f"Alpha: {alpha:+.1f}%",
                        xy=(0.02, 0.93),
                        xycoords="axes fraction",
                        fontsize=7,
                        color=c_alpha,
                        fontweight="bold",
                    )
                    p_legend = [
                        mpatches.Patch(label=f"Cartera ({last_c:+.1f}%)", color="#27ae60"),
                        mpatches.Patch(label=f"{symbol} ({last_i:+.1f}%)", color="#3498db"),
                    ]
                    titulo = f"Cartera vs {symbol}"

                ax.axhline(y=0, color="gray", linewidth=0.5)
                ax.set_ylabel("Rend. Acum. (%)", fontsize=7, color="white")
                ax.yaxis.set_label_position("right")
                ax.yaxis.tick_right()
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
                ax.tick_params(axis="x", rotation=45)
                ax.tick_params(colors="white", labelsize=7)
                ax.grid(True, alpha=0.3, color="gray")
                ax.spines[["top", "left"]].set_visible(False)
                ax.spines["bottom"].set_visible(True)
                ax.spines["right"].set_visible(True)
                for spine in ax.spines.values():
                    spine.set_color("gray")

                fg.legend(
                    handles=p_legend,
                    loc="outside upper left",
                    fontsize=5,
                    facecolor="white",
                    labelcolor="black",
                    framealpha=1.0,
                )
                _DIAS_LABEL = {30: "1m", 90: "3m", 180: "6m", 365: "1y", 1825: "5y"}
                periodo = _DIAS_LABEL.get(dias, f"{dias}d")
                fg.suptitle(f"{titulo} — {periodo}", fontsize=10, color="white")
                fg.subplots_adjust(left=0.05, right=0.90, top=0.85, bottom=0.20)
                canvas.draw()

            # Botones de intervalo — mismo estilo que gráfico principal
            frame_btns = tk.Frame(frame_g, bg=self.CG_COLOR)
            frame_btns.pack(anchor="e", padx=4)
            for label, dias in INTERVALOS.items():
                d = dias
                tk.Button(
                    frame_btns,
                    text=label,
                    width=2,
                    bg=self.CG_COLOR,
                    fg=self.BG_COLOR,
                    relief=tk.FLAT,
                    command=lambda d=d: _draw(d),
                ).pack(side="left")

            # Dibujo inicial: 1 año
            _draw(90)

            return row + 1

        except Exception as e:
            _logger.error(f"[crear_grafico_vs_indice]: {e}")
            traceback.print_exc()
            return row

    def _dibujar_evolucion_ax(self, ax, df_historico, fondos_list, color_titulo):
        """Helper compartido: filtra, calcula rendimiento acumulado y dibuja sobre un eje existente."""
        df_f = df_historico[df_historico["fondo"].isin(fondos_list)].copy()
        if df_f.empty:
            return
        df_f["fecha"] = pd.to_datetime(df_f["fecha"])
        df_f = df_f.sort_values(["fondo", "fecha"])
        df_f["rendimiento_pct"] = df_f.groupby("fondo")["valorActual"].transform(lambda x: (x / x.iloc[0] - 1) * 100)
        ax.set_facecolor(self.CG_COLOR)
        p_legend = []
        for fondo in fondos_list:
            data = df_f[df_f["fondo"] == fondo]
            if not data.empty:
                (line,) = ax.plot(data["fecha"], data["rendimiento_pct"], linewidth=1.0, alpha=0.85)
                p_legend.append(mpatches.Patch(label=fondo[:28], color=line.get_color()))
        ax.axhline(y=0, color="gray", linewidth=0.5, alpha=0.5)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
        ax.set_ylabel("Rend. Acum. (%)", fontsize=6, color="white")
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()
        ax.tick_params(colors="white", labelsize=6)
        ax.tick_params(axis="x", rotation=30)
        ax.grid(True, alpha=0.3, color="gray")
        ax.spines[["top", "left"]].set_visible(False)
        ax.spines["bottom"].set_visible(True)
        ax.spines["right"].set_visible(True)
        for sp in ax.spines.values():
            sp.set_color("gray")
        return p_legend

    # Fondos que forman la banda de referencia (piso y techo)
    _BANDA_PISO = "FBA Horizonte"
    _BANDA_TECHO = "Supergestion Mix VI - Clase A"
    # Prefijos de familias de fondos disponibles en los bancos del usuario
    _FUND_PREFIXES = ("FBA", "Super")
    # Fondos de renta variable a graficar sobre la banda
    _EQUITY_FONDOS = [
        "FBA Acciones Argentinas - Clase A",
        "Superfondo Acciones - Clase A",
        "Superfondo Renta Variable - Clase A",
    ]
    _EQUITY_COLORES = ["#2ecc71", "#e74c3c", "#3498db"]

    def crear_grafico_evolucion_combinado(self, parent, df_historico, _fondos_mejores, _fondos_peores, row):
        """Un único gráfico: banda o estimador sintético + líneas renta variable. Botones Banda/Estimador + temporalidad."""
        if df_historico.empty:
            return row
        try:
            frame_g = tk.Frame(parent, bg=self.CG_COLOR)
            frame_g.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

            fg = Figure(figsize=(5.4, 3.8), dpi=100)
            fg.patch.set_facecolor(self.CG_COLOR)
            canvas = FigureCanvasTkAgg(fg, master=frame_g)
            canvas.get_tk_widget().pack(fill="x", expand=True, pady=2)

            _estado = {"modo": "banda", "dias": 180}

            def _dibujar(modo=None, dias=None):
                if modo is not None:
                    _estado["modo"] = modo
                if dias is not None:
                    _estado["dias"] = dias

                df = df_historico.copy()
                df["fecha"] = pd.to_datetime(df["fecha"])
                df = df.sort_values(["fondo", "fecha"])
                fecha_desde = pd.Timestamp.now() - pd.Timedelta(days=_estado["dias"])
                df = df[df["fecha"] >= fecha_desde]
                if df.empty:
                    return
                df["rend"] = df.groupby("fondo")["valorActual"].transform(lambda x: (x / x.iloc[0] - 1) * 100)

                def _serie(nombre):
                    s = df[df["fondo"] == nombre][["fecha", "rend"]].dropna()
                    return s["fecha"].values, s["rend"].values

                fechas_piso, vals_piso = _serie(self._BANDA_PISO)
                fechas_techo, vals_techo = _serie(self._BANDA_TECHO)
                piso_s = pd.Series(vals_piso, index=pd.to_datetime(fechas_piso))
                techo_s = pd.Series(vals_techo, index=pd.to_datetime(fechas_techo))
                idx_comun = piso_s.index.intersection(techo_s.index)
                estimador_s = ((piso_s[idx_comun] + techo_s[idx_comun]) / 2) if len(idx_comun) else pd.Series()
                fondos_equity = [f for f in self._EQUITY_FONDOS if f in df["fondo"].values]

                spread = pd.Series()
                señales_bloques = []
                if not piso_s.empty and fondos_equity:
                    eq_series = []
                    for fondo in fondos_equity:
                        fechas_e, vals_e = _serie(fondo)
                        if len(fechas_e):
                            eq_series.append(pd.Series(vals_e, index=pd.to_datetime(fechas_e)))
                    if eq_series:
                        eq_avg = pd.DataFrame(eq_series).T.sort_index().mean(axis=1)
                        common = piso_s.index.intersection(eq_avg.index)
                        if not common.empty:
                            spread = eq_avg[common] - piso_s[common]
                            bloques, prev_tipo, bloque_ini, fecha_prev = [], None, None, None
                            for fecha in spread.index:
                                s_val = spread[fecha]
                                tipo = "COMPRA" if s_val < -10 else ("CAUTELA" if s_val > 10 else None)
                                if tipo != prev_tipo:
                                    if prev_tipo and bloque_ini:
                                        bloques.append((bloque_ini, fecha_prev, prev_tipo))
                                    bloque_ini = fecha if tipo else None
                                    prev_tipo = tipo
                                if tipo:
                                    fecha_prev = fecha
                            if prev_tipo and bloque_ini:
                                bloques.append((bloque_ini, fecha_prev, prev_tipo))
                            señales_bloques = bloques

                fg.clear()
                gs = fg.add_gridspec(2, 1, height_ratios=[5, 1], hspace=0.08)
                ax = fg.add_subplot(gs[0])
                ax.set_facecolor(self.CG_COLOR)

                modo_actual = _estado["modo"]
                if modo_actual == "banda":
                    if len(idx_comun):
                        ax.fill_between(
                            idx_comun,
                            piso_s[idx_comun],
                            techo_s[idx_comun],
                            color="#f1c40f",
                            alpha=0.15,
                            zorder=1,
                            label="_banda",
                        )
                    if len(fechas_piso):
                        ax.plot(
                            fechas_piso,
                            vals_piso,
                            color="#ffffff",
                            linewidth=1.2,
                            linestyle="--",
                            alpha=0.6,
                            label=self._BANDA_PISO[:22],
                        )
                    if len(fechas_techo):
                        ax.plot(
                            fechas_techo,
                            vals_techo,
                            color="#f1c40f",
                            linewidth=1.2,
                            linestyle="--",
                            alpha=0.8,
                            label=self._BANDA_TECHO[:22],
                        )
                else:
                    if not estimador_s.empty:
                        ax.plot(
                            estimador_s.index,
                            estimador_s.values,
                            color="#f1c40f",
                            linewidth=1.8,
                            linestyle="-",
                            alpha=0.9,
                            label="Estimador (punto medio)",
                        )

                for i, fondo in enumerate(fondos_equity):
                    color = self._EQUITY_COLORES[i % len(self._EQUITY_COLORES)]
                    fechas_e, vals_e = _serie(fondo)
                    if len(fechas_e):
                        ax.plot(fechas_e, vals_e, color=color, linewidth=1.2, alpha=0.9, label=fondo[:28], zorder=3)

                ax.axhline(y=0, color="gray", linewidth=0.5, alpha=0.5)

                _señal_added = set()
                for ini, fin, tipo in señales_bloques:
                    color = "#27ae60" if tipo == "COMPRA" else "#e67e22"
                    lbl = ("▲ RV" if tipo == "COMPRA" else "▼ RF") if tipo not in _señal_added else f"_{tipo}"
                    ax.axvspan(ini, fin, color=color, alpha=0.18, zorder=0, label=lbl)
                    _señal_added.add(tipo)

                # Marcadores explícitos en puntos de quiebre (cruce del spread por 0)
                # ▼ RF en la parte superior, ▲ RV en la inferior — evita solapamiento
                if not spread.empty and len(spread) > 1:
                    sign = spread >= 0
                    cruces = sign[sign != sign.shift(1)].iloc[1:]
                    for fecha, hacia_pos in cruces.items():
                        tag = "▼ RF" if hacia_pos else "▲ RV"
                        col_tag = "#e74c3c" if hacia_pos else "#27ae60"
                        y_pos = 0.98 if hacia_pos else 0.04
                        v_align = "top" if hacia_pos else "bottom"
                        ax.axvline(x=fecha, color=col_tag, linewidth=1.0, linestyle=":", alpha=0.85, zorder=5)
                        ax.annotate(
                            tag,
                            xy=(fecha, y_pos),
                            xycoords=("data", "axes fraction"),
                            fontsize=6,
                            color=col_tag,
                            ha="center",
                            va=v_align,
                            fontweight="bold",
                        )

                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
                ax.set_ylabel("Rend. Acum. (%)", fontsize=6, color="white")
                ax.yaxis.set_label_position("right")
                ax.yaxis.tick_right()
                ax.tick_params(colors="white", labelsize=6)
                ax.tick_params(axis="x", rotation=30)
                ax.grid(True, alpha=0.3, color="gray")
                ax.spines[["top", "left"]].set_visible(False)
                ax.spines["bottom"].set_visible(True)
                ax.spines["right"].set_visible(True)
                for sp in ax.spines.values():
                    sp.set_color("gray")

                # --- Panel Rotación FCI ---
                ax2 = fg.add_subplot(gs[1])
                ax2.set_facecolor(self.CG_COLOR)
                # En modo estimador usa el punto medio como referencia del spread
                rot_ref = estimador_s if (modo_actual == "estimador" and not estimador_s.empty) else piso_s
                if not spread.empty and not rot_ref.empty:
                    common_rot = spread.index.intersection(rot_ref.index)
                    spread_rot = (
                        (spread[common_rot] - rot_ref[common_rot]) if modo_actual == "estimador" else spread[common_rot]
                    )
                    if not spread_rot.empty:
                        ventana = min(10, max(3, len(spread_rot) // 6))
                        ma_rot = spread_rot.rolling(ventana, min_periods=1).mean()
                        ax2.fill_between(
                            spread_rot.index,
                            spread_rot.values,
                            0,
                            where=(spread_rot.values >= 0),
                            color="#e74c3c",
                            alpha=0.35,
                            interpolate=True,
                        )
                        ax2.fill_between(
                            spread_rot.index,
                            spread_rot.values,
                            0,
                            where=(spread_rot.values < 0),
                            color="#27ae60",
                            alpha=0.35,
                            interpolate=True,
                        )
                        ax2.plot(ma_rot.index, ma_rot.values, color="white", linewidth=0.9, alpha=0.9)
                        ax2.axhline(0, color="#aaaaaa", linewidth=0.5)
                        ax2.set_xlim(ax.get_xlim())
                ax2.set_ylabel("Rot", fontsize=5, color="white", rotation=0, labelpad=14)
                ax2.yaxis.set_label_position("right")
                ax2.yaxis.tick_right()
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
                ax2.tick_params(colors="white", labelsize=5)
                ax2.tick_params(axis="x", rotation=30, labelsize=5)
                ax2.spines[["top", "left"]].set_visible(False)
                ax2.spines["right"].set_color("gray")
                ax2.grid(False)

                handles, labels = ax.get_legend_handles_labels()
                all_h = [h for h, l in zip(handles, labels) if not l.startswith("_")]
                all_l = [l for l in labels if not l.startswith("_")]
                if all_h:
                    fg.legend(
                        handles=all_h,
                        labels=all_l,
                        loc="outside lower left",
                        fontsize=6,
                        facecolor="white",
                        labelcolor="black",
                        framealpha=0.9,
                        ncols=2,
                    )
                _DIAS_LABEL = {30: "1m", 90: "3m", 180: "6m", 365: "1y", 1825: "5y"}
                periodo = _DIAS_LABEL.get(_estado["dias"], f"{_estado['dias']}d")
                base = "Renta Variable vs Banda" if modo_actual == "banda" else "Renta Variable vs Estimador"
                fg.suptitle(f"{base} — {periodo}", fontsize=9, color="white", y=0.98)
                fg.subplots_adjust(left=0.05, right=0.88, top=0.88, bottom=0.24)
                canvas.draw()

            INTERVALOS = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "5y": 1825}
            frame_btns = tk.Frame(frame_g, bg=self.CG_COLOR)
            frame_btns.pack(anchor="e", padx=4)
            for label, dias in INTERVALOS.items():
                d = dias
                tk.Button(
                    frame_btns,
                    text=label,
                    width=2,
                    bg=self.CG_COLOR,
                    fg=self.BG_COLOR,
                    relief=tk.FLAT,
                    command=lambda d=d: _dibujar(dias=d),
                ).pack(side="left")
            for emoji, modo in (("〰", "banda"), ("≈", "estimador")):
                m = modo
                tk.Button(
                    frame_btns,
                    text=emoji,
                    width=3,
                    bg=self.CG_COLOR,
                    fg=self.BG_COLOR,
                    relief=tk.FLAT,
                    command=lambda m=m: _dibujar(modo=m),
                ).pack(side="left")

            _dibujar(dias=180)
            return row + 1
        except Exception as e:
            _logger.error(f"[crear_grafico_evolucion_combinado]: {e}")
            traceback.print_exc()
            return row

    @staticmethod
    def margin_risk(total_position, equity, beta):
        """Riesgo de margen ajustado por beta: usage = deuda/equity, risk = usage × beta."""
        debt = max(0.0, total_position - equity)
        usage = debt / equity if equity > 0 else 0.0
        return {"usage": usage, "risk": usage * beta}

    def _fetch_historico_yfinance(self):
        """Descarga 6 meses de precios para todos los símbolos activos (batch único). Subclases pueden override."""
        try:
            symbols = [p["ticket"] for p in self.positions if float(p.get("position", 0)) > 0]
            if not symbols:
                return pd.DataFrame()
            raw = yf.download(symbols, period="6mo", auto_adjust=True, progress=False)
            if raw.empty:
                return pd.DataFrame()
            close = raw[["Close"]].rename(columns={"Close": symbols[0]}) if len(symbols) == 1 else raw["Close"]
            df = close.reset_index().melt(id_vars="Date", var_name="fondo", value_name="valorActual")
            df = df.rename(columns={"Date": "fecha"})
            return df.dropna(subset=["valorActual"])
        except Exception as e:
            _logger.error(f"_fetch_historico_yfinance(): {e}")
            return pd.DataFrame()

    def _render_grafico_evolucion(self, frame_chart, df_hist):
        """Dos gráficos separados: TOP N GANADORES y TOP N PERDEDORES con leyenda blanca fuera."""
        try:
            for w in frame_chart.winfo_children():
                w.destroy()
            if df_hist.empty or self.df_lotes.empty:
                tk.Label(
                    frame_chart,
                    text="Sin datos históricos disponibles",
                    bg=self.CG_COLOR,
                    fg="gray",
                    font=("Segoe UI", 8),
                ).pack()
                return
            top_gan = self.df_lotes.nlargest(self.top, "ganancia_pct")["symbol"].tolist()
            top_per = self.df_lotes.nsmallest(self.top, "ganancia_pct")["symbol"].tolist()
            for simbolos, titulo, color_titulo in (
                (top_gan, f"TOP {self.top} GANADORES", "#2ecc71"),
                (top_per, f"TOP {self.top} PERDEDORES", "#e67e22"),
            ):
                fg = Figure(figsize=(5.4, 2.8), dpi=100)
                fg.patch.set_facecolor(self.CG_COLOR)
                ax = fg.add_subplot(111)
                p_legend = self._dibujar_evolucion_ax(ax, df_hist, simbolos, color_titulo)
                fg.legend(
                    handles=p_legend,
                    loc="outside upper left",
                    fontsize=6,
                    facecolor="white",
                    labelcolor="black",
                    framealpha=1.0,
                )
                fg.suptitle(titulo, fontsize=9, color=color_titulo)
                fg.subplots_adjust(left=0.05, right=0.88, top=0.80, bottom=0.18)
                canvas = FigureCanvasTkAgg(fg, master=frame_chart)
                canvas.get_tk_widget().pack(fill="x", expand=True, pady=2)
                canvas.draw()
        except Exception as e:
            _logger.error(f"_render_grafico_evolucion(): {e}")

    def crear_treeview_ranking(self, parent, df, columnas, titulo, row, height=8):
        """
        Crea TreeView con fondo negro para mostrar ranking de datos.

        Args:
            parent: Frame padre
            df: DataFrame con datos
            columnas: Lista de tuplas (nombre_col_df, titulo_display, ancho)
            titulo: Título de la sección
            row: Fila donde ubicar
            height: Altura del treeview

        Returns:
            int: Siguiente fila disponible
        """
        row = self.crear_seccion(parent, titulo, row)

        if df.empty:
            row = self.crear_campo(parent, "Estado:", "Sin datos disponibles", row, fg_valor="gray")
            return row

        frame_tree = tk.Frame(parent, bg="black")
        frame_tree.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        col_ids = [c[0] for c in columnas]

        # Hereda estilo base "Treeview" de style_app() (negro, blanco, Courier 8)
        tree = ttk.Treeview(frame_tree, columns=col_ids, show="headings", height=height)

        # Tags para colorear filas por señal
        tree.tag_configure("compra", foreground="lime")
        tree.tag_configure("venta", foreground="red")
        tree.tag_configure("neutral", foreground="white")

        for col_id, col_titulo, col_ancho in columnas:
            anchor = "w" if col_id == "fondo" else "center"
            tree.heading(col_id, text=col_titulo)
            tree.column(col_id, width=col_ancho, anchor=anchor)

        cols_importe = {"valor_actual", "costo_base", "ganancia_abs"}
        for _, fila in df.iterrows():
            factor = float(fila.get("factor_cambio", 1)) if "factor_cambio" in fila.index else 1
            valores = []
            for col_id, _, _ in columnas:
                val = fila.get(col_id, "")
                if isinstance(val, float):
                    if col_id in cols_importe:
                        val = f"${val * factor:,.0f}"
                    elif "score" in col_id.lower():
                        val = f"{val:+.1f}"
                    elif "pct" in col_id.lower() or "ganancia" in col_id.lower():
                        val = f"{val:+.1f}%"
                    else:
                        val = f"{val:.2f}"
                valores.append(val)

            senal = str(fila.get("senal", fila.get("decision", ""))).upper()
            tag = "compra" if "COMPRA" in senal else ("venta" if "VENT" in senal else "neutral")
            tree.insert("", "end", values=valores, tags=(tag,))

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        return row + 1

    def crear_grafico_todas_posiciones(self, parent, df, row):
        """
        Gráfico de barras horizontales con TODAS las posiciones ordenadas de mayor a menor ganancia_pct.
        Cada barra muestra: símbolo | valor_actual | ganancia_pct.
        La altura de la figura escala con la cantidad de posiciones.
        """
        if df is None or df.empty:
            return row
        try:
            df_sorted = df.sort_values("ganancia_pct", ascending=True).copy()
            n = len(df_sorted)
            nombres = [s[:12] for s in df_sorted["symbol"]]
            valores = df_sorted["ganancia_pct"].values
            valores_usd = df_sorted["valor_actual"].values
            colores = ["#2ecc71" if v >= 0 else "#e74c3c" for v in valores]

            altura = max(2.0, n * 0.32)
            fg = Figure(figsize=(5.4, altura), dpi=100)
            fg.patch.set_facecolor(self.CG_COLOR)
            ax = fg.add_subplot(111)
            ax.set_facecolor(self.CG_COLOR)

            bars = ax.barh(nombres, valores, color=colores, height=0.65)
            ax.axvline(0, color="gray", linewidth=0.6)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:+.0f}%"))
            ax.tick_params(colors="white", labelsize=6)
            ax.spines[["top", "right"]].set_visible(False)
            for sp in ["bottom", "left"]:
                ax.spines[sp].set_color("gray")
            ax.grid(axis="x", alpha=0.2, color="gray")

            # Etiqueta: valor USD + pct fuera de la barra
            xmax = max(abs(valores)) if len(valores) else 1
            offset = xmax * 0.02
            for bar, val, usd in zip(bars, valores, valores_usd):
                ha = "left" if val >= 0 else "right"
                x = val + offset if val >= 0 else val - offset
                ax.text(
                    x,
                    bar.get_y() + bar.get_height() / 2,
                    f"${usd:,.0f}  {val:+.1f}%",
                    va="center",
                    ha=ha,
                    fontsize=5,
                    color="white",
                )

            fg.suptitle("Detalle de Posiciones", fontsize=9, color="white", y=0.99)
            fg.subplots_adjust(left=0.30, right=0.95, top=0.94, bottom=0.08)

            frame_g = tk.Frame(parent, bg=self.CG_COLOR)
            frame_g.grid(row=row, column=0, columnspan=2, padx=5, pady=3, sticky="ew")
            canvas = FigureCanvasTkAgg(fg, master=frame_g)
            canvas.get_tk_widget().pack(fill="x", expand=True)
            canvas.draw()
            return row + 1

        except Exception as e:
            _logger.error(f"[crear_grafico_todas_posiciones]: {e}")
            traceback.print_exc()
            return row


class AnalisisFCI(AnalisisBase):
    """Análisis específico para Fondos Comunes de Inversión"""

    # Parámetros de decisión
    UMBRAL_GANANCIA_MIN = 5  # % mínimo de ganancia para vender
    UMBRAL_POSICION_MAX = 90  # % cerca del máximo histórico
    DIAS_HOLDING_MIN = 7  # días mínimos de holding

    def __init__(self, master, info, repositorio, colors, vehiculo="BBVA.ARS"):
        super().__init__(master, info, repositorio, colors, vehiculo)
        self.vehiculo = vehiculo
        self.df_historico = pd.DataFrame()
        self.df_ultimo = pd.DataFrame()
        self.metricas = pd.DataFrame()

    def _poblar_contenido(self, frame):
        """Implementación específica para FCI"""
        # Cargar datos históricos primero (necesario para precios en df_ultimo)
        self.cargar_datos_historicos()
        # Cargar lotes (usa df_ultimo para precios si viene de BD)
        self.obtener_lotes_desde_info()
        # Calcular métricas y señales
        self.calcular_metricas_todos()
        self.analizar_lotes_venta()
        resumen = self.obtener_resumen()

        row = 0

        # ========== RESUMEN DE CARTERA ==========
        divisa = resumen.get("divisa", "USD")
        factor = resumen.get("factor_cambio", 1.0)
        sfx = f" ({divisa})" if divisa and str(divisa).upper() != "USD" else ""

        row = self.crear_seccion(frame, f"Resumen: {self.vehiculo}", row)
        row = self.crear_campo(frame, "Fecha:", datetime.now().strftime("%Y-%m-%d %H:%M"), row)
        row = self.crear_campo(frame, "Total Fondos:", resumen["total_activos"], row)
        if sfx:
            row = self.crear_campo(frame, "Tipo de Cambio:", f"{factor:,.2f}", row)
        row = self.crear_campo(frame, f"Costo Base{sfx}:", f"${resumen['total_costo']:,.2f}", row)
        row = self.crear_campo(frame, f"Valor Actual{sfx}:", f"${resumen['total_valor']:,.2f}", row)

        color_gan = self.obtener_color_ganancia(resumen["total_ganancia"])
        row = self.crear_campo(
            frame,
            f"Ganancia Total{sfx}:",
            f"${resumen['total_ganancia']:,.2f} ({resumen['ganancia_pct']:+.2f}%)",
            row,
            fg_valor=color_gan,
        )

        # ========== GRÁFICO BANDA + RENTA VARIABLE ==========
        row = self.crear_seccion(frame, "Renta Variable vs Banda de Referencia:", row)
        if not self.df_historico.empty:
            row = self.crear_grafico_evolucion_combinado(
                parent=frame,
                df_historico=self.df_historico,
                _fondos_mejores=[],
                _fondos_peores=[],
                row=row,
            )

        # ========== CARTERA VS ÍNDICE DE REFERENCIA ==========
        row = self.crear_seccion(frame, f"Cartera vs Índice:", row)
        row = self.crear_grafico_vs_indice(parent=frame, row=row)

        # ========== GRÁFICO FONDO INDIVIDUAL VS BANDA ==========
        row = self.crear_seccion(frame, "Fondo vs Banda de Referencia:", row)
        row_chart, fn_update_fondo = self.crear_grafico_fondo_vs_banda(parent=frame, row=row)
        row = row_chart

        # ========== SPREAD VS BANDA (tabla) ==========
        row, primera_fondo = self.crear_tabla_spread_banda(parent=frame, row=row, on_select=fn_update_fondo)
        if primera_fondo and fn_update_fondo:
            fn_update_fondo(primera_fondo)

        # ========== SEÑALES ==========
        if not self.df_lotes.empty and "decision" in self.df_lotes.columns:
            senales_df = self.df_lotes[self.df_lotes["decision"].isin(["VENDER", "COMPRAR"])].copy()
            if not senales_df.empty:
                col_senales = [
                    ("fondo", "Fondo", 155),
                    ("decision", "Señal", 75),
                    ("valor_actual", "Valor", 75),
                    ("ganancia_pct", "Gan%", 60),
                    ("costo_base", "Costo", 75),
                ]
                row = self.crear_treeview_ranking(
                    parent=frame,
                    df=senales_df,
                    columnas=col_senales,
                    titulo="Señales de Compra / Venta",
                    row=row,
                    height=min(8, len(senales_df)),
                )

    def crear_grafico_fondo_vs_banda(self, parent, row):
        """Gráfico interactivo: fondo seleccionado vs banda piso/techo. Retorna (row+1, fn_actualizar)."""
        if not hasattr(self, "df_historico") or self.df_historico.empty:
            return row, None
        try:
            frame_g = tk.Frame(parent, bg=self.CG_COLOR)
            frame_g.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

            fg = Figure(figsize=(5.4, 3.2), dpi=100)
            fg.patch.set_facecolor(self.CG_COLOR)
            canvas = FigureCanvasTkAgg(fg, master=frame_g)
            canvas.get_tk_widget().pack(fill="x", expand=True, pady=2)

            _ctx = {"fondo": None, "dias": 365, "modo": "banda"}

            def _dibujar(fondo=None, dias=None, modo=None):
                if fondo is not None:
                    _ctx["fondo"] = fondo
                if dias is not None:
                    _ctx["dias"] = dias
                if modo is not None:
                    _ctx["modo"] = modo
                nombre = _ctx["fondo"]
                if not nombre:
                    return

                df = self.df_historico.copy()
                df["fecha"] = pd.to_datetime(df["fecha"])
                df = df.sort_values(["fondo", "fecha"])
                fecha_desde = pd.Timestamp.now() - pd.Timedelta(days=_ctx["dias"])
                df = df[df["fecha"] >= fecha_desde]
                if df.empty:
                    return
                df["rend"] = df.groupby("fondo")["valorActual"].transform(lambda x: (x / x.iloc[0] - 1) * 100)

                def _serie(n):
                    s = df[df["fondo"] == n][["fecha", "rend"]].dropna()
                    return s["fecha"].values, s["rend"].values

                fechas_piso, vals_piso = _serie(self._BANDA_PISO)
                fechas_techo, vals_techo = _serie(self._BANDA_TECHO)
                fechas_fondo, vals_fondo = _serie(nombre)

                fg.clear()
                ax = fg.add_subplot(111)
                ax.set_facecolor(self.CG_COLOR)
                ax.set_frame_on(False)
                ax.grid(True, color="#333333", linewidth=0.5, alpha=0.5, zorder=0)

                piso_s = pd.Series(vals_piso, index=pd.to_datetime(fechas_piso))
                techo_s = pd.Series(vals_techo, index=pd.to_datetime(fechas_techo))
                idx_comun = piso_s.index.intersection(techo_s.index)

                modo_actual = _ctx["modo"]
                if len(idx_comun):
                    if modo_actual == "banda":
                        ax.fill_between(
                            idx_comun, piso_s[idx_comun], techo_s[idx_comun], alpha=0.35, color="#f1c40f", zorder=1
                        )
                        ax.plot(
                            idx_comun,
                            piso_s[idx_comun],
                            "--",
                            color="white",
                            linewidth=0.8,
                            alpha=0.6,
                            label=self._BANDA_PISO[:20],
                            zorder=2,
                        )
                        ax.plot(
                            idx_comun,
                            techo_s[idx_comun],
                            "-",
                            color="#f1c40f",
                            linewidth=0.8,
                            alpha=0.8,
                            label=self._BANDA_TECHO[:20],
                            zorder=2,
                        )
                    else:
                        estimador_s = (piso_s[idx_comun] + techo_s[idx_comun]) / 2
                        ax.plot(
                            idx_comun,
                            estimador_s,
                            "--",
                            color="#f1c40f",
                            linewidth=1.0,
                            alpha=0.8,
                            label="Estimador",
                            zorder=2,
                        )

                if len(fechas_fondo):
                    fd = pd.to_datetime(fechas_fondo)
                    ax.plot(fd, vals_fondo, color="#00d4ff", linewidth=1.8, label=nombre[:28], zorder=3)

                    if len(idx_comun):
                        fondo_s = pd.Series(vals_fondo, index=fd)
                        common = piso_s.index.intersection(fondo_s.index)
                        if not common.empty:
                            spread = fondo_s[common] - piso_s[common]
                            for i in range(1, len(spread)):
                                if spread.iloc[i - 1] >= 0 > spread.iloc[i]:
                                    ax.annotate(
                                        "▲",
                                        xy=(spread.index[i], piso_s[spread.index[i]]),
                                        color="#2ecc71",
                                        fontsize=7,
                                        ha="center",
                                        zorder=4,
                                    )
                                elif spread.iloc[i - 1] < 0 <= spread.iloc[i]:
                                    ax.annotate(
                                        "▼",
                                        xy=(spread.index[i], piso_s[spread.index[i]]),
                                        color="#e74c3c",
                                        fontsize=7,
                                        ha="center",
                                        zorder=4,
                                    )

                ax.set_ylabel("Rend. Acum. (%)", color="white", fontsize=7)
                ax.tick_params(colors="white", labelsize=7)
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                fg.autofmt_xdate(rotation=30, ha="right")

                handles, labels = ax.get_legend_handles_labels()
                all_h = [h for h, l in zip(handles, labels) if not l.startswith("_")]
                all_l = [l for l in labels if not l.startswith("_")]
                if all_h:
                    fg.legend(
                        handles=all_h,
                        labels=all_l,
                        loc="outside lower left",
                        fontsize=6,
                        facecolor="white",
                        labelcolor="black",
                        framealpha=0.9,
                        ncols=2,
                    )

                _DIAS_LABEL = {30: "1m", 90: "3m", 180: "6m", 365: "1y", 1825: "5y"}
                periodo = _DIAS_LABEL.get(_ctx["dias"], f"{_ctx['dias']}d")
                titulo_corto = nombre if len(nombre) <= 28 else nombre[:25] + "…"
                base = "vs Banda" if modo_actual == "banda" else "vs Estimador"
                fg.suptitle(f"{titulo_corto} {base} — {periodo}", fontsize=8, color="white", y=0.98)
                fg.subplots_adjust(left=0.09, right=0.93, top=0.88, bottom=0.24)
                canvas.draw()

            frame_btns = tk.Frame(frame_g, bg=self.CG_COLOR)
            frame_btns.pack(anchor="e", padx=4)
            for label, dias in {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "5y": 1825}.items():
                d = dias
                tk.Button(
                    frame_btns,
                    text=label,
                    width=2,
                    bg=self.CG_COLOR,
                    fg=self.BG_COLOR,
                    relief=tk.FLAT,
                    command=lambda d=d: _dibujar(dias=d),
                ).pack(side="left")
            for emoji, modo in (("〰", "banda"), ("≈", "estimador")):
                m = modo
                tk.Button(
                    frame_btns,
                    text=emoji,
                    width=3,
                    bg=self.CG_COLOR,
                    fg=self.BG_COLOR,
                    relief=tk.FLAT,
                    command=lambda m=m: _dibujar(modo=m),
                ).pack(side="left")

            return row + 1, _dibujar
        except Exception as e:
            _logger.error(f"[crear_grafico_fondo_vs_banda]: {e}")
            return row, None

    def crear_tabla_spread_banda(self, parent, row, on_select=None):
        """Tabla de spread de cada fondo vs FBA Horizonte (piso) y Supergestion Mix VI (techo).
        Retorna (row, primera_fondo) — primera_fondo es el nombre del primer fondo en la lista."""
        primera_fondo = None
        if self.df_historico.empty:
            return row, primera_fondo
        try:
            df = self.df_historico.copy()
            df["fecha"] = pd.to_datetime(df["fecha"])
            df = df.sort_values(["fondo", "fecha"]).drop_duplicates(subset=["fondo", "fecha"], keep="last")

            # normalizar todos los fondos al mismo punto de inicio
            # para que el Rend% sea comparable (se usa el máximo de los mínimos de fecha)
            fecha_inicio = df.groupby("fondo")["fecha"].min().max()
            df = df[df["fecha"] >= fecha_inicio]

            df["rend"] = df.groupby("fondo")["valorActual"].transform(lambda x: (x / x.iloc[0] - 1) * 100)

            ultima = df.groupby("fondo")["rend"].last()
            rend_piso = ultima.get(self._BANDA_PISO, None)
            rend_techo = ultima.get(self._BANDA_TECHO, None)
            if rend_piso is None or rend_techo is None:
                return row, primera_fondo

            excluir = {self._BANDA_PISO, self._BANDA_TECHO}
            fondos = [f for f in ultima.index if f not in excluir]

            filas = []
            for fondo in sorted(fondos):
                rend = ultima[fondo]
                vs_piso = round(rend - rend_piso, 1)
                vs_techo = round(rend - rend_techo, 1)
                if vs_piso < 0:
                    señal = "COMPRA"
                elif vs_techo > 0:
                    señal = "CAUTELA"
                else:
                    señal = "MANTENER"
                filas.append(
                    {"fondo": fondo, "rend": round(rend, 1), "vs_piso": vs_piso, "vs_techo": vs_techo, "senal": señal}
                )

            if not filas:
                return row, primera_fondo

            df_spread = pd.DataFrame(filas).sort_values("vs_piso").reset_index(drop=True)
            primera_fondo = df_spread.iloc[0]["fondo"]

            # ── treeview inline para poder bindear selección ──────────────────
            row = self.crear_seccion(parent, "Spread vs Banda de Referencia", row)
            col_defs = [
                ("fondo", "Fondo", 160),
                ("rend", "Rend%", 55),
                ("vs_piso", "vs Horizonte", 75),
                ("vs_techo", "vs Supergestion", 80),
                ("senal", "Señal", 70),
            ]
            frame_tree = tk.Frame(parent, bg="black")
            frame_tree.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

            col_ids = [c[0] for c in col_defs]
            tree = ttk.Treeview(frame_tree, columns=col_ids, show="headings", height=min(12, len(df_spread)))
            tree.tag_configure("compra", foreground="lime")
            tree.tag_configure("cautela", foreground="orange")
            tree.tag_configure("neutral", foreground="white")
            for col_id, col_titulo, col_ancho in col_defs:
                tree.heading(col_id, text=col_titulo)
                tree.column(col_id, width=col_ancho, anchor="w" if col_id == "fondo" else "center")

            _iid_fondo = {}
            for _, fila in df_spread.iterrows():
                senal = str(fila.get("senal", "")).upper()
                tag = "compra" if "COMPRA" in senal else ("cautela" if "CAUTELA" in senal else "neutral")
                iid = tree.insert(
                    "",
                    "end",
                    values=(fila["fondo"], fila["rend"], fila["vs_piso"], fila["vs_techo"], fila["senal"]),
                    tags=(tag,),
                )
                _iid_fondo[iid] = fila["fondo"]

            if on_select:

                def _on_tree_select(event):
                    sel = tree.selection()
                    if sel:
                        on_select(_iid_fondo.get(sel[0]))

                tree.bind("<<TreeviewSelect>>", _on_tree_select)

            sb = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=sb.set)
            tree.pack(side=tk.LEFT, fill="both", expand=True)
            sb.pack(side="right", fill="y")
            row += 1
        except Exception as e:
            _logger.error(f"[crear_tabla_spread_banda]: {e}")
        return row, primera_fondo

    def cargar_datos_historicos(self):
        """Carga historial de precios desde diaria_cnv"""
        try:
            conn = BDsystem.connect_dbase("select.diaria_cnv", False)
            cursor = conn.cursor()

            # empresa = nombre completo que coincide con diaria_cnv.fondo
            cursor.execute(
                "SELECT DISTINCT empresa, position, iactiva FROM bdinv.inversion WHERE tipoinv = %s AND empresa IS NOT NULL",
                (self.vehiculo,),
            )
            rows_inv = cursor.fetchall()
            fondos_cargar = list(
                {r[0] for r in rows_inv}
                | {self._BANDA_PISO, self._BANDA_TECHO}
                | set(self._EQUITY_FONDOS)
            )

            placeholders = ",".join(["%s"] * len(fondos_cargar))
            cursor.execute(
                f"SELECT * FROM bdinv.diaria_cnv WHERE fondo IN ({placeholders}) ORDER BY fecha DESC",
                fondos_cargar,
            )
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            cursor.close()
            conn.close()

            self.df_historico = pd.DataFrame(rows, columns=cols)
            if not self.df_historico.empty:
                self.df_historico["fecha"] = pd.to_datetime(self.df_historico["fecha"])
                ultima_fecha = self.df_historico["fecha"].max()
                self.df_ultimo = self.df_historico[self.df_historico["fecha"] == ultima_fecha].copy()

            return len(self.df_historico)
        except Exception as e:
            _logger.error(f"[cargar_datos_historicos]: {e}")
            return 0

    def obtener_lotes_desde_info(self):
        """Obtiene lotes fiscales desde query get_totales_otros_activos()"""
        try:
            lotes = []

            # Obtener datos directamente del query (ya tiene todo lo necesario)
            positions = self.repositorio.get_totales_otros_activos(vehiculo=self.vehiculo)

            if positions:
                for position in positions:
                    factor = float(position.get("factor_cambio", 1))
                    costo_base = float(position.get("total_costo_base", 0))
                    valor_actual = float(position.get("total_mercado", 0))
                    ganancia_abs = float(position.get("total_unrealized_pnl", 0))

                    # Calcular porcentaje de ganancia
                    ganancia_pct = 0
                    if costo_base > 0:
                        ganancia_pct = ((valor_actual / costo_base) - 1) * 100

                    lote = {
                        "symbol": position.get("symbol", ""),
                        "fondo": position.get("asset", ""),
                        "cantidad": float(position.get("posicion", 0)),
                        "costo_base": costo_base,
                        "valor_actual": valor_actual,
                        "ganancia_abs": ganancia_abs,
                        "ganancia_pct": ganancia_pct,
                        "ganancia_dia": float(position.get("total_ganancia_dia", 0)) * factor,
                        "divisa": str(position.get("divisa", "USD")),
                        "factor_cambio": float(position.get("tasa", 1)),
                    }

                    if lote["cantidad"] > 0:
                        lotes.append(lote)

            self.df_lotes = pd.DataFrame(lotes)
            return len(self.df_lotes)
        except Exception as e:
            _logger.error(f"[obtener_lotes_desde_info]: {e}")
            return 0

    def calcular_metricas_fondo(self, grupo):
        """Calcula métricas de riesgo y momentum para cada fondo"""
        grupo = grupo.sort_values("fecha")
        valores = grupo["valorActual"].values

        if len(valores) < self.top:
            return pd.Series(
                {
                    "volatilidad": np.nan,
                    "drawdown_max": np.nan,
                    "sharpe_ratio": np.nan,
                    "rendimiento_total": np.nan,
                    "posicion_relativa": np.nan,
                    "dias_datos": len(valores),
                }
            )

        # Rendimientos diarios
        rendimientos = np.diff(valores) / valores[:-1] * 100

        # Volatilidad (desviación estándar anualizada)
        volatilidad = np.std(rendimientos) * np.sqrt(252)

        # Drawdown máximo
        peak = np.maximum.accumulate(valores)
        drawdown = (valores - peak) / peak * 100
        drawdown_max = np.min(drawdown)

        # Rendimiento total
        rendimiento_total = (valores[-1] / valores[0] - 1) * 100

        # Sharpe Ratio simplificado
        sharpe = rendimiento_total / volatilidad if volatilidad > 0 else 0

        # Posición relativa al máximo histórico
        posicion_relativa = (valores[-1] / np.max(valores)) * 100

        return pd.Series(
            {
                "volatilidad": round(volatilidad, 2),
                "drawdown_max": round(drawdown_max, 2),
                "sharpe_ratio": round(sharpe, 2),
                "rendimiento_total": round(rendimiento_total, 2),
                "posicion_relativa": round(posicion_relativa, 2),
                "dias_datos": len(valores),
            }
        )

    def calcular_metricas_todos(self):
        """Calcula métricas para todos los fondos"""
        try:
            if self.df_historico.empty:
                self.cargar_datos_historicos()

            if self.df_historico.empty:
                return pd.DataFrame()

            self.metricas = (
                self.df_historico.groupby("fondo")
                .apply(self.calcular_metricas_fondo, include_groups=False)
                .reset_index()
            )

            # Agregar info del último registro
            if not self.df_ultimo.empty:
                info_cols = ["fondo", "moneda", "horizonte", "variacion", "variacion30dias", "variacion90dias"]
                info_ultimo = self.df_ultimo[[c for c in info_cols if c in self.df_ultimo.columns]].copy()
                self.metricas = self.metricas.merge(info_ultimo, on="fondo", how="left")

            # Calcular scoring
            self.metricas["score_decision"] = self.metricas.apply(self.generar_scoring, axis=1)
            self.metricas["senal"] = self.metricas["score_decision"].apply(self.clasificar_senal)

            return self.metricas
        except Exception as e:
            _logger.error(f"[calcular_metricas_todos]: {e}")
            return pd.DataFrame()

    def generar_scoring(self, row):
        """Genera score de -100 a +100: Positivo = COMPRA, Negativo = VENTA"""
        score = 0

        # 1. Posición relativa al máximo (peso: 40%)
        pos_rel = row.get("posicion_relativa", 100)
        if pd.notna(pos_rel):
            if pos_rel < 85:
                score += (100 - pos_rel) * 0.4
            else:
                score -= (pos_rel - 85) * 2

        # 2. Variación reciente vs histórica (peso: 30%)
        var_dia = row.get("variacion", 0) if pd.notna(row.get("variacion")) else 0
        var_90d = row.get("variacion90dias", 0) if pd.notna(row.get("variacion90dias")) else 0

        if var_dia < 0 and var_90d > 20:
            score += 30
        elif var_dia > 1 and var_90d > 50:
            score -= 20

        # 3. Sharpe Ratio (peso: 20%)
        sharpe = row.get("sharpe_ratio", 0) if pd.notna(row.get("sharpe_ratio")) else 0
        score += min(sharpe * 5, 20)

        # 4. Drawdown (peso: 10%)
        dd = row.get("drawdown_max", 0) if pd.notna(row.get("drawdown_max")) else 0
        if dd < -10:
            score += min(abs(dd) * 0.5, 10)

        return round(score, 1)

    def clasificar_senal(self, score):
        """Clasifica señal según score"""
        if score >= 30:
            return "COMPRA FUERTE"
        elif score >= 15:
            return "COMPRA"
        elif score >= -15:
            return "MANTENER"
        elif score >= -30:
            return "REDUCIR"
        else:
            return "VENTA"

    def analizar_lotes_venta(self):
        """Analiza lotes para decisión de venta.
        El umbral mínimo de ganancia se lee de sesion.gypPrecio (ratio decimal → ×100 = %).
        Fallback: UMBRAL_GANANCIA_MIN si no se puede obtener la configuración.
        """
        if self.df_lotes.empty:
            self.obtener_lotes_desde_info()

        if self.df_lotes.empty:
            return pd.DataFrame()

        # Obtener umbral desde configuración del vehículo (sesion.gypPrecio)
        umbral_ganancia = self.UMBRAL_GANANCIA_MIN  # fallback por defecto
        try:
            sesion = BDsystem.get_sesion_by_vehiculo(vehiculo=self.vehiculo)
            gyp = sesion.get("gypPrecio")
            if gyp is not None and float(gyp) > 0:
                umbral_ganancia = float(gyp) * 100  # ratio decimal → porcentaje
        except Exception as e:
            _logger.error(
                f"[analizar_lotes_venta] No se pudo leer gypPrecio, usando default {self.UMBRAL_GANANCIA_MIN}%: {e}"
            )

        # Agregar score del fondo
        if not self.metricas.empty:
            score_map = self.metricas.set_index("fondo")["score_decision"].to_dict()
            pos_map = self.metricas.set_index("fondo")["posicion_relativa"].to_dict()

            self.df_lotes["score_fondo"] = self.df_lotes["fondo"].map(score_map)
            self.df_lotes["posicion_fondo"] = self.df_lotes["fondo"].map(pos_map)

        if "posicion_fondo" not in self.df_lotes.columns:
            self.df_lotes["posicion_fondo"] = float("nan")
        if "score_fondo" not in self.df_lotes.columns:
            self.df_lotes["score_fondo"] = 0.0

        # Calcular prioridad de venta
        self.df_lotes["prioridad_venta"] = (
            (self.df_lotes["ganancia_pct"] > umbral_ganancia).astype(int) * 35
            + (self.df_lotes["posicion_fondo"].fillna(100) > self.UMBRAL_POSICION_MAX).astype(int) * 30
            + (-self.df_lotes["score_fondo"].fillna(0)) * 0.5
        )

        # Clasificar decisión
        def decision_venta(row):
            if row["ganancia_pct"] <= 0:
                return "MANTENER"
            if row["ganancia_pct"] < umbral_ganancia:
                return "ESPERAR"
            if row["prioridad_venta"] > 40:
                return "VENDER"
            return "CONSIDERAR"

        self.df_lotes["decision"] = self.df_lotes.apply(decision_venta, axis=1)

        return self.df_lotes

    def obtener_resumen(self):
        """Obtiene resumen de cartera"""
        if self.df_lotes.empty:
            self.obtener_lotes_desde_info()

        if self.df_lotes.empty:
            return {
                "total_activos": 0,
                "total_costo": 0,
                "total_valor": 0,
                "total_ganancia": 0,
                "ganancia_pct": 0,
                "divisa": "USD",
                "factor_cambio": 1.0,
            }

        total_costo = (self.df_lotes["costo_base"] * self.df_lotes["factor_cambio"]).sum()
        total_valor = (self.df_lotes["valor_actual"] * self.df_lotes["factor_cambio"]).sum()
        total_ganancia = (self.df_lotes["ganancia_abs"] * self.df_lotes["factor_cambio"]).sum()
        ganancia_pct = ((total_valor / total_costo) - 1) * 100 if total_costo > 0 else 0

        # Divisa y factor de cambio
        divisa = self.df_lotes["divisa"].iloc[0] if "divisa" in self.df_lotes.columns else "USD"
        factor_cambio = self.df_lotes["factor_cambio"].iloc[0] if "factor_cambio" in self.df_lotes.columns else 1.0

        return {
            "total_activos": len(self.df_lotes),
            "total_costo": total_costo,
            "total_valor": total_valor,
            "total_ganancia": total_ganancia,
            "ganancia_pct": ganancia_pct,
            "divisa": divisa,
            "factor_cambio": factor_cambio,
        }


class AnalisisCrypto(AnalisisBase):
    """Análisis específico para Criptomonedas"""

    def __init__(self, master, info, repositorio, colors, vehiculo="Crypto", positions=None):
        super().__init__(master, info, repositorio, colors, vehiculo)
        self._positions = positions or []

    def _calcular_beta_portfolio(self, df_hist):
        """Beta portfolio Crypto vs BTC usando la misma data histórica ya descargada."""
        try:
            from Class_customer import DataHub  # import diferido — evita ciclo

            if df_hist.empty or self.df_lotes.empty:
                return
            pivot = df_hist.pivot(index="fecha", columns="fondo", values="valorActual").dropna(how="all")
            returns = pivot.pct_change().dropna()
            if returns.empty or len(returns) < 10:
                return
            btc_col = next((c for c in returns.columns if "BTC" in c.upper()), None)
            market_ret = returns[btc_col] if btc_col else returns.mean(axis=1)
            market_var = market_ret.var()
            if market_var == 0:
                return
            beta_map = {col: returns[col].cov(market_ret) / market_var for col in returns.columns}
            total_val = self.df_lotes["valor_actual"].sum()
            if total_val <= 0:
                return
            beta_port = sum(
                (row["valor_actual"] / total_val) * beta_map.get(row["symbol"], 1.5)
                for _, row in self.df_lotes.iterrows()
            )
            DataHub.manager_GyP["Crypto"]["BetaPortfolio"] = round(max(beta_port, 0.1), 3)
        except Exception as e:
            _logger.error(f"_calcular_beta_portfolio(): {e}")

    def _refresh_mrg_display(self):
        """Actualiza Beta y % Mrg/Risk en Analysis luego de que el thread de yfinance computa el beta real."""
        from Class_customer import DataHub  # import diferido — evita ciclo: Class_Analisis→Class_customer

        if not hasattr(self, "_entry_beta") or not hasattr(self, "_entry_mrg") or not hasattr(self, "_mrg_data"):
            return
        try:
            if not self._entry_beta.winfo_exists():
                return
        except Exception:
            return

        beta = DataHub.manager_GyP["Crypto"].get("BetaPortfolio", 1.5)
        total_deuda, capital_neto = self._mrg_data
        equity = max(capital_neto, 1.0)
        mrg = (total_deuda / equity) * beta
        mrs = margin_risk_status(mrg)

        for entry in (self._entry_beta, self._entry_mrg):
            entry.config(state="normal")

        self._entry_beta.delete(0, "end")
        self._entry_beta.insert(0, f"{beta:.2f}")
        self._entry_beta.config(state="readonly")

        self._entry_mrg.delete(0, "end")
        self._entry_mrg.insert(
            0,
            f"{mrg:.1%}  {mrs['emoji']} {mrs['estado']} — {mrs['accion']}  (deuda/equity × β={beta:.2f})",
        )
        self._entry_mrg.config(state="readonly", fg=mrs["color"])

    def _fetch_historico_yfinance(self):
        """Override: convierte BTCUSDT→BTC-USD para yfinance y descarga 6 meses."""
        try:
            positions = [p for p in self._positions if float(p.get("position", 0)) > 0]
            if not positions:
                return pd.DataFrame()
            orig_names = [p["ticket"] for p in positions]
            yf_names = [s[:-4] + "-USD" if s.endswith("USDT") else s for s in orig_names]
            name_map = dict(zip(yf_names, orig_names))
            raw = yf.download(yf_names, period="6mo", auto_adjust=True, progress=False)
            if raw.empty:
                return pd.DataFrame()
            close = (
                raw[["Close"]].rename(columns={"Close": orig_names[0]})
                if len(yf_names) == 1
                else raw["Close"].rename(columns=name_map)
            )
            df = close.reset_index().melt(id_vars="Date", var_name="fondo", value_name="valorActual")
            df = df.rename(columns={"Date": "fecha"})
            return df.dropna(subset=["valorActual"])
        except Exception as e:
            _logger.error(f"AnalisisCrypto._fetch_historico_yfinance(): {e}")
            return pd.DataFrame()

    def _poblar_contenido(self, frame):
        """Implementación específica para Crypto"""

        def _actualizar():
            for w in frame.winfo_children():
                w.destroy()
            self._poblar_contenido(frame)

        self.obtener_lotes_desde_info()
        resumen = self.obtener_resumen()

        row = 0

        # ========== RESUMEN DE CARTERA ==========
        row = self.crear_seccion(frame, f"Resumen Cartera {self.vehiculo}", row)
        row = self.crear_campo(frame, "Fecha:", datetime.now().strftime("%Y-%m-%d %H:%M"), row)
        row = self.crear_campo(frame, "Total Activos:", resumen["total_activos"], row)
        row = self.crear_campo(frame, "Costo Base:", f"${resumen['total_costo']:,.2f}", row)
        row = self.crear_campo(frame, "Valor Actual:", f"${resumen['total_valor']:,.2f}", row)

        color_gan = self.obtener_color_ganancia(resumen["total_ganancia"])
        row = self.crear_campo(
            frame,
            "Ganancia Total:",
            f"${resumen['total_ganancia']:,.2f} ({resumen['ganancia_pct']:+.2f}%)",
            row,
            fg_valor=color_gan,
        )

        # ========== ANÁLISIS DE PRÉSTAMOS FLEXIBLES ==========
        row = self._seccion_deuda(frame, row)

        # ========== GESTIÓN EARN ↔ SPOT ==========
        row = self._seccion_earn_spot(frame, row)

        # ========== RENDIMIENTO DE POSICIONES ==========
        row = self.crear_seccion(frame, f"Rendimiento Top {self.top} (6m):", row)
        frame_chart = tk.Frame(frame, bg=self.CG_COLOR)
        frame_chart.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        tk.Label(
            frame_chart,
            text="Cargando datos históricos...",
            bg=self.CG_COLOR,
            fg="gray",
            font=("Segoe UI", 8),
        ).pack()
        row += 1

        def _cargar_y_render_crypto():
            df_hist = self._fetch_historico_yfinance()
            self._calcular_beta_portfolio(df_hist)
            frame_chart.after(0, self._refresh_mrg_display)
            frame_chart.after(0, lambda: self._render_grafico_evolucion(frame_chart, df_hist))

        threading.Thread(target=_cargar_y_render_crypto, daemon=True).start()

        # ========== CARTERA VS ÍNDICE ==========
        row = self.crear_seccion(frame, "Cartera vs Índice:", row)

        row = self.crear_grafico_vs_indice(parent=frame, row=row)

        after_id = frame.after(60000, _actualizar)
        frame.winfo_toplevel().bind("<Destroy>", lambda e: frame.after_cancel(after_id), add="+")

    def _seccion_deuda(self, frame, row):
        """Sección de análisis de préstamos flexibles Binance con simulador loan_distribute."""
        from Class_customer import DataHub  # import diferido — evita ciclo: Class_Analisis→Class_customer
        from Class_ServiciosCrypto import ServiciosCrypto  # import diferido — evita ciclo con Modulos_python chain

        def _get_loan_data():
            from Class_ApiBinnace import BinanceClient  # import diferido — evita ciclo con Modulos_python chain

            try:
                spot = BinanceClient(vehiculo="Crypto").spot
                resultado = spot.get_flexible_loan_ongoing_orders()
                rows = resultado.get("rows", []) if resultado else []
                prestamos = []
                for r in rows:
                    ltv = float(r.get("currentLTV", 0))
                    if ltv == 0:
                        continue
                    loan_usd = float(r.get("loanValueInUSD") or r.get("totalDebt", 0))
                    col_usd = float(r.get("collateralValueInUSD", 0))
                    if col_usd == 0 and ltv > 0:
                        col_usd = loan_usd / ltv
                    prestamos.append(
                        {
                            "activo": r.get("collateralCoin", ""),
                            "loan_coin": r.get("loanCoin", "USDT"),
                            "col_usd": col_usd,
                            "ltv": ltv,
                            "deuda": loan_usd,
                            "col_amount": float(r.get("collateralAmount", 0)),
                        }
                    )
                return prestamos
            except Exception as e:
                _logger.error(f"[_get_loan_data]: {e}")
                return []

        def _draw_grafico_en_fig(fg, prestamos_data, earn_map_local):
            """Dibuja datos LTV/Colateral sobre una Figure — reutilizable para actualización sin parpadeo."""
            if not prestamos_data:
                return
            ltv_inicial = float(lconfig.get("ltv_inicial", 0.78))
            ltv_alerta = float(lconfig.get("ltv_alerta", 0.85))
            ltv_liquidacion = float(lconfig.get("ltv_liquidacion", 0.91))

            activos = [p["activo"] for p in prestamos_data]
            ltvs = [p["ltv"] * 100 for p in prestamos_data]
            deudas = [p["deuda"] for p in prestamos_data]
            cols_usd = [p["col_usd"] for p in prestamos_data]
            n = len(activos)
            x = np.arange(n)

            fg.patch.set_facecolor(self.CG_COLOR)
            fg.subplots_adjust(left=0.10, right=0.88, top=0.82, bottom=0.18)
            ax1 = fg.add_subplot(111)
            ax1.set_facecolor(self.CG_COLOR)
            ax2 = ax1.twinx()

            ltv_max = ltv_liquidacion * 100 + 10

            def _span(y0, y1, color, alpha):
                y0n = y0 / ltv_max
                y1n = y1 / ltv_max
                ax1.add_patch(
                    Rectangle((0, y0n), 1, y1n - y0n, transform=ax1.transAxes, color=color, alpha=alpha, zorder=0)
                )

            _span(0, ltv_inicial * 100, "#27ae60", 0.08)
            _span(ltv_inicial * 100, ltv_alerta * 100, "#e67e22", 0.10)
            _span(ltv_alerta * 100, ltv_liquidacion * 100, "#e74c3c", 0.13)

            ax1.axhline(
                ltv_inicial * 100,
                color="#27ae60",
                linewidth=0.9,
                linestyle="--",
                zorder=2,
                label=f"Inicial {ltv_inicial:.0%}",
            )
            ax1.axhline(
                ltv_alerta * 100,
                color="#e67e22",
                linewidth=0.9,
                linestyle="--",
                zorder=2,
                label=f"Alerta {ltv_alerta:.0%}",
            )
            ax1.axhline(
                ltv_liquidacion * 100,
                color="#e74c3c",
                linewidth=1.1,
                linestyle="-",
                zorder=2,
                label=f"Liquidación {ltv_liquidacion:.0%}",
            )

            ax1.plot(x, ltvs, color="white", linewidth=1.0, marker="o", markersize=3, zorder=7, label="LTV actual")
            for i in range(n):
                ax1.text(
                    x[i],
                    ltvs[i] + 1.5,
                    f"{ltvs[i]:.1f}%",
                    color="white",
                    fontsize=6,
                    ha="center",
                    va="bottom",
                    zorder=8,
                )
                if ltvs[i] >= ltv_inicial * 100:
                    ax1.text(x[i], ltvs[i] + 4.5, "⚠", color="#e74c3c", fontsize=7, ha="center", va="bottom", zorder=8)

            ax1.set_ylim(0, ltv_liquidacion * 100 + 10)
            ax1.set_ylabel("Ratio Deuda / Colateral (LTV)", color="white", fontsize=6)
            ax1.tick_params(axis="y", colors="white", labelsize=6)
            ax1.spines["left"].set_color("white")
            ax1.spines["left"].set_linewidth(1.0)
            ax1.grid(True, alpha=0.12, color="gray", axis="y", linestyle=":", zorder=0)

            deudas_arr = np.array(deudas)
            cols_arr = np.array(cols_usd)
            ax2.fill_between(x, 0, deudas_arr, color="#e74c3c", alpha=0.40, zorder=3, label="Deuda USD")
            ax2.plot(x, deudas_arr, color="#e74c3c", linewidth=0.9, zorder=4)
            ax2.fill_between(x, deudas_arr, cols_arr, color="#2980b9", alpha=0.35, zorder=3, label="Col. USD")
            ax2.plot(x, cols_arr, color="#2980b9", linewidth=0.9, zorder=4)

            max_usd = float(cols_arr.max()) * 1.1 if len(cols_arr) > 0 else 1
            ax2.set_ylim(0, max_usd * 1.55)
            ax2.set_ylabel("Deuda / Colateral USD", color="white", fontsize=6)
            ax2.tick_params(axis="y", colors="white", labelsize=6)
            ax2.spines["right"].set_color("gray")
            ax2.grid(True, alpha=0.22, color="gray", axis="y", linestyle=":", zorder=1)

            ax1.set_xticks(x)
            ax1.set_xticklabels(activos, color="white", fontsize=7, rotation=60, ha="right")
            ax1.set_xlim(-0.6, n - 0.4)
            ax2.set_xlim(-0.6, n - 0.4)
            for ax in (ax1, ax2):
                ax.spines["top"].set_visible(False)
                ax.spines["bottom"].set_visible(False)
                ax.tick_params(axis="x", length=0)

            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            leg1 = fg.legend(
                lines1,
                labels1,
                loc="outside upper left",
                fontsize=5,
                facecolor="white",
                labelcolor="black",
                framealpha=1.0,
                title="Zonas / LTV",
                title_fontsize=5,
            )
            leg2 = fg.legend(
                lines2,
                labels2,
                loc="lower right",
                fontsize=5,
                facecolor="white",
                labelcolor="black",
                framealpha=0.9,
                title="Importes",
                title_fontsize=5,
            )
            fg.add_artist(leg1)
            fg.add_artist(leg2)
            fg.suptitle("Deuda / Colateral USD", fontsize=9, color="white")

        def _crear_grafico_prestamos(parent, prestamos_data, earn_map_local, row):
            if not prestamos_data:
                return row, None
            fg = Figure(figsize=(5.6, 3.2), dpi=100)
            _draw_grafico_en_fig(fg, prestamos_data, earn_map_local)
            frm = tk.Frame(parent, bg=self.CG_COLOR)
            frm.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
            canvas_fig = FigureCanvasTkAgg(fg, master=frm)
            canvas_fig.draw()
            canvas_fig.get_tk_widget().pack(fill="x", expand=True)
            frm._fg = fg
            frm._canvas = canvas_fig
            return row + 1, frm

        def _calcular_distribucion():
            try:
                monto_str = entry_monto.get().strip()
                requested = float(monto_str) if monto_str else 0.0
                if requested <= 0:
                    return
                delta_min = float(lconfig.get("delta_minimo", 1.0))
                # distribuir proporcional al earn disponible (colateral total, no solo bloqueado)
                # BTC puede tener mucho earn libre aunque tenga poco colateral bloqueado
                cap_disponible = [earn_map.get(p["activo"], p["col_usd"]) for p in prestamos]
                total_cap = sum(cap_disponible)
                target_ltv = (total_deuda + requested) / total_cap if total_cap > 0 else 0
                raw = [max(0.0, cap * target_ltv - p["deuda"]) for cap, p in zip(cap_disponible, prestamos)]
                total_raw = sum(raw)
                scale = requested / total_raw if total_raw > 0 else 0

                for item in tree_result.get_children():
                    tree_result.delete(item)

                total_borrow = 0.0
                for p, r, cap in zip(prestamos, raw, cap_disponible):
                    borrow = r * scale if r * scale >= delta_min else 0.0
                    ltv_final = (p["deuda"] + borrow) / cap if cap > 0 else 0
                    total_borrow += borrow
                    tree_result.insert(
                        "",
                        "end",
                        values=(
                            p["activo"],
                            f"{p['col_usd']:,.2f}",
                            f"{p['ltv']:.2%}",
                            f"{p['deuda']:,.2f}",
                            f"{borrow:,.2f}" if borrow > 0 else "-",
                            f"{ltv_final:.2%}",
                        ),
                    )
                ltv_portfolio = (total_deuda + total_borrow) / total_col if total_col > 0 else 0
                tree_result.insert(
                    "",
                    "end",
                    values=(
                        "TOTAL",
                        f"{total_col:,.2f}",
                        "",
                        f"{total_deuda:,.2f}",
                        f"{total_borrow:,.2f}",
                        f"{ltv_portfolio:.2%}",
                    ),
                    tags=("total",),
                )
                tree_result.tag_configure("total", foreground="yellow")
            except Exception as e:
                _logger.error(f"_calcular_distribucion(): {e}")

        # — leer params desde BD —
        try:
            sesion = self.repositorio.get_sesion_by_vehiculo("Crypto")
            params_raw = sesion.get("parameters", "{}") if sesion else "{}"
            params = json.loads(params_raw.decode("utf-8") if isinstance(params_raw, bytes) else params_raw)
            lconfig = params.get("loan", {})
        except Exception:
            lconfig = {}

        prestamos = _get_loan_data()
        total_col = sum(p["col_usd"] for p in prestamos)
        total_deuda = sum(p["deuda"] for p in prestamos)

        # capital earn de los activos con LTV activo = capital real disponible
        # Binance puede bloquear todo ese earn como colateral en cualquier momento
        try:
            earn_balances = ServiciosCrypto().earn_spot_balances()
            earn_map = {b["asset"]: b.get("usdt_value", 0.0) for b in earn_balances}
        except Exception:
            earn_map = {}
        col_assets = {p["activo"] for p in prestamos}
        capital_earn_col = sum(earn_map.get(a, 0.0) for a in col_assets)
        capital_base = capital_earn_col if capital_earn_col > 0 else total_col

        capital_neto = capital_base - total_deuda
        apalancamiento = total_deuda / capital_base if capital_base > 0 else 0
        leverage_crypto = total_col / max(capital_neto, 1.0)

        _beta_c = DataHub.manager_GyP["Crypto"].get("BetaPortfolio", 1.5)
        _equity_c = max(capital_neto, 1.0)
        _mrg_risk_c = (total_deuda / _equity_c) * _beta_c
        _mrs_c = margin_risk_status(_mrg_risk_c)

        # sincronizar con panel — solo si tenemos datos válidos de API (evita reset a 0 cuando falla)
        if prestamos:
            DataHub.manager_GyP["Crypto"]["Colateral"] = total_col
            DataHub.manager_GyP["Crypto"]["CapitalNeto"] = capital_neto
            DataHub.manager_GyP["Crypto"]["Debit"] = total_deuda
            DataHub.manager_GyP["Crypto"]["Leverage"] = leverage_crypto
        else:
            _logger.error("[_seccion_deuda]: prestamos vacío — DataHub no actualizado, se conservan valores previos")

        ltv_binance = total_deuda / total_col if total_col > 0 else 0

        row = self.crear_seccion(frame, "Análisis de Préstamos Flexibles", row)
        row = self.crear_campo(frame, "Capital disponible (earn):", f"${capital_base:,.2f} USD", row)
        row = self.crear_campo(frame, "Deuda Total:", f"${total_deuda:,.2f} USDT", row)
        color_neto = "green" if capital_neto >= 0 else "red"
        row = self.crear_campo(frame, "Capital Neto:", f"${capital_neto:,.2f} USD", row, fg_valor=color_neto)
        row = self.crear_campo(
            frame, "Exposición sobre capital:", f"{apalancamiento:.2%}  (deuda / capital disponible)", row
        )
        row = self.crear_campo(
            frame, "LTV Binance actual:", f"{ltv_binance:.2%}  (ref. simulador — deuda / col. bloqueado)", row
        )
        row = self.crear_campo(frame, "Leverage:", f"{leverage_crypto:.2f}x  (col bloqueado / capital_neto)", row)
        # Beta y % Mrg/Risk — entradas con referencia para actualizar luego de que el thread de yfinance compute el beta real
        tk.Label(
            frame, text="Beta Portfolio:", bg=self.BG_COLOR, fg=self.VALUE_FG, font=("Segoe UI", 9), anchor="w"
        ).grid(row=row, column=0, sticky="w", padx=10, pady=3)
        self._entry_beta = tk.Entry(
            frame, width=45, bg=self.ENTRY_BG, fg=self.VALUE_FG, font=("Segoe UI", 9), relief="flat"
        )
        self._entry_beta.insert(0, f"{_beta_c:.2f}  (actualizando...)")
        self._entry_beta.config(state="readonly")
        self._entry_beta.grid(row=row, column=1, padx=10, pady=3, sticky="w")
        row += 1

        tk.Label(frame, text="% Mrg/Risk:", bg=self.BG_COLOR, fg=self.VALUE_FG, font=("Segoe UI", 9), anchor="w").grid(
            row=row, column=0, sticky="w", padx=10, pady=3
        )
        self._entry_mrg = tk.Entry(
            frame, width=45, bg=self.ENTRY_BG, fg=_mrs_c["color"], font=("Segoe UI", 9), relief="flat"
        )
        self._entry_mrg.insert(
            0,
            f"{_mrg_risk_c:.1%}  {_mrs_c['emoji']} {_mrs_c['estado']} — {_mrs_c['accion']}  (deuda/equity × β={_beta_c:.2f})",
        )
        self._entry_mrg.config(state="readonly")
        self._entry_mrg.grid(row=row, column=1, padx=10, pady=3, sticky="w")
        self._mrg_data = (total_deuda, capital_neto)
        row += 1

        row, frm_grafico = _crear_grafico_prestamos(frame, prestamos, earn_map, row)

        # simulador loan_distribute
        row = self.crear_seccion(frame, "Simulador loan_distribute", row)

        frame_input = tk.Frame(frame, bg=self.BG_COLOR)
        frame_input.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=4)
        tk.Label(
            frame_input,
            text=f"Monto a solicitar (máx. ${capital_neto:,.2f}):",
            bg=self.BG_COLOR,
            fg="black",
            font=("Segoe UI", 9),
        ).pack(side="left")
        entry_monto = tk.Entry(frame_input, width=12, bg=self.ENTRY_BG, fg="white", font=("Segoe UI", 9), relief="flat")
        entry_monto.insert(0, "0")
        entry_monto.pack(side="left", padx=6)
        tk.Button(
            frame_input,
            text="Calcular",
            bg="DarkCyan",
            fg="white",
            width=10,
            font=("Segoe UI", 9),
            command=_calcular_distribucion,
        ).pack(side="left", padx=4)
        row += 1

        cols_res = ("Activo", "Col USD", "LTV actual", "USDT Actual", "Pedir USDT", "LTV final")

        frame_tree_sim = tk.Frame(frame, bg=self.BG_COLOR)
        frame_tree_sim.grid(row=row, column=0, columnspan=2, padx=10, pady=4, sticky="w")

        sb_sim = ttk.Scrollbar(frame_tree_sim, orient="vertical")
        tree_result = ttk.Treeview(
            frame_tree_sim,
            columns=cols_res,
            show="headings",
            height=len(prestamos) + 1 or 2,
            yscrollcommand=sb_sim.set,
        )
        sb_sim.config(command=tree_result.yview)

        for c, w in zip(cols_res, (70, 90, 80, 90, 90, 80)):
            tree_result.heading(c, text=c)
            tree_result.column(c, width=w, anchor="e")
        tree_result.column("Activo", anchor="center")

        # distribución actual al cargar
        ltv_portfolio_actual = total_deuda / total_col if total_col > 0 else 0
        for p in prestamos:
            tree_result.insert(
                "",
                "end",
                values=(
                    p["activo"],
                    f"{p['col_usd']:,.2f}",
                    f"{p['ltv']:.2%}",
                    f"{p['deuda']:,.2f}",
                    "-",
                    f"{p['ltv']:.2%}",
                ),
            )
        tree_result.insert(
            "",
            "end",
            values=(
                "TOTAL",
                f"{total_col:,.2f}",
                f"{ltv_portfolio_actual:.2%}",
                f"{total_deuda:,.2f}",
                "-",
                f"{ltv_portfolio_actual:.2%}",
            ),
            tags=("total",),
        )
        tree_result.tag_configure("total", foreground="yellow")

        tree_result.pack(side="left", fill="both")
        sb_sim.pack(side="right", fill="y")
        row += 1

        def _actualizar_live():
            nonlocal frm_grafico, prestamos, earn_map
            try:
                nuevos = _get_loan_data()
                if not nuevos:
                    tree_result.after(10000, _actualizar_live)
                    return
                # actualizar treeview
                iids = tree_result.get_children()
                for iid, p in zip(iids, nuevos):
                    vals = tree_result.item(iid, "values")
                    if vals[0] == "TOTAL":
                        continue
                    tree_result.set(iid, "Col USD", f"{p['col_usd']:,.2f}")
                    tree_result.set(iid, "LTV actual", f"{p['ltv']:.2%}")
                    tree_result.set(iid, "USDT Actual", f"{p['deuda']:,.2f}")
                    tree_result.set(iid, "Pedir USDT", "-")
                    tree_result.set(iid, "LTV final", f"{p['ltv']:.2%}")
                total_iid = iids[-1] if iids else None
                if total_iid:
                    t_col = sum(p["col_usd"] for p in nuevos)
                    t_deu = sum(p["deuda"] for p in nuevos)
                    t_ltv = t_deu / t_col if t_col > 0 else 0
                    tree_result.set(total_iid, "Col USD", f"{t_col:,.2f}")
                    tree_result.set(total_iid, "USDT Actual", f"{t_deu:,.2f}")
                    tree_result.set(total_iid, "LTV final", f"{t_ltv:.2%}")
                # actualizar closures para que _calcular_distribucion use datos frescos
                earn_nuevo = {b["asset"]: b.get("usdt_value", 0.0) for b in ServiciosCrypto().earn_spot_balances()}
                prestamos = nuevos
                earn_map = earn_nuevo
                # redibujar gráfico in-place — sin destroy para eliminar parpadeo
                if frm_grafico is not None and hasattr(frm_grafico, "_fg"):
                    frm_grafico._fg.clear()
                    _draw_grafico_en_fig(frm_grafico._fg, nuevos, earn_nuevo)
                    frm_grafico._canvas.draw_idle()
            except Exception as e:
                _logger.error(f"_actualizar_live: {e}")
            tree_result.after(10000, _actualizar_live)

        tree_result.after(10000, _actualizar_live)

        def _ejecutar_prestamo():
            from Class_ApiBinnace import BinanceClient  # import diferido — evita ciclo con Modulos_python chain
            from Class_customer import MyMessageBox  # import diferido — evita ciclo

            try:
                spot = BinanceClient(vehiculo="Crypto").spot
                errores, ok, total_ejecutado = [], 0, 0.0
                for item in tree_result.get_children():
                    vals = tree_result.item(item, "values")
                    if vals[0] == "TOTAL" or vals[4] == "-":
                        continue
                    activo = vals[0]
                    borrow = float(vals[4].replace(",", ""))
                    if borrow <= 0:
                        continue
                    time.sleep(2)
                    resp = spot.get_flexible_loan_borrow(loanCoin="USDT", collateralCoin=activo, amount=borrow)
                    _logger.warning(f"loan_borrow [{activo}] ${borrow:.2f} → {resp}")
                    if not resp:
                        errores.append(f"{activo}:sin respuesta")
                    elif "code" in resp and int(resp["code"]) < 0:
                        errores.append(f"{activo}:{resp.get('msg', resp['code'])}")
                    else:
                        ok += 1
                        total_ejecutado += borrow
                msg = f"Préstamo ejecutado: {ok} activos\n${total_ejecutado:.2f} USDT"
                if errores:
                    msg += f"\n\nErrores:\n" + "\n".join(errores)
                MyMessageBox(frame).showinfo("Préstamo", msg)
            except Exception as e:
                MyMessageBox(frame).showinfo("Error", str(e))
                _logger.error(f"_ejecutar_prestamo(): {e}")

        def _ejecutar_pago():
            from Class_ApiBinnace import BinanceClient  # import diferido — evita ciclo con Modulos_python chain
            from Class_customer import MyMessageBox  # import diferido — evita ciclo

            try:
                monto_str = entry_monto.get().strip()
                requested = float(monto_str) if monto_str else 0.0
                if requested <= 0:
                    MyMessageBox(frame).showinfo("Pagar", "Ingresa el monto a pagar")
                    return
                spot = BinanceClient(vehiculo="Crypto").spot
                n_repay = len(prestamos)
                target_deuda_repay = (total_deuda - requested) / n_repay if n_repay > 0 else 0
                raw_repay = [max(0.0, p["deuda"] - target_deuda_repay) for p in prestamos]
                total_raw_repay = sum(raw_repay) or 1.0
                errores, ok, total_pagado = [], 0, 0.0
                for p, r in zip(prestamos, raw_repay):
                    repay = round(requested * (r / total_raw_repay), 2)
                    if repay <= 0:
                        continue
                    time.sleep(2)
                    resp = spot.get_flexible_loan_repay(loanCoin="USDT", collateralCoin=p["activo"], amount=repay)
                    _logger.warning(f"loan_repay [{p['activo']}] ${repay:.2f} → {resp}")
                    if not resp:
                        errores.append(f"{p['activo']}:sin respuesta")
                    elif "code" in resp and int(resp["code"]) < 0:
                        errores.append(f"{p['activo']}:{resp.get('msg', resp['code'])}")
                    else:
                        repay_status = resp.get("repayStatus", resp.get("status", "OK"))
                        ok += 1
                        total_pagado += repay
                        _logger.warning(f"loan_repay [{p['activo']}] → {repay_status}")
                msg = f"Pago ejecutado: {ok} activos\n${total_pagado:.2f} USDT"
                if errores:
                    msg += f"\n\nErrores:\n" + "\n".join(errores)
                MyMessageBox(frame).showinfo("Pagar", msg)
            except Exception as e:
                MyMessageBox(frame).showinfo("Error", str(e))
                _logger.error(f"_ejecutar_pago(): {e}")

        frame_btns = tk.Frame(frame, bg=self.BG_COLOR)
        frame_btns.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=8)
        tk.Button(frame_btns, text="Préstamo", bg="#2471a3", fg="white", width=12, command=_ejecutar_prestamo).pack(
            side="left", padx=4
        )
        tk.Button(frame_btns, text="Pagar", bg="#922b21", fg="white", width=12, command=_ejecutar_pago).pack(
            side="left", padx=4
        )
        row += 1

        return row

    def _seccion_earn_spot(self, frame, row):
        """Sección Gestión Earn ↔ Spot: suscribir / rescatar fondos Simple Earn."""

        def _cargar_balances():
            from Class_ServiciosCrypto import ServiciosCrypto  # import diferido — evita ciclo con Modulos_python chain

            try:
                return ServiciosCrypto().earn_spot_balances()
            except Exception as e:
                _logger.error(f"_seccion_earn_spot._cargar_balances(): {e}")
                return []

        def _ejecutar_subscribe():
            from Class_ServiciosCrypto import ServiciosCrypto  # import diferido — evita ciclo con Modulos_python chain
            from Class_customer import MyMessageBox  # import diferido — evita ciclo

            sel = tree_earn.selection()
            if not sel:
                MyMessageBox(frame).showinfo("Earn", "Selecciona una fila primero")
                return
            vals = tree_earn.item(sel[0], "values")
            product_id = vals[6]
            if not product_id:
                MyMessageBox(frame).showinfo("Earn", f"No hay productId para {vals[0]} — activo sin posición Earn")
                return
            try:
                amount = float(entry_monto_earn.get().strip())
            except ValueError:
                MyMessageBox(frame).showinfo("Earn", "Ingresa un monto válido")
                return
            if amount <= 0:
                MyMessageBox(frame).showinfo("Earn", "El monto debe ser mayor a 0")
                return
            spot_str = vals[1].replace(",", "") if vals[1] != "-" else "0"
            spot_disponible = float(spot_str) if spot_str else 0.0
            if amount > spot_disponible:
                MyMessageBox(frame).showinfo(
                    "Earn",
                    f"Insuficiente en Spot\nDisponible: {spot_disponible:.6f} {vals[0]}\nSolicitado: {amount:.6f}",
                )
                return
            try:
                resp = ServiciosCrypto().earn_subscribe(productId=product_id, amount=amount)
                _logger.warning(f"earn_subscribe [{vals[0]}] {amount} → {resp}")
                if resp and "code" in resp and int(resp["code"]) < 0:
                    MyMessageBox(frame).showinfo("Earn", f"Error: {resp.get('msg', resp['code'])}")
                else:
                    MyMessageBox(frame).showinfo("Earn", f"Suscrito: {amount} {vals[0]}\n{resp}")
            except Exception as e:
                MyMessageBox(frame).showinfo("Error", str(e))
                _logger.error(f"_ejecutar_subscribe(): {e}")

        def _ejecutar_redeem():
            from Class_ServiciosCrypto import ServiciosCrypto  # import diferido — evita ciclo con Modulos_python chain
            from Class_customer import MyMessageBox  # import diferido — evita ciclo

            sel = tree_earn.selection()
            if not sel:
                MyMessageBox(frame).showinfo("Earn", "Selecciona una fila primero")
                return
            vals = tree_earn.item(sel[0], "values")
            product_id = vals[6]
            if not product_id:
                MyMessageBox(frame).showinfo("Earn", f"No hay productId para {vals[0]} — sin posición Earn activa")
                return
            try:
                amount = float(entry_monto_earn.get().strip())
            except ValueError:
                MyMessageBox(frame).showinfo("Earn", "Ingresa un monto válido")
                return
            if amount <= 0:
                MyMessageBox(frame).showinfo("Earn", "El monto debe ser mayor a 0")
                return
            earn_str = vals[2].replace(",", "") if vals[2] != "-" else "0"
            earn_disponible = float(earn_str) if earn_str else 0.0
            if amount > earn_disponible:
                MyMessageBox(frame).showinfo(
                    "Earn",
                    f"Insuficiente en Earn\nDisponible: {earn_disponible:.6f} {vals[0]}\nSolicitado: {amount:.6f}",
                )
                return
            try:
                resp = ServiciosCrypto().earn_redeem(productId=product_id, amount=amount)
                _logger.warning(f"earn_redeem [{vals[0]}] {amount} → {resp}")
                if resp and "code" in resp and int(resp["code"]) < 0:
                    MyMessageBox(frame).showinfo("Earn", f"Error: {resp.get('msg', resp['code'])}")
                else:
                    MyMessageBox(frame).showinfo("Earn", f"Rescatado: {amount} {vals[0]}\n{resp}")
            except Exception as e:
                MyMessageBox(frame).showinfo("Error", str(e))
                _logger.error(f"_ejecutar_redeem(): {e}")

        def _on_select(event):
            sel = tree_earn.selection()
            if not sel:
                return
            vals = tree_earn.item(sel[0], "values")
            entry_monto_earn.delete(0, "end")
            # Pre-fill con el Spot libre (máximo disponible para Spot → Earn)
            spot_str = vals[1].replace(",", "") if vals[1] != "-" else "0"
            try:
                entry_monto_earn.insert(0, f"{float(spot_str):.6f}".rstrip("0").rstrip("."))
            except ValueError:
                pass

        row = self.crear_seccion(frame, "Gestión Earn ↔ Spot", row)

        balances = _cargar_balances()

        cols_earn = ("Activo", "Spot Libre", "Earn Amount", "APR %", "Rescate", "USDT", "productId")
        n_rows = max(len(balances), 2)

        frame_tree_earn = tk.Frame(frame, bg=self.BG_COLOR)
        frame_tree_earn.grid(row=row, column=0, columnspan=2, padx=10, pady=4, sticky="w")

        sb_earn = ttk.Scrollbar(frame_tree_earn, orient="vertical")
        tree_earn = ttk.Treeview(
            frame_tree_earn,
            columns=cols_earn,
            show="headings",
            height=min(n_rows, 8),
            yscrollcommand=sb_earn.set,
        )
        sb_earn.config(command=tree_earn.yview)

        _sort_state = {}

        def _sort_col(col):
            reverse = _sort_state.get(col, False)
            col_idx = cols_earn.index(col)
            rows = [(tree_earn.set(k, col), k) for k in tree_earn.get_children("")]

            def _key(item):
                v = item[0]
                if v in ("-", "Sí", "No"):
                    return (0, v)
                try:
                    return (1, float(v.replace("$", "").replace(",", "").replace("%", "")))
                except ValueError:
                    return (0, v)

            rows.sort(key=_key, reverse=reverse)
            for idx, (_, k) in enumerate(rows):
                tree_earn.move(k, "", idx)
            _sort_state[col] = not reverse
            for c in cols_earn:
                tree_earn.heading(c, text=c)
            arrow = " ▲" if not reverse else " ▼"
            tree_earn.heading(col, text=col + arrow)

        for col, w in zip(cols_earn, (70, 100, 100, 60, 80, 90, 0)):
            tree_earn.heading(col, text=col, command=lambda c=col: _sort_col(c))
            tree_earn.column(col, width=w, anchor="e" if col != "Activo" else "center", minwidth=w)
        tree_earn.column("productId", width=0, minwidth=0, stretch=False)

        for b in balances:
            usdt_val = b.get("usdt_value", 0.0)
            tree_earn.insert(
                "",
                "end",
                values=(
                    b["asset"],
                    f"{b['spot_free']:,.6f}" if b["spot_free"] > 0 else "-",
                    f"{b['earn_amount']:,.6f}" if b["earn_amount"] > 0 else "-",
                    f"{b['earn_apr']:.2%}" if b["earn_apr"] > 0 else "-",
                    "Sí" if b["can_redeem"] else ("No" if b["earn_amount"] > 0 else "-"),
                    f"${usdt_val:,.2f}" if usdt_val > 0 else "-",
                    b["earn_product_id"],
                ),
            )

        tree_earn.pack(side="left", fill="both")
        sb_earn.pack(side="right", fill="y")
        tree_earn.bind("<<TreeviewSelect>>", _on_select)
        row += 1

        frame_earn_ctrl = tk.Frame(frame, bg=self.BG_COLOR)
        frame_earn_ctrl.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=4)

        tk.Label(frame_earn_ctrl, text="Monto:", bg=self.BG_COLOR, fg="black", font=("Segoe UI", 9)).pack(side="left")
        entry_monto_earn = tk.Entry(
            frame_earn_ctrl, width=16, bg=self.ENTRY_BG, fg="white", font=("Segoe UI", 9), relief="flat"
        )
        entry_monto_earn.insert(0, "0")
        entry_monto_earn.pack(side="left", padx=6)

        tk.Button(
            frame_earn_ctrl,
            text="Spot → Earn",
            bg="#1a5276",
            fg="white",
            width=14,
            font=("Segoe UI", 9),
            command=_ejecutar_subscribe,
        ).pack(side="left", padx=4)
        tk.Button(
            frame_earn_ctrl,
            text="Earn → Spot",
            bg="#7d6608",
            fg="white",
            width=14,
            font=("Segoe UI", 9),
            command=_ejecutar_redeem,
        ).pack(side="left", padx=4)
        row += 1

        return row

    def obtener_lotes_desde_info(self):
        """Obtiene lotes desde self._positions (lista de DataHub.positions)"""
        try:
            lotes = []

            for pos in self._positions:
                if not isinstance(pos, dict):
                    continue

                cantidad = float(pos.get("position", 0))
                costobase = float(pos.get("costobase", 0))
                mrkprice = float(pos.get("mrkprice", 0))

                if cantidad <= 0:
                    continue

                valor_actual = cantidad * mrkprice if mrkprice > 0 else 0
                ganancia_abs = valor_actual - costobase if costobase > 0 else 0
                ganancia_pct = ((valor_actual / costobase) - 1) * 100 if costobase > 0 else 0

                lotes.append(
                    {
                        "symbol": pos.get("ticket", ""),
                        "cantidad": cantidad,
                        "costo_base": costobase,
                        "precio_actual": mrkprice,
                        "valor_actual": valor_actual,
                        "ganancia_abs": ganancia_abs,
                        "ganancia_pct": ganancia_pct,
                    }
                )

            self.df_lotes = pd.DataFrame(lotes)
            return len(self.df_lotes)

        except Exception as e:
            _logger.error(f"[AnalisisCrypto.obtener_lotes_desde_info]: {e}")
            return 0

    def obtener_resumen(self):
        """Obtiene resumen de cartera crypto"""
        if self.df_lotes.empty:
            return {
                "total_activos": 0,
                "total_costo": 0,
                "total_valor": 0,
                "total_ganancia": 0,
                "ganancia_pct": 0,
            }

        total_costo = self.df_lotes["costo_base"].sum()
        total_valor = self.df_lotes["valor_actual"].sum()
        total_ganancia = self.df_lotes["ganancia_abs"].sum()
        ganancia_pct = ((total_valor / total_costo) - 1) * 100 if total_costo > 0 else 0

        return {
            "total_activos": len(self.df_lotes),
            "total_costo": total_costo,
            "total_valor": total_valor,
            "total_ganancia": total_ganancia,
            "ganancia_pct": ganancia_pct,
        }


class AnalisisStock(AnalisisBase):
    """Análisis específico para Acciones (IB)"""

    _LEVERAGE_PARAMS = {
        "max_leverage": 1.8,
        "max_monthly_interest_pct": 0.02,
        "target_beta_portfolio": 1.2,
        "max_beta_portfolio": 1.5,
        "tasa_ib": 0.065,
    }

    def __init__(self, master, info, repositorio, colors, vehiculo="Stock", summary=None, account=None, positions=None):
        super().__init__(
            master, info, repositorio, colors, vehiculo, summary=summary, account=account, positions=positions
        )

    def _poblar_contenido(self, frame):
        """Implementación específica para Stock"""
        self.obtener_lotes_desde_info()
        resumen = self.obtener_resumen()

        row = 0

        # ========== RESUMEN DE CARTERA ==========
        row = self.crear_seccion(frame, f"Resumen Cartera {self.vehiculo}", row)
        row = self.crear_campo(frame, "Fecha:", datetime.now().strftime("%Y-%m-%d %H:%M"), row)
        row = self.crear_campo(frame, "Total Activos:", resumen["total_activos"], row)
        row = self.crear_campo(frame, "Costo Base:", f"${resumen['total_costo']:,.2f}", row)
        row = self.crear_campo(frame, "Valor Actual:", f"${resumen['total_valor']:,.2f}", row)

        color_gan = self.obtener_color_ganancia(resumen["total_ganancia"])
        row = self.crear_campo(
            frame,
            "Ganancia Total:",
            f"${resumen['total_ganancia']:,.2f} ({resumen['ganancia_pct']:+.2f}%)",
            row,
            fg_valor=color_gan,
        )

        # ========== GRÁFICO EVOLUCIÓN TOP 5 (carga asíncrona) ==========
        row = self.crear_seccion(frame, f"Rendimiento Top {self.top} (6m):", row)
        frame_chart = tk.Frame(frame, bg=self.CG_COLOR)
        frame_chart.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        tk.Label(
            frame_chart,
            text="Cargando datos históricos...",
            bg=self.CG_COLOR,
            fg="gray",
            font=("Segoe UI", 8),
        ).pack()
        row += 1

        def _cargar_y_render():
            df_hist = self._fetch_historico_yfinance()
            frame_chart.after(0, lambda: self._render_grafico_evolucion(frame_chart, df_hist))

        threading.Thread(target=_cargar_y_render, daemon=True).start()

        # ========== CONTROL DE APALANCAMIENTO + SIMULADOR ==========
        apal = self._evaluar_apalancamiento(resumen["total_valor"])
        if apal:
            p = self._LEVERAGE_PARAMS
            margen_max = max(0.0, apal["netliq"] * p["max_leverage"] - apal["gross_pos"])

            row = self.crear_seccion(frame, "Control de Apalancamiento (IB)", row)

            # fila input integrada en la misma sección
            fr_sim = tk.Frame(frame, bg=self.BG_COLOR)
            fr_sim.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=4)
            tk.Label(
                fr_sim,
                text=f"Invertir adicional (máx. ${margen_max:,.0f}):",
                bg=self.BG_COLOR,
                fg="black",
                font=("Segoe UI", 9),
            ).pack(side="left")
            entry_sim = tk.Entry(fr_sim, width=12, bg=self.ENTRY_BG, fg="white", font=("Segoe UI", 9), relief="flat")
            entry_sim.insert(0, "0")
            entry_sim.pack(side="left", padx=6)
            tk.Button(
                fr_sim,
                text="Calcular",
                bg="DarkCyan",
                fg="white",
                width=10,
                font=("Segoe UI", 9),
                command=lambda: _simular(),
            ).pack(side="left", padx=4)
            row += 1

            # tabla principal: todas las métricas con Actual | Proyectado | Δ
            cols_cmp = ("Métrica", "Actual", "Proyectado", "Δ")
            tv_cmp = ttk.Treeview(frame, columns=cols_cmp, show="headings", height=12)
            for c, w, anc in zip(cols_cmp, (200, 130, 120, 90), ("w", "e", "e", "e")):
                tv_cmp.heading(c, text=c)
                tv_cmp.column(c, width=w, anchor=anc)
            tv_cmp.grid(row=row, column=0, columnspan=2, padx=10, pady=4, sticky="ew")
            row += 1

            # tabla proyección temporal
            row = self.crear_seccion(frame, "Proyección de costos de interés", row)
            cols_proy = ("Período", "Int. Acumulada ($)", "% de NetLiq", "Margen libre ($)")
            tv_proy = ttk.Treeview(frame, columns=cols_proy, show="headings", height=4)
            for c, w, anc in zip(cols_proy, (90, 150, 130, 170), ("w", "e", "e", "e")):
                tv_proy.heading(c, text=c)
                tv_proy.column(c, width=w, anchor=anc)
            tv_proy.grid(row=row, column=0, columnspan=2, padx=10, pady=4, sticky="ew")
            row += 1

            def _simular():
                def _delta_str(v_new, v_cur, fmt=".2f"):
                    d = v_new - v_cur
                    return f"{d:+{fmt}}" if d != 0 else "–"

                def _col_lev(v):
                    return (
                        "red" if v >= p["max_leverage"] else ("orange" if v >= p["max_leverage"] * 0.9 else "#2ecc71")
                    )

                def _col_risk(v):
                    return "red" if v >= 2.0 else ("orange" if v >= 1.5 else "#2ecc71")

                def _col_int(v):
                    mx = p["max_monthly_interest_pct"]
                    return "red" if v >= mx else ("orange" if v >= mx * 0.8 else "white")

                try:
                    extra = float(entry_sim.get().replace(",", "") or 0)
                except ValueError:
                    return

                new_gross = apal["gross_pos"] + extra
                new_lev = new_gross / apal["netliq"]
                new_deuda = max(0.0, new_gross - apal["netliq"])
                new_int_m = new_deuda * p["tasa_ib"] / 12
                new_int_a = new_deuda * p["tasa_ib"]
                new_risk = new_lev * apal["beta_portfolio"]
                new_cost_pct = new_int_m / apal["netliq"] if apal["netliq"] > 0 else 0
                new_margen = max(0.0, apal["netliq"] * p["max_leverage"] - new_gross)
                cur_int_m = apal["monthly_interest"]
                cur_int_a = cur_int_m * 12
                cur_margen = max(0.0, apal["netliq"] * p["max_leverage"] - apal["gross_pos"])
                # usar apal["deuda"] (abs(cashbalance) si <0) — misma fuente que el panel
                risk_cur = (apal["deuda"] / max(apal["netliq"], 1.0)) * apal["beta_portfolio"]
                risk_new = (new_deuda / max(apal["netliq"], 1.0)) * apal["beta_portfolio"]
                mrs_cur = margin_risk_status(risk_cur)
                mrs_new = margin_risk_status(risk_new)

                # filas: (métrica, actual, proyectado, Δ, tag_color)
                filas = [
                    ("Net Liquidation ($)", f"${apal['netliq']:,.2f}", "–", "–", "white"),
                    (
                        "Gross Position ($)",
                        f"${apal['gross_pos']:,.2f}",
                        f"${new_gross:,.2f}",
                        f"${extra:+,.0f}",
                        "white",
                    ),
                    (
                        "Deuda ($)",
                        f"${apal['deuda']:,.2f}",
                        f"${new_deuda:,.2f}",
                        _delta_str(new_deuda, apal["deuda"], ",.0f"),
                        "white",
                    ),
                    (
                        "Leverage",
                        f"{apal['leverage']:.2f}x  (máx {p['max_leverage']}x)",
                        f"{new_lev:.2f}x",
                        _delta_str(new_lev, apal["leverage"]),
                        _col_lev(new_lev),
                    ),
                    ("Leverage máx dinámico", f"{apal['leverage_max_din']:.2f}x  (= 2 / β)", "–", "–", "white"),
                    (
                        "Beta Portfolio",
                        f"{apal['beta_portfolio']:.2f}  (target {p['target_beta_portfolio']})",
                        "–",
                        "–",
                        apal["color_beta"],
                    ),
                    (
                        "Risk Real (Lev×Beta)",
                        f"{apal['risk_real']:.2f}  (límite 2.0)",
                        f"{new_risk:.2f}",
                        _delta_str(new_risk, apal["risk_real"]),
                        _col_risk(new_risk),
                    ),
                    (
                        "% Mrg/Risk",
                        f"{risk_cur:.1%} {mrs_cur['emoji']} {mrs_cur['estado']} — {mrs_cur['accion']}",
                        f"{risk_new:.1%} {mrs_new['emoji']} {mrs_new['estado']} — {mrs_new['accion']}",
                        _delta_str(risk_new, risk_cur, ".1%"),
                        mrs_cur["color"],
                    ),
                    (
                        "Interés mensual ($)",
                        f"${cur_int_m:,.2f}  ({apal['interest_source']})",
                        f"${new_int_m:,.2f}",
                        f"${new_int_m - cur_int_m:+,.2f}",
                        "white",
                    ),
                    (
                        "Interés anual ($)",
                        f"${cur_int_a:,.2f}",
                        f"${new_int_a:,.2f}",
                        f"${new_int_a - cur_int_a:+,.2f}",
                        "white",
                    ),
                    (
                        "Costo % NetLiq/mes",
                        f"{apal['interest_pct']:.3%}  (máx {p['max_monthly_interest_pct']:.0%})",
                        f"{new_cost_pct:.3%}",
                        _delta_str(new_cost_pct, apal["interest_pct"], ".3%"),
                        _col_int(new_cost_pct),
                    ),
                    (
                        "Margen libre ($)",
                        f"${cur_margen:,.0f}",
                        f"${new_margen:,.0f}",
                        f"${new_margen - cur_margen:+,.0f}",
                        "white",
                    ),
                ]

                tv_cmp.delete(*tv_cmp.get_children())
                for idx, (metrica, actual, proy, delta, color) in enumerate(filas):
                    tag = f"row{idx}"
                    tv_cmp.insert("", "end", values=(metrica, actual, proy, delta), tags=(tag,))
                    tv_cmp.tag_configure(tag, foreground=color)

                # proyección temporal
                tv_proy.delete(*tv_proy.get_children())
                for meses, label in ((1, "1 mes"), (3, "3 meses"), (6, "6 meses"), (12, "12 meses")):
                    int_acum = new_int_m * meses
                    pct_netliq = int_acum / apal["netliq"] if apal["netliq"] > 0 else 0
                    tv_proy.insert(
                        "",
                        "end",
                        values=(
                            label,
                            f"${int_acum:,.2f}",
                            f"{pct_netliq:.3%}",
                            f"${max(0.0, new_margen - int_acum):,.0f}",
                        ),
                    )

            _simular()  # mostrar estado actual al abrir

    def obtener_lotes_desde_info(self):
        """Obtiene lotes desde self.positions para Stock"""
        try:
            lotes = []

            for position in self.positions:
                cantidad = float(position.get("position", 0))
                if cantidad <= 0:
                    continue

                costo_base = float(position.get("costobase", 0))
                precio_actual = float(position.get("mrkprice", 0))
                lote = {
                    "symbol": position.get("ticket", ""),
                    "cantidad": cantidad,
                    "costo_base": costo_base,
                    "precio_actual": precio_actual,
                    "valor_actual": 0,
                    "ganancia_abs": 0,
                    "ganancia_pct": 0,
                    "beta": 1.0,
                }

                if precio_actual > 0:
                    lote["valor_actual"] = cantidad * precio_actual
                    if costo_base > 0:
                        lote["ganancia_abs"] = lote["valor_actual"] - costo_base
                        lote["ganancia_pct"] = ((lote["valor_actual"] / costo_base) - 1) * 100

                lotes.append(lote)

            # Enriquecer con beta desde tabla market — una sola consulta bulk
            if lotes and self.account:
                market = MarketScreen()
                result = market.select(account=self.account, tipo="Dividends")
                if result:
                    rows, ix = result
                    if rows and ix:
                        beta_map = {dict(zip(ix, row))["symbol"]: dict(zip(ix, row)).get("beta") for row in rows}
                        for lote in lotes:
                            beta_val = beta_map.get(lote["symbol"])
                            if beta_val is not None:
                                try:
                                    lote["beta"] = float(beta_val)
                                except (TypeError, ValueError):
                                    pass

            self.df_lotes = pd.DataFrame(lotes)
            return len(self.df_lotes)

        except Exception as e:
            _logger.error(f"obtener_lotes_desde_info(): {e}")
            return 0

    def obtener_resumen(self):
        """Obtiene resumen de cartera stock"""
        if self.df_lotes.empty:
            return {
                "total_activos": 0,
                "total_costo": 0,
                "total_valor": 0,
                "total_ganancia": 0,
                "ganancia_pct": 0,
            }

        total_costo = self.df_lotes["costo_base"].sum()
        total_valor = self.df_lotes["valor_actual"].sum()
        total_ganancia = self.df_lotes["ganancia_abs"].sum()
        ganancia_pct = ((total_valor / total_costo) - 1) * 100 if total_costo > 0 else 0

        return {
            "total_activos": len(self.df_lotes),
            "total_costo": total_costo,
            "total_valor": total_valor,
            "total_ganancia": total_ganancia,
            "ganancia_pct": ganancia_pct,
        }

    def _evaluar_apalancamiento(self, total_valor):
        """Calcula métricas de apalancamiento y semáforos de riesgo.
        Usa stockmarketvalue e interest del ledger IB cuando están disponibles.
        """
        from Class_customer import DataHub  # import diferido — evita ciclo: Class_Analisis→Class_customer

        def _semaforo(valor, umbral_warn, umbral_alert):
            if valor >= umbral_alert:
                return "red"
            if valor >= umbral_warn:
                return "orange"
            return "green"

        if not self.summary or self.df_lotes.empty or total_valor <= 0:
            return None

        base = self.summary.get("BASE", {})
        netliq = float(base.get("netliquidationvalue") or 0)
        if netliq <= 0:
            return None

        p = self._LEVERAGE_PARAMS

        # Preferir stockmarketvalue del ledger (fuente IB) sobre total calculado desde posiciones
        gross_pos = float(base.get("stockmarketvalue") or 0) or total_valor
        leverage = gross_pos / netliq

        total_w = self.df_lotes["valor_actual"].sum()
        if total_w > 0 and "beta" in self.df_lotes.columns:
            beta_port = float((self.df_lotes["valor_actual"] * self.df_lotes["beta"]).sum() / total_w)
        else:
            beta_port = 1.0
        beta_port = max(beta_port, 0.1)
        DataHub.manager_GyP["Stock"]["BetaPortfolio"] = round(beta_port, 3)

        risk_real = leverage * beta_port
        cash_balance = float(base.get("cashbalance") or 0)
        deuda = abs(cash_balance) if cash_balance < 0 else max(0.0, gross_pos - netliq)
        leverage_max_din = 2.0 / beta_port

        # Interés real del ledger IB (MTD accrued); si no hay, estimar con tasa_ib
        interest_real = float(base.get("interest") or 0)
        if interest_real != 0:
            monthly_interest = abs(interest_real)
            interest_source = "IB real"
        else:
            monthly_interest = deuda * p["tasa_ib"] / 12
            interest_source = "estimado"
        interest_pct = monthly_interest / netliq

        return {
            "netliq": netliq,
            "gross_pos": gross_pos,
            "leverage": leverage,
            "beta_portfolio": beta_port,
            "risk_real": risk_real,
            "deuda": deuda,
            "monthly_interest": monthly_interest,
            "interest_source": interest_source,
            "interest_pct": interest_pct,
            "leverage_max_din": leverage_max_din,
            "color_leverage": _semaforo(leverage, p["max_leverage"] * 0.9, p["max_leverage"]),
            "color_beta": _semaforo(beta_port, p["target_beta_portfolio"], p["max_beta_portfolio"]),
            "color_risk": _semaforo(risk_real, 1.5, 2.0),
            "color_interest": _semaforo(
                interest_pct, p["max_monthly_interest_pct"] * 0.8, p["max_monthly_interest_pct"]
            ),
        }
