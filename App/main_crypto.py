from threading import Thread

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from api_chart import *
from api_utilitis import *

global mxp, itrue, s_invertir, tdebit, wboard, wperf
itrue, tdebit, wperf, t_inicio = True, 0, pd.DataFrame(), 0


class cryptos(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.widgets_cryptos()
        self.update_cryptos()
        self.config(bg="black")
    global mxp

    @staticmethod
    def fila(i=None) -> None:
        """
        @param i:
        @return:
        """
        if not is_none(i):
            ticket = mxp[i][0].cget('text').strip()
            evaluar_fila(account='B0000001', vehiculo='Crypto', ticket=ticket)

    def titulos(self, i=4):
        """
        @param i: denota fila de impresión
        @return:  display de titulos para el panel
        """
        titulo = ['Ticket', 'dGyP', 'Posición', 'mktPrice', 'AvgCost', 'ValueMkt', 'GyP',
                  '%ROI', 'GyP.proy', '%V (Prc)(Gan)']
        mxp[i][0] = ttk.Button(self, text=titulo[0], width=15)
        mxp[i][1] = ttk.Button(self, text=titulo[1], width=15)
        mxp[i][2] = ttk.Button(self, text=titulo[2], width=15)
        mxp[i][3] = ttk.Button(self, text=titulo[3], width=15)
        mxp[i][4] = ttk.Button(self, text=titulo[4], width=15)
        mxp[i][5] = ttk.Button(self, text=titulo[5], width=15)
        mxp[i][6] = ttk.Button(self, text=titulo[6], width=15)
        mxp[i][7] = ttk.Button(self, text=titulo[7], width=15)
        mxp[i][8] = ttk.Button(self, text=titulo[8], width=15)
        mxp[i][9] = ttk.Button(self, text=titulo[9], width=15)

        mxp[i][0].grid(row=i, column=0)
        mxp[i][1].grid(row=i, column=1)
        mxp[i][2].grid(row=i, column=2)
        mxp[i][3].grid(row=i, column=3)
        mxp[i][4].grid(row=i, column=4)
        mxp[i][5].grid(row=i, column=5)
        mxp[i][6].grid(row=i, column=6)
        mxp[i][7].grid(row=i, column=7)
        mxp[i][8].grid(row=i, column=8)
        mxp[i][9].grid(row=i, column=9)

        return mxp

    def lineas(self, i, j=0):
        global mxp

        lfg = "TLabel"
        if i == 6:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 7:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 8:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 9:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 10:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 11:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 12:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 13:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 14:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 15:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 16:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 17:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 18:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 19:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 20:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 21:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 22:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)
        if i == 23:
            mxp[i][j] = ttk.Button(self, text=str(i), width=14, style=lfg)
            mxp[i][j].grid(row=i, column=j)

        return mxp

    def widgets_cryptos(self):

        global mxp, board, s_invertir, fg0, cv0, fg1, cv1, fg2, cv2, fg3, cv3
        mxp = [[None] * 10 for _ in range(26)]
        board = {'Nav': 0, 'UnP&l': 0, 'Dividendos': 0, 'Cash': 0, 'UnProfit': 0,
                 'PB/año': 0, '%Margen': 0, 'Pinvertir': 0, 'costobase': 0}

        win1 = tk.Frame(self, bg='black', bd=1)
        win2 = tk.Frame(self, bg='white', bd=1)
        win3 = tk.Frame(self, bg='white', bd=1)

        win20 = tk.Frame(win2, bg='black')
        win21 = tk.Frame(win2, bg='black')
        win30 = tk.Frame(win3, bg='black')
        win31 = tk.Frame(win3, bg='black')

        win1.grid(row=0, column=0, padx=1, pady=5)
        win2.grid(row=0, column=1, padx=1, pady=5)
        win3.grid(row=1, column=0, padx=1, pady=10, columnspan=2)

        win20.grid(row=0, column=0, padx=0, pady=1)
        win21.grid(row=1, column=0, padx=0, pady=1)
        win30.grid(row=0, column=0, padx=0, pady=1)
        win31.grid(row=0, column=1, padx=0, pady=1)

        gcolor = 'black'
        fg0 = Figure(figsize=(2.30, 2.0), dpi=110, layout="tight")
        fg0.set_facecolor(gcolor)
        cv0 = FigureCanvasTkAgg(fg0, master=win20)
        cv0.draw()
        cv0.get_tk_widget().pack()

        fg1 = Figure(figsize=(2.30, 2.0), dpi=110, layout="tight")
        fg1.set_facecolor(gcolor)
        cv1 = FigureCanvasTkAgg(fg1, master=win21)
        cv1.draw()
        cv1.get_tk_widget().pack()

        fg2 = Figure(figsize=(7.3, 2.1), dpi=110, layout="tight")
        fg2.set_facecolor(gcolor)
        cv2 = FigureCanvasTkAgg(fg2, master=win30)
        cv2.draw()
        cv2.get_tk_widget().pack()

        fg3 = Figure(figsize=(4.35, 2.1), dpi=110, layout="tight")
        fg3.set_facecolor(gcolor)
        cv3 = FigureCanvasTkAgg(fg3, master=win31)
        cv3.draw()
        cv3.get_tk_widget().pack()

        for i in range(0, 24):
            for j in range(0, 10):
                if i in (0, 1, 2):
                    if i == 2:
                        if j == 8:
                            s_invertir = StringVar(win1, '20')
                            mxp[i][j] = ttk.Entry(win1, width=7, font=10, justify="right", textvariable=s_invertir)
                            mxp[i][j].grid(row=i, column=j)
                        if j == 9:
                            mxp[i][j] = ttk.Button(win1, text="Inversión", style='TLabel', width=10)
                            mxp[i][j].grid(row=i, column=j)
                    else:
                        mxp[i][j] = ttk.Button(win1, text=' ', width=10, style='TLabel')
                        mxp[i][j].grid(row=i, column=j)
                if i == 4:
                    cryptos.titulos(win1, i)
                if i > 4:
                    cryptos.lineas(win1, i, j)
                    lfg = "TLabel" if i == 5 else ("TLabel" if i % 2 == 0 else "I.TLabel")
                    mxp[i][j] = ttk.Button(win1, text=" ", width=14, style=lfg)
                    mxp[i][j].grid(row=i, column=j)
        """
        @ reescribe header del panel  
        """
        k, i, tdpyl = 2, 2, 0
        for key, value in board.items():
            if k == 2:
                mxp[1][0] = ttk.Label(win1, text='{:>20f}'.format(tdpyl), font=26, width=17)
                mxp[1][0].grid(row=0, column=0, rowspan=2, columnspan=2)
            if key in ('Nav', 'UnP&l', 'Dividendos', 'Cash'):
                mxp[0][k] = ttk.Label(win1, text='{:>10}'.format(key))
                mxp[0][k].grid(row=0, column=k + 0)
                mxp[0][k + 1] = ttk.Label(win1, text='{:>10.2f}'.format(value))
                mxp[0][k + 1].grid(row=0, column=k + 1)
                k += 2
            if key in ('UnProfit', '%Margen', 'PB/año'):
                mxp[1][i] = ttk.Label(win1, text='{:>10}'.format(key))
                mxp[1][i].grid(row=1, column=i + 0)
                mxp[1][i + 1] = ttk.Label(win1, text='{:>10.2f}'.format(board[key]))
                mxp[1][i + 1].grid(row=1, column=i + 1)
                i += 2

        return mxp

    def update_cryptos(self):
        """
        @return:
        """
        global board, tdpyl, tcosb, tmkv, tgyp, tunp, tdiv, s_invertir, t_inicio
        xdict = json.loads('{"unrealizedpnl": "ASC"}')
        orden = list(xdict.keys())
        orden.append(xdict[orden[0]])
        p_invertir = Decimal(s_invertir.get())
        positions = create_p_crypto(orden, p_invertir)

        tdpyl, tcosb, tmkv, tgyp, tunp, tdiv, k = 0, 0, 0, 0, 0, 0, 0
        for i in range(len(positions)):
            if i < 25:
                k = 6 + i
                display_crypto(k, pkey=positions[i], writelinea=True)

        j = k
        k, i, = 3, 3
        for key, value in board.items():
            if key in ('Nav', 'UnP&l', 'Dividendos', 'Cash'):
                mxp[0][k].config(text='{:>10.2f}'.format(value))
                k += 2
            if key in ('UnProfit', '%Margen', 'PB/año'):
                if board['Cash'] < 0:
                    board['%Margen'] = abs(board['Cash']) / board['costobase']
                if (board['UnProfit'] + board['Dividendos']) > 0:
                    board['PB/año'] = (board['Nav'] + abs(board['UnP&l'])) / (board['UnProfit'] + board['Dividendos'])
                mxp[1][i].config(text='{:>10.2f}'.format(board[key]))
                i += 2

        wboard['Crypto'] = board

        if i > 0:
            for i in range(j + 1, 24):
                display_crypto(i, writelinea=False)

        self.after(5000, self.update_cryptos)
        if time.time() - t_inicio > 60:
            panel_graficos(fg0, cv0, fg1, cv1, fg2, cv2, fg3, cv3)
            t_inicio = time.time()

        return


def display_crypto(i, pkey=None, writelinea=False):
    global mxp, board, tdpyl, tcosb, tmkv, tgyp, tunp, tdiv, tdebit

    lfg = "TLabel-" if i == 5 else ("TLabel" if i % 2 == 0 else "I.TLabel")
    if writelinea:

        mkv = pkey['mktPrice'] * pkey['position']
        chg = pkey['pchange'] * pkey['position']
        tdpyl += chg
        roi = pkey['unrealizedpnl'] / pkey['costobase'] if pkey['costobase'] > 0 else 0

        cbg = display_red_green(chg, i)
        rbg = display_red_green(pkey['unrealizedpnl'], i)
        gbg = display_red_green(tdpyl)
        ibg = display_azul(20, i)

        mxp[1][0].config(text='{:>20.0f}'.format(tdpyl), style=gbg, font=16)
        mxp[i][0].config(text=' {:<10}'.format(pkey['ticket']), style=lfg, command=lambda: cryptos.fila(i))
        mxp[i][1].config(text='{:>11.0f}'.format(chg), style=cbg)
        mxp[i][2].config(text='{:>13.4f}'.format(pkey['position']), style=lfg)
        mxp[i][3].config(text='{:>13.6f}'.format(pkey['mrkprice']), style=lfg)
        mxp[i][4].config(text='{:>13.2f}'.format(pkey['costobase']), style=lfg)
        mxp[i][5].config(text='{:>13.2f}'.format(mkv), style=lfg)
        mxp[i][6].config(text='{:>13.2f}'.format(pkey['unrealizedpnl']), style=rbg)
        mxp[i][7].config(text='{:>11.1%}'.format(roi), style=rbg)
        mxp[i][8].config(text='{:>13.2f}'.format(pkey['gypp']), style=ibg)
        mxp[i][9].config(text='({:>5.1f})({:>5.1f})'.format(pkey['ixVp'] * 100, pkey['ixGp'] * 100), style=ibg)

        tmkv += mkv
        tgyp += pkey['unrealizedpnl']
        tdiv += pkey['dividendo']
        tunp = tunp if pkey['unrealizedpnl'] < 0 else tunp + pkey['unrealizedpnl']
        tcosb += pkey['costobase']

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
    """
    @ display liena de totales
    """
    pgyp = (tmkv - tcosb) / tcosb if tcosb > 0 else 0
    lfg = "TLabel"
    mxp[5][4].config(text='{:>13.2f}'.format(tcosb), style=lfg)
    mxp[5][5].config(text='{:>13.2f}'.format(tmkv), style=lfg)
    mxp[5][6].config(text='{:>13.2f}'.format(tgyp), style=lfg)
    mxp[5][7].config(text='{:>11.1%}'.format(pgyp), style=lfg)
    board['Dividendos'] = tdiv
    board['costobase'] = tcosb
    board['UnProfit'] = tunp
    board['UnP&l'] = tgyp
    board['Cash'] = -tdebit
    board['Nav'] = tmkv


def create_p_crypto(orden, p_invertir) -> dict:
    cartera = select_inversion(tipoin='Crypto')
    for pkey in cartera:

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


def thr_datos_crypto(itrue):
    """
    @return: Thread que construye datos de graficos y actualiza tabla booktrading
    """
    global wperf

    try:
        while not itrue.is_set():

            (asset, xlist) = dict_peso_positions(vehiculo='Crypto')
            wperf = performa_asset(account='B0000001', vehiculo='Crypto', tipo='Crypto')


            actualiza_booktrading_performa(xlist=xlist, asset=asset, account='B0000001', vehiculo='Crypto')

            #
            # evaluar que entrega performa_asset  y actualizar
            # wperf = performa_asset(account='B0000001', vehiculo='Crypto', tipo='Crypto')

            diaria_book_performance(account='B0000001', vehiculo='Crypto', asset=xlist)

            time.sleep(15)

    except threading.ThreadError as error:
        print("[Thread:: thr_datos_crypto()]: {}".format(error))

    return


def thr_position_crypto(itrue):
    """
    @return: Tread que construye dict() position y actualiza tabla inversiones
    """
    global tdebit
    try:
        wdebit, cartera = 0, dict()
        while not itrue.is_set():
            positions, simbolos = wallet_snapshot()
            if len(positions) > 0:

                (cartera, wdebit) = debit_wallet(positions=positions)
                if is_none(cartera):
                    update_inversion(positions=positions, tipo='Crypto', account='B0000001')
                    time.sleep(2.0)
                else:
                    tdebit = wdebit
                    update_inversion(positions=cartera, tipo='Crypto', account='B0000001')

    except threading.ThreadError as error:
        print("[Thread error]: {}".format(error))

    return


def panel_graficos(fg0=None, cv0=None, fg1=None, cv1=None, fg2=None, cv2=None, fg3=None, cv3=None):
    global board, wperf

    """
    @ llenado de estructuras para los graficos del panel
    """
    cartera = select_inversion(tipoin='Crypto')
    wvals, wlabe, wrati, wcost, wpeso, wdebi, wprof, parm = list(), list(), list(), list(), list(), list(), list(), {}
    tcos, tpro, tunr = 0, 0, 0
    ocos, opro, ounr, odeu, opes = 0, 0, 0, 0, 0

    i = 0
    orden = ["unrealizedpnl", "DES"]
    cartera = sort_positions(cartera, orden)

    for key in cartera:
        pobj = 0 if key['unrealizedpnl'] < 0 else float(key['unrealizedpnl'])
        tcos += float(key['costobase'])
        tunr += float(key['unrealizedpnl'])
        tpro += pobj

        if i < 4:
            wvals.append([float(key['costobase']), pobj])
            wcost.append(float(key['costobase']))
            wrati.append(float(key['unrealizedpnl']))
            wprof.append(0 if float(key['unrealizedpnl']) < 0 else float(key['unrealizedpnl']))
            wdebi.append(float(key['deuda']))
            ticket = key['ticket'].replace("USDT", "")
            wlabe.append(ticket)
            wpeso.append('{:>2.0%} {}'.format(key['peso'], ticket))
        else:
            ocos += float(key['costobase'])
            ounr += float(key['unrealizedpnl'])
            odeu += float(key['deuda'])
            opes += key['peso']
        i += 1

    if i > 4:
        wcost.append(ocos)
        wrati.append(ounr)
        wdebi.append(odeu)
        wlabe.append('Otros')
        wpeso.append('{:>2.0%} {}'.format(opes, 'Otros'))
    wdata = {'Inversión': tcos, 'UnProfit': tpro,  'UnP&l': tunr, 'Cash': - sum(wdebi)}
    parm.update({'titulo': 'ROI Crypto'})
    parm.update({'aspect': 0.50})
    performa(fg0, cv0, wdata, parm)

    xdata = {'data': wcost, 'peso': wpeso}
    asignacion(fg1, cv1, xdata, 'Asignación')

    bdata = {'series': {'Debit': wdebi, 'Profit': wrati, 'Inversión': wcost}, 'label': wlabe}
    distribucion(fg3, cv3, bdata, 'Distribución de Activos')

    # wperf proviene de Dataframe construido por select_performa_inversion('Crypto')
    dlabl = {'BTC': 'BTC++index', '++ index': "++ Portafolio", 'Value': 'Value Market', 'Costo': 'Cost basic',
             "legend": 'outside upper left', "aspect": 0.21}
    performa_portafolio(fg2, cv2, wperf, dlabl, 'Performance (acumulativo) portafolio :: Crypto')


if __name__ == '__main__':
    win = tk.Tk()
    dimension = "%dx%d+0+0" % (dw, dh)
    win.geometry(dimension)
    win.config(bg="black")

    style = style_app(main=win)
    itrue = threading.Event()

    dpn = ttk.Frame(win, style="TFrame", width=df, height=700)
    dpn.grid(pady=40, padx=5)

    itrue = threading.Event()
    thr_c1 = Thread(target=thr_datos_crypto, name='datos_crypto', args=(itrue,))
    thr_c1.start()

    thr_c0 = Thread(target=thr_position_crypto, name='position_crypto', args=(itrue,))
    thr_c0.start()

    frame_cryp = cryptos(master=dpn)
    frame_cryp.pack()
    frame_cryp.mainloop()
    itrue.clear()

    win.mainloop()
