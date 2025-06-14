from Modulos_python  import *


class CustomTreeview:
    def __init__(self, master, columns, fixed_columns=None, fixed_row=False,
                 show_vscroll=True, show_hscroll=True, height=10, column_alignments=None, style=None):
        """
        Constructor para crear un Treeview personalizado.

        Args:
            parent: El widget padre (como un Frame o la ventana principal).
            columns: Lista de nombres de columnas.
            fixed_columns: Lista de columnas que serán fijas (opcional).
            fixed_row: Índice de la fila que será fija (opcional).
            show_vscroll: Booleano, muestra o no la barra de scroll vertical.
            show_hscroll: Booleano, muestra o no la barra de scroll horizontal.
            height: Altura del Treeview (número de filas visibles).
            column_alignments: Diccionario para alinear columnas, ej: {'Nombre': 'center', 'Edad': 'right'}
        """
        self.parent = master
        self.columns = columns
        self.fixed_columns = fixed_columns or []
        self.fixed_row = fixed_row
        self.show_vscroll = show_vscroll
        self.show_hscroll = show_hscroll
        self.height = height
        self.column_alignments = column_alignments or {}
        self.style = style or ttk.Style()
        show_fixed_row = 'headings' if not self.fixed_row else 'tree'

        # Crear los frames
        self.master = tk.Frame(self.parent)
        self.heard = tk.Frame(self.parent)
        self.right = tk.Frame(self.parent)
        self.right.pack(side=tk.RIGHT, fill=tk.Y, expand=True)
        self.heard.pack(side=tk.TOP, fill=tk.X)
        self.master.pack(side=tk.BOTTOM, fill=tk.X)
        self.heard_fixed, self.heard_scroll = self.create_treeview(master=self.heard,
                                                                   show='headings',
                                                                   height=1,
                                                                   style=self.style)

        self.tree_fixed, self.tree_scroll = self.create_treeview(master=self.master,
                                                                 show='headings',
                                                                 height=self.height,
                                                                 style=self.style)

        # set movimientos del mouse.
        self.heard_fixed.bind("<MouseWheel>", self.on_mouse_wheel)
        self.heard_scroll.bind("<MouseWheel>", self.on_mouse_wheel)
        self.tree_fixed.bind("<MouseWheel>", self.on_mouse_wheel)
        self.tree_scroll.bind("<MouseWheel>", self.on_mouse_wheel)

        # set selección de items
        self.tree_fixed.bind("<<TreeviewSelect>>", self.sync_fixed_selection)
        self.tree_scroll.bind("<<TreeviewSelect>>", self.disable_selection)

        # Sincronizar el scroll vertical si se habilita
        if self.show_vscroll:
            self.vscroll = ttk.Scrollbar(self.right, orient="vertical", command=self.sync_vertical_scroll)
            self.vscroll.pack(side=tk.RIGHT, fill=tk.Y)
            self.tree_fixed.config(yscrollcommand=self.vscroll.set)
            self.tree_scroll.config(yscrollcommand=self.vscroll.set)


        # Sincronizar el scroll horizontal si se habilita
        if self.show_hscroll:
            if not self.fixed_row:
                self.hscroll = ttk.Scrollbar(self.master, orient="horizontal", command=self.tree_scroll.xview)
                self.hscroll.pack(side=tk.BOTTOM, fill=tk.X)
                self.tree_scroll.config(xscrollcommand=self.hscroll.set)

            if self.fixed_row:
                self.hscroll = ttk.Scrollbar(self.master, orient="horizontal", command=self.sync_horizontal_scroll)
                self.hscroll.pack(side=tk.BOTTOM, fill=tk.X)
                self.tree_scroll.config(xscrollcommand=self.hscroll.set)
                self.heard_scroll.config(xscrollcommand=self.hscroll.set)

        # Configurar los treeviews header
        if self.fixed_row:
            self.heard_fixed.pack(side=tk.LEFT)
            self.heard_scroll.pack(side=tk.RIGHT, expand=True)
            self.tree_fixed.pack(side=tk.LEFT)
            self.tree_scroll.pack(side=tk.RIGHT, expand=True)

        # Configurar los treeviews clasico
        if not self.fixed_row:
            self.tree_fixed.pack(side=tk.LEFT)
            self.tree_scroll.pack(side=tk.RIGHT, fill=tk.X)

        # Configurar los heading treeviews para el detalle
        if show_fixed_row == 'tree':
            self.tree_fixed.configure(show="tree")
            self.tree_scroll.configure(show="tree")

    # creación de treeview, con o sin fixed row
    def create_treeview(self, master=None, show=None, height=None, style=None):
        if not self.fixed_columns:
            return

        # construye parte fixed
        tree_fixed = ttk.Treeview(master, columns=self.fixed_columns, show=show, height=height, style=style)
        tree_fixed.heading('#0')
        tree_fixed.column('#0', width=0, minwidth=1)

        for col in self.fixed_columns:
            tree_fixed.heading(col, text=col)
            anchor = self.column_alignments[col]['anchor'] if col in self.column_alignments.keys() else 'center'
            width = self.column_alignments[col]['width'] if col in self.column_alignments.keys() else '100'

            tree_fixed.column(col, width=width, anchor=anchor)

        # construye parte scrollable
        scrollable_columns = [col for col in self.columns if col not in self.fixed_columns]
        tree_scroll = ttk.Treeview(master, columns=scrollable_columns, show=show, height=height, style=style)
        tree_scroll.heading('#0')
        tree_scroll.column('#0', width=0, minwidth=1)

        for col in scrollable_columns:
            tree_scroll.heading(col, text=col)
            anchor = self.column_alignments[col]['anchor'] if col in self.column_alignments.keys() else 'center'
            width = self.column_alignments[col]['width'] if col in self.column_alignments.keys() else '100'
            tree_scroll.column(col, width=width, anchor=anchor)

        return tree_fixed, tree_scroll

    # Desplazar el Treeview cuando se arrastra el mouse
    def on_mouse_drag(self, event):
        self.heard_fixed.yview_scroll(-1 * int(event.delta / 120), "units")
        self.tree_fixed.yview_scroll(-1 * int(event.delta / 120), "units")
        self.tree_scroll.yview_scroll(-1 * int(event.delta / 120), "units")

    # Scroll cuando se usa la rueda del ratón
    def on_mouse_wheel(self, event):
        self.heard_fixed.yview_scroll(-1 * int(event.delta / 120), "units")
        self.tree_fixed.yview_scroll(-1 * int(event.delta / 120), "units")
        self.tree_scroll.yview_scroll(-1 * int(event.delta / 120), "units")

    # Sincronizar el scroll vertical entre los dos Treeviews.
    def sync_vertical_scroll(self, *args):
        self.heard_fixed.yview(*args)
        self.tree_fixed.yview(*args)
        self.tree_scroll.yview(*args)

    # Función para sincronizar el desplazamiento horizontal de ambos Treeview
    def sync_horizontal_scroll(self, *args):
        self.heard_scroll.xview(*args)
        self.tree_scroll.xview(*args)

    # Función para sincronizar la selección
    def sync_fixed_selection(self, event):
        selected_item = self.tree_fixed.selection()
        self.tree_scroll.selection_set(selected_item)

    # Deshabilitar selección en tree2 interceptando el evento
    @staticmethod
    def disable_selection(event):
        return "break"  # Evitar que el evento de selección en tree2 se ejecute

    def insert_row(self, values=None, summary=None):
        """Método para insertar una fila en los Treeviews.
           Values: para detalle y
           summary: para línea de totales"""
        if self.fixed_columns:
            fixed_values = values[:len(self.fixed_columns)]
            self.tree_fixed.insert("", "end", values=fixed_values)

        scrollable_values = values[len(self.fixed_columns):]
        self.tree_scroll.insert("", "end", values=scrollable_values)
        print(fixed_values, '>>', scrollable_values)

        if self.fixed_row:
            left_values = summary[:len(self.fixed_columns)]
            self.heard_fixed.insert("", "end", values=left_values)

            right_values = summary[len(self.fixed_columns):]
            self.heard_scroll.insert("", "end", values=right_values)


# Ejemplo de uso
root = tk.Tk()
max_dw = root.winfo_screenwidth()
max_dh = root.winfo_screenheight()
dimension = "%dx%d+%d+%d" % (max_dw, max_dh, 0, 0)
root.geometry(dimension)
win1 = tk.Frame(root, width=600, height=165, bg='Black')
win2 = tk.Frame(root, width=200, height=200, bg='blue')
win1.pack(side=tk.TOP)
win2.pack(side=tk.TOP)
win1.pack_propagate(False)

style = ttk.Style()
style.configure('Treeview',  background='black', foreground='white')
style.map('Treeview', background=[('selected', 'lightblue')], foreground=[('selected', 'gray')])

# área y figura de graficos
rg = Figure(figsize=(5.55, 4.00), dpi=110, layout="tight")
rv = FigureCanvasTkAgg(rg, master=win2)
rv.draw()
rv.get_tk_widget().grid()


# Definir las columnas, columnas fijas y alineaciones
columns = ["Nombre", "Edad", "País", "Profesión", "Salario", "beca", "pension"]
fixed_columns = ["Nombre", "Edad"]

alignments = {
    "Nombre": {'width': 100, 'anchor': "w"},
    "Edad": {'width': 100, 'anchor': "center"},
    "País": {'width': 100, 'anchor': "e"},
    "Profesión": {'width': 70, 'anchor': "w"},
    "Salario": {'width': 70, 'anchor': "e"}
}

# Crear instancia de la clase con columnas fijas, scroll y alineación
custom_tree = CustomTreeview(master=win1,
                             columns=columns,
                             fixed_columns=fixed_columns,
                             fixed_row=False,
                             show_vscroll=True,
                             show_hscroll=True,
                             height=6,
                             column_alignments=alignments,
                             style='Treeview')

# Insertar filas de ejemplos
rows = [
    ["Juan", 25, "España", "Ingeniero", 3000, 1000, 300],
    ["Ana", 30, "México", "Doctora", 3500, 100, 200],
    ["Pedro", 28, "Argentina", "Programador", 3200, 200, 100],
    ["Maria", 35, "Chile", "Abogada", 4000, 500, 400],
    ["wilmer", 30, "México", "Doctora", 1500, 300, 300],
    ["israel", 30, "México", "Doctora", 1500, 300, 300],
    ["daiana", 28, "Argentina", "Programador", 6200, 700, 1000],
    ["camila", 28, "Argentina", "Programador", 6200, 700, 1000]
]
total = ["-----", "", "", "", 16200, 1700, 21000]
for row in rows:
    custom_tree.insert_row(summary=total, values=row)

root.mainloop()
