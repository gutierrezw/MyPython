import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from Modulos_python import *


def on_button_click():
    selected_item = tree.selection()
    if selected_item:
        values = tree.item(selected_item)["values"]
        print(f"Botón en la fila seleccionada: {values}")

# Configuración de la ventana
root = tk.Tk()
root.title("Treeview con Botón Simulado")
root.geometry("400x300")

# Configuración del Treeview
tree = ttk.Treeview(root, columns=("Columna1", "Columna2"), show="headings")
tree.heading("Columna1", text="Columna 1")
tree.heading("Columna2", text="Columna 2")
tree.column("Columna1", width=60)
tree.column("Columna2", width=60)

# Insertar algunas filas de ejemplo
for i in range(5):
    tree.insert("", "end", values=(f"Valor {i+1}", i * 10))

tree.pack(side="right", fill="both", expand=True)

# Crear un botón que actúa como "botón de celda"
modifica = ttk.Button(root, text="Inactiva", command=on_button_click)
cancela = ttk.Button(root, text="Modifica", command=on_button_click)
inactiva = ttk.Button(root, text="Cancela", command=on_button_click)

modifica.pack(side="left",   expand=True)
cancela.pack(side="left",   expand=True)
inactiva.pack(side="left",   expand=True)

root.mainloop()
