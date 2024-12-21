import tkinter as tk

def foco_cambiado(event):
    print(f"Foco actual: {root.focus_get()}")

root = tk.Tk()
root.title("Ejemplo de foco")

entry1 = tk.Entry(root, takefocus=True)
entry1.pack(pady=10)
entry1.bind("<FocusIn>", foco_cambiado)

entry2 = tk.Entry(root, takefocus=True)
entry2.pack(pady=10)
entry2.bind("<FocusIn>", foco_cambiado)

boton = tk.Button(root, text="Forzar foco en Entry 1", command=lambda: entry1.focus_force())
boton.pack(pady=10)

root.mainloop()
