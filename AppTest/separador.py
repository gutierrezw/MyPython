from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

import tkinter as tk
from tkinter import ttk


root = tk.Tk()
root.title("Titulo de la ventana principal")
root.resizable(width=False, height=False)
root.geometry('700x400')

frame = ttk.Notebook(root)
frame.pack(expand=True, fill="both")
window0 = ttk.Frame(frame)

frame.add(window0,text="Pestaña 1")

tk.Label(
    window0, text="Etiqueta 1"
    ).grid(row=1, column=0, sticky="nsw")
tk.Button(window0, text="Boton 1", command="buscar"
          ).grid(row=1, column=2, sticky="w")

ttk.Separator(fwin1, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=3, sticky="EW")


tk.Label(window0, text="Etiqueta 2"
         ).grid(row=3, column=0, sticky="nsw")
tk.Button(
    window0, text="Boton 2",command="buscar"
    ).grid(row=3, column=2, sticky="w")


window0.grid_rowconfigure(0, minsize=15)
window0.grid_columnconfigure(1, minsize=5)
window0.grid_rowconfigure(2, minsize=15)  # <<<<<<<<<<<<<<<

root.mainloop()