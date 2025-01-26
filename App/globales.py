import io
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageTk
from ibapi import *
from ibapi.client import *
from ibapi.connection import *
from ibapi.contract import *
from ibapi.wrapper import *

from bd_conect import select_objeto
from Class_Ibrks import *
from rutinas import *

"""
    define globales de configuración
"""
global apilocal, iclient, ib_client, isApiweb, fectime, wboard
global dversion, dw, dh, df, pn0, pn1, pn2, pn3, pn4
current_prices = dict()
dversion = 'DashInv v6.0'
gchar = dict()
dw = 1295
dh = 780
df = 1295
apilocal, wboard = dict(), dict()
apilocal['elapse open'] = 3000
apilocal['elapse estrategia'] = apilocal['elapse open'] * 500
apilocal['elapse vision'] = apilocal['elapse open'] * 50
apilocal['elapse stock'] = apilocal['elapse open']
apilocal['elapse board'] = apilocal['elapse open']
apilocal['elapse plan'] = apilocal['elapse open'] * 700
apilocal['hostlocal'] = '127.0.0.1'
apilocal['username'] = 'guti2004'
apilocal['tsw_client'] = None
apilocal['ib_client'] = None
apilocal['isApiweb'] = False
apilocal['isApiTsw'] = False
apilocal['account'] = 'U4214563'
apilocal['client'] = 6666
apilocal['port'] = 0
ib_clientTSW = None
fectime = datetime.now()
itwspor = 7496
igbpor = 4001
ibool = False
"""
    define globales de ed marcos de modulos

"""
# wboard['status'] = status_marckets()


class ApiTest(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def error(self, reqid, errorcode, errorstring, advancedorderrejectjson):
        if errorcode not in (2104, 2106, 2158):
            print("[Error]: ", reqid, " ", errorcode, " ", errorstring, " ", advancedorderrejectjson)

    def nextValidId(self, orderid):
        global currency


def ib_sapiweb(s) -> bool:
    """
    @param s:
    @return:
    """
    con = False
    if s._is_server_running:
        if s.is_authenticated()['connected'] and s.is_authenticated()['authenticated']:
            con = True
    return con


def inicio():
    global listbox, ibool, apilocal

    def on_closing():
        if tk.messagebox.askokcancel(dversion, "¿Estás seguro de que deseas salir?"):
            ini.destroy()

    def selopcion():
        global ibool, apilocal
        sel = listbox.get(tk.ACTIVE)

        if sel == 'ApiWeb':
            apilocal['ib_client'] = IBClient(username=apilocal['username'],
                                             account=apilocal['account'],
                                             is_server_running=True)
            apilocal['isApiweb'] = ib_sapiweb(apilocal['ib_client'])

            if apilocal['isApiweb']:
                ibool = True
                print("[Messg]: inicio de sesión (ApiWeb) :" + str(datetime.now()))
            else:
                tk.messagebox.showinfo(dversion, "!Falla conección a ApiWeb¡")

        if sel == 'ApiTws':
            ib_client_tsw = ApiTest()
            apilocal['tsw_client'] = ib_client_tsw
            ib_client_tsw.connect(apilocal['hostlocal'], itwspor, apilocal['client'])
            apilocal['isApiTsw'] = ib_client_tsw.isConnected()

            if apilocal['isApiTsw']:
                ibool = True
                apilocal['port'] = itwspor
                print("[Messg]: inicio de sesión (ApiTws) :" + str(datetime.now()))
                ib_client_tsw.disconnect()
            else:
                tk.messagebox.showinfo(dversion, "!Falla conección a ApiTws¡")

        if sel == 'Api Gateway':
            ib_client_tsw = ApiTest()
            ib_client_tsw.connect(apilocal['hostlocal'], igbpor, apilocal['client'])
            apilocal['isApiTsw'] = ib_client_tsw.isConnected()
            if apilocal['isApiTsw']:
                ibool = True
                apilocal['port'] = igbpor
                print("[Messg]: inicio de sesión (Api Gateway) :" + str(datetime.now()))
                ib_client_tsw.disconnect()
            else:
                tk.messagebox.showinfo(dversion, "!Falla conección a Api Gateway¡")

        if sel not in opciones:
            tk.messagebox.showinfo(dversion, "!Debe seleccionar una Api  para la conección¡")

        ini.destroy()
        return ibool, apilocal

    ini = tk.Tk()
    style = ttk.Style(ini)
    style.configure('TFrame', font=('Courier', 8), foreground="white", background="black")
    style.configure('TLabel', font=('Courier', 8), foreground="white", background="black")

    ini.protocol("WM_DELETE_WINDOW", on_closing)
    ini.geometry("570x370+700+400")
    ini.title(dversion)
    ini.config(bg="black")

    opciones = ["ApiWeb", "ApiTws", "Api Gateway"]
    fin0 = ttk.Frame(ini, style="TFrame")
    fin0.grid(row=0, column=0, padx=20, pady=15)
    fin1 = ttk.Frame(ini, style="TFrame")
    fin1.grid(row=0, column=2, padx=20, pady=15)
    fin2 = ttk.Frame(ini, style="TFrame")
    fin2.grid(row=1, column=0, padx=20, pady=10, columnspan=3)

    listbox = tk.Listbox(fin0, selectmode=tk.SINGLE, height=6, width=28, background='black', foreground='white')
    for opcion in opciones:
        listbox.insert(tk.END, opcion)
    listbox.grid(row=0, column=0, columnspan=2)

    imagencod = numero_randon(amplitud=10)
    imagen0, xlis = select_objeto(codigo=imagencod)
    imagen = Image.open(io.BytesIO(imagen0))
    imagen = imagen.resize((300, 200), Image.ADAPTIVE)
    imagen_tk = ImageTk.PhotoImage(imagen)
    tk.Label(fin1, image=imagen_tk).grid(row=2, column=4, padx=10)

    tk.Text(fin2, height=4, width=74, font=('Courier', 8),background='black',
                  foreground='white').grid(row=1, column=0, columnspan=3)
    boton = ttk.Button(ini, text="Aplicar", width=10, style='TButton', command=selopcion)
    eexit = ttk.Button(ini, text="Exit", width=10, style='TButton', command=on_closing)
    boton.place(x=380, y=320)
    eexit.place(x=450, y=320)
    ini.mainloop()
    return ibool


