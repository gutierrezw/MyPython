import tkinter as tk

def validar_entra_numeros(P):
    if P == "" or P.isdigit():
        return True
    else:
        return False

ventana = tk.Tk()
ventana.title("Validación de Entrada en tiempo real")

validar_cmd = ventana.register(validar_entra_numeros)

label = tk.Label(ventana, text="Ingresa un número entero:")
label.pack()

entry = tk.Entry(ventana, validate="key", validatecommand=(validar_cmd, "%P"))
entry.pack()

ventana.mainloop()
