from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from api_chart import *
from api_io_file import *
from api_io_file import cagar_archivo

global tree, extract


def update_plan(account=None, condicion=None):
    """
    @param account: id de cuenta de inversión
    @param condicion: si para cierre de fiscal
    @return: actualiza tabla trazaplan y plan desde estrategia
    """
    # ex_ant = select_extracto(account=account, extract='last')
    ex_year = select_extracto(account=account, extract='fiscal')
    btotal = (ex_year[0]['sum(dividendos)'] + ex_year[0]['sum(crecimiento)'] + ex_year[0]['sum(idevengo)'] -
              (ex_year[0]['sum(perdidas)'] + ex_year[0]['sum(fee)'] +
               ex_year[0]['sum(comisiones)'] + ex_year[0]['sum(fee)'] +
               ex_year[0]['sum(tax)'] + ex_year[0]['sum(imargen)']))

    re_total = 0 if ex_year[0]['avg(cierreanterior)'] == 0 else btotal / ex_year[0]['avg(cierreanterior)']

    update_trazaplan(idcuenta=account, costobase=t_total['IBKs']['total'],
                     inversion=t_total['all']['total'], div=ex_year[0]['sum(dividendos)'],
                     rend=re_total, crec=btotal, condicion=condicion)


class estrategy(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.widgets_estrategia()
        self.update_estrategia()
        self.config(bg="black")

    global tree, extract, mes, items, e, pextrct
    mes = ['Null', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

    def widgets_estrategia(self):
        global tree, extract, fg, cv, pag, c

        pag = 1

        def add():
            global tree, extract, mes, items
            hoy = datetime.now()
            sesion = select_sesion(hoy, accion="select", vehiculo='Stock')
            d_extract, ilog = cagar_archivo(account=sesion['idcuenta'], titulo='Activity Statement', tipo='csv')
            if ilog:

                a_extracto = select_extracto(account=sesion['idcuenta'], extract='last')
                if a_extracto[0]['extracto'] < d_extract['extracto'].date():
                    insert_extracto(account=sesion['idcuenta'], values=d_extract)
                    #
                    # actualiza tabla de plan cuando cierra el año fiscal
                    if d_extract['extracto'].month == sesion['fiscalYear'].month:
                        update_plan(account=sesion['idcuenta'], condicion='Cumplido')

                    self.update_estrategia()
                    messagebox.showinfo("Add", "Successfully load Extracto.csv")
                else:
                    msj = ('No puede agregar nuevamente el Extracto [' + d_extract['extracto'].strftime("%b-%Y") +
                           '], existe en el sistema')
                    messagebox.showinfo("Error", msj)

        def new_pagina(selec):
            global pag

            pag += selec
            pag = 1 if pag > 2 else 2 if pag == 0 else pag
            panel_graficos(pag, xestrategia, d_extract)

        def set_cell_value(event):
            column, row = 0, 0
            item_text = ' '
            for item in tree.selection():
                item_text = tree.item(item, "values")
                column = tree.identify_column(event.x)
                row = tree.identify_row(event.y)
                print('row=', row, ' colum=', column)
            cn = int(str(column).replace('#', ''))
            rn = int(str(row).replace('I', ''))
            print('cn=', cn, 'rn=', rn, item_text[cn - 1])
            if cn in (1, 6):
                entryedit = Text(tree, width=8, height=1)
                entryedit.place(x=70 + (cn - 1) * 200, y=6 + rn * 20)

            def saveedit():
                tree.set(item, column=column, value=entryedit.get(0.0, "end"))
                entryedit.destroy()
                okb.destroy()

            okb = ttk.Button(tree, text='ok', width=2, command=saveedit)
            okb.place(x=140 + (cn - 1) * 200, y=2 + rn * 20)

        win1 = tk.Frame(self, bg='black')
        win2 = tk.Frame(self, bg='black')
        win3 = tk.Frame(self, bg='black')

        win20 = tk.Frame(win2, bg='black')
        win21 = tk.Frame(win2, bg='black', relief='groove', bd=2)
        win30 = tk.Frame(win3, bg='black')
        win31 = tk.Frame(win3, bg='black')

        win1.grid(column=0, row=0, padx=2)
        win2.grid(column=1, row=0, padx=1)
        win3.grid(column=0, row=1, padx=1, columnspan=2)

        win20.grid(column=0, row=1, pady=0, sticky=(N, S, E, W))
        win21.grid(column=0, row=0, pady=2)
        win30.grid(column=0, row=0, pady=2, sticky=(N, S, E, W))
        win31.grid(column=0, row=1, pady=2, sticky=(N, S, E, W))
        #
        # widgets para estrategia
        #
        ctree = ["est", "last", "peso", "div", "Obj", "fair", "ret"]
        tree = ttk.Treeview(win1, columns=ctree, height=15, style='TFrame')
        tree.grid(column=0, row=0, padx=2, pady=0)
        tree.column(ctree[0], width=70, anchor='e')
        tree.column(ctree[1], width=90, anchor='e')
        tree.column(ctree[2], width=50, anchor='e')
        tree.column(ctree[3], width=70, anchor='e')
        tree.column(ctree[4], width=70, anchor='e')
        tree.column(ctree[5], width=70, anchor='e')
        tree.column(ctree[6], width=70, anchor='e')
        tree.heading("#0", text="Descripción/Empresa")
        tree.heading("est", text="Estrategia")
        tree.heading("last", text="Costo")
        tree.heading("div", text="Dividendo")
        tree.heading("peso", text="Peso")
        tree.heading("Obj", text="Valor 1año")
        tree.heading("fair", text="Valor fair")
        tree.heading("ret", text="Performa")
        tree.bind('<Double-1>', set_cell_value)

        #
        # widgets para chart
        #
        gcolor = 'black'
        fg = Figure(figsize=(5.3, 2.7), dpi=110, layout="tight")
        ax = fg.add_subplot()
        fg.set_facecolor(gcolor)
        cv = FigureCanvasTkAgg(fg, master=win21)
        cv.draw()
        cv.get_tk_widget().pack()

        l_arrow_tk, tmp = get_imagen(ix=102, ancho=18, largo=18)
        r_arrow_tk, tmp = get_imagen(ix=103, ancho=18, largo=18)

        b_left = ttk.Button(win20, image=l_arrow_tk,  command=lambda: new_pagina(-1))
        b_right = ttk.Button(win20, image=r_arrow_tk, command=lambda: new_pagina(+1))
        b_left.imagen = l_arrow_tk
        b_right.imagen = r_arrow_tk

        b_left.grid(column=0, row=0, sticky=E)
        b_right.grid(column=1, row=0, sticky=E)

        #
        # widgets para mostrar Extractos
        #
        cextr = ["Depo", "Reti", "Grou", "Divi", "Perd", "Fee", "Comi",
                 "Tax", "Nav", "Cost", "deve", "marg", "rend", "pb"]
        titulo = ["Extracto", "Depositos", "Retiros", "Crecimiento", "Dividendos",
                  "Perdidas", "Fee", "Comisiones", "Tax", "Value", "Costo Base",
                  "Devengado", "Costo Margen", "%Groud.Value", "Ren. Total"]

        extract = ttk.Treeview(win31, columns=cextr, height=15, style='TFrame')
        extract.grid(row=0, column=0, padx=1)
        extract.column("#0",      width=90, anchor='e')
        extract.column(cextr[0],  width=80, anchor='e')
        extract.column(cextr[1],  width=80, anchor='e')
        extract.column(cextr[2],  width=100, anchor='e')
        extract.column(cextr[3],  width=80, anchor='e')
        extract.column(cextr[4],  width=80, anchor='e')
        extract.column(cextr[5],  width=80, anchor='e')
        extract.column(cextr[6],  width=80, anchor='e')
        extract.column(cextr[7],  width=80, anchor='e')
        extract.column(cextr[8],  width=80, anchor='e')
        extract.column(cextr[9],  width=80, anchor='e')
        extract.column(cextr[10], width=80, anchor='e')
        extract.column(cextr[11], width=80, anchor='e')
        extract.column(cextr[12], width=100, anchor='e')
        extract.column(cextr[13], width=80, anchor='e')
        extract.heading("#0",   text=titulo[0])
        extract.heading("Depo", text=titulo[1])
        extract.heading("Reti", text=titulo[2])
        extract.heading("Grou", text=titulo[3])
        extract.heading("Divi", text=titulo[4])
        extract.heading("Perd", text=titulo[5])
        extract.heading("Fee",  text=titulo[6])
        extract.heading("Comi", text=titulo[7])
        extract.heading("Tax",  text=titulo[8])
        extract.heading("Nav",  text=titulo[9])
        extract.heading("Cost", text=titulo[10])
        extract.heading("deve",  text=titulo[11])
        extract.heading("marg", text=titulo[12])
        extract.heading("rend", text=titulo[13])
        extract.heading("pb",   text=titulo[14])

        e = [[None] * 1 for _ in range(len(titulo))]

        uextract = select_extracto(account=apilocal['account'], extract='last')
        fini = proximo_extracto(uextract[0]['extracto'])
        fec = tk.StringVar(value=fini)
        validar_key = self.register(entry_numeric)

        f_load_tk, tmp = get_imagen(ix=300, ancho=18, largo=18)
        f_year_tk, tmp = get_imagen(ix=302, ancho=18, largo=18)
        c_year_tk, tmp = get_imagen(ix=301, ancho=18, largo=18)

        e_stock_tk, tmp = get_imagen(ix=303, ancho=18, largo=18)
        e_crypto_tk, tmp = get_imagen(ix=304, ancho=18, largo=18)

        b_load = ttk.Button(win30, image=f_load_tk, command=add)
        b_load.imagen = f_load_tk
        b_year = ttk.Button(win30, image=c_year_tk)
        b_year.imagen = c_year_tk
        f_year = ttk.Button(win30, image=f_year_tk)
        f_year.imagen = f_year_tk

        b_stock = ttk.Button(win30, image=e_stock_tk)
        b_stock.imagen = e_stock_tk
        b_crypto = ttk.Button(win30, image=e_crypto_tk)
        b_crypto.imagen = e_crypto_tk

        b_stock.grid(column=0, row=0, sticky=E)
        b_crypto.grid(column=1, row=0, sticky=E)

        b_year.grid(column=3, row=0, sticky=E)
        f_year.grid(column=4, row=0, sticky=E)
        b_load.grid(column=5, row=0, sticky=E)


        return tree, extract

    def update_estrategia(self):
        global tree, extract, mes, items, pextrct, win2, fg, t_total, Textract, d_extract, ix, pag, xestrategia

        val = [[0] * 1 for _ in range(15)]
        #
        # carga widgets de estrategias
        #

        xestrategia = read_estrategia()
        t_total, x = dict(), dict()
        x['total']: float = 0
        x['div']: float = 0
        x['peso']: float = 0
        t_total['all'] = x.copy()
        t_total['IBKs'] = x.copy()
        t_total['Crypto'] = x.copy()

        tree.delete(*tree.get_children())

        for keys in xestrategia:
            linea = xestrategia[keys]
            vehiculo_total('all', linea, t_total)

        all = tree.insert("", tk.END, text='Total Inversiones:', values=('{:>10}'.format(' '),
                                                                         '{:>10.2f}'.format(t_total['all']['total']),
                                                                         '{:>2.1%}'.format(t_total['all']['peso']),
                                                                         '{:>10.2f}'.format(t_total['all']['div']),
                                                                         "", ""))
        tree.item(all, open=True)

        cargar_stock(xestrategia, tree, all, t_total)
        cargar_crypto(xestrategia, tree, all, t_total)
        """
            actualiza Plan y trazaplan a partir de la estrategia
        """
        update_plan(account=apilocal['account'], condicion=None)

        Textract, d_extract, ix = extractos()
        panel_graficos(pag, xestrategia, d_extract)

        self.after(apilocal['elapse estrategia'], self.update_estrategia)
        return tree, extract, Textract, d_extract, ix


def vehiculo_total(vehiculo, linea, t_total):
    sstck: float = 0
    ssdiv: float = 0
    sspes: float = 0

    for i in linea:
        estr = None
        if vehiculo == i:
            for estr in linea[vehiculo]:
                pass
            activos = linea[vehiculo][estr]
            for j in range(0, len(activos)):
                ix = list(activos[j].keys())
                sstck += activos[j][ix[0]]
                ssdiv += activos[j]['Dividendo']

            t_total[vehiculo]['total'] += sstck
            t_total[vehiculo]['div'] += ssdiv
            t_total[vehiculo]['peso'] += sspes
        if vehiculo == 'all':
            for estr in linea[i]:
                activos = linea[i][estr]
                for j in range(0, len(activos)):
                    ix = list(activos[j].keys())
                    sstck += activos[j][ix[0]]
                    ssdiv += activos[j]['Dividendo']

                t_total[vehiculo]['total'] += sstck
                t_total[vehiculo]['div'] += ssdiv
                t_total[vehiculo]['peso'] += sspes


def cargar_stock(xestrategia, tree, all, t_total):

    for keys in xestrategia:
        linea = xestrategia[keys]
        vehiculo_total('IBKs', linea, t_total)

    itemt = tree.insert(all, tk.END, text='Renta Variable(Stock)', values=('{:>10}'.format(' '),
                                                                            '{:>10.2f}'.format(t_total['IBKs']['total']),
                                                                            '{:>2.1%}'.format(t_total['IBKs']['peso']),
                                                                            '{:>10.2f}'.format(t_total['IBKs']['div']),
                                                                            "", ""))
    tree.item(itemt, open=True)
    #
    # recorre los activos de la estractegia y los agrega al arbol
    # en detalle
    #
    tgen = t_total['IBKs']['total']
    tadiv = t_total['IBKs']['div']

    for keys in xestrategia:
        linea = xestrategia[keys]
        for i in linea:
            estr = None
            if 'IBKs' == i:
                for estr in linea['IBKs']:
                    pass
                activos = linea['IBKs'][estr]

                tpeso = t_total['IBKs']['total'] / tgen
                tadiv = t_total['IBKs']['div']
                #
                # insert nivel estrategia
                #
                eitems = tree.insert(itemt, tk.END, text='{:<20}'.format(estr if not is_none(estr) else 'Pendiente'),
                                                 values=('{:>10}'.format(' '),
                                                         '{:>10.2f}'.format(t_total['IBKs']['total']),
                                                         '{:>2.1%}'.format(tpeso),
                                                         '{:>10.2f}'.format(tadiv),
                                                         '{:>10.2f}'.format(0.00),
                                                         '{:>10.2f}'.format(0.00)))
                stck, div = 0, 0
                for j in range(0, len(activos)):
                    ix = list(activos[j].keys())
                    stck += activos[j][ix[0]]
                    div += activos[j]['Dividendo']
                    est = activos[j]['Estrategia']
                    tpeso = stck / t_total['IBKs']['total']
                    emp = ix[0]
                    tree.insert(eitems, tk.END, text=emp, open=True,
                                               values=('{:<10}'.format(est),
                                                       '{:10.2f}'.format(activos[j][ix[0]]),
                                                       '{:>2.1%}'.format(tpeso),
                                                       '{:>10.2f}'.format(activos[j]['Dividendo']),
                                                       '{:>10.2f}'.format(activos[j]['Objetivo']),
                                                       '{:>10.2f}'.format(0.00)))

                item_values = tree.item(eitems)
                item_values['values'] = (" ", '{:10.2f}'.format(stck), '{:>2.1%}'.format(stck/t_total['IBKs']['total']),
                                              '{:10.2f}'.format(div), '')
                tree.item(eitems, **item_values)

    return tree


def cargar_crypto(xestrategia, tree, all, t_total):
    for keys in xestrategia:
        linea = xestrategia[keys]
        vehiculo_total('Crypto', linea, t_total)

    itemt = tree.insert(all, tk.END, text='CryptoActivos',
                            values=('{:>10}'.format(' '),
                                    '{:>10.2f}'.format(t_total['Crypto']['total']),
                                    '{:>2.1%}'.format(t_total['Crypto']['peso']),
                                    '{:>10.2f}'.format(t_total['Crypto']['div']), "", ""))
    tree.item(itemt, open=True)
    #
    # recorre los activos de la estractegia y los agrega al arbol
    # en detalle
    #
    tgen = t_total['Crypto']['total']
    tadiv = t_total['Crypto']['div']

    for keys in xestrategia:
        linea = xestrategia[keys]
        for i in linea:
            estr = ' '
            if 'Crypto' == i:
                for estr in linea['Crypto']:
                    pass
                activos = linea['Crypto'][estr]

                tpeso = t_total['Crypto']['total'] / tgen
                tadiv = t_total['Crypto']['div']
                """
                @ insert nivel estrategia
                """
                eitems = tree.insert(itemt, tk.END, text='{:<20}'.format(estr if not is_none(estr) else 'Pendiente'),
                                                 values=('{:>10}'.format(' '),
                                                         '{:>10.2f}'.format(t_total['Crypto']['total']),
                                                         '{:>2.1%}'.format(tpeso),
                                                         '{:>10.2f}'.format(tadiv),
                                                         '{:>10.2f}'.format(0.00),
                                                         '{:>10.2f}'.format(0.00)))
                stck, div = 0, 0
                for j in range(0, len(activos)):
                    ix = list(activos[j].keys())
                    stck += activos[j][ix[0]]
                    div += activos[j]['Dividendo']
                    est = activos[j]['Estrategia']
                    tpeso = activos[j][ix[0]] / tgen
                    emp = ix[0]
                    tree.insert(eitems, tk.END, text=emp, open=True,
                                               values=('{:<10}'.format(est),
                                                       '{:10.2f}'.format(activos[j][ix[0]]),
                                                       '{:>2.1%}'.format(tpeso),
                                                       '{:>10.2f}'.format(activos[j]['Dividendo']),
                                                       '{:>10.2f}'.format(activos[j]['Objetivo']),
                                                       '{:>10.2f}'.format(0.00)))

                item_values = tree.item(eitems)
                item_values['values'] = (" ", '{:10.2f}'.format(stck),
                                              '{:>2.1%}'.format(stck/t_total['Crypto']['total']),
                                              '{:10.2f}'.format(div), '')
                tree.item(eitems, **item_values)


def cargar_crowdfunding(con_string: object, xestrategia: object, tree: object) -> object:
    t_total = dict()
    t_total['IBKs'] = {'total': 0.00, 'div': 0.00, 'peso': 0.00}

    itemt = tree.insert("", tk.END, text='crowdfunding',
                            values=('{:>10}'.format(' '),
                                    '{:>10.2f}'.format(t_total['IBKs']['total']),
                                    '{:>2.1%}'.format(t_total['IBKs']['peso']),
                                    '{:>10.2f}'.format(t_total['IBKs']['div']),
                                    '{:>10.2f}'.format(0.00),
                                    '{:>10.2f}'.format(0.00),))


def extractos() -> dict:
    global tree, extract, mes, items, pextrct
    x = dict()
    x['Depo']: float = 0
    x['Reti']: float = 0
    x['Grou']: float = 0
    x['Divi']: float = 0
    x['Perd']: float = 0
    x['Fee']: float = 0
    x['Comi']: float = 0
    x['Tax']: float = 0
    x['Nav']: float = 0
    x['Cost']: float = 0
    x['deve']: float = 0
    x['marg']: float = 0
    x['rend']: float = 0
    x['perf']: float = 0
    x['pb']: float = 0

    # GWI001
    cursor = connect_dbase("select.extractos", False).cursor()
    sql = '''SELECT * FROM extractos ORDER BY extracto DESC;'''

    cursor.execute(sql)
    ix = [column[0] for column in cursor.description]
    xcur = cursor.fetchall()
    # xcur = select_extracto(account=apilocal['account'], extract='select*')

    extract.delete(*extract.get_children())
    totales = dict()

    if xcur:
        totales['resu'] = x.copy()
        resu = extract.insert("", tk.END, text='{:<15}'.format('Resumen'), values=(
                                '{:10.2f}'.format(0), '{:10.2f}'.format(0), '{:10.2f}'.format(0),
                                '{:10.2f}'.format(0), '{:10.2f}'.format(0), '{:10.2f}'.format(0),
                                '{:10.2f}'.format(0), '{:10.2f}'.format(0), '', '',
                                '{:10.2f}'.format(0), '{:10.2f}'.format(0), '{:10.2%}'.format(0)))
        extract.item(resu, open=True)

        i = 0
        keys = xcur[i]
        hasta = len(xcur) - 1
        pmes = keys[ix.index('extracto')].month + 1 if keys[ix.index('extracto')].month < 12 else 1
        pyear = keys[ix.index('extracto')].year + 1 if pmes == 1 else keys[ix.index('extracto')].year
        pextrct = ultimo_dia_mes(pyear, pmes)

        a = 0
        while i < hasta:
            year = str(keys[ix.index('extracto')].year)
            totales[year] = x.copy()
            totales[year]['ayear'] = keys[ix.index("cierreanterior")]
            totales[year]['Nav'] = keys[ix.index("navcierre")]
            totales[year]['Cost'] = keys[ix.index("costobase")]

            items = extract.insert(resu, tk.END, text='{:<15}'.format(year), values=(
                                            '{:10.2f}'.format(0), '{:10.2f}'.format(0), '{:10.2f}'.format(0),
                                            '{:10.2f}'.format(0), '{:10.2f}'.format(0), '{:10.2f}'.format(0),
                                            '{:10.2f}'.format(0), '{:10.2f}'.format(0), '{:10.2f}'.format(0),
                                            '{:10.2f}'.format(0), '{:10.2f}'.format(0), '{:10.2%}'.format(0),
                                            '{:10.2f}'.format(0)))
            """
            # open del año mas reciente
            """
            if i == 0:
                extract.item(items, open=True)

            m = 0
            while str(keys[ix.index('extracto')].year) == year:
                extr = mes[keys[ix.index('extracto')].month]
                if keys[ix.index("cierreanterior")] > 0:
                    # GWI001
                    rend = (keys[ix.index("navcierre")] - keys[ix.index("cierreanterior")])
                    perf = (keys[ix.index("crecimiento")] + keys[ix.index("dividendos")] + keys[ix.index("idevengo")] -
                            (keys[ix.index("perdidas")] + keys[ix.index("fee")] +
                             keys[ix.index("comisiones")] + keys[ix.index("tax")] + keys[ix.index("imargen")]))

                    rend = rend / keys[ix.index("cierreanterior")]
                    perf = perf / keys[ix.index("cierreanterior")]
                else:
                    rend: float = 0
                    perf: float = 0

                extract.insert(items, tk.END, text='{:<15}'.format(extr), values=(
                                            '{:10.2f}'.format(keys[ix.index("depositos")]),
                                            '{:10.2f}'.format(keys[ix.index("retiros")]),
                                            '{:10.2f}'.format(keys[ix.index("crecimiento")]),
                                            '{:10.2f}'.format(keys[ix.index("dividendos")]),
                                            '{:10.2f}'.format(keys[ix.index("perdidas")]),
                                            '{:10.2f}'.format(keys[ix.index("fee")]),
                                            '{:10.2f}'.format(keys[ix.index("comisiones")]),
                                            '{:10.2f}'.format(keys[ix.index("tax")]),
                                            '{:10.2f}'.format(keys[ix.index("navcierre")]),
                                            '{:10.2f}'.format(keys[ix.index("costobase")]),
                                            '{:10.2f}'.format(keys[ix.index("idevengo")]),
                                            '{:10.2f}'.format(keys[ix.index("imargen")]),
                                            '{:10.2%}'.format(rend),
                                            '{:10.2%}'.format(perf)))

                totales[year]['Depo'] += keys[ix.index("depositos")]
                totales[year]['Reti'] += keys[ix.index("retiros")]
                totales[year]['Grou'] += keys[ix.index("crecimiento")]
                totales[year]['Divi'] += keys[ix.index("dividendos")]
                totales[year]['Perd'] += keys[ix.index("perdidas")]
                totales[year]['Fee'] += keys[ix.index("fee")]
                totales[year]['Comi'] += keys[ix.index("comisiones")]
                totales[year]['Tax'] += keys[ix.index("tax")]
                totales[year]['deve'] += keys[ix.index("idevengo")]
                totales[year]['marg'] += keys[ix.index("imargen")]
                totales[year]['rend'] += rend
                totales[year]['perf'] += perf

                i += 1
                m += 1
                if i > hasta:
                    break
                keys = xcur[i]

            eps = totales[year]['Grou'] + totales[year]['Divi'] + totales[year]['deve']
            eps = eps - (totales[year]['Perd'] + totales[year]['Fee'] + totales[year]['Comi'] +
                         totales[year]['Tax'] + totales[year]['marg'])
            totales[year]['pb'] = totales[year]['Cost'] / eps
            a += 1
            extract.item(items, values=('{:10.2f}'.format(totales[year]['Depo']),
                                        '{:10.2f}'.format(totales[year]['Reti']),
                                        '{:10.2f}'.format(totales[year]['Grou']),
                                        '{:10.2f}'.format(totales[year]['Divi']),
                                        '{:10.2f}'.format(totales[year]['Perd']),
                                        '{:10.2f}'.format(totales[year]['Fee']),
                                        '{:10.2f}'.format(totales[year]['Comi']),
                                        '{:10.2f}'.format(totales[year]['Tax']),
                                        '{:10.2f}'.format(totales[year]['Nav']),
                                        '{:10.2f}'.format(totales[year]['Cost']),
                                        '{:10.2f}'.format(totales[year]['deve']),
                                        '{:10.2f}'.format(totales[year]['marg']),
                                        '{:10.2%}'.format(totales[year]['rend']/m),
                                        '{:10.2f}'.format(totales[year]['pb'])))

            totales['resu']['Depo'] += totales[year]['Depo']
            totales['resu']['Reti'] += totales[year]['Reti']
            totales['resu']['Grou'] += totales[year]['Grou']
            totales['resu']['Divi'] += totales[year]['Divi']
            totales['resu']['Perd'] += totales[year]['Perd']
            totales['resu']['Fee'] += totales[year]['Fee']
            totales['resu']['Comi'] += totales[year]['Comi']
            totales['resu']['Tax'] += totales[year]['Tax']
            totales['resu']['deve'] += totales[year]['deve']
            totales['resu']['marg'] += totales[year]['marg']
            totales['resu']['rend'] += totales[year]['rend']
            totales['resu']['pb'] += totales[year]['pb']

        totales['resu']['rend'] = totales['resu']['rend']/i
        totales['resu']['pb'] = totales['resu']['pb']/a
        extract.item(resu, values=('{:10.2f}'.format(totales['resu']['Depo']),
                                     '{:10.2f}'.format(totales['resu']['Reti']),
                                     '{:10.2f}'.format(totales['resu']['Grou']),
                                     '{:10.2f}'.format(totales['resu']['Divi']),
                                     '{:10.2f}'.format(totales['resu']['Perd']),
                                     '{:10.2f}'.format(totales['resu']['Fee']),
                                     '{:10.2f}'.format(totales['resu']['Comi']),
                                     '{:10.2f}'.format(totales['resu']['Tax']),
                                     '', '',
                                     '{:10.2f}'.format(totales['resu']['deve']),
                                     '{:10.2f}'.format(totales['resu']['marg']),
                                     '{:10.2%}'.format(totales['resu']['rend']),
                                     '{:10.2f}'.format(totales['resu']['pb'])))

    return totales, xcur, ix


def panel_graficos(selec: object, xestrategia: object, d_extract: object) -> object:
    global fg, cv

    if selec == 2:
        chart_extracto(fg=fg, cv=cv, dextract=d_extract, columnas=ix)

    if selec == 1:
        char_performan_estrategia(fg=fg, cv=cv, dextract=d_extract, columnas=ix)


if __name__ == '__main__':
    win = tk.Tk()
    dimension = "%dx%d+0+0" % (dw, dh)
    win.geometry(dimension)
    win.config(bg="black")
    style = ttk.Style(win)
    style.configure('TFrame',   font=('Courier', 8), foreground="white", background="black")
    dpn = ttk.Frame(win, style="TFrame", width=df, height=700)
    dpn.grid(pady=40)

    frame_strat = estrategy(master=dpn)
    frame_strat.pack()
    frame_strat.mainloop()
