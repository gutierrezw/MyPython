import tkinter as tk
from tkinter import ttk

# Configuración de la ventana principal
root = tk.Tk()
root.title("Recorrer Treeview")

# Creación del Treeview
tree = ttk.Treeview(root, columns=("A", "B"), show="headings")
tree.pack(padx=10, pady=10)

# Configuración de las columnas
tree.heading("A", text="Columna A")
tree.heading("B", text="Columna B")

# Insertar padres
P1 = tree.insert("", "end", text="P1", values=("Padre 1A", "Padre 1B"))
P2 = tree.insert("", "end", text="P2", values=("Padre 2A", "Padre 2B"))

# Insertar hijos
tree.insert(P2, "end", iid="C1", values=("Hijo 1A", "Hijo 1B"))
tree.insert(P2, "end", iid="C2", values=("Hijo 2A", "Hijo 2B"))
tree.insert(P2, "end", iid="C3", values=("Hijo 3A", "Hijo 3B"))

# Función para recorrer los elementos
def recorrer_treeview():
    # Obtener todos los elementos padre
    padres = tree.get_children()
    for padre in padres:
        print(f"Padre: {padre}, Valores: {tree.item(padre)['values']}")
        # Obtener los hijos del padre
        hijos = tree.get_children(padre)
        for hijo in hijos:
            print(f"  Hijo: {hijo}, Valores: {tree.item(hijo)['values']}")

# Botón para recorrer y mostrar el contenido
btn_recorrer = tk.Button(root, text="Recorrer Treeview", command=recorrer_treeview)
btn_recorrer.pack(pady=10)

root.mainloop()
