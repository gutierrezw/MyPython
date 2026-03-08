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

from Modulos_python import (
    tk,
    ttk,
    datetime,
    pd,
    np,
    mpatches,
    mdates,
    traceback,
)
from Modulos_Mysql import BDsystem, PlanInversion, RepositorioOportunidadesBuySell
from Modulos_Comunes import performa_asset, detalle_book, read_csv_insert_diaria, proceso_update_performance
from Modulos_Utilitarios import vehiculo_parm
from Modulos_python import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


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

    def __init__(self, master, info, repositorio, colors, vehiculo):
        """
        Inicializa el análisis base

        Args:
            master: Ventana padre de Tkinter
            info: dict con datos de activos (DataHub.info)
            repositorio: Objeto para queries a BD
            colors: dict con colores de la aplicación
            vehiculo: Tipo de vehículo
        """
        self.master = master
        self.info = info
        self.repositorio = repositorio
        self.colors = colors
        self.vehiculo = vehiculo

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
            print(f"[AnalisisBase.mostrar_ventana]: {e}")
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

    def obtener_color_ganancia(self, valor):
        """Retorna color según ganancia/pérdida"""
        if valor > 0:
            return "green"
        elif valor < 0:
            return "red"
        return self.VALUE_FG

    def crear_grafico_top5(self, parent, df, columna_nombre, columna_valor, titulo, row, es_ganadores=True):
        """
        Crea gráfico de barras horizontales TOP 5.

        Args:
            parent: Frame padre
            df: DataFrame con datos
            columna_nombre: Columna para nombres (eje Y)
            columna_valor: Columna para valores (barras)
            titulo: Título del gráfico
            row: Fila donde ubicar
            es_ganadores: True para ordenar descendente, False para ascendente

        Returns:
            int: Siguiente fila disponible
        """
        if df.empty:
            return row

        # Ordenar y tomar TOP 5
        if es_ganadores:
            top5 = df.nlargest(5, columna_valor)
        else:
            top5 = df.nsmallest(5, columna_valor)

        nombres = [str(n) for n in top5[columna_nombre].values]
        valores = top5[columna_valor].values

        # Crear figura
        fg = Figure(figsize=(5.4, 2.0), dpi=100)
        fg.patch.set_facecolor(self.CG_COLOR)
        fg.suptitle(titulo, fontsize=10, color="white")
        fg.subplots_adjust(left=0.35, right=0.95, top=0.85, bottom=0.10)

        ax = fg.add_subplot(111)
        ax.set_facecolor(self.CG_COLOR)

        colores = ["#024E02" if v > 0 else "#FF4444" for v in valores]
        bars = ax.barh(nombres[::-1], valores[::-1], color=colores[::-1], height=0.6)

        # Texto dentro de las barras
        for bar, val in zip(bars, valores[::-1]):
            x_pos = bar.get_width()
            ha = "right" if x_pos >= 0 else "left"
            offset = -0.02 if x_pos >= 0 else 0.02
            ax.text(
                x_pos + offset,
                bar.get_y() + bar.get_height() / 2,
                f"{val:+.1f}%",
                va="center",
                ha=ha,
                fontsize=7,
                color="white",
                fontweight="bold",
            )

        ax.tick_params(colors="white", labelsize=7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color("gray")
        ax.spines["left"].set_color("gray")
        ax.axvline(x=0, color="gray", linewidth=0.5)

        frame_grafico = tk.Frame(parent, bg=self.CG_COLOR)
        frame_grafico.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        canvas = FigureCanvasTkAgg(fg, master=frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", expand=True)

        return row + 1

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
            df_plot["indice_pct"]  = df_plot[cum_index] * 100

            # --- Figura interactiva con botones de intervalo ---
            INTERVALOS = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "5y": 1825}

            fg = Figure(figsize=(5.4, 2.8), dpi=100)
            fg.patch.set_facecolor(self.CG_COLOR)
            fg.subplots_adjust(left=0.05, right=0.90, top=0.85, bottom=0.20)

            frame_g = tk.Frame(parent, bg=self.CG_COLOR)
            frame_g.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

            canvas = FigureCanvasTkAgg(fg, master=frame_g)
            canvas.get_tk_widget().pack(fill="x", expand=True)

            def _draw(dias):
                """Filtra df_plot al período y redibuja."""
                fecha_desde = df_plot.index.max() - pd.Timedelta(days=dias)
                df = df_plot[df_plot.index >= fecha_desde].copy()
                if df.empty:
                    return

                # Re-normalizar desde la raíz del intervalo seleccionado
                df["cartera_pct"] = (df["CumPort"] - df["CumPort"].iloc[0]) * 100
                df["indice_pct"]  = (df[cum_index]  - df[cum_index].iloc[0])  * 100

                last_c = float(df["cartera_pct"].iloc[-1])
                last_i = float(df["indice_pct"].iloc[-1])
                alpha  = last_c - last_i
                c_alpha = "#2ecc71" if alpha >= 0 else "#e74c3c"

                fg.clear()
                ax = fg.add_subplot(111)
                ax.set_facecolor(self.CG_COLOR)

                dates = df.index
                cart  = df["cartera_pct"].values
                indx  = df["indice_pct"].values

                ax.fill_between(dates, cart, indx, where=(cart >= indx), alpha=0.18, color="#2ecc71", interpolate=True)
                ax.fill_between(dates, cart, indx, where=(cart <  indx), alpha=0.18, color="#e74c3c", interpolate=True)
                ax.plot(dates, cart, color="#27ae60", linewidth=1.2)
                ax.plot(dates, indx, color="#3498db", linewidth=1.2, linestyle="--")

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

                ax.annotate(f"Alpha: {alpha:+.1f}%", xy=(0.02, 0.93),
                            xycoords="axes fraction", fontsize=7,
                            color=c_alpha, fontweight="bold")

                p_legend = [
                    mpatches.Patch(label=f"Cartera ({last_c:+.1f}%)", color="#27ae60"),
                    mpatches.Patch(label=f"{symbol} ({last_i:+.1f}%)", color="#3498db"),
                ]
                fg.legend(handles=p_legend, loc="outside upper left", fontsize=5,
                          facecolor="white", labelcolor="black", framealpha=1.0)
                fg.suptitle(f"Cartera vs {symbol}", fontsize=10, color="white")
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
            _draw(365)

            return row + 1

        except Exception as e:
            print(f"[crear_grafico_vs_indice]: {e}")
            traceback.print_exc()
            return row

    def crear_grafico_top5_periodos(self, parent, df, df_historico, columna_nombre, titulo, row, es_ganadores=True):
        """
        Crea gráfico de barras agrupadas horizontales TOP 5 con variaciones 30d, 60d, 90d y 180d.
        El top 5 se selecciona por variacion30dias. El 180d se calcula desde df_historico.
        Color único por período (coherente con leyenda). Leyenda fondo blanco debajo del título.
        """
        if df.empty:
            return row

        col_ref = "variacion30dias"
        if col_ref not in df.columns:
            return row

        # Un color por período — coherente con la leyenda (sin distinción positivo/negativo)
        PERIOD_CFG = {
            "variacion30dias":  ("30d",  "#ADFF2F"),   # GreenYellow
            "variacion60dias":  ("60d",  "#00CED1"),   # DarkTurquoise
            "variacion90dias":  ("90d",  "#2E8B57"),   # SeaGreen
            "variacion180dias": ("180d", "#9370DB"),   # MediumPurple
        }

        periodos = ["variacion30dias", "variacion60dias", "variacion90dias"]

        # Calcular variacion180dias desde historico
        df = df.copy()
        if not df_historico.empty and "fecha" in df_historico.columns:
            try:
                df_h = df_historico.copy()
                df_h["fecha"] = pd.to_datetime(df_h["fecha"])
                fecha_max = df_h["fecha"].max()
                fecha_180 = fecha_max - pd.Timedelta(days=180)
                df_prev = df_h[df_h["fecha"] <= fecha_180].sort_values("fecha")
                df_prev = df_prev.groupby("fondo").last()[["valorActual"]].reset_index()
                df_prev.columns = ["fondo", "val_180"]
                df_m = df[["fondo", "valorActual"]].copy().merge(df_prev, on="fondo", how="left")
                df_m["variacion180dias"] = ((df_m["valorActual"] / df_m["val_180"]) - 1) * 100
                df = df.merge(df_m[["fondo", "variacion180dias"]], on="fondo", how="left")
                periodos.append("variacion180dias")
            except Exception:
                pass

        periodos_ok = [c for c in periodos if c in df.columns]
        n_p = len(periodos_ok)

        # Selección top 5
        top5 = df.nlargest(5, col_ref) if es_ganadores else df.nsmallest(5, col_ref)
        nombres = top5[columna_nombre].tolist()
        n_fondos = len(nombres)

        # Rango del eje X para offset de etiquetas fuera de la barra
        all_vals = top5[periodos_ok].fillna(0).values.flatten()
        xmax = max(abs(float(all_vals.max())), abs(float(all_vals.min())), 1.0)
        x_label_offset = xmax * 0.02

        # Layout: título (y=0.97) → leyenda (y≈0.89) → gráfico (top=0.78)
        altura = max(3.2, n_fondos * 0.62 + 1.1)
        fg = Figure(figsize=(5.4, altura), dpi=100)
        fg.patch.set_facecolor(self.CG_COLOR)
        fg.suptitle(titulo, fontsize=10, color="white", y=0.97)
        fg.subplots_adjust(left=0.35, right=0.92, top=0.76, bottom=0.08)

        ax = fg.add_subplot(111)
        ax.set_facecolor(self.CG_COLOR)

        bar_h = 0.15
        y_pos = np.arange(n_fondos)
        p_legend = []

        for i, col in enumerate(periodos_ok):
            label, color = PERIOD_CFG[col]
            valores = top5[col].fillna(0).values
            y_offset = (i - (n_p - 1) / 2) * bar_h
            bars = ax.barh(y_pos + y_offset, valores[::-1], height=bar_h, color=color, alpha=0.92)

            # Etiqueta fuera del extremo de la barra (no invade etiquetas del eje Y)
            for bar, val in zip(bars, valores[::-1]):
                x_pos = bar.get_width()
                if x_pos >= 0:
                    x_text = x_pos + x_label_offset
                    ha = "left"
                else:
                    x_text = x_pos - x_label_offset
                    ha = "right"
                ax.text(
                    x_text,
                    bar.get_y() + bar.get_height() / 2,
                    f"{val:+.1f}%",
                    va="center",
                    ha=ha,
                    fontsize=5,
                    color="white",
                    fontweight="bold",
                )

            p_legend.append(mpatches.Patch(label=label, color=color))

        ax.set_yticks(y_pos)
        ax.set_yticklabels(nombres[::-1], fontsize=7, color="white")
        ax.set_xlim(-xmax * 1.18, xmax * 1.18)
        ax.axvline(x=0, color="gray", linewidth=0.5)
        ax.tick_params(colors="white", labelsize=7)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines["bottom"].set_color("gray")
        ax.spines["left"].set_color("gray")

        # Leyenda fondo blanco debajo del título — igual estilo que crear_grafico_evolucion_top
        fg.legend(
            handles=p_legend,
            loc="upper left",
            bbox_to_anchor=(0.0, 0.91),
            bbox_transform=fg.transFigure,
            fontsize=6,
            ncol=n_p,
            facecolor="white",
            labelcolor="black",
            framealpha=1.0,
        )

        frame_grafico = tk.Frame(parent, bg=self.CG_COLOR)
        frame_grafico.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        canvas = FigureCanvasTkAgg(fg, master=frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", expand=True)

        return row + 1

    def _dibujar_evolucion_ax(self, ax, df_historico, fondos_list, titulo_ax, color_titulo):
        """Helper compartido: filtra, calcula rendimiento acumulado y dibuja sobre un eje existente."""
        df_f = df_historico[df_historico["fondo"].isin(fondos_list)].copy()
        if df_f.empty:
            return
        df_f["fecha"] = pd.to_datetime(df_f["fecha"])
        df_f = df_f.sort_values(["fondo", "fecha"])
        df_f["rendimiento_pct"] = df_f.groupby("fondo")["valorActual"].transform(
            lambda x: (x / x.iloc[0] - 1) * 100
        )
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
        ax.set_title(titulo_ax, fontsize=9, color=color_titulo, pad=3)
        ax.legend(handles=p_legend, loc="upper left", fontsize=5,
                  facecolor=self.CG_COLOR, labelcolor="white", framealpha=0.6)

    def crear_grafico_evolucion_top(self, parent, df_historico, fondos_list, titulo, row, color_titulo="#27ae60"):
        """Crea gráfico de líneas con evolución histórica del rendimiento acumulado (subplot único)."""
        if df_historico.empty or not fondos_list:
            return row
        try:
            fg = Figure(figsize=(5.4, 3.0), dpi=100)
            fg.patch.set_facecolor(self.CG_COLOR)
            ax = fg.add_subplot(111)
            self._dibujar_evolucion_ax(ax, df_historico, fondos_list, titulo, color_titulo)
            fg.subplots_adjust(left=0.05, right=0.90, top=0.85, bottom=0.20)

            frame_grafico = tk.Frame(parent, bg=self.CG_COLOR)
            frame_grafico.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
            canvas = FigureCanvasTkAgg(fg, master=frame_grafico)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="x", expand=True)
            return row + 1
        except Exception as e:
            print(f"[crear_grafico_evolucion_top]: {e}")
            return row

    def crear_grafico_evolucion_combinado(self, parent, df_historico, fondos_mejores, fondos_peores, row):
        """Un solo Figure con 2 subplots apilados: MEJORES (verde) arriba, PEORES (naranja) abajo."""
        if df_historico.empty:
            return row
        try:
            n = self.top
            fg = Figure(figsize=(5.4, 5.2), dpi=100)
            fg.patch.set_facecolor(self.CG_COLOR)
            ax1 = fg.add_subplot(211)
            ax2 = fg.add_subplot(212)

            self._dibujar_evolucion_ax(ax1, df_historico, fondos_mejores, f"TOP {n} MEJORES FCIs", "#2ecc71")
            self._dibujar_evolucion_ax(ax2, df_historico, fondos_peores,  f"TOP {n} PEORES FCIs",  "#e67e22")

            fg.subplots_adjust(left=0.05, right=0.88, top=0.97, bottom=0.08, hspace=0.35)

            frame_g = tk.Frame(parent, bg=self.CG_COLOR)
            frame_g.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
            canvas = FigureCanvasTkAgg(fg, master=frame_g)
            canvas.get_tk_widget().pack(fill="x", expand=True)
            canvas.draw()
            return row + 1
        except Exception as e:
            print(f"[crear_grafico_evolucion_combinado]: {e}")
            traceback.print_exc()
            return row

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
            nombres  = [s[:12] for s in df_sorted["symbol"]]
            valores  = df_sorted["ganancia_pct"].values
            valores_usd = df_sorted["valor_actual"].values
            colores  = ["#2ecc71" if v >= 0 else "#e74c3c" for v in valores]

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
                x  = val + offset if val >= 0 else val - offset
                ax.text(x, bar.get_y() + bar.get_height() / 2,
                        f"${usd:,.0f}  {val:+.1f}%",
                        va="center", ha=ha, fontsize=5, color="white")

            fg.suptitle("Detalle de Posiciones", fontsize=9, color="white", y=0.99)
            fg.subplots_adjust(left=0.30, right=0.95, top=0.94, bottom=0.08)

            frame_g = tk.Frame(parent, bg=self.CG_COLOR)
            frame_g.grid(row=row, column=0, columnspan=2, padx=5, pady=3, sticky="ew")
            canvas = FigureCanvasTkAgg(fg, master=frame_g)
            canvas.get_tk_widget().pack(fill="x", expand=True)
            canvas.draw()
            return row + 1

        except Exception as e:
            print(f"[crear_grafico_todas_posiciones]: {e}")
            traceback.print_exc()
            return row

    def crear_grafico_ganadores_perdedores(self, parent, df, col_symbol, col_pct, titulo, row):
        """
        Gráfico de barras horizontales: top 5 ganadores + top 5 perdedores por col_pct.
        df: DataFrame con columnas col_symbol y col_pct (porcentaje float).
        """
        if df is None or df.empty:
            return row
        try:
            top_gan = df[df[col_pct] >= 0].nlargest(5, col_pct)
            top_per = df[df[col_pct] < 0].nsmallest(5, col_pct)
            # Bear market: si no hay positivos, toma los menos negativos
            if top_gan.empty:
                top_gan = df.nlargest(5, col_pct)
            df_chart = pd.concat([
                top_gan.sort_values(col_pct, ascending=True),
                top_per.sort_values(col_pct, ascending=True),
            ]).drop_duplicates(subset=[col_symbol])

            colores = ["#2ecc71" if v >= 0 else "#e74c3c" for v in df_chart[col_pct]]
            nombres = [s[:12] for s in df_chart[col_symbol]]
            valores = df_chart[col_pct].values

            fg = Figure(figsize=(5.4, 2.4), dpi=100)
            fg.patch.set_facecolor(self.CG_COLOR)
            ax = fg.add_subplot(111)
            ax.set_facecolor(self.CG_COLOR)

            bars = ax.barh(nombres, valores, color=colores, height=0.6)
            ax.axvline(0, color="gray", linewidth=0.6)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:+.0f}%"))
            ax.tick_params(colors="white", labelsize=7)
            ax.spines[["top", "right"]].set_visible(False)
            for sp in ["bottom", "left"]:
                ax.spines[sp].set_color("gray")
            ax.grid(axis="x", alpha=0.2, color="gray")

            # etiquetas dentro/fuera de cada barra
            xmax = max(abs(valores)) if len(valores) else 1
            for bar, val in zip(bars, valores):
                offset = xmax * 0.02
                ha = "left" if val >= 0 else "right"
                x  = val + offset if val >= 0 else val - offset
                ax.text(x, bar.get_y() + bar.get_height() / 2,
                        f"{val:+.1f}%", va="center", ha=ha, fontsize=5, color="white")

            fg.suptitle(titulo, fontsize=9, color="white", y=0.98)
            fg.subplots_adjust(left=0.28, right=0.95, top=0.88, bottom=0.15)

            frame_g = tk.Frame(parent, bg=self.CG_COLOR)
            frame_g.grid(row=row, column=0, columnspan=2, padx=5, pady=3, sticky="ew")
            canvas = FigureCanvasTkAgg(fg, master=frame_g)
            canvas.get_tk_widget().pack(fill="x", expand=True)
            canvas.draw()
            return row + 1

        except Exception as e:
            print(f"[crear_grafico_ganadores_perdedores]: {e}")
            traceback.print_exc()
            return row

    def reconstruir_diaria_performance(self, btn=None, lbl=None):
        """
        Versión base: reconstruye diaria_performance + performa_inversion para self.vehiculo.
        Corre en thread daemon para no bloquear la UI.
        """
        def _run():
            try:
                if btn:
                    btn.after(0, lambda: btn.config(state="disabled", text="Procesando..."))
                if lbl:
                    lbl.after(0, lambda: lbl.config(text=""))

                ROp = RepositorioOportunidadesBuySell()
                errores = []

                ses = BDsystem.get_sesion_by_vehiculo(vehiculo=self.vehiculo)
                if not ses or not ses.get("idcuenta"):
                    errores.append("sin sesión configurada")
                else:
                    account = ses["idcuenta"]
                    divisa  = ses.get("idmoneda", "USD")
                    try:
                        book, ix = ROp.select_booktrading(accion="cartera", account=account, idivisa=divisa)
                        path = detalle_book(account=account, vehiculo=self.vehiculo, book=book, ix=ix)
                        if path is None:
                            errores.append("detalle_book sin path")
                        else:
                            read_csv_insert_diaria(path=path, insert=True)
                            proceso_update_performance(account=account, vehiculo=self.vehiculo)
                    except Exception as e:
                        errores.append(str(e))
                        print(f"[reconstruir_diaria_performance/{self.vehiculo}]: {e}")

                msg   = "✓ Reconstruido" if not errores else f"Errores: {'; '.join(errores)}"
                color = "#2ecc71" if not errores else "#e74c3c"
                if lbl:
                    lbl.after(0, lambda: lbl.config(text=msg, fg=color))
                if btn:
                    btn.after(0, lambda: btn.config(state="normal", text="Reconstruir Performance"))

            except Exception as e:
                print(f"[reconstruir_diaria_performance]: {e}")
                if btn:
                    btn.after(0, lambda: btn.config(state="normal", text="Reconstruir Performance"))

        threading.Thread(target=_run, daemon=True).start()


class AnalisisFCI(AnalisisBase):
    """Análisis específico para Fondos Comunes de Inversión"""

    # Parámetros de decisión
    UMBRAL_GANANCIA_MIN = 5  # % mínimo de ganancia para vender
    UMBRAL_POSICION_MAX = 90  # % cerca del máximo histórico
    DIAS_HOLDING_MIN = 7  # días mínimos de holding

    def __init__(self, master, info, repositorio, colors, vehiculo="BBVA.ARS"):
        super().__init__(master, info, repositorio, colors, vehiculo)
        self.vehiculo = vehiculo
        self.top = 3
        self.df_historico = pd.DataFrame()
        self.df_ultimo = pd.DataFrame()
        self.metricas = pd.DataFrame()

    def reconstruir_diaria_performance(self, btn=None, lbl=None):
        """
        Reconstruye diaria_performance y performa_inversion para todas las cuentas FCI.
        Flujo por cuenta:
          1) booktrading → detalle_book() → CSV
          2) read_csv_insert_diaria(insert=True) → actualiza diaria_performance
          3) proceso_update_performance()       → actualiza performa_inversion
        Corre en thread para no bloquear la UI.
        """
        def _run():
            try:
                if btn:
                    btn.config(state="disabled", text="Procesando...")
                if lbl:
                    lbl.config(text="")

                ROp = RepositorioOportunidadesBuySell()
                errores = []

                for veh in (self.vehiculo, "SANT.ARS"):
                    try:
                        ses = BDsystem.get_sesion_by_vehiculo(vehiculo=veh)
                        if not ses or not ses.get("idcuenta"):
                            continue
                        account = ses["idcuenta"]
                        divisa  = ses.get("idmoneda", "ARS")

                        # 1. booktrading completo → CSV
                        book, ix = ROp.select_booktrading(accion="cartera", account=account, idivisa=divisa)
                        path = detalle_book(account=account, vehiculo=self.vehiculo, book=book, ix=ix)
                        if path is None:
                            errores.append(f"{veh}: detalle_book sin path")
                            continue

                        # 2. CSV → diaria_performance (solo inserta filas > last Date)
                        read_csv_insert_diaria(path=path, insert=True)

                        # 3. diaria_performance → performa_inversion
                        proceso_update_performance(account=account, vehiculo=self.vehiculo)

                    except Exception as e:
                        errores.append(f"{veh}: {e}")
                        print(f"[reconstruir_diaria_performance/{veh}]: {e}")

                # Feedback en UI (desde thread → after)
                msg = "✓ Reconstruido" if not errores else f"Errores: {'; '.join(errores)}"
                color = "#2ecc71" if not errores else "#e74c3c"
                if lbl:
                    lbl.after(0, lambda: lbl.config(text=msg, fg=color))
                if btn:
                    btn.after(0, lambda: btn.config(state="normal", text="Reconstruir Performance"))

            except Exception as e:
                print(f"[reconstruir_diaria_performance]: {e}")
                if btn:
                    btn.after(0, lambda: btn.config(state="normal", text="Reconstruir Performance"))

        threading.Thread(target=_run, daemon=True).start()

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

        # ========== GRÁFICOS EVOLUCIÓN HISTÓRICA (Rendimiento 90d) ==========
        row = self.crear_seccion(frame, f"Rendimiento Posiciones:", row)
        if not self.df_historico.empty and not self.df_ultimo.empty:
            top_mejores = self.df_ultimo.nlargest(self.top, "variacion90dias")["fondo"].tolist()
            top_peores  = self.df_ultimo.nsmallest(self.top, "variacion90dias")["fondo"].tolist()
            row = self.crear_grafico_evolucion_combinado(
                parent=frame,
                df_historico=self.df_historico,
                fondos_mejores=top_mejores,
                fondos_peores=top_peores,
                row=row,
            )

        # ========== CARTERA VS ÍNDICE DE REFERENCIA ==========
        row = self.crear_seccion(frame, f"Cartera vs Índice:", row)

        # Botón reconstruir diaria_performance + performa_inversion
        frame_btn = tk.Frame(frame, bg=self.BG_COLOR)
        frame_btn.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 4))
        lbl_status = tk.Label(frame_btn, text="", bg=self.BG_COLOR, fg="#2ecc71", font=("Segoe UI", 8))
        btn_rebuild = tk.Button(
            frame_btn,
            text="Reconstruir Performance",
            bg="gray",
            fg="white",
            width=22,
        )
        btn_rebuild.config(command=lambda: self.reconstruir_diaria_performance(btn=btn_rebuild, lbl=lbl_status))
        btn_rebuild.pack(side="left")
        lbl_status.pack(side="left", padx=8)
        row += 1

        row = self.crear_grafico_vs_indice(parent=frame, row=row)

        # ========== GRÁFICOS TOP 5 (Ganadores y Perdedores — 30d / 60d / 90d / 180d) ==========
        row = self.crear_seccion(frame, "Gráficos Top 5:", row)
        if not self.df_ultimo.empty and "variacion30dias" in self.df_ultimo.columns:
            row = self.crear_grafico_top5_periodos(
                parent=frame,
                df=self.df_ultimo,
                df_historico=self.df_historico,
                columna_nombre="fondo",
                titulo="FCIs GANADORES",
                row=row,
                es_ganadores=True,
            )

            row = self.crear_grafico_top5_periodos(
                parent=frame,
                df=self.df_ultimo,
                df_historico=self.df_historico,
                columna_nombre="fondo",
                titulo="FCIs PERDEDORES",
                row=row,
                es_ganadores=False,
            )

        # ========== RANKING DE FONDOS ==========
        if not self.metricas.empty:
            ranking = self.metricas.nlargest(10, "score_decision")
            columnas = [
                ("fondo", "Fondo", 145),
                ("score_decision", "Score", 50),
                ("senal", "Señal", 75),
                ("rendimiento_total", "Rend%", 50),
                ("volatilidad", "Volat.", 45),
                ("sharpe_ratio", "Sharpe", 50),
                ("drawdown_max", "MaxDD%", 55),
                ("posicion_relativa", "PosRel%", 55),
            ]
            row = self.crear_treeview_ranking(
                parent=frame,
                df=ranking,
                columnas=columnas,
                titulo="Ranking Fondos (Score)",
                row=row,
                height=min(10, len(ranking)),
            )

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

    def cargar_datos_historicos(self):
        """Carga historial de precios desde diaria_cnv"""
        try:
            conn = BDsystem.connect_dbase("select.diaria_cnv", False)
            query = """
                SELECT * FROM bdinv.diaria_cnv
                ORDER BY fecha DESC
            """
            self.df_historico = pd.read_sql(query, conn)
            conn.close()

            if not self.df_historico.empty:
                self.df_historico["fecha"] = pd.to_datetime(self.df_historico["fecha"])
                ultima_fecha = self.df_historico["fecha"].max()
                self.df_ultimo = self.df_historico[self.df_historico["fecha"] == ultima_fecha].copy()

            return len(self.df_historico)
        except Exception as e:
            print(f"[cargar_datos_historicos]: {e}")
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
            print(f"[obtener_lotes_desde_info]: {e}")
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
            print(f"[calcular_metricas_todos]: {e}")
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
            print(f"[analizar_lotes_venta] No se pudo leer gypPrecio, usando default {self.UMBRAL_GANANCIA_MIN}%: {e}")

        # Agregar score del fondo
        if not self.metricas.empty:
            score_map = self.metricas.set_index("fondo")["score_decision"].to_dict()
            pos_map = self.metricas.set_index("fondo")["posicion_relativa"].to_dict()

            self.df_lotes["score_fondo"] = self.df_lotes["fondo"].map(score_map)
            self.df_lotes["posicion_fondo"] = self.df_lotes["fondo"].map(pos_map)

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

    def _poblar_contenido(self, frame):
        """Implementación específica para Crypto"""
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

        # ========== TOP 5 GANADORES / PERDEDORES (gráfico barras) ==========
        if not self.df_lotes.empty:
            row = self.crear_grafico_ganadores_perdedores(
                parent=frame,
                df=self.df_lotes,
                col_symbol="symbol",
                col_pct="ganancia_pct",
                titulo="Top 5 Ganadores / Perdedores",
                row=row,
            )

        # ========== DETALLE DE POSICIONES (gráfico barras todas) ==========
        if not self.df_lotes.empty:
            row = self.crear_grafico_todas_posiciones(
                parent=frame,
                df=self.df_lotes,
                row=row,
            )

        # ========== CARTERA VS ÍNDICE ==========
        row = self.crear_seccion(frame, "Cartera vs Índice:", row)

        frame_btn = tk.Frame(frame, bg=self.BG_COLOR)
        frame_btn.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 4))
        lbl_status = tk.Label(frame_btn, text="", bg=self.BG_COLOR, fg="#2ecc71", font=("Segoe UI", 8))
        btn_rebuild = tk.Button(frame_btn, text="Reconstruir Performance", bg="gray", fg="white", width=22)
        btn_rebuild.config(command=lambda: self.reconstruir_diaria_performance(btn=btn_rebuild, lbl=lbl_status))
        btn_rebuild.pack(side="left")
        lbl_status.pack(side="left", padx=8)
        row += 1

        row = self.crear_grafico_vs_indice(parent=frame, row=row)

    def obtener_lotes_desde_info(self):
        """Obtiene lotes desde self._positions (lista de DataHub.positions)"""
        try:
            lotes = []

            for pos in self._positions:
                if not isinstance(pos, dict):
                    continue

                cantidad  = float(pos.get("position", 0))
                costobase = float(pos.get("costobase", 0))
                mrkprice  = float(pos.get("mrkprice", 0))

                if cantidad <= 0:
                    continue

                valor_actual = cantidad * mrkprice if mrkprice > 0 else 0
                ganancia_abs = valor_actual - costobase if costobase > 0 else 0
                ganancia_pct = ((valor_actual / costobase) - 1) * 100 if costobase > 0 else 0

                lotes.append({
                    "symbol":       pos.get("ticket", ""),
                    "cantidad":     cantidad,
                    "costo_base":   costobase,
                    "precio_actual": mrkprice,
                    "valor_actual": valor_actual,
                    "ganancia_abs": ganancia_abs,
                    "ganancia_pct": ganancia_pct,
                })

            self.df_lotes = pd.DataFrame(lotes)
            return len(self.df_lotes)

        except Exception as e:
            print(f"[AnalisisCrypto.obtener_lotes_desde_info]: {e}")
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

    def __init__(self, master, info, repositorio, colors, vehiculo="Stock"):
        super().__init__(master, info, repositorio, colors, vehiculo)

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

        # ========== TOP GANADORES ==========
        row = self.crear_seccion(frame, "Top 5 Ganadores", row)
        if not self.df_lotes.empty:
            top_ganadores = self.df_lotes.nlargest(5, "ganancia_pct")
            for _, lote in top_ganadores.iterrows():
                color = self.obtener_color_ganancia(lote["ganancia_pct"])
                row = self.crear_campo(
                    frame,
                    f"{lote['symbol'][:15]}:",
                    f"${lote['valor_actual']:,.2f}  |  {lote['ganancia_pct']:+.2f}%",
                    row,
                    fg_valor=color,
                )

        # ========== TOP PERDEDORES ==========
        row = self.crear_seccion(frame, "Top 5 Perdedores", row)
        if not self.df_lotes.empty:
            top_perdedores = self.df_lotes.nsmallest(5, "ganancia_pct")
            for _, lote in top_perdedores.iterrows():
                color = self.obtener_color_ganancia(lote["ganancia_pct"])
                row = self.crear_campo(
                    frame,
                    f"{lote['symbol'][:15]}:",
                    f"${lote['valor_actual']:,.2f}  |  {lote['ganancia_pct']:+.2f}%",
                    row,
                    fg_valor=color,
                )

        # ========== DETALLE DE POSICIONES ==========
        row = self.crear_seccion(frame, "Detalle de Posiciones", row)
        if not self.df_lotes.empty:
            for _, lote in self.df_lotes.sort_values("valor_actual", ascending=False).iterrows():
                color = self.obtener_color_ganancia(lote["ganancia_pct"])
                row = self.crear_campo(
                    frame,
                    f"{lote['symbol'][:15]}:",
                    f"Qty: {lote['cantidad']:.0f} | ${lote['valor_actual']:,.2f} | {lote['ganancia_pct']:+.1f}%",
                    row,
                    width=50,
                    fg_valor=color,
                )

    def obtener_lotes_desde_info(self):
        """Obtiene lotes desde self.info para Stock"""
        try:
            lotes = []

            for symbol, data in self.info.items():
                if symbol == "TimeDataHub" or not isinstance(data, dict):
                    continue

                position = data.get("position", {})
                if not position:
                    continue

                lote = {
                    "symbol": symbol,
                    "cantidad": float(position.get("position", 0)),
                    "costo_base": float(data.get("costobase", 0) or position.get("costobase", 0)),
                    "precio_actual": float(position.get("mrkprice", 0)),
                    "valor_actual": 0,
                    "ganancia_abs": 0,
                    "ganancia_pct": 0,
                }

                if lote["cantidad"] > 0 and lote["precio_actual"] > 0:
                    lote["valor_actual"] = lote["cantidad"] * lote["precio_actual"]
                    if lote["costo_base"] > 0:
                        lote["ganancia_abs"] = lote["valor_actual"] - lote["costo_base"]
                        lote["ganancia_pct"] = ((lote["valor_actual"] / lote["costo_base"]) - 1) * 100

                if lote["cantidad"] > 0:
                    lotes.append(lote)

            self.df_lotes = pd.DataFrame(lotes)
            return len(self.df_lotes)

        except Exception as e:
            print(f"[AnalisisStock.obtener_lotes_desde_info]: {e}")
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
