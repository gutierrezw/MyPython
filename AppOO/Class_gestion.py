from Class_DataFrame import chart_margen_neto, chart_trazaplan, cagar_archivo
from Modulos_Mysql import (
    PlanInversion,
    RepositorioOportunidadesBuySell,
    IPerformance,
    BDsystem,
)
from Modulos_python import (
    tk,
    ttk,
    pd,
    Figure,
    FigureCanvasTkAgg,
    E,
    W,
    S,
    N,
    datetime,
    timedelta,
    traceback,
)
from Class_customer import MyMessageBox, CustomTreeview, DataHub


class GestionInversion(tk.Frame):
    def __init__(self, parent=None, master=None, colores=None):
        super().__init__(parent)
        self.root = master
        self.colors = colores
        self.bgcolor = self.colors["bgcolor"]
        self.cgcolor = self.colors["cgcolor"]
        self.cchart = self.colors["cchart"]
        self.threads = []
        self.titulo = [
            "Depositos",
            "Retiros",
            "Crecimiento",
            "Dividendos",
            "Perdidas",
            "Fee",
            "Comisiones",
            "Tax",
            "Value",
            "Costo Base",
            "Devengado",
            "Intereses",
            "Income-Cost",
            "%Margen OP.",
        ]
        self.plan = {}
        self.type_extract = {
            "Resumen": 0,
            "Stock": 1,
            "Crypto": 2,
            "BotCrypto": 3,
            "BBVA.ARS": 4,
            "SANT.ARS": 5,
        }
        self.datsess = None
        self.indice = 0
        self.dw = 1290
        self.dh = 700
        self.df = 1297

        # def de frame
        win0 = ttk.Frame(self.root, padding=(1, 1, 1, 1), style="B.TFrame")  # principal
        win1 = ttk.Frame(win0, padding=(1, 1, 1, 1), style="C.TFrame")  # frame superior
        win2 = ttk.Frame(win0, padding=(1, 1, 1, 1), style="B.TFrame")  # frame extracto

        wi10 = ttk.Frame(win1, padding=(1, 1, 1, 1), style="B.TFrame")  # frame izquierda
        wt10 = ttk.Frame(wi10, padding=(1, 1, 1, 1), style="B.TFrame")  # frame derecha
        wt11 = ttk.Frame(wi10, padding=(1, 1, 1, 1), style="B.TFrame")  # frame superior

        wi11 = ttk.Frame(win1, padding=(1, 1, 1, 1), style="C.TFrame")  # frame plan
        wr10 = ttk.Frame(wi11, padding=(1, 1, 1, 1), style="C.TFrame")  # frame plan
        wr11 = ttk.Frame(wi11, padding=(1, 1, 1, 1), style="C.TFrame")  # frame button

        win0.grid(sticky=N + S + E + W)
        win1.pack(side=tk.TOP, pady=10)
        win2.pack(side=tk.TOP, fill=tk.X)
        wi10.pack(side=tk.LEFT)
        wi11.pack(side=tk.LEFT)

        wt10.pack(side=tk.TOP)
        wt11.pack(side=tk.TOP)
        wr10.pack(side=tk.TOP)
        wr11.pack(side=tk.TOP)

        # definición de gráfico ------------------------------------------------------------------------------
        self.fg0 = Figure(figsize=(5.0, 2.1), dpi=100, layout="tight")
        ax = self.fg0.add_subplot()
        self.fg0.set_facecolor(self.colors["bgcolor"])
        self.cv0 = FigureCanvasTkAgg(self.fg0, master=wt10)
        self.cv0.draw()
        self.cv0.get_tk_widget().pack(side=tk.TOP)

        self.fg1 = Figure(figsize=(5.0, 2.1), dpi=100, layout="tight")
        ax = self.fg1.add_subplot()
        self.fg1.set_facecolor(self.colors["bgcolor"])
        self.cv1 = FigureCanvasTkAgg(self.fg1, master=wt11)
        self.cv1.draw()
        self.cv1.get_tk_widget().pack(side=tk.TOP)

        # definición de combobox para selección de extracto (reemplaza botón circular)------------------------
        self.combo_extractos = ttk.Combobox(
            wr11,
            values=list(self.type_extract.keys()),
            state="readonly",
            width=15,
            style="TCombobox",
        )
        self.combo_extractos.set("Resumen")  # Valor inicial
        self.combo_extractos.bind("<<ComboboxSelected>>", self.on_select_extracto)
        self.combo_extractos.pack(side=tk.LEFT, fill=tk.X, padx=5)

        # definición de boton detalle traza plan -------------------------------------------------------------------
        imagen_tk = BDsystem.select_image(idd=17, size=(24, 24))
        self.otro = tk.Button(
            wr11,
            image=imagen_tk,
            text="Detalle Plan",
            bg=self.colors["bgcolor"],
            relief=tk.FLAT,
            command=self.detalle_plan,
        )
        self.otro.imagen = imagen_tk
        self.otro.pack(side=tk.LEFT, fill=tk.X)

        # definición de boton load-----------------------------------------------------------------------------------
        imagen_tk = BDsystem.select_image(idd=300, size=(24, 24))
        self.load = tk.Button(
            wr11,
            image=imagen_tk,
            text="Extracto",
            bg=self.colors["bgcolor"],
            relief=tk.FLAT,
            command=self.add_csv,
        )
        self.load.imagen = imagen_tk
        self.load.pack(side=tk.LEFT, fill=tk.X)

        # definición de boton detalle cierre de mes------------------------------------------------------------------
        imagen_tk = BDsystem.select_image(idd=304, size=(24, 24))
        self.cierre = tk.Button(
            wr11,
            image=imagen_tk,
            text="Cierre Mes",
            bg=self.colors["bgcolor"],
            relief=tk.FLAT,
            command=self.cierre_extractos,
        )
        self.cierre.imagen = imagen_tk
        self.cierre.pack(side=tk.LEFT, fill=tk.X)

        # definición de boton detalle editar plan ------------------------------------------------------------------
        imagen_tk = BDsystem.select_image(idd=303, size=(24, 24))
        self.edit = tk.Button(
            wr11,
            image=imagen_tk,
            text="Edit Plan",
            bg=self.colors["bgcolor"],
            relief=tk.FLAT,
            command=self.edit_plan,
        )
        self.edit.imagen = imagen_tk
        self.edit.pack(side=tk.LEFT, fill=tk.X)

        # definición treeview extractos --------------------------------------------------------------------------
        self.extract = ttk.Treeview(win2, columns=self.titulo, height=10, style="TFrame")
        self.extract.pack(fill=tk.X, expand=True, padx=3)

        self.extract.column("#0", width=92, anchor=tk.E)
        self.extract.heading("#0", text="Extracto")
        for k, column in enumerate(self.titulo):
            self.extract.column(column, width=84, anchor=tk.E)
            self.extract.heading(column, text=column)

        # widget plan de inversión ----------------------------------------------------------------------------------
        self.mpl = [[None] * 10 for _ in range(35)]
        wx11 = tk.Frame(wr10, bg=self.bgcolor)
        wx11.grid(row=0, column=0, padx=1, pady=1)

        # widget para visión del plan
        tit = ["Visión", "Deseada", "Actual", "Indicador", "Objetivo"]
        self.mpl[0][0] = ttk.Button(wx11, text=tit[0], width=17, style="TButton", state="disabled")
        self.mpl[0][1] = ttk.Button(wx11, text=tit[1], width=15, style="TButton", state="disabled")
        self.mpl[0][2] = ttk.Button(wx11, text=tit[2], width=15, style="TButton", state="disabled")
        self.mpl[0][3] = ttk.Button(wx11, text=tit[3], width=15, style="TButton", state="disabled")
        self.mpl[0][4] = ttk.Button(wx11, text=tit[4], width=44, style="TButton", state="disabled")

        # texto Objetivo
        self.mpl[0][5] = tk.Text(
            wx11,
            height=5,
            width=49,
            font=("Segoe UI", 8),
            wrap="word",
            bg=self.bgcolor,
            fg=self.cgcolor,
        )

        self.mpl[0][0].grid(row=0, column=0, pady=1)
        self.mpl[0][1].grid(row=0, column=1, pady=1)
        self.mpl[0][2].grid(row=0, column=2, pady=1)
        self.mpl[0][3].grid(row=0, column=3, pady=1)
        self.mpl[0][4].grid(row=0, column=4, columnspan=4)
        self.mpl[0][5].grid(row=1, column=4, rowspan=4, columnspan=4)

        # localiza cada celda objetivo---------------------------------------------------------------------------------
        for i in range(1, 7):
            for j in range(0, 4):
                self.mpl[i][j] = tk.Label(
                    wx11,
                    text=" ".rjust(12),
                    bg=self.bgcolor,
                    fg="white",
                    font=("Courier", 8),
                    anchor="e",
                )
                self.mpl[i][j].grid(row=i, column=j)

        self.mpl[4][0] = ttk.Separator(wx11, orient="horizontal", style="G.TSeparator")
        self.mpl[5][5] = tk.Label(wx11, text=" divisa USD", bg=self.bgcolor, fg="white", font=("Courier", 8))
        self.mpl[5][6] = tk.Label(
            wx11,
            text=" Ingresos pasivos",
            bg=self.bgcolor,
            fg="white",
            font=("Courier", 8),
        )

        self.mpl[4][0].grid(row=4, column=1, ipadx=140, columnspa=3)
        self.mpl[5][5].grid(row=5, column=3)
        self.mpl[5][6].grid(row=5, column=4, pady=5)

        # treeview plan metas ---------------------------------------------------------------------------------
        _trz_cols = [
            "meta",
            "extracto",
            "vision",
            "capital",
            "dividendos",
            "efectividad",
            "status",
            "recompensa",
        ]
        self.tree_plan = ttk.Treeview(wr10, columns=_trz_cols, show="headings", height=11)
        self.tree_plan.heading("meta", text="Meta", anchor=tk.E)
        self.tree_plan.heading("extracto", text="Extracto", anchor=tk.E)
        self.tree_plan.heading("vision", text="Visión", anchor=tk.E)
        self.tree_plan.heading("capital", text="Capital Inv.", anchor=tk.E)
        self.tree_plan.heading("dividendos", text="Div/año", anchor=tk.E)
        self.tree_plan.heading("efectividad", text="Efectividad", anchor=tk.E)
        self.tree_plan.heading("status", text="Estatus", anchor=tk.W)
        self.tree_plan.heading("recompensa", text="Recompensa", anchor=tk.W)
        self.tree_plan.column("meta", width=80, anchor=tk.E)
        self.tree_plan.column("extracto", width=80, anchor=tk.E)
        self.tree_plan.column("vision", width=90, anchor=tk.E)
        self.tree_plan.column("capital", width=90, anchor=tk.E)
        self.tree_plan.column("dividendos", width=90, anchor=tk.E)
        self.tree_plan.column("efectividad", width=90, anchor=tk.E)
        self.tree_plan.column("status", width=100, anchor=tk.W)
        self.tree_plan.column("recompensa", width=130, anchor=tk.W)
        self.tree_plan.grid(row=1, column=0, padx=2, pady=1)

        # Accesos MySql ----------------------------------------------------------------------------------------------
        self.PlaInversion = PlanInversion()
        self.RepositorioOportunidades = RepositorioOportunidadesBuySell()
        self.Perfoma = IPerformance()

        # información de sesión principal
        lista = self.PlaInversion.select_all_sesion()
        self.sesion = {}
        self.d_extract = None
        for sesion in lista:

            # rechaza los registros q no aplican como vehiculo de inversión
            if (sesion["Pinvertir"] is None or sesion["Pinvertir"] == 0) and sesion["fefund"] is None:
                continue

            # toma información clave fiscal Year
            elif sesion["Idcuenta_principal"]:
                self.fiscalYear = sesion["fiscalYear"]
                self.year = "YE-" + self.fiscalYear.strftime("%b").upper()
                self.month = int(self.fiscalYear.month)

            # crea diccionario de sesiones.
            self.sesion.update({sesion["vehiculo"]: sesion})

        # invoca widget princiapar de gistión
        self.widgets_extractos()

    # mantiene actualizada información de extractos
    def widgets_extractos(self):

        def meses_extract(x_datos=None, extracto=None, parent=None):
            try:
                (
                    ilog,
                    anterior,
                ) = (
                    True,
                    extracto - 1,
                )
                costo_base, nav_cierre, margen_neto = 0.0, 0.0, 0.0

                for idd, fila in x_datos.iterrows():
                    if (idd.month in (8, 9, 10, 11, 12) and idd.year == anterior) or (
                        idd.month in (1, 2, 3, 4, 5, 6, 7) and idd.year == extracto
                    ):

                        if ilog:
                            nav_cierre = fila["navcierre"]
                            costo_base = fila["costobase"]
                            ilog = False
                        marge_neto = (fila["beneficios"] / fila["ingresos"]) if fila["ingresos"] > 0 else 0.0
                        self.extract.insert(
                            parent,
                            tk.END,
                            text=idd.strftime("%b"),
                            values=(
                                "{:10.2f}".format(fila["depositos"]),
                                "{:10.2f}".format(fila["retiros"]),
                                "{:10.2f}".format(fila["crecimiento"]),
                                "{:10.2f}".format(fila["dividendos"]),
                                "{:10.2f}".format(fila["perdidas"]),
                                "{:10.2f}".format(fila["fee"]),
                                "{:10.2f}".format(fila["comisiones"]),
                                "{:10.2f}".format(fila["tax"]),
                                "{:10.2f}".format(fila["navcierre"]),
                                "{:10.2f}".format(fila["costobase"]),
                                "{:10.2f}".format(fila["idevengo"]),
                                "{:10.2f}".format(fila["imargen"]),
                                "{:10.2f}".format(fila["beneficios"]),
                                "{:10.1%}".format(marge_neto),
                            ),
                        )
                return costo_base, nav_cierre
            except Exception as e:
                print("meses_extract(): {}".format(e))
                return 0.0, 0.0

        # Detalles de extracts por year  en stock -------------------------------------------------------------
        def extract_update_treeview(tipo=None):

            # detalle de extracts por year fiscal
            self.extract.item(tipo, open=True)
            for index, row in f_datos[::-1].iterrows():
                extracto = index.year

                margen = row["margen"] if row["margen"] > 0 else 0.0
                parent = self.extract.insert(
                    tipo,
                    tk.END,
                    text="{:<15}".format(extracto),
                    values=(
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ),
                )

                # detalle de extracts correspondientes year-month
                costobase, navcierre = meses_extract(datos, extracto, parent)

                self.extract.item(
                    parent,
                    values=(
                        "{:10.2f}".format(row["depositos"]),
                        "{:10.2f}".format(row["retiros"]),
                        "{:10.2f}".format(row["crecimiento"]),
                        "{:10.2f}".format(row["dividendos"]),
                        "{:10.2f}".format(row["perdidas"]),
                        "{:10.2f}".format(row["fee"]),
                        "{:10.2f}".format(row["comisiones"]),
                        "{:10.2f}".format(row["tax"]),
                        "{:10.2f}".format(navcierre),
                        "{:10.2f}".format(costobase),
                        "{:10.2f}".format(row["idevengo"]),
                        "{:10.2f}".format(row["imargen"]),
                        "{:10.2f}".format(row["beneficios"]),
                        "{:10.1%}".format(margen),
                    ),
                )

            # calcula resumen y muestra
            self.update_first_row_extract(padre=tipo)

        try:
            self.widgets_plan()
            lista = list(self.type_extract.values())

            # Sincronizar combobox con índice actual
            current_index = self.indice % len(lista)
            for nombre, valor in self.type_extract.items():
                if valor == current_index:
                    self.combo_extractos.set(nombre)
                    break

            parm = {
                "cchart": self.colors["cchart"],
                "InicioInversior": DataHub.InicioInversior,
                "titulo": "Ingresos y Costos de Operación (Resumen)",
            }

            self.load.config(state="disabled")

            # elimina items cuando existan en self.extract -----------------------------------------------------
            if self.extract.get_children():  # Verifica si hay elementos en el Treeview
                for item in self.extract.get_children():
                    self.extract.delete(item)

            if self.type_extract["Resumen"] == lista[self.indice % len(lista)]:
                datos, f_datos = self.extractos(account="sum*", periodo=self.year)
                resumen = self.extract.insert(
                    "",
                    "end",
                    text="Resumen",
                    values=(
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ),
                )
                extract_update_treeview(tipo=resumen)

            elif self.type_extract["Stock"] == lista[self.indice % len(lista)]:
                self.load.config(state="normal")
                datos, f_datos = self.extractos(account=self.sesion["Stock"]["idcuenta"], periodo=self.year)
                stock = self.extract.insert(
                    "",
                    "end",
                    text="Stock",
                    values=(
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ),
                )

                extract_update_treeview(tipo=stock)

                parm["titulo"] = "Ingresos y Costos de Operación (Stock)"

            elif self.type_extract["Crypto"] == lista[self.indice % len(lista)]:

                datos, f_datos = self.extractos(account=self.sesion["Crypto"]["idcuenta"], periodo=self.year)
                crypto = self.extract.insert(
                    "",
                    "end",
                    text="Crypto",
                    values=(
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ),
                )

                extract_update_treeview(tipo=crypto)

                parm["titulo"] = "Ingresos y Costos de Operación (Crypto)"

            elif self.type_extract["BotCrypto"] == lista[self.indice % len(lista)]:

                datos, f_datos = self.extractos(account=self.sesion["BotCrypto"]["idcuenta"], periodo=self.year)
                botcrypto = self.extract.insert(
                    "",
                    "end",
                    text="BotCrypto",
                    values=(
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ),
                )

                extract_update_treeview(tipo=botcrypto)

                parm["titulo"] = "Ingresos y Costos de Operación (BotCrypto)"

            elif self.type_extract["BBVA.ARS"] == lista[self.indice % len(lista)]:

                datos, f_datos = self.extractos(account=self.sesion["BBVA.ARS"]["idcuenta"], periodo=self.year)
                FCI_bbva = self.extract.insert(
                    "",
                    "end",
                    text="BBVA.ARS",
                    values=(
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ),
                )

                extract_update_treeview(tipo=FCI_bbva)

                parm["titulo"] = "Ingresos y Costos de Operación (FCI - BBVA)"

            elif self.type_extract["SANT.ARS"] == lista[self.indice % len(lista)]:

                datos, f_datos = self.extractos(account=self.sesion["SANT.ARS"]["idcuenta"], periodo=self.year)
                FCI_sant = self.extract.insert(
                    "",
                    "end",
                    text="SANT.ARS",
                    values=(
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ),
                )

                extract_update_treeview(tipo=FCI_sant)

                parm["titulo"] = "Ingresos y Costos de Operación (FCI - Santander)"

            # redibuja gráfico de margen Neto
            chart_margen_neto(fg=self.fg1, df=f_datos, parm=parm)
            self.cv1.draw()
        except Exception as error:
            print("widgets_extractos(): {}".format(error))

    def update_first_row_extract(self, padre=None):
        try:
            itrue = True
            depositos, retiros, crecimiento, dividendos, perdidas, value = (
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            )
            fee, comisiones, tax, idevengo, imargen, beneficios, costo_base = (
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            )

            for items in self.extract.get_children():
                depositos, retiros, crecimiento, dividendos, perdidas, value = (
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                )
                fee, comisiones, tax, idevengo, imargen, beneficios, costo_base = (
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                )

                # Recorrer los hijos del padre
                for child in self.extract.get_children(items):
                    depositos += float(self.extract.item(child, "values")[0])
                    retiros += float(self.extract.item(child, "values")[1])
                    crecimiento += float(self.extract.item(child, "values")[2])
                    dividendos += float(self.extract.item(child, "values")[3])
                    perdidas += float(self.extract.item(child, "values")[4])
                    fee += float(self.extract.item(child, "values")[5])
                    comisiones += float(self.extract.item(child, "values")[6])
                    tax += float(self.extract.item(child, "values")[7])
                    idevengo += float(self.extract.item(child, "values")[10])
                    imargen += float(self.extract.item(child, "values")[11])
                    beneficios += float(self.extract.item(child, "values")[12])

                    # toma costo y value más recientes
                    if itrue:
                        value = float(self.extract.item(child, "values")[8])
                        costo_base = float(self.extract.item(child, "values")[9])
                        itrue = False

            # Actualizar el valor del padre
            margen_neto = beneficios / costo_base if costo_base > 0 else 0
            self.extract.item(
                padre,
                values=(
                    "{:10.2f}".format(depositos),
                    "{:10.2f}".format(retiros),
                    "{:10.2f}".format(crecimiento),
                    "{:10.2f}".format(dividendos),
                    "{:10.2f}".format(perdidas),
                    "{:10.2f}".format(fee),
                    "{:10.2f}".format(comisiones),
                    "{:10.2f}".format(tax),
                    "{:10.2f}".format(value),
                    "{:10.2f}".format(costo_base),
                    "{:10.2f}".format(idevengo),
                    "{:10.2f}".format(imargen),
                    "{:10.2f}".format(beneficios),
                    "{:10.1%}".format(margen_neto),
                ),
            )
        except Exception as error:
            print("update_first_row_extract(): {}".format(error))

    def lista_extractos(self):
        """
        Método legacy para compatibilidad.
        Ahora el comportamiento circular se maneja mediante el combobox.
        """
        try:
            # elimina items
            for item in self.extract.get_children():
                self.extract.delete(item)

            # incrementa indice de llamado a la lista
            self.indice += 1
            self.widgets_extractos()
        except Exception as e:
            print("lista_extractos(): {}".format(e))

    def on_select_extracto(self, event=None):
        """
        Maneja la selección de extracto desde el combobox.
        Permite acceso directo a cualquier cuenta sin comportamiento circular.

        Args:
            event: Evento de selección del combobox
        """
        try:
            # Obtener nombre seleccionado del combobox
            selected = self.combo_extractos.get()

            # Actualizar índice según la selección
            if selected in self.type_extract:
                self.indice = self.type_extract[selected]

                # Limpiar items actuales
                for item in self.extract.get_children():
                    self.extract.delete(item)

                # Actualizar vista con el extracto seleccionado
                self.widgets_extractos()
        except Exception as e:
            print("on_select_extracto(): {}".format(e))

    # mantiene actualizada información del plan de inversión
    def widgets_plan(self):
        self.datsess = self.PlaInversion.get_sesion_by_vehiculo("Stock")
        plan = self.PlaInversion.select_plan(self.datsess["idcuenta"])
        traz = self.PlaInversion.select_trazaplan(self.datsess["idcuenta"])
        vari = self.PlaInversion.select_variablesplan(self.datsess["idcuenta"])

        if plan:
            (
                deseada,
                actual,
            ) = (
                0,
                0,
            )
            for i, key in enumerate(plan):
                s_deseada = "{:>,.0f}".format(key["deseada"])
                s_actual = "{:>,.0f}".format(key["actual"])
                self.plan[key["vision"]] = key["deseada"]

                self.mpl[i + 1][0].config(text="{:>10}".format(key["vision"]))
                self.mpl[i + 1][1].config(text=s_deseada.rjust(14))
                self.mpl[i + 1][2].config(text=s_actual.rjust(14))
                deseada += key["deseada"]
                actual += key["actual"]
                if i == 0:
                    self.mpl[i + 1][3].config(text="{:>12.1%}".format(key["objetivo"]))
                    self.mpl[5][6].config(
                        text="{:>6.0f} de Ingresos ({:>5.2%} visión actual)".format(key["indicador"], key["objetivo"])
                    )
                else:
                    self.mpl[i + 1][3].config(text="{:>12.1%}".format(key["indicador"]))

                if key["proyecto"] != " ":
                    self.mpl[0][5].insert(tk.END, str(i) + ") " + key["proyecto"] + "\n")

            # totaliza y justifica a la derecha
            s_deseada = "{:>,.0f}".format(deseada)
            s_actual = "{:>,.0f}".format(actual)
            self.mpl[5][1].config(text=s_deseada.rjust(14))
            self.mpl[5][2].config(text=s_actual.rjust(13))

            if traz:
                self.tree_plan.delete(*self.tree_plan.get_children())
                for tkey in traz:
                    vision = "{:>,.0f}".format(tkey["vision"])
                    cap = div = efe = sta = rec = ""
                    if tkey["costobase"] > 0:
                        cap = "{:>,.1f}".format(tkey["tinversion"])
                        div = "{:>,.1f}".format(tkey["dividendo"])
                        efe = "{:>+.1%}".format(tkey["efectividad"])
                        sta = tkey["status"] or ""
                        rec = tkey["recompensa"] or ""
                    self.tree_plan.insert(
                        "",
                        tk.END,
                        values=(
                            "{:>n} Año".format(tkey["meta"]),
                            "{:%Y-%b}".format(tkey["extracto"]),
                            vision,
                            cap,
                            div,
                            efe,
                            sta,
                            rec,
                        ),
                    )

                # redibuja gráfico de plan trazado Neto
                chart_trazaplan(fg=self.fg0, traza=traz, cchart=self.colors["cchart"])
                self.cv0.draw()

    # despliega los riesgos y otras variables a considerar en plan de inversión
    def detalle_plan(self):
        # controla salida de window_estrategia()
        def eexit():
            rnb.destroy()

        try:
            # define windows de detalle plan
            rnb = tk.Toplevel()
            title = "Detalle Plan"
            x_dimension = "%dx%d+%d+%d" % (620, 665, self.df - 5, 65)
            rnb.geometry(x_dimension)
            rnb.resizable(False, False)
            rnb.attributes("-toolwindow", 1)
            rnb.config(bg=self.bgcolor)
            rnb.title(title)
            rnb.focus()
            rnb.grab_set()
            rnb.protocol("WM_DELETE_WINDOW", eexit)

            win1 = ttk.Frame(rnb, padding=(1, 1, 1, 1), style="C.TFrame")  # variables riesgos
            win2 = ttk.Frame(rnb, padding=(1, 1, 1, 1), style="C.TFrame")  # variables precio a pagar
            win3 = ttk.Frame(rnb, padding=(1, 1, 1, 1), style="C.TFrame")  # variables precio a pagar
            wi30 = ttk.Frame(win3, padding=(1, 1, 1, 1), style="C.TFrame")  # botones
            wi31 = ttk.Frame(win3, padding=(1, 1, 1, 1), style="C.TFrame")  # botones
            win4 = ttk.Frame(rnb, padding=(1, 1, 1, 1), style="C.TFrame")  # botones
            win1.pack(fill=tk.X, pady=5)
            win2.pack(fill=tk.X, pady=1)
            win3.pack(fill=tk.X, pady=5)
            wi30.pack(side=tk.LEFT, expand=True)
            wi31.pack(side=tk.LEFT)
            win4.pack(fill=tk.X, pady=5)

            rsg = ["Riesgos", "Solución Potencial"]
            self.mpl[14][8] = tk.Button(
                win1,
                text=rsg[0],
                width=27,
                height=2,
                state="disabled",
                font=("Segoe UI", 10),
                fg="white",
                bg="firebrick4",
                relief=tk.FLAT,
            )
            self.mpl[14][9] = tk.Button(
                win1,
                text=rsg[1],
                width=39,
                height=2,
                state="disabled",
                font=("Segoe UI", 10),
                fg="white",
                bg="firebrick4",
                relief=tk.FLAT,
            )
            self.mpl[14][8].pack(side=tk.LEFT)
            self.mpl[14][9].pack(side=tk.LEFT)

            # Configurar el Treeview para usar los scrollbars
            columns = []
            fixed_columns = ["Riesgos"]
            alignments = {"Riesgos": {"width": 250, "anchor": tk.W}}
            alignments.update({"Solución Potencial": {"width": 350, "anchor": tk.W}})

            columns.extend(list(alignments.keys()))
            tree = CustomTreeview(
                master=win2,
                columns=columns,
                fixed_columns=fixed_columns,
                fixed_row=False,
                show_vscroll=False,
                show_hscroll=False,
                show_headings=False,
                height=5,
                column_alignments=alignments,
                style="TFrame",
            )

            prc = ["Precio \na \nPagar", "Tiempo/Energía", "Económicos", "Personales"]
            self.mpl[23][0] = tk.Button(
                wi30,
                text=prc[0],
                width=10,
                height=23,
                state="disabled",
                font=("Segoe UI", 10),
                fg="white",
                bg="firebrick4",
                relief=tk.FLAT,
            )
            tiempo = ttk.Treeview(wi31, columns=prc[1], show="headings", height=5, style="TFrame")
            tiempo.heading(prc[1], text=prc[1])
            tiempo.column(prc[1], width=480)

            economico = ttk.Treeview(wi31, columns=prc[2], show="headings", height=5, style="TFrame")
            economico.heading(prc[2], text=prc[2])
            economico.column(prc[2], width=480)

            personal = ttk.Treeview(wi31, columns=prc[3], show="headings", height=5, style="TFrame")
            personal.heading(prc[3], text=prc[3])
            personal.column(prc[3], width=480)

            self.mpl[23][0].pack(fill=tk.Y, pady=5)
            tiempo.pack(fill=tk.X, padx=5, pady=3)
            economico.pack(fill=tk.X, padx=5, pady=3)
            personal.pack(fill=tk.X, padx=5, pady=3)

            cancel = tk.Button(
                win4,
                text="Cancel",
                width=8,
                bg="gray",
                fg="white",
                command=lambda: eexit(),
            )
            cancel.grid(row=1, column=1, pady=2, padx=13)

            # volcado de información de variables del plan
            vari = self.PlaInversion.select_variablesplan(self.datsess["idcuenta"])
            if vari:
                i, j, k, l = 1, 1, 1, 1
                for tkey in vari:
                    if tkey["tipo"] == "riesgos":
                        values = [
                            "{:2.0f}). {:<30}".format(i, tkey["ditem"]),
                            "{:<60}".format(tkey["observaciones"]),
                        ]
                        tree.insert_row(values=values)
                        i += 1

                    elif tkey["tipo"] == "esfuerzo":
                        values = ("{:2.0f}). {:<30}".format(j, tkey["ditem"]),)
                        tiempo.insert("", tk.END, values=values)
                        j += 1

                    elif tkey["tipo"] == "economico":
                        values = ("{:2.0f}). {:<30}".format(k, tkey["ditem"]),)
                        economico.insert("", tk.END, values=values)
                        k += 1

                    elif tkey["tipo"] == "personal":
                        values = ("{:2.0f}). {:<30}".format(l, tkey["ditem"]),)
                        personal.insert("", tk.END, values=values)
                        l += 1

        except Exception as e:
            print("detalle_plan(): {}".format(e))

    # entrega Dataframe con información de extractos
    def extractos(self, account=None, periodo=None):
        try:
            if account != "sum*":
                extracto = self.PlaInversion.select_extracto(account=account, extract="select*")
            else:
                extracto = self.PlaInversion.select_extracto(extract="sum*")

            datos, y_datos, f_datos = (
                pd.DataFrame(extracto),
                pd.DataFrame(),
                pd.DataFrame(),
            )

            datos["extracto"] = pd.to_datetime(datos["extracto"])
            datos.set_index("extracto", inplace=True)

            datos["ingresos"] = datos["crecimiento"] + datos["dividendos"] + datos["idevengo"]

            datos["costos"] = datos["perdidas"] + datos["fee"] + datos["comisiones"]

            datos["beneficios"] = datos["ingresos"] - datos["costos"]
            datos["beneficiosNeto"] = datos["beneficios"] - (datos["tax"] + datos["imargen"])

            # resume por periodo información de extractos
            f_datos["depositos"] = datos["depositos"].resample(periodo).sum()
            f_datos["dividendos"] = datos["dividendos"].resample(periodo).sum()
            f_datos["crecimiento"] = datos["crecimiento"].resample(periodo).sum()
            f_datos["comisiones"] = datos["comisiones"].resample(periodo).sum()
            f_datos["idevengo"] = datos["idevengo"].resample(periodo).sum()
            f_datos["imargen"] = datos["imargen"].resample(periodo).sum()
            f_datos["perdidas"] = datos["perdidas"].resample(periodo).sum()
            f_datos["ingresos"] = datos["ingresos"].resample(periodo).sum()
            f_datos["retiros"] = datos["retiros"].resample(periodo).sum()
            f_datos["costos"] = datos["costos"].resample(periodo).sum()
            f_datos["fee"] = datos["fee"].resample(periodo).sum()
            f_datos["tax"] = datos["tax"].resample(periodo).sum()

            # beneficio y %margen por periodo
            f_datos["beneficios"] = datos["beneficios"].resample(periodo).sum()
            f_datos["beneficiosNeto"] = datos["beneficiosNeto"].resample(periodo).sum()

            f_datos["margen"] = f_datos["beneficios"] / f_datos["ingresos"]
            f_datos["margenNT"] = f_datos["beneficiosNeto"] / f_datos["ingresos"]

            return datos, f_datos
        except Exception as error:
            print("extractos(): {}".format(error))

    def construir_extracto_crypto(self, desde=None, hasta=None):

        # información de sesión
        vehiculo = "Crypto"
        sesion = self.PlaInversion.get_sesion_by_vehiculo(vehiculo)
        account = sesion["idcuenta"]

        if desde is not None:
            # Obtener información de la cartera del booktrading
            book, ix = self.RepositorioOportunidades.select_booktrading(
                accion="desde_hasta",
                account=account,
                idivisa="USD",
                fecha=desde,
                hasta=hasta,
            )
        elif desde is None:
            book, ix = self.RepositorioOportunidades.select_booktrading(
                accion="cartera", account=account, idivisa="USD"
            )

        # Obtener desempeño del vehículo
        performa, iy = self.Perfoma.select_performa_inversion(account=account, vehiculo=vehiculo, accion="all")

        # dataframe(): para obtener ingresos, costos y comisiones ------------------------------------------------------------
        datos = pd.DataFrame(book, columns=ix)
        datos = datos.drop(
            columns=[
                "id",
                "sec",
                "split",
                "factor_cambio",
                "updateStamp",
                "categoria",
                "idtrans",
                "divisa",
                "cuenta",
                "sell",
                "activa",
                "cantidad",
                "simbolo",
                "preciocierre",
                "preciotrans",
                "basico",
                "mtmgp",
                "stock",
            ]
        )

        # Dataframe() with datos de costo base y value -----------------------------------------------------------------------
        idatos = pd.DataFrame(performa, columns=iy)
        idatos = idatos.drop(
            columns=[
                "id",
                "idcuenta",
                "vehiculo",
                "referencia",
                "p_referencia",
                "p_vehiculo",
                "timestamp",
            ]
        )

        idatos["dividendos"] = idatos["dividends"]
        idatos["navcierre"] = idatos["value"]
        idatos["Date"] = pd.to_datetime(idatos["fechaclose"])

        idatos.set_index("Date", inplace=True)
        idatos = idatos.drop(columns=["fechaclose", "dividends", "value"])

        # Seleccionar solo los fines de mes
        idatos.index = pd.to_datetime(idatos.index)
        m_idatos = idatos[idatos.index.is_month_end]

        # cambia formato de index para aparear con los beneficios
        m_idatos.index = pd.to_datetime(m_idatos.index)
        m_idatos.index = m_idatos.index.strftime("%Y-%m")

        # identificar en columnas compras y ventas --------------------------------------------------------------------------
        datos["depositos"] = datos.apply(lambda rows: rows["producto"] if rows["codigo"] == "O" else 0, axis=1)
        datos["retiros"] = datos.apply(lambda rows: rows["producto"] if rows["codigo"] == "C" else 0, axis=1)
        datos["perdidas"] = datos.apply(
            lambda rows: -rows["gprealizadas"] if rows["gprealizadas"] < 0 else 0,
            axis=1,
        )
        datos["crecimiento"] = datos.apply(lambda rows: rows["gprealizadas"] if rows["gprealizadas"] > 0 else 0, axis=1)
        datos["costos"] = datos["perdidas"] + datos["tarifacomision"]
        datos["beneficios"] = datos["crecimiento"] - datos["costos"]
        datos["comisiones"] = datos["tarifacomision"]
        datos["idevengo"] = 0.0
        datos["imargen"] = 0.0
        datos["Date"] = pd.to_datetime(datos["fechahora"])
        datos["tax"] = 0.0
        datos["fee"] = 0.0

        # agrupa por meses y suma los valores, cambia formato index para aparear y obtener costo_base mensual
        datos = datos.drop(columns=["fechahora", "producto", "tarifacomision"])
        datos.set_index("Date", inplace=True)
        datos.index = pd.to_datetime(datos.index)

        datos.index = datos.index.strftime("%Y-%m")
        m_datos = datos.groupby(datos.index).sum()

        resumen = pd.merge(m_datos, m_idatos, on="Date", how="left")
        # resumen = resumen.bfill()
        resumen = resumen.infer_objects(copy=False).fillna(0)
        resumen.index = pd.to_datetime(resumen.index)

        # deja como fin de mes las fechas Dataframe
        resumen.index = resumen.index + pd.offsets.MonthEnd(0)
        resumen.fillna(0, inplace=True)

        anterior = 0.0
        for row in resumen.itertuples():
            values = {
                "extracto": row.Index.date(),
                "idcuenta": "B0000001",
                "depositos": row.depositos,
                "retiros": row.retiros,
                "crecimiento": row.crecimiento,
                "dividendos": row.dividendos,
                "perdidas": row.perdidas,
                "fee": row.fee,
                "comisiones": row.comisiones,
                "tax": row.tax,
                "navcierre": row.navcierre,
                "cierreanterior": anterior,
                "costobase": row.costo_base,
                "idevengo": row.idevengo,
                "imargen": row.imargen,
            }
            anterior = row.navcierre

        # inserta último mes calculado
        self.PlaInversion.insert_extracto(account="B0000001", values=values)

    # construye extracto de BotCrypto (cuenta B0000002, Binance Bot)
    def construir_extracto_botcrypto(self, desde=None, hasta=None):

        vehiculo = "BotCrypto"
        sesion = self.PlaInversion.get_sesion_by_vehiculo(vehiculo)
        account = sesion["idcuenta"]

        if desde is not None:
            book, ix = self.RepositorioOportunidades.select_booktrading(
                accion="desde_hasta",
                account=account,
                idivisa="USD",
                fecha=desde,
                hasta=hasta,
            )
        else:
            book, ix = self.RepositorioOportunidades.select_booktrading(
                accion="cartera", account=account, idivisa="USD"
            )

        # Obtener desempeño del vehículo
        performa, iy = self.Perfoma.select_performa_inversion(account=account, vehiculo=vehiculo, accion="all")

        # dataframe(): para obtener ingresos, costos y comisiones
        datos = pd.DataFrame(book, columns=ix)
        datos = datos.drop(
            columns=[
                "id",
                "sec",
                "split",
                "factor_cambio",
                "updateStamp",
                "categoria",
                "idtrans",
                "divisa",
                "cuenta",
                "sell",
                "activa",
                "cantidad",
                "simbolo",
                "preciocierre",
                "preciotrans",
                "basico",
                "mtmgp",
                "stock",
            ]
        )

        # Dataframe() with datos de costo base y value
        idatos = pd.DataFrame(performa, columns=iy)
        idatos = idatos.drop(
            columns=[
                "id",
                "idcuenta",
                "vehiculo",
                "referencia",
                "p_referencia",
                "p_vehiculo",
                "timestamp",
            ]
        )

        idatos["dividendos"] = idatos["dividends"]
        idatos["navcierre"] = idatos["value"]
        idatos["Date"] = pd.to_datetime(idatos["fechaclose"])

        idatos.set_index("Date", inplace=True)
        idatos = idatos.drop(columns=["fechaclose", "dividends", "value"])

        # Seleccionar solo los fines de mes
        idatos.index = pd.to_datetime(idatos.index)
        m_idatos = idatos[idatos.index.is_month_end]

        m_idatos.index = pd.to_datetime(m_idatos.index)
        m_idatos.index = m_idatos.index.strftime("%Y-%m")

        # identificar en columnas compras y ventas -- realmente no es nuevo capital solo itera sobre el mismo capital
        # datos["depositos"] = datos.apply(lambda rows: rows["producto"] if rows["codigo"] == "O" else 0, axis=1)
        # datos["retiros"] = datos.apply(lambda rows: rows["producto"] if rows["codigo"] == "C" else 0, axis=1)
        datos["depositos"] = 0.0
        datos["retiros"] = 0.0
        datos["perdidas"] = datos.apply(
            lambda rows: -rows["gprealizadas"] if rows["gprealizadas"] < 0 else 0,
            axis=1,
        )
        datos["crecimiento"] = datos.apply(lambda rows: rows["gprealizadas"] if rows["gprealizadas"] > 0 else 0, axis=1)
        datos["costos"] = datos["perdidas"] + datos["tarifacomision"]
        datos["beneficios"] = datos["crecimiento"] - datos["costos"]
        datos["comisiones"] = datos["tarifacomision"]
        datos["idevengo"] = 0.0
        datos["imargen"] = 0.0
        datos["Date"] = pd.to_datetime(datos["fechahora"])
        datos["tax"] = 0.0
        datos["fee"] = 0.0

        # agrupa por meses y suma los valores
        datos = datos.drop(columns=["fechahora", "producto", "tarifacomision"])
        datos.set_index("Date", inplace=True)
        datos.index = pd.to_datetime(datos.index)
        datos.index = datos.index.strftime("%Y-%m")
        m_datos = datos.groupby(datos.index).sum()

        resumen = pd.merge(m_datos, m_idatos, on="Date", how="left")
        resumen = resumen.infer_objects(copy=False).fillna(0)
        resumen.index = pd.to_datetime(resumen.index)

        # deja como fin de mes las fechas Dataframe
        resumen.index = resumen.index + pd.offsets.MonthEnd(0)
        resumen.fillna(0, inplace=True)

        anterior = 0.0
        for row in resumen.itertuples():
            values = {
                "extracto": row.Index.date(),
                "idcuenta": account,
                "depositos": row.depositos,
                "retiros": row.retiros,
                "crecimiento": row.crecimiento,
                "dividendos": row.dividendos,
                "perdidas": row.perdidas,
                "fee": row.fee,
                "comisiones": row.comisiones,
                "tax": row.tax,
                "navcierre": row.navcierre,
                "cierreanterior": anterior,
                "costobase": row.costo_base,
                "idevengo": row.idevengo,
                "imargen": row.imargen,
            }
            anterior = row.navcierre

        # inserta último mes calculado
        self.PlaInversion.insert_extracto(account=account, values=values)

    # construye extracto de FCI en ARS
    def construir_extracto_fci(self, account=None, desde=None, hasta=None, insert=True):

        book, ix = self.RepositorioOportunidades.select_booktrading(accion="cartera", account=account, idivisa="ARS")

        # Obtener desempeño del vehículo
        performa, iy = self.Perfoma.select_performa_inversion(account="U4214563", vehiculo="Stock", accion="all")

        # dataframe(): para obtener ingresos, costos y comisiones ------------------------------------------------------------
        datos = pd.DataFrame(book, columns=ix)
        datos = datos.drop(
            columns=[
                "id",
                "sec",
                "split",
                "updateStamp",
                "categoria",
                "idtrans",
                "divisa",
                "cuenta",
                "sell",
                "activa",
                "cantidad",
                "simbolo",
                "preciocierre",
                "preciotrans",
                "basico",
                "mtmgp",
                "stock",
            ]
        )

        # Dataframe() with datos de costo base y value -----------------------------------------------------------------------
        idatos = pd.DataFrame(performa, columns=iy)
        idatos = idatos.drop(
            columns=[
                "id",
                "idcuenta",
                "vehiculo",
                "referencia",
                "p_referencia",
                "p_vehiculo",
                "timestamp",
                "costo_base",
            ]
        )

        idatos["dividendos"] = idatos["dividends"]
        idatos["navcierre"] = idatos["value"]
        idatos["Date"] = pd.to_datetime(idatos["fechaclose"])

        idatos.set_index("Date", inplace=True)
        idatos = idatos.drop(columns=["fechaclose", "dividends", "value"])

        # Seleccionar solo los fines de mes
        idatos.index = pd.to_datetime(idatos.index)
        m_idatos = idatos[idatos.index.is_month_end]

        # cambia formato de index para aparear con los beneficios
        m_idatos.index = pd.to_datetime(m_idatos.index)
        m_idatos.index = m_idatos.index.strftime("%Y-%m")

        # identificar en columnas compras y ventas ---------------------------------------------------------------------
        datos["depositos"] = datos.apply(
            lambda rows: (rows["producto"] / rows["factor_cambio"] if rows["codigo"] == "O" else 0),
            axis=1,
        )
        datos["retiros"] = datos.apply(
            lambda rows: (rows["producto"] / rows["factor_cambio"] if rows["codigo"] == "C" else 0),
            axis=1,
        )
        datos["perdidas"] = datos.apply(
            lambda rows: (-rows["gprealizadas"] / rows["factor_cambio"] if rows["gprealizadas"] < 0 else 0),
            axis=1,
        )
        datos["crecimiento"] = datos.apply(
            lambda rows: (rows["gprealizadas"] / rows["factor_cambio"] if rows["gprealizadas"] >= 0 else 0),
            axis=1,
        )

        datos["gprealizadas"] = datos.apply(
            lambda rows: (rows["gprealizadas"] / rows["factor_cambio"] if rows["gprealizadas"] >= 0 else 0),
            axis=1,
        )

        datos["costos"] = datos["perdidas"] + datos["tarifacomision"]
        datos["costo_base"] = datos["depositos"] - datos["retiros"]
        datos["beneficios"] = datos["crecimiento"] - datos["costos"]
        datos["comisiones"] = datos["tarifacomision"]

        datos["idevengo"] = 0.0
        datos["imargen"] = 0.0
        datos["Date"] = pd.to_datetime(datos["fechahora"])
        datos["tax"] = 0.0
        datos["fee"] = 0.0

        # agrupa por meses y suma los valores, cambia formato index para aparear y obtener costo_base mensual
        datos = datos.drop(columns=["fechahora", "producto", "tarifacomision"])
        datos.set_index("Date", inplace=True)
        datos.index = pd.to_datetime(datos.index)

        datos.index = datos.index.strftime("%Y-%m")
        m_datos = datos.groupby(datos.index).sum()

        resumen = pd.merge(m_datos, m_idatos, on="Date", how="left")

        # resumen = resumen.bfill()
        resumen = resumen.infer_objects(copy=False).fillna(0)
        resumen.index = pd.to_datetime(resumen.index)

        # se construye saldo al final de cada mes
        resumen["navcierre"] = resumen["costo_base"] + resumen["beneficios"] - resumen["costos"]

        # deja como fin de mes las fechas Dataframe
        resumen.index = resumen.index + pd.offsets.MonthEnd(0)
        resumen.fillna(0, inplace=True)

        anterior = 0.0
        for row in resumen.itertuples():
            values = {
                "extracto": row.Index.date(),
                "idcuenta": account,
                "depositos": row.depositos,
                "retiros": row.retiros,
                "crecimiento": row.crecimiento,
                "dividendos": row.dividendos,
                "perdidas": row.perdidas,
                "fee": row.fee,
                "comisiones": row.comisiones,
                "tax": row.tax,
                "navcierre": row.navcierre + anterior,
                "cierreanterior": anterior,
                "costobase": row.navcierre + anterior - row.crecimiento,
                "idevengo": row.idevengo,
                "imargen": row.imargen,
            }

            anterior = values["navcierre"]

            # evalua si trabaja ne opción insert para agregar el mes en curso
            if insert and (hasta == row.Index.date().strftime("%Y-%m-%d")):
                # inserta último mes calculado
                self.PlaInversion.insert_extracto(account=account, values=values)

    def update_plan(self, account=None, condicion=None):
        """
        @param account: id de cuenta de inversión
        @param condicion: si para cierre de fiscal
        @return: actualiza tabla trazaplan y plan desde estrategia."""

        crecimiento, dividendos, idevengo, perdidas, fee = 0.0, 0.0, 0.0, 0.0, 0.0
        comisiones, tax, ingresos, costos, beneficios, imargen = (
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        )

        def acumulate_extracto():
            nonlocal crecimiento, dividendos, idevengo, perdidas, fee, comisiones, tax, ingresos, costos, beneficios, imargen, costobase

            crecimiento += s_extracto["crecimiento"]
            dividendos += s_extracto["dividendos"]
            idevengo += s_extracto["idevengo"]
            ingresos = crecimiento + dividendos + idevengo

            comisiones += s_extracto["comisiones"]
            perdidas += s_extracto["perdidas"]
            imargen += s_extracto["imargen"]
            fee += s_extracto["fee"]
            tax += s_extracto["tax"]

            costos = comisiones + perdidas + imargen + fee + tax
            beneficios = ingresos - costos

        try:
            traza = self.PlaInversion.select_trazaplan(idcuenta=account, orden="ASC")
            entrada = self.PlaInversion.select_extracto(extract="sum*")
            extracto = sorted(entrada, key=lambda x: x["extracto"], reverse=False)

            ibook = enumerate(traza)
            eof_ibook, i_traza = next(ibook, (None, None))

            sbook = enumerate(extracto)
            eof_sbook, s_extracto = next(sbook, (None, None))

            # aparea traza y extracto para actualizar trazaplan ---------------------------------------------------------
            while (eof_ibook is not None) and (eof_sbook is not None):

                acumulate_extracto()

                # actualiza años anteriores --------------------------------
                if i_traza["extracto"] == s_extracto["extracto"]:

                    efectividad = (s_extracto["costobase"] - i_traza["vision"]) / i_traza["vision"]
                    rendimiento = beneficios / s_extracto["costobase"]

                    values = {
                        "tinversion": s_extracto["costobase"],
                        "dividendo": dividendos,
                        "ccapital": beneficios,
                        "efectividad": efectividad,
                        "trendimiento": rendimiento,
                        "status": "Cumplido",
                    }

                    crecimiento, dividendos, idevengo, perdidas, fee, costobase = (
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                    )
                    comisiones, tax, ingresos, costos, beneficios, imargen = (
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                    )
                    self.PlaInversion.update_trazaplan_inversion(idcuenta=account, meta=i_traza["meta"], values=values)

                    # logica para comenzar proximo año fiscal
                    # validar en julio 2026
                    values = {
                        "tinversion": s_extracto["costobase"],
                        "dividendo": 0.0,
                        "ccapital": 0.0,
                        "efectividad": 0.0,
                        "trendimiento": 0.0,
                        "status": "Ejecucion",
                    }
                    proxima = i_traza["meta"] + 1
                    self.PlaInversion.update_trazaplan_inversion(idcuenta=account, meta=proxima, values=values)

                    eof_ibook, i_traza = next(ibook, (None, None))
                    eof_sbook, s_extracto = next(sbook, (None, None))

                else:
                    if i_traza["extracto"] < s_extracto["extracto"]:
                        eof_ibook, i_traza = next(ibook, (None, None))
                    else:
                        costobase = s_extracto["costobase"]
                        eof_sbook, s_extracto = next(sbook, (None, None))

            # actualiza último mes calculado ---------------------------------------------------------------------
            if eof_sbook is None:
                if i_traza["status"] == "Ejecucion":

                    beneficios = ingresos - costos
                    efectividad = (costobase - i_traza["vision"]) / i_traza["vision"]
                    rendimiento = beneficios / costobase
                    values = {
                        "tinversion": costobase,
                        "dividendo": dividendos,
                        "ccapital": beneficios,
                        "efectividad": efectividad,
                        "trendimiento": rendimiento,
                    }
                    self.PlaInversion.update_trazaplan_inversion(idcuenta=account, meta=i_traza["meta"], values=values)

                    # actualiza vision financiera actual sobre tabla plan
                    campos = {"Financiera": costobase}
                    self.PlaInversion.update_plan_inversion(idcuenta=account, vision="actual", values=campos)
        except Exception as e:
            print(f"update_plan(): {e} {traceback.print_exc()}")

    def edit_plan(self):
        # controla salida de window_estrategia()
        def eexit():
            if not (rnb is None):
                rnb.destroy()

        def submit_values():
            try:
                # Obtener valores de las entradas
                vision_financiera = int(entry_vision.get())
                estilo_vida = int(entry_estilo.get())
                contribucion = int(entry_contribucion.get())

                # Validar que los valores sean mayores o iguales a 1000
                if vision_financiera < 1000 or estilo_vida < 1000 or contribucion < 1000:
                    MyMessageBox(self.root).showerror("Error", "Todos los valores deben ser enteros de al menos 1000.")
                    return

                campos = {
                    "Financiera": vision_financiera,
                    "Estilo de vida": estilo_vida,
                    "Contribucion": contribucion,
                }

                self.PlaInversion.update_plan_inversion(
                    idcuenta=self.sesion["Stock"]["idcuenta"],
                    vision="deseada",
                    values=campos,
                )
                eexit()
                self.widgets_plan()

            except ValueError:
                MyMessageBox.showerror("Error", "Todos los valores deben ser números enteros válidos.")

        try:
            rnb = tk.Toplevel()
            title = "Visión Deseada"
            marco = "%dx%d+%d+%d" % (620, 150, 667, 490)
            rnb.geometry(marco)
            rnb.resizable(False, False)
            rnb.attributes("-toolwindow", 1)
            rnb.config(bg=self.bgcolor)
            rnb.title(title)
            rnb.focus()
            rnb.grab_set()
            rnb.protocol("WM_DELETE_WINDOW", eexit)

            # Etiquetas y entradas
            vision = tk.Label(rnb, text="Visión financiera (mínimo 1000 $USD):", bg=self.bgcolor)
            vision.grid(row=0, column=0, padx=10, pady=7, sticky=E)
            vision_str = tk.StringVar()
            vision_str.set(str(self.plan["Financiera"]))

            entry_vision = tk.Entry(rnb, textvariable=vision_str)
            entry_vision.grid(row=0, column=1, padx=10, pady=5)

            estilo = tk.Label(rnb, text="Estilo de vida (mínimo 1000 $USD):", bg=self.bgcolor)
            estilo.grid(row=1, column=0, padx=10, pady=5, sticky=E)
            estilo_str = tk.StringVar()
            estilo_str.set(str(self.plan["Estilo de vida"]))

            entry_estilo = tk.Entry(rnb, textvariable=estilo_str)
            entry_estilo.grid(row=1, column=1, padx=10, pady=5)

            contrib = tk.Label(rnb, text="Contribución (mínimo 1000 $USD):", bg=self.bgcolor)
            contrib.grid(row=2, column=0, padx=10, pady=5, sticky=E)

            contrib_str = tk.StringVar()
            contrib_str.set(str(self.plan["Contribucion"]))

            entry_contribucion = tk.Entry(rnb, textvariable=contrib_str)
            entry_contribucion.grid(row=2, column=1, padx=10, pady=5)

            # Botón para enviar
            ct1 = tk.Button(
                rnb,
                text="Update",
                width=8,
                bg="gray",
                fg="white",
                command=lambda: submit_values(),
            )
            ct2 = tk.Button(
                rnb,
                text="Cancel",
                width=8,
                bg="gray",
                fg="white",
                command=lambda: eexit(),
            )

            ct1.grid(row=3, column=3, padx=10, pady=10)
            ct2.grid(row=3, column=4, padx=10, pady=10)
        except ValueError:
            raise ValueError("Error: {}".format("los valores deben ser números enteros."))

    # asegura que esté completo performance crypto para crear extracto
    def check_performance_vehiculo(self, vehiculo=None, account=None, extracto=None):
        try:
            log = False
            last_update, ix = self.Perfoma.select_performa_inversion(account=account, vehiculo=vehiculo, accion="last")

            if last_update:
                f_hasta = last_update[ix.index("fechaclose")]
                if extracto <= f_hasta:
                    log = True

            return log
        except Exception as e:
            print(f"check_performance_vehiculo(): {e}")

    # agregar desde boton extractos
    def add_csv(self):
        try:
            hoy = datetime.now()
            dias = hoy.day
            last = hoy - timedelta(days=dias)
            sesion = self.PlaInversion.get_sesion_by_vehiculo(principal=True)

            d_extract, ilog = cagar_archivo(account=sesion["idcuenta"], titulo="Activity Statement", tipo="csv")

            if not ilog:
                return

            # get last date extract
            lastExtracto = self.PlaInversion.select_extracto(
                account=sesion["idcuenta"],
                extract=d_extract["extracto"].strftime("%Y-%m-%d"),
            )

            # valida que no haya sido Extracto cargado mes anterior
            if lastExtracto:

                # para no procesar extracto mas de una vez
                if lastExtracto[0]["extracto"] <= d_extract["extracto"].date():
                    idcuenta = lastExtracto[0]["idcuenta"]
                    extracto = lastExtracto[0]["extracto"]

                    msj = f"No se puede cargar dos veces CSV extracto {idcuenta} para el mes [{extracto.strftime("%b-%Y")}], intente nuevamente."
                    MyMessageBox(self.root).showwarning("Advertencia", msj)
                    return

                # para asegurar que el extracto load no exceda la today()
                if d_extract["extracto"].date() > hoy.date():
                    msj = f"No se puede cargar extracto {idcuenta} mayor a la fecha [{d_extract["extracto"].strftime("%b-%Y")}], intente nuevamente."
                    MyMessageBox(self.root).showwarning("Advertencia", msj)
                    return

            # chequea carga de extracto Stock -----------------------------------------------------------------------
            if ilog:
                idcuenta = sesion["idcuenta"]
                self.PlaInversion.insert_extracto(account=idcuenta, values=d_extract)
                self.d_extract = d_extract
                msj = f"Cargado extracto {idcuenta} a la fecha [{d_extract["extracto"].strftime("%b-%Y")}], enter para continuar."
                MyMessageBox(self.root).showwarning("Advertencia", msj)

                # actualiza panel gestion
                self.widgets_extractos()
        except Exception as e:
            print(f"add_csv(): {e} {traceback.print_exc()}")

    def get_date_extrato(self):
        sesion = self.PlaInversion.get_sesion_by_vehiculo(principal=True)

        # get last date extract
        lastExtracto = self.PlaInversion.select_extracto(account=sesion["idcuenta"], extract="last")

        hoy = datetime.now()
        dias = hoy.day
        last = hoy - timedelta(days=dias)

        # Convierte Extrado a "%Y-%m-%d 00:00:00"
        lastDate = datetime.combine(lastExtracto[0]["extracto"], datetime.min.time())
        lastExtracto[0]["extracto"] = lastDate

        # Extracto cargado mes anterior
        if lastExtracto[0]["extracto"].date() == last.date():
            return lastExtracto[0], True

        # Extracto NO cargado mes anterior
        if lastExtracto[0]["extracto"].date() < last.date():
            return lastExtracto[0], False

    # controla  el cierre de mes() gwi001
    def cierre_extractos(self):
        def insert_new_extracto():
            try:
                # extracto crypto ---------------------------------------------------------------------------------
                now = self.d_extract["extracto"]
                inicio = now - timedelta(days=90)
                f_desde = inicio.strftime("%Y-%m-%d")
                f_hasta = now.strftime("%Y-%m-%d")
                self.construir_extracto_crypto(desde=f_desde, hasta=f_hasta)

                # extracto BotCrypto (Binance Bot, cuenta B0000002) ------------------------------------------------
                self.construir_extracto_botcrypto(desde=f_desde, hasta=f_hasta)

                # extracto BBVA y santander-------------------------------------------------------------------------
                self.construir_extracto_fci(
                    account=self.sesion["BBVA.ARS"]["idcuenta"],
                    desde=f_desde,
                    hasta=f_hasta,
                )
                self.construir_extracto_fci(
                    account=self.sesion["SANT.ARS"]["idcuenta"],
                    desde=f_desde,
                    hasta=f_hasta,
                )

            except Exception as e:
                print("insert_new_extracto(): {}".format(e))

            # Proceso mensuales y fin de año fiscal

        def procesa_extractos():
            try:
                # asegura tomar datos de sesion principal
                sesion = self.PlaInversion.get_sesion_by_vehiculo(principal=True)
                a_extracto = self.PlaInversion.select_extracto(account=sesion["idcuenta"], extract="last")

                if a_extracto[0]["extracto"] == self.d_extract["extracto"].date():

                    # inserta extracto Stock y Crypto ---------------------
                    insert_new_extracto()

                    # actualiza tabla de plan cuando cierra el año fiscal ---------------------------------------------
                    if self.d_extract["extracto"].month == sesion["fiscalYear"].month:
                        self.update_plan(account=sesion["idcuenta"], condicion="Cumplido")
                    else:
                        self.update_plan(account=sesion["idcuenta"], condicion=None)

                    MyMessageBox(self.root).showwarning("Add", "Cargados exitosamente los Extracto")

                else:
                    idcuenta = a_extracto[0]["idcuenta"]
                    extracto = self.d_extract["extracto"].strftime("%b-%Y")
                    msj = f"No puede agregar nuevamente el Extracto {idcuenta} [{extracto}], existe en el sistema"
                    MyMessageBox(self.root).showwarning("Advertencia", msj)
            except Exception as e:
                print(f"procesa_extractos(): {e} {traceback.print_exc()}")

        def valida_all_load_csv():
            try:
                hoy = datetime.now()
                dias = hoy.day
                last = hoy - timedelta(days=dias)

                for vehiculo, sesion in self.sesion.items():
                    classActivo = "BBVA.ARS" if vehiculo.endswith(".ARS") else vehiculo

                    # chequea si extrato fue cargado
                    if sesion["load_csv"]:
                        a_extracto = self.PlaInversion.select_extracto(account=sesion["idcuenta"], extract="last")
                        if a_extracto[0]["extracto"] != last.date():
                            msj = (
                                f"Debe realizar load CSV de extracto para {classActivo} al ["
                                + f"{last.date()}], intente mas tarde"
                            )
                            MyMessageBox(self.root).showwarning("Advertencia", msj)
                            return False

                return True
            except Exception as e:
                print(f"valida_all_load_csv(): {e} {traceback.print_exc()}")

        try:

            # obtiene y valida last extract
            self.d_extract, logLastExtract = self.get_date_extrato()

            # valida que se hayan cargados los archivos CSV
            if not valida_all_load_csv():
                return

            if not logLastExtract:
                idcuenta = self.d_extract["idcuenta"]
                msj = f"No se ha cargado CSV extracto {idcuenta} del mes anterior, intente mas tarde"
                MyMessageBox(self.root).showwarning("Advertencia", msj)
                return

            check = []
            # valida existencia de performance de vehiculos al cierre de mes
            for vehiculo, sesion in self.sesion.items():
                classActivo = "BBVA.ARS" if vehiculo.endswith(".ARS") else vehiculo

                clog = self.check_performance_vehiculo(
                    vehiculo=classActivo,
                    account=self.sesion[vehiculo]["idcuenta"],
                    extracto=self.d_extract["extracto"].date(),
                )
                check.append({vehiculo: clog})

            # si ambos Ok, procede con la carga de extractos
            all_true = all(val for d in check for val in d.values())
            if all_true:
                procesa_extractos()

                # actualiza panel gestion
                self.widgets_extractos()

            # emite mensajes
            elif not all_true:
                for vehiculo in check:
                    ok = list(vehiculo.values())[0]
                    if not ok:
                        keys = list(vehiculo.keys())[0]
                        msj = (
                            f"Aguarde ejecución 1er dia hábil para {keys}, tras cierre ["
                            + f"{self.d_extract["extracto"].strftime("%b-%Y")}], Intente nuevamente más tarde."
                        )
                        MyMessageBox(self.root).showwarning("Advertencia", msj)
        except Exception as error:
            print(f"cierre_extractos(): {traceback.print_exc()}")


if __name__ == "__main__":
    win = tk.Tk()
    cchart = {
        "texto": "white",
        "titulo": "cyan",
        "fondo": "black",
        "axsy": "black",
        "axsx": "black",
        "2eje": "orange",
        "plot0": "white",
        "plot1": "green",
        "plot2": "orange",
        "plot3": "red",
        "plot4": "yellow",
        "plot5": "DodgerBlue",
        "plot6": "skyblue",
        "plot7": "black",
    }
    colors = {
        "bgcolor": "DarkCyan",
        "fgcolor": "white",
        "cgcolor": "black",
        "dw": 1290,
        "dh": 700,
        "df": 1297,
        "max_dw": win.winfo_screenwidth(),
        "max_dh": win.winfo_screenheight(),
        "cchart": cchart,
    }

    dimension = "%dx%d+0+0" % (colors["dw"], colors["dh"])
    win.geometry(dimension)
    win.config(bg=colors["bgcolor"])
    style = ttk.Style(win)
    style.configure("TFrame", font=("Segoe UI", 8), foreground="white", background="black")
    dpn = ttk.Frame(win, style="TFrame", width=colors["df"], height=700)
    dpn.pack()

    frame_strat = GestionInversion(master=dpn, colores=colors)
    frame_strat.grid()
    frame_strat.mainloop()
