import tkinter as tk

def on_listbox_select(event):
    """Cierra la entrada de texto y asigna el valor seleccionado."""
    selected_item = listbox.get(listbox.curselection())
    entry_var.set(selected_item)
    listbox.pack_forget()  # Ocultar Listbox

def on_entry_click(event):
    """Muestra el Listbox cuando se hace clic en el Entry."""
    listbox.pack()  # Mostrar Listbox

# Ventana principal
root = tk.Tk()
root.geometry("300x200")

# Lista de opciones
items = ["Apple", "Banana", "Cherry", "Date", "Grape", "Kiwi", "Lemon", "Mango", "Orange", "Peach"]

# Variable del Entry con un valor inicial por defecto
entry_var = tk.StringVar(value="Banana")  # Valor inicial por defecto

# Crear Entry
entry = tk.Entry(root, textvariable=entry_var)
entry.pack(pady=10)
entry.bind("<Button-1>", on_entry_click)  # Mostrar el Listbox al hacer clic en el Entry

# Crear Listbox con todas las opciones visibles
listbox = tk.Listbox(root, height=6)
for item in items:
    listbox.insert(tk.END, item)

# Vincular selección de Listbox con la entrada
listbox.bind("<<ListboxSelect>>", on_listbox_select)

# Iniciar la interfaz
root.mainloop()
