
from tkinter import *
from tkinter import ttk

import time



def imprimir_fecha():
    return  str(time.localtime()[2]) + "/" + str(time.localtime()[1]) + "/" + str(time.localtime()[0]) + ", " + str(
                time.localtime()[3]) + ":" + str(time.localtime()[4]) + ":" + str(time.localtime()[5])


v0 = Tk()
v0.title("Hora")
mifecha = StringVar()
l1 = Label(v0, textvar=mifecha, font=(16))
l1.pack()
l2 = Label(v0, text="", font=(16))
l2.pack()


def refresh_fecha():
    v0.after(1000, refresh_fecha)
    mifecha.set(imprimir_fecha())
    l2.config(text=imprimir_fecha())


refresh_fecha()
v0.mainloop()