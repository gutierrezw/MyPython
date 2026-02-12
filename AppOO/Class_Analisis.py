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
from Modulos_Mysql import BDsystem, PlanInversion
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

    def crear_grafico_evolucion_top(self, parent, df_historico, fondos_list, titulo, row, color_titulo="#27ae60"):
        """
        Crea gráfico de líneas con evolución histórica del rendimiento acumulado.

        Args:
            parent: Frame padre
            df_historico: DataFrame con historial (columnas: fecha, fondo, valorActual)
            fondos_list: Lista de nombres de fondos a graficar
            titulo: Título del gráfico
            row: Fila donde ubicar
            color_titulo: Color del título (verde para mejores, rojo para peores)

        Returns:
            int: Siguiente fila disponible
        """
        if df_historico.empty or not fondos_list:
            return row

        try:
            # Filtrar y preparar datos
            df_filtered = df_historico[df_historico["fondo"].isin(fondos_list)].copy()
            if df_filtered.empty:
                return row

            df_filtered["fecha"] = pd.to_datetime(df_filtered["fecha"])
            df_filtered = df_filtered.sort_values(["fondo", "fecha"])

            # Calcular rendimiento acumulado desde el inicio
            df_filtered["rendimiento_pct"] = df_filtered.groupby("fondo")["valorActual"].transform(
                lambda x: (x / x.iloc[0] - 1) * 100
            )

            # Crear figura
            fg = Figure(figsize=(5.4, 3.0), dpi=100)
            fg.patch.set_facecolor(self.CG_COLOR)

            ax = fg.add_subplot(111)
            ax.set_facecolor(self.CG_COLOR)
            p_legend = []

            # Graficar cada fondo
            for fondo in fondos_list:
                data = df_filtered[df_filtered["fondo"] == fondo]
                if not data.empty:
                    (Plot,) = ax.plot(
                        data["fecha"],
                        data["rendimiento_pct"],
                        # label=fondo[:25],
                        linewidth=1.0,
                        alpha=0.85,
                    )
                    color_asignado = Plot.get_color()
                    p_legend.append(mpatches.Patch(label=fondo[:25], color=color_asignado))

            # Estilo
            ax.set_xlabel("", fontsize=7, color="white")
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
            ax.set_ylabel("Rendimiento Acumulado (%)", fontsize=7, color="white")
            ax.yaxis.set_label_position("right")
            ax.axhline(y=0, color="gray", linestyle="-", linewidth=0.5, alpha=0.5)
            ax.grid(True, alpha=0.3, color="gray")
            ax.tick_params(colors="white", labelsize=7)
            ax.tick_params(axis="x", rotation=45)

            # ajustes de eje
            ax.spines[["top", "bottom", "left", "right"]].set_visible(False)
            ax.spines.bottom.set_visible(True)
            ax.spines.right.set_visible(True)
            ax.yaxis.tick_right()
            for spine in ax.spines.values():
                spine.set_color("gray")

            fg.legend(loc="outside upper left", handles=p_legend, fontsize=5)
            fg.suptitle(titulo, fontsize=10, color=color_titulo)
            fg.subplots_adjust(left=0.05, right=0.90, top=0.85, bottom=0.20)

            # Insertar en Tkinter
            frame_grafico = tk.Frame(parent, bg=self.CG_COLOR)
            frame_grafico.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

            canvas = FigureCanvasTkAgg(fg, master=frame_grafico)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="x", expand=True)

            return row + 1
        except Exception as e:
            print(f"[crear_grafico_evolucion_top]: {e}")
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
            # self.Top mejores por variación 90 días
            top_mejores = self.df_ultimo.nlargest(self.top, "variacion90dias")["fondo"].tolist()
            row = self.crear_grafico_evolucion_top(
                parent=frame,
                df_historico=self.df_historico,
                fondos_list=top_mejores,
                titulo=f"TOP {self.top:.0f} MEJORES FCIs",
                row=row,
                color_titulo="#f7f7f7ff",
            )

            # self.Top peores por variación 90 días
            top_peores = self.df_ultimo.nsmallest(self.top, "variacion90dias")["fondo"].tolist()
            row = self.crear_grafico_evolucion_top(
                parent=frame,
                df_historico=self.df_historico,
                fondos_list=top_peores,
                titulo=f"TOP {self.top:.0f} PEORES FCIs",
                row=row,
                color_titulo="#f7f7f7ff",
            )

        # ========== GRÁFICOS TOP 5 (Ganadores y Perdedores - todos los FCIs) ==========
        row = self.crear_seccion(frame, "Gráficos Top 5:", row)
        if not self.df_ultimo.empty and "variacion" in self.df_ultimo.columns:
            row = self.crear_grafico_top5(
                parent=frame,
                df=self.df_ultimo,
                columna_nombre="fondo",
                columna_valor="variacion",
                titulo="FCIs GANADORES",
                row=row,
                es_ganadores=True,
            )

            row = self.crear_grafico_top5(
                parent=frame,
                df=self.df_ultimo,
                columna_nombre="fondo",
                columna_valor="variacion",
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
        """Analiza lotes para decisión de venta"""
        if self.df_lotes.empty:
            self.obtener_lotes_desde_info()

        if self.df_lotes.empty:
            return pd.DataFrame()

        # Agregar score del fondo
        if not self.metricas.empty:
            score_map = self.metricas.set_index("fondo")["score_decision"].to_dict()
            pos_map = self.metricas.set_index("fondo")["posicion_relativa"].to_dict()

            self.df_lotes["score_fondo"] = self.df_lotes["fondo"].map(score_map)
            self.df_lotes["posicion_fondo"] = self.df_lotes["fondo"].map(pos_map)

        # Calcular prioridad de venta
        self.df_lotes["prioridad_venta"] = (
            (self.df_lotes["ganancia_pct"] > self.UMBRAL_GANANCIA_MIN).astype(int) * 35
            + (self.df_lotes["posicion_fondo"].fillna(100) > self.UMBRAL_POSICION_MAX).astype(int) * 30
            + (-self.df_lotes["score_fondo"].fillna(0)) * 0.5
        )

        # Clasificar decisión
        def decision_venta(row):
            if row["ganancia_pct"] <= 0:
                return "MANTENER"
            if row["ganancia_pct"] < self.UMBRAL_GANANCIA_MIN:
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

    def __init__(self, master, info, repositorio, colors, vehiculo="Crypto"):
        super().__init__(master, info, repositorio, colors, vehiculo)

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
                    f"Qty: {lote['cantidad']:.6f} | ${lote['valor_actual']:,.2f} | {lote['ganancia_pct']:+.1f}%",
                    row,
                    width=50,
                    fg_valor=color,
                )

    def obtener_lotes_desde_info(self):
        """Obtiene lotes desde self.info para Crypto"""
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
