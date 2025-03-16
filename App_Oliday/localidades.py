import tkinter as tk
from tkinter import messagebox

from connector_db import *

connection = create_connection(host="localhost", user="root", password="Daga2004", database="bdoliday")


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestión de Registros")

        # Etiquetas y campos de entrada
        self.name_label = tk.Label(root, text="Nombre")
        self.name_label.grid(row=0, column=0)
        self.name_entry = tk.Entry(root)
        self.name_entry.grid(row=0, column=1)

        self.age_label = tk.Label(root, text="Edad")
        self.age_label.grid(row=1, column=0)
        self.age_entry = tk.Entry(root)
        self.age_entry.grid(row=1, column=1)

        self.city_label = tk.Label(root, text="Ciudad")
        self.city_label.grid(row=2, column=0)
        self.city_entry = tk.Entry(root)
        self.city_entry.grid(row=2, column=1)

        # Botones
        self.add_button = tk.Button(root, text="Agregar", command=self.add_record)
        self.add_button.grid(row=3, column=0)

        self.update_button = tk.Button(root, text="Modificar", command=self.update_record)
        self.update_button.grid(row=3, column=1)

        self.delete_button = tk.Button(root, text="Eliminar", command=self.delete_record)
        self.delete_button.grid(row=3, column=2)

    def add_record(self):
        record = {
            "name": self.name_entry.get(),
            "age": int(self.age_entry.get()),
            "city": self.city_entry.get()
        }
        db.add_record(connection, "table_name", record)
        messagebox.showinfo("Info", "Registro agregado exitosamente")

    def update_record(self):
        record = {
            "name": self.name_entry.get(),
            "age": int(self.age_entry.get()),
            "city": self.city_entry.get()
        }
        condition = "id = 1"  # Aquí deberías obtener el ID del registro a actualizar
        db.update_record(connection, "table_name", record, condition)
        messagebox.showinfo("Info", "Registro actualizado exitosamente")

    def delete_record(self):
        condition = "id = 1"  # Aquí deberías obtener el ID del registro a eliminar
        db.delete_record(connection, "table_name", condition)
        messagebox.showinfo("Info", "Registro eliminado exitosamente")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
