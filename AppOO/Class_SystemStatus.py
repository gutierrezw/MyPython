from Modulos_python import (
    tk,
    ttk,
    sys,
    datetime,
    threading,
    Figure,
    FigureCanvasTkAgg,
    time,
    json,
    timedelta,
    pd,
    plt,
    animation,
    schedule,
    traceback,
    logging,
    mpatches,
)
from Modulos_Mysql import RepositorioOportunidadesBuySell
from Class_customer import (
    MyMessageBox,
    DataHub,
    CacheHut,
)
from Class_IA_modelos import ModeloOportunidadesSell


# clase paar monitorear el estado del sistema
class system_status(tk.Frame):
    def __init__(self, master=None, colores=None):
        self.system = master
        self.colors = colores
        self.itemsInfo = None

        # Lista para rastrear todos los after() callbacks
        self.after_ids = []
        self.is_running = True  # Flag para controlar loops

        self.messagebox = MyMessageBox(self.system)

        self.process = ttk.Frame(self.system, padding=(1, 10, 1, 1), style="C.TFrame")
        self.right = ttk.Frame(self.system, padding=(1, 10, 1, 1), style="C.TFrame")

        # Cambio: usar Notebook (tabs) en lugar de frames individuales
        self.bottom = ttk.Notebook(self.system, style="C.TNotebook")

        # Crear frames para cada tab
        self.datahub = ttk.Frame(self.bottom, padding=(1, 1, 1, 1), style="C.TFrame")
        self.cache = ttk.Frame(self.bottom, padding=(1, 1, 1, 1), style="C.TFrame")
        self.buysell = ttk.Frame(self.bottom, padding=(1, 1, 1, 1), style="C.TFrame")
        self.rebalanceo = ttk.Frame(self.bottom, padding=(1, 1, 1, 1), style="C.TFrame")
        self.modeloia = ttk.Frame(self.bottom, padding=(1, 1, 1, 1), style="C.TFrame")
        self.debugging = ttk.Frame(self.bottom, padding=(1, 1, 1, 1), style="C.TFrame")

        # Frames para la derecha
        self.connect = ttk.Frame(self.right, padding=(1, 1, 1, 1), style="C.TFrame")

        # establece figura performance system
        self.fg = Figure(figsize=(4.2, 1.5), dpi=110, layout="tight")
        self.rv = FigureCanvasTkAgg(self.fg, master=self.right)
        self.fg.set_facecolor("DodgerBlue")

        self.rv.draw()
        self.rv.get_tk_widget().pack()
        self.connect.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Agregar tabs al Notebook
        self.bottom.add(self.datahub, text="DataHub")
        self.bottom.add(self.cache, text="Cache")
        self.bottom.add(self.buysell, text="BuySell")
        self.bottom.add(self.rebalanceo, text="Rebalanceo")
        self.bottom.add(self.modeloia, text="Sell IA")
        self.bottom.add(self.debugging, text="Debugging")

        self.bottom.pack(side=tk.BOTTOM, fill=tk.BOTH)
        self.right.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.process.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Bind cleanup al destruir la ventana
        self.system.bind("<Destroy>", self._on_destroy)

        self.process_system()
        # NOTA: modelo_ia_monitor() se llama desde start_chatbot() después de inicializar chatbot

    def _on_destroy(self, event):
        """Limpia recursos al cerrar la ventana"""
        if event.widget == self.system:
            self.cleanup()

    def cleanup(self):
        """Cancela todos los after() callbacks y detiene animaciones"""
        try:
            # Marcar como no ejecutando
            self.is_running = False

            # Cancelar todos los after() callbacks
            for after_id in self.after_ids:
                try:
                    self.system.after_cancel(after_id)
                except:
                    pass

            # Limpiar lista
            self.after_ids.clear()

            # Detener animación de monitor_realtime si existe
            if hasattr(self, "monitor_animation") and self.monitor_animation:
                try:
                    self.monitor_animation.event_source.stop()
                    self.monitor_animation = None
                except:
                    pass

            print("✅ system_status: Recursos liberados correctamente")

        except Exception as e:
            print(f"[cleanup]: {e}")

    # detalla los procesos y schedule del system
    def process_system(self):
        # extrae information de thread y schedule
        def obtener_datos():
            nonlocal procesos
            try:

                procesos = {"widget": {}, "thread": {}, "jobs": {}}

                # Ordena los threads por nombre antes de procesarlos
                for keys in sorted(threading.enumerate(), key=lambda t: t.name):
                    # obtiene contador de actividad (Running) para el job
                    itera = DataHub.update_self_procesos(
                        proces="thread", tarea=keys.name
                    )
                    status = f"Run({itera})" if keys.is_alive() else "Stop()"

                    # cuando existe la task en DataHub
                    if keys.ident in procesos["thread"]:
                        procesos["thread"][keys.ident].update(
                            {"tarea": keys.name, "params": status}
                        )
                    else:
                        # casos donde nose a agregado la task en DataHub
                        procesos["thread"].update(
                            {keys.ident: {"tarea": keys.name, "params": status}}
                        )

                # Ordena los jobs por tag antes de mostrar
                jobs_sorted = sorted(
                    schedule.jobs, key=lambda job: list(job.tags)[0] if job.tags else ""
                )

                for job in jobs_sorted:
                    # obtiene contador de actividad (Running) para el job
                    job_tags = list(job.tags)[0]
                    itera = DataHub.update_self_procesos(
                        proces="running", tarea=job_tags
                    )

                    if job_tags in procesos["jobs"]:
                        procesos["jobs"][job_tags].update(
                            {
                                "tarea": job.next_run,
                                "params": f"Run({itera}), cada: {job.interval}/{job.unit[0]}",
                            }
                        )
                    else:
                        procesos["jobs"].update(
                            {
                                job_tags: {
                                    "tarea": job.next_run,
                                    "params": f"Run({itera}), cada: {job.interval}/{job.unit[0]}",
                                }
                            }
                        )

                # cargar datos de widget
                widget = [item for item in DataHub.procesos if "widget" in item]

                # Ordena el arreglo widget por keys antes de procesarlo
                for proceso in sorted(
                    widget, key=lambda x: list(x["widget"].keys())[0]
                ):
                    grupo = proceso["widget"]
                    for task in sorted(grupo.keys()):
                        values = grupo[task]
                        name = task.split("_", 1)[1]
                        status = f"Run({values})"
                        procesos["widget"].update(
                            {name: {"tarea": task, "params": status}}
                        )

                return procesos
            except Exception as e:
                print(f"obtener_datos(): {e}")

        def buscar_item_treeview(keys=None, iid=None, sobre="text"):
            for item_id in tree.get_children(padre[keys]):
                info = tree.item(item_id)
                if info["text"] == iid:
                    return item_id
                elif info["values"][0] == iid:
                    return item_id

            return None

        # control para mantener lista de procesos actualizados
        def delete_items():
            nonlocal contador

            if contador > limite - 1:
                for padre_id in tree.get_children():
                    for item_id in tree.get_children(padre_id):
                        tree.delete(item_id)
                return tree

        # reset de control de procesos actualizados
        def reset_contador():
            nonlocal contador

            contador += 1
            if contador > limite:
                contador = 0
            return contador

        # update de treeview
        def update_status():
            # Verificar si debemos continuar ejecutando
            if not self.is_running:
                return

            obtener_datos()

            # verifica si es tiempo de refrescar lista
            delete_items()

            # mueve nuevos valores de proceso a treeview
            for keys, grupo in procesos.items():

                if (
                    keys == "thread"
                ):  # ------------------------------------------------------------------------------
                    for clave, vals in grupo.items():
                        if vals["params"] == "Stop()":
                            pass
                        if vals["params"] != "Stop()":
                            Bitems = buscar_item_treeview(keys=keys, iid=clave)
                            if Bitems is None:
                                tree.insert(
                                    Thread,
                                    "end",
                                    text=clave,
                                    values=(vals["tarea"], vals["params"]),
                                )
                            else:
                                tree.item(
                                    Bitems,
                                    values=(
                                        vals["tarea"],
                                        vals["params"],
                                    ),
                                )

                if keys == "jobs":
                    for clave, vals in grupo.items():
                        Bitems = buscar_item_treeview(
                            keys=keys, iid=clave, sobre="values"
                        )

                        if Bitems is None:
                            tree.insert(
                                Jobs,
                                "end",
                                text=vals["tarea"],
                                values=(clave, vals["params"]),
                            )
                        else:
                            tree.item(
                                Bitems,
                                text=vals["tarea"],
                                values=(
                                    clave,
                                    vals["params"],
                                ),
                            )

                if keys == "widget":
                    for clave, vals in grupo.items():
                        Bitems = buscar_item_treeview(keys=keys, iid=clave)

                        if Bitems is None:
                            tree.insert(
                                Widget,
                                "end",
                                text=clave,
                                values=(vals["tarea"], vals["params"]),
                            )
                        else:
                            tree.item(
                                Bitems,
                                values=(
                                    vals["tarea"],
                                    vals["params"],
                                ),
                            )

            reset_contador()
            # Registrar el after_id para poder cancelarlo luego
            after_id = self.system.after(2000, update_status)
            self.after_ids.append(after_id)
            # DataHub.manager_after._safe(2000, update_status(), name="update_status")

        try:
            # Configurar el Treeview
            cols = ["Tarea", "Parámetros"]
            tree = ttk.Treeview(self.process, columns=cols, height=18, style="TFrame")
            tree.heading("#0", text="Id - proceso")
            tree.column("#0", width=60, minwidth=60)

            tree.heading("Tarea", text="Tarea")
            tree.column("Tarea", width=120, minwidth=120)
            tree.heading("Parámetros", text="Parámetros")
            tree.column("Parámetros", width=40, minwidth=40)
            tree.pack(fill="both", expand=True)

            Widget = tree.insert("", "end", text="Widget", values=("", ""))
            Thread = tree.insert("", "end", text="Thread", values=("", ""))
            Jobs = tree.insert("", "end", text="Schedule", values=("", ""))
            padre = {"thread": Thread, "jobs": Jobs, "widget": Widget}

            tree.item(Widget, open=True)
            tree.item(Thread, open=True)
            tree.item(Jobs, open=True)

            # declara y Expande los hijos de tree
            procesos, contador, limite = {}, 0, 21

            # mustra e iterea los moitores del sistema -------------------------------------------------------------------------
            self.datahub_system()
            self.connect_api()
            self.debugging_system()

            # bloqueado hasta que mejore consumo CPU
            # self.monitor_realtime()  # Activado con optimizaciones (actualiza cada 10s)
            self.monitor_cache()
            self.manager_buysell_system()
            self.rebalanceo_system()
            update_status()
        except Exception as e:
            print(f"process_system(): {e}")

    # modulo principal para recorre Datahub()
    def datahub_system(self):
        """
        Visualiza DataHub.info con patrón lista-detalle mejorado.
        - LISTA (izquierda): Símbolos disponibles en DataHub.info
        - DETALLE (derecha): Información completa del símbolo seleccionado
        - Evento: Doble click o selección simple para ver detalle
        """

        # Selecciona y actualiza el detalle del primer elemento.
        def display_first_item():
            symbol = search_lista(first=True)
            if symbol:
                display_items_lista(symbol)
                self.itemsInfo = symbol

        # display items del activo con formato mejorado
        def display_items_lista(symbol):
            """Muestra detalle del símbolo seleccionado en DataHub.info"""
            try:
                # Limpiar el treeview de detalles
                for item in detalle.get_children():
                    detalle.delete(item)

                # Verificar que el símbolo existe
                if symbol not in DataHub.info:
                    detalle.insert(
                        "", "end", text=f"⚠️ {symbol}: No disponible", tags=("warning",)
                    )
                    return

                data = DataHub.info[symbol]

                # Header con símbolo y timestamp
                if "websocket" in data and "timestamp" in data["websocket"]:
                    timestamp = data["websocket"]["timestamp"]
                    detalle.insert(
                        "", "end", text=f"📊 Symbol: {symbol.upper()}", tags=("header",)
                    )
                    detalle.insert(
                        "", "end", text=f"⏰ Update: {timestamp}", tags=("info",)
                    )
                else:
                    detalle.insert(
                        "", "end", text=f"📊 Symbol: {symbol.upper()}", tags=("header",)
                    )

                detalle.insert("", "end", text="", tags=("spacer",))

                # Display detalle del activo con estructura mejorada
                for key, value in data.items():
                    if isinstance(value, dict):
                        # Crear nodo para diccionarios
                        node = detalle.insert(
                            "", "end", text=f"📂 {key}", tags=("section",)
                        )

                        for fields, valor in value.items():
                            # Formatear valores según tipo
                            if isinstance(valor, float):
                                valor_str = (
                                    f"{valor:,.4f}"
                                    if abs(valor) < 1000
                                    else f"{valor:,.2f}"
                                )
                            elif isinstance(valor, (int, str)):
                                valor_str = str(valor)
                            else:
                                valor_str = str(valor)

                            detalle.insert(
                                node,
                                "end",
                                text=f"  {fields}: {valor_str}",
                                tags=("value",),
                            )

                        # Expandir nodos importantes
                        if key in ["websocket", "market", "position"]:
                            detalle.item(node, open=True)

                    elif isinstance(value, pd.DataFrame):
                        # Mostrar información de DataFrames
                        node = detalle.insert(
                            "", "end", text=f"📋 {key}", tags=("section",)
                        )
                        detalle.insert(
                            node,
                            "end",
                            text=f"  Filas: {value.shape[0]}",
                            tags=("summary",),
                        )
                        detalle.insert(
                            node,
                            "end",
                            text=f"  Columnas: {value.shape[1]}",
                            tags=("summary",),
                        )
                        detalle.insert(
                            node,
                            "end",
                            text=f"  Nombres: {list(value.columns)[:5]}{'...' if len(value.columns) > 5 else ''}",
                            tags=("summary",),
                        )

                    else:
                        # Valores simples
                        if isinstance(value, float):
                            value_str = (
                                f"{value:,.4f}"
                                if abs(value) < 1000
                                else f"{value:,.2f}"
                            )
                        else:
                            value_str = str(value)
                        detalle.insert(
                            "", "end", text=f"🔹 {key}: {value_str}", tags=("value",)
                        )

            except Exception as e:
                detalle.insert(
                    "", "end", text=f"❌ Error al mostrar detalle: {e}", tags=("error",)
                )
                print(f"[display_items_lista({symbol})]: {e}")

        # Obtener el ítem seleccionado con un solo click
        def on_item_selected(event):
            """Maneja selección simple en la lista"""
            selected_items = lista.selection()
            if selected_items:
                selected_id = selected_items[0]
                symbol = lista.item(selected_id, "text")

                # Verificar que no sea un nodo padre
                if symbol and not symbol.startswith(":"):
                    if symbol in DataHub.info:
                        display_items_lista(symbol)
                        self.itemsInfo = symbol

        # Doble click para expandir/contraer o mostrar detalle
        def on_double_click(event):
            """Maneja doble click en la lista"""
            selected_items = lista.selection()
            if selected_items:
                selected_id = selected_items[0]
                symbol = lista.item(selected_id, "text")

                # Si no es un nodo padre, mostrar detalle
                if symbol and not symbol.startswith(":"):
                    if symbol in DataHub.info:
                        display_items_lista(symbol)
                        self.itemsInfo = symbol

        # busca activo en lista
        def search_lista(first=None, symbol=None):
            log = False
            for padre_id in lista.get_children():
                padre = lista.item(padre_id, "text")
                for item_id in lista.get_children(padre_id):
                    if first is None:
                        if symbol == lista.item(item_id, "text"):
                            log = True
                            break
                    elif first is not None:
                        # return first de la lista
                        if padre != lastClose:
                            return lista.item(item_id, "text")
            return log

        # inserta lista los values de campo
        def insert_process(parent):
            for key, campo in DataHub.last_process.items():
                if isinstance(campo, dict):
                    lista.insert(
                        parent,
                        "end",
                        text=f" {key}: {campo['diaria_book_performance'].date()}",
                        tags=("colorTex",),
                    )

        # recorre e inserta hijos por cada nodo
        def insert_lista(parent=None, struct="info()"):

            if struct == "Last Daily()":
                # for padre_id in lista.get_children():
                #    if ": Last Process " = lista.item(padre_id, "text")

                # for item_id in lista.get_children(padre_id):
                #    lista.item(item_id, textalues=(nuevos_datos["nombre"],))
                pass

            elif struct == "info()":
                for key, value in DataHub.info.items():

                    if key == "TimeDataHub":
                        continue
                    else:
                        if not search_lista(symbol=key):
                            lista.insert(parent, "end", text=key)

                # start con la infor del primer Items
                if not self.itemsInfo:
                    display_first_item()
                else:
                    display_items_lista(self.itemsInfo)

            return lista

        # Itera  y update Treeview cada 3 seg
        def update_datahub():
            # Verificar si debemos continuar ejecutando
            if not self.is_running:
                return

            lista.item(root, open=True)
            insert_lista(parent=root)
            # Registrar el after_id para poder cancelarlo luego
            after_id = self.system.after(30000, update_datahub)
            self.after_ids.append(after_id)
            # DataHub.manager_after._safe(30000, update_datahub(), name="update_datahub")

        try:
            # define TreeView para mostras  Lista y detalle de items DataHub.Info()
            lista = ttk.Treeview(self.datahub, style="TFrame")
            detalle = ttk.Treeview(self.datahub, style="TFrame")

            # Configurar headers
            lista.heading("#0", text="DataHub - Símbolos")
            detalle.heading("#0", text="Información Detallada del Activo")

            # Configurar anchos
            lista.column("#0", width=180, minwidth=150)

            # Pack widgets
            lista.pack(side=tk.LEFT, fill=tk.BOTH, pady=5, padx=(5, 2))
            detalle.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, pady=5, padx=(2, 5))

            # Configurar colores y estilos mejorados (consistente con manager_buysell)
            detalle.tag_configure(
                "header", foreground="cyan", font=("TkDefaultFont", 10, "bold")
            )
            detalle.tag_configure(
                "section", foreground="yellow", font=("TkDefaultFont", 9, "bold")
            )
            detalle.tag_configure("info", foreground="lightgreen")
            detalle.tag_configure("summary", foreground="orange")
            detalle.tag_configure("value", foreground="white")
            detalle.tag_configure("error", foreground="red")
            detalle.tag_configure("warning", foreground="orange")

            # Tags antiguos para compatibilidad
            detalle.tag_configure("colorTex", foreground="orange")
            detalle.tag_configure("colorGroup", foreground=DataHub.bgcolor)

            # Bind eventos
            lista.bind("<<TreeviewSelect>>", on_item_selected)
            lista.bind("<Double-Button-1>", on_double_click)

            # --- Scrollbars ---
            hsb = ttk.Scrollbar(detalle, orient=tk.HORIZONTAL, command=detalle.xview)
            detalle.configure(xscroll=hsb.set)
            hsb.pack(side=tk.BOTTOM, fill=tk.X)

            # inicia insert de lista
            lastClose = ": Close Market(last) "
            process = lista.insert("", "end", text=lastClose)
            insert_process(process)

            root = lista.insert("", "end", text=f": {DataHub.info['TimeDataHub']}")

            # Mostrar mensaje inicial en detalle
            detalle.insert(
                "",
                "end",
                text="👈 Selecciona un símbolo de la izquierda",
                tags=("info",),
            )
            detalle.insert(
                "", "end", text="para ver su información detallada", tags=("info",)
            )
            detalle.insert("", "end", text="", tags=("spacer",))
            detalle.insert(
                "",
                "end",
                text="💡 Click simple o doble click para ver detalles",
                tags=("summary",),
            )

            update_datahub()
        except Exception as e:
            traceback.print_exc()
            print(f"datahub_system(): {e}")

    # detalla uso de cache
    def monitor_cache(self):
        """
        Visualiza CacheHut.cache con patrón lista-detalle mejorado.
        - LISTA (izquierda): Claves del cache con información resumida
        - DETALLE (derecha): Información completa del item en cache
        - Evento: Doble click para ver detalle completo

        Características:
            ✅ Ver claves actuales del cache
            ✅ Información de tipo, tamaño y timestamp
            ✅ Refrescar contenido automático
            ✅ Eliminar entradas manualmente
            ✅ Ver detalles completos de DataFrames y otros objetos
        """

        #   FUNCIONALIDAD PRINCIPAL
        def refresh_cache_list():
            """Recarga la lista de claves desde el cache."""
            try:
                # Limpiar lista
                for item in lista.get_children():
                    lista.delete(item)

                # Contador de elementos
                total_items = 0

                # Insertar items del cache
                for k, v in CacheHut.cache.items():
                    tipo = type(v).__name__

                    # Calcular tamaño aproximado
                    try:
                        size_bytes = sys.getsizeof(v)
                        if size_bytes < 1024:
                            size_str = f"{size_bytes}B"
                        elif size_bytes < 1024 * 1024:
                            size_str = f"{size_bytes/1024:.1f}KB"
                        else:
                            size_str = f"{size_bytes/(1024*1024):.1f}MB"
                    except:
                        size_str = "N/A"

                    # Insertar en lista con icono según tipo
                    if tipo == "DataFrame":
                        icon = "📊"
                    elif tipo in ["dict", "DotMap"]:
                        icon = "📂"
                    elif tipo in ["list", "tuple"]:
                        icon = "📋"
                    else:
                        icon = "📦"

                    lista.insert(
                        "",
                        tk.END,
                        text=f"{icon} {k}",
                        values=(tipo, size_str),
                        tags=("item",),
                    )
                    total_items += 1

                # Actualizar header con contador
                lista.heading("#0", text=f"Cache Keys ({total_items} items)")

                # Si no hay items
                if total_items == 0:
                    lista.insert(
                        "", "end", text="(Vacío - sin datos en cache)", tags=("empty",)
                    )

            except Exception as e:
                print(f"[refresh_cache_list()]: {e}")

        def display_cache_detail(key):
            """Muestra detalle completo del item seleccionado en cache"""
            try:
                # Limpiar detalle
                for item in detalle.get_children():
                    detalle.delete(item)

                # Obtener datos del cache
                data = CacheHut.cache.get(key)

                if data is None:
                    detalle.insert(
                        "",
                        "end",
                        text=f"⚠️ {key}: No disponible o expirado",
                        tags=("warning",),
                    )
                    return

                # Header con el nombre de la clave
                detalle.insert("", "end", text=f"🔑 Key: {key}", tags=("header",))
                detalle.insert("", "end", text="", tags=("spacer",))

                # Información del tipo de objeto
                tipo_data = type(data).__name__
                detalle.insert("", "end", text=f"📦 Tipo: {tipo_data}", tags=("info",))

                # Tamaño del objeto
                try:
                    size_bytes = sys.getsizeof(data)
                    if size_bytes < 1024:
                        size_str = f"{size_bytes} bytes"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes/1024:.2f} KB"
                    else:
                        size_str = f"{size_bytes/(1024*1024):.2f} MB"
                    detalle.insert(
                        "", "end", text=f"💾 Tamaño: {size_str}", tags=("info",)
                    )
                except:
                    pass

                # Timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                detalle.insert(
                    "", "end", text=f"⏰ Consultado: {timestamp}", tags=("info",)
                )
                detalle.insert("", "end", text="", tags=("spacer",))

                # Mostrar contenido según el tipo
                if isinstance(data, pd.DataFrame):
                    # DataFrame
                    detalle.insert(
                        "", "end", text="📊 DataFrame - Resumen", tags=("section",)
                    )
                    detalle.insert(
                        "", "end", text=f"  Filas: {data.shape[0]:,}", tags=("summary",)
                    )
                    detalle.insert(
                        "",
                        "end",
                        text=f"  Columnas: {data.shape[1]}",
                        tags=("summary",),
                    )
                    detalle.insert(
                        "",
                        "end",
                        text=f"  Nombres: {list(data.columns)[:8]}",
                        tags=("summary",),
                    )
                    if len(data.columns) > 8:
                        detalle.insert(
                            "",
                            "end",
                            text=f"  ... y {len(data.columns) - 8} más",
                            tags=("summary",),
                        )

                    # Mostrar primeras filas
                    detalle.insert("", "end", text="", tags=("spacer",))
                    node = detalle.insert(
                        "",
                        "end",
                        text="📋 Primeras 5 filas (haz doble click para ver completo)",
                        tags=("section",),
                    )
                    df_string = data.head(5).to_string()
                    for line in df_string.split("\n")[:15]:  # Limitar líneas
                        detalle.insert(node, "end", text=line, tags=("data",))

                elif isinstance(data, dict):
                    # Diccionario
                    detalle.insert(
                        "", "end", text="📂 Diccionario - Contenido", tags=("section",)
                    )
                    detalle.insert(
                        "",
                        "end",
                        text=f"  Total de claves: {len(data)}",
                        tags=("summary",),
                    )
                    detalle.insert("", "end", text="", tags=("spacer",))

                    node = detalle.insert(
                        "", "end", text="🔹 Estructura", tags=("section",)
                    )
                    for idx, (k, v) in enumerate(data.items()):
                        if idx >= 20:  # Limitar a 20 items
                            detalle.insert(
                                node,
                                "end",
                                text=f"  ... y {len(data) - 20} más",
                                tags=("value",),
                            )
                            break
                        v_str = str(v)[:100] + "..." if len(str(v)) > 100 else str(v)
                        detalle.insert(
                            node, "end", text=f"  {k}: {v_str}", tags=("value",)
                        )

                elif isinstance(data, (list, tuple)):
                    # Lista o tupla
                    detalle.insert(
                        "", "end", text=f"📋 {tipo_data} - Contenido", tags=("section",)
                    )
                    detalle.insert(
                        "",
                        "end",
                        text=f"  Total de elementos: {len(data)}",
                        tags=("summary",),
                    )
                    detalle.insert("", "end", text="", tags=("spacer",))

                    node = detalle.insert(
                        "", "end", text="🔹 Elementos", tags=("section",)
                    )
                    for idx, item in enumerate(data):
                        if idx >= 20:  # Limitar a 20 items
                            detalle.insert(
                                node,
                                "end",
                                text=f"  ... y {len(data) - 20} más",
                                tags=("value",),
                            )
                            break
                        item_str = (
                            str(item)[:100] + "..."
                            if len(str(item)) > 100
                            else str(item)
                        )
                        detalle.insert(
                            node, "end", text=f"  [{idx}]: {item_str}", tags=("value",)
                        )

                else:
                    # Otros tipos
                    detalle.insert("", "end", text="📦 Valor", tags=("section",))
                    value_str = (
                        str(data)[:500] + "..." if len(str(data)) > 500 else str(data)
                    )
                    detalle.insert("", "end", text=value_str, tags=("value",))

            except Exception as e:
                detalle.insert(
                    "", "end", text=f"❌ Error al mostrar detalle: {e}", tags=("error",)
                )
                print(f"[display_cache_detail({key})]: {e}")

        def remove_selected_key():
            """Elimina la clave seleccionada del cache."""
            selected = lista.selection()
            if not selected:
                self.messagebox.showinfo(
                    "Información", "Seleccione una clave para eliminar."
                )
                return

            # Extraer key del texto (remover icono)
            item_text = lista.item(selected[0], "text")
            key = item_text.split(" ", 1)[1] if " " in item_text else item_text

            if key in CacheHut.cache:
                del CacheHut.cache[key]
                self.messagebox.showinfo(
                    "Cache", f"✅ Clave '{key}' eliminada del cache."
                )
                refresh_cache_list()
                # Limpiar detalle
                for item in detalle.get_children():
                    detalle.delete(item)
                detalle.insert(
                    "",
                    "end",
                    text="👈 Selecciona un item de la izquierda",
                    tags=("info",),
                )
            else:
                self.messagebox.showwarning(
                    "Cache", f"⚠️ Clave '{key}' no encontrada o ya expirada."
                )

        #   EVENTOS DE INTERFAZ
        def on_double_click(event):
            """Maneja doble clic sobre una clave: muestra detalle completo."""
            selected = lista.selection()
            if not selected:
                return

            # Extraer key del texto (remover icono)
            item_text = lista.item(selected[0], "text")
            if item_text.startswith("("):  # Es el mensaje de vacío
                return

            key = item_text.split(" ", 1)[1] if " " in item_text else item_text
            display_cache_detail(key)

        def on_item_selected(event):
            """Maneja selección simple en la lista"""
            selected = lista.selection()
            if selected:
                item_text = lista.item(selected[0], "text")
                if not item_text.startswith("("):  # No es mensaje de vacío
                    key = item_text.split(" ", 1)[1] if " " in item_text else item_text
                    display_cache_detail(key)

        def auto_refresh():
            """Auto-actualiza la lista cada 30 segundos"""
            # Verificar si debemos continuar ejecutando
            if not self.is_running:
                return

            refresh_cache_list()
            # Registrar el after_id para poder cancelarlo luego
            after_id = self.system.after(30000, auto_refresh)
            self.after_ids.append(after_id)

        try:
            # Crear TreeViews para lista y detalle
            lista = ttk.Treeview(self.cache, columns=("tipo", "tamaño"), style="TFrame")
            detalle = ttk.Treeview(self.cache, style="TFrame")

            # Configurar headers y columnas de lista
            lista.heading("#0", text="Cache Keys")
            lista.heading("tipo", text="Tipo")
            lista.heading("tamaño", text="Tamaño")

            lista.column("#0", width=200, minwidth=150)
            lista.column("tipo", width=100, minwidth=80)
            lista.column("tamaño", width=80, minwidth=60)

            # Configurar header de detalle
            detalle.heading("#0", text="Información Detallada")

            # Pack widgets
            lista.pack(side=tk.LEFT, fill=tk.BOTH, pady=5, padx=(5, 2))
            detalle.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5, padx=(2, 5))

            # Configurar colores y estilos (consistente con otros módulos)
            detalle.tag_configure(
                "header", foreground="cyan", font=("TkDefaultFont", 10, "bold")
            )
            detalle.tag_configure(
                "section", foreground="yellow", font=("TkDefaultFont", 9, "bold")
            )
            detalle.tag_configure("info", foreground="lightgreen")
            detalle.tag_configure("summary", foreground="orange")
            detalle.tag_configure("value", foreground="white")
            detalle.tag_configure("data", foreground="lightgray", font=("Courier", 8))
            detalle.tag_configure("error", foreground="red")
            detalle.tag_configure("warning", foreground="orange")

            lista.tag_configure("item", foreground="lightgreen")
            lista.tag_configure("empty", foreground="gray")

            # --- Scrollbars ---
            hsb = ttk.Scrollbar(detalle, orient=tk.HORIZONTAL, command=detalle.xview)
            detalle.configure(xscroll=hsb.set)
            hsb.pack(side=tk.BOTTOM, fill=tk.X)

            # --- Botonera ---
            frame_btn = ttk.Frame(self.cache)
            frame_btn.pack(fill=tk.X, pady=(0, 5), padx=5)

            ttk.Button(frame_btn, text="🔄 Refrescar", command=refresh_cache_list).pack(
                side=tk.LEFT, padx=5
            )
            ttk.Button(frame_btn, text="🗑️ Eliminar", command=remove_selected_key).pack(
                side=tk.LEFT, padx=5
            )

            # --- Bind eventos ---
            lista.bind("<Double-Button-1>", on_double_click)
            lista.bind("<<TreeviewSelect>>", on_item_selected)

            # Mostrar mensaje inicial en detalle
            detalle.insert(
                "", "end", text="👈 Selecciona un item de la izquierda", tags=("info",)
            )
            detalle.insert(
                "", "end", text="para ver su información detallada", tags=("info",)
            )
            detalle.insert("", "end", text="", tags=("spacer",))
            detalle.insert(
                "",
                "end",
                text="💡 Click simple o doble click para ver detalles",
                tags=("summary",),
            )

            # --- Carga inicial y auto-refresh ---
            refresh_cache_list()
            auto_refresh()

        except Exception as e:
            traceback.print_exc()
            print(f"monitor_cache(): {e}")

    # detalla estados de conexiones
    def connect_api(self):
        """
        Visualiza estado de conexiones API en lista compacta.
        - LISTA: APIs disponibles con estado e icono
        - EVENTO: Doble click abre ventana con detalles completos

        APIs monitoreadas:
            ✅ Binance (WebSocket Streams & API Client)
            ✅ Interactive Brokers (IBKR)
            ✅ Yahoo Finance
            ✅ Finviz
        """

        def get_api_status():
            """Obtiene el estado actual de las APIs"""
            apis = {}

            try:
                # Binance WebSocket Streams
                try:
                    binance_ws = (
                        hasattr(DataHub, "WStreams") and DataHub.WStreams is not None
                    )
                    apis["Binance WebSocket"] = {
                        "status": "🟢 Conectado" if binance_ws else "🔴 Desconectado",
                        "type": "WebSocket Streams",
                        "endpoint": "wss://stream.binance.com:9443",
                        "connected": binance_ws,
                        "description": "Streaming de precios en tiempo real",
                    }
                except:
                    apis["Binance WebSocket"] = {
                        "status": "⚪ No Disponible",
                        "type": "WebSocket Streams",
                        "endpoint": "N/A",
                        "connected": False,
                        "description": "Streaming de precios en tiempo real",
                    }

                # Binance API Client
                try:
                    binance_api = (
                        hasattr(DataHub, "WsClient") and DataHub.WsClient is not None
                    )
                    apis["Binance API"] = {
                        "status": "🟢 Conectado" if binance_api else "🔴 Desconectado",
                        "type": "WebSocket API Client",
                        "endpoint": "wss://ws-api.binance.com:443/ws-api/v3",
                        "connected": binance_api,
                        "description": "API de trading y consultas",
                    }
                except:
                    apis["Binance API"] = {
                        "status": "⚪ No Disponible",
                        "type": "WebSocket API Client",
                        "endpoint": "N/A",
                        "connected": False,
                        "description": "API de trading y consultas",
                    }

                # Yahoo Finance
                try:
                    yfinance = DataHub.SessionYfinance is not None
                    apis["Yahoo Finance"] = {
                        "status": "🟢 Activo" if yfinance else "🔴 Inactivo",
                        "type": "HTTP REST API",
                        "endpoint": "https://query1.finance.yahoo.com",
                        "connected": yfinance,
                        "description": "Datos de mercado y fundamentales",
                    }
                except:
                    apis["Yahoo Finance"] = {
                        "status": "⚪ No Disponible",
                        "type": "HTTP REST API",
                        "endpoint": "N/A",
                        "connected": False,
                        "description": "Datos de mercado y fundamentales",
                    }

                # Interactive Brokers
                apis["Interactive Brokers"] = {
                    "status": "🟡 Configurado",
                    "type": "TWS API",
                    "endpoint": "localhost:7497",
                    "connected": True,  # Asumir configurado
                    "description": "Trading y datos de mercado",
                }

                # Finviz
                apis["Finviz"] = {
                    "status": "🟢 Disponible",
                    "type": "Web Scraping",
                    "endpoint": "https://finviz.com",
                    "connected": True,  # Siempre disponible si hay internet
                    "description": "Análisis técnico y fundamentales",
                }

            except Exception as e:
                print(f"[get_api_status()]: {e}")

            return apis

        def refresh_api_list():
            """Actualiza la lista de APIs"""
            try:
                # Limpiar lista
                for item in lista.get_children():
                    lista.delete(item)

                # Obtener estado de APIs
                apis = get_api_status()

                # Contador de conectadas
                connected_count = sum(
                    1 for api in apis.values() if api.get("connected")
                )
                total_count = len(apis)

                # Insertar APIs en la lista con tres columnas
                for name, info in apis.items():
                    status = info["status"]
                    api_type = info["type"]

                    # Extraer solo el emoji de estado
                    status_emoji = status.split()[0] if status else "⚪"

                    lista.insert(
                        "",
                        tk.END,
                        text=name,  # Nombre de API
                        values=(api_type, status),  # Tipo y Estado completo
                        tags=("item",),
                    )

                # Actualizar header con contador
                lista.heading(
                    "#0", text=f"API ({connected_count}/{total_count} activas)"
                )

            except Exception as e:
                print(f"[refresh_api_list()]: {e}")

        def show_api_detail_window(api_name):
            """Abre ventana emergente con detalles de la API seleccionada"""
            try:
                # El nombre ya viene limpio (sin emoji)
                clean_name = api_name

                # Obtener información de la API
                apis = get_api_status()
                api_info = apis.get(clean_name)

                if not api_info:
                    self.messagebox.showwarning(
                        "API Info", f"⚠️ {clean_name}: No encontrada"
                    )
                    return

                # Crear ventana Toplevel
                detail_window = tk.Toplevel(self.system)
                detail_window.title(f"🌐 Información de API - {clean_name}")
                detail_window.geometry("600x450")
                detail_window.transient(self.system)  # Ventana modal relativa al padre

                # Frame principal con scrollbar
                main_frame = ttk.Frame(detail_window, padding=10)
                main_frame.pack(fill=tk.BOTH, expand=True)

                # Treeview para mostrar información
                tree = ttk.Treeview(main_frame, style="TFrame")
                tree.heading("#0", text=f"Detalles de {clean_name}")
                tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

                # Configurar colores
                tree.tag_configure(
                    "header", foreground="cyan", font=("TkDefaultFont", 11, "bold")
                )
                tree.tag_configure(
                    "section", foreground="yellow", font=("TkDefaultFont", 9, "bold")
                )
                tree.tag_configure("info", foreground="lightgreen")
                tree.tag_configure("summary", foreground="orange")
                tree.tag_configure("value", foreground="white")

                # Scrollbar
                vsb = ttk.Scrollbar(tree, orient=tk.VERTICAL, command=tree.yview)
                tree.configure(yscroll=vsb.set)
                vsb.pack(side=tk.RIGHT, fill=tk.Y)

                # Header
                tree.insert("", "end", text=f"🌐 API: {clean_name}", tags=("header",))
                tree.insert("", "end", text="", tags=("spacer",))

                # Información básica
                tree.insert(
                    "", "end", text=f"📊 Estado: {api_info['status']}", tags=("info",)
                )
                tree.insert(
                    "", "end", text=f"🔧 Tipo: {api_info['type']}", tags=("info",)
                )
                tree.insert(
                    "",
                    "end",
                    text=f"🔗 Endpoint: {api_info['endpoint']}",
                    tags=("value",),
                )
                tree.insert(
                    "",
                    "end",
                    text=f"📝 Descripción: {api_info['description']}",
                    tags=("summary",),
                )

                # Timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                tree.insert(
                    "", "end", text=f"⏰ Consultado: {timestamp}", tags=("info",)
                )
                tree.insert("", "end", text="", tags=("spacer",))

                # Información adicional según API
                node = tree.insert(
                    "", "end", text="📋 Información Adicional", tags=("section",)
                )

                if "Binance" in clean_name:
                    tree.insert(
                        node,
                        "end",
                        text="  • Mercado: Cryptocurrencies",
                        tags=("value",),
                    )
                    tree.insert(
                        node, "end", text="  • Frecuencia: Tiempo real", tags=("value",)
                    )
                    tree.insert(
                        node,
                        "end",
                        text="  • Límites: Sin límite en WebSocket",
                        tags=("value",),
                    )
                    tree.insert(
                        node,
                        "end",
                        text="  • Documentación: https://binance-docs.github.io",
                        tags=("value",),
                    )

                elif "Yahoo Finance" in clean_name:
                    tree.insert(
                        node,
                        "end",
                        text="  • Mercado: Stocks, ETFs, Indices",
                        tags=("value",),
                    )
                    tree.insert(
                        node,
                        "end",
                        text="  • Frecuencia: 15 min delay (free)",
                        tags=("value",),
                    )
                    tree.insert(
                        node, "end", text="  • Límites: 2000 req/hora", tags=("value",)
                    )
                    tree.insert(
                        node, "end", text="  • Cobertura: Global", tags=("value",)
                    )

                elif "Interactive Brokers" in clean_name:
                    tree.insert(
                        node,
                        "end",
                        text="  • Mercado: Global (Stocks, Forex, etc)",
                        tags=("value",),
                    )
                    tree.insert(
                        node, "end", text="  • Frecuencia: Tiempo real", tags=("value",)
                    )
                    tree.insert(
                        node,
                        "end",
                        text="  • Requiere: TWS o IB Gateway activo",
                        tags=("value",),
                    )
                    tree.insert(
                        node,
                        "end",
                        text="  • Puerto: 7497 (TWS) / 4002 (Gateway)",
                        tags=("value",),
                    )

                elif "Finviz" in clean_name:
                    tree.insert(
                        node, "end", text="  • Mercado: US Stocks", tags=("value",)
                    )
                    tree.insert(
                        node,
                        "end",
                        text="  • Datos: Screener, Charts, News",
                        tags=("value",),
                    )
                    tree.insert(
                        node, "end", text="  • Método: Web Scraping", tags=("value",)
                    )
                    tree.insert(
                        node,
                        "end",
                        text="  • Limitaciones: Requiere acceso web",
                        tags=("value",),
                    )

                # Expandir nodo
                tree.item(node, open=True)

                # Botón cerrar
                btn_frame = ttk.Frame(main_frame)
                btn_frame.pack(fill=tk.X, pady=(5, 0))

                ttk.Button(
                    btn_frame, text="✖️ Cerrar", command=detail_window.destroy
                ).pack(side=tk.RIGHT, padx=5)

                # Centrar ventana
                detail_window.update_idletasks()
                x = (detail_window.winfo_screenwidth() // 2) - (600 // 2)
                y = (detail_window.winfo_screenheight() // 2) - (450 // 2)
                detail_window.geometry(f"600x450+{x}+{y}")

            except Exception as e:
                traceback.print_exc()
                print(f"[show_api_detail_window({api_name})]: {e}")
                self.messagebox.showerror("Error", f"❌ Error al mostrar detalle: {e}")

        def on_double_click(event):
            """Maneja doble click para abrir ventana de detalle"""
            selected = lista.selection()
            if selected:
                api_name = lista.item(selected[0], "text")
                show_api_detail_window(api_name)

        def auto_refresh():
            """Auto-actualiza la lista cada 30 segundos"""
            # Verificar si debemos continuar ejecutando
            if not self.is_running:
                return

            refresh_api_list()
            # Registrar el after_id para poder cancelarlo luego
            after_id = self.system.after(30000, auto_refresh)
            self.after_ids.append(after_id)

        try:
            # Frame contenedor principal
            main_frame = ttk.Frame(self.connect)
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Label de instrucciones
            info_frame = ttk.Frame(main_frame)
            info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

            # Crear TreeView solo para lista (más espacio)
            lista = ttk.Treeview(main_frame, columns=("tipo", "estado"), style="TFrame")

            # Configurar headers y columnas
            lista.heading("#0", text="API")
            lista.heading("tipo", text="Tipo de Conexión")
            lista.heading("estado", text="Estado")

            lista.column("#0", width=180, minwidth=150)
            lista.column("tipo", width=150, minwidth=120)
            lista.column("estado", width=120, minwidth=100)

            # Pack lista con scrollbar
            lista.pack(fill=tk.BOTH, expand=True)

            # Configurar colores
            lista.tag_configure("item", foreground="lightgreen")

            # --- Scrollbars ---
            # vsb = ttk.Scrollbar(lista, orient=tk.VERTICAL, command=lista.yview)
            # lista.configure(yscroll=vsb.set)
            # vsb.pack(side=tk.RIGHT, fill=tk.Y)

            # --- Bind evento doble click ---
            lista.bind("<Double-Button-1>", on_double_click)

            # --- Carga inicial y auto-refresh ---
            refresh_api_list()
            auto_refresh()
        except Exception as e:
            traceback.print_exc()
            print(f"connect_api(): {e}")

    # detalla estados de conexiones
    def debugging_system(self):
        try:

            cols = ["Option"]
            tree = ttk.Treeview(self.debugging, columns=cols, height=15, style="TFrame")
            tree.heading("#0", text="Logger")
            tree.heading("Option", text="Level")

            tree.column("#0", width=200, minwidth=100)
            tree.column("Option", width=80, minwidth=80)
            tree.pack(expand=True, fill="both", pady=5, padx=(5, 5))

            for key, handler in DataHub.logger.items():
                tree.insert(
                    "",
                    "end",
                    text=f"{key}",
                    values=f"{logging.getLevelName(handler.level)}",
                )
        except Exception as e:
            print("debugging_system(): {}".format(e))

    # visualiza manager_buysell con lista-detalle
    def manager_buysell_system(self):
        """
        Visualiza DataHub.manager_buysell con patrón lista-detalle.
        - LISTA (izquierda): Keys de manager_buysell (dividends, sector, activos, region)
        - DETALLE (derecha): Información completa y resumen del item seleccionado
        - Evento: Doble click para ver detalle
        """

        def display_buysell_detail(key):
            """Muestra detalle del item seleccionado en manager_buysell"""
            try:
                # Limpiar detalle
                for item in detalle.get_children():
                    detalle.delete(item)

                # Obtener datos
                data = DataHub.manager_buysell.get(key)

                if data is None:
                    detalle.insert(
                        "", "end", text=f"⚠️ {key}: No disponible aún", tags=("warning",)
                    )
                    return

                # Header con el nombre del item
                detalle.insert(
                    "", "end", text=f"📊 Item: {key.upper()}", tags=("header",)
                )
                detalle.insert("", "end", text="", tags=("spacer",))

                # Información del tipo de objeto
                tipo_data = type(data).__name__
                detalle.insert(
                    "", "end", text=f"Tipo de objeto: {tipo_data}", tags=("info",)
                )

                # Timestamp de actualización
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                detalle.insert(
                    "", "end", text=f"Última consulta: {timestamp}", tags=("info",)
                )
                detalle.insert("", "end", text="", tags=("spacer",))

                # Mostrar estructura completa del objeto
                node_estructura = detalle.insert(
                    "", "end", text="📂 Estructura Completa", tags=("section",)
                )

                # Si es un diccionario, mostrar sus claves y valores
                if isinstance(data, dict):
                    detalle.insert(
                        "",
                        "end",
                        text=f"Total de claves: {len(data)}",
                        tags=("summary",),
                    )
                    detalle.insert("", "end", text="", tags=("spacer",))

                    for subkey, subvalue in data.items():
                        if isinstance(subvalue, dict):
                            # Crear nodo expandible para diccionarios anidados
                            subnode = detalle.insert(
                                node_estructura,
                                "end",
                                text=f"🔹 {subkey}",
                                tags=("subkey",),
                            )
                            for k, v in subvalue.items():
                                detalle.insert(
                                    subnode, "end", text=f"  {k}: {v}", tags=("value",)
                                )
                        elif isinstance(subvalue, (list, tuple)):
                            # Mostrar listas/tuplas
                            subnode = detalle.insert(
                                node_estructura,
                                "end",
                                text=f"🔹 {subkey} (lista con {len(subvalue)} elementos)",
                                tags=("subkey",),
                            )
                            for idx, item in enumerate(
                                subvalue[:10]
                            ):  # Mostrar solo primeros 10
                                detalle.insert(
                                    subnode,
                                    "end",
                                    text=f"  [{idx}]: {item}",
                                    tags=("value",),
                                )
                            if len(subvalue) > 10:
                                detalle.insert(
                                    subnode,
                                    "end",
                                    text=f"  ... y {len(subvalue) - 10} más",
                                    tags=("value",),
                                )
                        elif isinstance(subvalue, pd.DataFrame):
                            # Mostrar info de DataFrames
                            df_info = f"DataFrame: {subvalue.shape[0]} filas × {subvalue.shape[1]} columnas"
                            subnode = detalle.insert(
                                node_estructura,
                                "end",
                                text=f"🔹 {subkey}",
                                tags=("subkey",),
                            )
                            detalle.insert(
                                subnode, "end", text=f"  {df_info}", tags=("value",)
                            )
                            detalle.insert(
                                subnode,
                                "end",
                                text=f"  Columnas: {list(subvalue.columns)}",
                                tags=("value",),
                            )
                        else:
                            # Valores simples
                            detalle.insert(
                                node_estructura,
                                "end",
                                text=f"🔹 {subkey}: {subvalue}",
                                tags=("value",),
                            )

                # Si es DataFrame directamente
                elif isinstance(data, pd.DataFrame):
                    detalle.insert(
                        "", "end", text="📋 Resumen del DataFrame", tags=("section",)
                    )
                    detalle.insert(
                        "", "end", text=f"Filas: {data.shape[0]}", tags=("summary",)
                    )
                    detalle.insert(
                        "", "end", text=f"Columnas: {data.shape[1]}", tags=("summary",)
                    )
                    detalle.insert(
                        "",
                        "end",
                        text=f"Columnas: {list(data.columns)}",
                        tags=("summary",),
                    )

                    # Mostrar primeras filas
                    detalle.insert("", "end", text="", tags=("spacer",))
                    detalle.insert(
                        "", "end", text="📊 Primeras 5 filas:", tags=("section",)
                    )
                    df_string = data.head().to_string()
                    for line in df_string.split("\n"):
                        detalle.insert("", "end", text=line, tags=("data",))

                # Si es otro tipo de objeto
                else:
                    detalle.insert(
                        node_estructura, "end", text=str(data)[:500], tags=("value",)
                    )

                # Expandir nodo principal
                detalle.item(node_estructura, open=True)

            except Exception as e:
                detalle.insert(
                    "", "end", text=f"❌ Error al mostrar detalle: {e}", tags=("error",)
                )
                print(f"[display_buysell_detail({key})]: {e}")

        def on_double_click(event):
            """Evento de doble click en la lista"""
            selected = lista.selection()
            if selected:
                key = lista.item(selected[0], "text")
                display_buysell_detail(key)

        def update_buysell_list():
            """Actualiza la lista de manager_buysell cada 30 segundos"""
            try:
                # Verificar si debemos continuar ejecutando
                if not self.is_running:
                    return

                # Limpiar lista
                for item in lista.get_children():
                    lista.delete(item)

                # Insertar keys de manager_buysell
                if DataHub.manager_buysell:
                    for key in sorted(DataHub.manager_buysell.keys()):
                        lista.insert("", "end", text=key, tags=("item",))
                else:
                    lista.insert(
                        "", "end", text="(Vacío - esperando datos)", tags=("empty",)
                    )

                # Programar siguiente actualización y registrar el after_id
                after_id = self.system.after(30000, update_buysell_list)
                self.after_ids.append(after_id)

            except Exception as e:
                print(f"[update_buysell_list()]: {e}")

        try:
            # Crear TreeViews para lista y detalle
            lista = ttk.Treeview(self.buysell, style="TFrame")
            detalle = ttk.Treeview(self.buysell, style="TFrame")

            # Configurar headers
            lista.heading("#0", text="Manager BuySell")
            detalle.heading("#0", text="Información Detallada")

            # Configurar anchos
            lista.column("#0", width=180, minwidth=150)

            # Pack widgets
            lista.pack(side=tk.LEFT, fill=tk.BOTH, pady=5, padx=(5, 2))
            detalle.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5, padx=(2, 5))

            # Configurar colores y estilos
            detalle.tag_configure(
                "header", foreground="cyan", font=("TkDefaultFont", 10, "bold")
            )
            detalle.tag_configure(
                "section", foreground="yellow", font=("TkDefaultFont", 9, "bold")
            )
            detalle.tag_configure("info", foreground="lightgreen")
            detalle.tag_configure("summary", foreground="orange")
            detalle.tag_configure("subkey", foreground="lightblue")
            detalle.tag_configure("value", foreground="white")
            detalle.tag_configure("data", foreground="lightgray", font=("Courier", 8))
            detalle.tag_configure("error", foreground="red")
            detalle.tag_configure("warning", foreground="orange")
            lista.tag_configure("item", foreground="lightgreen")
            lista.tag_configure("empty", foreground="gray")

            # Bind evento doble click
            lista.bind("<Double-Button-1>", on_double_click)

            # Scrollbars para detalle
            hsb = ttk.Scrollbar(detalle, orient=tk.HORIZONTAL, command=detalle.xview)
            detalle.configure(xscroll=hsb.set)
            hsb.pack(side=tk.BOTTOM, fill=tk.X)

            # Iniciar actualización de lista
            update_buysell_list()

            # Mostrar mensaje inicial en detalle
            detalle.insert(
                "",
                "end",
                text="👈 Haz doble click en un item de la izquierda",
                tags=("info",),
            )
            detalle.insert(
                "", "end", text="para ver su información detallada", tags=("info",)
            )
        except Exception as e:
            print(f"manager_buysell_system(): {e}")

    def rebalanceo_system(self):
        """
        Visualiza resultados del motor de rebalanceo con patrón lista-detalle.
        - LISTA (izquierda): Ranking de activos priorizados
        - DETALLE (derecha): Score, impacto por dimensión, monto sugerido
        """
        def display_rebalanceo_detail(index):
            """Muestra detalle del activo seleccionado"""
            try:
                for item in detalle.get_children():
                    detalle.delete(item)

                if not hasattr(DataHub, 'rebalanceo') or not DataHub.rebalanceo:
                    detalle.insert("", "end", text="⚠️ Motor de rebalanceo no ejecutado aún", tags=("warning",))
                    return

                asignaciones = DataHub.rebalanceo.get("asignaciones", [])

                if index >= len(asignaciones):
                    detalle.insert("", "end", text="⚠️ Índice fuera de rango", tags=("warning",))
                    return

                item = asignaciones[index]

                detalle.insert("", "end", text=f"📊 Symbol: {item['symbol']}", tags=("header",))
                detalle.insert("", "end", text="", tags=("spacer",))

                detalle.insert("", "end", text=f"Score: {item['score']:.4f}", tags=("info",))
                detalle.insert("", "end", text=f"Monto sugerido: ${item['monto_sugerido']:,.2f}", tags=("info",))
                detalle.insert("", "end", text=f"Presupuesto (Pinvertir): ${item['pinvertir']:,.2f}", tags=("info",))
                detalle.insert("", "end", text="", tags=("spacer",))

                node_impacto = detalle.insert("", "end", text="📂 Impacto por dimensión", tags=("section",))

                impacto = item.get("impacto", {})
                for dim, valor in impacto.items():
                    if dim not in ["gap_valor_total", "gap_valor_norm"] and valor > 0:
                        detalle.insert(node_impacto, "end", text=f"  {dim}: {valor:.4f}", tags=("value",))

                detalle.insert("", "end", text="", tags=("spacer",))
                detalle.insert("", "end", text=f"Gap valor total: ${impacto.get('gap_valor_total', 0):,.2f}", tags=("summary",))
                detalle.insert("", "end", text=f"Gap valor norm: {impacto.get('gap_valor_norm', 0):.4f}", tags=("summary",))

            except Exception as e:
                print(f"display_rebalanceo_detail(): {e}")

        def update_rebalanceo_list():
            """Actualiza la lista del ranking cada 30 segundos"""
            try:
                if not self.is_running:
                    return

                lista.delete(*lista.get_children())

                if not hasattr(DataHub, 'rebalanceo') or not DataHub.rebalanceo:
                    lista.insert("", "end", text="⏳ Esperando ejecución...", values=("", ""))
                else:
                    # Iterar sobre todos los vehículos en DataHub.rebalanceo
                    for vehiculo, datos in DataHub.rebalanceo.items():
                        timestamp = datos.get("timestamp", "N/A")
                        # Formatear timestamp si es datetime
                        if timestamp != "N/A" and hasattr(timestamp, 'strftime'):
                            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            timestamp_str = str(timestamp)

                        lista.insert("", "end", text=f"📋 {vehiculo}", values=("", ""), tags=("header",))
                        lista.insert("", "end", text=f"🕐 {timestamp_str}", values=("", ""), tags=("info",))

                        asignaciones = datos.get("asignaciones", [])

                        if not asignaciones:
                            lista.insert("", "end", text="  Sin recomendaciones", values=("", ""), tags=("info",))
                        else:
                            for idx, item in enumerate(asignaciones):
                                lista.insert(
                                    "",
                                    "end",
                                    text=f"  {item['symbol']}",
                                    values=(f"{item['score']:.4f}", f"${item['monto_sugerido']:,.0f}"),
                                    tags=("item",)
                                )

                        lista.insert("", "end", text="", values=("", ""))

                # Actualizar también el panel de gaps
                show_gap_summary()

                after_id = self.system.after(30000, update_rebalanceo_list)
                self.after_ids.append(after_id)

            except Exception as e:
                print(f"update_rebalanceo_list(): {e}")

        try:
            lista = ttk.Treeview(self.rebalanceo, columns=("score", "monto"), height=12, show="tree headings", style="TFrame")
            lista.column("#0", width=150, anchor="w")
            lista.column("score", width=80, anchor="center")
            lista.column("monto", width=100, anchor="e")

            lista.heading("#0", text="Ranking Rebalanceo")
            lista.heading("score", text="Score")
            lista.heading("monto", text="Monto $")

            lista.tag_configure("header", background="black", foreground="lime")
            lista.tag_configure("info", foreground="white")
            lista.tag_configure("item", foreground="lightgreen")

            detalle = ttk.Treeview(self.rebalanceo, height=12, show="tree", style="TFrame")
            detalle.column("#0", width=400)

            detalle.tag_configure("header", font=("Arial", 10, "bold"), foreground="lime")
            detalle.tag_configure("section", font=("Arial", 9, "bold"), foreground="white")
            detalle.tag_configure("info", foreground="lightgray")
            detalle.tag_configure("summary", foreground="lime", font=("Arial", 9, "bold"))
            detalle.tag_configure("value", foreground="lightgreen")
            detalle.tag_configure("spacer", font=("Arial", 2))
            detalle.tag_configure("warning", foreground="orange")

            lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
            detalle.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

            def on_double_click(event):
                item = lista.selection()
                if item:
                    valores = lista.item(item[0])
                    texto = valores["text"]
                    if texto.startswith("#"):
                        index = int(texto.split()[0][1:]) - 1
                        display_rebalanceo_detail(index)

            lista.bind("<Double-1>", on_double_click)

            def show_gap_summary():
                """Muestra resumen de gaps de todos los vehículos"""
                try:
                    for item in detalle.get_children():
                        detalle.delete(item)

                    if not hasattr(DataHub, 'rebalanceo') or not DataHub.rebalanceo:
                        detalle.insert("", "end", text="⏳ Esperando primera ejecución", tags=("info",))
                        return

                    detalle.insert("", "end", text="📊 Estado del Portfolio", tags=("header",))
                    detalle.insert("", "end", text="", tags=("spacer",))

                    # Iterar sobre todos los vehículos
                    for vehiculo, datos in DataHub.rebalanceo.items():
                        detalle.insert("", "end", text=f"🚗 {vehiculo}", tags=("section",))

                        gaps = datos.get("gaps", {})
                        if gaps:
                            for dim, valor in gaps.items():
                                color = "value" if valor > 0 else "info"
                                detalle.insert("", "end", text=f"  {dim}: {valor:.4f}", tags=(color,))
                        else:
                            detalle.insert("", "end", text="  Sin gaps", tags=("info",))

                        ranking = datos.get("ranking", [])
                        candidatos_con_score = sum(1 for c in ranking if c.get('score', 0) > 0)

                        detalle.insert("", "end", text=f"  Evaluados: {len(ranking)}, Score>0: {candidatos_con_score}", tags=("info",))
                        detalle.insert("", "end", text="", tags=("spacer",))

                    detalle.insert("", "end", text="💡 Doble click en un activo para ver detalle", tags=("info",))

                except Exception as e:
                    print(f"show_gap_summary(): {e}")

            update_rebalanceo_list()
            show_gap_summary()

        except Exception as e:
            print(f"rebalanceo_system(): {e}")

    # plot uso %CPU y %RAM
    def monitor_realtime(self):
        """
        Dibuja el gráfico en tiempo real de CPU y RAM.
        """

        # valida se debe mostrar o no performance
        if not DataHub.display:
            return

        # variables de entorno
        colorfondo = DataHub.cchart["plot5"]
        colorCpu = DataHub.cchart["plot4"]
        colorRam = DataHub.cchart["plot2"]
        ColorAx = DataHub.cchart["texto"]
        ColorAy = DataHub.cchart["texto"]
        ColorTt = DataHub.cchart["titulo"]

        self.fg.clear()
        self.ax = self.fg.add_subplot()
        self.ax.set_facecolor(colorfondo)

        # plot graficos
        (line_cpu,) = self.ax.plot([], [], color=colorCpu)
        (line_mem,) = self.ax.plot([], [], color=colorRam)
        yTicks = [0, 25, 50, 75, 100]

        # legend y label
        p_legend, etiquetas = [], ["Cpu %", "Ram %"]
        p_legend.append(mpatches.Patch(color=colorCpu, label=etiquetas[0]))
        p_legend.append(mpatches.Patch(color=colorRam, label=etiquetas[1]))

        self.ax.set_ylim(0, 100)

        self.ax.set_xlim(0, DataHub.max_points)
        self.ax.set_xlabel("Tiempo (últimos segundos)", fontsize=7, color=ColorAx)
        self.ax.set_ylabel("Uso (%)", fontsize=7, color=ColorAy)
        self.ax.grid(True, color=ColorAy, linewidth=0.1)
        self.ax.spines[["top", "right"]].set_visible(False)

        plt.setp(self.ax.get_xticklabels(), ha="right", fontsize=6, color=ColorAx)
        plt.setp(self.ax.get_yticklabels(), ha="right", fontsize=6, color=ColorAy)
        plt.yticks(yTicks)

        self.fg.legend(loc="upper right", handles=p_legend, fontsize=6)
        self.fg.suptitle("Monitor de CPU y Memoria", fontsize="medium", color=ColorTt)

        # toma series de datos desde DataHub - OPTIMIZADO
        def update(frame):
            try:
                # Verificar que los datos existen y tienen CpuLock
                if not hasattr(DataHub, "CpuLock") or DataHub.CpuLock is None:
                    return line_cpu, line_mem

                # Verificar que hay datos
                if not DataHub.DCpu or not DataHub.DMem:
                    return line_cpu, line_mem

                with DataHub.CpuLock:
                    x = list(range(len(DataHub.DCpu)))
                    line_cpu.set_data(x, DataHub.DCpu)
                    line_mem.set_data(x, DataHub.DMem)

                    # Actualizar límites solo si cambió el tamaño
                    max_x = max(
                        len(x), DataHub.max_points if DataHub.max_points > 0 else 60
                    )
                    self.ax.set_xlim(0, max_x)

                return line_cpu, line_mem

            except Exception as e:
                # Silenciar errores para no interrumpir la animación
                return line_cpu, line_mem

        # OPTIMIZACIÓN: Intervalo más largo para reducir consumo de CPU
        # Cambiado de interval * 3000 (3 segundos) a 10 segundos
        interval_optimizado = 15000  # 10 segundos (antes era ~3 segundos)

        ani = animation.FuncAnimation(
            self.fg,
            update,
            interval=interval_optimizado,  # Actualiza cada 10 segundos
            blit=True,
            cache_frame_data=False,
            save_count=0,  # No guardar frames en caché (ahorro de memoria)
        )

        # Guardar referencia para evitar que se recolecte por garbage collector
        self.monitor_animation = ani

        self.rv.draw()

    def modelo_ia_monitor(self, chatbot=None):
        """
        Monitor del modelo de IA para oportunidades Sell.
        Muestra métricas, distribución de confianza y permite re-entrenar.

        Args:
            chatbot: Instancia de AsistenteChatbot (se pasa desde DashMain.start_chatbot)

        TODO: Agregar soporte para modelo Buy (futuro)
        """
        # Validar que chatbot esté disponible
        if chatbot is None:
            return

        def entrenar_modelo():
            """Inicia el entrenamiento del modelo usando lógica centralizada"""
            try:
                # Instanciar modelo
                modelo = ModeloOportunidadesSell()

                # Obtener datos de entrenamiento usando método centralizado
                # Usa chatbot.obtener_dataframe_entrenamiento_IA()
                df, errores_parseo = chatbot.obtener_dataframe_entrenamiento_IA(
                    tipo="sell",
                    return_stats=True
                )

                if df.empty:
                    msg = MyMessageBox(self.system)
                    msg.showinfo(
                        "Sin datos para entrenar",
                        "No hay datos disponibles para entrenar el modelo Sell.\n\n"
                        "Asegúrate de tener oportunidades Sell registradas con decisiones tomadas (1 o -1)."
                    )
                    return

                # Calcular total de errores
                total_errores = sum(errores_parseo.values())
                registros = df.to_dict('records')

                if len(df) < 10:
                    # Construir mensaje detallado de errores
                    errores_msg = f"Sin decisión tomada: {errores_parseo.get('sin_decision', 0)}\n"
                    errores_msg += f"JSON inválido: {errores_parseo.get('json_invalido', 0)}\n"
                    errores_msg += f"Detalle no es dict: {errores_parseo.get('detalle_no_dict', 0)}\n"
                    errores_msg += f"Indicadores no es dict: {errores_parseo.get('indicadores_no_dict', 0)}\n"
                    errores_msg += f"Otros errores: {errores_parseo.get('otros', 0)}"

                    msg = MyMessageBox(self.system)
                    msg.showinfo(
                        "Datos insuficientes",
                        f"Datos insuficientes para entrenar el modelo.\n\n"
                        f"Registros válidos: {len(df)}\n"
                        f"Mínimo requerido: 10\n"
                        f"Total omitidos: {total_errores}\n\n"
                        f"Desglose de errores:\n{errores_msg}\n\n"
                        f"Genera más oportunidades Sell con decisiones tomadas."
                    )
                    return

                # Entrenar modelo
                modelo.entrenar_modelo(df)
                modelo.save_modelo(modelo.modelo_name)

                # Actualizar métricas
                actualizar_metricas()

                # Construir mensaje detallado de errores para éxito también
                errores_msg = ""
                if total_errores > 0:
                    errores_msg = f"\n\nRegistros omitidos ({total_errores}):\n"
                    if errores_parseo['sin_decision'] > 0:
                        errores_msg += f"• Sin decisión: {errores_parseo['sin_decision']}\n"
                    if errores_parseo['json_invalido'] > 0:
                        errores_msg += f"• JSON inválido: {errores_parseo['json_invalido']}\n"
                    if errores_parseo['detalle_no_dict'] > 0:
                        errores_msg += f"• Detalle no dict: {errores_parseo['detalle_no_dict']}\n"
                    if errores_parseo['indicadores_no_dict'] > 0:
                        errores_msg += f"• Indicadores no dict: {errores_parseo['indicadores_no_dict']}\n"
                    if errores_parseo['otros'] > 0:
                        errores_msg += f"• Otros: {errores_parseo['otros']}"

                msg = MyMessageBox(self.system)
                msg.showinfo(
                    "Entrenamiento exitoso",
                    f"Modelo Sell entrenado exitosamente.\n\n"
                    f"Registros procesados: {len(df)}{errores_msg}\n\n"
                    f"Las métricas se han actualizado."
                )
            except Exception as e:
                error_msg = str(e)
                print(f"entrenar_modelo(): {e}")
                traceback.print_exc()

                msg = MyMessageBox(self.system)
                msg.showinfo(
                    "Error al entrenar",
                    f"Error al entrenar el modelo Sell:\n\n{error_msg}\n\n"
                    f"Revisa la consola para más detalles."
                )

        def actualizar_metricas():
            """Actualiza las métricas del modelo"""
            try:
                # Limpiar tree
                for item in metrics_tree.get_children():
                    metrics_tree.delete(item)

                for item in metrics_tree.get_children():
                    metrics_tree.delete(item)

                # Cargar modelo
                modelo = ModeloOportunidadesSell()
                modelo.load_modelo(modelo.modelo_name)

                # Obtener métricas del modelo
                if hasattr(modelo, 'metrics') and modelo.metrics:
                    metrics_tree.insert("", "end", text="🎯 Métricas de Rendimiento", values=("", "", ""), tags=("header",))

                    precision = modelo.metrics.get("precision", 0)
                    recall = modelo.metrics.get("recall", 0)
                    f1 = modelo.metrics.get("f1_score", 0)
                    accuracy = modelo.metrics.get("accuracy", 0)

                    # Determinar color según valor
                    def get_tag(value):
                        if value >= 0.75: return "good"
                        if value >= 0.60: return "warning"
                        return "bad"

                    metrics_tree.insert("", "end", text="  Precisión", values=(f"{precision:.2%}", "", ""), tags=(get_tag(precision),))
                    metrics_tree.insert("", "end", text="  Recall", values=(f"{recall:.2%}", "", ""), tags=(get_tag(recall),))
                    metrics_tree.insert("", "end", text="  F1-Score", values=(f"{f1:.2%}", "", ""), tags=(get_tag(f1),))
                    metrics_tree.insert("", "end", text="  Accuracy", values=(f"{accuracy:.2%}", "", ""), tags=(get_tag(accuracy),))

                    metrics_tree.insert("", "end", text="", values=("", "", ""))
                else:
                    metrics_tree.insert("", "end", text="🎯 Métricas de Rendimiento", values=("", "", ""), tags=("header",))
                    metrics_tree.insert("", "end", text="  ℹ️ Modelo no entrenado", values=("", "", ""), tags=("warning",))
                    metrics_tree.insert("", "end", text="  Entrena el modelo para ver métricas", values=("", "", ""), tags=("info",))
                    metrics_tree.insert("", "end", text="", values=("", "", ""))

                # Información del dataset usando método centralizado
                df_stats = chatbot.obtener_dataframe_entrenamiento_IA(tipo="sell", return_stats=False)
                total = len(df_stats)
                df_apr = df_stats[df_stats["recomendado"] == 1] if total > 0 else pd.DataFrame()
                df_rec = df_stats[df_stats["recomendado"] == -1] if total > 0 else pd.DataFrame()
                aprobadas = len(df_apr)
                rechazadas = len(df_rec)

                # Calcular promedios ROI y Confianza
                roi_apr, roi_rec, conf_apr, conf_rec = 0, 0, 0, 0
                if total > 0:
                    if "roi" in df_stats.columns:
                        roi_apr = df_apr["roi"].dropna().mean() if len(df_apr) > 0 else 0
                        roi_rec = df_rec["roi"].dropna().mean() if len(df_rec) > 0 else 0
                        roi_apr = roi_apr if pd.notna(roi_apr) else 0
                        roi_rec = roi_rec if pd.notna(roi_rec) else 0
                    # Obtener confianza promedio del json_detalle
                    repo = RepositorioOportunidadesBuySell()
                    todas_ops, ix = repo.obtener_por_tipo(tipo="sell")
                    conf_apr_list, conf_rec_list = [], []
                    for op in todas_ops:
                        try:
                            rec = op[ix.index("recomendado")]
                            json_raw = op[ix.index("json_detalle")]
                            if json_raw and rec in [1, -1]:
                                detalle = json.loads(json_raw) if isinstance(json_raw, str) else json_raw
                                if isinstance(detalle, str):
                                    detalle = json.loads(detalle)
                                if isinstance(detalle, dict) and "confianza" in detalle:
                                    conf = detalle["confianza"]
                                    if isinstance(conf, (int, float)):
                                        if rec == 1:
                                            conf_apr_list.append(conf)
                                        else:
                                            conf_rec_list.append(conf)
                        except Exception:
                            continue
                    conf_apr = sum(conf_apr_list) / len(conf_apr_list) if conf_apr_list else 0
                    conf_rec = sum(conf_rec_list) / len(conf_rec_list) if conf_rec_list else 0

                metrics_tree.insert("", "end", text="📚 Dataset Sell (decisiones)", values=("", "", ""), tags=("header",))
                metrics_tree.insert("", "end", text="  Total con decisión", values=(f"{total}", "", ""), tags=("info",))

                roi_apr_str = f"{roi_apr*100:.1f}%" if roi_apr != 0 else "-"
                conf_apr_str = f"{conf_apr*100:.1f}%" if conf_apr != 0 else "-"
                metrics_tree.insert("", "end", text="  Aprobadas (rec=1)", values=(f"{aprobadas}", roi_apr_str, conf_apr_str), tags=("good",))

                roi_rec_str = f"{roi_rec*100:.1f}%" if roi_rec != 0 else "-"
                conf_rec_str = f"{conf_rec*100:.1f}%" if conf_rec != 0 else "-"
                metrics_tree.insert("", "end", text="  Rechazadas (rec=-1)", values=(f"{rechazadas}", roi_rec_str, conf_rec_str), tags=("bad",))

                entrenables = aprobadas + rechazadas
                tag_entrenables = "good" if entrenables >= 50 else "warning" if entrenables >= 20 else "bad"
                metrics_tree.insert("", "end", text="  Muestras para entrenar", values=(f"{entrenables}", "", ""), tags=(tag_entrenables,))

                # Distribución de confianza en predicciones recientes
                # Usar DataFrame ya obtenido - últimas 100 filas
                if total > 0:
                    # Obtener datos con stats para acceder a json_detalle completo
                    repo = RepositorioOportunidadesBuySell()
                    todas_oportunidades, ix = repo.obtener_por_tipo(tipo="sell")

                    # Filtrar solo con decisión y con json_detalle
                    oportunidades_recientes = [
                        op for op in todas_oportunidades
                        if op[ix.index("recomendado")] in [1, -1] and op[ix.index("json_detalle")]
                    ][-100:]

                    confianzas = []
                    for op in oportunidades_recientes:
                        try:
                            json_detalle_raw = op[ix.index("json_detalle")]

                            # Manejar doble codificación si es necesario
                            if isinstance(json_detalle_raw, str):
                                detalle = json.loads(json_detalle_raw)
                                # Si aún es string, intentar parsear de nuevo
                                if isinstance(detalle, str):
                                    detalle = json.loads(detalle)
                            else:
                                detalle = json_detalle_raw

                            # Validar que sea dict y tenga confianza
                            if isinstance(detalle, dict) and "confianza" in detalle:
                                conf_value = detalle["confianza"]
                                # Validar que sea numérico
                                if isinstance(conf_value, (int, float)):
                                    confianzas.append(conf_value)
                        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                            continue

                    if confianzas:
                        # Calcular distribución por rangos
                        rangos = [
                            ("90-100%", 0.90, 1.01, "high"),
                            ("75-90%", 0.75, 0.90, "high"),
                            ("65-75%", 0.65, 0.75, "medium"),
                            ("50-65%", 0.50, 0.65, "low"),
                            ("< 50%", 0.0, 0.50, "verylow"),
                        ]

                        total_conf = len(confianzas)
                        metrics_tree.insert("", "end", text=f"Total predicciones: {total_conf}", values=("", ""), tags=("header",))
                        metrics_tree.insert("", "end", text="", values=("", ""))

                        for rango_nombre, min_val, max_val, tag in rangos:
                            count = sum(1 for c in confianzas if min_val <= c < max_val)
                            pct = (count / total_conf * 100) if total_conf > 0 else 0
                            metrics_tree.insert("", "end", text=f"  {rango_nombre}", values=(count, f"{pct:.1f}%"), tags=(tag,))

                        # Estadísticas adicionales
                        metrics_tree.insert("", "end", text="", values=("", ""))
                        metrics_tree.insert("", "end", text="📊 Estadísticas", values=("", ""), tags=("header",))

                        media = sum(confianzas) / len(confianzas)
                        tag_media = "good" if media >= 0.70 else "warning" if media >= 0.60 else "bad"
                        metrics_tree.insert("", "end", text="  Confianza media", values=(f"{media:.2%}", ""), tags=(tag_media,))

                        maxima = max(confianzas)
                        minima = min(confianzas)
                        metrics_tree.insert("", "end", text="  Confianza máxima", values=(f"{maxima:.2%}", ""), tags=("info",))
                        metrics_tree.insert("", "end", text="  Confianza mínima", values=(f"{minima:.2%}", ""), tags=("info",))

                        # Alertas
                        metrics_tree.insert("", "end", text="", values=("", ""))
                        bajo_umbral = sum(1 for c in confianzas if c < 0.65)
                        pct_bajo = (bajo_umbral / total_conf * 100) if total_conf > 0 else 0

                        if pct_bajo > 50:
                            metrics_tree.insert("", "end", text="⚠️ ALERTA", values=("", ""), tags=("bad",))
                            metrics_tree.insert("", "end", text=f"  {pct_bajo:.1f}% bajo umbral 65%", values=("", ""), tags=("bad",))
                            metrics_tree.insert("", "end", text="  Considera re-entrenar", values=("", ""), tags=("warning",))
                    else:
                        metrics_tree.insert("", "end", text="ℹ️ No hay datos de confianza", values=("", ""), tags=("info",))
                else:
                    metrics_tree.insert("", "end", text="ℹ️ No hay predicciones recientes", values=("", ""), tags=("info",))
            except Exception as e:
                metrics_tree.insert("", "end", text=f"❌ Error: {str(e)[:50]}", values=("", "", ""), tags=("bad",))
                print(f"actualizar_metricas(): {e}")
                traceback.print_exc()

        # Programar actualización automática cada 30 segundos
        def auto_actualizar():
            if self.is_running:
                actualizar_metricas()
                after_id = self.system.after(30000, auto_actualizar)
                self.after_ids.append(after_id)


        try:
            # Frame principal dividido en dos secciones
            left_frame = ttk.Frame(self.modeloia, padding=(5, 5), style="C.TFrame")
            right_frame = ttk.Frame(self.modeloia, padding=(5, 5), style="C.TFrame")

            left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

            # === SECCIÓN IZQUIERDA: Métricas y Estadísticas ===
            metrics_label = ttk.Label(
                left_frame,
                text="📊 Métricas del Modelo Sell",
                font=("TkDefaultFont", 10, "bold"),
                foreground="cyan",
                background=self.colors.get("background")
            )
            metrics_label.pack(anchor=tk.W, pady=(0, 5))

            # TreeView para mostrar métricas (3 columnas: Valor, ROI Prom, Profit Prom)
            metrics_tree = ttk.Treeview(
                left_frame,
                columns=("value", "roi_prom", "profit_prom"),
                height=12,
                show="tree headings",
                style="TFrame"
            )
            metrics_tree.heading("#0", text="Métrica")
            metrics_tree.heading("value", text="Valor")
            metrics_tree.heading("roi_prom", text="ROI Prom")
            metrics_tree.heading("profit_prom", text="Profit Prom")
            metrics_tree.column("#0", width=180)
            metrics_tree.column("value", width=70, anchor=tk.E)
            metrics_tree.column("roi_prom", width=70, anchor=tk.E)
            metrics_tree.column("profit_prom", width=70, anchor=tk.E)

            metrics_tree.tag_configure("header", foreground="yellow", font=("TkDefaultFont", 9, "bold"))
            metrics_tree.tag_configure("good", foreground="lightgreen")
            metrics_tree.tag_configure("warning", foreground="orange")
            metrics_tree.tag_configure("bad", foreground="red")
            metrics_tree.tag_configure("info", foreground="lightblue")

            metrics_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

            # Botones para modelo
            btn_frame = ttk.Frame(left_frame, style="C.TFrame")
            btn_frame.pack(fill=tk.X, pady=(5, 0))

            train_btn = ttk.Button(
                btn_frame,
                text="Re-entrenar",
                command=entrenar_modelo,
                style="TButton"
            )
            train_btn.pack(side=tk.LEFT, padx=(0, 5))

            # TODO: Implementar ventana de configuración de parámetros
            def modificar_parametros():
                pass  # Pendiente: abrir ventana para ajustar umbrales, features, etc.

            config_btn = ttk.Button(
                btn_frame,
                text="Modificar",
                command=modificar_parametros,
                style="TButton"
            )
            config_btn.pack(side=tk.LEFT)

            # === SECCIÓN DERECHA: Oportunidades Actuales ===
            opp_label = ttk.Label(
                right_frame,
                text="🎯 Oportunidades Actuales (tiempo real)",
                font=("TkDefaultFont", 10, "bold"),
                foreground="cyan",
                background=self.colors.get("background")
            )
            opp_label.pack(anchor=tk.W, pady=(5, 5))

            # TreeView para oportunidades actuales
            opp_tree = ttk.Treeview(
                right_frame,
                columns=("opcion", "rsi", "roi", "conf", "estado"),
                height=8,
                show="tree headings",
                style="TFrame"
            )
            opp_tree.heading("#0", text="Symbol")
            opp_tree.heading("opcion", text="Opción")
            opp_tree.heading("rsi", text="RSI")
            opp_tree.heading("roi", text="ROI%")
            opp_tree.heading("conf", text="Conf")
            opp_tree.heading("estado", text="Estado")
            opp_tree.column("#0", width=60)
            opp_tree.column("opcion", width=50, anchor=tk.CENTER)
            opp_tree.column("rsi", width=45, anchor=tk.E)
            opp_tree.column("roi", width=50, anchor=tk.E)
            opp_tree.column("conf", width=45, anchor=tk.E)
            opp_tree.column("estado", width=70, anchor=tk.CENTER)

            opp_tree.tag_configure("vender", foreground="lightgreen", font=("TkDefaultFont", 9, "bold"))
            opp_tree.tag_configure("observar", foreground="yellow")
            opp_tree.tag_configure("ignorar", foreground="gray")
            opp_tree.tag_configure("header", foreground="cyan", font=("TkDefaultFont", 9, "bold"))

            opp_tree.pack(fill=tk.BOTH, expand=True)

            # Función para ordenar TreeView por columna
            def treeview_sort_column(tree, col, reverse):
                """Ordena el TreeView por columna al hacer clic en el header"""
                try:
                    # Obtener todos los items excepto headers/resumen
                    items = [(tree.set(k, col), k) for k in tree.get_children("")]
                    # Filtrar items vacíos (headers/resumen)
                    items = [(val, k) for val, k in items if val and not val.startswith("V:") and not val.startswith("O:") and not val.startswith("I:") and val != "Total:"]

                    # Convertir a número si es posible
                    try:
                        items.sort(key=lambda t: float(t[0].replace("%", "")), reverse=reverse)
                    except ValueError:
                        items.sort(key=lambda t: t[0], reverse=reverse)

                    # Reorganizar items
                    for index, (val, k) in enumerate(items):
                        tree.move(k, "", index)

                    # Cambiar dirección para próximo clic
                    tree.heading(col, command=lambda: treeview_sort_column(tree, col, not reverse))
                except Exception:
                    pass

            # Configurar headers para ordenamiento
            opp_tree.heading("#0", text="Symbol", command=lambda: treeview_sort_column(opp_tree, "#0", False))
            opp_tree.heading("opcion", text="Opción", command=lambda: treeview_sort_column(opp_tree, "opcion", False))
            opp_tree.heading("rsi", text="RSI", command=lambda: treeview_sort_column(opp_tree, "rsi", True))
            opp_tree.heading("roi", text="ROI%", command=lambda: treeview_sort_column(opp_tree, "roi", True))
            opp_tree.heading("conf", text="Conf", command=lambda: treeview_sort_column(opp_tree, "conf", True))
            opp_tree.heading("estado", text="Estado", command=lambda: treeview_sort_column(opp_tree, "estado", False))

            def actualizar_metricas():
                """Actualiza las métricas del modelo y oportunidades actuales"""
                try:
                    # Limpiar trees
                    for item in metrics_tree.get_children():
                        metrics_tree.delete(item)

                    for item in opp_tree.get_children():
                        opp_tree.delete(item)

                    # Cargar modelo
                    modelo = ModeloOportunidadesSell()
                    modelo.load_modelo(modelo.modelo_name)

                    # === 1. DATASET SELL (primero) ===
                    # Calcular promedios ROI y Profit por decisión
                    roi_apr, roi_rec, profit_apr, profit_rec = 0, 0, 0, 0
                    if chatbot is not None:
                        df_stats = chatbot.obtener_dataframe_entrenamiento_IA(tipo="sell", return_stats=False)
                        total = len(df_stats)
                        df_apr = df_stats[df_stats["recomendado"] == 1] if total > 0 else pd.DataFrame()
                        df_rec = df_stats[df_stats["recomendado"] == -1] if total > 0 else pd.DataFrame()
                        aprobadas = len(df_apr)
                        rechazadas = len(df_rec)

                        # Calcular promedios ROI
                        if "roi" in df_stats.columns:
                            roi_apr = df_apr["roi"].dropna().mean() if len(df_apr) > 0 else 0
                            roi_rec = df_rec["roi"].dropna().mean() if len(df_rec) > 0 else 0
                            roi_apr = roi_apr if pd.notna(roi_apr) else 0
                            roi_rec = roi_rec if pd.notna(roi_rec) else 0

                        # Calcular promedios Profit
                        if "profit" in df_stats.columns:
                            profit_apr = df_apr["profit"].dropna().mean() if len(df_apr) > 0 else 0
                            profit_rec = df_rec["profit"].dropna().mean() if len(df_rec) > 0 else 0
                            profit_apr = profit_apr if pd.notna(profit_apr) else 0
                            profit_rec = profit_rec if pd.notna(profit_rec) else 0
                    else:
                        total, aprobadas, rechazadas = 0, 0, 0

                    metrics_tree.insert("", "end", text="📚 Dataset Sell (decisiones)", values=("", "", ""), tags=("header",))
                    metrics_tree.insert("", "end", text="  Total con decisión", values=(f"{total}", "", ""), tags=("info",))

                    roi_apr_str = f"{roi_apr*100:.1f}%" if roi_apr != 0 else "-"
                    profit_apr_str = f"${profit_apr:,.0f}" if profit_apr != 0 else "-"
                    metrics_tree.insert("", "end", text="  Aprobadas (rec=1)", values=(f"{aprobadas}", roi_apr_str, profit_apr_str), tags=("good",))

                    roi_rec_str = f"{roi_rec*100:.1f}%" if roi_rec != 0 else "-"
                    profit_rec_str = f"${profit_rec:,.0f}" if profit_rec != 0 else "-"
                    metrics_tree.insert("", "end", text="  Rechazadas (rec=-1)", values=(f"{rechazadas}", roi_rec_str, profit_rec_str), tags=("bad",))

                    entrenables = aprobadas + rechazadas
                    tag_entrenables = "good" if entrenables >= 50 else "warning" if entrenables >= 20 else "bad"
                    metrics_tree.insert("", "end", text="  Muestras para entrenar", values=(f"{entrenables}", "", ""), tags=(tag_entrenables,))

                    # === 2. MÉTRICAS CV ===
                    if hasattr(modelo, 'metrics') and modelo.metrics:
                        metrics_tree.insert("", "end", text="", values=("", "", ""))
                        metrics_tree.insert("", "end", text="🎯 Métricas CV (5-fold)", values=("", "", ""), tags=("header",))

                        precision = modelo.metrics.get("precision", 0)
                        precision_std = modelo.metrics.get("precision_std", 0)
                        recall = modelo.metrics.get("recall", 0)
                        recall_std = modelo.metrics.get("recall_std", 0)
                        f1 = modelo.metrics.get("f1_score", 0)
                        f1_std = modelo.metrics.get("f1_std", 0)
                        accuracy = modelo.metrics.get("accuracy", 0)
                        accuracy_std = modelo.metrics.get("accuracy_std", 0)

                        def get_tag(value):
                            if value >= 0.75: return "good"
                            if value >= 0.60: return "warning"
                            return "bad"

                        metrics_tree.insert("", "end", text="  Precisión", values=(f"{precision:.0%}±{precision_std*100:.0f}", "", ""), tags=(get_tag(precision),))
                        metrics_tree.insert("", "end", text="  Recall", values=(f"{recall:.0%}±{recall_std*100:.0f}", "", ""), tags=(get_tag(recall),))
                        metrics_tree.insert("", "end", text="  F1-Score", values=(f"{f1:.0%}±{f1_std*100:.0f}", "", ""), tags=(get_tag(f1),))
                        metrics_tree.insert("", "end", text="  Accuracy", values=(f"{accuracy:.0%}±{accuracy_std*100:.0f}", "", ""), tags=(get_tag(accuracy),))

                        # === 3. TOP 10 FEATURES ===
                        feature_imp = modelo.metrics.get("feature_importance", [])
                        if feature_imp:
                            metrics_tree.insert("", "end", text="", values=("", "", ""))
                            metrics_tree.insert("", "end", text="🔍 Top 10 Features", values=("", "", ""), tags=("header",))
                            for i, feat in enumerate(feature_imp[:10]):
                                name = feat["feature"].replace("_d", "").replace("_", " ")
                                imp = feat["importance"]
                                metrics_tree.insert("", "end", text=f"  {i+1}. {name}", values=(f"{imp:.1%}", "", ""), tags=("info",))
                    else:
                        metrics_tree.insert("", "end", text="", values=("", "", ""))
                        metrics_tree.insert("", "end", text="🎯 Métricas CV", values=("", "", ""), tags=("header",))
                        metrics_tree.insert("", "end", text="  ℹ️ Modelo no entrenado", values=("", "", ""), tags=("warning",))

                    # === Oportunidades Actuales (desde CSV en tiempo real) ===
                    try:
                        from Class_DashBot import Chatbot
                        df_sell = Chatbot.readCSV(file="csv_datosIA_sell")

                        if df_sell is not None and not df_sell.empty:
                            # Cargar modelo para predecir
                            modelo_pred = ModeloOportunidadesSell()
                            modelo_pred.load_modelo(modelo_pred.modelo_name)

                            if modelo_pred.modelo is not None:
                                # Preparar datos para predicción
                                df_pred = df_sell.copy()
                                df_pred = df_pred.rename(columns=DataHub.SellCsvJsonDcolumnas)
                                df_aplanado = modelo_pred.aplanar_datos_tecnicos(df_pred)

                                if df_aplanado is not None and not df_aplanado.empty:
                                    resultado = modelo_pred.predecir_modelo(df_aplanado)

                                    if resultado is not None and not resultado.empty:
                                        # Contadores
                                        n_vender = 0
                                        n_observar = 0
                                        n_ignorar = 0

                                        # Recolectar datos para ordenar por ROI
                                        oportunidades = []
                                        for i, (_, row_pred) in enumerate(resultado.iterrows()):
                                            if i >= len(df_sell):
                                                break
                                            row_orig = df_sell.iloc[i]

                                            symbol = row_orig.get("Symbol", "???")
                                            roi = row_orig.get("%Roi", 0) * 100
                                            conf = row_pred.get("confianza", 0)
                                            opcion = row_orig.get("Opcion", "")

                                            # Extraer RSI del JSON si existe
                                            rsi = 0
                                            try:
                                                datos_tec = row_orig.get("Datostecnicos", "{}")
                                                if isinstance(datos_tec, str):
                                                    datos_tec = json.loads(datos_tec)
                                                rsi = datos_tec.get("diaria", {}).get("rsi", 0)
                                            except:
                                                pass

                                            # Determinar estado según umbrales
                                            if conf >= 0.65:
                                                estado = "VENDER"
                                                tag = "vender"
                                                n_vender += 1
                                            elif conf >= 0.35:
                                                estado = "Observar"
                                                tag = "observar"
                                                n_observar += 1
                                            else:
                                                estado = "Ignorar"
                                                tag = "ignorar"
                                                n_ignorar += 1

                                            oportunidades.append({
                                                "symbol": symbol,
                                                "opcion": opcion,
                                                "rsi": rsi,
                                                "roi": roi,
                                                "conf": conf,
                                                "estado": estado,
                                                "tag": tag
                                            })

                                        # Ordenar por ROI decreciente
                                        oportunidades.sort(key=lambda x: x["roi"], reverse=True)

                                        # Insertar ordenados
                                        for opp in oportunidades:
                                            opp_tree.insert("", "end",
                                                text=opp["symbol"],
                                                values=(opp["opcion"], f"{opp['rsi']:.1f}", f"{opp['roi']:.1f}", f"{opp['conf']:.2f}", opp["estado"]),
                                                tags=(opp["tag"],)
                                            )

                                        # Resumen en una línea simple
                                        opp_tree.insert("", "end",
                                            text=f"Total: {len(resultado)}",
                                            values=("", f"V:{n_vender}", f"O:{n_observar}", f"I:{n_ignorar}", ""),
                                            tags=("header",)
                                        )
                                    else:
                                        opp_tree.insert("", "end", text="Sin predicciones", values=("", "", "", "", ""), tags=("ignorar",))
                                else:
                                    opp_tree.insert("", "end", text="Error aplanando", values=("", "", "", "", ""), tags=("ignorar",))
                            else:
                                opp_tree.insert("", "end", text="Modelo no cargado", values=("", "", "", "", ""), tags=("ignorar",))
                        else:
                            opp_tree.insert("", "end", text="Sin oportunidades", values=("", "", "", "", ""), tags=("ignorar",))
                    except Exception as e_opp:
                        opp_tree.insert("", "end", text=f"Error: {str(e_opp)[:30]}", values=("", "", "", "", ""), tags=("ignorar",))

                except Exception as e:
                    metrics_tree.insert("", "end", text=f"❌ Error: {str(e)[:50]}", values=("", "", ""), tags=("bad",))
                    print(f"actualizar_metricas(): {e}")
                    traceback.print_exc()

            # Actualizar métricas al inicio
            actualizar_metricas()
    
            auto_actualizar()
        except Exception as e:
            print(f"modelo_ia_monitor(): {e}")
            traceback.print_exc()

