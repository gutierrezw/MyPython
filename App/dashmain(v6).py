from target_price_update import *
from operator import itemgetter
from estrategia import *
from planInversion import *
from api_finviz import *
from api_conect import *
from vision_board import *
from main_board import *
from main_crypto import *
from screener_board import *
from operator import itemgetter

from api_conect import *
from api_finviz import *
from estrategia import *
from main_board import *
from main_crypto import *
from planInversion import *
from screener_board import *
from target_price_update import *
from vision_board import *

global positions, current_prices, account_data, mxp, headings, win, gchar, itrue, wboard, waccp
itrue,  waccp = True, pd.DataFrame()


class acciones(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.create_widgets
        self.config(bg="black")
        self.update_stock()

    @staticmethod
    def fila(i) -> None:
        """
        @param i:
        @return:
        """
        ticket = mxp[i][0].cget('text').strip()
        evaluar_fila(account=apilocal['account'], vehiculo="Stock", ticket=ticket)

    def titulos(self, i=4):
        headings = ['Ticket', 'dGyP', 'position', 'mktPrice', 'AvgCost', 'mktValue', 'GyP', '%ROI',
                    'Dividendo', 'objetivo', 'GyP proy', 'V.price']

        mxp[i][0] = ttk.Button(self, text=headings[0], width=13,  command=lambda: order(0))
        mxp[i][1] = ttk.Button(self, text=headings[1], width=13,  command=lambda: order(1))
        mxp[i][2] = ttk.Button(self, text=headings[2], width=13,  command=lambda: order(2))
        mxp[i][3] = ttk.Button(self, text=headings[3], width=13,  command=lambda: order(3))
        mxp[i][4] = ttk.Button(self, text=headings[4], width=13,  command=lambda: order(4))
        mxp[i][5] = ttk.Button(self, text=headings[5], width=13,  command=lambda: order(5))
        mxp[i][6] = ttk.Button(self, text=headings[6], width=13,  command=lambda: order(6))
        mxp[i][7] = ttk.Button(self, text=headings[7], width=13,  command=lambda: order(7))
        mxp[i][8] = ttk.Button(self, text=headings[8], width=13,  command=lambda: order(8))
        mxp[i][9] = ttk.Button(self, text=headings[9], width=13,  command=lambda: order(9))
        mxp[i][10] = ttk.Button(self, text=headings[10], width=13, command=lambda: order(10))
        mxp[i][11] = ttk.Button(self, text=headings[11], width=13, command=lambda: order(11))

        mxp[i][0].grid(row=i, column=0, padx=0)
        mxp[i][1].grid(row=i, column=1, padx=0)
        mxp[i][2].grid(row=i, column=2, padx=0)
        mxp[i][3].grid(row=i, column=3, padx=0)
        mxp[i][4].grid(row=i, column=4, padx=0)
        mxp[i][5].grid(row=i, column=5, padx=0)
        mxp[i][6].grid(row=i, column=6, padx=0)
        mxp[i][7].grid(row=i, column=7, padx=0)
        mxp[i][8].grid(row=i, column=8, padx=0)
        mxp[i][9].grid(row=i, column=9, padx=0)
        mxp[i][10].grid(row=i, column=10, padx=0)
        mxp[i][11].grid(row=i, column=11, padx=0)

        return mxp

    def lineas(self, i, j=0):
        lfg = "TLabel"

        if i == 6:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 7:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 8:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 9:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 10:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 11:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 12:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 13:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 14:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 15:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 16:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 17:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 18:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 19:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 20:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 21:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 22:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 23:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 24:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 25:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 26:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 27:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 28:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 29:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 30:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 31:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 32:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 33:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 34:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 35:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)
        if i == 36:
            mxp[i][j] = ttk.Button(self, text=" ", style=lfg, command=lambda: acciones.fila(i))
            mxp[i][j].grid(row=i, column=j)

        return mxp

    @property
    def create_widgets(self):
        global positions, current_prices, account_data, board, s_invertir, mxp
        global fg0, cv0, fg1, cv1, fg2, cv2

        x: tuple = ('Tcos', 'TMkV', 'TPos', 'TObj', 'TDiv', 'TPyl', 'TRet', 'TCre', 'TdPyl')
        totales: dict = dict.fromkeys(x, 0.00)
        datsess = select_sesion(fectime, "orden", "select")
        p_invertir = int(datsess['Pinvertir'])
        """
        @ pinta panel vacio de stock
        """
        win1 = tk.Frame(self, bg='black', bd=1)
        win2 = tk.Frame(self, bg='white', bd=1)

        win20 = tk.Frame(win2, bg='black')
        win21 = tk.Frame(win2, bg='black')
        win22 = tk.Frame(win2, bg='black')

        win1.grid(row=0, column=0, padx=2, pady=0)
        win2.grid(row=0, column=1, padx=2, pady=0)

        win20.grid(row=0, column=0, padx=0, pady=1)
        win21.grid(row=1, column=0, padx=0, pady=1)
        win22.grid(row=2, column=0, padx=0, pady=1)

        for i in range(0, 36):
            for j in range(12):
                if i in (0, 1, 2):
                    if i == 2:
                        if j == 8:
                            s_invertir = StringVar(win1, p_invertir)
                            mxp[i][j] = ttk.Entry(win1, width=7, font=8, justify="right", textvariable=s_invertir)
                            mxp[i][j].grid(row=i, column=j, padx=0)
                        if j == 9:
                            mxp[i][j] = ttk.Button(win1, text="Inversión", style='TLabel', width=10)
                            mxp[i][j].grid(row=i, column=j, padx=0)
                    else:
                        mxp[i][j] = ttk.Button(win1, text=' ', width=10, style='TLabel')
                        mxp[i][j].grid(row=i, column=j, padx=0)
                if i == 4:
                    acciones.titulos(win1, i)
                if i > 4:
                    acciones.lineas(win1, i, j=0)
                    mxp[i][j] = ttk.Button(win1, text=' ', width=12, style='TLabel')
                    mxp[i][j].grid(row=i, column=j)

        mxp[37][8] = ttk.Button(win1, text='-- Pag', width=13, command=lambda: pagina(), style='TButton')
        mxp[37][9] = ttk.Button(win1, text='++ Pag', width=13, command=lambda: pagina(), style='TButton')
        mxp[37][10] = ttk.Button(win1, text='Filtro', width=13, command=lambda: filtro(), style='TButton')
        mxp[37][8].grid(row=37, column=8)
        mxp[37][9].grid(row=37, column=9)
        mxp[37][10].grid(row=37, column=10)
        """
        @ pinta header de stock
        """
        k, i, tdpyl = 2, 2, 0
        for key in board:
            if k == 2:
                xbg = "red" if tdpyl < 0 else "green"
                mxp[1][0] = ttk.Label(win1, text='{:>20.2f}'.format(tdpyl), font=10, background=xbg, width=16)
                mxp[1][0].grid(row=1, column=0, columnspan=2)
            if key in ('Nav', 'UnP&l', 'P&l', 'Div/cobrar', 'Cash'):
                mxp[0][k] = ttk.Label(win1, text='{:>10}'.format(key))
                mxp[0][k].grid(row=0, column=k)
                mxp[0][k + 1] = ttk.Label(win1, text='{:>10.2f}'.format(board[key]))
                mxp[0][k + 1].grid(row=0, column=k + 1)
                k += 2
            if key in ('Stock', 'Crypto', 'UnProfit', 'Div/año', 'PB/año'):
                mxp[1][i] = ttk.Label(win1, text='{:>10}'.format(key))
                mxp[1][i].grid(row=1, column=i)
                mxp[1][i + 1] = ttk.Label(win1, text='{:>10.2f}'.format(board[key]))
                mxp[1][i + 1].grid(row=1, column=i + 1)
                i += 2

        gcolor = 'black'
        fg0 = Figure(figsize=(2.0, 2.0), dpi=110, layout="tight")
        fg0.set_facecolor(gcolor)
        cv0 = FigureCanvasTkAgg(fg0, master=win20)
        cv0.draw()
        cv0.get_tk_widget().pack()

        fg1 = Figure(figsize=(2.0, 2.0), dpi=110, layout="tight")
        fg1.set_facecolor(gcolor)
        cv1 = FigureCanvasTkAgg(fg1, master=win21)
        cv1.draw()
        cv1.get_tk_widget().pack()

        fg2 = Figure(figsize=(2.0, 2.0), dpi=110, layout="tight")
        fg2.set_facecolor(gcolor)
        cv2 = FigureCanvasTkAgg(fg2, master=win22)
        cv2.draw()
        cv2.get_tk_widget().pack()

        return mxp

    def update_stock(self):
        global positions, current_prices, account_data, board, s_invertir, mxp, lock
        global fg0, cv0, fg1, cv1, fg2, cv2

        x: tuple = ('Tcos', 'TMkV', 'TPos', 'TObj', 'TDiv', 'TPyl', 'TRet', 'TCre', 'TdPyl')
        totales: dict = dict.fromkeys(x, Decimal(0.00))

        board['Nav'] = Decimal(account_data["USD"]['netliquidationvalue'])
        board['UnP&l'] = Decimal(account_data["USD"]['unrealizedpnl'])
        board['P&l'] = Decimal(account_data["USD"]['realizedpnl'])
        board['Div/cobrar'] = Decimal(account_data["USD"]['dividends'])
        board['Cash'] = Decimal(account_data["USD"]['cashbalance'])
        board['Stock'] = Decimal(account_data["USD"]['stockmarketvalue'])
        board['Crypto'] = Decimal(account_data["USD"]['cryptocurrencyvalue'])
        board['UnProfit'] = Decimal(0)
        board['Pinvertir'] = p_invertir = Decimal(s_invertir.get())
        wboard['Stock'] = board
        """
        @ pinta detalle del panel acciones  y controla orden en que se muestra positions
        """
        datsess = select_sesion(fectime, accion="select")
        xdict = json.loads(datsess['orcartera'])
        orden = list(xdict.keys())
        orden.append(xdict[orden[0]])
        positions = create_position(orden, p_invertir)

        if datsess['xstrategy']:
            tstrategy = datsess['xstrategy'].split()
        else:
            tstrategy = list()
            sstrategy = select_estrategia('estrategia')
            for i in range(len(sstrategy)):
                tstrategy.append(sstrategy[i][0:3])

        i = 6
        for pkey in positions:
            if i < 36:
                if pkey['estrategia'] in tstrategy:

                    displaystoc(i, pkey, True)
                    totales['TPos'] += Decimal(pkey['position'])
                    totales['Tcos'] += Decimal(pkey['costobase'])
                    totales['TMkV'] += Decimal(pkey['mktValue'])
                    totales['TPyl'] += Decimal(pkey['unrealizedpnl'])
                    totales['TObj'] += Decimal(pkey['gypo'])
                    i += 1

            totales['TdPyl'] += pkey['change']
            totales['TDiv'] += pkey['dividendo']
            if pkey['unrealizedpnl'] > 0:
                board['UnProfit'] += pkey['unrealizedpnl']
            board['costobase'] = totales['Tcos']

        """
        @ limpia panel hasta fin de pantalla
        """
        for k in range(i, 36):
            displaystoc(k, False)
        """
        @ escribe totales del panel (1era linea)
        """
        gbg = "red" if totales['TdPyl'] < 0 else "green"
        mxp[1][0].config(text='{:>20.0f}'.format(totales['TdPyl']), background=gbg)
        mxp[5][2].config(text='{:>10.3f}'.format(totales['TPos']))
        mxp[5][4].config(text='{:>10.2f}'.format(totales['Tcos']))
        mxp[5][5].config(text='{:>10.2f}'.format(totales['TMkV']))
        mxp[5][6].config(text='{:>10.2f}'.format(totales['TPyl']))
        if totales['Tcos'] > 0:
            mxp[5][7].config(text='{:>+10.2%}'.format(totales['TPyl']/totales['Tcos']))
        mxp[5][8].config(text='{:>10.2f}'.format(totales['TDiv']))
        mxp[5][10].config(text='{:>10.2f}'.format(totales['TObj']))
        """
        @ actualiza header del panel acciones
        """
        k, i, = 3, 3
        for key in board:
            if key in ('Nav', 'UnP&l', 'P&l', 'Div/cobrar', 'Cash'):
                mxp[0][k].config(text='{:>10.2f}'.format(board[key]))
                k += 2
            if key in ('Stock', 'Crypto', 'UnProfit', 'Div/año', 'PB/año'):
                board['PB/año'] = 0.00
                if (board['UnProfit'] + totales['TDiv']) > 0:
                    board['PB/año'] = (board['Nav'] + abs(board['UnP&l'])) / (board['UnProfit'] + totales['TDiv'])

                board['Div/año'] = totales['TDiv']
                mxp[1][i].config(text='{:>10.2f}'.format(board[key]))
                i += 2

        self.after(4000, self.update_stock)
        roi_stock(fg=fg0, cv=cv0)

        return board, positions, current_prices, account_data


def thr_positions(itrue) -> None:
    """
    @return:
    """
    global account_data, positions
    try:
        while not itrue.is_set():
            positions = positions_account(account_id=apilocal['account'])
            account_data = summary_account_api(account=apilocal['account'])
            if positions:
                datosmarket_api(positions=positions)

            time.sleep(5)

    except threading.ThreadError as error:
        print("[Thread::  thr_positions()]: {}".format(error))

    return account_data


def thr_chartmain(itrue) -> None:
    """
    @return:
    """
    global wboard, waccp, win
    global fg1, cv1, fg2, cv2, fg3, cv3, fg4, cv4, fg5, cv5, fg6, cv6
    try:
        while not itrue.is_set():

            # indicador del miedo
            setup_fear_greed(fg1, cv1)

            #
            # chart estrategia estratificada
            xestrategia = read_estrategia()
            char_estrategia(fg=fg3, cv=cv3, xaspect=0.4, strategy=xestrategia)

            #
            # chart por performance por sector
            grupo_sector(fg4, cv4)

            # waccp proviene de Dataframe construido por select_performa_inversion()
            #(asset, xlist) = dict_peso_positions(vehiculo='Stock')
            #waccp = performa_asset(account=apilocal['account'], tipo='Stock', activos=xlist, asset=asset)
            # dlabl = {'SPX': 'SPX++index', '++ index': '++ Portafolio', "legend": 'outside upper right', "aspect": 0.40}
            # performa_portafolio(fg5, cv5, waccp, dlabl, 'Rendimiento de Acciones')

            # waccp proviene de Dataframe construido por select_performa_inversion()
            waccp = performa_asset(account=apilocal['account'], vehiculo='Stock', tipo='Stock')

            dlabl = {'SPX': 'SPX++index', '++ index': "++ Portafolio", 'Value': 'Value Market', 'Costo': 'Cost basic',
                     "legend": 'outside upper left', "aspect": 0.40}
            performa_portafolio(fg5, cv5, waccp, dlabl, 'Performance (acumulativo) portafolio vs ^GSPC')
            time.sleep(60)

    except EncodingWarning as error:
        print("[Thread :: thr_chartmain()]: {}".format(error))

    return


def roi_stock(fg=None, cv=None):
    global tdebit, board, wperf

    """
    @ llenado de estructuras para los graficos del panel
    """
    cartera = select_inversion(tipoin='Stock')
    tcos, tpro, tunr = 0, 0, 0
    cash, parm = float(board['Cash']), {}
    i = 0
    orden = ["unrealizedpnl", "DES"]
    cartera = sort_positions(cartera, orden)

    for key in cartera:
        pobj = 0 if key['unrealizedpnl'] < 0 else float(key['unrealizedpnl'])
        tcos += float(key['costobase'])
        tunr += float(key['unrealizedpnl'])
        tpro += pobj

    wdata = {'Inversión': tcos, 'UnProfit': tpro,  'UnP&l': tunr, 'Cash': cash}
    parm.update({'titulo': 'ROI de Stock'})
    parm.update({'aspect': 0.50})
    performa(fg, cv, wdata, parm)


def thr_datos_account(itrue):
    global wboard

    try:
        while not itrue.is_set():

            actualiza_booktrading_stock(account_id=apilocal['account'])
            (asset, xlist) = dict_peso_positions(vehiculo='Stock')

            target_price_washlist()
            diaria_book_performance(account=apilocal['account'], vehiculo='Stock', asset=xlist)

            time.sleep(20)
            print('thr_datos_account()', datetime.now())

    except EncodingWarning as error:
        print("[Thread error]: {}".format(error))

    return


def order(colm):
    keys = ["contractDesc", "change", "position", "mktPrice", "CosS", "mktValue", "gyp",
            "retorno", "Adiv", "Obje", "avgCost", "gypo", "Stock", "prmd", "indx", "gypp", "ixGp"]

    datsess = select_sesion(fectime, accion="select")
    a_orden = datsess['OrCartera']

    x = str({keys[colm]: 'ASC'}) if 'DES' in a_orden else str({keys[colm]: 'DES'})
    u_orden = x.replace("'", '"')
    datsess = select_sesion(fectime, u_orden, accion="update")


def pagina(accion):
    if accion == '--':
        print('pagina atras')
    if accion == '++':
        print('avanza pagina')


def displaystoc(i, pkey=None, writelinea=False):
    if writelinea:

        cbg = display_red_green(pkey['pchange'], i)
        gbg = display_red_green(pkey['unrealizedpnl'], i)
        ibg = display_azul(0.00, i)
        iibg = display_azul(0.20, i)

        lfg = "TLabel" if i == 5 else ("TLabel" if i % 2 == 0 else "I.TLabel")
        pibg = "Sy.TLabel" if i == 5 else ("Sy.TLabel" if i % 2 == 0 else "Cw.TLabel")

        mxp[i][0].config(text=' {:<10}'.format(pkey['ticket'][0:4]), style=lfg)
        mxp[i][1].config(text='{:>10.0f}'.format(pkey['change']), style=cbg)
        mxp[i][2].config(text='{:>10.3f}'.format(pkey['position']), style=lfg)
        mxp[i][3].config(text='{:>10.3f}'.format(pkey['mrkprice']), style=lfg)
        mxp[i][4].config(text='{:>10.2f}'.format(pkey['costobase']), style=lfg)
        mxp[i][5].config(text='{:>10.2f}'.format(pkey['mktValue']), style=ibg)
        mxp[i][6].config(text='{:>10.2f}'.format(pkey['unrealizedpnl']), style=gbg)
        mxp[i][7].config(text='{:>+10.2%}'.format(pkey['retorno']), style=gbg)
        mxp[i][8].config(text='{:>10.2f}'.format(pkey['dividendo']), style=lfg)
        mxp[i][9].config(text='{:>10.2f}'.format(pkey['objetivo']), style=lfg)
        mxp[i][10].config(text='{:>10.2f}'.format(pkey['gypo']), style=pibg)
        mxp[i][11].config(text='{:>+10.1%}'.format(pkey['ixVp']), style=iibg)
        mxp[i][18] = pkey['empresa']
    else:
        mxp[i][0].config(text=' ', style="TLabel")
        mxp[i][1].config(text=' ', style="TLabel")
        mxp[i][2].config(text=' ', style="TLabel")
        mxp[i][3].config(text=' ', style="TLabel")
        mxp[i][4].config(text=' ', style="TLabel")
        mxp[i][5].config(text=' ', style="TLabel")
        mxp[i][6].config(text=' ', style="TLabel")
        mxp[i][7].config(text=' ', style="TLabel")
        mxp[i][8].config(text=' ', style="TLabel")
        mxp[i][9].config(text=' ', style="TLabel")
        mxp[i][10].config(text=' ', style="TLabel")
        mxp[i][11].config(text=' ', style="TLabel")


def filtro():
    """
    @ aplica filtro en la posición en funcion del tipo de estrategia
    """
    def eexit() -> None:
        rnb.destroy()

    def seleccion():
        global xestrategy
        ix = lis.curselection()
        if ix:
            xestrategy = ' '
            for i in ix:
                xestrategy = xestrategy + lis.get(i)[0:3] + ' '
        datsess = select_sesion(fectime, filtro=xestrategy, accion="updatexstrategy")

    rnb = tk.Tk()
    xdimension = "%dx%d+%d+%d" % (240, 220, df + 5, 700)
    rnb.geometry(xdimension)
    rnb.resizable(False, False)
    rnb.attributes('-toolwindow', 1)
    rnb.title("Seleccione la(s) estrategia(s)")
    rnb.config(bg="black")

    lis = tk.Listbox(rnb, width=40, height=10, selectmode=tk.EXTENDED, bg='black', fg='white')
    lis.pack()
    ttk.Button(rnb, text='Aplicar', width=10, command=seleccion, style='TButton').place(x=90, y=180)
    ttk.Button(rnb, text='Exit',    width=10, command=eexit,      style='TButton').place(x=160, y=180)

    xstrategy = select_estrategia(accion='estrategia', ivehiculo='IBKs')
    for key in xstrategy:
        lis.insert(tk.END, key)

    rnb.mainloop()
    rnb.destroy()


def create_position(orden, p_invertir) -> dict:
    cartera = select_inversion(tipoin='Stock')
    for pkey in cartera:
        if pkey['position'] > 0:

            position = Decimal(pkey['position'])
            pkey['avgCost'] = pkey['costobase'] / position
            pkey['change'] = position * pkey['pchange']
            pkey['gypo'] = pkey['objetivo'] * position - pkey['costobase']

            (nstok, prcmd, gypp, indx) = donde_invertir(pkey, p_invertir)
            pkey['Nstok'] = nstok
            pkey['prcmd'] = prcmd
            pkey['gypp'] = gypp
            pkey['ixVp'] = indx['ixVp']
            pkey['ixGp'] = indx['ixGp']
            if pkey['gypo'] != 0:
                pkey['GpyGo'] = (pkey['gypp'] - pkey['gypo']) / pkey['gypo']

    xcartera = sort_positions(cartera, orden)
    return xcartera


def actualiza_booktrading_stock(account_id=None):
    """
    @param account_id: id de cuenta
    @return: controla e inserta trades en la tabla booktrading
    """
    datos = list()
    try:
        trades = trades_api(account_id=account_id)
        if trades:
            for keys in trades:
                values = dict()
                values.update({'simbolo': keys['symbol']})
                values.update({'categoria': 'Stock'})
                values.update({'divisa': 'USD'})
                values.update({'cuenta': keys['accountCode']})
                timestamp = int(keys['trade_time_r'] / 1000)
                values.update({'fechahora': datetime.fromtimestamp(timestamp)})
                values.update({'idtrans': keys['execution_id']})

                values.update({'preciotrans': Decimal(keys['price'])})
                values.update({'preciocierre': Decimal(keys['price'])})
                values.update({'tarifacomision': Decimal(keys['commission'])})
                values.update({'producto': Decimal(keys['net_amount'])})

                if keys['side'] == 'B':
                    values.update({'cantidad': Decimal(keys['size'])})
                    values.update({'gprealizadas': 0.00})
                    values.update({'mtmgp': 0.00})
                    values.update({'codigo': 'O'})

                if keys['side'] == 'S':
                    values.update({'cantidad': -Decimal(keys['size'])})
                    values.update({'gprealizadas': 0.00})
                    values.update({'mtmgp': 0.00})
                    values.update({'codigo': 'C'})

                datos.append(values)

    except EncodingWarning as error:
        print("actualiza_booktrading_stock()::]: {}".format(error))

    if datos:

        datos_ord = sorted(datos, key=itemgetter('cuenta', 'simbolo', 'fechahora', ))
        for key in datos_ord:
            simbolo = key['simbolo']
            values = key.pop('simbolo')
            insert_booktrading(values=key, symbol=simbolo)


def the_gui():
    global positions, current_prices, account_data, board, s_invertir, mxp, win, gchar, itrue
    global fg1, cv1, fg2, cv2, fg3, cv3, fg4, cv4, fg5, cv5, fg6, cv6, win

    def on_closing() -> None:
        """
        @return:
        """
        global itrue
        if tk.messagebox.askokcancel(dversion, "¿Estás seguro de que deseas salir?"):
            itrue = False
            frame_strat.destroy()
            frame_stock.destroy()
            frame_plan.destroy()
            win.destroy()

    win = tk.Tk()
    win.protocol("WM_DELETE_WINDOW", on_closing)
    dw = win.winfo_screenwidth()
    dh = win.winfo_screenheight()
    dimension = "%dx%d+0+0" % (dw, dh)
    win.geometry(dimension)
    win.title(dversion)
    win.config(bg="black")

    style = style_app(main=win)

    nb = ttk.Notebook(win, style="TNotebook", width=df, height=700)
    fwin0 = ttk.Frame(nb, style="TFrame", width=df, height=700)
    fwin1 = ttk.Frame(nb, style="TFrame", width=df, height=700)
    fwin2 = ttk.Frame(nb, style="TFrame", width=df, height=700)
    fwin3 = ttk.Frame(nb, style="TFrame", width=df, height=700)
    fwin4 = ttk.Frame(nb, style="TFrame", width=df, height=700)
    fwin5 = ttk.Frame(nb, style="TFrame", width=df, height=700)

    nb.add(fwin0, text='Stock          ')
    nb.add(fwin1, text='Crypto         ')
    nb.add(fwin2, text='Estrategia     ')
    nb.add(fwin3, text='Plan           ')
    nb.add(fwin4, text='VisionBoard    ')
    nb.add(fwin5, text='Screener       ')
    nb.pack(anchor='nw', pady=10, expand=True)

    rnb = ttk.Frame(win, style="TFrame")
    rnb.place(x=df + 10, y=10)
    """
    @ Crear la figura de matplotlib
    """
    pn0 = tk.Frame(win, bg='black')
    pn1 = tk.Frame(win, bg='white', border=2)
    pn2 = tk.Frame(win, bg='white', border=2)
    pn3 = tk.Frame(win, bg='white', border=2)
    pn4 = tk.Frame(win, bg='white', border=2)
    pn5 = tk.Frame(win, bg='white', border=2)
    pn6 = tk.Frame(win, bg='white', border=2)

    pn0.place(x=df + 15, y=10)
    pn1.place(x=df + 15, y=190)
    pn2.place(x=df + 15, y=470)
    pn3.pack(pady=2, padx=2, side="left")
    pn4.pack(pady=2, padx=2, side="left")
    pn5.pack(pady=2, padx=2, side="left")
    pn6.pack(pady=2, padx=2, side="left")

    fg1 = Figure(figsize=(5.50, 2.4), dpi=110, layout="tight")
    fg2 = Figure(figsize=(5.50, 2.4), dpi=110, layout="tight")
    fg3 = Figure(figsize=(5.75, 2.9), dpi=110, layout="tight")
    fg4 = Figure(figsize=(5.75, 2.9), dpi=110, layout="tight")
    fg5 = Figure(figsize=(5.75, 2.9), dpi=110, layout="tight")
    gcolor = 'black'
    fg1.set_facecolor(gcolor)
    fg2.set_facecolor(gcolor)
    fg3.set_facecolor(gcolor)
    fg4.set_facecolor(gcolor)
    fg5.set_facecolor(gcolor)

    cv1 = FigureCanvasTkAgg(fg1, master=pn1)
    cv1.draw()
    cv1.get_tk_widget().pack()

    cv2 = FigureCanvasTkAgg(fg2, master=pn2)
    cv2.draw()
    cv2.get_tk_widget().pack()

    cv3 = FigureCanvasTkAgg(fg3, master=pn3)
    cv3.draw()
    cv3.get_tk_widget().pack()

    cv4 = FigureCanvasTkAgg(fg4, master=pn4)
    cv4.draw()
    cv4.get_tk_widget().pack()

    cv5 = FigureCanvasTkAgg(fg5, master=pn5)
    cv5.draw()
    cv5.get_tk_widget().pack()

    """
     @ wingless para menu acciones
     @ mxp[i,18]:= nombre del activo
    """
    mxp = [[None] * 19 for _ in range(38)]
    board = {'Nav': 0, 'UnP&l': 0, 'P&l': 0, 'Div/cobrar': 0, 'Cash': 0, 'Stock': 0, 'Crypto': 0,
             'UnProfit': 0, 'Div/año': 0, 'PB/año': 0, 'Pinvertir': 0}

    account_data = summary_account_api(account=apilocal['account'])

    itrue = threading.Event()
    Thread(target=thr_positions, name='thr_positions', args=(itrue,)).start()
    Thread(target=thr_chartmain, name='thr_chartmain', args=(itrue,)).start()

    frame_stock = acciones(master=fwin0)
    frame_stock.pack()

    #Thread(target=thr_datos_crypto, name='datos_crypto', args=(itrue,)).start()
    #Thread(target=thr_position_crypto, name='position_crypto', args=(itrue,)).start()
    #frame_cryp = cryptos(master=fwin1)
    #frame_cryp.pack()

    frame_strat = estrategy(master=fwin2)
    frame_strat.pack()

    frame_plan = plan_inversion(master=fwin3)
    frame_plan.grid()

    Thread(target=thr_datos_account, name='datos_account', args=(itrue,)).start()
    frame_pn0 = mboard0(master=pn0)
    frame_pn0.pack()

    frame_vision = visionBoard(master=fwin4)
    frame_vision.pack(pady=15)

    #frame_screener = screener_board(master=fwin5)
    #frame_screener.pack()

    itrue.clear()
    win.update()
    win.mainloop()


if __name__ == '__main__':
    if inicio():
        the_gui()
    else:
        itrue = False
        print("[Messg]: fin de sesión (Api) :" + str(datetime.now()))