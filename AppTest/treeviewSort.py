import tkinter as tk
from tkinter import ttk

# Función para ordenar las tres columnas sincronizadamente
def ordenar_columnas(col_tree, col, reverse):
    # Obtener valores de la columna que va a ser ordenada
    data = [(col_tree.set(k, col), k) for k in col_tree.get_children('')]

    # Ordenar los valores
    data.sort(reverse=reverse)

    # Reorganizar los valores de cada Treeview sincronizadamente
    for index, (val, k) in enumerate(data):
        col_tree.move(k, '', index)

        # Mover el mismo índice en las otras columnas
        for tree in trees:
            if tree != col_tree:
                tree.move(k, '', index)

    # Alternar entre ascendente y descendente
    col_tree.heading(col, command=lambda: ordenar_columnas(col_tree, col, not reverse))

# Crear ventana principal
root = tk.Tk()
root.title("Ordenar Treeviews sincronizados")

# Definir las tres columnas (tres Treeviews)
columns = ['Nombre', 'Edad', 'País']

# Crear una lista para contener los tres Treeview
trees = []

# Crear Treeview para cada columna
for i, col in enumerate(columns):
    tree = ttk.Treeview(root, columns=[col], show='headings')
    tree.heading(col, text=col, command=lambda _col=col, _tree=tree: ordenar_columnas(_tree, _col, False))
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    trees.append(tree)

# Datos a insertar (una fila por Treeview)
data = [
    ('Juan', 25, 'España'),
    ('Ana', 30, 'México'),
    ('Pedro', 22, 'Argentina'),
    ('Lucía', 29, 'Chile'),
    ('Camila', 28, 'Perú'),
]

# Insertar los datos en los tres Treeviews
for row in data:
    for i, tree in enumerate(trees):
        tree.insert('', tk.END, values=[row[i]])

root.mainloop()
