#menu_demo.py

import PySimpleGUI as sg

layout = [
        [sg.Text("Hola desde PySimpleGUI")],
        [sg.Button("Ok")]

]

# crea una window
window = sg.Window("Wilmer", layout)

#crea un evento loop
while True:
    event, values = window.read()
    # fin de programa si user close window or
    # presiona  Ok
    if event == "Ok"  or event == sg.WIN_CLOSED:
        break

window.close()