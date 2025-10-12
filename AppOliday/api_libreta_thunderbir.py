import pythunderbird as tb

# Inicializar Thunderbird
tb_app = tb.ThunderbirdApp()

# Acceder a la libreta de direcciones
address_book = tb_app.address_book

# Listar todos los contactos
contacts = address_book.get_contacts()
for contact in contacts:
    print(contact.name, contact.email)
