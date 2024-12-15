from datetime import *

from api_chart import *
from bd_conect import *


class mboard0(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.widgets_mboard()
        self.update_mboard()
        self.config(bg="SpringGreen3")

    global inversor, traz

    def widgets_mboard(self):
        global inversor, status, traz

        inversor = tk.Label(self, text=' ', width=30, bg="SpringGreen3", fg='white')
        inversor.grid(row=0, column=0, padx=10)
        status = tk.Label(self, text='', width=30, bg="SpringGreen3", fg='white')
        status.grid(row=1, column=0, padx=10)

    def update_mboard(self):
        global inversor, status, traz, wboard
        datsess = select_sesion("select")
        traz = select_trazaplan(datsess['idcuenta'])[10]

        hoy = datetime.now()
        dias = hoy - datetime.combine(traz['extracto'], time(0, 0))
        inversor.config(text=dias, font=('Courier', 12))
        status.config(text='open', font=('Courier', 12))
        self.after(apilocal['elapse board'], self.update_mboard)


def chart_performa(fg, cv):
    global wboard

    if not is_vacio(wboard):
        gcolor = 'DarkSeaGreen'
        tcos, tpro, tunr, cash = 0, 0, 0, 0
        for keys, vals in wboard.items():
            if keys != 'status':
                tcos += float(vals['costobase'])
                tpro += float(vals['UnProfit'])
                tunr += float(vals['UnP&l'])
                cash += float(vals['Cash'])

        wdata = {'Inversión': tcos, 'UnProfit': tpro, 'UnP&l': tunr, 'Cash': cash}
        performa(fg, cv, wdata, 'ROI Global de Inversiones')


def chart_asignacion(fg, cv):
    global wboard

    if wboard:
        gcolor = 'DarkSeaGreen'
        tcos, peso, acum, xpeso = list(), list(), 0, 0
        for keys, vals in wboard.items():
            acum += float(vals['costobase'])
            tcos.append(float(vals['costobase']))

        for keys, vals in wboard.items():
            xpeso = float(vals['costobase']) / acum
            peso.append('{}{:>2.%}'.format(keys, xpeso))

        xdata = {'data': tcos, 'peso': peso}
        asignacion(fg, cv, xdata, 'Vehículos de Inversión')


def chart_account_performa(fg, cv):
    global waccp, wpaccp, wperf

    dlabl = {'SP500': 'S&P 500', '++ index': '++ Portafolio', "legend": 'outside upper right', "aspect": 0.21}
    performa_portafolio(fg2, cv2, waccp,  dlabl, 'Rendimiento Global de la Inversión')