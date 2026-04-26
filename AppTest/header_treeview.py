import tkinter as tk
from tkinter import ttk

# Crear ventana principal
root = tk.Tk()

# Crear estilo
style = ttk.Style()
style.theme_use("default")

# Crear dos estilos diferentes para los encabezados de columnas
style.configure("Treeview.Heading", font=('Arial', 10, 'bold'), background="lightgray", foreground="black")
style.configure("Red.Heading", font=('Arial', 10, 'bold'), background="red", foreground="white")
style.configure("Blue.Heading", font=('Arial', 10, 'bold'), background="blue", foreground="white")

# Crear Treeview
tree = ttk.Treeview(root, columns=("A", "B", "C"), show="headings")

# Definir encabezados de las columnas y aplicar estilos
tree.heading("A", text="Columna A", command=lambda: print("Header A"))
tree.heading("B", text="Columna B", command=lambda: print("Header B"))
tree.heading("C", text="Columna C", command=lambda: print("Header C"))

# Aplicar estilos personalizados a los encabezados
tree.tag_configure('headerA', background="lightgray")
tree.tag_configure('headerB', background="red")
tree.tag_configure('headerC', background="blue")

# Colocar las columnas en el Treeview
tree.pack(fill=tk.BOTH, expand=True)

# Insertar algunos datos de prueba
tree.insert('', tk.END, values=("1", "2", "3"))

root.mainloop()
